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
          @mouseenter="handleHoverEnter"
          @mouseleave="handleHoverLeave"
        >
          <div class="hover-time">
            {{ formatTimeRange(hoverEvent.start_datetime, hoverEvent.end_datetime) }}
          </div>
          <div v-if="hoverTagName" class="hover-tag">
            🏷 {{ hoverTagName }}
          </div>
          <div class="hover-title">{{ hoverEvent.work_item || '未命名' }}</div>
          <div v-if="hoverEvent.work_content" class="hover-content">{{ hoverEvent.work_content }}</div>
          <div v-if="hoverEvent.participants && hoverEvent.participants.length" class="hover-participants">
            👥 {{ hoverEvent.participants.join('、') }}
          </div>
          <div class="hover-actions">
            <el-button size="small" type="primary" plain @click.stop="openEditorFromHover">✎ 编辑</el-button>
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

              <el-form-item label="标签">
                <el-radio-group v-model="formData.tags">
                  <el-radio
                    v-for="tag in tagOptions"
                    :key="tag.code"
                    :value="tag.code"
                  >{{ tag.name }}</el-radio>
                  <el-radio :value="''">无</el-radio>
                </el-radio-group>
              </el-form-item>

              <el-form-item>
                <span class="sync-ledger-check">
                  <el-checkbox v-model="formData.sync_to_ledger">同步写入工作大事记</el-checkbox>
                </span>
                <div class="sync-ledger-hint">勾选后，本条工作记录将同步展示在工作大事记中</div>
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
              <el-button
                v-if="isEditing && businessAuth.hasPermission('work_calendar', 'delete')"
                type="danger"
                @click="handleDeleteEntry"
              >删除</el-button>
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
  tags: '',  // 动态标签（单选，存 code，如 'activity_tag_meeting'）
  attachments: [],
  start_datetime: '',
  end_datetime: '',
  start_date: '',
  end_date: '',
  start_time: '',
  end_time: '',
  time_period: '',
  sync_to_ledger: false
})

const formData = ref(emptyForm())

// ===== 附件上传（含 Ctrl+V 粘贴，复用工作大事记交互） =====
// 后端路由为 POST /api/upload（api_bp url_prefix=/api + /upload）
const uploadUrl = '/api/upload'
// 附件列表：{ name, url, size, uid }
const fileList = ref([])

// ===== 工作人员列表（用于自动补全） =====
const staffList = ref([])

// ===== 动态标签字典（表单标签单选，复用 activity_tag_dict） =====
const tagOptions = ref([])

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
// 悬停源的几何信息（用事件卡 DOM 的 rect，而不是鼠标坐标）
const hoverPos = ref({ left: 0, right: 0, top: 0 })
const hoverStay = ref(false)
// 悬停卡宽度（与 .event-hover-card 的 width 保持一致）与「贴边重叠」像素
const HOVER_CARD_WIDTH = 320
const HOVER_CARD_OVERLAP = 2
// 延迟关闭只保留一个定时器：每次显示 / 进入卡片前先清掉，
// 否则旧定时器会在新卡片刚出现时把它关掉（表现为「一闪而过」）
let hoverHideTimer = null

function clearHoverHideTimer() {
  if (hoverHideTimer) {
    clearTimeout(hoverHideTimer)
    hoverHideTimer = null
  }
}

function scheduleHoverHide(delay = 160) {
  clearHoverHideTimer()
  hoverHideTimer = setTimeout(() => {
    hoverHideTimer = null
    if (!hoverStay.value) hoverEvent.value = null
  }, delay)
}

function showHoverCard(props, id) {
  clearHoverHideTimer()
  hoverEvent.value = { ...props, id }
}

const hoverImages = computed(() => {
  const atts = hoverEvent.value?.attachments || []
  return atts.filter(a => a && a.url && isImageUrl(a.url))
})

