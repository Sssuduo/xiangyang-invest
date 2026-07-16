import os
from os import getenv
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

    # SQLAlchemy 引擎选项（连接池 + SQLite 优化）
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'connect_args': {
            'check_same_thread': False,
            'timeout': 30,
        },
        'pool_pre_ping': True,
    }

    # 文件上传配置
    # 上传目录默认指向项目 static/uploads,生产强烈推荐用环境变量覆盖为独立于代码的持久化绝对路径,
    # 这样部署时 git pull 不会清除已上传文件(详见 DEPLOY.md「上传文件持久化」)。
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(project_root, 'static', 'uploads')
    AUDIO_FOLDER = os.path.join(UPLOAD_FOLDER, 'audio')  # 录音文件专用目录
    BACKGROUNDS_FOLDER = os.path.join(UPLOAD_FOLDER, 'backgrounds')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB 上传限制（含大视频）
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # 音频压缩包阈值（字节），默认 0 = 压缩所有文件
    AUDIO_ARCHIVE_THRESHOLD = int(os.environ.get('AUDIO_ARCHIVE_THRESHOLD', '0'))

    # 笔记本 SenseVoice ASR 服务
    # 启动：笔记本运行 services/asr_api.py (port 5002)
    #       → scripts/asr_service.sh SSH 反代到 123.56.9.243:15002
    #       → 生产端 transcribe_audio 走 Config.ASR_API_URL
    ASR_API_URL = getenv('ASR_API_URL', 'http://localhost:15002').rstrip('/')
    ASR_API_TIMEOUT = int(getenv('ASR_API_TIMEOUT', '600'))       # 单次 HTTP 调用超时（秒）
    ASR_SEGMENT_SECONDS = int(getenv('ASR_SEGMENT_SECONDS', '600'))  # 长音频切片长度（秒）

    # 服务器公网地址
    SERVER_BASE_URL = os.environ.get('SERVER_BASE_URL', '')

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
