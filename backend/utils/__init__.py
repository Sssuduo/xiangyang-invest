from flask import session
from flask_login import current_user
from models import BusinessUser, ChangeHistory
from extensions import db


def get_current_user_info():
    """
    获取当前登录用户信息（兼容 admin 和 business 两种登录方式）。
    返回: (user_type, user_id, display_name) 或 None
    """
    # 先检查 AdminUser（Flask-Login）
    if current_user.is_authenticated:
        return ('admin', current_user.id, current_user.display_name or current_user.username)

    # 再检查 BusinessUser（session）
    user_id = session.get('business_user_id')
    if user_id:
        user = BusinessUser.query.get(int(user_id))
        if user:
            return ('business', user.id, user.display_name or user.username)

    return None


def log_changes(table_name, record_id, changes_dict, change_type, user_info):
    """
    批量记录字段级变更历史。

    Args:
        table_name: 表名 (str)
        record_id: 记录主键 (int)
        changes_dict: {field_name: (old_value, new_value)}
        change_type: 'create' 或 'update'
        user_info: get_current_user_info() 的返回值
    """
    if user_info is None:
        return

    for field_name, (old_val, new_val) in changes_dict.items():
        if old_val != new_val:
            record = ChangeHistory(
                table_name=table_name,
                record_id=record_id,
                field_name=field_name,
                old_value=str(old_val) if old_val is not None else None,
                new_value=str(new_val) if new_val is not None else None,
                change_type=change_type,
                changed_by_type=user_info[0],
                changed_by_id=user_info[1],
                changed_by_name=user_info[2]
            )
            db.session.add(record)


# ============================================================
# SQLite 监控：锁等待 + 慢操作装饰器
# ============================================================
import time as _time
import logging as _logging

_logger = _logging.getLogger(__name__)

# 慢操作阈值（秒）：超过则记 warning 日志
SLOW_OPERATION_THRESHOLD = 1.0


def monitor_db_operation(func):
    """
    装饰器：监控 DB 操作的锁等待时间。

    用法：在调用 DB 的关键函数上加 @monitor_db_operation
    示例：
        @monitor_db_operation
        def import_activities():
            ...

    触发条件：
      - 抛出 'database is locked' 异常时记 warning
      - 单次操作超过 SLOW_OPERATION_THRESHOLD 时记 warning
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = _time.time()
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            if 'database is locked' in str(exc).lower() or 'locked' in str(exc).lower():
                _logger.warning(
                    f'[SQLite 锁等待超时] {func.__name__}({args!r}, {kwargs!r}): {exc}'
                )
            raise
        finally:
            elapsed = _time.time() - start
            if elapsed > SLOW_OPERATION_THRESHOLD:
                _logger.warning(
                    f'[SQLite 慢操作] {func.__name__} 耗时 {elapsed:.3f}s (阈值 {SLOW_OPERATION_THRESHOLD}s)'
                )
    return wrapper


def log_slow_query(sql: str, elapsed: float):
    """
    供路由层调用：手动记录慢查询。

    用法（在路由内）：
        log_slow_query("SELECT ... FROM large_table", elapsed=1.23)
    """
    if elapsed > SLOW_OPERATION_THRESHOLD:
        _logger.warning(f'[慢查询] {elapsed:.3f}s | {sql[:200]}')
