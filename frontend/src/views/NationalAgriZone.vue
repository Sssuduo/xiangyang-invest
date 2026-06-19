<template>
  <div class="national-page">
    <!-- ===== 顶部导航栏（透明叠加） ===== -->
    <header class="top-nav">
      <div class="nav-inner">
        <router-link to="/" class="nav-brand">
          <span class="brand-text">襄阳农高区</span>
        </router-link>
        <nav class="nav-menu">
          <router-link to="/national" class="nav-item active-item">国家农高区</router-link>
          <router-link to="/intro" class="nav-item">襄阳农高区介绍</router-link>
          <router-link to="/toolbox" class="nav-item">招商工具箱</router-link>
          <router-link to="/contact" class="nav-item">联系我们</router-link>
        </nav>
      </div>
    </header>

    <!-- ===== 地图主体（全屏） ===== -->
    <div class="map-stage">
      <ChinaMap
        map-scope="china"
        :interactive="true"
        :show-scope-toggle="false"
        :map-center="[104, 37]"
        :map-zoom="1.35"
        highlight-color="#5a9e6f"
        city-highlight-color="#d4a94e"
        class="full-map"
        @focus-change="handleFocusChange"
      />
    </div>

    <!-- 底部图例：聚焦省级地图时仅展示淡金色图例 -->
    <div class="map-legend">
      <template v-if="isMapFocused">
        <div class="legend-item">
          <span class="legend-dot city-gold"></span>
          <span>国家级农高区</span>
        </div>
      </template>
      <template v-else>
        <div class="legend-item">
          <span class="legend-dot highlight"></span>
          <span>国家级农高区（绿色）</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot normal"></span>
          <span>其他省份</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChinaMap from '@/components/map/ChinaMap.vue'

const isMapFocused = ref(false)

function handleFocusChange(province) {
  isMapFocused.value = !!province
}
</script>

<style scoped>
/* ============================================================
   整体：全屏
   ============================================================ */
.national-page {
  width: 100vw; height: 100vh; overflow: hidden;
  position: relative;
  background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%);
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif;
}

/* ============================================================
   顶部导航栏 — 透明毛玻璃
   ============================================================ */
.top-nav {
  position: absolute; top: 0; left: 0; right: 0; z-index: 100;
  padding: 0 48px; height: 64px;
  display: flex; align-items: center;
  background: rgba(255,255,255,0.72);
  backdrop-filter: saturate(180%) blur(16px);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
}
.nav-inner {
  width: 100%; max-width: 1400px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
}
.nav-brand { text-decoration: none; font-size: 20px; font-weight: 700; letter-spacing: 3px; }
.brand-text {
  background: linear-gradient(90deg, #1a3a5c, #2a5a8c);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.nav-menu { display: flex; gap: 36px; align-items: center; }
.nav-item {
  text-decoration: none; color: #4a5568; font-size: 14px;
  font-weight: 400; letter-spacing: 1px; padding: 4px 0;
  position: relative; transition: color 0.3s;
}
.nav-item::after {
  content: ''; position: absolute; bottom: -2px; left: 0; width: 0; height: 2px;
  background: #1a3a5c; border-radius: 1px;
  transition: width 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.nav-item:hover { color: #1a3a5c; }
.nav-item:hover::after { width: 100%; }
.active-item { color: #1a3a5c; font-weight: 600; }
.active-item::after { width: 100%; }

/* ============================================================
   地图舞台
   ============================================================ */
.map-stage {
  position: absolute;
  top: 64px;  /* 导航栏高度 */
  left: 0; right: 0; bottom: 0;
  padding: 8px 8px 0; box-sizing: border-box;
}
.full-map {
  width: 100%; height: 100%;
}

/* ============================================================
   底部图例
   ============================================================ */
.map-legend {
  position: absolute; bottom: 28px; left: 50%; transform: translateX(-50%);
  z-index: 50;
  display: flex; gap: 28px; align-items: center;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 24px;
  padding: 10px 24px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.06);
}
.legend-item {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: #4a5568; letter-spacing: 0.5px;
}
.legend-dot {
  width: 12px; height: 12px; border-radius: 3px;
}
.legend-dot.highlight {
  background: #5a9e6f;
  box-shadow: 0 0 6px rgba(90,158,111,0.4);
}
.legend-dot.city-gold {
  background: #d4a94e;
  box-shadow: 0 0 6px rgba(212,169,78,0.5);
}
.legend-dot.normal {
  background: #c8d2dc;
  border: 1px solid #b0bcc6;
}
</style>
