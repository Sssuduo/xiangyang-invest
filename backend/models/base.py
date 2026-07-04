"""公共基类 Mixin"""
from datetime import datetime
from extensions import db


class TimestampMixin:
    """自动时间戳 Mixin（created_at / updated_at）"""
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