// 悬停卡/事件卡标签名称（复用动态标签字典）
function tagNameOf(tags) {
  if (!Array.isArray(tags) || !tags.length) return ''
  const hit = tagOptions.value.find(t => t.code === tags[0])
  return hit ? hit.name : ''
}

const hoverTagName = computed(() => tagNameOf(hoverEvent.value?.tags))

// 悬停卡定位：优先贴事件卡右侧，右侧放不下则向左展开；
// 两种方向都让卡片与事件卡重叠 2px —— 指针从事件卡横向移出时直接进入悬停卡，
// 不会先掠过紧挨着的相邻事项（那会触发相邻事项的 mouseenter，把卡片挤走/闪掉）。
const hoverStyle = computed(() => {
  const p = hoverPos.value
  const vw = window.innerWidth
  const vh = window.innerHeight
  const margin = 8

  let left
  if (p.right + HOVER_CARD_WIDTH - HOVER_CARD_OVERLAP + margin <= vw) {
    left = p.right - HOVER_CARD_OVERLAP
  } else if (p.left - HOVER_CARD_WIDTH + HOVER_CARD_OVERLAP - margin >= 0) {
    left = p.left + HOVER_CARD_OVERLAP - HOVER_CARD_WIDTH
  } else {
    // 两侧都不够：贴住视口并夹紧，保证整卡可见（不再被挤出屏幕）
    left = Math.max(margin, Math.min(p.right - HOVER_CARD_WIDTH, vw - HOVER_CARD_WIDTH - margin))
  }

  const top = Math.max(margin, Math.min(p.top, vh - 240))
  return { left: `${Math.round(left)}px`, top: `${Math.round(top)}px` }
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
  // 允许在已有事件覆盖的时间区间内继续拖选新建（不打断原有下拉交互）
  selectAllow: (info) => {
    if (!info.allDay) return true
    return false
  },

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

  // 点击已有事件：不直接弹编辑框（编辑走卡上 ✎ 按钮），仅停留悬浮预览，避免打断拖选新建流程
  eventClick: (info) => {
    const props = info.event.extendedProps
    if (!props.start_datetime) return
    hoverStay.value = false
    showHoverCard(props, info.event.id)
  },

  // 悬停预览
  eventMouseEnter: (info, jsEvent) => {
    const props = info.event.extendedProps
    if (!props.start_datetime) return // 拖选 mirror 不预览

    // 同一张事件卡重复 mouseenter（悬停卡覆盖相邻事项时浏览器会重放）：
    // 只取消待关闭定时器，不重排位置、不重置停留态，避免卡片抖动/闪退
    if (hoverEvent.value && String(hoverEvent.value.id) === String(info.event.id)) {
      clearHoverHideTimer()
      return
    }

    hoverStay.value = false
    showHoverCard(props, info.event.id)

    // 用事件卡 DOM 位置定位：jsEvent.clientX/Y 在 FullCalendar 事件回调里可能为 0(undefined)，
    // 导致悬停卡 fixed 定位到左上角；getBoundingClientRect 始终可靠
    const el = info.el
    const rect = el && typeof el.getBoundingClientRect === 'function' ? el.getBoundingClientRect() : null
    if (rect && rect.width > 0) {
      hoverPos.value = { left: rect.left, right: rect.right, top: rect.top }
    } else {
      const x = jsEvent ? jsEvent.clientX : 0
      const y = jsEvent ? jsEvent.clientY : 0
      hoverPos.value = { left: x, right: x, top: y }
    }
  },
  eventMouseLeave: () => {
    // 延迟关闭，给指针留出移入悬停卡的时间（定时器全局唯一，不会互相抢）
    scheduleHoverHide()
  },

  // 自定义事件渲染（浅色滤镜：同一时段多事项可并存互不遮挡；按标签/事项分色）
  eventContent: (arg) => {
    const { event } = arg
    const props = event.extendedProps

    // 拖选预览（mirror）事件：无真实数据，渲染淡色占位，不出现 NaN/未命名
    if (!props.start_datetime) {
      return { html: '<div class="calendar-event-card is-mirror"><div class="event-title">新记录</div></div>' }
    }

    const startTime = formatDate(new Date(props.start_datetime), 'HH:mm')
    const endTime = formatDate(new Date(props.end_datetime), 'HH:mm')
    // 类型色调：优先按动态标签映射；无标签回退标题 hash 色
    const tagCode = Array.isArray(props.tags) && props.tags.length ? props.tags[0] : ''
    const tone = TAG_TONE_MAP[tagCode] || colorTone(props.work_item || '')

    let participantsHtml = ''
    if (props.participants && props.participants.length > 0) {
      const names = props.participants.slice(0, 2).map(escapeHtml).join(', ')
      const more = props.participants.length > 2 ? ` +${props.participants.length - 2}` : ''
      participantsHtml = `<div class="event-participants">👥 ${names}${more}</div>`
    }

    const imgCount = (props.attachments || []).filter(a => a && isImageUrl(a.url)).length
    const imgHtml = imgCount > 0 ? `<div class="event-imgs">🖼 ${imgCount}</div>` : ''

    const tagName = tagNameOf(props.tags)
    const tagHtml = tagName ? `<div class="event-tag-badge">🏷 ${escapeHtml(tagName)}</div>` : ''

    const contentHtml = props.work_content
      ? `<div class="event-content">${escapeHtml(props.work_content)}</div>`
      : ''

    return {
      html: `
        <div class="calendar-event-card ev-${tone}">
          <span class="event-color-bar"></span>
          <div class="event-time">${startTime}-${endTime}${imgHtml}</div>
          ${tagHtml}
          <div class="event-title">${escapeHtml(event.title || '未命名')}</div>
          ${contentHtml}
          ${participantsHtml}
        </div>
      `
    }
  },

  // 事件挂载：本版事件卡采用 hover 预览卡触发编辑（见 hover 卡「✎ 编辑」按钮）
  eventDidMount: () => {},

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
    // 周视图标题：2026年9月7日--9月14日（结束只展示 月日）
    const startLabel = `${start.getFullYear()}年${start.getMonth() + 1}月${start.getDate()}日`
    const endLabel = `${end.getMonth() + 1}月${end.getDate()}日`
    currentDateLabel.value = `${startLabel}--${endLabel}`
  } else {
    currentDateLabel.value = `${start.getFullYear()}年${start.getMonth() + 1}月`
  }
}

