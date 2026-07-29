// 文体类型规则库 - 基于《公文写作算法》Skill

export const docTypes = [
  { code: 'work_summary', name: '工作总结', icon: '📊' },
  { code: 'work_plan', name: '工作计划', icon: '📋' },
  { code: 'work_report', name: '工作汇报', icon: '📝' },
  { code: 'speech', name: '领导讲话', icon: '🎤' },
  { code: 'research_report', name: '调研报告', icon: '🔍' },
  { code: 'work_plan_detail', name: '工作方案', icon: '📑' },
  { code: 'advanced_deeds', name: '先进事迹', icon: '🏆' },
  { code: 'meeting_minutes', name: '会议纪要', icon: '📅' }
]

export const docTypeRules = {
  work_summary: {
    name: '工作总结',
    structure: [
      { title: '一、工作完成情况', type: '成绩+措施', ratio: 'N+V≥40%' },
      { title: '二、存在问题及原因', type: '问题', ratio: '可选' },
      { title: '三、下一步打算', type: '计划', ratio: 'V+N≥60%' }
    ],
    rules: [
      'N+V（结果）占比应≥40%',
      '重点讲成绩、剧情、产品化名词',
      '存在问题部分看情况决定是否写',
      '首段必须包含"按·拿·推"结构'
    ]
  },
  work_plan: {
    name: '工作计划',
    structure: [
      { title: '一、工作目标', type: '目标' },
      { title: '二、重点任务', type: '措施', ratio: 'V+N≥60%' },
      { title: '三、保障措施', type: '措施' }
    ],
    rules: [
      'V+N（措施）占比应≥60%',
      '几乎全部 V+N 结构',
      '数字为大概而非精准',
      '篇幅比工作总结短'
    ]
  },
  work_report: {
    name: '工作汇报',
    structure: [
      { title: '一、工作开展情况', type: '成绩+措施' },
      { title: '二、存在问题', type: '问题' },
      { title: '三、下一步计划', type: '计划' }
    ],
    rules: [
      '首段必须包含"按·拿·推"结构',
      '重点讲成绩和产品化名词',
      '数据前置、量化优先',
      '结果在前、措施在后'
    ]
  },
  speech: {
    name: '领导讲话',
    structure: [
      { title: '一、思想意义层面', type: '务虚', note: '侧重"因"' },
      { title: '二、核心工作', type: '务实' },
      { title: '三、对内要求', type: '措施' }
    ],
    rules: [
      '事前类：思想意义+核心工作+对内要求',
      '事中类：成绩+问题+核心工作+对内要求',
      '语言可适当口语化',
      '结尾用号召式结尾'
    ]
  },
  research_report: {
    name: '调研报告',
    structure: [
      { title: '一、调研背景', type: '背景' },
      { title: '二、现状分析', type: '分析' },
      { title: '三、对策建议', type: '措施' }
    ],
    rules: [
      '经验型：调研对象成绩→经验→建议',
      '问题型：问题→原因→对策',
      '数据要精准',
      '建议要可操作'
    ]
  },
  work_plan_detail: {
    name: '工作方案',
    structure: [
      { title: '一、总体要求', type: '目标' },
      { title: '二、主要任务', type: '措施' },
      { title: '三、工作措施', type: '措施' }
    ],
    rules: [
      '指导思想/基本原则/工作目标',
      '核心名词要突出',
      '工作要求要具体'
    ]
  },
  advanced_deeds: {
    name: '先进事迹',
    structure: [
      { title: '一、基本情况', type: '背景' },
      { title: '二、主要事迹', type: '成绩' },
      { title: '三、经验启示', type: '总结' }
    ],
    rules: [
      '工作简报式：只有干货，没有水分',
      '通讯稿式：有故事性、有情节',
      '成绩要数字化',
      '用词要朴实'
    ]
  },
  meeting_minutes: {
    name: '会议纪要',
    structure: [
      { title: '会议基本情况', type: '背景' },
      { title: '会议指出', type: '意义/方向' },
      { title: '会议强调', type: '核心工作' },
      { title: '会议要求', type: '对内要求' }
    ],
    rules: [
      '只保留一把手最后决定的内容',
      '其他人发言全部删掉',
      '格式参照本单位过去纪要',
      '语言要精炼'
    ]
  }
}

