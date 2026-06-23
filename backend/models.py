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


class BusinessUser(UserMixin, db.Model):
    """业务用户（前台登录）— 由管理员在后台配置"""
    __tablename__ = 'business_users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
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
            'permissions': self.get_permissions(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class HomepageConfig(db.Model):
    """首页配置（单行记录）"""
    __tablename__ = 'homepage_config'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    background_image = db.Column(db.String(512), default='')
    title_text = db.Column(db.String(255), default='襄阳农高区')
    subtitle_text = db.Column(db.String(512), default='招商服务一站式平台')
    carousel_interval = db.Column(db.Integer, default=8)  # 轮播自动切换间隔（秒），默认8秒
    carousel_display_mode = db.Column(db.String(20), default='coverflow')  # 'coverflow' | 'fullscreen'
    carousel_width = db.Column(db.Integer, default=85)    # 轮播宽度（视口百分比），默认85%
    carousel_height = db.Column(db.Integer, default=80)   # 轮播高度（视口百分比），默认80%
    presentation_interval = db.Column(db.Integer, default=5)  # 演示模式自动切换间隔（秒），默认5秒
    carousel_autoplay = db.Column(db.Boolean, default=True)  # 轮播模式是否自动播放，默认开启
    presentation_autoplay = db.Column(db.Boolean, default=True)  # 演示模式是否自动播放，默认开启
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'background_image': self.background_image or '',
            'title_text': self.title_text or '',
            'subtitle_text': self.subtitle_text or '',
            'carousel_interval': self.carousel_interval if self.carousel_interval is not None else 8,
            'carousel_display_mode': self.carousel_display_mode or 'coverflow',
            'carousel_width': self.carousel_width if self.carousel_width is not None else 85,
            'carousel_height': self.carousel_height if self.carousel_height is not None else 80,
            'presentation_interval': self.presentation_interval if self.presentation_interval is not None else 5,
            'carousel_autoplay': self.carousel_autoplay if self.carousel_autoplay is not None else True,
            'presentation_autoplay': self.presentation_autoplay if self.presentation_autoplay is not None else True
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
            'has_city_highlights': bool(CityInfo.query.filter_by(province_id=self.id, is_highlighted=True).first()),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class CityInfo(db.Model):
    """城市/区县高亮信息（省份的子级）"""
    __tablename__ = 'city_infos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    province_id = db.Column(db.Integer, db.ForeignKey('province_infos.id'), nullable=False)
    city_code = db.Column(db.String(6), nullable=False)
    city_name = db.Column(db.String(64), nullable=False)
    is_highlighted = db.Column(db.Boolean, nullable=False, default=False)
    card_title = db.Column(db.String(255), default='')
    card_content = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('province_id', 'city_code', name='uq_province_city'),
    )

    province = db.relationship('ProvinceInfo', backref=db.backref('cities', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'province_id': self.province_id,
            'city_code': self.city_code,
            'city_name': self.city_name,
            'is_highlighted': self.is_highlighted,
            'card_title': self.card_title or '',
            'card_content': self.card_content or '',
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


# ============================================================
# 招商对接项目库
# ============================================================

class FollowStatusDict(db.Model):
    """跟进状态字典"""
    __tablename__ = 'follow_status_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    display_color = db.Column(db.String(32), default='#909399')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'display_color': self.display_color, 'sort_order': self.sort_order,
            'is_active': self.is_active
        }


class MeetingStatusDict(db.Model):
    """上会状态字典"""
    __tablename__ = 'meeting_status_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    display_color = db.Column(db.String(32), default='#909399')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'display_color': self.display_color, 'sort_order': self.sort_order,
            'is_active': self.is_active
        }


class OrganizationDict(db.Model):
    """单位字典（推介单位 & 包保单位共用）"""
    __tablename__ = 'organization_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'sort_order': self.sort_order, 'is_active': self.is_active
        }


class ProjectTypeDict(db.Model):
    """项目类型字典"""
    __tablename__ = 'project_type_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'sort_order': self.sort_order, 'is_active': self.is_active
        }


