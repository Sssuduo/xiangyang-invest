"""
语音转文字客户端 — 生产端纯 HTTP 调用笔记本 ASR 服务。

部署架构：
  笔记本运行 services/asr_api.py (port 5002)
      → scripts/asr_service.sh SSH 反代到 123.56.9.243:15002
      → 生产端 services.speech_to_text 走 Config.ASR_API_URL

异常传播：
  ConnectionError / Timeout / HTTPError / Exception → RuntimeError
  标准前缀确保路由层写出统一的中文提示
      「录音文件识别需依赖本地模型，请联系管理员苏铎」

长音频：
  ≤ ASR_SEGMENT_SECONDS (默认 600s)：直接调 /transcribe
  >  ASR_SEGMENT_SECONDS：生产端先用 ffmpeg -f segment 切片，逐段 ASR，\n 拼接文本

接口返回 dict: {'success': bool, 'text': str, 'duration': float}
"""
import os
import logging
import tempfile
import shutil
import uuid
import glob

import requests

from config import Config

logger = logging.getLogger(__name__)

# 长音频切片长度（production 端与笔记本 asr_api 端共用同一个语义）
SEGMENT_DURATION = Config.ASR_SEGMENT_SECONDS

# ASR 不可达时的中文提示前缀，方便路由层识别并原样透传到 item.audio_summary
_UNREACHABLE_HINT = '录音文件识别需依赖本地模型，请联系管理员苏铎'


def _get_audio_duration(filepath):
    """获取音频时长（秒）。用 ffprobe，失败返回 0.0。"""
    ffprobe = os.environ.get('FFPROBE')
    if not ffprobe:
        # 退路：按 ffmpeg 同目录
        ffprobe = os.environ.get('FFMPEG', 'ffprobe')
        if os.path.isfile(ffprobe):
            ffprobe = os.path.join(os.path.dirname(ffprobe), 'ffprobe')
    cmd = [
        ffprobe, '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', filepath,
    ]
    try:
        import subprocess
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if r.returncode == 0 and r.stdout.strip():
            return float(r.stdout.strip())
    except Exception:
        pass
    return 0.0


def _split_audio_ffmpeg(input_path, output_dir, segment_duration=SEGMENT_DURATION):
    """FFmpeg 按 segment_duration 秒切分长音频到 output_dir，返回绝对路径升序列表。

    失败返回 []；调用方需对返回值判空。

    仅对 .wav 走流复制；对 .mp3/.m4a 等封装格式重编码为 PCM 后再切，
    避免 -c copy 因帧边界不对齐造成解码异常。输出一律为 WAV PCM 16k/mono。
    """
    import subprocess
    ext = (os.path.splitext(input_path)[1] or '.wav').lower()
    prefix = uuid.uuid4().hex[:8]
    out_pat = os.path.join(output_dir, f'_seg_{prefix}_%03d.wav')
    cmd = ['ffmpeg', '-y', '-i', input_path]
    if ext != '.wav':
        cmd += ['-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1']
    cmd += ['-f', 'segment', '-segment_time', str(segment_duration),
            '-reset_timestamps', '1', out_pat]
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                           creationflags=creationflags)
        if r.returncode != 0:
            logger.error(f'切片失败：{r.stderr[-300:] if r.stderr else ""}')
            return []
        segs = sorted(glob.glob(os.path.join(output_dir, f'_seg_{prefix}_*.wav')))
        logger.info(f'切分完成：{len(segs)} 段，每段 {segment_duration}s')
        return segs
    except Exception as e:
        logger.error(f'切片异常：{e}')
        return []


def _post_single(filepath, url, timeout, language='zh'):
    """把单段音频 POST 到 {url}/transcribe，返回 text。

    失败抛 RuntimeError（含 _UNREACHABLE_HINT 作为路由层识别锚点）。
    """
    base_url = url.rstrip('/')
    with open(filepath, 'rb') as fb:
        resp = requests.post(
            f'{base_url}/transcribe',
            files={'file': (os.path.basename(filepath), fb, 'application/octet-stream')},
            data={'language': language},
            timeout=timeout,
        )
    if resp.status_code != 200:
        raise requests.HTTPError(
            f'HTTP {resp.status_code}: {resp.text[:300]}', response=resp
        )
    try:
        r = resp.json()
    except ValueError:
        raise RuntimeError(f'{_UNREACHABLE_HINT}（返回非 JSON：{resp.text[:200]}）')
    if r.get('code', 0) != 0:
        raise RuntimeError(f'{_UNREACHABLE_HINT}（远端 code={r.get("code")} msg={str(r.get("message",""))[:200]}）')
    text = r.get('text', '') or ''
    return text.strip()


def transcribe_audio(audio_file_path, base_url=None):
    """将音频文件转换为文字（纯 HTTP 客户端，不引 funasr-onnx）。

    Args:
        audio_file_path: 音频文件绝对路径
        base_url: ASR 服务基础 URL；None 时取 Config.ASR_API_URL
            （笔记本反代后生产端用 http://localhost:15002）

    Returns:
        dict: {'success': True, 'text': str, 'duration': float}

    Raises:
        RuntimeError: 任何失败场景，消息均含 _UNREACHABLE_HINT
    """
    duration = _get_audio_duration(audio_file_path) or 0.0
    url = (base_url or Config.ASR_API_URL)
    timeout = Config.ASR_API_TIMEOUT

    logger.info(f'ASR 开始：{os.path.basename(audio_file_path)}，{duration:.0f}s，endpoint={url}')

    try:
        if duration <= SEGMENT_DURATION:
            text = _post_single(audio_file_path, url, timeout)
        else:
            logger.info(f'长音频（{duration:.0f}s），切片 {SEGMENT_DURATION}s/段后逐段 ASR')
            tmp = tempfile.mkdtemp(prefix='asr_seg_')
            try:
                segs = _split_audio_ffmpeg(audio_file_path, tmp, SEGMENT_DURATION)
                if not segs:
                    logger.warning('切片失败，回退到整段请求')
                    text = _post_single(audio_file_path, url, timeout)
                else:
                    parts = []
                    for i, seg in enumerate(segs):
                        logger.info(f'ASR 段 [{i + 1}/{len(segs)}]: {os.path.basename(seg)}')
                        parts.append(_post_single(seg, url, timeout))
                    text = '\n'.join(parts)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

        logger.info(f'ASR 完成：{len(text)} 字 / {duration:.0f}s')
        return {'success': True, 'text': text, 'duration': duration}

    except (requests.ConnectionError, requests.Timeout) as e:
        raise RuntimeError(
            f'{_UNREACHABLE_HINT}（ASR 服务 {url} 不可达，{type(e).__name__}）'
        ) from e
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else '?'
        raise RuntimeError(
            f'{_UNREACHABLE_HINT}（ASR 服务返回 HTTP {status}）'
        ) from e
    except RuntimeError:
        # 已包装过的 RuntimeError 直接抛出，避免双层包装
        raise
    except Exception as e:
        raise RuntimeError(
            f'{_UNREACHABLE_HINT}（未知错误：{type(e).__name__}: {str(e)[:200]}）'
        ) from e