// 获取文体规则提示词
export function getDocTypeRulesPrompt(docType) {
  const rule = docTypeRules[docType]
  if (!rule) return ''

  return `
## 当前文体：${rule.name}

### 文体结构规范
${rule.structure.map((s, i) => `${i + 1}. ${s.title}${s.type ? '（' + s.type + '）' : ''}${s.ratio ? ' - ' + s.ratio : ''}${s.note ? ' - ' + s.note : ''}`).join('\n')}

### 文体特殊规则
${rule.rules.map(r => `- ${r}`).join('\n')}
`
}

// 风格参数映射
export const styleMapping = {
  detailLevel: {
    1: '只写关键词和结果，不展开',
    2: '简要描述，每点1-2句',
    3: '标准详略，每点3-5句',
    4: '详细展开，每点5-8句',
    5: '详实论述，每点展开背景、过程、分析'
  },
  dataDensity: {
    1: '定性描述为主，少用数据',
    2: '关键节点配数据',
    3: '每段有1-2个数据支撑',
    4: '每点必有数据',
    5: '全量化，每句话都有数据或可验证事实'
  },
  politicalStance: {
    1: '只谈业务，不提上级精神',
    2: '偶尔提及政策依据',
    3: '每部分开头点明政策来源',
    4: '每段必引上级精神',
    5: '高举高打，全程对标中央/省市要求'
  },
  reflectionDepth: {
    1: '只报成绩，不提问题',
    2: '成绩为主，问题一笔带过',
    3: '成绩与问题均衡',
    4: '问题篇幅≥40%',
    5: '问题篇幅≥50%，深入分析原因'
  },
  sentenceComplexity: {
    1: '短句直给，每句≤15字',
    2: '长短句结合',
    3: '排比/对仗工整，增强气势'
  }
}

// 生成风格提示词
export function getStylePrompt(styleConfig) {
  return `
## 风格参数要求
- 详略度（${styleConfig.detailLevel}/5）：${styleMapping.detailLevel[styleConfig.detailLevel]}
- 数据密度（${styleConfig.dataDensity}/5）：${styleMapping.dataDensity[styleConfig.dataDensity]}
- 政治站位（${styleConfig.politicalStance}/5）：${styleMapping.politicalStance[styleConfig.politicalStance]}
- 反思深度（${styleConfig.reflectionDepth}/5）：${styleMapping.reflectionDepth[styleConfig.reflectionDepth]}
- 句式复杂度（${styleConfig.sentenceComplexity}/3）：${styleMapping.sentenceComplexity[styleConfig.sentenceComplexity]}
`
}

// 内置模板
export const builtinTemplates = [
  {
    id: 'blank',
    name: '空白文档',
    docType: null,
    isBuiltin: true,
    structure: []
  },
  {
    id: 'investment_report',
    name: '招商情况汇报',
    docType: 'work_report',
    isBuiltin: true,
    structure: [
      { id: '1', title: '一、工作开展情况', children: [
        { id: '1-1', title: '（一）招商引资成效' },
        { id: '1-2', title: '（二）主要做法' }
      ]},
      { id: '2', title: '二、存在问题', children: [] },
      { id: '3', title: '三、下一步计划', children: [] }
    ]
  },
  {
    id: 'project_progress',
    name: '项目推进情况报告',
    docType: 'work_report',
    isBuiltin: true,
    structure: [
      { id: '1', title: '一、项目概况', children: [] },
      { id: '2', title: '二、推进情况', children: [
        { id: '2-1', title: '（一）已完成工作' },
        { id: '2-2', title: '（二）正在推进工作' }
      ]},
      { id: '3', title: '三、存在问题', children: [] },
      { id: '4', title: '四、下步打算', children: [] }
    ]
  },
  {
    id: 'work_summary',
    name: '工作总结',
    docType: 'work_summary',
    isBuiltin: true,
    structure: [
      { id: '1', title: '一、工作完成情况', children: [
        { id: '1-1', title: '（一）主要成绩' },
        { id: '1-2', title: '（二）具体做法' }
      ]},
      { id: '2', title: '二、存在问题及原因', children: [] },
      { id: '3', title: '三、下一步打算', children: [] }
    ]
  },
  {
    id: 'speech',
    name: '领导讲话',
    docType: 'speech',
    isBuiltin: true,
    structure: [
      { id: '1', title: '一、统一思想，提高认识', children: [] },
      { id: '2', title: '二、明确任务，突出重点', children: [] },
      { id: '3', title: '三、加强领导，狠抓落实', children: [] }
    ]
  }
]