class InvestmentProject(db.Model):
    """招商对接项目"""
    __tablename__ = 'investment_projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.Integer, nullable=False, default=0)
    project_name = db.Column(db.String(255), nullable=False)
    invest_enterprise = db.Column(db.String(255), nullable=False)
    enterprise_info = db.Column(db.Text, nullable=False)
    project_content = db.Column(db.Text, nullable=False)
    invest_amount = db.Column(db.Numeric(15, 2), nullable=False)  # 万元

    follow_status_code = db.Column(db.String(32), nullable=False)
    meeting_status_code = db.Column(db.String(32), nullable=False, default='not_meeting')
    recommend_unit_code = db.Column(db.String(32), default='')
    responsible_unit_code = db.Column(db.String(32), nullable=True, default='')
    project_type_code = db.Column(db.String(32), nullable=False)

    person_in_charge = db.Column(db.String(64), default='')
    project_doc = db.Column(db.Text, default='')
    investment_plan = db.Column(db.Text, default='')
    conclusion = db.Column(db.Text, default='')
    first_contact_date = db.Column(db.Date)

    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    demands = db.relationship('EnterpriseDemand', backref='project', lazy='dynamic',
                              order_by='EnterpriseDemand.sort_order')

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'project_name': self.project_name,
            'invest_enterprise': self.invest_enterprise,
            'enterprise_info': self.enterprise_info or '',
            'project_content': self.project_content or '',
            'invest_amount': float(self.invest_amount) if self.invest_amount else 0,
            'follow_status_code': self.follow_status_code,
            'meeting_status_code': self.meeting_status_code,
            'recommend_unit_code': self.recommend_unit_code or '',
            'responsible_unit_code': self.responsible_unit_code,
            'project_type_code': self.project_type_code,
            'person_in_charge': self.person_in_charge or '',
            'project_doc': self.project_doc or '',
            'investment_plan': self.investment_plan or '',
            'conclusion': self.conclusion or '',
            'first_contact_date': self.first_contact_date.isoformat() if self.first_contact_date else None,
            'is_deleted': self.is_deleted,
            'demands': [d.to_dict() for d in self.demands.all()],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DemandTypeDict(db.Model):
    """诉求类型字典（支持两级：parent_code 为空则为一级）"""
    __tablename__ = 'demand_type_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    parent_code = db.Column(db.String(32), default='')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'parent_code': self.parent_code or '',
            'sort_order': self.sort_order, 'is_active': self.is_active
        }

    @staticmethod
    def build_display_name_map():
        """构建 code → display_name 映射（子级显示为 一级：二级）"""
        all_items = DemandTypeDict.query.all()
        name_map = {d.code: d.name for d in all_items}
        result = {}
        for d in all_items:
            if d.parent_code and d.parent_code in name_map:
                result[d.code] = f'{name_map[d.parent_code]}：{d.name}'
            else:
                result[d.code] = d.name
        return result


class EnterpriseDemand(db.Model):
    """企业诉求子表"""
    __tablename__ = 'enterprise_demands'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('investment_projects.id'), nullable=False)
    demand_type_code = db.Column(db.String(32), default='')
    demand_content = db.Column(db.Text, nullable=False)
    resolution = db.Column(db.Text, default='')
    unit_code = db.Column(db.String(32), default='')
    status = db.Column(db.String(32), nullable=False, default='pending')  # pending/processing/resolved
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'demand_type_code': self.demand_type_code or '',
            'demand_content': self.demand_content,
            'resolution': self.resolution or '',
            'unit_code': self.unit_code or '',
            'status': self.status,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ContactInfo(db.Model):
    """联系我们 — 个人名片配置（单行记录）"""
    __tablename__ = 'contact_info'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), default='')
    title = db.Column(db.String(255), default='')
    phone = db.Column(db.String(32), default='')
    email = db.Column(db.String(255), default='')
    intro = db.Column(db.Text, default='')
    wechat_qr_image = db.Column(db.String(512), default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name or '',
            'title': self.title or '',
            'phone': self.phone or '',
            'email': self.email or '',
            'intro': self.intro or '',
            'wechat_qr_image': self.wechat_qr_image or ''
        }


class ExportTemplate(db.Model):
    """导出模板（支持多模板命名）"""
    __tablename__ = 'export_template'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    entity_type = db.Column(db.String(32), default='investment')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fields = db.relationship('ExportFieldConfig', backref='template', lazy='dynamic',
                              cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'entity_type': self.entity_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ExportFieldConfig(db.Model):
    """导出字段配置"""
    __tablename__ = 'export_field_config'
    __table_args__ = (
        db.UniqueConstraint('template_id', 'field_key', name='uq_template_field'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.Integer, db.ForeignKey('export_template.id'), nullable=False, default=1)
    field_key = db.Column(db.String(64), nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_visible = db.Column(db.Boolean, default=True)
    is_custom = db.Column(db.Boolean, default=False)
    column_width = db.Column(db.Integer, default=120)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'template_id': self.template_id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_visible': self.is_visible,
            'is_custom': self.is_custom,
            'column_width': self.column_width,
            'sort_order': self.sort_order
        }


class ImportFieldConfig(db.Model):
    """导入字段配置（导入模板的列定义）"""
    __tablename__ = 'import_field_config'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field_key = db.Column(db.String(64), unique=True, nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_required = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_enabled': self.is_enabled,
            'is_required': self.is_required,
            'sort_order': self.sort_order
        }


class InvestmentActivity(db.Model):
    """招商动态"""
    __tablename__ = 'investment_activities'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('investment_projects.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=True)
    content = db.Column(db.Text, nullable=False)
    files = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship('InvestmentProject', backref=db.backref('activities', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'project_name': self.project.project_name if self.project else '',
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'content': self.content,
            'files': json.loads(self.files) if self.files else [],
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class ExportFieldConfigActivity(db.Model):
    """招商动态导出字段配置"""
    __tablename__ = 'export_field_config_activity'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field_key = db.Column(db.String(64), unique=True, nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_visible = db.Column(db.Boolean, default=True)
    column_width = db.Column(db.Integer, default=120)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_visible': self.is_visible,
            'column_width': self.column_width,
            'sort_order': self.sort_order
        }


class ImportFieldConfigActivity(db.Model):
    """招商动态导入字段配置"""
    __tablename__ = 'import_field_config_activity'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field_key = db.Column(db.String(64), unique=True, nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_required = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_enabled': self.is_enabled,
            'is_required': self.is_required,
            'sort_order': self.sort_order
        }


class ImportFieldConfigDemand(db.Model):
    """企业诉求导入字段配置"""
    __tablename__ = 'import_field_config_demand'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field_key = db.Column(db.String(64), unique=True, nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_required = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_enabled': self.is_enabled,
            'is_required': self.is_required,
            'sort_order': self.sort_order
        }
