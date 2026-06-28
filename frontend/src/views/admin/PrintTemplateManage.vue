<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>打印模板管理</h2>
        </div>

        <!-- 卡片1：模板选择 + 管理 -->
        <div class="card" style="margin-bottom:16px">
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
            <span class="setting-label">实体类型</span>
            <el-select v-model="entityType" size="small" style="width:120px" @change="onEntityChange">
              <el-option label="招商项目" value="investment" />
              <el-option label="在建项目" value="construction" />
            </el-select>
            <span class="setting-label">模板</span>
            <el-select v-model="currentTemplateId" size="small" style="width:160px" @change="onTemplateChange">
              <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
            <el-button size="small" @click="onNewTemplate">新建</el-button>
            <el-button size="small" @click="onRenameTemplate" :disabled="!currentTemplateId">重命名</el-button>
            <el-button size="small" type="danger" @click="onDeleteTemplate" :disabled="!currentTemplateId || templates.length<=1">删除</el-button>
          </div>
        </div>

        <!-- 卡片2：上传模板文件 -->
        <div class="card" style="margin-bottom:16px">
          <h3 style="margin:0 0 12px 0">上传模板文件 (.xlsx)</h3>
          <p class="page-desc" style="margin-bottom:12px">
            上传已在 Excel 中调试好格式的 .xlsx 模板文件。系统将自动解析列标题，保留全部格式（字体、列宽、行高、合并单元格、页边距）。
          </p>
          <div style="display:flex;align-items:center;gap:16px">
            <el-upload
              ref="uploadRef"
              :action="uploadUrl"
              :auto-upload="true"
              :limit="1"
              accept=".xlsx"
              :on-success="onUploadSuccess"
              :on-error="onUploadError"
              :show-file-list="false"
              :disabled="!currentTemplateId"
            >
              <el-button type="primary" size="small" :disabled="!currentTemplateId">
                <el-icon><Upload /></el-icon> 选择 .xlsx 文件
              </el-button>
            </el-upload>
            <template v-if="currentTemplate?.template_file">
              <span style="color:#67c23a;font-size:13px">✓ 已上传: {{ currentTemplate.template_file.split('/').pop() }}</span>
              <el-button size="small" text type="primary" @click="downloadTemplateFile">下载当前模板</el-button>
              <el-button size="small" text type="danger" @click="deleteTemplateFile">删除模板文件</el-button>
            </template>
          </div>
        </div>

        <!-- 卡片3：字段映射 -->
        <div class="card" style="margin-bottom:16px" v-if="mappings.length > 0">
          <h3 style="margin:0 0 12px 0">字段映射</h3>
          <p class="page-desc" style="margin-bottom:12px">
            系统已自动解析列标题，请将每列映射到对应的系统字段。未映射的列将不会写入数据。
          </p>
          <el-table :data="mappings" size="small" border stripe style="width:100%">
            <el-table-column prop="column_letter" label="列" width="60" />
            <el-table-column prop="column_header" label="模板列标题（原文）" min-width="200" />
            <el-table-column label="映射系统字段" min-width="220">
              <template #default="{ row }">
                <el-select v-model="row.field_key" size="small" style="width:100%"
                  clearable placeholder="-- 选择系统字段 --"
                  @change="onMappingChange(row)">
                  <el-option v-for="af in availableFields" :key="af.field_key"
                    :label="af.field_label" :value="af.field_key" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column prop="field_key" label="field_key" width="180">
              <template #default="{ row }">
                <code v-if="row.field_key" style="font-size:11px;color:#409eff">{{ row.field_key }}</code>
                <span v-else style="color:#909399;font-size:11px">未映射</span>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top:8px;font-size:12px;color:#909399">
            已映射 {{ mappedCount }} / {{ mappings.length }} 列
            <el-button size="small" text @click="saveAllMappings" :loading="saving" style="margin-left:12px">保存全部映射</el-button>
          </div>
        </div>

        <!-- 卡片4：模板结构参数 -->
        <div class="card" v-if="currentTemplate">
          <h3 style="margin:0 0 12px 0">模板结构参数</h3>
          <div style="display:flex;gap:24px;flex-wrap:wrap">
            <div>
              <span class="setting-label">大标题行</span>
              <el-input-number v-model="currentTemplate.title_row" :min="1" :max="10" size="small" style="width:70px" @change="saveTemplateInfo" />
            </div>
            <div>
              <span class="setting-label">列标题行</span>
              <el-input-number v-model="currentTemplate.header_row" :min="1" :max="10" size="small" style="width:70px" @change="saveTemplateInfo" />
            </div>
            <div>
              <span class="setting-label">数据起始行</span>
              <el-input-number v-model="currentTemplate.data_start_row" :min="2" :max="20" size="small" style="width:70px" @change="saveTemplateInfo" />
            </div>
            <div style="display:flex;align-items:center;gap:6px">
              <el-switch v-model="currentTemplate.has_group_title" size="small" @change="saveTemplateInfo" />
              <span class="setting-label">有分组标题</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getPrintTemplates, createPrintTemplate, updatePrintTemplate, deletePrintTemplate } from '@/api/print'
import { getConstructionPrintTemplates, createConstructionPrintTemplate, updateConstructionPrintTemplate, deleteConstructionPrintTemplate } from '@/api/construction_print'
import api from '@/api/index'

const entityType = ref('investment')
const templates = ref([])
const currentTemplateId = ref(0)
const currentTemplate = ref(null)
const mappings = ref([])
const availableFields = ref([])
const saving = ref(false)

const uploadUrl = ref('')

// 动态更新 upload action，避免初始模板 ID 为 0
function updateUploadUrl() {
  uploadUrl.value = currentTemplateId.value
    ? `/api/admin/print/templates/${currentTemplateId.value}/upload`
    : ''
}

