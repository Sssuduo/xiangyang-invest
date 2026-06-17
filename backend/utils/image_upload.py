import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    """检查文件扩展名是否合法"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(file, upload_folder):
    """
    保存上传的图片文件

    Args:
        file: Flask FileStorage 对象
        upload_folder: 上传目录路径（如 static/uploads）

    Returns:
        str: 文件的 URL 相对路径（如 /static/uploads/20240101_abc123.jpg）

    Raises:
        ValueError: 文件类型不合法
    """
    if not file or not file.filename:
        raise ValueError('未选择文件')

    if not allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else '未知'
        raise ValueError(f'不支持的文件类型：.{ext}，仅支持 {", ".join(ALLOWED_EXTENSIONS)}')

    # 生成唯一文件名
    ext = file.filename.rsplit('.', 1)[1].lower()
    date_prefix = datetime.now().strftime('%Y%m%d')
    unique_name = f'{date_prefix}_{uuid.uuid4().hex[:8]}.{ext}'

    # 确保目录存在
    os.makedirs(upload_folder, exist_ok=True)

    # 保存文件
    filepath = os.path.join(upload_folder, unique_name)
    file.save(filepath)

    # 返回相对 URL 路径
    return f'/static/uploads/{unique_name}'
