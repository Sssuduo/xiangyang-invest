<template>
  <div class="chat-display" ref="scrollRef">
    <div v-if="messages.length === 0 && !loading" class="chat-empty">
      <div class="empty-icon">💬</div>
      <p>在输入框中输入企业名称、项目名称或企业家姓名</p>
      <p>然后选择左侧的快捷提示词开始查询</p>
    </div>

    <div v-for="(msg, index) in messages" :key="index" class="chat-message" :class="msg.role">
      <div class="message-header">
        <span class="message-role">{{ msg.role === 'user' ? '您' : (msg.modelName || 'AI') }}</span>
        <span v-if="msg.isError" class="error-tag">错误</span>
      </div>
      <div class="message-content" :class="{ error: msg.isError }">
        {{ msg.content }}
      </div>
    </div>

    <div v-if="loading" class="loading-indicator">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在生成回复...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const scrollRef = ref(null)

watch(
  () => props.messages.length,
  () => nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
)

watch(
  () => props.loading,
  (val) => {
    if (val) {
      nextTick(() => {
        if (scrollRef.value) {
          scrollRef.value.scrollTop = scrollRef.value.scrollHeight
        }
      })
    }
  }
)
</script>

<style scoped>
.chat-display {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  text-align: center;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.chat-empty p {
  font-size: 14px;
  margin-bottom: 8px;
  opacity: 0.7;
}

.chat-message {
  max-width: 80%;
}

.chat-message.user {
  align-self: flex-end;
}
.chat-message.assistant {
  align-self: flex-start;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.message-role {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

.error-tag {
  font-size: 11px;
  color: #e74c3c;
  background: #fde8e8;
  padding: 1px 6px;
  border-radius: 3px;
}

.message-content {
  padding: 14px 18px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

.chat-message.user .message-content {
  background: var(--primary-color);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-message.assistant .message-content {
  background: #fff;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: 4px;
}

.chat-message.assistant .message-content.error {
  background: #fef2f2;
  border-color: #fca5a5;
  color: #991b1b;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  color: var(--text-secondary);
  font-size: 14px;
}
</style>
