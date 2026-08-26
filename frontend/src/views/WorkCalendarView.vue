<!-- WorkCalendarView.vue: 工作日历 - 周/月视图 + 内联编辑 + Word导出（区间/字段自选） -->
<template>
  <div class="work-calendar-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 工具栏（单行：视图切换 + 翻页 + 日期 + 操作） -->
        <div class="toolbar">
          <div class="view-switch">
            <el-button-group>
              <el-button
                :type="currentView === 'timeGridWeek' ? 'primary' : ''"
                @click="switchView('timeGridWeek')"
              >周视图</el-button>
              <el-button
                :type="currentView === 'dayGridMonth' ? 'primary' : ''"
                @click="switchView('dayGridMonth')"
              >月视图</el-button>
            </el-button-group>
          </div>

          <div class="nav-group">
            <el-button circle @click="calendarRef?.getApi()?.prev()">
              <el-icon><ArrowLeft /></el-icon>
            </el-button>
            <el-button circle @click="calendarRef?.getApi()?.next()">
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>

          <span class="current-date-label">{{ currentDateLabel }}</span>

          <div class="toolbar-spacer" />

          <el-button type="success" plain @click="openExportDialog">
            <el-icon><Document /></el-icon> 导出Word
          </el-button>
          <el-button type="primary" @click="handleQuickAdd">
            <el-icon><Plus /></el-icon> 快速添加
          </el-button>
        </div>

        <!-- FullCalendar 容器 -->
        <FullCalendar
          ref="calendarRef"
          :options="calendarOptions"
          class="work-calendar"
        />
      </div>
    </div>

    <!-- 导出弹窗：区间 + 字段选择 -->
    <el-dialog v-model="exportDialogVisible" title="导出工作日历" width="480px" append-to-body>
      <div class="export-dialog-body">
        <div class="export-field-title">导出区间</div>
        <el-date-picker
          v-model="exportDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
        <div class="export-field-title" style="margin-top: 18px;">导出字段</div>
        <div class="export-fields">
          <el-checkbox
            v-for="f in exportFieldOptions"
            :key="f.key"
            v-model="exportFields"
            :label="f.key"
            :value="f.key"
          >{{ f.label }}</el-checkbox>
        </div>
        <div class="export-fields-hint">「工作事项」作为记录标题始终导出</div>
      </div>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="handleExportWord">导出</el-button>
      </template>
    </el-dialog>

    <!-- 事件悬停预览（跟随鼠标，图片可点击放大） -->
    <Teleport to="body">
      <transition name="hover-fade">
        <div
          v-if="hoverEvent"
          class="event-hover-card"
          :style="hoverStyle"
          @mouseenter="hoverStay = true"
          @mouseleave="handleHoverLeave"
        >
          <div class="hover-time">
            {{ formatTimeRange(hoverEvent.start_datetime, hoverEvent.end_datetime) }}
          </div>
          <div class="hover-title">{{ hoverEvent.work_item || '未命名' }}</div>
          <div v-if="hoverEvent.work_content" class="hover-content">{{ hoverEvent.work_content }}</div>
          <div v-if="hoverEvent.participants && hoverEvent.participants.length" class="hover-participants">
            👥 {{ hoverEvent.participants.join('、') }}
          </div>
          <div v-if="hoverImages.length" class="hover-images">
            <el-image
              v-for="(img, i) in hoverImages"
              :key="img.url"
              :src="img.url"
              :preview-src-list="hoverImages.map(x => x.url)"
              :initial-index="i"
              fit="cover"
              class="hover-thumb"
              preview-teleported
            />
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- 内联编辑浮层（全屏遮罩 + 上移加宽卡片） -->
    <Teleport to="body">
      <transition name="inline-edit-fade">
        <div
          v-if="showInlineEditor"
          class="inline-editor-overlay"
          @click.self="handleCloseEditor"
        >
          <div class="inline-editor-card" :style="editorPosition" @mousedown.stop>
            <div class="editor-header">
              <span class="editor-title">{{ isEditing ? '编辑工作记录' : '新建工作记录' }}</span>
              <el-icon class="close-btn" @click="handleCloseEditor"><Close /></el-icon>
            </div>

            <el-form :model="formData" label-position="top" size="small" class="editor-form">
              <el-form-item label="工作日期">
                <!-- 单日期：不跨天，直接展示选中格子的日期 -->
                <el-date-picker
                  v-model="formData.start_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="选择日期"
                  style="width: 100%"
                  @change="onWorkDateChange"
                />
              </el-form-item>

              <el-form-item label="工作时段">
                <div class="time-range-display">
                  {{ formatTimeRange(formData.start_datetime, formData.end_datetime) }}
                </div>
                <!-- 两个时间编辑框在同一行 -->
                <div class="time-range-row">
                  <el-time-picker
                    v-model="formData.start_time"
                    format="HH:mm"
                    value-format="HH:mm"
                    placeholder="开始时间"
                    class="time-picker-item"
                    @change="onStartTimeChange"
                  />
                  <span class="time-range-sep">至</span>
                  <el-time-picker
                    v-model="formData.end_time"
                    format="HH:mm"
                    value-format="HH:mm"
                    placeholder="结束时间"
                    class="time-picker-item"
                    @change="onEndTimeChange"
                  />
                </div>
              </el-form-item>

              <el-form-item label="工作事项" required>
                <el-input
                  v-model="formData.work_item"
                  placeholder="例如：项目评审会议"
                  maxlength="200"
                  show-word-limit
                />
              </el-form-item>

              <el-form-item label="工作内容">
                <el-input
                  v-model="formData.work_content"
                  type="textarea"
                  :rows="2"
                  placeholder="详细描述工作内容..."
                  maxlength="2000"
                  show-word-limit
                />
              </el-form-item>

              <el-form-item label="参加人员">
                <el-select
                  v-model="formData.participants"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="输入或选择参加人员"
                  filterable
                  allow-create
                  default-first-option
                  style="width: 100%"
                >
                  <el-option
                    v-for="staff in staffList"
                    :key="staff.id"
                    :label="staff.name"
                    :value="staff.name"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="附件">
                <div class="attach-layout">
                  <!-- 上传区（半宽半高、向左对齐）+ Ctrl+V 粘贴（复用工作大事记抽屉的交互） -->
                  <div class="upload-wrapper" @paste="handleClipboardPaste">
                    <el-upload
                      :action="uploadUrl"
                      :on-success="handleUploadSuccess"
                      :on-error="handleUploadError"
                      :show-file-list="false"
                      multiple
                      drag
                      accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.png,.jpg,.jpeg,.gif,.webp"
                    >
                      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                      <div class="el-upload__text">拖动文件到此处 或 <em>点击上传</em></div>
                    </el-upload>
                    <!-- 文件缩略图网格 -->
                    <div v-if="fileList.length > 0" class="file-thumbnail-grid">
                      <div v-for="(file, idx) in fileList" :key="file.uid || idx" class="file-thumb-card">
                        <div class="thumb-preview">
                          <el-image
                            v-if="isImageFile(file)"
                            :src="getFilePreviewUrl(file)"
                            :preview-src-list="fileList.filter(isImageFile).map(getFilePreviewUrl)"
                            :initial-index="fileList.filter(isImageFile).indexOf(file)"
                            fit="cover"
                            class="thumb-img"
                            preview-teleported
                          />
                          <div v-else class="thumb-generic">
                            <el-icon :size="28"><Document /></el-icon>
                            <span>{{ getFileExt(file) }}</span>
                          </div>
                          <div class="thumb-remove" @click="handleThumbRemove(idx)">
                            <el-icon><Close /></el-icon>
                          </div>
                        </div>
                        <div class="thumb-name" :title="getFileName(file)">{{ getFileName(file) }}</div>
                      </div>
                    </div>
                  </div>
                  <!-- 粘贴图片组件：放在右侧空出的区域，高度与附件框一致 -->
                  <div class="paste-zone" @paste="handleClipboardPaste" tabindex="0" title="点击此处后按 Ctrl+V 粘贴图片">
                    <span class="paste-icon"><el-icon><Picture /></el-icon></span>
                    <span class="paste-label">粘贴图片</span>
                    <span class="paste-hint">点击此处 · 按 <kbd>Ctrl+V</kbd> 插入图片</span>
                  </div>
                </div>
              </el-form-item>
            </el-form>

            <div class="editor-footer">
              <el-button @click="closeEditor">取消</el-button>
              <el-button v-if="isEditing" type="danger" @click="handleDeleteEntry">删除</el-button>
              <el-button type="primary" :loading="saving" @click="saveEntry">保存</el-button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import timeGridPlugin from '@fullcalendar/timegrid'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import zhLocale from '@fullcalendar/core/locales/zh-cn'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Close, UploadFilled, Plus, Document, Picture, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import { workCalendarApi } from '@/api/workCalendar'
