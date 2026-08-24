<!-- WorkCalendarView.vue: 工作日历 - 周/月视图 + 内联编辑 + Word导出 -->
<template>
  <div class="work-calendar-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 工具栏 -->
        <div class="toolbar">
          <el-button-group>
            <el-button 
              :type="currentView === 'timeGridWeek' ? 'primary' : ''" 
              @click="switchView('timeGridWeek')"
            >
              周视图
            </el-button>
            <el-button 
              :type="currentView === 'dayGridMonth' ? 'primary' : ''" 
              @click="switchView('dayGridMonth')"
            >
              月视图
            </el-button>
          </el-button-group>
          
          <el-button @click="calendarRef?.getApi()?.prev()">上一{{ currentView === 'timeGridWeek' ? '周' : '月' }}</el-button>
          <el-button @click="calendarRef?.getApi()?.today()">今天</el-button>
          <el-button @click="calendarRef?.getApi()?.next()">下一{{ currentView === 'timeGridWeek' ? '周' : '月' }}</el-button>
          
          <span class="current-date-label">{{ currentDateLabel }}</span>
          
          <div class="toolbar-spacer" />
          
          <el-button type="success" @click="handleExportWord" :loading="exporting">
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
    
    <!-- 内联编辑浮层（全屏遮罩 + 悬浮卡片，点击外部或 Esc 关闭） -->
    <Teleport to="body">
      <transition name="inline-edit-fade">
        <div 
          v-if="showInlineEditor" 
          class="inline-editor-overlay"
          @click.self="closeEditor"
        >
          <div class="inline-editor-card" :style="editorPosition" @mousedown.stop>
            <div class="editor-header">
              <span class="editor-title">{{ isEditing ? '编辑工作记录' : '新建工作记录' }}</span>
              <el-icon class="close-btn" @click="closeEditor"><Close /></el-icon>
            </div>
            
            <el-form :model="formData" label-position="top" size="small" class="editor-form">
              <el-form-item label="工作日期">
                <el-date-picker
                  v-model="formData.start_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="开始日期"
                  style="width: 45%; margin-right: 4px;"
                  @change="onStartDateChange"
                />
                <el-date-picker
                  v-model="formData.end_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="结束日期"
                  style="width: 45%;"
                  @change="onEndDateChange"
                />
              </el-form-item>

              <el-form-item label="工作时段">
                <div class="time-range-display">
                  {{ formatTimeRange(formData.start_datetime, formData.end_datetime) }}
                </div>
                <!-- 时间选择器 -->
                <el-time-picker
                  v-model="formData.start_time"
                  format="HH:mm"
                  value-format="HH:mm"
                  placeholder="开始时间"
                  style="width: 45%; margin-right: 4px;"
                  @change="onStartTimeChange"
                />
                <el-time-picker
                  v-model="formData.end_time"
                  format="HH:mm"
                  value-format="HH:mm"
                  placeholder="结束时间"
                  style="width: 45%;"
                  @change="onEndTimeChange"
                />
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
                  :rows="3"
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
                <el-upload
                  :action="uploadUrl"
                  :on-success="handleUploadSuccess"
                  :on-remove="handleUploadRemove"
                  :file-list="attachmentFileList"
                  multiple
                  drag
                  :limit="10"
                >
                  <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                  <div class="el-upload__text">拖拽或点击上传（最多10个）</div>
                </el-upload>
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
import { Close, UploadFilled, Plus, Document } from '@element-plus/icons-vue'
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
const exporting = ref(false)
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

// ===== 附件上传 =====
const attachmentFileList = ref([])
// 后端路由为 POST /api/upload（api_bp url_prefix=/api + /upload）
const uploadUrl = '/api/upload'

// ===== 工作人员列表（用于自动补全） =====
const staffList = ref([])

// ===== 编辑器位置 =====
const editorPosition = computed(() => {
  if (!selectionRect.value) return { display: 'none' }
  return {
    left: `${selectionRect.value.left}px`,
    top: `${selectionRect.value.top}px`,
    display: 'block'
  }
})

