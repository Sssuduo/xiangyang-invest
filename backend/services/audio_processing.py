"""
录音处理通用服务
供活动台账 / 招商动态等实体复用
"""
import os
import json
import logging
import threading
import time as _time
from datetime import datetime

logger = logging.getLogger(__name__)

# 取消注册表 {item_id: threading.Event}
_TASK_CANCEL_EVENTS: dict[int, threading.Event] = {}
_TASK_CANCEL_LOCK = threading.Lock()


def is_task_cancelled(item_id: int, model_class=None) -> bool:
    """检查任务是否被取消。优先查内存注册表，回退查 DB 状态（V15.1 对齐活动台账双源检查）。"""
    with _TASK_CANCEL_LOCK:
        ev = _TASK_CANCEL_EVENTS.get(item_id)
        if ev is not None:
            return ev.is_set()
    # DB 回退：避免内存注册表因重启/多 worker 丢失取消信号
    if model_class is not None:
        try:
            item = model_class.query.get(item_id)
            return item is not None and getattr(item, 'audio_status', None) == 'cancelled'
        except Exception:
            return False
    return False


def register_cancel(item_id: int):
    with _TASK_CANCEL_LOCK:
        ev = _TASK_CANCEL_EVENTS.get(item_id)
        if ev is None:
            ev = threading.Event()
            _TASK_CANCEL_EVENTS[item_id] = ev
        ev.set()


def clear_cancel(item_id: int):
    with _TASK_CANCEL_EVENTS.pop(item_id, None):
        pass


def get_audio_files(item):
    return json.loads(item.audio_files or '[]')


def set_audio_files(item, files_list):
    item.audio_files = json.dumps(files_list, ensure_ascii=False)


def resolve_audio_path_by_url(url, app):
    file_rel = url.lstrip('/')
    project_root = os.path.dirname(os.path.dirname(app.config['UPLOAD_FOLDER']))
    return os.path.join(project_root, file_rel)


def estimate_time(duration_s, transcript_chars):
    if not duration_s and not transcript_chars:
        return 60
    asr = (duration_s or 0) * 8
    llm = (transcript_chars or 0) * 0.003
    return int(asr + llm + 30)


