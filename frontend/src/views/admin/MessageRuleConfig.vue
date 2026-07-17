<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>消息提醒规则配置</h2>
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 新建规则
          </el-button>
        </div>

        <el-table :data="rules" stripe class="rule-table" v-loading="loading">
          <el-table-column label="启用" width="80" align="center">
            <template #default="{ row }">
              <el-switch
                v-model="row.is_active"
                size="small"
                @change="() => handleToggle(row)"
              />
            </template>
          </el-table-column>

          <el-table-column label="规则名称" prop="name" min-width="200" />

          <el-table-column label="触发条件" min-width="220">
            <template #default="{ row }">
              <el-tag size="small" type="info">{{ conditionTypeLabel(row.condition_type) }}</el-tag>
              <span style="margin-left: 8px;">></span>
              <span style="font-weight: 600; margin-left: 4px;">{{ row.threshold_days }}天</span>
            </template>
          </el-table-column>

          <el-table-column label="消息对象" width="140">
            <template #default="{ row }">
              <el-tag size="small" :type="row.target_type === 'all' ? 'success' : 'warning'">
                {{ targetLabel(row.target_type) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="更新时间" width="160">
            <template #default="{ row }">
              {{ formatTime(row.updated_at) }}
            </template>
          </el-table-column>

          <el-table-column label="操作" width="180" align="center" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 创建/编辑  Drawer -->
        <el-drawer
          v-model="drawerVisible"
          :title="editing ? '编辑规则' : '新建规则'"
          direction="rtl"
          size="560px"
          :close-on-click-modal="false"
        >
          <el-form :model="form" :rules="formRules" ref="formRef" label-position="top">
            <el-form-item label="规则名称" prop="name">
              <el-input v-model="form.name" placeholder="如:新项目超15天需研判" />
            </el-form-item>

            <el-form-item label="触发条件">
              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="条件类型" prop="condition_type">
                    <el-select v-model="form.condition_type" style="width: 100%;">
                      <el-option
                        v-for="opt in conditionTypeOptions"
                        :key="opt.value"
                        :label="opt.label"
                        :value="opt.value"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="阈值天数" prop="threshold_days">
                    <el-input-number v-model="form.threshold_days" :min="1" :max="999" style="width: 100%;" />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form-item>

            <el-form-item label="消息对象" prop="target_type">
              <el-radio-group v-model="form.target_type">
                <el-radio value="all">全部用户</el-radio>
                <el-radio value="specific_users">指定用户</el-radio>
                <el-radio value="project_leaders">项目负责人</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item v-if="form.target_type === 'specific_users'" label="指定用户 ID(逗号分隔)">
              <el-input
                v-model="targetUserIdsStr"
                placeholder="如: 1,3,5(用户 ID,可在业务用户管理页查到)"
              />
            </el-form-item>

            <el-form-item label="消息标题模板" prop="title_template">
              <el-input v-model="form.title_template" placeholder="新消息提醒" />
            </el-form-item>

            <el-form-item label="消息体模板" prop="body_template">
              <el-input
                v-model="form.body_template"
                type="textarea"
                :rows="4"
                placeholder="{username}您好,[{project_name}]距离首次对接[{first_contact_date}]已超过{threshold_days}天,需要进行研判"
              />
              <div class="form-tip">
                可用变量:<code>{username}</code> <code>{project_name}</code> <code>{first_contact_date}</code>
                <code>{threshold_days}</code> <code>{project_id}</code>;用 <code>[文本]</code> 包起来的内容会渲染为链接
              </div>
            </el-form-item>

            <el-form-item label="跳转路由" prop="link_route">
              <el-input v-model="form.link_route" placeholder="/investment" />
            </el-form-item>

            <el-form-item label="跳转参数模板(JSON)" prop="link_query_template">
              <el-input
                v-model="form.link_query_template"
                placeholder='{"focusProjectId": {project_id}}'
              />
              <div class="form-tip">用于点击消息体链接时聚焦到对应项目</div>
            </el-form-item>
          </el-form>

          <template #footer>
            <el-button @click="drawerVisible = false">取消</el-button>
            <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
          </template>
        </el-drawer>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { listMessageRules, createMessageRule, updateMessageRule, deleteMessageRule, toggleMessageRule } from '@/api/admin.js'

const rules = ref([])
const loading = ref(false)
const drawerVisible = ref(false)
const editing = ref(null)
const submitting = ref(false)
const formRef = ref(null)
const targetUserIdsStr = ref('')

const conditionTypeOptions = [
  { value: 'project_no_meeting', label: '招商项目超期未研判' },
  { value: 'project_no_followup', label: '招商项目超期无动态' },
]

const form = reactive({
  name: '',
  is_active: true,
  condition_type: 'project_no_meeting',
  threshold_days: 15,
  target_type: 'all',
  target_user_ids: [],
  title_template: '新消息提醒',
  body_template: '',
  link_route: '/investment',
  link_query_template: '{"focusProjectId": {project_id}}',
})

const formRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  body_template: [{ required: true, message: '请输入消息体模板', trigger: 'blur' }],
}

async function loadRules() {
  loading.value = true
  try {
    const res = await listMessageRules()
    rules.value = res.data.data || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, {
    name: '', is_active: true, condition_type: 'project_no_meeting',
    threshold_days: 15, target_type: 'all', title_template: '新消息提醒',
    body_template: '', link_route: '/investment',
    link_query_template: '{"focusProjectId": {project_id}}',
  })
  targetUserIdsStr.value = ''
  drawerVisible.value = true
}

function openEdit(row) {
  editing.value = row
  Object.assign(form, {
    name: row.name, is_active: row.is_active, condition_type: row.condition_type,
    threshold_days: row.threshold_days, target_type: row.target_type,
    title_template: row.title_template, body_template: row.body_template,
    link_route: row.link_route, link_query_template: row.link_query_template,
  })
  targetUserIdsStr.value = (row.target_user_ids || []).join(',')
  drawerVisible.value = true
}

async function handleSubmit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = { ...form, target_user_ids: parseUserIds(targetUserIdsStr.value) }
    if (editing.value) {
      await updateMessageRule(editing.value.id, payload)
    } else {
      await createMessageRule(payload)
    }
    ElMessage.success('保存成功')
    drawerVisible.value = false
    loadRules()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除规则"${row.name}"?`, '提示', { type: 'warning' })
  await deleteMessageRule(row.id)
  ElMessage.success('删除成功')
  loadRules()
}

async function handleToggle(row) {
  try {
    await toggleMessageRule(row.id)
    ElMessage.success(row.is_active ? '已启用' : '已禁用')
  } catch {
    row.is_active = !row.is_active
  }
}

function parseUserIds(str) {
  return (str || '').split(',').map(s => parseInt(s.trim(), 10)).filter(Boolean)
}

function conditionTypeLabel(value) {
  return conditionTypeOptions.find(o => o.value === value)?.label || value
}

function targetLabel(value) {
  return { all: '全部用户', specific_users: '指定用户', project_leaders: '项目负责人' }[value] || value
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

onMounted(loadRules)
</script>

<style scoped>
.rule-table { margin-top: 12px; }
.form-tip { font-size: 12px; color: #909399; margin-top: 4px; line-height: 1.4; }
.form-tip code {
  background: #f4f4f5; padding: 1px 4px; border-radius: 3px;
  margin: 0 2px; font-family: monospace; color: #e6a23c;
}
.page-header { display: flex; justify-content: space-between; align-items: center; }
</style>