// ===== 日历配置 =====
const calendarOptions = ref({
  plugins: [timeGridPlugin, dayGridPlugin, interactionPlugin],
  initialView: 'timeGridWeek',
  locale: zhLocale,
  firstDay: 1, // 周一为第一天
  slotMinTime: '08:00:00',
  slotMaxTime: '18:30:00',
  slotDuration: '00:30:00', // 30分钟一格
  allDaySlot: false,
  height: 'auto',
  contentHeight: 700,
  expandRows: true,
  
  // 启用时间选择
  selectable: true,
  selectMirror: true,
  
  // 周视图配置
  timeGridWeek: {
    slotLabelFormat: 'HH:mm',
    eventTimeFormat: 'HH:mm',
    titleFormat: 'YYYY年MM月DD日',
  },
  
  // 月视图配置
  dayGridMonth: {
    eventDisplay: 'block',
    titleFormat: 'YYYY年MM月',
  },
  
  // 事件重叠允许
  eventOverlap: true,
  
  // 选择事件（拖拽选择时间段后触发）
  select: (info) => {
    if (info.allDay) {
      // 月视图/全天选择的守卫：工作日历要求具体时段，避免产生无时间数据
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
      time_period: determineTimePeriod(startDate, endDate)
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
  
  // 自定义事件渲染（所有用户文本经 escapeHtml，防 XSS）
  eventContent: (arg) => {
    const { event } = arg
    const props = event.extendedProps
    const startTime = formatDate(new Date(props.start_datetime), 'HH:mm')
    const endTime = formatDate(new Date(props.end_datetime), 'HH:mm')

    let participantsHtml = ''
    if (props.participants && props.participants.length > 0) {
      const names = props.participants.slice(0, 2).map(escapeHtml).join(', ')
      const more = props.participants.length > 2 ? ` +${props.participants.length - 2}` : ''
      participantsHtml = `<div class="event-participants">👥 ${names}${more}</div>`
    }

    return {
      html: `
        <div class="calendar-event-card">
          <div class="event-time">${startTime}-${endTime}</div>
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

function determineTimePeriod(startDate, endDate) {
  const hour = startDate.getHours()
  if (hour >= 8 && hour < 12) return 'morning'
  if (hour >= 14 && hour < 18) return 'afternoon'
  return 'custom'
}

function updateDateLabel(dateInfo) {
  const start = new Date(dateInfo.start)
  const end = new Date(dateInfo.end)
  
  if (currentView.value === 'timeGridWeek') {
    currentDateLabel.value = `${formatDate(start, 'YYYY-MM-DD')} 至 ${formatDate(end, 'YYYY-MM-DD')}`
  } else {
    currentDateLabel.value = `${start.getFullYear()}年${start.getMonth() + 1}月`
  }
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
    start_date: startDate && !isNaN(startDate) ? formatDate(startDate, 'YYYY-MM-DD') : '',
    end_date: endDate && !isNaN(endDate) ? formatDate(endDate, 'YYYY-MM-DD') : '',
    start_time: data.start_time || '',
    end_time: data.end_time || '',
    time_period: data.time_period || ''
  }
  
  // 更新附件列表显示
  attachmentFileList.value = (data.attachments || []).map((att, idx) => ({
    name: att.name || `附件${idx + 1}`,
    url: att.url
  }))
  
  // 计算编辑器位置（在选择区域旁边弹出）
  nextTick(() => {
    // $el 可能是组件代理而非 DOM 元素，先做 Element 判定，失败则按窗口居中兜底
    const calendarEl = calendarRef.value?.$el
    let left = window.innerWidth / 2 - 210
    let top = 100
    if (calendarEl instanceof Element) {
      const rect = calendarEl.getBoundingClientRect()
      left = rect.left + rect.width / 2 - 200
      top = rect.top + 100
    }
    selectionRect.value = { left, top }
  })
}

function closeEditor() {
  showInlineEditor.value = false
  isEditing.value = false
  editingId.value = null
  formData.value = emptyForm()
  attachmentFileList.value = []
  selectionRect.value = null
}

// 日期 + 时间 → UTC ISO（与后端/FullCalendar 的存储基准一致）
function buildISODateTime(dateStr, timeStr) {
  if (!dateStr || !timeStr) return ''
  return new Date(`${dateStr}T${timeStr}:00`).toISOString()
}

// 根据当前起止时间重新判断工作时段（上午/下午/自定义）
function refreshTimePeriod() {
  const s = formData.value.start_datetime ? new Date(formData.value.start_datetime) : null
  const e = formData.value.end_datetime ? new Date(formData.value.end_datetime) : null
  if (s && e && !isNaN(s) && !isNaN(e)) {
    formData.value.time_period = determineTimePeriod(s, e)
  }
}

function onStartDateChange(val) {
  formData.value.start_datetime = buildISODateTime(val, formData.value.start_time)
  refreshTimePeriod()
}

function onEndDateChange(val) {
  formData.value.end_datetime = buildISODateTime(val, formData.value.end_time)
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
      attachments: formData.value.attachments,
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

// ===== 附件上传处理 =====

function handleUploadSuccess(response, file, fileList) {
  // 上传接口返回 { code: 0, data: { url, original_name } }
  if (response.code === 0) {
    formData.value.attachments.push({
      url: response.data.url,
      name: response.data.original_name || response.data.name || file.name,
      size: file.size || response.data.size || 0
    })
    ElMessage.success('上传成功')
  } else {
    ElMessage.error(response.message || '上传失败')
  }
}

function handleUploadRemove(file, fileList) {
  // 新上传文件的地址在 file.response.data.url；回显的存量附件在 file.url
  const url = file.response?.data?.url || file.url
  const index = formData.value.attachments.findIndex(att => att.url === url)
  if (index !== -1) {
    formData.value.attachments.splice(index, 1)
  }
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
    time_period: determineTimePeriod(start, end)
  })
}

// ===== Word 导出 =====

async function handleExportWord() {
  const api = calendarRef.value?.getApi()
  if (!api) return
  
  const viewStart = api.view.activeStart
  const viewEnd = api.view.activeEnd
  
  try {
    exporting.value = true
    
    const blob = await workCalendarApi.exportWord({
      start: viewStart.toISOString(),
      end: viewEnd.toISOString()
    })
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const startStr = formatDate(viewStart, 'YYYY-MM-DD')
    const endStr = formatDate(viewEnd, 'YYYY-MM-DD')
    a.download = `工作日历_${startStr}_至_${endStr}.docx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (e) {
    console.error('导出失败:', e)
    ElMessage.error(e.message || '导出失败')
  } finally {
    exporting.value = false
  }
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
    closeEditor()
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
.work-calendar-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.page-body {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
}

.content-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.toolbar-spacer {
  flex: 1;
}

.current-date-label {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-left: 12px;
}

/* FullCalendar 自定义样式 */
.work-calendar {
  font-family: '微软雅黑', sans-serif;
}

.work-calendar :deep(.fc-col-header-cell) {
  background: #f0f2f5;
  font-weight: 600;
}

.work-calendar :deep(.fc-timegrid-slot) {
  height: 40px;
}

.work-calendar :deep(.fc-event) {
  border: none;
  border-radius: 4px;
  margin: 2px 0;
}

/* 日历事件卡片 */
.calendar-event-card {
  padding: 4px 6px;
  font-size: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 4px;
  overflow: hidden;
}

.event-time {
  font-weight: 600;
  font-size: 11px;
  opacity: 0.9;
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
  opacity: 0.8;
  margin-top: 2px;
}

/* 内联编辑器浮层（全屏遮罩，点击外部关闭） */
.inline-editor-overlay {
  position: fixed;
  inset: 0;
  z-index: 1999;
  background: rgba(0, 0, 0, 0.25);
}

/* 悬浮卡片（定位由 editorPosition 控制） */
.inline-editor-card {
  position: fixed;
  z-index: 2000;
  background: white;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  width: 420px;
  max-height: 80vh;
  overflow-y: auto;
  padding: 16px;
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

.inline-editor-card {
  padding: 16px;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.editor-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.close-btn {
  font-size: 20px;
  cursor: pointer;
  color: #909399;
  transition: color 0.2s;
}

.close-btn:hover {
  color: #f56c6c;
}

.editor-form {
  margin-bottom: 16px;
}

.time-range-display {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
  font-weight: 500;
}

.editor-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

/* 响应式 */
@media (max-width: 768px) {
  .inline-editor-card {
    width: 90vw;
    left: 5vw !important;
    top: 10vh !important;
  }
  
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .toolbar-spacer {
    display: none;
  }
}
</style>
