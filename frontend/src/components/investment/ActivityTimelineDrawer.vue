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
          <el-icon><ChatLineSquare /></el-icon>
          项目动态 · {{ projectName }}
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
            <el-icon><Plus /></el-icon> 新建动态
          </el-button>
          <span v-if="activities.length > 0" class="mode-count">共 {{ activities.length }} 条</span>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!loading && activities.length === 0" class="empty-state">
        <el-icon class="empty-icon"><ChatLineSquare /></el-icon>
        <p>暂无项目动态</p>
      </div>

      <!-- ==================== 流式（时间轴）模式 ==================== -->
      <div v-if="mode === 'timeline' && activities.length > 0" class="timeline-wrap">
        <div
          v-for="(act, ai) in activities"
          :key="act.id"
          class="timeline-item"
        >
          <!-- 时间轴节点 -->
          <div class="tl-node">
            <div class="tl-dot" />
            <div v-if="ai < activities.length - 1" class="tl-line" />
          </div>
          <!-- 卡片内容 -->
          <div class="tl-card">
            <div class="card-actions">
              <el-button size="small" link type="primary" title="编辑动态" @click="openEditDialog(act)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button size="small" link type="danger" title="删除动态" @click="handleDeleteAct(act)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div class="card-date">
              <el-icon><Clock /></el-icon>
              <span>{{ act.date || act.created_at?.slice(0, 10) || '-' }}</span>
            </div>
            <div class="card-body">{{ act.content }}</div>
            <!-- 附件 -->
            <div v-if="act.files && act.files.length > 0" class="card-files">
              <div
                v-for="(file, fi) in act.files"
                :key="fi"
                class="file-item"
              >
                <!-- 图片缩略图 -->
                <template v-if="isImage(file)">
                  <div class="file-thumb file-thumb--image">
                    <el-image
                      :src="file"
                      fit="cover"
                      :preview-src-list="getCardImageUrls(act.files)"
                      :initial-index="getImageIndex(act.files, fi)"
                      class="thumb-img-el"
                    />
                    <div class="file-actions">
                      <el-button size="small" link @click.stop="previewFile(file, act.files)">
                        <el-icon><ZoomIn /></el-icon>
                      </el-button>
                      <el-button size="small" link @click.stop="downloadFile(file)">
                        <el-icon><Download /></el-icon>
                      </el-button>
                    </div>
                  </div>
                </template>
                <!-- 文档缩略图 -->
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

      <!-- ==================== 极简模式 ==================== -->
      <div v-if="mode === 'simple' && activities.length > 0" class="simple-wrap">
        <div
          v-for="act in activities"
          :key="act.id"
          class="simple-item"
        >
          <div class="simple-item-header">
            <div class="simple-date">
              <el-icon><Clock /></el-icon>
              <span>{{ act.date || act.created_at?.slice(0, 10) || '-' }}</span>
            </div>
            <div class="simple-item-actions">
              <el-button size="small" link type="primary" title="编辑动态" @click="openEditDialog(act)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button size="small" link type="danger" title="删除动态" @click="handleDeleteAct(act)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="simple-content">{{ act.content }}</div>
          <!-- 附件 -->
          <div v-if="act.files && act.files.length > 0" class="simple-files">
            <div
              v-for="(file, fi) in act.files"
              :key="fi"
              class="sfile-item"
            >
              <template v-if="isImage(file)">
                <el-image
                  :src="file"
                  fit="cover"
                  :preview-src-list="getCardImageUrls(act.files)"
                  :initial-index="getImageIndex(act.files, fi)"
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

    <!-- 编辑/新建动态弹窗 -->
    <el-dialog
      v-model="editDialogVisible"
      :title="editMode === 'create' ? '新建动态' : '编辑动态'"
      width="580px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" label-width="80px" label-position="right">
        <el-form-item label="日期">
          <el-date-picker
            v-model="form.date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
          />
        </el-form-item>
        <el-form-item label="动态内容" prop="content" :rules="[{ required: true, message: '请输入动态内容', trigger: 'blur' }]">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="6"
            placeholder="请输入动态内容..."
            maxlength="5000"
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
        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple placeholder="请选择标签" style="width: 100%;">
            <el-option v-for="d in activityTags" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
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
import { ref, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatLineSquare, Clock, ZoomIn, Download, View, Document, Edit, Delete, Plus, UploadFilled } from '@element-plus/icons-vue'
import { getPublicActivities, createActivity, updateActivity, deleteActivity } from '@/api/activity'
import { getDictItems } from '@/api/dict'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  projectId: { type: [Number, String], default: null },
  projectName: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const activities = ref([])
