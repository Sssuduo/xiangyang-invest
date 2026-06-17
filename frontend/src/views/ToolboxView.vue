<template>
  <div class="toolbox-page">
    <!-- 顶部导航 -->
    <header class="toolbox-header">
      <el-button text @click="$router.push('/')" class="back-link">
        ← 返回首页
      </el-button>
      <h2 class="toolbox-title">招商工具箱</h2>
      <div class="header-spacer" />
    </header>

    <!-- 主体区域 -->
    <div class="toolbox-body">
      <!-- 左侧面板 -->
      <aside class="toolbox-sidebar">
        <!-- 模型选择 -->
        <ModelSelector
          v-model="selectedModelId"
          :models="models"
        />

        <!-- 快捷提示词 -->
        <PromptButtons
          :prompts="prompts"
          :disabled="!userInput"
          @select="handlePromptSelect"
        />

        <!-- 自定义提问 -->
        <div class="custom-question-section">
          <el-button
            type="primary"
            :disabled="!userInput || !selectedModelId"
            @click="handleCustomQuestion"
            style="width: 100%"
          >
            自定义提问
          </el-button>
        </div>
      </aside>

      <!-- 右侧对话区 -->
      <main class="toolbox-main">
        <!-- 输入区 -->
        <InputSection
          v-model="userInput"
          :loading="loading"
          @send="handleSend"
        />

        <!-- 对话展示 -->
        <ChatDisplay
          :messages="messages"
          :loading="loading"
        />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getModels } from '@/api/model'
import { getPrompts } from '@/api/prompt'
import { sendChat } from '@/api/chat'
import { ElMessage } from 'element-plus'
import ModelSelector from '@/components/toolbox/ModelSelector.vue'
import PromptButtons from '@/components/toolbox/PromptButtons.vue'
import InputSection from '@/components/toolbox/InputSection.vue'
import ChatDisplay from '@/components/toolbox/ChatDisplay.vue'

const models = ref([])
const prompts = ref([])
const selectedModelId = ref(null)
const userInput = ref('')
const messages = ref([])
const loading = ref(false)

onMounted(async () => {
  try {
    const [modelsRes, promptsRes] = await Promise.all([
      getModels(),
      getPrompts()
    ])
    if (modelsRes.code === 0) {
      models.value = modelsRes.data || []
      if (models.value.length > 0) {
        selectedModelId.value = models.value[0].id
      }
    }
    if (promptsRes.code === 0) {
      prompts.value = promptsRes.data || []
    }
  } catch {
    // 静默处理
  }
})

async function handlePromptSelect(prompt) {
  if (!userInput.value || !selectedModelId.value) return
  await sendMessage(userInput.value, prompt.id, false)
}

async function handleCustomQuestion() {
  if (!userInput.value || !selectedModelId.value) return
  await sendMessage(userInput.value, null, true)
}

async function handleSend() {
  // 当用户点击发送按钮时，不做任何事（需要先选择提示词或自定义提问）
  // 因为交互流程是：输入 → 点击提示词按钮 → 发送
}

async function sendMessage(input, promptId, customQuestion) {
  loading.value = true

  // 添加用户消息
  const selectedModel = models.value.find(m => m.id === selectedModelId.value)
  const selectedPrompt = promptId ? prompts.value.find(p => p.id === promptId) : null

  messages.value.push({
    role: 'user',
    content: promptId && selectedPrompt
      ? `【${selectedPrompt.button_text}】${input}`
      : input,
    modelName: null
  })

  try {
    const res = await sendChat({
      user_input: input,
      model_id: selectedModelId.value,
      prompt_id: promptId || undefined,
      custom_question: customQuestion
    })

    if (res.code === 0) {
      messages.value.push({
        role: 'assistant',
        content: res.data.response_text,
        modelName: res.data.model_name
      })
    } else {
      ElMessage.error(res.message || '请求失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '调用大模型失败，请检查网络连接')
    messages.value.push({
      role: 'assistant',
      content: `错误：${err.message}`,
      modelName: '系统',
      isError: true
    })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.toolbox-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-light);
}

.toolbox-header {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  background: var(--bg-white);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
}

.back-link {
  font-size: 14px;
}

.toolbox-title {
  flex: 1;
  text-align: center;
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-color);
}

.header-spacer {
  width: 80px;
}

.toolbox-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.toolbox-sidebar {
  width: 280px;
  background: var(--bg-white);
  border-right: 1px solid var(--border-color);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  flex-shrink: 0;
}

.toolbox-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.custom-question-section {
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}
</style>
