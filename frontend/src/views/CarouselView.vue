<!--
  ============================================================
  农高区介绍页（业务端）
  ============================================================
  本轮重构：
    • 轮播交互为纯原生实现（@/features/carousel/）
    • 本组件是「数据壳」：fetch 接口 → 交给原生 initCarousel 构建 DOM
    • 页面顶部带导航栏（不再全屏覆盖），淡蓝背景
    • 底部胶卷式缩略图进度（原生轮播内部实现）
  路由：/intro
-->
<template>
  <div class="intro-page">
    <!-- 顶部导航栏：正常显示，不被轮播遮挡 -->
    <BusinessNavbar variant="light" />
    <!-- 原生轮播会接管这个根元素的内部 DOM -->
    <div ref="rootRef" class="carousel-shell"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import BusinessNavbar from '@/components/common/BusinessNavbar.vue';
import { initCarousel } from '@/features/carousel/carousel.js';
import '@/features/carousel/carousel.css';
import { getCarouselPages } from '@/api/carousel';
import { getHomepageConfig } from '@/api/homepage';

const rootRef = ref(null);
let carouselHandle = null;

onMounted(async () => {
  try {
    const res = await getCarouselPages();
    // 读取轮播配置（自动播放间隔 / 是否自动播放）
    let config = { interval: 5, autoplay: true };
    try {
      const cfgRes = await getHomepageConfig();
      if (cfgRes.code === 0 && cfgRes.data) {
        config = {
          interval: cfgRes.data.carousel_interval ?? 5,
          autoplay: cfgRes.data.carousel_autoplay ?? true,
        };
      }
    } catch { /* 使用默认配置 */ }

    if (res.code === 0 && res.data?.length && rootRef.value) {
      // 等一帧布局完成后再初始化，避免 clientHeight=0 导致白屏
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          carouselHandle = initCarousel(rootRef.value, res.data, {
            interval: config.interval,
            autoplay: config.autoplay,
            // onCardClick: (card) => { ... },
          });
        });
      });
    }
  } catch (err) {
    console.error('轮播数据加载失败:', err);
  }
});

onUnmounted(() => {
  carouselHandle?.destroy();
});
</script>

<style scoped>
/* 页面精确一屏：导航栏叠加在轮播上方，轮播撑满 100vh */
.intro-page {
  height: 100vh;
  position: relative;
  overflow: hidden;
}
/* 导航栏改为叠加模式（不占文档流高度） */
.intro-page :deep(.top-nav) {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
}
.carousel-shell {
  height: 100vh;
  width: 100%;
}
</style>
