"""
文字内容总结服务

将语音转写的长文本进行智能总结，提取关键信息。
优先使用项目已有的 LLM 大模型配置，若未配置则使用规则提取作为降级方案。

V15.2 变更:
- summarize_meeting() 拆分为 3 次独立 LLM 调用，避免输出截断
  1. segment_meeting()  → 发言分段
  2. clean_meeting()    → 清洁版（基于分段）
  3. summarize_meeting_inner() → 摘要版（基于分段+清洁版）
- 每一阶段可独立重试

V15.3 变更:
- 知识库提示词注入: 每阶段 prompt 追加本地词汇知识
- 同音词精准替换指导
"""
import logging
import re

logger = logging.getLogger(__name__)
import logging
import re

logger = logging.getLogger(__name__)

# ===================== V15.2 三段式 prompt (每次独立调用) =====================

SEGMENT_SYSTEM_PROMPT = """您是专业的政务招商会议文本整理专员, 熟悉招商引资、项目落地、园区配套、要素保障等领域的专有名词与工作流程。所有输出必须 100% 基于原文信息, 严禁编造、补充任何原文未提及的内容。

【本次会议关联的项目名称 (供消歧参考, 请勿凭空引入)】
{meeting_knowledge}

任务: 识别原文中的发言轮次, 在每轮发言前插入换行+发言标记 (格式: [发言N]:), 仅做切断分段, 不修改原文措辞/内容。

规则:
- 当话题切换、发言人改变、或出现明显停顿(如"好的""接下来""另外一个事")时切段
- 保留原文所有信息, 不增不减
- 每段以 [发言N]: 开头(N从1递增)

输出: 仅输出分段后的完整文本, 不加任何标题或说明"""

SEGMENT_USER_PROMPT = """请对以下原始会议语音转写文本进行发言分段:

{transcript}"""


CLEAN_SYSTEM_PROMPT = """您是专业的政务招商会议文本整理专员, 熟悉招商引资、项目落地、园区配套、要素保障等领域的专有名词与工作流程。所有输出必须 100% 基于原文信息, 严禁编造、补充任何原文未提及的内容。

【本次会议关联的项目名称 (供消歧参考, 请勿凭空引入)】
{meeting_knowledge}

任务: 将带发言标记的会议文本整理为清洁版正式文档。

规则:
- 剔除嗯/啊/重复句/无关语气词
- 还原谐音错别字、断句错误
- 统一专有名词（参考上方知识库）
- 多人对话按议题整合为连贯的正式陈述
- 按「会议开场→议题讨论→工作部署→补充事项」分二三级标题
- 不遗漏卡点、时间节点、工作要求
- 保留所有实质性内容

输出: 仅输出清洁版 Markdown 文本, 不加任何说明"""

CLEAN_USER_PROMPT = """请对以下带发言标记的会议文本进行清洁整理:

{transcript}"""


SUMMARY_SYSTEM_PROMPT = """您是专业的政务招商会议总结专家, 熟悉招商引资、项目落地、园区配套、要素保障等领域。所有输出必须 100% 基于原文信息, 严禁编造、补充任何原文未提及的内容。

任务: 接收清洁版会议文档, 生成高度结构化的摘要。

强制覆盖 4 维度:
1. 会议议程概述 (会议主题、核心目的、议程与参会主体)
2. 核心内容与关键信息 (核心议题、项目进展、核心堵点、讨论共识)
3. 决议与行动事项 (任务内容+责任主体+完成时限+交付要求)
4. 会议总结 (定调+整体工作要求+后续推进方向)

输出: 仅输出 Markdown 格式的摘要, 使用 ## 三级标题区分维度, 不加说明"""

SUMMARY_USER_PROMPT = """请基于以下会议文本生成结构化摘要。

【发言分段版】(原始对话轮次):
{segmented}

【清洁版】(整理后文档):
{transcript}

注意: 摘要应基于以上两个版本的完整信息, 不要遗漏任何关键内容。"""


# ===================== V15.2 三阶段总结函数 =====================

