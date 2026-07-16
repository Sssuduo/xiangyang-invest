"""
upload_health.py — 启动期上传文件健康扫描

扫描所有引用上传文件的表,输出缺失清单到日志,避免"DB 引用但磁盘无文件"静默 404。
未来如果引入新表保存 files 引用,在此处追加 TABLE_SCHEMAS 条目即可。

调用方:
- backend/app.py create_app(): 启动时跑一次,logger.warning 汇总缺失
- backend/routes/api.py /api/uploads/health: 给后台/监控用的统计接口
"""
import json
import logging
import os

logger = logging.getLogger(__name__)


# (表模型类, files 字段名, 业务标签)
# 扫描时按反射读 column,避免 import 具体模型类带来耦合
TABLE_SCHEMAS = [
    ('InvestmentActivity', 'files', '招商动态'),
    ('ActivityLedger', 'files', '活动台账-图片附件'),
    ('ActivityLedger', 'audio_files', '活动台账-录音文件'),
    # work_progress / project_issues / work_roadmap_items 等表如有 files 引用可在此追加
]


def _get_model_class(model_name: str):
    """延迟导入,避免循环 import 与启动期沉重导入"""
    from models import InvestmentActivity, ActivityLedger
    mapping = {
        'InvestmentActivity': InvestmentActivity,
        'ActivityLedger': ActivityLedger,
    }
    return mapping.get(model_name)


def scan_missing_uploads(app) -> dict:
    """
    返回:
    {
      "upload_folder": "...",
      "total_referenced": 120,     # DB 引用的文件总数
      "missing_count": 3,
      "missing": [
         {"table": "investment_activities", "field": "files", "id": 157, "label": "招商动态",
          "url": "/static/uploads/20260627_09b76c10.jpg", "path": "/abs/path/static/uploads/xxx.jpg"},
         ...
      ],
      "present_count": 117
    }
    """
    upload_folder = app.config.get('UPLOAD_FOLDER') or ''
    upload_folder_real = os.path.realpath(upload_folder)

    referenced = 0
    present = 0
    missing = []

    with app.app_context():
        for model_name, field, label in TABLE_SCHEMAS:
            model_cls = _get_model_class(model_name)
            if model_cls is None:
                continue
            try:
                rows = model_cls.query.with_entities(
                    model_cls.id, getattr(model_cls, field)
                ).all()
            except Exception as e:
                logger.warning('[upload_health] 读取 %s.%s 失败: %s', model_name, field, e)
                continue

            for row_id, raw in rows:
                if not raw:
                    continue
                try:
                    items = json.loads(raw)
                    if isinstance(items, str):
                        items = json.loads(items)
                except Exception:
                    items = []
                if not isinstance(items, (list, tuple)):
                    items = [items]

                for item in items:
                    url = None
                    if isinstance(item, str):
                        url = item
                    elif isinstance(item, dict):
                        url = item.get('url') or item.get('file') or item.get('path')
                    if not url:
                        continue

                    referenced += 1
                    # URL 形如 /static/uploads/xxx; 去掉前缀,基于 UPLOAD_FOLDER 拼接绝对路径
                    rel = url
                    for prefix in ('/static/uploads/', '/uploads/'):
                        if rel.startswith(prefix):
                            rel = rel[len(prefix):]
                            break
                    # 防止路径穿越
                    rel = rel.lstrip('/')
                    if '..' in rel.split(os.sep) or '..' in rel.split('/'):
                        continue
                    abs_path = os.path.join(upload_folder_real, rel)
                    abs_path = os.path.realpath(abs_path)
                    # 二次校验仍在 upload_folder 内
                    if not abs_path.startswith(upload_folder_real + os.sep) and abs_path != upload_folder_real:
                        continue
                    if os.path.exists(abs_path):
                        present += 1
                    else:
                        missing.append({
                            'table': model_cls.__tablename__,
                            'field': field,
                            'id': row_id,
                            'label': label,
                            'url': url,
                            'expected_path': abs_path,
                        })

    return {
        'upload_folder': upload_folder_real,
        'total_referenced': referenced,
        'present_count': present,
        'missing_count': len(missing),
        'missing': missing,
    }


def log_missing_report(app) -> None:
    """启动时打印一次性报告,用 warning 级便于日志采集"""
    try:
        report = scan_missing_uploads(app)
    except Exception as e:
        logger.warning('[upload_health] 启动扫描异常: %s', e)
        return

    logger.info(
        '[upload_health] 上传目录=%s,引用总数=%d,缺失=%d',
        report['upload_folder'], report['total_referenced'], report['missing_count']
    )
    if report['missing_count'] > 0:
        # 只打印前 20 个,防止日志爆炸
        preview = report['missing'][:20]
        details = '; '.join(
            f"{m['table']}.{m['field']}#id={m['id']} -> {m['url']}" for m in preview
        )
        logger.warning(
            '[upload_health] 缺失文件 %d 个(仅显示前%d): %s',
            report['missing_count'], len(preview), details
        )
        logger.warning(
            '[upload_health] 修复建议: 从备份恢复对应文件到 %s,或在 admin/系统管理 查看完整清单 /api/uploads/health',
            report['upload_folder']
        )
