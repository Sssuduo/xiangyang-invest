<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <div>
            <h2>调度问题 / Issue 管理</h2>
            <p class="page-subtitle">统一管理所有在建项目调度问题，前台「调度问题管理」页同步展示，便于前后台对照</p>
          </div>
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 添加问题
          </el-button>
        </div>

        <!-- 统计卡片（可视化概览） -->
        <div class="stat-cards">
          <div class="stat-card" :style="{ borderLeftColor: '#909399' }">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">问题总数</div>
          </div>
          <div class="stat-card" :style="{ borderLeftColor: '#f56c6c' }">
            <div class="stat-value" style="color:#f56c6c">{{ stats.pending }}</div>
            <div class="stat-label">待处理</div>
          </div>
          <div class="stat-card" :style="{ borderLeftColor: '#e6a23c' }">
            <div class="stat-value" style="color:#e6a23c">{{ stats.processing }}</div>
            <div class="stat-label">处理中</div>
          </div>
          <div class="stat-card" :style="{ borderLeftColor: '#67c23a' }">
            <div class="stat-value" style="color:#67c23a">{{ stats.resolved }}</div>
            <div class="stat-label">已解决</div>
          </div>
        </div>

        <!-- 搜索筛选 -->
        <div class="filter-bar">
          <el-input
            v-model="searchText"
            placeholder="搜索项目名称、问题描述..."
            :prefix-icon="Search"
            clearable
            class="search-input"
            @input="handleSearch"
          />
          <el-select
            v-model="filterProjectId"
            placeholder="所属项目"
            clearable
            filterable
            style="width: 220px"
            @change="fetchData"
          >
            <el-option v-for="p in projectOptions" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
          <el-select
            v-model="filterIssueType"
            placeholder="问题类型"
            clearable
            style="width: 140px"
            @change="fetchData"
          >
            <el-option v-for="d in dicts.issue_types" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
          <el-select
            v-model="filterResStatus"
            placeholder="解决状态"
            clearable
            style="width: 130px"
            @change="fetchData"
          >
            <el-option v-for="d in dicts.resolution_statuses" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
        </div>

        <!-- 表格 -->
        <el-table
          :data="pagedItems"
          stripe
          row-key="id"
          v-loading="loading"
          empty-text="暂无调度问题数据"
          style="width: 100%"
        >
          <el-table-column label="所属项目" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ row.project_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="问题类型" width="110">
            <template #default="{ row }">
              <span v-if="row.issue_type_name" class="type-tag">{{ row.issue_type_name }}</span>
              <span v-else style="color:#909399;">-</span>
            </template>
          </el-table-column>
          <el-table-column label="问题描述" min-width="220">
            <template #default="{ row }">
              <el-tooltip :content="row.issue_description" placement="top" :show-after="300" popper-class="content-tooltip">
                <span class="content-preview">{{ truncate(row.issue_description, 50) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="解决状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag
                effect="dark"
                size="small"
                :color="resolveColor(row.resolution_status_code)"
                style="border:none;color:#fff"
              >
                {{ row.resolution_status_name || row.resolution_status_code }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="责任部门" width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ row.main_department_name || row.main_department_code || '-' }}</template>
          </el-table-column>
          <el-table-column label="解决措施" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.resolution_note" class="content-preview">{{ truncate(row.resolution_note, 40) }}</span>
              <span v-else style="color:#909399;">-</span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="170">
            <template #default="{ row }">{{ row.created_at ? row.created_at.replace('T', ' ').slice(0, 16) : '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <div class="action-cell">
                <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
                <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[5, 10, 20, 50]"
            :total="items.length"
            layout="total, sizes, prev, pager, next"
            background
            small
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
        </div>
      </div>
    </main>

    <!-- 编辑抽屉 -->
    <el-drawer
      v-model="editDrawerVisible"
      direction="rtl"
      size="600px"
      @closed="resetForm"
    >
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">
            <el-icon><Edit /></el-icon>
            {{ editMode === 'create' ? '新建调度问题' : '编辑调度问题' }}
          </span>
        </div>
      </template>
      <div class="drawer-form">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" label-position="right">
          <el-form-item label="所属项目" prop="project_id">
            <el-select v-model="form.project_id" placeholder="请选择在建项目" filterable style="width:100%">
              <el-option v-for="p in projectOptions" :key="p.id" :label="p.project_name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="问题类型">
                <el-select v-model="form.issue_type_code" placeholder="选择问题类型" clearable style="width:100%">
                  <el-option v-for="d in dicts.issue_types" :key="d.code" :label="d.name" :value="d.code" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="解决状态">
                <el-select v-model="form.resolution_status_code" placeholder="选择解决状态" style="width:100%">
                  <el-option v-for="d in dicts.resolution_statuses" :key="d.code" :label="d.name" :value="d.code" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="责任部门">
            <el-select v-model="form.main_department_code" placeholder="选择责任部门" clearable filterable style="width:100%">
              <el-option v-for="d in dicts.organizations" :key="d.code" :label="d.name" :value="d.code" />
            </el-select>
          </el-form-item>
          <el-form-item label="问题描述" prop="issue_description">
            <el-input
              v-model="form.issue_description"
              type="textarea"
              :rows="4"
              placeholder="请输入问题描述..."
              maxlength="2000"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="解决措施">
            <el-input
              v-model="form.resolution_note"
              type="textarea"
              :rows="3"
              placeholder="请输入解决措施..."
              maxlength="2000"
              show-word-limit
            />
          </el-form-item>

          <div class="drawer-footer">
            <el-button @click="editDrawerVisible = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">
              {{ editMode === 'create' ? '创建' : '保存' }}
            </el-button>
          </div>
        </el-form>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Edit } from '@element-plus/icons-vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getDicts, getProjects, getIssueList, createIssue, updateIssue, deleteIssue } from '@/api/construction'