import { getDicts } from '@/api/investment'
import { useBusinessAuthStore } from '@/stores/businessAuth'

const businessAuth = useBusinessAuthStore()

// ===== 日历引用和状态 =====
const calendarRef = ref(null)
const currentView = ref('timeGridWeek')
const currentDateLabel = ref('')

// ===== 内联编辑器状态 =====
const showInlineEditor = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const saving = ref(false)
const selectionRect = ref(null)

// ===== 表单数据 =====
const emptyForm = () => ({
  work_item: '',
  work_content: '',
  participants: [],
  attachments: [],
  start_datetime: '',
  end_datetime: '',
  start_date: '',
  end_date: '',
  start_time: '',
  end_time: '',
  time_period: ''
})

const formData = ref(emptyForm())

// ===== 附件上传（含 Ctrl+V 粘贴，复用工作大事记交互） =====
// 后端路由为 POST /api/upload（api_bp url_prefix=/api + /upload）
const uploadUrl = '/api/upload'
// 附件列表：{ name, url, size, uid }
const fileList = ref([])

// ===== 工作人员列表（用于自动补全） =====
const staffList = ref([])

// ===== 导出弹窗 =====
const exportDialogVisible = ref(false)
const exporting = ref(false)
const exportDateRange = ref([])
const exportFieldOptions = [
  { key: 'time', label: '工作时段' },
  { key: 'work_content', label: '工作内容' },
  { key: 'participants', label: '参加人员' },
  { key: 'attachments', label: '附件' }
]
const exportFields = ref(exportFieldOptions.map(f => f.key))

