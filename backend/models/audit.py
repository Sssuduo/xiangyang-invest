"""审计模型：变更历史"""
from datetime import datetime
from extensions import db


class ChangeHistory(db.Model):
    """变更历史 / 审计日志"""
    __tablename__ = 'change_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    table_name = db.Column(db.String(64), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    field_name = db.Column(db.String(64), nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    change_type = db.Column(db.String(16), nullable=False)
    changed_by_type = db.Column(db.String(16), nullable=False)
    changed_by_id = db.Column(db.Integer, nullable=False)
    changed_by_name = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'table_name': self.table_name,
            'record_id': self.record_id,
            'field_name': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'change_type': self.change_type,
            'changed_by_type': self.changed_by_type,
            'changed_by_id': self.changed_by_id,
            'changed_by_name': self.changed_by_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
