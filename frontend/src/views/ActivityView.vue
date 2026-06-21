<template>
  <div class="activity-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 工具栏 -->
        <div class="toolbar">
          <el-input v-model="searchText" placeholder="搜索项目名称、动态内容..." :prefix-icon="Search" clearable class="search-input" @input="handleSearch" />
          <el-select v-model="filterProjectId" placeholder="所属项目" clearable @change="fetchData" style="width: 180px;">
            <el-option v-for="p in projectList" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
          <el-date-picker
            v-model="filterDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="onDateRangeChange"
            style="width: 260px;"
          />
          <el-button v-if="selectedIds.length > 0" type="success" @click="handleExport">
            <el-icon><Download /></el-icon> 导出Excel ({{ selectedIds.length }})
          </el-button>
          <el-dropdown trigger="click" @command="handleImportCmd">
            <el-button type="default">
              <el-icon><Upload /></el-icon> 动态导入 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="download-template">
                  <el-icon><Download /></el-icon> 下载导入模板
                </el-dropdown-item>
                <el-dropdown-item command="import-data">
                  <el-icon><Upload /></el-icon> 导入动态
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <div class="toolbar-spacer" />
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 添加动态
          </el-button>
        </div>

        <!-- 表格 -->
        <el-table
          ref="tableRef"
          :data="activities"
          stripe
          row-key="id"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          empty-text="暂无招商动态数据"
          style="width: 100%"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column label="所属项目" width="180">
            <template #default="{ row }">
              <el-tag effect="plain" size="small" type="info">{{ row.project_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="date" label="日期" width="170" />
          <el-table-column label="动态内容" min-width="240">
            <template #default="{ row }">
              <el-tooltip :content="row.content" placement="top" :show-after="300" popper-class="content-tooltip">
                <span class="content-preview">{{ truncate(row.content, 50) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="附件" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.files && row.files.length > 0" effect="plain" size="small" type="success">{{ row.files.length }}</el-tag>
              <span v-else class="no-data">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="handleView(row)">查看</el-button>
              <el-button size="small" link type="success" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 查看抽屉 -->
    <ActivityDrawer v-model="viewDrawerVisible" :activity="viewActivity" />

    <!-- 编辑抽屉（新建/编辑共用） -->
    <el-drawer v-model="editDrawerVisible" direction="rtl" size="680px" @closed="resetForm">
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">{{ editMode === 'create' ? '新建动态' : '编辑动态' }}</span>
        </div>
      </template>
      <div class="drawer-form">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" label-position="right">
          <!-- 基础信息 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><InfoFilled /></el-icon></span>
            <span class="section-title">基础信息</span>
          </div>
          <el-form-item label="所属项目" prop="project_id">
            <el-select v-model="form.project_id" placeholder="请选择项目" filterable style="width: 100%;">
              <el-option v-for="p in projectList" :key="p.id" :label="p.project_name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="日期" prop="date">
            <el-date-picker
              v-model="form.date"
              type="datetime"
              placeholder="选择日期时间"
              format="YYYY-MM-DD HH:mm"
              value-format="YYYY-MM-DDTHH:mm"
              style="width: 100%;"
            />
          </el-form-item>

          <!-- 动态内容 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><Document /></el-icon></span>
            <span class="section-title">动态内容</span>
          </div>
          <el-form-item label="动态内容" prop="content">
            <el-input v-model="form.content" type="textarea" :rows="4" placeholder="请输入动态内容..." maxlength="5000" show-word-limit />
          </el-form-item>
          <el-form-item label="附件">
            <div class="upload-wrapper">
              <el-upload
                ref="uploadRef"
                v-model:file-list="fileList"
                :action="uploadUrl"
                :headers="uploadHeaders"
                :on-success="handleUploadSuccess"
                :on-error="handleUploadError"
                :before-upload="beforeUpload"
                :on-remove="handleFileRemove"
                multiple
                drag
                accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.png,.jpg,.jpeg"
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖动文件到此处 或 <em>点击上传</em></div>
                <template #tip>
                  <div class="el-upload__tip">支持 PDF/DOC/DOCX/PPT/XLS/图片，可上传多个</div>
                </template>
              </el-upload>
            </div>
          </el-form-item>

          <div class="drawer-footer">
            <el-button @click="editDrawerVisible = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">{{ editMode === 'create' ? '创建' : '保存' }}</el-button>
          </div>
        </el-form>
      </div>
    </el-drawer>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入动态" width="900px" :close-on-click-modal="false" @closed="resetImport">
      <template v-if="importStep === 'select'">
        <el-upload
          ref="importUploadRef"
          :auto-upload="false"
          :limit="1"
          accept=".xlsx,.xls"
          :on-change="handleImportFile"
          :file-list="importFileList"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖动 Excel 文件到此处 或 <em>点击选取文件</em></div>
          <template #tip>
            <div class="el-upload__tip">仅支持 .xlsx / .xls 格式，请先下载导入模板填写数据</div>
          </template>
        </el-upload>
      </template>

      <template v-if="importStep === 'preview'">
        <div class="import-summary">
          <span>总计 <strong>{{ importRows.length }}</strong> 条</span>
          <span class="summary-valid">有效 <strong>{{ importValidCount }}</strong> 条</span>
          <span v-if="importErrorCount > 0" class="summary-error">错误 <strong>{{ importErrorCount }}</strong> 条</span>
        </div>
        <el-alert v-if="importErrorCount > 0" type="warning" :closable="false" show-icon style="margin-bottom: 12px;">
          存在错误数据的行已标红，请修正后重新导入，或删除错误行后进行部分导入
        </el-alert>
        <div class="import-table-wrap">
          <el-table :data="importRows" stripe size="small" max-height="400" row-key="row" :row-class-name="importRowClass">
            <el-table-column type="index" label="#" width="40" />
            <el-table-column v-for="h in importHeaders" :key="h" :label="h" min-width="110" show-overflow-tooltip>
              <template #default="{ row }">{{ row.data[h] ?? '' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag v-if="row._valid" type="success" size="small">正常</el-tag>
                <el-tooltip v-else placement="top" :content="row.errors.join('\n')">
                  <el-tag type="danger" size="small">错误</el-tag>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70" align="center">
              <template #default="{ row, $index }">
                <el-button v-if="!row._valid" size="small" link type="danger" @click="removeImportRow($index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>

      <template #footer>
        <template v-if="importStep === 'select'">
          <el-button @click="importDialogVisible = false">取消</el-button>
        </template>
        <template v-if="importStep === 'preview'">
          <el-button @click="resetImport">重新选择文件</el-button>
          <el-button type="primary" :disabled="importValidCount === 0" :loading="importing" @click="handleImportExecute">
            开始导入 ({{ importValidCount }} 条)
          </el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Document, Plus, Delete, Download, UploadFilled, Upload, ArrowDown, InfoFilled } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import ActivityDrawer from '@/components/investment/ActivityDrawer.vue'
import { getPublicActivities, createActivity, updateActivity, getActivity, deleteActivity } from '@/api/activity'
import { getPublicProjects } from '@/api/investment'
import { downloadActivityExcel } from '@/api/activity_export'
import { downloadActivityImportTemplate, activityImportPreviewApi, activityImportExecute } from '@/api/activity_import'

const tableRef = ref(null)
const activities = ref([])
const loading = ref(false)
const searchText = ref('')
const filterProjectId = ref('')
const filterDateRange = ref([])
const filterDateFrom = ref('')
const filterDateTo = ref('')
const selectedIds = ref([])
const projectList = ref([])

let searchTimer = null

// 查看抽屉
const viewDrawerVisible = ref(false)
const viewActivity = ref(null)

// 编辑抽屉
const editDrawerVisible = ref(false)
const editMode = ref('create')
const editingId = ref(null)
const formRef = ref(null)
const uploadRef = ref(null)
const saving = ref(false)
const fileList = ref([])
const uploadUrl = '/api/upload'
const uploadHeaders = {}

// 导入
const importDialogVisible = ref(false)
const importStep = ref('select')
const importFileList = ref([])
const importUploadRef = ref(null)
const importHeaders = ref([])
const importRows = ref([])
const importing = ref(false)
const importValidCount = ref(0)
const importErrorCount = ref(0)

const defaultForm = () => ({
  project_id: '',
  date: '',
  content: '',
  files: []
})

const form = reactive(defaultForm())

const rules = {
  project_id: [{ required: true, message: '请选择所属项目', trigger: 'change' }],
  date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  content: [{ required: true, message: '请输入动态内容', trigger: 'blur' }]
}

onMounted(async () => { await loadProjects(); fetchData() })

async function loadProjects() {
  try {
    const res = await getPublicProjects()
    if (res.code === 0) projectList.value = res.data || []
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (searchText.value) params.search = searchText.value
    if (filterProjectId.value) params.project_id = filterProjectId.value
    if (filterDateFrom.value) params.date_from = filterDateFrom.value
    if (filterDateTo.value) params.date_to = filterDateTo.value
    const res = await getPublicActivities(params)
    activities.value = res.data || []
  } catch { activities.value = [] }
  finally { loading.value = false }
}

function handleSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(fetchData, 300) }

function onDateRangeChange(vals) {
  if (vals && vals.length === 2) {
    filterDateFrom.value = vals[0]
    filterDateTo.value = vals[1]
  } else {
    filterDateFrom.value = ''
    filterDateTo.value = ''
  }
  fetchData()
}

function handleSelectionChange(selection) { selectedIds.value = selection.map(s => s.id) }

function truncate(text, max) { if (!text) return ''; return text.length > max ? text.slice(0, max) + '...' : text }

// ---- 查看 ----
function handleView(row) {
  viewActivity.value = row
  viewDrawerVisible.value = true
}

// ---- 导出 ----
async function handleExport() {
  try {
    await ElMessageBox.confirm(
      `确定要导出选中的 ${selectedIds.value.length} 条动态为 Excel 文件吗？`,
      '确认导出',
      { confirmButtonText: '导出', cancelButtonText: '取消', type: 'info' }
    )
    await downloadActivityExcel(selectedIds.value)
    ElMessage.success('导出成功')
  } catch { /* cancelled */ }
}

// ---- 导入 ----
function handleImportCmd(cmd) {
  if (cmd === 'download-template') {
    downloadActivityImportTemplate().catch(err => ElMessage.error(err.message))
  } else if (cmd === 'import-data') {
    resetImport()
    importDialogVisible.value = true
  }
}

function resetImport() {
  importStep.value = 'select'
  importFileList.value = []
  importHeaders.value = []
  importRows.value = []
  importValidCount.value = 0
  importErrorCount.value = 0
}

async function handleImportFile(file) {
  importFileList.value = [file]
  try {
    const res = await activityImportPreviewApi(file.raw)
    importHeaders.value = res.data.headers
    importRows.value = res.data.rows
    importValidCount.value = res.data.valid_count
    importErrorCount.value = res.data.error_count
    importStep.value = 'preview'
  } catch (err) {
    ElMessage.error(err.message)
    importFileList.value = []
  }
}

function importRowClass({ row }) { return !row._valid ? 'import-error-row' : '' }

function removeImportRow(idx) {
  importRows.value.splice(idx, 1)
  importValidCount.value = importRows.value.filter(r => r._valid).length
  importErrorCount.value = importRows.value.length - importValidCount.value
}

async function handleImportExecute() {
  const validRows = importRows.value.filter(r => r._valid)
  if (validRows.length === 0) {
    ElMessage.warning('没有有效数据可导入')
    return
  }
  importing.value = true
  try {
    const res = await activityImportExecute(validRows)
    if (res.code === 0) {
      ElMessage.success(`成功导入 ${res.data?.count || validRows.length} 条记录`)
      importDialogVisible.value = false
      fetchData()
    }
  } catch (err) { ElMessage.error(err.message) }
  finally { importing.value = false }
}

// ---- 新建 ----
function openCreate() {
  editMode.value = 'create'
  editingId.value = null
  resetForm()
  fileList.value = []
  editDrawerVisible.value = true
}

// ---- 编辑 ----
async function openEdit(row) {
  editMode.value = 'edit'
  editingId.value = row.id
  try {
    const res = await getActivity(row.id)
    if (res.code === 0) {
      const d = res.data
      form.project_id = d.project_id || ''
      form.date = d.date ? d.date.replace(' ', 'T') : ''
      form.content = d.content || ''
      form.files = d.files || []
      // 解析已有的文件列表
      try {
        fileList.value = Array.isArray(d.files) ? d.files.map((url, i) => ({ name: url.split('/').pop() || `文件${i+1}`, url })) : []
      } catch { fileList.value = [] }
    }
    editDrawerVisible.value = true
  } catch (err) { ElMessage.error(err.message) }
}

function resetForm() {
  Object.assign(form, defaultForm())
  fileList.value = []
  formRef.value?.clearValidate()
}

// ---- 文件上传处理 ----
function handleUploadSuccess(response, file) {
  if (response.code === 0) { file.url = response.data.url }
}
function handleUploadError() { ElMessage.error('文件上传失败') }
function beforeUpload(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  const allowed = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg']
  if (!allowed.includes(ext)) {
    ElMessage.error(`不支持的文件类型: .${ext}`)
    return false
  }
  return true
}
function handleFileRemove(file) {
  const idx = fileList.value.findIndex(f => f.url === file.url || f.uid === file.uid)
  if (idx > -1) fileList.value.splice(idx, 1)
}

// ---- 保存 ----
async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const docUrls = fileList.value.filter(f => f.url).map(f => f.url)
    const data = {
      project_id: form.project_id,
      date: form.date,
      content: form.content,
      files: docUrls
    }

    if (editMode.value === 'create') {
      await createActivity(data)
      ElMessage.success('动态创建成功')
      editDrawerVisible.value = false
      fetchData()
    } else {
      await updateActivity(editingId.value, data)
      ElMessage.success('动态更新成功')
      editDrawerVisible.value = false
      fetchData()
    }
  } catch (err) { ElMessage.error(err.message) }
  finally { saving.value = false }
}

