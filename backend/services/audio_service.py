"""
录音处理共享 service 层（V15.1 组件化）

可供任意模块复用：
  - 活动台账 (ActivityLedger.admin_activity_ledger_audio)
  - 招商动态 (InvestmentActivity.admin_activity_audio)
  - 其他未来模块

核心设计：
- 取消注册表按 (model_class, item_id) 键控，不同模型互不干扰
- 所有 worker 函数接受 model_class + item_id，通过 getattr 读写字段（字段名已对齐）
- 调用方需要在本模块初始化时调用 register_audio_model 注册自己的字段名配置
"""
import os
import json
import time as _time
import logging
import threading
from typing import Optional

# ---------------------------------------------------------------------------
# 字段注册表：{ModelClass: {"files": "audio_files", "status": "audio_status", ...}}
# ---------------------------------------------------------------------------
_FIELD_REGISTRY: dict[type, dict[str, str]] = {}
_CANCEL_EVENTS: dict[tuple[type, int], threading.Event] = {}
_CANCEL_LOCK = threading.Lock()

logger = logging.getLogger(__name__)


def register_audio_model(model_class: type, fields: dict[str, str]):
    """注册一个模型的音频字段名映射（在模块加载时调用一次）"""
    _FIELD_REGISTRY[model_class] = fields


def _fields(item) -> dict[str, str]:
    """获取 item 对应的字段名映射"""
    mc = type(item)
    if mc not in _FIELD_REGISTRY:
        raise RuntimeError(f"模型 {mc.__name__} 未注册音频字段。请先调用 register_audio_model()。")
    return _FIELD_REGISTRY[mc]


# ---------------------------------------------------------------------------
# 取消控制
# ---------------------------------------------------------------------------

def is_task_cancelled(model_class: type, item_id: int) -> bool:
    """检查任务是否被取消（内存 + DB 双源）"""
    with _CANCEL_LOCK:
        ev = _CANCEL_EVENTS.get((model_class, item_id))
        if ev is not None:
            return ev.is_set()
    try:
        from extensions import db
        item = db.session.get(model_class, item_id)
        return item is not None and getattr(item, _fields(item)["status"]) == "cancelled"
    except Exception:
        return False


def register_cancel(model_class: type, item_id: int):
    """注册取消事件"""
    with _CANCEL_LOCK:
        ev = _CANCEL_EVENTS.get((model_class, item_id))
        if ev is None:
            ev = threading.Event()
            _CANCEL_EVENTS[(model_class, item_id)] = ev
        ev.set()


def clear_cancel(model_class: type, item_id: int):
    """清理取消事件"""
    with _CANCEL_LOCK:
        _CANCEL_EVENTS.pop((model_class, item_id), None)


# ---------------------------------------------------------------------------
# audio_files 读写
# ---------------------------------------------------------------------------

def get_audio_files(item) -> list:
    """解析 audio_files JSON"""
    f = _fields(item)
    return json.loads(getattr(item, f["files"]) or "[]")


def set_audio_files(item, files_list: list):
    """写入 audio_files JSON"""
    f = _fields(item)
    setattr(item, f["files"], json.dumps(files_list, ensure_ascii=False))


def resolve_audio_path_by_url(url: str) -> str:
    """根据文件 URL 解析文件绝对路径"""
    from config import Config
    file_rel = url.lstrip('/')
    project_root = os.path.dirname(os.path.dirname(Config.UPLOAD_FOLDER))
    return os.path.join(project_root, file_rel)


# ---------------------------------------------------------------------------
# 进度与预估
# ---------------------------------------------------------------------------

def estimate_time(duration_s: float, transcript_chars: int) -> int:
    """预估完成时间（秒）。"""
    if not duration_s and not transcript_chars:
        return 60
    asr = (duration_s or 0) * 8
    llm = (transcript_chars or 0) * 0.003
    overhead = 30
    return int(asr + llm + overhead)


# ---------------------------------------------------------------------------
# 核心 worker：ASR + 总结（共用）
# ---------------------------------------------------------------------------

