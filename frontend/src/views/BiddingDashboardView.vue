<!-- BiddingDashboardView.vue: 揭榜挂帅看板 — 七步漏斗 + 待办清单 + 超期提醒 -->
<template>
  <div class="bidding-dashboard">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <!-- 顶部统计卡 -->
      <div class="stat-cards">
        <div class="stat-card">
          <div class="stat-num">{{ stats.total || 0 }}</div>
          <div class="stat-label">揭榜挂帅项目总数</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ inProgressCount }}</div>
          <div class="stat-label">流程进行中</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ overduePublishCount }}</div>
          <div class="stat-label">发榜超期未截止</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ overdueMilestoneCount }}</div>
          <div class="stat-label">里程碑超期</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ stats.terminal_counts ? Object.values(stats.terminal_counts).reduce((a, b) => a + b, 0) : 0 }}</div>
          <div class="stat-label">已终止（驳回/流标/取消）</div>
        </div>
      </div>

      <div class="dash-grid">
        <!-- 七步漏斗 -->
        <div class="card">
          <div class="card-title">
            <span>七步工作法漏斗</span>
            <el-tooltip content="各阶段当前项目数" placement="top">
              <el-icon><InfoFilled /></el-icon>
            </el-tooltip>
          </div>
          <div class="funnel-list">
            <div
              v-for="(s, i) in stageRows"
              :key="s.key"
              class="funnel-row"
              :class="{ active: s.count > 0 }"
            >
              <span class="funnel-idx">{{ i + 1 }}</span>
              <span class="funnel-name">{{ s.name }}</span>
              <el-progress
                :percentage="s.pct"
                :color="s.count > 0 ? '#1a3a5c' : '#e4e7ed'"
                :stroke-width="14"
                class="funnel-bar"
              >
                <span class="funnel-count">{{ s.count }}</span>
              </el-progress>
            </div>
          </div>
          <el-divider />
          <div class="terminal-row">
            <el-tag v-for="(count, key) in stats.terminal_counts || {}" :key="key" type="danger" size="small">
              {{ TERMINAL_LABELS[key] }} {{ count }}
            </el-tag>
          </div>
        </div>

        <!-- 待办清单 -->
        <div class="card">
          <div class="card-title">待办清单（按当前阶段）</div>
          <div v-for="s in BIDDING_STAGES" :key="s.key" class="todo-group">
            <div class="todo-stage" @click="gotoStage(s.key)">
              <el-tag size="small" :type="STAGE_COLORS[s.key]">{{ s.name }}</el-tag>
              <span class="todo-count">{{ stageProjects(s.key).length }}</span>
            </div>
            <div v-if="stageProjects(s.key).length" class="todo-items">
              <div v-for="p in stageProjects(s.key).slice(0, 5)" :key="p.id" class="todo-item" @click="gotoProject(p)">
                <span class="todo-title">{{ p.title }}</span>
                <span class="todo-meta">{{ p.demander_name || '' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 超期提醒双表 -->
      <div class="card">
        <div class="card-title">超期提醒</div>
        <el-tabs>
          <el-tab-pane :label="`发榜超期未截止（${overduePublish.length}）`">
            <el-table :data="overduePublish" size="small" stripe>
              <el-table-column prop="title" label="榜单名称" min-width="200">
                <template #default="{ row }">
                  <el-link type="primary" @click="gotoProject(row)">{{ row.title }}</el-link>
                </template>
              </el-table-column>
              <el-table-column prop="demander_name" label="发榜企业" width="150" />
              <el-table-column prop="deadline_date" label="揭榜截止" width="110" align="center" />
              <el-table-column label="超期天数" width="90" align="center">
                <template #default="{ row }">
                  <el-tag type="danger" size="small">{{ row.overdue_days }} 天</el-tag>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="!overduePublish.length" description="暂无发榜超期" :image-size="60" />
          </el-tab-pane>
          <el-tab-pane :label="`里程碑超期（${overdueMilestones.length}）`">
            <el-table :data="overdueMilestones" size="small" stripe>
              <el-table-column prop="project_title" label="榜单名称" min-width="200" />
              <el-table-column prop="content" label="里程碑" min-width="160" show-overflow-tooltip />
              <el-table-column prop="planned_date" label="计划完成" width="110" align="center" />
              <el-table-column label="超期天数" width="90" align="center">
                <template #default="{ row }">
                  <el-tag type="danger" size="small">{{ row.overdue_days }} 天</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="90" align="center">
                <template #default="{ row }">
                  <el-tag size="small">{{ MILESTONE_STATUS_LABELS[row.status] || row.status }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="!overdueMilestones.length" description="暂无里程碑超期" :image-size="60" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { InfoFilled } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import { biddingApi } from '@/api/bidding'
import {
  BIDDING_STAGES, STAGE_COLORS, TERMINAL_LABELS, MILESTONE_STATUS_LABELS,
} from '@/config/biddingStages'

const router = useRouter()
const stats = ref({ total: 0, stage_counts: {}, terminal_counts: {}, projects: [] })
const loading = ref(false)

const overduePublish = computed(() => stats.value.overdue_publish || [])
const overdueMilestones = computed(() => stats.value.overdue_milestones || [])
const overduePublishCount = computed(() => overduePublish.value.length)
const overdueMilestoneCount = computed(() => overdueMilestones.value.length)

const inProgressCount = computed(() => {
  const sc = stats.value.stage_counts || {}
  return BIDDING_STAGES.reduce((sum, s) => sum + (sc[s.key] || 0), 0)
})

function stageProjects(key) {
  return (stats.value.projects || []).filter(p => p.current_stage === key)
}

const stageRows = computed(() => {
  const sc = stats.value.stage_counts || {}
  const max = Math.max(...BIDDING_STAGES.map(s => sc[s.key] || 0), 1)
  return BIDDING_STAGES.map(s => ({
    key: s.key,
    name: s.name,
    count: sc[s.key] || 0,
    pct: Math.round(((sc[s.key] || 0) / max) * 100),
  }))
})

function gotoProject(p) {
  router.push({ path: '/bidding', query: { focus: p.id } })
}
function gotoStage(key) {
  router.push({ path: '/bidding', query: { stage: key } })
}

async function fetchStats() {
  loading.value = true
  try {
    const res = await biddingApi.getStats()
    if (res.code === 0) stats.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
</script>

<style scoped>
.bidding-dashboard {
  min-height: 100vh;
  background: var(--bg-light);
}
.page-body {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.stat-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}
.stat-card {
  background: var(--bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 20px;
  text-align: center;
}
.stat-num {
  font-size: 32px;
  font-weight: 700;
  color: var(--primary-color);
}
.stat-label { color: var(--text-secondary); margin-top: 6px; font-size: 13px; }
.dash-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.card {
  background: var(--bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 20px;
}
.card-title {
  font-weight: 600;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-primary);
}
.funnel-list { display: flex; flex-direction: column; gap: 10px; }
.funnel-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.funnel-idx {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--primary-color);
  color: #fff;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.funnel-row:not(.active) .funnel-idx { background: #c0c4cc; }
.funnel-name { width: 70px; font-size: 13px; flex-shrink: 0; }
.funnel-bar { flex: 1; }
.funnel-count { font-size: 12px; color: var(--text-secondary); padding-left: 6px; }
.terminal-row { display: flex; gap: 8px; }
.todo-group { margin-bottom: 8px; }
.todo-stage {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 0;
}
.todo-count {
  color: var(--text-secondary);
  font-size: 12px;
}
.todo-items {
  padding-left: 8px;
  border-left: 2px solid #e4e7ed;
  margin-left: 10px;
}
.todo-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 8px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13px;
}
.todo-item:hover { background: #f5f7fa; }
.todo-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.todo-meta { color: var(--text-secondary); flex-shrink: 0; }

@media (max-width: 1200px) {
  .stat-cards { grid-template-columns: repeat(3, 1fr); }
  .dash-grid { grid-template-columns: 1fr; }
}
</style>
