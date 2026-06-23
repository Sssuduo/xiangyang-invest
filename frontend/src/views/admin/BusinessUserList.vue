<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>用户管理</h2>
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 新建用户
          </el-button>
        </div>

        <el-table :data="users" stripe row-key="id" v-loading="loading" empty-text="暂无业务用户">
          <el-table-column label="用户名" width="160">
            <template #default="{ row }">{{ row.username }}</template>
          </el-table-column>
          <el-table-column label="显示名称" width="160">
            <template #default="{ row }">{{ row.display_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                {{ row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="权限概览" min-width="280">
            <template #default="{ row }">
              <div class="perm-summary">
                <template v-for="mod in modules" :key="mod.key">
                  <span v-if="row.permissions?.[mod.key]" class="perm-module">
                    <span class="perm-module-name">{{ mod.label }}</span>
                    <span v-if="row.permissions[mod.key].edit" class="perm-tag">编辑</span>
                    <span v-if="row.permissions[mod.key].delete" class="perm-tag">删除</span>
                    <span v-if="row.permissions[mod.key].batch_delete" class="perm-tag">批量删</span>
                    <span v-if="!row.permissions[mod.key].edit && !row.permissions[mod.key].delete && !row.permissions[mod.key].batch_delete" class="perm-tag perm-none">无</span>
                  </span>
                </template>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" align="center">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </main>

    <!-- 新建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新建用户'"
      width="600px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" placeholder="请输入用户名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="显示名称" prop="display_name">
              <el-input v-model="form.display_name" placeholder="请输入显示名称" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="isEdit ? '新密码（留空则不修改）' : '密码'" :prop="isEdit ? '' : 'password'">
              <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用状态">
              <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 按钮权限配置 -->
        <el-divider content-position="left">按钮权限配置</el-divider>
        <div class="perm-config">
          <div v-for="mod in modules" :key="mod.key" class="perm-module-row">
            <span class="perm-module-label">{{ mod.label }}</span>
            <el-checkbox
              v-model="form.permissions[mod.key].edit"
              :disabled="!form.permissions[mod.key]"
            >编辑</el-checkbox>
            <el-checkbox
              v-model="form.permissions[mod.key].delete"
              :disabled="!form.permissions[mod.key]"
            >删除</el-checkbox>
            <el-checkbox
              v-model="form.permissions[mod.key].batch_delete"
              :disabled="!form.permissions[mod.key]"
            >批量删除</el-checkbox>
          </div>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getBusinessUsers, createBusinessUser, updateBusinessUser, deleteBusinessUser } from '@/api/businessUsers'

const modules = [
  { key: 'investment', label: '招商项目管理' },
  { key: 'activity', label: '招商动态管理' },
  { key: 'demand', label: '企业诉求管理' }
]

const users = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const defaultPermissions = () => {
  const p = {}
  modules.forEach(m => {
    p[m.key] = { edit: true, delete: true, batch_delete: true }
  })
  return p
}

const defaultForm = () => ({
  username: '',
  display_name: '',
  password: '',
  is_active: true,
  permissions: defaultPermissions()
})

const form = reactive(defaultForm())

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }]
}

// 新建时密码必填
const passwordRule = { required: true, message: '请输入密码', trigger: 'blur' }

onMounted(() => {
  fetchUsers()
})

async function fetchUsers() {
  loading.value = true
  try {
    const res = await getBusinessUsers()
    users.value = res.data || []
  } catch (err) {
    ElMessage.error(err.message || '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, defaultForm())
  // 新建时密码必填
  rules.password = [passwordRule]
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  form.username = row.username
  form.display_name = row.display_name || ''
  form.password = ''
  form.is_active = row.is_active
  // 合并权限（确保所有字段存在）
  const p = defaultPermissions()
  if (row.permissions) {
    modules.forEach(m => {
      if (row.permissions[m.key]) {
        p[m.key] = { ...p[m.key], ...row.permissions[m.key] }
      }
    })
  }
  form.permissions = p
  // 编辑时密码选填
  rules.password = []
  dialogVisible.value = true
}

function resetForm() {
  formRef.value?.resetFields()
  rules.password = []
}

async function handleSave() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const data = {
      username: form.username,
      display_name: form.display_name,
      is_active: form.is_active,
      permissions: form.permissions
    }
    if (form.password) {
      data.password = form.password
    }

    if (isEdit.value) {
      await updateBusinessUser(editingId.value, data)
      ElMessage.success('用户更新成功')
    } else {
      await createBusinessUser(data)
      ElMessage.success('用户创建成功')
    }
    dialogVisible.value = false
    await fetchUsers()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户「${row.username}」吗？此操作不可恢复。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteBusinessUser(row.id)
    ElMessage.success('用户已删除')
    await fetchUsers()
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err.message || '删除失败')
    }
  }
}

function formatDate(isoStr) {
  if (!isoStr) return '-'
  return isoStr.replace('T', ' ').substring(0, 19)
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; background: #f5f7fa; }
.admin-main { flex: 1; margin-left: 220px; padding: 24px; }
.admin-content { max-width: 1200px; }

.page-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px;
}
.page-header h2 { margin: 0; font-size: 22px; color: #1a3a5c; font-weight: 600; }

.perm-summary { display: flex; flex-wrap: wrap; gap: 8px; }
.perm-module { display: inline-flex; align-items: center; gap: 4px; }
.perm-module-name { font-size: 12px; color: #606266; font-weight: 500; margin-right: 2px; }
.perm-tag {
  font-size: 11px; color: #409eff; background: #ecf5ff;
  padding: 1px 6px; border-radius: 3px;
}
.perm-tag.perm-none { color: #c0c4cc; background: #f5f7fa; }

.perm-config { padding: 4px 0; }
.perm-module-row {
  display: flex; align-items: center; gap: 16px;
  padding: 10px 12px; margin-bottom: 6px;
  background: #fafafa; border-radius: 6px;
}
.perm-module-label { font-weight: 500; color: #303133; min-width: 120px; font-size: 14px; }
</style>