def run_async_processing(app, item_id, model_class, model_id: int = None):
    """
    后台线程：对 item.audio_files 逐个 ASR 转写 → 实时更新进度 → 完成后自动总结。
    model_class: ActivityLedger 或 InvestmentActivity 等模型类。
    model_id: 可选，LLM 模型 ID（V15.1 retry-summary 透传，None 则 _apply_summary 自动选默认模型）。
    """
    from extensions import db
    from models import InvestmentActivity  # 避免循环导入

    with app.app_context():
        try:
            item = model_class.query.get(item_id)
            if not item:
                logger.error(f'后台处理：{item_class.__name__} {item_id} 不存在')
                return

            files = get_audio_files(item)
            if not files:
                item.audio_status = 'failed'
                item.audio_summary = '处理失败：没有录音文件'
                db.session.commit()
                return

            from services.speech_to_text import transcribe_audio, check_asr_health

            if not check_asr_health():
                item.audio_status = 'failed'
                item.audio_summary = '录音转写服务未启动，请联系管理员苏铎'
                item.progress_message = None
                item.progress_pct = 0
                db.session.commit()
                return

            item.audio_status = 'asr_processing'
            item.progress_message = '转写准备中...'
            item.progress_pct = 0
            db.session.commit()

            all_texts = []
            total_ok = 0
            total_err = 0
            _transcript_cache = {}
            total_files = len(files)

            # 预计算切片数
            SLICE_DURATION = 30
            file_slice_counts = []
            for af in files:
                dur = af.get('duration') or 0
                slices = max(1, int(dur + SLICE_DURATION - 1) // SLICE_DURATION) if dur > 0 else 1
                file_slice_counts.append(slices)
            total_slices = sum(file_slice_counts)
            slices_completed = 0
            start_time = _time.time()

            def _update_progress():
                nonlocal slices_completed
                slices_completed += 1
                pct = int(slices_completed / total_slices * 100) if total_slices > 0 else 0
                item.progress_pct = min(pct, 99)
                elapsed = _time.time() - start_time
                if slices_completed > 0 and elapsed > 1:
                    avg = elapsed / slices_completed
                    remaining = max(1, int(avg * (total_slices - slices_completed)) // 60)
                    item.progress_message = f'正在识别 ({slices_completed}/{total_slices} 段) · 约 {remaining} 分钟'
                else:
                    item.progress_message = f'正在识别 ({slices_completed}/{total_slices} 段)...'
                try:
                    db.session.commit()
                except Exception:
                    pass

            for i, af in enumerate(files):
                if is_task_cancelled(item_id, model_class):
                    item.audio_status = 'cancelled'
                    item.audio_summary = '处理已取消'
                    db.session.commit()
                    return

                if af.get('status') == 'ok' and i in _transcript_cache:
                    slices_completed += file_slice_counts[i]
                    all_texts.append(_transcript_cache[i])
                    continue

                file_path = resolve_audio_path_by_url(af['url'], app)
                if not os.path.exists(file_path):
                    af['status'] = 'error'
                    af['error'] = '文件不存在'
                    total_err += 1
                    slices_completed += file_slice_counts[i]
                    all_texts.append('')
                    continue

                try:
                    asr_result = transcribe_audio(file_path, on_slice_done=_update_progress)
                    text = asr_result['text']
                    af['status'] = 'ok'
                    af['error'] = ''
                    _transcript_cache[i] = text
                    all_texts.append(text)
                    total_ok += 1
                    set_audio_files(item, files)
                except Exception as e:
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
            full_text = '\n\n---\n\n'.join(full_text_parts)

            item.audio_transcript = full_text
            item.audio_status = 'asr_completed'
            item.progress_pct = 100
            item.progress_message = f'识别完成 ({total_ok}/{total_files} 文件)'
            db.session.commit()

            # 自动触发总结
            if full_text.strip():
                item.audio_status = 'summarizing'
                item.progress_message = '正在总结...'
                db.session.commit()
                try:
                    _apply_summary(app, item, full_text, model_id=model_id)
                    item.audio_status = 'completed'
                    item.progress_pct = 100
                    item.progress_message = '处理完成'
                    db.session.commit()
                except Exception as e:
                    item.audio_status = 'summary_failed'
                    item.audio_summary = f'总结失败：{str(e)[:200]}'
                    db.session.commit()
            else:
                item.audio_status = 'completed'
                item.progress_pct = 100
                item.progress_message = '处理完成（转写内容为空）'
                item.audio_summary = '转写内容为空，无法生成总结'
                db.session.commit()

        except Exception as e:
            logger.error(f'后台处理失败：{item_class.__name__} {item_id}, 错误：{e}', exc_info=True)
            try:
                item = model_class.query.get(item_id)
                if item:
                    item.audio_status = 'failed'
                    item.audio_summary = f'处理失败：{str(e)[:500]}'
                    db.session.commit()
            except Exception:
                pass


def _apply_summary(app, item, full_text, model_id=None):
    """生成结构化总结 (V15.1 对齐活动台账：支持 model_id 透传 + 记录 docx 大小)"""
    from extensions import db
    from services.text_summarizer import summarize_meeting
    from services.meeting_document import generate_meeting_docx

    summary_result = summarize_meeting(full_text, model_id=model_id)
    item.audio_transcript_segmented = summary_result.get('segmented', '')
    item.audio_transcript_clean = summary_result.get('clean', '')
    item.audio_summary_structured = summary_result.get('summary', '')
    item.audio_summary = summary_result.get('summary', '')
    # V15.1 记录本次总结使用的 LLM 模型 ID，前端可回填选择器
    if model_id is not None:
        item.summary_model_id = model_id

    # 生成 docx
    try:
        docx_url, _ = generate_meeting_docx(
            activity=item,
            segmented_text=summary_result.get('segmented', ''),
            clean_text=summary_result.get('clean', ''),
            summary_text=summary_result.get('summary', '')
        )
        item.audio_docx_path = docx_url
        # V15.1 记录 docx 文件大小（对齐活动台账 L341-342）
        try:
            docx_abs = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # backend/ → 项目根
                'static', docx_url.replace('/static/', '')
            )
            if os.path.exists(docx_abs):
                item.audio_docx_size = os.path.getsize(docx_abs)
        except Exception:
            pass
    except Exception:
        pass

    db.session.commit()
