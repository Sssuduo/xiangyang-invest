<template>
  <div class="construction-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 工具栏 -->
        <div class="toolbar">
          <el-input
            v-model="searchText"
            placeholder="搜索项目名称、建设内容..."
            :prefix-icon="Search"
            clearable
            class="search-input"
            @input="handleSearch"
          />
          <el-input
            v-model="filterConstructionUnit"
            placeholder="建设单位"
            clearable
            style="width: 180px;"
            @input="handleSearch"
          />
          <el-select
            v-model="filterDispatchStatus"
            placeholder="调度状态"
            clearable
            style="width: 140px;"
            @change="currentPage = 1; fetchData()"
          >
            <el-option
              v-for="d in dicts.dispatch_statuses"
              :key="d.code"
              :label="d.name"
              :value="d.code"
            />
          </el-select>
          <el-select
            v-model="filterProjectType"
            placeholder="项目类型"
            clearable
            style="width: 140px;"
            @change="currentPage = 1; fetchData()"
          >
            <el-option
              v-for="d in dicts.project_types"
              :key="d.code"
              :label="d.name"
              :value="d.code"
            />
          </el-select>
          <el-select
            v-model="filterResponsibleUnit"
            placeholder="责任单位"
            clearable
            style="width: 160px;"
            @change="currentPage = 1; fetchData()"
          >
            <el-option
              v-for="d in dicts.organizations"
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
            <el-icon><Plus /></el-icon> 添加在建项目
          </el-button>
        </div>

        <!-- 表格 -->
        <el-table
          ref="tableRef"
          :data="pagedProjects"
          stripe
          row-key="id"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          empty-text="暂无在建项目数据"
          style="width: 100%"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column prop="order_no" label="序号" width="60" align="center" />
          <el-table-column prop="project_name" label="在建项目名称" min-width="140" show-overflow-tooltip />
          <el-table-column label="项目类型" width="110">
            <template #default="{ row }">
              <span class="project-type-tag">{{ row.project_type_name || row.project_type_code }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="construction_unit" label="建设单位" width="130" show-overflow-tooltip />
          <el-table-column label="建设内容" min-width="160">
            <template #default="{ row }">
              <el-tooltip :content="row.construction_content" placement="top" :show-after="300" popper-class="content-tooltip">
                <span class="content-preview">{{ truncate(row.construction_content, 40) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="调度状态" width="95" align="center">
            <template #default="{ row }">
              <el-tag
                effect="dark"
                size="small"
                :color="dispatchStatusColor(row.dispatch_status_code)"
                style="border: none; color: #fff;"
              >
                {{ row.dispatch_status_name || row.dispatch_status_code }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="责任单位" width="120" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.responsible_unit_name || row.responsible_unit_code || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="responsible_person" label="责任人" width="70" align="center" />
          <el-table-column label="操作" width="180" fixed="right">
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
                  size="small"
                  link
                  type="warning"
                  @click="handleProgress(row)"
                >进展</el-button>
                <el-dropdown trigger="click" @command="(cmd) => handleRowCmd(cmd, row)">
                  <el-button size="small" link type="info" class="more-btn">
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="view">
                        <el-icon><View /></el-icon> 项目详情
                      </el-dropdown-item>
                      <el-dropdown-item
                        v-if="businessAuth.hasPermission('construction', 'delete')"
                        command="delete"
                        style="color: #f56c6c;"
                      >
                        <el-icon><Delete /></el-icon> 删除
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
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
            :total="projects.length"
            layout="total, sizes, prev, pager, next"
            background
            small
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
          <el-checkbox v-model="showAll" class="show-all-check" @change="handleShowAllChange">
            展示全部
          </el-checkbox>
        </div>
      </div>
    </div>

    <!-- 编辑抽屉 -->
    <el-drawer
      v-model="editDrawerVisible"
      direction="rtl"
      size="780px"
      @closed="resetForm"
    >
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">
            {{ editMode === 'create' ? '新建在建项目' : '编辑在建项目' }}
          </span>
        </div>
      </template>
      <div class="drawer-form">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" label-position="right">
          <!-- 基础信息 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><InfoFilled /></el-icon></span>
            <span class="section-title">基础信息</span>
          </div>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="顺序号">
                <el-input-number
                  v-model="form.order_no"
                  :min="0"
                  :max="9999"
                  controls-position="right"
                  style="width: 100%;"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="项目类型" prop="project_type_code">
                <el-select v-model="form.project_type_code" placeholder="请选择项目类型" style="width: 100%;">
                  <el-option
                    v-for="d in dicts.project_types"
                    :key="d.code"
                    :label="d.name"
                    :value="d.code"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="项目名称" prop="project_name">
            <el-input v-model="form.project_name" placeholder="请输入项目名称" maxlength="255" show-word-limit />
          </el-form-item>
          <el-form-item label="调度状态">
            <el-select v-model="form.dispatch_status_code" placeholder="请选择调度状态" style="width: 100%;">
              <el-option
                v-for="d in dicts.dispatch_statuses"
                :key="d.code"
                :label="d.name"
                :value="d.code"
              />
            </el-select>
          </el-form-item>

          <!-- 建设内容 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><Document /></el-icon></span>
            <span class="section-title">建设内容</span>
          </div>
          <el-form-item label="建设内容">
            <el-input
              v-model="form.construction_content"
              type="textarea"
              :rows="6"
              placeholder="请输入建设内容..."
              maxlength="5000"
              show-word-limit
            />
          </el-form-item>

          <!-- 工作路径图 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><Guide /></el-icon></span>
            <span class="section-title">工作路径图</span>
          </div>
          <el-form-item label="工作路径图">
            <el-input
              v-model="form.work_roadmap"
              type="textarea"
              :rows="4"
              placeholder="请输入工作路径图..."
              maxlength="3000"
              show-word-limit
            />
          </el-form-item>

          <!-- 单位信息 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><OfficeBuilding /></el-icon></span>
            <span class="section-title">单位信息</span>
          </div>
          <el-form-item label="建设单位">
            <el-input v-model="form.construction_unit" placeholder="请输入建设单位" maxlength="255" />
          </el-form-item>
          <el-form-item label="责任单位">
            <el-select v-model="form.responsible_unit_code" placeholder="请选择责任单位" clearable style="width: 100%;">
              <el-option
                v-for="d in dicts.organizations"
                :key="d.code"
                :label="d.name"
                :value="d.code"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="责任人">
            <el-input v-model="form.responsible_person" placeholder="请输入责任人" maxlength="64" style="width: 48%;" />
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

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="detailProject?.project_name || '项目详情'"
      width="700px"
      :close-on-click-modal="false"
    >
      <template v-if="detailProject">
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-label">序号</span><span>{{ detailProject.order_no }}</span></div>
          <div class="detail-item"><span class="detail-label">项目类型</span><span class="project-type-tag">{{ detailProject.project_type_name || detailProject.project_type_code }}</span></div>
          <div class="detail-item"><span class="detail-label">调度状态</span><el-tag effect="dark" size="small" :color="dispatchStatusColor(detailProject.dispatch_status_code)">{{ detailProject.dispatch_status_name || detailProject.dispatch_status_code }}</el-tag></div>
          <div class="detail-item"><span class="detail-label">建设单位</span><span>{{ detailProject.construction_unit || '-' }}</span></div>
          <div class="detail-item"><span class="detail-label">责任单位</span><span>{{ detailProject.responsible_unit_name || detailProject.responsible_unit_code || '-' }}</span></div>
          <div class="detail-item"><span class="detail-label">责任人</span><span>{{ detailProject.responsible_person || '-' }}</span></div>
        </div>
        <div class="detail-section" v-if="detailProject.construction_content">
          <h4>建设内容</h4>
          <p>{{ detailProject.construction_content }}</p>
        </div>
        <div class="detail-section" v-if="detailProject.work_roadmap">
          <h4>工作路径图</h4>
          <p>{{ detailProject.work_roadmap }}</p>
        </div>
        <!-- 工作进展 -->
        <div class="detail-section" v-if="detailProject.work_progresses && detailProject.work_progresses.length > 0">
          <h4>工作进展 ({{ detailProject.work_progresses.length }}条)</h4>
          <div v-for="(wp, i) in detailProject.work_progresses" :key="i" class="detail-sub-item">
            <span class="sub-date">{{ wp.start_date }} ~ {{ wp.end_date }}</span>
            <p>{{ wp.content }}</p>
          </div>
        </div>
        <!-- 存在问题 -->
        <div class="detail-section" v-if="detailProject.issues && detailProject.issues.length > 0">
          <h4>存在问题 ({{ detailProject.issues.length }}条)</h4>
          <div v-for="(iss, i) in detailProject.issues" :key="i" class="detail-sub-item">
            <el-tag size="small" effect="plain">{{ iss.issue_type_name || iss.issue_type_code }}</el-tag>
            <el-tag size="small" effect="dark" :color="resolutionStatusColor(iss.resolution_status_code)" style="margin-left: 8px; border: none; color: #fff;">{{ iss.resolution_status_name || iss.resolution_status_code }}</el-tag>
            <p v-if="iss.issue_description" style="margin-top: 6px;">{{ iss.issue_description }}</p>
            <p v-if="iss.resolution_note" style="color: #909399; font-size: 12px;">解决措施：{{ iss.resolution_note }}</p>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, MoreFilled, View, Delete,
  InfoFilled, Document, OfficeBuilding, Guide
} from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import {
  getDicts, getProjects, createProject, updateProject,
  getProject, deleteProject, getMaxOrderNo
} from '@/api/construction'
import { useBusinessAuthStore } from '@/stores/businessAuth'

const businessAuth = useBusinessAuthStore()
const tableRef = ref(null)
const projects = ref([])
const loading = ref(false)
const searchText = ref('')
const filterConstructionUnit = ref('')
const filterDispatchStatus = ref('')
const filterProjectType = ref('')
const filterResponsibleUnit = ref('')
const selectedIds = ref([])

const dicts = reactive({
  project_types: [],
  dispatch_statuses: [],
  issue_types: [],
  resolution_statuses: [],
  organizations: []
})

// 分页
const currentPage = ref(1)
const pageSize = ref(5)
const showAll = ref(false)

const pagedProjects = computed(() => {
  if (showAll.value) return projects.value
  const start = (currentPage.value - 1) * pageSize.value
  return projects.value.slice(start, start + pageSize.value)
})

// 编辑抽屉
const editDrawerVisible = ref(false)
const editMode = ref('create')
const editingId = ref(null)
const formRef = ref(null)
const saving = ref(false)

const defaultForm = () => ({
  order_no: 0,
  project_name: '',
  project_type_code: '',
  dispatch_status_code: 'dispatching',
  construction_content: '',
  work_roadmap: '',
  construction_unit: '',
  responsible_unit_code: '',
  responsible_person: ''
})
const form = reactive(defaultForm())

const rules = {
  project_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  project_type_code: [{ required: true, message: '请选择项目类型', trigger: 'change' }]
}

// 详情弹窗
const detailVisible = ref(false)
const detailProject = ref(null)

let searchTimer = null

// ---- 工具函数 ----
function truncate(text, max) {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}

function dispatchStatusColor(code) {
  return code === 'dispatching' ? '#409eff' : '#909399'
}

function resolutionStatusColor(code) {
  const map = { pending: '#f56c6c', processing: '#e6a23c', resolved: '#67c23a' }
  return map[code] || '#909399'
}

// ---- 数据加载 ----
onMounted(async () => {
  await loadDicts()
  fetchData()
})

async function loadDicts() {
  try {
    const res = await getDicts()
    if (res.code === 0) Object.assign(dicts, res.data)
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (searchText.value) params.search = searchText.value
    if (filterConstructionUnit.value) params.construction_unit = filterConstructionUnit.value
    if (filterDispatchStatus.value) params.dispatch_status = filterDispatchStatus.value
    if (filterProjectType.value) params.project_type = filterProjectType.value
    if (filterResponsibleUnit.value) params.responsible_unit = filterResponsibleUnit.value
    const res = await getProjects(params)
    projects.value = res.data || []
    currentPage.value = 1
  } catch {
    projects.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchData, 300)
}

function handleSelectionChange(selection) {
  selectedIds.value = selection.map(s => s.id)
}

// ---- 分页 ----
function handlePageChange(page) { currentPage.value = page }
function handleSizeChange(size) { pageSize.value = size; currentPage.value = 1 }
function handleShowAllChange(val) { currentPage.value = 1 }

// ---- 新建 ----
async function openCreate() {
  editMode.value = 'create'
  editingId.value = null
  resetForm()
  try {
    const res = await getMaxOrderNo()
    if (res.code === 0) {
      form.order_no = (res.data?.max_order_no || 0) + 1
    }
  } catch { form.order_no = 0 }
  editDrawerVisible.value = true
}

// ---- 编辑 ----
async function openEdit(row) {
  editMode.value = 'edit'
  editingId.value = row.id
  try {
    const res = await getProject(row.id)
    if (res.code === 0) {
      const d = res.data
      form.order_no = d.order_no ?? 0
      form.project_name = d.project_name || ''
      form.project_type_code = d.project_type_code || ''
      form.dispatch_status_code = d.dispatch_status_code || 'dispatching'
      form.construction_content = d.construction_content || ''
      form.work_roadmap = d.work_roadmap || ''
      form.construction_unit = d.construction_unit || ''
      form.responsible_unit_code = d.responsible_unit_code || ''
      form.responsible_person = d.responsible_person || ''
    }
    editDrawerVisible.value = true
  } catch (err) {
    ElMessage.error(err.message || '获取项目详情失败')
  }
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
      res = await createProject(data)
    } else {
      res = await updateProject(editingId.value, data)
    }

    if (res.code === 0) {
      ElMessage.success(editMode.value === 'create' ? '项目已创建' : '项目已更新')
      editDrawerVisible.value = false
      fetchData()
    } else if (res.code === 2) {
      // 序号冲突
      try {
        await ElMessageBox.confirm(
          res.message + '，是否强制调整序号？',
          '序号冲突',
          { confirmButtonText: '强制调整', cancelButtonText: '取消', type: 'warning' }
        )
        data.force_reorder = true
        const retryRes = editMode.value === 'create'
          ? await createProject(data)
          : await updateProject(editingId.value, data)
        if (retryRes.code === 0) {
          ElMessage.success(editMode.value === 'create' ? '项目已创建' : '项目已更新')
          editDrawerVisible.value = false
          fetchData()
        }
      } catch { /* cancelled */ }
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
      `确定要删除在建项目「${row.project_name}」吗？此操作不可恢复。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteProject(row.id)
    ElMessage.success('项目已删除')
    fetchData()
  } catch { /* cancelled */ }
}

// ---- 进展（占位） ----
function handleProgress(row) {
  ElMessage.info(`项目「${row.project_name}」的工作进展功能即将上线`)
}

// ---- 操作下拉 ----
function handleRowCmd(cmd, row) {
  if (cmd === 'view') {
    handleViewDetail(row)
  } else if (cmd === 'delete') {
    handleDelete(row)
  }
}

// ---- 查看详情 ----
async function handleViewDetail(row) {
  try {
    const res = await getProject(row.id)
    if (res.code === 0) {
      detailProject.value = res.data
      detailVisible.value = true
    }
  } catch (err) {
    ElMessage.error(err.message || '获取项目详情失败')
  }
}
</script>

<style scoped>
.construction-page { min-height: 100vh; background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%); }
.page-body { max-width: 1600px; margin: 0 auto; padding: 28px 32px 60px; }
.content-card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 20px rgba(0,0,0,0.06); }

/* 工具栏 */
.toolbar { display: flex; gap: 16px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
.toolbar-spacer { flex: 1; }
.search-input { width: 320px; }

/* 表格 */
.content-preview { cursor: default; color: #606266; }
.project-type-tag {
  display: inline-block;
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 500;
  color: #1a3a5c;
  background: #e0ecf6;
  border: 1px solid #b8d4ec;
  border-radius: 4px;
}
.action-cell { display: flex; align-items: center; gap: 2px; }
.more-btn { padding: 2px 4px !important; font-size: 16px; }

/* 分页 */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  gap: 16px;
}
.show-all-check { margin-left: 8px; }

/* 抽屉 */
.drawer-title-bar {
  background: linear-gradient(135deg, #3a7abd 0%, #6ba3d6 100%);
  margin: -20px -20px 0 -20px;
  padding: 10px 20px;
}
.drawer-title { color: #fff; font-size: 16px; font-weight: 600; letter-spacing: 1px; }
.drawer-form { padding: 0 4px; }
.drawer-form :deep(.el-form-item) { margin-bottom: 16px; }
.drawer-form :deep(.el-input-number .el-input__inner) { text-align: left; }

/* 分区标题 */
.section-header {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; margin: 20px 0 14px;
  background: #f5f7fa; border-radius: 6px;
  border-left: 3px solid #1a3a5c;
}
.section-icon { color: #1a3a5c; font-size: 16px; display: flex; align-items: center; }
.section-title { font-size: 14px; font-weight: 600; color: #303133; }

.drawer-footer { display: flex; justify-content: center; gap: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #ebeef5; }

/* 详情弹窗 */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 24px;
  margin-bottom: 16px;
}
.detail-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.detail-label {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
  min-width: 56px;
}
.detail-section {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}
.detail-section h4 {
  font-size: 14px;
  color: #303133;
  margin: 0 0 8px;
  font-weight: 600;
}
.detail-section p {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  white-space: pre-wrap;
}
.detail-sub-item {
  padding: 8px 12px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 6px;
}
.sub-date {
  font-size: 12px;
  color: #409eff;
  font-weight: 500;
}
.detail-sub-item p {
  margin: 4px 0 0;
}

/* 表格行 hover */
:deep(.el-table__body tr:hover > td) { background-color: #fef7e8 !important; }
:deep(.el-table td.el-table__cell) { padding: 6px 2px; }
</style>

<!-- 非 scoped 样式：Element Plus teleported popper -->
<style>
.content-tooltip { max-width: 480px !important; white-space: pre-wrap !important; }
</style>
