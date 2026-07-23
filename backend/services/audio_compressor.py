"""
音频文件服务

职责分为两部分：
1. 上传时：直接保存原始文件（不压缩），供在线播放
2. 夜间定时任务：压缩超过 50MB 的大文件为 Opus 格式并打包为 zip
   （压缩后文件不可在线播放，只支持下载解压）

开发环境（无 FFmpeg）：自动降级为保留原始文件。
生产环境：必须安装 FFmpeg 以启用压缩。
"""
import os
import shutil
import subprocess
import uuid
import zipfile
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 压缩目标：Opus 32kbps 单声道（语音足够清晰）
AUDIO_CODEC = 'libopus'
AUDIO_BITRATE = '32k'
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
OUTPUT_EXT = 'opus'

# 全局标记 FFmpeg 是否可用（只检查一次）
_ffmpeg_available = None


def _check_ffmpeg():
    """检查 FFmpeg 是否可用（带缓存）"""
    global _ffmpeg_available
    if _ffmpeg_available is not None:
        return _ffmpeg_available
    try:
        subprocess.run(
            ['ffmpeg', '-version'], capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        _ffmpeg_available = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _ffmpeg_available = False
    return _ffmpeg_available


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


# ======================== 上传阶段：保存原始文件 ========================


def save_original_audio(input_filepath, upload_folder):
    """
    上传时直接保存原始音频文件（不做压缩）

    原始文件保存在 static/uploads/audio/ 目录下，支持在线播放。

    Args:
        input_filepath: 临时文件绝对路径
        upload_folder: 上传根目录（如 static/uploads）

    Returns:
        dict: {
            'file_path': str,         # 保存后的文件绝对路径
            'relative_url': str,      # 相对 URL 路径
            'duration': float,        # 时长(秒)
            'file_size': int,         # 文件大小(字节)
        }
    """
    audio_dir = os.path.join(upload_folder, 'audio')
    os.makedirs(audio_dir, exist_ok=True)

    # 保留原始扩展名
    _, ext = os.path.splitext(input_filepath)
    ext = ext.lower() or '.audio'

    date_prefix = datetime.now().strftime('%Y%m%d')
    unique_id = uuid.uuid4().hex[:8]
    output_filename = f'{date_prefix}_{unique_id}_orig{ext}'
    output_path = os.path.join(audio_dir, output_filename)

    shutil.copy2(input_filepath, output_path)

    file_size = os.path.getsize(output_path)
    duration = get_audio_duration(output_path)
    relative_url = f'/static/uploads/audio/{output_filename}'

    logger.info(f'原始音频已保存：{output_filename}，{file_size / 1024 / 1024:.1f}MB，{duration:.0f}s')

    return {
        'file_path': output_path,
        'relative_url': relative_url,
        'duration': round(duration, 1),
        'file_size': file_size,
    }


# ======================== 夜间压缩阶段 ========================


def _compress_single_file(input_path, output_dir):
    """
    将单个音频文件压缩为 Opus 格式

    Args:
        input_path: 原始文件路径
        output_dir: 输出目录

    Returns:
        str: 压缩后的文件路径，失败返回 None
    """
    if not _check_ffmpeg():
        logger.warning(f'FFmpeg 未安装，跳过压缩：{input_path}')
        return None

    date_prefix = datetime.now().strftime('%Y%m%d')
    unique_id = uuid.uuid4().hex[:8]
    output_filename = f'{date_prefix}_{unique_id}_compressed.{OUTPUT_EXT}'
    output_path = os.path.join(output_dir, output_filename)

    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-c:a', AUDIO_CODEC,
        '-b:a', AUDIO_BITRATE,
        '-ar', str(AUDIO_SAMPLE_RATE),
        '-ac', str(AUDIO_CHANNELS),
        '-vn',
        '-map_metadata', '-1',
        output_path
    ]

    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            creationflags=creationflags
        )
        if result.returncode != 0 or not os.path.exists(output_path):
            logger.error(f'压缩失败：{input_path}，错误：{result.stderr[-300:] if result.stderr else "未知"}')
            return None

        orig_size = os.path.getsize(input_path)
        comp_size = os.path.getsize(output_path)
        logger.info(f'压缩完成：{orig_size / 1024 / 1024:.1f}MB → {comp_size / 1024 / 1024:.1f}MB')
        return output_path
    except Exception as e:
        logger.error(f'压缩异常：{input_path}，{e}')
        return None


