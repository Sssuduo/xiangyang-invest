<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>编辑省份信息 — {{ form.region_name }}</h2>
          <el-button @click="$router.push('/admin/provinces')">返回列表</el-button>
        </div>

        <el-form :model="form" label-width="100px" class="edit-form">
          <el-form-item label="名称">
            <el-input v-model="form.region_name" disabled />
          </el-form-item>
          <el-form-item label="卡片标题">
            <el-input v-model="form.card_title" placeholder="鼠标悬停时显示的标题" />
          </el-form-item>
          <el-form-item label="卡片内容">
            <el-input
              v-model="form.card_content"
              type="textarea"
              :rows="6"
              placeholder="鼠标悬停时显示的详细内容"
            />
          </el-form-item>
          <el-form-item label="高亮">
            <el-switch v-model="form.is_highlighted" />
          </el-form-item>
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
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getAdminProvince, updateProvince } from '@/api/province'

const route = useRoute()
const router = useRouter()
const saving = ref(false)
const form = ref({})

onMounted(async () => {
  try {
    const res = await getAdminProvince(route.params.id)
    if (res.code === 0) form.value = res.data
  } catch (err) {
    ElMessage.error(err.message)
    router.push('/admin/provinces')
  }
})

async function handleSave() {
  saving.value = true
  try {
    await updateProvince(route.params.id, form.value)
    ElMessage.success('保存成功')
    router.push('/admin/provinces')
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
.admin-content { padding: 32px; max-width: 700px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
h2 { color: var(--primary-color); }
.edit-form { background: #fff; padding: 32px; border-radius: 12px; box-shadow: var(--shadow-sm); }
</style>
