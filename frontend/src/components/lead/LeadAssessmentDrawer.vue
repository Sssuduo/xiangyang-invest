<template>
  <el-drawer v-model="visible" direction="rtl" size="780px" @closed="handleClosed">
    <template #header>
      <div class="drawer-title-bar">
        <span class="drawer-title">
          <el-icon><Cpu /></el-icon>
          AI 研判 · {{ leadName }}
        </span>
      </div>
    </template>

    <div class="assess-drawer-body">
      <!-- ====== 工具栏 ====== -->
      <div class="assess-toolbar">
        <el-select v-model="selectedModelId" placeholder="选择AI模型" size="default" style="width: 240px;">
          <el-option v-for="m in modelList" :key="m.id" :label="m.name" :value="m.id" />
        </el-select>
        <el-button type="primary" @click="generateReport" :loading="assessLoading" :disabled="assessLoading">
          <el-icon><Document /></el-icon>
          {{ assessLoading ? '正在生成报告...' : '生成项目分析报告' }}
        </el-button>
        <el-tooltip content="复制当前使用的完整提示词（含项目信息+知识库）" placement="bottom">
          <el-button @click="copyPrompt" :loading="copyPromptLoading">
            <el-icon><CopyDocument /></el-icon> 一键复制提示词
          </el-button>
        </el-tooltip>
        <div class="toolbar-spacer" />
        <!-- 历史会话列表 -->
        <el-select
          v-if="sessionList.length > 0"
          v-model="currentSessionId"
          placeholder="历史研判会话"
          size="default"
          style="width: 200px;"
          @change="switchSession"
        >
          <el-option
            v-for="s in sessionList"
            :key="s.id"
            :label="formatSessionLabel(s)"
            :value="s.id"
          />
        </el-select>
      </div>

      <!-- ====== 消息区域 ====== -->
      <div class="assess-messages" ref="messagesContainer">
        <!-- 空状态 -->
        <div v-if="!currentSessionId && !assessLoading" class="assess-empty">
          <el-icon class="empty-icon"><Cpu /></el-icon>
          <p class="empty-title">AI 项目分析研判</p>
          <p class="empty-desc">选择 AI 模型，点击「生成项目分析报告」开始智能研判</p>
          <p class="empty-hint">分析报告将以 Word 文档形式呈现，可下载保存</p>
        </div>

        <!-- 消息列表 -->
        <template v-for="msg in messages" :key="msg.id">
          <div :class="['msg-row', msg.role === 'user' ? 'msg-user' : 'msg-ai']">
            <div class="msg-avatar">
              <el-icon v-if="msg.role === 'user'"><User /></el-icon>
              <el-icon v-else><Cpu /></el-icon>
            </div>
            <div class="msg-body">
              <div class="msg-header">
                <span class="msg-role">{{ msg.role === 'user' ? '提问' : 'AI 研判报告' }}</span>
                <span class="msg-time">{{ formatTime(msg.created_at) }}</span>
              </div>
              <div class="msg-content" v-if="msg.role === 'assistant'">
                <div class="msg-text-preview">{{ getPreview(msg.content) }}</div>
                <div class="msg-actions">
                  <el-button
                    v-if="msg.file_url"
                    size="small"
                    type="success"
                    @click="downloadFile(msg)"
                  >
                    <el-icon><Download /></el-icon> 下载 Word
                  </el-button>
                  <el-button
                    v-if="msg.html_url"
                    size="small"
                    type="primary"
                    @click="viewHtml(msg)"
                  >
                    <el-icon><View /></el-icon> Web 报告
                  </el-button>
                  <el-button size="small" link type="primary" @click="toggleExpand(msg)">
                    {{ expandedMsgs.has(msg.id) ? '收起' : '展开全文' }}
                  </el-button>
                  <el-button size="small" link type="danger" @click="deleteMessage(msg)">
                    <el-icon><Delete /></el-icon> 删除
                  </el-button>
                </div>
                <div v-if="expandedMsgs.has(msg.id)" class="msg-text-full">{{ msg.content }}</div>
              </div>
              <div class="msg-content" v-else>
                <div class="msg-text-full">{{ msg.content.length > 500 ? msg.content.substring(0, 500) + '...' : msg.content }}</div>
              </div>
            </div>
          </div>
        </template>

        <!-- Loading -->
        <div v-if="assessLoading" class="msg-row msg-ai">
          <div class="msg-avatar"><el-icon><Cpu /></el-icon></div>
          <div class="msg-body">
            <div class="msg-loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>AI 正在分析研判中，预计 1-3 分钟，请稍候...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ====== 追问输入区（有会话后显示） ====== -->
      <div v-if="currentSessionId" class="assess-input-area">
        <el-input
          v-model="followUpText"
          type="textarea"
          :rows="2"
          placeholder="输入追问内容，基于上文继续分析..."
          :disabled="assessLoading"
          @keydown.ctrl.enter="sendFollowUp"
        />
        <el-button
          type="primary"
          :loading="assessLoading"
          :disabled="!followUpText.trim() || assessLoading"
          @click="sendFollowUp"
          style="margin-top: 8px;"
        >
          <el-icon><Promotion /></el-icon> 发送追问
        </el-button>
        <span class="input-hint">Ctrl + Enter 快捷发送</span>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Cpu, User, Document, Download, Loading, Promotion, CopyDocument, View, Delete } from '@element-plus/icons-vue'