const items = ref([])
const loading = ref(false)
const searchText = ref('')
const filterProjectId = ref('')
const filterIssueType = ref('')
const filterResStatus = ref('')

const projectOptions = ref([])

const dicts = reactive({
  issue_types: [],
  resolution_statuses: [],
  organizations: []
})

// 分页
const currentPage = ref(1)
const pageSize = ref(10)

const pagedItems = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})

// 统计（可视化概览）
const stats = computed(() => {
  const s = { total: items.value.length, pending: 0, processing: 0, resolved: 0 }
  for (const it of items.value) {
    if (it.resolution_status_code === 'pending') s.pending++
    else if (it.resolution_status_code === 'processing') s.processing++
    else if (it.resolution_status_code === 'resolved') s.resolved++
  }
  return s
})

// 编辑抽屉
const editDrawerVisible = ref(false)
const editMode = ref('create')
const editingId = ref(null)
const formRef = ref(null)
const saving = ref(false)

const defaultForm = () => ({
  project_id: '',
  issue_type_code: '',
  issue_description: '',
  resolution_status_code: 'pending',
  resolution_note: '',
  main_department_code: ''
})
const form = reactive(defaultForm())

const rules = {
  project_id: [{ required: true, message: '请选择所属项目', trigger: 'change' }],
  issue_description: [{ required: true, message: '请输入问题描述', trigger: 'blur' }]
}

let searchTimer = null

function truncate(text, max) {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}

function resolveColor(code) {
  const map = { pending: '#f56c6c', processing: '#e6a23c', resolved: '#67c23a' }
  return map[code] || '#909399'
}

// ---- 数据加载 ----
onMounted(async () => {
  await Promise.all([loadDicts(), loadProjectOptions()])
  fetchData()
})

async function loadDicts() {
  try {
    const res = await getDicts()
    if (res.code === 0) Object.assign(dicts, res.data)
  } catch { /* ignore */ }
}

