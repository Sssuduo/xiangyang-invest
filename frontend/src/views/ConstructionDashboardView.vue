<template>
  <div class="dashboard-page" v-loading="loading">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1>数据看板</h1>
        <span class="page-subtitle">在建项目统计分析</span>
      </div>

      <!-- 统计卡片 -->
      <div class="stat-cards">
        <div class="stat-card stat-total">
          <div class="stat-card-icon">
            <el-icon><Folder /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.total_projects ?? 0 }}</span>
            <span class="stat-card-label">在建项目总数</span>
          </div>
        </div>
        <div class="stat-card stat-dispatching">
          <div class="stat-card-icon">
            <el-icon><Loading /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.dispatching_count ?? 0 }}</span>
            <span class="stat-card-label">调度中</span>
          </div>
        </div>
        <div class="stat-card stat-completed">
          <div class="stat-card-icon">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.completed_count ?? 0 }}</span>
            <span class="stat-card-label">已完成</span>
          </div>
        </div>
        <div class="stat-card stat-units">
          <div class="stat-card-icon">
            <el-icon><OfficeBuilding /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.responsible_units ?? 0 }}</span>
            <span class="stat-card-label">涉及责任单位</span>
          </div>
        </div>
        <div class="stat-card stat-progress">
          <div class="stat-card-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.total_progress ?? 0 }}</span>
            <span class="stat-card-label">工作进展总数</span>
          </div>
        </div>
        <div class="stat-card stat-issues">
          <div class="stat-card-icon">
            <el-icon><WarningFilled /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.pending_issues ?? 0 }}</span>
            <span class="stat-card-label">待解决问题</span>
          </div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="charts-grid">
        <!-- 图表1 & 图表3：左右并排 -->
        <div class="charts-row-two">
          <!-- 项目类型分布（柱状图，支持下钻） -->
          <div class="chart-panel">
            <div class="chart-panel-header">
              <h3>项目类型分布</h3>
              <div class="chart-panel-actions">
                <el-button
                  v-if="drilldownType"
                  size="small"
                  @click="drillupTypeChart"
                >
                  <el-icon><Back /></el-icon> 返回项目类型
                </el-button>
                <el-select
                  v-model="filterDispatchStatus"
                  placeholder="调度状态"
                  clearable
                  multiple
                  collapse-tags
                  size="small"
                  style="width: 160px;"
                  @change="onFilterChange"
                >
                  <el-option label="调度中" value="dispatching" />
                  <el-option label="不予调度" value="no_dispatch" />
                </el-select>
                <el-select
                  v-model="filterProjectType"
                  placeholder="项目类型"
                  clearable
                  multiple
                  collapse-tags
                  size="small"
                  style="width: 160px;"
                  @change="onFilterChange"
                >
                  <el-option
                    v-for="t in projectTypes"
                    :key="t.code"
                    :label="t.name"
                    :value="t.code"
                  />
                </el-select>
              </div>
            </div>
            <div ref="typeChartRef" class="chart-box"></div>
          </div>

          <!-- 项目类型分布（饼状图，支持下钻） -->
          <div class="chart-panel">
            <div class="chart-panel-header">
              <h3>项目类型分布</h3>
              <div class="chart-panel-actions">
                <el-button
                  v-if="drilldownPie"
                  size="small"
                  @click="drillupPieChart"
                >
                  <el-icon><Back /></el-icon> 返回项目类型
                </el-button>
              </div>
            </div>
            <div ref="dispatchPieRef" class="chart-box"></div>
          </div>
        </div>

        <!-- 图表2：责任单位分布（横向柱状图） -->
        <div class="chart-panel chart-panel-full">
          <div class="chart-panel-header">
            <h3>责任单位分布（Top 15）</h3>
            <div class="chart-panel-actions">
              <el-button
                v-if="drilldownUnit"
                size="small"
                @click="drillupUnitChart"
              >
                <el-icon><Back /></el-icon> 返回单位列表
              </el-button>
            </div>
          </div>
          <div ref="unitChartRef" class="chart-box"></div>
        </div>

        <!-- 专班负责人分布（饼状图） -->
        <div class="chart-panel chart-panel-full">
          <div class="chart-panel-header">
            <h3>专班负责人分布</h3>
          </div>
          <div ref="teamPieChartRef" class="chart-box" style="height:400px"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import echarts from '@/utils/echarts'
