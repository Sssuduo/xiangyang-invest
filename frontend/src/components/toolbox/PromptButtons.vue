<template>
  <div class="prompt-buttons">
    <label class="section-label">快捷提示词</label>
    <div v-if="prompts.length === 0" class="empty-hint">
      暂无可用提示词
    </div>
    <div v-else class="prompt-list">
      <el-button
        v-for="prompt in prompts"
        :key="prompt.id"
        :disabled="disabled"
        @click="$emit('select', prompt)"
        class="prompt-btn"
        :title="prompt.description"
      >
        {{ prompt.button_text }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  prompts: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false }
})
defineEmits(['select'])
</script>

<style scoped>
.section-label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  font-weight: 500;
}
.prompt-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.prompt-btn {
  justify-content: flex-start;
  text-align: left;
  white-space: normal;
  height: auto;
  min-height: 36px;
  padding: 8px 12px;
  line-height: 1.4;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  transition: all 0.2s;
}
.prompt-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  background: rgba(26, 58, 92, 0.04);
}
.empty-hint {
  font-size: 13px;
  color: #aaa;
  font-style: italic;
}
</style>
