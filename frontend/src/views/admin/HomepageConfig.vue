<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>首页配置</h2>
        </div>

        <el-form :model="form" label-width="110px" class="edit-form">
          <el-form-item label="背景图">
            <div class="bg-upload">
              <el-input v-model="form.background_image" placeholder="图片URL路径" />
              <label class="upload-label">
                <input
                  type="file"
                  accept="image/*"
                  @change="onFileSelected"
                />
                <el-button
                  type="primary"
                  :loading="uploading"
                  tag="span"
                  style="pointer-events: none; margin-left: 10px"
                >
                  上传
                </el-button>
              </label>
            </div>
            <div v-if="form.background_image" class="bg-preview">
              <img :src="form.background_image" alt="背景图预览" />
            </div>
          </el-form-item>

          <el-form-item label="主标题">
            <el-input v-model="form.title_text" placeholder="如：襄阳农高区" />
          </el-form-item>
          <el-form-item label="副标题">
            <el-input v-model="form.subtitle_text" placeholder="如：招商服务一站式平台" />
          </el-form-item>
          <el-form-item label="按钮1文字">
            <el-input v-model="form.button1_text" placeholder="如：襄阳农高区介绍" />
          </el-form-item>
          <el-form-item label="按钮2文字">
            <el-input v-model="form.button2_text" placeholder="如：招商工具箱" />
          </el-form-item>

          <el-divider content-position="left">实时预览</el-divider>
          <div class="homepage-preview" :style="previewStyle">
            <div class="preview-overlay">
              <h1 class="preview-title">{{ form.title_text || '襄阳农高区' }}</h1>
              <p class="preview-subtitle">{{ form.subtitle_text || '招商服务一站式平台' }}</p>
              <div class="preview-buttons">
                <span class="preview-btn">{{ form.button1_text || '襄阳农高区介绍' }}</span>
                <span class="preview-btn">{{ form.button2_text || '招商工具箱' }}</span>
              </div>
            </div>
          </div>

          <el-form-item style="margin-top: 24px">
            <el-button type="primary" size="large" :loading="saving" @click="handleSave">
              保 存
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getAdminHomepageConfig, updateHomepageConfig } from '@/api/homepage'
import { uploadImage } from '@/api/upload'

const form = ref({
  background_image: '',
  title_text: '襄阳农高区',
  subtitle_text: '招商服务一站式平台',
  button1_text: '襄阳农高区介绍',
  button2_text: '招商工具箱'
})

const saving = ref(false)
const uploading = ref(false)

const previewStyle = computed(() => ({
  backgroundImage: form.value.background_image
    ? `url(${form.value.background_image})`
    : 'linear-gradient(135deg, #1a3a5c, #2a5a8c)',
  backgroundSize: 'cover',
  backgroundPosition: 'center'
}))

onMounted(async () => {
  try {
    const res = await getAdminHomepageConfig()
    if (res.code === 0 && res.data) {
      form.value = res.data
    }
  } catch { /* ignore */ }
})

async function onFileSelected(e) {
  const file = e.target.files[0]
  if (!file) return

  console.log('上传文件:', file.name, `(${(file.size / 1024).toFixed(1)}KB)`)

  uploading.value = true
  try {
    const res = await uploadImage(file)
    console.log('上传响应:', res)
    if (res.code === 0) {
      form.value.background_image = res.data.url
      ElMessage.success('上传成功')
    } else {
      ElMessage.error({ message: res.message || '上传失败', duration: 8000 })
    }
  } catch (err) {
    console.error('上传异常 - 完整错误对象:', err)
    const rawMsg = err.message || String(err) || '上传失败'
    ElMessage({
      message: rawMsg,
      type: 'error',
      duration: 10000,
      showClose: true
    })
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

async function handleSave() {
  saving.value = true
  try {
    await updateHomepageConfig(form.value)
    ElMessage.success('首页配置已保存')
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: var(--bg-light); }
.admin-content { padding: 32px; max-width: 800px; }
.page-header { margin-bottom: 24px; }
h2 { color: var(--primary-color); }
.edit-form { background: #fff; padding: 32px; border-radius: 12px; box-shadow: var(--shadow-sm); }

.bg-upload { display: flex; align-items: center; width: 100%; }
.upload-label { display: inline-flex; cursor: pointer; }
.upload-label input[type="file"] { position: absolute; width: 1px; height: 1px; opacity: 0; overflow: hidden; clip: rect(0,0,0,0); }
.bg-preview { margin-top: 12px; }
.bg-preview img { max-width: 400px; max-height: 200px; border-radius: 8px; border: 1px solid var(--border-color); }

.homepage-preview {
  width: 100%;
  height: 260px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}
.preview-overlay {
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.preview-title { font-size: 32px; font-weight: 700; letter-spacing: 4px; margin-bottom: 8px; }
.preview-subtitle { font-size: 14px; opacity: 0.8; margin-bottom: 32px; }
.preview-buttons { display: flex; gap: 20px; }
.preview-btn {
  padding: 10px 28px;
  border: 2px solid rgba(255,255,255,0.6);
  border-radius: 8px;
  font-size: 14px;
  background: rgba(255,255,255,0.1);
}
</style>
