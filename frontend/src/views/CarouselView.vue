<template>
  <!-- ============================================================
       演示模式：全屏纯黑 + 虚化氛围 + 居中主图
       ============================================================ -->
  <div
    v-if="isPresenting"
    class="presentation-overlay"
    @keydown="handlePresentKeydown"
    @mousemove="onPresentMouseMove"
    tabindex="0"
    ref="presentRef"
  >
    <!-- 退出按钮 -->
    <button
      class="present-exit-btn"
      :class="{ visible: showPresentUI }"
      @click="exitPresentation"
    >✕ 退出演示</button>

    <!-- 左右切换按钮 -->
    <button v-if="pages.length > 1" class="present-nav present-prev" :class="{ visible: showPresentUI }" @click.stop="prevSlide">‹</button>
    <button v-if="pages.length > 1" class="present-nav present-next" :class="{ visible: showPresentUI }" @click.stop="nextSlide">›</button>

    <!-- 虚化氛围层（填充图片周围空隙） -->
    <Transition name="ambiance-fade" mode="out-in">
      <div v-if="currentPage?.page_type === 'image_text'" :key="'pa-' + currentIndex" class="present-ambiance">
        <img :src="currentImage" class="present-ambiance-img" alt="" />
      </div>
    </Transition>

    <!-- 主图：contain 居中，点击切到下一页 -->
    <div class="present-img-stage" @click="presentNextSlide">
      <img
        v-if="currentPage?.page_type === 'image_text'"
        :key="'pres-img-' + currentIndex"
        :src="currentImage"
        class="present-main-img"
        alt=""
      />
      <ChinaMap
        v-else-if="currentPage?.page_type === 'map'"
        :key="'pres-map-' + currentIndex"
        :map-scope="currentPage.map_scope || 'china'"
        :interactive="true"
        class="present-main-map"
      />
    </div>

    <!-- 底部页码 -->
    <div class="present-page-num" :class="{ visible: showPresentUI }">
      {{ currentIndex + 1 }} / {{ pages.length }}
    </div>
  </div>

  <!-- ============================================================
       正常模式
       ============================================================ -->
  <div
    v-else
    class="carousel-container"
    @keydown="handleKeydown"
    tabindex="0"
    ref="containerRef"
  >
    <!-- 顶栏按钮 -->
    <button class="carousel-back-btn" @click="$router.push('/')">← 返回首页</button>
    <button class="present-btn" @click="enterPresentation" title="全屏演示模式">⛶ 演示模式</button>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="40"><Loading /></el-icon>
      <p>加载中...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="pages.length === 0" class="empty-state">
      <p>暂无内容，请先在管理后台添加轮播页</p>
      <el-button @click="$router.push('/')">返回首页</el-button>
    </div>

    <!-- 轮播主体 -->
    <template v-else>
      <!-- 背景氛围层（底层） -->
      <div class="ambiance-layer" v-if="isImagePage">
        <Transition name="ambiance-fade" mode="out-in">
          <img :key="'amb-' + currentIndex" :src="currentImage" class="ambiance-img" alt="" />
        </Transition>
      </div>

      <!-- ===== 主舞台：左中右三图 + 箭头，整体居中 ===== -->
      <div class="carousel-stage">
        <!-- 左侧虚化图：固定容器+absolute，过渡互不挤压 -->
        <div class="side-slot left-slot">
          <Transition :name="sideTransitionName">
            <div
              v-if="isImagePage && hasLeftSlide"
              :key="'sl-' + leftIndex"
              class="side-blur"
              @click="prevSlide"
            >
              <img :src="leftImage" alt="" />
            </div>
          </Transition>
        </div>

        <!-- 中间主图：同时滑动（无 mode=out-in 避免黑屏） -->
        <div class="main-img-wrapper">
          <Transition :name="transitionName">
            <div
              v-if="currentPage?.page_type === 'image_text'"
              :key="'img-' + currentIndex"
              class="main-img-inner"
            >
              <img :src="currentImage" class="main-img" alt="" />
              <div v-if="hasText" class="main-text-overlay" v-html="currentPage.rich_text_content" />
            </div>
            <div
              v-else-if="currentPage?.page_type === 'map'"
              :key="'map-' + currentIndex"
              class="main-map-wrapper"
            >
              <ChinaMap :map-scope="currentPage.map_scope || 'china'" :interactive="true" />
            </div>
            <div v-else :key="'empty-' + currentIndex" class="main-img-inner">
              <div class="main-placeholder" />
            </div>
          </Transition>
        </div>

        <!-- 右侧虚化图 -->
        <div class="side-slot right-slot">
          <Transition :name="sideTransitionName">
            <div
              v-if="isImagePage && hasRightSlide"
              :key="'sr-' + rightIndex"
              class="side-blur"
              @click="nextSlide"
            >
              <img :src="rightImage" alt="" />
            </div>
          </Transition>
        </div>
      </div>

      <!-- 左右导航箭头 -->
      <button v-if="pages.length > 1" class="nav-arrow left-arrow" @click.stop="prevSlide">‹</button>
      <button v-if="pages.length > 1" class="nav-arrow right-arrow" @click.stop="nextSlide">›</button>

      <!-- 胶卷式缩略图 -->
      <div v-if="pages.length > 1" class="filmstrip">
        <div class="filmstrip-track">
          <div
            v-for="(p, i) in pages"
            :key="'thumb-' + p.id"
            class="filmstrip-item"
            :class="{ active: i === currentIndex }"
            @click="goToSlide(i)"
          >
            <img v-if="p.page_type === 'image_text' && p.background_image" :src="p.background_image" alt="" />
            <span v-else class="filmstrip-label">{{ p.title || '地图' }}</span>
          </div>
        </div>
      </div>

      <!-- 底部指示器 -->
      <div v-if="pages.length > 1" class="carousel-indicators">
        <button v-for="(p, i) in pages" :key="'d-'+p.id" class="carousel-dot"
          :class="{ active: i === currentIndex }" @click="goToSlide(i)" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getCarouselPages } from '@/api/carousel'