// ===== 事件悬停预览 =====
const hoverEvent = ref(null)
const hoverPos = ref({ x: 0, y: 0 })
const hoverStay = ref(false)

const hoverImages = computed(() => {
  const atts = hoverEvent.value?.attachments || []
  return atts.filter(a => a && a.url && isImageUrl(a.url))
})

const hoverStyle = computed(() => {
  let left = hoverPos.value.x + 14
  let top = hoverPos.value.y + 14
  if (left + 320 > window.innerWidth) left = hoverPos.value.x - 334
  if (top + 200 > window.innerHeight) top = hoverPos.value.y - 214
  return { left: `${left}px`, top: `${top}px` }
})

// ===== 编辑器位置（卡到窗口上部，向上放） =====
const editorPosition = computed(() => {
  if (!selectionRect.value) return { display: 'none' }
  return {
    left: `${selectionRect.value.left}px`,
    top: `${selectionRect.value.top}px`,
    display: 'block'
  }
})

// 时间轴：上午 08:30-12:00 · 午休 · 下午 14:30-18:00
function isRestSlot(date) {
  const mins = date.getHours() * 60 + date.getMinutes()
  return mins >= 12 * 60 && mins < 14 * 60 + 30
}

// ===== 日历配置 =====
const calendarOptions = ref({
  plugins: [timeGridPlugin, dayGridPlugin, interactionPlugin],
  initialView: 'timeGridWeek',
  locale: zhLocale,
  firstDay: 1, // 周一为第一天
  headerToolbar: false, // 隐藏 FullCalendar 自带标题行/今天按钮（自绘工具栏）
  slotMinTime: '08:30:00',
  slotMaxTime: '18:00:00',
  slotDuration: '00:30:00', // 30分钟一格
  slotLabelInterval: '00:30:00', // 每半小时都标注
  allDaySlot: false,
  height: 'auto',
  contentHeight: 640,
  expandRows: true,

  // 日列表头（纵列标题）：周视图显示 X月X日 周X（中间一个空格），月视图保持仅周几
  dayHeaderContent: (arg) => {
    const d = arg.date
    const weekdays = ['日', '一', '二', '三', '四', '五', '六']
    if (arg.view?.type === 'dayGridMonth') {
      return `周${weekdays[d.getDay()]}`
    }
    return `${d.getMonth() + 1}月${d.getDate()}日 周${weekdays[d.getDay()]}`
  },

  // 启用时间选择
  selectable: true,
  selectMirror: true,

  eventOverlap: true,

  // 纵轴时间标签：完全由 slotLabelContent 输出
  // （不设 slotLabelFormat 字符串，core 6.1 ESM 下 cmdFormatter 为空会抛错）
  slotLabelContent: (arg) => {
    const d = arg.date
    if (isRestSlot(d)) return '' // 午休段不展示文字（该行已压缩到一半高度）
    const h = d.getHours()
    const m = String(d.getMinutes()).padStart(2, '0')
    return `${h}:${m}`
  },
  // 午休段：标签格 + 时间格同时打标，用于把对应 5 行压缩为一半高度
  slotLabelClassNames: (arg) => (isRestSlot(arg.date) ? ['fc-rest-slot'] : []),
  slotLaneClassNames: (arg) => (isRestSlot(arg.date) ? ['fc-rest-slot', 'fc-rest-lane'] : []),

  // 选择事件（拖拽选择时间段后触发）
  select: (info) => {
    if (info.allDay) {
      ElMessage.info('请在周视图中框选具体时间，或点击「快速添加」')
      return
    }
    const startDate = new Date(info.startStr)
    const endDate = new Date(info.endStr)

    openEditor({
      start_datetime: info.startStr,
      end_datetime: info.endStr,
      start_time: formatDate(startDate, 'HH:mm'),
      end_time: formatDate(endDate, 'HH:mm'),
      time_period: determineTimePeriod(startDate)
    })
  },

  // 点击已有事件编辑
  eventClick: (info) => {
    const props = info.event.extendedProps
    const startDate = new Date(props.start_datetime)
    const endDate = new Date(props.end_datetime)

    openEditor({
      ...props,
      start_time: formatDate(startDate, 'HH:mm'),
      end_time: formatDate(endDate, 'HH:mm')
    }, info.event.id)
  },

  // 悬停预览
  eventMouseEnter: (info, jsEvent) => {
    const props = info.event.extendedProps
    if (!props.start_datetime) return // 拖选 mirror 不预览
    hoverEvent.value = props
    hoverPos.value = { x: jsEvent.clientX, y: jsEvent.clientY }
  },
  eventMouseLeave: () => {
    // 延迟关闭，允许移入预览卡
    setTimeout(() => {
      if (!hoverStay.value) hoverEvent.value = null
    }, 120)
  },

  // 自定义事件渲染（多彩渐变；用户文本转义防 XSS；拖选 mirror 不显示 NaN/未命名）
  eventContent: (arg) => {
    const { event } = arg
    const props = event.extendedProps

    // 拖选预览（mirror）事件：无真实数据，渲染淡色占位，不出现 NaN/未命名
    if (!props.start_datetime) {
      return { html: '<div class="calendar-event-card is-mirror"><div class="event-title">新记录</div></div>' }
    }

    const startTime = formatDate(new Date(props.start_datetime), 'HH:mm')
    const endTime = formatDate(new Date(props.end_datetime), 'HH:mm')
    const tone = colorTone(props.work_item || '')

    let participantsHtml = ''
    if (props.participants && props.participants.length > 0) {
      const names = props.participants.slice(0, 2).map(escapeHtml).join(', ')
      const more = props.participants.length > 2 ? ` +${props.participants.length - 2}` : ''
      participantsHtml = `<div class="event-participants">👥 ${names}${more}</div>`
    }

    const imgCount = (props.attachments || []).filter(a => a && isImageUrl(a.url)).length
    const imgHtml = imgCount > 0 ? `<div class="event-imgs">🖼 ${imgCount}</div>` : ''

    return {
      html: `
        <div class="calendar-event-card ev-${tone}">
          <div class="event-time">${startTime}-${endTime}${imgHtml}</div>
          <div class="event-title">${escapeHtml(event.title || '未命名')}</div>
          ${participantsHtml}
        </div>
      `
    }
  },

  // 加载事件数据
  events: async (fetchInfo, successCallback, failureCallback) => {
    try {
      const res = await workCalendarApi.getList({
        start: fetchInfo.startStr,
        end: fetchInfo.endStr
      })

      const events = res.data.map(entry => ({
        id: entry.id,
        title: entry.work_item,
        start: entry.start_datetime,
        end: entry.end_datetime,
        extendedProps: entry
      }))

      successCallback(events)
    } catch (e) {
      console.error('加载日历事件失败:', e)
      failureCallback(e)
    }
  },

  // 日期变化时更新标签
  datesSet: (dateInfo) => {
    updateDateLabel(dateInfo)
  }
})