// 事件配色：优先按动态标签映射色调；无标签回退标题 hash 取 8 组之一
const TAG_TONE_MAP = {
  activity_tag_waichu: 'tag-g',   // 外出考察 → 绿
  activity_tag_daofang: 'tag-b',  // 到访接待 → 蓝
  activity_tag_shipin: 'tag-o',   // 食品企业走进农高区活动 → 橙
  activity_tag_diaodu: 'tag-p',   // 调度推进 → 紫
  activity_tag_meeting: 'tag-c',  // 参加会议 → 青
}
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
    time_period: data.time_period || '',
    tags: Array.isArray(data.tags) && data.tags.length ? data.tags[0] : '',
    sync_to_ledger: !!data.ledger_id
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

// 悬浮预览卡 → 编辑（hoverEvent 已带 id）
function openEditorFromHover() {
  const h = hoverEvent.value
  if (!h || !h.id) return
  clearHoverHideTimer()
  hoverEvent.value = null
  hoverStay.value = false
  const startDate = h.start_datetime ? new Date(h.start_datetime) : null
  const endDate = h.end_datetime ? new Date(h.end_datetime) : null
  openEditor({
    ...h,
    start_time: startDate && !isNaN(startDate) ? formatDate(startDate, 'HH:mm') : '',
    end_time: endDate && !isNaN(endDate) ? formatDate(endDate, 'HH:mm') : ''
  }, h.id)
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
      tags: formData.value.tags ? [formData.value.tags] : [],
      attachments: fileList.value
        .filter(f => f.url)
        .map(f => ({ url: f.url, name: f.name, size: f.size || 0 })),
      start_datetime: startDatetime,
      end_datetime: endDatetime,
      time_period: formData.value.time_period,
      sync_to_ledger: formData.value.sync_to_ledger
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

// 指针进入悬停卡：取消待关闭定时器并标记「停留」，卡片可长期展示、可点编辑/看大图
function handleHoverEnter() {
  hoverStay.value = true
  clearHoverHideTimer()
}

function handleHoverLeave() {
  hoverStay.value = false
  clearHoverHideTimer()
  hoverEvent.value = null
}

// ===== 工作人员列表（参加人员自动补全） =====

async function loadStaffList() {
  try {
    const res = await getDicts()
    if (res.code === 0) {
      staffList.value = (res.data.staff || []).map(s => ({ id: s.id, name: s.name }))
      tagOptions.value = res.data.activity_tags || []
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
  clearHoverHideTimer()
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

/* 事件容器：去掉 FullCalendar 默认不透明深蓝背景，颜色完全由自定义浅色卡片呈现 */
.work-calendar :deep(.fc-event) {
  background: transparent !important;
  border-color: transparent !important;
  box-shadow: none !important;
}
.work-calendar :deep(.fc-timegrid-event),
.work-calendar :deep(.fc-daygrid-event) {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin: 0 !important;
}
.work-calendar :deep(.fc-event-main) {
  padding: 0;
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

/* ===== 日历事件卡片（类型色打底：同一时段可并存多事项，互不遮挡） =====
   ⚠️ 全部规则必须带 :deep()：eventContent 返回的是 HTML 字符串，由 FullCalendar 直接 innerHTML
   注入，元素上不带 Vue scoped 的 data-v 属性；若直接写 .calendar-event-card {...}，编译后为
   .calendar-event-card[data-v-xxx]，永远命中不了 —— 这正是历史版本「卡片几乎看不到」的真因
   （底色/边框/文字色全部未生效，白字落在透明底上，只剩 emoji 可见）。 */
.work-calendar :deep(.calendar-event-card) {
  position: relative;
  padding: 4px 8px 4px 10px;
  font-size: 12px;
  line-height: 1.35;
  color: #1b2540;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(60, 60, 110, 0.14);
  /* 兜底底色（无色调类时）：浅色卡面 + 深色文字 */
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(120, 138, 190, 0.62);
}

/* 左侧色条按色调区分 */
.work-calendar :deep(.calendar-event-card .event-color-bar) {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 3px 0 0 3px;
}

/* 拖选中的占位卡 */
.work-calendar :deep(.calendar-event-card.is-mirror) {
  background: rgba(140, 150, 180, 0.34) !important;
  border: 1.5px dashed rgba(110, 122, 160, 0.72) !important;
  box-shadow: none;
  color: #5f6984;
}
.work-calendar :deep(.calendar-event-card.is-mirror .event-title) {
  color: #5f6984;
}

.work-calendar :deep(.event-time) {
  font-weight: 700;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #2c3a5e;
}

.work-calendar :deep(.event-title) {
  font-weight: 700;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #131c36;
}

.work-calendar :deep(.event-content) {
  font-size: 11px;
  color: #3a4867;
  margin-top: 2px;
  /* 内容只展示一部分：最多两行，超出省略号缩略 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
}

.work-calendar :deep(.event-participants) {
  font-size: 10px;
  margin-top: 2px;
  color: #46527a;
}

.work-calendar :deep(.event-imgs) {
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  margin-left: 6px;
  color: #46527a;
}

.work-calendar :deep(.event-tag-badge) {
  display: inline-block;
  font-size: 10px;
  color: #2b3a55;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(105, 125, 180, 0.55);
  border-radius: 8px;
  padding: 0 6px;
  margin-top: 3px;
  line-height: 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  vertical-align: middle;
}

/* 色调（无标签 fallback）：类型色半透明打底整卡（底 alpha 0.36 / 边框 0.72，清晰可辨） */
.work-calendar :deep(.ev-c0) { background: rgba(102, 126, 234, 0.36); border-color: rgba(102, 126, 234, 0.72); }
.work-calendar :deep(.ev-c1) { background: rgba(54, 209, 220, 0.38); border-color: rgba(30, 186, 197, 0.78); }
.work-calendar :deep(.ev-c2) { background: rgba(247, 151, 30, 0.36); border-color: rgba(247, 151, 30, 0.72); }
.work-calendar :deep(.ev-c3) { background: rgba(17, 153, 142, 0.36); border-color: rgba(17, 153, 142, 0.72); }
.work-calendar :deep(.ev-c4) { background: rgba(238, 156, 167, 0.42); border-color: rgba(224, 108, 126, 0.78); }
.work-calendar :deep(.ev-c5) { background: rgba(71, 118, 230, 0.36); border-color: rgba(71, 118, 230, 0.72); }
.work-calendar :deep(.ev-c6) { background: rgba(249, 83, 198, 0.34); border-color: rgba(249, 83, 198, 0.72); }
.work-calendar :deep(.ev-c7) { background: rgba(11, 163, 96, 0.36); border-color: rgba(11, 163, 96, 0.72); }

/* 标签类型专属色调（内置配色）：外出考察→绿、到访接待→蓝、食品活动→橙、调度推进→紫、参加会议→青 */
.work-calendar :deep(.ev-tag-g) { background: rgba(76, 175, 80, 0.36); border-color: rgba(56, 142, 60, 0.78); }
.work-calendar :deep(.ev-tag-b) { background: rgba(66, 133, 244, 0.36); border-color: rgba(66, 133, 244, 0.76); }
.work-calendar :deep(.ev-tag-o) { background: rgba(255, 152, 0, 0.38); border-color: rgba(230, 126, 0, 0.80); }
.work-calendar :deep(.ev-tag-p) { background: rgba(156, 39, 176, 0.34); border-color: rgba(156, 39, 176, 0.74); }
.work-calendar :deep(.ev-tag-c) { background: rgba(0, 172, 193, 0.36); border-color: rgba(0, 143, 160, 0.78); }

/* 左侧色条颜色（与色调一致，实色） */
.work-calendar :deep(.ev-c0 .event-color-bar) { background: #667eea; }
.work-calendar :deep(.ev-c1 .event-color-bar) { background: #12b3bf; }
.work-calendar :deep(.ev-c2 .event-color-bar) { background: #f7971e; }
.work-calendar :deep(.ev-c3 .event-color-bar) { background: #11998e; }
.work-calendar :deep(.ev-c4 .event-color-bar) { background: #e06c7e; }
.work-calendar :deep(.ev-c5 .event-color-bar) { background: #4776e6; }
.work-calendar :deep(.ev-c6 .event-color-bar) { background: #f953c6; }
.work-calendar :deep(.ev-c7 .event-color-bar) { background: #0ba360; }
.work-calendar :deep(.ev-tag-g .event-color-bar) { background: #388e3c; }
.work-calendar :deep(.ev-tag-b .event-color-bar) { background: #4285f4; }
.work-calendar :deep(.ev-tag-o .event-color-bar) { background: #e67e00; }
.work-calendar :deep(.ev-tag-p .event-color-bar) { background: #9c27b0; }
.work-calendar :deep(.ev-tag-c .event-color-bar) { background: #008fa0; }

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

.hover-tag {
  font-size: 12px;
  color: #3c5a9e;
  margin-top: 6px;
}

.hover-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
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

/* 同步写入工作大事记 勾选框 */
.sync-ledger-check {
  display: inline-flex;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
  color: #1a3a5c;
}
.sync-ledger-hint {
  font-size: 12px;
  color: #8a93a8;
  margin-top: 2px;
  line-height: 1.4;
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