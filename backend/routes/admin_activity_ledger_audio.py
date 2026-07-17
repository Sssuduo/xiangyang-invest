"""
活动台账 - 录音文件上传 API

流程：
1. 上传：支持多个录音文件，逐个保存 → 开始处理
2. 处理: ASR 逐步转写 → 完成 → 自动触发 LLM 总结 → 完成
3. 进度实时可见，已识别内容不覆盖
4. 取消：后台线程检查取消标记，在段间隙退出

多文件结构：
- audio_files JSON 数组：[{url, name, duration, size, status: 'ok'|'error'|'pending', error: ''}, ...]
- audio_transcript: 多文件转写全文（按序拼接）
- audio_summary: 基于合并全文的 LLM 总结
"""
import os
import json
import threading
from flask import request, jsonify, send_from_directory, current_app
from models import ActivityLedger
from extensions import db
from routes import admin_activity_ledger_audio_bp
from routes.business_auth import dual_login_required, visitor_block
from utils.image_upload import AUDIO_EXTENSIONS
from config import Config

# 后台任务取消注册表 {item_id: threading.Event}
_TASK_CANCEL_EVENTS: dict[int, threading.Event] = {}
_TASK_CANCEL_LOCK = threading.Lock()


def _is_task_cancelled(item_id: int) -> bool:
    """检查任务是否被取消。优先查内存注册表，回退查 DB 状态"""
    with _TASK_CANCEL_LOCK:
        ev = _TASK_CANCEL_EVENTS.get(item_id)
        if ev is not None:
            return ev.is_set()
    try:
        item = ActivityLedger.query.get(item_id)
        return item is not None and item.audio_status == 'cancelled'
    except Exception:
        return False