// ===== 工具函数 =====

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[c]))
}

function formatDate(date, format) {
  const pad = (n) => n.toString().padStart(2, '0')
  const year = date.getFullYear()
  const month = pad(date.getMonth() + 1)
  const day = pad(date.getDate())
  const hours = pad(date.getHours())
  const minutes = pad(date.getMinutes())

  if (format === 'HH:mm') return `${hours}:${minutes}`
  if (format === 'YYYY-MM-DD') return `${year}-${month}-${day}`
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

function formatTimeRange(start, end) {
  if (!start || !end) return '-'
  const s = new Date(start)
  const e = new Date(end)
  const sameDay = formatDate(s, 'YYYY-MM-DD') === formatDate(e, 'YYYY-MM-DD')
  return sameDay
    ? `${formatDate(s, 'HH:mm')} - ${formatDate(e, 'HH:mm')}`
    : `${formatDate(s, 'YYYY-MM-DD HH:mm')} - ${formatDate(e, 'YYYY-MM-DD HH:mm')}`
}

function determineTimePeriod(startDate) {
  const hour = startDate.getHours()
  if (hour >= 8 && hour < 12) return 'morning'
  if (hour >= 14 && hour < 18) return 'afternoon'
  return 'custom'
}

function updateDateLabel(dateInfo) {
  const start = new Date(dateInfo.start)
  const end = new Date(dateInfo.end)

  if (currentView.value === 'timeGridWeek') {
    // 周视图标题：2026-08-24 - 08-31日（结束只展示 月-日）
    const mm = String(end.getMonth() + 1).padStart(2, '0')
    const dd = String(end.getDate()).padStart(2, '0')
    currentDateLabel.value = `${formatDate(start, 'YYYY-MM-DD')} - ${mm}-${dd}日`
  } else {
    currentDateLabel.value = `${start.getFullYear()}年${start.getMonth() + 1}月`
  }
}

// 事件配色：按标题 hash 取 8 组渐变之一
const TONES = ['c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7']
function colorTone(str) {
  let h = 0
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0
  return TONES[h % TONES.length]
}

function isImageUrl(url) {
  if (!url) return false
  return /\.(png|jpe?g|gif|webp|bmp|svg)(\?|$)/i.test(url.split('?')[0])
}

// ===== 编辑器操作 =====

function openEditor(data, eventId = null) {
  showInlineEditor.value = true
  isEditing.value = !!eventId
  editingId.value = eventId

  const startDate = data.start_datetime ? new Date(data.start_datetime) : null
  const endDate = data.end_datetime ? new Date(data.end_datetime) : null

  formData.value = {
    ...emptyForm(),
    work_item: data.work_item || '',
    work_content: data.work_content || '',
    participants: Array.isArray(data.participants) ? data.participants : [],
    attachments: Array.isArray(data.attachments) ? data.attachments : [],
    start_datetime: data.start_datetime,
    end_datetime: data.end_datetime,
    // 工作日期不跨天：统一以开始日期为准
    start_date: startDate && !isNaN(startDate) ? formatDate(startDate, 'YYYY-MM-DD') : '',
    end_date: startDate && !isNaN(startDate) ? formatDate(startDate, 'YYYY-MM-DD') : '',
    start_time: data.start_time || '',
    end_time: data.end_time || '',
    time_period: data.time_period || ''
  }

  // 附件列表回显
  fileList.value = (data.attachments || []).map((att, idx) => ({
    name: att.name || `附件${idx + 1}`,
    url: att.url,
    size: att.size || 0,
    uid: `att-${Date.now()}-${idx}`
  }))

  // 计算编辑器位置（窗口顶部居中，向上放避免遮挡操作区）
  nextTick(() => {
    selectionRect.value = {
      left: Math.max(8, Math.round((window.innerWidth - 680) / 2)),
      top: 48
    }
  })
}

function closeEditor() {
  showInlineEditor.value = false
  isEditing.value = false
  editingId.value = null
  formData.value = emptyForm()
  fileList.value = []
  selectionRect.value = null
}

// 是否存在未保存内容
function hasFormContent() {
  const f = formData.value
  return !!(
    (f.work_item && f.work_item.trim()) ||
    (f.work_content && f.work_content.trim()) ||
    (Array.isArray(f.participants) && f.participants.length > 0) ||
    fileList.value.length > 0 ||
    f.start_date || f.start_time || f.end_time
  )
}

// 点击 × / 遮罩 / Esc 关闭：有内容时先弹窗提示保存
async function handleCloseEditor() {
  if (!hasFormContent()) {
    closeEditor()
    return
  }
  try {
    await ElMessageBox.confirm('当前记录尚未保存，是否保存？', '提示', {
      confirmButtonText: '保存',
      cancelButtonText: '不保存',
      type: 'warning',
      distinguishCancelAndClose: true
    })
    await saveEntry() // 确认保存（校验失败时 saveEntry 内部提示且不关闭）
  } catch (action) {
    if (action === 'cancel') closeEditor() // 选择不保存 → 丢弃
    // 点击弹窗右上角 X（'close'）→ 保持编辑
  }
}

// 日期 + 时间 → UTC ISO（与后端/FullCalendar 的存储基准一致）
function buildISODateTime(dateStr, timeStr) {
  if (!dateStr || !timeStr) return ''
  return new Date(`${dateStr}T${timeStr}:00`).toISOString()
}

// 根据当前起止时间重新判断工作时段（上午/下午/自定义）
function refreshTimePeriod() {
  const s = formData.value.start_datetime ? new Date(formData.value.start_datetime) : null
  if (s && !isNaN(s)) {
    formData.value.time_period = determineTimePeriod(s)
  }
}

function onWorkDateChange(val) {
  formData.value.start_date = val
  formData.value.end_date = val // 不跨天
  formData.value.start_datetime = buildISODateTime(val, formData.value.start_time)
  formData.value.end_datetime = buildISODateTime(val, formData.value.end_time)
  refreshTimePeriod()
}

function onStartTimeChange(val) {
  formData.value.start_datetime = buildISODateTime(formData.value.start_date, val)
  refreshTimePeriod()
}

function onEndTimeChange(val) {
  formData.value.end_datetime = buildISODateTime(formData.value.end_date, val)
}

async function saveEntry() {
  if (!formData.value.work_item.trim()) {
    ElMessage.warning('请输入工作事项')
    return
  }

  // 以日期 + 时间重建起止时刻（本地时间 → UTC ISO），用户改过任何一项都生效
  const startDatetime = buildISODateTime(formData.value.start_date, formData.value.start_time) || formData.value.start_datetime
  const endDatetime = buildISODateTime(formData.value.end_date, formData.value.end_time) || formData.value.end_datetime

  if (!startDatetime || !endDatetime) {
    ElMessage.warning('请选择日期和时间范围')
    return
  }

  if (new Date(startDatetime) >= new Date(endDatetime)) {
    ElMessage.warning('结束时间必须晚于开始时间')
    return
  }

  saving.value = true

  try {
    const payload = {
      work_item: formData.value.work_item,
      work_content: formData.value.work_content,
      participants: formData.value.participants,
      attachments: fileList.value
        .filter(f => f.url)
        .map(f => ({ url: f.url, name: f.name, size: f.size || 0 })),
      start_datetime: startDatetime,
      end_datetime: endDatetime,
      time_period: formData.value.time_period
    }

    if (isEditing.value && editingId.value) {
      await workCalendarApi.update(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await workCalendarApi.create(payload)
      ElMessage.success('创建成功')
    }

    closeEditor()
    refreshCalendar()
  } catch (e) {
    console.error('保存失败:', e)
    ElMessage.error(e.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDeleteEntry() {
  if (!editingId.value) return

  try {
    await ElMessageBox.confirm('确定要删除这条工作记录吗？', '确认删除', {
      type: 'warning'
    })

    await workCalendarApi.delete(editingId.value)
    ElMessage.success('删除成功')
    closeEditor()
    refreshCalendar()
  } catch (e) {
    if (e !== 'cancel') {
      console.error('删除失败:', e)
      ElMessage.error(e.response?.data?.message || '删除失败')
    }
  }
}

// ===== 附件上传处理（含 Ctrl+V 粘贴） =====

function handleUploadSuccess(response, file) {
  // 上传接口返回 { code: 0, data: { url, original_name } }
  if (response.code === 0) {
    fileList.value.push({
      url: response.data.url,
      name: response.data.original_name || response.data.name || file.name,
      size: file.size || response.data.size || 0,
      uid: `upload-${Date.now()}-${Math.random().toString(16).slice(2)}`
    })
    ElMessage.success('上传成功')
  } else {
    ElMessage.error(response.message || '上传失败')
  }
}

function handleUploadError(err, file) {
  ElMessage.error(`上传失败：${err?.message || '网络错误'}`)
}

// 剪贴板粘贴图片（复用工作大事记抽屉逻辑）
async function handleClipboardPaste(event) {
  const items = event.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const blob = item.getAsFile()
      if (!blob) continue
      const ext = item.type.split('/')[1] || 'png'
      const filename = `paste-${Date.now()}.${ext}`
      const file = new File([blob], filename, { type: item.type })
      const formData = new FormData()
      formData.append('file', file)
      try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData })
        const data = await res.json()
        if (data.code === 0) {
          fileList.value.push({
            name: filename,
            url: data.data.url,
            size: blob.size || 0,
            uid: `paste-${Date.now()}-${Math.random().toString(16).slice(2)}`
          })
          ElMessage.success('图片已粘贴上传')
        } else {
          ElMessage.error(data.message || '图片上传失败')
        }
      } catch {
        ElMessage.error('图片上传失败')
      }
    }
  }
}

