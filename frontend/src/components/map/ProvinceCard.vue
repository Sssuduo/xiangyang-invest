<template>
  <div
    class="province-card"
    :class="{ 'card-focused': isFocused }"
    :style="isFocused ? {} : { left: position.x + 'px', top: position.y + 'px' }"
  >
    <h4>{{ province.card_title || province.region_name }}</h4>
    <div v-if="province.card_content" class="card-body" v-html="province.card_content" />
    <p v-else class="no-content">暂无详细信息</p>
  </div>
</template>

<script setup>
defineProps({
  province: { type: Object, required: true },
  position: { type: Object, required: true },
  isFocused: { type: Boolean, default: false }
})
</script>

<style scoped>
.province-card {
  position: fixed;
  z-index: 9999;
  background: #fff;
  border-radius: 10px;
  padding: 16px 20px;
  min-width: 220px;
  max-width: 320px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.18);
  pointer-events: none;
  animation: cardFadeIn 0.2s ease;
}

.province-card h4 {
  font-size: 16px;
  color: var(--primary-color);
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--accent-color);
}

.card-body {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
}
.card-body :deep(b),
.card-body :deep(strong) { color: var(--text-primary, #303133); font-weight: 600; }
.card-body :deep(ol),
.card-body :deep(ul) { padding-left: 18px; margin: 4px 0; }
.card-body :deep(li) { margin-bottom: 2px; }
.card-body :deep(br) { display: block; content: ''; margin-bottom: 2px; }

.no-content {
  font-style: italic;
  opacity: 0.5;
}

/* ---- 聚焦模式：右侧固定定位 ---- */
.province-card.card-focused {
  position: fixed;
  right: 40px;
  top: 50%;
  transform: translateY(-50%);
  left: auto;
  min-width: 280px;
  max-width: 380px;
  pointer-events: auto;
  animation: cardSlideIn 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.22);
  z-index: 9999;
}

@keyframes cardSlideIn {
  from {
    opacity: 0;
    transform: translateY(-50%) translateX(40px);
  }
  to {
    opacity: 1;
    transform: translateY(-50%) translateX(0);
  }
}

@keyframes cardFadeIn {
  from {
    opacity: 0;
    transform: translateY(5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
