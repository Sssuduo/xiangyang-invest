import os
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


class ProjectTagDict(db.Model):
    """项目标签字典"""
    __tablename__ = 'project_tag_dict'

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


class ActivityTagDict(db.Model):
    """动态标签字典"""
    __tablename__ = 'activity_tag_dict'

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
    person_in_charge_phone = db.Column(db.String(32), default='')
    project_doc = db.Column(db.Text, default='')
    investment_plan = db.Column(db.Text, default='')
    conclusion = db.Column(db.Text, default='')
    tags = db.Column(db.Text, default='[]')
    team_leader_ids = db.Column(db.Text, default='[]')  # JSON 数组，staff ID 列表
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
            'person_in_charge_phone': self.person_in_charge_phone or '',
            'project_doc': self.project_doc or '',
            'investment_plan': self.investment_plan or '',
            'conclusion': self.conclusion or '',
            'tags': json.loads(self.tags) if self.tags else [],
            'team_leader_ids': json.loads(self.team_leader_ids) if self.team_leader_ids else [],
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

    @staticmethod
    def resolve_display_names(codes_str, separator='、'):
        """将逗号分隔的编码字符串解析为显示名称（用于多选值）"""
        if not codes_str:
            return ''
        name_map = DemandTypeDict.build_display_name_map()
        names = []
        for code in codes_str.split(','):
            code = code.strip()
            if code:
                names.append(name_map.get(code, code))
        return separator.join(names) if names else ''


