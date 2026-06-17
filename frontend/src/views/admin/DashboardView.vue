<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <h2>管理仪表盘</h2>
        <p class="text-secondary">欢迎回来，{{ adminStore.user?.display_name || '管理员' }}</p>

        <el-row :gutter="20" style="margin-top: 30px">
          <el-col :span="6">
            <div class="stat-card" @click="$router.push('/admin/pages')">
              <div class="stat-number">{{ stats.pages }}</div>
              <div class="stat-label">轮播页</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card" @click="$router.push('/admin/provinces')">
              <div class="stat-number">{{ stats.provinces }}</div>
              <div class="stat-label">省份/城市</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card" @click="$router.push('/admin/models')">
              <div class="stat-number">{{ stats.models }}</div>
              <div class="stat-label">大模型</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card" @click="$router.push('/admin/prompts')">
              <div class="stat-number">{{ stats.prompts }}</div>
              <div class="stat-label">快捷提示词</div>
            </div>
          </el-col>
        </el-row>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { useAdminStore } from '@/stores/admin'
import { getAdminPages } from '@/api/carousel'
import { getAdminProvinces } from '@/api/province'
import { getAdminModels } from '@/api/model'
import { getAdminPrompts } from '@/api/prompt'

const adminStore = useAdminStore()
const stats = ref({ pages: 0, provinces: 0, models: 0, prompts: 0 })

onMounted(async () => {
  try {
    const [pages, provinces, models, prompts] = await Promise.all([
      getAdminPages(),
      getAdminProvinces(),
      getAdminModels(),
      getAdminPrompts()
    ])
    stats.value.pages = pages.data?.length || 0
    stats.value.provinces = provinces.data?.length || 0
    stats.value.models = models.data?.length || 0
    stats.value.prompts = prompts.data?.length || 0
  } catch { /* ignore */ }
})
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}

.admin-main {
  flex: 1;
  background: var(--bg-light);
}

.admin-content {
  padding: 32px;
  max-width: 1200px;
}

h2 {
  color: var(--primary-color);
  margin-bottom: 8px;
}

.text-secondary {
  color: var(--text-secondary);
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 28px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: var(--shadow-sm);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}

.stat-number {
  font-size: 36px;
  font-weight: 700;
  color: var(--primary-color);
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 8px;
}
</style>