def run_async_processing(app, model_class: type, item_id: int):
    """
    后台线程：对 audio_files 逐个 ASR 转写 → 实时更新进度 → 完成后自动总结。
    已识别的段 (status === 'ok') 保留不覆盖。
    """
    with app.app_context():
        try:
            logger.info(f'后台转写线程启动：{model_class.__name__} {item_id}')
            from extensions import db
            item = db.session.get(model_class, item_id)
            if not item:
                logger.error(f'后台处理：{model_class.__name__} {item_id} 不存在')
                return

            files = get_audio_files(item)
            if not files:
                _set_status_failed(item, '处理失败：没有录音文件')
                return

            from services.speech_to_text import transcribe_audio, check_asr_health

            if not check_asr_health():
                # 转写阶段失败：明确为 asr_failed，区别于总结阶段的 summary_failed
                _set_status(item, 'asr_failed', 0, '录音转写服务未启动，请联系管理员苏铎')
                setattr(item, _fields(item)["summary"], '录音转写服务未启动，请联系管理员苏铎')
                try:
                    db.session.commit()
                except Exception:
                    pass
                return

            f = _fields(item)
            _set_status(item, 'asr_processing', 0, '转写准备中...')

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

            def _update_progress(done=None, total=None):
                nonlocal slices_completed
                slices_completed += 1
                pct = int(slices_completed / total_slices * 100) if total_slices > 0 else 0
                pw = _fields(item)
                setattr(item, pw["pct"], min(pct, 99))
                elapsed = _time.time() - start_time
                if slices_completed > 0 and elapsed > 1:
                    avg = elapsed / slices_completed
                    remaining = max(1, int(avg * (total_slices - slices_completed)) // 60)
                    msg = f'正在识别 ({slices_completed}/{total_slices} 段) · 约 {remaining} 分钟'
                else:
                    msg = f'正在识别 ({slices_completed}/{total_slices} 段)...'
                setattr(item, pw["message"], msg)
                try:
                    db.session.commit()
                except Exception:
                    pass

            for i, af in enumerate(files):
                if is_task_cancelled(model_class, item_id):
                    _set_status(item, 'cancelled', None, '处理已取消')
                    return

                if af.get('status') == 'ok' and i in _transcript_cache:
                    slices_completed += file_slice_counts[i]
                    all_texts.append(_transcript_cache[i])
                    continue

                file_path = resolve_audio_path_by_url(af['url'])
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
                    logger.error(f'单文件转写失败：{af["name"]} ({file_path})，错误：{e}', exc_info=True)
                    total_err += 1
                    slices_completed += file_slice_counts[i]
                    all_texts.append(f'[识别失败：{af["name"]}]')
                    set_audio_files(item, files)

            # 拼接全文
            full_text_parts = []
            for i, af in enumerate(files):
                if all_texts[i]:
                    full_text_parts.append(f'【{af["name"]}】\n{all_texts[i]}')

            full_text = '\n\n---\n\n'.join(full_text_parts)

            setattr(item, f["transcript"], full_text)
            db.session.commit()

            # 全部文件转写失败：归为 asr_failed（而非被占位符误报为 asr_completed）。
            # 仅当 total_ok == 0 时判定失败；部分成功仍走 asr_completed。
            if total_ok == 0:
                first_err = ''
                for af in files:
                    if af.get('status') == 'error' and af.get('error'):
                        first_err = af['error']
                        break
                err_msg = first_err or '录音转写失败（所有文件均未识别成功）'
                setattr(item, f["status"], 'asr_failed')
                setattr(item, f["pct"], 0)
                setattr(item, f["message"], f'识别失败 ({total_ok}/{total_files} 文件)')
                setattr(item, f["summary"],
                        err_msg if '请联系管理员苏铎' in err_msg else f'识别失败：{err_msg[:300]}')
                db.session.commit()
                return

            # 解耦：转写完成即结束，总结交由前端“重新总结”按钮独立触发。
            # 状态停在 asr_completed，不再自动串联总结，
            # 以避免“总结失败”被误报为“识别失败”（两者失败语义已分离：
            # 转写失败 = asr_failed，总结失败 = summary_failed）。
            if full_text.strip():
                setattr(item, f["status"], 'asr_completed')
                setattr(item, f["pct"], 100)
                setattr(item, f["message"], f'转写完成 ({total_ok}/{total_files} 文件)，请点击“重新总结”')
                # V16.0 修复：清除上一轮失败/旧总结残留，避免界面把旧错误文本误显示成“失败”
                setattr(item, f["summary"], '')
                setattr(item, f["segmented"], '')
                setattr(item, f["clean"], '')
                setattr(item, f["structured"], '')
                setattr(item, f["docx_path"], '')
                setattr(item, f["docx_size"], 0)
            else:
                setattr(item, f["status"], 'completed')
                setattr(item, f["pct"], 100)
                setattr(item, f["message"], '处理完成（转写内容为空）')
                setattr(item, f["summary"], '转写内容为空，无法生成总结')
            db.session.commit()

        except BaseException as e:
            logger.error(f'后台处理失败（含 BaseException）：{model_class.__name__} {item_id}, 错误：{e}', exc_info=True)
            try:
                from extensions import db
                item = db.session.get(model_class, item_id)
                if item:
                    err_msg = str(e)[:500]
                    # 转写阶段未捕获异常：归为 asr_failed
                    setattr(item, _fields(item)["status"], 'asr_failed')
                    setattr(item, _fields(item)["summary"],
                            err_msg if '请联系管理员苏铎' in err_msg else f'处理失败：{err_msg}')
                    db.session.commit()
            except Exception:
                pass


def run_summary_only(app, model_class: type, item_id: int, model_id: int = None):
    """仅重新生成结构化总结（基于现有 audio_transcript）。"""
    with app.app_context():
        from extensions import db
        item = db.session.get(model_class, item_id)
        if not item:
            return
        if is_task_cancelled(model_class, item_id):
            setattr(item, _fields(item)["status"], 'cancelled')
            db.session.commit()
            return
        f = _fields(item)
        setattr(item, f["status"], 'summarizing')
        setattr(item, f["message"], '正在总结...')
        db.session.commit()
        try:
            apply_summary_to_item(item, getattr(item, f["transcript"]) or '', model_id=model_id)
            setattr(item, f["status"], 'completed')
            setattr(item, f["pct"], 100)
            setattr(item, f["message"], '处理完成')
            db.session.commit()
        except Exception as e:
            setattr(item, f["summary"], f'总结失败: {str(e)[:200]}')
            setattr(item, f["status"], 'summary_failed')
            db.session.commit()


def apply_summary_to_item(item, full_text: str, model_id: int = None):
    """对 item 生成结构化总结 (segmented + clean + summary + docx)"""
    from services.text_summarizer import summarize_meeting
    from services.meeting_document import generate_meeting_docx

    f = _fields(item)

    logger.info(f'后台结构化总结开始：{type(item).__name__} id={item.id}，{len(full_text)} 字，model_id={model_id}')
    try:
        summary_result = summarize_meeting(full_text, model_id=model_id)
        setattr(item, f["segmented"], summary_result.get('segmented', ''))
        setattr(item, f["clean"], summary_result.get('clean', ''))
        setattr(item, f["structured"], summary_result.get('summary', ''))
        try:
            docx_url, docx_abs = generate_meeting_docx(
                activity=item,
                segmented_text=summary_result.get('segmented', ''),
                clean_text=summary_result.get('clean', ''),
                summary_text=summary_result.get('summary', '')
            )
            setattr(item, f["docx_path"], docx_url)
            # docx_abs 已由 generate_meeting_docx 返回（基于 current_app.static_folder，
            # 即 Flask 实际提供 /static 的目录，避免从 backend 目录推导导致的路径偏差）
            if docx_abs and os.path.exists(docx_abs):
                setattr(item, f["docx_size"], os.path.getsize(docx_abs))
        except Exception as docx_err:
            logger.error(f'docx generation failed: {docx_err}', exc_info=True)
        setattr(item, f["summary"], summary_result.get('summary', ''))
        from extensions import db
        db.session.commit()
        logger.info(f'后台结构化总结完成：{type(item).__name__} id={item.id}')
    except Exception as e:
        logger.error(f'summary failed: {e}', exc_info=True)
        setattr(item, f["summary"], f'总结失败: {str(e)[:200]}')
        setattr(item, f["status"], 'summary_failed')
        db.session.commit()


# ---------------------------------------------------------------------------
# 私有辅助
# ---------------------------------------------------------------------------

def _set_status(item, status: str, pct: Optional[int], message: Optional[str]):
    f = _fields(item)
    setattr(item, f["status"], status)
    if pct is not None:
        setattr(item, f["pct"], pct)
    if message is not None:
        setattr(item, f["message"], message)
    from extensions import db
    db.session.commit()


def _set_status_failed(item, summary_msg: str):
    f = _fields(item)
    setattr(item, f["status"], 'failed')
    setattr(item, f["summary"], summary_msg)
    setattr(item, f["message"], None)
    setattr(item, f["pct"], 0)
    from extensions import db
    db.session.commit()
