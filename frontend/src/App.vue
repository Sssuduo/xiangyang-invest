<template>
  <div id="app-root">
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
#app-root {
  width: 100%;
  min-height: 100vh;
}

/* 诉求卡片编辑/删除按钮颜色（修复全局 --el-color-primary 被覆盖导致颜色过深） */
.demand-card-actions .el-button.is-link { font-weight: 500; }
.demand-card-actions .el-button--primary.is-link { color: #409eff; }
.demand-card-actions .el-button--danger.is-link { color: #f56c6c; }
.demand-card-actions .el-button.is-link .el-icon { color: inherit; }
</style>
