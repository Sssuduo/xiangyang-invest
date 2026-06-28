import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.dirname(basedir)


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'xiangyang-invest-secret-key-dev'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 数据库配置 - 默认使用 SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(project_root, "instance", "app.db")}'

    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(project_root, 'static', 'uploads')
    BACKGROUNDS_FOLDER = os.path.join(UPLOAD_FOLDER, 'backgrounds')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB 上传限制（含大视频）
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Session 配置
    PERMANENT_SESSION_LIFETIME = 8 * 3600  # 8 小时

    # Debug 模式开关（通过 API 切换，存储在实例目录）
    DEBUG_MODE_FILE = os.path.join(project_root, 'instance', '.debug_mode')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
