"""
公文规范清洗服务 — PDF 导出前调用

将工作台账的录音总结内容（分段原文/清洁版/摘要版）用公文提示词清洗，
产出符合《党政机关公文格式》(GB/T 9704-2012) 的规范文稿，再交给 pdf_service 排版。

与清洁版解耦：清洁版保留原 LLM 框架不动，此服务仅在导出 PDF 时调用。
"""
import logging

logger = logging.getLogger(__name__)

# 公文规范清洗提示词（参照 GB/T 9704-2012 文稿规范）
OFFICIAL_CLEAN_SYSTEM_PROMPT = """您是专业的党政机关公文排版专员，严格遵循《党政机关公文格式》(GB/T 9704-2012) 标准。基于提供的会议录音总结原始素材，完成**文稿规范化润色**，产出可直接按公文格式排版的 Markdown 文本。所有输出必须 100% 基于原文信息，严禁编造、补充原文未提及的内容。

【一、结构重构规则】
1. 自动提炼规范标题：根据文档内容生成规范会议纪要标题，格式如《关于X月X日XX项目融资座谈会议纪要》，替换原文无规范标题的现状。
2. 补充公文前置导语：统一规范开头导语，整合原文开篇信息，规范表述时间、组织单位、参会主体、座谈核心议题，删除口语化断句、零散短句。
3. 按业务逻辑拆分固定一级章节，严格匹配原文信息，不增删核心业务数据：
   一、项目基础概况
   二、当前融资困难与资金缺口现状
   三、合作对接可行性及制约因素
   四、下一步实施路径
   五、要素保障事项
   六、政策申报与扶持资金争取
   七、其他同步洽谈事项
   （章节数量与命名根据实际内容灵活调整，无对应内容的章节省略）
4. 层级序号严格公文规范：一级标题「一、」；二级「（一）」；三级「1.」；四级「（1）」，原文所有圆点●、横杠-零散记录全部转化为标准层级序号。

【二、文字、数据、标点整改规则】
1. 口语清理：删除"提到、希望、认为、努力后、卡点"等口语化表述，替换为政府公务书面用语；修正原文断句碎片化、分句残缺问题，合并同类零散要点。
2. 标点统一：全文中文标点使用全角；数字、金额、百分比、吨/亩/万元等计量单位用半角；顿号统一为标准全角顿号，年份六角括号统一为标准〔〕。
3. 数据规整：所有资金、面积、产能、工期、成本数据单独梳理，统一格式，同类数据集中归类，不零散穿插段落；金额统一规范表述（如3000万元，不出现"1.1亿多元"模糊表述，调整为1.1亿余元）。
4. 人名、职务规范：原文人名、职务统一规范表述，职务前置或后置统一格式，不简写混乱。
5. 修正逻辑断层：原文多处内容中途截断、语句不完整的，根据上下文业务逻辑补全通顺书面表述，不丢失原有信息。
6. 区分项目主体：不同项目（如乳制品项目、可降解地膜项目）分块隔离，避免内容混杂；遗留协调事项单独成块，不和融资、配套内容混淆。

【三、输出格式要求】
1. 文档标题用 #（一级），章节用 ##（二级），条目用序号（一、/（一）/1./（1）），不使用圆点、横杠作为层级符号。
2. 全文无多余空行、无重复要点，同类内容合并，删除原文重复赘述语句。
3. 保留原始全部业务信息：资金缺口、建设进度、土地面积、蒸汽污水参数、基金规则、政策申报金额、遗留协调责任人全部完整保留，仅优化表述。
4. 输出直接为清洗后的 Markdown 文本，不加任何说明。"""


def official_clean(content: str, model_id=None) -> str:
    """用公文提示词清洗内容。

    长文本（> 3000 字）按块清洗后合并，避免 deepseek-v4-flash
    对长输入返回空串（实测 5000+ 字输入空返回，3000 字内正常）。

    Args:
        content: 原始内容（分段原文/清洁版/摘要版）
        model_id: LLM 模型 ID（可选）

    Returns:
        str: 清洗后的规范 Markdown；失败时返回原文（不阻塞导出）
    """
    if not content or not content.strip():
        return content or ''

    config = _get_llm_config(model_id)
    if not config:
        logger.warning('公文清洗：未配置 LLM 模型，返回原文')
        return content

    from services.llm_service import call_llm

    system = OFFICIAL_CLEAN_SYSTEM_PROMPT

    def _clean_chunk(chunk):
        user = f'请对以下会议录音总结内容进行公文规范化润色：\n\n{chunk}'
        try:
            result = call_llm(
                config,
                [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
                temperature=0.3,
                max_tokens=8192,
                enable_web_search=False,
            ).strip()
            return result if result else ''
        except Exception as e:
            logger.warning(f'公文清洗块失败：{e}')
            return ''

    # 分块清洗（每块 ≤ 2500 字，保证模型正常输出）
    MAX_CHUNK = 2500
    if len(content) <= MAX_CHUNK:
        result = _clean_chunk(content)
        if result:
            return result
        logger.warning('公文清洗：模型返回空串，返回原文')
        return content

    # 长文本分块：按段落边界切分
    parts = _chunk_text(content, MAX_CHUNK)
    cleaned_parts = []
    for p in parts:
        r = _clean_chunk(p)
        if r:
            cleaned_parts.append(r)
        else:
            cleaned_parts.append(p)  # 块清洗失败用原文

    merged = '\n\n'.join(cleaned_parts)
    if not merged.strip():
        return content
    return merged


def _chunk_text(text, size=2500):
    """按段落边界切分文本，避免在句中断开。"""
    if len(text) <= size:
        return [text]
    # 优先按换行切
    paragraphs = [p for p in text.split('\n') if p.strip()]
    chunks = []
    current = ''
    for p in paragraphs:
        if len(current) + len(p) > size and current:
            chunks.append(current)
            current = p
        else:
            current = (current + '\n' + p).strip()
    if current:
        chunks.append(current)
    # 若仍有超长段（单段超 size），按字符硬切
    final = []
    for c in chunks:
        if len(c) <= size:
            final.append(c)
        else:
            for i in range(0, len(c), size):
                final.append(c[i:i + size])
    return final


def _get_llm_config(model_id=None):
    """获取 LLM 配置（与 text_summarizer 共用逻辑）"""
    try:
        from models.ai import LLMModel
        query = LLMModel.query.filter_by(is_active=True)
        if model_id is not None:
            model = query.filter_by(id=model_id).first()
        else:
            model = query.order_by(LLMModel.sort_order).first()
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
