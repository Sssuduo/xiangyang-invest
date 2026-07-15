<template>
  <div class="text-editor-wrapper">
    <div
      ref="editorRef"
      class="text-editor"
      contenteditable="plaintext-only"
      @mouseup="handleMouseUp"
      @input="handleInput"
      v-text="content"
    ></div>

    <!-- 选中后弹出替换浮层 -->
    <div
      v-if="showPopover"
      class="tc-popover"
      :style="{ left: popoverX + 'px', top: popoverY + 'px' }"
    >
      <div class="tc-popover-header">
        选中: <strong>{{ selectedText }}</strong>
      </div>
      <div class="tc-popover-body">
        <el-input
          v-model="replacement"
          size="small"
          placeholder="替换为..."
          @keyup.enter="doReplace"
        />
        <div v-if="kbSuggestions.length" class="tc-suggestions">
          <el-tag
            v-for="s in kbSuggestions"
            :key="s.replacement"
            size="small"
            type="success"
            @click="replacement = s.replacement"
          >
            {{ s.replacement }}
          </el-tag>
        </div>
      </div>
      <div class="tc-popover-footer">
        <el-button size="small" @click="cancelReplace">取消</el-button>
        <el-button size="small" type="primary" @click="doReplace">替换</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'

const props = defineProps({
  content: { type: String, default: '' },
  candidates: { type: Array, default: () => [] },
})

const emit = defineEmits(['selection-change', 'replace'])

const editorRef = ref(null)
const showPopover = ref(false)
const selectedText = ref('')
const replacement = ref('')
const popoverX = ref(0)
const popoverY = ref(0)
const kbSuggestions = ref([])

// 保存选区的 range 引用，避免 doReplace 时 focus 移到 input 后 selection 丢失
let savedRange = null
let savedSelectedText = ''

watch(() => props.content, (val) => {
  if (editorRef.value && editorRef.value.textContent !== val) {
    editorRef.value.textContent = val
  }
})

onMounted(() => {
  if (editorRef.value && props.content) {
    editorRef.value.textContent = props.content
  }
})

function handleMouseUp() {
  const sel = window.getSelection()
  if (!sel || sel.isCollapsed) {
    showPopover.value = false
    return
  }

  const text = sel.toString().trim()
  if (text.length < 2 || text.length > 30) {
    showPopover.value = false
    return
  }

  selectedText.value = text
  replacement.value = ''
  kbSuggestions.value = []

  // 查询知识库中的同音建议 (基于 props.candidates)
  kbSuggestions.value = props.candidates.filter(c => c.source === text)

  // 计算浮层位置
  const range = sel.getRangeAt(0)
  const rect = range.getBoundingClientRect()
  const editorRect = editorRef.value.getBoundingClientRect()

  popoverX.value = Math.min(rect.left - editorRect.left, editorRef.value.clientWidth - 280)
  popoverY.value = rect.bottom - editorRect.top + 8

  showPopover.value = true

  savedRange = range
  savedSelectedText = text

  emit('selection-change', { text, range })
}

function handleInput() {
  // 内容变化时通知父组件 (可省略，替换时直接用 editorRef.textContent)
}

function doReplace() {
  if (!replacement.value.trim()) return

  const range = savedRange
  const sourceText = savedSelectedText
  if (range && sourceText) {
    // 重选举区并替换文本
  const sel = window.getSelection()
  sel.removeAllRanges()
  sel.addRange(range)
    range.deleteContents()
    range.insertNode(document.createTextNode(replacement.value))

    emit('replace', {
      range,
      replacement: replacement.value,
      source: sourceText,
    })
  }

  showPopover.value = false
  savedRange = null
  savedSelectedText = ''
}

function cancelReplace() {
  showPopover.value = false
}

// 供父组件获取当前文本
function getText() {
  return editorRef.value?.textContent || ''
}

defineExpose({ getText })
</script>

<style scoped>
.text-editor-wrapper {
  position: relative;
  height: 100%;
}

.text-editor {
  min-height: 400px;
  padding: 16px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  line-height: 1.8;
  font-size: 14px;
  white-space: pre-wrap;
  overflow-y: auto;
  outline: none;
}

.text-editor:focus {
  border-color: #409eff;
}

.tc-popover {
  position: absolute;
  z-index: 100;
  width: 260px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 12px;
}

.tc-popover-header {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.tc-popover-body {
  margin-bottom: 8px;
}

.tc-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.tc-suggestions .el-tag {
  cursor: pointer;
}

.tc-popover-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
