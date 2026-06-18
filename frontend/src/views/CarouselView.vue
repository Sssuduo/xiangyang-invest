<template>
  <!-- 演示模式：全屏覆盖 -->
  <div v-if="isPresenting" class="presentation-overlay" @keydown="handleKeydown" tabindex="0" ref="presentRef">
    <button class="present-exit-btn" @click="exitPresentation">✕ 退出演示</button>
    <div
      v-for="(page, index) in pages"
      :key="'pres-' + page.id"
      class="present-slide"
      :class="{ active: index === currentIndex }"
    >
      <ImageTextSlide v-if="page.page_type === 'image_text'" :page="page" />
      <MapSlide v-else-if="page.page_type === 'map'" :page="page" />
    </div>
    <button v-if="pages.length > 1" class="carousel-nav-btn prev" @click="prevSlide">‹</button>
    <button v-if="pages.length > 1" class="carousel-nav-btn next" @click="nextSlide">›</button>
    <div v-if="pages.length > 1" class="carousel-indicators">
      <button v-for="(p, i) in pages" :key="'dp-'+p.id" class="carousel-dot" :class="{active:i===currentIndex}" @click="goToSlide(i)" />
    </div>
  </div>

  <!-- 正常模式 -->
  <div v-else class="carousel-container" @keydown="handleKeydown" tabindex="0" ref="containerRef">
    <button class="carousel-back-btn" @click="$router.push('/')">← 返回首页</button>
    <button class="present-btn" @click="enterPresentation" title="全屏演示模式">⛶ 演示模式</button>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="40"><Loading /></el-icon>
      <p>加载中...</p>
    </div>

    <!-- 幻灯片 -->
    <template v-else>
      <div
        v-for="(page, index) in pages"
        :key="page.id"
        class="carousel-slide"
        :class="{ active: index === currentIndex }"
      >
        <ImageTextSlide v-if="page.page_type === 'image_text'" :page="page" />
        <MapSlide v-else-if="page.page_type === 'map'" :page="page" />
      </div>

      <button v-if="pages.length > 1" class="carousel-nav-btn prev" @click="prevSlide">‹</button>
      <button v-if="pages.length > 1" class="carousel-nav-btn next" @click="nextSlide">›</button>
      <div v-if="pages.length > 1" class="carousel-indicators">
        <button v-for="(p, i) in pages" :key="'d-'+p.id" class="carousel-dot" :class="{active:i===currentIndex}" @click="goToSlide(i)" />
      </div>

      <!-- 空状态：仅在加载完成且确实无数据时显示 -->
      <div v-if="!loading && pages.length === 0" class="empty-state">
        <p>暂无内容，请先在管理后台添加轮播页</p>
        <el-button @click="$router.push('/')">返回首页</el-button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getCarouselPages } from '@/api/carousel'
import { getHomepageConfig } from '@/api/homepage'
import ImageTextSlide from '@/components/carousel/ImageTextSlide.vue'
import MapSlide from '@/components/carousel/MapSlide.vue'

const pages = ref([])
const currentIndex = ref(0)
const containerRef = ref(null)
const presentRef = ref(null)
const loading = ref(true)
const isPresenting = ref(false)
let autoPlayTimer = null
let intervalSeconds = 8

onMounted(async () => {
  try {
    const [pagesRes, configRes] = await Promise.all([
      getCarouselPages(),
      getHomepageConfig()
    ])
    if (pagesRes.code === 0) {
      pages.value = pagesRes.data || []
    }
    if (configRes.code === 0 && configRes.data?.carousel_interval) {
      intervalSeconds = configRes.data.carousel_interval
    }
  } catch {
    // 加载失败
  } finally {
    loading.value = false
    if (pages.value.length > 1) {
      startAutoPlay()
    }
    nextTick(() => containerRef.value?.focus())
  }
})

onUnmounted(() => stopAutoPlay())

function startAutoPlay() {
  stopAutoPlay()
  if (pages.value.length > 1) {
    autoPlayTimer = setInterval(() => {
      currentIndex.value = (currentIndex.value + 1) % pages.value.length
    }, intervalSeconds * 1000)
  }
}
function stopAutoPlay() {
  if (autoPlayTimer) { clearInterval(autoPlayTimer); autoPlayTimer = null }
}
function prevSlide() { stopAutoPlay(); currentIndex.value = (currentIndex.value - 1 + pages.value.length) % pages.value.length; startAutoPlay() }
function nextSlide() { stopAutoPlay(); currentIndex.value = (currentIndex.value + 1) % pages.value.length; startAutoPlay() }
function goToSlide(i) { stopAutoPlay(); currentIndex.value = i; startAutoPlay() }
function handleKeydown(e) {
  if (e.key === 'ArrowLeft') prevSlide()
  if (e.key === 'ArrowRight') nextSlide()
  if (e.key === 'Escape') isPresenting.value ? exitPresentation() : window.history.back()
}

function enterPresentation() {
  isPresenting.value = true
  stopAutoPlay()
  nextTick(() => {
    presentRef.value?.focus()
    if (pages.value.length > 1) startAutoPlay()
  })
}
function exitPresentation() {
  isPresenting.value = false
  stopAutoPlay()
  nextTick(() => {
    containerRef.value?.focus()
    if (pages.value.length > 1) startAutoPlay()
  })
}
</script>

<style scoped>
@import '@/assets/styles/carousel.css';

.carousel-container { outline: none; }

.loading-state {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
  display: flex; flex-direction: column; align-items: center; gap: 16px; color: rgba(255,255,255,0.7);
}
.empty-state {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
  text-align: center; color: #fff;
}
.empty-state p { font-size: 18px; margin-bottom: 20px; opacity: 0.7; }

.present-btn {
  position: absolute; top: 24px; right: 80px; z-index: 20;
  padding: 8px 18px; border: 1px solid rgba(255,255,255,.3); border-radius: 8px;
  background: rgba(0,0,0,.3); color: #fff; font-size: 14px; cursor: pointer;
  backdrop-filter: blur(4px); transition: all .3s;
}
.present-btn:hover { background: rgba(0,0,0,.5); }

.presentation-overlay {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
  background: #000; z-index: 9999; outline: none;
}
.present-exit-btn {
  position: absolute; top: 20px; right: 20px; z-index: 10001;
  padding: 12px 24px; border: 2px solid rgba(255,255,255,.5); border-radius: 10px;
  background: rgba(0,0,0,.5); color: #fff; font-size: 16px; cursor: pointer;
  backdrop-filter: blur(8px); transition: all .3s;
}
.present-exit-btn:hover { background: rgba(220,38,38,.7); border-color: #fff; }
.present-slide {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; transition: opacity 0.6s;
}
.present-slide.active { opacity: 1; }
</style>
