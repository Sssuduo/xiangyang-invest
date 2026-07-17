<template>
  <div class="activity-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 工具栏 -->
        <div class="toolbar">
          <el-input v-model="searchText" placeholder="搜索项目名称、动态内容..." :prefix-icon="Search" clearable class="search-input" @input="handleSearch" />
          <el-select v-model="filterProjectId" placeholder="项目" clearable @change="currentPage = 1; fetchData()" style="width: 180px;">
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
          <el-select v-model="filterTags" multiple collapse-tags placeholder="标签筛选" clearable @change="currentPage = 1; fetchData()" style="width: 200px;">
            <el-option v-for="d in activityTagDicts" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
          <el-button v-if="selectedIds.length > 0" type="success" @click="handleExport">
            <el-icon><Download /></el-icon> 导出Excel ({{ selectedIds.length }})
          </el-button>
          <el-button v-if="selectedIds.length > 0 && businessAuth.hasPermission('activity', 'batch_delete')" type="danger" @click="handleBatchDelete">
            <el-icon><Delete /></el-icon> 批量删除 ({{ selectedIds.length }})
          </el-button>
          <el-dropdown v-if="businessAuth.hasPermission('activity', 'import')" trigger="click" @command="handleImportCmd">
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
          <el-button v-if="businessAuth.hasPermission('activity', 'add')" type="primary" @click="openCreate">
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
          <el-table-column label="项目" width="210">
            <template #default="{ row }">
              <el-tag class="project-name-tag" @click="handleProjectClick(row)">
                {{ dn(row.project_name) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="日期" width="140" align="center">
            <template #default="{ row }">
              <span class="date-cell">{{ row.date || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="动态内容" min-width="210">
            <template #default="{ row }">
              <el-tooltip :content="businessAuth.isVisitor ? '' : row.content" placement="top" :show-after="300" popper-class="content-tooltip">
                <span class="content-preview">{{ dc(truncate(row.content, 50)) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="附件" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.files && row.files.length > 0" effect="plain" size="small" type="success">{{ row.files.length }}</el-tag>
              <span v-else class="no-data">-</span>
            </template>
          </el-table-column>
          <el-table-column label="标签" width="160">
            <template #default="{ row }">
              <template v-if="row.tag_names && row.tag_names.length">
                <el-tag v-for="tag_name in row.tag_names" :key="tag_name" size="small" effect="plain" style="margin-right: 4px; margin-bottom: 2px;">
                  {{ tag_name }}
                </el-tag>
              </template>
              <template v-else>
                <el-tag v-for="tag in (row.tags || [])" :key="tag" size="small" effect="plain" style="margin-right: 4px; margin-bottom: 2px;">
                  {{ getTagName(tag) }}
                </el-tag>
              </template>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="handleView(row)">查看</el-button>
              <el-button v-if="businessAuth.hasPermission('activity', 'edit')" size="small" link type="success" @click="openEdit(row)">编辑</el-button>
              <el-button v-if="businessAuth.hasPermission('activity', 'delete')" size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
          style="margin-top: 20px; justify-content: flex-end;"
        />
      </div>
    </div>

    <!-- 查看抽屉 -->
    <ActivityDrawer v-model="viewDrawerVisible" :activity="viewActivity" />

    <!-- 项目详情抽屉 -->
    <ProjectDrawer v-model="projectDrawerVisible" :project="projectDrawerProject" />

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
          <el-form-item label="项目" prop="project_id">
            <el-select v-model="form.project_id" placeholder="请选择项目" filterable style="width: 100%;">
              <el-option v-for="p in projectList" :key="p.id" :label="p.project_name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="日期" prop="date">
            <el-date-picker
              v-model="form.date"
              type="date"
              placeholder="选择日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
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
            <div class="upload-wrapper" @paste="handleClipboardPaste">
              <el-upload
                ref="uploadRef"
                v-model:file-list="fileList"
                :action="uploadUrl"
                :headers="uploadHeaders"
                :on-success="handleUploadSuccess"
                :on-error="handleUploadError"
                :before-upload="beforeUpload"
                :on-remove="handleFileRemove"
                :show-file-list="false"
                multiple
                drag
                accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.png,.jpg,.jpeg"
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖动文件到此处 或 <em>点击上传</em></div>
                <template #tip>
                  <div class="el-upload__tip">支持 PDF/DOC/DOCX/PPT/XLS/图片，可多个上传</div>
                </template>
              </el-upload>
              <!-- 文件缩略图网格 -->
              <div v-if="fileList.length > 0" class="file-thumbnail-grid">
                <div v-for="(file, idx) in fileList" :key="file.uid || idx" class="file-thumb-card">
                  <div class="thumb-preview">
                    <img v-if="isImageFile(file)" :src="getFilePreviewUrl(file)" class="thumb-img" />
                    <div v-else-if="isPdfFile(file)" class="thumb-pdf">
                      <el-icon :size="32"><Document /></el-icon>
                      <span>PDF</span>
                    </div>
                    <div v-else class="thumb-generic">
                      <el-icon :size="28"><Document /></el-icon>
                    </div>
                    <div class="thumb-remove" @click="handleThumbRemove(idx)">
                      <el-icon><Close /></el-icon>
                    </div>
                  </div>
                  <div class="thumb-name" :title="getFileName(file)">{{ getFileName(file) }}</div>
                </div>
              </div>
            </div>
            <!-- 粘贴图片专属区域 -->
            <div class="paste-zone" @paste="handleClipboardPaste" tabindex="0" title="点击此处后按 Ctrl+V 粘贴图片">
              <span class="paste-icon"><el-icon><Picture /></el-icon></span>
              <span class="paste-label">粘贴截图</span>
              <span class="paste-hint">点击此处 / 鼠标停留 · 按 <kbd>Ctrl+V</kbd> 插入图片</span>
            </div>
          </el-form-item>

          <!-- 动态标签 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><PriceTag /></el-icon></span>
            <span class="section-title">动态标签</span>
          </div>
          <el-form-item label="标签">
            <el-select v-model="form.tags" multiple placeholder="请选择标签" style="width: 100%;">
              <el-option v-for="d in activityTagDicts" :key="d.code" :label="d.name" :value="d.code" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联诉求">
            <el-select v-model="form.demand_ids" multiple placeholder="选择关联的诉求（可选）" filterable style="width: 100%;" :disabled="!form.project_id">
              <el-option v-for="d in projectDemands" :key="d.id" :label="d.demand_content ? d.demand_content.slice(0, 50) : `诉求#${d.id}`" :value="d.id">
                <span style="float:left">{{ d.demand_content ? d.demand_content.slice(0, 50) : `诉求#${d.id}` }}</span>
                <el-tag size="small" effect="plain" style="float:right; margin-left:8px" :type="d.status === 'resolved' ? 'success' : d.status === 'processing' ? 'warning' : 'info'">
                  {{ d.status === 'pending' ? '待回应' : d.status === 'processing' ? '协调中' : '已回应' }}
                </el-tag>
              </el-option>
            </el-select>
          </el-form-item>

          <div class="drawer-footer">
            <el-button @click="editDrawerVisible = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">{{ editMode === 'create' ? '创建' : '保存' }}</el-button>
          </div>
        </el-form>
      </div>
    </el-drawer>

    <!-- ========== 下载导入模板对话框 ========== -->
    <el-dialog
      v-model="templateDialogVisible"
      title="下载导入模板"
      width="780px"
      :close-on-click-modal="false"
      @closed="resetTemplateDialog"
    >
      <!-- 筛选栏 -->
      <div class="template-filter">
        <span class="filter-label">跟进状态：</span>
        <el-select v-model="templateFollowStatus" placeholder="全部" clearable style="width: 200px;" @change="loadTemplateProjects">
          <el-option v-for="s in followStatusList" :key="s.code" :label="s.name" :value="s.code" />
        </el-select>
        <el-button type="primary" @click="loadTemplateProjects">
          <el-icon><Search /></el-icon> 查询
        </el-button>
        <span class="template-count">已勾选 {{ templateSelectedCount }} / {{ templateProjects.length }} 个项目</span>
      </div>

      <!-- 项目表格 -->
      <el-table
        ref="templateTableRef"
        :data="templateProjects"
        size="small"
        max-height="380"
        row-key="id"
        class="template-table"
        empty-text="暂无匹配的项目"
        @selection-change="handleTemplateSelectionChange"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="跟进状态" width="110">
          <template #default="{ row }">
            <span>{{ row.follow_status_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="invest_enterprise" label="投资企业" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="70" align="center">
          <template #default="{ row, $index }">
            <el-button size="small" link type="danger" @click="removeTemplateProject($index)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <el-button @click="templateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleDownloadTemplate" :disabled="templateSelectedCount === 0">
          <el-icon><Download /></el-icon> 下载导入模板 ({{ templateSelectedCount }} 个项目)
        </el-button>
      </template>
    </el-dialog>

    <!-- ========== 导入动态对话框 ========== -->
    <el-dialog v-model="importDialogVisible" title="导入动态" width="1080px" :close-on-click-modal="false" @closed="resetImport">
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
            <div class="el-upload__tip">仅支持 .xlsx / .xls 格式。系统将自动识别动态内容中的日期并智能拆分为多条记录。</div>
          </template>
        </el-upload>
      </template>

      <template v-if="importStep === 'preview'">
        <!-- 统计信息 -->
        <div class="import-summary">
          <span>总计 <strong>{{ importRows.length }}</strong> 条</span>
          <span class="summary-valid">有效 <strong>{{ importValidCount }}</strong> 条</span>
          <span v-if="importErrorCount > 0" class="summary-error">错误 <strong>{{ importErrorCount }}</strong> 条</span>
          <span v-if="importSplitInfo" class="summary-split">{{ importSplitInfo }}</span>
        </div>

        <!-- 全局年份设置 -->
        <div class="import-year-bar">
          <span class="year-label">默认年份：</span>
          <el-input-number v-model="importDefaultYear" :min="2000" :max="2100" size="small" style="width: 120px;" @change="onDefaultYearChange" />
          <span class="year-hint">（可逐行修改年份列）</span>
        </div>

        <el-alert v-if="importErrorCount > 0" type="warning" :closable="false" show-icon style="margin-bottom: 12px;">
          存在错误数据的行已标红，请修正后重新导入，或删除错误行后进行部分导入
        </el-alert>
        <el-alert v-if="importHasSplit" type="info" :closable="false" show-icon style="margin-bottom: 12px;">
          系统已自动识别动态内容中的日期，并按日期拆分为独立行。请核对拆分结果，确认无误后点击导入。
        </el-alert>

        <div class="import-table-wrap">
          <el-table :data="importRows" stripe size="small" max-height="400" row-key="row" :row-class-name="importRowClass">
            <el-table-column type="index" label="#" width="40" />
            <el-table-column label="项目ID" width="75" align="center">
              <template #default="{ row }">
                <span class="project-id-tag">{{ row.data.project_id || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="项目" width="150" show-overflow-tooltip>
              <template #default="{ row }">{{ row.data.project_name }}</template>
            </el-table-column>
            <el-table-column label="年份" width="90" align="center">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.data.year"
                  :min="2000"
                  :max="2100"
                  size="small"
                  controls-position="right"
                  style="width: 85px;"
                />
              </template>
            </el-table-column>
            <el-table-column label="月日" width="110">
              <template #default="{ row }">
                <span>{{ row.data.month_day || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="动态内容" min-width="300">
              <template #default="{ row }">
                <el-tooltip placement="top" :show-after="400" popper-class="import-content-tooltip">
                  <template #content>
                    <div class="tooltip-content-text">{{ row.data.content }}</div>
                  </template>
                  <span class="import-content-cell" :class="{ 'split-highlight': row._split }">{{ row.data.content }}</span>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column label="附件(URL)" width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.data.files || '-' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="75" align="center">
              <template #default="{ row }">
                <el-tag v-if="row._valid" type="success" size="small">正常</el-tag>
                <el-tooltip v-else placement="top" :content="row.errors.join('\n')">
                  <el-tag type="danger" size="small">错误</el-tag>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="65" align="center">
              <template #default="{ row, $index }">
                <el-button size="small" link type="danger" @click="removeImportRow($index)">
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
import { ref, reactive, computed, nextTick, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Document, Plus, Delete, Download, UploadFilled, Upload, ArrowDown, InfoFilled, PriceTag, Close, Picture } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import ActivityDrawer from '@/components/investment/ActivityDrawer.vue'
import ProjectDrawer from '@/components/investment/ProjectDrawer.vue'
import { getPublicActivities, createActivity, updateActivity, getActivity, deleteActivity, batchDeleteActivities } from '@/api/activity'
import { getPublicProjects, getProject } from '@/api/investment'
import { downloadActivityExcel } from '@/api/activity_export'
import { downloadActivityImportTemplate, activityImportPreviewApi, activityImportExecute, getTemplateProjects } from '@/api/activity_import'
import { getDictItems } from '@/api/dict'
import { getDemands } from '@/api/demand'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import { maskName, maskContent } from '@/utils/mask'

const businessAuth = useBusinessAuthStore()

function dn(v) { return businessAuth.isVisitor ? maskName(v) : (v || '') }
function dc(v) { return businessAuth.isVisitor ? maskContent(v) : (v || '') }
const tableRef = ref(null)
const activities = ref([])
const loading = ref(false)
const searchText = ref('')
const filterProjectId = ref('')
const filterTags = ref([])
const filterDateRange = ref([])
const filterDateFrom = ref('')
const filterDateTo = ref('')
const selectedIds = ref([])
const projectList = ref([])

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 字典数据
const followStatusList = ref([])
const activityTagDicts = ref([])

let searchTimer = null

// 查看抽屉
const viewDrawerVisible = ref(false)
const viewActivity = ref(null)

// 项目详情抽屉
const projectDrawerVisible = ref(false)
const projectDrawerProject = ref(null)

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
const projectDemands = ref([])

// ---- 下载导入模板对话框 ----
const templateDialogVisible = ref(false)
const templateFollowStatus = ref('')
const templateProjects = ref([])
const templateTableRef = ref(null)
const templateSelectedProjects = ref([])
const templateSelectedCount = computed(() => templateSelectedProjects.value.length)

// ---- 导入对话框 ----
const importDialogVisible = ref(false)
const importStep = ref('select')
const importFileList = ref([])
const importUploadRef = ref(null)
const importHeaders = ref([])
const importRows = ref([])
const importing = ref(false)
const importValidCount = ref(0)
const importErrorCount = ref(0)
const importSplitInfo = ref('')
const importDefaultYear = ref(new Date().getFullYear())
const importHasSplit = computed(() => importRows.value.some(r => r._split))

const defaultForm = () => ({
  project_id: '',
  date: '',
  content: '',
  files: [],
  tags: [],
  demand_ids: []
})

const form = reactive(defaultForm())

const rules = {
  project_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
  content: [{ required: true, message: '请输入动态内容', trigger: 'blur' }]
}

onMounted(async () => {
  await Promise.all([loadProjects(), loadDicts()])
  fetchData()
})

watch(() => form.project_id, () => {
  if (editDrawerVisible.value) loadProjectDemands()
})

async function loadProjectDemands() {
  if (!form.project_id) { projectDemands.value = []; return }
  try {
    const res = await getDemands({ project_id: form.project_id, page_size: 999 })
    if (res.code === 0) projectDemands.value = res.data || []
  } catch { projectDemands.value = [] }
}

async function loadDicts() {
  try {
    const [res1, res2] = await Promise.all([
      getDictItems('follow_statuses'),
      getDictItems('activity_tags')
    ])
    if (res1.code === 0) followStatusList.value = res1.data || []
    if (res2.code === 0) activityTagDicts.value = res2.data || []
  } catch { /* ignore */ }
}

function getTagName(code) {
  return activityTagDicts.value.find(d => d.code === code)?.name || code
}

async function loadProjects() {
  try {
    const res = await getPublicProjects()
    if (res.code === 0) projectList.value = res.data || []
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const params = { page: currentPage.value, page_size: pageSize.value }
    if (searchText.value) params.search = searchText.value
    if (filterProjectId.value) params.project_id = filterProjectId.value
    if (filterDateFrom.value) params.date_from = filterDateFrom.value
    if (filterDateTo.value) params.date_to = filterDateTo.value
    if (filterTags.value.length > 0) params.tags = filterTags.value.join(',')
    const res = await getPublicActivities(params)
    activities.value = res.data || []
    total.value = res.total || 0
  } catch { activities.value = [] }
  finally { loading.value = false }
}

function handleSearch() { currentPage.value = 1; clearTimeout(searchTimer); searchTimer = setTimeout(fetchData, 300) }

function onDateRangeChange(vals) {
  if (vals && vals.length === 2) {
    filterDateFrom.value = vals[0]
    filterDateTo.value = vals[1]
  } else {
    filterDateFrom.value = ''
    filterDateTo.value = ''
  }
  currentPage.value = 1
  fetchData()
}

function handlePageChange(page) { currentPage.value = page; fetchData() }
function handlePageSizeChange(size) { pageSize.value = size; currentPage.value = 1; fetchData() }

function handleSelectionChange(selection) { selectedIds.value = selection.map(s => s.id) }

function truncate(text, max) { if (!text) return ''; return text.length > max ? text.slice(0, max) + '...' : text }

// ---- 查看 ----
function handleView(row) {
  if (row.tag_names) {
    row._tagNames = row.tag_names
  } else {
    const tagMap = {}
    activityTagDicts.value.forEach(t => { tagMap[t.code] = t.name })
    row._tagNames = (row.tags || []).map(tc => tagMap[tc] || tc)
  }
  viewActivity.value = row
  viewDrawerVisible.value = true
}

async function handleProjectClick(row) {
  try {
    const res = await getProject(row.project_id)
    if (res.code === 0) {
      projectDrawerProject.value = res.data
      projectDrawerVisible.value = true
    }
  } catch (err) {
    ElMessage.error('获取项目详情失败')
  }
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

// ---- 批量删除 ----
async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedIds.value.length} 条动态吗？此操作不可恢复。`,
      '批量删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    const res = await batchDeleteActivities(selectedIds.value)
    if (res.code === 0) {
      ElMessage.success(res.message)
      selectedIds.value = []
      fetchData()
    }
  } catch { /* cancelled */ }
}

// ---- 下载导入模板对话框 ----
function resetTemplateDialog() {
  templateFollowStatus.value = ''
  templateProjects.value = []
  templateSelectedProjects.value = []
}

async function loadTemplateProjects() {
  try {
    const res = await getTemplateProjects(templateFollowStatus.value)
    if (res.code === 0) {
      templateProjects.value = res.data || []
      // 默认全选
      templateSelectedProjects.value = [...templateProjects.value]
      nextTick(() => {
        templateTableRef.value?.toggleAllSelection()
      })
    }
  } catch {
    templateProjects.value = []
    templateSelectedProjects.value = []
  }
}

function handleTemplateSelectionChange(selection) {
  templateSelectedProjects.value = selection
}

function removeTemplateProject(idx) {
  const removed = templateProjects.value[idx]
  templateProjects.value.splice(idx, 1)
  if (removed) {
    templateSelectedProjects.value = templateSelectedProjects.value.filter(p => p.id !== removed.id)
  }
}

async function handleDownloadTemplate() {
  if (templateSelectedProjects.value.length === 0) {
    ElMessage.warning('请至少选择一个项目')
    return
  }
  try {
    const ids = templateSelectedProjects.value.map(p => p.id)
    await downloadActivityImportTemplate(ids)
    ElMessage.success('模板下载成功')
    templateDialogVisible.value = false
  } catch (err) {
    ElMessage.error(err.message)
  }
}

// ---- 导入 ----
function handleImportCmd(cmd) {
  if (cmd === 'download-template') {
    resetTemplateDialog()
    loadTemplateProjects()
    templateDialogVisible.value = true
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
  importSplitInfo.value = ''
  importDefaultYear.value = new Date().getFullYear()
}

async function handleImportFile(file) {
  importFileList.value = [file]
  try {
    const res = await activityImportPreviewApi(file.raw)
    importHeaders.value = res.data.headers
    importRows.value = res.data.rows
    importValidCount.value = res.data.valid_count
    importErrorCount.value = res.data.error_count
    importSplitInfo.value = res.data.split_info || ''
    importDefaultYear.value = res.data.default_year || new Date().getFullYear()
    importStep.value = 'preview'
  } catch (err) {
    ElMessage.error(err.message)
    importFileList.value = []
  }
}

function onDefaultYearChange(val) {
  importRows.value.forEach(r => {
    r.data.year = val
  })
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
      form.date = d.date ? d.date.substring(0, 10) : ''
      form.content = d.content || ''
      form.files = d.files || []
      form.tags = Array.isArray(d.tags) ? [...d.tags] : []
      form.demand_ids = d.linked_demands ? d.linked_demands.map(dm => dm.id) : []
      try {
        fileList.value = Array.isArray(d.files) ? d.files.map((url, i) => ({ name: url.split('/').pop() || `文件${i+1}`, url })) : []
      } catch { fileList.value = [] }
      if (form.project_id) await loadProjectDemands()
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

// ---- 剪贴板粘贴图片 ----
async function handleClipboardPaste(event) {
  const items = event.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const blob = item.getAsFile()
      if (!blob) continue
      const ext = item.type.split('/')[1] || 'png'
      const filename = `paste-${Date.now()}.${ext}`
      const file = new File([blob], filename, { type: item.type })
      const formData = new FormData()
      formData.append('file', file)
      try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData })
        const data = await res.json()
        if (data.code === 0) {
          fileList.value.push({
            name: filename,
            url: data.data.url,
            uid: Date.now() + Math.random()
          })
          ElMessage.success('图片已粘贴上传')
        } else {
          ElMessage.error(data.message || '图片上传失败')
        }
      } catch {
        ElMessage.error('图片上传失败')
      }
    }
  }
}

// ---- 文件缩略图辅助 ----
function getFileExtension(file) {
  const name = getFileName(file)
  return name.split('.').pop().toLowerCase()
}
function getFileName(file) {
  return file.name || (file.url ? file.url.split('/').pop() : '未知文件')
}
function isImageFile(file) {
  const ext = getFileExtension(file)
  const query = (file.url || '').split('?')[0]
  const urlExt = query.split('.').pop().toLowerCase()
  return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext) ||
         ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(urlExt)
}
function isPdfFile(file) {
  return getFileExtension(file) === 'pdf' || (file.url || '').toLowerCase().includes('.pdf')
}
function getFilePreviewUrl(file) {
  if (file.url) return file.url
  if (file.raw) return URL.createObjectURL(file.raw)
  return ''
}
function handleThumbRemove(idx) {
  const file = fileList.value[idx]
  if (file) {
    // 如果文件已有 URL (服务端已有)，仍需保留在数组中供后续删除标记
    // 这里直接从列表中移除
    if (file.previewUrl && file.raw) {
      URL.revokeObjectURL(file.previewUrl)
    }
  }
  fileList.value.splice(idx, 1)
}

// ---- 保存 ----
async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    ElMessage.warning('请填写必填字段（项目、动态内容不能为空）')
    return
  }

  saving.value = true
  try {
    const docUrls = fileList.value.filter(f => f.url).map(f => f.url)
    const data = {
      project_id: form.project_id,
      date: form.date,
      content: form.content,
      files: docUrls,
      tags: form.tags,
      demand_ids: form.demand_ids || []
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
.date-cell { color: #606266; font-size: 13px; white-space: nowrap; }
.project-name-tag {
  cursor: pointer;
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
}
.project-name-tag:hover { background: #d0e0f0; border-color: #90bcd8; }
.content-tooltip { max-width: 480px !important; white-space: pre-wrap !important; }
.no-data { color: #909399; }

/* ---- 编辑抽屉样式 ---- */
.drawer-title-bar {
  background: linear-gradient(135deg, #3a7abd 0%, #6ba3d6 100%);
  margin: 0 -20px 0 -20px;
  padding: 28px 20px 24px 40px;
}
.drawer-title {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 8px;
}
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

/* 粘贴图片专属区域 */
.paste-zone {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border: 1.5px dashed #c8d0db;
  border-radius: 8px;
  background: #f7f9fc;
  color: #8a95a5;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  outline: none;
}
.paste-zone:hover,
.paste-zone:focus {
  border-color: #409eff;
  background: #e8f3ff;
  color: #2c5fb8;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.12);
}
.paste-icon { display: flex; font-size: 22px; color: inherit; }
.paste-label { font-size: 14px; font-weight: 600; }
.paste-hint { font-size: 12px; margin-left: auto; color: inherit; opacity: 0.8; }
.paste-zone kbd {
  padding: 1px 5px;
  font-size: 11px;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  box-shadow: 0 1px 0 #cbd5e1;
}

/* 文件缩略图网格 */
.file-thumbnail-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}
.file-thumb-card {
  width: 120px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  transition: box-shadow 0.2s;
}
.file-thumb-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.thumb-preview {
  width: 100%;
  height: 90px;
  position: relative;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
}
.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-pdf {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: #e6a23c;
}
.thumb-pdf span {
  font-size: 11px;
  font-weight: 600;
  color: #e6a23c;
}
.thumb-generic {
  color: #909399;
}
.thumb-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0,0,0,0.5);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
}
.thumb-preview:hover .thumb-remove { opacity: 1; }
.thumb-name {
  padding: 4px 8px;
  font-size: 11px;
  color: #606266;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---- 导入对话框 ---- */
.import-summary { display: flex; gap: 24px; margin-bottom: 8px; font-size: 14px; flex-wrap: wrap; }
.import-summary strong { font-size: 18px; margin: 0 2px; }
.summary-valid { color: #67c23a; }
.summary-error { color: #f56c6c; }
.summary-split { color: #409eff; font-size: 12px; }

.import-year-bar {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 12px; padding: 8px 14px;
  background: #f0f7ff; border-radius: 6px; border: 1px solid #d6e8ff;
}
.year-label { font-size: 13px; color: #1a3a5c; font-weight: 600; }
.year-hint { font-size: 12px; color: #909399; }

.import-table-wrap { border: 1px solid #ebeef5; border-radius: 6px; overflow: hidden; }
:deep(.import-error-row) { background-color: #fef0f0 !important; }
:deep(.import-error-row:hover > td) { background-color: #fde2e2 !important; }

.import-content-cell {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.5;
  max-height: 4.5em;
  cursor: pointer;
}
.split-highlight { background: #ecf5ff; padding: 1px 4px; border-radius: 3px; font-weight: 500; }
.project-id-tag {
  font-family: 'Consolas', 'Menlo', monospace;
  font-size: 12px;
  color: #1a3a5c;
  background: #f0f5ff;
  padding: 2px 6px;
  border-radius: 3px;
}

/* ---- 模板下载对话框 ---- */
.template-filter {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
}
.filter-label { font-size: 14px; color: #606266; font-weight: 500; white-space: nowrap; }
.template-count { font-size: 13px; color: #909399; margin-left: auto; }
.template-table { margin-bottom: 4px; }
</style>

<!-- 非 scoped 样式：用于 Element Plus teleported popper + drawer header -->
<style>
.import-content-tooltip {
  max-width: 600px !important;
}
.import-content-tooltip .tooltip-content-text {
  white-space: pre-wrap;
  line-height: 1.7;
  font-size: 13px;
}
.el-drawer__header {
  margin-bottom: 0 !important;
  padding: 0 !important;
}
.el-drawer__body {
  padding: 12px 20px 20px !important;
}
</style>
