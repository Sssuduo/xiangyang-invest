"""
文字内容总结服务

将语音转写的长文本进行智能总结，提取关键信息。
优先使用项目已有的 LLM 大模型配置，若未配置则使用规则提取作为降级方案。

V15.2 变更:
- summarize_meeting() 拆分为 3 次独立 LLM 调用，避免输出截断
  1. segment_meeting()  → 分段原文（基础分段 + 术语/谐音校正，不改动内容）
  2. clean_meeting()    → 清洁版（基础结构化 + 去噪，完整度优先、不浓缩）
  3. summarize_meeting_inner() → 摘要版（高度凝练：核心结论/决策/行动项）
- 每一阶段可独立重试

V15.3 变更:
- 知识库提示词注入: 每阶段 prompt 追加本地词汇知识
- 同音词精准替换指导
"""
import logging
import re
import time

logger = logging.getLogger(__name__)

# ===================== V15.2 三段式 prompt (每次独立调用) =====================

SEGMENT_SYSTEM_PROMPT = """您是专业的政务招商会议文本整理专员, 熟悉招商引资、项目落地、园区配套、要素保障等领域的专有名词与工作流程。所有输出必须 100% 基于原文信息, 严禁编造、补充任何原文未提及的内容。

【本次会议关联的项目名称 (供消歧参考, 请勿凭空引入)】
{meeting_knowledge}

任务: 对原始会议语音转写文本做【基础分段 + 术语/谐音校正】, 输出带发言标记的"分段原文"。本阶段只做"分段"与"识别纠错", 不增删任何实质性内容。

【发言分段】
- 识别发言轮次, 在每轮发言前插入换行与发言标记(格式: [发言N]:), 仅做切断分段。
- 当话题切换、发言人改变、或出现明显停顿(如"好的""接下来""另外一个事")时切段。
- 每段以 [发言N]: 开头(N从1递增); 输出篇幅应与原文基本一致。

【术语/谐音校正】(仅修正明显的语音识别错误, 不改变语义与内容)
- 依据下方【语音识别本地知识提示】, 把误识别的同音词、方言词、专有名词改正为正确写法。
- 仅做"纠错", 不得增删任何实质性句子、不得改写语义、不得省略原句信息。
- 无法确认的词汇一律保留原样, 宁可不改也不要臆造。

输出: 仅输出分段 + 校正后的完整文本, 不加任何标题或说明"""

SEGMENT_USER_PROMPT = """请对以下原始会议语音转写文本进行发言分段:

{transcript}"""


CLEAN_SYSTEM_PROMPT = """您是专业的政务招商会议文本整理专员, 熟悉招商引资、项目落地、园区配套、要素保障等领域。所有输出必须 100% 基于原文信息, 严禁编造、补充原文未提及的内容。

【本次会议关联的项目名称 (供消歧参考, 请勿凭空引入)】
{meeting_knowledge}

任务: 在"分段原文"基础上做【清洁整理 + 基础结构化】。目标是"整理"而非"概括"——在尽量不丢失任何实质性内容的前提下, 让文本结构清晰、便于阅读, 篇幅应接近原文, 严禁浓缩。

【完整度优先(必须保留)】
- 逐条保留: 决议、工作任务、责任主体、时间节点、金额、数量、地名、机构名、人名、关键原话要点。
- 保留原始 [发言N]: 标记与发言顺序(可适度按议题归并呈现, 但不得删减发言中的任何实质性内容)。
- 仅删除无信息量的口语杂音: 嗯/啊/那个/这个/口头重复/自我打断后的重复纠正片段。

【层次化处理(基础结构化)】
- 仅在块内出现明确的议题/板块转换时, 用二级标题(##)概括该议题; 若本块只是某个更大议题的一部分(承接上文), 请勿在开头强行新建大标题, 直接以项目符号(-)继续列出要点即可。
- 同一议题/同一发言下的要点用项目符号(-)列出, 每条保留完整表述, 不简化、不合并不同要点。
- 严禁为了"整洁"而压缩、概括、省略任何实质性句子或数据。

【严禁】
- 严禁浓缩、概括、省略、改写语义; 严禁编造。
- 严禁增删或改动 [发言N]: 标记、严禁调换发言顺序。

输出: 仅输出整理后的 Markdown 文本, 不加任何说明。"""

