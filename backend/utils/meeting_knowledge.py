"""
会议知识库构建 — 从 DB 提取项目名称/企业名称/状态, 拼成 prompt 知识块。

仅输出名称列表 (不拼接进展/卡点/时间节点), 避免 context 过长。
供 text_summarizer.summarize_meeting() 注入到 SYSTEM prompt 中, 辅助 LLM 消歧同音/简称/错别字。
"""
import logging

logger = logging.getLogger(__name__)


def build_meeting_knowledge(transcript: str = '', max_projects: int = 50) -> str:
    """从 DB 提取项目名称+企业名称+状态, 构建 prompt 知识块。

    Args:
        transcript: 原始转写文本 (预留, 当前未使用; 后续可基于关键词过滤相关项目)
        max_projects: 最大项目数 (避免 context 过长)

    Returns:
        str: Markdown 格式的项目列表, 作为 SYSTEM prompt 后缀注入。
    """
    try:
        from models.investment import InvestmentProject
        from models.construction import ConstructionProject
    except ImportError as e:
        logger.warning(f'导入模型失败: {e}')
        return ''

    lines = []

    # 招商对接项目
    try:
        projects = InvestmentProject.query.filter_by(is_deleted=False)\
            .order_by(InvestmentProject.updated_at.desc().nulls_last())\
            .limit(max_projects).all()
        if projects:
            lines.append('### 招商对接项目')
            seen = set()
            for p in projects:
                key = (p.project_name, p.invest_enterprise)
                if key in seen:
                    continue
                seen.add(key)
                name = p.project_name or '(未命名)'
                enterprise = p.invest_enterprise or ''
                status = p.follow_status_code or ''
                status_label = _follow_status_label(status)
                if enterprise and status_label:
                    lines.append(f'- {name} ({enterprise}, {status_label})')
                elif enterprise:
                    lines.append(f'- {name} ({enterprise})')
                else:
                    lines.append(f'- {name}')
    except Exception as e:
        logger.warning(f'查询招商项目失败: {e}')

    # 在建项目
    try:
        constructions = ConstructionProject.query\
            .order_by(ConstructionProject.updated_at.desc().nulls_last())\
            .limit(max_projects).all()
        if constructions:
            lines.append('')
            lines.append('### 在建项目')
            seen = set()
            for c in constructions:
                name = c.project_name or '(未命名)'
                if name in seen:
                    continue
                seen.add(name)
                status = c.dispatch_status_code or ''
                status_label = _dispatch_status_label(status)
                if status_label:
                    lines.append(f'- {name} ({status_label})')
                else:
                    lines.append(f'- {name}')
    except Exception as e:
        logger.warning(f'查询在建项目失败: {e}')

    return '\n'.join(lines)


def _follow_status_label(code: str) -> str:
    """招商项目跟进状态 code -> 中文标签"""
    mapping = {
        'following': '在谈',
        'signed': '已签约',
        'landed': '已落地',
        'suspended': '暂停',
        'terminated': '终止',
    }
    return mapping.get(code, code)


def _dispatch_status_label(code: str) -> str:
    """在建项目调度状态 code -> 中文标签"""
    mapping = {
        'dispatching': '调度中',
        'progressing': '在建',
        'completed': '已完工',
        'paused': '暂停',
    }
    return mapping.get(code, code)
