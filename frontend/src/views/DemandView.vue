<template>
  <div class="demand-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 工具栏 -->
        <div class="toolbar">
          <el-input v-model="searchText" placeholder="搜索项目名称、诉求内容..." :prefix-icon="Search" clearable class="search-input" @input="handleSearch" />
          <el-select v-model="filterProjectId" placeholder="项目" clearable @change="currentPage = 1; fetchData()" style="width: 180px;">
            <el-option v-for="p in projectList" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
          <el-select v-model="filterProjectType" placeholder="项目类型" clearable @change="currentPage = 1; fetchData()" style="width: 140px;">
            <el-option v-for="t in projectTypes" :key="t.code" :label="t.name" :value="t.code" />
          </el-select>
          <el-cascader
            v-model="filterDemandTypeCascader"
            :options="demandTypeTree"
            :props="{ expandTrigger: 'click', checkStrictly: true }"
            placeholder="诉求类型"
            clearable
            style="width: 200px;"
            @change="onFilterDemandTypeChange"
          />
          <el-select v-model="filterStatus" placeholder="状态" clearable @change="currentPage = 1; fetchData()" style="width: 120px;">
            <el-option label="待回应" value="pending" />
            <el-option label="协调中" value="processing" />
            <el-option label="已回应" value="resolved" />
          </el-select>
          <el-button v-if="selectedIds.length > 0 && businessAuth.hasPermission('demand', 'batch_delete')" type="danger" @click="handleBatchDelete">
            <el-icon><Delete /></el-icon> 批量删除 ({{ selectedIds.length }})
          </el-button>
          <el-dropdown v-if="businessAuth.hasPermission('demand', 'import')" trigger="click" @command="handleImportCmd">
            <el-button type="default">
              <el-icon><Upload /></el-icon> 诉求导入 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="download-template">
                  <el-icon><Download /></el-icon> 下载导入模板
                </el-dropdown-item>
                <el-dropdown-item command="import-data">
                  <el-icon><Upload /></el-icon> 导入诉求
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <div class="toolbar-spacer" />
          <el-button v-if="businessAuth.hasPermission('demand', 'add')" type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 添加诉求
          </el-button>
        </div>

        <!-- ========== 下载导入模板对话框 ========== -->
        <el-dialog
          v-model="templateDialogVisible"
          title="下载导入模板"
          width="780px"
          :close-on-click-modal="false"
          @closed="resetTemplateDialog"
        >
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

        <!-- 表格 -->
        <el-table
          ref="tableRef"
          :data="demands"
          stripe
          row-key="id"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          empty-text="暂无企业诉求数据"
          style="width: 100%"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column label="项目" width="200">
            <template #default="{ row }">
              <el-tag class="project-name-tag" @click="handleProjectClick(row)">
                {{ dn(row.project_name) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="诉求类型" width="240">
            <template #default="{ row }">
              <span class="demand-type-tag">{{ row.demand_type_name || row.demand_type_code || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="诉求内容" min-width="260">
            <template #default="{ row }">
              <el-tooltip :content="businessAuth.isVisitor ? '' : row.demand_content" placement="top" :show-after="300" popper-class="content-tooltip">
                <span class="content-preview">{{ dc(truncate(row.demand_content, 50)) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="对接单位" width="140">
            <template #default="{ row }">{{ row.unit_name || row.unit_code || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :color="statusColor(row.status)" effect="dark" size="small">{{ statusName(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="handleView(row)">查看</el-button>
              <el-button v-if="businessAuth.hasPermission('demand', 'edit')" size="small" link type="success" @click="openEdit(row)">编辑</el-button>
              <el-button v-if="businessAuth.hasPermission('demand', 'delete')" size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
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
    <el-drawer v-model="viewDrawerVisible" direction="rtl" size="560px">
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">
            <el-icon><View /></el-icon>
            诉求详情
          </span>
        </div>
      </template>
      <template v-if="viewDemand">
        <el-descriptions :column="2" border size="small" class="detail-desc">
          <el-descriptions-item label="项目" :span="2">
            <strong>{{ dn(viewDemand.project_name) }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="诉求类型">
            {{ viewDemand.demand_type_name || viewDemand.demand_type_code || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="对接单位">
            {{ viewDemand.unit_name || viewDemand.unit_code || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态" :span="2">
            <el-tag :color="statusColor(viewDemand.status)" effect="dark" size="small">{{ statusName(viewDemand.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="诉求内容" :span="2">
            <div class="text-block">{{ dc(viewDemand.demand_content) || '-' }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="解决措施" :span="2">
            <div class="text-block">{{ dc(viewDemand.resolution) || '暂无' }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="写入时间">{{ fmtDt(viewDemand.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="最后更新">{{ fmtDt(viewDemand.updated_at) }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>

    <!-- 编辑抽屉（新建/编辑共用） -->
    <el-drawer v-model="editDrawerVisible" direction="rtl" size="680px" @closed="resetForm">
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">
            <el-icon><Edit /></el-icon>
            {{ editMode === 'create' ? '新建诉求' : '编辑诉求' }}
          </span>
        </div>
      </template>
      <div class="drawer-form">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" label-position="right">
          <div class="section-header">
            <span class="section-icon"><el-icon><InfoFilled /></el-icon></span>
            <span class="section-title">基础信息</span>
          </div>
          <el-form-item label="项目" prop="project_id">
            <el-select v-model="form.project_id" placeholder="请选择项目" filterable style="width: 100%;">
              <el-option v-for="p in projectList" :key="p.id" :label="p.project_name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-row :gutter="16">
            <el-col :span="16">
              <el-form-item label="诉求类型">
                <el-cascader
                  v-model="demandTypeCascaderValue"
                  :options="demandTypeTree"
                  :props="{ expandTrigger: 'click', checkStrictly: true, multiple: true }"
                  placeholder="请选择诉求类型（可多选）"
                  clearable
                  collapse-tags
                  collapse-tags-tooltip
                  style="width: 100%;"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="对接单位">
                <el-select v-model="form.unit_code" placeholder="请选择" clearable style="width: 100%;">
                  <el-option v-for="org in organizations" :key="org.code" :label="org.name" :value="org.code" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width: 200px;">
              <el-option label="待回应" value="pending" />
              <el-option label="协调中" value="processing" />
              <el-option label="已回应" value="resolved" />
            </el-select>
          </el-form-item>

          <div class="section-header">
            <span class="section-icon"><el-icon><Document /></el-icon></span>
            <span class="section-title">诉求详情</span>
          </div>
          <el-form-item label="诉求内容" prop="demand_content">
            <el-input v-model="form.demand_content" type="textarea" :rows="4" placeholder="请输入诉求内容..." maxlength="5000" show-word-limit />
          </el-form-item>
          <el-form-item label="解决措施">
            <el-input v-model="form.resolution" type="textarea" :rows="3" placeholder="请输入解决措施（可选）..." maxlength="5000" show-word-limit />
          </el-form-item>

          <div class="drawer-footer">
            <el-button @click="editDrawerVisible = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">{{ editMode === 'create' ? '创建' : '保存' }}</el-button>
          </div>
        </el-form>
      </div>
    </el-drawer>

    <!-- 项目详情抽屉 -->
    <ProjectDrawer v-model="projectDrawerVisible" :project="projectDrawerProject" />

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入诉求" width="900px" :close-on-click-modal="false" @closed="resetImport">
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
import { ref, reactive, computed, nextTick, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Document, Plus, Delete, Download, UploadFilled, Upload, ArrowDown, InfoFilled, Edit, View } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import ProjectDrawer from '@/components/investment/ProjectDrawer.vue'
import { getPublicDemands, getDemandDicts, createDemand, updateDemand, getDemand, deleteDemand, batchDeleteDemands } from '@/api/demand'
import { getTemplateProjects, downloadDemandImportTemplate, demandImportPreview, demandImportExecute } from '@/api/demand'
import { getPublicProjects, getProject } from '@/api/investment'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import { maskName, maskContent } from '@/utils/mask'

const businessAuth = useBusinessAuthStore()

function dn(v) { return businessAuth.isVisitor ? maskName(v) : (v || '') }
function dc(v) { return businessAuth.isVisitor ? maskContent(v) : (v || '') }
const tableRef = ref(null)
const demands = ref([])
const loading = ref(false)
const searchText = ref('')
const filterProjectId = ref('')
const filterDemandType = ref('')
const filterDemandTypeCascader = ref([])

function onFilterDemandTypeChange(val) {
  currentPage.value = 1
  if (!val || val.length === 0) {
    filterDemandType.value = ''
  } else if (val.length === 1) {
    // 选中一级：收集该父级及所有子级 code
    const parent = val[0]
    const children = (demandTypes.value || []).filter(t => t.parent_code === parent).map(t => t.code)
    filterDemandType.value = [parent, ...children].join(',')
  } else {
    // 选中二级：仅该子级 code
    filterDemandType.value = val[val.length - 1]
  }
  fetchData()
}
const filterStatus = ref('')
const filterProjectType = ref('')
const selectedIds = ref([])
const projectList = ref([])
const demandTypes = ref([])
const demandTypeTree = computed(() => {
  const types = demandTypes.value || []
  const parents = types.filter(t => !t.parent_code)
  return parents.map(p => {
    const children = types.filter(t => t.parent_code === p.code)
    return {
      value: p.code,
      label: p.name,
      children: children.length > 0 ? children.map(c => ({ value: c.code, label: c.name })) : undefined
    }
  })
})
const demandTypeCascaderValue = ref([])
const organizations = ref([])
const projectTypes = ref([])

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

let searchTimer = null

// 查看抽屉
const viewDrawerVisible = ref(false)
const viewDemand = ref(null)

// 项目详情抽屉
const projectDrawerVisible = ref(false)
const projectDrawerProject = ref(null)

// 编辑抽屉
const editDrawerVisible = ref(false)
const editMode = ref('create')
const editingId = ref(null)
const formRef = ref(null)
const saving = ref(false)

const defaultForm = () => ({
  project_id: '',
  demand_type_code: '',
  demand_content: '',
  resolution: '',
  unit_code: '',
  status: 'pending'
})

const form = reactive(defaultForm())

const rules = {
  project_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
  demand_content: [{ required: true, message: '请输入诉求内容', trigger: 'blur' }]
}

// 下载导入模板对话框
const templateDialogVisible = ref(false)
const templateFollowStatus = ref('')
const templateProjects = ref([])
const templateTableRef = ref(null)
const templateSelectedProjects = ref([])
const templateSelectedCount = computed(() => templateSelectedProjects.value.length)
const followStatusList = ref([])

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

const route = useRoute()

onMounted(async () => {
  await loadDicts()
  await loadProjects()
  fetchData()
})

// 从 query 参数自动打开诉求查看抽屉（供其他页面跳转使用，如动态关联诉求卡片）
watch(() => route.query.view, async (demandId) => {
  if (demandId) {
    try {
      const res = await getDemand(Number(demandId))
      if (res.code === 0) {
        viewDemand.value = res.data
        viewDrawerVisible.value = true
      }
    } catch { /* ignore */ }
  }
}, { immediate: true })

async function loadDicts() {
  try {
    const res = await getDemandDicts()
    if (res.code === 0) {
      demandTypes.value = res.data.demand_types || []
      organizations.value = res.data.organizations || []
      projectTypes.value = res.data.project_types || []
      followStatusList.value = res.data.follow_statuses || []
    }
  } catch { /* ignore */ }
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
    if (filterDemandType.value) params.demand_type = filterDemandType.value
    if (filterProjectType.value) params.project_type = filterProjectType.value
    if (filterStatus.value) params.status = filterStatus.value
    const res = await getPublicDemands(params)
    demands.value = res.data || []
    total.value = res.total || 0
  } catch { demands.value = [] }
  finally { loading.value = false }
}

function handleSearch() { currentPage.value = 1; clearTimeout(searchTimer); searchTimer = setTimeout(fetchData, 300) }

function handlePageChange(page) { currentPage.value = page; fetchData() }
function handlePageSizeChange(size) { pageSize.value = size; currentPage.value = 1; fetchData() }

function handleSelectionChange(selection) { selectedIds.value = selection.map(s => s.id) }

function truncate(text, max) { if (!text) return ''; return text.length > max ? text.slice(0, max) + '...' : text }

function statusColor(s) {
  return { pending: '#e6a23c', processing: '#409eff', resolved: '#67c23a' }[s] || '#909399'
}
function statusName(s) {
  return { pending: '待回应', processing: '协调中', resolved: '已回应' }[s] || s
}

function fmtDt(d) {
  if (!d) return '-'
  return new Date(d + 'Z').toLocaleString('zh-CN', { hour12: false })
}

function resolveDemandTypePath(code) {
  if (!code) return []
  const types = demandTypes.value || []
  // 支持逗号分隔的多值编码
  const codes = code.split(',').map(c => c.trim()).filter(Boolean)
  return codes.map(c => {
    const type = types.find(t => t.code === c)
    if (!type) return null
    if (type.parent_code) return [type.parent_code, c]
    return [c]
  }).filter(Boolean)
}

// ---- 查看 ----
function handleView(row) {
  viewDemand.value = row
  viewDrawerVisible.value = true
}

// ---- 点击项目名称 ----
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

// ---- 新建 ----
function openCreate() {
  editMode.value = 'create'
  editingId.value = null
  demandTypeCascaderValue.value = []
  resetForm()
  editDrawerVisible.value = true
}

// ---- 编辑 ----
async function openEdit(row) {
  editMode.value = 'edit'
  editingId.value = row.id
  try {
    const res = await getDemand(row.id)
    if (res.code === 0) {
      const d = res.data
      form.project_id = d.project_id || ''
      form.demand_type_code = d.demand_type_code || ''
      form.demand_content = d.demand_content || ''
      form.resolution = d.resolution || ''
      form.unit_code = d.unit_code || ''
      form.status = d.status || 'pending'
      demandTypeCascaderValue.value = resolveDemandTypePath(d.demand_type_code)
    }
    editDrawerVisible.value = true
  } catch (err) { ElMessage.error(err.message) }
}

function resetForm() {
  Object.assign(form, defaultForm())
  demandTypeCascaderValue.value = []
  formRef.value?.clearValidate()
}

// ---- 保存 ----
async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const cv = demandTypeCascaderValue.value
    if (Array.isArray(cv) && cv.length > 0) {
      // multiple:true 时 cv 是路径数组的数组 [[parent, child], [parent], ...]
      const codes = cv.map(path => Array.isArray(path) ? path[path.length - 1] : path)
      form.demand_type_code = codes.join(',')
    } else {
      form.demand_type_code = ''
    }
    const data = { ...form }
    if (editMode.value === 'create') {
      await createDemand(data)
      ElMessage.success('诉求创建成功')
    } else {
      await updateDemand(editingId.value, data)
      ElMessage.success('诉求更新成功')
    }
    editDrawerVisible.value = false
    fetchData()
  } catch (err) { ElMessage.error(err.message) }
  finally { saving.value = false }
}

// ---- 删除 ----
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该诉求吗？', '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    await deleteDemand(row.id)
    ElMessage.success('诉求已删除')
    fetchData()
  } catch { /* cancelled */ }
}

// ---- 批量删除 ----
async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedIds.value.length} 条诉求吗？此操作不可恢复。`,
      '批量删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    const res = await batchDeleteDemands(selectedIds.value)
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
  // 先获取被删项目的引用，从选中列表中移除
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
    await downloadDemandImportTemplate(ids)
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
}

async function handleImportFile(file) {
  importFileList.value = [file]
  try {
    const res = await demandImportPreview(file.raw)
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

function importRowClass({ row }) {
  return !row._valid ? 'import-error-row' : ''
}

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
    const res = await demandImportExecute(validRows)
    if (res.code === 0) {
      ElMessage.success(`成功导入 ${res.data?.count || validRows.length} 条诉求`)
      importDialogVisible.value = false
      fetchData()
    }
  } catch (err) { ElMessage.error(err.message) }
  finally { importing.value = false }
}
</script>

<style scoped>
.demand-page { min-height: 100vh; background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%); }
.page-body { max-width: 1600px; margin: 0 auto; padding: 28px 32px 60px; }
.content-card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 20px rgba(0,0,0,0.06); }
.toolbar { display: flex; gap: 16px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
.toolbar-spacer { flex: 1; }
.search-input { width: 320px; }

.content-preview { cursor: default; color: #606266; }
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

.demand-type-tag {
  display: inline-block;
  padding: 0 8px;
  font-size: 11px;
  line-height: 20px;
  color: #607080;
  background: #f0f2f5;
  border: 1px solid #dde0e4;
  border-radius: 3px;
}

/* ---- 编辑/查看抽屉样式 ---- */
.drawer-title-bar {
  background: linear-gradient(135deg, #5b9bd5 0%, #8ab8e8 100%);
  margin: 0 -20px 0 -20px;
  padding: 20px 20px 20px 40px;
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

.section-header {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; margin: 20px 0 14px;
  background: #f5f7fa; border-radius: 6px;
  border-left: 3px solid #1a3a5c;
}
.section-icon { color: #1a3a5c; font-size: 16px; display: flex; align-items: center; }
.section-title { font-size: 14px; font-weight: 600; color: #303133; }

.drawer-footer { display: flex; justify-content: center; gap: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #ebeef5; }

/* 查看详情 */
.detail-desc :deep(.el-descriptions__label) { width: 100px; font-weight: 500; color: #606266; }
.text-block { white-space: pre-wrap; line-height: 1.7; font-size: 13px; color: #303133; max-height: 300px; overflow-y: auto; }

/* 导入对话框 */
.import-summary { display: flex; gap: 24px; margin-bottom: 16px; font-size: 14px; }
.import-summary strong { font-size: 18px; margin: 0 2px; }
.summary-valid { color: #67c23a; }
.summary-error { color: #f56c6c; }
.import-table-wrap { border: 1px solid #ebeef5; border-radius: 6px; overflow: hidden; }
:deep(.import-error-row) { background-color: #fef0f0 !important; }
:deep(.import-error-row:hover > td) { background-color: #fde2e2 !important; }

/* 下载导入模板对话框 */
.template-filter { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.filter-label { font-size: 13px; color: #606266; }
.template-count { font-size: 13px; color: #909399; margin-left: auto; }
.template-table { border: 1px solid #ebeef5; border-radius: 6px; }
</style>

<style>
.content-tooltip { max-width: 480px !important; white-space: pre-wrap !important; }

.el-drawer__header {
  margin-bottom: 0 !important;
  padding: 0 !important;
}
.el-drawer__body {
  padding: 12px 20px 20px !important;
}
</style>
