<template>
  <div class="map-slide">
    <ChinaMap :map-scope="page.map_scope || 'china'" />
  </div>
</template>

<script setup>
import ChinaMap from '@/components/map/ChinaMap.vue'

defineProps({
  page: { type: Object, required: true }
})
</script>

<style scoped>
.map-slide {
  width: 100%;
  height: 100%;
  position: relative;
}
</style>
