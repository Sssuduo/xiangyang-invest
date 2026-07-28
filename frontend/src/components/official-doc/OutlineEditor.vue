<template>
  <div class="outline-editor">
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
    <div v-else class="outline-result">
      <div class="result-header">
        <h3>📋 文章提纲</h3>
        <div class="header-actions">
          <el-button @click="$emit('regenerate')">
            <el-icon><Refresh /></el-icon> 重新生成
          </el-button>
        </div>
      </div>

      <el-tree
        v-if="localValue.length > 0"
        ref="treeRef"
        :data="localValue"
        node-key="id"
        default-expand-all
        draggable
        :allow-drop="allowDrop"
        class="outline-tree"
      >
        <template #default="{ node, data }">
          <div class="outline-item">
            <span class="item-label">
              <el-input
                v-if="data.editing"
                v-model="data.title"
                size="small"
                @blur="handleEditEnd(data)"
                @keyup.enter="handleEditEnd(data)"
                @keyup.escape="handleEditCancel(data)"
                ref="editInputRef"
              />
              <span
                v-else
                class="item-title"
                @dblclick="handleEditStart(data)"
              >
                {{ node.label }}
              </span>
            </span>
            <span class="item-actions">
              <el-button text size="small" @click="handleAddChild(data)" title="添加子项">
                <el-icon><Plus /></el-icon>
              </el-button>
              <el-button text size="small" @click="handleRemove(node, data)" title="删除">
                <el-icon><Delete /></el-icon>
              </el-button>
            </span>
          </div>
        </template>
      </el-tree>

      <el-empty v-else description="暂无提纲内容，请点击「重新生成」" :image-size="100" />

      <div class="tips">
        <el-icon><InfoFilled /></el-icon>
        提示：双击编辑提纲项，拖动调整顺序，点击 +/- 添加/删除子项
      </div>
    </div>

    <!-- 步骤按钮 -->
    <div class="step-actions">
      <el-button @click="$emit('prev')">
        <el-icon><ArrowLeft /></el-icon> 返回修改素材
      </el-button>
      <el-button
        type="primary"
        size="large"
        :disabled="localValue.length === 0"
        @click="$emit('next')"
      >
        下一步：生成成文 <el-icon><ArrowRight /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { Refresh, Plus, Delete, ArrowLeft, ArrowRight, InfoFilled } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  generating: { type: Boolean, default: false },
  progress: { type: Number, default: 0 },
  statusText: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'prev', 'next', 'regenerate'])

// 本地提纲数据
const localValue = ref([])

watch(() => props.modelValue, (val) => {
  localValue.value = JSON.parse(JSON.stringify(val || []))
}, { immediate: true, deep: true })

watch(localValue, (val) => {
  emit('update:modelValue', JSON.parse(JSON.stringify(val)))
}, { deep: true })

// 树组件引用
const treeRef = ref(null)
const editInputRef = ref(null)

// 编辑状态
const editingId = ref(null)

// 开始编辑
function handleEditStart(data) {
  editingId.value = data.id
  data.editing = true
  nextTick(() => {
    if (editInputRef.value) {
      editInputRef.value.focus()
    }
  })
}

// 结束编辑
function handleEditEnd(data) {
  data.editing = false
  editingId.value = null
}

// 取消编辑
function handleEditCancel(data) {
  data.editing = false
  editingId.value = null
}

// 添加子项
function handleAddChild(data) {
  if (!data.children) {
    data.children = []
  }
  const newId = `${data.id}-${data.children.length + 1}`
  data.children.push({
    id: newId,
    title: '（新子项）',
    children: []
  })
}

// 删除节点
function handleRemove(node, data) {
  if (node.level === 1) {
    const idx = localValue.value.findIndex(d => d.id === data.id)
    if (idx !== -1) localValue.value.splice(idx, 1)
    return
  }
  const parent = node.parent
  const children = parent.data.children || []
  const index = children.findIndex(d => d.id === data.id)
  if (index !== -1) children.splice(index, 1)
}

// 拖拽判断
function allowDrop(draggingNode, dropNode, type) {
  // 不允许跨级拖入
  if (type === 'inner') {
    return dropNode.level < 3 // 最多三级
  }
  return true
}
</script>

<style scoped>
.outline-editor {
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

.outline-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
}

.outline-tree {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 12px;
}

.outline-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 4px 0;
}

.item-label {
  flex: 1;
  display: flex;
  align-items: center;
}

.item-title {
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background 0.2s;
}

.item-title:hover {
  background: var(--bg-light);
}

.item-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.outline-item:hover .item-actions {
  opacity: 1;
}

.tips {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f0f9eb;
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: #67c23a;
}

.step-actions {
  display: flex;
  justify-content: space-between;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}
</style>
