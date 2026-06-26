<template>
  <div class="dashboard-page" v-loading="loading">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1>数据看板</h1>
        <span class="page-subtitle">企业诉求统计分析</span>
      </div>

      <!-- 统计卡片 -->
      <div class="stat-cards">
        <div class="stat-card stat-total">
          <div class="stat-card-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.total_demands ?? 0 }}</span>
            <span class="stat-card-label">总诉求数</span>
          </div>
        </div>
        <div class="stat-card stat-pending">
          <div class="stat-card-icon">
            <el-icon><Clock /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.pending_count ?? 0 }}</span>
            <span class="stat-card-label">待处理</span>
          </div>
        </div>
        <div class="stat-card stat-processing">
          <div class="stat-card-icon">
            <el-icon><Loading /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.processing_count ?? 0 }}</span>
            <span class="stat-card-label">处理中</span>
          </div>
        </div>
        <div class="stat-card stat-resolved">
          <div class="stat-card-icon">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.resolved_count ?? 0 }}</span>
            <span class="stat-card-label">已解决</span>
          </div>
        </div>
        <div class="stat-card stat-projects">
          <div class="stat-card-icon">
            <el-icon><Folder /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.projects_with_demands ?? 0 }}</span>
            <span class="stat-card-label">涉及项目</span>
          </div>
        </div>
        <div class="stat-card stat-rate">
          <div class="stat-card-icon">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ stats.overview?.resolution_rate ?? 0 }}%</span>
            <span class="stat-card-label">解决率</span>
          </div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="charts-grid">
        <!-- 招商项目按类型分布（饼状图） -->
        <div class="chart-panel">
          <div class="chart-panel-header">
            <h3>招商项目类型分布</h3>
            <div class="chart-panel-actions">
              <el-select
                v-model="pieFollowStatus"
                placeholder="跟进状态"
                clearable
                multiple
                collapse-tags
                size="small"
                style="width: 150px;"
                @change="fetchInvestmentStats"
              >
                <el-option
                  v-for="s in followStatuses"
                  :key="s.code"
                  :label="s.name"
                  :value="s.code"
                />
              </el-select>
              <el-select
                v-model="pieMeetingStatus"
                placeholder="上会状态"
                clearable
                multiple
                collapse-tags
                size="small"
                style="width: 150px;"
                @change="fetchInvestmentStats"
              >
                <el-option
                  v-for="s in meetingStatuses"
                  :key="s.code"
                  :label="s.name"
                  :value="s.code"
                />
              </el-select>
            </div>
          </div>
          <div ref="pieChartRef" class="chart-box"></div>
        </div>

        <!-- 诉求类型分布（堆叠柱状图，支持一级/二级下钻 + 状态筛选 + 项目类型筛选） -->
        <div class="chart-panel">
          <div class="chart-panel-header">
            <h3>诉求类型分布</h3>
            <div class="chart-panel-actions">
              <el-button
                v-if="drilldownParent"
                size="small"
                @click="drillupTypeChart"
              >
                <el-icon><Back /></el-icon> 返回一级分类
              </el-button>
              <el-select
                v-model="filterProjectType"
                placeholder="项目类型"
                clearable
                size="small"
                style="width: 150px;"
                @change="onProjectTypeChange"
              >
                <el-option
                  v-for="t in projectTypes"
                  :key="t.code"
                  :label="t.name"
                  :value="t.code"
                />
              </el-select>
              <el-select
                v-model="filterStatus"
                placeholder="处理状态"
                size="small"
                style="width: 110px;"
                @change="renderTypeChart"
              >
                <el-option label="全部状态" value="" />
                <el-option label="待处理" value="pending" />
                <el-option label="处理中" value="processing" />
                <el-option label="已解决" value="resolved" />
              </el-select>
            </div>
          </div>
          <div ref="typeChartRef" class="chart-box"></div>
        </div>

        <!-- 对接单位分布（横向柱状图，支持下钻至类型） -->
        <div class="chart-panel chart-panel-full">
          <div class="chart-panel-header">
            <h3>对接单位分布（Top 15）</h3>
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { Document, Clock, Loading, CircleCheck, Folder, TrendCharts, Back } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import { getDemandStats, getInvestmentStats } from '@/api/dashboard'
import { getDicts } from '@/api/investment'

