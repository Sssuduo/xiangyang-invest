<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>{{ isEdit ? '编辑大模型' : '新建大模型' }}</h2>
          <el-button @click="$router.push('/admin/models')">返回列表</el-button>
        </div>

        <el-form :model="form" label-width="110px" class="edit-form">
          <el-form-item label="显示名称">
            <el-input v-model="form.name" placeholder="如：DeepSeek V3" />
          </el-form-item>
          <el-form-item label="厂商">
            <el-select v-model="form.provider" placeholder="选择厂商">
              <el-option label="OpenAI" value="openai" />
              <el-option label="DeepSeek" value="deepseek" />
              <el-option label="智谱AI" value="zhipu" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </el-form-item>
          <el-form-item label="API 地址">
            <el-input v-model="form.api_base_url" placeholder="https://api.deepseek.com/v1" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="form.api_key" type="password" show-password placeholder="sk-..." />
          </el-form-item>
          <el-form-item label="模型名">
            <el-input v-model="form.model_name" placeholder="如：deepseek-chat" />
          </el-form-item>
          <el-form-item label="Temperature">
            <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" :precision="1" />
          </el-form-item>
          <el-form-item label="Max Tokens">
            <el-input-number v-model="form.max_tokens" :min="100" :max="128000" :step="100" />
          </el-form-item>
          <el-form-item label="系统提示词">
            <el-input v-model="form.system_prompt" type="textarea" :rows="3" placeholder="可选" />
          </el-form-item>

          <!-- Embedding 独立配置（可选） -->
          <el-divider content-position="left">
            <span class="embedding-divider-text">Embedding 配置（可选，留空则复用上方 Chat 配置）</span>
          </el-divider>
          <el-form-item label="Embedding URL">
            <el-input v-model="form.embedding_api_url" placeholder="如：https://api.siliconflow.cn/v1/embeddings" />
            <div class="form-tip">硅基流动免费 Embedding 端点：https://api.siliconflow.cn/v1/embeddings</div>
          </el-form-item>
          <el-form-item label="Embedding Key">
            <el-input v-model="form.embedding_api_key" type="password" show-password placeholder="sk-...（留空则复用上方的 API Key）" />
          </el-form-item>
          <el-form-item label="Embedding 模型">
            <el-input v-model="form.embedding_model_name" placeholder="BAAI/bge-m3（免费，1024维，中英文通用）" />
            <div class="form-tip">推荐免费模型：BAAI/bge-m3（1024维）或 BAAI/bge-large-zh-v1.5（纯中文）</div>
          </el-form-item>

          <!-- 关联搜索模型（用于研判时自动联网搜索） -->
          <el-divider content-position="left">
            <span class="embedding-divider-text">联网搜索配置（可选，GLM-4-Flash 等支持 Web Search 的模型）</span>
          </el-divider>
          <el-form-item label="搜索模型">
            <el-select v-model="form.search_model_id" placeholder="选择用于联网搜索的模型（留空则不启用联网搜索）" clearable style="width: 100%;">
              <el-option
                v-for="m in searchModelCandidates"
                :key="m.id"
                :label="`${m.name} (${m.model_name})`"
                :value="m.id"
              />
            </el-select>
            <div class="form-tip">选择支持 Web Search API 的模型（如 GLM-4-Flash），研判时将自动使用此模型进行联网搜索，再将结果交给主模型生成报告。</div>
          </el-form-item>

          <el-form-item label="启用">
            <el-switch v-model="form.is_active" />
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="form.sort_order" :min="0" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="large" :loading="saving" @click="handleSave">保 存</el-button>
          </el-form-item>
        </el-form>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getAdminModel, createModel, updateModel, getAdminModels } from '@/api/model'

const route = useRoute()
const router = useRouter()
const isEdit = ref(!!route.params.id)
const saving = ref(false)

const form = ref({
  name: '',
  provider: 'custom',
  api_base_url: '',
  api_key: '',
  model_name: '',
  temperature: 0.7,
  max_tokens: 4096,
  system_prompt: '',
  embedding_api_url: '',
  embedding_api_key: '',
  embedding_model_name: '',
  search_model_id: null,
  is_active: true,
  sort_order: 0
})

const searchModelCandidates = ref([])

onMounted(async () => {
  // 预加载所有模型作为搜索模型候选
  try {
    const res = await getAdminModels()
    if (res.code === 0) {
      searchModelCandidates.value = (res.data || []).filter(
        m => m.provider === 'glm' || m.provider === 'zhipu'
      )
    }
  } catch { /* ignore */ }

  if (isEdit.value) {
    try {
      const res = await getAdminModel(route.params.id)
      if (res.code === 0) form.value = { ...form.value, ...res.data }
    } catch (err) {
      ElMessage.error(err.message)
      router.push('/admin/models')
    }
  }
})

async function handleSave() {
  saving.value = true
  try {
    if (isEdit.value) {
      await updateModel(route.params.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createModel(form.value)
      ElMessage.success('创建成功')
      router.push('/admin/models')
    }
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: var(--bg-light); }
.admin-content { padding: 32px; max-width: 700px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
h2 { color: var(--primary-color); }
.edit-form { background: #fff; padding: 32px; border-radius: 12px; box-shadow: var(--shadow-sm); }
.form-tip { margin-top: 4px; font-size: 12px; color: #909399; line-height: 1.4; }
.embedding-divider-text { font-size: 13px; color: #909399; font-weight: 400; }
</style>
