<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>{{ isEdit ? '编辑提示词' : '新建提示词' }}</h2>
          <el-button @click="$router.push('/admin/prompts')">返回列表</el-button>
        </div>

        <el-form :model="form" label-width="110px" class="edit-form">
          <el-form-item label="按钮文字">
            <el-input v-model="form.button_text" placeholder="如：生成项目可行性报告" />
          </el-form-item>
          <el-form-item label="提示词模板">
            <el-input
              v-model="form.prompt_template"
              type="textarea"
              :rows="5"
              placeholder="请根据以下信息进行分析：{{user_input}}"
            />
            <div class="form-tip">
              💡 使用 <code v-pre>{{ user_input }}</code> 作为用户输入内容的占位符
            </div>
          </el-form-item>
          <el-form-item label="说明">
            <el-input v-model="form.description" placeholder="简短说明该提示词的用途" />
          </el-form-item>
          <el-form-item label="分类">
            <el-input v-model="form.category" placeholder="如：投资分析、项目评估" />
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
import { getAdminPrompt, createPrompt, updatePrompt } from '@/api/prompt'

const route = useRoute()
const router = useRouter()
const isEdit = ref(!!route.params.id)
const saving = ref(false)

const form = ref({
  button_text: '',
  prompt_template: '',
  description: '',
  category: 'general',
  is_active: true,
  sort_order: 0
})

onMounted(async () => {
  if (isEdit.value) {
    try {
      const res = await getAdminPrompt(route.params.id)
      if (res.code === 0) form.value = { ...form.value, ...res.data }
    } catch (err) {
      ElMessage.error(err.message)
      router.push('/admin/prompts')
    }
  }
})

async function handleSave() {
  saving.value = true
  try {
    if (isEdit.value) {
      await updatePrompt(route.params.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createPrompt(form.value)
      ElMessage.success('创建成功')
      router.push('/admin/prompts')
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
.form-tip { margin-top: 8px; font-size: 13px; color: var(--text-secondary); }
.form-tip code { background: #f0f0f0; padding: 1px 6px; border-radius: 3px; font-size: 12px; }
</style>
