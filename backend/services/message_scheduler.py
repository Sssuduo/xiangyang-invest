"""消息提醒定时任务 — 每天评估规则 + 生成消息"""
import logging
from services.message_engine import evaluate_all_rules

logger = logging.getLogger(__name__)


def start_message_scheduler(app):
    """启动消息提醒定时调度器(每天 09:00 跑一次，避开 08:00 业务高峰)"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning('[message_scheduler] APScheduler 未安装,跳过消息提醒定时任务。请 pip install apscheduler')
        return

    scheduler = BackgroundScheduler(timezone='Asia/Shanghai')

    def _job():
        with app.app_context():
            try:
                total = evaluate_all_rules()
                logger.info(f'[message_scheduler] 消息规则评估完成,生成 {total} 条用户消息')
            except Exception as exc:
                logger.error(f'[message_scheduler] 消息规则评估异常: {exc}')

    # 每天 09:00 执行（错开 08:00 业务写入高峰 + 夜间压缩 02:00-03:00）
    scheduler.add_job(_job, 'cron', hour=9, minute=0, id='message_rule_evaluate')
    scheduler.start()
    logger.info('[message_scheduler] 消息提醒定时任务已启动(每天 09:00)')
