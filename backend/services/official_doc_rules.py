"""
公文写作规则库与提示词组装（服务端）

将《公文写作算法》方法论沉淀在服务端，由后端统一组装 system / user 提示词，
前端只下发结构化字段（doc_type / style_config / material / projects_text / template_content），
避免把付费模型网关暴露为任意 system_prompt 的代理。
"""

# ============================================================
# 文体类型规则
# ============================================================
DOC_TYPE_RULES = {
    'work_summary': {
        'name': '工作总结',
        'structure': [
            {'title': '一、工作完成情况', 'type': '成绩+措施', 'ratio': 'N+V≥40%'},
            {'title': '二、存在问题及原因', 'type': '问题', 'ratio': '可选'},
            {'title': '三、下一步打算', 'type': '计划', 'ratio': 'V+N≥60%'}
        ],
        'rules': [
            'N+V（结果）占比应≥40%',
            '重点讲成绩、剧情、产品化名词',
            '存在问题部分看情况决定是否写',
            '首段必须包含“按·拿·推”结构'
        ]
    },
    'work_plan': {
        'name': '工作计划',
        'structure': [
            {'title': '一、工作目标', 'type': '目标'},
            {'title': '二、重点任务', 'type': '措施', 'ratio': 'V+N≥60%'},
            {'title': '三、保障措施', 'type': '措施'}
        ],
        'rules': [
            'V+N（措施）占比应≥60%',
            '几乎全部 V+N 结构',
            '数字为大概而非精准',
            '篇幅比工作总结短'
        ]
    },
    'work_report': {
        'name': '工作汇报',
        'structure': [
            {'title': '一、工作开展情况', 'type': '成绩+措施'},
            {'title': '二、存在问题', 'type': '问题'},
            {'title': '三、下一步计划', 'type': '计划'}
        ],
        'rules': [
            '首段必须包含“按·拿·推”结构',
            '重点讲成绩和产品化名词',
            '数据前置、量化优先',
            '结果在前、措施在后'
        ]
    },
    'speech': {
        'name': '领导讲话',
        'structure': [
            {'title': '一、思想意义层面', 'type': '务虚', 'note': '侧重“因”'},
            {'title': '二、核心工作', 'type': '务实'},
            {'title': '三、对内要求', 'type': '措施'}
        ],
        'rules': [
            '事前类：思想意义+核心工作+对内要求',
            '事中类：成绩+问题+核心工作+对内要求',
            '语言可适当口语化',
            '结尾用号召式结尾'
        ]
    },
    'research_report': {
        'name': '调研报告',
        'structure': [
            {'title': '一、调研背景', 'type': '背景'},
            {'title': '二、现状分析', 'type': '分析'},
            {'title': '三、对策建议', 'type': '措施'}
        ],
        'rules': [
            '经验型：调研对象成绩→经验→建议',
            '问题型：问题→原因→对策',
            '数据要精准',
            '建议要可操作'
        ]
    },
    'work_plan_detail': {
        'name': '工作方案',
        'structure': [
            {'title': '一、总体要求', 'type': '目标'},
            {'title': '二、主要任务', 'type': '措施'},
            {'title': '三、工作措施', 'type': '措施'}
        ],
        'rules': [
            '指导思想/基本原则/工作目标',
            '核心名词要突出',
            '工作要求要具体'
        ]
    },
    'advanced_deeds': {
        'name': '先进事迹',
        'structure': [
            {'title': '一、基本情况', 'type': '背景'},
            {'title': '二、主要事迹', 'type': '成绩'},
            {'title': '三、经验启示', 'type': '总结'}
        ],
        'rules': [
            '工作简报式：只有干货，没有水分',
            '通讯稿式：有故事性、有情节',
            '成绩要数字化',
            '用词要朴实'
        ]
    },
    'meeting_minutes': {
        'name': '会议纪要',
        'structure': [
            {'title': '会议基本情况', 'type': '背景'},
            {'title': '会议指出', 'type': '意义/方向'},
            {'title': '会议强调', 'type': '核心工作'},
            {'title': '会议要求', 'type': '对内要求'}
        ],
        'rules': [
            '只保留一把手最后决定的内容',
            '其他人发言全部删掉',
            '格式参照本单位过去纪要',
            '语言要精炼'
        ]
    }
}