CLEAN_USER_PROMPT = """请对以下带发言标记的会议文本进行清洁整理:

{transcript}"""


SUMMARY_SYSTEM_PROMPT = """您是专业的政务招商会议总结专家, 熟悉招商引资、项目落地、园区配套、要素保障等领域。所有输出必须 100% 基于原文信息, 严禁编造。

任务: 对会议内容做【高度凝练】的总结——只提炼核心结论、关键决策、行动事项、关键数据与主要风险, 舍弃冗长的讨论过程、口语化细节与重复表述。目标是产出一份"一眼掌握会议要点"的精炼纪要, 而非完整详尽的逐条记录。

【必须凝练保留的要点】(可合并、可概括, 但不得编造)
1. 一句话核心结论/会议成果。
2. 关键决策与决议(含倾向性结论; 无明确结论标注"待定/未形成决议")。
3. 行动事项: 任务 + 责任方 + 时限 + 交付要求(原文明确才写)。
4. 关键数据与时点: 金额、数量、比例、日期、阶段目标(原样保留具体数字)。
5. 主要风险与需协调事项。

【凝练要求】
- 大幅压缩篇幅: 用精炼条目与短句, 删除一切铺垫、重复、口语与过程性描述。
- 同类信息合并为一句; 不写"讨论了XX"的过程, 直接给结论。
- 保留具体人名、机构、地名、数字, 不得笼统化(如不得把"3月底前完成"写成"尽快")。
- 原文模糊处如实标注"未明确"; 不编造原文未提及的内容。

【分块处理说明】
- 本纪要可能仅基于会议的一个片段(分块)生成; 若本块信息不足以支撑完整结论, 严禁编造, 仅在相关处标注"待续/见前后块"。最终合并阶段会跨块统一去重。

输出: 仅输出 Markdown 精炼纪要, 不加说明。"""

SUMMARY_USER_PROMPT = """请基于以下会议文本生成高度凝练的结构化纪要。

【发言分段版】(原始对话轮次):
{segmented}

【清洁版】(整理后文档):
{transcript}

注意: 纪要应聚焦核心结论与行动事项, 进行高度凝练, 舍弃过程性细节, 但不得遗漏关键数据与待办。"""


# ===================== V15.2 三阶段总结函数 =====================

