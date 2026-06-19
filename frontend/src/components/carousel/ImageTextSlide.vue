<template>
  <div
    class="image-text-slide"
    :style="bgStyle"
  >
    <div
      v-if="hasContent && !dimmed"
      class="image-text-overlay"
      :style="overlayStyle"
      v-html="page.rich_text_content"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Object, required: true },
  dimmed: { type: Boolean, default: false }   // 非激活卡片时隐藏文字叠加层
})

// 只在有实际文字内容时才显示叠加层
const hasContent = computed(() => {
  const html = (props.page.rich_text_content || '').trim()
  if (!html) return false
  // 过滤掉空标签（如 <p><br></p>）
  const stripped = html.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, '').trim()
  return stripped.length > 0
})

// 背景图自适应：无图用渐变占位
const bgStyle = computed(() => {
  if (props.page.background_image) {
    return {
      backgroundImage: `url(${props.page.background_image})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat'
    }
  }
  return {
    background: 'linear-gradient(135deg, #1a3a5c 0%, #2a5a8c 50%, #0d2137 100%)'
  }
})

const overlayStyle = computed(() => ({
  left: `${props.page.text_position_x || 10}%`,
  top: `${props.page.text_position_y || 10}%`,
  width: `${props.page.text_width || 40}%`,
  height: `${props.page.text_height || 80}%`
}))
</script>

<style scoped>
.image-text-slide {
  width: 100%;
  height: 100%;
  position: relative;
}

.image-text-overlay {
  position: absolute;
  overflow: auto;
  background: rgba(0, 0, 0, 0.45);
  border-radius: 12px;
  padding: 32px;
  color: #fff;
  backdrop-filter: blur(10px);
  line-height: 1.8;
}

.image-text-overlay :deep(h1),
.image-text-overlay :deep(h2),
.image-text-overlay :deep(h3) {
  margin-bottom: 16px;
  color: #fff;
}
.image-text-overlay :deep(p) { margin-bottom: 12px; }
.image-text-overlay :deep(img) { max-width: 100%; border-radius: 8px; }
</style>
