<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>字典配置</h2>
        </div>

        <el-tabs v-model="activeTab" @tab-change="switchTab">
          <el-tab-pane
            v-for="tab in tabs"
            :key="tab.key"
            :label="tab.label"
            :name="tab.key"
          />
        </el-tabs>

        <div class="dict-toolbar">
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 新增条目
          </el-button>
          <span class="dict-count">共 {{ items.length }} 条</span>
        </div>

        <el-table :data="items" stripe row-key="id" class="dict-table">
          <el-table-column label="排序" width="100" align="center">
            <template #default="{ row, $index }">
              <div class="sort-actions">
                <el-button
                  size="small"
                  :disabled="$index === 0"
                  link
                  @click="moveUp($index)"
                >
                  <el-icon><ArrowUp /></el-icon>
                </el-button>
                <el-button
                  size="small"
                  :disabled="$index === items.length - 1"
                  link
                  @click="moveDown($index)"
                >
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="编码" width="180">
            <template #default="{ row }">
              <span class="code-mono">{{ row.code }}</span>
            </template>
          </el-table-column>

          <el-table-column label="名称" min-width="160">
            <template #default="{ row }">
              <span>{{ row.name }}</span>
            </template>
          </el-table-column>

          <el-table-column v-if="currentTabHasColor" label="颜色" width="100" align="center">
            <template #default="{ row }">
              <span class="color-dot" :style="{ background: row.display_color }"></span>
              <span class="color-code">{{ row.display_color }}</span>
            </template>
          </el-table-column>

          <el-table-column label="启用" width="80" align="center">
            <template #default="{ row }">
              <el-switch
                v-model="row.is_active"
                size="small"
                @change="(val) => handleToggleActive(row, val)"
              />
            </template>
          </el-table-column>

          <el-table-column label="操作" width="160" align="center">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </main>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增条目' : '编辑条目'"
      width="480px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="编码" prop="code">
          <el-input v-model="form.code" placeholder="唯一编码（英文/数字/下划线）" :disabled="dialogMode === 'edit'" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item v-if="currentTabHasColor" label="颜色">
          <el-color-picker v-model="form.display_color" show-alpha />
          <span style="margin-left: 8px; font-size: 12px; color: #909399;">{{ form.display_color }}</span>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getDictItems, createDictItem, updateDictItem, deleteDictItem, reorderDictItems } from '@/api/dict'

// ---- Tab 配置 ----
const tabs = [
  { key: 'follow_statuses', label: '跟进状态' },
  { key: 'meeting_statuses', label: '上会状态' },
  { key: 'organizations', label: '单位字典' },
  { key: 'project_types', label: '项目类型' },
  { key: 'demand_types', label: '诉求类型' },
]
const tabsWithColor = ['follow_statuses', 'meeting_statuses']

const activeTab = ref('follow_statuses')
const currentTabHasColor = computed(() => tabsWithColor.includes(activeTab.value))

// ---- 数据 ----
const items = ref([])

async function loadItems() {
  try {
    const res = await getDictItems(activeTab.value)
    if (res.code === 0) items.value = res.data || []
  } catch { items.value = [] }
}

function switchTab() { loadItems() }

// ---- 排序 ----
async function moveUp(idx) {
  if (idx === 0) return
  const arr = [...items.value]
  ;[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]
  items.value = arr
  await saveOrder()
}

async function moveDown(idx) {
  if (idx >= items.value.length - 1) return
  const arr = [...items.value]
  ;[arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]]
  items.value = arr
  await saveOrder()
}

async function saveOrder() {
  try {
    const ids = items.value.map(i => i.id)
    await reorderDictItems(activeTab.value, ids)
  } catch { /* ignore */ }
}

// ---- 启用/禁用 ----
async function handleToggleActive(row, val) {
  try {
    await updateDictItem(activeTab.value, row.id, { is_active: val })
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch { row.is_active = !val }
}

// ---- 对话框 ----
const dialogVisible = ref(false)
const dialogMode = ref('create')
const editingId = ref(null)
const formRef = ref(null)
const saving = ref(false)

const defaultForm = () => ({
  code: '',
  name: '',
  display_color: '#909399',
  is_active: true
})
const form = reactive(defaultForm())

const rules = {
  code: [{ required: true, message: '请输入编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }]
}

function openCreate() {
  dialogMode.value = 'create'
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  dialogMode.value = 'edit'
  editingId.value = row.id
  form.code = row.code
  form.name = row.name
  form.display_color = row.display_color || '#909399'
  form.is_active = row.is_active
  dialogVisible.value = true
}

function resetForm() {
  Object.assign(form, defaultForm())
  formRef.value?.clearValidate()
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const data = {
      name: form.name,
      is_active: form.is_active
    }
    if (currentTabHasColor.value) data.display_color = form.display_color

    if (dialogMode.value === 'create') {
      data.code = form.code
      await createDictItem(activeTab.value, data)
      ElMessage.success('创建成功')
    } else {
      await updateDictItem(activeTab.value, editingId.value, data)
      ElMessage.success('保存成功')
    }
    dialogVisible.value = false
    loadItems()
  } catch (err) {
    ElMessage.error(err.message || '操作失败')
  } finally {
    saving.value = false
  }
}

// ---- 删除 ----
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除「${row.name}」吗？`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    await deleteDictItem(activeTab.value, row.id)
    ElMessage.success('已删除')
    loadItems()
  } catch { /* cancelled */ }
}

onMounted(loadItems)
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; background: #f0f2f5; }
.admin-main { flex: 1; overflow-y: auto; }
.admin-content { padding: 32px; max-width: 960px; }

.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { font-size: 20px; color: #303133; }

.dict-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.dict-count { font-size: 13px; color: #909399; }

.dict-table {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

.sort-actions { display: flex; flex-direction: column; align-items: center; gap: 0; }
.sort-actions .el-button { padding: 2px 4px; }

.code-mono {
  font-family: 'Consolas', 'Menlo', monospace;
  font-size: 12px;
  color: #1a3a5c;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
}

.color-dot {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 3px;
  border: 1px solid #dcdfe6;
  vertical-align: middle;
  margin-right: 6px;
}
.color-code { font-size: 12px; color: #909399; vertical-align: middle; }
</style>
