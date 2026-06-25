<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    direction="rtl"
    size="620px"
    @closed="handleClosed"
  >
    <template #header>
      <div class="drawer-title-bar">
        <span class="drawer-title">
          <el-icon><List /></el-icon>
          工作进展 · {{ projectName }}
        </span>
      </div>
    </template>

    <div class="drawer-body" v-loading="loading">
      <!-- 模式切换 + 新建按钮 -->
      <div class="mode-bar">
        <div class="mode-toggle">
          <span
            class="mode-btn"
            :class="{ active: mode === 'timeline' }"
            @click="mode = 'timeline'"
          >流式</span>
          <span
            class="mode-btn"
            :class="{ active: mode === 'simple' }"
            @click="mode = 'simple'"
          >极简</span>
        </div>
        <div class="mode-right">
          <el-button size="small" type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon> 新建进展
          </el-button>
          <span v-if="items.length > 0" class="mode-count">共 {{ items.length }} 条</span>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!loading && items.length === 0" class="empty-state">
        <el-icon class="empty-icon"><List /></el-icon>
        <p>暂无工作进展</p>
      </div>

      <!-- ========== 流式（时间轴）模式 ========== -->
      <div v-if="mode === 'timeline' && items.length > 0" class="timeline-wrap">
        <div
          v-for="(item, ai) in items"
          :key="item.id"
          class="timeline-item"
        >
          <div class="tl-node">
            <div class="tl-dot" />
            <div v-if="ai < items.length - 1" class="tl-line" />
          </div>
          <div class="tl-card">
            <div class="card-actions">
              <el-button size="small" link type="primary" title="编辑进展" @click="openEditDialog(item)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button v-if="businessAuth.hasPermission('construction', 'delete')" size="small" link type="danger" title="删除进展" @click="handleDelete(item)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div class="card-date">
              <el-icon><Clock /></el-icon>
              <span>{{ item.start_date }} ~ {{ item.end_date }}</span>
            </div>
            <div class="card-body">{{ item.content }}</div>
            <!-- 附件 -->
            <div v-if="item.files && item.files.length > 0" class="card-files">
              <div v-for="(file, fi) in item.files" :key="fi" class="file-item">
                <template v-if="isImage(file)">
                  <div class="file-thumb file-thumb--image">
                    <el-image
                      :src="file"
                      fit="cover"
                      :preview-src-list="getCardImageUrls(item.files)"
                      :initial-index="getImageIndex(item.files, fi)"
                      class="thumb-img-el"
                    />
                    <div class="file-actions">
                      <el-button size="small" link @click.stop="previewFile(file, item.files)">
                        <el-icon><ZoomIn /></el-icon>
                      </el-button>
                      <el-button size="small" link @click.stop="downloadFile(file)">
                        <el-icon><Download /></el-icon>
                      </el-button>
                    </div>
                  </div>
                </template>
                <template v-else>
                  <div class="file-thumb file-thumb--doc" @click="openFile(file)">
                    <div class="doc-icon-wrap" :style="{ background: docColor(file) }">
                      <span class="doc-ext">{{ getFileExt(file) }}</span>
                    </div>
                    <div class="doc-name" :title="getFileName(file)">{{ getFileName(file) }}</div>
                    <div class="file-actions">
                      <el-button size="small" link @click.stop="openFile(file)">
                        <el-icon><View /></el-icon>
                      </el-button>
                      <el-button size="small" link @click.stop="downloadFile(file)">
                        <el-icon><Download /></el-icon>
                      </el-button>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ========== 极简模式 ========== -->
      <div v-if="mode === 'simple' && items.length > 0" class="simple-wrap">
        <div
          v-for="item in items"
          :key="item.id"
          class="simple-item"
        >
          <div class="simple-item-header">
            <div class="simple-date">
              <el-icon><Clock /></el-icon>
              <span>{{ item.start_date }} ~ {{ item.end_date }}</span>
            </div>
            <div class="simple-item-actions">
              <el-button size="small" link type="primary" title="编辑进展" @click="openEditDialog(item)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button v-if="businessAuth.hasPermission('construction', 'delete')" size="small" link type="danger" title="删除进展" @click="handleDelete(item)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="simple-content">{{ item.content }}</div>
          <!-- 附件 -->
          <div v-if="item.files && item.files.length > 0" class="simple-files">
            <div v-for="(file, fi) in item.files" :key="fi" class="sfile-item">
              <template v-if="isImage(file)">
                <el-image
                  :src="file"
                  fit="cover"
                  :preview-src-list="getCardImageUrls(item.files)"
                  :initial-index="getImageIndex(item.files, fi)"
                  class="sfile-img"
                />
                <el-button size="small" link @click.stop="downloadFile(file)">
                  <el-icon><Download /></el-icon>
                </el-button>
              </template>
              <template v-else>
                <span class="sfile-doc" @click="openFile(file)">
                  <el-icon><Document /></el-icon>
                  {{ getFileName(file) }}
                </span>
                <el-button size="small" link @click.stop="downloadFile(file)">
                  <el-icon><Download /></el-icon>
                </el-button>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑/新建弹窗 -->
    <el-dialog
      v-model="editDialogVisible"
      :title="editMode === 'create' ? '新建工作进展' : '编辑工作进展'"
      width="580px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" label-position="right">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="开始日期" prop="start_date">
              <el-date-picker
                v-model="form.start_date"
                type="date"
                placeholder="选择日期"
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
                placeholder="选择日期"
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
            placeholder="请输入进展内容..."
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="附件">
          <el-upload
            v-model:file-list="editFileList"
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
              <div class="el-upload__tip">支持 PDF/DOC/PPT/XLS/图片，可上传多个</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ editMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { List, Clock, Edit, Delete, Plus, UploadFilled, ZoomIn, Download, View, Document } from '@element-plus/icons-vue'