import { Folder, Loading, CircleCheck, OfficeBuilding, Document, WarningFilled, Back } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import { getConstructionStats } from '@/api/construction_dashboard'
import { getDicts } from '@/api/construction'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import { maskName } from '@/utils/mask'

const businessAuth = useBusinessAuthStore()
function mn(v) { return businessAuth.isVisitor ? maskName(v) : (v || '') }

const loading = ref(false)
const stats = reactive({
  overview: null,
  by_type: [],
  by_unit: [],
  by_dispatch_status: [],
  by_team_leader: []
})

// 图表 refs
const typeChartRef = ref(null)
const unitChartRef = ref(null)
const dispatchPieRef = ref(null)
const teamPieChartRef = ref(null)

// 图表实例
let typeChart = null
let unitChart = null
let dispatchPieChart = null
let teamPieChart = null

// 筛选
const filterProjectType = ref([])
const filterDispatchStatus = ref(['dispatching'])  // 默认只看调度中
const projectTypes = ref([])

// 下钻状态
const drilldownType = ref(null)
const drilldownPie = ref(null)
const drilldownUnit = ref(null)

// 调度状态配色（预设）
const dispatchStatusColors = {
  'dispatching': '#e6a23c',
  'completed': '#67c23a',
  'pending': '#f56c6c',
  'paused': '#909399'
}

// ResizeObserver
let resizeObserver = null

// ========== 颜色工具 ==========
function typeColorMap(keys) {
  const map = {}
  keys.forEach((k, i) => {
    const hue = ((i * 137.508) % 360)
    map[k] = `hsl(${Math.round(hue)}, 60%, 55%)`
  })
  return map
}

// ========== 图表1：项目类型分布（柱状图，支持下钻到调度状态）==========
function renderTypeChart() {
  if (!typeChart) return

  let data
  if (drilldownType.value) {
    // 下钻视图：显示各调度状态在该类型下的分布
    const item = stats.by_type.find(d => d.code === drilldownType.value)
    if (!item) return
    const parts = [
      { name: '调度中', value: item.dispatching || 0, color: dispatchStatusColors.dispatching },
      { name: '已完成', value: item.completed || 0, color: dispatchStatusColors.completed },
      { name: '其他', value: item.other || 0, color: '#909399' }
    ]
    data = parts.filter(p => p.value > 0)
    const names = data.map(d => d.name)
    const values = data.map(d => d.value)
    const colors = data.map(d => d.color)

    typeChart.off('click')
    typeChart.setOption({
      title: {
        text: `「${item.name}」调度状态分布`,
        textStyle: { fontSize: 14, fontWeight: 500, color: '#606266' },
        left: 'center',
        top: 0
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true },
      grid: { left: 12, right: 24, top: 40, bottom: 40, containLabel: true },
      xAxis: {
        type: 'category',
        data: names,
        axisLabel: { fontSize: 12 }
      },
      yAxis: { type: 'value', minInterval: 1, name: '项目数量' },
      series: [{
        type: 'bar',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: { color: colors[i], borderRadius: [4, 4, 0, 0] }
        })),
        barWidth: 40,
        label: { show: true, position: 'top', fontSize: 12, color: '#606266' }
      }]
    }, true)
  } else {
    // 默认视图：项目类型
    data = stats.by_type
    if (!data || data.length === 0) {
      typeChart.clear()
      return
    }

    const names = data.map(d => d.name)
    const values = data.map(d => d.count)
    const colorMap = typeColorMap(names)
    const colors = names.map(n => colorMap[n])
    const projectLists = data.map(d => d.projects || [])

    typeChart.off('click')
    typeChart.on('click', (params) => {
      const item = data[params.dataIndex]
      if (item) {
        drilldownType.value = item.code
      }
    })

    typeChart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        confine: true,
        formatter: (params) => {
          const idx = params[0]?.dataIndex ?? 0
          const item = data[idx]
          let html = `<strong>${params[0]?.axisValue || ''}</strong><br/>`
          html += `${params[0]?.marker} 项目数量：${params[0]?.value}<br/>`
          html += `<div style="margin-top:4px;padding-top:4px;border-top:1px dashed #ddd;font-size:12px;color:#666;">`
          html += `  调度中：${item.dispatching}　已完成：${item.completed}　其他：${item.other}`
          html += `</div>`
          const projects = projectLists[idx]
          if (projects && projects.length > 0) {
            html += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid #eee;font-size:12px;color:#666;">'
            html += '<strong>关联项目：</strong><br/>'
            projects.forEach(p => {
              html += `· ${mn(p.name)}<br/>`
            })
            html += '</div>'
          }
          return html
        }
      },
      grid: { left: 12, right: 24, top: 16, bottom: 80, containLabel: true },
      xAxis: {
        type: 'category',
        data: names,
        axisLabel: { rotate: names.length > 5 ? 35 : 0, fontSize: 11 }
      },
      yAxis: { type: 'value', minInterval: 1, name: '项目数量' },
      series: [{
        type: 'bar',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: { color: colors[i], borderRadius: [4, 4, 0, 0] }
        })),
        barWidth: data.length > 8 ? 26 : 34,
        emphasis: { itemStyle: { opacity: 0.8 } }
      }]
    }, true)
  }
}

