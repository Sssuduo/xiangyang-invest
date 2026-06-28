<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>在建项目导出配置</h2>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon> 保存配置
          </el-button>
        </div>

        <p class="page-desc">配置在建项目库 Excel 导出的字段、列宽和顺序。支持创建多个导出模板。</p>

        <!-- 模板管理 -->
        <div class="card" style="margin-bottom: 20px;">
          <div class="template-bar">
            <span class="template-label">导出模板：</span>
            <el-select v-model="currentTemplateId" placeholder="选择模板" style="width: 280px;" @change="onTemplateChange">
              <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
            <el-button size="small" @click="openCreateTemplate">
              <el-icon><Plus /></el-icon> 新建
            </el-button>
            <el-button size="small" @click="openRenameTemplate" :disabled="!currentTemplateId">
              重命名
            </el-button>
            <el-button size="small" type="danger" @click="handleDeleteTemplate" :disabled="templates.length <= 1">
              删除
            </el-button>
          </div>
        </div>

        <!-- 字段配置 -->
        <div class="card">
          <h4 class="card-title">导出字段列表</h4>
          <el-table :data="fields" row-key="id" stripe size="small" v-loading="loading">
            <el-table-column label="排序" width="60" align="center">
              <template #default="{ $index }">
                <el-icon class="drag-handle" style="cursor: grab;"><Rank /></el-icon>
                <span style="margin-left: 4px;">{{ $index + 1 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="field_key" label="字段标识" width="150" />
            <el-table-column label="导出列标题" min-width="160">
              <template #default="{ row }">
                <el-input v-model="row.field_label" size="small" placeholder="列标题" />
              </template>
            </el-table-column>
            <el-table-column label="导出" width="70" align="center">
              <template #default="{ row }">
                <el-switch v-model="row.is_visible" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="列宽(px)" width="100" align="center">
              <template #default="{ row }">
                <el-input-number v-model="row.column_width" :min="40" :max="600" :step="10" size="small" controls-position="right" style="width: 90px;" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="130" align="center">
              <template #default="{ row, $index }">
                <el-button size="small" link @click="moveUp($index)" :disabled="$index === 0" title="上移">
                  <el-icon><Top /></el-icon>
                </el-button>
                <el-button size="small" link @click="moveDown($index)" :disabled="$index === fields.length - 1" title="下移">
                  <el-icon><Bottom /></el-icon>
                </el-button>
                <el-button v-if="row.is_custom" size="small" link type="danger" @click="removeCustomField($index)" title="删除">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button size="small" style="margin-top: 12px;" @click="addCustomField">
            <el-icon><Plus /></el-icon> 添加自定义列
          </el-button>
        </div>

        <!-- 导出预览 -->
        <div class="card" style="margin-top: 20px;">
          <h4 class="card-title">导出预览</h4>
          <el-button size="small" :loading="previewing" @click="loadPreview" style="margin-bottom: 12px;">
            <el-icon><View /></el-icon> 刷新预览
          </el-button>
          <div class="preview-table-wrapper" v-if="previewHeaders.length > 0">
            <div class="preview-table" :style="{ minWidth: totalPreviewWidth + 'px' }">
              <div class="preview-header-row">
                <div
                  v-for="(h, i) in previewHeaders"
                  :key="h.field_key"
                  class="preview-header-cell"
                  :style="{ width: h.column_width + 'px' }"
                >
                  {{ h.field_label }}
                  <span class="col-resizer" @mousedown="startResize($event, i)" />
                </div>
              </div>
              <div v-for="(row, ri) in previewRows" :key="ri" class="preview-data-row">
                <div
                  v-for="h in previewHeaders"
                  :key="h.field_key"
                  class="preview-data-cell"
                  :style="{ width: h.column_width + 'px' }"
                >
                  {{ row[h.field_key] ?? '-' }}
                </div>
              </div>
            </div>
            <p class="preview-hint">共 {{ previewTotal }} 条记录（预览仅展示前3条）</p>
          </div>
          <el-empty v-else description="点击刷新预览" :image-size="60" />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { Check, View, Rank, Plus, Delete, Top, Bottom } from '@element-plus/icons-vue'
import {
  getConstructionExportFields, updateConstructionExportFields, constructionExportPreview,
  getConstructionExportTemplates, createConstructionExportTemplate,
  updateConstructionExportTemplate, deleteConstructionExportTemplate
} from '@/api/construction_export'

const templates = ref([])
const currentTemplateId = ref(0)
const fields = ref([])
const loading = ref(false)
const saving = ref(false)
const previewing = ref(false)
const previewHeaders = ref([])
const previewRows = ref([])
const previewTotal = ref(0)
const totalPreviewWidth = ref(0)

onMounted(async () => {
  await loadTemplates()
  if (currentTemplateId.value) {
    await loadFields()
  }
})

async function loadTemplates(autoSelect = true) {
  try {
    const res = await getConstructionExportTemplates()
    if (res.code === 0) {
      templates.value = res.data || []
      if (autoSelect && templates.value.length > 0) {
        const stillExists = templates.value.some(t => t.id === currentTemplateId.value)
        if (!stillExists) {
          currentTemplateId.value = templates.value[0].id
        }
        if (!currentTemplateId.value) {
          currentTemplateId.value = templates.value[0].id
        }
      }
    }
  } catch { /* ignore */ }
}

async function onTemplateChange() {
  await loadFields()
}

async function loadFields() {
  if (!currentTemplateId.value) return
  loading.value = true
  try {
    const res = await getConstructionExportFields(currentTemplateId.value)
    if (res.code === 0) {
      fields.value = res.data.map(f => ({ ...f, column_width: f.column_width || 120 }))
    }
  } catch { /* ignore */ }
  finally { loading.value = false }
}

async function openCreateTemplate() {
  try {
    const { value } = await ElMessageBox.prompt('请输入新模板名称', '新建导出模板', {
      confirmButtonText: '创建', cancelButtonText: '取消',
      inputPlaceholder: '模板名称'
    })
    if (value && value.trim()) {
      const res = await createConstructionExportTemplate({ name: value.trim(), entity_type: 'construction' })
      if (res.code === 0 && res.data && res.data.id) {
        const newId = res.data.id
        ElMessage.success(`模板「${res.data.name}」已创建`)
        await loadTemplates(false)
        const found = templates.value.find(t => t.id === newId)
        if (found) {
          currentTemplateId.value = newId
          await loadFields()
        } else {
          ElMessage.warning('模板已创建但未在列表中，请刷新页面')
          await loadTemplates(true)
          if (currentTemplateId.value) await loadFields()
        }
      } else {
        ElMessage.error(res.message || '模板创建失败')
      }
    }
  } catch (err) {
    ElMessage.error(err.message || '模板创建失败')
  }
}

async function openRenameTemplate() {
  if (!currentTemplateId.value) return
  const tpl = templates.value.find(t => t.id === currentTemplateId.value)
  if (!tpl) return
  try {
    const { value } = await ElMessageBox.prompt('请输入新名称', '重命名模板', {
      confirmButtonText: '确定', cancelButtonText: '取消',
      inputPlaceholder: '模板名称', inputValue: tpl.name
    })
    if (value && value.trim()) {
      await updateConstructionExportTemplate(currentTemplateId.value, { name: value.trim() })
      ElMessage.success('模板已重命名')
      await loadTemplates()
    }
  } catch { /* cancelled */ }
}

async function handleDeleteTemplate() {
  if (templates.value.length <= 1) {
    ElMessage.warning('至少保留一个导出模板')
    return
  }
  try {
    await ElMessageBox.confirm('确定要删除该模板及其所有字段配置吗？', '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    await deleteConstructionExportTemplate(currentTemplateId.value)
    ElMessage.success('模板已删除')
    currentTemplateId.value = 0
    await loadTemplates()
    if (currentTemplateId.value) {
      await loadFields()
    }
  } catch { /* cancelled */ }
}

async function loadPreview() {
  previewing.value = true
  try {
    const res = await constructionExportPreview([], currentTemplateId.value)
    if (res.code === 0) {
      previewHeaders.value = res.data.headers
      previewRows.value = res.data.rows
      previewTotal.value = res.data.total
      totalPreviewWidth.value = res.data.headers.reduce((s, h) => s + h.column_width, 0)
    }
  } catch { /* ignore */ }
  finally { previewing.value = false }
}

let customFieldCounter = 1

function addCustomField() {
  const key = `custom_${customFieldCounter++}`
  fields.value.push({
    id: 0,
    template_id: currentTemplateId.value,
    field_key: key,
    field_label: '自定义列',
    is_visible: true,
    is_custom: true,
    column_width: 120,
    sort_order: fields.value.length + 1,
    _new: true
  })
}

function removeCustomField(idx) {
  fields.value.splice(idx, 1)
}

function moveUp(idx) {
  if (idx <= 0) return
  const arr = fields.value
  ;[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]
}

function moveDown(idx) {
  if (idx >= fields.value.length - 1) return
  const arr = fields.value
  ;[arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]]
}

async function handleSave() {
  saving.value = true
  try {
    const data = fields.value.map((f, i) => ({
      id: f.id || 0,
      template_id: f.template_id,
      field_key: f.field_key,
      field_label: f.field_label,
      is_visible: f.is_visible,
      is_custom: f.is_custom || false,
      column_width: f.column_width,
      sort_order: i + 1,
      _new: f._new || false
    }))
    const res = await updateConstructionExportFields(data)
    if (res.code === 0) {
      ElMessage.success('导出配置已保存')
    }
  } catch (err) {
    ElMessage.error(err.message)
  }
  finally { saving.value = false }
}

// ---- 列宽拖拽调整 ----
let resizeIndex = -1
let resizeStartX = 0
let resizeStartWidth = 0

function startResize(e, index) {
  e.preventDefault()
  resizeIndex = index
  resizeStartX = e.clientX
  resizeStartWidth = previewHeaders.value[index].column_width
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
}

function onResize(e) {
  if (resizeIndex < 0) return
  const diff = e.clientX - resizeStartX
  const newWidth = Math.max(40, Math.min(600, resizeStartWidth + diff))
  previewHeaders.value[resizeIndex].column_width = newWidth
  totalPreviewWidth.value = previewHeaders.value.reduce((s, h) => s + h.column_width, 0)
  const key = previewHeaders.value[resizeIndex].field_key
  const field = fields.value.find(f => f.field_key === key)
  if (field) field.column_width = newWidth
}

function stopResize() {
  resizeIndex = -1
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: #f5f7fa; min-width: 0; }
.admin-content { padding: 28px 32px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.page-header h2 { color: #1a3a5c; margin: 0; }
.page-desc { color: #909399; font-size: 13px; margin-bottom: 24px; }

.card { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 8px rgba(0,0,0,0.04); }
.card-title { margin: 0 0 14px; font-size: 15px; color: #303133; padding-bottom: 10px; border-bottom: 2px solid #1a3a5c; display: inline-block; }

.template-bar { display: flex; align-items: center; gap: 12px; }
.template-label { font-size: 14px; font-weight: 500; color: #303133; }

.preview-table-wrapper { overflow-x: auto; border: 1px solid #e0e0e0; border-radius: 6px; }
.preview-table { border-collapse: collapse; }
.preview-header-row { display: flex; background: #fff; color: #303133; font-size: 12px; font-weight: 600; border-bottom: 2px solid #d0d0d0; }
.preview-header-cell { padding: 8px 6px; border-right: 1px solid #d0d0d0; position: relative; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }
.preview-header-cell:last-child { border-right: none; }
.col-resizer { position: absolute; right: 0; top: 0; width: 5px; height: 100%; cursor: col-resize; background: transparent; }
.col-resizer:hover { background: rgba(0,0,0,0.15); }
.preview-data-row { display: flex; border-bottom: 1px solid #d0d0d0; }
.preview-data-row:last-child { border-bottom: 1px solid #d0d0d0; }
.preview-data-cell { padding: 7px 6px; font-size: 12px; color: #303133; border-right: 1px solid #d0d0d0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }
.preview-data-cell:last-child { border-right: 1px solid #d0d0d0; }
.preview-hint { font-size: 12px; color: #909399; margin-top: 10px; text-align: right; }
</style>
