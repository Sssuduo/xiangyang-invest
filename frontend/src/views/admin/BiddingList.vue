<!-- BiddingList.vue: 揭榜挂帅 — 管理端列表（列表 + 登记 + 阶段推进 + 只读详情） -->
<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>揭榜挂帅管理</h2>
          <div class="page-header-actions">
            <el-button @click="$router.push('/admin/bidding-users')">揭榜方用户</el-button>
            <el-button type="primary" @click="openCreate">
              <el-icon><Plus /></el-icon> 登记需求
            </el-button>
          </div>
        </div>

        <div class="filter-bar">
          <el-input v-model="searchText" placeholder="搜索榜单名称、发榜企业..." :prefix-icon="Search" clearable class="search-input" @input="fetchData" />
          <el-select v-model="filterStage" placeholder="当前阶段" clearable @change="fetchData" style="width: 140px;">
            <el-option v-for="s in allStageOptions" :key="s.key" :label="s.name" :value="s.key" />
          </el-select>
          <el-select v-model="filterCategory" placeholder="技术领域" clearable @change="fetchData" style="width: 140px;">
            <el-option v-for="c in dicts.categories" :key="c.code" :label="c.name" :value="c.code" />
          </el-select>
        </div>

        <el-table :data="projects" v-loading="loading" stripe>
          <el-table-column prop="order_no" label="序号" width="60" align="center" />
          <el-table-column prop="title" label="榜单名称" min-width="180" show-overflow-tooltip />
          <el-table-column prop="demander_name" label="发榜企业" min-width="130" show-overflow-tooltip />
          <el-table-column prop="category_name" label="领域" width="110" />
          <el-table-column label="阶段" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="stageTagType(row.current_stage)" size="small">{{ row.stage_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="揭榜数" width="70" align="center">
            <template #default="{ row }">{{ row.bid_count }}</template>
          </el-table-column>
          <el-table-column prop="deadline_date" label="揭榜截止" width="110" align="center" />
          <el-table-column prop="created_at" label="登记时间" width="140" align="center" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openDetail(row)">查看</el-button>
              <el-button size="small" link @click="openEdit(row)">编辑</el-button>
              <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 详情抽屉：只读展示 + 阶段推进 -->
        <el-drawer v-model="showDetail" size="760px" :title="detail ? detail.title : ''" destroy-on-close>
          <template v-if="detail">
            <el-steps :active="stepActiveIndex" align-center finish-status="success" class="steps-bar">
              <el-step v-for="s in BIDDING_STAGES" :key="s.key" :title="s.name" />
            </el-steps>
            <el-alert
              v-if="TERMINAL_STAGES.includes(detail.current_stage)"
              type="error" :title="`已终止（${TERMINAL_LABELS[detail.current_stage]}）`" :closable="false" show-icon
            />
            <div v-else class="action-bar">
              <span>当前操作：</span>
              <el-button
                v-for="a in STAGE_ACTIONS[detail.current_stage] || []"
                :key="a.action" :type="a.type" size="small" @click="openAction(a.action)"
              >{{ a.label }}</el-button>
            </div>

            <el-descriptions :column="2" border size="small" class="desc-block">
              <el-descriptions-item label="技术领域">{{ detail.category_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="需求来源">{{ detail.demand_source || '-' }}</el-descriptions-item>
              <el-descriptions-item label="发榜企业">{{ detail.demander_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="联系人">{{ detail.demander_contact || '-' }} {{ detail.demander_phone || '' }}</el-descriptions-item>
              <el-descriptions-item label="预期投入(万元)">{{ detail.expected_budget || '-' }}</el-descriptions-item>
              <el-descriptions-item label="期望时限">{{ detail.expected_deadline || '-' }}</el-descriptions-item>
              <el-descriptions-item label="悬赏(万元)">{{ detail.bounty_amount || '-' }}</el-descriptions-item>
              <el-descriptions-item label="揭榜截止">{{ detail.deadline_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="揭榜方" :span="2">
                {{ detail.selected_bid ? detail.selected_bid.bidder_name : '未定标' }}
              </el-descriptions-item>
            </el-descriptions>

            <div class="block-title">技术需求描述</div>
            <div class="block-text">{{ detail.requirement_desc || '（未填写）' }}</div>

            <div class="block-title">揭榜申请（{{ detail.bids.length }}）</div>
            <el-table :data="detail.bids" size="small" border>
              <el-table-column prop="bidder_name" label="揭榜方" min-width="120" show-overflow-tooltip />
              <el-table-column prop="bidder_type" label="类型" width="80" />
              <el-table-column label="报价" width="90" align="right">
                <template #default="{ row }">{{ row.expected_amount }}万</template>
              </el-table-column>
              <el-table-column label="评分" width="70" align="center">
                <template #default="{ row }">{{ row.score ?? '-' }}</template>
              </el-table-column>
              <el-table-column label="状态" width="80" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="bidStatusType(row.status)">{{ BID_STATUS_LABELS[row.status] || row.status }}</el-tag>
                </template>
              </el-table-column>
            </el-table>

            <div class="block-title">里程碑（{{ detail.milestones.length }}）</div>
            <el-table :data="detail.milestones" size="small" border>
              <el-table-column prop="content" label="内容" min-width="140" show-overflow-tooltip />
              <el-table-column prop="planned_date" label="计划" width="100" align="center" />
              <el-table-column prop="actual_date" label="实际" width="100" align="center" />
              <el-table-column label="状态" width="90" align="center">
                <template #default="{ row }">
                  <el-tag size="small">{{ MILESTONE_STATUS_LABELS[row.status] || row.status }}</el-tag>
                </template>
              </el-table-column>
            </el-table>

            <div class="block-title">全周期跟踪时间线</div>
            <el-timeline v-if="detail.timeline.length" class="timeline-list">
              <el-timeline-item
                v-for="t in detail.timeline" :key="t.id"
                :timestamp="`${t.created_at} · ${t.record_by}`" placement="top"
              >
                <div class="timeline-content">{{ t.content }}</div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无跟踪记录" :image-size="50" />
          </template>
        </el-drawer>

        <!-- 登记/编辑需求（抽屉：企业需求申报表） -->
        <el-drawer v-model="showForm" :title="editing ? '编辑需求信息' : '登记技术需求（企业需求申报表）'" size="700px" destroy-on-close>
          <el-form :model="form" label-width="130px" label-position="left">
            <div class="form-section-title">一、基本信息</div>
            <el-form-item label="榜单/需求名称" required>
              <el-input v-model="form.title" placeholder="一句话概括" />
            </el-form-item>
            <el-form-item label="技术领域">
              <el-select v-model="form.category_code" style="width: 100%">
                <el-option v-for="c in dicts.categories" :key="c.code" :label="c.name" :value="c.code" />
              </el-select>
            </el-form-item>
            <el-form-item label="需求来源">
              <el-select v-model="form.demand_source" style="width: 100%">
                <el-option v-for="s in DEMAND_SOURCES" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>
            <el-form-item label="预期投入(万)">
              <el-input-number v-model="form.expected_budget" :min="0" :precision="2" />
            </el-form-item>
            <el-form-item label="期望时限">
              <el-date-picker v-model="form.expected_deadline" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>

            <div class="form-section-title">二、企业概况</div>
            <el-form-item label="企业名称" required>
              <el-input v-model="form.demander_name" />
            </el-form-item>
            <el-form-item label="企业地址">
              <el-input v-model="form.enterprise_address" />
            </el-form-item>
            <el-form-item label="资质/荣誉（多选）">
              <el-checkbox-group v-model="form.enterprise_qualifications">
                <el-checkbox v-for="q in QUALIFICATION_OPTIONS" :key="q" :label="q" />
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="所属行业">
              <el-select v-model="form.industry_code" style="width: 100%">
                <el-option v-for="i in INDUSTRY_OPTIONS" :key="i" :label="i" :value="i" />
              </el-select>
            </el-form-item>
            <el-form-item label="注册资本">
              <el-input v-model="form.registered_capital" style="width: 220px" placeholder="如：1.44亿" />
            </el-form-item>
            <el-form-item label="成立时间">
              <el-input v-model="form.founded_year" style="width: 220px" placeholder="如：1996年" />
            </el-form-item>
            <el-form-item label="人员规模">
              <el-input v-model="form.staff_size" style="width: 220px" placeholder="如：220" />
            </el-form-item>
            <el-form-item label="企业性质">
              <el-radio-group v-model="form.enterprise_nature">
                <el-radio v-for="n in ENTERPRISE_NATURES" :key="n" :label="n" />
              </el-radio-group>
            </el-form-item>
            <el-form-item label="主要产品/服务">
              <el-input v-model="form.main_products" type="textarea" :rows="2" />
            </el-form-item>
            <el-form-item label="上年度营收">
              <el-input v-model="form.last_year_revenue" style="width: 220px" placeholder="如：3.61亿" />
            </el-form-item>
            <el-form-item label="联系人及职务">
              <el-input v-model="form.demander_contact" />
            </el-form-item>
            <el-form-item label="手机号码">
              <el-input v-model="form.demander_phone" style="width: 220px" />
            </el-form-item>

            <div class="form-section-title">三、需求描述</div>
            <el-form-item label="主要技术难点">
              <el-input v-model="form.tech_difficulties" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="主要技术指标">
              <el-input v-model="form.tech_indicators" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="主要研究内容">
              <el-input v-model="form.research_content" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="需求描述（兼容）">
              <el-input v-model="form.requirement_desc" type="textarea" :rows="2" />
            </el-form-item>

            <div class="form-section-title">四、合作意向</div>
            <el-form-item label="拟短期合作（多选）">
              <el-checkbox-group v-model="form.short_term_cooperation">
                <el-checkbox v-for="c in SHORT_TERM_COOPERATION_OPTIONS" :key="c" :label="c" />
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="拟长期合作（多选）">
              <el-checkbox-group v-model="form.long_term_cooperation">
                <el-checkbox v-for="c in LONG_TERM_COOPERATION_OPTIONS" :key="c" :label="c" />
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="意向合作专家">
              <el-radio-group v-model="form.expert_intent">
                <el-radio label="yes">有</el-radio>
                <el-radio label="no">无</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="form.expert_intent === 'yes'" label="专家及单位">
              <el-input v-model="form.expert_names" type="textarea" :rows="2" placeholder="如：严建兵、邱法展（华中农业大学）" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showForm = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="saveForm">保存</el-button>
          </template>
        </el-drawer>

        <!-- 阶段操作 -->
        <el-dialog v-model="showAction" :title="actionMeta ? actionMeta.label : ''" width="520px">
          <template v-if="currentAction === 'publish'">
            <el-form-item label="悬赏(万元)" label-width="110px">
              <el-input-number v-model="actionForm.bounty_amount" :min="0" :precision="2" />
            </el-form-item>
            <el-form-item label="揭榜截止" label-width="110px" required>
              <el-date-picker v-model="actionForm.deadline_date" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="揭榜条件" label-width="110px">
              <el-input v-model="actionForm.accept_conditions" type="textarea" :rows="3" />
            </el-form-item>
          </template>
          <template v-else-if="currentAction === 'select_bid'">
            <el-form-item label="选择揭榜方" label-width="110px">
              <el-radio-group v-model="actionForm.bid_id">
                <el-radio v-for="b in detail.bids" :key="b.id" :value="b.id" style="display: flex; margin-bottom: 4px;">
                  {{ b.bidder_name }}（{{ b.bidder_type }}）
                </el-radio>
              </el-radio-group>
            </el-form-item>
          </template>
          <template v-else-if="currentAction === 'sign'">
            <el-form-item label="任务经费(万)" label-width="110px">
              <el-input-number v-model="actionForm.task_amount" :min="0" :precision="2" />
            </el-form-item>
            <el-form-item label="任务期限" label-width="110px">
              <el-input v-model="actionForm.task_duration" placeholder="如：24个月" />
            </el-form-item>
            <el-form-item label="备注" label-width="110px">
              <el-input v-model="actionForm.task_notes" type="textarea" :rows="2" />
            </el-form-item>
          </template>
          <template v-else-if="currentAction === 'evaluate'">
            <el-form-item label="评分(0-100)" label-width="110px" required>
              <el-input-number v-model="actionForm.eval_score" :min="0" :max="100" />
            </el-form-item>
            <el-form-item label="等级" label-width="110px" required>
              <el-select v-model="actionForm.eval_level" style="width: 200px">
                <el-option v-for="l in EVAL_LEVELS" :key="l" :label="l" :value="l" />
              </el-select>
            </el-form-item>
            <el-form-item label="评价报告" label-width="110px">
              <el-input v-model="actionForm.eval_report" type="textarea" :rows="3" />
            </el-form-item>
          </template>
          <template v-else>
            <el-alert
              v-if="currentAction === 'submit_argument' || currentAction === 'expire'"
              :title="currentAction === 'submit_argument' ? '确认提交专家论证？' : '确认截止揭榜？'" type="info" :closable="false" show-icon
            />
            <el-form-item
              v-if="['argument_reject', 'fail_bid', 'complete', 'terminate', 'cancel'].includes(currentAction)"
              :label="currentAction === 'fail_bid' ? '流标原因' : currentAction === 'cancel' ? '取消原因' : '说明'"
              label-width="110px"
            >
              <el-input v-model="actionForm.reason" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item v-if="currentAction === 'argument_pass'" label="论证结论" label-width="110px">
              <el-input v-model="actionForm.argument_result" type="textarea" :rows="2" />
            </el-form-item>
          </template>
          <template #footer>
            <el-button @click="showAction = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="submitAction">确认</el-button>
          </template>
        </el-dialog>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { biddingApi } from '@/api/bidding'
import {
  BIDDING_STAGES, TERMINAL_STAGES, TERMINAL_LABELS, STAGE_ACTIONS,
  STAGE_COLORS, DEMAND_SOURCES, EVAL_LEVELS, BID_STATUS_LABELS, MILESTONE_STATUS_LABELS,
  ENTERPRISE_NATURES, QUALIFICATION_OPTIONS, INDUSTRY_OPTIONS,
  SHORT_TERM_COOPERATION_OPTIONS, LONG_TERM_COOPERATION_OPTIONS,
} from '@/config/biddingStages'

const projects = ref([])
const loading = ref(false)
const dicts = ref({ categories: [], staff: [] })
const searchText = ref('')
const filterStage = ref('')
const filterCategory = ref('')
const saving = ref(false)

const allStageOptions = computed(() => [
  ...BIDDING_STAGES,
  ...Object.entries(TERMINAL_LABELS).map(([key, name]) => ({ key, name })),
])
function stageTagType(key) {
  return TERMINAL_STAGES.includes(key) ? 'danger' : (STAGE_COLORS[key] || 'info')
}
function bidStatusType(s) {
  return { submitted: 'info', reviewing: 'warning', selected: 'success', rejected: 'danger' }[s] || 'info'
}

async function fetchDicts() {
  const res = await biddingApi.getDicts()
  if (res.code === 0) dicts.value = res.data
}
async function fetchData() {
  loading.value = true
  try {
    const res = await biddingApi.listProjects({
      search: searchText.value || undefined,
      stage: filterStage.value || undefined,
      category: filterCategory.value || undefined,
    })
    if (res.code === 0) projects.value = res.data
  } finally {
    loading.value = false
  }
}

// 详情
const showDetail = ref(false)
const detail = ref(null)
const stepActiveIndex = computed(() => {
  const idx = BIDDING_STAGES.findIndex(s => s.key === detail.value?.current_stage)
  return idx === -1 ? 7 : idx
})
async function openDetail(row) {
  const res = await biddingApi.getProject(row.id)
  if (res.code === 0) { detail.value = res.data; showDetail.value = true }
}

// 登记/编辑
const showForm = ref(false)
const editing = ref(null)
const form = reactive({})

function emptyForm() {
  return {
    title: '', category_code: '', demander_name: '', demander_contact: '', demander_phone: '',
    demand_source: '', requirement_desc: '', expected_budget: 0, expected_deadline: '',
    enterprise_address: '', enterprise_qualifications: [], industry_code: '',
    registered_capital: '', founded_year: '', staff_size: '', enterprise_nature: '',
    main_products: '', last_year_revenue: '',
    tech_difficulties: '', tech_indicators: '', research_content: '',
    short_term_cooperation: [], long_term_cooperation: [], expert_intent: 'no', expert_names: '',
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, emptyForm())
  showForm.value = true
}
function openEdit(row) {
  editing.value = row
  Object.assign(form, {
    title: row.title, category_code: row.category_code, demander_name: row.demander_name,
    demander_contact: row.demander_contact, demander_phone: row.demander_phone,
    demand_source: row.demand_source, requirement_desc: row.requirement_desc,
    expected_budget: row.expected_budget, expected_deadline: row.expected_deadline,
    enterprise_address: row.enterprise_address || '',
    enterprise_qualifications: [...(row.enterprise_qualifications || [])],
    industry_code: row.industry_code || '',
    registered_capital: row.registered_capital || '',
    founded_year: row.founded_year || '',
    staff_size: row.staff_size || '',
    enterprise_nature: row.enterprise_nature || '',
    main_products: row.main_products || '',
    last_year_revenue: row.last_year_revenue || '',
    tech_difficulties: row.tech_difficulties || '',
    tech_indicators: row.tech_indicators || '',
    research_content: row.research_content || '',
    short_term_cooperation: [...(row.short_term_cooperation || [])],
    long_term_cooperation: [...(row.long_term_cooperation || [])],
    expert_intent: row.expert_intent || 'no',
    expert_names: row.expert_names || '',
  })
  showForm.value = true
}
async function saveForm() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写榜单/需求名称'); return
  }
  if (!form.demander_name.trim()) {
    ElMessage.warning('请填写企业名称'); return
  }
  saving.value = true
  try {
    const res = editing.value
      ? await biddingApi.updateProject(editing.value.id, form)
      : await biddingApi.createProject(form)
    if (res.code === 0) { ElMessage.success(res.message); showForm.value = false; fetchData() }
  } finally { saving.value = false }
}
function handleDelete(row) {
  ElMessageBox.confirm(`确认删除「${row.title}」？`, '删除确认', { type: 'warning' })
    .then(async () => {
      const res = await biddingApi.deleteProject(row.id)
      if (res.code === 0) { ElMessage.success('已删除'); fetchData() }
    }).catch(() => {})
}

// 阶段操作
const showAction = ref(false)
const currentAction = ref('')
const actionForm = reactive({})
const actionMeta = computed(() =>
  (STAGE_ACTIONS[detail.value?.current_stage] || []).find(a => a.action === currentAction.value))
function openAction(action) {
  currentAction.value = action
  Object.assign(actionForm, {
    bounty_amount: detail.value?.bounty_amount || 0, deadline_date: '',
    accept_conditions: detail.value?.accept_conditions || '',
    bid_id: detail.value?.selected_bid_id,
    task_amount: detail.value?.task_amount || 0, task_duration: '',
    task_notes: detail.value?.task_notes || '',
    eval_score: detail.value?.eval_score, eval_level: detail.value?.eval_level || '',
    eval_report: detail.value?.eval_report || '',
    argument_result: '', reason: '',
  })
  showAction.value = true
}
async function submitAction() {
  saving.value = true
  try {
    const payload = { action: currentAction.value }
    const a = currentAction.value
    if (a === 'publish') Object.assign(payload, actionForm)
    else if (a === 'select_bid') { payload.bid_id = actionForm.bid_id }
    else if (a === 'sign') Object.assign(payload, { task_amount: actionForm.task_amount, task_duration: actionForm.task_duration, task_notes: actionForm.task_notes })
    else if (a === 'evaluate') Object.assign(payload, { eval_score: actionForm.eval_score, eval_level: actionForm.eval_level, eval_report: actionForm.eval_report })
    else if (a === 'argument_pass') payload.argument_result = actionForm.argument_result
    else if (['argument_reject', 'fail_bid', 'complete', 'terminate', 'cancel'].includes(a)) {
      payload[a === 'fail_bid' ? 'review_result' : (a === 'argument_reject' ? 'argument_result' : (a === 'cancel' ? 'reason' : 'process_notes'))] = actionForm.reason
    }
    const res = await biddingApi.transition(detail.value.id, payload)
    if (res.code === 0) {
      ElMessage.success(res.message)
      showAction.value = false
      detail.value = res.data
      fetchData()
    } else {
      ElMessage.error(res.message)
    }
  } finally { saving.value = false }
}

onMounted(() => { fetchDicts(); fetchData() })
</script>

<style scoped>
.admin-layout { display: flex; }
.admin-main { flex: 1; overflow-y: auto; height: 100vh; background: #f5f6f8; }
.admin-content { padding: 20px; max-width: 1400px; margin: 0 auto; }
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.page-header h2 { color: var(--text-primary); }
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
.search-input { width: 240px; }
.steps-bar { margin-bottom: 16px; }
.action-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #f0f7ff;
  border: 1px solid #d6e4ff;
  border-radius: 6px;
  margin-bottom: 16px;
}
.desc-block { margin-bottom: 16px; }
.block-title { font-weight: 600; margin: 14px 0 8px; }
.block-text {
  white-space: pre-wrap;
  line-height: 1.8;
  background: #f8f9fb;
  padding: 10px 12px;
  border-radius: 6px;
}
.timeline-list { padding-left: 4px; }
.timeline-content { line-height: 1.7; }
.form-section-title {
  font-weight: 600;
  color: var(--primary-color);
  border-left: 3px solid var(--primary-color);
  padding-left: 10px;
  margin: 8px 0 16px;
}
</style>
