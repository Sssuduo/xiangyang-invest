"""
SenseVoice ASR HTTP API 服务（笔记本端运行）。

启动方式：python asr_api.py --port 5002
部署链路：
    生产服务器 123.56.9.243:15002
        → scripts/asr_service.sh SSH 反代
        → 笔记本 localhost:5002 本服务

端点：
    GET  /health        健康检查
    GET  /info          模型信息（便于监控）
    GET  /transcribe?url=...&split_sec=600  调试：按 URL 取音频并转写
    POST /transcribe    form-data: {file, language=zh, split_sec=600}

输入策略：
    任意封装（mp3 / m4a / flac / opus / amr / ogg）一路 ffmpeg 解析；
    长音频（> split_sec）切片 → 逐段推理 → \\n 拼接文本。
    切片阶段用『-f segment + 流复制』秒级完成，整体时间 ≈ 纯 FunASR 推理时间。
    若 funasr-onnx 内部解码报非法头/unspecified internal error，降级为: 整段 PCM WAV 重编码 + 推理。
"""
import os
import json
import tempfile
import uuid
import shutil
import argparse
import subprocess
import glob
import logging

import requests as http_requests
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 模型（懒加载）
_model = None
_model_dir = os.environ.get('SENSEVOICE_MODEL_DIR',
                            r'C:\temp_sensevoice\models\iic\SenseVoiceSmall')

# FFmpeg 路径（笔记本端有 FunASR 环境）
_FFMPEG_CANDIDATES = [
    os.environ.get('FFMPEG', ''),
    os.environ.get('FFPROBE', ''),
    r'C:\Users\苏铎\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe',
    r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
    'ffmpeg',
]
_FFPROBE_CANDIDATES = [
    os.environ.get('FFPROBE', ''),
    r'C:\Users\苏铎\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffprobe.exe',
    r'C:\Program Files\ffmpeg\bin\ffprobe.exe',
    'ffprobe',
]


def _find_exe(candidates):
    """从可执行文件候选列表中找第一个可调用者"""
    for c in candidates:
        if not c:
            continue
        if os.path.isabs(c):
            if os.path.isfile(c):
                return c
        else:
            import shutil as _shutil
            found = _shutil.which(c)
            if found:
                return found
    return candidates[-1]


FFMPEG = _find_exe(_FFMPEG_CANDIDATES)
FFPROBE = _find_exe(_FFPROBE_CANDIDATES)

# 默认长音频切片长度（秒）；可在请求中覆盖
DEFAULT_SPLIT_SEC = int(os.environ.get('ASR_SPLIT_SEC', '600'))

# 中文路径安全
os.environ.setdefault('TMPDIR', r'C:\temp_sensevoice')
os.environ.setdefault('TEMP', r'C:\temp_sensevoice')
os.environ.setdefault('TMP', r'C:\temp_sensevoice')


def get_model():
    """懒加载 SenseVoiceSmall ONNX 模型（笔记本端有 GPU/大内存）"""
    global _model
    if _model is None:
        from funasr_onnx import SenseVoiceSmall
        _model = SenseVoiceSmall(_model_dir, batch_size=1, quantize=False)
        logger.info('SenseVoiceSmall ONNX 模型已加载')
    return _model


