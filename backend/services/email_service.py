"""
邮件通知服务（揭榜挂帅对外端口回执 + 通用能力）

- 通过 smtplib 发送，支持 SSL(465) / STARTTLS(587)
- 配置来自环境变量（生产在 backend/.env 注入）：
    SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM
- 线程池异步发送，不阻塞 HTTP 请求
- SMTP 未配置或发送失败 → 记日志降级（不抛异常，不阻断业务）
"""
import logging
import smtplib
import threading
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

logger = logging.getLogger(__name__)

_send_lock = threading.Lock()


def _get_smtp_config():
    import os
    host = os.environ.get('SMTP_HOST', '')
    if not host:
        return None
    return {
        'host': host,
        'port': int(os.environ.get('SMTP_PORT', '465')),
        'user': os.environ.get('SMTP_USER', ''),
        'password': os.environ.get('SMTP_PASSWORD', ''),
        'from_addr': os.environ.get('SMTP_FROM', '') or os.environ.get('SMTP_USER', ''),
        'from_name': os.environ.get('SMTP_FROM_NAME', '襄阳农高区揭榜挂帅平台'),
    }


def email_configured() -> bool:
    """SMTP 是否已配置（供前端提示"回执邮件服务未配置"）"""
    return _get_smtp_config() is not None


def _send_sync(cfg, to_addr, subject, html_body):
    """同步发送单封邮件；失败抛异常由调用方捕获"""
    msg = MIMEText(html_body, 'html', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = formataddr((str(Header(cfg['from_name'], 'utf-8')), cfg['from_addr']))
    msg['To'] = to_addr

    if cfg['port'] == 465:
        server = smtplib.SMTP_SSL(cfg['host'], cfg['port'], timeout=30)
    else:
        server = smtplib.SMTP(cfg['host'], cfg['port'], timeout=30)
        server.ehlo()
        if cfg['port'] == 587:
            server.starttls()
            server.ehlo()
    try:
        if cfg['user']:
            server.login(cfg['user'], cfg['password'])
        server.sendmail(cfg['from_addr'], [to_addr], msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass


def send_email(to_addr, subject, html_body, async_send=True):
    """发送邮件。async_send=True 时后台线程发送（默认）。

    返回 True/False：False 表示未配置或发送失败（已记日志，不抛异常）。
    """
    cfg = _get_smtp_config()
    if not cfg:
        logger.warning('[email] SMTP 未配置，跳过发送：to=%s subject=%s', to_addr, subject)
        return False
    if not to_addr:
        logger.warning('[email] 收件地址为空，跳过发送')
        return False

    def _worker():
        try:
            _send_sync(cfg, to_addr, subject, html_body)
            logger.info('[email] 发送成功：to=%s subject=%s', to_addr, subject)
        except Exception as e:
            logger.error('[email] 发送失败：to=%s subject=%s err=%s', to_addr, subject, e)

    if async_send:
        threading.Thread(target=_worker, daemon=True).start()
        return True
    else:
        try:
            _send_sync(cfg, to_addr, subject, html_body)
            logger.info('[email] 发送成功：to=%s subject=%s', to_addr, subject)
            return True
        except Exception as e:
            logger.error('[email] 发送失败：to=%s subject=%s err=%s', to_addr, subject, e)
            return False


# ---------------------------------------------------------------------------
# 揭榜挂帅回执模板
# ---------------------------------------------------------------------------

def send_register_receipt(email, username, org_name):
    """注册成功回执"""
    subject = '【襄阳农高区揭榜挂帅平台】注册成功通知'
    body = f"""
    <div style="font-family: 'Microsoft YaHei', sans-serif; max-width: 640px; margin: 0 auto; line-height: 1.8; color: #333;">
      <h2 style="color: #1a3a5c;">揭榜挂帅平台注册成功</h2>
      <p>尊敬的 {org_name or '揭榜方'}：</p>
      <p>您好！您已在<strong>襄阳国家农高区揭榜挂帅平台</strong>成功注册账号，信息如下：</p>
      <table style="border-collapse: collapse; margin: 12px 0;">
        <tr><td style="padding: 4px 16px 4px 0; color: #666;">登录账号</td><td style="padding: 4px 0;"><strong>{username}</strong></td></tr>
        <tr><td style="padding: 4px 16px 4px 0; color: #666;">注册邮箱</td><td style="padding: 4px 0;">{email}</td></tr>
      </table>
      <p>您可以登录平台浏览已发布的揭榜榜单并提交揭榜申请。如有疑问，请联系农高区招商专班。</p>
      <p style="color: #999; font-size: 12px;">此邮件由系统自动发送，请勿直接回复。</p>
    </div>
    """
    return send_email(email, subject, body)


def send_apply_receipt(email, org_name, board_title, bid_id):
    """揭榜申请提交回执"""
    subject = '【襄阳农高区揭榜挂帅平台】揭榜申请已提交'
    body = f"""
    <div style="font-family: 'Microsoft YaHei', sans-serif; max-width: 640px; margin: 0 auto; line-height: 1.8; color: #333;">
      <h2 style="color: #1a3a5c;">揭榜申请提交成功</h2>
      <p>尊敬的 {org_name or '揭榜方'}：</p>
      <p>您好！您提交的揭榜申请已成功受理：</p>
      <table style="border-collapse: collapse; margin: 12px 0;">
        <tr><td style="padding: 4px 16px 4px 0; color: #666;">榜单名称</td><td style="padding: 4px 0;"><strong>{board_title}</strong></td></tr>
        <tr><td style="padding: 4px 16px 4px 0; color: #666;">申请编号</td><td style="padding: 4px 0;">BID-{bid_id}</td></tr>
      </table>
      <p>申请将进入<strong>专家评审</strong>环节，评审结果确定后可在平台「我的申请」中查看进展。请保持联系方式畅通。</p>
      <p style="color: #999; font-size: 12px;">此邮件由系统自动发送，请勿直接回复。</p>
    </div>
    """
    return send_email(email, subject, body)
