<!--
AppDrawer.vue — 系统统一侧滑抽屉（UI 风格固化，禁止各页面重复调试）

用法：
  <AppDrawer v-model="show" title="企业需求申报" :icon="Document" size="720px">
    <div class="sticky-tabs">   (需要 tab 冻结时包上 el-tabs)
      ...
    </div>
    <template #footer>   (取消/保存按钮)
      ...
    </template>
  </AppDrawer>

内置约定：
  - 渐变蓝标题栏（icon + 标题），顶住上/右边缘
  - 主体 .app-drawer-body 统一样式
  - footer 按钮整体居中 + 顶部横条
  - .sticky-tabs 使 tab 标题栏滚动冻结
  - .declare-form 表单 label 左对齐（首个汉字对齐，必填星号在左侧不参与对齐）
-->
<template>
  <el-drawer
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    direction="rtl"
    :size="size"
    :destroy-on-close="destroyOnClose"
    :close-on-click-modal="closeOnClickModal"
  >
    <!-- 标题栏：渐变 + icon，顶住上/右边缘 -->
    <template #header>
      <div class="app-drawer-title-bar">
        <span class="app-drawer-title">
          <el-icon v-if="icon"><component :is="icon" /></el-icon>
          {{ title }}
        </span>
        <span v-if="subtitle" class="app-drawer-subtitle">{{ subtitle }}</span>
      </div>
    </template>

    <!-- 主体 -->
    <div class="app-drawer-body">
      <slot />
    </div>

    <!-- 底部按钮区：整体居中 + 上分隔横条 -->
    <template #footer v-if="$slots.footer">
      <div class="app-drawer-footer">
        <slot name="footer" />
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  icon: { type: Object, default: null },   // @element-plus/icons-vue 组件
  size: { type: String, default: '720px' },
  destroyOnClose: { type: Boolean, default: true },
  closeOnClickModal: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])
</script>

<style scoped>
/* ---- 标题栏：顶住上方与右侧边缘 + 底部横条顶满左右 ---- */
:deep(.el-drawer__header) {
  padding: 0 !important;
  margin: 0 !important;
  border-bottom: none;
}
.app-drawer-title-bar {
  background: linear-gradient(135deg, #5b9bd5 0%, #8ab8e8 100%);
  padding: 18px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.45);   /* 标题栏底部横条：随标题栏顶满左右 */
}
.app-drawer-title {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.app-drawer-subtitle {
  color: rgba(255, 255, 255, 0.85);
  font-size: 12px;
  letter-spacing: 0.5px;
}

/* ---- 主体 ---- */
:deep(.el-drawer__body) {
  padding: 0 !important;
  overflow-y: auto;
}
.app-drawer-body {
  padding: 14px 20px 24px;
}

/* ---- 底部按钮区：居中 + 分隔横条 ---- */
:deep(.el-drawer__footer) {
  padding: 0 !important;
  border-top: 1px solid #ebeef5;
}
.app-drawer-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #fafbfc;
}

/* ---- tab 冻结（使用时在外层包 .sticky-tabs）---- */
:deep(.sticky-tabs .el-tabs__header) {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #fff;
  margin: 0 -20px 4px;
  padding: 0 20px;
}

/* ---- 表单 label 对齐：所有 label 文本首个汉字在同一列（必填星号绝对定位在左侧，不参与对齐） ---- */
:deep(.declare-form .el-form-item) {
  margin-bottom: 16px;
}
:deep(.declare-form .el-form-item__label) {
  position: relative;
  text-align: left !important;
  justify-content: flex-start !important;
  padding-right: 12px;
  padding-left: 16px;        /* 所有 label 文本统一右移，required/非 required 首字对齐 */
  line-height: 32px;
}
:deep(.declare-form .el-form-item.is-required .el-form-item__label::before) {
  position: absolute;
  left: 2px;
  top: 0;
  margin-right: 0;
}
:deep(.declare-form .el-input__count, .declare-form .el-textarea__count) {
  background: transparent;
}
</style>
