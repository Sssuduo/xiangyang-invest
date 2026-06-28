<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>专班工作人员管理</h2>
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 新增人员
          </el-button>
        </div>

        <el-table :data="items" stripe row-key="id" v-loading="loading" empty-text="暂无工作人员">
          <el-table-column label="序号" width="70" align="center">
            <template #default="{ row }">{{ row.sort_order }}</template>
          </el-table-column>
          <el-table-column label="姓名" width="140">
            <template #default="{ row }">{{ row.name }}</template>
          </el-table-column>
          <el-table-column label="职务" min-width="180">
            <template #default="{ row }">{{ row.position || '-' }}</template>
          </el-table-column>
          <el-table-column label="关联账号" width="140">
            <template #default="{ row }">
              <span v-if="row.admin_display_name">{{ row.admin_display_name }}</span>
              <span v-else style="color:#c0c4cc">未关联</span>
            </template>
          </el-table-column>
          <el-table-column label="启用" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                {{ row.is_active ? '是' : '否' }}
              </el-tag>
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
      :title="isEdit ? '编辑工作人员' : '新增工作人员'"
      width="480px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="职务">
          <el-input v-model="form.position" placeholder="农高区创建专班工作人员" />
        </el-form-item>
        <el-form-item label="关联账号">
          <el-select v-model="form.user_id" placeholder="不关联" clearable style="width:100%">
            <el-option
              v-for="admin in adminUsers"
              :key="admin.id"
              :label="admin.display_name"
              :value="admin.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="排序序号">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
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
import { getStaffList, createStaff, updateStaff, deleteStaff, getAdminUsers } from '@/api/staff'

const items = ref([])
const adminUsers = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const defaultForm = () => ({
  name: '',
  position: '',
  user_id: null,
  sort_order: 0,
  is_active: true,
})

const form = reactive(defaultForm())

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
}

onMounted(() => {
  fetchData()
  fetchAdmins()
})

async function fetchData() {
  loading.value = true
  try {
    const res = await getStaffList()
    items.value = res.data || []
  } catch (err) {
    ElMessage.error(err.message || '获取工作人员列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchAdmins() {
  try {
    const res = await getAdminUsers()
    adminUsers.value = res.data || []
  } catch {
    // 静默失败，下拉为空
  }
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  form.name = row.name
  form.position = row.position || ''
  form.user_id = row.user_id || null
  form.sort_order = row.sort_order || 0
  form.is_active = row.is_active
  dialogVisible.value = true
}

function resetForm() {
  formRef.value?.resetFields()
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
      name: form.name,
      position: form.position,
      user_id: form.user_id,
      sort_order: form.sort_order,
      is_active: form.is_active,
    }

    if (isEdit.value) {
      await updateStaff(editingId.value, data)
      ElMessage.success('已更新')
    } else {
      await createStaff(data)
      ElMessage.success('已添加')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${row.name}」吗？`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteStaff(row.id)
    ElMessage.success('已删除')
    await fetchData()
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err.message || '删除失败')
    }
  }
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; background: #f5f7fa; }
.admin-main { flex: 1; margin-left: 220px; padding: 24px; }
.admin-content { max-width: 1100px; }

.page-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px;
}
.page-header h2 { margin: 0; font-size: 22px; color: #1a3a5c; font-weight: 600; }
</style>
