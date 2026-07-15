<template>
  <div class="text-correction-page">
    <!-- 顶部工具栏 -->
    <div class="tc-header">
      <el-button @click="goBack">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
      <h2 class="tc-title">文本校正 - 台账 #{{ ledgerId }}</h2>
      <div class="tc-header-actions">
        <el-button type="success" @click="handleApplyToLedger" :loading="saving">
          <el-icon><Check /></el-icon> 应用到台账
        </el-button>
        <el-button type="primary" @click="handleSaveAndPersist" :loading="saving">
          <el-icon><Collection /></el-icon> 保存并沉淀到知识库
        </el-button>
      </div>
    </div>

    <!-- 主体三栏布局 -->
    <div class="tc-body">
      <!-- 左: 原文 + 编辑器 -->
      <div class="tc-main">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="分段原文" name="segmented">
            <TextEditor
              ref="segmentedEditorRef"
              :content="data.transcript_segmented || data.transcript"
              :candidates="candidates"
              @selection-change="onSelectionChange"
              @replace="onEditorReplace"
            />
          </el-tab-pane>
          <el-tab-pane label="清洁版" name="clean">
            <TextEditor
              ref="cleanEditorRef"
              :content="data.transcript_clean"
              :candidates="candidates"
              @selection-change="onSelectionChange"
              @replace="onEditorReplace"
            />
          </el-tab-pane>
          <el-tab-pane label="摘要版" name="summary">
            <TextEditor
              ref="summaryEditorRef"
              :content="data.summary_structured"
              :candidates="candidates"
              @selection-change="onSelectionChange"
              @replace="onEditorReplace"
            />
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 右: 知识库 + 检测 -->
      <div class="tc-sidebar">
        <el-collapse v-model="sidebarActive">
          <el-collapse-item title="🤖 智能检测" name="detect">
            <el-button type="primary" plain @click="runDetection" :loading="detecting"
              style="width: 100%;">
              <el-icon><Search /></el-icon> 检测同音词
            </el-button>
            <div v-if="candidates.length" class="tc-candidate-list">
              <div v-for="c in candidates" :key="c.start" class="tc-candidate"
                   :class="'tc-conf-' + getConfidenceClass(c.confidence)">
                <span class="tc-cand-source">{{ c.source }}</span>
                <el-icon><Right /></el-icon>
                <span class="tc-cand-target">{{ c.target }}</span>
                <el-tag size="small" :type="c.confidence >= 0.9 ? 'success' : 'warning'">
                  {{ (c.confidence * 100).toFixed(0) }}%
                </el-tag>
              </div>
            </div>
            <el-empty v-else description="暂无候选" :image-size="60" />
          </el-collapse-item>

          <el-collapse-item title="📚 知识库" name="knowledge">
            <div class="tc-kb-list">
              <div v-for="kb in knowledgeList" :key="kb.id" class="tc-kb-item">
                <span class="tc-kb-original">{{ kb.original }}</span>
                <el-icon size="12"><Right /></el-icon>
                <span class="tc-kb-replacement">{{ kb.replacement }}</span>
                <el-tag size="small" type="info">{{ kb.usage_count }}</el-tag>
              </div>
            </div>
            <el-empty v-if="!knowledgeList.length" description="知识库为空" :image-size="60" />
          </el-collapse-item>

          <el-collapse-item title="📝 校正记录" name="records">
            <div class="tc-record-list">
              <div v-for="r in corrections" :key="r.id" class="tc-record">
                <span class="tc-record-original">{{ r.original }}</span>
                <el-icon size="12"><Right /></el-icon>
                <span class="tc-record-replacement">{{ r.replacement }}</span>
              </div>
            </div>
            <el-empty v-if="!corrections.length" description="暂无校正记录" :image-size="60" />
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>

    <!-- 选中词汇后的替换弹出层 -->
    <el-dialog v-model="showReplaceDialog" title="替换词汇" width="400px" :append-to-body="true">
      <p>选中: <strong>{{ selectedText }}</strong></p>
      <el-form label-position="top">
        <el-form-item label="替换为">
          <el-input v-model="replacementText" placeholder="输入替换词汇" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReplaceDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmReplace">确认替换</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Right, Check, Collection, Search } from '@element-plus/icons-vue'

import TextEditor from '@/components/ledcor/TextEditor.vue'
import { getSummaryPageData, detectHomophones, saveCorrections, getKnowledgeList } from '@/api/textCorrection'

const route = useRoute()
const router = useRouter()

const ledgerId = computed(() => Number(route.params.id))

// 数据
const data = reactive({
  transcript: '',
  transcript_segmented: '',
  transcript_clean: '',
  summary_structured: '',
})

const corrections = ref([])
const candidates = ref([])
const knowledgeList = ref([])

const activeTab = ref('segmented')
const sidebarActive = ref(['detect'])

const detecting = ref(false)
const saving = ref(false)

