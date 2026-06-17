<template>
  <div
    class="image-text-slide"
    :style="{ backgroundImage: page.background_image ? `url(${page.background_image})` : 'linear-gradient(135deg, #1a3a5c, #2a5a8c)' }"
  >
    <div
      v-if="page.rich_text_content"
      class="image-text-overlay"
      :style="overlayStyle"
      v-html="page.rich_text_content"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Object, required: true }
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
  background-size: cover;
  background-position: center;
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

.image-text-overlay :deep(p) {
  margin-bottom: 12px;
}

.image-text-overlay :deep(img) {
  max-width: 100%;
  border-radius: 8px;
}
</style>
