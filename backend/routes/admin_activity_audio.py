"""
招商动态 - 录音文件上传/处理 API（V15.1 组件化重构）

复用共享 service 层 services/audio_service.py（与活动台账共用同一套录音能力）：
  - 字段名映射通过 register_audio_model(InvestmentActivity, _ACTIVITY_AUDIO_FIELDS) 注册
  - ASR 转写 / 结构化总结 / 取消 / 进度 全部走 audio_service，不再内联 worker

此文件仅保留路由装饰器、鉴权与模型绑定（薄包装）。
"""
import os
import logging
import threading
import uuid
from flask import request, jsonify, send_from_directory, current_app
from models import InvestmentActivity
from models.ai import LLMModel
from extensions import db
from routes import admin_activity_audio_bp
from routes.business_auth import dual_login_required, visitor_block
from utils.image_upload import AUDIO_EXTENSIONS
from config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 注册招商动态的音频字段名映射（字段名与活动台账一致）
# ---------------------------------------------------------------------------
from services.audio_service import register_audio_model

_ACTIVITY_AUDIO_FIELDS = {
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

register_audio_model(InvestmentActivity, _ACTIVITY_AUDIO_FIELDS)


def _allowed_audio(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in AUDIO_EXTENSIONS


# ---------------------------------------------------------------------------
# 上传
# ---------------------------------------------------------------------------

@admin_activity_audio_bp.route('/activity/<int:item_id>/audio', methods=['POST'])
@dual_login_required
@visitor_block
def upload_activity_audio(item_id):
    """上传录音文件（支持多文件，异步处理）"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()

    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '请选择录音文件'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'code': 1, 'message': '未选择文件'}), 400

    if not _allowed_audio(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else '未知'
        return jsonify({'code': 1, 'message': f'不支持的音频格式：.{ext}'}), 400

    upload_dir = Config.UPLOAD_FOLDER
    os.makedirs(upload_dir, exist_ok=True)
    tmp_filename = f'_tmp_audio_{uuid.uuid4().hex[:8]}_{file.filename}'
    tmp_path = os.path.join(upload_dir, tmp_filename)

    try:
        file.save(tmp_path)
        from services.audio_compressor import save_original_audio
        save_result = save_original_audio(tmp_path, upload_dir)

        from services.audio_service import get_audio_files, set_audio_files

        new_entry = {
            'url': save_result['relative_url'],
            'name': file.filename,
            'duration': save_result['duration'],
            'size': save_result['file_size'],
            'status': 'pending',
            'error': ''
        }

        append_mode = request.form.get('append', 'false') == 'true'
        existing = get_audio_files(item) if append_mode else []
        existing.append(new_entry)
        set_audio_files(item, existing)

        total_duration = sum(f.get('duration', 0) for f in existing)

        # 上传新文件会使旧压缩包/转写失效，重置相关字段（对齐活动台账）
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

@admin_activity_audio_bp.route('/activity/<int:item_id>/audio', methods=['GET'])
@dual_login_required
def get_activity_audio_detail(item_id):
    """获取录音处理状态（含结构化总结字段）"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
    from services.audio_service import get_audio_files, estimate_time
    files = get_audio_files(item)
    return jsonify({'code': 0, 'data': {
        'audio_files': files,
        'audio_status': item.audio_status or '',
        'audio_transcript': item.audio_transcript or '',
        'audio_summary': item.audio_summary or '',
        'audio_duration': item.audio_duration or 0,
        'progress_pct': item.progress_pct or 0,
        'progress_message': item.progress_message or '',
        'estimated_summary_seconds': estimate_time(item.audio_duration, len(item.audio_transcript or '')),
        'audio_transcript_segmented': item.audio_transcript_segmented or '',
        'audio_transcript_clean': item.audio_transcript_clean or '',
        'audio_summary_structured': item.audio_summary_structured or '',
        'audio_docx_path': item.audio_docx_path or '',
        'audio_docx_size': item.audio_docx_size or 0,
        'audio_archive': item.audio_archive or '',
        'audio_archive_size': item.audio_archive_size or 0,
        'summary_model_id': item.summary_model_id or 0,
    }})


# ---------------------------------------------------------------------------
# 重新识别 / 重新总结
# ---------------------------------------------------------------------------

@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/retry', methods=['POST'])
@dual_login_required
@visitor_block
def retry_activity_audio(item_id):
    """重新调用语音识别（ASR 可用性检查由共享 worker 负责）"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()

    from services.audio_service import get_audio_files, run_async_processing, clear_cancel

    files = get_audio_files(item)
    if not files:
        return jsonify({'code': 1, 'message': '没有录音文件'}), 400

    if item.audio_status in ('asr_processing', 'summarizing'):
        return jsonify({'code': 1, 'message': '正在处理中'}), 409

    # 预检 ASR 服务是否可达：避免“已开始识别”后又静默失败
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

    # 清除上一次可能残留的取消标志（内存事件 + DB 状态），否则后台线程会在
    # is_task_cancelled() 处立即判定为“已取消”而退出，导致“重新识别”无效。
    clear_cancel(InvestmentActivity, item_id)

    app_obj = current_app._get_current_object()
    threading.Thread(target=run_async_processing, args=(app_obj, InvestmentActivity, item_id), daemon=True).start()
    return jsonify({'code': 0, 'message': '已开始识别', 'data': {'audio_status': 'asr_processing'}})


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/retry-summary', methods=['POST'])
@dual_login_required
@visitor_block
def retry_activity_audio_summary(item_id):
    """单独重新生成结构化总结（与 ASR 解耦，可带 model_id）"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()

    has_transcript = bool(
        (item.audio_transcript and item.audio_transcript.strip()) or
        (item.audio_transcript_segmented and item.audio_transcript_segmented.strip())
    )
    if not has_transcript:
        return jsonify({
            'code': 1,
            'message': '没有转写内容，请先完成识别或手动输入转写文本后重试'
        }), 400

    if item.audio_status == 'summarizing':
        return jsonify({'code': 1, 'message': '正在总结中，请等待完成后重试'}), 409

    data = request.get_json(silent=True) or {}
    model_id = data.get('model_id')
    if model_id:
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
    from services.audio_service import run_summary_only, clear_cancel
    # 同样清除可能的取消标志，避免重新总结被立即取消
    clear_cancel(InvestmentActivity, item_id)
    threading.Thread(
        target=run_summary_only,
        args=(app_obj, InvestmentActivity, item_id, model_id),
        daemon=True
    ).start()
    return jsonify({'code': 0, 'message': '正在开始生成总结（与 ASR 服务独立）...', 'data': {'audio_status': 'summarizing'}})


# ---------------------------------------------------------------------------
# 取消
# ---------------------------------------------------------------------------

@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/cancel', methods=['POST'])
@dual_login_required
@visitor_block
def cancel_activity_audio_processing(item_id):
    """取消正在进行的识别/总结任务（DB+内存双写，键含模型类，与台账一致）"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
    from services.audio_service import register_cancel
    register_cancel(InvestmentActivity, item_id)
    if item.audio_status in ('asr_processing', 'summarizing'):
        item.audio_status = 'cancelled'
        item.audio_summary = '处理已取消'
        db.session.commit()
    return jsonify({'code': 0, 'message': '已取消处理', 'data': {'audio_status': 'cancelled'}})


# ---------------------------------------------------------------------------
# 删除单个文件
# ---------------------------------------------------------------------------

@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/<int:file_index>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_activity_audio_file(item_id, file_index):
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()

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

    set_audio_files(item, files)
    if not files:
        item.audio_files = '[]'
        item.audio_archive = None
        item.audio_archive_size = None
        item.audio_transcript = None
        item.audio_summary = None
        item.audio_status = None
        item.audio_duration = None
        item.audio_transcript_segmented = None
        item.audio_transcript_clean = None
        item.audio_summary_structured = None
        item.audio_docx_path = None
        item.audio_docx_size = None
        item.summary_model_id = None
    else:
        item.audio_duration = sum(f.get('duration', 0) for f in files)

    db.session.commit()
    return jsonify({'code': 0, 'message': '文件已删除', 'data': {'audio_files': files}})


# ---------------------------------------------------------------------------
# 全部删除
# ---------------------------------------------------------------------------

@admin_activity_audio_bp.route('/activity/<int:item_id>/audio', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_activity_audio(item_id):
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()

    from services.audio_service import get_audio_files, resolve_audio_path_by_url

    files = get_audio_files(item)
    for af in files:
        try:
            abs_path = resolve_audio_path_by_url(af['url'])
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except OSError:
            pass

    if item.audio_archive:
        try:
            archive_abs = resolve_audio_path_by_url(item.audio_archive.lstrip('/'))
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
    item.progress_pct = 0
    item.progress_message = ''
    db.session.commit()

    return jsonify({'code': 0, 'message': '录音文件及数据已删除'})


# ---------------------------------------------------------------------------
# 手动编辑转写/总结
# ---------------------------------------------------------------------------

@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/transcript', methods=['PUT'])
@dual_login_required
@visitor_block
def update_activity_audio_transcript(item_id):
    """手动编辑转写/总结后独立保存"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()

    from services.audio_service import get_audio_files

    if not get_audio_files(item):
        return jsonify({'code': 1, 'message': '该动态没有录音文件'}), 400

    data = request.get_json(silent=True) or {}
    transcript = data.get('transcript')
    summary = data.get('summary')

    updated = False
    if transcript is not None:
        item.audio_transcript = transcript
        item.audio_transcript_segmented = transcript
        updated = True
    if summary is not None:
        item.audio_summary = summary
        item.audio_summary_structured = summary
        updated = True

    if not updated:
        return jsonify({'code': 1, 'message': '未提供需要更新的内容'}), 400

    db.session.commit()
    return jsonify({'code': 0, 'message': '转写内容已更新'})


# ---------------------------------------------------------------------------
# 结构化多版本 / docx 下载
# ---------------------------------------------------------------------------

@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/versions', methods=['GET'])
@dual_login_required
def get_activity_audio_versions(item_id):
    """获取结构化总结多版本数据"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
    return jsonify({'code': 0, 'data': {
        'transcript': item.audio_transcript,
        'transcript_segmented': item.audio_transcript_segmented,
        'transcript_clean': item.audio_transcript_clean,
        'summary_structured': item.audio_summary_structured,
        'docx_path': item.audio_docx_path,
        'docx_size': item.audio_docx_size,
    }})


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/docx', methods=['GET'])
@dual_login_required
def download_activity_audio_docx(item_id):
    """下载结构化总结 docx 文件"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
    if not item.audio_docx_path:
        return jsonify({'code': 1, 'message': '尚未生成 Word 文档，请等待处理完成或重新识别'}), 404
    docx_abs = os.path.join(current_app.static_folder, item.audio_docx_path.replace('/static/', ''))
    if not os.path.exists(docx_abs):
        return jsonify({'code': 1, 'message': 'Word 文件不存在，请重新生成'}), 404
    dir_name = os.path.dirname(docx_abs)
    basename = os.path.basename(docx_abs)
    return send_from_directory(dir_name, basename, as_attachment=True)
