<template>
  <div class="message-center">
    <el-tabs v-model="activeTab" stretch>
      <el-tab-pane :label="`待处理(${pendingCount})`" name="pending">
        <MessageList
          :messages="pending"
          :loading="loading"
          status="pending"
          @snooze="handleSnooze"
          @done="handleDone"
        />
      </el-tab-pane>
      <el-tab-pane label="已挂起" name="snoozed">
        <MessageList
          :messages="snoozed"
          :loading="loading"
          status="snoozed"
          @snooze="handleSnooze"
          @done="handleDone"
        />
      </el-tab-pane>
      <el-tab-pane label="已处理" name="done">
        <MessageList
          :messages="done"
          :loading="loading"
          status="done"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import MessageList from './MessageList.vue'
import { userMessageApi } from '@/api/userMessage.js'

const messages = ref([])
const loading = ref(false)
const activeTab = ref('pending')

const pending = computed(() => messages.value.filter(m => m.status === 'pending'))
const snoozed = computed(() => messages.value.filter(m => m.status === 'snoozed'))
const done = computed(() => messages.value.filter(m => m.status === 'done'))
const pendingCount = computed(() => pending.value.length + snoozed.value.length)

async function loadMessages() {
  loading.value = true
  try {
    const [p, s, d] = await Promise.all([
      userMessageApi.listInbox({ status: 'pending' }),
      userMessageApi.listInbox({ status: 'snoozed' }),
      userMessageApi.listInbox({ status: 'done' }),
    ])
    messages.value = [
      ...(p.data.data?.items || []),
      ...(s.data.data?.items || []),
      ...(d.data.data?.items || []),
    ]
  } finally {
    loading.value = false
  }
}

async function handleSnooze(id) {
  await userMessageApi.snooze(id)
  loadMessages()
}

async function handleDone(id) {
  await userMessageApi.done(id)
  loadMessages()
}

onMounted(loadMessages)
defineExpose({ loadMessages })
</script>

<style scoped>
.message-center {
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