const mode = ref('timeline') // 'timeline' | 'simple'

// ---- 编辑弹窗 ----
const editDialogVisible = ref(false)
const editMode = ref('create') // 'create' | 'edit'
const editingId = ref(null)
const saving = ref(false)
const formRef = ref(null)
const form = ref({ date: '', content: '', tags: [] })
const editFileList = ref([])
const uploadUrl = '/api/upload'
const uploadHeaders = {}
const activityTags = ref([])

async function loadActivityTags() {
  try {
    const res = await getDictItems('activity_tags')
    if (res.code === 0) activityTags.value = res.data || []
  } catch { /* ignore */ }
}

function resetForm() {
  form.value = { date: '', content: '', tags: [] }
  editFileList.value = []
  editingId.value = null
  formRef.value?.clearValidate()
}

watch(() => props.modelValue, (val) => {
  if (val && props.projectId) {
    loadActivityTags()
    fetchActivities()
  }
})

async function fetchActivities() {
  loading.value = true
  try {
    const res = await getPublicActivities({ project_id: props.projectId })
    activities.value = (res.data || []).sort((a, b) => {
      // 倒序：最新的在前
      const da = a.date || a.created_at || ''
      const db = b.date || b.created_at || ''
      return db.localeCompare(da)
    })
  } catch {
    activities.value = []
    ElMessage.error('加载项目动态失败')
  } finally {
    loading.value = false
  }
}

// ---- 新建 ----
function openCreateDialog() {
  editMode.value = 'create'
  resetForm()
  loadActivityTags()
  editDialogVisible.value = true
}

// ---- 编辑 ----
function openEditDialog(act) {
  editMode.value = 'edit'
  editingId.value = act.id
  form.value = {
    date: act.date || '',
    content: act.content || '',
    tags: Array.isArray(act.tags) ? [...act.tags] : []
  }
  editFileList.value = (act.files || []).map((url, i) => ({
    name: url.split('/').pop() || `文件${i + 1}`,
    url
  }))
  editDialogVisible.value = true
}

// ---- 保存 ----
async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const docUrls = editFileList.value.filter(f => f.url).map(f => f.url)
    const data = {
      project_id: Number(props.projectId),
      date: form.value.date || null,
      content: form.value.content,
      files: docUrls,
      tags: form.value.tags
    }

    if (editMode.value === 'create') {
      await createActivity(data)
      ElMessage.success('动态已创建')
    } else {
      await updateActivity(editingId.value, data)
      ElMessage.success('动态已更新')
    }
    editDialogVisible.value = false
    await fetchActivities()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

