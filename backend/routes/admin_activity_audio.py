"""
招商动态 - 录音文件上传 API
复用 services/audio_processing.py 的通用处理逻辑
"""
import os
import uuid
import logging
import threading
from flask import request, jsonify, current_app
from models import InvestmentActivity
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

        # 启动后台处理
        app_obj = current_app._get_current_object()
        threading.Thread(
            target=run_async_processing,
            args=(app_obj, item_id, InvestmentActivity),
            daemon=True
        ).start()

        return jsonify({
            'code': 0, 'message': '录音已上传，正在后台处理',
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
    """获取录音处理状态"""
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


@admin_activity_audio_bp.route('/activity/<int:item_id>/audio/cancel', methods=['POST'])
@dual_login_required
@visitor_block
def cancel_activity_audio(item_id):
    item = InvestmentActivity.query.filter_by(id=item_id).first_or_404()
    register_cancel(item_id)
    if item.audio_status in ('asr_processing', 'summarizing'):
        item.audio_status = 'cancelled'
        db.session.commit()
    return jsonify({'code': 0, 'message': '已取消', 'data': {'audio_status': 'cancelled'}})


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
    item.audio_files = '[]'
    item.audio_status = None
    item.audio_transcript = None
    item.audio_summary = None
    item.audio_duration = None
    item.progress_pct = 0
    item.progress_message = ''
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
    db.session.commit()
    return jsonify({'code': 0, 'message': '文件已删除', 'data': {'audio_files': files}})
