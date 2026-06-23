<template>
  <div class="homepage" :style="bgStyle">
    <!-- ===== 顶部导航栏 ===== -->
    <BusinessNavbar variant="home" :scrolled="isScrolled" />

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
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import { toWebpUrl } from '@/utils/webp'

const config = ref({
  background_image: '',
  title_text: '襄阳农高区',
  subtitle_text: '招商服务一站式平台'
})

const bgImageUrl = ref('')

const isScrolled = ref(false)

function onScroll() {
  isScrolled.value = window.scrollY > 50
}

const bgStyle = computed(() => {
  const imgUrl = bgImageUrl.value || config.value.background_image
  if (imgUrl) {
    return {
      backgroundImage: `url(${imgUrl})`,
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
      // 异步转换 WebP URL（不阻塞渲染）
      toWebpUrl(res.data.background_image).then(url => { bgImageUrl.value = url })
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
