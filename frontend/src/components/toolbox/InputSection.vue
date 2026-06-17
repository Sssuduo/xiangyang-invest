<template>
  <div class="input-section">
    <el-input
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      type="textarea"
      :rows="3"
      placeholder="您可以输入企业名称、项目名称、企业家姓名"
      resize="none"
      class="main-input"
      :disabled="loading"
    />
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  loading: { type: Boolean, default: false }
})
defineEmits(['update:modelValue', 'send'])
</script>

<style scoped>
.input-section {
  padding: 20px 24px;
  background: var(--bg-white);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.main-input :deep(.el-textarea__inner) {
  font-size: 15px;
  border-radius: 10px;
  border: 2px solid var(--border-color);
  transition: border-color 0.3s;
  padding: 14px 16px;
}
.main-input :deep(.el-textarea__inner):focus {
  border-color: var(--primary-color);
}
</style>