import { getProgressList, createProgress, updateProgress, deleteProgress } from '@/api/construction'
import { useBusinessAuthStore } from '@/stores/businessAuth'

const businessAuth = useBusinessAuthStore()

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  projectId: { type: [Number, String], default: null },
  projectName: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const items = ref([])
const mode = ref('timeline')

// ---- 编辑弹窗 ----
const editDialogVisible = ref(false)
const editMode = ref('create')
const editingId = ref(null)
const saving = ref(false)
const formRef = ref(null)
const form = ref({ start_date: null, end_date: null, content: '' })
const editFileList = ref([])
const uploadUrl = '/api/upload'
const uploadHeaders = {}

const rules = {
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
  content: [{ required: true, message: '请输入进展内容', trigger: 'blur' }]
}

function resetForm() {
  form.value = { start_date: null, end_date: null, content: '' }
  editFileList.value = []
  editingId.value = null
  formRef.value?.clearValidate()
}

watch(() => props.modelValue, (val) => {
  if (val && props.projectId) {
    fetchItems()
  }
})

async function fetchItems() {
  loading.value = true
  try {
    const res = await getProgressList({ project_id: props.projectId })
    items.value = (res.data || []).sort((a, b) => {
      const da = a.start_date || ''
      const db = b.start_date || ''
      return db.localeCompare(da)
    })
  } catch {
    items.value = []
    ElMessage.error('加载工作进展失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  editMode.value = 'create'
  resetForm()
  editDialogVisible.value = true
}

function openEditDialog(item) {
  editMode.value = 'edit'
  editingId.value = item.id
  form.value = {
    start_date: item.start_date || null,
    end_date: item.end_date || null,
    content: item.content || ''
  }
  editFileList.value = (item.files || []).map((url, i) => ({
    name: url.split('/').pop() || `文件${i + 1}`,
    url
  }))
  editDialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const fileUrls = editFileList.value.filter(f => f.url).map(f => f.url)
    const data = {
      project_id: Number(props.projectId),
      start_date: form.value.start_date,
      end_date: form.value.end_date,
      content: form.value.content,
      files: fileUrls
    }

    if (editMode.value === 'create') {
      await createProgress(data)
      ElMessage.success('工作进展已创建')
    } else {
      await updateProgress(editingId.value, data)
      ElMessage.success('工作进展已更新')
    }
    editDialogVisible.value = false
    await fetchItems()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(item) {
  try {
    await ElMessageBox.confirm(
      '确定要删除这条工作进展吗？',
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteProgress(item.id)
    ElMessage.success('工作进展已删除')
    await fetchItems()
  } catch { /* cancelled */ }
}

// ---- 文件上传回调 ----
function handleUploadSuccess(res, file) {
  if (res.code === 0) file.url = res.data.url
}
function handleUploadError() {
  ElMessage.error('文件上传失败')
}
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
  const idx = editFileList.value.findIndex(f => f.url === file.url || f.uid === file.uid)
  if (idx > -1) editFileList.value.splice(idx, 1)
}

// ---- 文件工具 ----
const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']

function getFileExt(url) {
  if (!url) return '?'
  const name = url.split('?')[0]
  return (name.split('.').pop() || '?').toLowerCase()
}

function getFileName(url) {
  if (!url) return '未知文件'
  const name = url.split('?')[0].split('/').pop() || '未知文件'
  try { return decodeURIComponent(name) } catch { return name }
}

function isImage(url) {
  return IMAGE_EXTS.includes(getFileExt(url))
}

function getCardImageUrls(files) {
  return files.filter(f => isImage(f))
}

function getImageIndex(files, targetIdx) {
  const imageFiles = files.filter(f => isImage(f))
  const targetFile = files[targetIdx]
  return imageFiles.indexOf(targetFile)
}

function docColor(url) {
  const ext = getFileExt(url)
  const map = { pdf: '#ef4444', doc: '#3b82f6', docx: '#3b82f6', xls: '#22c55e', xlsx: '#22c55e', ppt: '#f97316', pptx: '#f97316' }
  return map[ext] || '#6b7280'
}

function previewFile(file, allFiles) {
  if (!isImage(file)) openFile(file)
}

function openFile(url) {
  window.open(url, '_blank')
}

function downloadFile(url) {
  const a = document.createElement('a')
  a.href = url
  a.download = getFileName(url)
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function handleClosed() {
  items.value = []
  mode.value = 'timeline'
}
</script>

<style scoped>
.drawer-title-bar {
  background: linear-gradient(135deg, #5b9bd5 0%, #8ab8e8 100%);
  margin: 0 -20px 0 -20px;
  padding: 20px 20px 20px 40px;
}
.drawer-title {
  color: #fff; font-size: 16px; font-weight: 600;
  letter-spacing: 1px; display: flex; align-items: center; gap: 8px;
}

.drawer-body { padding: 4px 0 20px; }

/* ---- 模式切换 ---- */
.mode-bar {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid #ebeef5;
}
.mode-toggle {
  display: flex; background: #f0f2f5; border-radius: 6px; padding: 3px; gap: 2px;
}
.mode-btn {
  padding: 5px 18px; font-size: 13px; border-radius: 4px;
  cursor: pointer; color: #606266; font-weight: 500;
  transition: all 0.2s; user-select: none;
}
.mode-btn:hover { color: #303133; }
.mode-btn.active {
  background: #fff; color: #1a3a5c; font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.mode-count { font-size: 12px; color: #909399; }
.mode-right { display: flex; align-items: center; gap: 14px; }

/* ---- 空状态 ---- */
.empty-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 80px 0; color: #c0c4cc;
}
.empty-icon { font-size: 56px; margin-bottom: 16px; }
.empty-state p { font-size: 14px; color: #909399; }

/* ========== 流式（时间轴） ========== */
.timeline-wrap { position: relative; padding-left: 4px; }
.timeline-item { display: flex; gap: 0; position: relative; }
.tl-node {
  position: relative; width: 32px; flex-shrink: 0;
  display: flex; flex-direction: column; align-items: center;
}
.tl-dot {
  width: 13px; height: 13px; border-radius: 50%; background: #409eff;
  border: 2.5px solid #fff; box-shadow: 0 0 0 2px #409eff;
  z-index: 1; margin-top: 22px; flex-shrink: 0;
}
.tl-line {
  width: 2px; background: #d9dde4; flex: 1; min-height: 100%; margin-top: 6px;
}
.tl-card {
  position: relative; flex: 1; min-width: 0; background: #fff;
  border: 1px solid #e8ecf1; border-radius: 10px;
  padding: 16px 20px; margin-bottom: 6px; margin-left: 12px;
  transition: box-shadow 0.25s;
}
.tl-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.tl-card:hover .card-actions { opacity: 1; }

.card-actions {
  position: absolute; top: 10px; right: 12px;
  display: flex; align-items: center; gap: 4px;
  opacity: 0; transition: opacity 0.2s;
}
.card-actions .el-button { padding: 3px 5px; font-size: 14px; }

.card-date {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 13px; color: #409eff; font-weight: 600;
  margin-bottom: 10px; padding: 2px 10px; background: #ecf5ff; border-radius: 4px;
}
.card-body {
  font-size: 14px; color: #303133; line-height: 1.75;
  white-space: pre-wrap; word-break: break-word;
}

/* ========== 极简模式 ========== */
.simple-wrap { display: flex; flex-direction: column; gap: 0; }
.simple-item { padding: 16px 0; border-bottom: 1px solid #ebeef5; }
.simple-item:first-child { padding-top: 0; }
.simple-item-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;
}
.simple-item-actions {
  display: flex; align-items: center; gap: 2px;
  opacity: 0; transition: opacity 0.2s;
}
.simple-item:hover .simple-item-actions { opacity: 1; }
.simple-date {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 13px; color: #409eff; font-weight: 600; margin-bottom: 8px;
}
.simple-content {
  font-size: 14px; color: #303133; line-height: 1.7;
  white-space: pre-wrap; word-break: break-word;
}

/* ---- 附件 ---- */
.card-files {
  margin-top: 14px; padding-top: 12px;
  border-top: 1px dashed #e4e7ed;
  display: flex; flex-wrap: wrap; gap: 10px;
}
.file-item { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.file-thumb {
  border-radius: 8px; overflow: hidden;
  border: 1px solid #ebeef5; transition: box-shadow 0.2s;
}
.file-thumb:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.file-thumb--image {
  width: 90px; height: 90px; display: flex;
  flex-direction: column; background: #fafafa;
}
.file-thumb--image .thumb-img-el { width: 90px; height: 68px; }
.file-thumb--image .thumb-img-el :deep(img) { object-fit: cover; }
.file-thumb--doc {
  width: 90px; padding: 10px 6px 6px;
  background: #fafafa; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
}
.doc-icon-wrap {
  width: 44px; height: 44px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
}
.doc-ext {
  font-size: 11px; font-weight: 700; color: #fff;
  text-transform: uppercase; letter-spacing: 0.5px;
}
.doc-name {
  font-size: 10px; color: #606266; max-width: 80px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: center;
}
.file-actions { display: flex; align-items: center; gap: 2px; }
.file-actions .el-button { padding: 2px 4px; font-size: 13px; }

/* 极简模式附件 */
.simple-files { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
.sfile-item { display: flex; align-items: center; gap: 6px; }
.sfile-img {
  width: 48px; height: 48px; border-radius: 6px;
  overflow: hidden; border: 1px solid #ebeef5; cursor: pointer;
}
.sfile-img :deep(img) { object-fit: cover; }
.sfile-doc {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; color: #409eff; cursor: pointer;
  padding: 4px 10px; background: #ecf5ff; border-radius: 4px;
  max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sfile-doc:hover { background: #d9ecff; }
</style>

<style>
.el-drawer__header { margin-bottom: 0 !important; padding: 0 !important; }
.el-drawer__body { padding: 12px 20px 20px !important; }
</style>
