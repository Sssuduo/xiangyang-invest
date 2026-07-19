"""
语音识别知识库模型

存储同音/谐音校正知识，用于:
1. ASR 语音识别后的后处理（替换同音错字）
2. LLM 总结时的提示词注入（精准识别指导）
3. Web 文本校正页的智能候选推荐

拼音索引使用 pypinyin 库，支持同音词模糊匹配。
"""
import json
from datetime import datetime
from extensions import db


class VoiceKnowledgeEntry(db.Model):
    """语音识别同音/谐音校正知识条目"""
    __tablename__ = 'voice_knowledge_entries'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 核心字段: 错误文本 → 正确文本
    original = db.Column(db.String(128), nullable=False, index=True)
    replacement = db.Column(db.String(128), nullable=False)

    # 拼音索引 (JSON 数组, 无声调, 用于模糊匹配)
    # 例如 "火牌" → ["huo", "pai"]
    pinyin = db.Column(db.Text, nullable=True)

    # 上下文线索 (可选, 用于消歧)
    # 例如 "伙牌镇" 需要和 "火车票" 中的 "火" 区分
    context = db.Column(db.String(256), nullable=True)

    # 统计反馈
    usage_count = db.Column(db.Integer, default=1)  # 被应用次数
    confidence = db.Column(db.Float, default=0.9)   # 置信度 (0~1)

    # 来源: manual (用户手工添加) | auto_detected (系统检测)
    source = db.Column(db.String(32), default='manual')

    # 软删除
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        # 容错：pinyin 字段可能存了历史脏数据（非 JSON 字符串，如 "None"），
        # json.loads 失败时不让整个知识库列表接口崩溃，回退为空列表。
        pinyin = []
        if self.pinyin:
            try:
                parsed = json.loads(self.pinyin)
                if isinstance(parsed, list):
                    pinyin = parsed
            except (ValueError, TypeError):
                pinyin = []
        return {
            'id': self.id,
            'original': self.original,
            'replacement': self.replacement,
            'pinyin': pinyin,
            'context': self.context or '',
            'usage_count': self.usage_count,
            'confidence': self.confidence,
            'source': self.source,
            'is_active': self.is_active,
        }

    @staticmethod
    def generate_pinyin_cache(text: str) -> str:
        """生成拼音索引缓存 (JSON 字符串)"""
        try:
            from pypinyin import lazy_pinyin, Style
            py_list = lazy_pinyin(text, style=Style.NORMAL)
            return json.dumps(py_list, ensure_ascii=False)
        except ImportError:
            # pypinyin 未安装时返回空
            return '[]'

    def refresh_pinyin_cache(self):
        """更新拼音缓存"""
        self.pinyin = self.generate_pinyin_cache(self.original)

    def increment_usage(self):
        """使用频次 +1"""
        self.usage_count = (self.usage_count or 0) + 1


class TextCorrectionRecord(db.Model):
    """Web 文本校正记录 (审计 + 反馈)"""
    __tablename__ = 'text_correction_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 关联台账
    ledger_id = db.Column(db.Integer, db.ForeignKey('activity_ledger.id'), nullable=False, index=True)

    # 校正内容
    original_text = db.Column(db.String(256), nullable=False)
    replacement_text = db.Column(db.String(256), nullable=False)

    # 上下文 (替换位置前后各 50 字)
    context_before = db.Column(db.String(128), nullable=True)
    context_after = db.Column(db.String(128), nullable=True)

    # 替换策略
    method = db.Column(db.String(32), default='manual')  # manual / homophone_auto / homophone_manual
    confidence = db.Column(db.Float, nullable=True)       # AI 推荐的置信度

    # 是否已沉淀到知识库
    persisted_to_knowledge = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    ledger = db.relationship('ActivityLedger', backref='text_corrections')