const loading = ref(false)
const stats = reactive({
  overview: null,
  by_type: [],
  by_type_level1: [],
  by_status: [],
  by_unit: [],
  by_project: [],
  by_month: []
})

// 图表 refs
const pieChartRef = ref(null)
const typeChartRef = ref(null)
const unitChartRef = ref(null)

// 图表实例
let pieChart = null
let typeChart = null
let unitChart = null

// 招商项目统计数据
const investmentStats = reactive({
  total_projects: 0,
  by_project_type: []
})

// 饼状图筛选
const pieFollowStatus = ref([])
const pieMeetingStatus = ref([])
const followStatuses = ref([])
const meetingStatuses = ref([])

// 状态筛选（下拉框，''=全部）
const filterStatus = ref('')
// 项目类型筛选
const filterProjectType = ref('')
const projectTypes = ref([])
// 下钻状态：null=一级视图，非空=当前下钻的一级字典code
const drilldownParent = ref(null)
// 单位图表下钻：null=单位列表，非空=当前下钻的单位code
const drilldownUnit = ref(null)

// ResizeObserver 实例
let resizeObserver = null

// 颜色
const statusColors = { pending: '#f56c6c', processing: '#e6a23c', resolved: '#67c23a' }
const statusNames = { pending: '待处理', processing: '处理中', resolved: '已解决' }

// ========== 渲染招商项目类型分布（饼状图）==========

