// 揭榜挂帅七步工作法 — 前端镜像配置（与后端 services/bidding_service.py 保持一致）
// 修改七步定义时需同时更新后端 STAGES

export const BIDDING_STAGES = [
  { key: 'stage1', name: '需求征集', desc: '征集企业技术需求，登记榜单信息' },
  { key: 'stage2', name: '专家论证', desc: '组织专家论证需求是否适合揭榜挂帅' },
  { key: 'stage3', name: '发榜公告', desc: '公开发布榜单，征集揭榜方' },
  { key: 'stage4', name: '揭榜评审', desc: '接收揭榜申请，评审择优定标' },
  { key: 'stage5', name: '任务签订', desc: '与揭榜方签订攻关任务书' },
  { key: 'stage6', name: '过程管理', desc: '跟踪实施进度，核查里程碑' },
  { key: 'stage7', name: '绩效评价', desc: '结题绩效评价与成果跟踪' },
]

export const STAGE_NAME_MAP = Object.fromEntries(BIDDING_STAGES.map(s => [s.key, s.name]))

// 终止态
export const TERMINAL_STAGES = ['rejected', 'failed', 'cancelled']

export const TERMINAL_LABELS = {
  rejected: '论证驳回',
  failed: '流标',
  cancelled: '已终止',
}

// 阶段 → 颜色（el-tag type / el-steps 状态）
export const STAGE_COLORS = {
  stage1: 'info',
  stage2: 'primary',
  stage3: 'warning',
  stage4: 'success',
  stage5: 'primary',
  stage6: 'warning',
  stage7: 'success',
}

export const TERMINAL_COLORS = {
  rejected: 'danger',
  failed: 'danger',
  cancelled: 'danger',
}

export function stageIndex(stage) {
  return BIDDING_STAGES.findIndex(s => s.key === stage)
}

// 当前阶段可执行的动作（前端按钮渲染依据；后端仍会二次校验）
// action: { label, type: 'primary'|'danger'|'default', payloadKeys: [...] }
export const STAGE_ACTIONS = {
  stage1: [
    { action: 'submit_argument', label: '提交专家论证', type: 'primary' },
  ],
  stage2: [
    { action: 'argument_pass', label: '论证通过', type: 'primary' },
    { action: 'argument_reject', label: '论证驳回', type: 'danger' },
  ],
  stage3: [
    { action: 'publish', label: '发布公告', type: 'primary' },
    { action: 'expire', label: '截止揭榜', type: 'default' },
  ],
  stage4: [
    { action: 'select_bid', label: '确定揭榜方', type: 'primary' },
    { action: 'fail_bid', label: '流标', type: 'danger' },
  ],
  stage5: [
    { action: 'sign', label: '签订任务书', type: 'primary' },
  ],
  stage6: [
    { action: 'complete', label: '实施完成', type: 'primary' },
    { action: 'terminate', label: '项目终止', type: 'danger' },
  ],
  stage7: [
    { action: 'evaluate', label: '绩效评价', type: 'primary' },
  ],
}

export const DEMAND_SOURCES = ['企业申报', '专班征集', '部门推荐', '其他']
export const BIDDER_TYPES = ['高校', '科研院所', '企业', '团队']
export const EVAL_LEVELS = ['优秀', '良好', '合格', '不合格']

export const BID_STATUS_LABELS = {
  submitted: '已提交',
  reviewing: '评审中',
  selected: '已中标',
  rejected: '未中标',
}

export const MILESTONE_STATUS_LABELS = {
  pending: '待完成',
  in_progress: '进行中',
  done: '已完成',
  delayed: '已延期',
  cancelled: '已取消',
}

export const MILESTONE_STATUS_COLORS = {
  pending: 'info',
  in_progress: 'warning',
  done: 'success',
  delayed: 'danger',
  cancelled: 'info',
}

export const TIMELINE_TYPE_LABELS = {
  system: '系统流转',
  service: '服务记录',
  notice: '通知',
}
