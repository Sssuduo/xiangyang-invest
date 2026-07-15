"""
语音知识库 API

端点:
- GET    /api/admin/voice-knowledge             活跃知识列表
- POST   /api/admin/voice-knowledge             新增知识条目
- DELETE /api/admin/voice-knowledge/<id>        软删除
- POST   /api/admin/voice-knowledge/detect      检测文本中的同音词
- POST   /api/admin/activity-ledger/<id>/save-corrections  保存 Web 校正结果
"""
import logging

from flask import request, jsonify

from models import VoiceKnowledgeEntry, ActivityLedger, TextCorrectionRecord
from routes import admin_voice_knowledge_bp
from routes.business_auth import dual_login_required, visitor_block
from services.voice_knowledge import VoiceKnowledgeService

logger = logging.getLogger(__name__)


def _get_item_or_404(item_id: int) -> ActivityLedger:
    """获取台账或 404"""
    from models.investment import ActivityLedger as AL  # 避免循环导入
    return AL.query.filter_by(id=item_id).first_or_404()


@admin_voice_knowledge_bp.route('', methods=['GET'])
@dual_login_required
def list_voice_knowledge():
    """知识库列表"""
    entries = VoiceKnowledgeService.list_active_entries()
    return jsonify({
        'code': 0,
        'data': [e.to_dict() for e in entries],
        'total': len(entries),
    })


@admin_voice_knowledge_bp.route('', methods=['POST'])
@dual_login_required
@visitor_block
def create_voice_knowledge():
    """新增知识条目"""
    data = request.get_json(silent=True) or {}
    original = (data.get('original') or '').strip()
    replacement = (data.get('replacement') or '').strip()
    context = data.get('context')

    if not original or not replacement:
        return jsonify({'code': 1, 'message': '原文和替换词不能为空'}), 400

    # 防重复
    existing = VoiceKnowledgeEntry.query.filter_by(
        original=original, replacement=replacement, is_active=True
    ).first()
    if existing:
        return jsonify({'code': 1, 'message': '该映射已存在', 'data': existing.to_dict()}), 409

    entry = VoiceKnowledgeService.create_entry(
        original=original,
        replacement=replacement,
        context=context,
        source='manual',
    )
    return jsonify({'code': 0, 'message': '已保存', 'data': entry.to_dict()})