class EnterpriseDemand(db.Model):
    """企业诉求子表"""
    __tablename__ = 'enterprise_demands'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('investment_projects.id'), nullable=False)
    demand_type_code = db.Column(db.String(255), default='')
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
    tags = db.Column(db.Text, default='[]')
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
            'tags': json.loads(self.tags) if self.tags else [],
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class ActivityLedger(db.Model):
    """活动台账（未明确项目的活动记录，后续可关联到招商项目）"""
    __tablename__ = 'activity_ledger'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.DateTime, nullable=True)
    content = db.Column(db.Text, nullable=False)
    files = db.Column(db.Text, default='[]')
    tags = db.Column(db.Text, default='[]')
    linked_project_id = db.Column(db.Integer, db.ForeignKey('investment_projects.id'), nullable=True)
    linked_activity_id = db.Column(db.Integer, db.ForeignKey('investment_activities.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    linked_project = db.relationship('InvestmentProject', foreign_keys=[linked_project_id])
    linked_activity = db.relationship('InvestmentActivity', foreign_keys=[linked_activity_id])

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'content': self.content,
            'files': json.loads(self.files) if self.files else [],
            'tags': json.loads(self.tags) if self.tags else [],
            'linked_project_id': self.linked_project_id,
            'linked_project_name': self.linked_project.project_name if self.linked_project else '',
            'linked_activity_id': self.linked_activity_id,
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


class PrintTemplate(db.Model):
    """打印模板"""
    __tablename__ = 'print_template'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    entity_type = db.Column(db.String(32), default='investment')  # 'investment' | 'construction'
    # 页面布局
    paper_size = db.Column(db.String(20), default='A4')          # A4 | A3 | Letter
    orientation = db.Column(db.String(10), default='landscape')   # portrait | landscape
    font_family = db.Column(db.String(64), default='微软雅黑')     # 全局默认字体（fallback）
    font_size = db.Column(db.Integer, default=10)                 # 全局默认字号（fallback）
    # 三部分独立字体
    title_font_family = db.Column(db.String(64), default='微软雅黑')      # 大标题字体
    title_font_size = db.Column(db.Integer, default=14)                  # 大标题字号
    table_header_font_family = db.Column(db.String(64), default='微软雅黑')  # 列标题字体
    table_header_font_size = db.Column(db.Integer, default=10)           # 列标题字号
    cell_font_family = db.Column(db.String(64), default='微软雅黑')       # 单元格字体
    cell_font_size = db.Column(db.Integer, default=10)                   # 单元格字号
    header_font_size = db.Column(db.Integer, default=12)          # 标题 pt（旧，兼容）
    margin_top = db.Column(db.Float, default=0.5)                 # inches
    margin_bottom = db.Column(db.Float, default=0.5)
    margin_left = db.Column(db.Float, default=0.4)
    margin_right = db.Column(db.Float, default=0.4)
    show_page_number = db.Column(db.Boolean, default=True)
    show_print_meta = db.Column(db.Boolean, default=True)         # 显示"打印时间 + 共N条记录"
    # V3 新增
    sub_title_font_size = db.Column(db.Integer, default=12)       # 小标题字号
    title_bold = db.Column(db.Boolean, default=True)              # 大标题加粗
    subtitle_bold = db.Column(db.Boolean, default=True)           # 小标题加粗
    border_style = db.Column(db.String(20), default='all')        # 边框样式: 'all' | 'none'
    group_by = db.Column(db.String(64), default='')               # 分组字段（预留扩展）
    # 模板文件上传
    template_file = db.Column(db.String(512), default='')           # 上传的模板文件路径
    data_start_row = db.Column(db.Integer, default=3)               # 数据起始行
    header_row = db.Column(db.Integer, default=2)                   # 列标题所在行
    title_row = db.Column(db.Integer, default=1)                    # 大标题所在行
    has_group_title = db.Column(db.Boolean, default=False)          # 是否有分组标题行
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fields = db.relationship('PrintFieldConfig', backref='template', lazy='dynamic',
                             cascade='all, delete-orphan')
    mappings = db.relationship('TemplateFieldMapping', backref='template', lazy='dynamic',
                               cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'entity_type': self.entity_type,
            'paper_size': self.paper_size,
            'orientation': self.orientation,
            'font_family': self.font_family,
            'font_size': self.font_size,
            'title_font_family': self.title_font_family,
            'title_font_size': self.title_font_size,
            'table_header_font_family': self.table_header_font_family,
            'table_header_font_size': self.table_header_font_size,
            'cell_font_family': self.cell_font_family,
            'cell_font_size': self.cell_font_size,
            'header_font_size': self.header_font_size,
            'margin_top': self.margin_top,
            'margin_bottom': self.margin_bottom,
            'margin_left': self.margin_left,
            'margin_right': self.margin_right,
            'show_page_number': self.show_page_number,
            'show_print_meta': self.show_print_meta,
            'sub_title_font_size': self.sub_title_font_size,
            'title_bold': self.title_bold,
            'subtitle_bold': self.subtitle_bold,
            'border_style': self.border_style,
            'group_by': self.group_by,
            'template_file': self.template_file,
            'data_start_row': self.data_start_row,
            'header_row': self.header_row,
            'title_row': self.title_row,
            'has_group_title': self.has_group_title,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PrintFieldConfig(db.Model):
    """打印字段配置"""
    __tablename__ = 'print_field_config'
    __table_args__ = (
        db.UniqueConstraint('template_id', 'field_key', name='uq_print_template_field'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.Integer, db.ForeignKey('print_template.id'), nullable=False)
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


class TemplateFieldMapping(db.Model):
    """模板列→系统字段映射（上传 .xlsx 模板后自动解析列标题）"""
    __tablename__ = 'template_field_mapping'
    __table_args__ = (
        db.UniqueConstraint('template_id', 'column_letter', name='uq_template_column'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.Integer, db.ForeignKey('print_template.id'), nullable=False)
    column_letter = db.Column(db.String(4), nullable=False)          # Excel 列字母: A, B, ... AA
    column_header = db.Column(db.String(255), default='')            # 模板中读到的列标题原文
    field_key = db.Column(db.String(64), default='')                 # 映射的系统字段 key（空=未映射）
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'template_id': self.template_id,
            'column_letter': self.column_letter,
            'column_header': self.column_header,
            'field_key': self.field_key,
            'sort_order': self.sort_order,
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


class ImportFieldConfigConstruction(db.Model):
    """在建项目导入字段配置"""
    __tablename__ = 'import_field_config_construction'

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


class ImportFieldConfigWorkProgress(db.Model):
    """工作进展导入字段配置"""
    __tablename__ = 'import_field_config_work_progress'

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


# ============================================================
# 在建项目库
# ============================================================

class ConstructionProjectTypeDict(db.Model):
    """在建项目类型字典"""
    __tablename__ = 'construction_project_type_dict'

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


class DispatchStatusDict(db.Model):
    """调度状态字典"""
    __tablename__ = 'dispatch_status_dict'

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


class IssueTypeDict(db.Model):
    """存在问题类型字典"""
    __tablename__ = 'issue_type_dict'

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


class ResolutionStatusDict(db.Model):
    """解决状态字典"""
    __tablename__ = 'resolution_status_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    display_color = db.Column(db.String(32), default='#909399')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'display_color': self.display_color, 'sort_order': self.sort_order,
            'is_active': self.is_active
        }


class ConstructionProject(db.Model):
    """在建项目"""
    __tablename__ = 'construction_projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.Integer, nullable=False, default=0)
    project_name = db.Column(db.String(255), nullable=False)
    project_type_code = db.Column(db.String(32), nullable=False)
    dispatch_status_code = db.Column(db.String(32), nullable=False, default='dispatching')
    construction_content = db.Column(db.Text, default='')
    construction_location = db.Column(db.String(255), default='')
    start_date = db.Column(db.String(7), default='')     # 年-月 格式
    end_date = db.Column(db.String(7), default='')       # 年-月 格式
    funding_source = db.Column(db.String(255), default='')
    wuhua_platform = db.Column(db.String(8), default='')  # 是 / 否
    construction_unit = db.Column(db.String(255), default='')
    responsible_unit_code = db.Column(db.String(32), default='')
    responsible_person = db.Column(db.String(64), default='')
    responsible_person_phone = db.Column(db.String(32), default='')
    team_leader_ids = db.Column(db.Text, default='[]')    # JSON 数组
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    work_progresses = db.relationship('WorkProgress', backref='project', lazy='dynamic',
                                       order_by='WorkProgress.start_date.desc()')
    issues = db.relationship('ProjectIssue', backref='project', lazy='dynamic',
                              order_by='ProjectIssue.created_at.desc()')
    work_roadmap_items = db.relationship('WorkRoadmapItem', backref='project', lazy='dynamic',
                                          order_by='WorkRoadmapItem.sort_order.asc()')

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'project_name': self.project_name,
            'project_type_code': self.project_type_code,
            'dispatch_status_code': self.dispatch_status_code,
            'construction_content': self.construction_content or '',
            'construction_location': self.construction_location or '',
            'start_date': self.start_date or '',
            'end_date': self.end_date or '',
            'funding_source': self.funding_source or '',
            'wuhua_platform': self.wuhua_platform or '',
            'work_roadmap_items': [wri.to_dict() for wri in self.work_roadmap_items.all()],
            'construction_unit': self.construction_unit or '',
            'responsible_unit_code': self.responsible_unit_code or '',
            'responsible_person': self.responsible_person or '',
            'responsible_person_phone': self.responsible_person_phone or '',
            'team_leader_ids': json.loads(self.team_leader_ids) if self.team_leader_ids else [],
            'is_deleted': self.is_deleted,
            'work_progresses': [wp.to_dict() for wp in self.work_progresses.all()],
            'issues': [iss.to_dict() for iss in self.issues.all()],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WorkProgress(db.Model):
    """工作进展"""
    __tablename__ = 'work_progress'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('construction_projects.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text, nullable=False)
    files = db.Column(db.Text, default='[]')  # JSON array of file URLs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        _files = []
        try:
            _files = json.loads(self.files or '[]')
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            'id': self.id,
            'project_id': self.project_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'content': self.content,
            'files': _files,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ProjectIssue(db.Model):
    """存在问题"""
    __tablename__ = 'project_issues'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('construction_projects.id'), nullable=False)
    issue_type_code = db.Column(db.String(32), default='')
    issue_description = db.Column(db.Text, default='')
    resolution_status_code = db.Column(db.String(32), nullable=False, default='pending')
    resolution_note = db.Column(db.Text, default='')
    main_department_code = db.Column(db.String(32), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'issue_type_code': self.issue_type_code or '',
            'issue_description': self.issue_description or '',
            'resolution_status_code': self.resolution_status_code,
            'resolution_note': self.resolution_note or '',
            'main_department_code': self.main_department_code or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WorkRoadmapItem(db.Model):
    """工作路径图子项"""
    __tablename__ = 'work_roadmap_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('construction_projects.id'), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    content = db.Column(db.Text, nullable=False)
    planned_date = db.Column(db.Date, nullable=True)
    actual_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(32), nullable=False, default='pending')
    is_delayed = db.Column(db.Boolean, nullable=False, default=False)
    delay_reason = db.Column(db.Text, default='')
    cancel_reason = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'sort_order': self.sort_order,
            'content': self.content,
            'planned_date': self.planned_date.isoformat() if self.planned_date else None,
            'actual_date': self.actual_date.isoformat() if self.actual_date else None,
            'status': self.status,
            'is_delayed': self.is_delayed,
            'delay_reason': self.delay_reason or '',
            'cancel_reason': self.cancel_reason or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


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


# ============================================================
# 招商宣传视频
# ============================================================

class PromoVideo(db.Model):
    """招商宣传视频"""
    __tablename__ = 'promo_videos'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def thumbnail_url(self):
        """从视频路径推导缩略图 URL"""
        if not self.file_path:
            return None
        # /static/uploads/xxx.mp4 → /static/uploads/xxx_thumb.jpg
        base, ext = os.path.splitext(self.file_path)
        return f'{base}_thumb.jpg'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'file_path': self.file_path,
            'thumbnail_url': self.thumbnail_url,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
