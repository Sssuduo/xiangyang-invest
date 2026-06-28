<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="v => emit('update:modelValue', v)"
    :title="dialogTitle"
    width="480px"
    :close-on-click-modal="false"
    @opened="onOpened"
  >
    <el-form label-width="80px" size="small">
      <el-form-item label="选择模板">
        <el-select v-model="selectedTemplateId" style="width:100%">
          <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </el-form-item>

      <!-- 招商项目选项 -->
      <template v-if="entityType === 'investment'">
        <el-form-item label="动态范围">
          <el-select v-model="subOptions.activityRange" style="width:100%">
            <el-option label="全部动态" value="" />
            <el-option label="最近5条" value="last5" />
            <el-option label="最近1个月" value="last1m" />
            <el-option label="最近3个月" value="last3m" />
          </el-select>
        </el-form-item>
        <el-form-item label="诉求模式">
          <el-select v-model="subOptions.demandMode" style="width:100%">
            <el-option label="聚合导出" value="aggregate" />
            <el-option label="按行展开" value="row" />
          </el-select>
        </el-form-item>
        <el-form-item label="诉求范围">
          <el-checkbox-group v-model="subOptions.demandStatus" size="small">
            <el-checkbox label="pending">待回应</el-checkbox>
            <el-checkbox label="processing">协调中</el-checkbox>
            <el-checkbox label="resolved">已回应</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </template>

      <!-- 在建项目选项 -->
      <template v-if="entityType === 'construction'">
        <el-form-item label="进展范围">
          <el-select v-model="subOptions.progressRange" style="width:100%">
            <el-option label="全部进展" value="" />
            <el-option label="最近2条" value="last2" />
            <el-option label="最近5条" value="last5" />
            <el-option label="最近1个月" value="last1m" />
            <el-option label="最近3个月" value="last3m" />
          </el-select>
        </el-form-item>
        <el-form-item label="进展模式">
          <el-select v-model="subOptions.progressMode" style="width:100%">
            <el-option label="聚合导出" value="aggregate" />
            <el-option label="按行展开" value="progress" />
          </el-select>
        </el-form-item>
        <el-form-item label="工作路径范围">
          <el-select v-model="subOptions.workPathRange" style="width:100%">
            <el-option label="全部路径" value="" />
            <el-option label="仅待完成" value="pending" />
          </el-select>
        </el-form-item>
      </template>
    </el-form>

    <div style="text-align:center;padding:12px 0;color:#606266;font-size:13px">
      共选中 <strong style="color:#409eff">{{ projectIds.length }}</strong> 条记录
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handlePrint" :loading="processing">
        <el-icon><Printer /></el-icon> 在线打印
      </el-button>
      <el-button type="success" @click="handleExport" :loading="processing">
        <el-icon><Download /></el-icon> 导出Excel
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Printer, Download } from '@element-plus/icons-vue'
import { getPrintTemplates } from '@/api/print'
import { getConstructionPrintTemplates } from '@/api/construction_print'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  entityType: { type: String, default: 'investment' },
  projectIds: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: v => emit('update:modelValue', v)
})

const dialogTitle = computed(() => {
  if (props.entityType === 'construction') return '打印 / 导出 — 在建项目'
  return '打印 / 导出 — 招商项目'
})

const templates = ref([])
const selectedTemplateId = ref(0)
const processing = ref(false)

const subOptions = ref({
  activityRange: '',
  demandMode: 'aggregate',
  demandStatus: ['pending', 'processing'],  // 默认待回应+协调中，不含已回应
  progressRange: '',
  progressMode: 'aggregate',
  workPathRange: 'pending',  // 默认仅待完成
})

async function onOpened() {
  await loadTemplates()
}

async function loadTemplates() {
  try {
    const fn = props.entityType === 'construction' ? getConstructionPrintTemplates : getPrintTemplates
    const res = await fn(props.entityType)
    if (res.code === 0 && res.data && res.data.length > 0) {
      templates.value = res.data
      selectedTemplateId.value = res.data[0].id
    }
  } catch (e) {
    ElMessage.error('加载模板失败')
  }
}

