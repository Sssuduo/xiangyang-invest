"""
活动台账 - 录音文件上传 API

流程：
1. 上传：保存原始文件（不压缩）→ 异步 ASR 转写 + LLM 总结
2. 夜间定时：压缩超过 50MB 的大文件为 zip 下载包
3. 失败重试：POST /audio/retry 重新调用识别接口
"""
import os
import threading
from flask import request, jsonify, current_app
from models import ActivityLedger
from extensions import db
from routes import admin_activity_ledger_bp
from routes.business_auth import dual_login_required, visitor_block
from utils.image_upload import AUDIO_EXTENSIONS
from config import Config


def _allowed_audio(filename):
    """检查是否为允许的音频格式"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in AUDIO_EXTENSIONS


def _get_server_base_url():
    """获取服务器公网地址"""
    url = os.environ.get('SERVER_BASE_URL', Config.SERVER_BASE_URL)
    if not url:
        # 回退：用当前请求的 host
        try:
            url = request.host_url.rstrip('/')
        except RuntimeError:
            url = ''
    return url


def _run_async_processing(app, item_id, audio_path):
    """
    后台线程：执行 ASR 转写 + LLM 总结，更新数据库
    """
    import logging
    logger = logging.getLogger(__name__)

    base_url = _get_server_base_url()

    with app.app_context():
        try:
            item = ActivityLedger.query.get(item_id)
            if not item:
                logger.error(f'后台处理：活动台账 {item_id} 不存在')
                return

            # 1. 语音转文字
            from services.speech_to_text import transcribe_audio
            logger.info(f'后台 ASR 开始：item_id={item_id}，文件={audio_path}')
            asr_result = transcribe_audio(audio_path, base_url=base_url)
            item.audio_transcript = asr_result['text']
            db.session.commit()
            logger.info(f'后台 ASR 完成：{len(asr_result["text"])} 字')

            # 2. 内容总结
            if asr_result['text']:
                from services.text_summarizer import summarize_with_llm
                logger.info(f'后台总结开始：item_id={item_id}')
                summary = summarize_with_llm(asr_result['text'])
                item.audio_summary = summary
            else:
                item.audio_summary = '（转写内容为空，无法生成总结）'

            item.audio_status = 'completed'
            db.session.commit()
            logger.info(f'后台处理完成：item_id={item_id}')

        except Exception as e:
            logger.error(f'后台处理失败：item_id={item_id}，错误：{e}', exc_info=True)
            try:
                item = ActivityLedger.query.get(item_id)
                if item:
                    item.audio_status = 'failed'
                    err_msg = str(e)[:500]  # 截断过长错误信息
                    item.audio_summary = f'处理失败：{err_msg}'
                    db.session.commit()
            except Exception:
                pass


def _resolve_audio_path(item):
    """根据 audio_file 字段解析文件绝对路径"""
    file_rel = item.audio_file.lstrip('/')
    upload_folder = Config.UPLOAD_FOLDER
    return os.path.join(os.path.dirname(upload_folder), file_rel)


# ======================== 上传 ========================


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>/audio', methods=['POST'])
@dual_login_required
@visitor_block
def upload_audio(item_id):
    """
    上传录音文件（异步处理）

    上传原始文件直接保存，不压缩。ASR 转写和总结在后台异步执行。

    Form Data:
        file: 录音文件（wav, mp3, m4a, ogg, flac, wma, aac, amr, opus, weba）

    Returns:
        JSON: { code: 0, data: { audio_file, audio_status: 'processing', ... } }
    """
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '请选择录音文件'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'code': 1, 'message': '未选择文件'}), 400

    if not _allowed_audio(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else '未知'
        return jsonify({
            'code': 1,
            'message': f'不支持的音频格式：.{ext}，支持：{", ".join(sorted(AUDIO_EXTENSIONS))}'
        }), 400

    # 1. 暂存临时文件
    import uuid
    upload_dir = Config.UPLOAD_FOLDER
    os.makedirs(upload_dir, exist_ok=True)
    tmp_filename = f'_tmp_audio_{uuid.uuid4().hex[:8]}_{file.filename}'
    tmp_path = os.path.join(upload_dir, tmp_filename)

    try:
        file.save(tmp_path)

        # 2. 直接保存原始文件（不压缩）
        from services.audio_compressor import save_original_audio
        save_result = save_original_audio(tmp_path, upload_dir)
        audio_path_abs = save_result['file_path']

        # 3. 更新数据库状态：processing
        item.audio_file = save_result['relative_url']
        item.audio_archive = None
        item.audio_archive_size = None
        item.audio_status = 'processing'
        item.audio_duration = save_result['duration']
        item.audio_transcript = None
        item.audio_summary = None
        db.session.commit()

        # 4. 启动后台线程：ASR 转写 + 总结
        app = current_app._get_current_object()
        thread = threading.Thread(
            target=_run_async_processing,
            args=(app, item_id, audio_path_abs),
            daemon=True
        )
        thread.start()

        return jsonify({
            'code': 0,
            'message': '录音已上传，正在后台处理...',
            'data': {
                'audio_file': save_result['relative_url'],
                'audio_status': 'processing',
                'audio_duration': save_result['duration'],
                'file_size': save_result['file_size'],
            }
        })

    except Exception as e:
        item.audio_status = 'failed'
        item.audio_summary = f'上传失败：{str(e)}'
        db.session.commit()
        return jsonify({'code': 1, 'message': f'录音处理失败：{str(e)}'}), 500

    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# ======================== 查询 ========================


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>/audio', methods=['GET'])
@dual_login_required
def get_audio_detail(item_id):
    """
    获取录音处理状态及详情

    Returns:
        JSON: { code: 0, data: { audio_file, audio_archive, audio_archive_size,
                audio_transcript, audio_summary, audio_status, audio_duration, file_size } }
    """
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    data = {
        'audio_file': item.audio_file,
        'audio_archive': item.audio_archive,
        'audio_archive_size': item.audio_archive_size,
        'audio_transcript': item.audio_transcript,
        'audio_summary': item.audio_summary,
        'audio_status': item.audio_status,
        'audio_duration': item.audio_duration,
    }

    # 获取原始文件大小
    if item.audio_file:
        try:
            file_abs = _resolve_audio_path(item)
            if os.path.exists(file_abs):
                data['file_size'] = os.path.getsize(file_abs)
        except Exception:
            pass

    return jsonify({'code': 0, 'data': data})


# ======================== 重新识别 ========================


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>/audio/retry', methods=['POST'])
@dual_login_required
@visitor_block
def retry_audio_recognition(item_id):
    """
    重新调用语音识别接口（当识别失败时手动触发）

    Returns:
        JSON: { code: 0, message: '...' }
    """
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    if not item.audio_file:
        return jsonify({'code': 1, 'message': '没有录音文件，无法重新识别'}), 400

    audio_path = _resolve_audio_path(item)
    if not os.path.exists(audio_path):
        return jsonify({'code': 1, 'message': '录音文件不存在，请重新上传'}), 400

    # 重置状态
    item.audio_status = 'processing'
    item.audio_transcript = None
    item.audio_summary = None
    db.session.commit()

    # 启动后台处理
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_run_async_processing,
        args=(app, item_id, audio_path),
        daemon=True
    )
    thread.start()

    return jsonify({
        'code': 0,
        'message': '已重新开始语音识别，请等待处理完成...',
        'data': {'audio_status': 'processing'}
    })


# ======================== 编辑 ========================


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>/audio/transcript', methods=['PUT'])
@dual_login_required
@visitor_block
def update_audio_transcript(item_id):
    """
    手动编辑/更新转写文本或总结

    JSON Body:
        transcript: str   # （可选）新的转写文本
        summary: str       # （可选）新的总结文本

    Returns:
        JSON: { code: 0, message: '...' }
    """
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    if not item.audio_file:
        return jsonify({'code': 1, 'message': '该台账没有录音文件'}), 400

    data = request.get_json(silent=True) or {}
    transcript = data.get('transcript')
    summary = data.get('summary')

    updated = False
    if transcript is not None:
        item.audio_transcript = transcript
        updated = True
    if summary is not None:
        item.audio_summary = summary
        updated = True

    if not updated:
        return jsonify({'code': 1, 'message': '未提供需要更新的内容'}), 400

    db.session.commit()
    return jsonify({'code': 0, 'message': '转写内容已更新'})


# ======================== 删除 ========================


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>/audio', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_audio(item_id):
    """删除录音文件、压缩包及转写/总结数据"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    if not item.audio_file:
        return jsonify({'code': 1, 'message': '该台账没有录音文件'}), 400

    # 删除原始文件
    try:
        file_abs = _resolve_audio_path(item)
        if os.path.exists(file_abs):
            os.remove(file_abs)
    except OSError:
        pass

    # 删除压缩包
    if item.audio_archive:
        try:
            archive_rel = item.audio_archive.lstrip('/')
            archive_abs = os.path.join(os.path.dirname(Config.UPLOAD_FOLDER), archive_rel)
            if os.path.exists(archive_abs):
                os.remove(archive_abs)
        except OSError:
            pass

    # 清除数据库字段
    item.audio_file = None
    item.audio_archive = None
    item.audio_archive_size = None
    item.audio_transcript = None
    item.audio_summary = None
    item.audio_status = None
    item.audio_duration = None
    db.session.commit()

    return jsonify({'code': 0, 'message': '录音文件及数据已删除'})


# ======================== 夜间压缩（管理员手动触发或定时任务调用） ========================


@admin_activity_ledger_bp.route('/admin/audio/compress-night', methods=['POST'])
@dual_login_required
@visitor_block
def compress_night():
    """
    手动触发的夜间压缩任务

    扫描所有超过 50MB 的原始录音文件，压缩为 Opus 并打包 zip。
    压缩后的 zip 文件不支持在线播放，仅可下载解压。

    Returns:
        JSON: { code: 0, data: { processed, compressed, skipped, errors } }
    """
    from services.audio_compressor import run_night_compression

    try:
        result = run_night_compression(threshold_bytes=Config.AUDIO_ARCHIVE_THRESHOLD)
        return jsonify({
            'code': 0,
            'message': f'压缩完成：处理 {result["processed"]} 个，'
                       f'压缩 {result["compressed"]} 个，'
                       f'跳过 {result["skipped"]} 个，'
                       f'错误 {result["errors"]} 个',
            'data': result
        })
    except Exception as e:
        return jsonify({'code': 1, 'message': f'压缩任务失败：{str(e)}'}), 500
