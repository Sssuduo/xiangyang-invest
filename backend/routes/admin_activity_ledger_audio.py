"""
活动台账 - 录音路由层（薄包装）
所有核心逻辑已迁移至 services/audio_service.py（共享 service 层）
此文件仅保留路由装饰器与模型绑定。
"""
import os
import json
import logging
import threading
from flask import request, jsonify, send_from_directory, current_app
from models import ActivityLedger
from extensions import db
from routes import admin_activity_ledger_audio_bp
from routes.business_auth import dual_login_required, visitor_block
from utils.image_upload import AUDIO_EXTENSIONS
from config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 注册活动台账的音频字段名映射
# ---------------------------------------------------------------------------
from services.audio_service import register_audio_model

_LEDGER_AUDIO_FIELDS = {
    "files": "audio_files",
    "status": "audio_status",
    "message": "progress_message",
    "pct": "progress_pct",
    "duration": "audio_duration",
    "transcript": "audio_transcript",
    "summary": "audio_summary",
    "segmented": "audio_transcript_segmented",
    "clean": "audio_transcript_clean",
    "structured": "audio_summary_structured",
    "docx_path": "audio_docx_path",
    "docx_size": "audio_docx_size",
    "archive": "audio_archive",
    "archive_size": "audio_archive_size",
    "model_id": "summary_model_id",
}

register_audio_model(ActivityLedger, _LEDGER_AUDIO_FIELDS)


