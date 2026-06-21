<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>招商动态管理</h2>
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 添加动态
          </el-button>
        </div>

        <!-- 搜索筛选 -->
        <div class="filter-bar">
          <el-input v-model="searchText" placeholder="搜索项目名称、动态内容..." :prefix-icon="Search" clearable class="search-input" @input="handleSearch" />
          <el-select v-model="filterProjectId" placeholder="所属项目" clearable @change="fetchData" style="width: 180px;">
            <el-option v-for="p in projectList" :key="p.id" :label="p.project_name" :value="p.id" />
          </el-select>
          <el-date-picker
            v-model="filterDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始"
            end-placeholder="结束"
            value-format="YYYY-MM-DD"
            @change="onDateRangeChange"
            style="width: 240px;"
          />
        </div>

        <el-table :data="activities" stripe row-key="id" v-loading="loading" empty-text="暂无动态数据">
          <el-table-column label="所属项目" width="180">
            <template #default="{ row }">
              <el-tag effect="plain" size="small" type="info">{{ row.project_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="date" label="日期" width="170" />
          <el-table-column label="动态内容" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">{{ truncate(row.content, 60) }}</template>
          </el-table-column>
          <el-table-column label="附件" width="80" align="center">
            <template #default="{ row }">
              <span>{{ row.files ? row.files.length : 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="handleView(row)">查看</el-button>
              <el-button size="small" link type="success" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </main>

    <!-- 查看抽屉 -->
    <ActivityDrawer v-model="viewDrawerVisible" :activity="viewActivity" />

    <!-- 编辑抽屉 -->
    <el-drawer v-model="editDrawerVisible" direction="rtl" size="680px" @closed="resetForm">
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">{{ editMode === 'create' ? '新建动态' : '编辑动态' }}</span>
        </div>
      </template>
      <div class="drawer-form">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" label-position="right">
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, InfoFilled, Document, UploadFilled } from '@element-plus/icons-vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import ActivityDrawer from '@/components/investment/ActivityDrawer.vue'
import { getActivities, createActivity, updateActivity, getActivity, deleteActivity } from '@/api/activity'
import { getPublicProjects } from '@/api/investment'

const activities = ref([])
const loading = ref(false)
const searchText = ref('')
const filterProjectId = ref('')
const filterDateRange = ref([])
const filterDateFrom = ref('')
const filterDateTo = ref('')
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
    const res = await getActivities(params)
    activities.value = res.data || []
  } catch { activities.value = [] }
  finally { loading.value = false }
}

function handleSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(fetchData, 300) }

function onDateRangeChange(vals) {
  if (vals && vals.length === 2) {
    filterDateFrom.value = vals[0]; filterDateTo.value = vals[1]
  } else {
    filterDateFrom.value = ''; filterDateTo.value = ''
  }
  fetchData()
}

function truncate(text, max) { if (!text) return ''; return text.length > max ? text.slice(0, max) + '...' : text }

function handleView(row) {
  viewActivity.value = row
  viewDrawerVisible.value = true
}

function openCreate() {
  editMode.value = 'create'
  editingId.value = null
  resetForm()
  fileList.value = []
  editDrawerVisible.value = true
}

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
    } else {
      await updateActivity(editingId.value, data)
      ElMessage.success('动态更新成功')
    }
    editDrawerVisible.value = false
    fetchData()
  } catch (err) { ElMessage.error(err.message) }
  finally { saving.value = false }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该动态吗？', '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    await deleteActivity(row.id)
    ElMessage.success('动态已删除')
    fetchData()
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: #f5f7fa; }
.admin-content { padding: 28px 32px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { color: #1a3a5c; margin: 0; }

.filter-bar { display: flex; gap: 16px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
.search-input { width: 320px; }

.drawer-title-bar {
  background: linear-gradient(135deg, #3a7abd 0%, #6ba3d6 100%);
  margin: -20px -20px 0 -20px; padding: 10px 20px;
}
.drawer-title { color: #fff; font-size: 16px; font-weight: 600; letter-spacing: 1px; }
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
.upload-wrapper { width: 100%; }
.upload-wrapper :deep(.el-upload-dragger) { padding: 16px 0; }
.upload-wrapper :deep(.el-upload__text) { font-size: 13px; }
</style>
