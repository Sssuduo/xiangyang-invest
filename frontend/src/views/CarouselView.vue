<template>
  <div class="carousel-container" @keydown="handleKeydown" tabindex="0" ref="containerRef">
    <!-- 返回按钮 -->
    <button class="carousel-back-btn" @click="$router.push('/')">
      ← 返回首页
    </button>

    <!-- 幻灯片 -->
    <transition-group name="slide-fade">
      <div
        v-for="(page, index) in pages"
        :key="page.id"
        v-show="index === currentIndex"
        class="carousel-slide"
      >
        <!-- 图文页 -->
        <ImageTextSlide v-if="page.page_type === 'image_text'" :page="page" />
        <!-- 地图页 -->
        <MapSlide v-else-if="page.page_type === 'map'" :page="page" />
      </div>
    </transition-group>

    <!-- 左右翻页按钮 -->
    <button v-if="pages.length > 1" class="carousel-nav-btn prev" @click="prevSlide">
      ‹
    </button>
    <button v-if="pages.length > 1" class="carousel-nav-btn next" @click="nextSlide">
      ›
    </button>

    <!-- 指示器 -->
    <div v-if="pages.length > 1" class="carousel-indicators">
      <button
        v-for="(page, index) in pages"
        :key="'dot-' + page.id"
        class="carousel-dot"
        :class="{ active: index === currentIndex }"
        @click="goToSlide(index)"
      />
    </div>

    <!-- 空状态 -->
    <div v-if="pages.length === 0" class="empty-state">
      <p>暂无内容，请先在管理后台添加轮播页</p>
      <el-button @click="$router.push('/')">返回首页</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { getCarouselPages } from '@/api/carousel'
import ImageTextSlide from '@/components/carousel/ImageTextSlide.vue'
import MapSlide from '@/components/carousel/MapSlide.vue'

const pages = ref([])
const currentIndex = ref(0)
const containerRef = ref(null)
let autoPlayTimer = null

onMounted(async () => {
  try {
    const res = await getCarouselPages()
    if (res.code === 0) {
      pages.value = res.data || []
    }
  } catch {
    // 加载失败
  }

  startAutoPlay()
  nextTick(() => containerRef.value?.focus())
})

onUnmounted(() => {
  stopAutoPlay()
})

function startAutoPlay() {
  stopAutoPlay()
  if (pages.value.length > 1) {
    autoPlayTimer = setInterval(() => {
      currentIndex.value = (currentIndex.value + 1) % pages.value.length
    }, 8000)
  }
}

function stopAutoPlay() {
  if (autoPlayTimer) {
    clearInterval(autoPlayTimer)
    autoPlayTimer = null
  }
}

function prevSlide() {
  stopAutoPlay()
  currentIndex.value = (currentIndex.value - 1 + pages.value.length) % pages.value.length
  startAutoPlay()
}

function nextSlide() {
  stopAutoPlay()
  currentIndex.value = (currentIndex.value + 1) % pages.value.length
  startAutoPlay()
}

function goToSlide(index) {
  stopAutoPlay()
  currentIndex.value = index
  startAutoPlay()
}

function handleKeydown(e) {
  if (e.key === 'ArrowLeft') prevSlide()
  if (e.key === 'ArrowRight') nextSlide()
  if (e.key === 'Escape') window.history.back()
}
</script>

<style scoped>
@import '@/assets/styles/carousel.css';

.carousel-container {
  outline: none;
}

.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #fff;
}
.empty-state p {
  font-size: 18px;
  margin-bottom: 20px;
  opacity: 0.7;
}

.slide-fade-enter-active {
  transition: opacity 0.6s ease;
}
.slide-fade-leave-active {
  transition: opacity 0.3s ease;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
}
</style>
