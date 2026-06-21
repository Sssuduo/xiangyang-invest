<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>招商对接项目库</h2>
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 添加项目
          </el-button>
        </div>

        <!-- 搜索筛选 -->
        <div class="filter-bar">
          <el-input v-model="searchText" placeholder="模糊搜索..." :prefix-icon="Search" clearable class="search-input" @input="handleSearch" />
          <el-select v-model="filterFollow" placeholder="跟进状态" clearable @change="fetchData" style="width: 130px;">
            <el-option v-for="d in dicts.follow_statuses" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
          <el-select v-model="filterMeeting" placeholder="上会状态" clearable @change="fetchData" style="width: 130px;">
            <el-option v-for="d in dicts.meeting_statuses" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
          <el-select v-model="filterType" placeholder="项目类型" clearable @change="fetchData" style="width: 140px;">
            <el-option v-for="d in dicts.project_types" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
        </div>

        <!-- 表格 -->
        <el-table :data="projects" stripe row-key="id" v-loading="loading" empty-text="暂无项目">
          <el-table-column prop="order_no" label="序号" width="65" align="left" />
          <el-table-column prop="project_name" label="项目名称" min-width="150" show-overflow-tooltip />
          <el-table-column label="项目类型" width="140">
            <template #default="{ row }">{{ resolveName('project_types', row.project_type_code) }}</template>
          </el-table-column>
          <el-table-column prop="invest_enterprise" label="投资商名称" min-width="140" show-overflow-tooltip />
          <el-table-column label="投资金额(万)" width="120" align="right">
            <template #default="{ row }">{{ formatMoney(row.invest_amount) }}</template>
          </el-table-column>
          <el-table-column label="跟进状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :color="resolveColor('follow_statuses', row.follow_status_code)" effect="dark" size="small">
                {{ resolveName('follow_statuses', row.follow_status_code) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="上会状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :color="resolveColor('meeting_statuses', row.meeting_status_code)" effect="dark" size="small">
                {{ resolveName('meeting_statuses', row.meeting_status_code) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="责任单位" width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ resolveName('organizations', row.responsible_unit_code) }}</template>
          </el-table-column>
          <el-table-column prop="person_in_charge" label="责任人" width="80" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="handleView(row)">查看</el-button>
              <el-button size="small" link type="success" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

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
                <el-input v-model="form.project_content" type="textarea" :rows="3" placeholder="项目详细内容..." maxlength="5000" show-word-limit />
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
                  >
                    <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                    <div class="el-upload__text">拖动文件到此处 或 <em>点击上传</em></div>
                    <template #tip>
                      <div class="el-upload__tip">支持 PDF/DOC/DOCX/PPT/XLS/图片，可上传多个</div>
                    </template>
                  </el-upload>
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
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Delete, InfoFilled, OfficeBuilding, Connection, ChatLineSquare, UploadFilled } from '@element-plus/icons-vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import ProjectDrawer from '@/components/investment/ProjectDrawer.vue'
import { getProjects, deleteProject, getDicts, createProject, updateProject, getProject, getMaxOrderNo } from '@/api/investment'

const projects = ref([])
const loading = ref(false)
const searchText = ref('')
const filterFollow = ref('')
const filterMeeting = ref('')
const filterType = ref('')
const dicts = reactive({ follow_statuses: [], meeting_statuses: [], organizations: [], project_types: [] })

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

let searchTimer = null

onMounted(async () => { await loadDicts(); fetchData() })

async function loadDicts() {
  try { const res = await getDicts(); if (res.code === 0) Object.assign(dicts, res.data) } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (searchText.value) params.search = searchText.value
    if (filterFollow.value) params.follow_status = filterFollow.value
    if (filterMeeting.value) params.meeting_status = filterMeeting.value
    if (filterType.value) params.project_type = filterType.value
    const res = await getProjects(params)
    projects.value = res.data || []
  } catch { projects.value = [] }
  finally { loading.value = false }
}

function handleSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(fetchData, 300) }
function resolveName(key, code) { return dicts[key]?.find(d => d.code === code)?.name || code || '-' }
function resolveColor(key, code) { return dicts[key]?.find(d => d.code === code)?.display_color || '#909399' }
function formatMoney(a) { if (!a && a !== 0) return '-'; return Number(a).toLocaleString('zh-CN') }

// ---- 查看 ----
function handleView(row) { viewProject.value = row; viewDrawerVisible.value = true }

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
      form.demands = (d.demands || []).map(dd => ({ ...dd }))
    }
    editDrawerVisible.value = true
  } catch (err) { ElMessage.error(err.message) }
}

function resetForm() {
  Object.assign(form, defaultForm())
  fileList.value = []
  formRef.value?.clearValidate()
}

// ---- 企业诉求操作 ----
function addDemand() { form.demands.push({ demand_content: '', resolution: '', status: 'pending' }) }
function removeDemand(i) { form.demands.splice(i, 1) }

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
      const res = await updateProject(editingId.value, data)
      if (res.code === 2) {
        await ElMessageBox.confirm(
          `顺序号 ${form.order_no} 已被项目「${res.data?.conflict_project || ''}」使用，是否将后续项目整体下移？`,
          '顺序号冲突',
          { confirmButtonText: '确认下移', cancelButtonText: '取消', type: 'warning' }
        )
        saving.value = true
        const d2 = fileList.value.filter(f => f.url).map(f => f.url)
        const retryRes = await updateProject(editingId.value, { ...data, project_doc: JSON.stringify(d2), force_reorder: true })
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
  } catch (err) { ElMessage.error(err.message) }
  finally { saving.value = false }
}

// ---- 删除 ----
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除项目「${row.project_name}」吗？删除后可在数据库恢复。`, '确认删除', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
    await deleteProject(row.id)
    ElMessage.success('项目已删除')
    fetchData()
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: #f5f7fa; }
.admin-content { padding: 28px 32px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
h2 { color: #1a3a5c; margin: 0; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
.search-input { width: 260px; }

/* 编辑抽屉 */
.drawer-form { padding: 0 4px; }
.drawer-form :deep(.el-form-item) { margin-bottom: 16px; }
.drawer-form :deep(.el-input-number .el-input__inner) { text-align: left; }

.drawer-title-bar {
  background: linear-gradient(135deg, #3a7abd 0%, #6ba3d6 100%);
  margin: -20px -20px 0 -20px;
  padding: 10px 20px;
}
.drawer-title { color: #fff; font-size: 16px; font-weight: 600; letter-spacing: 1px; }

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
</style>
