"""
术语校正服务 — 文本词汇统一替换。

应用场景:
- 用户将台账总结中的"田勇书记"统一改为"天勇书记"
- 自动应用到清洁版 / 摘要版 / 分段原文所有字段
- 术语表在音频识别时作为知识库注入 prompt，提高 LLM 识别精度
"""
import logging
from extensions import db
from models.term_correction import TermCorrection

logger = logging.getLogger(__name__)


def apply_corrections(text: str, scope: str = 'all') -> tuple[str, int]:
    """应用启用的术语校正, 返回 (替换后文本, 替换次数)。

    Args:
        text: 需要替换的原始文本
        scope: 适用范围 ('all' | 'summary' | 'clean' | 'segmented')
    """
    if not text:
        return text, 0
    try:
        corrections = TermCorrection.query.filter_by(is_active=True).all()
    except Exception as e:
        logger.warning(f'查询术语校正表失败: {e}')
        return text, 0

    result = text
    total = 0
    for c in corrections:
        if scope != 'all' and c.apply_scope not in ('all', scope):
            continue
        if not c.original:
            continue
        # str.replace 全局替换
        before = result
        result = result.replace(c.original, c.replacement or '')
        # 粗略计数
        if c.replacement != c.original:
            count = (len(before) - len(result)) // max(len(c.original) - len(c.replacement), 1)
            total += max(count, 0)
        else:
            total += before.count(c.original)
    return result, total


def get_all_corrections(scope: str = None) -> list[TermCorrection]:
    """列出术语校正。"""
    query = TermCorrection.query
    if scope and scope != 'all':
        query = query.filter((TermCorrection.apply_scope == 'all') | (TermCorrection.apply_scope == scope))
    return query.order_by(TermCorrection.created_at.desc()).all()


def create_or_update_correction(original: str, replacement: str, scope: str = 'all', user: str = None) -> TermCorrection:
    """新建或更新术语校正 (基于 original 唯一)。"""
    original = (original or '').strip()
    replacement = (replacement or '').strip()
    if not original:
        raise ValueError('原文词汇不能为空')
    item = TermCorrection.query.filter_by(original=original).first()
    if item:
        item.replacement = replacement
        item.apply_scope = scope
        if user:
            item.created_by = user
        db.session.commit()
        return item
    item = TermCorrection(
        original=original,
        replacement=replacement,
        apply_scope=scope,
        created_by=user,
    )
    db.session.add(item)
    db.session.commit()
    return item


def apply_corrections_to_item(item, scope: str = 'all') -> int:
    """将术语校正应用到 ActivityLedger 实例的所有总结字段。返回替换总次数。"""
    if not item.audio_transcript:
        return 0
    seg, n1 = apply_corrections(item.audio_transcript_segmented or '', scope)
    clean, n2 = apply_corrections(item.audio_transcript_clean or '', scope)
    summary, n3 = apply_corrections(item.audio_summary_structured or '', scope)
    item.audio_transcript_segmented = seg
    item.audio_transcript_clean = clean
    item.audio_summary_structured = summary
    item.audio_summary = summary or item.audio_summary
    db.session.commit()
    return n1 + n2 + n3
