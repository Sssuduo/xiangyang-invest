<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>{{ isEdit ? '编辑大模型' : '新建大模型' }}</h2>
          <el-button @click="$router.push('/admin/models')">返回列表</el-button>
        </div>

        <el-form :model="form" label-width="110px" class="edit-form">
          <el-form-item label="显示名称">
            <el-input v-model="form.name" placeholder="如：DeepSeek V3" />
          </el-form-item>
          <el-form-item label="厂商">
            <el-select v-model="form.provider" placeholder="选择厂商">
              <el-option label="OpenAI" value="openai" />
              <el-option label="DeepSeek" value="deepseek" />
              <el-option label="智谱AI" value="zhipu" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </el-form-item>
          <el-form-item label="API 地址">
            <el-input v-model="form.api_base_url" placeholder="https://api.deepseek.com/v1" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="form.api_key" type="password" show-password placeholder="sk-..." />
          </el-form-item>
          <el-form-item label="模型名">
            <el-input v-model="form.model_name" placeholder="如：deepseek-chat" />
          </el-form-item>
          <el-form-item label="Temperature">
            <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" :precision="1" />
          </el-form-item>
          <el-form-item label="Max Tokens">
            <el-input-number v-model="form.max_tokens" :min="100" :max="128000" :step="100" />
          </el-form-item>
          <el-form-item label="系统提示词">
            <el-input v-model="form.system_prompt" type="textarea" :rows="3" placeholder="可选" />
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.is_active" />
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="form.sort_order" :min="0" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="large" :loading="saving" @click="handleSave">保 存</el-button>
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
import { getAdminModel, createModel, updateModel } from '@/api/model'

const route = useRoute()
const router = useRouter()
const isEdit = ref(!!route.params.id)
const saving = ref(false)

const form = ref({
  name: '',
  provider: 'custom',
  api_base_url: '',
  api_key: '',
  model_name: '',
  temperature: 0.7,
  max_tokens: 4096,
  system_prompt: '',
  is_active: true,
  sort_order: 0
})

onMounted(async () => {
  if (isEdit.value) {
    try {
      const res = await getAdminModel(route.params.id)
      if (res.code === 0) form.value = { ...form.value, ...res.data }
    } catch (err) {
      ElMessage.error(err.message)
      router.push('/admin/models')
    }
  }
})

async function handleSave() {
  saving.value = true
  try {
    if (isEdit.value) {
      await updateModel(route.params.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createModel(form.value)
      ElMessage.success('创建成功')
      router.push('/admin/models')
    }
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
