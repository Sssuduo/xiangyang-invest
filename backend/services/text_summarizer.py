"""
文字内容总结服务

将语音转写的长文本进行智能总结，提取关键信息。
优先使用项目已有的 LLM 大模型配置，若未配置则使用规则提取作为降级方案。
"""
import logging

logger = logging.getLogger(__name__)

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
