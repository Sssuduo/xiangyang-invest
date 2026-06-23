<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>{{ isEdit ? '编辑项目' : '新建项目' }}</h2>
          <el-button @click="router.push('/admin/investment')">返回列表</el-button>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" class="edit-form" size="default">
          <!-- 基础信息 -->
          <el-divider content-position="left">基础信息</el-divider>

          <el-form-item label="顺序号" prop="order_no">
            <el-input-number v-model="form.order_no" :min="0" :max="9999" style="width: 140px;" />
          </el-form-item>

          <el-form-item label="项目名称" prop="project_name">
            <el-input v-model="form.project_name" placeholder="请输入项目名称" maxlength="255" />
          </el-form-item>

          <el-form-item label="项目类型" prop="project_type_code">
            <el-select v-model="form.project_type_code" placeholder="请选择">
              <el-option v-for="d in dicts.project_types" :key="d.code" :label="d.name" :value="d.code" />
            </el-select>
          </el-form-item>

          <el-form-item label="投资金额" prop="invest_amount">
            <el-input-number v-model="form.invest_amount" :min="0" :precision="2" :step="100" style="width: 260px;" />
            <span class="input-hint">单位：万元。大于等于 10000 万时前台自动展示为亿元</span>
          </el-form-item>

          <el-form-item label="首次对接时间">
            <el-date-picker v-model="form.first_contact_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 200px;" />
          </el-form-item>

          <!-- 企业信息 -->
          <el-divider content-position="left">企业信息</el-divider>

          <el-form-item label="投资企业" prop="invest_enterprise">
            <el-input v-model="form.invest_enterprise" placeholder="请输入投资企业名称" maxlength="255" />
          </el-form-item>

          <el-form-item label="企业信息" prop="enterprise_info">
            <el-input v-model="form.enterprise_info" type="textarea" :rows="3" placeholder="企业详细信息..." maxlength="2000" show-word-limit />
          </el-form-item>

          <!-- 项目详情 -->
          <el-divider content-position="left">项目详情</el-divider>

          <el-form-item label="项目内容" prop="project_content">
            <el-input v-model="form.project_content" type="textarea" :rows="4" placeholder="项目详细内容..." maxlength="5000" show-word-limit />
          </el-form-item>

          <el-form-item label="项目文档">
            <el-input v-model="form.project_doc" placeholder="文档链接（支持 PDF/DOC/DOCX/PPT 等）" maxlength="512" />
            <span class="input-hint">粘贴文件链接或使用上传功能获取路径</span>
          </el-form-item>

          <!-- 状态与分配 -->
          <el-divider content-position="left">状态与分配</el-divider>

          <el-form-item label="跟进状态" prop="follow_status_code">
            <el-select v-model="form.follow_status_code" placeholder="请选择">
              <el-option v-for="d in dicts.follow_statuses" :key="d.code" :label="d.name" :value="d.code" />
            </el-select>
          </el-form-item>

          <el-form-item label="上会状态" prop="meeting_status_code">
            <el-select v-model="form.meeting_status_code" placeholder="请选择">
              <el-option v-for="d in dicts.meeting_statuses" :key="d.code" :label="d.name" :value="d.code" />
            </el-select>
          </el-form-item>

          <el-form-item label="推介单位">
            <el-select v-model="form.recommend_unit_code" placeholder="请选择" clearable>
              <el-option v-for="d in dicts.organizations" :key="d.code" :label="d.name" :value="d.code" />
            </el-select>
          </el-form-item>

          <el-form-item label="包保单位" prop="responsible_unit_code">
            <el-select v-model="form.responsible_unit_code" placeholder="请选择">
              <el-option v-for="d in dicts.organizations" :key="d.code" :label="d.name" :value="d.code" />
            </el-select>
          </el-form-item>

          <el-form-item label="负责人">
            <el-input v-model="form.person_in_charge" placeholder="负责人姓名" maxlength="64" style="width: 200px;" />
          </el-form-item>

          <!-- 项目标签 -->
          <el-divider content-position="left">项目标签</el-divider>
          <el-form-item label="标签">
            <el-select v-model="form.tags" multiple placeholder="请选择标签" style="width: 100%;">
              <el-option v-for="d in dicts.project_tags" :key="d.code" :label="d.name" :value="d.code" />
            </el-select>
          </el-form-item>

          <!-- 保存 -->
          <el-form-item>
            <el-button type="primary" size="large" :loading="saving" @click="handleSave">
              {{ isEdit ? '更新' : '创建' }}
            </el-button>
            <el-button size="large" @click="router.push('/admin/investment')">取消</el-button>
          </el-form-item>
        </el-form>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getDicts, createProject, getProject, updateProject } from '@/api/investment'

const route = useRoute()
const router = useRouter()
const formRef = ref(null)
const saving = ref(false)
const isEdit = computed(() => !!route.params.id)

const dicts = reactive({
  follow_statuses: [],
  meeting_statuses: [],
  organizations: [],
  project_types: [],
  project_tags: []
})

const form = reactive({
  order_no: 0,
  project_name: '',
  project_type_code: '',
  invest_amount: 0,
  invest_enterprise: '',
  enterprise_info: '',
  project_content: '',
  project_doc: '',
  follow_status_code: '',
  meeting_status_code: 'not_meeting',
  recommend_unit_code: '',
  responsible_unit_code: '',
  person_in_charge: '',
  first_contact_date: '',
  tags: []
})

const rules = {
  project_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  project_type_code: [{ required: true, message: '请选择项目类型', trigger: 'change' }],
  invest_amount: [{ required: true, message: '请输入投资金额', trigger: 'blur' }],
  invest_enterprise: [{ required: true, message: '请输入投资企业', trigger: 'blur' }],
  enterprise_info: [{ required: true, message: '请输入企业信息', trigger: 'blur' }],
  project_content: [{ required: true, message: '请输入项目内容', trigger: 'blur' }],
  follow_status_code: [{ required: true, message: '请选择跟进状态', trigger: 'change' }],
  responsible_unit_code: [{ required: true, message: '请选择包保单位', trigger: 'change' }]
}

onMounted(async () => {
  await loadDicts()
  if (isEdit.value) {
    await loadProject()
  }
})

async function loadDicts() {
  try {
    const res = await getDicts()
    if (res.code === 0) {
      Object.assign(dicts, res.data)
    }
  } catch { /* ignore */ }
}

async function loadProject() {
  try {
    const res = await getProject(route.params.id)
    if (res.code === 0) {
      const d = res.data
      Object.keys(form).forEach(k => {
        if (k in d) form[k] = d[k] ?? form[k]
      })
      // 确保数值类型
      form.order_no = Number(form.order_no) || 0
      form.invest_amount = Number(form.invest_amount) || 0
      form.tags = Array.isArray(form.tags) ? form.tags : []
    }
  } catch (err) {
    ElMessage.error(err.message)
    router.push('/admin/investment')
  }
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const data = { ...form }
    data.invest_amount = Number(data.invest_amount)
    data.order_no = Number(data.order_no)

    if (isEdit.value) {
      await updateProject(route.params.id, data)
      ElMessage.success('项目更新成功')
    } else {
      await createProject(data)
      ElMessage.success('项目创建成功')
    }
    router.push('/admin/investment')
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: #f5f7fa; }
.admin-content { padding: 28px 32px; max-width: 800px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
h2 { color: #1a3a5c; margin: 0; }
.edit-form { background: #fff; padding: 32px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.input-hint { font-size: 12px; color: #909399; margin-left: 12px; }
</style>
