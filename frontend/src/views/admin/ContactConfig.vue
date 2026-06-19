<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>联系我们 — 名片配置</h2>
          <p class="page-desc">配置前台"联系我们"页面展示的个人名片信息</p>
        </div>

        <el-form :model="form" label-width="120px" class="edit-form">
          <el-form-item label="姓名">
            <el-input v-model="form.name" placeholder="如：张经理" maxlength="64" />
          </el-form-item>

          <el-form-item label="职务">
            <el-input v-model="form.title" placeholder="如：招商部负责人" maxlength="128" />
          </el-form-item>

          <el-form-item label="联系电话">
            <el-input v-model="form.phone" placeholder="如：138-0000-0000" maxlength="32" />
          </el-form-item>

          <el-form-item label="电子邮箱">
            <el-input v-model="form.email" placeholder="如：zhang@example.com" maxlength="255" />
          </el-form-item>

          <el-form-item label="个人介绍">
            <el-input
              v-model="form.intro"
              type="textarea"
              :rows="4"
              placeholder="简要介绍个人信息、负责领域等"
              maxlength="1000"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="微信二维码">
            <div class="qr-upload">
              <el-input v-model="form.wechat_qr_image" placeholder="图片URL路径" />
              <label class="upload-label">
                <input
                  type="file"
                  accept="image/*"
                  @change="onQRSelected"
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
            <div v-if="form.wechat_qr_image" class="qr-preview">
              <img :src="form.wechat_qr_image" alt="二维码预览" />
            </div>
          </el-form-item>

          <el-divider content-position="left">名片预览</el-divider>
          <div class="card-preview">
            <div class="mini-card">
              <div class="mini-avatar">{{ form.name ? form.name.charAt(0) : '联' }}</div>
              <div class="mini-name">{{ form.name || '未设置' }}</div>
              <div class="mini-title">{{ form.title || '未设置职务' }}</div>
              <div class="mini-divider" />
              <div v-if="form.phone" class="mini-contact">📞 {{ form.phone }}</div>
              <div v-if="form.email" class="mini-contact">📧 {{ form.email }}</div>
              <div v-if="form.intro" class="mini-intro">{{ form.intro }}</div>
              <img v-if="form.wechat_qr_image" :src="form.wechat_qr_image" class="mini-qr" alt="" />
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
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getAdminContactInfo, updateContactInfo } from '@/api/contact'
import { uploadImage } from '@/api/upload'

const form = ref({
  name: '',
  title: '',
  phone: '',
  email: '',
  intro: '',
  wechat_qr_image: ''
})

const saving = ref(false)
const uploading = ref(false)

onMounted(async () => {
  try {
    const res = await getAdminContactInfo()
    if (res.code === 0 && res.data) {
      form.value = res.data
    }
  } catch { /* ignore */ }
})

async function onQRSelected(e) {
  const file = e.target.files[0]
  if (!file) return
  uploading.value = true
  try {
    const res = await uploadImage(file)
    if (res.code === 0) {
      form.value.wechat_qr_image = res.data.url
      ElMessage.success('上传成功')
    } else {
      ElMessage.error(res.message || '上传失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '上传失败')
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

async function handleSave() {
  saving.value = true
  try {
    await updateContactInfo(form.value)
    ElMessage.success('联系我们配置已保存')
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
.admin-content { padding: 32px; max-width: 760px; }
.page-header { margin-bottom: 24px; }
h2 { color: var(--primary-color); margin-bottom: 4px; }
.page-desc { color: #909399; font-size: 13px; margin: 0; }
.edit-form { background: #fff; padding: 32px; border-radius: 12px; box-shadow: var(--shadow-sm); }

.qr-upload { display: flex; align-items: center; width: 100%; }
.upload-label { display: inline-flex; cursor: pointer; }
.upload-label input[type="file"] { position: absolute; width: 1px; height: 1px; opacity: 0; overflow: hidden; clip: rect(0,0,0,0); }
.qr-preview { margin-top: 12px; }
.qr-preview img { width: 120px; height: 120px; object-fit: contain; border-radius: 8px; border: 1px solid var(--border-color); }

/* 名片预览 */
.card-preview {
  background: #f7f8fa; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 28px; display: flex; justify-content: center;
}
.mini-card {
  background: #fff; border-radius: 14px; padding: 28px 32px 24px;
  box-shadow: 0 1px 12px rgba(0,0,0,0.06);
  display: flex; flex-direction: column; align-items: center;
  text-align: center; max-width: 300px;
}
.mini-avatar {
  width: 56px; height: 56px; border-radius: 50%;
  background: linear-gradient(135deg, #1a3a5c, #2a5a8c);
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 24px; font-weight: 700;
  margin-bottom: 12px;
}
.mini-name { font-size: 18px; font-weight: 700; color: #1a202c; margin-bottom: 2px; }
.mini-title { font-size: 12px; color: #a0aec0; margin-bottom: 12px; }
.mini-divider { width: 32px; height: 1px; background: #e2e8f0; margin-bottom: 12px; }
.mini-contact { font-size: 12px; color: #718096; margin-bottom: 4px; }
.mini-intro { font-size: 11px; color: #a0aec0; line-height: 1.6; margin-top: 8px; text-align: left; }
.mini-qr { width: 64px; height: 64px; object-fit: contain; margin-top: 12px; border-radius: 6px; border: 1px solid #e2e8f0; padding: 3px; }
</style>
