<template>
  <div class="document-preview">
    <!-- 生成中状态 -->
    <div v-if="generating" class="generating">
      <el-progress
        :percentage="Math.round(progress)"
        :stroke-width="20"
        striped
        striped-flow
        style="max-width: 600px; margin: 0 auto;"
      />
      <p class="status-text">{{ statusText }}</p>
    </div>

    <!-- 生成完成 -->
    <div v-else class="document-result">
      <div class="result-header">
        <h3>📄 生成结果</h3>
        <div class="header-actions">
          <el-button @click="handleCopy">
            <el-icon><CopyDocument /></el-icon> 复制
          </el-button>
          <el-button @click="handleDownloadMarkdown">
            <el-icon><Download /></el-icon> 下载 Markdown
          </el-button>
          <el-button @click="handleDownloadWord" :loading="wordLoading">
            <el-icon><Document /></el-icon> 下载 Word
          </el-button>
          <el-button @click="handleDownloadHtml">
            <el-icon><Download /></el-icon> 下载 HTML
          </el-button>
          <el-button @click="$emit('regenerate')">
            <el-icon><Refresh /></el-icon> 重新生成
          </el-button>
        </div>
      </div>

      <!-- 文档内容区 -->
      <div v-if="localValue" class="document-content" ref="documentRef">
        <div v-html="formattedDocument"></div>
      </div>

      <el-empty v-else description="暂无文档内容，请点击「重新生成」" :image-size="100" />
    </div>

    <!-- 步骤按钮 -->
    <div class="step-actions">
      <el-button @click="$emit('prev')">
        <el-icon><ArrowLeft /></el-icon> 返回修改提纲
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { CopyDocument, Download, Refresh, ArrowLeft, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import MarkdownIt from 'markdown-it'
import { downloadWord } from '@/api/official-doc'
import api from '@/api'

const props = defineProps({
  modelValue: { type: String, default: '' },
  generating: { type: Boolean, default: false },
  progress: { type: Number, default: 0 },
  statusText: { type: String, default: '' },
  docTitle: { type: String, default: '公文文档' }
})

const emit = defineEmits(['update:modelValue', 'prev', 'regenerate'])

// markdown-it：默认转义原始 HTML，天然防止 XSS
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

// 本地文档内容
const localValue = ref('')
const wordLoading = ref(false)

watch(() => props.modelValue, (val) => {
  localValue.value = val || ''
}, { immediate: true })

watch(localValue, (val) => {
  emit('update:modelValue', val)
})

// 格式化文档（Markdown → HTML，已转义）
const formattedDocument = computed(() => {
  if (!localValue.value) return ''
  return md.render(localValue.value)
})

// 复制内容
async function handleCopy() {
  if (!localValue.value) {
    ElMessage.warning('暂无内容可复制')
    return
  }
  try {
    await navigator.clipboard.writeText(localValue.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = localValue.value
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('已复制到剪贴板')
  }
}

// 下载 Markdown（前端直接生成）
function handleDownloadMarkdown() {
  if (!localValue.value) {
    ElMessage.warning('暂无内容可下载')
    return
  }
  const blob = new Blob([localValue.value], { type: 'text/markdown;charset=utf-8' })
  triggerDownload(blob, `${props.docTitle || '公文文档'}.md`)
  ElMessage.success('下载成功')
}

// 下载 Word（后端生成 .docx）
async function handleDownloadWord() {
  if (!localValue.value) {
    ElMessage.warning('暂无内容可下载')
    return
  }
  wordLoading.value = true
  try {
    const res = await downloadWord({
      content: localValue.value,
      title: props.docTitle || '公文文档'
    })
    if (res.code !== 0) {
      ElMessage.error(res.message || '生成 Word 失败')
      return
    }
    const url = res.data.download_url
    const blobRes = await api.get(url, { responseType: 'blob' })
    triggerDownload(blobRes, `${props.docTitle || '公文文档'}.docx`)
    ElMessage.success('下载成功')
  } catch (err) {
    ElMessage.error(err.message || '生成 Word 失败')
  } finally {
    wordLoading.value = false
  }
}

// 下载 HTML（前端生成）
function handleDownloadHtml() {
  if (!localValue.value) {
    ElMessage.warning('暂无内容可下载')
    return
  }
  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>${props.docTitle || '公文文档'}</title>
  <style>
    body { font-family: 'Microsoft YaHei', 'SimSun', serif; line-height: 1.8; max-width: 800px; margin: 40px auto; padding: 20px; }
    h1 { text-align: center; font-size: 22px; }
    h2 { font-size: 18px; margin-top: 24px; }
    h3 { font-size: 16px; margin-top: 20px; }
    p { text-indent: 2em; margin: 12px 0; }
  </style>
</head>
<body>
  ${formattedDocument.value}
</body>
</html>`

  const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' })
  triggerDownload(blob, `${props.docTitle || '公文文档'}.html`)
  ElMessage.success('下载成功')
}

// 触发浏览器下载
function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.document-preview {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.generating {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 20px;
}

.status-text {
  font-size: 14px;
  color: var(--text-secondary);
}

.document-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.result-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.document-content {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 40px;
  min-height: 500px;
  background: #fff;
  font-family: 'Microsoft YaHei', 'SimSun', 'PingFang SC', serif;
  line-height: 2;
  color: #333;
}

.document-content :deep(h1) {
  text-align: center;
  font-size: 22px;
  font-weight: bold;
  margin: 0 0 24px;
  color: #333;
}

.document-content :deep(h2) {
  font-size: 18px;
  font-weight: bold;
  margin: 24px 0 16px;
  color: #333;
}

.document-content :deep(h3) {
  font-size: 16px;
  font-weight: bold;
  margin: 20px 0 12px;
  color: #333;
}

.document-content :deep(p) {
  text-indent: 2em;
  margin: 12px 0;
  text-align: justify;
}

.document-content :deep(ul),
.document-content :deep(ol) {
  padding-left: 2em;
  margin: 12px 0;
}

.document-content :deep(li) {
  margin: 8px 0;
}

.document-content :deep(blockquote) {
  border-left: 4px solid #1a3a5c;
  padding: 12px 16px;
  background: #f5f6f8;
  margin: 16px 0;
  color: #555;
}

.document-content :deep(strong) {
  color: #1a3a5c;
}

.step-actions {
  display: flex;
  justify-content: flex-start;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}
</style>
