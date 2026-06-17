<template>
  <div
    class="province-card"
    :style="{ left: position.x + 'px', top: position.y + 'px' }"
  >
    <h4>{{ province.card_title || province.region_name }}</h4>
    <p v-if="province.card_content">{{ province.card_content }}</p>
    <p v-else class="no-content">暂无详细信息</p>
  </div>
</template>

<script setup>
defineProps({
  province: { type: Object, required: true },
  position: { type: Object, required: true }
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

.province-card p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.no-content {
  font-style: italic;
  opacity: 0.5;
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