// ---- 删除 ----
async function handleDeleteAct(act) {
  try {
    await ElMessageBox.confirm(
      `确定要删除这条动态吗？`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteActivity(act.id)
    ElMessage.success('动态已删除')
    await fetchActivities()
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

function handleClosed() {
  activities.value = []
  mode.value = 'timeline'
}

// ---- 文件工具 ----
const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']

function getFileExt(url) {
  if (!url) return '?'
  const name = url.split('?')[0] // 去掉查询参数
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
  // 在 files 数组中，图片在完整列表中的位置映射到 image-only 列表中的位置
  const imageFiles = files.filter(f => isImage(f))
  const targetFile = files[targetIdx]
  return imageFiles.indexOf(targetFile)
}

function docColor(url) {
  const ext = getFileExt(url)
  const map = {
    pdf: '#ef4444',
    doc: '#3b82f6',
    docx: '#3b82f6',
    xls: '#22c55e',
    xlsx: '#22c55e',
    ppt: '#f97316',
    pptx: '#f97316'
  }
  return map[ext] || '#6b7280'
}

// ---- 文件操作 ----
function previewFile(file, allFiles) {
  // el-image 已经处理了图片预览，这里主要处理文档
  if (!isImage(file)) {
    openFile(file)
  }
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
</script>

<style scoped>
/* ---- 抽屉标题 ---- */
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

.drawer-body {
  padding: 4px 0 20px;
}

/* ---- 模式切换 ---- */
.mode-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}
.mode-toggle {
  display: flex;
  background: #f0f2f5;
  border-radius: 6px;
  padding: 3px;
  gap: 2px;
}
.mode-btn {
  padding: 5px 18px;
  font-size: 13px;
  border-radius: 4px;
  cursor: pointer;
  color: #606266;
  font-weight: 500;
  transition: all 0.2s;
  user-select: none;
}
.mode-btn:hover {
  color: #303133;
}
.mode-btn.active {
  background: #fff;
  color: #1a3a5c;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.mode-count {
  font-size: 12px;
  color: #909399;
}
.mode-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

/* ---- 空状态 ---- */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #c0c4cc;
}
.empty-icon { font-size: 56px; margin-bottom: 16px; }
.empty-state p { font-size: 14px; color: #909399; }

/* ==================== 流式（时间轴） ==================== */
.timeline-wrap {
  position: relative;
  padding-left: 4px;
}

.timeline-item {
  display: flex;
  gap: 0;
  position: relative;
}

/* 时间轴节点列 */
.tl-node {
  position: relative;
  width: 32px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.tl-dot {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: #409eff;
  border: 2.5px solid #fff;
  box-shadow: 0 0 0 2px #409eff;
  z-index: 1;
  margin-top: 22px;
  flex-shrink: 0;
}

.tl-line {
  width: 2px;
  background: #d9dde4;
  flex: 1;
  min-height: 100%;
  margin-top: 6px;
}

/* 卡片 */
.tl-card {
  position: relative;
  flex: 1;
  min-width: 0;
  background: #fff;
  border: 1px solid #e8ecf1;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 6px;
  margin-left: 12px;
  transition: box-shadow 0.25s;
}
.tl-card:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.tl-card:hover .card-actions {
  opacity: 1;
}

.card-actions {
  position: absolute;
  top: 10px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}
.card-actions .el-button {
  padding: 3px 5px;
  font-size: 14px;
}

.card-date {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #409eff;
  font-weight: 600;
  margin-bottom: 10px;
  padding: 2px 10px;
  background: #ecf5ff;
  border-radius: 4px;
}

.card-body {
  font-size: 14px;
  color: #303133;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ---- 附件 ---- */
.card-files {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #e4e7ed;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.file-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

/* 缩略图容器 */
.file-thumb {
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #ebeef5;
  transition: box-shadow 0.2s;
}
.file-thumb:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* 图片缩略图 */
.file-thumb--image {
  width: 90px;
  height: 90px;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}
.file-thumb--image .thumb-img-el {
  width: 90px;
  height: 68px;
}
.file-thumb--image .thumb-img-el :deep(img) {
  object-fit: cover;
}

/* 文档缩略图 */
.file-thumb--doc {
  width: 90px;
  padding: 10px 6px 6px;
  background: #fafafa;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.doc-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.doc-ext {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.doc-name {
  font-size: 10px;
  color: #606266;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}

/* 文件操作按钮 */
.file-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}
.file-actions .el-button {
  padding: 2px 4px;
  font-size: 13px;
}

/* ==================== 极简模式 ==================== */
.simple-wrap {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.simple-item {
  padding: 16px 0;
  border-bottom: 1px solid #ebeef5;
}
.simple-item:first-child {
  padding-top: 0;
}

.simple-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.simple-item-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}
.simple-item:hover .simple-item-actions {
  opacity: 1;
}

.simple-date {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #409eff;
  font-weight: 600;
  margin-bottom: 8px;
}

.simple-content {
  font-size: 14px;
  color: #303133;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: 10px;
}

.simple-files {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.sfile-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sfile-img {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #ebeef5;
  cursor: pointer;
}
.sfile-img :deep(img) {
  object-fit: cover;
}

.sfile-doc {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #409eff;
  cursor: pointer;
  padding: 4px 10px;
  background: #ecf5ff;
  border-radius: 4px;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sfile-doc:hover {
  background: #d9ecff;
}
</style>
