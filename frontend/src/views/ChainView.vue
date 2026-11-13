<!-- ChainView.vue: 产业链招商智能分析 — 图谱 / 缺口 / 目标企业 / 招商建议 四页签 -->
<template>
  <div class="chain-page">
    <BusinessNavbar variant="light" />

    <div class="page-body" v-loading="loading">
      <!-- 页面标题 -->
      <div class="page-header">
        <div>
          <h1>产业链招商智能分析</h1>
          <span class="page-subtitle">
            襄州片区企业产业链图谱 · 共性配套缺口 · 目标企业定向招引
          </span>
        </div>
        <div class="page-header-actions">
          <el-button plain @click="handleExportCsv('enterprises')">
            <el-icon><Grid /></el-icon> 环节供给总表
          </el-button>
          <el-button plain @click="handleExportCsv('gaps')">
            <el-icon><DataAnalysis /></el-icon> 缺口表
          </el-button>
          <el-button plain @click="handleExportCsv('targets')">
            <el-icon><Aim /></el-icon> 目标企业清单
          </el-button>
          <el-button type="success" plain @click="handleExportWord">
            <el-icon><Document /></el-icon> 导出分析报告
          </el-button>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="stat-cards">
        <div class="stat-card stat-total">
          <div class="stat-card-icon"><el-icon><Share /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ overview.enterprise_count ?? 0 }}</span>
            <span class="stat-card-label">分析企业数</span>
          </div>
        </div>
        <div class="stat-card stat-node">
          <div class="stat-card-icon"><el-icon><Connection /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ overview.node_count ?? 0 }}</span>
            <span class="stat-card-label">产业链环节</span>
          </div>
        </div>
        <div class="stat-card stat-leader">
          <div class="stat-card-icon"><el-icon><Star /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ overview.leader_count ?? 0 }}</span>
            <span class="stat-card-label">链主企业</span>
          </div>
        </div>
        <div class="stat-card stat-gap">
          <div class="stat-card-icon"><el-icon><Warning /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ overview.gap_count ?? 0 }}</span>
            <span class="stat-card-label">共性配套缺口</span>
          </div>
        </div>
        <div class="stat-card stat-target">
          <div class="stat-card-icon"><el-icon><Aim /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ overview.target_count ?? 0 }}</span>
            <span class="stat-card-label">目标企业候选</span>
          </div>
        </div>
        <div class="stat-card stat-local">
          <div class="stat-card-icon"><el-icon><OfficeBuilding /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ overview.local_target_count ?? 0 }}</span>
            <span class="stat-card-label">市域内可联动</span>
          </div>
        </div>
      </div>

      <el-tabs v-model="activeTab" class="chain-tabs">
        <!-- ========== 页签一：产业链图谱 ========== -->
        <el-tab-pane label="产业链图谱" name="graph">
          <div class="graph-toolbar">
            <span class="graph-legend">
              <span class="legend-item"><i class="legend-box local"></i>本地企业</span>
              <span class="legend-item"><i class="legend-star">★</i>链主企业</span>
              <span class="legend-item"><i class="legend-score">88</i>右上角徽标 = 存在共性缺口（数字为优先级总分）</span>
              <span class="legend-tip">点击环节节点可查看该环节企业清单</span>
            </span>
            <span class="toolbar-spacer" />
            <el-select v-model="graphLayerFilter" placeholder="全部层级" clearable style="width: 130px">
              <el-option label="上游" value="上游" />
              <el-option label="中游" value="中游" />
              <el-option label="下游" value="下游" />
              <el-option label="平台支撑" value="平台" />
            </el-select>
          </div>

          <div class="graph-wrap">
            <svg class="chain-svg" :viewBox="`0 0 ${SVG_W} ${svgHeight}`" preserveAspectRatio="xMidYMin meet">
              <defs>
                <marker id="arw" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
                  <path d="M0,0 L9,4.5 L0,9 Z" fill="#9aa8b8" />
                </marker>
              </defs>

              <!-- 层级泳道 -->
              <g v-for="lane in lanes" :key="'lane-' + lane.layer">
                <rect
                  :x="lane.x" :y="lane.y" :width="lane.w" :height="lane.h"
                  rx="10" :fill="lane.color" opacity="0.06"
                />
                <!-- 左侧层徽标 -->
                <rect
                  :x="lane.badgeX" :y="lane.y + 8" :width="META_W - 18" :height="42" rx="8"
                  :fill="lane.color" opacity="0.9"
                />
                <text
                  :x="lane.badgeX + (META_W - 18) / 2" :y="lane.y + 35"
                  class="lane-badge-text" text-anchor="middle"
                >{{ lane.layer }}</text>
              </g>

              <!-- 层间流向箭头（位于左侧徽标列） -->
              <g v-for="flow in flows" :key="'flow-' + flow.key">
                <line
                  :x1="flow.x" :y1="flow.y1" :x2="flow.x" :y2="flow.y2"
                  stroke="#9aa8b8" stroke-width="2" marker-end="url(#arw)"
                />
              </g>

              <!-- 环节节点 -->
              <g
                v-for="node in graphNodes" :key="node.code"
                class="node-group" :class="{ active: selectedNodeCode === node.code }"
                @click="handleNodeClick(node)"
              >
                <rect
                  :x="node.x" :y="node.y" :width="node.w" :height="node.h" rx="8"
                  :fill="selectedNodeCode === node.code ? node.color : '#ffffff'"
                  :stroke="node.color" stroke-width="1.4"
                />
                <text
                  :x="node.x + 12" :y="node.y + 23"
                  class="node-name" :fill="selectedNodeCode === node.code ? '#ffffff' : '#303133'"
                >{{ node.name }}</text>
                <text
                  :x="node.x + 12" :y="node.y + 42"
                  class="node-meta" :fill="selectedNodeCode === node.code ? 'rgba(255,255,255,0.88)' : '#909399'"
                >{{ node.enterprise_count }} 家企业<tspan v-if="node.leader_count"> · {{ node.leader_count }} 链主</tspan></text>
                <!-- 缺口角标 -->
                <g v-if="node.has_gap">
                  <circle :cx="node.x + node.w - 13" :cy="node.y + 13" r="10" :fill="node.gapColor" />
                  <text
                    :x="node.x + node.w - 13" :y="node.y + 17"
                    class="gap-badge-text" text-anchor="middle"
                  >{{ node.gap_score }}</text>
                </g>
                <!-- 链主星标 -->
                <text
                  v-if="node.leader_count" :x="node.x + node.w - 12" :y="node.y + node.h - 8"
                  class="leader-star" text-anchor="end"
                >★</text>
              </g>
            </svg>
          </div>

          <!-- 环节企业清单 -->
          <div class="section-header">
            <el-icon class="section-icon"><OfficeBuilding /></el-icon>
            <span class="section-title">{{ selectedNodeName ? selectedNodeName + ' 企业清单' : '全部环节企业清单' }}</span>
            <span class="section-extra" v-if="selectedNodeName">（点击图谱节点可切换）</span>
          </div>
          <el-table :data="nodeEnterprises" border size="small" max-height="360" v-loading="entLoading">
            <el-table-column prop="seq" label="序号" width="60" align="center" />
            <el-table-column prop="name" label="企业名称" min-width="220" show-overflow-tooltip />
            <el-table-column prop="industry" label="产业" width="90" align="center" />
            <el-table-column prop="node_name" label="所属环节" width="150" show-overflow-tooltip />
            <el-table-column label="层级" width="80" align="center">
              <template #default="{ row }">
                <span class="layer-chip" :style="{ background: row.layer_color + '1f', color: row.layer_color }">
                  {{ row.layer }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="role" label="角色" width="80" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.role === '链主'" type="danger" size="small" effect="dark">链主</el-tag>
                <el-tag v-else-if="row.role === '重点'" type="warning" size="small">重点</el-tag>
                <span v-else class="plain-text">一般</span>
              </template>
            </el-table-column>
            <el-table-column label="资质" width="150" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.is_hightech" type="success" size="small" effect="plain">高企</el-tag>
                <el-tag v-if="row.leader_level" type="warning" size="small" effect="plain" style="margin-left: 4px">
                  {{ row.leader_level }}龙头
                </el-tag>
                <el-tag v-if="row.is_scale" type="primary" size="small" effect="plain" style="margin-left: 4px">规上</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="region" label="属地" width="130" show-overflow-tooltip />
            <el-table-column prop="basis" label="归类依据" min-width="240" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>

        <!-- ========== 页签二：缺口分析 ========== -->
        <el-tab-pane label="缺口与优先级" name="gap">
          <!-- 优先级规则可视化 -->
          <div class="section-header">
            <el-icon class="section-icon"><SetUp /></el-icon>
            <span class="section-title">优先级评分规则（五因子）</span>
            <span class="section-extra">总分 = 五因子加权合计，满分 100 分</span>
          </div>
          <div class="rules-panel">
            <div class="rule-factors">
              <div v-for="f in ruleFactors" :key="f.key" class="factor-item">
                <div class="factor-head">
                  <span class="factor-name">{{ f.name }}</span>
                  <span class="factor-weight">{{ f.max }} 分</span>
                </div>
                <div class="factor-bar">
                  <div class="factor-bar-fill" :style="{ width: (f.max / 30 * 100) + '%' }" />
                </div>
                <div class="factor-desc">{{ f.desc }}</div>
              </div>
            </div>
            <div class="rule-levels">
              <div v-for="lv in ruleLevels" :key="lv.level" class="level-item">
                <span class="level-badge" :style="{ background: lv.color }">{{ lv.level }}</span>
                <div class="level-body">
                  <span class="level-range">{{ lv.range }}</span>
                  <span class="level-desc">{{ lv.desc }}</span>
                </div>
              </div>
              <div class="veto-rule">
                <el-icon><WarningFilled /></el-icon>
                <span>{{ ruleVeto }}</span>
              </div>
            </div>
          </div>

          <div class="section-header">
            <el-icon class="section-icon"><Warning /></el-icon>
            <span class="section-title">共性配套缺口清单</span>
            <span class="section-extra">按优先级总分降序</span>
          </div>
          <div class="gap-cards">
            <div
              v-for="gap in gaps" :key="gap.id"
              class="gap-card" :class="'lv-' + gap.level"
              @click="handleGapClick(gap)"
            >
              <div class="gap-card-head">
                <span class="gap-rank">#{{ gap.sort_order }}</span>
                <span class="gap-title">{{ gap.title }}</span>
                <el-tag :color="gap.level_color" effect="dark" size="small" class="gap-level-tag">
                  {{ gap.level }}优先级
                </el-tag>
                <span class="gap-score">{{ gap.total_score }}<i>分</i></span>
              </div>
              <div class="gap-meta">
                <span class="meta-item"><i class="dot" :style="{ background: gap.layer_color }" />{{ gap.node_name }}</span>
                <span class="meta-item">支撑企业 <b>{{ gap.supporter_count }}</b> 家</span>
                <span class="meta-item">目标企业 <b>{{ gap.target_count }}</b> 家</span>
              </div>
              <!-- 五因子构成条 -->
              <div class="factor-stack">
                <div
                  v-for="f in factorChips(gap)" :key="f.key"
                  class="factor-seg"
                  :style="{ width: f.pct + '%', background: f.color }"
                  :title="f.name + ' ' + f.value + '/' + f.max"
                >
                  <span v-if="f.pct > 8">{{ f.name }}</span>
                </div>
              </div>
              <div class="gap-demand">{{ gap.demand }}</div>
              <div class="gap-note">
                <el-icon><ChatDotSquare /></el-icon>
                <span>{{ gap.analysis_note }}</span>
              </div>
            </div>
          </div>

          <!-- 缺口雷达图 -->
          <div class="section-header">
            <el-icon class="section-icon"><DataAnalysis /></el-icon>
            <span class="section-title">五因子得分对比</span>
            <span class="section-extra">选中缺口与最高优先级缺口对比</span>
            <span class="toolbar-spacer" />
            <el-select v-model="selectedGapId" size="small" style="width: 240px">
              <el-option v-for="g in gaps" :key="g.id" :label="`${g.title}（${g.total_score}分）`" :value="g.id" />
            </el-select>
          </div>
          <div class="chart-panel">
            <div ref="radarRef" class="chart-box"></div>
          </div>
        </el-tab-pane>

        <!-- ========== 页签三：目标企业库 ========== -->
        <el-tab-pane label="目标企业库" name="target">
          <div class="target-toolbar">
            <el-select v-model="targetFilter.gap_id" placeholder="全部缺口" clearable style="width: 200px" @change="fetchTargets">
              <el-option label="全部缺口" value="" />
              <el-option v-for="g in gaps" :key="g.id" :label="`${g.title}（${g.total_score}分）`" :value="String(g.id)" />
            </el-select>
            <el-select v-model="targetFilter.node_code" placeholder="全部环节" clearable style="width: 170px" @change="fetchTargets">
              <el-option label="全部环节" value="" />
              <el-option v-for="n in nodes" :key="n.code" :label="n.name" :value="n.code" />
            </el-select>
            <el-select v-model="targetFilter.is_local" placeholder="全部区域" clearable style="width: 140px" @change="fetchTargets">
              <el-option label="全部区域" value="" />
              <el-option label="市域内已有" value="1" />
              <el-option label="待引进" value="0" />
            </el-select>
            <el-input
              v-model="targetFilter.keyword" placeholder="搜索企业名 / 主营 / 所在地" clearable
              style="width: 240px" @keyup.enter="fetchTargets" @clear="fetchTargets"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-button type="primary" @click="fetchTargets">查询</el-button>
            <span class="toolbar-spacer" />
            <span class="result-count">共 {{ targets.length }} 家目标企业</span>
          </div>

          <el-table :data="targets" border size="small" v-loading="targetLoading" max-height="600">
            <el-table-column prop="name" label="目标企业" min-width="200" show-overflow-tooltip />
            <el-table-column prop="gap_title" label="对应缺口" min-width="160" show-overflow-tooltip />
            <el-table-column label="缺口分档" width="90" align="center">
              <template #default="{ row }">
                <span class="level-badge-sm" :style="{ background: levelColor(row.gap_level) }">{{ row.gap_level }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="region" label="所在地" width="130" show-overflow-tooltip />
            <el-table-column prop="products" label="主营方向" min-width="190" show-overflow-tooltip />
            <el-table-column prop="scale" label="规模" min-width="170" show-overflow-tooltip />
            <el-table-column label="匹配分" width="90" align="center" sortable :sort-by="row => row.total_score">
              <template #default="{ row }">
                <span class="score-badge" :style="{ background: levelColor(row.gap_level) + '1f', color: levelColor(row.gap_level) }">
                  {{ row.total_score }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="区域属性" width="100" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.is_local" type="success" size="small" effect="plain">市域内已有</el-tag>
                <el-tag v-else type="info" size="small" effect="plain">待引进</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="复核状态" width="100" align="center">
              <template #default="{ row }">
                <el-select
                  :model-value="row.review_status" size="small"
                  :disabled="!canEdit"
                  @change="(v) => handleReviewChange(row, v)"
                >
                  <el-option label="待复核" value="待复核" />
                  <el-option label="已复核" value="已复核" />
                  <el-option label="已排除" value="已排除" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right" align="center">
              <template #default="{ row }">
                <el-button size="small" link type="primary" @click="showTargetDetail(row)">详情</el-button>
                <el-button
                  size="small" link type="warning"
                  v-if="canConvert"
                  @click="handleConvert(row)"
                >转为线索</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- ========== 页签四：招商建议与材料 ========== -->
        <el-tab-pane label="招商建议与材料" name="advice">
          <div class="advice-list">
            <div v-for="adv in advice" :key="adv.id" class="advice-card" :class="{ 'is-overall': adv.gap_id === 0 }">
              <div class="advice-head">
                <el-icon class="advice-icon"><Promotion v-if="adv.gap_id === 0" /><Guide v-else /></el-icon>
                <span class="advice-title">{{ adv.title }}</span>
                <el-tag v-if="adv.gap_score" :color="levelColor(adv.gap_level)" effect="dark" size="small">
                  {{ adv.gap_score }} 分
                </el-tag>
              </div>
              <div v-if="adv.kv" class="advice-kv">
                <el-icon><InfoFilled /></el-icon>
                <span>{{ adv.kv }}</span>
              </div>
              <div class="advice-content">{{ adv.content }}</div>
            </div>
          </div>

          <div class="section-header">
            <el-icon class="section-icon"><Files /></el-icon>
            <span class="section-title">材料导出</span>
            <span class="section-extra">导出内容均含评分口径与来源链接</span>
          </div>
          <div class="export-grid">
            <div class="export-card" @click="handleExportWord">
              <el-icon class="export-icon" style="color: #67c23a"><Document /></el-icon>
              <div class="export-name">产业链招商分析报告</div>
              <div class="export-desc">Word · 含总体判断、五个招商方向、风险提示与两张附表</div>
            </div>
            <div class="export-card" @click="handleExportCsv('enterprises')">
              <el-icon class="export-icon" style="color: #409eff"><Grid /></el-icon>
              <div class="export-name">环节供给总表</div>
              <div class="export-desc">CSV · 62 家企业的环节归类、资质与归类依据</div>
            </div>
            <div class="export-card" @click="handleExportCsv('gaps')">
              <el-icon class="export-icon" style="color: #e6a23c"><DataAnalysis /></el-icon>
              <div class="export-name">产业链缺口表</div>
              <div class="export-desc">CSV · 五因子分项得分、支撑企业与研判结论</div>
            </div>
            <div class="export-card" @click="handleExportCsv('targets')">
              <el-icon class="export-icon" style="color: #f56c6c"><Aim /></el-icon>
              <div class="export-name">目标企业清单</div>
              <div class="export-desc">CSV · 候选企业、匹配理由与来源链接（采集时间 2026-11-13）</div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 目标企业详情抽屉 -->
    <el-drawer v-model="detailVisible" title="目标企业详情" direction="rtl" size="520px" append-to-body class="chain-drawer">
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title"><el-icon><Aim /></el-icon> 目标企业详情</span>
        </div>
      </template>
      <div v-if="currentTarget" class="detail-body">
        <h3 class="detail-name">{{ currentTarget.name }}</h3>
        <div class="detail-tags">
          <el-tag size="small" :style="{ background: currentTarget.layer_color + '1f', color: currentTarget.layer_color }">
            {{ currentTarget.node_name }}
          </el-tag>
          <el-tag size="small" :color="levelColor(currentTarget.gap_level)" effect="dark">
            {{ currentTarget.gap_title }}
          </el-tag>
          <el-tag v-if="currentTarget.is_local" type="success" size="small" effect="plain">市域内已有</el-tag>
          <el-tag size="small" effect="plain">匹配 {{ currentTarget.total_score }} 分</el-tag>
        </div>
        <el-descriptions :column="1" border size="small" class="detail-desc">
          <el-descriptions-item label="所在地">{{ currentTarget.region || '—' }}</el-descriptions-item>
          <el-descriptions-item label="主营方向">{{ currentTarget.products || '—' }}</el-descriptions-item>
          <el-descriptions-item label="企业规模">{{ currentTarget.scale || '—' }}</el-descriptions-item>
          <el-descriptions-item label="匹配理由">{{ currentTarget.evidence || '—' }}</el-descriptions-item>
          <el-descriptions-item label="来源链接">
            <a v-if="currentTarget.source_url" :href="currentTarget.source_url" target="_blank" rel="noopener" class="source-link">
              {{ currentTarget.source_url }}
            </a>
            <span v-else>—</span>
          </el-descriptions-item>
          <el-descriptions-item label="复核状态">{{ currentTarget.review_status }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-score">
          <div class="score-title">五因子匹配得分</div>
          <div v-for="f in factorChips(currentTarget)" :key="f.key" class="score-row">
            <span class="score-name">{{ f.name }}</span>
            <div class="score-bar">
              <div class="score-bar-fill" :style="{ width: f.pct + '%', background: f.color }" />
            </div>
            <span class="score-value">{{ f.value }}</span>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Share, Connection, Star, Warning, Aim, OfficeBuilding, Grid, DataAnalysis,
  Document, SetUp, WarningFilled, ChatDotSquare, Search, InfoFilled, Files,
  Promotion, Guide,
} from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import { chainApi, downloadBlob } from '@/api/chain'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import echarts from '@/utils/echarts'

const businessAuth = useBusinessAuthStore()

const loading = ref(false)
const activeTab = ref('graph')
const overview = ref({})
const nodes = ref([])
const gaps = ref([])
const targets = ref([])
const advice = ref([])

const selectedNodeCode = ref('')
const graphLayerFilter = ref('')
const nodeEnterprises = ref([])
const entLoading = ref(false)

const targetLoading = ref(false)
const targetFilter = ref({ gap_id: '', node_code: '', is_local: '', keyword: '' })

const detailVisible = ref(false)
const currentTarget = ref(null)

const radarRef = ref(null)
let radarChart = null
const selectedGapId = ref(0)

// ===== 布局常量 =====
const SVG_W = 1180
const META_W = 76          // 左侧层徽标列宽
const NODE_AREA_X = META_W + 18
const NODE_AREA_W = SVG_W - NODE_AREA_X - 16
const NODE_W = 202
const NODE_H = 54
const COL_GAP = 14
const ROW_H = 72
const PER_ROW = 5
const LANE_PAD = 14
const LANE_GAP = 18

const LAYERS = [
  { layer: '上游', color: '#5b9bd5' },
  { layer: '中游', color: '#2f7f5f' },
  { layer: '下游', color: '#c98b2e' },
  { layer: '平台', color: '#7b6fd4' },
]

const LEVEL_COLORS = { 高: '#f56c6c', 中: '#e6a23c', 低: '#909399' }

const FACTOR_DEFS = [
  { key: 'f1', name: '需求刚性', max: 30, color: '#f56c6c' },
  { key: 'f2', name: '支撑企业数', max: 25, color: '#e6a23c' },
  { key: 'f3', name: '本地缺失度', max: 25, color: '#409eff' },
  { key: 'f4', name: '链主牵引', max: 10, color: '#67c23a' },
  { key: 'f5', name: '落地可行性', max: 10, color: '#7b6fd4' },
]

// ===== 计算属性 =====
const ruleFactors = computed(() => overview.value.rules?.factors || [])
const ruleLevels = computed(() => overview.value.rules?.levels || [])
const ruleVeto = computed(() => overview.value.rules?.veto || '')

const visibleNodes = computed(() => {
  if (!graphLayerFilter.value) return nodes.value
  return nodes.value.filter(n => n.layer === graphLayerFilter.value)
})

/** 每层节点按 PER_ROW 分行，返回行分组 */
function groupRows(layerNodes) {
  const rows = []
  for (let i = 0; i < layerNodes.length; i += PER_ROW) {
    rows.push(layerNodes.slice(i, i + PER_ROW))
  }
  return rows
}

/** 泳道：每层一条横向条带，高度按实际行数计算 */
const lanes = computed(() => {
  const result = []
  let y = 10
  for (const l of LAYERS) {
    const layerNodes = visibleNodes.value.filter(n => n.layer === l.layer)
    if (!layerNodes.length) continue
    const rows = groupRows(layerNodes)
    const h = rows.length * ROW_H + LANE_PAD * 2
    result.push({
      layer: l.layer,
      color: l.color,
      x: 8,
      y,
      w: SVG_W - 16,
      h,
      badgeX: 20,
      rows,
    })
    y += h + LANE_GAP
  }
  return result
})

const svgHeight = computed(() => {
  const ls = lanes.value
  if (!ls.length) return 200
  const last = ls[ls.length - 1]
  return last.y + last.h + 10
})

/** 节点坐标：层内分行横排，整行居中 */
const graphNodes = computed(() => {
  const out = []
  for (const lane of lanes.value) {
    lane.rows.forEach((row, ri) => {
      const totalW = row.length * NODE_W + (row.length - 1) * COL_GAP
      const startX = NODE_AREA_X + (NODE_AREA_W - totalW) / 2
      const y = lane.y + LANE_PAD + ri * ROW_H
      row.forEach((n, i) => {
        out.push({
          ...n,
          x: startX + i * (NODE_W + COL_GAP),
          y,
          w: NODE_W,
          h: NODE_H,
          gapColor: LEVEL_COLORS[n.gap_level] || '#909399',
        })
      })
    })
  }
  return out
})

/** 层间流向箭头：位于左侧徽标列的垂直短线 */
const flows = computed(() => {
  const out = []
  const ls = lanes.value
  for (let i = 0; i < ls.length - 1; i++) {
    const a = ls[i]
    const b = ls[i + 1]
    out.push({
      key: a.layer + '-' + b.layer,
      x: 20 + (META_W - 18) / 2,
      y1: a.y + a.h + 3,
      y2: b.y - 4,
    })
  }
  return out
})

const selectedNodeName = computed(() => {
  const n = nodes.value.find(x => x.code === selectedNodeCode.value)
  return n ? n.name : ''
})

const canEdit = computed(() => businessAuth.hasPermission('chain', 'edit'))
const canConvert = computed(() => businessAuth.hasPermission('chain', 'convert'))

function levelColor(level) {
  return LEVEL_COLORS[level] || '#909399'
}

/** 缺口 / 目标企业的五因子构成（用于堆叠条与详情） */
function factorChips(item) {
  const src = item.factors || item.scores || {}
  return FACTOR_DEFS.map(f => {
    const raw = src[f.key] || 0
    // 缺口为百分制得分（0-30/25/10），目标企业为 0-100 评分
    const value = item.factors ? raw : Math.round(raw * f.max / 100)
    return {
      key: f.key,
      name: f.name,
      color: f.color,
      max: f.max,
      value,
      pct: Math.max(0, Math.min(100, value / f.max * 100)),
    }
  })
}

// ===== 数据加载 =====
async function fetchOverview() {
  const res = await chainApi.getOverview()
  if (res.code === 0) overview.value = res.data || {}
}

async function fetchNodes() {
  const res = await chainApi.getNodes()
  if (res.code === 0) nodes.value = res.data || []
}

async function fetchGaps() {
  const res = await chainApi.getGaps()
  if (res.code === 0) {
    gaps.value = res.data || []
    // 默认选中第二优先缺口（与最高优先级缺口形成可区分的对比）
    if (!selectedGapId.value && gaps.value.length) {
      selectedGapId.value = gaps.value.length > 1 ? gaps.value[1].id : gaps.value[0].id
    }
  }
}

async function fetchTargets() {
  targetLoading.value = true
  try {
    const params = {}
    if (targetFilter.value.gap_id) params.gap_id = targetFilter.value.gap_id
    if (targetFilter.value.node_code) params.node_code = targetFilter.value.node_code
    if (targetFilter.value.is_local !== '') params.is_local = targetFilter.value.is_local
    if (targetFilter.value.keyword) params.keyword = targetFilter.value.keyword
    const res = await chainApi.getTargets(params)
    if (res.code === 0) targets.value = res.data || []
  } finally {
    targetLoading.value = false
  }
}

async function fetchAdvice() {
  const res = await chainApi.getAdvice()
  if (res.code === 0) advice.value = res.data || []
}

async function fetchNodeEnterprises() {
  entLoading.value = true
  try {
    const params = selectedNodeCode.value ? { node_code: selectedNodeCode.value } : {}
    const res = await chainApi.getEnterprises(params)
    if (res.code === 0) nodeEnterprises.value = res.data || []
  } finally {
    entLoading.value = false
  }
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.all([fetchOverview(), fetchNodes(), fetchGaps(), fetchTargets(), fetchAdvice()])
    await fetchNodeEnterprises()
  } catch (err) {
    ElMessage.error(err.message || '加载产业链分析数据失败')
  } finally {
    loading.value = false
  }
}

// ===== 交互 =====
function handleNodeClick(node) {
  selectedNodeCode.value = selectedNodeCode.value === node.code ? '' : node.code
  fetchNodeEnterprises()
}

function handleGapClick(gap) {
  targetFilter.value.gap_id = String(gap.id)
  activeTab.value = 'target'
  fetchTargets()
}

function showTargetDetail(row) {
  currentTarget.value = row
  detailVisible.value = true
}

async function handleReviewChange(row, status) {
  try {
    const res = await chainApi.updateReview(row.id, status)
    if (res.code === 0) {
      row.review_status = status
      ElMessage.success('复核状态已更新')
    }
  } catch (err) {
    ElMessage.error(err.message || '更新失败')
  }
}

async function handleConvert(row) {
  try {
    await ElMessageBox.confirm(
      `确认将「${row.name}」转为招商线索？将进入「招商线索研判」流程。`,
      '转为招商线索',
      { type: 'warning', confirmButtonText: '确认转换', cancelButtonText: '取消' }
    )
  } catch { return }

  try {
    const res = await chainApi.convertTarget(row.id)
    if (res.code === 0) {
      ElMessage.success(res.message || '已转为招商线索')
    }
  } catch (err) {
    ElMessage.error(err.message || '转换失败')
  }
}

// ===== 导出 =====
async function handleExportCsv(dataset) {
  try {
    const blob = await chainApi.exportCsv(dataset)
    const names = {
      enterprises: '环节供给总表',
      gaps: '产业链缺口表',
      targets: '目标企业清单',
    }
    downloadBlob(blob, `产业链招商-${names[dataset]}.csv`)
    ElMessage.success('导出成功')
  } catch (err) {
    ElMessage.error(err.message || '导出失败')
  }
}

async function handleExportWord() {
  try {
    const blob = await chainApi.exportWord()
    downloadBlob(blob, '襄阳农高区产业链招商分析报告.docx')
    ElMessage.success('导出成功')
  } catch (err) {
    ElMessage.error(err.message || '导出失败')
  }
}

// ===== 雷达图 =====
function renderRadar() {
  if (!radarRef.value || !gaps.value.length) return
  // 容器尚未布局完成时（display:none 或宽高为 0）跳过，等页签切换回调再触发
  const box = radarRef.value
  if (!box.offsetWidth || !box.offsetHeight) return
  if (!radarChart) radarChart = echarts.init(box)
  radarChart.resize()

  const top = gaps.value[0]
  const sel = gaps.value.find(g => g.id === selectedGapId.value) || top
  const same = sel.id === top.id

  const toPair = (g) => FACTOR_DEFS.map(f => {
    const raw = (g.factors || {})[f.key] || 0
    return Math.round(raw / f.max * 100)
  })

  const series = [{
    value: toPair(sel),
    name: sel.title,
    areaStyle: { color: 'rgba(64,158,255,0.28)' },
    lineStyle: { color: '#409eff', width: 2 },
    itemStyle: { color: '#409eff' },
  }]
  if (!same) {
    series.push({
      value: toPair(top),
      name: '最高优先级：' + top.title,
      areaStyle: { color: 'rgba(245,108,108,0.16)' },
      lineStyle: { color: '#f56c6c', width: 2, type: 'dashed' },
      itemStyle: { color: '#f56c6c' },
    })
  }

  radarChart.setOption({
    tooltip: {},
    legend: {
      data: series.map(s => s.name),
      bottom: 0,
      textStyle: { fontSize: 12 },
    },
    radar: {
      indicator: FACTOR_DEFS.map(f => ({ name: `${f.name}(${f.max})`, max: 100 })),
      radius: '64%',
      center: ['50%', '46%'],
      splitNumber: 4,
      axisName: { fontSize: 12, color: '#606266' },
      splitArea: { areaStyle: { color: ['#fbfcfd', '#f5f7fa'] } },
    },
    series: [{
      type: 'radar',
      data: series,
    }],
  }, true)
}

function handleResize() {
  if (radarChart) radarChart.resize()
}

onMounted(async () => {
  await loadAll()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (radarChart) {
    radarChart.dispose()
    radarChart = null
  }
})

watch(activeTab, (val) => {
  if (val === 'gap') {
    // 等页签完成切换、容器恢复显示后再初始化/重绘，避免画布尺寸塌陷
    nextTick(() => {
      setTimeout(() => {
        if (!radarChart && radarRef.value) radarChart = echarts.init(radarRef.value)
        renderRadar()
      }, 150)
    })
  }
})

watch(selectedGapId, () => {
  nextTick(() => setTimeout(renderRadar, 60))
})
</script>

<style scoped>
.chain-page { min-height: 100vh; background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%); }
.page-body { max-width: 1600px; margin: 0 auto; padding: 24px 32px 60px; }

.page-header {
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 16px; flex-wrap: wrap; margin-bottom: 20px;
}
.page-header h1 { margin: 0; font-size: 24px; font-weight: 700; color: #1a3a5c; }
.page-subtitle { font-size: 14px; color: #5b7189; margin-top: 4px; display: inline-block; }
.page-header-actions { display: flex; gap: 8px; flex-wrap: wrap; }

/* 统计卡片 */
.stat-cards { display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; margin-bottom: 20px; }
@media (max-width: 1400px) { .stat-cards { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 768px) { .stat-cards { grid-template-columns: repeat(2, 1fr); } }

.stat-card {
  background: #fff; border-radius: 10px; padding: 18px 20px;
  display: flex; align-items: center; gap: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  transition: box-shadow 0.3s, transform 0.2s;
}
.stat-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-2px); }
.stat-card-icon {
  width: 46px; height: 46px; border-radius: 12px; display: flex; align-items: center;
  justify-content: center; font-size: 22px; flex-shrink: 0;
}
.stat-total .stat-card-icon { background: #ecf5ff; color: #409eff; }
.stat-node .stat-card-icon { background: #e8f3ee; color: #2f7f5f; }
.stat-leader .stat-card-icon { background: #fdf6ec; color: #e6a23c; }
.stat-gap .stat-card-icon { background: #fef0f0; color: #f56c6c; }
.stat-target .stat-card-icon { background: #f4f4f5; color: #7b6fd4; }
.stat-local .stat-card-icon { background: #f0f9eb; color: #67c23a; }
.stat-card-body { display: flex; flex-direction: column; }
.stat-card-value { font-size: 26px; font-weight: 700; color: #303133; line-height: 1.2; }
.stat-card-label { font-size: 13px; color: #909399; margin-top: 2px; }

/* 页签 */
.chain-tabs { background: #fff; border-radius: 10px; padding: 8px 20px 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }

/* 分区标题 */
.section-header {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; margin: 20px 0 14px;
  background: #f5f7fa; border-radius: 6px; border-left: 3px solid #1a3a5c;
}
.section-icon { color: #1a3a5c; font-size: 16px; display: flex; align-items: center; }
.section-title { font-size: 14px; font-weight: 600; color: #303133; }
.section-extra { font-size: 12px; color: #909399; margin-left: 4px; }

/* 图谱 */
.graph-toolbar { display: flex; align-items: center; gap: 12px; margin: 14px 0 6px; flex-wrap: wrap; }
.graph-legend { display: flex; align-items: center; gap: 16px; font-size: 13px; color: #606266; }
.legend-item { display: inline-flex; align-items: center; gap: 5px; }

.graph-wrap {
  background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 10px;
  padding: 12px; overflow-x: auto;
}
.chain-svg { width: 100%; min-width: 1080px; height: auto; display: block; }
.lane-badge-text { font-size: 14px; font-weight: 700; fill: #fff; letter-spacing: 1px; }
.node-group { cursor: pointer; }
.node-group:hover rect { filter: brightness(0.97); }
.node-name { font-size: 13px; font-weight: 600; }
.node-meta { font-size: 11px; }
.gap-badge-text { font-size: 10px; fill: #fff; font-weight: 700; }
.leader-star { font-size: 13px; fill: #e6a23c; }

.legend-box { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.legend-box.local { background: #fff; border: 1.6px solid #5b9bd5; }
.legend-star { color: #e6a23c; font-style: normal; font-size: 14px; }
.legend-score {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 20px; height: 20px; padding: 0 5px; border-radius: 10px;
  background: #f56c6c; color: #fff; font-size: 10px; font-weight: 700; font-style: normal;
}
.legend-tip { color: #909399; font-size: 12px; }
.toolbar-spacer { flex: 1; }

.layer-chip { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px; }
.plain-text { color: #909399; font-size: 12px; }

/* 规则面板 */
.rules-panel { display: grid; grid-template-columns: 1.6fr 1fr; gap: 20px; }
@media (max-width: 1100px) { .rules-panel { grid-template-columns: 1fr; } }
.rule-factors { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; }
.factor-item { background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 8px; padding: 12px 14px; }
.factor-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }
.factor-name { font-size: 13px; font-weight: 600; color: #303133; }
.factor-weight { font-size: 13px; font-weight: 700; color: #409eff; }
.factor-bar { height: 8px; background: #ebeef5; border-radius: 4px; overflow: hidden; margin-bottom: 8px; }
.factor-bar-fill { height: 100%; background: linear-gradient(90deg, #5b9bd5, #409eff); border-radius: 4px; }
.factor-desc { font-size: 12px; color: #909399; line-height: 1.6; }

.rule-levels { background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 8px; padding: 14px; }
.level-item { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 12px; }
.level-badge {
  flex-shrink: 0; width: 26px; height: 26px; border-radius: 50%;
  color: #fff; font-size: 13px; font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center;
}
.level-badge-sm {
  display: inline-block; min-width: 22px; padding: 1px 7px; border-radius: 10px;
  color: #fff; font-size: 12px; text-align: center;
}
.level-body { display: flex; flex-direction: column; }
.level-range { font-size: 13px; font-weight: 600; color: #303133; }
.level-desc { font-size: 12px; color: #909399; margin-top: 2px; }
.veto-rule {
  display: flex; gap: 8px; align-items: flex-start;
  background: #fef7e8; border: 1px solid #f5dab1; border-radius: 6px;
  padding: 9px 12px; font-size: 12px; color: #8b6914; line-height: 1.6;
}

/* 缺口卡片 */
.gap-cards { display: flex; flex-direction: column; gap: 12px; }
.gap-card {
  background: #fff; border: 1px solid #ebeef5; border-left: 4px solid #909399;
  border-radius: 8px; padding: 14px 16px; cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
}
.gap-card:hover { box-shadow: 0 3px 12px rgba(0,0,0,0.08); transform: translateY(-1px); }
.gap-card.lv-高 { border-left-color: #f56c6c; }
.gap-card.lv-中 { border-left-color: #e6a23c; }
.gap-card.lv-低 { border-left-color: #909399; }
.gap-card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.gap-rank { font-size: 12px; font-weight: 700; color: #fff; background: #1a3a5c; border-radius: 4px; padding: 1px 7px; }
.gap-title { font-size: 15px; font-weight: 600; color: #303133; }
.gap-level-tag { border: none !important; }
.gap-score { margin-left: auto; font-size: 22px; font-weight: 700; color: #1a3a5c; }
.gap-score i { font-size: 12px; font-style: normal; color: #909399; margin-left: 2px; }
.gap-meta { display: flex; gap: 18px; font-size: 12px; color: #909399; margin-bottom: 8px; flex-wrap: wrap; }
.meta-item { display: inline-flex; align-items: center; gap: 5px; }
.meta-item b { color: #303133; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }

.factor-stack { display: flex; height: 20px; border-radius: 4px; overflow: hidden; margin-bottom: 10px; }
.factor-seg {
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; color: #fff; white-space: nowrap; overflow: hidden;
}

.gap-demand { font-size: 13px; color: #606266; line-height: 1.8; margin-bottom: 8px; }
.gap-note {
  display: flex; gap: 7px; align-items: flex-start;
  background: #f5f9ff; border-radius: 6px; padding: 9px 12px;
  font-size: 12px; color: #4a5568; line-height: 1.7;
}
.gap-note .el-icon { color: #409eff; margin-top: 2px; flex-shrink: 0; }

.chart-panel {
  background: #fff; border: 1px solid #ebeef5; border-radius: 10px; padding: 16px;
}
.chart-box { width: 100%; height: 420px; min-height: 420px; }

/* 目标企业 */
.target-toolbar { display: flex; align-items: center; gap: 10px; margin: 14px 0; flex-wrap: wrap; }
.result-count { font-size: 13px; color: #909399; }
.score-badge { display: inline-block; min-width: 34px; padding: 2px 8px; border-radius: 10px; font-weight: 700; font-size: 13px; text-align: center; }

/* 建议 */
.advice-list { display: flex; flex-direction: column; gap: 14px; margin-top: 14px; }
.advice-card {
  background: #fff; border: 1px solid #ebeef5; border-radius: 10px; padding: 18px 22px;
  border-left: 4px solid #1a3a5c;
}
.advice-card.is-overall { border-left-color: #409eff; background: linear-gradient(135deg, #f7fbff 0%, #eef6ff 100%); }
.advice-head { display: flex; align-items: center; gap: 9px; margin-bottom: 10px; flex-wrap: wrap; }
.advice-icon { color: #1a3a5c; font-size: 17px; }
.advice-title { font-size: 16px; font-weight: 600; color: #1a3a5c; }
.advice-kv {
  display: flex; align-items: center; gap: 7px;
  background: #f5f7fa; border-radius: 6px; padding: 7px 12px;
  font-size: 12px; color: #4a5568; margin-bottom: 10px;
}
.advice-kv .el-icon { color: #409eff; }
.advice-content { font-size: 14px; color: #303133; line-height: 2; white-space: pre-wrap; }

/* 导出卡片 */
.export-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
.export-card {
  background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 10px;
  padding: 18px; cursor: pointer; transition: all 0.2s;
}
.export-card:hover { border-color: #409eff; box-shadow: 0 3px 12px rgba(64,158,255,0.15); transform: translateY(-2px); }
.export-icon { font-size: 28px; margin-bottom: 8px; }
.export-name { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 5px; }
.export-desc { font-size: 12px; color: #909399; line-height: 1.7; }

/* 抽屉 */
.detail-body { padding: 4px 4px 20px; }
.detail-name { margin: 0 0 10px; font-size: 18px; font-weight: 700; color: #1a3a5c; }
.detail-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
.detail-desc ::v-deep(.el-descriptions__label) { width: 82px; color: #606266; }
.source-link { color: #409eff; word-break: break-all; }
.detail-score { margin-top: 20px; background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 8px; padding: 14px; }
.score-title { font-size: 13px; font-weight: 600; color: #303133; margin-bottom: 12px; }
.score-row { display: flex; align-items: center; gap: 10px; margin-bottom: 9px; }
.score-name { width: 84px; font-size: 12px; color: #606266; flex-shrink: 0; }
.score-bar { flex: 1; height: 8px; background: #ebeef5; border-radius: 4px; overflow: hidden; }
.score-bar-fill { height: 100%; border-radius: 4px; }
.score-value { width: 32px; text-align: right; font-size: 12px; font-weight: 600; color: #303133; }
</style>

<!-- 非 scoped：抽屉 append-to-body，渐变标题栏覆盖关闭按钮区域 -->
<style>
.chain-drawer { padding: 0 !important; margin: 0 !important; }
.chain-drawer .el-drawer__header {
  padding: 0 !important; margin: 0 !important; border-bottom: none !important;
  background: linear-gradient(135deg, #5b9bd5 0%, #8ab8e8 100%);
}
.chain-drawer .el-drawer__close-btn { color: #fff; }
.chain-drawer .el-drawer__body { padding: 18px 22px 22px !important; }
.drawer-title-bar { background: transparent; padding: 18px 24px; margin: 0 !important; width: 100%; box-sizing: border-box; display: flex; align-items: center; }
.drawer-title { color: #fff; font-size: 16px; font-weight: 600; letter-spacing: 1px; display: flex; align-items: center; gap: 8px; }
</style>
