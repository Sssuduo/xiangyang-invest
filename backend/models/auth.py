"""认证相关模型：管理员 / 业务用户 / 工作人员"""
import json
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class AdminUser(UserMixin, db.Model):
    """管理员账号"""
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='scrypt')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Staff(db.Model):
    """工作人员（专班成员）"""
    __tablename__ = 'staff'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), nullable=False)
    position = db.Column(db.String(128), default='农高区创建专班工作人员')
    user_id = db.Column(db.Integer, db.ForeignKey('business_users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'position': self.position or '农高区创建专班工作人员',
            'user_id': self.user_id,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BusinessUser(UserMixin, db.Model):
    """业务用户（前台登录）— 由管理员在后台配置"""
    __tablename__ = 'business_users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(16), default='user')  # 'user' | 'visitor'
    permissions = db.Column(db.Text, default='{}')  # JSON: {"investment":{"edit":true,...},...}
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='scrypt')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_permissions(self):
        """返回权限字典"""
        try:
            return json.loads(self.permissions) if self.permissions else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_permissions(self, perms_dict):
        """保存权限字典"""
        self.permissions = json.dumps(perms_dict, ensure_ascii=False)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'is_active': self.is_active,
            'role': self.role,
            'permissions': self.get_permissions(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