async function loadProjectOptions() {
  try {
    const res = await getProjects({})
    if (res.code === 0) projectOptions.value = res.data || []
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (searchText.value) params.search = searchText.value
    if (filterProjectId.value) params.project_id = filterProjectId.value
    if (filterIssueType.value) params.issue_type = filterIssueType.value
    if (filterResStatus.value) params.resolution_status = filterResStatus.value
    const res = await getIssueList(params)
    items.value = res.data || []
    currentPage.value = 1
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchData, 300)
}

function handlePageChange(page) { currentPage.value = page }
function handleSizeChange(size) { pageSize.value = size; currentPage.value = 1 }

// ---- 新建 ----
function openCreate() {
  editMode.value = 'create'
  editingId.value = null
  resetForm()
  editDrawerVisible.value = true
}

// ---- 编辑 ----
function openEdit(row) {
  editMode.value = 'edit'
  editingId.value = row.id
  form.project_id = row.project_id
  form.issue_type_code = row.issue_type_code || ''
  form.issue_description = row.issue_description || ''
  form.resolution_status_code = row.resolution_status_code || 'pending'
  form.resolution_note = row.resolution_note || ''
  form.main_department_code = row.main_department_code || ''
  editDrawerVisible.value = true
}

function resetForm() {
  Object.assign(form, defaultForm())
  formRef.value?.clearValidate()
}

// ---- 保存 ----
async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const data = { ...form }
    let res
    if (editMode.value === 'create') {
      res = await createIssue(data)
    } else {
      res = await updateIssue(editingId.value, data)
    }

    if (res.code === 0) {
      ElMessage.success(editMode.value === 'create' ? '调度问题已创建' : '调度问题已更新')
      editDrawerVisible.value = false
      fetchData()
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

// ---- 删除 ----
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      '确定要删除该调度问题吗？此操作不可恢复。',
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    const res = await deleteIssue(row.id)
    if (res.code === 0) {
      ElMessage.success('已删除')
      fetchData()
    }
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; background: #f5f7fa; }
.admin-main { flex: 1; min-width: 0; }
.admin-content { padding: 24px 28px 40px; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 18px; }
.page-header h2 { margin: 0; font-size: 20px; color: #1a3a5c; }
.page-subtitle { margin: 6px 0 0; font-size: 13px; color: #909399; }

/* 统计卡片 */
.stat-cards { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-card {
  flex: 1; min-width: 140px; background: #fff; border-radius: 10px; padding: 18px 20px;
  border-left: 4px solid #909399; box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}
.stat-value { font-size: 28px; font-weight: 700; color: #1a3a5c; line-height: 1.1; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }

/* 筛选栏 */
.filter-bar { display: flex; gap: 14px; margin-bottom: 18px; align-items: center; flex-wrap: wrap; }
.search-input { width: 320px; }

.content-preview { cursor: default; color: #606266; }
.type-tag {
  display: inline-block; padding: 2px 8px; font-size: 12px; color: #1a3a5c;
  background: #e0ecf6; border: 1px solid #b8d4ec; border-radius: 4px;
}
.action-cell { display: flex; align-items: center; gap: 2px; }

.pagination-bar {
  display: flex; align-items: center; justify-content: center;
  margin-top: 20px; padding-top: 16px; border-top: 1px solid #ebeef5;
}

.drawer-title-bar {
  background: linear-gradient(135deg, #5b9bd5 0%, #8ab8e8 100%);
  margin: 0 -20px 0 -20px; padding: 20px 20px 20px 40px;
}
.drawer-title { color: #fff; font-size: 16px; font-weight: 600; letter-spacing: 1px; display: flex; align-items: center; gap: 8px; }
.drawer-form { padding: 0 4px; }
.drawer-form :deep(.el-form-item) { margin-bottom: 16px; }
.drawer-footer { display: flex; justify-content: center; gap: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #ebeef5; }
</style>

<style>
.content-tooltip { max-width: 480px !important; white-space: pre-wrap !important; }
.el-drawer__header { margin-bottom: 0 !important; padding: 0 !important; }
.el-drawer__body { padding: 12px 20px 20px !important; }
</style>