// ---- 文件缩略图辅助 ----
function getFileExt(file) {
  const name = getFileName(file)
  const ext = name.split('.').pop().toLowerCase()
  return ext && ext.length <= 5 ? ext.toUpperCase() : '文件'
}

function getFileName(file) {
  return file.name || (file.url ? file.url.split('/').pop() : '未知文件')
}

function isImageFile(file) {
  const ext = getFileName(file).split('.').pop().toLowerCase()
  return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext) || isImageUrl(file.url || '')
}

function getFilePreviewUrl(file) {
  if (file.url) return file.url
  if (file.raw) return URL.createObjectURL(file.raw)
  return ''
}

function handleThumbRemove(idx) {
  fileList.value.splice(idx, 1)
}

// ===== 视图切换 =====

function switchView(viewName) {
  currentView.value = viewName
  const api = calendarRef.value?.getApi()
  if (api) {
    api.changeView(viewName)
  }
}

function refreshCalendar() {
  const api = calendarRef.value?.getApi()
  if (api) {
    api.refetchEvents()
  }
}

// ===== 快速添加 =====

function handleQuickAdd() {
  const now = new Date()
  const start = new Date(now)
  start.setMinutes(0, 0, 0)
  const end = new Date(start)
  end.setHours(start.getHours() + 1)

  openEditor({
    start_datetime: start.toISOString(),
    end_datetime: end.toISOString(),
    start_time: formatDate(start, 'HH:mm'),
    end_time: formatDate(end, 'HH:mm'),
    time_period: determineTimePeriod(start)
  })
}