import { getModels, getAdminModels } from '@/api/model'
import {
  createAssessmentSession,
  getAssessmentSessions,
  getSessionMessages,
  sendFollowUpQuestion,
  getDownloadUrl,
  getPromptPreview,
  deleteAssessmentSession,
  deleteAssessmentMessage
} from '@/api/lead'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  leadId: { type: Number, required: true },
  leadName: { type: String, default: '' },
  isAdmin: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'assessment-complete'])

const visible = computed({
  get: () => props.modelValue,
  set: v => emit('update:modelValue', v)
})

const selectedModelId = ref(null)
const modelList = ref([])
const assessLoading = ref(false)
const currentSessionId = ref(null)
const sessionList = ref([])
const messages = ref([])
const followUpText = ref('')
const expandedMsgs = ref(new Set())
const messagesContainer = ref(null)
const copyPromptLoading = ref(false)

function formatSessionLabel(s) {
  const t = s.created_at ? new Date(s.created_at + 'Z').toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''
  return `${s.title || 'AI 研判'} (${t})`
}

function formatTime(t) {
  if (!t) return ''
  return new Date(t + 'Z').toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function getPreview(content) {
  if (!content) return ''
  // 显示前 300 字
  return content.length > 300 ? content.substring(0, 300) + '...' : content
}

function toggleExpand(msg) {
  const next = new Set(expandedMsgs.value)
  if (next.has(msg.id)) next.delete(msg.id)
  else next.add(msg.id)
  expandedMsgs.value = next
}

function downloadFile(msg) {
  const url = msg.file_url
  if (url) window.open(url, '_blank')
}

function viewHtml(msg) {
  const url = msg.html_url
  if (url) window.open(url, '_blank')
}

async function loadModels() {
  try {
    const fn = props.isAdmin ? getAdminModels : getModels
    const res = await fn()
    if (res.code === 0) {
      modelList.value = res.data || []
      if (modelList.value.length > 0 && !selectedModelId.value) {
        selectedModelId.value = modelList.value[0].id
      }
    }
  } catch { modelList.value = [] }
}

async function loadSessions() {
  try {
    const res = await getAssessmentSessions(props.leadId)
    if (res.code === 0) {
      sessionList.value = res.data || []
    }
  } catch { sessionList.value = [] }
}

async function loadSessionMessages(sid) {
  try {
    const res = await getSessionMessages(sid)
    if (res.code === 0) {
      messages.value = (res.data.messages || []).reverse()  // 正序显示
    }
  } catch { messages.value = [] }
}

async function switchSession(sid) {
  currentSessionId.value = sid
  expandedMsgs.value = new Set()
  await loadSessionMessages(sid)
  scrollToBottom()
}

function scrollToBottom() {
  nextTick(() => {
    const el = messagesContainer.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

// ---- 生成报告 ----
async function generateReport() {
  if (!selectedModelId.value) {
    ElMessage.warning('请先选择 AI 模型')
    return
  }
  assessLoading.value = true
  try {
    const res = await createAssessmentSession(props.leadId, {
      model_id: selectedModelId.value
    })
    if (res.code === 0) {
      currentSessionId.value = res.data.session_id
      // 加载消息
      await loadSessionMessages(currentSessionId.value)
      await loadSessions()
      scrollToBottom()
      ElMessage.success('AI 研判报告生成成功')
      emit('assessment-complete')
    } else {
      ElMessage.error(res.message || 'AI 研判失败')
    }
  } catch (err) {
    ElMessage.error(err.message || 'AI 研判请求失败')
  } finally {
    assessLoading.value = false
  }
}

// ---- 追问 ----
async function sendFollowUp() {
  const q = followUpText.value.trim()
  if (!q || assessLoading.value) return
  if (!currentSessionId.value) {
    ElMessage.warning('请先生成项目分析报告')
    return
  }
  assessLoading.value = true
  followUpText.value = ''
  try {
    const res = await sendFollowUpQuestion(currentSessionId.value, {
      model_id: selectedModelId.value || null,
      question: q
    })
    if (res.code === 0) {
      // 重新加载消息
      await loadSessionMessages(currentSessionId.value)
      scrollToBottom()
      ElMessage.success('追问回答已生成')
    } else {
      ElMessage.error(res.message || '追问失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '请求失败')
  } finally {
    assessLoading.value = false
  }
}

// ---- 一键复制提示词 ----
async function copyPrompt() {
  copyPromptLoading.value = true
  try {
    const res = await getPromptPreview(props.leadId, selectedModelId.value)
    if (res.code !== 0) {
      ElMessage.error(res.message || '获取提示词失败')
      return
    }
    const data = res.data
    const parts = []
    if (data.system_prompt) {
      parts.push('【系统提示词】')
      parts.push(data.system_prompt)
      parts.push('')
    }
    parts.push('【用户提示词】')
    parts.push(data.prompt_text)

    const fullText = parts.join('\n')
    // 降级方案：优先 navigator.clipboard，非安全上下文时 fallback 到 textarea
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(fullText)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = fullText
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    ElMessage.success('提示词已复制到剪贴板')
  } catch (err) {
    ElMessage.error(err.message || '复制失败')
  } finally {
    copyPromptLoading.value = false
  }
}

// ---- 删除研判消息 ----
async function deleteMessage(msg) {
  try {
    await ElMessageBox.confirm('确定删除这条研判报告吗？关联的 Word/HTML 文件也会一并删除。', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch { return }

  try {
    const res = await deleteAssessmentMessage(currentSessionId.value, msg.id)
    if (res.code === 0) {
      ElMessage.success('已删除')
      await loadSessionMessages(currentSessionId.value)
      if (messages.value.length === 0) {
        await loadSessions()
        currentSessionId.value = null
      }
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '删除失败')
  }
}

function handleClosed() {
  expandedMsgs.value = new Set()
  followUpText.value = ''
  // 不重置 currentSessionId/messages，下次打开时重新加载
  messages.value = []
  currentSessionId.value = null
}

// 监听 drawer 打开
watch(() => props.modelValue, async (val) => {
  if (val) {
    expandedMsgs.value = new Set()
    assessLoading.value = false
    followUpText.value = ''
    messages.value = []
    currentSessionId.value = null
    await Promise.all([loadModels(), loadSessions()])
    // 如果有历史会话，默认加载最近一个
    if (sessionList.value.length > 0) {
      currentSessionId.value = sessionList.value[0].id
      await loadSessionMessages(currentSessionId.value)
      scrollToBottom()
    }
  }
})
</script>

<style scoped>
/* 标题栏 */
.drawer-title-bar {
  background: linear-gradient(135deg, #5b9bd5 0%, #8ab8e8 100%);
  margin: 0 -20px 0 -20px;
  padding: 20px 20px 20px 40px;
}
.drawer-title {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.assess-drawer-body {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 80px);
}

/* 工具栏 */
.assess-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}
.toolbar-spacer { flex: 1; }

/* 消息区域 */
.assess-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}
.assess-messages::-webkit-scrollbar { width: 6px; }
.assess-messages::-webkit-scrollbar-thumb { background: #d0d7de; border-radius: 3px; }

/* 空状态 */
.assess-empty {
  text-align: center;
  padding: 80px 40px;
  color: #909399;
}
.empty-icon { font-size: 56px; color: #c8daf0; margin-bottom: 16px; }
.empty-title { font-size: 18px; font-weight: 600; color: #606266; margin-bottom: 8px; }
.empty-desc { font-size: 14px; margin-bottom: 4px; }
.empty-hint { font-size: 13px; color: #b0b8c8; }

/* 消息行 */
.msg-row { display: flex; gap: 12px; margin-bottom: 20px; padding: 0 8px; }
.msg-user { flex-direction: row-reverse; }
.msg-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}
.msg-user .msg-avatar { background: #ecf5ff; color: #409eff; }
.msg-ai .msg-avatar { background: #edfaf1; color: #67c23a; }

.msg-body { max-width: 620px; min-width: 0; }
.msg-user .msg-body { text-align: right; }

.msg-header { display: flex; gap: 12px; align-items: center; margin-bottom: 6px; }
.msg-user .msg-header { flex-direction: row-reverse; }
.msg-role { font-size: 12px; font-weight: 600; color: #606266; }
.msg-time { font-size: 11px; color: #909399; }

.msg-text-preview { font-size: 13px; color: #303133; line-height: 1.7; white-space: pre-wrap; word-break: break-word; }
.msg-text-full {
  font-size: 13px; color: #303133; line-height: 1.7; white-space: pre-wrap; word-break: break-word;
  margin-top: 8px; padding: 12px; background: #f5f7fa; border-radius: 6px;
  max-height: 400px; overflow-y: auto;
}

.msg-actions { display: flex; gap: 8px; align-items: center; margin-top: 8px; }
.msg-user .msg-actions { justify-content: flex-end; }

/* Loading */
.msg-loading { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #909399; padding: 12px 0; }
.msg-loading .is-loading { animation: rotating 1.5s linear infinite; }
@keyframes rotating { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* 输入区 */
.assess-input-area {
  padding: 12px 0 4px;
  border-top: 1px solid #ebeef5;
  flex-shrink: 0;
}
.input-hint { font-size: 11px; color: #b0b8c8; margin-left: 12px; }
</style>
