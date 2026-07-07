"""
音频压缩服务

使用 FFmpeg 将录音文件压缩为 Opus 格式（高效语音编码），
大幅减小文件体积，适合服务器存储。
"""
import os
import subprocess
import uuid
from datetime import datetime


# 压缩目标：Opus 32kbps 单声道（语音场景足够清晰）
AUDIO_CODEC = 'libopus'
AUDIO_BITRATE = '32k'
AUDIO_SAMPLE_RATE = 16000  # 16kHz
AUDIO_CHANNELS = 1         # 单声道
OUTPUT_EXT = 'opus'


def _check_ffmpeg():
    """检查 FFmpeg 是否可用"""
    try:
        subprocess.run(
            ['ffmpeg', '-version'], capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_audio_duration(filepath):
    """
    获取音频时长（秒）

    使用 ffprobe 读取时长，失败时返回 0
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass
    return 0.0


def compress_audio(input_path, output_dir):
    """
    压缩音频文件

    Args:
        input_path: 原始音频文件路径
        output_dir: 输出目录（如 static/uploads/audio）

    Returns:
        tuple: (output_path, duration_seconds, original_size, compressed_size)
               - output_path: 压缩后文件的完整绝对路径
               - duration: 音频时长（秒）
               - original_size: 原始文件大小（字节）
               - compressed_size: 压缩后文件大小（字节）

    Raises:
        RuntimeError: FFmpeg 不可用时抛出
        Exception: 压缩失败时抛出
    """
    if not _check_ffmpeg():
        raise RuntimeError(
            'FFmpeg 不可用，请在生产服务器上安装 FFmpeg：\n'
            '  CentOS/RHEL: yum install -y ffmpeg\n'
            '  Ubuntu/Debian: apt install -y ffmpeg\n'
            '  Windows: 下载 https://ffmpeg.org/download.html'
        )

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 生成唯一输出文件名
    date_prefix = datetime.now().strftime('%Y%m%d')
    unique_id = uuid.uuid4().hex[:8]
    output_filename = f'{date_prefix}_{unique_id}.{OUTPUT_EXT}'
    output_path = os.path.join(output_dir, output_filename)

    # 原始文件大小
    original_size = os.path.getsize(input_path)

    # 获取音频时长
    duration = get_audio_duration(input_path)

    # 使用 FFmpeg 压缩
    cmd = [
        'ffmpeg', '-y',  # -y 覆盖已有文件
        '-i', input_path,
        '-c:a', AUDIO_CODEC,
        '-b:a', AUDIO_BITRATE,
        '-ar', str(AUDIO_SAMPLE_RATE),
        '-ac', str(AUDIO_CHANNELS),
        '-vn',  # 去除视频轨道
        '-map_metadata', '-1',  # 去除元数据（减小体积）
        output_path
    ]

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=180,
        creationflags=creationflags
    )

    if result.returncode != 0:
        raise Exception(f'音频压缩失败：{result.stderr[-500:] if result.stderr else "未知错误"}')

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise Exception('音频压缩失败：输出文件为空')

    compressed_size = os.path.getsize(output_path)

    return output_path, duration, original_size, compressed_size


def compress_audio_to_storage(input_filepath, upload_folder):
    """
    高层接口：压缩音频文件并保存到存储目录

    Args:
        input_filepath: 原始文件绝对路径
        upload_folder: 上传根目录（如 static/uploads）

    Returns:
        dict: {
            'output_path': str,          # 压缩后文件的绝对路径
            'relative_url': str,         # 相对 URL 路径（用于数据库存储）
            'duration': float,           # 时长(秒)
            'original_size': int,        # 原始大小(字节)
            'compressed_size': int,      # 压缩后大小(字节)
            'compression_ratio': float   # 压缩比
        }
    """
    from config import Config
    audio_dir = os.path.join(upload_folder, 'audio')
    output_path, duration, orig_size, comp_size = compress_audio(input_filepath, audio_dir)

    # 计算相对 URL（/static/uploads/audio/xxx.opus）
    relative_url = '/static/uploads/audio/' + os.path.basename(output_path)

    return {
        'output_path': output_path,
        'relative_url': relative_url,
        'duration': round(duration, 1),
        'original_size': orig_size,
        'compressed_size': comp_size,
        'compression_ratio': round(orig_size / comp_size, 1) if comp_size > 0 else 0
    }
