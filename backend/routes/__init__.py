from flask import Blueprint

# 公开 API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 后台管理 blueprints
admin_auth_bp = Blueprint('admin_auth', __name__, url_prefix='/api/admin')
admin_pages_bp = Blueprint('admin_pages', __name__, url_prefix='/api/admin')
admin_provinces_bp = Blueprint('admin_provinces', __name__, url_prefix='/api/admin')
admin_models_bp = Blueprint('admin_models', __name__, url_prefix='/api/admin')
admin_prompts_bp = Blueprint('admin_prompts', __name__, url_prefix='/api/admin')
admin_homepage_bp = Blueprint('admin_homepage', __name__, url_prefix='/api/admin')
admin_contact_bp = Blueprint('admin_contact', __name__, url_prefix='/api/admin')


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
    from routes import admin_debug as _admin_debug

    app.register_blueprint(api.api_bp)
    app.register_blueprint(admin_auth.admin_auth_bp)
    app.register_blueprint(admin_pages.admin_pages_bp)
    app.register_blueprint(admin_provinces.admin_provinces_bp)
    app.register_blueprint(admin_models.admin_models_bp)
    app.register_blueprint(admin_prompts.admin_prompts_bp)
    app.register_blueprint(admin_homepage.admin_homepage_bp)
    app.register_blueprint(admin_contact.admin_contact_bp)

    # 注册 debug 路由和错误处理器
    _admin_debug.register_debug_routes(app)
