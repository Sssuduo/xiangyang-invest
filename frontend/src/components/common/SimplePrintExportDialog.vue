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
          <el-radio-group v-model="subOptions.activityRangeType">
            <el-radio label="count">按条数导出</el-radio>
            <el-radio label="month">按最近月份</el-radio>
            <el-radio label="daterange">按时间段</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 按条数导出 -->
        <el-form-item v-if="subOptions.activityRangeType === 'count'" label=" ">
          <span class="range-hint">取最近</span>
          <el-input-number v-model="subOptions.activityCount" :min="1" :max="999" controls-position="right" />
          <span class="range-hint">条</span>
          <span class="range-hint--weak">不足则导出全部</span>
        </el-form-item>

        <!-- 按最近月份 -->
        <el-form-item v-if="subOptions.activityRangeType === 'month'" label=" ">
          <span class="range-hint">最近</span>
          <el-input-number v-model="subOptions.activityMonths" :min="1" :max="60" controls-position="right" />
          <span class="range-hint">个月</span>
        </el-form-item>

        <!-- 按时间段 -->
        <el-form-item v-if="subOptions.activityRangeType === 'daterange'" label=" ">
          <el-date-picker
            v-model="subOptions.activityDateRange"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width:100%"
          />
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
        <el-form-item label="调度状态">
          <el-select
            v-model="subOptions.dispatchStatus"
            multiple
            collapse-tags
            placeholder="选择调度状态"
            style="width:100%"
          >
            <el-option
              v-for="d in dispatchStatusOptions"
              :key="d.code"
              :label="d.name"
              :value="d.code"
            />
          </el-select>
          <div class="dispatch-hint">默认：调度中 + 不予调度；可补选其他状态</div>
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
const dispatchStatusOptions = ref([])  // 调度状态字典选项

const subOptions = ref({
  // ---- 招商项目：动态范围（V15.3: 三选一） ----
  activityRangeType: 'count',     // 'count' | 'month' | 'daterange'
  activityCount: 5,               // 按条数时的条数（默认 5）
  activityMonths: 1,              // 按最近月份时的月数（默认 1）
  activityDateRange: null,        // 按时间段时的 [start, end] daterange
  // ---- 招商项目：诉求 ----
  demandMode: 'aggregate',
  demandStatus: ['pending', 'processing'],  // 默认待回应+协调中，不含已回应
  // ---- 在建项目：进展/路径（V15.3 不动） ----
  progressRange: '',
  progressMode: 'aggregate',
  workPathRange: 'pending',  // 默认仅待完成
  // ---- 在建项目：调度状态（V15.4 新增 多选） ----
  dispatchStatus: ['dispatching', 'no_dispatch'],  // 默认调度中+不予调度
})

async function onOpened() {
  await loadTemplates()
  if (props.entityType === 'construction') await loadDispatchStatuses()
}

async function loadDispatchStatuses() {
  // 拉取调度状态字典，供多选下拉使用
  try {
    const res = await fetch('/api/admin/construction/dicts', { credentials: 'same-origin' })
    const data = await res.json()
    if (data.code === 0 && Array.isArray(data.data?.dispatch_statuses)) {
      dispatchStatusOptions.value = data.data.dispatch_statuses
      // 校验默认选中项仍存在于字典中（过滤已删除/停用的）
      const validCodes = new Set(dispatchStatusOptions.value.map(d => d.code))
      subOptions.value.dispatchStatus = subOptions.value.dispatchStatus.filter(c => validCodes.has(c))
      if (subOptions.value.dispatchStatus.length === 0) {
        // 兜底：字典中前两项或全部
        subOptions.value.dispatchStatus = dispatchStatusOptions.value.slice(0, 2).map(d => d.code)
      }
    }
  } catch { /* 字典加载失败不影响主流程 */ }
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
    // V15.3: 招商项目导出 — 三选一（按条数/按最近月份/按时间段）
    const ao = subOptions.value
    if (ao.activityRangeType === 'count') {
      params.set('activity_mode', 'count')
      if (ao.activityCount > 0) params.set('activity_count', String(ao.activityCount))
    } else if (ao.activityRangeType === 'month') {
      params.set('activity_mode', 'time')
      params.set('activity_time_mode', 'month')
      if (ao.activityMonths > 0) params.set('activity_months', String(ao.activityMonths))
    } else if (ao.activityRangeType === 'daterange') {
      params.set('activity_mode', 'time')
      params.set('activity_time_mode', 'daterange')
      if (Array.isArray(ao.activityDateRange) && ao.activityDateRange.length === 2) {
        params.set('activity_start', ao.activityDateRange[0])
        params.set('activity_end', ao.activityDateRange[1])
      }
    }
    if (subOptions.value.demandMode) params.set('demand_mode', subOptions.value.demandMode)
    // 诉求范围：逗号拼接状态码，空数组=全部
    params.set('demand_status', subOptions.value.demandStatus.join(',') || '')
  } else {
    if (subOptions.value.progressRange) params.set('progress_range', subOptions.value.progressRange)
    if (subOptions.value.progressMode) params.set('progress_mode', subOptions.value.progressMode)
    if (subOptions.value.workPathRange) params.set('work_path_range', subOptions.value.workPathRange)
    // 调度状态多选（逗号分隔），空则传默认
    const ds = subOptions.value.dispatchStatus
    params.set('dispatch_status', Array.isArray(ds) && ds.length > 0 ? ds.join(',') : 'dispatching,no_dispatch')
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

<style scoped>
.dispatch-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
</style>
