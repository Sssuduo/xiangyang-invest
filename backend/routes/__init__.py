from flask import Blueprint

# 公开 API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 业务用户认证 blueprint
business_auth_bp = Blueprint('business_auth', __name__, url_prefix='/api/auth')

# 后台管理 blueprints
admin_auth_bp = Blueprint('admin_auth', __name__, url_prefix='/api/admin')
admin_pages_bp = Blueprint('admin_pages', __name__, url_prefix='/api/admin')
admin_provinces_bp = Blueprint('admin_provinces', __name__, url_prefix='/api/admin')
admin_models_bp = Blueprint('admin_models', __name__, url_prefix='/api/admin')
admin_prompts_bp = Blueprint('admin_prompts', __name__, url_prefix='/api/admin')
admin_homepage_bp = Blueprint('admin_homepage', __name__, url_prefix='/api/admin')
admin_contact_bp = Blueprint('admin_contact', __name__, url_prefix='/api/admin')
admin_investment_bp = Blueprint('admin_investment', __name__, url_prefix='/api/admin')
admin_export_bp = Blueprint('admin_export', __name__, url_prefix='/api/admin')
admin_import_bp = Blueprint('admin_import', __name__, url_prefix='/api/admin')

# 字典管理
admin_dict_bp = Blueprint('admin_dict', __name__, url_prefix='/api/admin')

# 招商动态
admin_activity_bp = Blueprint('admin_activity', __name__, url_prefix='/api/admin')
admin_activity_export_bp = Blueprint('admin_activity_export', __name__, url_prefix='/api/admin')
admin_activity_import_bp = Blueprint('admin_activity_import', __name__, url_prefix='/api/admin')

# 活动台账 - 主资源 CRUD (含术语校正)
admin_activity_ledger_bp = Blueprint('admin_activity_ledger', __name__, url_prefix='/api/admin')
# 术语校正 (活动台账 / 研判 / 清洁摘要)
admin_term_correction_bp = Blueprint('admin_term_correction', __name__, url_prefix='/api/admin')
# 活动台账 - 录音文件与结构化总结 (独立 blueprint 避免命名冲突)
admin_activity_ledger_audio_bp = Blueprint('admin_activity_ledger_audio', __name__, url_prefix='/api/admin')

# 企业诉求
admin_demand_bp = Blueprint('admin_demand', __name__, url_prefix='/api/admin')

# 在建项目库
admin_construction_bp = Blueprint('admin_construction', __name__, url_prefix='/api/admin')
admin_construction_import_bp = Blueprint('admin_construction_import', __name__, url_prefix='/api/admin')
admin_construction_progress_import_bp = Blueprint('admin_construction_progress_import', __name__, url_prefix='/api/admin')
admin_construction_progress_update_import_bp = Blueprint('admin_construction_progress_update_import', __name__, url_prefix='/api/admin')
admin_construction_export_bp = Blueprint('admin_construction_export', __name__, url_prefix='/api/admin')

# 打印模板
admin_print_bp = Blueprint('admin_print', __name__, url_prefix='/api/admin')
admin_construction_print_bp = Blueprint('admin_construction_print', __name__, url_prefix='/api/admin')

# 招商宣传视频
admin_promo_video_bp = Blueprint('admin_promo_video', __name__, url_prefix='/api')

# 专班工作人员管理
admin_staff_bp = Blueprint('admin_staff', __name__, url_prefix='/api/admin')

# 业务用户管理（后台）
admin_business_users_bp = Blueprint('admin_business_users', __name__, url_prefix='/api/admin')

# 招商线索研判 + 本地招商知识库
admin_lead_bp = Blueprint('admin_lead', __name__, url_prefix='/api/admin')
admin_knowledge_bp = Blueprint('admin_knowledge', __name__, url_prefix='/api/admin')

# C 端 App 只读蓝图（内部人员查看 + AI 研判 + 周报）
client_bp = Blueprint('client', __name__, url_prefix='/api/client')


