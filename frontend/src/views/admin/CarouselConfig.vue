<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>轮播设置</h2>
        </div>

        <el-form :model="form" label-width="140px" class="edit-form">
          <el-divider content-position="left">布局说明</el-divider>
          <div class="layout-note">
            <p>轮播图采用 <strong>左中右三图居中</strong> 布局：</p>
            <p>• 中间为主图（55vw / 68vh），左右两侧为虚化预览图（200px 宽）</p>
            <p>• 点击两侧虚化图或键盘 ← → 可滑动切换</p>
            <p>• 演示模式：全屏纯黑背景，仅居中展示图片（contain 防裁切），周围填充虚化氛围</p>
          </div>

          <el-divider content-position="left">自动播放速度</el-divider>

          <el-form-item label="轮播间隔">
            <el-input-number v-model="form.carousel_interval" :min="1" :max="30" :step="1" />
            <span class="unit-hint">秒（正常轮播模式下自动切换间隔，默认 8 秒）</span>
          </el-form-item>

          <el-form-item label="演示模式间隔">
            <el-input-number v-model="form.presentation_interval" :min="1" :max="30" :step="1" />
            <span class="unit-hint">秒（演示模式下自动切换间隔，默认 5 秒）</span>
          </el-form-item>

          <el-divider content-position="left">自动播放开关</el-divider>

          <el-form-item label="轮播自动播放">
            <el-switch v-model="form.carousel_autoplay" active-text="开启" inactive-text="关闭" />
            <span class="unit-hint" style="margin-left: 12px">关闭后，正常模式下不再自动切换</span>
          </el-form-item>

          <el-form-item label="演示自动播放">
            <el-switch v-model="form.presentation_autoplay" active-text="开启" inactive-text="关闭" />
            <span class="unit-hint" style="margin-left: 12px">关闭后，演示模式下不再自动切换</span>
          </el-form-item>

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
import { getAdminHomepageConfig, updateHomepageConfig } from '@/api/homepage'

const form = ref({
  carousel_interval: 8,
  presentation_interval: 5,
  carousel_autoplay: true,
  presentation_autoplay: true
})

const saving = ref(false)

onMounted(async () => {
  try {
    const res = await getAdminHomepageConfig()
    if (res.code === 0 && res.data) {
      form.value.carousel_interval = res.data.carousel_interval ?? 8
      form.value.presentation_interval = res.data.presentation_interval ?? 5
      form.value.carousel_autoplay = res.data.carousel_autoplay ?? true
      form.value.presentation_autoplay = res.data.presentation_autoplay ?? true
    }
  } catch { /* ignore */ }
})

async function handleSave() {
  saving.value = true
  try {
    await updateHomepageConfig({
      carousel_interval: form.value.carousel_interval,
      presentation_interval: form.value.presentation_interval,
      carousel_autoplay: form.value.carousel_autoplay,
      presentation_autoplay: form.value.presentation_autoplay
    })
    ElMessage.success('轮播设置已保存')
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
.admin-content { padding: 32px; max-width: 700px; }
.page-header { margin-bottom: 24px; }
h2 { color: var(--primary-color); }
.edit-form { background: #fff; padding: 32px; border-radius: 12px; box-shadow: var(--shadow-sm); }
.unit-hint { font-size: 12px; color: #909399; margin-left: 8px; }

.layout-note {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 14px 18px;
  font-size: 13px;
  color: #606266;
  line-height: 1.9;
  margin-bottom: 8px;
}
.layout-note p { margin: 2px 0; }
.layout-note strong { color: #303133; }
</style>
