<template>
  <div class="promo-video-page">
    <BusinessNavbar variant="light" />

    <div class="video-page-body">
      <!-- 播放器 -->
      <div class="player-section">
        <div class="player-wrapper" v-if="currentVideo">
          <video
            ref="playerRef"
            :src="currentVideo.file_path"
            :key="currentVideo.id"
            class="main-player"
            controls
            controlsList="nodownload"
            preload="metadata"
            autoplay
            @ended="onVideoEnded"
            @loadeddata="onPlayerReady"
            @waiting="onPlayerWaiting"
            @canplay="onPlayerCanPlay"
          >
            您的浏览器不支持视频播放
          </video>
          <div class="player-title-bar">
            <h2 class="current-title">{{ currentVideo.title }}</h2>
          </div>
        </div>
        <div class="player-wrapper empty-player" v-else>
          <div class="empty-hint">
            <el-icon><VideoCameraFilled /></el-icon>
            <span>暂无宣传视频</span>
          </div>
        </div>
      </div>

      <!-- 右侧：竖排胶卷 -->
      <div class="filmstrip-section" v-if="videos.length > 0">
        <div class="filmstrip-label">视频列表</div>
        <div class="filmstrip-scroll">
          <div
            v-for="(v, idx) in videos"
            :key="v.id"
            class="film-item"
            :class="{ active: currentVideo && v.id === currentVideo.id }"
            @click="switchVideo(v, idx)"
          >
            <div class="film-thumb">
              <img v-if="v.thumbnail_url" :src="v.thumbnail_url" alt="" loading="lazy" />
              <div v-else class="thumb-placeholder">
                <el-icon><VideoCameraFilled /></el-icon>
              </div>
              <div class="film-overlay">
                <el-icon><VideoPlay /></el-icon>
              </div>
            </div>
            <div class="film-info">
              <span class="film-index">{{ idx + 1 }}</span>
              <span class="film-title">{{ v.title }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { VideoPlay, VideoCameraFilled } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import { getPublicVideos } from '@/api/promo_video'

const playerRef = ref(null)
const videos = ref([])
const currentVideo = ref(null)
const currentIndex = ref(0)

// 预缓冲：隐藏的 video 元素，提前加载下一个视频
const prebufferRef = ref(null)
const playerBuffering = ref(false)

onMounted(async () => {
  try {
    const res = await getPublicVideos()
    if (res.data.code === 0 && res.data.data.length > 0) {
      videos.value = res.data.data
      currentVideo.value = videos.value[0]
      currentIndex.value = 0
      await nextTick()
      // 第一个视频开始播放后，预缓冲下一个
      prebufferNext(0)
    }
  } catch (e) {
    console.error('加载视频列表失败', e)
  }
})

onUnmounted(() => {
  // 清理预缓冲元素
  if (prebufferRef.value) {
    prebufferRef.value.removeAttribute('src')
    prebufferRef.value.load()
  }
})

function switchVideo(v, idx) {
  currentVideo.value = v
  currentIndex.value = idx
  prebufferNext(idx)
}

function onVideoEnded() {
  if (currentIndex.value < videos.value.length - 1) {
    const next = videos.value[currentIndex.value + 1]
    switchVideo(next, currentIndex.value + 1)
  }
}

function onPlayerReady() {
  if (playerRef.value) {
    playerRef.value.play().catch(() => {})
  }
}

function onPlayerWaiting() {
  playerBuffering.value = true
}

function onPlayerCanPlay() {
  playerBuffering.value = false
}

// 预缓冲下一个视频
function prebufferNext(currentIdx) {
  const nextIdx = currentIdx + 1
  if (nextIdx >= videos.value.length) {
    // 最后一个视频，预缓冲第一个（循环）
    if (videos.value.length > 1 && currentIdx === videos.value.length - 1) {
      preloadVideo(videos.value[0].file_path)
    }
    return
  }
  preloadVideo(videos.value[nextIdx].file_path)
}

function preloadVideo(url) {
  if (!prebufferRef.value) {
    prebufferRef.value = document.createElement('video')
    prebufferRef.value.muted = true
    prebufferRef.value.preload = 'auto'
    prebufferRef.value.style.display = 'none'
    document.body.appendChild(prebufferRef.value)
  }
  // 避免重复加载同一个 URL
  if (prebufferRef.value.getAttribute('data-url') !== url) {
    prebufferRef.value.setAttribute('data-url', url)
    prebufferRef.value.src = url
  }
}
</script>

<style scoped>
.promo-video-page {
  min-height: 100vh;
  background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%);
  display: flex;
  flex-direction: column;
}

.video-page-body {
  flex: 1;
  display: flex;
  gap: 28px;
  padding: 32px 40px 40px;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  align-items: flex-start;
}

/* ---- 播放器 ---- */
.player-section {
  flex: 1;
  min-width: 0;
}

.player-wrapper {
  position: relative;
  background: #000;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
  aspect-ratio: 16 / 9;
}

.main-player {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
}

.player-title-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20px 24px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
  pointer-events: none;
}

.current-title {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
  letter-spacing: 1px;
}

.empty-player {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px dashed #c8d6e5;
}

.empty-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 16px;
  letter-spacing: 2px;
}

.empty-hint .el-icon {
  font-size: 48px;
  color: #c0c4cc;
}

/* ---- 右侧竖排胶卷 ---- */
.filmstrip-section {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 120px);
}

.filmstrip-label {
  font-size: 14px;
  font-weight: 600;
  color: #1a3a5c;
  letter-spacing: 1px;
  margin-bottom: 12px;
  padding-left: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.filmstrip-label::before {
  content: '';
  display: inline-block;
  width: 3px;
  height: 14px;
  background: #1a3a5c;
  border-radius: 2px;
}

.filmstrip-scroll {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  padding-right: 4px;
  scroll-behavior: smooth;
}

.filmstrip-scroll::-webkit-scrollbar {
  width: 4px;
}
.filmstrip-scroll::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.04);
  border-radius: 2px;
}
.filmstrip-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 2px;
}

.film-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, box-shadow 0.2s;
}

.film-item:hover {
  background: rgba(255, 255, 255, 0.6);
}

.film-item.active {
  background: #fff;
  box-shadow: 0 2px 12px rgba(26, 58, 92, 0.12);
}

.film-thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
  background: #e8edf2;
  border: 2px solid transparent;
  transition: border-color 0.2s;
}

.film-item.active .film-thumb {
  border-color: #409eff;
}

.film-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  font-size: 32px;
}

.film-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.2);
  opacity: 0;
  transition: opacity 0.2s;
  font-size: 36px;
  color: #fff;
}

.film-item:hover .film-overlay {
  opacity: 1;
}

.film-item.active .film-overlay {
  opacity: 0;
}

.film-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.film-index {
  font-size: 11px;
  color: #909399;
  font-weight: 500;
  flex-shrink: 0;
}

.film-title {
  font-size: 13px;
  color: #4a5568;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.film-item.active .film-title {
  color: #1a3a5c;
  font-weight: 600;
}
</style>
