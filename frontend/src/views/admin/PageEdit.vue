<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>{{ isEdit ? '编辑轮播页' : '新建轮播页' }}</h2>
          <el-button @click="$router.push('/admin/pages')">返回列表</el-button>
        </div>

        <el-form :model="form" label-width="120px" class="edit-form" :rules="formRules" ref="formRef">
          <!-- 必填：标题 -->
          <el-form-item label="页面标题" prop="title" :required="true">
            <template #label>
              <span class="required-label"><span class="required-icon">*</span> 页面标题</span>
            </template>
            <el-input v-model="form.title" placeholder="管理后台标识用，如：襄阳农高区概览" />
          </el-form-item>

          <el-form-item label="页面类型">
            <el-radio-group v-model="form.page_type">
              <el-radio value="image_text">图文页</el-radio>
              <el-radio value="map">地图页</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- 必填：排序 -->
          <el-form-item label="排序" prop="sort_order" :required="true">
            <template #label>
              <span class="required-label"><span class="required-icon">*</span> 排序</span>
            </template>
            <el-input-number v-model="form.sort_order" :min="0" />
          </el-form-item>

          <el-form-item label="启用">
            <el-switch v-model="form.is_active" />
          </el-form-item>

          <!-- 图文页配置 -->
          <template v-if="form.page_type === 'image_text'">
            <el-divider content-position="left">图文页配置</el-divider>

            <!-- 必填：背景图 -->
            <el-form-item label="背景图" prop="background_image" :required="true">
              <template #label>
                <span class="required-label"><span class="required-icon">*</span> 背景图</span>
              </template>
              <div class="bg-upload">
                <el-input v-model="form.background_image" placeholder="图片URL路径或点击上传按钮选择图片" />
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

            <!-- 文字区域位置（可选） -->
            <el-form-item label="文字区域位置">
              <div class="position-grid">
                <div class="position-item">
                  <label>左边距(%)</label>
                  <el-input-number v-model="form.text_position_x" :min="0" :max="100" :step="0.5" />
                </div>
                <div class="position-item">
                  <label>上边距(%)</label>
                  <el-input-number v-model="form.text_position_y" :min="0" :max="100" :step="0.5" />
                </div>
                <div class="position-item">
                  <label>宽度(%)</label>
                  <el-input-number v-model="form.text_width" :min="5" :max="100" :step="0.5" />
                </div>
                <div class="position-item">
                  <label>高度(%)</label>
                  <el-input-number v-model="form.text_height" :min="5" :max="100" :step="0.5" />
                </div>
              </div>
            </el-form-item>

            <!-- 文字内容（可选） -->
            <el-form-item label="文字内容">
              <div class="editor-wrapper">
                <div id="quill-editor" ref="editorRef" />
              </div>
              <span class="optional-hint">（选填）鼠标悬停时展示的文字内容</span>
            </el-form-item>
          </template>

          <!-- 地图页配置 -->
          <template v-if="form.page_type === 'map'">
            <el-divider content-position="left">地图页配置</el-divider>
            <el-form-item label="地图范围">
              <el-radio-group v-model="form.map_scope">
                <el-radio value="china">全国</el-radio>
                <el-radio value="hubei">湖北省</el-radio>
              </el-radio-group>
            </el-form-item>
          </template>

          <el-form-item>
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
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getAdminPage, getAdminPages, createPage, updatePage } from '@/api/carousel'
import { uploadImage } from '@/api/upload'
import Quill from 'quill'
import 'quill/dist/quill.snow.css'

const route = useRoute()
const router = useRouter()

const isEdit = ref(!!route.params.id)
const saving = ref(false)
const uploading = ref(false)
const editorRef = ref(null)
const formRef = ref(null)
let quillEditor = null

const form = reactive({
  title: '',
  page_type: 'image_text',
  map_scope: 'china',
  sort_order: 0,
  is_active: true,
  background_image: '',
  rich_text_content: '',
  text_position_x: 10,
  text_position_y: 10,
  text_width: 40,
  text_height: 80
})

