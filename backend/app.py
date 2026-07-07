import os
import sys

# 将 backend 目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from config import config
from extensions import db, migrate, login_manager, cors
from routes import register_routes
from models import AdminUser


def _run_auto_migrations(app):
    """自动向已存在的数据库表添加缺失的列（简化版迁移，适用于 SQLite）。
    
    生产环境新增模型字段后，db.create_all() 不会修改已有表结构，
    此处逐表检查并补上缺失列，避免 500 错误。
    """
    from sqlalchemy import inspect, text
    from extensions import db as _db

    # 各表缺失列映射：{表名: [(列名, 列类型), ...]}
    MIGRATIONS = {
        'activity_ledger': [
            ('audio_archive', 'TEXT'),
            ('audio_archive_size', 'INTEGER'),
        ],
        'work_progress': [
            ('import_user_id', 'INTEGER'),
            ('import_user_name', 'VARCHAR(128)'),
        ],
        # 后续如有新增字段，在此追加即可
    }

    with app.app_context():
        inspector = inspect(_db.engine)
        for table_name, cols in MIGRATIONS.items():
            try:
                existing_cols = {c['name'] for c in inspector.get_columns(table_name)}
            except Exception:
                continue  # 表不存在，skip

            for col_name, col_type in cols:
                if col_name not in existing_cols:
                    try:
                        _db.session.execute(
                            text(f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}')
                        )
                        _db.session.commit()
                        app.logger.info(
                            f'[自动迁移] 表 {table_name} 已添加缺失列 {col_name} ({col_type})'
                        )
                    except Exception as exc:
                        _db.session.rollback()
                        app.logger.warning(
                            f'[自动迁移] 添加列失败 ({table_name}.{col_name}): {exc}'
                        )


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

        # 自动添加缺失的数据库列（简化迁移）
        _run_auto_migrations(app)

    # 启动夜间压缩调度器
    if not app.config.get('TESTING'):
        from services.night_scheduler import start_night_scheduler
        start_night_scheduler(app)

    return app


if __name__ == '__main__':
    app = create_app()
    print('=' * 60)
    print('  襄阳农高区招商服务网站 — 后端 API 服务')
    print(f'  访问地址: http://localhost:5000')
    print(f'  管理员账号: admin / changeme123')
    print('=' * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