def _ffprobe_duration(filepath):
    """取音频时长，错误返回 0.0"""
    try:
        r = subprocess.run(
            [FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if r.returncode == 0 and r.stdout.strip():
            return float(r.stdout.strip())
    except Exception:
        pass
    return 0.0


def _to_pcm_wav(input_path, output_path, sr=16000):
    """把任意音频重编码为 PCM WAV 16-bit mono @ sr。

    用于 funasr-onnx 无法直接解码原 mp3 时的降级链路。
    代价高（秒到分钟级），仅在必要时调用。失败抛 RuntimeError。
    """
    cmd = [FFMPEG, '-y', '-i', input_path,
           '-acodec', 'pcm_s16le', '-ac', '1', '-ar', str(sr),
           '-vn', '-map_metadata', '-1',
           output_path]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    except FileNotFoundError:
        raise RuntimeError('需要 ffmpeg 才能转 PCM')
    if r.returncode != 0 or not os.path.exists(output_path):
        raise RuntimeError(f'ffmpeg PCM 转写失败: {r.stderr[-300:] if r.stderr else "rc=%d" % r.returncode}')


def _split_stream(input_path, output_dir, seg_sec):
    """按 seg_sec 秒切片 PCM WAV，输出流复制 wav。

    若输入本身是 wav PCM，使用 keycopy + 分段同时切到 16k 16-bit mono；
    否则先 reencode 一次再切片（仅 mp3 走此分支），确保每段都能正确解码。
    """
    prefix = uuid.uuid4().hex[:8]
    out_pat = os.path.join(output_dir, f'_seg_{prefix}_%03d.wav')
    cmd = [FFMPEG, '-y', '-i', input_path]
    # 强制转 PCM 16k mono 解码成 PCM 后分段 - segmentation 在 PCM 上无关键帧限制
    cmd += ['-acodec', 'pcm_s16le', '-ac', '1', '-ar', '16000']
    cmd += ['-f', 'segment', '-segment_time', str(seg_sec),
            '-reset_timestamps', '1', '-map', '0',
            out_pat]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if r.returncode != 0:
            logger.error(f'流复制切片失败：{r.stderr[-300:] if r.stderr else ""}')
            return []
        segs = sorted(glob.glob(os.path.join(output_dir, f'_seg_{prefix}_*.wav')))
        logger.info(f'切片完成：{len(segs)} 段')
        return segs
    except Exception as e:
        logger.error(f'切片异常：{e}')
        return []


def _infer_single(filepath, language='zh'):
    """单段推理：直接喂 funasr-onnx，内部解码会做 VAD。"""
    from funasr_onnx.utils.postprocess_utils import rich_transcription_postprocess
    model = get_model()
    res = model([filepath], language=language, use_itn=True)
    return rich_transcription_postprocess(res[0]) if (res and len(res) > 0) else ''


def transcribe_file(filepath, language='zh', split_sec=DEFAULT_SPLIT_SEC):
    """核心转写。

    优先路径：流复制切片 → 逐段 FunASR 推理 → \\n 拼接。
    任意 RuntimeError（主要是 funasr 解码异常）触发降级路径：
    整段 PCM WAV → 重新切片 → 推理。
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f'音频文件不存在：{filepath}')

    duration = _ffprobe_duration(filepath)
    logger.info(f'transcribe_file：{os.path.basename(filepath)}，{duration:.0f}s，split_sec={split_sec}')

    def _pipeline(src):
        """流复制切 + 推理；解码异常会抛 RuntimeError"""
        if duration <= split_sec:
            return _infer_single(src, language)
        temp_dir = tempfile.mkdtemp(prefix='asr_long_')
        try:
            segs = _split_stream(src, temp_dir, split_sec)
            if not segs:
                return _infer_single(src, language)  # 切不掉赌整段
            parts = []
            for i, seg in enumerate(segs):
                logger.info(f'推理段 [{i + 1}/{len(segs)}]：{os.path.basename(seg)}')
                try:
                    parts.append(_infer_single(seg, language))
                except Exception as e:
                    logger.error(f'推理段 [{i + 1}/{len(segs)}] 失败：{e}')
                    parts.append(f'[第{i + 1}段识别失败]')
            return '\n'.join(parts)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    try:
        return _pipeline(filepath)
    except Exception as primary_err:
        # 降级：把原文件一次性重编码为 PCM 后再走一次
        logger.warning(f'主路径失败({type(primary_err).__name__}: {str(primary_err)[:250]})，降级 PCM 重编码')
        pcm_path = tempfile.mkstemp(suffix='.wav', prefix='asr_pcm_fallback_')[1]
        try:
            _to_pcm_wav(filepath, pcm_path)
            return _pipeline(pcm_path)
        finally:
            try:
                os.remove(pcm_path)
            except OSError:
                pass


@app.route('/info', methods=['GET'])
def info():
    """模型信息（便于监控）"""
    return jsonify({'status': 'ok', 'model': 'SenseVoiceSmall-ONNX',
                    'split_sec_default': DEFAULT_SPLIT_SEC})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'model': 'SenseVoiceSmall-ONNX'})


@app.route('/transcribe', methods=['GET'], endpoint='transcribe_get')
def transcribe_get():
    """调试端点：通过 url 参数取音频再转写。

    GET /transcribe?url=...&language=zh&split_sec=600
    """
    url = request.args.get('url')
    if not url:
        return jsonify({'code': 1, 'message': 'url 参数必填'}), 400
    language = request.args.get('language', 'zh')
    try:
        split_sec = int(request.args.get('split_sec', str(DEFAULT_SPLIT_SEC)))
    except ValueError:
        split_sec = DEFAULT_SPLIT_SEC

    # 下载到临时文件
    tmpdir = tempfile.mkdtemp(prefix='asr_get_')
    try:
        ext = os.path.splitext(url.split('?')[0])[1] or '.wav'
        tmpfile = os.path.join(tmpdir, f'input{ext}')
        with http_requests.get(url, timeout=120) as r, open(tmpfile, 'wb') as f:
            if r.status_code != 200:
                return jsonify({'code': 1, 'message': f'HTTP {r.status_code} 拉取音频失败'}), 500
            for chunk in r.iter_content(65536):
                f.write(chunk)
        text = transcribe_file(tmpfile, language, split_sec)
        return jsonify({'code': 0, 'text': text})
    except Exception as e:
        logger.exception('GET /transcribe 失败')
        return jsonify({'code': 1, 'message': str(e)}), 500
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@app.route('/transcribe', methods=['POST'])
def transcribe_post():
    """接受音频文件（form-data: file, language, split_sec），返回转写文本。"""
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '请上传音频文件'}), 400

    f = request.files['file']
    language = request.form.get('language', 'zh')
    try:
        split_sec = int(request.form.get('split_sec', str(DEFAULT_SPLIT_SEC)))
    except ValueError:
        split_sec = DEFAULT_SPLIT_SEC

    tmpdir = tempfile.mkdtemp(prefix='asr_api_')
    try:
        ext = os.path.splitext(f.filename or 'audio.wav')[1] or '.wav'
        tmpfile = os.path.join(tmpdir, f'input{ext}')
        f.save(tmpfile)

        text = transcribe_file(tmpfile, language, split_sec)
        return jsonify({'code': 0, 'text': text})
    except Exception as e:
        logger.exception('POST /transcribe 失败')
        return jsonify({'code': 1, 'message': str(e)}), 500
    finally:
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5002)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--threaded', action='store_true', default=True, help='启用多线程（大文件上传必须）')
    args = parser.parse_args()
    logger.info(f'Starting SenseVoice ASR API on {args.host}:{args.port} threaded={args.threaded}')
    app.run(host=args.host, port=args.port, debug=False, threaded=args.threaded)
