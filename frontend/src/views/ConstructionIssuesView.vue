<template>
  <div class="construction-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 工具栏 -->
        <div class="toolbar">
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
            style="width: 220px;"
            @change="currentPage = 1; fetchData()"
          >
            <el-option
              v-for="p in projectOptions"
              :key="p.id"
              :label="p.project_name"
              :value="p.id"
            />
          </el-select>
          <el-select
            v-model="filterIssueType"
            placeholder="问题类型"
            clearable
            style="width: 140px;"
            @change="currentPage = 1; fetchData()"
          >
            <el-option
              v-for="d in dicts.issue_types"
              :key="d.code"
              :label="d.name"
              :value="d.code"
            />
          </el-select>
          <el-select
            v-model="filterResStatus"
            placeholder="解决状态"
            clearable
            style="width: 130px;"
            @change="currentPage = 1; fetchData()"
          >
            <el-option
              v-for="d in dicts.resolution_statuses"
              :key="d.code"
              :label="d.name"
              :value="d.code"
            />
          </el-select>
          <div class="toolbar-spacer" />
          <el-button
            v-if="businessAuth.hasPermission('construction', 'add')"
            type="primary"
            @click="openCreate"
          >
            <el-icon><Plus /></el-icon> 添加调度问题
          </el-button>
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
          <el-table-column label="所属项目" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tag class="project-name-tag" @click="handleProjectClick(row)">
                {{ dn(row.project_name) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="问题类型" width="110">
            <template #default="{ row }">
              <span v-if="row.issue_type_name" class="type-tag">{{ row.issue_type_name }}</span>
              <span v-else style="color:#909399;">-</span>
            </template>
          </el-table-column>
          <el-table-column label="问题描述" min-width="220">
            <template #default="{ row }">
              <el-tooltip :content="businessAuth.isVisitor ? '' : row.issue_description" placement="top" :show-after="300" popper-class="content-tooltip">
                <span class="content-preview">{{ dc(truncate(row.issue_description, 50)) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="解决状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag
                effect="dark"
                size="small"
                :color="resolveColor(row.resolution_status_code)"
                style="border:none;color:#fff;"
              >
                {{ row.resolution_status_name || row.resolution_status_code }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="责任部门" width="120" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.main_department_name || row.main_department_code || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="解决措施" min-width="160">
            <template #default="{ row }">
              <span v-if="row.resolution_note" class="content-preview">{{ dc(truncate(row.resolution_note, 40)) }}</span>
              <span v-else style="color:#909399;">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <div class="action-cell">
                <el-button
                  v-if="businessAuth.hasPermission('construction', 'edit')"
                  size="small"
                  link
                  type="primary"
                  @click="openEdit(row)"
                >编辑</el-button>
                <el-button
                  v-if="businessAuth.hasPermission('construction', 'delete')"
                  size="small"
                  link
                  type="danger"
                  @click="handleDelete(row)"
                >删除</el-button>
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
    </div>

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
            <el-select
              v-model="form.project_id"
              placeholder="请选择在建项目"
              filterable
              style="width: 100%;"
            >
              <el-option
                v-for="p in projectOptions"
                :key="p.id"
                :label="p.project_name"
                :value="p.id"
              />
            </el-select>
          </el-form-item>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="问题类型">
                <el-select
                  v-model="form.issue_type_code"
                  placeholder="选择问题类型"
                  clearable
                  style="width: 100%;"
                >
                  <el-option
                    v-for="d in dicts.issue_types"
                    :key="d.code"
                    :label="d.name"
                    :value="d.code"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="解决状态">
                <el-select
                  v-model="form.resolution_status_code"
                  placeholder="选择解决状态"
                  style="width: 100%;"
                >
                  <el-option
                    v-for="d in dicts.resolution_statuses"
                    :key="d.code"
                    :label="d.name"
                    :value="d.code"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="责任部门">
            <el-select
              v-model="form.main_department_code"
              placeholder="选择责任部门"
              clearable
              style="width: 100%;"
            >
              <el-option
                v-for="d in dicts.organizations"
                :key="d.code"
                :label="d.name"
                :value="d.code"
              />
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

    <!-- 项目详情抽屉 -->
    <ConstructionProjectDrawer v-model="projectDrawerVisible" :project-id="projectDrawerId" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Edit } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import ConstructionProjectDrawer from '@/components/investment/ConstructionProjectDrawer.vue'
import { getDicts, getProjects, getIssueList, createIssue, updateIssue, deleteIssue } from '@/api/construction'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import { maskName, maskContent } from '@/utils/mask'

const businessAuth = useBusinessAuthStore()

function dn(v) { return businessAuth.isVisitor ? maskName(v) : (v || '') }
function dc(v) { return businessAuth.isVisitor ? maskContent(v) : (v || '') }
const items = ref([])
const loading = ref(false)
const searchText = ref('')
const filterProjectId = ref('')
const filterIssueType = ref('')
const filterResStatus = ref('')

const projectOptions = ref([])

// 项目详情抽屉
const projectDrawerVisible = ref(false)
const projectDrawerId = ref(null)

function handleProjectClick(row) {
  projectDrawerId.value = row.project_id
  projectDrawerVisible.value = true
}

const dicts = reactive({
  project_types: [],
  dispatch_statuses: [],
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
  await loadDicts()
  await loadProjectOptions()
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
    if (res.code === 0) {
      projectOptions.value = res.data || []
    }
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
.construction-page { min-height: 100vh; background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%); }
.page-body { max-width: 1600px; margin: 0 auto; padding: 28px 32px 60px; }
.content-card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 20px rgba(0,0,0,0.06); }

.toolbar { display: flex; gap: 16px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
.toolbar-spacer { flex: 1; }
.search-input { width: 320px; }

.content-preview { cursor: default; color: #606266; }
.project-name-tag { cursor: pointer; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.project-name-tag:hover { opacity: 0.8; }
.type-tag {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  color: #1a3a5c;
  background: #e0ecf6;
  border: 1px solid #b8d4ec;
  border-radius: 4px;
}
.action-cell { display: flex; align-items: center; gap: 2px; }

.pagination-bar {
  display: flex; align-items: center; justify-content: center;
  margin-top: 20px; padding-top: 16px; border-top: 1px solid #ebeef5; gap: 16px;
}

.drawer-title-bar {
  background: linear-gradient(135deg, #5b9bd5 0%, #8ab8e8 100%);
  margin: 0 -20px 0 -20px; padding: 20px 20px 20px 40px;
}
.drawer-title { color: #fff; font-size: 16px; font-weight: 600; letter-spacing: 1px; display: flex; align-items: center; gap: 8px; }
.drawer-form { padding: 0 4px; }
.drawer-form :deep(.el-form-item) { margin-bottom: 16px; }
.drawer-footer { display: flex; justify-content: center; gap: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #ebeef5; }

:deep(.el-table__body tr:hover > td) { background-color: #fef7e8 !important; }
:deep(.el-table td.el-table__cell) { padding: 6px 2px; }
</style>

<style>
.content-tooltip { max-width: 480px !important; white-space: pre-wrap !important; }
.el-drawer__header { margin-bottom: 0 !important; padding: 0 !important; }
.el-drawer__body { padding: 12px 20px 20px !important; }
</style>
