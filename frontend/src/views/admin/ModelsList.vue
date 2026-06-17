<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>大模型管理</h2>
          <el-button type="primary" @click="$router.push('/admin/models/new')">新建模型</el-button>
        </div>

        <el-table :data="models" stripe style="width: 100%; margin-top: 20px">
          <el-table-column prop="name" label="名称" width="160" />
          <el-table-column prop="provider" label="厂商" width="100" />
          <el-table-column prop="model_name" label="模型名" width="180" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-switch
                :model-value="row.is_active"
                @change="(val) => toggleActive(row, val)"
                size="small"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="300">
            <template #default="{ row }">
              <el-button size="small" @click="$router.push(`/admin/models/${row.id}/edit`)">编辑</el-button>
              <el-button size="small" @click="handleTest(row)" :loading="testingId === row.id">测试</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="models.length === 0" class="empty-state">暂无大模型配置</div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getAdminModels, updateModel, deleteModel, testModel } from '@/api/model'

const models = ref([])
const testingId = ref(null)

async function loadModels() {
  try {
    const res = await getAdminModels()
    if (res.code === 0) models.value = res.data || []
  } catch { /* ignore */ }
}

async function toggleActive(model, val) {
  try {
    await updateModel(model.id, { is_active: val })
    model.is_active = val
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch (err) {
    ElMessage.error(err.message)
  }
}

async function handleTest(model) {
  testingId.value = model.id
  try {
    const res = await testModel(model.id)
    ElMessage.success(res.message || '连接测试成功')
  } catch (err) {
    ElMessage.error(err.message || '连接测试失败')
  } finally {
    testingId.value = null
  }
}

async function handleDelete(model) {
  try {
    await ElMessageBox.confirm(`确定删除"${model.name}"吗？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deleteModel(model.id)
    ElMessage.success('删除成功')
    await loadModels()
  } catch { /* cancelled */ }
}

onMounted(loadModels)
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: var(--bg-light); }
.admin-content { padding: 32px; max-width: 1100px; }
.page-header { display: flex; justify-content: space-between; align-items: center; }
h2 { color: var(--primary-color); }
.empty-state { text-align: center; padding: 60px 0; color: var(--text-secondary); }
</style>