const mappedCount = computed(() => mappings.value.filter(m => m.field_key).length)

function getPrintAPI() {
  if (entityType.value === 'construction') {
    return {
      getTemplates: getConstructionPrintTemplates,
      createTemplate: createConstructionPrintTemplate,
      updateTemplate: updateConstructionPrintTemplate,
      deleteTemplate: deleteConstructionPrintTemplate,
    }
  }
  return {
    getTemplates: getPrintTemplates,
    createTemplate: createPrintTemplate,
    updateTemplate: updatePrintTemplate,
    deleteTemplate: deletePrintTemplate,
  }
}

async function loadTemplates() {
  const api2 = getPrintAPI()
  const res = await api2.getTemplates(entityType.value)
  if (res.code === 0) {
    templates.value = res.data || []
    if (templates.value.length > 0) {
      currentTemplateId.value = templates.value[0].id
      currentTemplate.value = templates.value[0]
      updateUploadUrl()
      await loadMappings()
    }
  }
}

function onEntityChange() {
  currentTemplateId.value = 0
  currentTemplate.value = null
  mappings.value = []
  loadTemplates()
}

async function onTemplateChange(id) {
  const tpl = templates.value.find(t => t.id === id)
  if (tpl) {
    currentTemplate.value = tpl
    updateUploadUrl()
    await loadMappings()
  }
}

async function loadMappings() {
  if (!currentTemplateId.value) return
  const res = await api.get(`/admin/print/templates/${currentTemplateId.value}/mappings`)
  if (res.code === 0) {
    mappings.value = res.data.mappings || []
    availableFields.value = res.data.available_fields || []
  }
}

async function onNewTemplate() {
  const { value } = await ElMessageBox.prompt('请输入模板名称', '新建模板')
  if (!value || !value.trim()) return
  const api2 = getPrintAPI()
  const res = await api2.createTemplate({ name: value.trim(), entity_type: entityType.value })
  if (res.code === 0) {
    ElMessage.success('模板已创建')
    await loadTemplates()
    currentTemplateId.value = res.data.id
    currentTemplate.value = templates.value.find(t => t.id === res.data.id)
    mappings.value = []
  } else {
    ElMessage.error(res.message || '创建失败')
  }
}

async function onRenameTemplate() {
  const tpl = currentTemplate.value
  if (!tpl) return
  const { value } = await ElMessageBox.prompt('请输入新名称', '重命名模板', { inputValue: tpl.name })
  if (!value || !value.trim()) return
  const api2 = getPrintAPI()
  const res = await api2.updateTemplate(tpl.id, { name: value.trim() })
  if (res.code === 0) {
    ElMessage.success('已重命名')
    await loadTemplates()
  } else {
    ElMessage.error(res.message || '重命名失败')
  }
}

async function onDeleteTemplate() {
  const tpl = currentTemplate.value
  if (!tpl) return
  await ElMessageBox.confirm(`确定删除模板「${tpl.name}」？`, '删除确认', { type: 'warning' })
  const api2 = getPrintAPI()
  const res = await api2.deleteTemplate(tpl.id)
  if (res.code === 0) {
    ElMessage.success('已删除')
    currentTemplateId.value = 0
    currentTemplate.value = null
    mappings.value = []
    await loadTemplates()
  } else {
    ElMessage.error(res.message || '删除失败')
  }
}

function onUploadSuccess(response) {
  if (response.code === 0) {
    ElMessage.success(response.message || '模板已上传')
    mappings.value = response.data || []
    if (currentTemplate.value) {
      currentTemplate.value.template_file = true // trigger re-render
    }
    loadMappings()
  } else {
    ElMessage.error(response.message || '上传失败')
  }
}

function onUploadError() {
  ElMessage.error('上传失败，请检查网络或文件格式')
}

async function onMappingChange(row) {
  await saveAllMappings()
}

async function saveAllMappings() {
  if (!currentTemplateId.value || mappings.value.length === 0) return
  saving.value = true
  try {
    const payload = mappings.value.map(m => ({
      column_letter: m.column_letter,
      field_key: m.field_key || ''
    }))
    const res = await api.put(`/admin/print/templates/${currentTemplateId.value}/mappings`, payload)
    if (res.code === 0) {
      ElMessage.success(res.message || '映射已保存')
    }
  } finally {
    saving.value = false
  }
}

async function saveTemplateInfo() {
  if (!currentTemplateId.value) return
  const api2 = getPrintAPI()
  await api2.updateTemplate(currentTemplateId.value, {
    title_row: currentTemplate.value.title_row,
    header_row: currentTemplate.value.header_row,
    data_start_row: currentTemplate.value.data_start_row,
    has_group_title: currentTemplate.value.has_group_title,
  })
}

function downloadTemplateFile() {
  if (!currentTemplateId.value) return
  window.open(`/api/admin/print/templates/${currentTemplateId.value}/file`, '_blank')
}

async function deleteTemplateFile() {
  await ElMessageBox.confirm('确定删除模板文件及列映射？', '确认', { type: 'warning' })
  const res = await api.delete(`/admin/print/templates/${currentTemplateId.value}/file`)
  if (res.code === 0) {
    ElMessage.success('已删除')
    if (currentTemplate.value) currentTemplate.value.template_file = ''
    mappings.value = []
  } else {
    ElMessage.error(res.message || '删除失败')
  }
}

onMounted(loadTemplates)
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: #f5f7fa; }
.admin-content { padding: 28px 32px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; color: #303133; }
.card { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.setting-label { font-size: 13px; color: #606266; white-space: nowrap; }
.page-desc { font-size: 13px; color: #909399; margin: 0; }
</style>
