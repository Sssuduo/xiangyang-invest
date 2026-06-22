<template>
  <div class="investment-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <div class="toolbar">
          <el-input v-model="searchText" placeholder="搜索项目名称、企业、内容..." :prefix-icon="Search" clearable class="search-input" @input="handleSearch" />
          <el-select v-model="filterFollowStatus" placeholder="跟进状态" clearable @change="fetchData" style="width: 140px;">
            <el-option v-for="d in dicts.follow_statuses" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
          <el-select v-model="filterMeetingStatus" placeholder="上会状态" clearable @change="fetchData" style="width: 140px;">
            <el-option v-for="d in dicts.meeting_statuses" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
          <el-select v-model="filterProjectType" placeholder="项目类型" clearable @change="fetchData" style="width: 140px;">
            <el-option v-for="d in dicts.project_types" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
          <el-button v-if="selectedIds.length > 0" type="success" @click="handleExport">
            <el-icon><Download /></el-icon> 导出Excel ({{ selectedIds.length }})
          </el-button>
          <el-dropdown trigger="click" @command="handleImportCmd">
            <el-button type="default">
              <el-icon><Upload /></el-icon> 项目导入 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="download-template">
                  <el-icon><Download /></el-icon> 下载导入模板
                </el-dropdown-item>
                <el-dropdown-item command="import-data">
                  <el-icon><Upload /></el-icon> 导入项目
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <div class="toolbar-spacer" />
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 添加项目
          </el-button>
        </div>

        <el-table
          ref="tableRef"
          :data="pagedProjects"
          stripe
          row-key="id"
          :row-class-name="tableRowClassName"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          @expand-change="nextTick(updateExpandWidth)"
          empty-text="暂无招商项目数据"
          style="width: 100%"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column type="expand" width="42">
            <template #default="{ row }">
              <div class="expand-content" :style="{ width: expandWidth + 'px', maxWidth: expandWidth + 'px' }">
                <div class="expand-block">
                  <div class="expand-block-title">基础信息</div>
                  <div class="expand-grid">
                    <div class="expand-item"><label>项目名称</label><span>{{ row.project_name }}</span></div>
                    <div class="expand-item"><label>投资商名称</label><span>{{ row.invest_enterprise }}</span></div>
                    <div class="expand-item"><label>推介单位</label><span>{{ row.recommend_unit_name || '-' }}</span></div>
                    <div class="expand-item"><label>首次对接</label><span>{{ row.first_contact_date || '-' }}</span></div>
                  </div>
                </div>
                <div class="expand-block">
                  <div class="expand-block-title">企业简介</div>
                  <p class="expand-text-block">{{ row.enterprise_info }}</p>
                </div>
                <div class="expand-block">
                  <div class="expand-block-title">项目内容</div>
                  <p class="expand-text-block">{{ row.project_content }}</p>
                </div>
                <div class="expand-block" v-if="row.project_doc">
                  <div class="expand-block-title">项目文档</div>
                  <a :href="row.project_doc" target="_blank" class="doc-link"><el-icon><Document /></el-icon> 查看</a>
                </div>
                <div class="expand-block" v-if="row.demands && row.demands.length > 0">
                  <div class="expand-block-title">企业诉求</div>
                  <div class="demand-list">
                    <div v-for="(d, i) in row.demands" :key="d.id" class="demand-row-card">
                      <div class="demand-row-top">
                        <span class="demand-idx">{{ i + 1 }}.</span>
                        <span v-if="d.demand_type_name || d.demand_type_code" class="demand-type-badge">{{ d.demand_type_name || d.demand_type_code }}</span>
                        <span v-if="d.unit_name || d.unit_code" class="demand-unit-tag"><el-icon><OfficeBuilding /></el-icon> {{ d.unit_name || d.unit_code }}</span>
                        <div class="demand-top-spacer"></div>
                        <el-tag :color="demandStatusColor(d.status)" effect="dark" size="small">{{ demandStatusName(d.status) }}</el-tag>
                      </div>
                      <div class="demand-row-body">{{ d.demand_content }}</div>
                      <div v-if="d.resolution" class="demand-row-res">
                        <span class="res-divider"><el-icon><ArrowRight /></el-icon> 解决措施</span>
                        <span class="res-text">{{ d.resolution }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="order_no" label="序号" width="65" align="left" class-name="col-order-no" />
          <el-table-column prop="project_name" label="项目名称" min-width="160" show-overflow-tooltip />
          <el-table-column label="项目类型" width="150">
            <template #default="{ row }">
              <span class="project-type-tag">{{ row.project_type_name || row.project_type_code }}</span>
            </template>
          </el-table-column>
          <el-table-column label="投资商名称" width="160">
            <template #default="{ row }">
              <el-tooltip :content="row.enterprise_info" placement="top" :show-after="300" popper-class="enterprise-tooltip">
                <span class="enterprise-name">{{ row.invest_enterprise }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="项目内容" min-width="200">
            <template #default="{ row }">
              <el-tooltip :content="row.project_content" placement="top" :show-after="300" popper-class="content-tooltip">
                <span class="content-preview">{{ truncate(row.project_content, 40) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="投资金额" width="130" align="right">
            <template #default="{ row }">
              <span>{{ formatAmount(row.invest_amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="跟进状态" width="110" align="center">
            <template #default="{ row }">
              <el-tag :color="row.follow_status_color" effect="dark" size="small">{{ row.follow_status_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="上会状态" width="110" align="center">
            <template #default="{ row }">
              <el-tag :color="row.meeting_status_color" effect="dark" size="small">{{ row.meeting_status_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="责任单位" width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.responsible_unit_name || row.responsible_unit_code }}</template>
          </el-table-column>
          <el-table-column prop="person_in_charge" label="责任人" width="90" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <div class="action-cell">
                <el-button size="small" link type="success" @click="openEdit(row)">编辑</el-button>
                <el-button size="small" link type="warning" @click="handleAddActivity(row)">动态</el-button>
                <el-button size="small" link type="primary" @click="handleAI(row)">AI助手</el-button>
                <el-dropdown trigger="click" @command="(cmd) => handleRowCmd(cmd, row)">
                  <el-button size="small" link class="action-more">
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="view">
                        <el-icon><View /></el-icon> 项目详情
                      </el-dropdown-item>
                      <el-dropdown-item command="delete" divided>
                        <el-icon><Delete /></el-icon> 删除
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[5, 10, 20, 50]"
            :total="projects.length"
            layout="total, sizes, prev, pager, next"
            background
            small
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
          <el-checkbox v-model="showAll" class="show-all-check" @change="handleShowAllChange">展示全部</el-checkbox>
        </div>
      </div>
    </div>

    <!-- 查看抽屉 -->
    <ProjectDrawer v-model="viewDrawerVisible" :project="viewProject" />

    <!-- 编辑抽屉（新建/编辑共用） -->
    <el-drawer v-model="editDrawerVisible" direction="rtl" size="680px" @closed="resetForm">
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">{{ editMode === 'create' ? '新建项目' : '编辑项目' }}</span>
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
              <el-form-item label="顺序号" prop="order_no">
                <el-input-number v-model="form.order_no" :min="0" :max="9999" controls-position="right" style="width: 100%;" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="项目类型" prop="project_type_code">
                <el-select v-model="form.project_type_code" placeholder="请选择" style="width: 100%;">
                  <el-option v-for="d in dicts.project_types" :key="d.code" :label="d.name" :value="d.code" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="项目名称" prop="project_name">
            <el-input v-model="form.project_name" placeholder="请输入项目名称" maxlength="255" />
          </el-form-item>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="投资金额" prop="invest_amount">
                <el-input-number v-model="form.invest_amount" :min="0" :precision="2" :step="100" controls-position="right" style="width: 100%;" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="首次对接时间">
                <el-date-picker v-model="form.first_contact_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%;" />
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 企业信息 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><OfficeBuilding /></el-icon></span>
            <span class="section-title">企业信息</span>
          </div>
          <el-form-item label="投资商名称" prop="invest_enterprise">
            <el-input v-model="form.invest_enterprise" placeholder="请输入投资商名称" maxlength="255" />
          </el-form-item>
          <el-form-item label="企业简介" prop="enterprise_info">
            <el-input v-model="form.enterprise_info" type="textarea" :rows="3" placeholder="企业简介..." maxlength="2000" show-word-limit />
          </el-form-item>

          <!-- 项目详情 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><Document /></el-icon></span>
            <span class="section-title">项目详情</span>
          </div>
          <el-form-item label="项目内容" prop="project_content">
            <el-input v-model="form.project_content" type="textarea" :rows="6" placeholder="项目详细内容..." maxlength="5000" show-word-limit />
          </el-form-item>
          <el-form-item label="项目文档">
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

          <!-- 对接信息 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><Connection /></el-icon></span>
            <span class="section-title">对接信息</span>
          </div>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="跟进状态" prop="follow_status_code">
                <el-select v-model="form.follow_status_code" style="width: 100%;">
                  <el-option v-for="d in dicts.follow_statuses" :key="d.code" :label="d.name" :value="d.code" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="上会状态" prop="meeting_status_code">
                <el-select v-model="form.meeting_status_code" style="width: 100%;">
                  <el-option v-for="d in dicts.meeting_statuses" :key="d.code" :label="d.name" :value="d.code" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="推介单位">
                <el-select v-model="form.recommend_unit_code" placeholder="请选择" clearable style="width: 100%;">
                  <el-option v-for="d in dicts.organizations" :key="d.code" :label="d.name" :value="d.code" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="责任单位" prop="responsible_unit_code">
                <el-select v-model="form.responsible_unit_code" style="width: 100%;">
                  <el-option v-for="d in dicts.organizations" :key="d.code" :label="d.name" :value="d.code" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="责任人">
            <el-input v-model="form.person_in_charge" placeholder="责任人姓名" maxlength="64" style="width: 48%;" />
          </el-form-item>

          <!-- 企业诉求 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><ChatLineSquare /></el-icon></span>
            <span class="section-title">企业诉求</span>
          </div>
          <div class="demands-section">
            <div v-for="(d, i) in form.demands" :key="i" class="demand-card">
              <div class="demand-card-header">
                <span class="demand-card-title">诉求 {{ i + 1 }}</span>
                <el-button size="small" type="danger" link @click="removeDemand(i)"><el-icon><Delete /></el-icon></el-button>
              </div>
              <el-row :gutter="12" style="margin-bottom: 8px;">
                <el-col :span="12">
                  <el-select v-model="d.demand_type_code" placeholder="诉求类型" size="small" style="width: 100%;">
                    <el-option v-for="dt in dicts.demand_types" :key="dt.code" :label="dt.name" :value="dt.code" />
                  </el-select>
                </el-col>
                <el-col :span="12">
                  <el-select v-model="d.unit_code" placeholder="对接单位" size="small" style="width: 100%;">
                    <el-option v-for="org in dicts.organizations" :key="org.code" :label="org.name" :value="org.code" />
                  </el-select>
                </el-col>
              </el-row>
              <el-input v-model="d.demand_content" type="textarea" :rows="2" placeholder="诉求内容" style="margin-bottom: 8px;" />
              <el-input v-model="d.resolution" type="textarea" :rows="2" placeholder="解决措施（可选）" style="margin-bottom: 8px;" />
              <el-select v-model="d.status" size="small" style="width: 120px;">
                <el-option label="待处理" value="pending" />
                <el-option label="处理中" value="processing" />
                <el-option label="已解决" value="resolved" />
              </el-select>
            </div>
            <el-button size="small" @click="addDemand">
              <el-icon><Plus /></el-icon> 添加诉求
            </el-button>
          </div>

          <div class="drawer-footer">
            <el-button @click="editDrawerVisible = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">{{ editMode === 'create' ? '创建' : '保存' }}</el-button>
          </div>
        </el-form>
      </div>
    </el-drawer>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入项目" width="900px" :close-on-click-modal="false" @closed="resetImport">
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
import { ref, reactive, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
import { Search, Document, Plus, Delete, Download, UploadFilled, Upload, ArrowDown, MoreFilled, View, OfficeBuilding, ArrowRight } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import ProjectDrawer from '@/components/investment/ProjectDrawer.vue'
import { getPublicProjects } from '@/api/investment'
import { getDicts, createProject, updateProject, getProject, deleteProject, getMaxOrderNo } from '@/api/investment'
import { downloadExcel } from '@/api/export'
import { downloadImportTemplate, importPreviewApi, importExecute } from '@/api/import_api'

const tableRef = ref(null)
const projects = ref([])
const loading = ref(false)
const searchText = ref('')
const filterFollowStatus = ref('')
const filterMeetingStatus = ref('')
const filterProjectType = ref('')
const selectedIds = ref([])
const dicts = reactive({ follow_statuses: [], meeting_statuses: [], organizations: [], project_types: [], demand_types: [] })

// 分页
const currentPage = ref(1)
const pageSize = ref(5)
const showAll = ref(false)

const pagedProjects = computed(() => {
  if (showAll.value) return projects.value
  const start = (currentPage.value - 1) * pageSize.value
  return projects.value.slice(start, start + pageSize.value)
})

function handlePageChange() { /* currentPage 已双向绑定 */ }
function handleSizeChange() {
  currentPage.value = 1
}
function handleShowAllChange(val) {
  currentPage.value = 1
}

// 展开卡片固定宽度 & 冻结效果
const expandWidth = ref(1488)
let tableScrollWrapper = null

function updateExpandWidth() {
  const el = tableRef.value?.$el
  if (el) {
    expandWidth.value = el.clientWidth || 1488
  }
}

function onTableScroll(e) {
  const sl = e.target.scrollLeft
  const cells = tableRef.value?.$el?.querySelectorAll('.el-table__expanded-cell')
  cells?.forEach(c => {
    c.style.transform = `translateX(${sl}px)`
  })
}

onMounted(() => {
  nextTick(() => {
    updateExpandWidth()
    tableScrollWrapper = tableRef.value?.$el?.querySelector('.el-table__body-wrapper')
    if (tableScrollWrapper) {
      tableScrollWrapper.addEventListener('scroll', onTableScroll)
    }
    window.addEventListener('resize', updateExpandWidth)
  })
})

onBeforeUnmount(() => {
  if (tableScrollWrapper) {
    tableScrollWrapper.removeEventListener('scroll', onTableScroll)
  }
  window.removeEventListener('resize', updateExpandWidth)
})

let searchTimer = null

// 查看抽屉
const viewDrawerVisible = ref(false)
const viewProject = ref(null)

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
const importStep = ref('select')  // 'select' | 'preview'
const importFileList = ref([])
const importUploadRef = ref(null)
const importHeaders = ref([])
const importRows = ref([])
const importing = ref(false)

const importValidCount = ref(0)
const importErrorCount = ref(0)

const defaultForm = () => ({
  order_no: 0,
  project_name: '',
  project_type_code: '',
  invest_amount: 0,
  invest_enterprise: '',
  enterprise_info: '',
  project_content: '',
  project_doc: '',
  follow_status_code: '',
  meeting_status_code: 'not_meeting',
  recommend_unit_code: '',
  responsible_unit_code: '',
  person_in_charge: '',
  first_contact_date: '',
  demands: []
})

const form = reactive(defaultForm())

const rules = {
  project_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  project_type_code: [{ required: true, message: '请选择项目类型', trigger: 'change' }],
  invest_amount: [{ required: true, message: '请输入投资金额', trigger: 'blur' }],
  invest_enterprise: [{ required: true, message: '请输入投资商名称', trigger: 'blur' }],
  enterprise_info: [{ required: true, message: '请输入企业简介', trigger: 'blur' }],
  project_content: [{ required: true, message: '请输入项目内容', trigger: 'blur' }],
  follow_status_code: [{ required: true, message: '请选择跟进状态', trigger: 'change' }],
  responsible_unit_code: [{ required: true, message: '请选择责任单位', trigger: 'change' }]
}

onMounted(async () => { await loadDicts(); fetchData() })

async function loadDicts() {
  try { const res = await getDicts(); if (res.code === 0) Object.assign(dicts, res.data) } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (searchText.value) params.search = searchText.value
    if (filterFollowStatus.value) params.follow_status = filterFollowStatus.value
    if (filterMeetingStatus.value) params.meeting_status = filterMeetingStatus.value
    if (filterProjectType.value) params.project_type = filterProjectType.value
    const res = await getPublicProjects(params)
    projects.value = res.data || []
    currentPage.value = 1
    nextTick(updateExpandWidth)
  } catch { projects.value = [] }
  finally { loading.value = false }
}

function handleSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(fetchData, 300) }

function handleSelectionChange(selection) { selectedIds.value = selection.map(s => s.id) }

function formatAmount(amount) {
  if (!amount && amount !== 0) return '-'
  const n = Number(amount)
  if (n >= 10000) return (n / 10000).toFixed(2) + ' 亿元'
  return n.toLocaleString('zh-CN') + ' 万元'
}

function truncate(text, max) { if (!text) return ''; return text.length > max ? text.slice(0, max) + '...' : text }
function tableRowClassName({ row }) { return row.follow_status_code === 'follow_focus' ? 'row-focus' : '' }

function demandStatusColor(s) {
  const map = { pending: '#e6a23c', processing: '#409eff', resolved: '#67c23a' }
  return map[s] || '#909399'
}
function demandStatusName(s) {
  const map = { pending: '待处理', processing: '处理中', resolved: '已解决' }
  return map[s] || s
}

// ---- 操作列 ----
function handleRowCmd(cmd, row) {
  if (cmd === 'view') {
    viewProject.value = row
    viewDrawerVisible.value = true
  } else if (cmd === 'delete') {
    handleDelete(row)
  }
}
function handleAddActivity(row) {
  router.push({ path: '/admin/activity', query: { project_id: row.id } })
}
function handleAI(row) {
  router.push({ path: '/toolbox', query: { topic: row.project_name } })
}

// ---- 查看 ----
function handleView(row) {
  viewProject.value = row
  viewDrawerVisible.value = true
}

// ---- 导出 ----
async function handleExport() {
  try {
    await ElMessageBox.confirm(
      `确定要导出选中的 ${selectedIds.value.length} 个项目为 Excel 文件吗？`,
      '确认导出',
      { confirmButtonText: '导出', cancelButtonText: '取消', type: 'info' }
    )
    await downloadExcel(selectedIds.value)
    ElMessage.success('导出成功')
  } catch { /* cancelled */ }
}

// ---- 导入 ----
function handleImportCmd(cmd) {
  if (cmd === 'download-template') {
    downloadImportTemplate().catch(err => ElMessage.error(err.message))
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
    const res = await importPreviewApi(file.raw)
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
  const removed = importRows.value[idx]
  importRows.value.splice(idx, 1)
  // 重新统计
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
    const res = await importExecute(validRows)
    if (res.code === 0) {
      ElMessage.success(`成功导入 ${res.data?.count || validRows.length} 条记录`)
      importDialogVisible.value = false
    }
  } catch (err) { ElMessage.error(err.message) }
  finally { importing.value = false }
}

// ---- 新建 ----
async function openCreate() {
  editMode.value = 'create'
  editingId.value = null
  resetForm()
  fileList.value = []
  try {
    const res = await getMaxOrderNo()
    if (res.code === 0) form.order_no = (res.data.max_order_no || 0) + 1
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
      form.order_no = d.order_no || 0
      form.project_name = d.project_name || ''
      form.project_type_code = d.project_type_code || ''
      form.invest_amount = Number(d.invest_amount) || 0
      form.invest_enterprise = d.invest_enterprise || ''
      form.enterprise_info = d.enterprise_info || ''
      form.project_content = d.project_content || ''
      form.project_doc = d.project_doc || ''
      // 解析已有的文件列表
      try {
        const parsed = typeof form.project_doc === 'string' ? JSON.parse(form.project_doc) : form.project_doc
        fileList.value = Array.isArray(parsed) ? parsed.map((url, i) => ({ name: url.split('/').pop() || `文件${i+1}`, url })) : []
      } catch { fileList.value = [] }
      form.follow_status_code = d.follow_status_code || ''
      form.meeting_status_code = d.meeting_status_code || 'not_meeting'
      form.recommend_unit_code = d.recommend_unit_code || ''
      form.responsible_unit_code = d.responsible_unit_code || ''
      form.person_in_charge = d.person_in_charge || ''
      form.first_contact_date = d.first_contact_date || ''
      form.demands = (d.demands || []).map(dd => ({
        ...dd,
        demand_type_code: dd.demand_type_code || '',
        unit_code: dd.unit_code || ''
      }))
    }
    editDrawerVisible.value = true
  } catch (err) { ElMessage.error(err.message) }
}

function resetForm() {
  Object.assign(form, defaultForm())
  fileList.value = []
  formRef.value?.clearValidate()
}

function addDemand() { form.demands.push({ demand_type_code: '', demand_content: '', resolution: '', unit_code: '', status: 'pending' }) }
function removeDemand(i) { form.demands.splice(i, 1) }

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
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    // 构建 project_doc JSON 数组
    const docUrls = fileList.value
      .filter(f => f.url)
      .map(f => f.url)
    const projectDoc = JSON.stringify(docUrls)

    const data = {
      order_no: Number(form.order_no),
      project_name: form.project_name,
      project_type_code: form.project_type_code,
      invest_amount: Number(form.invest_amount),
      invest_enterprise: form.invest_enterprise,
      enterprise_info: form.enterprise_info,
      project_content: form.project_content,
      project_doc: projectDoc,
      follow_status_code: form.follow_status_code,
      meeting_status_code: form.meeting_status_code,
      recommend_unit_code: form.recommend_unit_code,
      responsible_unit_code: form.responsible_unit_code,
      person_in_charge: form.person_in_charge,
      first_contact_date: form.first_contact_date || null,
      demands: form.demands
    }

    if (editMode.value === 'create') {
      await createProject(data)
      ElMessage.success('项目创建成功')
      editDrawerVisible.value = false
      fetchData()
    } else {
      // 编辑模式：尝试保存
      const res = await updateProject(editingId.value, data)
      if (res.code === 2) {
        // 顺序号冲突：询问是否下移
        await ElMessageBox.confirm(
          `顺序号 ${form.order_no} 已被项目「${res.data?.conflict_project || ''}」使用，是否将后续项目整体下移？`,
          '顺序号冲突',
          { confirmButtonText: '确认下移', cancelButtonText: '取消', type: 'warning' }
        )
        // 重试：force_reorder
        saving.value = true
        const docUrls2 = fileList.value.filter(f => f.url).map(f => f.url)
        const retryRes = await updateProject(editingId.value, { ...data, project_doc: JSON.stringify(docUrls2), force_reorder: true })
        if (retryRes.code === 0) {
          editDrawerVisible.value = false
          fetchData()
          ElMessage.success('项目更新成功，顺序号已重排')
          return
        }
      }
      editDrawerVisible.value = false
      fetchData()
      ElMessage.success('项目更新成功')
    }
  } catch (err) {
    ElMessage.error(err.message)
  }
  finally { saving.value = false }
}

// ---- 删除 ----
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除项目「${row.project_name}」吗？`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    await deleteProject(row.id)
    ElMessage.success('项目已删除')
    fetchData()
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.investment-page { min-height: 100vh; background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%); }
.page-body { max-width: 1600px; margin: 0 auto; padding: 28px 32px 60px; }
.content-card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 20px rgba(0,0,0,0.06); }
.toolbar { display: flex; gap: 16px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
.toolbar-spacer { flex: 1; }
.search-input { width: 320px; }

/* 展开行 */
.expand-content {
  padding: 8px 20px 16px;
  background: #f5f7fa;
  box-sizing: border-box;
  overflow: hidden;
}
.expand-block {
  margin-top: 14px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  box-sizing: border-box;
}
.expand-block:first-child { margin-top: 6px; }
.expand-block-title {
  font-size: 12px;
  font-weight: 600;
  color: #1a3a5c;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px dashed #e4e7ed;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.expand-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 28px;
}
.expand-item { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.expand-item label { font-size: 12px; color: #909399; font-weight: 500; }
.expand-item span {
  font-size: 14px;
  color: #303133;
  word-break: break-word;
  overflow-wrap: break-word;
}
.expand-text-block {
  margin: 0;
  font-size: 14px;
  color: #303133;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: break-word;
}

/* 项目类型标签 */
.project-type-tag {
  display: inline-block;
  padding: 2px 10px;
  font-size: 12px;
  color: #1a3a5c;
  background: #e8f0f8;
  border: 1px solid #c8daf0;
  border-radius: 4px;
  white-space: nowrap;
}

.enterprise-name { cursor: default; border-bottom: 1px dotted #909399; }
.content-preview { cursor: default; color: #606266; }

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}
.show-all-check { margin-left: 8px; }
.doc-link { color: #409eff; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }
.doc-link:hover { text-decoration: underline; }

/* 操作列 */
.action-cell { display: flex; align-items: center; gap: 2px; }
.action-more { font-size: 18px; padding: 4px; }

/* 展开卡片 - 诉求 */
.demand-list { width: 100%; }
.demand-row-card {
  padding: 10px 12px;
  margin-bottom: 8px;
  background: #f8f9fb;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}
.demand-row-card:last-child { margin-bottom: 0; }
.demand-row-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.demand-idx { color: #909399; font-weight: 600; min-width: 20px; font-size: 13px; }
.demand-type-badge {
  display: inline-block;
  padding: 1px 8px;
  font-size: 11px;
  color: #1a3a5c;
  background: #e8f0f8;
  border: 1px solid #c8daf0;
  border-radius: 3px;
}
.demand-unit-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: #1a3a5c;
  background: #f0f5ff;
  border: 1px solid #c8daf0;
  border-radius: 3px;
  padding: 1px 8px;
}
.demand-top-spacer { flex: 1; }
.demand-row-body {
  font-size: 13px;
  color: #303133;
  line-height: 1.6;
  margin-bottom: 6px;
  padding-bottom: 6px;
  border-bottom: 1px dashed #e4e7ed;
}
.demand-row-res {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
}
.res-divider {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
  color: #409eff;
  white-space: nowrap;
  flex-shrink: 0;
}
.res-text {
  color: #606266;
  line-height: 1.6;
}
:deep(.row-focus) { background-color: #fef7e8 !important; }
:deep(.row-focus:hover > td) { background-color: #fdf0d5 !important; }
:deep(.col-order-no) { padding-left: 4px !important; padding-right: 4px !important; }

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

/* 诉求卡片 */
.demands-section { margin-bottom: 16px; }
.demand-card { background: #f8f9fb; border: 1px solid #ebeef5; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
.demand-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.demand-card-title { font-size: 13px; font-weight: 600; color: #606266; }

.drawer-footer { display: flex; justify-content: center; gap: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #ebeef5; }

.upload-wrapper { width: 100%; }
.upload-wrapper :deep(.el-upload-dragger) { padding: 16px 0; }
.upload-wrapper :deep(.el-upload__text) { font-size: 13px; }
.upload-compact :deep(.el-upload-dragger) { padding: 8px 0 !important; height: 80px !important; }
.upload-compact :deep(.el-upload-dragger .el-icon--upload) { font-size: 24px; margin-bottom: 0; }

/* 导入对话框 */
.import-summary { display: flex; gap: 24px; margin-bottom: 16px; font-size: 14px; }
.import-summary strong { font-size: 18px; margin: 0 2px; }
.summary-valid { color: #67c23a; }
.summary-error { color: #f56c6c; }
.import-table-wrap { border: 1px solid #ebeef5; border-radius: 6px; overflow: hidden; }
:deep(.import-error-row) { background-color: #fef0f0 !important; }
:deep(.import-error-row:hover > td) { background-color: #fde2e2 !important; }
</style>

<!-- 非 scoped 样式：覆盖 Element Plus teleport 到 body 的 popper 和内部表格结构 -->
<style>
/* 悬停留固定宽度 496px（popper 被 teleport 到 body，必须非 scoped） */
.enterprise-tooltip {
  max-width: 496px !important;
  word-break: break-word !important;
  overflow-wrap: break-word !important;
}
.content-tooltip {
  max-width: 496px !important;
  white-space: pre-wrap !important;
  word-break: break-word !important;
}

/* 展开单元格冻结 + 宽度约束 */
.el-table__expanded-cell {
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}
</style>