// 编辑器 refs
const segmentedEditorRef = ref(null)
const cleanEditorRef = ref(null)
const summaryEditorRef = ref(null)

// 替换对话框
const showReplaceDialog = ref(false)
const selectedText = ref('')
const replacementText = ref('')
let currentReplaceContext = null

onMounted(async () => {
  await loadData()
  await loadKnowledge()
})

async function loadData() {
  try {
    const res = await getSummaryPageData(ledgerId.value)
    if (res.code === 0) {
      Object.assign(data, res.data)
      corrections.value = res.data.corrections || []
    }
  } catch (e) {
    ElMessage.error('加载数据失败')
  }
}

async function loadKnowledge() {
  try {
    const res = await getKnowledgeList()
    if (res.code === 0) {
      knowledgeList.value = res.data || []
    }
  } catch (e) {
    // ignore
  }
}

function goBack() {
  router.back()
}

// 编辑器选中词汇
function onSelectionChange({ text, range }) {
  if (text && text.trim().length >= 2 && text.trim().length <= 30) {
    selectedText.value = text.trim()
    replacementText.value = ''
    currentReplaceContext = { tab: activeTab.value, range }
  }
}

// 编辑器内直接替换
function onEditorReplace({ range, replacement, source }) {
  range.deleteContents()
  range.insertNode(document.createTextNode(replacement))

  // 记录校正
  corrections.value.unshift({
    id: Date.now(),
    original: source,
    replacement: replacement,
    method: 'manual',
  })
}

async function runDetection() {
  detecting.value = true
  try {
    const text = getCurrentEditorText()
    const res = await detectHomophones(text, 0.70)
    if (res.code === 0) {
      candidates.value = res.data || []
      ElMessage.success(`检测到 ${candidates.value.length} 个候选`)
    }
  } finally {
    detecting.value = false
  }
}

function getCurrentEditorText() {
  switch (activeTab.value) {
    case 'clean': return data.transcript_clean
    case 'summary': return data.summary_structured
    default: return data.transcript_segmented || data.transcript
  }
}

function confirmReplace() {
  if (!replacementText.value.trim()) {
    ElMessage.warning('请输入替换词汇')
    return
  }
  showReplaceDialog.value = false

  // 记录校正（这才是"应用到台账"需要保存的数据）
  corrections.value.unshift({
    id: Date.now(),
    original: selectedText.value,
    replacement: replacementText.value.trim(),
    method: 'manual',
  })

  // 同步替换编辑器 DOM 中的文本，让用户立即看到效果
  if (currentReplaceContext) {
    const editorRef = getCurrentEditorRef()
    if (editorRef) {
      const sel = window.getSelection()
      if (sel.rangeCount > 0) {
        const range = sel.getRangeAt(0)
        if (range.toString().trim() === selectedText.value) {
          range.deleteContents()
          range.insertNode(document.createTextNode(replacementText.value.trim()))
        }
      }
    }
  }
}

// 根据当前 tab 返回对应的编辑器 ref
function getCurrentEditorRef() {
  switch (activeTab.value) {
    case 'clean': return cleanEditorRef.value
    case 'summary': return summaryEditorRef.value
    default: return segmentedEditorRef.value
  }
}

async function handleApplyToLedger() {
  await doSaveCorrections(false)
}

async function handleSaveAndPersist() {
  await doSaveCorrections(true)
}

async function doSaveCorrections(persist) {
  saving.value = true
  try {
    const res = await saveCorrections(ledgerId.value, corrections.value, persist)
    if (res.code === 0) {
      ElMessage.success(persist ? '已保存并沉淀到知识库' : '已保存到台账')
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } finally {
    saving.value = false
  }
}

function getConfidenceClass(conf) {
  if (conf >= 0.9) return 'high'
  if (conf >= 0.75) return 'medium'
  return 'low'
}
</script>

<style scoped>
.text-correction-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f7fa;
}

.tc-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.tc-title {
  flex: 1;
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.tc-header-actions {
  display: flex;
  gap: 8px;
}

.tc-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.tc-main {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.tc-main > .el-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.tc-main > .el-tabs > .el-tabs__content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.tc-main .el-tab-pane {
  height: 100%;
}

.tc-sidebar {
  width: 320px;
  background: #fff;
  border-left: 1px solid #e4e7ed;
  padding: 16px;
  overflow-y: auto;
}

.tc-candidate-list,
.tc-kb-list,
.tc-record-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tc-candidate,
.tc-kb-item,
.tc-record {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #fafafa;
  border-radius: 4px;
  font-size: 13px;
}

.tc-cand-source { color: #f56c6c; }
.tc-cand-target,
.tc-kb-replacement,
.tc-record-replacement { color: #67c23a; font-weight: 500; }

.tc-conf-high { background: #f0f9ff; border: 1px solid #d0e8ff; }
.tc-conf-medium { background: #fdf6ec; border: 1px solid #f5dab1; }
.tc-conf-low { background: #f4f4f5; border: 1px solid #d3d4d6; }
</style>
