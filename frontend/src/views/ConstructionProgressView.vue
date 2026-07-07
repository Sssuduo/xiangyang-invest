<template>
  <div class="construction-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 工具栏 -->
        <div class="toolbar">
          <el-input
            v-model="searchText"
            placeholder="搜索项目名称、进展内容..."
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
            style="width: 240px;"
            @change="currentPage = 1; fetchData()"
          >
            <el-option
              v-for="p in projectOptions"
              :key="p.id"
              :label="p.project_name"
              :value="p.id"
            />
          </el-select>
          <div class="toolbar-spacer" />
          <el-button
            v-if="businessAuth.hasPermission('construction', 'add')"
            type="primary"
            @click="openCreate"
          >
            <el-icon><Plus /></el-icon> 添加工作进展
          </el-button>
          <el-dropdown
            v-if="businessAuth.hasPermission('construction', 'import')"
            trigger="click"
            style="margin-left: 8px;"
            @command="handleImportCmd"
          >
            <el-button type="default">
              <el-icon><Download /></el-icon> 导入<el-icon style="margin-left:4px;"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="download-template">
                  <el-icon><Download /></el-icon> 下载更新模板
                </el-dropdown-item>
                <!-- <el-dropdown-item command="import-data">
                  <el-icon><Upload /></el-icon> 上传导入
                </el-dropdown-item> -->
                <el-dropdown-item command="update-import-data" divided>
                  <el-icon><Upload /></el-icon> 更新导入（本周）
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <!-- 表格 -->
        <el-table
          :data="pagedItems"
          stripe
          row-key="id"
          v-loading="loading"
          empty-text="暂无工作进展数据"
          style="width: 100%"
        >
          <el-table-column label="所属项目" min-width="220">
            <template #default="{ row }">
              <span class="project-name-card" @click="handleProjectClick(row)">
                {{ dn(row.project_name) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="起止日期" width="220">
            <template #default="{ row }">
              <span class="date-range">{{ row.start_date }} ~ {{ row.end_date }}</span>
            </template>
          </el-table-column>
          <el-table-column label="进展内容" min-width="300">
            <template #default="{ row }">
              <el-tooltip :content="businessAuth.isVisitor ? '' : row.content" placement="top" :show-after="300" popper-class="content-tooltip">
                <span class="content-preview">{{ dc(truncate(row.content, 60)) }}</span>
              </el-tooltip>
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
            {{ editMode === 'create' ? '新建工作进展' : '编辑工作进展' }}
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
              <el-form-item label="开始日期" prop="start_date">
                <el-date-picker
                  v-model="form.start_date"
                  type="date"
                  placeholder="选择开始日期"
                  value-format="YYYY-MM-DD"
                  style="width: 100%;"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="结束日期" prop="end_date">
                <el-date-picker
                  v-model="form.end_date"
                  type="date"
                  placeholder="选择结束日期"
                  value-format="YYYY-MM-DD"
                  style="width: 100%;"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="进展内容" prop="content">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="6"
              placeholder="请输入工作进展内容..."
              maxlength="2000"
              show-word-limit
            />
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
                class="upload-compact"
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖动文件到此处 或 <em>点击上传</em></div>
              </el-upload>
              <div class="el-upload__tip" style="margin-top: 6px;">支持 PDF/DOC/DOCX/PPT/XLS/图片，可上传多个</div>
            </div>
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

    <!-- 导入对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入工作进展"
      width="900px"
      :close-on-click-modal="false"
      @close="resetImport"
    >
      <div v-if="importStep === 'select'">
        <el-alert title="操作说明" type="info" :closable="false" style="margin-bottom: 16px;">
          <p style="margin: 2px 0; font-size: 13px;">
            1. 首次使用请先<strong>下载模板</strong>，按模板格式填写数据<br />
            2. 上传填写好的 Excel 文件，预览无误后执行导入
          </p>
        </el-alert>
        <el-upload
          ref="importUploadRef"
          :auto-upload="false"
          :on-change="handleImportFile"
          :file-list="importFileList"
          :limit="1"
          accept=".xlsx"
          drag
        >
          <el-icon style="font-size: 48px; color: #c0c4cc;"><UploadFilled /></el-icon>
          <div style="margin-top: 8px; color: #606266;">
            将 Excel 文件拖到此处，或<em style="color: #409eff;">点击上传</em>
          </div>
          <template #tip>
            <div style="margin-top: 6px; font-size: 12px; color: #909399;">
              仅支持 .xlsx 格式，请使用下载的模板填写数据
            </div>
          </template>
        </el-upload>
      </div>
      <div v-else>
        <div class="import-summary">
          <el-tag type="success" effect="plain">有效：{{ importValidCount }} 行</el-tag>
          <el-tag v-if="importErrorCount > 0" type="danger" effect="plain" style="margin-left: 8px;">错误：{{ importErrorCount }} 行</el-tag>
          <span style="margin-left: 12px; font-size: 12px; color: #909399;">共 {{ importRows.length }} 行</span>
        </div>
        <el-table :data="importRows" stripe max-height="400" :row-class-name="importRowClass" style="margin-top: 12px;">
          <el-table-column type="index" label="#" width="40" />
          <el-table-column prop="data.project_name" label="所属项目" min-width="180" show-overflow-tooltip />
          <el-table-column prop="data.start_date" label="开始日期" width="120" />
          <el-table-column prop="data.end_date" label="结束日期" width="120" />
          <el-table-column prop="data.content" label="进展内容" min-width="200" show-overflow-tooltip />
          <el-table-column label="错误" min-width="180">
            <template #default="{ row }">
              <div v-if="row.errors && row.errors.length > 0" class="import-errors">
                <span v-for="(e, i) in row.errors" :key="i" class="import-error-item">{{ e }}</span>
              </div>
              <span v-else style="color: #67c23a;">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="60" align="center">
            <template #default="{ $index }">
              <el-button size="small" type="danger" link @click="removeImportRow($index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button v-if="importStep === 'preview'" @click="resetImport">返回</el-button>
        <el-button
          v-if="importStep === 'preview'"
          type="primary"
          :loading="importing"
          :disabled="importValidCount === 0"
          @click="handleImportExecute"
        >
          执行导入（{{ importValidCount }} 行）
        </el-button>
      </template>
    </el-dialog>

    <!-- 更新导入对话框 -->
    <el-dialog
      v-model="updateImportDialogVisible"
      title="更新导入（本周）"
      width="1000px"
      :close-on-click-modal="false"
      @close="resetUpdateImport"
    >
      <div v-if="updateImportStep === 'select'">
        <el-alert title="操作说明" type="info" :closable="false" style="margin-bottom: 16px;">
          <p style="margin: 2px 0; font-size: 13px;">
            1. 首次使用请先<strong>下载更新导入模板</strong>，模板含项目编号+名称+内容<br />
            2. 选择工作进展的时间段（开始 ~ 结束日期），统一应用于所有行<br />
            3. 上传填写好的 Excel 文件，预览确认无误后执行导入<br />
            4. 导入后将记录导入人信息，便于追溯
          </p>
        </el-alert>
        <div style="margin-bottom: 16px; display: flex; align-items: center; gap: 12px;">
          <span style="font-size: 13px; color: #606266; white-space: nowrap;">工作进展时间段：</span>
          <el-date-picker
            v-model="updateImportDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 320px;"
          />
        </div>
        <div class="update-import-upload-wrapper" :class="{ 'upload-disabled': !updateImportDateRangeValid }">
          <el-upload
            ref="updateImportUploadRef"
            :auto-upload="false"
            :on-change="handleUpdateImportFile"
            :file-list="updateImportFileList"
            :limit="1"
            accept=".xlsx"
            drag
            :disabled="!updateImportDateRangeValid"
          >
            <el-icon style="font-size: 48px; color: #c0c4cc;"><UploadFilled /></el-icon>
            <div style="margin-top: 8px; color: #606266;">
              将 Excel 文件拖到此处，或<em style="color: #409eff;">点击上传</em>
            </div>
            <template #tip>
              <div style="margin-top: 6px; font-size: 12px; color: #909399;">
                仅支持 .xlsx 格式，请使用"更新导入模板"。时间段由上方选择器统一指定。
              </div>
            </template>
          </el-upload>
          <div v-if="!updateImportDateRangeValid" class="upload-mask">
            <el-icon style="font-size: 28px; color: #909399; margin-bottom: 6px;"><WarningFilled /></el-icon>
            <span>请先选择上方的工作进展时间段，再上传文件</span>
          </div>
        </div>
      </div>
      <div v-else>
        <div class="import-summary">
          <el-tag type="success" effect="plain">有效：{{ updateImportValidCount }} 行</el-tag>
          <el-tag v-if="updateImportErrorCount > 0" type="danger" effect="plain" style="margin-left: 8px;">错误：{{ updateImportErrorCount }} 行</el-tag>
          <el-tag v-if="updateImportChangedCount > 0" type="warning" effect="plain" style="margin-left: 8px;">内容截取：{{ updateImportChangedCount }} 行</el-tag>
          <span style="margin-left: 12px; font-size: 12px; color: #909399;">共 {{ updateImportRows.length }} 行</span>
        </div>
        <el-table :data="updateImportRows" stripe max-height="400" :row-class-name="updateImportRowClass" style="margin-top: 12px;">
          <el-table-column type="index" label="#" width="40" />
          <el-table-column prop="data.order_no" label="项目编号" width="90" />
          <el-table-column prop="data.project_name" label="项目名称" min-width="180" show-overflow-tooltip />
          <el-table-column label="开始日期" width="115">
            <template #default="{ row }">{{ row.data.start_date }}</template>
          </el-table-column>
          <el-table-column label="结束日期" width="115">
            <template #default="{ row }">{{ row.data.end_date }}</template>
          </el-table-column>
          <el-table-column label="处理后内容" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="{ 'content-changed': row.has_content_change }">{{ row.data.processed_content }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="content_note" label="备注" width="130">
            <template #default="{ row }">
              <el-tag v-if="row.has_content_change" type="warning" size="small">已截取"本周"</el-tag>
              <span v-else style="color: #909399;">保留全部</span>
            </template>
          </el-table-column>
          <el-table-column label="错误" min-width="180">
            <template #default="{ row }">
              <div v-if="row.errors && row.errors.length > 0" class="import-errors">
                <span v-for="(e, i) in row.errors" :key="i" class="import-error-item">{{ e }}</span>
              </div>
              <span v-else style="color: #67c23a;">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="60" align="center">
            <template #default="{ $index }">
              <el-button size="small" type="danger" link @click="removeUpdateImportRow($index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="updateImportDialogVisible = false">取消</el-button>
        <el-button v-if="updateImportStep === 'preview'" @click="resetUpdateImport">返回</el-button>
        <el-button
          v-if="updateImportStep === 'preview'"
          type="primary"
          :loading="updateImporting"
          :disabled="updateImportValidCount === 0"
          @click="handleUpdateImportExecute"
        >
          执行导入（{{ updateImportValidCount }} 行）
        </el-button>
      </template>
    </el-dialog>

    <!-- 项目详情抽屉 -->
    <ConstructionProjectDrawer v-model="projectDrawerVisible" :project-id="projectDrawerId" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Edit, UploadFilled, Download, Upload, ArrowDown, Delete, WarningFilled } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import ConstructionProjectDrawer from '@/components/investment/ConstructionProjectDrawer.vue'
import { getDicts, getProjects, getProgressList, createProgress, updateProgress, deleteProgress } from '@/api/construction'
import { downloadTemplate, previewImport, executeImport } from '@/api/construction_progress_import'
import { downloadUpdateTemplate, previewUpdateImport, executeUpdateImport } from '@/api/construction_progress_update_import'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import { maskName, maskContent } from '@/utils/mask'

const businessAuth = useBusinessAuthStore()

function dn(v) { return businessAuth.isVisitor ? maskName(v) : (v || '') }
function dc(v) { return businessAuth.isVisitor ? maskContent(v) : (v || '') }
const items = ref([])
const loading = ref(false)
const searchText = ref('')
const filterProjectId = ref('')

const projectOptions = ref([])

// 项目详情抽屉
const projectDrawerVisible = ref(false)
const projectDrawerId = ref(null)

function handleProjectClick(row) {
  projectDrawerId.value = row.project_id
  projectDrawerVisible.value = true
}

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

// 文件上传
const uploadRef = ref(null)
const fileList = ref([])
const uploadUrl = '/api/upload'
const uploadHeaders = {}

// 导入相关
const importDialogVisible = ref(false)
const importStep = ref('select')
const importFileList = ref([])
const importRows = ref([])
const importHeaders = ref([])
const importing = ref(false)
const importValidCount = computed(() => importRows.value.filter(r => r._valid).length)
const importErrorCount = computed(() => importRows.value.length - importValidCount.value)

// 更新导入相关
const updateImportDialogVisible = ref(false)
const updateImportStep = ref('select')
const updateImportFileList = ref([])
const updateImportRows = ref([])
const updateImportHeaders = ref([])
const updateImporting = ref(false)
const updateImportValidCount = computed(() => updateImportRows.value.filter(r => r._valid).length)
const updateImportErrorCount = computed(() => updateImportRows.value.length - updateImportValidCount.value)
const updateImportChangedCount = computed(() => updateImportRows.value.filter(r => r.has_content_change).length)
const updateImportDateRange = ref([])  // [startDate, endDate]
const updateImportDateRangeValid = computed(() =>
  updateImportDateRange.value && updateImportDateRange.value.length === 2
)

const defaultForm = () => ({
  project_id: '',
  start_date: null,
  end_date: null,
  content: ''
})
const form = reactive(defaultForm())

const rules = {
  project_id: [{ required: true, message: '请选择所属项目', trigger: 'change' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
  content: [{ required: true, message: '请输入进展内容', trigger: 'blur' }]
}

let searchTimer = null

function truncate(text, max) {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}

// ---- 数据加载 ----
onMounted(async () => {
  await loadProjectOptions()
  fetchData()
})

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
    const res = await getProgressList(params)
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
  form.start_date = row.start_date
  form.end_date = row.end_date
  form.content = row.content
  if (row.files && Array.isArray(row.files)) {
    fileList.value = row.files.map(url => ({ name: url.split('/').pop() || 'file', url }))
  } else {
    fileList.value = []
  }
  editDrawerVisible.value = true
}

function resetForm() {
  Object.assign(form, defaultForm())
  fileList.value = []
  formRef.value?.clearValidate()
}

// ---- 文件上传处理 ----
function handleUploadSuccess(response, file) {
  if (response.code === 0) {
    file.url = response.data.url
  }
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
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const files = fileList.value.filter(f => f.url).map(f => f.url)
    const data = { ...form, files }
    let res
    if (editMode.value === 'create') {
      res = await createProgress(data)
    } else {
      res = await updateProgress(editingId.value, data)
    }

    if (res.code === 0) {
      ElMessage.success(editMode.value === 'create' ? '工作进展已创建' : '工作进展已更新')
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
      '确定要删除该工作进展吗？此操作不可恢复。',
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    const res = await deleteProgress(row.id)
    if (res.code === 0) {
      ElMessage.success('已删除')
      fetchData()
    }
  } catch { /* cancelled */ }
}

// ---- 导入 ----
function handleImportCmd(cmd) {
  if (cmd === 'download-template') {
    handleDownloadUpdateTemplate()
  } else if (cmd === 'import-data') {
    importDialogVisible.value = true
    importStep.value = 'select'
    importFileList.value = []
    importRows.value = []
    importHeaders.value = []
  } else if (cmd === 'update-import-data') {
    updateImportDialogVisible.value = true
    updateImportStep.value = 'select'
    updateImportFileList.value = []
    updateImportRows.value = []
    updateImportHeaders.value = []
    updateImportDateRange.value = []
  }
}

async function handleDownloadUpdateTemplate() {
  try {
    await downloadUpdateTemplate()
    ElMessage.success('更新导入模板下载已开始')
  } catch (err) {
    ElMessage.error(err.message || '模板下载失败')
  }
}

function resetImport() {
  importStep.value = 'select'
  importFileList.value = []
  importRows.value = []
  importHeaders.value = []
}

async function handleImportFile(file) {
  importFileList.value = [file]
  try {
    const res = await previewImport(file.raw)
    importHeaders.value = res.data.headers || []
    importRows.value = res.data.rows || []
    importStep.value = 'preview'
    if (res.data.error_count === 0) {
      ElMessage.success(`预览成功，${res.data.valid_count} 条有效记录`)
    } else {
      ElMessage.warning(`${res.data.error_count} 行存在错误，已自动标红`)
    }
  } catch (err) {
    ElMessage.error(err.message || '预览失败')
    importFileList.value = []
  }
}

async function handleImportExecute() {
  importing.value = true
  try {
    const res = await executeImport(importRows.value)
    ElMessage.success(res.message || '导入成功')
    importDialogVisible.value = false
    fetchData()
  } catch (err) {
    ElMessage.error(err.message || '导入失败')
  } finally {
    importing.value = false
  }
}

function importRowClass({ row }) {
  return row._valid ? '' : 'import-error-row'
}

function removeImportRow(index) {
  importRows.value.splice(index, 1)
}

// ---- 更新导入 ----
function resetUpdateImport() {
  updateImportStep.value = 'select'
  updateImportFileList.value = []
  updateImportRows.value = []
  updateImportHeaders.value = []
  updateImportDateRange.value = []
}

async function handleUpdateImportFile(file) {
  if (!updateImportDateRangeValid.value) {
    ElMessage.warning('请先选择工作进展的时间段')
    return
  }
  updateImportFileList.value = [file]
  try {
    const res = await previewUpdateImport(
      file.raw,
      updateImportDateRange.value[0],
      updateImportDateRange.value[1]
    )
    updateImportHeaders.value = res.data.headers || []
    updateImportRows.value = res.data.rows || []
    updateImportStep.value = 'preview'
    if (res.data.error_count === 0) {
      ElMessage.success(`预览成功，${res.data.valid_count} 条有效记录`)
    } else {
      ElMessage.warning(`${res.data.error_count} 行存在错误，已自动标红`)
    }
  } catch (err) {
    ElMessage.error(err.message || '预览失败')
    updateImportFileList.value = []
  }
}

async function handleUpdateImportExecute() {
  updateImporting.value = true
  try {
    const res = await executeUpdateImport(
      updateImportRows.value,
      updateImportDateRange.value[0],
      updateImportDateRange.value[1]
    )
    ElMessage.success(res.message || '导入成功')
    updateImportDialogVisible.value = false
    fetchData()
  } catch (err) {
    ElMessage.error(err.message || '导入失败')
  } finally {
    updateImporting.value = false
  }
}

function updateImportRowClass({ row }) {
  if (!row._valid) return 'import-error-row'
  if (row.has_content_change) return 'import-content-changed-row'
  return ''
}

function removeUpdateImportRow(index) {
  updateImportRows.value.splice(index, 1)
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
.date-range { color: #409eff; font-size: 13px; font-weight: 500; }
.project-name-card {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 5px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #1a3a5c;
  background: #e0ecf6;
  border: 1px solid #b8d4ec;
  border-radius: 6px;
  transition: all 0.2s;
  vertical-align: middle;
  box-sizing: border-box;
  cursor: pointer;
}
.project-name-card:hover { background: #d0e0f0; border-color: #90bcd8; }
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

/* 导入相关 */
.import-summary { display: flex; align-items: center; gap: 8px; padding: 8px 0; }
.import-errors { display: flex; flex-direction: column; gap: 4px; }
.import-error-item { color: #f56c6c; font-size: 12px; }
:deep(.import-error-row) { background-color: #fef0f0 !important; }
:deep(.import-content-changed-row) { background-color: #fdf6ec !important; }
:deep(.import-content-changed-row.import-error-row) { background-color: #fef0f0 !important; }

/* 内容截取标记 */
.upload-wrapper { width: 100%; }
.upload-compact :deep(.el-upload) { width: 100%; }
.upload-compact :deep(.el-upload-dragger) { width: 100%; padding: 20px; }

/* 更新导入：未选日期时屏蔽上传区域 */
.update-import-upload-wrapper { position: relative; }
.update-import-upload-wrapper.upload-disabled :deep(.el-upload-dragger) {
  opacity: 0.45;
  pointer-events: none;
  user-select: none;
}
.upload-mask {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #909399;
  font-size: 13px;
  font-weight: 500;
  pointer-events: none;
  text-align: center;
  z-index: 10;
  background: rgba(255, 255, 255, 0.85);
  padding: 20px 32px;
  border-radius: 8px;
}
</style>

<style>
.content-tooltip { max-width: 480px !important; white-space: pre-wrap !important; }
.el-drawer__header { margin-bottom: 0 !important; padding: 0 !important; }
.el-drawer__body { padding: 12px 20px 20px !important; }
</style>
