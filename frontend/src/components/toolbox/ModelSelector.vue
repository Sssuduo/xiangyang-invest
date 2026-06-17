<template>
  <div class="model-selector">
    <label class="section-label">选择模型</label>
    <el-select
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      placeholder="请选择大模型"
      style="width: 100%"
    >
      <el-option
        v-for="model in models"
        :key="model.id"
        :label="model.name"
        :value="model.id"
      />
    </el-select>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: Number, default: null },
  models: { type: Array, default: () => [] }
})
defineEmits(['update:modelValue'])
</script>

<style scoped>
.model-selector {
  margin-bottom: 8px;
}
.section-label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  font-weight: 500;
}
</style>