function buildDownloadUrl() {
  if (!selectedTemplateId.value || props.projectIds.length === 0) return null

  const basePath = props.entityType === 'construction'
    ? '/api/admin/construction-print/download'
    : '/api/admin/print/download'

  const params = new URLSearchParams()
  params.set('project_ids', props.projectIds.join(','))
  params.set('template_id', selectedTemplateId.value)

  if (props.entityType === 'investment') {
    if (subOptions.value.activityRange) params.set('activity_range', subOptions.value.activityRange)
    if (subOptions.value.demandMode) params.set('demand_mode', subOptions.value.demandMode)
    // 诉求范围：逗号拼接状态码，空数组=全部
    params.set('demand_status', subOptions.value.demandStatus.join(',') || '')
  } else {
    if (subOptions.value.progressRange) params.set('progress_range', subOptions.value.progressRange)
    if (subOptions.value.progressMode) params.set('progress_mode', subOptions.value.progressMode)
    if (subOptions.value.workPathRange) params.set('work_path_range', subOptions.value.workPathRange)
  }

  return `${basePath}?${params.toString()}`
}

async function handleExport() {
  const url = buildDownloadUrl()
  if (!url) return ElMessage.warning('请先选择模板和项目')

  processing.value = true
  try {
    const resp = await fetch(url, { credentials: 'same-origin' })
    if (!resp.ok) {
      // 尝试从响应体中读取错误消息
      let errMsg = '导出失败'
      try {
        const errData = await resp.json()
        errMsg = errData.message || errMsg
      } catch { /* 非 JSON 响应体 */ }
      throw new Error(errMsg)
    }

    // Parse filename from Content-Disposition（与 print.js / export.js 一致的健壮解析）
    const disposition = resp.headers.get('Content-Disposition') || ''
    let filename = '导出文件.xlsx'
    // 优先匹配 RFC 5987: filename*=UTF-8''xxx
    const starMatch = disposition.match(/filename\*=UTF-8''([^;]*)/i)
    if (starMatch && starMatch[1]) {
      try { filename = decodeURIComponent(starMatch[1]) } catch { filename = starMatch[1] }
    } else {
      // 降级匹配 plain filename（处理可能带引号的情况）
      const plainMatch = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (plainMatch && plainMatch[1]) {
        filename = plainMatch[1].replace(/['"]/g, '')
        try { filename = decodeURIComponent(filename) } catch { /* keep as-is */ }
      }
    }

    const blob = await resp.blob()
    const blobUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(blobUrl)

    ElMessage.success('导出完成')
  } catch (e) {
    ElMessage.error(e.message || '导出失败')
  } finally {
    processing.value = false
  }
}

async function handlePrint() {
  const url = buildDownloadUrl()
  if (!url) return ElMessage.warning('请先选择模板和项目')

  processing.value = true
  try {
    const resp = await fetch(url, { credentials: 'same-origin' })
    if (!resp.ok) {
      // 尝试从响应体中读取错误消息
      let errMsg = '导出失败'
      try {
        const errData = await resp.json()
        errMsg = errData.message || errMsg
      } catch { /* 非 JSON 响应体 */ }
      throw new Error(errMsg)
    }

    // Parse filename from Content-Disposition（与 handleExport 一致）
    const disposition = resp.headers.get('Content-Disposition') || ''
    let filename = '打印文件.xlsx'
    const starMatch = disposition.match(/filename\*=UTF-8''([^;]*)/i)
    if (starMatch && starMatch[1]) {
      try { filename = decodeURIComponent(starMatch[1]) } catch { filename = starMatch[1] }
    } else {
      const plainMatch = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (plainMatch && plainMatch[1]) {
        filename = plainMatch[1].replace(/['"]/g, '')
        try { filename = decodeURIComponent(filename) } catch { /* keep as-is */ }
      }
    }

    const blob = await resp.blob()
    const blobUrl = URL.createObjectURL(blob)

    const w = window.open(blobUrl, '_blank')
    if (w) {
      setTimeout(() => {
        w.print()
      }, 1000)
    } else {
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    }

    URL.revokeObjectURL(blobUrl)
    ElMessage.success('已发送到打印机')
  } catch (e) {
    ElMessage.error(e.message || '打印失败')
  } finally {
    processing.value = false
  }
}</script>