def _allowed_audio(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in AUDIO_EXTENSIONS


# ---------------------------------------------------------------------------
# 上传
# ---------------------------------------------------------------------------

@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio', methods=['POST'])
@dual_login_required
@visitor_block
def upload_audio(item_id):
    """上传录音文件（支持多文件）"""
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

    import uuid
    upload_dir = Config.UPLOAD_FOLDER
    os.makedirs(upload_dir, exist_ok=True)
    tmp_filename = f'_tmp_audio_{uuid.uuid4().hex[:8]}_{file.filename}'
    tmp_path = os.path.join(upload_dir, tmp_filename)

    try:
        file.save(tmp_path)
        from services.audio_compressor import save_original_audio
        save_result = save_original_audio(tmp_path, upload_dir)

        from services.audio_service import get_audio_files, set_audio_files

        new_file_entry = {
            'url': save_result['relative_url'],
            'name': file.filename,
            'duration': save_result['duration'],
            'size': save_result['file_size'],
            'status': 'pending',
            'error': ''
        }

        append_mode = request.form.get('append', 'false') == 'true'
        existing = get_audio_files(item) if append_mode else []
        existing.append(new_file_entry)
        set_audio_files(item, existing)

        total_duration = sum(f.get('duration', 0) for f in existing)

        item.audio_archive = None
        item.audio_archive_size = None
        item.audio_status = 'uploaded'
        item.audio_duration = total_duration
        item.audio_transcript = None
        item.audio_summary = None
        db.session.commit()

        return jsonify({
            'code': 0, 'message': '录音已上传',
            'data': {'audio_files': existing, 'audio_status': 'uploaded', 'audio_duration': total_duration}
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


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------

@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio', methods=['GET'])
@dual_login_required
def get_audio_detail(item_id):
    """获取录音处理状态及详情"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    from services.audio_service import get_audio_files, estimate_time

    files = get_audio_files(item)
    data = {
        'audio_files': files,
        'audio_file': files[0]['url'] if files else None,
        'audio_archive': item.audio_archive,
        'audio_archive_size': item.audio_archive_size,
        'audio_transcript': item.audio_transcript,
        'audio_summary': item.audio_summary,
        'audio_status': item.audio_status,
        'audio_duration': item.audio_duration,
        'audio_transcript_segmented': item.audio_transcript_segmented,
        'audio_transcript_clean': item.audio_transcript_clean,
        'audio_summary_structured': item.audio_summary_structured,
        'audio_docx_path': item.audio_docx_path,
        'audio_docx_size': item.audio_docx_size,
        'summary_model_id': item.summary_model_id,
        'estimated_summary_seconds': estimate_time(item.audio_duration, len(item.audio_transcript or '')),
        'progress_message': item.progress_message,
        'progress_pct': item.progress_pct,
    }

    return jsonify({'code': 0, 'data': data})


# ---------------------------------------------------------------------------
# 重新识别 / 重新总结
# ---------------------------------------------------------------------------

@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/retry', methods=['POST'])
@dual_login_required
@visitor_block
def retry_audio_recognition(item_id):
    """重新调用语音识别"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    from services.audio_service import get_audio_files

    files = get_audio_files(item)
    if not files:
        return jsonify({'code': 1, 'message': '没有录音文件，无法重新识别'}), 400

    if item.audio_status in ('asr_processing', 'summarizing'):
        return jsonify({'code': 1, 'message': '正在处理中，请等待完成后重试'}), 409

    # 预检 ASR 服务是否可达：避免“已开始识别”后又静默失败，
    # 也规避“识别失败且无切片进度”的困惑（服务不可达时会瞬间失败、不产生任何切片）。
    from services.speech_to_text import check_asr_health
    if not check_asr_health():
        return jsonify({
            'code': 1,
            'message': '录音转写服务未连接，请联系管理员苏铎确认其笔记本已联网并启动转写服务（asr_service.sh）'
        }), 409

    item.audio_status = 'asr_processing'
    item.progress_message = '转写准备中...'
    item.progress_pct = 0
    db.session.commit()

    app = current_app._get_current_object()
    from services.audio_service import run_async_processing
    threading.Thread(target=run_async_processing, args=(app, ActivityLedger, item_id), daemon=True).start()

    return jsonify({
        'code': 0, 'message': '已开始识别，请等待处理完成...',
        'data': {'audio_status': 'asr_processing'}
    })


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/retry-summary', methods=['POST'])
@dual_login_required
@visitor_block
def retry_audio_summary(item_id):
    """单独重新生成结构化总结"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    has_transcript = bool(
        (item.audio_transcript and item.audio_transcript.strip()) or
        (item.audio_transcript_segmented and item.audio_transcript_segmented.strip())
    )
    if not has_transcript:
        return jsonify({'code': 1, 'message': '没有转写内容，请先完成识别或手动输入转写文本后重试'}), 400

    if item.audio_status == 'summarizing':
        return jsonify({'code': 1, 'message': '正在总结中，请等待完成后重试'}), 409

    data = request.get_json(silent=True) or {}
    model_id = data.get('model_id')
    if model_id:
        from models.ai import LLMModel
        model = LLMModel.query.get(model_id)
        if not model or not model.is_active:
            return jsonify({'code': 1, 'message': '选择的模型不可用'}), 400
        try:
            model_id = int(model_id)
        except (TypeError, ValueError):
            return jsonify({'code': 1, 'message': '模型 ID 格式无效'}), 400

    item.audio_status = 'summarizing'
    item.progress_message = '正在总结...'
    item.summary_model_id = model_id if model_id else None
    db.session.commit()

    app_obj = current_app._get_current_object()
    from services.audio_service import run_summary_only
    threading.Thread(target=run_summary_only, args=(app_obj, ActivityLedger, item_id, model_id), daemon=True).start()
    return jsonify({'code': 0, 'message': '正在重新生成总结（与 ASR 服务独立）...', 'data': {'audio_status': 'summarizing'}})


# ---------------------------------------------------------------------------
# 取消
# ---------------------------------------------------------------------------

@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/cancel', methods=['POST'])
@dual_login_required
@visitor_block
def cancel_audio_processing(item_id):
    from services.audio_service import register_cancel
    register_cancel(ActivityLedger, item_id)
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    if item.audio_status in ('asr_processing', 'summarizing'):
        item.audio_status = 'cancelled'
        item.audio_summary = '处理已取消'
        db.session.commit()
    return jsonify({'code': 0, 'message': '已取消处理', 'data': {'audio_status': 'cancelled'}})


# ---------------------------------------------------------------------------
# 删除单个文件
# ---------------------------------------------------------------------------

@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/<int:file_index>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_audio_file(item_id, file_index):
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    from services.audio_service import get_audio_files, set_audio_files, resolve_audio_path_by_url

    files = get_audio_files(item)
    if file_index < 0 or file_index >= len(files):
        return jsonify({'code': 1, 'message': '文件索引无效'}), 400

    removed = files.pop(file_index)

    try:
        abs_path = resolve_audio_path_by_url(removed['url'])
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except OSError:
        pass

    if not files:
        item.audio_files = '[]'
        item.audio_archive = None
        item.audio_archive_size = None
        item.audio_transcript = None
        item.audio_summary = None
        item.audio_status = None
        item.audio_duration = None
    else:
        set_audio_files(item, files)
        item.audio_duration = sum(f.get('duration', 0) for f in files)

    db.session.commit()
    return jsonify({'code': 0, 'message': '文件已删除', 'data': {'audio_files': files}})


# ---------------------------------------------------------------------------
# 全部删除
# ---------------------------------------------------------------------------

@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_audio(item_id):
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    from services.audio_service import get_audio_files, resolve_audio_path_by_url

    files = get_audio_files(item)
    if not files:
        return jsonify({'code': 1, 'message': '该台账没有录音文件'}), 400

    for af in files:
        try:
            abs_path = resolve_audio_path_by_url(af['url'])
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except OSError:
            pass

    if item.audio_archive:
        try:
            archive_abs = os.path.join(os.path.dirname(Config.UPLOAD_FOLDER), item.audio_archive.lstrip('/'))
            if os.path.exists(archive_abs):
                os.remove(archive_abs)
        except OSError:
            pass

    item.audio_files = '[]'
    item.audio_archive = None
    item.audio_archive_size = None
    item.audio_transcript = None
    item.audio_summary = None
    item.audio_status = None
    item.audio_duration = None
    db.session.commit()

    return jsonify({'code': 0, 'message': '录音文件及数据已删除'})


# ---------------------------------------------------------------------------
# 手动编辑转写/总结
# ---------------------------------------------------------------------------

@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/transcript', methods=['PUT'])
@dual_login_required
@visitor_block
def update_audio_transcript(item_id):
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    from services.audio_service import get_audio_files

    files = get_audio_files(item)
    if not files:
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


# ---------------------------------------------------------------------------
# 结构化多版本 / docx 下载
# ---------------------------------------------------------------------------

@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/versions', methods=['GET'])
@dual_login_required
def get_audio_versions(item_id):
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    return jsonify({'code': 0, 'data': {
        'transcript': item.audio_transcript,
        'transcript_segmented': item.audio_transcript_segmented,
        'transcript_clean': item.audio_transcript_clean,
        'summary_structured': item.audio_summary_structured,
        'docx_path': item.audio_docx_path,
        'docx_size': item.audio_docx_size,
    }})


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/docx', methods=['GET'])
@dual_login_required
def download_audio_docx(item_id):
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    if not item.audio_docx_path:
        return jsonify({'code': 1, 'message': '尚未生成 Word 文档'}), 404
    docx_abs = os.path.join(current_app.static_folder, item.audio_docx_path.replace('/static/', ''))
    if not os.path.exists(docx_abs):
        return jsonify({'code': 1, 'message': 'Word 文件不存在'}), 404
    return send_from_directory(os.path.dirname(docx_abs), os.path.basename(docx_abs), as_attachment=True)
