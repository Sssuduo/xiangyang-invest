import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'mp4', 'webm', 'mov', 'avi', 'mkv', 'ogg', 'wmv', 'flv', 'm4v'}

# 录音文件允许的扩展名
AUDIO_EXTENSIONS = {'wav', 'mp3', 'm4a', 'ogg', 'flac', 'wma', 'aac', 'amr', 'opus', 'webm', 'weba'}


def allowed_file(filename):
    """检查文件扩展名是否合法"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(file, upload_folder, keep_original_name=False):
    """
    保存上传的文件

    Args:
        file: Flask FileStorage 对象
        upload_folder: 上传目录路径（如 static/uploads）
        keep_original_name: True 时保留原始文件名（加日期前缀防重名），
                            False 时生成 UUID 短名（默认）

    Returns:
        dict: {'url': str, 'original_name': str} — URL 相对路径 + 原始文件名

    Raises:
        ValueError: 文件类型不合法
    """
    if not file or not file.filename:
        raise ValueError('未选择文件')

    if not allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else '未知'
        raise ValueError(f'不支持的文件类型：.{ext}，仅支持 {", ".join(ALLOWED_EXTENSIONS)}')

    original_name = file.filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    date_prefix = datetime.now().strftime('%Y%m%d')

    if keep_original_name:
        # 保留原始文件名（添加日期前缀防重名）
        base_name = file.filename.rsplit('.', 1)[0]
        safe_base = secure_filename(base_name) or 'file'
        safe_ext = secure_filename(ext)
        unique_name = f'{date_prefix}_{safe_base}.{safe_ext}'
    else:
        unique_name = f'{date_prefix}_{uuid.uuid4().hex[:8]}.{ext}'

    # 确保目录存在
    os.makedirs(upload_folder, exist_ok=True)

    # 处理重名（添加序号）
    filepath = os.path.join(upload_folder, unique_name)
    if os.path.exists(filepath) and keep_original_name:
        counter = 1
        base = unique_name.rsplit('.', 1)[0]
        while os.path.exists(filepath):
            unique_name = f'{base}_{counter}.{ext}'
            filepath = os.path.join(upload_folder, unique_name)
            counter += 1

    # 保存文件
    file.save(filepath)

    return {
        'url': f'/static/uploads/{unique_name}',
        'original_name': original_name,
    }
