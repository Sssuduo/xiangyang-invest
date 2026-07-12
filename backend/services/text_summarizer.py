"""
文字内容总结服务

将语音转写的长文本进行智能总结，提取关键信息。
优先使用项目已有的 LLM 大模型配置，若未配置则使用规则提取作为降级方案。

V15.0 新增:
- summarize_meeting(transcript): 三版输出 (发言分段 + 清洁版 + 摘要版)
- build_meeting_knowledge(): 项目名称消歧知识注入
- _parse_meeting_output(): 拆分 LLM 三版输出
"""
import logging
import re

logger = logging.getLogger(__name__)

# ===================== V14 及以前的单版 prompt (保留向后兼容) =====================

# 总结提示词模板
SUMMARY_SYSTEM_PROMPT = """你是一个专业的活动/会议记录总结助手。请根据以下录音转写文本，进行内容总结。

总结要求：
1. **核心主题**：用一句话概括录音的主要内容
2. **关键要点**：列出 3-5 条关键信息要点（每条一句话）
3. **参与方/人员**：提取文中提及的人员、单位、企业名称
4. **后续事项**：提取需要跟进的事项或行动计划
5. **总结段落**：用一段话（100-200字）简洁概括全文

格式要求：
- 使用 Markdown 格式输出
- 每条要点前用 "- " 开头
- 若某项没有相关信息，写"无"

以下是录音转写内容："""


# ===================== V15.0 三版 prompt (结构化总结) =====================

MEETING_SYSTEM_PROMPT = """您是专业的政务招商会议文本整理专员, 熟悉招商引资、项目落地、园区配套、要素保障等领域的专有名词与工作流程。所有输出必须 100% 基于原文信息, 严禁编造、补充任何原文未提及的内容。

【本次会议关联的项目名称 (供消歧参考, 请勿凭空引入)】
{meeting_knowledge}

核心任务: 接收原始会议语音转写文本, 完成以下 3 步输出:

1. 【发言分段】识别原文中的发言轮次, 在每轮发言前插入换行+发言标记 (格式: [发言X]:), 仅做切断分段, 不修改原文措辞/内容。
2. 【清洁版】剔除嗯/啊/重复句/无关语气词; 还原谐音错别字、断句错误; 统一专有名词（参考上方知识库）; 多人对话按议题整合为连贯的正式陈述; 按「会议开场→议题讨论→工作部署→补充事项」分二三级标题；不遗漏卡点、时间节点、工作要求。
3. 【摘要版】高度结构化, 强制覆盖 4 维度:
   - 会议议程概述 (会议主题、核心目的、议程与参会主体)
   - 核心内容与关键信息 (核心议题、项目进展、核心堵点、讨论共识)
   - 决议与行动事项 (任务内容+责任主体+完成时限+交付要求)
   - 会议总结 (定调+整体工作要求+后续推进方向)

输出格式 (严格 Markdown):
## 发言分段
(分段后原文)
## 清洁版
(内容)
## 摘要版
(内容)"""


MEETING_USER_PROMPT = """请基于以下原始会议语音转写文本, 严格按照规则生成发言分段、清洁版和摘要版:

{transcript}"""


# ===================== V14 旧版函数 (保留向后兼容) =====================


def _get_llm_config():
    """获取激活的 LLM 配置"""
    try:
        from models.ai import LLMModel
        model = LLMModel.query.filter_by(is_active=True).order_by(LLMModel.sort_order).first()
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


def summarize_with_llm(text):
    """
    使用 LLM 大模型总结文字内容

    Args:
        text: 转写文本（可能很长）

    Returns:
        str: Markdown 格式的总结文本
    """
    if not text or not text.strip():
        return '无录音内容，无法生成总结。'

    config = _get_llm_config()
    if not config:
        logger.info('未配置 LLM 大模型，使用规则提取方式生成摘要')
        return summarize_with_rules(text)

    from services.llm_service import call_llm

    # 限制输入长度（避免 token 超限）
    max_input_chars = 30000
    truncated_text = text if len(text) <= max_input_chars else text[:max_input_chars] + '\n\n[文本过长，已截断]'

    messages = [
        {'role': 'system', 'content': SUMMARY_SYSTEM_PROMPT},
        {'role': 'user', 'content': truncated_text}
    ]

    try:
        llm_config = {
            'api_base_url': config['api_base_url'],
            'api_key': config['api_key'],
            'model_name': config['model_name']
        }
        summary = call_llm(llm_config, messages, temperature=0.3, max_tokens=2000)
        logger.info(f'LLM 总结完成，长度 {len(summary)} 字符')
        return summary
    except Exception as e:
        logger.warning(f'LLM 总结失败，降级为规则提取：{e}')
        return summarize_with_rules(text)