def segment_meeting(transcript: str, knowledge_block: str = '', model_id=None, progress_callback=None) -> str:
    """阶段1: 发言分段 — 仅识别发言人并插入 [发言N]: 标记, 100% 保留原文内容, 不增不减。

    按小块 (ECHO_CHUNK_SIZE) 逐块回写, 确保模型能把整块原文完整输出 (避免 max_tokens 截断丢内容);
    若某块回写内容明显短于原文 (被截断), 退回该块原文以保证不丢内容; 最后全局重排发言人编号。
    progress_callback(block, total): 每完成一块回调一次, 用于上报进度。
    """
    if not transcript or not transcript.strip():
        return ''

    config = _get_llm_config(model_id)
    if not config:
        return transcript  # 降级：返回原文

    from services.llm_service import call_llm

    echo_chunk, echo_max = _echo_chunk_params(config)
    pieces = _chunk_text(transcript, echo_chunk, ECHO_OVERLAP_CHARS)
    out_parts = []
    total = len(pieces)
    for idx, piece in enumerate(pieces, 1):
        # === Phase 4: 注入语音知识库提示 ===
        system = SEGMENT_SYSTEM_PROMPT.replace('{meeting_knowledge}', knowledge_block or '（无关联项目）')
        knowledge_fragment = _build_knowledge_fragment(piece[:2000])
        if knowledge_fragment:
            system += '\n\n' + knowledge_fragment
        # === 注入结束 ===
        user = SEGMENT_USER_PROMPT.replace('{transcript}', piece)
        try:
            result = call_llm(
                config,
                [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
                temperature=0.2,
                max_tokens=echo_max, enable_web_search=False,
            ).strip()
        except Exception as e:
            logger.warning(f'segment_meeting failed: {e}')
            result = piece  # 降级：保留原文
        # 安全网：回写内容明显短于原文 (被截断) → 退回原文, 保证不丢内容
        if len(result) < len(piece) * 0.7:
            result = piece
        out_parts.append(result)
        if progress_callback:
            try:
                progress_callback(idx, total)
            except Exception:
                pass

    return _renumber_speakers('\n\n'.join(out_parts))


def clean_meeting(transcript: str, knowledge_block: str = '', model_id=None, progress_callback=None) -> str:
    """阶段2: 清洁版（输入：带标记的分段文本）— 基础结构化整理 + 去噪, 完整度优先、不浓缩。

    同样按小块 (ECHO_CHUNK_SIZE) 回写, 避免 max_tokens 截断丢内容; 回写明显短于原文时退回原文。
    progress_callback(block, total): 每完成一块回调一次, 用于上报进度。
    """
    if not transcript or not transcript.strip():
        return ''

    config = _get_llm_config(model_id)
    if not config:
        return transcript  # 降级

    from services.llm_service import call_llm

    echo_chunk, echo_max = _echo_chunk_params(config)
    pieces = _chunk_text(transcript, echo_chunk, ECHO_OVERLAP_CHARS)
    out_parts = []
    total = len(pieces)
    for idx, piece in enumerate(pieces, 1):
        # === Phase 4: 注入语音知识库提示 ===
        system = CLEAN_SYSTEM_PROMPT.replace('{meeting_knowledge}', knowledge_block or '（无关联项目）')
        knowledge_fragment = _build_knowledge_fragment(piece[:2000])
        if knowledge_fragment:
            system += '\n\n' + knowledge_fragment
        # === 注入结束 ===
        user = CLEAN_USER_PROMPT.replace('{transcript}', piece)
        try:
            result = call_llm(
                config,
                [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
                temperature=0.3,
                max_tokens=echo_max, enable_web_search=False,
            ).strip()
        except Exception as e:
            logger.warning(f'clean_meeting failed: {e}')
            result = piece  # 降级：保留原文
        # 安全网：回写明显短于原文 (被截断) → 退回原文, 保证不丢内容
        # 阈值与 segment 阶段保持一致(0.7): 避免被截断到 50%~70% 时静默接受半块而丢内容
        if len(result) < len(piece) * 0.7:
            result = piece
        out_parts.append(result)
        if progress_callback:
            try:
                progress_callback(idx, total)
            except Exception:
                pass

    return '\n\n'.join(out_parts)


def summarize_meeting_inner(transcript: str, segmented_text: str, knowledge_block: str = '', model_id=None) -> str:
    """阶段3: 摘要版（基于清洁版 + 发言分段，高度凝练核心结论与行动事项）"""
    if not transcript or not transcript.strip():
        return '无有效内容，无法生成摘要。'

    config = _get_llm_config(model_id)
    if not config:
        return '（未配置 AI 模型，请先配置 LLM 模型后使用此功能）'

    from services.llm_service import call_llm

    max_input_chars = 50000
    truncated_clean = transcript
    truncated_seg = segmented_text
    if len(transcript) > max_input_chars:
        logger.warning(f'summarize_meeting_inner: 清洁版输入 {len(transcript)} 字超过 {max_input_chars}，已截断尾部（长文本建议使用分块入口 summarize_meeting）')
        truncated_clean = transcript[:max_input_chars]
    if len(segmented_text) > max_input_chars:
        logger.warning(f'summarize_meeting_inner: 分段版输入 {len(segmented_text)} 字超过 {max_input_chars}，已截断尾部')
        truncated_seg = segmented_text[:max_input_chars]

    # === Phase 4: 注入语音知识库提示 ===
    system = SUMMARY_SYSTEM_PROMPT.replace('{meeting_knowledge}', knowledge_block or '（无关联项目）')
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
            max_tokens=8000, enable_web_search=False
        )
        return result.strip()
    except Exception as e:
        logger.warning(f'summarize_meeting_inner failed: {e}')
        return f'摘要生成失败: {str(e)[:200]}'


CHUNK_SIZE = 50000  # 单段 LLM 输入上限（字符）；超出则分段总结后合并

# 发言分段 / 清洁版 阶段：必须 100% 回写原文（仅加发言人标记），故按小块回写，
# 避免 max_tokens 上限导致模型无法完整输出原文而丢内容。
# 关键约束：回写型任务的块大小受"模型输出 token 上限"约束（需把整块原文重新输出），
# 因此块大小不能盲目增大；以下为保守默认值，实际块大小由 _echo_chunk_params 按模型
# 上下文窗口 + 输出能力动态计算（见 V16.0 设计文档）。
ECHO_CHUNK_SIZE = 2000        # 回写阶段单块字符基线（动态计算时的下限参考）
ECHO_MAX_TOKENS = 6000        # 回写阶段单块输出上限基线
ECHO_CHUNK_SIZE_MAX = 3000    # 回写阶段单块字符硬上限（受输出 token ~8K 限制，2*3000=6000≤常见上限）
ECHO_OVERLAP_CHARS = 0        # 回写阶段不加重叠：各块独立回写会致内容重复，重叠仅用于摘要阶段

# 摘要阶段：理解/总结类任务，输出短，块可较大；块间重叠提升跨块连贯
SUMMARY_CHUNK_CHARS = 30000
SUMMARY_OVERLAP_CHARS = 1000


def _tail_chars(text, n):
    """取文本最后 n 字符，并向前对齐到句末标点，作为重叠区（避免从句子中间开始）。"""
    if len(text) <= n:
        return text
    truncated = text[-n:]
    last_punct = max(
        truncated.rfind('。'), truncated.rfind('！'), truncated.rfind('？'),
        truncated.rfind('；'), truncated.rfind(';'), truncated.rfind('\n')
    )
    if last_punct > 0:
        return truncated[last_punct + 1:]
    return truncated


def _model_context_window(config):
    """粗略估计模型上下文窗口(token)，未知返回保守值 8000。

    仅依据 model_name / provider 关键字做启发式判断；无法精确时取保守下限，
    避免分块超过模型上下文导致 API 报错或截断。
    """
    if not config:
        return 8000
    name = (config.get('model_name') or '').lower()
    provider = (config.get('provider') or '').lower()
    for kw, win in (('128k', 128000), ('64k', 64000), ('32k', 32000),
                    ('16k', 16000), ('8k', 8000)):
        if kw in name:
            return win
    if any(k in name for k in ('long', 'max', 'pro', 'turbo', 'plus')):
        return 128000
    defaults = {
        'openai': 8000, 'azure': 8000, 'qwen': 8000, 'dashscope': 8000,
        'glm': 8000, 'zhipu': 8000, 'ernie': 8000, 'baidu': 8000,
        'deepseek': 64000, 'moonshot': 32000, 'kimi': 128000,
        'doubao': 32000, 'volc': 32000, 'claude': 200000,
        'anthropic': 200000, 'gemini': 1000000, 'google': 1000000,
    }
    return defaults.get(provider, 8000)


def _echo_chunk_params(config):
    """回写阶段 (阶段1/2) 的动态块大小与输出上限。

    回写型任务必须把整块原文重新输出，故块大小受"输出 token 上限"约束：
    块字符数 C 对应输出约 2*C token；输入约 1.5*C token；合计需 <= 模型上下文安全比例。
    同时输出上限硬控在 8192（常见模型输出上限），因此回写块实际天花板约 3000 字符。

    Returns:
        (chunk_chars, max_tokens)
    """
    if not config:
        return ECHO_CHUNK_SIZE, ECHO_MAX_TOKENS
    ctx = _model_context_window(config)
    safe_total = ctx * 0.75                      # 输入输出合计安全预算
    c = safe_total / 3.5                         # 3.5 ≈ 1.5(输入)+2(输出) tok/字符
    chunk_chars = int(min(ECHO_CHUNK_SIZE_MAX, max(1000, c)))
    max_tokens = int(min(chunk_chars * 2.2, 8192))
    return chunk_chars, max_tokens


def _summary_chunk_chars(config):
    """摘要阶段 (阶段3) 的动态块大小：输出短，主要受输入上下文约束。"""
    if not config:
        return SUMMARY_CHUNK_CHARS
    ctx = _model_context_window(config)
    c = ctx * 0.7 / 1.5                          # 输入~1.5 tok/字符，输出可忽略
    return int(min(SUMMARY_CHUNK_CHARS, max(2000, c)))


def _chunk_text(text, size=CHUNK_SIZE, overlap=0):
    """按段落/句子边界将长文本切成不超过 size 字符的块，尽量避免在句中断开。

    overlap > 0 时，除首块外每块前置上一块尾部 overlap 字符（句边界对齐），
    为下游任务提供跨块上下文。适用于摘要等理解型任务；回写型任务请勿使用，
    否则各块独立回写会导致内容重复。
    """
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
                        cur = ''
                    # 单句超长（如缺少句末标点的连续转写）：强制按字符截断兜底
                    if len(sent) > size:
                        for j in range(0, len(sent), size):
                            piece = sent[j:j + size]
                            if cur:
                                chunks.append(cur)
                            cur = piece
                    else:
                        cur = sent
    if cur:
        chunks.append(cur)
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = _tail_chars(chunks[i - 1], overlap)
            overlapped.append(tail + chunks[i])
        chunks = overlapped
    return chunks


def _renumber_speakers(text: str) -> str:
    """将全文中的 [发言N]: 标记按出现顺序全局重排为 [发言1]:、[发言2]: ……（跨分块拼接后保持连续编号）。"""
    counter = [0]

    def _repl(_m):
        counter[0] += 1
        return f'[发言{counter[0]}]:'

    return re.sub(r'\[发言\d+\]:', _repl, text)


SUMMARY_MERGE_INSTRUCTION = """你正在将同一场会议的多段局部纪要合并为一份统一纪要。
- 保留全部实质性内容(决议、行动项、数据、人名、机构), 仅去重相似条目。
- 严禁压缩或笼统化具体信息; 合并后长度应接近各段之和(去除重复后)。
- 结构按上述纪要框架统一, 节数可灵活。
- 不要新增原文没有的信息。"""


def _do_merge(text, knowledge_block, model_id=None):
    config = _get_llm_config(model_id)
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
            max_tokens=6000, enable_web_search=False,
        ).strip()
    except Exception as e:
        logger.warning(f'合并总结失败：{e}')
        return text


