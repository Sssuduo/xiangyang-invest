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


class HomepageConfig(db.Model):
    """首页配置（单行记录）"""
    __tablename__ = 'homepage_config'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    background_image = db.Column(db.String(512), default='')
    title_text = db.Column(db.String(255), default='襄阳农高区')
    subtitle_text = db.Column(db.String(512), default='招商服务一站式平台')
    button1_text = db.Column(db.String(64), default='襄阳农高区介绍')
    button2_text = db.Column(db.String(64), default='招商工具箱')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'background_image': self.background_image or '',
            'title_text': self.title_text or '',
            'subtitle_text': self.subtitle_text or '',
            'button1_text': self.button1_text or '襄阳农高区介绍',
            'button2_text': self.button2_text or '招商工具箱'
        }


class CarouselPage(db.Model):
    """轮播页"""
    __tablename__ = 'carousel_pages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    page_type = db.Column(db.String(20), nullable=False, default='image_text')  # 'image_text' | 'map'
    map_scope = db.Column(db.String(20), default='china')  # 'china' | 'hubei' (仅 map 类型)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # 图文页字段
    background_image = db.Column(db.String(512), default='')
    rich_text_content = db.Column(db.Text, default='')
    text_position_x = db.Column(db.Float, default=10.0)
    text_position_y = db.Column(db.Float, default=10.0)
    text_width = db.Column(db.Float, default=40.0)
    text_height = db.Column(db.Float, default=80.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'page_type': self.page_type,
            'map_scope': self.map_scope or 'china',
            'sort_order': self.sort_order,
            'is_active': self.is_active,
            'background_image': self.background_image or '',
            'rich_text_content': self.rich_text_content or '',
            'text_position_x': self.text_position_x,
            'text_position_y': self.text_position_y,
            'text_width': self.text_width,
            'text_height': self.text_height,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ProvinceInfo(db.Model):
    """省份/城市信息"""
    __tablename__ = 'province_infos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    region_code = db.Column(db.String(6), unique=True, nullable=False)
    region_name = db.Column(db.String(64), nullable=False)
    map_scope = db.Column(db.String(20), nullable=False, default='china')  # 'china' | 'hubei'
    card_title = db.Column(db.String(255), default='')
    card_content = db.Column(db.Text, default='')
    is_highlighted = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'region_code': self.region_code,
            'region_name': self.region_name,
            'map_scope': self.map_scope,
            'card_title': self.card_title or '',
            'card_content': self.card_content or '',
            'is_highlighted': self.is_highlighted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LLMModel(db.Model):
    """大模型配置"""
    __tablename__ = 'llm_models'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    provider = db.Column(db.String(64), nullable=False, default='custom')
    api_base_url = db.Column(db.String(512), nullable=False, default='')
    api_key = db.Column(db.String(512), nullable=False, default='')
    model_name = db.Column(db.String(128), nullable=False, default='')
    temperature = db.Column(db.Float, default=0.7)
    max_tokens = db.Column(db.Integer, default=4096)
    system_prompt = db.Column(db.Text, default='')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'provider': self.provider,
            'api_base_url': self.api_base_url,
            'model_name': self.model_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'system_prompt': self.system_prompt or '',
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            # 不返回 api_key
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def to_admin_dict(self):
        """管理员视图（含 api_key）"""
        d = self.to_dict()
        d['api_key'] = self.api_key
        return d


class QuickPrompt(db.Model):
    """快捷提示词"""
    __tablename__ = 'quick_prompts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    button_text = db.Column(db.String(128), nullable=False)
    prompt_template = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(512), default='')
    category = db.Column(db.String(64), default='general')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'button_text': self.button_text,
            'prompt_template': self.prompt_template,
            'description': self.description or '',
            'category': self.category or 'general',
            'is_active': self.is_active,
            'sort_order': self.sort_order
        }