// ===== Word 导出（弹窗选区间 + 字段） =====

function openExportDialog() {
  const api = calendarRef.value?.getApi()
  if (api) {
    const start = new Date(api.view.activeStart)
    const end = new Date(api.view.activeEnd)
    end.setDate(end.getDate() - 1) // activeEnd 指向下一天，回退一天
    exportDateRange.value = [formatDate(start, 'YYYY-MM-DD'), formatDate(end, 'YYYY-MM-DD')]
  } else {
    exportDateRange.value = []
  }
  exportFields.value = exportFieldOptions.map(f => f.key)
  exportDialogVisible.value = true
}

async function handleExportWord() {
  if (!exportDateRange.value || exportDateRange.value.length !== 2) {
    ElMessage.warning('请选择导出区间')
    return
  }

  exporting.value = true
  try {
    const [startDate, endDate] = exportDateRange.value
    const blob = await workCalendarApi.exportWord({
      start: new Date(`${startDate}T00:00:00`).toISOString(),
      end: new Date(`${endDate}T23:59:59`).toISOString(),
      fields: exportFields.value
    })

    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `工作日历_${startDate}_至_${endDate}.docx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)

    exportDialogVisible.value = false
    ElMessage.success('导出成功')
  } catch (e) {
    console.error('导出失败:', e)
    ElMessage.error(e.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

// ===== 悬停预览关闭 =====

function handleHoverLeave() {
  hoverStay.value = false
  hoverEvent.value = null
}

// ===== 工作人员列表（参加人员自动补全） =====

async function loadStaffList() {
  try {
    const res = await getDicts()
    if (res.code === 0) {
      staffList.value = (res.data.staff || []).map(s => ({ id: s.id, name: s.name }))
    }
  } catch (e) {
    console.error('加载工作人员列表失败:', e)
  }
}

// ===== 生命周期 =====

function onKeydown(e) {
  if (e.key === 'Escape' && showInlineEditor.value) {
    handleCloseEditor()
  }
}

onMounted(() => {
  loadStaffList()
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
/* ===== 页面骨架：淡雅渐变背景 + 玻璃卡片 ===== */
.work-calendar-page {
  min-height: 100vh;
  background:
    radial-gradient(1100px 500px at 85% -10%, rgba(102, 126, 234, 0.14), transparent 60%),
    radial-gradient(900px 480px at -10% 0%, rgba(118, 75, 162, 0.10), transparent 55%),
    linear-gradient(180deg, #f6f8ff 0%, #eef1f8 100%);
}

.page-body {
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px 20px 40px;
}

.content-card {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(60, 72, 130, 0.10);
  padding: 20px 24px;
}

/* ===== 工具栏（单行） ===== */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.nav-group {
  display: flex;
  gap: 6px;
  margin-left: 4px;
}
.nav-group .el-button {
  width: 34px;
  height: 34px;
  padding: 0;
}

.toolbar-spacer {
  flex: 1;
}

.current-date-label {
  font-size: 16px;
  font-weight: 600;
  color: #2b3350;
  margin-left: 10px;
  letter-spacing: 0.5px;
  background: linear-gradient(90deg, #1a3a5c, #6a4fb0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ===== FullCalendar 定制 ===== */
.work-calendar {
  font-family: '微软雅黑', 'PingFang SC', sans-serif;
}

.work-calendar :deep(.fc-col-header-cell) {
  background: linear-gradient(180deg, #f4f6ff 0%, #e9edfb 100%);
  font-weight: 600;
  color: #2b3350;
  border: none;
  text-align: center;
}

.work-calendar :deep(.fc-timegrid-slot) {
  height: 34px;
}

/* 午休段 5 行（12:00-14:00）：行高压缩为目前的一半 */
.work-calendar :deep(.fc-timegrid-slot.fc-rest-slot) {
  height: 17px !important;
}

/* 时间轴标签：骑在网格线上展示，每半小时一个 */
.work-calendar :deep(.fc-timegrid-slot-label) {
  font-size: 11px;
  color: #8a93a8;
  font-variant-numeric: tabular-nums;
}
.work-calendar :deep(.fc-timegrid-slot-label-frame) {
  position: relative;
  height: 100%;
  display: flex;
  align-items: flex-start;   /* 标签在单元格顶部，再上移一半即骑在网格线上 */
  justify-content: flex-end;
  padding-right: 4px;
}
.work-calendar :deep(.fc-timegrid-slot-label-cushion) {
  transform: translateY(-50%);
  line-height: 1.2;
  white-space: nowrap;
}
/* 首个时间标签（08:30）避免骑出日历顶部 */
.work-calendar :deep(.fc-timegrid-slot[data-time="08:30:00"] .fc-timegrid-slot-label-cushion) {
  transform: none;
}

/* 第一列（时间轴）去掉格子边框与底色，只保留骑线的时间文字 */
.work-calendar :deep(.fc-timegrid-slot-label) {
  border: none !important;
  background: transparent !important;
}

.work-calendar :deep(.fc-scrollgrid) {
  border-color: #e8ebf4;
  border-radius: 8px;
  overflow: hidden;
}

.work-calendar :deep(.fc-theme-standard td),
.work-calendar :deep(.fc-theme-standard th) {
  border-color: #eaedf6;
}

.work-calendar :deep(.fc-day-today) {
  background: rgba(102, 126, 234, 0.06) !important;
}

/* 午休段弱化 */
.work-calendar :deep(.fc-timegrid-slot-lane.fc-rest-lane) {
  background: repeating-linear-gradient(
    -45deg,
    rgba(200, 208, 228, 0.10) 0 6px,
    rgba(255, 255, 255, 0.9) 6px 12px
  );
}

/* ===== 日历事件卡片（多彩渐变） ===== */
.calendar-event-card {
  padding: 4px 8px;
  font-size: 12px;
  color: white;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(60, 60, 110, 0.18);
  border-left: 3px solid rgba(255, 255, 255, 0.35);
}

.calendar-event-card.is-mirror {
  background: rgba(140, 150, 180, 0.25) !important;
  border: 1.5px dashed rgba(120, 130, 165, 0.55) !important;
  box-shadow: none;
  color: #7a84a0;
}
.calendar-event-card.is-mirror .event-title {
  color: #7a84a0;
}

.event-time {
  font-weight: 600;
  font-size: 11px;
  opacity: 0.95;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.event-title {
  font-weight: 500;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.event-participants {
  font-size: 10px;
  opacity: 0.85;
  margin-top: 2px;
}

.event-imgs {
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  opacity: 0.9;
  margin-left: 6px;
}

.ev-c0 { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.ev-c1 { background: linear-gradient(135deg, #36d1dc 0%, #5b86e5 100%); }
.ev-c2 { background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%); }
.ev-c3 { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
.ev-c4 { background: linear-gradient(135deg, #ee9ca7 0%, #ffdde1 100%); }
.ev-c5 { background: linear-gradient(135deg, #4776e6 0%, #8e54e9 100%); }
.ev-c6 { background: linear-gradient(135deg, #f953c6 0%, #b91d73 100%); }
.ev-c7 { background: linear-gradient(135deg, #0ba360 0%, #3cba92 100%); }

/* ===== 悬停预览卡 ===== */
.hover-fade-enter-active,
.hover-fade-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.hover-fade-enter-from,
.hover-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

.event-hover-card {
  position: fixed;
  z-index: 3000;
  width: 320px;
  max-height: 46vh;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 12px;
  box-shadow: 0 12px 34px rgba(40, 50, 100, 0.22);
  border: 1px solid rgba(226, 230, 244, 0.9);
  padding: 12px 14px;
  pointer-events: auto;
}

.hover-time {
  font-size: 12px;
  font-weight: 600;
  color: #6a4fb0;
  margin-bottom: 6px;
}

.hover-title {
  font-size: 14px;
  font-weight: 600;
  color: #232c4d;
}

.hover-content {
  font-size: 12px;
  color: #5a637c;
  margin-top: 6px;
  line-height: 1.6;
  max-height: 96px;
  overflow: hidden;
  white-space: pre-line;
}

.hover-participants {
  font-size: 12px;
  color: #6b7490;
  margin-top: 6px;
}

.hover-images {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.hover-thumb {
  width: 72px;
  height: 72px;
  border-radius: 8px;
  cursor: zoom-in;
  border: 1px solid #e6e9f3;
  background: #f4f6fb;
}

/* ===== 内联编辑器（上移加宽） ===== */
.inline-editor-overlay {
  position: fixed;
  inset: 0;
  z-index: 1999;
  background: rgba(20, 26, 48, 0.35);
  backdrop-filter: blur(2px);
}

.inline-editor-card {
  position: fixed;
  z-index: 2000;
  width: 680px;
  max-height: 92vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(30, 40, 90, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.inline-edit-fade-enter-active,
.inline-edit-fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.inline-edit-fade-enter-from,
.inline-edit-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #5b7fe8 0%, #8a5fd0 100%);
  border-radius: 14px 14px 0 0;
  margin-bottom: 14px;
}

.editor-title {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 1px;
}

.close-btn {
  font-size: 18px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.85);
  transition: color 0.2s, transform 0.2s;
}
.close-btn:hover {
  color: #fff;
  transform: rotate(90deg);
}

.editor-form {
  padding: 0 20px;
  margin-bottom: 14px;
}

.editor-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.time-range-display {
  font-size: 13px;
  color: #5a637c;
  margin-bottom: 8px;
  font-weight: 500;
  background: #f3f5fb;
  border-radius: 6px;
  padding: 6px 10px;
}

/* 工作时段的两个时间编辑框放在同一行 */
.time-range-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.time-picker-item {
  flex: 1;
  min-width: 0;
}
.time-range-sep {
  flex-shrink: 0;
  font-size: 13px;
  color: #8a93a8;
}

.editor-footer {
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid #eceef6;
  background: #fafbfe;
  border-radius: 0 0 14px 14px;
}

/* ===== 附件：上传（半尺寸左对齐）+ 粘贴（右置等高）+ 缩略图 ===== */
.attach-layout {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.upload-wrapper {
  width: 180px; /* 默认拖拽框 360px 宽，压缩为一半 */
  flex-shrink: 0;
}
.upload-wrapper :deep(.el-upload),
.upload-wrapper :deep(.el-upload-dragger) {
  width: 100%;
}
.upload-wrapper :deep(.el-upload-dragger) {
  height: 90px; /* 默认拖拽框 180px 高，压缩为一半 */
  padding: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border-radius: 8px;
}
.upload-wrapper :deep(.el-upload-dragger .el-icon--upload) {
  font-size: 20px;
  line-height: 1;
  margin-bottom: 2px;
}
.upload-wrapper :deep(.el-upload-dragger .el-upload__text) {
  font-size: 12px;
  line-height: 1.3;
  color: #6b7490;
}

.file-thumbnail-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.file-thumb-card {
  width: 96px;
}

.thumb-preview {
  position: relative;
  width: 96px;
  height: 72px;
  border-radius: 8px;
  overflow: hidden;
  background: #f1f3fa;
  border: 1px solid #e6e9f3;
}

.thumb-img {
  width: 100%;
  height: 100%;
}

.thumb-generic {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: #8a93a8;
  font-size: 10px;
  font-weight: 600;
}

.thumb-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(20, 26, 48, 0.55);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 11px;
  transition: background 0.2s;
}
.thumb-remove:hover {
  background: rgba(220, 60, 80, 0.9);
}

.thumb-name {
  font-size: 11px;
  color: #6b7490;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
}

.paste-zone {
  flex: 1;
  height: 90px; /* 与压缩后的附件框高度一致 */
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border: 1.5px dashed #b9c3e8;
  border-radius: 10px;
  color: #5f6eb5;
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.06), rgba(138, 95, 208, 0.06));
  cursor: pointer;
  outline: none;
  transition: all 0.2s;
}
.paste-zone:hover,
.paste-zone:focus {
  border-color: #667eea;
  color: #4658c8;
  background: rgba(102, 126, 234, 0.10);
}
.paste-icon {
  display: flex;
  font-size: 20px;
}
.paste-label {
  font-size: 13px;
  font-weight: 600;
}
.paste-hint {
  font-size: 12px;
  margin-left: auto;
  color: inherit;
  opacity: 0.75;
}
.paste-zone kbd {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid #cfd6ee;
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 11px;
  font-family: inherit;
}

/* ===== 导出弹窗 ===== */
.export-dialog-body {
  padding: 4px 2px;
}
.export-field-title {
  font-size: 13px;
  font-weight: 600;
  color: #3a4468;
  margin-bottom: 8px;
}
.export-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 18px;
  padding: 8px 12px;
  background: #f6f8fe;
  border-radius: 8px;
}
.export-fields-hint {
  font-size: 12px;
  color: #9aa3b8;
  margin-top: 8px;
}

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .inline-editor-card {
    width: 94vw;
    left: 3vw !important;
    top: 4vh !important;
  }
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .toolbar-spacer {
    display: none;
  }
  .attach-layout {
    flex-direction: column;
  }
  .upload-wrapper {
    width: 100%;
  }
  .paste-zone {
    width: 100%;
  }
}
</style>