def _allowed_audio(filename):
    """检查是否为允许的音频格式"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in AUDIO_EXTENSIONS


def _get_audio_files(item):
    """解析 audio_files JSON"""
    return json.loads(item.audio_files or '[]')


def _set_audio_files(item, files_list):
    """设置 audio_files JSON"""
    item.audio_files = json.dumps(files_list, ensure_ascii=False)


def _resolve_audio_path_by_url(url):
    """根据文件 URL 解析文件绝对路径"""
    file_rel = url.lstrip('/')
    project_root = os.path.dirname(os.path.dirname(Config.UPLOAD_FOLDER))
    return os.path.join(project_root, file_rel)


def _apply_corrections_text(text, scope='all'):
    """应用术语校正表到任意文本，返回替换后的文本。"""
    if not text:
        return text, 0
    try:
        from services.term_correction import apply_corrections
        return apply_corrections(text, scope)
    except Exception:
        return text, 0


def _estimate_time(duration_s, transcript_chars):
    """预估完成时间（秒）。"""
    if not duration_s and not transcript_chars:
        return 60
    asr = (duration_s or 0) * 8
    llm = (transcript_chars or 0) * 0.003
    overhead = 30
    return int(asr + llm + overhead)


def _run_async_processing(app, item_id):
    """
    后台线程：对 audio_files 逐个 ASR 转写 → 实时更新进度 → 识别完成后自动调总结。
    已识别的段 (status === 'ok') 保留不覆盖。

    进度追踪：基于切片级别（30s/段），实时计算百分比和预估剩余时间。
    """
    import logging
    import time as _time
    logger = logging.getLogger(__name__)

    with app.app_context():
        try:
            item = ActivityLedger.query.get(item_id)
            if not item:
                logger.error(f'后台处理：活动台账 {item_id} 不存在')
                return

            files = _get_audio_files(item)
            if not files:
                item.audio_status = 'failed'
                item.audio_summary = '处理失败：没有录音文件'
                db.session.commit()
                return

            from services.speech_to_text import transcribe_audio, check_asr_health

            # 先检查 ASR 服务是否可用
            if not check_asr_health():
                item.audio_status = 'failed'
                item.audio_summary = '录音转写服务未启动，请联系管理员苏铎'
                item.progress_message = None
                item.progress_pct = 0
                db.session.commit()
                logger.error(f'后台处理：ASR 服务不可用，item_id={item_id}')
                return

            item.audio_status = 'asr_processing'
            item.progress_message = '转写准备中...'
            item.progress_pct = 0
            db.session.commit()

            all_texts = []
            total_ok = 0
            total_err = 0
            # 内存中转写缓存：status==='ok' 时，记录转写文本供本轮后续文件复用
            _transcript_cache = {}
            total_files = len(files)

            # === 进度追踪：预计算总切片数 ===
            SLICE_DURATION = 30  # 与 speech_to_text.SEGMENT_DURATION 一致
            file_slice_counts = []  # 每个文件的切片数
            for af in files:
                dur = af.get('duration') or 0
                if dur <= 0:
                    file_slice_counts.append(1)  # 无法获取时长时按 1 段算
                else:
                    slices = max(1, int(dur + SLICE_DURATION - 1) // SLICE_DURATION)  # 向上取整
                    file_slice_counts.append(slices)
            total_slices = sum(file_slice_counts)
            slices_completed = 0
            start_time = _time.time()

            def _update_progress(slice_idx, slice_total):
                """每完成一个切片调用：更新 progress_pct 和预估剩余时间"""
                nonlocal slices_completed
                slices_completed += 1
                pct = int(slices_completed / total_slices * 100) if total_slices > 0 else 0
                item.progress_pct = min(pct, 99)

                # 预估剩余时间（基于已用时间和完成比例）
                elapsed = _time.time() - start_time
                if slices_completed > 0 and elapsed > 1:
                    avg_time_per_slice = elapsed / slices_completed
                    remaining_slices = total_slices - slices_completed
                    remaining_sec = int(avg_time_per_slice * remaining_slices)
                    remaining_min = max(1, remaining_sec // 60)
                    item.progress_message = f'正在识别 ({slices_completed}/{total_slices} 段) · 约 {remaining_min} 分钟'
                else:
                    item.progress_message = f'正在识别 ({slices_completed}/{total_slices} 段)...'

                try:
                    db.session.commit()
                except Exception:
                    pass

            for i, af in enumerate(files):
                # 检查是否被取消
                if _is_task_cancelled(item_id):
                    logger.info(f'后台 ASR 已取消: item_id={item_id}')
                    item.audio_status = 'cancelled'
                    item.audio_summary = '处理已取消'
                    db.session.commit()
                    return

                if af.get('status') == 'ok' and i in _transcript_cache:
                    slices_completed += file_slice_counts[i]
                    all_texts.append(_transcript_cache[i])
                    continue

                file_path = _resolve_audio_path_by_url(af['url'])
                if not os.path.exists(file_path):
                    af['status'] = 'error'
                    af['error'] = '文件不存在'
                    total_err += 1
                    slices_completed += file_slice_counts[i]
                    all_texts.append('')
                    continue

                logger.info(f'后台 ASR [{i + 1}/{total_files}]: {af["name"]}')

                try:
                    asr_result = transcribe_audio(file_path, on_slice_done=_update_progress)
                    text = asr_result['text']
                    af['status'] = 'ok'
                    af['error'] = ''
                    af['_transcript'] = text  # 临时保存，JSON 持久化前需 strip
                    _transcript_cache[i] = text
                    all_texts.append(text)
                    total_ok += 1
                    af.pop('_transcript', None)
                    _set_audio_files(item, files)
                    logger.info(f'后台 ASR [{i + 1}/{total_files}] 完成: {len(text)} 字')
                except Exception as e:
                    logger.error(f'后台 ASR [{i + 1}/{total_files}] 失败: {e}')
                    af['status'] = 'error'
                    af['error'] = str(e)[:300]
                    total_err += 1
                    slices_completed += file_slice_counts[i]
                    all_texts.append(f'[识别失败：{af["name"]}]')

            # 拼接全文
            full_text_parts = []
            for i, af in enumerate(files):
                if all_texts[i]:
                    full_text_parts.append(f'【{af["name"]}】\n{all_texts[i]}')

            separator = '\n\n---\n\n'
            full_text = separator.join(full_text_parts)
            item.audio_transcript = full_text
            item.audio_status = 'asr_completed'
            item.progress_pct = 100
            item.progress_message = f'识别完成 ({total_ok}/{total_files} 文件)'
            db.session.commit()
            logger.info(f'后台 ASR 完成: item_id={item_id}, {total_ok}/{total_files} 成功')

            # ASR 完成 → 自动触发总结
            if full_text.strip():
                item.audio_status = 'summarizing'
                item.progress_message = '正在总结...'
                db.session.commit()
                try:
                    _apply_summary_to_item(item, full_text)
                    item.audio_status = 'completed'
                    item.progress_pct = 100
                    item.progress_message = '处理完成'
                    db.session.commit()
                    logger.info(f'后台处理完成: item_id={item_id}')
                except Exception as summary_err:
                    # 总结失败不影响转写内容展示
                    logger.warning(f'总结失败（转写成功）: item_id={item_id}, 错误={summary_err}')
                    item.audio_status = 'summary_failed'
                    item.audio_summary = f'总结失败：{str(summary_err)[:200]}'
                    db.session.commit()
            else:
                item.audio_status = 'completed'
                item.progress_pct = 100
                item.progress_message = '处理完成（转写内容为空）'
                item.audio_summary = '转写内容为空，无法生成总结'
                db.session.commit()

        except Exception as e:
            logger.error(f'后台处理失败：item_id={item_id}，错误：{e}', exc_info=True)
            try:
                item = ActivityLedger.query.get(item_id)
                if item:
                    item.audio_status = 'failed'
                    err_msg = str(e)[:500]
                    item.audio_summary = err_msg if '请联系管理员苏铎' in err_msg else f'处理失败：{err_msg}'
                    db.session.commit()
            except Exception:
                pass


def _run_summary_only(app, item_id, model_id=None):
    """仅重新生成结构化总结（基于现有 audio_transcript）。

    Args:
        app: Flask app 实例
        item_id: ActivityLedger ID
        model_id: 用户选择的 LLM 模型 ID (可选, None 使用默认激活模型)
    """
    with app.app_context():
        from models import ActivityLedger
        item = ActivityLedger.query.get(item_id)
        if not item:
            return
        if _is_task_cancelled(item_id):
            item.audio_status = 'cancelled'
            from extensions import db
            db.session.commit()
            return
        item.audio_status = 'summarizing'
        item.progress_message = '正在总结...'
        from extensions import db
        db.session.commit()
        try:
            clean_transcript, _ = _apply_corrections_text(item.audio_transcript or '', 'clean')
            _apply_summary_to_item(item, clean_transcript, model_id=model_id)
            item.audio_status = 'completed'
            item.progress_pct = 100
            item.progress_message = '处理完成'
            db.session.commit()
        except Exception as e:
            item.audio_summary = f'总结失败: {str(e)[:200]}'
            item.audio_status = 'failed'
            db.session.commit()


def _apply_summary_to_item(item, full_text, model_id=None):
    """对台账 item 生成结构化总结 (segmented + clean + summary + docx)

    Args:
        item: ActivityLedger 实例
        full_text: 输入文本
        model_id: 用户选择的 LLM 模型 ID (可选, None 使用默认激活模型)
    """
    import logging, os
    logger = logging.getLogger(__name__)
    from services.text_summarizer import summarize_meeting
    from services.meeting_document import generate_meeting_docx

    logger.info(f'后台结构化总结开始：item_id={item.id}，{len(full_text)} 字，model_id={model_id}')
    try:
        summary_result = summarize_meeting(full_text, model_id=model_id)
        item.audio_transcript_segmented = summary_result.get('segmented', '')
        item.audio_transcript_clean = summary_result.get('clean', '')
        item.audio_summary_structured = summary_result.get('summary', '')
        # 生成 docx
        try:
            docx_url, _ = generate_meeting_docx(
                activity=item,
                segmented_text=summary_result.get('segmented', ''),
                clean_text=summary_result.get('clean', ''),
                summary_text=summary_result.get('summary', '')
            )
            item.audio_docx_path = docx_url
            docx_abs = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'static', docx_url.replace('/static/', '')
            )
            if os.path.exists(docx_abs):
                item.audio_docx_size = os.path.getsize(docx_abs)
        except Exception as docx_err:
            logger.error(f'meeting docx generation failed: {docx_err}', exc_info=True)
        # backward compat: audio_summary 指向摘要版
        item.audio_summary = summary_result.get('summary', '')
        db.session.commit()
        summary_len = len(summary_result.get('summary', ''))
        logger.info(f'后台结构化总结完成 (3阶段串行LLM) segmented={len(summary_result.get("segmented",""))} clean={len(summary_result.get("clean",""))} summary={summary_len}')
    except Exception as e:
        logger.error(f'meeting summary failed: {e}', exc_info=True)
        item.audio_summary = f'总结失败: {str(e)[:200]}'
        item.audio_status = 'failed'
        db.session.commit()


def _run_terminology_only(app, item_id):
    """术语校正，仅替换不重新生成摘要结构"""
    with app.app_context():
        from models import ActivityLedger
        item = ActivityLedger.query.get(item_id)
        if not item:
            return
        from services.term_correction import apply_corrections_to_item
        item.audio_status = 'summarizing'
        from extensions import db
        db.session.commit()
        try:
            n = apply_corrections_to_item(item, 'all')
            item.audio_status = 'completed'
            item.progress_pct = 100
            item.progress_message = '处理完成'
            db.session.commit()
        except Exception as e:
            item.audio_status = 'failed'
            db.session.commit()


# ======================== 上传 ========================


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio', methods=['POST'])
@dual_login_required
@visitor_block
def upload_audio(item_id):
    """
    上传录音文件（支持多文件，异步处理）
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

    import uuid
    upload_dir = Config.UPLOAD_FOLDER
    os.makedirs(upload_dir, exist_ok=True)
    tmp_filename = f'_tmp_audio_{uuid.uuid4().hex[:8]}_{file.filename}'
    tmp_path = os.path.join(upload_dir, tmp_filename)

    try:
        file.save(tmp_path)

        from services.audio_compressor import save_original_audio
        save_result = save_original_audio(tmp_path, upload_dir)

        new_file_entry = {
            'url': save_result['relative_url'],
            'name': file.filename,
            'duration': save_result['duration'],
            'size': save_result['file_size'],
            'status': 'pending',
            'error': ''
        }

        append_mode = request.form.get('append', 'false') == 'true'
        existing = _get_audio_files(item) if append_mode else []
        existing.append(new_file_entry)
        _set_audio_files(item, existing)

        total_duration = sum(f.get('duration', 0) for f in existing)

        item.audio_archive = None
        item.audio_archive_size = None
        item.audio_status = 'uploaded'
        item.audio_duration = total_duration
        item.audio_transcript = None
        item.audio_summary = None
        db.session.commit()

        return jsonify({
            'code': 0,
            'message': '录音已上传',
            'data': {
                'audio_files': existing,
                'audio_status': 'uploaded',
                'audio_duration': total_duration,
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


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/batch', methods=['POST'])
@dual_login_required
@visitor_block
def upload_audio_batch(item_id):
    """批量上传多个录音文件"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    uploaded = request.files.getlist('files')
    if not uploaded:
        return jsonify({'code': 1, 'message': '请选择录音文件'}), 400

    import uuid
    upload_dir = Config.UPLOAD_FOLDER
    os.makedirs(upload_dir, exist_ok=True)

    existing = _get_audio_files(item)
    saved_files = []

    for file in uploaded:
        if not file or not file.filename:
            continue
        if not _allowed_audio(file.filename):
            continue

        tmp_filename = f'_tmp_audio_{uuid.uuid4().hex[:8]}_{file.filename}'
        tmp_path = os.path.join(upload_dir, tmp_filename)

        try:
            file.save(tmp_path)
            from services.audio_compressor import save_original_audio
            save_result = save_original_audio(tmp_path, upload_dir)
            existing.append({
                'url': save_result['relative_url'],
                'name': file.filename,
                'duration': save_result['duration'],
                'size': save_result['file_size'],
                'status': 'pending',
                'error': ''
            })
            saved_files.append(file.filename)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f'batch upload failed for {file.filename}: {e}')
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    if not saved_files:
        return jsonify({'code': 1, 'message': '所有文件上传失败'}), 400

    _set_audio_files(item, existing)
    total_duration = sum(f.get('duration', 0) for f in existing)

    item.audio_archive = None
    item.audio_archive_size = None
    item.audio_status = 'uploaded'
    item.audio_duration = total_duration
    item.audio_transcript = None
    item.audio_summary = None
    db.session.commit()

    return jsonify({
        'code': 0,
        'message': f'{len(saved_files)} 个文件已上传',
        'data': {
            'audio_files': existing,
            'audio_status': 'uploaded',
            'audio_duration': total_duration,
        }
    })


# ======================== 查询 ========================


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio', methods=['GET'])
@dual_login_required
def get_audio_detail(item_id):
    """获取录音处理状态及详情"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    files = _get_audio_files(item)
    data = {
        'audio_files': files,
        'audio_file': files[0]['url'] if files else None,
        'audio_archive': item.audio_archive,
        'audio_archive_size': item.audio_archive_size,
        'audio_transcript': item.audio_transcript,
        'audio_summary': item.audio_summary,
        'audio_status': item.audio_status,
        'audio_duration': item.audio_duration,
        # V15.1: 结构化总结多版本
        'audio_transcript_segmented': item.audio_transcript_segmented,
        'audio_transcript_clean': item.audio_transcript_clean,
        'audio_summary_structured': item.audio_summary_structured,
        'audio_docx_path': item.audio_docx_path,
        'audio_docx_size': item.audio_docx_size,
        # V15.1: 总结使用的模型 ID，供前端回填选择
        'summary_model_id': item.summary_model_id,
        # V15.1: 进度估算和实时 progress
        'estimated_summary_seconds': _estimate_time(item.audio_duration, len(item.audio_transcript or '')),
        'progress_message': item.progress_message,
        'progress_pct': item.progress_pct,
    }

    # 补充文件大小信息（实时查询）
    for af in files:
        if af.get('size'):
            continue
        try:
            abs_path = _resolve_audio_path_by_url(af['url'])
            if os.path.exists(abs_path):
                af['size'] = os.path.getsize(abs_path)
        except Exception:
            pass

    return jsonify({'code': 0, 'data': data})


# ======================== 重新识别 ========================


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/retry', methods=['POST'])
@dual_login_required
@visitor_block
def retry_audio_recognition(item_id):
    """重新调用语音识别 (不清空已有已识别内容, 完成后自动总结)"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    files = _get_audio_files(item)
    if not files:
        return jsonify({'code': 1, 'message': '没有录音文件，无法重新识别'}), 400

    # 如果当前正在处理, 拒绝
    if item.audio_status in ('asr_processing', 'summarizing'):
        return jsonify({'code': 1, 'message': '正在处理中，请等待完成后重试'}), 409

    # 重置状态字段, 但不清空已存在的识别缓存 (_transcript_cache 由 worker 内部维护)
    item.audio_status = 'asr_processing'
    item.progress_message = '转写准备中...'
    item.progress_pct = 0
    # 不覆盖已存在的 audio_transcript_segmented 等字段 (前端仍可显示已有内容)
    db.session.commit()

    app = current_app._get_current_object()
    threading.Thread(target=_run_async_processing, args=(app, item_id), daemon=True).start()

    return jsonify({
        'code': 0,
        'message': '已开始识别，请等待处理完成...',
        'data': {'audio_status': 'asr_processing'}
    })




@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/retry-summary', methods=['POST'])
@dual_login_required
@visitor_block
def retry_audio_summary(item_id):
    """单独重新生成结构化总结（基于现有 audio_transcript）

    与 ASR 解耦：只要有转写内容即可总结，无需 ASR 服务在线。
    """
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    # 检查是否有转写内容（核心：不依赖 ASR 服务状态）
    has_transcript = bool(
        (item.audio_transcript and item.audio_transcript.strip()) or
        (item.audio_transcript_segmented and item.audio_transcript_segmented.strip())
    )
    if not has_transcript:
        return jsonify({
            'code': 1,
            'message': '没有转写内容，请先完成识别或手动输入转写文本后重试'
        }), 400

    # 仅在 summarizing 时拒绝，asr_processing 不阻塞（允许先总结已有内容）
    if item.audio_status == 'summarizing':
        return jsonify({'code': 1, 'message': '正在总结中，请等待完成后重试'}), 409

    # 获取用户选择的模型 ID (可选)
    data = request.get_json(silent=True) or {}
    model_id = data.get('model_id')
    if model_id:
        from models.ai import LLMModel
        model = LLMModel.query.get(model_id)
        if not model or not model.is_active:
            return jsonify({'code': 1, 'message': '选择的模型不可用'}), 400
        # 转换为 int (前端可能传字符串)
        try:
            model_id = int(model_id)
        except (TypeError, ValueError):
            return jsonify({'code': 1, 'message': '模型 ID 格式无效'}), 400

    # 总结期间允许 asr_processing 并行（不阻塞新识别）
    item.audio_status = 'summarizing'
    item.progress_message = '正在总结...'
    # V15.1: 记录用户选择的模型 ID，刷新后前端可回填
    item.summary_model_id = model_id if model_id else None
    db.session.commit()

    app_obj = current_app._get_current_object()
    # 通过线程参数传递 model_id，避免 ORM 临时属性跨线程丢失
    threading.Thread(target=_run_summary_only, args=(app_obj, item.id, model_id), daemon=True).start()
    return jsonify({'code': 0, 'message': '正在重新生成总结（与 ASR 服务独立）...', 'data': {'audio_status': 'summarizing'}})


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/cancel', methods=['POST'])
@dual_login_required
@visitor_block
def cancel_audio_processing(item_id):
    """取消正在进行的识别/总结任务"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    # 设置内存取消事件 (同 worker 立即生效)
    with _TASK_CANCEL_LOCK:
        ev = _TASK_CANCEL_EVENTS.get(item_id)
        if ev is None:
            ev = threading.Event()
            _TASK_CANCEL_EVENTS[item_id] = ev
        ev.set()
    # 同时标记 DB (跨 worker 生效)
    if item.audio_status in ('asr_processing', 'summarizing'):
        item.audio_status = 'cancelled'
        item.audio_summary = '处理已取消'
        db.session.commit()
    return jsonify({'code': 0, 'message': '已取消处理', 'data': {'audio_status': 'cancelled'}})


# ======================== 删除单个文件 ========================


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/<int:file_index>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_audio_file(item_id, file_index):
    """删除单个录音文件"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    files = _get_audio_files(item)
    if file_index < 0 or file_index >= len(files):
        return jsonify({'code': 1, 'message': '文件索引无效'}), 400

    removed = files.pop(file_index)

    try:
        abs_path = _resolve_audio_path_by_url(removed['url'])
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
        _set_audio_files(item, files)
        item.audio_duration = sum(f.get('duration', 0) for f in files)

    db.session.commit()
    return jsonify({'code': 0, 'message': '文件已删除', 'data': {'audio_files': files}})


# ======================== 编辑 ========================


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/transcript', methods=['PUT'])
@dual_login_required
@visitor_block
def update_audio_transcript(item_id):
    """手动编辑转写文本或总结"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    files = _get_audio_files(item)
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


# ======================== 全部删除 ========================


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_audio(item_id):
    """删除所有录音文件、压缩包及转写/总结数据"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    files = _get_audio_files(item)
    if not files:
        return jsonify({'code': 1, 'message': '该台账没有录音文件'}), 400

    for af in files:
        try:
            abs_path = _resolve_audio_path_by_url(af['url'])
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except OSError:
            pass

    if item.audio_archive:
        try:
            archive_rel = item.audio_archive.lstrip('/')
            archive_abs = os.path.join(os.path.dirname(Config.UPLOAD_FOLDER), archive_rel)
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


# ======================== 夜间压缩 ========================


@admin_activity_ledger_audio_bp.route('/admin/audio/compress-night', methods=['POST'])
@dual_login_required
@visitor_block
def compress_night():
    """手动触发夜间压缩"""
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
        return jsonify({'code': 1, 'message': '压缩任务失败：' + str(e)}), 500


# ===================== V15.1 结构化总结端点 ========================


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/versions', methods=['GET'])
@dual_login_required
def get_audio_versions(item_id):
    """获取结构化总结多版本数据"""
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
    """下载结构化总结 docx 文件"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    if not item.audio_docx_path:
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
