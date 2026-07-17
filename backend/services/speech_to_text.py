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

长音频策略：
  生产端把长音频按 SEGMENT_DURATION=300 秒切成 WAV 段，逐段发到笔记本。

  关键约束（已观测到的 bug，必须严格遵守）：
    1. 笔记本端 PCM 重编码 + 按 300s 内部分割 + 2 worker 并发 三件套叠加
       会让 909s 文件的输出从参考值 1044 字降到 52 字（乱码）。
    2. 因此生产端预切后传给笔记本的是单段 WAV（每段≤300s），
       _post_single 调用 /transcribe 时只传 language 不传 split_sec，
       避免笔记本触发“内部分割 + 并行推理”。笔记本收到短 WAV 后
       走 pool.apply 直接单段推理，不进入"内部分割+并发"分支。
    3. 生产端仍对每段做 PCM 重编码（wav→wav 不重，但 mp3→wav），
       让笔记本收到的是标准 16k/mono/16bit PCM WAV。

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

# 生产端预切长度（秒）。对齐 funasr-onnx 训练窗口 (≤30s)：
# 实验证据：30s 段识别 90 字/段 (清晰可读)；≥60s 段模型崩溃；300s 段只出 10 字乱码。
# 把切分决策权交给笔记本 (asr_api 同样用 30s 内部分割)，生产端仅做"预整理"，
# _post_single 不传 split_sec (笔记本单段推理)。
SEGMENT_DURATION = 30

# ASR 不可达时的中文提示前缀，方便路由层识别并原样透传到 item.audio_summary
_UNREACHABLE_HINT = '录音转写服务未启动，请联系管理员苏铎'


def check_asr_health(base_url=None):
    """检查 ASR 服务是否可用。

    Returns:
        bool: True 表示可用，False 表示不可用
    """
    url = (base_url or Config.ASR_API_URL).rstrip('/')
    try:
        resp = requests.get(f'{url}/health', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'ok':
                return True
        return False
    except Exception:
        return False


def _get_audio_duration(filepath):
    """获取音频时长（秒）。用 ffprobe，失败返回 0.0。"""
    import subprocess
    # 与 audio_compressor 一致的 ffprobe 候选逻辑
    FFPROBE_CANDIDATES = [
        os.environ.get('FFPROBE', ''),
        r'C:\Program Files\ffmpeg\bin\ffprobe.exe',
        'ffprobe',
    ]
    ffprobe = None
    for c in FFPROBE_CANDIDATES:
        if not c:
            continue
        if os.path.isabs(c):
            if os.path.isfile(c):
                ffprobe = c
                break
        else:
            import shutil as _shutil
            found = _shutil.which(c)
            if found:
                ffprobe = found
                break
    if not ffprobe:
        ffprobe = 'ffprobe'
    cmd = [
        ffprobe, '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', filepath,
    ]
    try:
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

    对任意输入都先 PCM 重编码为 16k/mono/16bit WAV，再 -f segment 切割，
    保证笔记本收到的是标准 PCM WAV（不再触发它的 PCM 重编码）。
    """
    import subprocess
    prefix = uuid.uuid4().hex[:8]
    out_pat = os.path.join(output_dir, f'_seg_{prefix}_%03d.wav')
    cmd = ['ffmpeg', '-y', '-i', input_path,
           '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
           '-f', 'segment', '-segment_time', str(segment_duration),
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
    """把单段 WAV 音频 POST 到 {url}/transcribe，返回 text。

    不传 split_sec：笔记本收到 ≤300s WAV 后直接进入单段推理分支
    (pool.apply 推理单段)，不会触发“内部分割 + 并行推理”的重编码 bug。

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
            logger.info(f'长音频（{duration:.0f}s），按 {SEGMENT_DURATION}s/段预切后逐段 ASR')
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