def summarize_with_rules(text):
    """
    基于规则的文字内容总结（降级方案）

    当 LLM 不可用时，使用简单的规则提取关键信息：
    1. 提取前几段作为摘要
    2. 搜索关键实体（单位名、人名等）
    3. 提取含有关键动词的句子

    Args:
        text: 转写文本

    Returns:
        str: Markdown 格式的总结文本
    """
    import re

    if not text or not text.strip():
        return '无录音内容，无法生成总结。'

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # 1. 核心主题：取前 80 字
    first_part = text[:80].strip()
    theme = first_part + ('...' if len(text) > 80 else '')

    # 2. 关键要点：取每段首句（最多 5 条）
    key_points = []
    for line in lines:
        sentence = line.split('。')[0].split('；')[0].strip()
        if len(sentence) > 8 and len(sentence) < 80:
            key_points.append(sentence)
            if len(key_points) >= 5:
                break

    if not key_points:
        key_points = ['内容过于简短，无法提取要点']

    # 3. 提取时间/日期
    time_patterns = re.findall(
        r'(\d{4}[-年]\d{1,2}[-月]\d{1,2}[日号]|\d{1,2}月\d{1,2}[日号]|[上下]午\d{1,2}[点时]|星期[一二三四五六日天])',
        text
    )
    time_mentions = list(set(time_patterns))[:5] if time_patterns else ['无']

    # 4. 提取可能出现的人员/单位
    entity_patterns = re.findall(
        r'([A-Z\u4e00-\u9fff]{2,}(?:公司|集团|企业|部门|局|委|办|中心|研究院|协会|商会|银行|基金|投资)|(?:王|李|张|刘|陈|杨|赵|黄|周|吴|徐|孙|胡|朱|高|林|何|郭|马)[\u4e00-\u9fff]{1,2}(?:先生|女士|总|经理|局长|处长|科长|主任|董|书记|工|老师|教授|博士))',
        text
    )
    entities = list(set(entity_patterns))[:8] if entity_patterns else ['无']

    # 5. 提取后续事项（含有"需要、将、计划、安排、落实、推进、完成"的句子）
    action_keywords = ['需要', '将要', '计划', '安排', '落实', '推进', '完成', '下一步', '后续', '尽快', '预期']
    actions = []
    for line in lines:
        for kw in action_keywords:
            if kw in line and len(line) > 10:
                actions.append(line)
                break
            if len(actions) >= 3:
                break

    # 组装 Markdown 输出
    result = f"""## 录音内容总结

### 核心主题
{theme}

### 关键要点
{chr(10).join('- ' + p for p in key_points)}

### 提及时间
{chr(10).join('- ' + t for t in time_mentions)}

### 涉及单位/人员
{chr(10).join('- ' + e for e in entities)}

### 后续事项
{chr(10).join('- ' + a for a in actions) if actions else '- 未明确提及后续事项'}

---
*（注：此总结由规则引擎自动生成。配置 LLM 大模型可获得更准确的总结结果）*
"""
    return result


# ===================== V15.0 三版总结函数 =====================

def build_meeting_knowledge(transcript: str = '', max_projects: int = 50) -> str:
    """构建项目名称知识块 (委托给 utils.meeting_knowledge)"""
    from utils.meeting_knowledge import build_meeting_knowledge as _build
    return _build(transcript, max_projects)


def summarize_meeting(transcript: str) -> dict:
    """三版总结 (发言分段 + 清洁版 + 摘要版)。

    Args:
        transcript: 原始 ASR 转写文本

    Returns:
        dict: {'segmented': str, 'clean': str, 'summary': str}
    """
    if not transcript or not transcript.strip():
        return {'segmented': '', 'clean': '', 'summary': '无录音内容，无法生成总结。'}

    config = _get_llm_config()
    if not config:
        logger.info('未配置 LLM 大模型，无法生成结构化总结')
        return {'segmented': '', 'clean': '', 'summary': '（未配置 AI 模型，请先配置 LLM 模型后使用此功能）'}

    from services.llm_service import call_llm

    # 构建知识块
    knowledge_block = build_meeting_knowledge(transcript[:2000])  # 仅前 2000 字作为知识库采样

    # 限制输入长度
    max_input_chars = 30000
    truncated_text = transcript if len(transcript) <= max_input_chars else transcript[:max_input_chars] + '\n\n[文本过长，已截断]'

    system_prompt = MEETING_SYSTEM_PROMPT.replace('{meeting_knowledge}', knowledge_block)
    user_prompt = MEETING_USER_PROMPT.replace('{transcript}', truncated_text)

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt}
    ]

    try:
        llm_output = call_llm(config, messages, temperature=0.3, max_tokens=4000)
        logger.info(f'会议结构化总结完成，输出长度 {len(llm_output)} 字符')
        return _parse_meeting_output(llm_output)
    except Exception as e:
        logger.warning(f'会议结构化总结失败: {e}')
        return {'segmented': '', 'clean': '', 'summary': f'总结生成失败: {str(e)[:200]}'}


def _parse_meeting_output(text: str) -> tuple[str, str, str]:
    """从 LLM 输出拆分 segmented + clean + summary。

    支持多种分隔格式:
    - ## 发言分段 / ## 清洁版 / ## 摘要版 (V15.0 标准格式)
    - --- 三段分割 (fallback)

    返回: {'segmented': str, 'clean': str, 'summary': str}
    """
    if not text:
        return {'segmented': '', 'clean': '', 'summary': ''}

    # 1. 尝试按 ## 发言分段 / ## 清洁版 / ## 摘要版 切分
    def _extract_section(header_pattern: str, text: str) -> str:
        m = re.search(header_pattern, text)
        if not m:
            return ''
        start = m.end()
        # 找到下一个 ## 一级标题或文本结尾
        next_m = re.search(r'\n## [^#]', text[start:])
        end = start + next_m.start() if next_m else len(text)
        return text[start:end].strip()

    segmented = _extract_section(r'## 发言分段', text)
    clean = _extract_section(r'## 清洁版', text)
    summary = _extract_section(r'## 摘要版', text)

    # 2. fallback: 三段分割
    if not (segmented or clean or summary):
        parts = [p.strip() for p in re.split(r'\n---+\n|\n## ', text) if p.strip()]
        if len(parts) >= 3:
            segmented, clean, summary = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            segmented, clean, summary = '', parts[0], parts[1]
        elif len(parts) == 1:
            segmented, clean, summary = '', '', parts[0]

    return {'segmented': segmented, 'clean': clean, 'summary': summary}


def get_meeting_prompt_templates() -> tuple[str, str]:
    """返回 (MEETING_SYSTEM_PROMPT, MEETING_USER_PROMPT) 供前端预览。"""
    return MEETING_SYSTEM_PROMPT, MEETING_USER_PROMPT
