"""
揭榜挂帅七步工作法 — 阶段定义与状态机

七步：需求征集 → 专家论证 → 发榜公告 → 揭榜评审 → 任务签订 → 过程管理 → 绩效评价
终止态：rejected(论证驳回) / failed(流标) / cancelled(终止/取消)

设计原则：
- 阶段流转合法性由本模块统一校验（非法流转抛 BiddingTransitionError）
- 每个动作只允许在指定前置阶段调用，成功后返回新的 current_stage
- 路由层负责持久化与时间线写入；本模块专注规则
"""
from datetime import date, datetime

# ---------------------------------------------------------------------------
# 七步定义（唯一来源，前端 config/biddingStages.js 镜像本表）
# ---------------------------------------------------------------------------
STAGES = [
    {'key': 'stage1', 'name': '需求征集', 'desc': '征集企业技术需求，登记榜单信息'},
    {'key': 'stage2', 'name': '专家论证', 'desc': '组织专家论证需求是否适合揭榜挂帅'},
    {'key': 'stage3', 'name': '发榜公告', 'desc': '公开发布榜单，征集揭榜方'},
    {'key': 'stage4', 'name': '揭榜评审', 'desc': '接收揭榜申请，评审择优定标'},
    {'key': 'stage5', 'name': '任务签订', 'desc': '与揭榜方签订攻关任务书'},
    {'key': 'stage6', 'name': '过程管理', 'desc': '跟踪实施进度，核查里程碑'},
    {'key': 'stage7', 'name': '绩效评价', 'desc': '结题绩效评价与成果跟踪'},
]

STAGE_KEYS = [s['key'] for s in STAGES]
STAGE_NAME_MAP = {s['key']: s['name'] for s in STAGES}

# 终止态
TERMINAL_STAGES = ('rejected', 'failed', 'cancelled')

# 阶段序号（用于看板漏斗排序；终止态归为 -1）
def stage_index(stage):
    if stage in STAGE_KEYS:
        return STAGE_KEYS.index(stage)
    return -1


class BiddingTransitionError(Exception):
    """阶段流转非法时抛出，路由层捕获后返回 400 中文提示"""
    pass


# ---------------------------------------------------------------------------
# 动作定义：{action: {from_stages: [...], to_stage: str, label: str, terminal: bool}}
# ---------------------------------------------------------------------------
ACTIONS = {
    'submit_argument': {   # 需求征集 → 提交论证
        'from_stages': ['stage1'],
        'to_stage': 'stage2',
        'label': '提交专家论证',
        'terminal': False,
    },
    'argument_pass': {     # 专家论证 → 通过
        'from_stages': ['stage2'],
        'to_stage': 'stage3',
        'label': '论证通过',
        'terminal': False,
    },
    'argument_reject': {   # 专家论证 → 驳回（终止）
        'from_stages': ['stage2'],
        'to_stage': 'rejected',
        'label': '论证驳回',
        'terminal': True,
    },
    'publish': {           # 发榜公告 → 发布
        'from_stages': ['stage3'],
        'to_stage': 'stage3',
        'label': '发布公告',
        'terminal': False,
    },
    'expire': {            # 发榜公告 → 截止揭榜
        'from_stages': ['stage3'],
        'to_stage': 'stage4',
        'label': '截止揭榜',
        'terminal': False,
    },
    'select_bid': {        # 揭榜评审 → 定标
        'from_stages': ['stage4'],
        'to_stage': 'stage5',
        'label': '确定揭榜方',
        'terminal': False,
    },
    'fail_bid': {          # 揭榜评审 → 流标（终止）
        'from_stages': ['stage4'],
        'to_stage': 'failed',
        'label': '流标',
        'terminal': True,
    },
    'sign': {              # 任务签订 → 签订任务书
        'from_stages': ['stage5'],
        'to_stage': 'stage6',
        'label': '签订任务书',
        'terminal': False,
    },
    'complete': {          # 过程管理 → 实施完成
        'from_stages': ['stage6'],
        'to_stage': 'stage7',
        'label': '实施完成',
        'terminal': False,
    },
    'terminate': {         # 过程管理 → 终止
        'from_stages': ['stage6'],
        'to_stage': 'cancelled',
        'label': '项目终止',
        'terminal': True,
    },
    'evaluate': {          # 绩效评价 → 提交评价（终态，可重复修改）
        'from_stages': ['stage7'],
        'to_stage': 'stage7',
        'label': '绩效评价',
        'terminal': False,
    },
    'cancel': {            # 任意非终态 → 取消
        'from_stages': STAGE_KEYS,
        'to_stage': 'cancelled',
        'label': '项目取消',
        'terminal': True,
    },
}


def validate_transition(current_stage, action):
    """校验流转是否合法。合法返回目标阶段；非法抛 BiddingTransitionError。"""
    if action not in ACTIONS:
        raise BiddingTransitionError(f'未知的操作类型：{action}')

    act = ACTIONS[action]
    cur_name = STAGE_NAME_MAP.get(current_stage, current_stage)

    # 终止态只允许重复 evaluate / 不允许任何推进
    if current_stage in TERMINAL_STAGES:
        if current_stage == 'stage7' and action == 'evaluate':
            return 'stage7'
        raise BiddingTransitionError(f'项目已处于终止状态（{cur_name}），不能再进行「{act["label"]}」操作')

    if current_stage not in act['from_stages']:
        raise BiddingTransitionError(
            f'当前阶段为「{cur_name}」，不允许执行「{act["label"]}」操作（该操作仅适用于：'
            + '、'.join(STAGE_NAME_MAP.get(s, s) for s in act['from_stages']) + '）'
        )

    if action == 'publish':
        # 发布不改变阶段，仅要求处于 stage3
        return 'stage3'
    if action == 'evaluate':
        return 'stage7'
    return act['to_stage']


# ---------------------------------------------------------------------------
# 阶段推进后的自动时间线文案
# ---------------------------------------------------------------------------
def transition_summary(action, extra=''):
    act = ACTIONS[action]
    if act['terminal']:
        return f'【系统】项目{act["label"]}'
    return f'【系统】{act["label"]}，进入「{STAGE_NAME_MAP.get(act["to_stage"], act["to_stage"])}」阶段' + (f'（{extra}）' if extra else '')


def today_str():
    return date.today().isoformat()
