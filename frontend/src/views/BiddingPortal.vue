<!-- BiddingPortal.vue: 揭榜挂帅 — 对外门户（榜单浏览 / 注册登录 / 提交申请 / 我的进展） -->
<template>
  <div class="portal">
    <!-- 门户导航 -->
    <header class="portal-nav">
      <div class="nav-inner">
        <router-link to="/" class="nav-brand">襄阳农高区</router-link>
        <nav class="nav-menu">
          <span class="nav-item" :class="{ active: view === 'boards' }" @click="switchView('boards')">揭榜榜单</span>
          <span v-if="me" class="nav-item" :class="{ active: view === 'mine' }" @click="switchView('mine')">我的中心</span>
          <router-link to="/contact" class="nav-item">联系我们</router-link>
        </nav>
        <div class="nav-right">
          <template v-if="me">
            <el-dropdown @command="handleUserCommand">
              <span class="nav-user">
                <el-icon><UserFilled /></el-icon>
                {{ me.org_name || me.username }}
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="mine">我的中心</el-dropdown-item>
                  <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button size="small" @click="showLogin = true">登录</el-button>
            <el-button size="small" type="primary" @click="openRegister">注册账号</el-button>
          </template>
        </div>
      </div>
    </header>

    <main class="portal-main">
      <!-- ============ 榜单浏览 ============ -->
      <template v-if="view === 'boards'">
        <div class="banner">
          <h1>揭榜挂帅 · 线上技术对接平台</h1>
          <p>需求征集 → 专家论证 → 发榜公告 → 揭榜评审 → 任务签订 → 过程管理 → 绩效评价</p>
        </div>
        <div class="boards-wrap">
          <div v-if="!boards.length" class="empty-tip">当前暂无公开揭榜榜单，敬请期待</div>
          <el-card v-for="b in boards" :key="b.id" class="board-card" shadow="hover" @click="openBoard(b)">
            <div class="board-head">
              <span class="board-title">{{ b.title }}</span>
              <el-tag v-if="b.open" type="success" size="small">揭榜中</el-tag>
              <el-tag v-else type="info" size="small">已截止</el-tag>
            </div>
            <div class="board-meta">
              <span>发榜企业：{{ b.demander_name || '—' }}</span>
              <span>悬赏金额：{{ b.bounty_amount ? b.bounty_amount + ' 万元' : '—' }}</span>
              <span>揭榜截止：{{ b.deadline_date || '—' }}</span>
            </div>
            <div class="board-desc">{{ b.requirement_desc }}</div>
          </el-card>
        </div>
      </template>

      <!-- ============ 我的中心 ============ -->
      <template v-else-if="view === 'mine'">
        <div class="mine-wrap">
          <h2 class="mine-title">我的中心</h2>
          <el-tabs v-model="mineTab">
            <!-- 基本信息 -->
            <el-tab-pane label="基本信息" name="profile">
              <el-form :model="profileForm" label-width="110px" class="profile-form">
                <el-form-item label="单位/团队名称">
                  <el-input v-model="profileForm.org_name" />
                </el-form-item>
                <el-form-item label="单位性质">
                  <el-select v-model="profileForm.org_type" style="width: 240px">
                    <el-option v-for="t in BIDDER_TYPES" :key="t" :label="t" :value="t" />
                  </el-select>
                </el-form-item>
                <el-form-item label="联系人">
                  <el-input v-model="profileForm.contact_name" style="width: 240px" />
                </el-form-item>
                <el-form-item label="联系电话">
                  <el-input v-model="profileForm.contact_phone" style="width: 240px" />
                </el-form-item>
                <el-form-item label="登录邮箱">
                  <el-input :model-value="me?.email" disabled style="width: 240px" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="saving" @click="saveProfile">保存信息</el-button>
                  <el-button style="margin-left: 12px" @click="showPwd = true">修改密码</el-button>
                </el-form-item>
              </el-form>
            </el-tab-pane>

            <!-- 我的申请 -->
            <el-tab-pane label="我的申请" name="apps">
              <el-empty v-if="!applications.length" description="您还没有提交过揭榜申请" />
              <el-table v-else :data="applications" stripe @row-click="openApplication" class="app-table">
                <el-table-column prop="board_title" label="榜单名称" min-width="180" show-overflow-tooltip />
                <el-table-column label="申请状态" width="100" align="center">
                  <template #default="{ row }">
                    <el-tag :type="appStatusType(row.bid_status)" size="small">
                      {{ BID_STATUS_LABELS[row.bid_status] || row.bid_status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="项目阶段" width="110" align="center">
                  <template #default="{ row }">
                    <el-tag v-if="row.project_stage" size="small" type="info">
                      {{ row.project_stage_name }}
                    </el-tag>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="submitted_at" label="提交时间" width="150" align="center" />
                <el-table-column label="操作" width="80" align="center">
                  <template #default="{ row }">
                    <el-button size="small" link type="primary" @click.stop="openApplication(row)">查看</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </div>
      </template>
    </main>

    <!-- ============ 榜单详情抽屉 ============ -->
    <el-drawer v-model="showBoard" :title="currentBoard?.title || ''" size="620px" destroy-on-close>
      <template v-if="currentBoard">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="发榜企业">{{ currentBoard.demander_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="悬赏金额">{{ currentBoard.bounty_amount ? currentBoard.bounty_amount + ' 万元' : '-' }}</el-descriptions-item>
          <el-descriptions-item label="揭榜截止">{{ currentBoard.deadline_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="期望时限">{{ currentBoard.expected_deadline || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="block-title">技术需求描述</div>
        <div class="block-text">{{ currentBoard.requirement_desc || '（未填写）' }}</div>
        <div class="block-title">揭榜条件</div>
        <div class="block-text">{{ currentBoard.accept_conditions || '（未说明）' }}</div>

        <template v-if="currentBoard.open">
          <el-alert v-if="!me" type="info" :closable="false" show-icon
            title="提交揭榜申请需要登录账号，请先注册或登录" class="apply-tip" />
          <el-alert v-else-if="currentBoard.applied" type="success" :closable="false" show-icon
            title="您已提交过该榜单的揭榜申请，请勿重复提交" />
          <template v-else>
            <div class="block-title">提交揭榜申请</div>
            <el-form :model="applyForm" label-width="100px">
              <el-form-item label="团队负责人">
                <el-input v-model="applyForm.team_leader" :placeholder="me?.contact_name || '负责人姓名'" />
              </el-form-item>
              <el-form-item label="联系电话">
                <el-input v-model="applyForm.team_leader_phone" :placeholder="me?.contact_phone || '手机号'" />
              </el-form-item>
              <el-form-item label="技术方案" required>
                <el-input v-model="applyForm.tech_solution" type="textarea" :rows="4"
                  placeholder="技术路线、实施方案、关键技术指标等" />
              </el-form-item>
              <el-form-item label="团队优势">
                <el-input v-model="applyForm.team_advantage" type="textarea" :rows="3"
                  placeholder="相关业绩、平台条件、人员配置等" />
              </el-form-item>
              <el-form-item label="报价(万元)">
                <el-input-number v-model="applyForm.expected_amount" :min="0" :precision="2" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="submitting" @click="submitApply">提交申请</el-button>
                <span class="apply-hint">提交后系统将自动发送回执邮件</span>
              </el-form-item>
            </el-form>
          </template>
        </template>
        <el-alert v-else type="warning" :closable="false" title="该榜单已截止，不再接受揭榜申请" />
      </template>
    </el-drawer>

    <!-- ============ 我的申请详情抽屉 ============ -->
    <el-drawer v-model="showAppDetail" :title="appDetail?.board_title || '申请详情'" size="680px" destroy-on-close>
      <template v-if="appDetail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="申请状态">
            <el-tag :type="appStatusType(appDetail.bid_status)" size="small">
              {{ BID_STATUS_LABELS[appDetail.bid_status] || appDetail.bid_status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ appDetail.submitted_at }}</el-descriptions-item>
          <el-descriptions-item label="评审评分">{{ appDetail.score ?? '待评审' }}</el-descriptions-item>
          <el-descriptions-item label="评审意见">{{ appDetail.score_note || '待评审' }}</el-descriptions-item>
        </el-descriptions>

        <template v-if="appDetail.bid_status === 'selected'">
          <div class="block-title">项目当前阶段</div>
          <el-steps :active="appStageIndex" align-center finish-status="success" class="steps-bar">
            <el-step v-for="s in BIDDING_STAGES" :key="s.key" :title="s.name" />
          </el-steps>
          <el-alert v-if="appDetail.project_terminal" type="error" :closable="false" show-icon title="项目已终止" />

          <div class="block-title">任务书信息</div>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="任务经费">{{ appDetail.task_amount || '-' }} 万元</el-descriptions-item>
            <el-descriptions-item label="任务期限">{{ appDetail.task_duration || '-' }}</el-descriptions-item>
            <el-descriptions-item label="签订日期">{{ appDetail.task_date || '-' }}</el-descriptions-item>
          </el-descriptions>

          <template v-if="appDetail.milestones.length">
            <div class="block-title">任务里程碑</div>
            <el-table :data="appDetail.milestones" size="small" border>
              <el-table-column prop="content" label="里程碑内容" min-width="150" show-overflow-tooltip />
              <el-table-column prop="planned_date" label="计划完成" width="100" align="center" />
              <el-table-column prop="actual_date" label="实际完成" width="100" align="center" />
              <el-table-column label="状态" width="90" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="milestoneType(row.status)">
                    {{ MILESTONE_STATUS_LABELS[row.status] || row.status }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </template>

          <template v-if="appDetail.timeline.length">
            <div class="block-title">项目进展记录</div>
            <el-timeline class="timeline-list">
              <el-timeline-item
                v-for="t in appDetail.timeline" :key="t.id"
                :timestamp="`${t.created_at} · ${t.record_by}`" placement="top"
              >
                <div class="timeline-content">{{ t.content }}</div>
              </el-timeline-item>
            </el-timeline>
          </template>

          <template v-if="appDetail.eval_status === 'evaluated'">
            <div class="block-title">绩效评价结果</div>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="绩效评分">{{ appDetail.eval_score }}</el-descriptions-item>
              <el-descriptions-item label="评价等级">
                <el-tag type="success" size="small">{{ appDetail.eval_level }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="评价日期">{{ appDetail.eval_date || '-' }}</el-descriptions-item>
            </el-descriptions>
            <div class="block-text" style="margin-top: 8px;">{{ appDetail.eval_report || '' }}</div>
          </template>
        </template>
      </template>
    </el-drawer>

    <!-- ============ 登录弹窗 ============ -->
    <el-dialog v-model="showLogin" title="揭榜方登录" width="400px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="邮箱账号">
          <el-input v-model="loginForm.username" placeholder="注册时使用的邮箱" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="loginForm.password" type="password" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-alert v-if="loginError" :title="loginError" type="error" :closable="false" show-icon />
      </el-form>
      <template #footer>
        <el-button @click="showLogin = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleLogin">登录</el-button>
      </template>
    </el-dialog>

    <!-- ============ 注册弹窗 ============ -->
    <el-dialog v-model="showRegister" title="揭榜方注册" width="460px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="单位/团队名称" required>
          <el-input v-model="registerForm.org_name" placeholder="如：华中农业大学水稻育种团队" />
        </el-form-item>
        <el-form-item label="单位性质">
          <el-select v-model="registerForm.org_type" style="width: 100%">
            <el-option v-for="t in BIDDER_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="registerForm.contact_name" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="registerForm.contact_phone" />
        </el-form-item>
        <el-form-item label="邮箱（登录账号）" required>
          <el-input v-model="registerForm.email" placeholder="用于接收回执通知" />
        </el-form-item>
        <el-form-item label="密码（至少6位）" required>
          <el-input v-model="registerForm.password" type="password" show-password />
        </el-form-item>
        <el-alert v-if="registerError" :title="registerError" type="error" :closable="false" show-icon />
        <el-alert v-if="registerNotice" :title="registerNotice" type="success" :closable="false" show-icon />
      </el-form>
      <template #footer>
        <el-button @click="showRegister = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleRegister">注册</el-button>
      </template>
    </el-dialog>

    <!-- ============ 修改密码弹窗 ============ -->
    <el-dialog v-model="showPwd" title="修改密码" width="400px">
      <el-form label-position="top">
        <el-form-item label="原密码">
          <el-input v-model="pwdForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码（至少6位）">
          <el-input v-model="pwdForm.new_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPwd = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleChangePwd">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UserFilled, ArrowDown } from '@element-plus/icons-vue'
import { biddingPublicApi } from '@/api/biddingPublic'
import {
  BIDDING_STAGES, BIDDER_TYPES, BID_STATUS_LABELS, MILESTONE_STATUS_LABELS,
} from '@/config/biddingStages'

const view = ref('boards')
const me = ref(null)
const boards = ref([])
const applications = ref([])
const saving = ref(false)
const submitting = ref(false)
const mineTab = ref('profile')

// 榜单
const showBoard = ref(false)
const currentBoard = ref(null)
const applyForm = reactive({ team_leader: '', team_leader_phone: '', tech_solution: '', team_advantage: '', expected_amount: 0 })

// 登录/注册
const showLogin = ref(false)
const loginForm = reactive({ username: '', password: '' })
const loginError = ref('')
const showRegister = ref(false)
const registerForm = reactive({ org_name: '', org_type: '高校', contact_name: '', contact_phone: '', email: '', password: '' })
const registerError = ref('')
const registerNotice = ref('')

// 我的中心
const profileForm = reactive({ org_name: '', org_type: '', contact_name: '', contact_phone: '' })
const showPwd = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '' })
const showAppDetail = ref(false)
const appDetail = ref(null)

const appStageIndex = computed(() => {
  const idx = BIDDING_STAGES.findIndex(s => s.key === appDetail.value?.project_stage)
  return idx === -1 ? 7 : idx
})

function appStatusType(s) {
  return { submitted: 'info', reviewing: 'warning', selected: 'success', rejected: 'danger' }[s] || 'info'
}
function milestoneType(s) {
  return { pending: 'info', in_progress: 'warning', done: 'success', delayed: 'danger', cancelled: 'info' }[s] || 'info'
}

async function fetchBoards() {
  const res = await biddingPublicApi.listBoards()
  if (res.code === 0) boards.value = res.data
}

async function fetchMe() {
  try {
    const res = await biddingPublicApi.me()
    if (res.code === 0) {
      me.value = res.data
      Object.assign(profileForm, {
        org_name: res.data.org_name, org_type: res.data.org_type,
        contact_name: res.data.contact_name, contact_phone: res.data.contact_phone,
      })
      await fetchApplications()
    }
  } catch {
    me.value = null
  }
}

async function fetchApplications() {
  const res = await biddingPublicApi.myApplications()
  if (res.code === 0) applications.value = res.data
}

function switchView(v) {
  view.value = v
  if (v === 'boards') fetchBoards()
  if (v === 'mine' && me.value) {
    fetchMe()
    fetchApplications()
  }
}

// ==================== 榜单/申请 ====================
async function openBoard(b) {
  const res = await biddingPublicApi.getBoard(b.id)
  if (res.code === 0) {
    currentBoard.value = res.data
    Object.assign(applyForm, { team_leader: me.value?.contact_name || '', team_leader_phone: me.value?.contact_phone || '', tech_solution: '', team_advantage: '', expected_amount: 0 })
    showBoard.value = true
  }
}

async function submitApply() {
  if (!applyForm.tech_solution.trim()) { ElMessage.warning('请填写技术方案'); return }
  submitting.value = true
  try {
    const res = await biddingPublicApi.apply(currentBoard.value.id, applyForm)
    if (res.code === 0) {
      ElMessage.success(res.message)
      showBoard.value = false
      await fetchBoards()
      await fetchApplications()
    } else {
      ElMessage.error(res.message)
    }
  } finally {
    submitting.value = false
  }
}

async function openApplication(row) {
  const res = await biddingPublicApi.myApplicationDetail(row.id)
  if (res.code === 0) {
    appDetail.value = res.data
    showAppDetail.value = true
  }
}

// ==================== 登录/注册 ====================
async function handleLogin() {
  if (!loginForm.username || !loginForm.password) { ElMessage.warning('请输入邮箱和密码'); return }
  saving.value = true
  loginError.value = ''
  try {
    const res = await biddingPublicApi.login(loginForm)
    if (res.code === 0) {
      me.value = res.data
      Object.assign(profileForm, {
        org_name: res.data.org_name, org_type: res.data.org_type,
        contact_name: res.data.contact_name, contact_phone: res.data.contact_phone,
      })
      showLogin.value = false
      ElMessage.success('登录成功')
      await fetchApplications()
      if (showBoard.value) {
        const b = await biddingPublicApi.getBoard(currentBoard.value.id)
        currentBoard.value = b.data
      }
    } else {
      loginError.value = res.message || '登录失败'
    }
  } catch (e) {
    loginError.value = e.message || '登录失败'
  } finally {
    saving.value = false
  }
}

function openRegister() {
  registerError.value = ''
  registerNotice.value = ''
  showRegister.value = true
}

async function handleRegister() {
  if (!registerForm.org_name.trim()) { ElMessage.warning('请填写单位/团队名称'); return }
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(registerForm.email)) { ElMessage.warning('请填写有效邮箱'); return }
  if (registerForm.password.length < 6) { ElMessage.warning('密码至少 6 位'); return }
  saving.value = true
  registerError.value = ''
  registerNotice.value = ''
  try {
    const res = await biddingPublicApi.register(registerForm)
    if (res.code === 0) {
      registerNotice.value = res.message || '注册成功'
      // 注册成功自动登录
      const loginRes = await biddingPublicApi.login({ username: registerForm.email, password: registerForm.password })
      if (loginRes.code === 0) {
        me.value = loginRes.data
        Object.assign(profileForm, {
          org_name: loginRes.data.org_name, org_type: loginRes.data.org_type,
          contact_name: loginRes.data.contact_name, contact_phone: loginRes.data.contact_phone,
        })
        ElMessage.success('注册成功，已自动登录')
        showRegister.value = false
        await fetchApplications()
      }
    } else {
      registerError.value = res.message || '注册失败'
    }
  } catch (e) {
    registerError.value = e.message || '注册失败'
  } finally {
    saving.value = false
  }
}

async function handleUserCommand(cmd) {
  if (cmd === 'mine') switchView('mine')
  if (cmd === 'logout') {
    await biddingPublicApi.logout()
    me.value = null
    applications.value = []
    view.value = 'boards'
    ElMessage.success('已退出登录')
  }
}

// ==================== 个人中心 ====================
async function saveProfile() {
  saving.value = true
  try {
    const res = await biddingPublicApi.updateMe(profileForm)
    if (res.code === 0) {
      me.value = res.data
      ElMessage.success('信息已保存')
    }
  } finally {
    saving.value = false
  }
}

async function handleChangePwd() {
  if (pwdForm.new_password.length < 6) { ElMessage.warning('新密码至少 6 位'); return }
  saving.value = true
  try {
    const res = await biddingPublicApi.changePassword(pwdForm)
    if (res.code === 0) {
      ElMessage.success('密码已修改，请重新登录')
      showPwd.value = false
      await biddingPublicApi.logout()
      me.value = null
      view.value = 'boards'
    }
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchBoards()
  fetchMe()
})
</script>

<style scoped>
.portal {
  min-height: 100vh;
  background: #f5f6f8;
}
.portal-nav {
  background: #fff;
  border-bottom: 1px solid #e0e4e8;
  position: sticky;
  top: 0;
  z-index: 100;
}
.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  gap: 24px;
}
.nav-brand {
  font-size: 18px;
  font-weight: 700;
  color: var(--primary-color);
}
.nav-menu {
  display: flex;
  gap: 20px;
  flex: 1;
}
.nav-item {
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 15px;
  padding: 4px 2px;
}
.nav-item:hover, .nav-item.active { color: var(--primary-color); font-weight: 600; }
.nav-right { display: flex; align-items: center; gap: 10px; }
.nav-user {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: var(--text-primary);
}

.portal-main { max-width: 1200px; margin: 0 auto; padding: 24px 20px 60px; }
.banner {
  text-align: center;
  padding: 48px 20px 32px;
  background: linear-gradient(135deg, #1a3a5c 0%, #2a5a8c 100%);
  color: #fff;
  border-radius: 12px;
  margin-bottom: 24px;
}
.banner h1 { font-size: 28px; margin-bottom: 10px; }
.banner p { color: rgba(255, 255, 255, 0.85); }

.boards-wrap {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.board-card { cursor: pointer; }
.board-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}
.board-title { font-weight: 600; font-size: 15px; color: var(--text-primary); }
.board-meta {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: var(--text-secondary);
  font-size: 12px;
  margin-bottom: 8px;
}
.board-desc {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.empty-tip { text-align: center; color: #909399; padding: 60px 0; }

.mine-wrap {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 24px;
}
.mine-title { margin-bottom: 16px; color: var(--text-primary); }
.profile-form { max-width: 520px; }
.app-table { cursor: pointer; }

.block-title { font-weight: 600; margin: 16px 0 8px; color: var(--text-primary); }
.block-text {
  white-space: pre-wrap;
  line-height: 1.8;
  background: #f8f9fb;
  padding: 10px 12px;
  border-radius: 6px;
}
.apply-tip { margin: 16px 0; }
.apply-hint { margin-left: 12px; color: #909399; font-size: 12px; }
.steps-bar { margin: 12px 0 16px; }
.timeline-list { padding-left: 4px; }
.timeline-content { line-height: 1.7; }
</style>
