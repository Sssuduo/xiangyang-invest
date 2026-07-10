"""知识库共享常量 — CATEGORY_MAP 唯一来源

所有涉及知识库分类的模块统一引用此处，避免多文件重复定义导致不一致。
"""

CATEGORY_MAP = {
    'industry_policy': '产业政策',
    'park_info': '园区信息',
    'supporting': '配套能力',
    'land_cost': '土地成本',
    'case_study': '招商案例',
    'demand_pattern': '企业诉求',
    'market_data': '市场数据',
    'competitor': '周边竞争',
}

CATEGORY_OPTIONS = [{'code': k, 'name': v} for k, v in CATEGORY_MAP.items()]

# 保留别名兼容旧引用
CATEGORY_NAMES = CATEGORY_MAP

# 向量化阈值：知识库条目数超过此值后才启用向量语义搜索
KNOWLEDGE_EMBEDDING_THRESHOLD = 500