def compress_to_archive(file_paths, upload_folder):
    """
    将多个音频文件压缩为 Opus 并打包为 zip 压缩包

    压缩包保存在 static/uploads/audio/archives/ 目录下。

    Args:
        file_paths: 原始文件绝对路径列表
        upload_folder: 上传根目录

    Returns:
        dict: { 'archive_path': str, 'archive_url': str, 'archive_size': int }
        或 None（压缩失败时）
    """
    import zipfile

    archive_dir = os.path.join(upload_folder, 'audio', 'archives')
    os.makedirs(archive_dir, exist_ok=True)

    temp_dir = os.path.join(upload_folder, 'audio', '_temp_compress')
    os.makedirs(temp_dir, exist_ok=True)

    compressed_files = []
    for fp in file_paths:
        cp = _compress_single_file(fp, temp_dir)
        if cp:
            compressed_files.append(cp)

    if not compressed_files:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        return None

    # 打包为 zip
    date_prefix = datetime.now().strftime('%Y%m%d')
    unique_id = uuid.uuid4().hex[:8]
    zip_filename = f'{date_prefix}_{unique_id}_audio.zip'
    zip_path = os.path.join(archive_dir, zip_filename)

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for cp in compressed_files:
                zf.write(cp, os.path.basename(cp))
        archive_size = os.path.getsize(zip_path)
        archive_url = f'/static/uploads/audio/archives/{zip_filename}'

        total_orig = sum(os.path.getsize(fp) for fp in file_paths)
        logger.info(
            f'归档完成：{len(file_paths)} 个文件 '
            f'{total_orig / 1024 / 1024:.1f}MB → {archive_size / 1024 / 1024:.1f}MB zip'
        )

        return {
            'archive_path': zip_path,
            'archive_url': archive_url,
            'archive_size': archive_size,
        }
    except Exception as e:
        logger.error(f'打包失败：{e}')
        return None
    finally:
        # 清理临时压缩文件
        for cp in compressed_files:
            try:
                if os.path.exists(cp):
                    os.remove(cp)
            except Exception:
                pass
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


def run_night_compression(threshold_bytes=0):
    """
    夜间批量压缩：扫描所有录音文件，压缩所有文件为 zip

    [V15.5 已废弃/屏蔽] 录音方式已更新，不再需要夜间压缩音频文件大小。
    调度入口 services/night_scheduler.start_night_scheduler 已移除，app.py 中启动
    代码已注释关闭，此函数不会被调用。保留实现以备查。

    Args:
        threshold_bytes: 文件大小阈值（字节），默认 0 = 压缩所有文件

    Returns:
        dict: { 'processed': int, 'compressed': int, 'skipped': int, 'errors': int }
    """
    # 屏蔽：录音方式更新后不再执行实际压缩
    return {'processed': 0, 'compressed': 0, 'skipped': 0, 'errors': 0, 'disabled': True}
    import json
    from models import ActivityLedger
    from extensions import db
    from config import Config

    items = ActivityLedger.query.filter(
        ActivityLedger.audio_files.isnot(None),
        ActivityLedger.audio_files != '[]',
        ActivityLedger.audio_files != ''
    ).all()

    upload_folder = Config.UPLOAD_FOLDER
    result = {'processed': 0, 'compressed': 0, 'skipped': 0, 'errors': 0}

    for item in items:
        result['processed'] += 1

        try:
            files = json.loads(item.audio_files or '[]')
        except Exception:
            result['errors'] += 1
            continue

        if not files:
            result['skipped'] += 1
            continue

        # 收集存在的文件
        file_paths = []
        for af in files:
            try:
                url = af['url']
                file_rel = url.lstrip('/')
                file_abs = os.path.join(os.path.dirname(upload_folder), file_rel)
                if os.path.exists(file_abs):
                    if threshold_bytes <= 0 or os.path.getsize(file_abs) >= threshold_bytes:
                        file_paths.append(file_abs)
            except Exception:
                pass

        if not file_paths:
            result['skipped'] += 1
            continue

        # 清除旧压缩包
        if item.audio_archive:
            try:
                archive_rel = item.audio_archive.lstrip('/')
                archive_abs = os.path.join(os.path.dirname(upload_folder), archive_rel)
                if os.path.exists(archive_abs):
                    os.remove(archive_abs)
            except OSError:
                pass

        # 执行压缩
        archive_result = compress_to_archive(file_paths, upload_folder)
        if archive_result:
            item.audio_archive = archive_result['archive_url']
            item.audio_archive_size = archive_result['archive_size']
            db.session.commit()
            result['compressed'] += 1
            logger.info(f'夜间压缩成功：id={item.id}，{len(file_paths)}个文件')
        else:
            result['errors'] += 1

    logger.info(
        f'夜间压缩完成：处理 {result["processed"]}，'
        f'压缩 {result["compressed"]}，'
        f'跳过 {result["skipped"]}，'
        f'错误 {result["errors"]}'
    )
    return result