def register_routes(app):
    """注册所有蓝图"""
    from routes import api
    from routes import admin_auth as _admin_auth
    from routes import admin_pages as _admin_pages
    from routes import admin_provinces as _admin_provinces
    from routes import admin_models as _admin_models
    from routes import admin_prompts as _admin_prompts
    from routes import admin_homepage as _admin_homepage
    from routes import admin_contact as _admin_contact
    from routes import admin_investment as _admin_investment
    from routes import admin_export as _admin_export
    from routes import admin_import as _admin_import
    from routes import admin_dict as _admin_dict
    from routes import admin_activity as _admin_activity
    from routes import admin_activity_export as _admin_activity_export
    from routes import admin_activity_import as _admin_activity_import
    from routes import admin_activity_ledger as _admin_activity_ledger
    from routes import admin_activity_ledger_audio as _admin_activity_ledger_audio
    from routes import admin_term_correction as _admin_term_correction
    from routes import admin_demand as _admin_demand
    from routes import admin_construction as _admin_construction
    from routes import admin_construction_import as _admin_construction_import
    from routes import admin_construction_progress_import as _admin_construction_progress_import
    from routes import admin_construction_progress_update_import as _admin_construction_progress_update_import
    from routes import admin_construction_export as _admin_construction_export
    from routes import admin_print as _admin_print
    from routes import admin_construction_print as _admin_construction_print
    from routes import admin_promo_video as _admin_promo_video
    from routes import business_auth as _business_auth
    from routes import admin_business_users as _admin_business_users
    from routes import admin_staff as _admin_staff
    from routes import admin_debug as _admin_debug
    from routes import admin_lead as _admin_lead
    from routes import admin_knowledge as _admin_knowledge

    app.register_blueprint(api.api_bp)
    app.register_blueprint(admin_auth.admin_auth_bp)
    app.register_blueprint(admin_pages.admin_pages_bp)
    app.register_blueprint(admin_provinces.admin_provinces_bp)
    app.register_blueprint(admin_models.admin_models_bp)
    app.register_blueprint(admin_prompts.admin_prompts_bp)
    app.register_blueprint(admin_homepage.admin_homepage_bp)
    app.register_blueprint(admin_contact.admin_contact_bp)
    app.register_blueprint(admin_investment.admin_investment_bp)
    app.register_blueprint(admin_dict.admin_dict_bp)
    app.register_blueprint(admin_export.admin_export_bp)
    app.register_blueprint(admin_import.admin_import_bp)
    app.register_blueprint(admin_activity.admin_activity_bp)
    app.register_blueprint(admin_activity_export.admin_activity_export_bp)
    app.register_blueprint(admin_activity_import.admin_activity_import_bp)
    app.register_blueprint(admin_activity_ledger.admin_activity_ledger_bp)
    app.register_blueprint(admin_activity_ledger_audio.admin_activity_ledger_audio_bp)
    app.register_blueprint(admin_term_correction.admin_term_correction_bp)
    app.register_blueprint(admin_demand.admin_demand_bp)
    app.register_blueprint(admin_construction.admin_construction_bp)
    app.register_blueprint(admin_construction_import.admin_construction_import_bp)
    app.register_blueprint(admin_construction_progress_import.admin_construction_progress_import_bp)
    app.register_blueprint(admin_construction_progress_update_import.admin_construction_progress_update_import_bp)
    app.register_blueprint(admin_construction_export.admin_construction_export_bp)
    app.register_blueprint(admin_print.admin_print_bp)
    app.register_blueprint(admin_construction_print.admin_construction_print_bp)
    app.register_blueprint(admin_promo_video.admin_promo_video_bp)

    # 注册业务用户认证和管理蓝图
    app.register_blueprint(business_auth.business_auth_bp)
    app.register_blueprint(admin_staff.admin_staff_bp)
    app.register_blueprint(admin_business_users.admin_business_users_bp)
    app.register_blueprint(admin_lead.admin_lead_bp)
    app.register_blueprint(admin_knowledge.admin_knowledge_bp)

    # 注册 C 端 App 只读蓝图（当前禁用：移动端功能暂不上线）
    # from routes import client as _client
    # app.register_blueprint(client.client_bp)

    # 注册 debug 路由和错误处理器
    _admin_debug.register_debug_routes(app)
