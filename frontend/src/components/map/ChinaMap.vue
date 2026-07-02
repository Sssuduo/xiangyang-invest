<template>
  <div class="map-wrapper">
    <div ref="chartRef" class="map-chart" />

    <!-- 级别切换 -->
    <div v-if="showScopeToggle" class="map-scope-toggle">
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
        :is-focused="!!focusedProvince"
      />
    </teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import echarts from '@/utils/echarts'
import { getProvinces, getProvinceCities } from '@/api/province'
import ProvinceCard from './ProvinceCard.vue'

const props = defineProps({
  mapScope: { type: String, default: 'china' },
  interactive: { type: Boolean, default: true },
  showScopeToggle: { type: Boolean, default: true },
  mapCenter: { type: Array, default: null },  // [lng, lat] 覆盖默认中心
  mapZoom: { type: Number, default: null },   // 覆盖默认缩放
  highlightColor: { type: String, default: '#c9a84c' },  // 省份高亮颜色
  cityHighlightColor: { type: String, default: '#d4a94e' }  // 城市高亮颜色（淡金色）
})

const emit = defineEmits(['focus-change'])
const chartRef = ref(null)
const currentScope = ref(props.mapScope || 'china')
const hoveredProvince = ref(null)
const cardPosition = ref({ x: 0, y: 0 })
const isMounted = ref(true)
const focusedProvince = ref(null)   // 当前聚焦的省份（null = 全国视图）
const isTransitioning = ref(false)
const cityHighlightData = ref([])    // 聚焦省份的高亮城市数据
let chart = null
let geoJsonData = null
let provinceData = []
let nationalOption = null            // 缓存全国视图配置，用于恢复
let focusTimer = null                // 防抖定时器
const inProvinceCityNames = ref(new Set())  // 当前聚焦省份内的城市名集合

