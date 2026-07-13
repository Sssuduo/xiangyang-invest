"""
活动台账 - 录音文件上传 API

流程：
1. 上传：支持多个录音文件，逐个保存 → 逐个 ASR 转写 → 拼接全文 → LLM 总结
2. 夜间定时：压缩所有音频文件为 zip 下载包
3. 失败重试：POST /audio/retry 重新调用识别接口

多文件结构：
- audio_files JSON 数组：[{url, name, duration, size, status: 'ok'|'error', error: ''}, ...]
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
# 调用 cancel 接口会设置 event, 线程定期检查并提前退出
import threading as _threading
_TASK_CANCEL_EVENTS: dict[int, _threading.Event] = {}
_TASK_CANCEL_LOCK = _threading.Lock()


def _is_task_cancelled(item_id: int) -> bool:
    """检查任务是否被取消。优先查内存注册表，回退查 DB 状态 (多 worker 安全)"""
    with _TASK_CANCEL_LOCK:
        ev = _TASK_CANCEL_EVENTS.get(item_id)
        if ev is not None:
            return ev.is_set()
    # 回退: 查 DB (跨 worker)
    try:
        item = ActivityLedger.query.get(item_id)
        return item is not None and item.audio_status == 'cancelled'
    except Exception:
        return False


def _wait_or_cancel(item_id: int, timeout: float = 1.0) -> bool:
    """等待 timeout 秒或直到取消。返回 True 表示被取消。"""
    with _TASK_CANCEL_LOCK:
        ev = _TASK_CANCEL_EVENTS.get(item_id)
        if ev is None:
            ev = _threading.Event()
            _TASK_CANCEL_EVENTS[item_id] = ev
    return ev.wait(timeout=timeout)


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
    """根据文件 URL 解析文件绝对路径。

    DB 里 URL 形如 /static/uploads/audio/20260712_xxx.mp3。
    直接派生自 Config.UPLOAD_FOLDER：
        UPLOAD_FOLDER = <project_root>/static/uploads
        dirname(dirname(UPLOAD_FOLDER)) = <project_root>
    加 url.lstrip('/') 拼接得到正确绝对路径，避免早年旧代码中
    "static/static/uploads" 重复拼接导致录音文件找不到、状态被标记 error。
    """
    file_rel = url.lstrip('/')
    project_root = os.path.dirname(os.path.dirname(Config.UPLOAD_FOLDER))
    return os.path.join(project_root, file_rel)


def _run_async_processing(app, item_id):
    """
    后台线程：对 audio_files 中所有文件逐个 ASR 转写 → 拼接 → LLM 总结
    """
    import logging
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

            from services.speech_to_text import transcribe_audio

            all_texts = []
            total_ok = 0
            total_err = 0
            # 内存中转写缓存：status==='ok' 时，记录转写文本供本轮后续文件复用；不落 JSON
            _transcript_cache = {}

            for i, af in enumerate(files):
                # 检查是否被取消 (在每段处理前)
                if _is_task_cancelled(item_id):
                    logger.info(f'后台 ASR 已取消：item_id={item_id}，段 [{i+1}/{len(files)}] 前停止')
                    # 回退已成功转写的文件状态标记
                    item.audio_status = 'cancelled'
                    item.audio_summary = '处理已取消'
                    db.session.commit()
                    return

                if af.get('status') == 'ok' and i in _transcript_cache:
                    all_texts.append(_transcript_cache[i])
                    continue  # 已成功识别过的跳过（重试场景复用旧转写）

                file_path = _resolve_audio_path_by_url(af['url'])
                if not os.path.exists(file_path):
                    af['status'] = 'error'
                    af['error'] = '文件不存在'
                    total_err += 1
                    all_texts.append('')
                    continue

                logger.info(f'后台 ASR [{i + 1}/{len(files)}]：{af["name"]}')
                try:
                    asr_result = transcribe_audio(file_path)
                    text = asr_result['text']
                    af['status'] = 'ok'
                    af['error'] = ''
                    af['_transcript'] = text  # 临时保存，JSON 持久化前需 strip
                    _transcript_cache[i] = text
                    all_texts.append(text)
                    total_ok += 1
                    # 逐个保存进度；持久化前 strip 掉 _transcript，避免污染 audio_files JSON
                    af.pop('_transcript', None)
                    _set_audio_files(item, files)
                    db.session.commit()
                    logger.info(f'后台 ASR [{i + 1}/{len(files)}] 完成：{len(text)} 字')
                except Exception as e:
                    logger.error(f'后台 ASR [{i + 1}/{len(files)}] 失败：{e}')
                    af['status'] = 'error'
                    af['error'] = str(e)[:300]
                    total_err += 1
                    all_texts.append(f'[识别失败：{af["name"]}]')

            # 拼接全文
            full_text_parts = []
            for i, af in enumerate(files):
                if all_texts[i]:
                    full_text_parts.append(f'【{af["name"]}】\n{all_texts[i]}')

            separator = '\n\n---\n\n'
            full_text = separator.join(full_text_parts)
            item.audio_transcript = full_text
            db.session.commit()

            # V15.0: 结构化总结 (委托给 _run_summary_only)
            if full_text.strip():
                _apply_summary_to_item(item, full_text)
            else:
                item.audio_transcript_segmented = ''
                item.audio_transcript_clean = ''
                item.audio_summary_structured = ''
                item.audio_summary = '（转写内容为空，无法生成总结）'

            item.audio_status = 'completed'
            db.session.commit()
            logger.info(f'后台处理完成：item_id={item_id}，{len(files)}个文件，{total_ok}成功/{total_err}失败')

        except Exception as e:
            logger.error(f'后台处理失败：item_id={item_id}，错误：{e}', exc_info=True)
            try:
                item = ActivityLedger.query.get(item_id)
                if item:
                    item.audio_status = 'failed'
                    err_msg = str(e)[:500]
                    # 已是统一中文 message 则原样；否则包装一层通用兜底
                    item.audio_summary = err_msg if '请联系管理员苏铎' in err_msg else f'处理失败：{err_msg}'
                    db.session.commit()
            except Exception:
                pass


def _run_summary_only(app, item_id):
    """后台线程入口: 仅跑 summary pass (基于现有 audio_transcript)。"""
    with app.app_context():
        from models import ActivityLedger
        from services.term_correction import apply_corrections
        item = ActivityLedger.query.get(item_id)
        if not item:
            return
        # 检查是否已被取消
        if _is_task_cancelled(item_id):
            logger.info(f'总结任务已取消: item_id={item_id}')
            item.audio_status = 'cancelled'
            item.audio_summary = '处理已取消'
            from extensions import db
            db.session.commit()
            return
        clean_transcript, _ = apply_corrections(item.audio_transcript or '', 'clean')
        try:
            _apply_summary_to_item(item, clean_transcript)
        except Exception as e:
            item.audio_summary = f'总结失败: {str(e)[:200]}'
            from extensions import db
            db.session.commit()
        finally:
            from extensions import db
            item.audio_status = 'completed'
            db.session.commit()


def _apply_summary_to_item(item, full_text):
    """对台账 item 生成结构化总结 (segmented + clean + summary + docx)。可独立调用用于 resume。"""
    import logging, os
    logger = logging.getLogger(__name__)
    from services.text_summarizer import summarize_meeting, summarize_with_llm
    from services.meeting_document import generate_meeting_docx

    logger.info(f'后台结构化总结开始：item_id={item.id}，{len(full_text)} 字')
    try:
        summary_result = summarize_meeting(full_text)
        item.audio_transcript_segmented = summary_result.get('segmented', '')
        item.audio_transcript_clean = summary_result.get('clean', '')
        item.audio_summary_structured = summary_result.get('summary', '')
        # 生成 docx
        try:
            docx_url, docx_name = generate_meeting_docx(
                activity=item,
                segmented_text=summary_result.get('segmented', ''),
                clean_text=summary_result.get('clean', ''),
                summary_text=summary_result.get('summary', '')
            )
            item.audio_docx_path = docx_url
            # 计算文件大小
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
        logger.info(f'后台结构化总结完成：segmented={len(summary_result.get("segmented",""))} clean={len(summary_result.get("clean",""))} summary={len(summary_result.get("summary",""))} docx={item.audio_docx_path or "none"}')
    except Exception as e:
        logger.error(f'meeting summary generation failed: {e}', exc_info=True)
        item.audio_transcript_segmented = ''
        item.audio_transcript_clean = ''
        item.audio_summary_structured = ''
        item.audio_summary = f'（结构化总结生成失败：{str(e)[:200]}）'
        # 保留旧版 V14 单版作为兜底
        try:
            item.audio_summary = summarize_with_llm(full_text)
        except Exception:
            pass


def _apply_terminology_and_regenerate(item, user=None):
    """应用术语校正到该台账的总结字段，并重新结构化。

    流程:
      1) 用 TermCorrection 表替换 segmented/clean/summary 里的词汇
      2) 对替换后的 summary 再做一次结构化调用 (或直接保留原结构化结果)
      3) 更新 DB
    """
    from services.term_correction import apply_corrections
    if not item.audio_transcript:
        return
    # 应用术语校正到清洁版/摘要版
    seg_text, _ = apply_corrections(item.audio_transcript_segmented or '', 'segmented')
    clean_text, _ = apply_corrections(item.audio_transcript_clean or '', 'clean')
    summary_text, _ = apply_corrections(item.audio_summary_structured or '', 'summary')
    item.audio_transcript_segmented = seg_text
    item.audio_transcript_clean = clean_text
    item.audio_summary_structured = summary_text
    item.audio_summary = summary_text or item.audio_summary
    db.session.commit()


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
    """预估完成时间（秒）。

    实测经验:
      - ASR 约 8x 实时 (CPU SenseVoice 推理)
      - LLM 总结约 0.003 秒/字
      - docx 生成 + 网络抖动 ≈ 30s
    """
    if not duration_s and not transcript_chars:
        return 60
    asr = (duration_s or 0) * 8
    llm = (transcript_chars or 0) * 0.003
    overhead = 30
    return int(asr + llm + overhead)


# ======================== 上传 ========================


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio', methods=['POST'])
@dual_login_required
@visitor_block
def upload_audio(item_id):
    """
    上传录音文件（支持多文件，异步处理）

    多文件可以一次上传多个（前端逐次调用），也可以多次调用逐个追加。
    每次上传的文件加入 audio_files 列表，全部上传完成后自动开始处理。

    Form Data:
        file: 录音文件（wav, mp3, m4a, ogg, flac, wma, aac, amr, opus, weba）
        append: 追加模式（可选，"true"=保留已有文件追加）

    Returns:
        JSON: { code: 0, data: { audio_files, audio_status: 'processing', ... } }
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

        # 直接保存原始文件
        from services.audio_compressor import save_original_audio
        save_result = save_original_audio(tmp_path, upload_dir)

        # 构建文件条目
        new_file_entry = {
            'url': save_result['relative_url'],
            'name': file.filename,
            'duration': save_result['duration'],
            'size': save_result['file_size'],
            'status': 'pending',
            'error': ''
        }

        # 获取已有文件列表
        append_mode = request.form.get('append', 'false') == 'true'
        existing = _get_audio_files(item) if append_mode else []
        existing.append(new_file_entry)
        _set_audio_files(item, existing)

        # 计算总时长
        total_duration = sum(f.get('duration', 0) for f in existing)

        # 设置状态
        item.audio_archive = None
        item.audio_archive_size = None
        item.audio_status = 'processing'
        item.audio_duration = total_duration
        item.audio_transcript = None
        item.audio_summary = None
        db.session.commit()

        # 启动后台处理
        app = current_app._get_current_object()
        thread = threading.Thread(
            target=_run_async_processing,
            args=(app, item_id),
            daemon=True
        )
        thread.start()

        return jsonify({
            'code': 0,
            'message': '录音已上传，正在后台处理...',
            'data': {
                'audio_files': existing,
                'audio_status': 'processing',
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
    """
    批量上传多个录音文件

    Form Data:
        files: 多个录音文件（使用 HTML5 multiple）

    Returns:
        JSON: { code: 0, data: { audio_files, audio_status, ... } }
    """
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    uploaded = request.files.getlist('files')
    if not uploaded:
        return jsonify({'code': 1, 'message': '请选择录音文件'}), 400

    import uuid
    upload_dir = Config.UPLOAD_FOLDER
    os.makedirs(upload_dir, exist_ok=True)

    existing = _get_audio_files(item)
    saved_files = []
    errors = []

    for file in uploaded:
        if not file or not file.filename:
            continue
        if not _allowed_audio(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else '未知'
            errors.append(f'{file.filename}：不支持的格式 .{ext}')
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
            errors.append(f'{file.filename}：{str(e)[:100]}')
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    if not saved_files:
        return jsonify({'code': 1, 'message': f'所有文件上传失败：{"; ".join(errors)}'}), 400

    _set_audio_files(item, existing)
    total_duration = sum(f.get('duration', 0) for f in existing)

    item.audio_archive = None
    item.audio_archive_size = None
    item.audio_status = 'processing'
    item.audio_duration = total_duration
    item.audio_transcript = None
    item.audio_summary = None
    db.session.commit()

    # 启动后台处理
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_run_async_processing,
        args=(app, item_id),
        daemon=True
    )
    thread.start()

    msg = f'{len(saved_files)} 个文件已上传'
    if errors:
        msg += f'，{len(errors)} 个失败：{"; ".join(errors[:3])}'

    return jsonify({
        'code': 0,
        'message': msg,
        'data': {
            'audio_files': existing,
            'audio_status': 'processing',
            'audio_duration': total_duration,
            'errors': errors
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
        # V15.1: 结构化总结预估耗时 (秒)
        'estimated_summary_seconds': _estimate_time(item.audio_duration, len(item.audio_transcript or '')),
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


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/retry-summary', methods=['POST'])
@dual_login_required
@visitor_block
def retry_audio_summary(item_id):
    """单独重新生成结构化总结（基于现有 audio_transcript，不重跑 ASR）"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    if not item.audio_transcript:
        return jsonify({'code': 1, 'message': '没有转写内容，请先完成识别后重试'}), 400

    # 应用术语校正后的转写文本作为 summary 输入
    clean_transcript, _ = _apply_corrections_text(item.audio_transcript, 'clean')

    item.audio_status = 'processing'
    db.session.commit()

    # 拉起后台线程跑 summary pass
    app_obj = current_app._get_current_object()
    threading.Thread(target=_run_summary_only, args=(app_obj, item.id), daemon=True).start()
    return jsonify({'code': 0, 'message': '正在重新生成总结...', 'data': {'audio_status': 'processing'}})


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
            ev = _threading.Event()
            _TASK_CANCEL_EVENTS[item_id] = ev
        ev.set()
    # 同时标记 DB (跨 worker 生效)
    if item.audio_status == 'processing':
        item.audio_status = 'cancelled'
        item.audio_summary = '处理已取消'
        db.session.commit()
    return jsonify({'code': 0, 'message': '已取消处理', 'data': {'audio_status': 'cancelled'}})

# ======================== 核心处理逻辑 ========================

    # 应用术语校正后的转写文本作为 summary 输入
    clean_transcript, _ = _apply_corrections_text(item.audio_transcript, 'clean')

    item.audio_status = 'processing'
    db.session.commit()

    # 拉起后台线程跑 summary pass
    app_obj = current_app._get_current_object()
    threading.Thread(target=_run_summary_only, args=(app_obj, item.id), daemon=True).start()
    return jsonify({'code': 0, 'message': '正在重新生成总结...', 'data': {'audio_status': 'processing'}})


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/retry', methods=['POST'])
@dual_login_required
@visitor_block
def retry_audio_recognition(item_id):
    """重新调用语音识别"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    files = _get_audio_files(item)
    if not files:
        return jsonify({'code': 1, 'message': '没有录音文件，无法重新识别'}), 400

    # 重置所有文件状态
    for af in files:
        af['status'] = 'pending'
        af['error'] = ''
        af.pop('_transcript', None)

    _set_audio_files(item, files)
    item.audio_status = 'processing'
    item.audio_transcript = None
    item.audio_summary = None
    db.session.commit()

    app = current_app._get_current_object()
    threading.Thread(target=_run_async_processing, args=(app, item_id), daemon=True).start()

    return jsonify({
        'code': 0,
        'message': '已重新开始语音识别，请等待处理完成...',
        'data': {'audio_status': 'processing'}
    })


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

    # 删除磁盘文件
    try:
        abs_path = _resolve_audio_path_by_url(removed['url'])
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except OSError:
        pass

    if not files:
        # 清空所有音频数据
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
    """
    手动编辑转写文本或总结

    JSON Body:
        transcript: str   # （可选）新的转写文本
        summary: str       # （可选）新的总结文本

    Returns:
        JSON: { code: 0, message: '...' }
    """
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

    # 删除所有原始文件
    for af in files:
        try:
            abs_path = _resolve_audio_path_by_url(af['url'])
            if os.path.exists(abs_path):
                os.remove(abs_path)
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
        return jsonify({'code': 1, 'message': f'压缩任务失败：{str(e)}'}), 500


# ===================== V15.0 结构化总结端点 ========================


@admin_activity_ledger_audio_bp.route('/activity-ledger/<int:item_id>/audio/versions', methods=['GET'])
@dual_login_required
def get_audio_versions(item_id):
    """获取结构化总结多版本数据

    Returns:
        JSON: { code:0, data: { transcript, transcript_segmented, transcript_clean, summary_structured, docx_path, docx_size } }
    """
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
    from flask import send_from_directory
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    if not item.audio_docx_path:
        return jsonify({'code': 1, 'message': '尚未生成 Word 文档，请等待处理完成或重新识别'}), 404
    docx_abs = os.path.join(
        os.path.dirname(current_app.instance_path), '..',
        'static', item.audio_docx_path.replace('/static/', '')
    )
    if not os.path.exists(docx_abs):
        return jsonify({'code': 1, 'message': 'Word 文件不存在，请重新生成'}), 404
    dir_name = os.path.dirname(docx_abs)
    basename = os.path.basename(docx_abs)
    return send_from_directory(dir_name, basename, as_attachment=True)
