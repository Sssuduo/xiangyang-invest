<template>
  <el-menu
    :default-active="activeMenu"
    router
    class="admin-sidebar"
    background-color="#1a3a5c"
    text-color="rgba(255,255,255,0.7)"
    active-text-color="#fff"
  >
    <div class="sidebar-header">
      <h3>管理后台</h3>
    </div>

    <el-menu-item index="/admin">
      <el-icon><HomeFilled /></el-icon>
      <span>仪表盘</span>
    </el-menu-item>

    <el-menu-item index="/admin/homepage">
      <el-icon><Picture /></el-icon>
      <span>首页配置</span>
    </el-menu-item>

    <el-menu-item index="/admin/pages">
      <el-icon><Film /></el-icon>
      <span>轮播页管理</span>
    </el-menu-item>

    <el-menu-item index="/admin/carousel">
      <el-icon><Setting /></el-icon>
      <span>轮播设置</span>
    </el-menu-item>

    <!-- 招商项目管理 -->
    <el-menu-item index="/admin/investment">
      <el-icon><Folder /></el-icon>
      <span>招商项目管理</span>
    </el-menu-item>

    <!-- 招商动态管理 -->
    <el-menu-item index="/admin/activity">
      <el-icon><Notebook /></el-icon>
      <span>招商动态管理</span>
    </el-menu-item>

    <!-- 导出配置子菜单 -->
    <el-sub-menu index="sub-export">
      <template #title>
        <el-icon><Download /></el-icon>
        <span>导出配置</span>
      </template>
      <el-menu-item index="/admin/export-config">招商项目导出</el-menu-item>
      <el-menu-item index="/admin/activity-export-config">招商动态导出</el-menu-item>
    </el-sub-menu>

    <!-- 导入配置子菜单 -->
    <el-sub-menu index="sub-import">
      <template #title>
        <el-icon><Upload /></el-icon>
        <span>导入配置</span>
      </template>
      <el-menu-item index="/admin/import-config">招商项目导入</el-menu-item>
      <el-menu-item index="/admin/activity-import-config">招商动态导入</el-menu-item>
    </el-sub-menu>

    <el-menu-item index="/admin/provinces">
      <el-icon><Location /></el-icon>
      <span>省份信息</span>
    </el-menu-item>

    <el-menu-item index="/admin/models">
      <el-icon><Cpu /></el-icon>
      <span>大模型管理</span>
    </el-menu-item>

    <el-menu-item index="/admin/contact">
      <el-icon><User /></el-icon>
      <span>联系我们</span>
    </el-menu-item>

    <el-menu-item index="/admin/prompts">
      <el-icon><ChatDotSquare /></el-icon>
      <span>提示词管理</span>
    </el-menu-item>

    <div class="sidebar-footer">
      <div class="debug-toggle">
        <el-button
          text
          size="small"
          @click="debug.toggle()"
          :style="{ color: debug.isDebugEnabled.value ? '#e6a23c' : 'rgba(255,255,255,0.3)', width: '100%', fontSize: '12px' }"
        >
          🐛 {{ debug.isDebugEnabled.value ? 'Debug ON' : 'Debug OFF' }}
        </el-button>
      </div>
      <el-button text @click="handleLogout" style="color: rgba(255,255,255,0.5); width: 100%">
        退出登录
      </el-button>
    </div>
  </el-menu>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAdminStore } from '@/stores/admin'
import { useDebug } from '@/utils/debug'
import { ElMessage } from 'element-plus'
import { HomeFilled, Picture, Film, Setting, Download, Upload, Location, Cpu, User, ChatDotSquare, Folder, Notebook } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const adminStore = useAdminStore()
const debug = useDebug()

const activeMenu = computed(() => route.path)

async function handleLogout() {
  await adminStore.logout()
  ElMessage.success('已退出登录')
  router.push('/admin/login')
}
</script>

<style scoped>
.admin-sidebar {
  height: 100vh;
  width: 220px;
  border-right: none;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 24px 20px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 8px;
}
.sidebar-header h3 {
  color: #fff;
  font-size: 18px;
  text-align: center;
}

.sidebar-footer {
  margin-top: auto;
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