def segment_meeting(transcript: str, knowledge_block: str = '') -> str:
    """阶段1: 发言分段"""
    if not transcript or not transcript.strip():
        return ''

    config = _get_llm_config()
    if not config:
        return transcript  # 降级：返回原文

    from services.llm_service import call_llm

    max_input_chars = 50000
    truncated = transcript[:max_input_chars]

    # === Phase 4: 注入语音知识库提示 ===
    system = SEGMENT_SYSTEM_PROMPT.replace('{meeting_knowledge}', knowledge_block)
    knowledge_fragment = _build_knowledge_fragment(transcript[:2000])
    if knowledge_fragment:
        system += '\n\n' + knowledge_fragment
    # === 注入结束 ===

    user = SEGMENT_USER_PROMPT.replace('{transcript}', truncated)

    try:
        result = call_llm(
            config,
            [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            temperature=0.2,
            max_tokens=5000
        )
        return result.strip()
    except Exception as e:
        logger.warning(f'segment_meeting failed: {e}')
        return transcript  # 降级：返回原文


def clean_meeting(transcript: str, knowledge_block: str = '') -> str:
    """阶段2: 清洁版（输入：带标记的分段文本）"""
    if not transcript or not transcript.strip():
        return ''

    config = _get_llm_config()
    if not config:
        return transcript  # 降级

    from services.llm_service import call_llm

    max_input_chars = 50000
    truncated = transcript[:max_input_chars]

    # === Phase 4: 注入语音知识库提示 ===
    system = CLEAN_SYSTEM_PROMPT.replace('{meeting_knowledge}', knowledge_block)
    knowledge_fragment = _build_knowledge_fragment(transcript[:2000])
    if knowledge_fragment:
        system += '\n\n' + knowledge_fragment
    # === 注入结束 ===

    user = CLEAN_USER_PROMPT.replace('{transcript}', truncated)

    try:
        result = call_llm(
            config,
            [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            temperature=0.3,
            max_tokens=5000
        )
        return result.strip()
    except Exception as e:
        logger.warning(f'clean_meeting failed: {e}')
        return transcript  # 降级


def summarize_meeting_inner(transcript: str, segmented_text: str, knowledge_block: str = '') -> str:
    """阶段3: 摘要版（基于清洁版 + 发言分段，确保信息不丢失）"""
    if not transcript or not transcript.strip():
        return '无有效内容，无法生成摘要。'

    config = _get_llm_config()
    if not config:
        return '（未配置 AI 模型，请先配置 LLM 模型后使用此功能）'

    from services.llm_service import call_llm

    max_input_chars = 50000
    truncated_clean = transcript[:max_input_chars]
    truncated_seg = segmented_text[:max_input_chars]

    # === Phase 4: 注入语音知识库提示 ===
    system = SUMMARY_SYSTEM_PROMPT.replace('{meeting_knowledge}', knowledge_block)
    knowledge_fragment = _build_knowledge_fragment(transcript[:2000])
    if knowledge_fragment:
        system += '\n\n' + knowledge_fragment
    # === 注入结束 ===
    user = SUMMARY_USER_PROMPT.replace('{transcript}', truncated_clean).replace('{segmented}', truncated_seg)

    try:
        result = call_llm(
            config,
            [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            temperature=0.3,
            max_tokens=5000
        )
        return result.strip()
    except Exception as e:
        logger.warning(f'summarize_meeting_inner failed: {e}')
        return f'摘要生成失败: {str(e)[:200]}'


CHUNK_SIZE = 50000  # 单段 LLM 输入上限（字符）；超出则分段总结后合并


def _chunk_text(text, size=CHUNK_SIZE):
    """按段落/句子边界将长文本切成不超过 size 字符的块，尽量避免在句中断开。"""
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks = []
    cur = ''
    for para in re.split(r'\n\s*\n', text):
        if len(cur) + len(para) + 2 <= size:
            cur = (cur + '\n\n' + para) if cur else para
            continue
        if cur:
            chunks.append(cur)
            cur = ''
        if len(para) <= size:
            cur = para
        else:
            for sent in re.split(r'(?<=[。！？!?；;\n])', para):
                if len(cur) + len(sent) <= size:
                    cur = (cur + sent) if cur else sent
                else:
                    if cur:
                        chunks.append(cur)
                    cur = sent
    if cur:
        chunks.append(cur)
    return chunks


SUMMARY_MERGE_INSTRUCTION = """你正在将同一场会议的多段局部总结合并为一份统一的结构化总结。
请保留原有四个维度（核心结论 / 关键议题 / 待办事项 / 风险提示），去重并合并相似条目，
保持关键实体（人名、机构、金额、时间、地点）不变。不要新增原文没有的信息。"""


def _do_merge(text, knowledge_block):
    config = _get_llm_config()
    if not config:
        return text  # 无模型配置时退化为拼接，避免丢失内容
    from services.llm_service import call_llm
    system = SUMMARY_MERGE_INSTRUCTION
    if knowledge_block:
        system += '\n\n# 术语与专有名词参考\n' + knowledge_block
    user = f'请将以下多段局部总结合并为一份统一的结构化总结：\n\n{text}'
    try:
        return call_llm(
            config,
            [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            temperature=0.3,
            max_tokens=6000,
        ).strip()
    except Exception as e:
        logger.warning(f'合并总结失败：{e}')
        return text


def _merge_summaries(parts, knowledge_block):
    """将多段局部总结合并为一份统一总结；过长时分块合并，最终合并若仍超长则退化为拼接，避免死循环。"""
    parts = [p for p in parts if p and p.strip()]
    if not parts:
        return ''
    if len(parts) == 1:
        return parts[0]
    combined = '\n\n'.join(f'【第 {i + 1} 部分】\n{p}' for i, p in enumerate(parts))
    if len(combined) <= CHUNK_SIZE:
        return _do_merge(combined, knowledge_block)
    sub = [_do_merge(c, knowledge_block) for c in _chunk_text(combined)]
    final = '\n\n'.join(sub)
    if len(final) <= CHUNK_SIZE:
        return _do_merge(final, knowledge_block)
    return final


def summarize_meeting(transcript: str, model_id=None) -> dict:
    """三版总结 (串行调用 3 次 LLM, 避免截断)

    超长录音（> CHUNK_SIZE）按块分段处理各阶段，最后将多段局部总结合并为统一总结，
    避免任一阶段因输入超长被截断而丢失内容。

    Returns:
        dict: {'segmented': str, 'clean': str, 'summary': str}
    """
    if not transcript or not transcript.strip():
        return {'segmented': '', 'clean': '', 'summary': '无录音内容，无法生成总结。'}

    knowledge_block = build_meeting_knowledge(transcript[:2000])

    # 阶段1：发言分段（按块处理，避免超长截断丢内容）
    logger.info(f'阶段1/3: 发言分段 ({len(transcript)} 字输入)')
    segmented = '\n\n'.join(
        p for p in (segment_meeting(chunk, knowledge_block) for chunk in _chunk_text(transcript)) if p and p.strip()
    )

    # 阶段2：清洁版（基于分段输出按块处理）
    logger.info(f'阶段2/3: 清洁版 ({len(segmented)} 字输入)')
    clean = '\n\n'.join(
        p for p in (clean_meeting(chunk, knowledge_block) for chunk in _chunk_text(segmented)) if p and p.strip()
    )

    # 阶段3：摘要版（clean 分块各自生成局部总结，再合并为统一总结）
    logger.info(f'阶段3/3: 摘要版 (clean={len(clean)} 字输入)')
    summary = _merge_summaries(
        [summarize_meeting_inner(chunk, chunk, knowledge_block) for chunk in _chunk_text(clean)],
        knowledge_block,
    )

    return {
        'segmented': segmented,
        'clean': clean,
        'summary': summary
    }


# ===================== 辅助函数 =====================

def _get_llm_config(model_id=None):
    """获取 LLM 配置。

    Args:
        model_id: 指定模型 ID (可选); 为 None 时使用首个激活模型。

    Returns:
        dict: {api_base_url, api_key, model_name, provider}; 失败返回 None。
    """
    try:
        from models.ai import LLMModel
        query = LLMModel.query.filter_by(is_active=True)
        if model_id is not None:
            model = query.filter_by(id=model_id).first()
        else:
            model = query.order_by(LLMModel.sort_order).first()
        if model and model.api_base_url and model.api_key:
            return {
                'api_base_url': model.api_base_url,
                'api_key': model.api_key,
                'model_name': model.model_name,
                'provider': model.provider
            }
    except Exception as e:
        logger.warning(f'获取 LLM 配置失败：{e}')
    return None


def build_meeting_knowledge(transcript: str = '', max_projects: int = 50) -> str:
    """构建项目名称知识块 (委托给 utils.meeting_knowledge)"""
    from utils.meeting_knowledge import build_meeting_knowledge as _build
    return _build(transcript, max_projects)


def get_meeting_prompt_templates() -> dict:
    """返回各阶段 prompt 供前端预览。"""
    return {
        'segment': {'system': SEGMENT_SYSTEM_PROMPT, 'user': SEGMENT_USER_PROMPT},
        'clean': {'system': CLEAN_SYSTEM_PROMPT, 'user': CLEAN_USER_PROMPT},
        'summary': {'system': SUMMARY_SYSTEM_PROMPT, 'user': SUMMARY_USER_PROMPT},
    }


# ===================== Phase 4: 语音知识库提示注入 =====================

def _build_knowledge_fragment(transcript_sample: str) -> str:
    """
    根据当前知识库生成提示词片段, 注入到 LLM system prompt 中。

    让 LLM 了解当地方言/谐音词汇的正确含义，提升总结准确性。
    """
    if not transcript_sample:
        return ''

    try:
        from models import VoiceKnowledgeEntry
        from services.voice_knowledge import VoiceKnowledgeService

        # 检测文本中出现的同音词
        candidates = VoiceKnowledgeService.detect_homophones(transcript_sample, min_confidence=0.70)
        if not candidates:
            return ''

        # 只取高置信、去重
        seen_sources = set()
        lines = ['【语音识别本地知识提示】以下词汇在当地会议中常见, 请注意正确识别:']
        for c in candidates:
            if c['source'] not in seen_sources:
                seen_sources.add(c['source'])
                ctx = f' (上下文: {c["context"]})' if c.get('context') else ''
                lines.append(f'  - "{c["source"]}" → "{c["target"]}"{ctx}')

        return '\n'.join(lines) if len(lines) > 1 else ''

    except Exception as e:
        logger.warning(f'构建知识提示失败: {e}')
        return ''