function drillupTypeChart() {
  drilldownType.value = null
  renderTypeChart()
}

// ========== 图表2：项目类型分布（饼状图，支持下钻到调度状态）==========
function renderDispatchPie() {
  if (!dispatchPieChart) return

  dispatchPieChart.off('click')

  if (drilldownPie.value) {
    // ---- 下钻视图：该类型的调度状态分布 ----
    const item = stats.by_type.find(d => d.code === drilldownPie.value)
    if (!item) return
    const parts = [
      { name: '调度中', value: item.dispatching || 0, color: dispatchStatusColors.dispatching },
      { name: '已完成', value: item.completed || 0, color: dispatchStatusColors.completed },
      { name: '其他', value: item.other || 0, color: '#909399' }
    ].filter(p => p.value > 0)

    const total = parts.reduce((sum, p) => sum + p.value, 0)
    const colors = ['#e6a23c', '#67c23a', '#909399']

    dispatchPieChart.setOption({
      title: {
        text: `「${item.name}」调度状态`,
        textStyle: { fontSize: 14, fontWeight: 500, color: '#606266' },
        left: 'center',
        top: 0
      },
      tooltip: {
        trigger: 'item',
        confine: true,
        formatter: (params) => {
          return `<strong>${params.name}</strong><br/>项目数量：${params.value}（${params.percent}%）`
        }
      },
      legend: {
        orient: 'vertical',
        left: 10,
        top: 40,
        itemGap: 12,
        textStyle: { fontSize: 12 }
      },
      color: colors,
      series: [{
        type: 'pie',
        radius: ['50%', '72%'],
        center: ['58%', '55%'],
        avoidLabelOverlap: false,
        padAngle: 2,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}\n{d}%',
          fontSize: 11
        },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' },
          scaleSize: 8
        },
        data: parts.map(p => ({ name: mn(p.name), value: p.value }))
      }],
      graphic: [
        {
          type: 'text',
          left: '58%',
          top: '52%',
          style: {
            text: `${total}`,
            textAlign: 'center',
            fill: '#303133',
            fontSize: 22,
            fontWeight: 700
          }
        },
        {
          type: 'text',
          left: '58%',
          top: '59%',
          style: {
            text: '小计',
            textAlign: 'center',
            fill: '#909399',
            fontSize: 12
          }
        }
      ]
    }, true)
  } else {
    // ---- 默认视图：项目类型分布 ----
    const data = stats.by_type || []
    if (data.length === 0) {
      dispatchPieChart.clear()
      return
    }

    const total = data.reduce((sum, d) => sum + d.count, 0)
    const colorMap = typeColorMap(data.map(d => d.name))
    const colors = data.map(d => colorMap[d.name])

    dispatchPieChart.on('click', (params) => {
      const item = data[params.dataIndex]
      if (item) {
        drilldownPie.value = item.code
      }
    })

    dispatchPieChart.setOption({
      tooltip: {
        trigger: 'item',
        confine: true,
        formatter: (params) => {
          const item = data[params.dataIndex]
          let html = `<strong>${params.name}</strong><br/>项目数量：${params.value}（${params.percent}%）`
          if (item) {
            html += '<div style="margin-top:4px;padding-top:4px;border-top:1px dashed #ddd;font-size:12px;color:#666;">'
            html += `调度中：${item.dispatching}　已完成：${item.completed}　其他：${item.other}`
            html += '</div>'
            const projects = item.projects || []
            if (projects.length > 0) {
              html += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid #eee;font-size:12px;color:#666;">'
              html += '<strong>关联项目：</strong><br/>'
              projects.forEach(p => { html += `· ${mn(p.name)}<br/>` })
              html += '</div>'
            }
          }
          return html
        }
      },
      legend: {
        type: 'scroll',
        orient: 'vertical',
        left: 10,
        top: 'center',
        itemGap: 12,
        textStyle: { fontSize: 12 },
        formatter: (name) => {
          const item = data.find(d => d.name === name)
          const count = item ? item.count : 0
          const pct = total > 0 ? (count / total * 100).toFixed(1) : '0'
          return `${name}  ${count}个 (${pct}%)`
        }
      },
      color: colors,
      series: [{
        type: 'pie',
        radius: ['48%', '75%'],
        center: ['58%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 3, borderColor: '#fff', borderWidth: 2 },
        label: {
          show: true,
          position: 'inside',
          formatter: '{c}',
          fontSize: 13,
          fontWeight: 'bold',
          color: '#fff'
        },
        emphasis: {
          label: { show: true, fontSize: 18, fontWeight: 'bold' },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.3)'
          }
        },
        data: data.map(d => ({ name: d.name, value: d.count }))
      }],
      graphic: [
        {
          type: 'text',
          left: '58%',
          top: '49%',
          style: {
            text: `${total}`,
            textAlign: 'center',
            fill: '#303133',
            fontSize: 22,
            fontWeight: 700
          }
        },
        {
          type: 'text',
          left: '58%',
          top: '56%',
          style: {
            text: '项目总数',
            textAlign: 'center',
            fill: '#909399',
            fontSize: 12
          }
        }
      ]
    }, true)
  }
}

