<template>
  <div class="homepage" :style="bgStyle">
    <!-- ===== 顶部导航栏 ===== -->
    <header class="top-nav" :class="{ scrolled: isScrolled }">
      <div class="nav-inner">
        <!-- Logo / 品牌名 -->
        <router-link to="/" class="nav-brand">
          <span class="brand-text">襄阳农高区</span>
        </router-link>

        <!-- 导航菜单 -->
        <nav class="nav-menu">
          <router-link to="/national" class="nav-item">国家农高区</router-link>
          <router-link to="/intro" class="nav-item">襄阳农高区介绍</router-link>
          <router-link to="/toolbox" class="nav-item">招商工具箱</router-link>
          <router-link to="/contact" class="nav-item">联系我们</router-link>
        </nav>
      </div>
    </header>

    <!-- ===== 主视觉区 ===== -->
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">{{ config.title_text || '襄阳农高区' }}</h1>
        <p class="hero-subtitle">{{ config.subtitle_text || '招商服务一站式平台' }}</p>
      </div>

      <!-- 向下滚动提示 -->
      <div class="scroll-hint" v-if="!isScrolled">
        <span class="scroll-arrow">↓</span>
      </div>
    </div>

    <!-- 管理入口 -->
    <footer class="homepage-footer">
      <router-link to="/admin/login" class="admin-link">管理入口</router-link>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getHomepageConfig } from '@/api/homepage'

const config = ref({
  background_image: '',
  title_text: '襄阳农高区',
  subtitle_text: '招商服务一站式平台'
})

const isScrolled = ref(false)

function onScroll() {
  isScrolled.value = window.scrollY > 50
}

const bgStyle = computed(() => {
  if (config.value.background_image) {
    return {
      backgroundImage: `url(${config.value.background_image})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat'
    }
  }
  return {
    background: 'linear-gradient(135deg, #0f1923 0%, #1a3a5c 50%, #0d2137 100%)'
  }
})

onMounted(async () => {
  window.addEventListener('scroll', onScroll, { passive: true })
  try {
    const res = await getHomepageConfig()
    if (res.code === 0 && res.data) {
      config.value = res.data
    }
  } catch { /* 使用默认配置 */ }
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})
</script>

<style scoped>
/* ============================================================
   整体
   ============================================================ */
.homepage {
  width: 100vw; min-height: 100vh;
  position: relative; overflow-x: hidden;
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif;
}

/* ============================================================
   顶部导航栏 — OPPO 风格：透明→毛玻璃
   ============================================================ */
.top-nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
  padding: 0 48px; height: 72px;
  display: flex; align-items: center;
  transition: background 0.4s, backdrop-filter 0.4s, box-shadow 0.4s;
  background: transparent;
}
.top-nav.scrolled {
  background: rgba(15, 25, 35, 0.85);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  box-shadow: 0 1px 0 rgba(255,255,255,0.06);
}

.nav-inner {
  width: 100%; max-width: 1280px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
}

/* 品牌 */
.nav-brand {
  text-decoration: none; color: #fff;
  font-size: 22px; font-weight: 700; letter-spacing: 3px;
  transition: opacity 0.3s;
}
.nav-brand:hover { opacity: 0.8; }
.brand-text {
  background: linear-gradient(90deg, #fff, #cfd9e6);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 菜单 */
.nav-menu { display: flex; gap: 40px; align-items: center; }
.nav-item {
  text-decoration: none; color: rgba(255,255,255,0.75);
  font-size: 15px; font-weight: 400; letter-spacing: 1px;
  padding: 6px 0;
  position: relative;
  transition: color 0.3s;
}
.nav-item::after {
  content: ''; position: absolute; bottom: 0; left: 0; width: 0; height: 2px;
  background: #fff; border-radius: 1px;
  transition: width 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.nav-item:hover { color: #fff; }
.nav-item:hover::after { width: 100%; }
.nav-item.router-link-active { color: #fff; }
.nav-item.router-link-active::after { width: 100%; }

/* ============================================================
   主视觉区 — 全屏 hero
   ============================================================ */
.hero-section {
  width: 100%; min-height: 100vh;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  position: relative;
}

.hero-content {
  text-align: center; color: #fff;
  animation: fadeInUp 1.2s cubic-bezier(0.16, 1, 0.3, 1);
  padding: 0 32px;
}

.hero-title {
  font-size: clamp(36px, 5.5vw, 64px);
  font-weight: 700; letter-spacing: 6px;
  margin-bottom: 20px; line-height: 1.2;
  text-shadow: 0 2px 20px rgba(0,0,0,0.3);
}

.hero-subtitle {
  font-size: clamp(16px, 2vw, 22px);
  font-weight: 300; letter-spacing: 6px;
  margin-bottom: 64px; opacity: 0.85;
  text-shadow: 0 1px 8px rgba(0,0,0,0.2);
}

/* 向下滚动提示 */
.scroll-hint {
  position: absolute; bottom: 40px; left: 50%; transform: translateX(-50%);
  animation: bounce 2s infinite;
}
.scroll-arrow { color: rgba(255,255,255,0.4); font-size: 28px; }

/* ============================================================
   底部
   ============================================================ */
.homepage-footer {
  position: fixed; bottom: 24px; right: 32px; z-index: 100;
}
.admin-link {
  color: rgba(255,255,255,0.25); font-size: 12px; text-decoration: none;
  transition: color 0.3s;
}
.admin-link:hover { color: rgba(255,255,255,0.6); }

/* ============================================================
   动画
   ============================================================ */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(48px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes bounce {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  50%      { transform: translateX(-50%) translateY(8px); }
}
</style>
