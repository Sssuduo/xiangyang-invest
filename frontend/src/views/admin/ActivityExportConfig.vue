<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>动态导出配置</h2>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon> 保存配置
          </el-button>
        </div>

        <p class="page-desc">配置招商动态库 Excel 导出的字段、列宽和顺序。</p>

        <div class="card">
          <h4 class="card-title">导出字段列表</h4>
          <el-table :data="fields" row-key="id" stripe size="small" v-loading="loading">
            <el-table-column label="排序" width="60" align="center">
              <template #default="{ $index }">{{ $index + 1 }}</template>
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
          </el-table>
        </div>

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
                <div v-for="h in previewHeaders" :key="h.field_key" class="preview-data-cell" :style="{ width: h.column_width + 'px' }">
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
import { ElMessage } from 'element-plus'
import { Check, View } from '@element-plus/icons-vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getActivityExportFields, updateActivityExportFields, activityExportPreview } from '@/api/activity_export'

const fields = ref([])
const loading = ref(false)
const saving = ref(false)
const previewing = ref(false)
const previewHeaders = ref([])
const previewRows = ref([])
const previewTotal = ref(0)
const totalPreviewWidth = ref(0)

onMounted(async () => { await loadFields() })

async function loadFields() {
  loading.value = true
  try {
    const res = await getActivityExportFields()
    if (res.code === 0) {
      fields.value = res.data.map(f => ({ ...f, column_width: f.column_width || 120 }))
    }
  } catch { /* ignore */ }
  finally { loading.value = false }
}

async function loadPreview() {
  previewing.value = true
  try {
    const res = await activityExportPreview()
    if (res.code === 0) {
      previewHeaders.value = res.data.headers
      previewRows.value = res.data.rows
      previewTotal.value = res.data.total
      totalPreviewWidth.value = res.data.headers.reduce((s, h) => s + h.column_width, 0)
    }
  } catch { /* ignore */ }
  finally { previewing.value = false }
}

async function handleSave() {
  saving.value = true
  try {
    const data = fields.value.map((f, i) => ({
      id: f.id, field_label: f.field_label,
      is_visible: f.is_visible, column_width: f.column_width,
      sort_order: i + 1
    }))
    const res = await updateActivityExportFields(data)
    if (res.code === 0) ElMessage.success('导出配置已保存')
  } catch (err) { ElMessage.error(err.message) }
  finally { saving.value = false }
}

let resizeIndex = -1, resizeStartX = 0, resizeStartWidth = 0

function startResize(e, index) {
  e.preventDefault()
  resizeIndex = index; resizeStartX = e.clientX
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
.admin-main { flex: 1; background: #f5f7fa; }
.admin-content { padding: 28px 32px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.page-header h2 { color: #1a3a5c; margin: 0; }
.page-desc { color: #909399; font-size: 13px; margin-bottom: 24px; }
.card { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 8px rgba(0,0,0,0.04); }
.card-title { margin: 0 0 14px; font-size: 15px; color: #303133; padding-bottom: 10px; border-bottom: 2px solid #1a3a5c; display: inline-block; }
.preview-table-wrapper { overflow-x: auto; border: 1px solid #e0e0e0; border-radius: 6px; }
.preview-table { border-collapse: collapse; }
.preview-header-row { display: flex; background: #1a3a5c; color: #fff; font-size: 12px; font-weight: 600; }
.preview-header-cell { padding: 8px 6px; border-right: 1px solid rgba(255,255,255,0.2); position: relative; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }
.preview-header-cell:last-child { border-right: none; }
.col-resizer { position: absolute; right: 0; top: 0; width: 5px; height: 100%; cursor: col-resize; background: transparent; }
.col-resizer:hover { background: rgba(255,255,255,0.4); }
.preview-data-row { display: flex; border-bottom: 1px solid #f0f0f0; }
.preview-data-row:last-child { border-bottom: none; }
.preview-data-cell { padding: 7px 6px; font-size: 12px; color: #303133; border-right: 1px solid #f0f0f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }
.preview-data-cell:last-child { border-right: none; }
.preview-hint { font-size: 12px; color: #909399; margin-top: 10px; text-align: right; }
</style>
