<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>宣传视频管理</h2>
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 添加视频
          </el-button>
        </div>

        <!-- 视频列表 -->
        <el-table :data="videos" row-key="id" v-loading="loading" empty-text="暂无视频">
          <el-table-column label="序号" width="70" align="center">
            <template #default="{ row }">{{ row.sort_order }}</template>
          </el-table-column>
          <el-table-column label="标题" min-width="200">
            <template #default="{ row }">
              <span class="video-title-link" @click="handlePreview(row)">{{ row.title }}</span>
            </template>
          </el-table-column>
          <el-table-column label="视频文件" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">{{ row.file_path }}</template>
          </el-table-column>
          <el-table-column label="文件大小" width="100" align="center">
            <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="260" align="center">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="handlePreview(row)">预览</el-button>
              <el-button size="small" link type="success" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" link type="warning" @click="moveUp(row)" :disabled="row.sort_order <= 1">
                <el-icon><Top /></el-icon>
              </el-button>
              <el-button size="small" link type="warning" @click="moveDown(row)" :disabled="row.sort_order >= videos.length">
                <el-icon><Bottom /></el-icon>
              </el-button>
              <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </main>

    <!-- 添加 / 编辑 对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑视频' : '添加视频'"
      width="560px"
      :close-on-click-modal="false"
      append-to-body
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" label-position="top">
        <el-form-item label="视频标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入视频标题" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="视频文件" prop="file_path">
          <el-upload
            ref="uploadRef"
            class="video-upload"
            drag
            :action="uploadAction"
            :auto-upload="true"
            :limit="1"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            :file-list="uploadFileList"
            accept="video/mp4,video/webm,video/ogg,video/avi,video/mov,video/mkv,video/wmv,video/flv"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽视频文件到此处，或 <em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 MP4 / WebM / MOV / AVI / MKV 等常见视频格式</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>

      <!-- 已上传视频预览 -->
      <div v-if="form.file_path" class="upload-preview">
        <video :src="form.file_path" controls class="preview-video">
          您的浏览器不支持视频播放
        </video>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      title="视频预览"
      width="720px"
      append-to-body
    >
      <div v-if="previewVideo" class="preview-wrapper">
        <video :src="previewVideo.file_path" controls autoplay class="preview-video-large">
          您的浏览器不支持视频播放
        </video>
        <p class="preview-title-text">{{ previewVideo.title }}</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { Plus, UploadFilled, Top, Bottom } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getManageVideos, createVideo, updateVideo, deleteVideo } from '@/api/promo_video'

const loading = ref(false)
const videos = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const submitting = ref(false)
const formRef = ref(null)
const uploadRef = ref(null)

const uploadAction = '/api/upload'
const uploadFileList = ref([])

const form = reactive({
  title: '',
  file_path: ''
})

const rules = {
  title: [{ required: true, message: '请输入视频标题', trigger: 'blur' }],
  file_path: [{ required: true, message: '请上传视频文件', trigger: 'change' }]
}

// 预览
const previewVisible = ref(false)
const previewVideo = ref(null)

onMounted(() => {
  fetchVideos()
})

async function fetchVideos() {
  loading.value = true
  try {
    const res = await getManageVideos()
    if (res.data.code === 0) {
      videos.value = res.data.data
    }
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editId.value = null
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editId.value = row.id
  form.title = row.title
  form.file_path = row.file_path
  if (row.file_path) {
    uploadFileList.value = [{ name: row.file_path.split('/').pop() || 'video', url: row.file_path }]
  }
  dialogVisible.value = true
}

function resetForm() {
  form.title = ''
  form.file_path = ''
  uploadFileList.value = []
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

function beforeUpload(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  const allowed = ['mp4', 'webm', 'ogg', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'm4v']
  if (!allowed.includes(ext)) {
    ElMessage.error(`不支持的视频格式：.${ext}`)
    return false
  }
  return true
}

function handleUploadSuccess(response) {
  if (response.code === 0) {
    form.file_path = response.data.url
    ElMessage.success('视频上传成功')
  } else {
    ElMessage.error(response.message || '上传失败')
  }
}

function handleUploadError() {
  ElMessage.error('视频上传失败，请重试')
}

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  if (!form.file_path) {
    ElMessage.warning('请上传视频文件')
    return
  }

  submitting.value = true
  try {
    const data = { title: form.title, file_path: form.file_path }
    if (isEdit.value) {
      await updateVideo(editId.value, data)
      ElMessage.success('已更新')
    } else {
      await createVideo(data)
      ElMessage.success('已添加')
    }
    dialogVisible.value = false
    fetchVideos()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除视频「${row.title}」吗？此操作不可恢复。`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  try {
    await deleteVideo(row.id)
    ElMessage.success('已删除')
    fetchVideos()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '删除失败')
  }
}

async function moveUp(row) {
  const idx = videos.value.findIndex(v => v.id === row.id)
  if (idx <= 0) return
  const prev = videos.value[idx - 1]
  // 交换 sort_order
  const tmp = row.sort_order
  row.sort_order = prev.sort_order
  prev.sort_order = tmp
  await saveSort()
}

async function moveDown(row) {
  const idx = videos.value.findIndex(v => v.id === row.id)
  if (idx < 0 || idx >= videos.value.length - 1) return
  const next = videos.value[idx + 1]
  const tmp = row.sort_order
  row.sort_order = next.sort_order
  next.sort_order = tmp
  await saveSort()
}

async function saveSort() {
  const data = videos.value.map(v => ({ id: v.id, sort_order: v.sort_order }))
  try {
    const { sortVideos } = await import('@/api/promo_video')
    await sortVideos(data)
    fetchVideos()
  } catch (e) {
    ElMessage.error('排序失败')
  }
}

function formatFileSize(bytes) {
  if (bytes == null || bytes < 0) return '-'
  const gb = bytes / (1024 * 1024 * 1024)
  if (gb >= 1) {
    return gb.toFixed(2) + ' GB'
  }
  const mb = bytes / (1024 * 1024)
  return mb.toFixed(2) + ' MB'
}

function handlePreview(row) {
  previewVideo.value = row
  previewVisible.value = true
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}
.admin-main {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
}
.admin-content {
  padding: 24px;
  max-width: 1200px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1a3a5c;
}

.video-title-link {
  color: #409eff;
  cursor: pointer;
}
.video-title-link:hover {
  text-decoration: underline;
}

.video-upload {
  width: 100%;
}

.upload-preview {
  margin-top: 12px;
}
.preview-video {
  width: 100%;
  max-height: 260px;
  border-radius: 6px;
  background: #000;
}

.preview-wrapper {
  text-align: center;
}
.preview-video-large {
  width: 100%;
  max-height: 420px;
  border-radius: 8px;
  background: #000;
}
.preview-title-text {
  margin-top: 12px;
  font-size: 15px;
  color: #333;
  font-weight: 500;
}
</style>
