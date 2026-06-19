<template>
  <div class="map-slide" :class="{ dimmed: !interactive }">
    <ChinaMap :map-scope="page.map_scope || 'china'" :interactive="interactive" />
  </div>
</template>

<script setup>
import ChinaMap from '@/components/map/ChinaMap.vue'

defineProps({
  page: { type: Object, required: true },
  interactive: { type: Boolean, default: true }
})
</script>

<style scoped>
.map-slide.dimmed {
  pointer-events: none;
}
</style>

<style scoped>
.map-slide {
  width: 100%;
  height: 100%;
  position: relative;
}
</style>