// 校验规则：标题、排序、背景图（图文页）为必填
const formRules = computed(() => {
  const rules = {
    title: [
      { required: true, message: '请输入页面标题', trigger: 'blur' },
      { min: 1, max: 255, message: '标题长度在 1 到 255 个字符', trigger: 'blur' }
    ],
    sort_order: [
      { required: true, message: '请设置排序值', trigger: 'blur' }
    ]
  }
  if (form.page_type === 'image_text') {
    rules.background_image = [
      { required: true, message: '请上传背景图或填写图片URL', trigger: 'blur' }
    ]
  }
  return rules
})

onMounted(async () => {
  if (isEdit.value) {
    try {
      const res = await getAdminPage(route.params.id)
      if (res.code === 0) {
        Object.assign(form, res.data)
      }
    } catch (err) {
      ElMessage.error(err.message)
      router.push('/admin/pages')
    }
  } else {
    // 新建页：计算默认排序值 = 最大排序值 + 1
    try {
      const res = await getAdminPages()
      if (res.code === 0 && res.data && res.data.length > 0) {
        const maxOrder = Math.max(...res.data.map(p => p.sort_order))
        form.sort_order = maxOrder + 1
      }
    } catch { /* 获取失败则保持默认值 0 */ }
  }

  // 初始化 Quill 编辑器
  await nextTick()
  if (form.page_type === 'image_text') {
    initQuill()
  }
})

function initQuill() {
  if (quillEditor) return

  const toolbarOptions = [
    [{ header: [1, 2, 3, false] }],
    ['bold', 'italic', 'underline', 'strike'],
    [{ color: [] }, { background: [] }],
    [{ align: [] }],
    [{ list: 'ordered' }, { list: 'bullet' }],
    ['blockquote', 'code-block'],
    ['link', 'image'],
    ['clean']
  ]

  quillEditor = new Quill('#quill-editor', {
    theme: 'snow',
    modules: { toolbar: toolbarOptions },
    placeholder: '请输入文字内容...'
  })

  if (form.rich_text_content) {
    quillEditor.root.innerHTML = form.rich_text_content
  }

  quillEditor.on('text-change', () => {
    form.rich_text_content = quillEditor.root.innerHTML
  })
}

async function onFileSelected(e) {
  const file = e.target.files[0]
  if (!file) return

  console.log('上传文件:', file.name, `(${(file.size / 1024).toFixed(1)}KB)`)

  uploading.value = true
  try {
    const res = await uploadImage(file)
    console.log('上传响应:', res)
    if (res.code === 0) {
      form.background_image = res.data.url
      ElMessage.success('上传成功')
    } else {
      ElMessage.error({ message: res.message || '上传失败', duration: 8000 })
    }
  } catch (err) {
    console.error('上传异常 - 完整错误对象:', err)
    // 使用 ElNotification 显示长错误信息，避免被截断
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
  // 表单校验
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    ElMessage.warning('请填写所有必填项后再保存')
    return
  }

  saving.value = true
  try {
    const data = { ...form }
    // 传入 quill 最新内容
    if (quillEditor) {
      data.rich_text_content = quillEditor.root.innerHTML
    }
    if (isEdit.value) {
      await updatePage(route.params.id, data)
      ElMessage.success('更新成功')
    } else {
      await createPage(data)
      ElMessage.success('创建成功')
      router.push('/admin/pages')
    }
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: var(--bg-light); }
.admin-content { padding: 32px; max-width: 900px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
h2 { color: var(--primary-color); }

.required-label { display: inline-flex; align-items: center; }
.required-icon { color: #f56c6c; margin-right: 4px; font-weight: bold; font-size: 14px; }
.optional-hint { font-size: 12px; color: #909399; margin-top: 4px; display: inline-block; }

.edit-form {
  background: #fff;
  padding: 32px;
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
}

.bg-upload {
  display: flex;
  align-items: center;
  width: 100%;
}

/* 上传按钮 — 用 label 包裹隐藏的原生 input */
.upload-label {
  display: inline-flex;
  cursor: pointer;
  margin-left: 10px;
}
.upload-label input[type="file"] {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  overflow: hidden;
  clip: rect(0,0,0,0);
}
.bg-preview {
  margin-top: 12px;
}
.bg-preview img {
  max-width: 400px;
  max-height: 200px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.position-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  width: 100%;
}
.position-item label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.editor-wrapper {
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}
#quill-editor {
  min-height: 250px;
}
</style>