import { getHomepageConfig } from '@/api/homepage'
import ChinaMap from '@/components/map/ChinaMap.vue'

// —— 核心状态 ——
const pages = ref([])
const currentIndex = ref(0)
const loading = ref(true)
const isPresenting = ref(false)
const showPresentUI = ref(false)
const containerRef = ref(null)
const presentRef = ref(null)
const transitionName = ref('slide-next')
const sideTransitionName = ref('side-next')

let autoPlayTimer = null
let presentUITimer = null
let intervalSeconds = 8
let presentationInterval = 5
let carouselAutoplay = true
let presentationAutoplay = true

// —— 当前页 ——
const currentPage = computed(() => pages.value[currentIndex.value] ?? null)
const isImagePage = computed(() => currentPage.value?.page_type === 'image_text')
const currentImage = computed(() => currentPage.value?.background_image || '')

const hasText = computed(() => {
  if (!currentPage.value?.rich_text_content) return false
  const html = currentPage.value.rich_text_content.trim()
  if (!html) return false
  const stripped = html.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, '').trim()
  return stripped.length > 0
})

// —— 左侧/右侧相邻图片 ——
const hasLeftSlide = computed(() => {
  if (!isImagePage.value) return false
  return pages.value.filter(p => p.page_type === 'image_text').length >= 2
})
const leftIndex = computed(() => {
  const total = pages.value.length
  for (let i = 1; i < total; i++) {
    const idx = (currentIndex.value - i + total) % total
    if (pages.value[idx]?.page_type === 'image_text') return idx
  }
  return -1
})
const leftImage = computed(() => leftIndex.value < 0 ? '' : (pages.value[leftIndex.value]?.background_image || ''))

const hasRightSlide = computed(() => {
  if (!isImagePage.value) return false
  return pages.value.filter(p => p.page_type === 'image_text').length >= 2
})
const rightIndex = computed(() => {
  const total = pages.value.length
  for (let i = 1; i < total; i++) {
    const idx = (currentIndex.value + i) % total
    if (pages.value[idx]?.page_type === 'image_text') return idx
  }
  return -1
})
const rightImage = computed(() => rightIndex.value < 0 ? '' : (pages.value[rightIndex.value]?.background_image || ''))

// —— 初始化 ——
onMounted(async () => {
  try {
    const [pagesRes, configRes] = await Promise.all([
      getCarouselPages(),
      getHomepageConfig()
    ])
    if (pagesRes.code === 0) pages.value = pagesRes.data || []
    if (configRes.code === 0 && configRes.data) {
      intervalSeconds = configRes.data.carousel_interval ?? 8
      presentationInterval = configRes.data.presentation_interval ?? 5
      carouselAutoplay = configRes.data.carousel_autoplay ?? true
      presentationAutoplay = configRes.data.presentation_autoplay ?? true
    }
  } catch { /* fallback */ } finally {
    loading.value = false
    if (pages.value.length > 1) startAutoPlay()
    nextTick(() => containerRef.value?.focus())
  }
})