function drillupPieChart() {
  drilldownPie.value = null
  renderDispatchPie()
}

// ========== 图表3：专班负责人分布（饼状图）==========
function renderTeamPieChart() {
  if (!teamPieChart) return

  const data = stats.by_team_leader
  if (!data || data.length === 0) {
    teamPieChart.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } }
    })
    return
  }

  const colors = [
    '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
    '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#409eff',
    '#67c23a', '#e6a23c', '#f56c6c', '#909399'
  ]

  const total = data.reduce((sum, d) => sum + (d.count || 0), 0)

  teamPieChart.setOption({
    tooltip: {
      trigger: 'item',
      confine: true,
      extraCssText: 'max-width:420px;',
      formatter: (params) => {
        const pct = params.percent != null ? params.percent.toFixed(1) : '0.0'
        const item = data[params.dataIndex]
        const projects = item?.projects || []
        let html = `<strong>${params.name}</strong><br/>
          项目数量：${params.value} 个 &nbsp; 占比：${pct}%`
        if (projects.length > 0) {
          html += '<div style="margin-top:8px;padding-top:8px;border-top:1px solid #eee;font-size:12px;color:#606266;">'
          html += '<strong>关联项目：</strong><br/>'
          projects.forEach(p => {
            html += `<div style="padding:1px 0;">· ${mn(p.name)}</div>`
          })
          html += '</div>'
        }
        return html
      }
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 10,
      top: 'center',
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { fontSize: 12 },
      formatter: (name) => {
        const item = data.find(d => d.name === name)
        const count = item ? item.count : 0
        const pct = total > 0 ? (count / total * 100).toFixed(1) : '0'
        return `${name}  ${count}个 (${pct}%)`
      }
    },
    color: colors,
    series: [{
      type: 'pie',
      radius: ['48%', '75%'],
      center: ['40%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 3,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: true,
        position: 'inside',
        formatter: '{c}',
        fontSize: 13,
        fontWeight: 'bold',
        color: '#fff'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 18,
          fontWeight: 'bold'
        },
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.3)'
        }
      },
      data: data.map(d => ({ name: d.name, value: d.count }))
    }]
  }, true)
}

