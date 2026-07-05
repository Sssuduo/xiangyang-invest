<template>
  <div class="knowledge-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <div class="page-header">
          <h1>知识沉淀审核</h1>
          <el-button @click="$router.push('/knowledge')">返回知识库</el-button>
        </div>

        <!-- 状态筛选 -->
        <div class="filter-bar">
          <el-radio-group v-model="filterStatus" @change="fetchData" size="small">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="draft">待审核</el-radio-button>
            <el-radio-button value="approved">已批准</el-radio-button>
            <el-radio-button value="rejected">已拒绝</el-radio-button>
          </el-radio-group>
        </div>

        <el-table :data="drafts" row-key="id" v-loading="loading" empty-text="暂无知识草稿" style="margin-top: 16px;">
          <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
          <el-table-column label="分类" width="100" align="center">
            <template #default="{ row }">
              <el-tag effect="dark" size="small">{{ resolveCategory(row.category) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source" label="来源" width="120" />
          <el-table-column label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="160" align="center">
            <template #default="{ row }">{{ fmtDt(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <template v-if="row.status === 'draft'">
                <el-button size="small" link type="primary" @click="openDetail(row)">查看</el-button>
                <el-button size="small" link type="success" :loading="approveLoadingId === row.id" @click="handleApprove(row)">批准</el-button>
                <el-button size="small" link type="danger" @click="handleReject(row)">拒绝</el-button>
              </template>
              <el-button v-else size="small" link type="primary" @click="openDetail(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 详情弹窗 -->
        <el-dialog v-model="detailVisible" title="知识草稿详情" width="700px">
          <template v-if="currentDraft">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="标题">{{ currentDraft.title }}</el-descriptions-item>
              <el-descriptions-item label="分类">{{ resolveCategory(currentDraft.category) }}</el-descriptions-item>
              <el-descriptions-item label="来源">{{ currentDraft.source }}</el-descriptions-item>
              <el-descriptions-item label="状态">{{ statusLabel(currentDraft.status) }}</el-descriptions-item>
              <el-descriptions-item label="标签" :span="2">
                <el-tag v-for="tag in (currentDraft.tags || [])" :key="tag" size="small" effect="plain" style="margin-right:4px">{{ tag }}</el-tag>
                <span v-if="!currentDraft.tags || currentDraft.tags.length === 0" class="text-muted">无</span>
              </el-descriptions-item>
              <el-descriptions-item label="内容" :span="2">
                <div class="draft-content">{{ currentDraft.content }}</div>
              </el-descriptions-item>
              <el-descriptions-item v-if="currentDraft.review_note" label="审核备注" :span="2">
                {{ currentDraft.review_note }}
              </el-descriptions-item>
            </el-descriptions>
            <div v-if="currentDraft.status === 'draft'" style="text-align:center; margin-top: 20px;">
              <el-button @click="detailVisible = false">取消</el-button>
              <el-button type="success" :loading="approveLoadingId === currentDraft.id" @click="handleApprove(currentDraft); detailVisible = false">批准入库</el-button>
              <el-button type="danger" @click="handleReject(currentDraft); detailVisible = false">拒绝</el-button>
            </div>
          </template>
        </el-dialog>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import { getDrafts, approveDraft, rejectDraft } from '@/api/knowledge'

const CATEGORY_MAP = {
  industry_policy: '产业政策', park_info: '园区信息', supporting: '配套能力',
  land_cost: '土地成本', case_study: '招商案例', demand_pattern: '企业诉求',
  market_data: '市场数据', competitor: '周边竞争'
}

const drafts = ref([])
const loading = ref(false)
const filterStatus = ref('')
const detailVisible = ref(false)
const currentDraft = ref(null)
const approveLoadingId = ref(null)

function resolveCategory(code) { return CATEGORY_MAP[code] || code || '-' }
function statusType(s) { return { draft: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info' }
function statusLabel(s) { return { draft: '待审核', approved: '已批准', rejected: '已拒绝' }[s] || s }
function fmtDt(d) { if (!d) return '-'; return new Date(d + 'Z').toLocaleString('zh-CN', { hour12: false }) }

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    const res = await getDrafts(params)
    if (res.code === 0) drafts.value = res.data || []
  } catch { drafts.value = [] }
  finally { loading.value = false }
}

function openDetail(row) {
  currentDraft.value = row
  detailVisible.value = true
}

async function handleApprove(row) {
  approveLoadingId.value = row.id
  try {
    const res = await approveDraft(row.id)
    if (res.code === 0) {
      ElMessage.success('草稿已批准，知识条目已入库')
      fetchData()
    } else {
      ElMessage.error(res.message || '批准失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '请求失败')
  } finally {
    approveLoadingId.value = null
  }
}

async function handleReject(row) {
  try {
    const { value: note } = await ElMessageBox.prompt('请输入拒绝原因（可选）', '拒绝草稿', {
      confirmButtonText: '确认拒绝',
      cancelButtonText: '取消',
      inputType: 'textarea'
    }).catch(() => null)
    if (note === null || note === undefined) return
    const res = await rejectDraft(row.id, { note: note || '' })
    if (res.code === 0) {
      ElMessage.success('草稿已拒绝')
      fetchData()
    } else {
      ElMessage.error(res.message || '拒绝失败')
    }
  } catch (err) {
    // cancelled
  }
}

onMounted(fetchData)
</script>

<style scoped>
.knowledge-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.page-body {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 32px;
}

.content-card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.06);
  padding: 28px 32px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h1 {
  font-size: 22px;
  color: #1a3a5c;
  margin: 0;
}

.filter-bar {
  display: flex;
  gap: 12px;
}

.draft-content {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.7;
  max-height: 300px;
  overflow-y: auto;
  background: #f8f9fb;
  padding: 12px;
  border-radius: 6px;
}

.text-muted { color: #c0c4cc; }
</style>
