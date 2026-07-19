"""
招商动态 - 录音文件上传/处理 API（V15.1 对齐活动台账全套录音能力）
复用 services/audio_processing.py 的通用处理逻辑
"""
import os
import uuid
import logging
import threading
from flask import request, jsonify, current_app, send_from_directory
from models import InvestmentActivity
from models.ai import LLMModel
from extensions import db
from routes import admin_activity_audio_bp
from routes.business_auth import dual_login_required, visitor_block
from utils.image_upload import AUDIO_EXTENSIONS
from config import Config
from services.audio_processing import (
    run_async_processing, register_cancel, get_audio_files, set_audio_files,
    estimate_time
)

logger = logging.getLogger(__name__)


def _allowed_audio(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in AUDIO_EXTENSIONS


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
        item.audio_status = 'uploaded'
        item.audio_duration = total_duration
        item.audio_transcript = None
        item.audio_summary = None
        db.session.commit()

        # V15.1 对齐活动台账：上传仅落盘置 'uploaded'，不自动起后台线程；需前端调 /retry 触发 ASR
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
            try: os.remove(tmp_path)
            except OSError: pass


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio', methods=['GET'])
@dual_login_required
def get_activity_audio_detail(item_id):
    """获取录音处理状态（V15.1 对齐活动台账，含结构化总结字段）"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
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
        # V15.1 结构化总结 + docx + 压缩包 + LLM 模型回填
        'audio_transcript_segmented': getattr(item, 'audio_transcript_segmented', None) or '',
        'audio_transcript_clean': getattr(item, 'audio_transcript_clean', None) or '',
        'audio_summary_structured': getattr(item, 'audio_summary_structured', None) or '',
        'audio_docx_path': getattr(item, 'audio_docx_path', None) or '',
        'audio_docx_size': getattr(item, 'audio_docx_size', None) or 0,
        'audio_archive': getattr(item, 'audio_archive', None) or '',
        'audio_archive_size': getattr(item, 'audio_archive_size', None) or 0,
        'summary_model_id': getattr(item, 'summary_model_id', None) or 0,
    }})


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/retry', methods=['POST'])
@dual_login_required
@visitor_block
def retry_activity_audio(item_id):
    """重新识别"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
    files = get_audio_files(item)
    if not files:
        return jsonify({'code': 1, 'message': '没有录音文件'}), 400
    if item.audio_status in ('asr_processing', 'summarizing'):
        return jsonify({'code': 1, 'message': '正在处理中'}), 409

    item.audio_status = 'asr_processing'
    item.progress_message = '转写准备中...'
    item.progress_pct = 0
    db.session.commit()

    app_obj = current_app._get_current_object()
    threading.Thread(target=run_async_processing, args=(app_obj, item_id, InvestmentActivity), daemon=True).start()
    return jsonify({'code': 0, 'message': '已开始识别', 'data': {'audio_status': 'asr_processing'}})


# V15.1 取消端点已迁移至文件末尾的 cancel_activity_audio_processing（DB+内存双写）


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_activity_audio(item_id):
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
    files = get_audio_files(item)
    for af in files:
        try:
            file_rel = af['url'].lstrip('/')
            abs_path = os.path.join(os.path.dirname(Config.UPLOAD_FOLDER), file_rel)
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except OSError:
            pass
    # V15.1 对齐活动台账：全部删除时同步清压缩包文件
    if getattr(item, 'audio_archive', None):
        try:
            archive_abs = os.path.join(os.path.dirname(Config.UPLOAD_FOLDER), item.audio_archive.lstrip('/'))
            if os.path.exists(archive_abs):
                os.remove(archive_abs)
        except OSError:
            pass
    item.audio_files = '[]'
    item.audio_status = None
    item.audio_transcript = None
    item.audio_summary = None
    item.audio_duration = None
    item.progress_pct = 0
    item.progress_message = ''
    # V15.1 清理结构化总结 + docx + 压缩包 + LLM 模型回填
    item.audio_archive = None
    item.audio_archive_size = None
    item.audio_transcript_segmented = None
    item.audio_transcript_clean = None
    item.audio_summary_structured = None
    item.audio_docx_path = None
    item.audio_docx_size = None
    item.summary_model_id = None
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/<int:file_index>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_activity_audio_file(item_id, file_index):
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
    files = get_audio_files(item)
    if file_index < 0 or file_index >= len(files):
        return jsonify({'code': 1, 'message': '文件索引无效'}), 400
    removed = files.pop(file_index)
    try:
        abs_path = os.path.join(os.path.dirname(Config.UPLOAD_FOLDER), removed['url'].lstrip('/'))
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except OSError:
        pass
    set_audio_files(item, files)
    if not files:
        item.audio_files = '[]'
        item.audio_status = None
        item.audio_transcript = None
        item.audio_summary = None
        item.audio_duration = None
        # V15.1 对齐活动台账：files 清空时同步清压缩包与结构化字段
        item.audio_archive = None
        item.audio_archive_size = None
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


# ======================== V15.1 独立保存/多版本/重总结/下载/批量上传 ========================


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/transcript', methods=['PUT'])
@dual_login_required
@visitor_block
def update_activity_audio_transcript(item_id):
    """手动编辑转写/总结后独立保存（对齐活动台账 L739-766）"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
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


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/versions', methods=['GET'])
@dual_login_required
def get_activity_audio_versions(item_id):
    """获取结构化总结多版本数据（对齐活动台账 L839-851）"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
    return jsonify({'code': 0, 'data': {
        'transcript': item.audio_transcript,
        'transcript_segmented': getattr(item, 'audio_transcript_segmented', None),
        'transcript_clean': getattr(item, 'audio_transcript_clean', None),
        'summary_structured': getattr(item, 'audio_summary_structured', None),
        'docx_path': getattr(item, 'audio_docx_path', None),
        'docx_size': getattr(item, 'audio_docx_size', None),
    }})


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/docx', methods=['GET'])
@dual_login_required
def download_activity_audio_docx(item_id):
    """下载结构化总结 docx 文件（对齐活动台账 L854-869）"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
    if not getattr(item, 'audio_docx_path', None):
        return jsonify({'code': 1, 'message': '尚未生成 Word 文档，请等待处理完成或重新识别'}), 404
    docx_abs = os.path.join(
        current_app.static_folder,
        item.audio_docx_path.replace('/static/', '')
    )
    if not os.path.exists(docx_abs):
        return jsonify({'code': 1, 'message': 'Word 文件不存在，请重新生成'}), 404
    dir_name = os.path.dirname(docx_abs)
    basename = os.path.basename(docx_abs)
    return send_from_directory(dir_name, basename, as_attachment=True)


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/retry-summary', methods=['POST'])
@dual_login_required
@visitor_block
def retry_activity_audio_summary(item_id):
    """单独重新生成结构化总结（与 ASR 解耦，可带 model_id，对齐活动台账 L624-673）"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()

    has_transcript = bool(
        (item.audio_transcript and item.audio_transcript.strip()) or
        (getattr(item, 'audio_transcript_segmented', None) and item.audio_transcript_segmented.strip())
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

    # V15.1：通过 worker 透传 model_id，_run_summary_only 复用公共引擎的 _apply_summary
    app_obj = current_app._get_current_object()
    threading.Thread(
        target=_run_summary_only,
        args=(app_obj, item.id, model_id),
        daemon=True
    ).start()
    return jsonify({'code': 0, 'message': '正在重新生成总结（与 ASR 服务独立）...', 'data': {'audio_status': 'summarizing'}})


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/cancel', methods=['POST'])
@dual_login_required
@visitor_block
def cancel_activity_audio_processing(item_id):
    """取消正在进行的识别/总结任务（对齐活动台账 L676-694，DB+内存双写）"""
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
    register_cancel(item_id)
    if item.audio_status in ('asr_processing', 'summarizing'):
        item.audio_status = 'cancelled'
        item.audio_summary = '处理已取消'
        db.session.commit()
    return jsonify({'code': 0, 'message': '已取消处理', 'data': {'audio_status': 'cancelled'}})


def _run_summary_only(app, item_id, model_id=None):
    """仅重新总结（不跑 ASR，对齐活动台账 L274-306）"""
    with app.app_context():
        item = InvestmentActivity.query.get(item_id)
        if not item:
            return
        from services.audio_processing import _apply_summary
        full_text = item.audio_transcript or getattr(item, 'audio_transcript_segmented', None) or ''
        try:
            _apply_summary(app, item, full_text, model_id=model_id)
            item.audio_status = 'completed'
            item.progress_pct = 100
            item.progress_message = '处理完成'
            item.summary_model_id = model_id if model_id else item.summary_model_id
            from extensions import db
            db.session.commit()
        except Exception as e:
            from extensions import db
            item.audio_status = 'summary_failed'
            item.audio_summary = f'总结失败：{str(e)[:200]}'
            db.session.commit()