# ============================================================
# 风格参数映射
# ============================================================
STYLE_MAPPING = {
    'detailLevel': {
        1: '只写关键词和结果，不展开',
        2: '简要描述，每点1-2句',
        3: '标准详略，每点3-5句',
        4: '详细展开，每点5-8句',
        5: '详实论述，每点展开背景、过程、分析'
    },
    'dataDensity': {
        1: '定性描述为主，少用数据',
        2: '关键节点配数据',
        3: '每段有1-2个数据支撑',
        4: '每点必有数据',
        5: '全量化，每句话都有数据或可验证事实'
    },
    'politicalStance': {
        1: '只谈业务，不提上级精神',
        2: '偶尔提及政策依据',
        3: '每部分开头点明政策来源',
        4: '每段必引上级精神',
        5: '高举高打，全程对标中央/省市要求'
    },
    'reflectionDepth': {
        1: '只报成绩，不提问题',
        2: '成绩为主，问题一笔带过',
        3: '成绩与问题均衡',
        4: '问题篇幅≥40%',
        5: '问题篇幅≥50%，深入分析原因'
    },
    'sentenceComplexity': {
        1: '短句直给，每句≤15字',
        2: '长短句结合',
        3: '排比/对仗工整，增强气势'
    }
}


def _clamp(value, lo, hi, default):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def get_doc_type_rules_prompt(doc_type):
    rule = DOC_TYPE_RULES.get(doc_type)
    if not rule:
        return ''

    structure_lines = []
    for i, s in enumerate(rule['structure'], 1):
        line = f"{i}. {s['title']}"
        if s.get('type'):
            line += f"（{s['type']}）"
        if s.get('ratio'):
            line += f" - {s['ratio']}"
        if s.get('note'):
            line += f" - {s['note']}"
        structure_lines.append(line)

    rules_lines = [f"- {r}" for r in rule['rules']]

    return f"""
## 当前文体：{rule['name']}

### 文体结构规范
{chr(10).join(structure_lines)}

### 文体特殊规则
{chr(10).join(rules_lines)}
"""


def get_style_prompt(style_config):
    sc = style_config or {}
    detail = _clamp(sc.get('detailLevel'), 1, 5, 3)
    data = _clamp(sc.get('dataDensity'), 1, 5, 3)
    stance = _clamp(sc.get('politicalStance'), 1, 5, 2)
    reflect = _clamp(sc.get('reflectionDepth'), 1, 5, 3)
    sentence = _clamp(sc.get('sentenceComplexity'), 1, 3, 2)

    return f"""
## 风格参数要求
- 详略度（{detail}/5）：{STYLE_MAPPING['detailLevel'][detail]}
- 数据密度（{data}/5）：{STYLE_MAPPING['dataDensity'][data]}
- 政治站位（{stance}/5）：{STYLE_MAPPING['politicalStance'][stance]}
- 反思深度（{reflect}/5）：{STYLE_MAPPING['reflectionDepth'][reflect]}
- 句式复杂度（{sentence}/3）：{STYLE_MAPPING['sentenceComplexity'][sentence]}
"""


def _template_block(template_content):
    if not template_content:
        return ''
    return f"""
## 参考范本（请严格沿用其格式、标题层级、行文风格与段落结构，
## 仅用上方最新素材 / 项目数据替换其中的具体内容与数据，保持文体格式不变）
{template_content}
"""


def build_outline_system_prompt(doc_type, style_config):
    return f"""你是严格按照《公文写作算法》六层技能矩阵训练的 AI 公文撰写引擎。

{get_doc_type_rules_prompt(doc_type)}

## 提纲生成规则
1. 遵循“成分分析”：每个提纲点必须是“措施”、“目标”、“成绩”或“计划”之一
2. 遵循“六大逻辑”：结论先行、以上统下、归类分组、逻辑递进
3. 遵循“工作周期”：体现起始→推进→收尾的完整周期
4. 标题分形：全文标题 → 章节标题 → 段落主题句，逐级细化同一核心命题
5. 提纲到三级：一、（一）1.

{get_style_prompt(style_config)}

## 输出格式
返回 JSON 数组，每项包含 id、title、children，结构如下：
[
  {{ "id": "1", "title": "一、开展工作情况", "children": [
    {{ "id": "1-1", "title": "（一）招商引资成效", "children": [] }},
    {{ "id": "1-2", "title": "（二）主要做法", "children": [] }}
  ]}}
]
"""


