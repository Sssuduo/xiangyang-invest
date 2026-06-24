<template>
  <div class="construction-page">
    <BusinessNavbar variant="light" />
    <div class="page-body">
      <div class="content-card" style="text-align: center; padding: 80px 24px;">
        <el-icon :size="48" color="#909399"><Clock /></el-icon>
        <h2 style="color: #303133; margin: 20px 0 8px;">{{ title }}</h2>
        <p style="color: #909399;">功能开发中，敬请期待...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Clock } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'

defineProps({
  title: { type: String, default: '功能开发中' }
})
</script>

<style scoped>
.construction-page { min-height: 100vh; background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%); }
.page-body { max-width: 1600px; margin: 0 auto; padding: 28px 32px 60px; }
.content-card { background: #fff; border-radius: 12px; box-shadow: 0 2px 20px rgba(0,0,0,0.06); }
</style>
