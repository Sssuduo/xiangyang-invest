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
