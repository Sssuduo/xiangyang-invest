"""
公文写作模板模型
"""
from datetime import datetime
from extensions import db


class OfficialDocTemplate(db.Model):
    """公文写作模板"""
    __tablename__ = 'official_doc_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='模板名称')
    doc_type = db.Column(db.String(32), comment='文体类型')
    content = db.Column(db.Text, comment='模板内容')
    structure = db.Column(db.Text, comment='模板结构（JSON）')
    file_name = db.Column(db.String(255), comment='原始文件名')
    file_size = db.Column(db.Integer, default=0, comment='文件大小')
    created_by = db.Column(db.Integer, db.ForeignKey('business_users.id'), comment='创建人')
    is_deleted = db.Column(db.Boolean, default=False, comment='是否删除')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'doc_type': self.doc_type,
            'content': self.content,
            'structure': self.structure,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