// ---- 删除 ----
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除该动态吗？`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    await deleteActivity(row.id)
    ElMessage.success('动态已删除')
    fetchData()
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.activity-page { min-height: 100vh; background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%); }
.page-body { max-width: 1600px; margin: 0 auto; padding: 28px 32px 60px; }
.content-card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 20px rgba(0,0,0,0.06); }
.toolbar { display: flex; gap: 16px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
.toolbar-spacer { flex: 1; }
.search-input { width: 320px; }

.content-preview { cursor: default; color: #606266; }
.content-tooltip { max-width: 480px !important; white-space: pre-wrap !important; }
.no-data { color: #909399; }

/* ---- 编辑抽屉样式 ---- */
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

.upload-wrapper { width: 100%; }
.upload-wrapper :deep(.el-upload-dragger) { padding: 16px 0; }
.upload-wrapper :deep(.el-upload__text) { font-size: 13px; }

/* 导入对话框 */
.import-summary { display: flex; gap: 24px; margin-bottom: 16px; font-size: 14px; }
.import-summary strong { font-size: 18px; margin: 0 2px; }
.summary-valid { color: #67c23a; }
.summary-error { color: #f56c6c; }
.import-table-wrap { border: 1px solid #ebeef5; border-radius: 6px; overflow: hidden; }
:deep(.import-error-row) { background-color: #fef0f0 !important; }
:deep(.import-error-row:hover > td) { background-color: #fde2e2 !important; }
</style>