@admin_voice_knowledge_bp.route('/<int:entry_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_voice_knowledge(entry_id):
    """软删除知识条目"""
    ok = VoiceKnowledgeService.delete_entry(entry_id)
    if not ok:
        return jsonify({'code': 1, 'message': '条目不存在'}), 404
    return jsonify({'code': 0, 'message': '已删除'})


@admin_voice_knowledge_bp.route('/detect', methods=['POST'])
@dual_login_required
def detect_homophones():
    """
    检测文本中的同音词候选。

    Request: { text: str, min_confidence?: float }
    Response: { code: 0, data: [{ start, end, source, target, confidence, method, kb_id }] }
    """
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    min_confidence = data.get('min_confidence', 0.75)

    if not text:
        return jsonify({'code': 1, 'message': 'text 不能为空'}), 400

    candidates = VoiceKnowledgeService.detect_homophones(text, min_confidence=min_confidence)
    return jsonify({'code': 0, 'data': candidates, 'total': len(candidates)})


@admin_voice_knowledge_bp.route(
    '/activity-ledger/<int:item_id>/save-corrections',
    methods=['POST']
)
@dual_login_required
@visitor_block
def save_text_corrections(item_id):
    """
    保存 Web 文本校正结果。

    Request: {
        corrections: [
            { original, replacement, position, context_before, context_after, method, confidence }
        ],
        persist_to_knowledge: bool
    }
    """
    item = _get_item_or_404(item_id)
    data = request.get_json(silent=True) or {}
    corrections = data.get('corrections', [])
    persist = data.get('persist_to_knowledge', False)

    records = []
    for c in corrections:
        record = VoiceKnowledgeService.record_correction(
            ledger_id=item_id,
            original=c.get('original', ''),
            replacement=c.get('replacement', ''),
            context_before=c.get('context_before'),
            context_after=c.get('context_after'),
            method=c.get('method', 'manual'),
            confidence=c.get('confidence'),
        )
        records.append(record)

    # 沉淀到知识库
    if persist:
        for record in records:
            VoiceKnowledgeService.persist_to_knowledge(record.id)

    return jsonify({
        'code': 0,
        'message': f'已保存 {len(records)} 条校正',
        'data': {'count': len(records), 'persisted': persist},
    })


@admin_voice_knowledge_bp.route(
    '/activity-ledger/<int:item_id>/summary-data',
    methods=['GET']
)
@dual_login_required
def get_summary_page_data(item_id):
    """
    获取 Web 文本校正页所需数据。

    返回: 台账的清洁版、摘要版、分段原文、已应用的校正列表
    """
    item = _get_item_or_404(item_id)
    records = TextCorrectionRecord.query.filter_by(ledger_id=item_id)\
        .order_by(TextCorrectionRecord.created_at.desc()).all()

    return jsonify({
        'code': 0,
        'data': {
            'transcript': item.audio_transcript or '',
            'transcript_segmented': item.audio_transcript_segmented or '',
            'transcript_clean': item.audio_transcript_clean or '',
            'summary_structured': item.audio_summary_structured or '',
            'corrections': [{
                'id': r.id,
                'original': r.original_text,
                'replacement': r.replacement_text,
                'method': r.method,
                'confidence': r.confidence,
                'created_at': r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '',
            } for r in records],
        },
    })


# ======================== Phase 3: 智能替换 + 应用到台账 ========================

@admin_voice_knowledge_bp.route(
    '/activity-ledger/<int:item_id>/auto-correct',
    methods=['POST']
)
@dual_login_required
@visitor_block
def auto_correct_ledger(item_id):
    """
    对台账自动检测同音词并替换高置信度项。

    Request: { min_confidence?: float (默认 0.90) }
    Response: { code, data: { applied: [...], candidates: [...] } }
    """
    item = _get_item_or_404(item_id)
    data = request.get_json(silent=True) or {}
    min_conf = data.get('min_confidence', VoiceKnowledgeService.CONFIDENCE_HIGH)

    # 分段原文作为校正基准
    original_text = item.audio_transcript_segmented or item.audio_transcript or ''
    if not original_text.strip():
        return jsonify({'code': 1, 'message': '没有可校正的文本'}), 400

    # 应用校正
    corrected_text, corrections = VoiceKnowledgeService.apply_corrections(
        original_text,
        min_confidence=min_conf,
    )

    # 保存到台账
    item.audio_transcript_segmented = corrected_text
    db.session.commit()

    return jsonify({
        'code': 0,
        'message': f'自动校正完成，替换 {len(corrections)} 处',
        'data': {
            'applied': corrections,
            'corrected_text': corrected_text,
        },
    })


@admin_voice_knowledge_bp.route(
    '/activity-ledger/<int:item_id>/save-corrected-text',
    methods=['PUT']
)
@dual_login_required
@visitor_block
def save_corrected_text(item_id):
    """
    保存 Web 页编辑后的文本到台账。

    Request: {
        transcript_segmented?: str,
        transcript_clean?: str,
        summary_structured?: str,
        corrections: [{ original, replacement, method, confidence? }]
        persist_to_knowledge?: bool
    }
    """
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    data = request.get_json(silent=True) or {}

    # 更新文本字段
    if 'transcript_segmented' in data:
        item.audio_transcript_segmented = data['transcript_segmented']
    if 'transcript_clean' in data:
        item.audio_transcript_clean = data['transcript_clean']
    if 'summary_structured' in data:
        item.audio_summary_structured = data['summary_structured']

    # 记录校正
    corrections = data.get('corrections', [])
    for c in corrections:
        record = VoiceKnowledgeService.record_correction(
            ledger_id=item_id,
            original=c.get('original', ''),
            replacement=c.get('replacement', ''),
            context_before=c.get('context_before'),
            context_after=c.get('context_after'),
            method=c.get('method', 'manual'),
            confidence=c.get('confidence'),
        )
        # 沉淀到知识库
        if data.get('persist_to_knowledge', False):
            VoiceKnowledgeService.persist_to_knowledge(record.id)

    db.session.commit()

    return jsonify({
        'code': 0,
        'message': f'已保存文本和 {len(corrections)} 条校正',
        'data': {'corrections_count': len(corrections)},
    })


# ======================== 供 LLM 提示词注入调用 ========================

def build_knowledge_prompt_fragment(transcript: str = '',
                                    max_entries: int = 10) -> str:
    """
    构建知识库提示词片段，供 LLM 总结时注入。

    返回形如:
    【当地方言/专有名词提示】
    以下词汇在本地特定用法，请注意识别：
    - "火牌" 通指 "伙牌镇" (襄州区)
    - "环用" 可能是 "环用物流" 的简称
    """
    if not transcript:
        return ''

    # 查询高置信知识条目
    entries = VoiceKnowledgeEntry.query.filter_by(is_active=True)\
        .order_by(VoiceKnowledgeEntry.usage_count.desc())\
        .limit(max_entries).all()

    if not entries:
        return ''

    # 二次过滤: 只保留可能与当前文本相关的
    relevant = []
    for entry in entries:
        # 拼音重叠检测
        entry_py = set(json.loads(entry.pinyin) if entry.pinyin else [])
        text_py = set(VoiceKnowledgeService._get_pinyin(transcript[:500]))
        if entry_py & text_py:
            relevant.append(entry)

    if not relevant:
        return ''

    lines = ['【本地词汇提示】以下词汇在本地区特定语境下的正确用法:']
    for e in relevant:
        ctx = f' (上下文: {e.context})' if e.context else ''
        lines.append(f'- "{e.original}" → "{e.replacement}"{ctx}')

    return '\n'.join(lines)
