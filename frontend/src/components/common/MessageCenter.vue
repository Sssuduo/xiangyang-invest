<template>
  <div class="message-center">
    <!-- 类型筛选 -->
    <div class="mc-filter">
      <el-radio-group v-model="typeFilter" size="small" @change="onFilterChange">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="no_meeting">超期未研判</el-radio-button>
        <el-radio-button value="no_followup">超期无动态</el-radio-button>
      </el-radio-group>
    </div>

    <el-tabs v-model="activeTab" stretch>
      <el-tab-pane :label="`待处理(${pending.length})`" name="pending">
        <MessageList
          :messages="pending"
          :loading="loading"
          status="pending"
          @snooze="handleSnooze"
          @done="handleDone"
        />
      </el-tab-pane>
      <el-tab-pane :label="`已挂起(${snoozed.length})`" name="snoozed">
        <MessageList
          :messages="snoozed"
          :loading="loading"
          status="snoozed"
          @snooze="handleSnooze"
          @done="handleDone"
        />
      </el-tab-pane>
      <el-tab-pane :label="`已处理(${done.length})`" name="done">
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
const typeFilter = ref('')

// 按项目主体 + 规则类型去重（同一项目同一规则只保留最新一条，
// 不同规则（未研判/无动态）分别展示，类型筛选才有意义）
function dedupeByProject(list) {
  const seen = new Map()
  for (const m of list) {
    const key = m.source_id ? `p${m.source_id}_${m.alert_type || ''}` : `m${m.id}`
    if (!seen.has(key) || new Date(m.triggered_at) > new Date(seen.get(key).triggered_at)) {
      seen.set(key, m)
    }
  }
  return [...seen.values()]
}

function filterByType(list) {
  if (!typeFilter.value) return list
  return list.filter(m => m.alert_type === typeFilter.value)
}

const pending = computed(() => filterByType(dedupeByProject(messages.value.filter(m => m.status === 'pending'))))
const snoozed = computed(() => filterByType(dedupeByProject(messages.value.filter(m => m.status === 'snoozed'))))
const done = computed(() => filterByType(dedupeByProject(messages.value.filter(m => m.status === 'done'))))

function onFilterChange() {
  // 切换类型时保持当前 Tab
}

async function loadMessages() {
  loading.value = true
  try {
    const [p, s, d] = await Promise.all([
      userMessageApi.listInbox({ status: 'pending', page_size: 200 }),
      userMessageApi.listInbox({ status: 'snoozed', page_size: 200 }),
      userMessageApi.listInbox({ status: 'done', page_size: 200 }),
    ])
    // 响应拦截器已解包 response.data → res 即 {code, data:{items,total}}
    messages.value = [
      ...(p.data?.items || []),
      ...(s.data?.items || []),
      ...(d.data?.items || []),
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
.mc-filter {
  padding: 4px 4px 8px;
  display: flex;
}
</style>
