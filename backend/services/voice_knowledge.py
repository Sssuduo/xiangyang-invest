"""
语音识别知识库服务

核心功能:
1. 同音词检测 (拼音匹配 + 上下文消歧)
2. 知识条目管理 (CRUD + 反馈循环)
3. 文本校正应用 (对文本批量应用已知校正)

拼音匹配策略:
- 精确匹配: original == phrase → 直接替换 (confidence=1.0)
- 同音匹配: pinyin(original) == pinyin(phrase) → 推荐替换 (confidence≥0.85)
- 模糊匹配: 编辑距离 < threshold → 候选提示 (confidence<0.85)

安全机制:
- 置信度分级 (高/中/低)
- 上下文消歧 (检查前后缀)
- 长短语优先 (4字>3字>2字>1字)
"""
import json
import logging
from typing import List, Optional

from extensions import db
from models import VoiceKnowledgeEntry, TextCorrectionRecord

logger = logging.getLogger(__name__)


class VoiceKnowledgeService:
    """语音知识库服务"""

    # 置信度分级阈值
    CONFIDENCE_HIGH = 0.90    # 自动替换
    CONFIDENCE_MEDIUM = 0.75  # 提示确认
    CONFIDENCE_LOW = 0.60     # 仅标记，不替换

    @staticmethod
    def _get_pinyin(text: str) -> List[str]:
        """获取拼音列表 (无声调)"""
        try:
            from pypinyin import lazy_pinyin, Style
            return lazy_pinyin(text, style=Style.NORMAL)
        except ImportError:
            logger.warning('pypinyin 未安装，同音匹配不可用')
            return []

    @classmethod
    def create_entry(cls, original: str, replacement: str,
                     context: str = None, source: str = 'manual',
                     confidence: float = 0.9) -> VoiceKnowledgeEntry:
        """创建知识条目"""
        entry = VoiceKnowledgeEntry(
            original=original,
            replacement=replacement,
            context=context,
            source=source,
            confidence=min(confidence, 0.99),
        )
        entry.refresh_pinyin_cache()
        db.session.add(entry)
        db.session.commit()
        logger.info(f'[VoiceKnowledge] 新增: {original} → {replacement} (置信度 {confidence})')
        return entry

    @classmethod
    def list_active_entries(cls) -> List[VoiceKnowledgeEntry]:
        """列出所有活跃知识条目 (按 usage_count 降序)"""
        return VoiceKnowledgeEntry.query.filter_by(is_active=True)\
            .order_by(VoiceKnowledgeEntry.usage_count.desc()).all()

    @classmethod
    def delete_entry(cls, entry_id: int) -> bool:
        """软删除知识条目"""
        entry = VoiceKnowledgeEntry.query.get(entry_id)
        if not entry:
            return False
        entry.is_active = False
        db.session.commit()
        return True

    @classmethod
    def detect_homophones(cls, text: str,
                          min_confidence: float = 0.75) -> List[dict]:
        """
        检测文本中的同音错字候选。

        算法:
        1. 滑动窗口提取 2~4 字短语
        2. 对每个短语计算拼音
        3. 在知识库中查找拼音匹配的条目
        4. 计算置信度 (精确同音 + 上下文加权 + 频次加权)
        5. 按位置排序返回

        Args:
            text: 待检测文本
            min_confidence: 最低置信度阈值

        Returns:
            [{
                'start': int (字符偏移),
                'end': int,
                'source': str (文本中原始词),
                'target': str (推荐替换词),
                'confidence': float,
                'method': 'exact_homophone' | 'context_match',
                'kb_id': int
            }, ...]
        """
        if not text or len(text) < 2:
            return []

        # 加载活跃知识库 (按 original 长度降序，长短语优先)
        kb_entries = VoiceKnowledgeEntry.query.filter_by(is_active=True)\
            .order_by(db.func.length(VoiceKnowledgeEntry.original).desc()).all()

        if not kb_entries:
            return []

        # 建立拼音索引 (pinyin_str → [entries])
        pinyin_index = {}
        for kb in kb_entries:
            if not kb.pinyin:
                kb.refresh_pinyin_cache()
            try:
                py_list = json.loads(kb.pinyin) if isinstance(kb.pinyin, str) else kb.pinyin
            except (json.JSONDecodeError, TypeError):
                continue
            py_key = ''.join(py_list)  # "huopai"
            if py_key not in pinyin_index:
                pinyin_index[py_key] = []
            pinyin_index[py_key].append(kb)

        # 滑动窗口检测 (4字→3字→2字)
        text_len = len(text)
        results = []
        matched_positions = set()  # 避免重叠

        for window_size in (4, 3, 2):
            for i in range(text_len - window_size + 1):
                # 跳过已匹配位置
                if any(i <= p < i + window_size for p in matched_positions):
                    continue

                phrase = text[i:i + window_size]
                phrase_pinyin = cls._get_pinyin(phrase)
                if not phrase_pinyin:
                    continue
                phrase_py_key = ''.join(phrase_pinyin)

                # 拼音匹配
                matched_kbs = pinyin_index.get(phrase_py_key, [])
                for kb in matched_kbs:
                    # 跳过完全相同的 (不需要替换)
                    if phrase == kb.replacement:
                        continue

                    # 基础置信度
                    confidence = kb.confidence or 0.85

                    # 精确同音加分 (无声调拼音完全一致 +1)
                    if phrase != kb.original:
                        confidence = min(confidence + 0.05, 0.98)

                    # 上下文加权 (知识库有上下文 且 文本中出现)
                    if kb.context:
                        ctx_parts = [c for c in kb.context.replace('，', ',').split(',') if c.strip()]
                        if any(ctx in text[max(0, i-20):i+window_size+20] for ctx in ctx_parts):
                            confidence = min(confidence + 0.05, 0.99)

                    # 使用频次加权
                    if kb.usage_count and kb.usage_count > 10:
                        confidence = min(confidence + 0.03, 0.99)

                    if confidence >= min_confidence:
                        results.append({
                            'start': i,
                            'end': i + window_size,
                            'source': phrase,
                            'target': kb.replacement,
                            'confidence': confidence,
                            'method': 'exact_homophone' if phrase != kb.original else 'context_match',
                            'kb_id': kb.id,
                        })
                        matched_positions.update(range(i, i + window_size))
                        break  # 该位置已匹配，跳到下一位置

        # 按位置排序
        results.sort(key=lambda x: x['start'])
        return results

    @classmethod
    def apply_corrections(cls, text: str, min_confidence: float = 0.90,
                          user_confirmed: dict = None) -> tuple:
        """
        对文本应用已知校正。

        Args:
            text: 原始文本
            min_confidence: 最低置信度 (低于此值不替换)
            user_confirmed: 用户确认的替换 {start: replacement}
                            例如 {5: "伙牌"} 表示位置5的词替换为"伙牌"

        Returns:
            (替换后文本, 替换记录列表)
        """
        if not text:
            return text, []

        candidates = cls.detect_homophones(text, min_confidence=0.60)
        if not candidates:
            return text, []

        corrections = []
        # 从后往前替换 (避免偏移变化)
        for cand in reversed(candidates):
            start, end = cand['start'], cand['end']
            source = cand['source']
            target = cand['target']
            confidence = cand['confidence']

            # 高置信度自动替换
            if confidence >= min_confidence:
                pass  # 自动应用
            # 中置信度需用户确认
            elif user_confirmed and start in user_confirmed:
                target = user_confirmed.get(start, target)
            else:
                continue  # 跳过未确认的中置信度替换

            # 执行替换
            text = text[:start] + target + text[end:]
            corrections.append({
                'start': start,
                'end': start + len(target),
                'source': source,
                'target': target,
                'confidence': confidence,
            })

            # 频次 +1
            if cand.get('kb_id'):
                kb = VoiceKnowledgeEntry.query.get(cand['kb_id'])
                if kb:
                    kb.increment_usage()

        return text, corrections

    @classmethod
    def record_correction(cls, ledger_id: int, original: str, replacement: str,
                          context_before: str = None, context_after: str = None,
                          method: str = 'manual', confidence: float = None) -> TextCorrectionRecord:
        """记录一次文本校正"""
        record = TextCorrectionRecord(
            ledger_id=ledger_id,
            original_text=original,
            replacement_text=replacement,
            context_before=context_before[:128] if context_before else None,
            context_after=context_after[:128] if context_after else None,
            method=method,
            confidence=confidence,
        )
        db.session.add(record)
        db.session.commit()
        return record

    @classmethod
    def persist_to_knowledge(cls, record_id: int) -> Optional[VoiceKnowledgeEntry]:
        """将校正记录沉淀到知识库"""
        record = TextCorrectionRecord.query.get(record_id)
        if not record:
            return None

        # 检查是否已存在
        existing = VoiceKnowledgeEntry.query.filter_by(
            original=record.original_text,
            replacement=record.replacement_text,
            is_active=True
        ).first()

        if existing:
            existing.increment_usage()
            existing.confidence = min(existing.confidence + 0.01, 0.99)
        else:
            existing = cls.create_entry(
                original=record.original_text,
                replacement=record.replacement_text,
                context=(record.context_before or '')[-50:] + (record.context_after or '')[:50],
                source='auto_detected',
                confidence=record.confidence or 0.80,
            )

        record.persisted_to_knowledge = True
        db.session.commit()
        return existing
