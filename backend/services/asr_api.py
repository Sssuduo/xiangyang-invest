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

Input strategy:
    任意封装 (mp3/m4a/flac/opus/amr) 全部通过 ffmpeg 链路解码；
    长音频 (> split_sec) 切片 → 逐段推理 → \n 拼接文本。
    切片阶段统一走【PCM WAV 重编码 + segment 切片】（秒级），
    一次性把 mp3 变成 PCM WAV，避免之后 funasr-onnx 直接吃 mp3 触发
    soundfile/libsndfile 某些大体积/VBR mp3 报 unspecified internal error
    和 mpg123 sync lost。
    HTTP 服务用 waitress WSGI（非 werkzeug ev），
    配合 multiprocessing.Pool 真正让推理在独立子进程跑，不会被 HTTP 线程阻塞。
"""
import os
import sys
import json
import tempfile
import uuid
import shutil
import argparse
import subprocess
import glob
import logging
import multiprocessing
import time
import threading

import requests as http_requests
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# FunASR 模型（懒加载）
_model_lock = threading.Lock()
_model = None
_model_dir = os.environ.get('SENSEVOICE_MODEL_DIR',
                            r'C:\temp_sensevoice\models\iic\SenseVoiceSmall')

# FFmpeg 路径 (笔记本端有 FunASR 环境)
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
# 实验证据：funasr-onnx 在单段 ≤30 秒时可完整识别 (~90 字/段)；
#           单段 ≥60 秒后模型输出随时长急剧劣化 (300s 段只出 10 字乱码)。
#           此常数与 SenseVoice 训练时每句 30s 的窗口对齐。
DEFAULT_SPLIT_SEC = int(os.environ.get('ASR_SPLIT_SEC', '30'))  # 默认 30 秒段，与训练窗口对齐
INFER_WORKERS = int(os.environ.get('ASR_INFER_WORKERS', '2'))    # 推理并发的 worker 数 (受限于 CPU/内存)

# 中文路径安全
os.environ.setdefault('TMPDIR', r'C:\temp_sensevoice')
os.environ.setdefault('TEMP', r'C:\temp_sensevoice')
os.environ.setdefault('TMP', r'C:\temp_sensevoice')


def get_model():
    """懒加载 SenseVoiceSmall ONNX 模型（笔记本端有 GPU/大内存）。

    device_id 透传给 funasr_onnx：
      - 默认 '-1' 走 CPU（兼容现状）；
      - 设为 '0' 等 GPU id 时，funasr_onnx 内部在 CUDAExecutionProvider
        可用时自动用 GPU，否则回退 CPU 并打印 RuntimeWarning。
    由环境变量 ASR_DEVICE_ID 控制，部署 GPU 时置 '0'。
    """
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from funasr_onnx import SenseVoiceSmall
                device_id = os.environ.get('ASR_DEVICE_ID', '-1')
                _model = SenseVoiceSmall(_model_dir, batch_size=1, quantize=False, device_id=device_id)
                logger.info('SenseVoiceSmall ONNX 模型已加载 device_id=%s', device_id)
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
    """把任意音频重编码为 PCM WAV 16-bit mono @ sr."""
    cmd = [FFMPEG, '-y', '-i', input_path,
           '-acodec', 'pcm_s16le', '-ac', '1', '-ar', str(sr),
           '-vn', '-map_metadata', '-1', output_path]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=1200,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    except FileNotFoundError:
        raise RuntimeError('需要 ffmpeg 才能转 PCM')
    if r.returncode != 0 or not os.path.exists(output_path):
        raise RuntimeError(f'ffmpeg PCM 转写失败: {r.stderr[-300:] if r.stderr else "rc=%d" % r.returncode}')


def _split_stream(input_path, output_dir, seg_sec):
    """按 seg_sec 秒切片 PCM WAV；流复制 + 1k 秒以内的 PCM 边界稳定。

    已假定 input_path 是 PCM 16k/mono —— 之前的 _to_pcm_wav 已处理。
    """
    prefix = uuid.uuid4().hex[:8]
    out_pat = os.path.join(output_dir, f'_seg_{prefix}_%03d.wav')
    cmd = [FFMPEG, '-y', '-i', input_path,
           '-f', 'segment', '-segment_time', str(seg_sec),
           '-c', 'copy', '-reset_timestamps', '1',
           out_pat]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if r.returncode != 0:
            logger.error(f'切片失败：{r.stderr[-300:] if r.stderr else ""}')
            return []
        segs = sorted(glob.glob(os.path.join(output_dir, f'_seg_{prefix}_*.wav')))
        logger.info(f'切片完成：{len(segs)} 段')
        return segs
    except Exception as e:
        logger.error(f'切片异常：{e}')
        return []


# 推理进程池（全局，单进程 worker 模式时启动）
_infer_pool = None
_infer_pool_lock = threading.Lock()


def _get_pool():
    """获取/创建 funasr-onnx 推理进程池。

    注意：每个子进程都会单独懒加载 ONNX 模型，因此 INFER_WORKERS>1 会多占内存
    （SenseVoiceSmall 单个进程 ~500MB-1GB）。INFER_WORKERS=1 是保底稳定。
    """
    global _infer_pool
    if _infer_pool is None:
        with _infer_pool_lock:
            if _infer_pool is None:
                # 用 fork 省的进程复制模型不保险；直接用 spawn + 让子进程自己懒加载
                _infer_pool = multiprocessing.Pool(processes=INFER_WORKERS)
                logger.info(f'启动推理进程池，worker 数={INFER_WORKERS}')
    return _infer_pool


def _infer_in_subproc(args_tuple):
    """子进程执行的推理函数 — 模型会在子进程内独立懒加载。

    参数打包成 tuple 因为 Pool.map 要求可序列化参数。
    (filepath, language) -> text

    重要防御：对调用整体 try/except。因为 funasr-onnx 在某些段（
    常见的如静音段 + VAD 判定静音 → 前端 lfr_cmvn 空矩阵 → apply_lfr 内部
    IndexError "index 0 is out of bounds for axis 0 with size 0") 里会崩溃，
    而本防御把这段变成空字符串，不冒泡成 HTTP 500。
    """
    # 子进程里重新配 logger（spawn 子进程不继承父进程 logging 配置）
    import logging as _logging
    _sub_logger = _logging.getLogger('asr_subproc')
    if not _sub_logger.handlers:
        _h = _logging.StreamHandler()
        _h.setFormatter(_logging.Formatter('%(asctime)s %(levelname)s [subproc %(process)d] %(message)s'))
        _sub_logger.addHandler(_h)
        _sub_logger.setLevel(_logging.INFO)

    filepath, language = args_tuple
    try:
        _sub_logger.info(f'子进程推理开始：{os.path.basename(filepath)}')
        from funasr_onnx.utils.postprocess_utils import rich_transcription_postprocess
        _sub_logger.info('  importing model...')
        model = get_model()
        _sub_logger.info('  model loaded, calling model([filepath])...')
        res = model([filepath], language=language, use_itn=True)
        # 防御：某些段 funasr-onnx 返回空数组 (例如静音段 + VAD 全裁)，不索引 res[0]
        if not (res and len(res) > 0):
            _sub_logger.warning(f'推理返回空数组(段静音？)：{os.path.basename(filepath)}')
            return ''
        text = rich_transcription_postprocess(res[0])
        _sub_logger.info(f'子进程推理完成：{os.path.basename(filepath)}，{len(text)}字')
        return text
    except Exception as e:
        # 防御性兜底：funasr-onnx 模型内部报错不能冒泡成 HTTP 500——把该段变成空串，
        # 让调用方（transcribe_file）依然能拿到形如 "...\n\n..." 的拼接结果，
        # 不该段静音不会摧毁整段多文件转写结果。
        _sub_logger.error(f'子进程推理异常，已吞掉返回空串：{os.path.basename(filepath)}，{type(e).__name__}: {str(e)[:500]}')
        import traceback
        _sub_logger.error('traceback:')
        for line in traceback.format_exc().splitlines():
            _sub_logger.error('  ' + line)
        return ''


def transcribe_file(filepath, language='zh', split_sec=DEFAULT_SPLIT_SEC):
    """核心转写。

    链路: 输入 → PCM  (仅非 WAV 封装格式) → 切片 → 进程池并发推理 → \n 拼接文本。
    HTTP 线程不被阻塞。

    关键设计：
      - 非 WAV 封装 (mp3/m4a/opus/amr/flac) 在入口强制做 PCM WAV 重编码，
        把"mp3 帧边界/采样格式不对齐"这个导致 funasr-onnx 在某些段
        抛 IndexError / 返回空数组 的问题消灭。
      - 已经是 WAV 的输入 (16k/mono/16bit PCM) _不再_ 强制重编码：
        对长段 WAV 做二次 PCM 重编码已经被证实会严重破坏模型推理结果
        (60 段能出 271 字的输入，600s PCM 重编码后只出 7 字)；
        静音/空数组防御已全部下沉到 _infer_in_subproc 的 try/except 里，
        因此可以放心直接给 funasr 消费。
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f'音频文件不存在：{filepath}')

    work_path = filepath
    tmp_pcm = None
    # 仅对非 PCM 封装格式做一次重编码；WAV 输入直接走模型
    ext = (os.path.splitext(filepath)[1] or '').lower()
    if ext != '.wav':
        tmp_pcm = tempfile.mkstemp(suffix='.wav', prefix='asr_pcm_')[1]
        _to_pcm_wav(filepath, tmp_pcm)
        work_path = tmp_pcm

    try:
        duration = _ffprobe_duration(work_path)
        logger.info(f'transcribe_file：{os.path.basename(work_path)}，{duration:.0f}s，split_sec={split_sec}，workers={INFER_WORKERS}')

        if duration <= split_sec:
            # 单段: 扔进进程池 — 加 600s 超时保护
            pool = _get_pool()
            job = pool.apply_async(_infer_in_subproc, ((work_path, language),))
            text = job.get(timeout=600)
            return text

        # 长音频: 切片后并发推理
        temp_dir = tempfile.mkdtemp(prefix='asr_long_')
        try:
            segs = _split_stream(work_path, temp_dir, split_sec)
            if not segs:
                pool = _get_pool()
                job = pool.apply_async(_infer_in_subproc, ((work_path, language),))
                return job.get(timeout=600)

            pool = _get_pool()
            tasks = [(seg, language) for seg in segs]
            job_async = pool.map_async(_infer_in_subproc, tasks)
            # 每 300s 段模型推理约 60-120s，留足 600s 超时
            parts = job_async.get(timeout=600)
            return '\n'.join(parts)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    finally:
        if tmp_pcm:
            try:
                os.remove(tmp_pcm)
            except OSError:
                pass


