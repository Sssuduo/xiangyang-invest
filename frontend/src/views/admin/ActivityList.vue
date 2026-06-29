<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>招商动态管理</h2>
          <div class="page-header-actions">
            <el-button v-if="selectedIds.length > 0" type="danger" @click="handleBatchDelete">
              <el-icon><Delete /></el-icon> 批量删除 ({{ selectedIds.length }})
            </el-button>
            <el-button type="primary" @click="openCreate">
              <el-icon><Plus /></el-icon> 添加动态
            </el-button>
          </div>
        </div>

        <!-- 搜索筛选 -->
        <div class="filter-bar">
          <el-input v-model="searchText" placeholder="搜索项目名称、动态内容..." :prefix-icon="Search" clearable class="search-input" @input="handleSearch" />
          <el-select v-model="filterProjectId" placeholder="项目" clearable @change="currentPage = 1; fetchData()" style="width: 180px;">
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
          <el-select v-model="filterTags" multiple collapse-tags placeholder="标签筛选" clearable @change="currentPage = 1; fetchData()" style="width: 200px;">
            <el-option v-for="d in activityTagDicts" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
        </div>

        <el-table :data="activities" row-key="id" v-loading="loading" @selection-change="handleSelectionChange" empty-text="暂无动态数据">
          <el-table-column type="selection" width="45" />
          <el-table-column label="项目" width="210">
            <template #default="{ row }">
              <el-tag class="project-name-tag" @click="handleProjectClick(row)">
                {{ row.project_name }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="日期" width="140" align="center">
            <template #default="{ row }">
              <span class="date-cell">{{ row.date || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="动态内容" min-width="210" show-overflow-tooltip>
            <template #default="{ row }">{{ truncate(row.content, 60) }}</template>
          </el-table-column>
          <el-table-column label="附件" width="80" align="center">
            <template #default="{ row }">
              <span>{{ row.files ? row.files.length : 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="标签" width="160">
            <template #default="{ row }">
              <el-tag v-for="tag in (row.tags || [])" :key="tag" size="small" effect="plain" style="margin-right: 4px; margin-bottom: 2px;">
                {{ getTagName(tag) }}
              </el-tag>
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
    </main>

    <!-- 查看抽屉 -->
    <ActivityDrawer v-model="viewDrawerVisible" :activity="viewActivity" />

    <!-- 项目详情抽屉 -->
    <ProjectDrawer v-model="projectDrawerVisible" :project="projectDrawerProject" />

    <!-- 编辑抽屉 -->
    <el-drawer v-model="editDrawerVisible" direction="rtl" size="680px" @closed="resetForm">
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">
            <el-icon><Edit /></el-icon>
            {{ editMode === 'create' ? '新建动态' : '编辑动态' }}
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
                multiple
                drag
                accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.png,.jpg,.jpeg"
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖动文件到此处 或 <em>点击上传</em></div>
                <template #tip>
                  <div class="el-upload__tip">支持 PDF/DOC/DOCX/PPT/XLS/图片，可多个上传；也可 <kbd>Ctrl+V</kbd> 粘贴图片</div>
                </template>
              </el-upload>
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
import { Search, Plus, InfoFilled, Document, UploadFilled, Delete, Edit, PriceTag } from '@element-plus/icons-vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import ActivityDrawer from '@/components/investment/ActivityDrawer.vue'
import ProjectDrawer from '@/components/investment/ProjectDrawer.vue'
import { getActivities, createActivity, updateActivity, getActivity, deleteActivity, batchDeleteActivities } from '@/api/activity'
import { getPublicProjects, getProject, getPublicDemandDicts } from '@/api/investment'
import { getDictItems } from '@/api/dict'

const activities = ref([])
const loading = ref(false)
const searchText = ref('')
const activityTagDicts = ref([])
const filterProjectId = ref('')
const selectedIds = ref([])
const filterDateRange = ref([])
const filterDateFrom = ref('')
const filterDateTo = ref('')
const filterTags = ref([])
const projectList = ref([])

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

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

const defaultForm = () => ({
  project_id: '',
  date: '',
  content: '',
  files: [],
  tags: []
})

const form = reactive(defaultForm())

const rules = {
  project_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
  content: [{ required: true, message: '请输入动态内容', trigger: 'blur' }]
}

onMounted(async () => { await loadProjects(); loadActivityTags(); fetchData() })

async function loadActivityTags() {
  try {
    // 优先使用公开 API（无需额外鉴权，更可靠）
    const res = await getPublicDemandDicts()
    if (res.code === 0 && res.data) {
      activityTagDicts.value = res.data.activity_tags || []
    }
  } catch {
    // 降级：尝试 admin dict API
    try {
      const res = await getDictItems('activity_tags')
      if (res.code === 0) activityTagDicts.value = res.data || []
    } catch { /* ignore */ }
  }
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
    const res = await getActivities(params)
    activities.value = res.data || []
    total.value = res.total || 0
  } catch { activities.value = [] }
  finally { loading.value = false }
}

function handleSearch() { currentPage.value = 1; clearTimeout(searchTimer); searchTimer = setTimeout(fetchData, 300) }

function onDateRangeChange(vals) {
  if (vals && vals.length === 2) {
    filterDateFrom.value = vals[0]; filterDateTo.value = vals[1]
  } else {
    filterDateFrom.value = ''; filterDateTo.value = ''
  }
  currentPage.value = 1
  fetchData()
}

function handlePageChange(page) { currentPage.value = page; fetchData() }
function handlePageSizeChange(size) { pageSize.value = size; currentPage.value = 1; fetchData() }

function truncate(text, max) { if (!text) return ''; return text.length > max ? text.slice(0, max) + '...' : text }

function handleSelectionChange(selection) { selectedIds.value = selection.map(s => s.id) }

function handleView(row) {
  const tagMap = {}
  activityTagDicts.value.forEach(t => { tagMap[t.code] = t.name })
  row._tagNames = (row.tags || []).map(tc => tagMap[tc] || tc)
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
      form.date = d.date ? d.date.substring(0, 10) : ''
      form.content = d.content || ''
      form.files = d.files || []
      form.tags = Array.isArray(d.tags) ? [...d.tags] : []
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
      tags: form.tags
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
.page-header-actions { display: flex; gap: 10px; align-items: center; }

.filter-bar { display: flex; gap: 16px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
.search-input { width: 320px; }

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
.upload-wrapper { width: 100%; }
.upload-wrapper :deep(.el-upload-dragger) { padding: 16px 0; }
.upload-wrapper :deep(.el-upload__text) { font-size: 13px; }
</style>

<style>
.el-drawer__header {
  margin-bottom: 0 !important;
  padding: 0 !important;
}
.el-drawer__body {
  padding: 12px 20px 20px !important;
}
</style>
