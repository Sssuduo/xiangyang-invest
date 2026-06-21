<template>
  <header class="top-nav" :class="[navClass, { scrolled: props.scrolled }]">
    <div class="nav-inner">
      <router-link to="/" class="nav-brand">
        <span class="brand-text">襄阳农高区</span>
      </router-link>
      <nav class="nav-menu">
        <router-link to="/national" class="nav-item" active-class="active-item">国家农高区</router-link>
        <router-link to="/intro" class="nav-item" active-class="active-item">襄阳农高区介绍</router-link>
        <!-- 招商项目库 下拉菜单 -->
        <el-dropdown trigger="hover" class="nav-dropdown" @command="handleCommand">
          <span class="nav-item nav-dropdown-trigger" :class="{ 'is-active': isInvestmentRoute }">
            招商项目库
            <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="/investment">招商项目管理</el-dropdown-item>
              <el-dropdown-item command="/investment-activity">招商动态管理</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <router-link to="/contact" class="nav-item" active-class="active-item">联系我们</router-link>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  variant: { type: String, default: 'light' }, // 'home' | 'light' | 'overlay' | 'contact'
  scrolled: { type: Boolean, default: false }
})

const route = useRoute()
const router = useRouter()

const isInvestmentRoute = computed(() => route.path.startsWith('/investment'))

function handleCommand(path) {
  if (route.path !== path) {
    router.push(path)
  }
}

const navClass = computed(() => `nav-${props.variant}`)
</script>

<style scoped>
/* ===== 基础共用 ===== */
.top-nav { top: 0; left: 0; right: 0; z-index: 100; display: flex; align-items: center; padding: 0 48px; }
.nav-inner { width: 100%; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; }
.nav-brand { text-decoration: none; font-weight: 700; letter-spacing: 3px; }
.brand-text { background: linear-gradient(90deg, #1a3a5c, #2a5a8c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.nav-menu { display: flex; align-items: center; }
.nav-item {
  text-decoration: none; font-weight: 400; letter-spacing: 1px;
  padding: 4px 0; position: relative; transition: color 0.3s; cursor: pointer;
}
.nav-item::after {
  content: ''; position: absolute; bottom: -2px; left: 0; width: 0; height: 2px;
  border-radius: 1px; transition: width 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.nav-item:hover::after { width: 100%; }
.active-item::after { width: 100%; }

/* 下拉触发器 */
.nav-dropdown { display: flex; align-items: center; }
.nav-dropdown-trigger { display: inline-flex; align-items: center; gap: 2px; }
.dropdown-arrow { font-size: 12px; transition: transform 0.2s; }

/* ===== home 变体（深色透明→毛玻璃） ===== */
.nav-home {
  position: fixed; z-index: 1000; height: 72px;
  background: transparent; transition: background 0.4s, backdrop-filter 0.4s, box-shadow 0.4s;
}
.nav-home.scrolled {
  background: rgba(15, 25, 35, 0.85);
  backdrop-filter: saturate(180%) blur(20px);
  box-shadow: 0 1px 0 rgba(255,255,255,0.06);
}
.nav-home .nav-inner { max-width: 1280px; }
.nav-home .nav-brand { font-size: 22px; }
.nav-home .brand-text { background: linear-gradient(90deg, #fff, #cfd9e6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.nav-home .nav-menu { gap: 40px; }
.nav-home .nav-item { color: rgba(255,255,255,0.75); font-size: 15px; padding: 6px 0; }
.nav-home .nav-item::after { bottom: 0; background: #fff; }
.nav-home .nav-item:hover { color: #fff; }
.nav-home .active-item { color: #fff; }

/* ===== light 变体（粘性白色毛玻璃） ===== */
.nav-light {
  position: sticky; height: 64px;
  background: rgba(255,255,255,0.72); backdrop-filter: saturate(180%) blur(16px);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
}
.nav-light .nav-inner { max-width: 1600px; }
.nav-light .nav-brand { font-size: 20px; }
.nav-light .nav-menu { gap: 36px; }
.nav-light .nav-item { color: #4a5568; font-size: 14px; }
.nav-light .nav-item::after { background: #1a3a5c; }
.nav-light .nav-item:hover { color: #1a3a5c; }
.nav-light .active-item { color: #1a3a5c; font-weight: 600; }
.nav-light .is-active { color: #1a3a5c; font-weight: 600; }
.nav-light .is-active::after { width: 100%; }

/* ===== overlay 变体（绝对定位，透明叠加） ===== */
.nav-overlay {
  position: absolute; height: 64px;
  background: rgba(255,255,255,0.55); backdrop-filter: saturate(180%) blur(12px);
  box-shadow: 0 1px 0 rgba(0,0,0,0.04);
}
.nav-overlay .nav-inner { max-width: 1600px; }
.nav-overlay .nav-brand { font-size: 20px; }
.nav-overlay .nav-menu { gap: 36px; }
.nav-overlay .nav-item { color: #4a5568; font-size: 14px; }
.nav-overlay .nav-item::after { background: #1a3a5c; }
.nav-overlay .nav-item:hover { color: #1a3a5c; }
.nav-overlay .active-item { color: #1a3a5c; font-weight: 600; }
.nav-overlay .is-active { color: #1a3a5c; font-weight: 600; }
.nav-overlay .is-active::after { width: 100%; }

/* ===== contact 变体（固定白色毛玻璃 72px） ===== */
.nav-contact {
  position: fixed; z-index: 1000; height: 72px;
  background: rgba(255,255,255,0.82); backdrop-filter: saturate(180%) blur(20px);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
}
.nav-contact .nav-inner { max-width: 1280px; }
.nav-contact .nav-brand { font-size: 22px; }
.nav-contact .nav-menu { gap: 40px; }
.nav-contact .nav-item { color: #4a5568; font-size: 15px; padding: 6px 0; }
.nav-contact .nav-item::after { bottom: 0; background: #1a3a5c; }
.nav-contact .nav-item:hover { color: #1a3a5c; }
.nav-contact .active-item { color: #1a3a5c; font-weight: 600; }
.nav-contact .is-active { color: #1a3a5c; font-weight: 600; }
.nav-contact .is-active::after { width: 100%; }
</style>
