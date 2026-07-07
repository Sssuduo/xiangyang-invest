"""
活动台账 - 录音文件上传 API

支持录音上传 → 音频压缩 → 语音转文字 → 内容总结 的完整流程
"""
import os
import json
from flask import request, jsonify
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


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>/audio', methods=['POST'])
@dual_login_required
@visitor_block
def upload_audio(item_id):
    """
    上传录音文件并自动进行压缩、语音转文字和内容总结

    Form Data:
        file: 录音文件（wav, mp3, m4a, ogg, flac, wma, aac, amr, opus, weba）

    Returns:
        JSON:
        - code: 0
        - data: {
            audio_file: str,       # 压缩后录音文件路径
            audio_transcript: str, # 语音转文字结果
            audio_summary: str,    # 内容总结
            audio_duration: float, # 录音时长(秒)
            original_size: int,   # 原始文件大小
            compressed_size: int, # 压缩后文件大小
            compression_ratio: float # 压缩比
          }
    """
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    # 检查文件
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

    # 1. 暂存原始文件
    import uuid
    upload_dir = Config.UPLOAD_FOLDER
    os.makedirs(upload_dir, exist_ok=True)
    tmp_filename = f'_tmp_audio_{uuid.uuid4().hex[:8]}_{file.filename}'
    tmp_path = os.path.join(upload_dir, tmp_filename)

    try:
        file.save(tmp_path)

        # 2. 压缩音频
        from services.audio_compressor import compress_audio_to_storage
        compress_result = compress_audio_to_storage(tmp_path, upload_dir)

        # 3. 语音转文字
        from services.speech_to_text import transcribe_audio
        asr_result = transcribe_audio(compress_result['output_path'])

        # 4. 内容总结
        from services.text_summarizer import summarize_with_llm
        summary = summarize_with_llm(asr_result['text'])

        # 5. 更新数据库
        item.audio_file = compress_result['relative_url']
        item.audio_transcript = asr_result['text']
        item.audio_summary = summary
        item.audio_status = 'completed'
        item.audio_duration = round(compress_result['duration'], 1)
        db.session.commit()

        return jsonify({
            'code': 0,
            'message': '录音处理完成',
            'data': {
                'audio_file': compress_result['relative_url'],
                'audio_transcript': asr_result['text'],
                'audio_summary': summary,
                'audio_duration': round(compress_result['duration'], 1),
                'original_size': compress_result['original_size'],
                'compressed_size': compress_result['compressed_size'],
                'compression_ratio': compress_result['compression_ratio']
            }
        })

    except Exception as e:
        # 记录失败状态
        item.audio_status = 'failed'
        db.session.commit()
        error_msg = str(e)
        return jsonify({'code': 1, 'message': f'录音处理失败：{error_msg}'}), 500

    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>/audio', methods=['GET'])
@dual_login_required
def get_audio_detail(item_id):
    """获取录音详情（转写文本 + 总结）"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    return jsonify({
        'code': 0,
        'data': {
            'audio_file': item.audio_file,
            'audio_transcript': item.audio_transcript,
            'audio_summary': item.audio_summary,
            'audio_status': item.audio_status,
            'audio_duration': item.audio_duration
        }
    })


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>/audio', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_audio(item_id):
    """删除录音文件及转写/总结数据"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    if not item.audio_file:
        return jsonify({'code': 1, 'message': '该台账没有录音文件'}), 400

    # 删除物理文件
    from config import Config
    file_rel_path = item.audio_file.lstrip('/')
    file_abs_path = os.path.join(os.path.dirname(Config.UPLOAD_FOLDER), file_rel_path)
    if os.path.exists(file_abs_path):
        try:
            os.remove(file_abs_path)
        except OSError:
            pass

    # 清除数据库字段
    item.audio_file = None
    item.audio_transcript = None
    item.audio_summary = None
    item.audio_status = None
    item.audio_duration = None
    db.session.commit()

    return jsonify({'code': 0, 'message': '录音文件及数据已删除'})