onUnmounted(() => { stopAutoPlay(); clearTimeout(presentUITimer) })

// —— 自动播放 ——
function startAutoPlay() {
  stopAutoPlay()
  if (pages.value.length <= 1) return
  const enabled = isPresenting.value ? presentationAutoplay : carouselAutoplay
  if (!enabled) return
  const intv = isPresenting.value ? presentationInterval : intervalSeconds
  autoPlayTimer = setInterval(() => {
    switchSlide((currentIndex.value + 1) % pages.value.length, 'next')
  }, intv * 1000)
}
function stopAutoPlay() {
  if (autoPlayTimer) { clearInterval(autoPlayTimer); autoPlayTimer = null }
}

// —— 切换逻辑（方向感知） ——
function switchSlide(newIndex, direction) {
  stopAutoPlay()
  transitionName.value = direction === 'prev' ? 'slide-prev' : 'slide-next'
  sideTransitionName.value = direction === 'prev' ? 'side-prev' : 'side-next'
  currentIndex.value = newIndex
  startAutoPlay()
}
function prevSlide() { switchSlide((currentIndex.value - 1 + pages.value.length) % pages.value.length, 'prev') }
function nextSlide() { switchSlide((currentIndex.value + 1) % pages.value.length, 'next') }
function goToSlide(i) { switchSlide(i, i > currentIndex.value ? 'next' : 'prev') }

function handleKeydown(e) {
  if (e.key === 'ArrowLeft') prevSlide()
  if (e.key === 'ArrowRight') nextSlide()
  if (e.key === 'Escape') window.history.back()
}

// —— 演示模式 ——
function enterPresentation() {
  isPresenting.value = true
  showPresentUI.value = false
  stopAutoPlay()
  nextTick(() => { presentRef.value?.focus(); startAutoPlay() })
}
function exitPresentation() {
  isPresenting.value = false
  stopAutoPlay()
  clearTimeout(presentUITimer)
  nextTick(() => { containerRef.value?.focus(); startAutoPlay() })
}
function onPresentMouseMove() {
  showPresentUI.value = true
  clearTimeout(presentUITimer)
  presentUITimer = setTimeout(() => { showPresentUI.value = false }, 3000)
}
function presentNextSlide() {
  if (pages.value.length <= 1) return
  nextSlide()
  showPresentUI.value = true
  clearTimeout(presentUITimer)
  presentUITimer = setTimeout(() => { showPresentUI.value = false }, 3000)
}
function handlePresentKeydown(e) {
  if (e.key === 'ArrowLeft') prevSlide()
  if (e.key === 'ArrowRight') nextSlide()
  if (e.key === 'Escape') exitPresentation()
  showPresentUI.value = true
  clearTimeout(presentUITimer)
  presentUITimer = setTimeout(() => { showPresentUI.value = false }, 3000)
}
</script>

<style scoped>
/* ============================================================
   容器
   ============================================================ */
.carousel-container {
  width: 100vw; height: 100vh;
  background: radial-gradient(ellipse at center, #1e2a38 0%, #0a0d12 100%);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  position: relative; overflow: hidden; outline: none;
}

/* ============================================================
   背景氛围层
   ============================================================ */
.ambiance-layer {
  position: absolute; inset: 0; z-index: 1; overflow: hidden; pointer-events: none;
}
.ambiance-img {
  width: 100%; height: 100%; object-fit: cover;
  filter: blur(20px); transform: scale(1.1); opacity: 0.4;
}
.ambiance-fade-enter-active, .ambiance-fade-leave-active { transition: opacity 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94); }
.ambiance-fade-enter-from, .ambiance-fade-leave-to { opacity: 0; }

/* ============================================================
   主舞台：flex 居中，三图不设容器框
   ============================================================ */
.carousel-stage {
  position: relative; z-index: 2;
  display: flex; align-items: center; justify-content: center; gap: 0;
  width: 100%; padding: 0 80px; box-sizing: border-box;
}

/* ============================================================
   左侧 / 右侧虚化图
   ============================================================ */
