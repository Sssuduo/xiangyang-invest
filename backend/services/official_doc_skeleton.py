"""
公文范本骨架解析服务（模式 B：框架复用）

将上传的过往公文解析为结构化骨架：
- 每段标注 type: 'fixed'（定型段落，原文保留）| 'slot'（数据槽位，待替换）
- slot 段标注 slot_key（槽位语义，如 project_name/amount/date/percentage）
- 保留标题层级（level 1/2/3）

流程：上传范本时调用 LLM 解析 → 骨架 JSON 存入 OfficialDocTemplate.structure
生成新文档时：fixed 段原文保留 + slot 段用新数据生成后原位替换
"""
import json
import logging
import re

logger = logging.getLogger(__name__)

SKELETON_SYSTEM_PROMPT = """你是公文结构解析引擎。分析用户提供的公文范本，输出其结构骨架 JSON。

## 解析规则
1. 按标题层级拆分为段（一级"一、"、二级"（一）"、三级"1."等），每段包含标题与正文摘要
2. 每段标注 type：
   - "fixed"：定型段落——格式性、政策性、常规性表述，换数据时原文保留
   - "slot"：数据槽位——包含具体项目名、金额、日期、数量、百分比等业务数据的段落，需要替换
3. slot 段标注 slot_key（槽位语义类型，用英文）：
   project_name（项目名称）、amount（金额）、date（日期）、percentage（百分比）、
   count（数量）、enterprise（企业名称）、area（面积）、other（其他）
4. 标题层级标 level：1（一、）/ 2（（一））/ 3（1.）
5. 正文摘要控制在 60 字以内

## 输出格式（严格 JSON 数组，不要任何说明文字）
[
  {
    "id": "1",
    "level": 1,
    "heading": "一、招商引资总体情况",
    "type": "fixed",
    "summary": "开篇总体情况概述",
    "original": "该段原文（fixed 段保留用，slot 段可留空）",
    "slot_key": null
  },
  {
    "id": "2",
    "level": 2,
    "heading": "（一）重点项目建设",
    "type": "slot",
    "summary": "列出重点项目名称与投资额",
    "original": "",
    "slot_key": "project_name"
  }
]
"""

SKELETON_USER_TEMPLATE = """请解析以下公文范本的结构骨架：

{content}"""


def _get_active_llm():
    """获取启用的 LLM 模型配置（与 text_summarizer 一致的优先排序）"""
    try:
        from models.ai import LLMModel
        model = LLMModel.query.filter_by(is_active=True) \
            .order_by(LLMModel.sort_order).first()
        if not model:
            return None
        return {
            'api_base_url': model.api_base_url,
            'api_key': model.api_key,
            'model_name': model.model_name,
            'provider': model.provider,
        }
    except Exception:
        return None


def parse_skeleton(content: str, model_id=None) -> list:
    """解析范本内容为骨架 JSON 列表。

    LLM 失败时回退到正则解析（仅提取标题层级，全部标 fixed）。
    """
    if not content or not content.strip():
        return []

    config = _get_active_llm()
    if not config:
        logger.warning('[skeleton] 无可用 LLM，回退正则解析')
        return _fallback_regex_parse(content)

    from services.llm_service import call_llm

    try:
        result = call_llm(
            config,
            [
                {'role': 'system', 'content': SKELETON_SYSTEM_PROMPT},
                {'role': 'user', 'content': SKELETON_USER_TEMPLATE.format(content=content[:12000])},
            ],
            temperature=0.2,
            max_tokens=6000,
            enable_web_search=False,
        ).strip()

        skeleton = _extract_json(result)
        if skeleton:
            # 校验并归一化
            return [_normalize_block(b, i) for i, b in enumerate(skeleton, 1) if isinstance(b, dict)]
        logger.warning('[skeleton] LLM 返回空骨架，回退正则解析')
        return _fallback_regex_parse(content)
    except Exception as e:
        logger.warning(f'[skeleton] LLM 解析失败：{e}，回退正则解析')
        return _fallback_regex_parse(content)


def _extract_json(text: str):
    """从 LLM 输出提取 JSON 数组"""
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    m = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    m = re.search(r'\[[\s\S]*\]', text)
    if m:
        try:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


