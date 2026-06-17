<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>提示词管理</h2>
          <el-button type="primary" @click="$router.push('/admin/prompts/new')">新建提示词</el-button>
        </div>

        <el-table :data="prompts" stripe style="width: 100%; margin-top: 20px">
          <el-table-column prop="button_text" label="按钮文字" width="200" />
          <el-table-column prop="prompt_template" label="提示词模板" min-width="300">
            <template #default="{ row }">
              <div class="template-preview">{{ row.prompt_template }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="category" label="分类" width="100" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-switch
                :model-value="row.is_active"
                @change="(val) => toggleActive(row, val)"
                size="small"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button size="small" @click="$router.push(`/admin/prompts/${row.id}/edit`)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="prompts.length === 0" class="empty-state">暂无提示词</div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getAdminPrompts, updatePrompt, deletePrompt } from '@/api/prompt'

const prompts = ref([])

async function loadPrompts() {
  try {
    const res = await getAdminPrompts()
    if (res.code === 0) prompts.value = res.data || []
  } catch { /* ignore */ }
}

async function toggleActive(prompt, val) {
  try {
    await updatePrompt(prompt.id, { is_active: val })
    prompt.is_active = val
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch (err) {
    ElMessage.error(err.message)
  }
}

async function handleDelete(prompt) {
  try {
    await ElMessageBox.confirm(`确定删除"${prompt.button_text}"吗？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deletePrompt(prompt.id)
    ElMessage.success('删除成功')
    await loadPrompts()
  } catch { /* cancelled */ }
}

onMounted(loadPrompts)
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: var(--bg-light); }
.admin-content { padding: 32px; max-width: 1100px; }
.page-header { display: flex; justify-content: space-between; align-items: center; }
h2 { color: var(--primary-color); }
.template-preview { font-size: 13px; color: var(--text-secondary); max-height: 48px; overflow: hidden; }
.empty-state { text-align: center; padding: 60px 0; color: var(--text-secondary); }
</style>