.side-slot {
  position: relative; width: 200px; height: 60vh; max-height: 500px;
  flex-shrink: 0; z-index: 5;
}
.left-slot  { margin-right: -20px; }
.right-slot { margin-left: -20px; }

.side-blur {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  border-radius: 12px; overflow: hidden; cursor: pointer;
  filter: blur(4px) brightness(0.6); opacity: 0.7;
  transition: filter 0.3s, opacity 0.3s;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.side-blur img { width: 100%; height: 100%; object-fit: cover; user-select: none; -webkit-user-drag: none; }
.side-blur:hover { filter: blur(2px) brightness(0.8); opacity: 0.9; }

/* --- 侧翼滑动过渡（方向感知，无 mode=out-in） --- */
.side-next-enter-active,
.side-next-leave-active,
.side-prev-enter-active,
.side-prev-leave-active {
  transition: transform 0.55s cubic-bezier(0.25, 0.46, 0.45, 0.94),
              opacity 0.55s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
/* next: 旧图左滑，新图从右进 */
.side-next-enter-from { opacity: 0; transform: translateX(40px); }
.side-next-leave-to   { opacity: 0; transform: translateX(-40px); }
/* prev: 旧图右滑，新图从左进 */
.side-prev-enter-from { opacity: 0; transform: translateX(-40px); }
.side-prev-leave-to   { opacity: 0; transform: translateX(40px); }

/* ============================================================
   中间主图
   ============================================================ */
.main-img-wrapper {
  width: 55vw; max-width: 750px; height: 68vh; max-height: 600px;
  position: relative; z-index: 10; flex-shrink: 0;
  overflow: hidden;
}
.main-img-inner {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 12px 48px rgba(0,0,0,0.4);
}
.main-img {
  width: 100%; height: 100%; object-fit: contain;
  user-select: none; -webkit-user-drag: none;
}

/* 文字叠加层 */
.main-text-overlay {
  position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
  max-width: 90%; padding: 14px 22px;
  background: rgba(0,0,0,0.55); border-radius: 10px;
  color: #fff; font-size: 14px; line-height: 1.7; backdrop-filter: blur(8px);
}
.main-text-overlay :deep(h1), .main-text-overlay :deep(h2), .main-text-overlay :deep(h3) { margin-bottom: 6px; color: #fff; }
.main-text-overlay :deep(p) { margin-bottom: 4px; }

/* 地图页 */
.main-map-wrapper { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
.main-placeholder { width: 100%; height: 100%; background: linear-gradient(135deg, #1a3a5c 0%, #2a5a8c 50%, #0d2137 100%); }

/* ============================================================
   主图滑动过渡（关键！无 mode=out-in，同时滑动无黑屏）
   ============================================================ */
.slide-next-enter-active,
.slide-next-leave-active,
.slide-prev-enter-active,
.slide-prev-leave-active {
  transition: transform 0.55s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
/* next 方向：当前页左滑消失，新页从右侧滑入 */
.slide-next-enter-from { transform: translateX(100%); opacity: 1; }
.slide-next-leave-to   { transform: translateX(-100%); opacity: 1; }
/* prev 方向：当前页右滑消失，新页从左侧滑入 */
.slide-prev-enter-from { transform: translateX(-100%); opacity: 1; }
.slide-prev-leave-to   { transform: translateX(100%); opacity: 1; }

/* ============================================================
   导航箭头
   ============================================================ */
.nav-arrow {
  position: absolute; top: 50%; transform: translateY(-50%); z-index: 30;
  width: 48px; height: 48px; border: none; border-radius: 50%;
  background: rgba(255,255,255,0.1); color: #fff; font-size: 26px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(8px); transition: all 0.3s; line-height: 1;
}
.nav-arrow:hover { background: rgba(255,255,255,0.28); transform: translateY(-50%) scale(1.1); }
.left-arrow  { left: 28px; }
.right-arrow { right: 28px; }

/* ============================================================
   胶卷式缩略图
   ============================================================ */
.filmstrip {
  position: absolute; bottom: 64px; left: 50%; transform: translateX(-50%);
  z-index: 30; max-width: 90vw; overflow: hidden;
}
.filmstrip-track {
  display: flex; gap: 8px; align-items: center;
}
.filmstrip-item {
  width: 72px; height: 54px; flex-shrink: 0;
  border-radius: 6px; overflow: hidden; cursor: pointer;
  border: 2px solid transparent;
  opacity: 0.35; transition: all 0.35s;
}
.filmstrip-item:hover { opacity: 0.7; border-color: rgba(255,255,255,0.4); }
.filmstrip-item.active { opacity: 1; border-color: #fff; }
.filmstrip-item img { width: 100%; height: 100%; object-fit: cover; }
.filmstrip-label {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.5);
  font-size: 10px; text-align: center; line-height: 1.3; padding: 2px;
}

/* ============================================================
   指示器 / 顶栏按钮 / Loading
   ============================================================ */
.carousel-indicators { position: absolute; bottom: 28px; z-index: 30; display: flex; gap: 10px; }
.carousel-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: rgba(255,255,255,0.35); border: none; cursor: pointer; transition: all 0.3s;
}
.carousel-dot.active { background: #fff; transform: scale(1.3); box-shadow: 0 0 8px rgba(255,255,255,0.5); }

.carousel-back-btn {
  position: absolute; top: 24px; left: 24px; z-index: 50;
  padding: 10px 20px; border: 1px solid rgba(255,255,255,0.25); border-radius: 8px;
  background: rgba(0,0,0,0.35); color: #fff; font-size: 14px; cursor: pointer;
  backdrop-filter: blur(6px); transition: all 0.3s;
}
.carousel-back-btn:hover { background: rgba(0,0,0,0.55); }

.present-btn {
  position: absolute; top: 24px; right: 80px; z-index: 50;
  padding: 8px 18px; border: 1px solid rgba(255,255,255,0.25); border-radius: 8px;
  background: rgba(0,0,0,0.35); color: #fff; font-size: 14px; cursor: pointer;
  backdrop-filter: blur(6px); transition: all 0.3s;
}
.present-btn:hover { background: rgba(0,0,0,0.55); }

.loading-state {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  color: rgba(255,255,255,0.7); z-index: 10;
}
.empty-state {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
  text-align: center; color: #fff; z-index: 10;
}
.empty-state p { font-size: 18px; margin-bottom: 20px; opacity: 0.7; }

/* ============================================================
   演示模式
   ============================================================ */
.presentation-overlay {
  position: fixed; inset: 0; width: 100vw; height: 100vh;
  background: #000000; z-index: 9999; outline: none;
  overflow: hidden;
}

/* 演示模式虚化氛围层 */
.present-ambiance {
  position: absolute; inset: 0; z-index: 1; overflow: hidden;
}
.present-ambiance-img {
  width: 100%; height: 100%; object-fit: cover;
  filter: blur(30px); transform: scale(1.1); opacity: 0.55;
}

/* 演示模式图片舞台 */
.present-img-stage {
  position: relative; z-index: 2;
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
}
.present-main-img {
  max-width: 92%; max-height: 92%;
  object-fit: contain;
  user-select: none; -webkit-user-drag: none;
}
.present-main-map { width: 95%; height: 90%; }

/* 退出按钮 */
.present-exit-btn {
  position: absolute; top: 24px; right: 24px; z-index: 10001;
  padding: 10px 22px; border: 1px solid rgba(255,255,255,0.4); border-radius: 8px;
  background: rgba(0,0,0,0.5); color: #fff; font-size: 15px; cursor: pointer;
  backdrop-filter: blur(8px); opacity: 0; transition: opacity 0.4s;
}
.present-exit-btn.visible { opacity: 1; }
.present-exit-btn:hover { background: rgba(220,38,38,0.7); border-color: #fff; }

/* 演示模式左右切换按钮 */
.present-nav {
  position: absolute; top: 50%; transform: translateY(-50%); z-index: 10001;
  width: 56px; height: 56px; border: none; border-radius: 50%;
  background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.7);
  font-size: 32px; cursor: pointer; line-height: 1;
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(8px); opacity: 0; transition: opacity 0.4s;
}
.present-nav.visible { opacity: 1; }
.present-nav:hover { background: rgba(255,255,255,0.2); color: #fff; }
.present-prev { left: 24px; }
.present-next { right: 24px; }

/* 演示模式主图点击提示 */
.present-main-img { cursor: pointer; }

.present-page-num {
  position: absolute; bottom: 32px; left: 50%; transform: translateX(-50%);
  color: rgba(255,255,255,0.5); font-size: 16px; letter-spacing: 2px;
  opacity: 0; transition: opacity 0.4s; z-index: 10001;
}
.present-page-num.visible { opacity: 1; }
</style>
