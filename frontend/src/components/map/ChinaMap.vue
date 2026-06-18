<template>
  <div class="map-wrapper">
    <div ref="chartRef" class="map-chart" />

    <!-- 级别切换 -->
    <div class="map-scope-toggle">
      <el-radio-group v-model="currentScope" size="small" @change="handleScopeChange">
        <el-radio-button value="china">全国</el-radio-button>
        <el-radio-button value="hubei">湖北省</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 悬浮信息卡片 — 仅在组件挂载且有悬停数据时显示 -->
    <teleport to="body" v-if="isMounted">
      <ProvinceCard
        v-if="hoveredProvince"
        :province="hoveredProvince"
        :position="cardPosition"
      />
    </teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getProvinces } from '@/api/province'
import ProvinceCard from './ProvinceCard.vue'

const props = defineProps({
  mapScope: { type: String, default: 'china' }
})

const chartRef = ref(null)
const currentScope = ref(props.mapScope || 'china')
const hoveredProvince = ref(null)
const cardPosition = ref({ x: 0, y: 0 })
const isMounted = ref(true)
let chart = null
let geoJsonData = null
let provinceData = []

watch(() => props.mapScope, (val) => {
  if (val) currentScope.value = val
})

onMounted(async () => {
  await loadData()
  nextTick(() => initChart())
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  isMounted.value = false
  hoveredProvince.value = null
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})

async function loadData() {
  try {
    const [chinaGeo, hubeiGeo, provinces] = await Promise.all([
      fetch('/static/data/china_provinces.json').then(r => r.json()),
      fetch('/static/data/hubei_cities.json').then(r => r.json()).catch(() => null),
      getProvinces(currentScope.value)
    ])

    // 缓存两种 GeoJSON
    geoJsonData = { china: chinaGeo, hubei: hubeiGeo }

    if (provinces.code === 0) {
      provinceData = provinces.data || []
    }
  } catch (err) {
    console.error('地图数据加载失败:', err)
  }
}

function initChart() {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)

  const geoJson = currentScope.value === 'hubei' && geoJsonData?.hubei
    ? geoJsonData.hubei
    : geoJsonData?.china

  if (!geoJson) return

  const mapName = currentScope.value === 'hubei' ? 'hubei' : 'china'
  echarts.registerMap(mapName, geoJson)

  const highlighted = provinceData.filter(p => p.is_highlighted)
  const mapData = highlighted.map(p => ({
    name: p.region_name,
    itemStyle: {
      areaColor: '#c9a84c',
      borderColor: '#fff',
      borderWidth: 2
    },
    label: {
      show: true,
      color: '#1a3a5c',
      fontWeight: 'bold'
    }
  }))

  const option = {
    backgroundColor: '#f0f4f8',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'transparent',
      borderColor: 'transparent',
      padding: 0,
      formatter: () => '' // 使用自定义悬浮卡片
    },
    series: [{
      type: 'map',
      map: mapName,
      roam: true,
      zoom: currentScope.value === 'hubei' ? 1.2 : 1,
      center: currentScope.value === 'hubei' ? [112.9, 30.5] : [104, 36],
      label: {
        show: true,
        fontSize: currentScope.value === 'hubei' ? 11 : 10,
        color: '#555'
      },
      itemStyle: {
        areaColor: '#e8edf2',
        borderColor: '#c0c8d0',
        borderWidth: 1
      },
      emphasis: {
        label: {
          show: true,
          fontSize: currentScope.value === 'hubei' ? 16 : 14,
          fontWeight: 'bold',
          color: '#1a3a5c'
        },
        itemStyle: {
          areaColor: '#d4e4f7',
          borderColor: '#1a3a5c',
          borderWidth: 2,
          shadowBlur: 10,
          shadowColor: 'rgba(0,0,0,0.2)'
        }
      },
      data: mapData
    }]
  }

  chart.setOption(option)

  // 鼠标移动事件
  chart.off('mouseover')
  chart.off('mouseout')
  chart.off('mousemove')

  chart.on('mouseover', (params) => {
    if (params.componentType === 'series') {
      const found = provinceData.find(p => p.region_name === params.name)
      if (found) {
        hoveredProvince.value = found
      }
    }
  })

  chart.on('mousemove', (params) => {
    cardPosition.value = {
      x: params.event.event.clientX + 15,
      y: params.event.event.clientY - 10
    }
  })

  chart.on('mouseout', () => {
    hoveredProvince.value = null
  })
}

async function handleScopeChange(scope) {
  currentScope.value = scope
  // 重新加载该 scope 的省份数据
  try {
    const res = await getProvinces(scope)
    if (res.code === 0) {
      provinceData = res.data || []
    }
  } catch { /* ignore */ }

  chart?.dispose()
  await nextTick()
  initChart()
}

function handleResize() {
  chart?.resize()
}
</script>

<style scoped>
.map-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.map-chart {
  width: 100%;
  height: 100%;
}

.map-scope-toggle {
  position: absolute;
  top: 24px;
  right: 80px;
  z-index: 20;
}
</style>