def _merge_summaries(parts, knowledge_block, model_id=None):
    """将多段局部总结合并为一份统一总结；过长时分块合并，最终合并若仍超长则退化为拼接，避免死循环。"""
    parts = [p for p in parts if p and p.strip()]
    if not parts:
        return ''
    if len(parts) == 1:
        return parts[0]
    combined = '\n\n'.join(f'【第 {i + 1} 部分】\n{p}' for i, p in enumerate(parts))
    if len(combined) <= CHUNK_SIZE:
        return _do_merge(combined, knowledge_block, model_id)
    sub = [_do_merge(c, knowledge_block, model_id) for c in _chunk_text(combined)]
    final = '\n\n'.join(sub)
    if len(final) <= CHUNK_SIZE:
        return _do_merge(final, knowledge_block, model_id)
    return final


def summarize_meeting(transcript: str, model_id=None, progress_callback=None) -> dict:
    """三版总结 (串行调用, 避免截断)

    超长录音（> CHUNK_SIZE）按块分段处理各阶段，最后将多段局部总结合并为统一总结，
    避免任一阶段因输入超长被截断而丢失内容。

    进度上报: 若提供 progress_callback, 将以 dict 形式回调:
        {'stage': 阶段名, 'stage_index': 1-3, 'stage_total': 3,
         'block': 当前块序号, 'block_total': 本阶段总块数,
         'pct': 总体百分比(0-99), 'eta_sec': 预估剩余秒数}

    Returns:
        dict: {'segmented': str, 'clean': str, 'summary': str}
    """
    if not transcript or not transcript.strip():
        return {'segmented': '', 'clean': '', 'summary': '无录音内容，无法生成总结。'}

    config = _get_llm_config(model_id)
    knowledge_block = build_meeting_knowledge(transcript[:2000])
    echo_chunk, _ = _echo_chunk_params(config)
    summary_chunk = _summary_chunk_chars(config)

    # ----- 进度统计 -----
    phase1_blocks = max(1, len(_chunk_text(transcript, echo_chunk, ECHO_OVERLAP_CHARS)))
    phase2_blocks = phase1_blocks  # segmented 长度≈原文, 块数相近
    phase3_blocks = 1  # 阶段2完成后基于 clean 精确修正
    total_blocks = [phase1_blocks + phase2_blocks + phase3_blocks]
    done_blocks = [0]
    start_time = [time.time()]
    last_pct = [0]  # 进度百分比单调不减，防止分母中途变化导致回退

    def _report(stage_label, stage_index, block, block_total):
        done_blocks[0] += 1
        pct = int(done_blocks[0] / max(total_blocks[0], 1) * 100)
        pct = max(pct, last_pct[0])  # 防进度回退
        last_pct[0] = pct
        elapsed = time.time() - start_time[0]
        per_block = elapsed / max(done_blocks[0], 1)
        remain = max(total_blocks[0] - done_blocks[0], 0)
        eta_sec = int(per_block * remain)
        if progress_callback:
            try:
                progress_callback({
                    'stage': stage_label,
                    'stage_index': stage_index,
                    'stage_total': 3,
                    'block': block,
                    'block_total': block_total,
                    'pct': min(pct, 99),
                    'eta_sec': eta_sec,
                })
            except Exception:
                pass

    # 阶段1：发言分段（内部按小块回写，保证 100% 保留原文；全局重排发言人编号）
    logger.info(f'阶段1/3: 发言分段 ({len(transcript)} 字输入)')
    segmented = segment_meeting(
        transcript, knowledge_block, model_id,
        progress_callback=lambda b, t: _report('发言分段', 1, b, t),
    )

    # 阶段2：清洁版（基于分段输出，内部同样按小块回写，避免截断丢内容）
    logger.info(f'阶段2/3: 清洁版 ({len(segmented)} 字输入)')
    clean = clean_meeting(
        segmented, knowledge_block, model_id,
        progress_callback=lambda b, t: _report('清洁整理', 2, b, t),
    )

    # 阶段3：摘要版（clean 与 segmented 分别切分，各自生成局部总结，再合并）
    # 修复: 之前把同一 clean 块同时当 transcript 与 segmented_text 传入，导致 SUMMARY_USER_PROMPT
    # 的「发言分段版」形同虚设；现两路分别切分并逐一配对。
    clean_chunks = _chunk_text(clean, summary_chunk, overlap=SUMMARY_OVERLAP_CHARS)
    seg_chunks = _chunk_text(segmented, summary_chunk, overlap=SUMMARY_OVERLAP_CHARS)
    # 两路分块数可能因阶段2极轻微去噪差 1，按索引对齐，缺失一侧填空串
    n3 = max(len(clean_chunks), len(seg_chunks))
    phase3_pairs = [
        (clean_chunks[i] if i < len(clean_chunks) else '',
         seg_chunks[i] if i < len(seg_chunks) else '')
        for i in range(n3)
    ]
    phase3_blocks = max(1, n3) + 1  # +1 代表最终合并
    # 在进入阶段3前一次性算准 total_blocks，配合 _report 的单调防回退，避免进度条倒退
    total_blocks[0] = phase1_blocks + phase2_blocks + phase3_blocks
    logger.info(f'阶段3/3: 摘要版 (clean={len(clean)} 字, {len(clean_chunks)} 块)')
    summary_parts = []
    for ci, (clean_c, seg_c) in enumerate(phase3_pairs, 1):
        summary_parts.append(summarize_meeting_inner(clean_c, seg_c, knowledge_block, model_id))
        _report('智能摘要', 3, ci, phase3_blocks)
    summary = _merge_summaries(summary_parts, knowledge_block, model_id)
    _report('智能摘要', 3, phase3_blocks, phase3_blocks)  # 合并完成

    return {
        'segmented': segmented,
        'clean': clean,
        'summary': summary,
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