function renderPieChart() {
  if (!pieChart) return

  const data = investmentStats.by_project_type
  if (!data || data.length === 0) {
    pieChart.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } }
    })
    return
  }

  // 颜色方案：与项目类型标签风格一致
  const colors = [
    '#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399',
    '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
    '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'
  ]

  const total = investmentStats.total_projects

  pieChart.setOption({
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
            const raw = parseFloat(p.invest_amount) || 0
            let amt = ''
            if (raw >= 10000) {
              amt = (raw / 10000).toFixed(2) + ' 亿元'
            } else if (raw > 0) {
              amt = raw.toFixed(2) + ' 万元'
            } else {
              amt = '暂未明确'
            }
            html += `<div style="display:flex;justify-content:space-between;padding:1px 0;"><span>· ${p.name}</span><span style="text-align:right;min-width:100px;flex-shrink:0;color:#909399;">${amt}</span></div>`
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

// ========== 渲染诉求类型分布（单系列柱状图 + 按类型着色 + 支持下钻）==========

// 按类型名称生成稳定色值（HSL色相分散）
function typeColorMap(keys) {
  const map = {}
  const count = keys.length
  keys.forEach((k, i) => {
    const hue = ((i * 137.508) % 360) // 黄金角度分散，避免相近色
    map[k] = `hsl(${Math.round(hue)}, 60%, 55%)`
  })
  return map
}

function renderTypeChart() {
  if (!typeChart) return

  // 根据下钻状态选择数据源
  let data
  if (drilldownParent.value) {
    data = stats.by_type.filter(d => d.parent_code === drilldownParent.value)
  } else {
    data = stats.by_type_level1
  }
  if (!data || data.length === 0) {
    data = []
  }

  // 根据状态筛选取值字段 — 全部状态用 count，否则用对应状态字段
  const statusFilter = filterStatus.value
  const valKey = statusFilter || 'count'

  const names = data.map(d => d.name)
  const values = data.map(d => d[valKey] || 0)
  const projectLists = data.map(d => d.projects || [])

  // 颜色：按当前显示的 type name 分配
  const colorMap = typeColorMap(names)
  const colors = names.map(n => colorMap[n])

  typeChart.off('click')
  typeChart.on('click', (params) => {
    if (!drilldownParent.value && stats.by_type.some(d => d.parent_code === data[params.dataIndex]?.code)) {
      drilldownParent.value = data[params.dataIndex].code
    }
  })

  typeChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const idx = params[0]?.dataIndex ?? 0
        const item = data[idx]
        let html = `<strong>${params[0]?.axisValue || ''}</strong><br/>`
        const label = statusFilter ? statusNames[statusFilter] : '诉求数量'
        html += `${params[0]?.marker} ${label}：${params[0]?.value}<br/>`
        // 一级视图：显示二级分类明细
        if (!drilldownParent.value && item) {
          const children = stats.by_type.filter(d => d.parent_code === item.code)
          if (children.length > 0) {
            html += '<div style="margin-top:4px;padding-top:4px;border-top:1px dashed #ddd;font-size:12px;color:#666;">'
            children.forEach(c => {
              const simpleName = c.name.includes('：') ? c.name.split('：').pop() : c.name
              html += `  ${simpleName}：${c[valKey] || 0}<br/>`
            })
            html += '</div>'
          }
        }
        const projects = projectLists[idx]
        if (projects && projects.length > 0) {
          html += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid #eee;max-height:180px;overflow-y:auto;font-size:12px;color:#666;">'
          html += '<strong>关联项目：</strong><br/>'
          projects.forEach(p => {
            html += `· ${p.name}<br/>`
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
    yAxis: {
      type: 'value',
      minInterval: 1,
      name: statusFilter ? statusNames[statusFilter] + '诉求数量' : '诉求数量'
    },
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

// 返回一级分类
function drillupTypeChart() {
  drilldownParent.value = null
  renderTypeChart()
}

// ========== 渲染对接单位分布（横向柱状图，支持下钻至诉求类型）==========
function renderUnitChart() {
  if (!unitChart) return

  unitChart.off('click')

  if (drilldownUnit.value) {
    // ---- 下钻视图：该单位的诉求类型分布（二级分类）----
    const unit = stats.by_unit.find(u => u.code === drilldownUnit.value)
    const types = unit?.types || []
    // 纵轴用简化名（去掉一级前缀）
    const simpleName = (t) => t.name.includes('：') ? t.name.split('：').pop() : t.name
    const names = types.map(t => simpleName(t)).reverse()
    const values = types.map(t => t.count).reverse()
    const reversedTypes = [...types].reverse()
    const colorMap = typeColorMap(names)
    const colors = names.map(n => colorMap[n])

    unitChart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params) => {
          const idx = params[0]?.dataIndex ?? 0
          const t = reversedTypes[idx]
          let html = `<strong>${params[0]?.axisValue || ''}</strong><br/>`
          html += `关联${params[0]?.value}条诉求<br/>`
          const projects = t?.projects || []
          if (projects.length > 0) {
            html += '<div style="margin-top:4px;padding-top:4px;border-top:1px dashed #ddd;max-height:180px;overflow-y:auto;font-size:12px;color:#666;">'
            html += '<strong>关联项目：</strong><br/>'
            projects.forEach(p => {
              html += `· ${p.name}<br/>`
            })
            html += '</div>'
          }
          return html
        }
      },
      grid: { left: 120, right: 40, top: 10, bottom: 20 },
      xAxis: { type: 'value', minInterval: 1, name: '诉求数量' },
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
    // ---- 默认视图：单位列表 ----
    const data = stats.by_unit
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
        formatter: (params) => {
          const idx = params[0]?.dataIndex ?? 0
          const origIdx = data.length - 1 - idx
          const unit = stats.by_unit[origIdx]
          let html = `<strong>${params[0]?.axisValue || ''}</strong><br/>`
          html += `关联${params[0]?.value}条诉求<br/>`
          const types = unit?.types || []
          if (types.length > 0) {
            const groups = {}
            types.forEach(t => {
              const parent = t.parent_code || t.name
              if (!groups[parent]) {
                groups[parent] = { name: t.parent_code ? t.name.split('：')[0] : t.name, sort: t.parent_sort_order || 99, children: [], total: 0 }
              }
              const childName = t.parent_code ? (t.name.includes('：') ? t.name.split('：').pop() : t.name) : t.name
              groups[parent].children.push({ name: childName, count: t.count, sort: t.sort_order })
              groups[parent].total += t.count
            })
            const sortedGroups = Object.values(groups).sort((a, b) => a.sort - b.sort)
            sortedGroups.forEach(g => {
              g.children.sort((a, b) => a.sort - b.sort)
            })
            html += '<div style="margin-top:4px;padding-top:4px;border-top:1px dashed #ddd;max-height:220px;overflow-y:auto;font-size:12px;color:#666;">'
            sortedGroups.forEach(g => {
              html += `  <strong style="font-size:13px;">${g.name}：${g.total}</strong><br/>`
              g.children.forEach(c => {
                html += `    <span style="color:#aaa;">●</span> ${c.name}：${c.count}<br/>`
              })
            })
            html += '</div>'
          }
          return html
        }
      },
      grid: { left: 100, right: 40, top: 10, bottom: 20 },
      xAxis: { type: 'value', minInterval: 1, name: '诉求数量' },
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

// 返回单位列表
function drillupUnitChart() {
  drilldownUnit.value = null
  renderUnitChart()
}

// 渲染所有图表
function renderAllCharts() {
  renderTypeChart()
  renderUnitChart()
}

// ========== 数据加载 ==========
async function fetchStats() {
  loading.value = true
  try {
    const params = {}
    if (filterProjectType.value) {
      params.project_type = filterProjectType.value
    }
    const res = await getDemandStats(params)
    if (res?.code === 0) {
      const data = res.data
      stats.overview = data.overview
      stats.by_type = data.by_type || []
      stats.by_type_level1 = data.by_type_level1 || []
      stats.by_status = data.by_status
      stats.by_unit = data.by_unit
      stats.by_project = data.by_project
      stats.by_month = data.by_month
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

// 项目类型变化 → 重新获取全部统计数据
function onProjectTypeChange() {
  drilldownParent.value = null
  fetchStats()
}

// 获取招商项目统计数据
async function fetchInvestmentStats() {
  try {
    const params = {}
    if (pieFollowStatus.value && pieFollowStatus.value.length > 0) {
      params.follow_status = pieFollowStatus.value.join(',')
    }
    if (pieMeetingStatus.value && pieMeetingStatus.value.length > 0) {
      params.meeting_status = pieMeetingStatus.value.join(',')
    }
    const res = await getInvestmentStats(params)
    if (res?.code === 0) {
      investmentStats.total_projects = res.data.total_projects || 0
      investmentStats.by_project_type = res.data.by_project_type || []
      await nextTick()
      renderPieChart()
    }
  } catch { /* ignore */ }
}

// 监听下钻状态变化
watch(drilldownParent, () => {
  renderTypeChart()
})
watch(drilldownUnit, () => {
  renderUnitChart()
})

// 图表初始化
function initCharts() {
  if (pieChartRef.value && !pieChart) {
    pieChart = echarts.init(pieChartRef.value)
  }
  if (typeChartRef.value && !typeChart) {
    typeChart = echarts.init(typeChartRef.value)
  }
  if (unitChartRef.value && !unitChart) {
    unitChart = echarts.init(unitChartRef.value)
  }
}

// Resize 处理
function setupResizeObserver() {
  const container = document.querySelector('.charts-grid')
  if (!container) return

  resizeObserver = new ResizeObserver(() => {
    pieChart?.resize()
    typeChart?.resize()
    unitChart?.resize()
  })
  resizeObserver.observe(container)
}

// 销毁图表
function disposeCharts() {
  pieChart?.dispose()
  typeChart?.dispose()
  unitChart?.dispose()
  pieChart = null
  typeChart = null
  unitChart = null
  resizeObserver?.disconnect()
}

async function fetchDicts() {
  try {
    const res = await getDicts()
    if (res?.code === 0) {
      projectTypes.value = res.data?.project_types || []
      followStatuses.value = res.data?.follow_statuses || []
      meetingStatuses.value = res.data?.meeting_statuses || []
    }
  } catch { /* ignore */ }
}

onMounted(() => {
  initCharts()
  setupResizeObserver()
  fetchDicts()
  fetchStats()
  fetchInvestmentStats()
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
  .charts-grid { grid-template-columns: 1fr !important; }
  .chart-panel-full { grid-column: auto; }
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
.stat-pending .stat-card-icon { background: #fef0f0; color: #f56c6c; }
.stat-processing .stat-card-icon { background: #fdf6ec; color: #e6a23c; }
.stat-resolved .stat-card-icon { background: #f0f9eb; color: #67c23a; }
.stat-projects .stat-card-icon { background: #f4f4f5; color: #606266; }
.stat-rate .stat-card-icon { background: #f0f9eb; color: #409eff; }

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

.chart-panel-full {
  grid-column: 1 / -1;
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
