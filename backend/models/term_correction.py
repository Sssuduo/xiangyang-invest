"""术语校正模型 — 通用词汇映射表。"""
from datetime import datetime
from extensions import db


class TermCorrection(db.Model):
    __tablename__ = 'term_corrections'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    original = db.Column(db.String(255), nullable=False, index=True)   # 原文词汇 (如 ASR 识别错写)
    replacement = db.Column(db.String(255), nullable=False)            # 正确替换词
    is_active = db.Column(db.Boolean, nullable=False, default=True)     # 是否启用
    apply_scope = db.Column(db.String(32), nullable=False, default='all')  # all | summary | clean | segmented
    created_by = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('original', name='uq_term_correction_original'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'original': self.original,
            'replacement': self.replacement,
            'is_active': self.is_active,
            'apply_scope': self.apply_scope,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }
