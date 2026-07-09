<template>
  <div class="knowledge-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 页面标题 -->
        <div class="page-header">
          <h1>本地招商知识库</h1>
          <el-button v-if="businessAuth.hasPermission('knowledge', 'add')" type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 添加知识条目
          </el-button>
        </div>

        <!-- 搜索筛选 -->
        <div class="filter-bar">
          <el-input v-model="searchText" placeholder="搜索标题、内容、标签..." :prefix-icon="Search" clearable class="search-input" @input="handleSearch" />
          <el-select v-model="filterCategory" placeholder="分类筛选" clearable @change="fetchData" style="width: 160px;">
            <el-option v-for="cat in categoryOptions" :key="cat.code" :label="cat.name" :value="cat.code" />
          </el-select>
          <el-checkbox v-model="includeInactive" @change="fetchData" style="margin-left: 8px;">包含已停用</el-checkbox>
        </div>

        <!-- 表格 -->
        <el-table :data="entries" row-key="id" v-loading="loading" empty-text="暂无知识条目">
          <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
          <el-table-column label="分类" width="120" align="center">
            <template #default="{ row }">
              <el-tag effect="dark" size="small">{{ resolveCategory(row.category) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="标签" width="180">
            <template #default="{ row }">
              <el-tag v-for="tag in (row.tags || [])" :key="tag" size="small" effect="plain" style="margin-right: 4px; margin-bottom: 2px;">
                {{ tag }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source" label="来源" width="140" show-overflow-tooltip />
          <el-table-column label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.is_active" type="success" effect="dark" size="small">启用</el-tag>
              <el-tag v-else type="info" effect="dark" size="small">停用</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="170" align="center">
            <template #default="{ row }">{{ fmtDt(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="handleView(row)">查看</el-button>
              <el-button v-if="businessAuth.hasPermission('knowledge', 'edit')" size="small" link type="success" @click="openEdit(row)">编辑</el-button>
              <el-button v-if="businessAuth.hasPermission('knowledge', 'delete')" size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[15, 30, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="fetchData"
          @size-change="handlePageSizeChange"
          style="margin-top: 20px; justify-content: flex-end;"
        />

        <!-- 查看抽屉 -->
        <el-drawer v-model="viewDrawerVisible" direction="rtl" size="560px">
          <template #header>
            <div class="drawer-title-bar">
              <span class="drawer-title">
                <el-icon><View /></el-icon>
                知识条目详情
              </span>
            </div>
          </template>
          <template v-if="viewEntry">
            <el-descriptions :column="1" border size="small" class="detail-desc">
              <el-descriptions-item label="标题">
                <strong>{{ viewEntry.title }}</strong>
              </el-descriptions-item>
              <el-descriptions-item label="分类">
                <el-tag effect="dark" size="small">{{ resolveCategory(viewEntry.category) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="标签">
                <el-tag v-for="tag in (viewEntry.tags || [])" :key="tag" size="small" effect="plain" style="margin-right: 4px;">
                  {{ tag }}
                </el-tag>
                <span v-if="!viewEntry.tags || viewEntry.tags.length === 0">-</span>
              </el-descriptions-item>
              <el-descriptions-item label="来源">{{ viewEntry.source || '-' }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag v-if="viewEntry.is_active" type="success" effect="dark" size="small">启用</el-tag>
                <el-tag v-else type="info" effect="dark" size="small">停用</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="更新时间">{{ fmtDt(viewEntry.updated_at) }}</el-descriptions-item>
              <el-descriptions-item label="正文内容">
                <div class="text-block">{{ viewEntry.content }}</div>
              </el-descriptions-item>
              <el-descriptions-item v-if="viewEntry.attach_files && viewEntry.attach_files.length > 0" label="附件">
                <div class="attach-list">
                  <a v-for="(item, idx) in viewEntry.attach_files" :key="idx" :href="typeof item === 'string' ? item : item.url" target="_blank" class="attach-link" :download="typeof item === 'string' ? (item.split('/').pop() || '') : (item.original_name || '')">
                    <el-icon><Link /></el-icon>
                    {{ typeof item === 'string' ? item.split('/').pop() : (item.original_name || item.url?.split('/').pop() || `附件${idx + 1}`) }}
                  </a>
                </div>
              </el-descriptions-item>
            </el-descriptions>
          </template>
        </el-drawer>

        <!-- 编辑抽屉（新建/编辑共用） -->
        <el-drawer v-model="editDrawerVisible" direction="rtl" size="780px" @closed="resetForm">
          <template #header>
            <div class="drawer-title-bar">
              <span class="drawer-title">
                <el-icon><Edit /></el-icon>
                {{ editMode === 'create' ? '新建知识条目' : '编辑知识条目' }}
              </span>
            </div>
          </template>
          <div class="drawer-form">
            <el-form ref="formRef" :model="form" :rules="rules" label-width="90px" label-position="right">
              <!-- 基础信息 -->
              <div class="section-header">
                <span class="section-icon"><el-icon><InfoFilled /></el-icon></span>
                <span class="section-title">基础信息</span>
              </div>
              <el-form-item label="标题" prop="title">
                <el-input v-model="form.title" placeholder="请输入标题" maxlength="255" />
              </el-form-item>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="分类" prop="category">
                    <el-select v-model="form.category" placeholder="请选择分类" style="width: 100%;">
                      <el-option v-for="cat in categoryOptions" :key="cat.code" :label="cat.name" :value="cat.code" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="来源">
                    <el-input v-model="form.source" placeholder="信息来源" maxlength="255" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="启用状态">
                <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
              </el-form-item>

              <!-- 标签 -->
              <div class="section-header">
                <span class="section-icon"><el-icon><PriceTag /></el-icon></span>
                <span class="section-title">标签</span>
              </div>
              <el-form-item label="标签">
                <div class="tag-input-wrap">
                  <div class="tag-list">
                    <el-tag
                      v-for="(tag, idx) in form.tags"
                      :key="idx"
                      closable
                      size="default"
                      effect="plain"
                      @close="removeTag(idx)"
                      style="margin-right: 6px; margin-bottom: 6px;"
                    >
                      {{ tag }}
                    </el-tag>
                  </div>
                  <div class="tag-add-row">
                    <el-input
                      ref="tagInputRef"
                      v-model="tagInputValue"
                      size="small"
                      placeholder="输入标签后按回车添加"
                      style="width: 200px;"
                      maxlength="32"
                      @keyup.enter="addTag"
                    />
                    <el-button size="small" @click="addTag" style="margin-left: 8px;">添加</el-button>
                  </div>
                </div>
              </el-form-item>

              <!-- 内容 -->
              <div class="section-header">
                <span class="section-icon"><el-icon><Document /></el-icon></span>
                <span class="section-title">内容</span>
              </div>
              <el-form-item label="正文内容" prop="content">
                <el-input v-model="form.content" type="textarea" :rows="12" placeholder="请输入知识条目内容..." maxlength="10000" show-word-limit />
              </el-form-item>

              <!-- 附件 -->
              <div class="section-header">
                <span class="section-icon"><el-icon><Paperclip /></el-icon></span>
                <span class="section-title">附件</span>
              </div>
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
                <!-- 已上传文件列表（带预览/下载） -->
                <div v-if="fileList.length > 0" class="file-preview-list" style="margin-top: 8px;">
                  <div v-for="(f, idx) in fileList" :key="idx" class="file-preview-item">
                    <el-icon><Document /></el-icon>
                    <span class="file-preview-name" :title="f.originalName || f.name">{{ f.originalName || f.name }}</span>
                    <el-button size="small" link type="primary" @click="previewKBFile(f.url, f.originalName || f.name)">预览</el-button>
                    <el-button size="small" link type="success" @click="downloadKBFile(f.url, f.originalName || f.name)">下载</el-button>
                  </div>
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
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, InfoFilled, Document, UploadFilled, PriceTag, Paperclip, View, Edit, Link } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import { getEntries, createEntry, updateEntry, getEntry, deleteEntry, getCategories } from '@/api/knowledge'
import { useBusinessAuthStore } from '@/stores/businessAuth'

const businessAuth = useBusinessAuthStore()

// 分类从后端 API 动态获取
const categoryOptions = ref([])
async function loadCategories() {
  try {
    const res = await getCategories()
    if (res.code === 0) categoryOptions.value = res.data || []
  } catch { /* ignore */ }
}

// 分页
const currentPage = ref(1)
const pageSize = ref(15)
const total = ref(0)

// 查看抽屉
const viewDrawerVisible = ref(false)
const viewEntry = ref(null)

// 编辑抽屉
const editDrawerVisible = ref(false)
const editMode = ref('create')
const editingId = ref(null)
const formRef = ref(null)
const uploadRef = ref(null)
const tagInputRef = ref(null)
const saving = ref(false)
const fileList = ref([])
const tagInputValue = ref('')
const uploadUrl = '/api/upload'
const uploadHeaders = {}

const defaultForm = () => ({
  title: '',
  category: '',
  tags: [],
  source: '',
  content: '',
  attach_files: [],
  is_active: true,
  sort_order: 0
})

const form = reactive(defaultForm())

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [{ required: true, message: '请输入内容', trigger: 'blur' }]
}

let searchTimer = null

onMounted(() => { loadCategories(); fetchData() })

function fmtDt(d) {
  if (!d) return '-'
  return new Date(d + 'Z').toLocaleString('zh-CN', { hour12: false })
}

// ---- 数据获取 ----
async function fetchData() {
  loading.value = true
  try {
    const params = { page: currentPage.value, page_size: pageSize.value }
    if (searchText.value) params.search = searchText.value
    if (filterCategory.value) params.category = filterCategory.value
    if (includeInactive.value) params.include_inactive = '1'
    const res = await getEntries(params)
    if (res.code === 0) {
      entries.value = res.data.items || []
      total.value = res.data.total || 0
    }
  } catch { entries.value = [] }
  finally { loading.value = false }
}

function handleSearch() {
  currentPage.value = 1
  clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchData, 300)
}

function handlePageSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  fetchData()
}

// ---- 查看 ----
function handleView(row) {
  viewEntry.value = row
  viewDrawerVisible.value = true
}

// ---- 新建 ----
function openCreate() {
  editMode.value = 'create'
  editingId.value = null
  resetForm()
  editDrawerVisible.value = true
}

// ---- 编辑 ----
async function openEdit(row) {
  editMode.value = 'edit'
  editingId.value = row.id
  try {
    const res = await getEntry(row.id)
    if (res.code === 0) {
      const d = res.data
      form.title = d.title || ''
      form.category = d.category || ''
      form.tags = Array.isArray(d.tags) ? [...d.tags] : []
      form.source = d.source || ''
      form.content = d.content || ''
      form.is_active = d.is_active !== undefined ? d.is_active : true
      form.sort_order = d.sort_order || 0
      form.attach_files = Array.isArray(d.attach_files) ? d.attach_files : []
      // 解析已有的文件列表
      fileList.value = form.attach_files.map((item, i) => {
        if (typeof item === 'string') {
          return { name: item.split('/').pop() || `文件${i + 1}`, url: item }
        }
        return { name: item.original_name || item.url.split('/').pop(), url: item.url, originalName: item.original_name }
      })
    }
    editDrawerVisible.value = true
  } catch (err) { ElMessage.error(err.message) }
}

function resetForm() {
  Object.assign(form, defaultForm())
  tagInputValue.value = ''
  fileList.value = []
  formRef.value?.clearValidate()
}

// ---- 标签操作 ----
function addTag() {
  const val = tagInputValue.value.trim()
  if (!val) return
  if (form.tags.includes(val)) {
    ElMessage.warning('标签已存在')
    return
  }
  form.tags.push(val)
  tagInputValue.value = ''
  nextTick(() => { tagInputRef.value?.focus() })
}

function removeTag(idx) {
  form.tags.splice(idx, 1)
}

// ---- 文件上传处理 ----
function handleUploadSuccess(response, file) {
  if (response.code === 0) {
    file.url = response.data.url
    file.originalName = response.data.original_name || file.name
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

function previewKBFile(url, name) {
  const ext = (name || '').split('.').pop().toLowerCase()
  if (['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) {
    window.open(url, '_blank')
  } else if (['doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'].includes(ext)) {
    ElMessage.info('Office 文件需下载后查看，点击"下载"按钮即可')
  } else {
    ElMessage.info('该文件类型不支持在线预览，请下载后查看')
  }
}

function downloadKBFile(url, name) {
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// ---- 保存 ----
async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const docUrls = fileList.value.filter(f => f.url).map(f => ({
      url: f.url,
      original_name: f.originalName || f.name || f.url.split('/').pop()
    }))
    const data = {
      title: form.title,
      category: form.category,
      tags: form.tags,
      source: form.source,
      content: form.content,
      is_active: form.is_active,
      sort_order: form.sort_order,
      attach_files: docUrls
    }

    if (editMode.value === 'create') {
      await createEntry(data)
      ElMessage.success('知识条目创建成功')
    } else {
      await updateEntry(editingId.value, data)
      ElMessage.success('知识条目更新成功')
    }
    editDrawerVisible.value = false
    fetchData()
  } catch (err) { ElMessage.error(err.message) }
  finally { saving.value = false }
}

// ---- 删除 ----
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除知识条目「${row.title}」吗？此操作不可恢复。`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    await deleteEntry(row.id)
    ElMessage.success('知识条目已删除')
    fetchData()
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.knowledge-page { min-height: 100vh; background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%); }
.page-body { max-width: 1600px; margin: 0 auto; padding: 28px 32px 60px; }
.content-card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 20px rgba(0,0,0,0.06); }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { margin: 0; font-size: 22px; color: #1a3a5c; font-weight: 700; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
.search-input { width: 320px; }

/* 查看抽屉 */
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
.detail-desc :deep(.el-descriptions__label) { width: 100px; font-weight: 500; color: #606266; }
.text-block { white-space: pre-wrap; line-height: 1.7; font-size: 13px; color: #303133; max-height: 400px; overflow-y: auto; }
.attach-list { display: flex; flex-direction: column; gap: 6px; }
.attach-link {
  display: inline-flex; align-items: center; gap: 4px;
  color: #409eff; font-size: 13px; text-decoration: none;
}
.attach-link:hover { text-decoration: underline; }

/* 编辑抽屉 */
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

/* 标签输入 */
.tag-input-wrap { width: 100%; }
.tag-list { min-height: 32px; }
.tag-add-row { display: flex; align-items: center; margin-top: 6px; }

/* 文件上传 */
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