// ========== 图表4：责任单位分布（横向柱状图，支持下钻）==========
function renderUnitChart() {
  if (!unitChart) return

  unitChart.off('click')

  if (drilldownUnit.value) {
    // 下钻视图：该单位的项目类型分布
    const unit = stats.by_unit.find(u => u.code === drilldownUnit.value)
    const types = unit?.types || []
    const names = types.map(t => t.name).reverse()
    const values = types.map(t => t.count).reverse()
    const reversedTypes = [...types].reverse()
    const colorMap = typeColorMap(names)
    const colors = names.map(n => colorMap[n])

    unitChart.setOption({
      title: {
        text: `「${unit.name}」项目类型分布`,
        textStyle: { fontSize: 14, fontWeight: 500, color: '#606266' },
        left: 'center',
        top: 0
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true },
      grid: { left: 120, right: 40, top: 36, bottom: 20 },
      xAxis: { type: 'value', minInterval: 1, name: '项目数量' },
      yAxis: { type: 'category', data: names, axisLabel: { fontSize: 11 }, inverse: false },
      series: [{
        type: 'bar',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: { color: colors[i], borderRadius: [0, 4, 4, 0] }
        })),
        barMaxWidth: 20,
        label: { show: true, position: 'right', fontSize: 11, color: '#606266' }
      }]
    }, true)
  } else {
    // 默认视图：单位列表
    const data = stats.by_unit
    if (!data || data.length === 0) {
      unitChart.clear()
      return
    }

    const names = data.map(d => d.name).reverse()
    const values = data.map(d => d.count).reverse()

    unitChart.on('click', (params) => {
      const idx = params.dataIndex ?? 0
      const origIdx = data.length - 1 - idx
      const unit = stats.by_unit[origIdx]
      if (unit && (unit.types?.length > 0)) {
        drilldownUnit.value = unit.code
      }
    })

    unitChart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        confine: true,
        formatter: (params) => {
          const idx = params[0]?.dataIndex ?? 0
          const origIdx = data.length - 1 - idx
          const unit = stats.by_unit[origIdx]
          let html = `<strong>${params[0]?.axisValue || ''}</strong><br/>`
          html += `项目数量：${params[0]?.value}<br/>`
          const types = unit?.types || []
          if (types.length > 0) {
            html += '<div style="margin-top:4px;padding-top:4px;border-top:1px dashed #ddd;max-height:220px;overflow-y:auto;font-size:12px;color:#666;">'
            types.forEach(t => {
              html += `  · ${t.name}：${t.count}<br/>`
            })
            html += '</div>'
          }
          return html
        }
      },
      grid: { left: 100, right: 40, top: 10, bottom: 20 },
      xAxis: { type: 'value', minInterval: 1, name: '项目数量' },
      yAxis: { type: 'category', data: names, axisLabel: { fontSize: 12 }, inverse: false },
      series: [{
        type: 'bar',
        data: values,
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#5dade2' },
          { offset: 1, color: '#3498db' }
        ]),
        barMaxWidth: 22,
        itemStyle: { borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', fontSize: 12, color: '#606266' }
      }]
    }, true)
  }
}

function drillupUnitChart() {
  drilldownUnit.value = null
  renderUnitChart()
}

// ========== 渲染所有图表 ==========
function renderAllCharts() {
  renderTypeChart()
  renderDispatchPie()
  renderTeamPieChart()
  renderUnitChart()
}