@app.route('/info', methods=['GET'])
def info():
    """模型信息（便于监控）"""
    return jsonify({'status': 'ok', 'model': 'SenseVoiceSmall-ONNX',
                    'split_sec_default': DEFAULT_SPLIT_SEC,
                    'infer_workers': INFER_WORKERS})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'model': 'SenseVoiceSmall-ONNX'})


@app.route('/transcribe', methods=['GET'], endpoint='transcribe_get')
def transcribe_get():
    """调试：从 URL 下载然后转写。"""
    url = request.args.get('url')
    if not url:
        return jsonify({'code': 1, 'message': 'url 参数必填'}), 400
    language = request.args.get('language', 'zh')
    try:
        split_sec = int(request.args.get('split_sec', str(DEFAULT_SPLIT_SEC)))
    except ValueError:
        split_sec = DEFAULT_SPLIT_SEC

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


def _run_with_waitress(port):
    """用 waitress WSGI 多线程服务（HTTP 调度在独立线程，推理在进程池）。"""
    try:
        from waitress import serve as waitress_serve
    except ImportError:
        logger.error('waitress 未安装; 请执行: pip install waitress')
        raise SystemExit(2)
    logger.info(f'Starting waitress WSGI on 0.0.0.0:{port} — threads=8')
    waitress_serve(app, host='0.0.0.0', port=port, threads=8)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5002)
    parser.add_argument('--wsgi', choices=['waitress', 'flask', 'gunicorn'], default='waitress')
    args = parser.parse_args()

    if args.wsgi == 'waitress':
        _run_with_waitress(args.port)
    elif args.wsgi == 'gunicorn':
        logger.info(f'Starting gunicorn WSGI on 0.0.0.0:{args.port} --workers 1 --threads 8')
        from gunicorn.app.wsgiapp import WSGIApplication
        sys.argv = ['gunicorn', 'services.asr_api:app',
                    f'--bind=0.0.0.0:{args.port}', '--workers=1', '--threads=8', '--timeout=1800']
        WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]", prog='gunicorn').run()
    else:
        app.run(host='0.0.0.0', port=args.port, debug=False, threaded=True)
