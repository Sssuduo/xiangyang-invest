<template>
  <div class="message-list">
    <el-empty v-if="!messages.length && !loading" description="暂无消息" :image-size="80" />
    <div v-for="msg in messages" :key="msg.id" class="message-item" :class="{ 'msg-superseded': msg.status === 'superseded' }">
      <div class="message-title">{{ msg.title }}</div>
      <div class="message-body" v-html="renderedBody(msg)" @click="handleBodyClick($event, msg)" />
      <div v-if="msg.handled_by_other" class="message-other-handled">
        <el-tag size="small" type="success">已由 {{ msg.handled_by_other }} 处理</el-tag>
        <span class="message-handle-time">{{ formatTime(msg.handled_by_other_at) }}</span>
      </div>
      <div class="message-meta">
        <span class="message-time">{{ formatTime(msg.triggered_at) }}</span>
        <div v-if="status !== 'done'" class="message-actions">
          <el-button v-if="status !== 'snoozed'" size="small" @click="$emit('snooze', msg.id)">挂起</el-button>
          <el-button size="small" type="primary" @click="$emit('done', msg.id)">已处理</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  status: { type: String, default: 'pending' },
})
defineEmits(['snooze', 'done'])

const router = useRouter()

function renderedBody(msg) {
  // [项目名] → 项目超链接；[文本] → 高亮文本
  if (!msg.body) return ''
  const linkQuery = msg.link_query || {}
  const projectId = linkQuery.focusProjectId || msg.source_id
  return msg.body.replace(
    /\[([^\]]+)\]/g,
    (m, text) => {
      if (projectId) {
        return `<a class="msg-link" data-project-id="${projectId}">${text}</a>`
      }
      return `<span class="msg-text">${text}</span>`
    }
  )
}

function handleBodyClick(e, msg) {
  const target = e.target
  if (target.classList.contains('msg-link')) {
    const projectId = target.dataset.projectId
    const route = msg.link_route || '/investment'
    router.push({ path: route, query: { focusProjectId: projectId } })
  }
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const now = new Date()
  const diffDays = Math.floor((now - d) / (1000 * 60 * 60 * 24))
  if (diffDays === 0) {
    return d.toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit' })
  }
  if (diffDays < 7) return `${diffDays}天前`
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) + ' ' +
    d.toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.message-list { padding: 8px 0; min-height: 200px; }
.message-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.15s;
}
.message-item:hover { background: #fafafa; }
.message-item.msg-superseded { opacity: 0.6; }
.message-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}
.message-body {
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  margin-bottom: 6px;
}
.message-body :deep(.msg-link) {
  color: #409eff;
  cursor: pointer;
  text-decoration: none;
  font-weight: 600;
}
.message-body :deep(.msg-link:hover) { text-decoration: underline; }
.message-body :deep(.msg-text) { color: #606266; }
.message-other-handled {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.message-handle-time { font-size: 12px; color: #909399; }
.message-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.message-time { font-size: 12px; color: #909399; }
.message-actions { display: flex; gap: 8px; }
</style>
