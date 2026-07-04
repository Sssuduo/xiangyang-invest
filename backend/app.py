import os
import sys

# 将 backend 目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from config import config
from extensions import db, migrate, login_manager, cors
from routes import register_routes
from models import AdminUser


def create_app(config_name=None):
    """Flask 应用工厂"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    app.config.from_object(config.get(config_name, config['default']))

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*", "supports_credentials": True}})

    # Flask-Login 用户加载回调
    @login_manager.user_loader
    def load_user(user_id):
        return AdminUser.query.get(int(user_id))

    # 注册路由
    register_routes(app)

    # 自动创建数据库表（非测试环境才初始化种子数据）
    if not app.config.get('TESTING'):
        with app.app_context():
            from seed_data import init_database
            init_database(app)

    return app


if __name__ == '__main__':
    app = create_app()
    print('=' * 60)
    print('  襄阳农高区招商服务网站 — 后端 API 服务')
    print(f'  访问地址: http://localhost:5000')
    print(f'  管理员账号: admin / changeme123')
    print('=' * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