// ========== 数据加载 ==========
async function fetchStats() {
  loading.value = true
  try {
    const params = {}
    if (filterProjectType.value && filterProjectType.value.length > 0) {
      params.project_type = filterProjectType.value.join(',')
    }
    if (filterDispatchStatus.value && filterDispatchStatus.value.length > 0) {
      params.dispatch_status = filterDispatchStatus.value.join(',')
    }
    const res = await getConstructionStats(params)
    if (res?.code === 0) {
      const data = res.data
      stats.overview = data.overview
      stats.by_type = data.by_type || []
      stats.by_unit = data.by_unit || []
      stats.by_dispatch_status = data.by_dispatch_status || []
      stats.by_team_leader = data.by_team_leader || []
      await nextTick()
      renderAllCharts()
    } else {
      ElMessage.error(res?.message || '获取统计数据失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '请求失败')
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  drilldownType.value = null
  drilldownPie.value = null
  drilldownUnit.value = null
  fetchStats()
}

// 监听下钻状态
watch(drilldownType, () => {
  renderTypeChart()
})
watch(drilldownPie, () => {
  renderDispatchPie()
})
watch(drilldownUnit, () => {
  renderUnitChart()
})

// 图表初始化
function initCharts() {
  if (typeChartRef.value && !typeChart) {
    typeChart = echarts.init(typeChartRef.value)
  }
  if (dispatchPieRef.value && !dispatchPieChart) {
    dispatchPieChart = echarts.init(dispatchPieRef.value)
  }
  if (teamPieChartRef.value && !teamPieChart) {
    teamPieChart = echarts.init(teamPieChartRef.value)
  }
  if (unitChartRef.value && !unitChart) {
    unitChart = echarts.init(unitChartRef.value)
  }
}

function setupResizeObserver() {
  const container = document.querySelector('.charts-grid')
  if (!container) return

  resizeObserver = new ResizeObserver(() => {
    typeChart?.resize()
    dispatchPieChart?.resize()
    teamPieChart?.resize()
    unitChart?.resize()
  })
  resizeObserver.observe(container)
}

function disposeCharts() {
  typeChart?.dispose()
  dispatchPieChart?.dispose()
  teamPieChart?.dispose()
  unitChart?.dispose()
  typeChart = null
  dispatchPieChart = null
  teamPieChart = null
  unitChart = null
  resizeObserver?.disconnect()
}

async function fetchProjectTypes() {
  try {
    const res = await getDicts()
    if (res?.code === 0) {
      projectTypes.value = res.data?.project_types || []
    }
  } catch { /* ignore */ }
}

onMounted(() => {
  initCharts()
  setupResizeObserver()
  fetchProjectTypes()
  fetchStats()
})

onUnmounted(() => {
  disposeCharts()
})
</script>

<style scoped>
.dashboard-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.page-body {
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px 32px 48px;
}

/* 页面标题 */
.page-header {
  margin-bottom: 24px;
}
.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #1a3a5c;
}
.page-subtitle {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
  display: inline-block;
}

/* 统计卡片 */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 1200px) {
  .stat-cards { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 768px) {
  .stat-cards { grid-template-columns: repeat(2, 1fr); }
  .charts-row-two { grid-template-columns: 1fr !important; }
}

.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  transition: box-shadow 0.3s, transform 0.2s;
}
.stat-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}

.stat-card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.stat-total .stat-card-icon { background: #ecf5ff; color: #409eff; }
.stat-dispatching .stat-card-icon { background: #fdf6ec; color: #e6a23c; }
.stat-completed .stat-card-icon { background: #f0f9eb; color: #67c23a; }
.stat-units .stat-card-icon { background: #f4f4f5; color: #606266; }
.stat-progress .stat-card-icon { background: #ecf5ff; color: #409eff; }
.stat-issues .stat-card-icon { background: #fef0f0; color: #f56c6c; }

.stat-card-body {
  display: flex;
  flex-direction: column;
}
.stat-card-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}
.stat-card-label {
  font-size: 13px;
  color: #909399;
  margin-top: 2px;
}

/* 图表网格 */
.charts-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 双列并排 */
.charts-row-two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.chart-panel {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  min-height: 380px;
}

.chart-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.chart-panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.chart-panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.chart-box {
  width: 100%;
  height: 340px;
}
</style>