function handleEscKey(e) {
  if (e.key === 'Escape' && focusedProvince.value) {
    unfocusProvince()
  }
}

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
    const [chinaGeo, hubeiGeo, citiesGeo, provinces] = await Promise.all([
      fetch('/static/data/china_provinces.json').then(r => r.json()),
      fetch('/static/data/hubei_cities.json').then(r => r.json()).catch(() => null),
      fetch('/static/data/china_cities.json').then(r => r.json()).catch(() => null),
      getProvinces(currentScope.value)
    ])

    // 缓存 GeoJSON
    geoJsonData = { china: chinaGeo, hubei: hubeiGeo, cities: citiesGeo }

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

  // 注册城市级地图（用于省份聚焦）
  if (geoJsonData?.cities) {
    echarts.registerMap('china_cities', geoJsonData.cities)
  }

  const highlighted = provinceData.filter(p => p.is_highlighted)
  const mapData = highlighted.map(p => ({
    name: p.region_name,
    itemStyle: {
      areaColor: props.highlightColor || '#7ac8a0',
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
    backgroundColor: '#c2d8f0',
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
      roam: props.interactive,
      silent: !props.interactive,
      zoom: props.mapZoom ?? (currentScope.value === 'hubei' ? 1.2 : 1),
      center: props.mapCenter ?? (currentScope.value === 'hubei' ? [112.9, 30.5] : [104, 36]),
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
  nationalOption = option

  // 事件：悬浮显示卡片，点击触发聚焦
  chart.off('click')
  chart.off('mouseover')
  chart.off('mouseout')
  chart.off('mousemove')

  // 点击高亮省份 → 聚焦放大
  chart.on('click', (params) => {
    if (isTransitioning.value) return
    if (params.componentType === 'series') {
      const found = provinceData.find(p => p.region_name === params.name)
      if (found && found.is_highlighted && found.has_city_highlights && !focusedProvince.value) {
        focusProvince(found)
      }
    }
  })

  // 悬浮 → 显示卡片（不聚焦）
  chart.on('mouseover', (params) => {
    if (params.componentType === 'series') {
      const found = provinceData.find(p => p.region_name === params.name)
      if (found && found.is_highlighted) {
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

async function focusProvince(province) {
  if (!chart || !geoJsonData?.cities || isTransitioning.value) return

  isTransitioning.value = true

  // 加载该省份的高亮城市数据
  try {
    const res = await getProvinceCities(province.id)
    cityHighlightData.value = (res.code === 0 && res.data) ? res.data : []
  } catch {
    cityHighlightData.value = []
  }

  focusedProvince.value = province
  hoveredProvince.value = province  // 聚焦时保持省份卡片显示

  const provinceId = province.id
  const highlightCityCodes = new Set(cityHighlightData.value.map(c => String(c.city_code)))

  // 构建 adcode → province.id 映射，按数据库主键判定城市归属
  const adcodeToProvinceId = {}
  for (const p of provinceData) {
    adcodeToProvinceId[String(p.region_code)] = p.id
  }

  // 构建城市级地图数据（单系列：province.id 判定省内/省外）
  const cityFeatures = geoJsonData.cities.features || []
  const seriesData = []
  const inNames = new Set()
  const highlightCoords = []  // 收集高亮城市坐标用于居中

  for (const feature of cityFeatures) {
    const props = feature.properties || {}
    const cityName = props.name || ''
    const cityCode = String(props.adcode || '')
    const parentCode = String((props.parent || {}).adcode || '')
    const cityProvinceId = adcodeToProvinceId[parentCode]
    const isInFocusedProvince = cityProvinceId === provinceId
    const isHighlightedCity = highlightCityCodes.has(cityCode)

    if (isHighlightedCity) {
      inNames.add(cityName)
      // 收集高亮城市坐标
      const cityCenter = props.centroid || props.center
      if (cityCenter && cityCenter.length === 2) {
        highlightCoords.push(cityCenter)
      }
      seriesData.push({
        name: cityName,
        itemStyle: { areaColor: props.cityHighlightColor || '#d4a94e', borderColor: '#fff', borderWidth: 2, opacity: 1 },
        label: { show: true, color: '#5a4030', fontWeight: 'bold' }
      })
    } else if (isInFocusedProvince) {
      inNames.add(cityName)
      seriesData.push({
        name: cityName,
        itemStyle: { areaColor: '#5a9e6f', borderColor: '#fff', borderWidth: 1, opacity: 0.85 },
        label: { show: true, fontSize: 9, color: '#fff' }
      })
    } else {
      // 省外城市：暗灰色，标签默认展示（无需悬停）
      seriesData.push({
        name: cityName,
        itemStyle: { areaColor: '#5a5a5a', borderColor: '#444', borderWidth: 0.5, opacity: 0.35 },
        label: { show: true, fontSize: 8, color: '#888' }
      })
    }
  }

  inProvinceCityNames.value = inNames

  // 预先查找省份 GeoJSON feature（居中 + 缩放共用）
  const chinaFeatures = (geoJsonData.china?.features || [])
  const provinceFeature = chinaFeatures.find(f => {
    const p = f.properties || {}
    return String(p.adcode) === province.region_code || p.name === province.region_name
  })

  // 计算地图中心点：优先以高亮城市坐标均值居中，否则回退到省份 centroid
  let provinceCenter = [104, 36]
  if (highlightCoords.length > 0) {
    const sumLng = highlightCoords.reduce((s, c) => s + c[0], 0)
    const sumLat = highlightCoords.reduce((s, c) => s + c[1], 0)
    provinceCenter = [sumLng / highlightCoords.length, sumLat / highlightCoords.length]
  } else if (provinceFeature) {
    const props = provinceFeature.properties || {}
    const centroid = props.centroid || props.center
    if (centroid && centroid.length === 2) {
      provinceCenter = centroid
    }
  }

  // 计算缩放
  let provinceZoom = 3.5
  if (provinceFeature) {
    const childCount = provinceFeature.properties?.childrenNum || 10
    provinceZoom = Math.max(3.5, Math.min(8.5, 30 / Math.sqrt(childCount)))
  }

  chart.setOption({
    backgroundColor: '#c2d8f0',
    tooltip: { trigger: 'item', backgroundColor: 'transparent', borderColor: 'transparent', padding: 0, formatter: () => '' },
    series: [{
      type: 'map',
      map: 'china_cities',
      roam: false,
      silent: false,
      zoom: provinceZoom,
      center: provinceCenter,
      aspectScale: 0.85,
      label: { show: true, fontSize: 9, color: '#555' },
      itemStyle: { areaColor: '#e8edf2', borderColor: '#c0c8d0', borderWidth: 1 },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#1a3a5c' },
        itemStyle: { areaColor: '#d4e4f7', borderColor: '#1a3a5c', borderWidth: 2 }
      },
      data: seriesData
    }]
  })

  // 聚焦模式下的鼠标事件
  chart.off('click')
  chart.off('mouseover')
  chart.off('mouseout')
  chart.off('mousemove')

  // 点击：空白 或 城市父级 province_id ≠ 当前聚焦 province.id → 返回全国
  chart.on('click', (params) => {
    if (isTransitioning.value) return
    if (!params.componentType || params.componentType !== 'series' || !params.name) {
      unfocusProvince()
      return
    }
    if (!inProvinceCityNames.value.has(params.name)) {
      unfocusProvince()
    }
  })

  chart.on('mouseover', (params) => {
    if (params.componentType === 'series' && params.name && inProvinceCityNames.value.has(params.name)) {
      hoveredProvince.value = province
    }
  })

  chart.on('mousemove', (params) => {
    if (params.event?.event) {
      cardPosition.value = {
        x: params.event.event.clientX + 15,
        y: params.event.event.clientY - 10
      }
    }
  })

  // 聚焦模式下不清除悬停卡片
  chart.on('mouseout', () => {})

  // 绑定 ESC 键返回全国
  document.addEventListener('keydown', handleEscKey)

  emit('focus-change', province)
  setTimeout(() => { isTransitioning.value = false }, 900)
}

function unfocusProvince() {
  if (!chart || !nationalOption || isTransitioning.value) return

  document.removeEventListener('keydown', handleEscKey)
  clearTimeout(focusTimer)
  isTransitioning.value = true
  focusedProvince.value = null
  cityHighlightData.value = []

  // 清空聚焦状态
  inProvinceCityNames.value = new Set()

  chart.setOption(nationalOption)

  // 恢复全国视图的事件
  chart.off('click')
  chart.off('mouseover')
  chart.off('mouseout')
  chart.off('mousemove')

  // 点击高亮省份 → 聚焦放大
  chart.on('click', (params) => {
    if (isTransitioning.value) return
    if (params.componentType === 'series') {
      const found = provinceData.find(p => p.region_name === params.name)
      if (found && found.is_highlighted && found.has_city_highlights && !focusedProvince.value) {
        focusProvince(found)
      }
    }
  })

  // 悬浮 → 显示卡片（不聚焦）
  chart.on('mouseover', (params) => {
    if (params.componentType === 'series') {
      const found = provinceData.find(p => p.region_name === params.name)
      if (found && found.is_highlighted) {
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

  emit('focus-change', null)
  setTimeout(() => { isTransitioning.value = false }, 700)
}

async function handleScopeChange(scope) {
  currentScope.value = scope
  // 重置聚焦状态
  focusedProvince.value = null
  cityHighlightData.value = []
  clearTimeout(focusTimer)
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
