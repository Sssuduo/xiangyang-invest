<template>
  <div class="national-page">
    <!-- ===== 顶部导航栏（透明叠加） ===== -->
    <BusinessNavbar variant="overlay" />

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
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'

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