def _normalize_block(block: dict, idx: int) -> dict:
    """归一化骨架块字段"""
    return {
        'id': str(block.get('id') or idx),
        'level': int(block.get('level') or 1),
        'heading': (block.get('heading') or '').strip(),
        'type': block.get('type') if block.get('type') in ('fixed', 'slot') else 'fixed',
        'summary': (block.get('summary') or '').strip(),
        'original': block.get('original') or '',
        'slot_key': block.get('slot_key') if block.get('type') == 'slot' else None,
    }


def _fallback_regex_parse(content: str) -> list:
    """回退：正则提取标题层级，全部标 fixed（保留原文可用）"""
    skeleton = []
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        if re.match(r'^[一二三四五六七八九十]+、', line):
            level = 1
        elif re.match(r'^（[一二三四五六七八九十]+）', line):
            level = 2
        elif re.match(r'^\d+[\.、]', line):
            level = 3
        else:
            continue
        skeleton.append({
            'id': str(len(skeleton) + 1),
            'level': level,
            'heading': line,
            'type': 'fixed',
            'summary': '',
            'original': '',
            'slot_key': None,
        })
    return skeleton


def generate_from_skeleton(skeleton: list, replacements: dict, model_id=None) -> str:
    """基于骨架逐段生成成文。

    - fixed 段：优先用 original（原文保留），无原文时用 heading 占位
    - slot 段：用槽位数据（replacements[slot_key]）生成正文

    Args:
        skeleton: 骨架列表（parse_skeleton 的输出，用户可编辑）
        replacements: 槽位数据映射 {slot_key: 数据文本}，
                      如 {'project_name': '项目A、项目B', 'amount': '总投资20亿元'}
        model_id: LLM 模型 ID（可选）

    Returns:
        str: 生成的 Markdown 成文
    """
    config = _get_active_llm()
    if not config:
        return _fallback_assemble(skeleton, replacements)

    from services.llm_service import call_llm

    # 组装提示词：骨架 + 槽位数据
    skeleton_desc = []
    for b in skeleton:
        line = f"- id={b['id']} level={b['level']} type={b['type']} heading={b.get('heading','')}"
        if b['type'] == 'slot':
            key = b.get('slot_key') or 'other'
            data = replacements.get(key, '')
            line += f" slot_key={key} 新数据={data if data else '（无，请按上下文合理撰写）'}"
        else:
            orig = (b.get('original') or '').strip()
            line += f" 原文={orig[:80] if orig else '（无原文，请按 heading 与 summary 撰写）'}"
        skeleton_desc.append(line)

    system = """你是公文写作引擎。基于给定的结构骨架逐段生成公文正文。

## 规则
1. type=fixed 的段落：有原文则严格保留原文（只做格式整理）；无原文则按 heading 与 summary 撰写
2. type=slot 的段落：必须用新数据替换撰写，标题层级与行文风格与范本一致
3. 保持标题层级（一、/（一）/1.），输出为 Markdown
4. 全文连贯，段落之间自然衔接，不输出任何说明文字"""

    user = f"""## 结构骨架
{chr(10).join(skeleton_desc)}

请按骨架逐段生成完整公文正文（Markdown 格式）。"""

    try:
        result = call_llm(
            config,
            [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            temperature=0.5,
            max_tokens=8000,
            enable_web_search=False,
        ).strip()
        if result:
            return result
        logger.warning('[skeleton] 逐段生成返回空，回退本地拼装')
        return _fallback_assemble(skeleton, replacements)
    except Exception as e:
        logger.warning(f'[skeleton] 逐段生成失败：{e}，回退本地拼装')
        return _fallback_assemble(skeleton, replacements)


def _fallback_assemble(skeleton: list, replacements: dict) -> str:
    """本地兜底拼装：fixed 用原文/heading，slot 用新数据"""
    lines = []
    for b in skeleton:
        heading = b.get('heading') or ''
        if heading:
            lines.append(f'{"#" * min(max(int(b.get("level") or 1), 1), 3)} {heading}')
        if b['type'] == 'slot':
            key = b.get('slot_key') or 'other'
            data = replacements.get(key, '')
            lines.append(data if data else f'（{b.get("summary") or "待补充"}）')
        else:
            orig = (b.get('original') or '').strip()
            if orig:
                lines.append(orig)
            elif b.get('summary'):
                lines.append(b['summary'])
        lines.append('')
    return '\n'.join(lines).strip()