def build_outline_user_prompt(material, projects_text, template_content):
    material = material or {}
    prompt = f"## 写作主题\n{material.get('title', '')}\n\n"

    if material.get('background'):
        prompt += f"## 背景依据\n{material['background']}\n\n"
    if material.get('practices'):
        prompt += f"## 主要做法与成效\n{material['practices']}\n\n"
    if material.get('problems'):
        prompt += f"## 存在问题\n{material['problems']}\n\n"
    if material.get('nextSteps'):
        prompt += f"## 下一步计划\n{material['nextSteps']}\n\n"

    if projects_text:
        prompt += f"## 参考项目数据\n{projects_text}\n\n"

    prompt += _template_block(template_content)

    prompt += "请根据以上素材，生成符合规范的公文详细提纲（按输出格式返回 JSON）。"
    return prompt


def build_document_system_prompt(doc_type, style_config):
    return f"""你是严格按照《公文写作算法》训练的 AI 公文撰写引擎。

## 核心基因规则
1. **V+N 原则**：文章后半部分必须全部使用 V+N 结构（动词+名词）表达措施
   - 正确：推进项目建设、强化制度建设、深化协同联动
   - 错误：项目建设已推进（这是 N+V，只能在前半部分使用）
2. **N+V 原则**：文章前半部分可使用 N+V 结构表达成绩
   - 正确：重大项目落地见效、突出问题整改到位
3. **V+N 纯粹性铁律**：
   - 不以主语开头（不写“我们推进...”）
   - 逗号之间不超过25字
   - 尽量不用“的”字

## 句式规则（四大金刚）
每个句子遵循：目标 → 过程 → 措施(V+N) → 结果(N+V)

## 首段规则（按·拿·推）
首段必须包含：
- 按：政策依据/上级要求/背景形势
- 拿：具体做法/措施组合
- 推：推动实现的成效/目标

## 段落规则
1. 结论先行：段首亮观点/成绩/判断
2. 以上统下：先讲上级部署，再讲本级落实
3. 虚实搭配：务虚（站位/意义）+ 务实（具体做法/数据）交替
4. 因果串联：把原因、过程、结果串成完整链路

## 拔高技巧
1. 地空对接：将具体工作与宏观政策对接
2. 概念封装：把分散做法提炼为有辨识度的概念（如“三抓三促”）
3. 隔山打牛：通过A事项间接支撑B事项论点

{get_doc_type_rules_prompt(doc_type)}
{get_style_prompt(style_config)}

## 严禁事项
- 禁止空洞套话（高度重视/积极推进/切实抓好）
- 禁止口语化表达
- 禁止以“我们”“本单位”开头
- 禁止“非常”“特别”“极其”等过度主观词

## 输出格式
直接输出正文，用 Markdown 格式标记标题层级：
# 一级标题
## 二级标题
### 三级标题
"""


def build_document_user_prompt(outline, material, projects_text, template_content):
    material = material or {}
    prompt = f"## 文章提纲\n{outline}\n\n" if outline else "## 文章提纲\n（请按文体规范自行拟定提纲）\n\n"
    prompt += f"## 写作主题\n{material.get('title', '')}\n\n"

    if material.get('background'):
        prompt += f"### 背景依据\n{material['background']}\n\n"
    if material.get('practices'):
        prompt += f"### 主要做法与成效\n{material['practices']}\n\n"
    if material.get('problems'):
        prompt += f"### 存在问题\n{material['problems']}\n\n"
    if material.get('nextSteps'):
        prompt += f"### 下一步计划\n{material['nextSteps']}\n\n"

    if projects_text:
        prompt += f"## 参考项目数据\n{projects_text}\n\n"

    prompt += _template_block(template_content)

    prompt += "请严格按照提纲结构，运用 V+N/N+V 基因规则，生成完整的公文正文。"
    return prompt
