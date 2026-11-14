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
            <span class="stat-card-value">{{ overview.outprov_target_count ?? 0 }}</span>
            <span class="stat-card-label">省外目标企业</span>
          </div>
        </div>
        <div class="stat-card stat-fit">
          <div class="stat-card-icon"><el-icon><TrendCharts /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ overview.high_fit_count ?? 0 }}</span>
            <span class="stat-card-label">投资可行性高</span>
          </div>
        </div>
        <div class="stat-card stat-strong">
          <div class="stat-card-icon"><el-icon><Connection /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ strongTargetCount }}</span>
            <span class="stat-card-label">强链目标企业</span>
          </div>
        </div>
        <div class="stat-card stat-xz">
          <div class="stat-card-icon"><el-icon><OfficeBuilding /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ overview.xiangzhou_enterprise_count ?? 0 }}</span>
            <span class="stat-card-label">襄州区属地企业</span>
          </div>
        </div>
        <div class="stat-card stat-kx">
          <div class="stat-card-icon"><el-icon><CircleCheck /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ overview.smei_count ?? 0 }}</span>
            <span class="stat-card-label">专精特新企业</span>
          </div>
        </div>
        <div class="stat-card stat-kexiao">
          <div class="stat-card-icon"><el-icon><Star /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ overview.kexiao_count ?? 0 }}</span>
            <span class="stat-card-label">科小入库企业</span>
          </div>
        </div>
        <div class="stat-card stat-group">
          <div class="stat-card-icon"><el-icon><Grid /></el-icon></div>
          <div class="stat-card-body">
            <span class="stat-card-value">{{ (overview.group_stats || []).length }}</span>
            <span class="stat-card-label">产业链大类分组</span>
          </div>
        </div>
      </div>

      <el-tabs v-model="activeTab" class="chain-tabs">
        <!-- ========== 页签一：产业链图谱 ========== -->
        <el-tab-pane label="产业链图谱" name="graph">
          <!-- 大类分组概览 -->
          <div class="section-header">
            <el-icon class="section-icon"><Grid /></el-icon>
            <span class="section-title">产业链大类分组</span>
            <span class="section-extra">层级 → 大类 → 环节 三级结构，共 {{ (overview.group_stats || []).length }} 个大类</span>
          </div>
          <div class="group-panel">
            <div
              v-for="g in groupStats" :key="g.group_name"
              class="group-card" :style="{ borderTopColor: g.color }"
            >
              <div class="group-card-head">
                <span class="group-card-name" :style="{ color: g.color }">{{ g.group_name }}</span>
                <span class="group-card-layer">{{ g.layer }}</span>
              </div>
              <div class="group-card-stats">
                <span><b>{{ g.node_count }}</b> 环节</span>
                <span><b>{{ g.enterprise_count }}</b> 企业</span>
                <span><b>{{ g.gap_count }}</b> 缺口</span>
                <span><b>{{ g.target_count }}</b> 目标企业</span>
              </div>
            </div>
          </div>

          <!-- 本地企业属地分布 -->
          <div class="section-header">
            <el-icon class="section-icon"><MapLocation /></el-icon>
            <span class="section-title">本地企业属地分布</span>
            <span class="section-extra">襄州区属地企业置顶，东津新区企业依次排后</span>
          </div>
          <div class="region-ent-panel">
            <div v-for="r in regionEntStats" :key="r.district" class="region-ent-item">
              <span class="region-ent-name">{{ r.district }}</span>
              <div class="region-ent-bar">
                <div
                  class="region-ent-fill"
                  :style="{ width: (r.count / (overview.enterprise_count || 1) * 100) + '%', background: r.district === '襄州区' ? '#409eff' : '#a0518c' }"
                />
              </div>
              <span class="region-ent-count">{{ r.count }} 家</span>
              <span class="region-ent-extra">
                链主 {{ r.leader_count }} · 高企 {{ r.hightech_count }} · 规上 {{ r.scale_count }} ·
                专精特新 {{ r.smei_count }} · 科小 {{ r.kexiao_count }} · 均实力 {{ r.strength_avg }}
              </span>
            </div>
          </div>

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

              <!-- 大类分组条（层级 → 大类 → 环节） -->
              <g v-for="gb in groupBars" :key="'gb-' + gb.key">
                <rect
                  :x="gb.x" :y="gb.y" :width="gb.w" :height="20" rx="5"
                  :fill="gb.color" opacity="0.14"
                />
                <rect :x="gb.x" :y="gb.y" :width="3.5" :height="20" rx="1.5" :fill="gb.color" />
                <text :x="gb.x + 11" :y="gb.y + 14" class="group-bar-text" :fill="gb.color">
                  {{ gb.group_name }}
                </text>
                <text :x="gb.x + gb.w - 8" :y="gb.y + 14" class="group-bar-count" text-anchor="end">
                  {{ gb.nodeCount }} 个环节
                </text>
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
            <el-table-column label="资质" width="190" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.is_hightech" type="success" size="small" effect="plain">高企</el-tag>
                <el-tag v-if="row.leader_level" type="warning" size="small" effect="plain" style="margin-left: 4px">
                  {{ row.leader_level }}龙头
                </el-tag>
                <el-tag v-if="row.is_scale" type="primary" size="small" effect="plain" style="margin-left: 4px">规上</el-tag>
                <el-tag v-if="row.is_smei" type="danger" size="small" effect="plain" style="margin-left: 4px">专精特新</el-tag>
                <el-tag v-if="row.is_kexiao" type="info" size="small" effect="plain" style="margin-left: 4px">科小</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="region" label="属地" width="130" show-overflow-tooltip />
            <el-table-column label="注册资本" width="110" align="right">
              <template #default="{ row }">
                <span>{{ fmtCapital(row.reg_capital) || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="企业实力" width="100" align="center" sortable :sort-by="row => row.strength || 0">
              <template #default="{ row }">
                <span
                  class="score-badge"
                  :style="{ background: strengthColor(row.strength) + '1f', color: strengthColor(row.strength) }"
                >{{ row.strength ?? '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="basis" label="归类依据" min-width="240" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>

        <!-- ========== 页签二：缺口分析 ========== -->
        <el-tab-pane label="缺口与优先级" name="gap">
          <!-- 优先级规则可视化 -->
          <div class="section-header">
            <el-icon class="section-icon"><SetUp /></el-icon>
            <span class="section-title">优先级评分规则（六因子）</span>
            <span class="section-extra">总分 = 六因子加权合计，满分 100 分</span>
          </div>
          <div class="rules-panel">
            <div class="rule-factors">
              <div v-for="f in ruleFactors" :key="f.key" class="factor-item">
                <div class="factor-head">
                  <span class="factor-name">{{ f.name }}</span>
                  <span class="factor-weight">{{ f.max }} 分</span>
                </div>
                <div class="factor-bar">
                  <div class="factor-bar-fill" :style="{ width: (f.max / 25 * 100) + '%' }" />
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

          <!-- 企业实力五维（F6 因子内部构成） -->
          <div class="section-header">
            <el-icon class="section-icon"><TrendCharts /></el-icon>
            <span class="section-title">企业实力评价（五维，用于 F6 因子）</span>
            <span class="section-extra">全部基于公开工商与财务信息，查不到即置空，不做推测</span>
          </div>
          <div class="strength-panel">
            <div v-for="s in ruleStrengthFactors" :key="s.key" class="strength-item">
              <div class="strength-head">
                <span class="strength-name">{{ s.name }}</span>
                <span class="strength-weight">{{ s.max }} 分</span>
              </div>
              <div class="factor-bar">
                <div class="factor-bar-fill strength-fill" :style="{ width: (s.max / 25 * 100) + '%' }" />
              </div>
              <div class="strength-desc">{{ s.desc }}</div>
            </div>
          </div>

          <!-- 链作用 + 投资可行性 判定口径 -->
          <div class="section-header">
            <el-icon class="section-icon"><Guide /></el-icon>
            <span class="section-title">链作用与投资可行性判定口径</span>
            <span class="section-extra">判断引入后能否补链、延链、强链</span>
          </div>
          <div class="role-fit-panel">
            <div class="role-block">
              <div class="block-title">链作用三分类</div>
              <div v-for="r in ruleChainRoles" :key="r.role" class="role-item">
                <span class="role-badge" :style="{ background: r.color }">{{ r.role }}</span>
                <span class="role-desc">{{ r.desc }}</span>
                <span class="role-count">{{ (chainRoleStats.find(x => x.role === r.role) || {}).count || 0 }} 家</span>
              </div>
            </div>
            <div class="role-block">
              <div class="block-title">投资可行性分档</div>
              <div v-for="f in ruleInvestFit" :key="f.level" class="role-item">
                <span class="role-badge" :style="{ background: f.color }">{{ f.level }}</span>
                <span class="role-desc">{{ f.desc }}</span>
                <span class="role-count">{{ (fitStats.find(x => x.level === f.level) || {}).count || 0 }} 家</span>
              </div>
            </div>
          </div>

          <!-- 省外企业可获得性分布 -->
          <div class="section-header">
            <el-icon class="section-icon"><MapLocation /></el-icon>
            <span class="section-title">目标企业地域来源分布</span>
            <span class="section-extra">招商引资主视角：优先关注省外企业到襄州投资的可行性</span>
          </div>
          <div class="region-panel">
            <div v-for="r in regionStats" :key="r.region_type" class="region-item">
              <div class="region-bar-wrap">
                <span class="region-name">{{ r.region_type }}</span>
                <div class="region-bar">
                  <div
                    class="region-bar-fill"
                    :style="{ width: (r.count / (overview.target_count || 1) * 100) + '%', background: REGION_COLORS[r.region_type] || '#409eff' }"
                  />
                </div>
                <span class="region-count">{{ r.count }} 家</span>
                <span class="region-high">可行性高 {{ r.high_fit }} 家</span>
              </div>
            </div>
          </div>

          <div class="section-header">
            <el-icon class="section-icon"><Warning /></el-icon>
            <span class="section-title">共性配套缺口清单</span>
            <span class="section-extra">按优先级总分降序 · 每张卡片含六因子雷达图，悬停查看得分构成</span>
            <span class="toolbar-spacer" />
            <el-switch
              v-model="showGapRadar" active-text="显示雷达图" size="small"
            />
          </div>
          <div class="gap-cards">
            <div
              v-for="gap in gaps" :key="gap.id"
              class="gap-card" :class="['lv-' + gap.level, { 'with-radar': showGapRadar }]"
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
                <span class="meta-item"><i class="dot" :style="{ background: gap.group_color }" />{{ gap.group_name }}</span>
                <span class="meta-item"><i class="dot" :style="{ background: gap.layer_color }" />{{ gap.node_name }}</span>
                <span class="meta-item">支撑企业 <b>{{ gap.supporter_count }}</b> 家</span>
                <span class="meta-item">目标企业 <b>{{ gap.target_count }}</b> 家</span>
              </div>

              <!-- 六因子雷达图 + 因子得分条 -->
              <div v-if="showGapRadar" class="gap-radar-wrap">
                <div class="gap-radar-box">
                  <div :ref="el => setGapRadarRef(gap.id, el)" class="gap-radar"></div>
                  <!-- 自建悬浮信息层（radar 序列不支持 axis 触发，item 触发需精确命中数据点） -->
                  <div
                    v-if="hoverTip.id === gap.id"
                    class="gap-radar-tip"
                    :style="{ borderColor: gap.level_color }"
                  >
                    <div class="gap-radar-tip-title">
                      {{ gap.title }} · {{ gap.total_score }} 分
                    </div>
                    <div
                      v-for="(f, i) in factorChips(gap)" :key="f.key"
                      class="gap-radar-tip-row"
                      :class="{ active: i === hoverTip.axis }"
                    >
                      <span class="gap-radar-tip-name" :style="{ color: f.color }">{{ f.name }}</span>
                      <span class="gap-radar-tip-val">
                        <b>{{ f.value }}</b><i>/{{ f.max }}</i>
                      </span>
                    </div>
                  </div>
                </div>
                <div class="gap-factor-list">
                  <div v-for="f in factorChips(gap)" :key="f.key" class="gap-factor-row">
                    <span class="gap-factor-name" :style="{ color: f.color }">{{ f.name }}</span>
                    <div class="gap-factor-track">
                      <div class="gap-factor-fill" :style="{ width: f.pct + '%', background: f.color }" />
                    </div>
                    <span class="gap-factor-val">{{ f.value }}<i>/{{ f.max }}</i></span>
                  </div>
                </div>
              </div>
              <div v-else class="factor-stack">
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
            <span class="section-title">六因子得分对比</span>
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
            <div class="quick-filters">
              <el-button
                :type="targetFilter.region_type === '省外' ? 'danger' : 'default'"
                size="small" @click="applyOutprovFilter"
              >
                <el-icon><MapLocation /></el-icon> 省外企业
                <span class="qf-count">{{ (regionStats.find(x => x.region_type === '省外') || {}).count || 0 }}</span>
              </el-button>
              <el-button
                :type="targetFilter.invest_fit === '高' ? 'danger' : 'default'"
                size="small" @click="applyHighFitFilter"
              >
                <el-icon><TrendCharts /></el-icon> 可行性高
                <span class="qf-count">{{ overview.high_fit_count ?? 0 }}</span>
              </el-button>
              <el-button
                :type="targetFilter.chain_role === '强链' ? 'success' : 'default'"
                size="small" @click="applyStrongChainFilter"
              >
                <el-icon><Connection /></el-icon> 强链目标
                <span class="qf-count">{{ strongTargetCount }}</span>
              </el-button>
              <el-button size="small" @click="resetTargetFilters">
                <el-icon><RefreshLeft /></el-icon> 重置
              </el-button>
            </div>
            <el-select v-model="targetFilter.gap_id" placeholder="全部缺口" clearable style="width: 200px" @change="fetchTargets">
              <el-option label="全部缺口" value="" />
              <el-option v-for="g in gaps" :key="g.id" :label="`${g.title}（${g.total_score}分）`" :value="String(g.id)" />
            </el-select>
            <el-select v-model="targetFilter.node_code" placeholder="全部环节" clearable style="width: 170px" @change="fetchTargets">
              <el-option label="全部环节" value="" />
              <el-option v-for="n in nodes" :key="n.code" :label="n.name" :value="n.code" />
            </el-select>
            <el-select v-model="targetFilter.region_type" placeholder="地域类型" clearable style="width: 150px" @change="fetchTargets">
              <el-option label="全部地域" value="" />
              <el-option
                v-for="r in targetFilters.region_types" :key="r.name"
                :label="`${r.name}（${r.count}）`" :value="r.name"
              />
            </el-select>
            <el-select v-model="targetFilter.chain_role" placeholder="链作用" clearable style="width: 130px" @change="fetchTargets">
              <el-option label="全部链作用" value="" />
              <el-option
                v-for="r in targetFilters.chain_roles" :key="r.name"
                :label="`${r.name}（${r.count}）`" :value="r.name"
              />
            </el-select>
            <el-select v-model="targetFilter.invest_fit" placeholder="投资可行性" clearable style="width: 140px" @change="fetchTargets">
              <el-option label="全部可行性" value="" />
              <el-option
                v-for="f in targetFilters.invest_fits" :key="f.name"
                :label="`可行性${f.name}（${f.count}）`" :value="f.name"
              />
            </el-select>
            <el-select v-model="targetFilter.province" placeholder="省份" clearable filterable style="width: 130px" @change="fetchTargets">
              <el-option label="全部省份" value="" />
              <el-option
                v-for="p in targetFilters.provinces" :key="p.name"
                :label="`${p.name}（${p.count}）`" :value="p.name"
              />
            </el-select>
            <el-input
              v-model="targetFilter.keyword" placeholder="搜索企业名 / 主营 / 所在地" clearable
              style="width: 220px" @keyup.enter="fetchTargets" @clear="fetchTargets"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-button type="primary" @click="fetchTargets">查询</el-button>
            <span class="toolbar-spacer" />
            <span class="result-count">共 {{ targets.length }} 家目标企业</span>
          </div>

          <el-table
            :data="targets" border size="small" v-loading="targetLoading" max-height="600"
            class="target-table"
          >
            <el-table-column prop="name" label="目标企业" min-width="190" fixed="left" show-overflow-tooltip />
            <el-table-column prop="gap_title" label="对应缺口" min-width="150" show-overflow-tooltip />
            <el-table-column label="缺口分档" width="90" align="center">
              <template #default="{ row }">
                <span class="level-badge-sm" :style="{ background: levelColor(row.gap_level) }">{{ row.gap_level }}</span>
              </template>
            </el-table-column>
            <el-table-column label="所属大类" width="130" align="center" show-overflow-tooltip>
              <template #default="{ row }">
                <span
                  v-if="row.group_name"
                  class="group-tag"
                  :style="{ background: (row.group_color || '#5b9bd5') + '1f', color: row.group_color || '#5b9bd5' }"
                >{{ row.group_name }}</span>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column label="所属环节" width="140" show-overflow-tooltip>
              <template #default="{ row }">
                <span>{{ row.node_name || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="省份" width="80" align="center">
              <template #default="{ row }">
                <span v-if="row.province" class="prov-tag">{{ row.province }}</span>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column label="地域类型" width="120" align="center">
              <template #default="{ row }">
                <span
                  v-if="row.region_type"
                  class="region-type-tag"
                  :style="{ background: (REGION_COLORS[row.region_type] || '#909399') + '1f', color: REGION_COLORS[row.region_type] || '#909399' }"
                >{{ row.region_type }}</span>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column label="链作用" width="90" align="center">
              <template #default="{ row }">
                <span
                  v-if="row.chain_role"
                  class="role-tag"
                  :style="{ background: (ROLE_COLORS[row.chain_role] || '#909399') + '1f', color: ROLE_COLORS[row.chain_role] || '#909399' }"
                >{{ row.chain_role }}</span>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column label="可行性" width="90" align="center">
              <template #default="{ row }">
                <span
                  v-if="row.invest_fit_level"
                  class="fit-tag"
                  :style="{ background: (FIT_COLORS[row.invest_fit_level] || '#909399') + '1f', color: FIT_COLORS[row.invest_fit_level] || '#909399' }"
                >{{ row.invest_fit_level }}</span>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column prop="region" label="所在地" width="120" show-overflow-tooltip />
            <el-table-column prop="products" label="主营方向" min-width="170" show-overflow-tooltip />
            <el-table-column label="落地形式" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <span>{{ row.landing_form || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="匹配分" width="90" align="center" sortable :sort-by="row => row.total_score">
              <template #default="{ row }">
                <span class="score-badge" :style="{ background: levelColor(row.gap_level) + '1f', color: levelColor(row.gap_level) }">
                  {{ row.total_score }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="企业实力" width="90" align="center" sortable :sort-by="row => row.strength || 0">
              <template #default="{ row }">
                <span
                  class="score-badge"
                  :style="{ background: strengthColor(row.strength) + '1f', color: strengthColor(row.strength) }"
                >{{ row.strength ?? '—' }}</span>
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
          <!-- 更新日志 -->
          <div class="section-header">
            <el-icon class="section-icon"><Clock /></el-icon>
            <span class="section-title">更新日志</span>
            <span class="section-extra">每次更新的修改内容、风险提示与下一步工作</span>
            <span class="toolbar-spacer" />
            <el-button size="small" plain @click="handleExportCsv('changelog')">
              <el-icon><Download /></el-icon> 导出日志
            </el-button>
          </div>
          <div class="changelog-list">
            <div v-for="c in changelog" :key="c.id" class="changelog-card">
              <div class="changelog-head">
                <el-tag type="primary" effect="dark" size="small">{{ c.version }}</el-tag>
                <span class="changelog-date">{{ c.log_date }}</span>
                <span class="changelog-title">{{ c.title }}</span>
              </div>
              <p v-if="c.summary" class="changelog-summary">{{ c.summary }}</p>
              <div class="changelog-blocks">
                <div class="changelog-block">
                  <div class="changelog-block-title">
                    <el-icon><EditPen /></el-icon> 修改内容
                  </div>
                  <ul>
                    <li v-for="(x, i) in c.changes" :key="i">{{ x }}</li>
                  </ul>
                </div>
                <div class="changelog-block risk">
                  <div class="changelog-block-title">
                    <el-icon><WarningFilled /></el-icon> 风险提示
                  </div>
                  <ul>
                    <li v-for="(x, i) in c.risks" :key="i">{{ x }}</li>
                  </ul>
                </div>
                <div class="changelog-block next">
                  <div class="changelog-block-title">
                    <el-icon><CircleCheck /></el-icon> 下一步工作
                  </div>
                  <ul>
                    <li v-for="(x, i) in c.next_steps" :key="i">{{ x }}</li>
                  </ul>
                </div>
              </div>
            </div>
            <div v-if="!changelog.length" class="plain-text">暂无更新日志</div>
          </div>

          <div class="section-header">
            <el-icon class="section-icon"><Promotion /></el-icon>
            <span class="section-title">招商建议</span>
            <span class="section-extra">总体判断 + 九个方向 + 风险提示 + 下一步工作</span>
          </div>
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
              <div class="advice-content" v-html="renderRichText(adv.content)" />
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
              <div class="export-desc">Word · 含总体判断、招商方向、风险提示、三张附表（本地企业实力）与更新日志</div>
            </div>
            <div class="export-card" @click="handleExportCsv('enterprises')">
              <el-icon class="export-icon" style="color: #409eff"><Grid /></el-icon>
              <div class="export-name">环节供给总表</div>
              <div class="export-desc">CSV · {{ overview.enterprise_count || 90 }} 家企业的大类与环节归类、资质、注册资本与实力评分</div>
            </div>
            <div class="export-card" @click="handleExportCsv('gaps')">
              <el-icon class="export-icon" style="color: #e6a23c"><DataAnalysis /></el-icon>
              <div class="export-name">产业链缺口表</div>
              <div class="export-desc">CSV · 六因子分项得分、支撑企业与研判结论</div>
            </div>
            <div class="export-card" @click="handleExportCsv('targets')">
              <el-icon class="export-icon" style="color: #f56c6c"><Aim /></el-icon>
              <div class="export-name">目标企业清单</div>
              <div class="export-desc">CSV · 省外候选企业、链作用、投资可行性、落地形式与多条来源链接</div>
            </div>
            <div class="export-card" @click="handleExportCsv('changelog')">
              <el-icon class="export-icon" style="color: #7b6fd4"><Clock /></el-icon>
              <div class="export-name">更新日志</div>
              <div class="export-desc">CSV · 历次修改内容、风险提示与下一步工作</div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 目标企业详情抽屉 -->
    <el-drawer v-model="detailVisible" title="目标企业详情" direction="rtl" size="780px" append-to-body class="chain-drawer">
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
          <el-tag
            v-if="currentTarget.group_name" size="small" effect="plain"
            :style="{ color: currentTarget.group_color || '#5b9bd5', borderColor: (currentTarget.group_color || '#5b9bd5') + '66' }"
          >{{ currentTarget.group_name }}</el-tag>
          <el-tag size="small" :color="levelColor(currentTarget.gap_level)" effect="dark">
            {{ currentTarget.gap_title }}
          </el-tag>
          <el-tag
            v-if="currentTarget.region_type" size="small" effect="plain"
            :style="{ color: REGION_COLORS[currentTarget.region_type] || '#909399' }"
          >{{ currentTarget.region_type }}</el-tag>
          <el-tag
            v-if="currentTarget.chain_role" size="small" effect="plain"
            :style="{ color: ROLE_COLORS[currentTarget.chain_role] || '#909399' }"
          >{{ currentTarget.chain_role }}</el-tag>
          <el-tag
            v-if="currentTarget.invest_fit_level" size="small" effect="plain"
            :style="{ color: FIT_COLORS[currentTarget.invest_fit_level] || '#909399' }"
          >可行性{{ currentTarget.invest_fit_level }}</el-tag>
          <el-tag size="small" effect="plain">匹配 {{ currentTarget.total_score }} 分</el-tag>
        </div>

        <div class="detail-section-title">
          <el-icon><Guide /></el-icon> 引才补链研判
        </div>
        <el-descriptions :column="1" border size="small" class="detail-desc">
          <el-descriptions-item label="所属省份">{{ currentTarget.province || '—' }}</el-descriptions-item>
          <el-descriptions-item label="所在地">{{ currentTarget.region || '—' }}</el-descriptions-item>
          <el-descriptions-item label="主营方向">{{ currentTarget.products || '—' }}</el-descriptions-item>
          <el-descriptions-item label="企业规模">{{ currentTarget.scale || '—' }}</el-descriptions-item>
          <el-descriptions-item label="链作用">{{ currentTarget.chain_role || '—' }}（补链/延链/强链）</el-descriptions-item>
          <el-descriptions-item label="建议落地形式">{{ currentTarget.landing_form || '—' }}</el-descriptions-item>
          <el-descriptions-item label="匹配本地链主">
            <span v-if="matchedChainNames.length">{{ matchedChainNames.join('、') }}</span>
            <span v-else>—</span>
          </el-descriptions-item>
          <el-descriptions-item label="投资可行性">
            <span :style="{ color: FIT_COLORS[currentTarget.invest_fit_level] || '#909399', fontWeight: 600 }">
              {{ currentTarget.invest_fit_level || '—' }}
            </span>
            <span v-if="currentTarget.invest_fit_reason" class="fit-reason">{{ currentTarget.invest_fit_reason }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="匹配理由">{{ currentTarget.evidence || '—' }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section-title">
          <el-icon><TrendCharts /></el-icon> 企业实力
        </div>
        <el-descriptions :column="2" border size="small" class="detail-desc">
          <el-descriptions-item label="注册资本">{{ fmtCapital(currentTarget.reg_capital) || '—' }}</el-descriptions-item>
          <el-descriptions-item label="实力评分">
            <span class="strength-num" :style="{ color: strengthColor(currentTarget.strength) }">{{ currentTarget.strength ?? '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="近三年营收">{{ fmtSeries(currentTarget.revenue_3y) || '—' }}</el-descriptions-item>
          <el-descriptions-item label="近三年净利">{{ fmtSeries(currentTarget.netprofit_3y) || '—' }}</el-descriptions-item>
          <el-descriptions-item label="融资情况">{{ currentTarget.funding || '—' }}</el-descriptions-item>
          <el-descriptions-item label="对外投资">{{ currentTarget.investments || '—' }}</el-descriptions-item>
          <el-descriptions-item label="投资签约" :span="2">{{ currentTarget.signed_deal || '—' }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section-title">
          <el-icon><Link /></el-icon> 来源链接
          <span class="section-extra">共 {{ currentSourceLinks.length }} 条</span>
        </div>
        <div class="source-list">
          <a
            v-for="(s, i) in currentSourceLinks" :key="i"
            :href="s.url" target="_blank" rel="noopener"
            class="source-item"
          >
            <span class="source-idx">{{ i + 1 }}</span>
            <span class="source-body">
              <span class="source-title">{{ s.title || '信息来源' }}</span>
              <span class="source-url">{{ s.url }}</span>
            </span>
            <el-icon class="source-arrow"><TopRight /></el-icon>
          </a>
          <span v-if="!currentSourceLinks.length" class="plain-text">—</span>
        </div>
        <el-descriptions :column="1" border size="small" class="detail-desc">
          <el-descriptions-item label="复核状态">{{ currentTarget.review_status }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-score">
          <div class="score-title">六因子匹配得分</div>
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
  Promotion, Guide, TrendCharts, MapLocation, RefreshLeft, Link, Clock,
  EditPen, CircleCheck, TopRight, Download,
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
const changelog = ref([])

const selectedNodeCode = ref('')
const graphLayerFilter = ref('')
const nodeEnterprises = ref([])
const entLoading = ref(false)

const targetLoading = ref(false)
const targetFilter = ref({
  gap_id: '', node_code: '', is_local: '', region_type: '',
  chain_role: '', invest_fit: '', province: '', keyword: '',
})
const targetFilters = ref({ provinces: [], region_types: [], chain_roles: [], invest_fits: [] })

const detailVisible = ref(false)
const currentTarget = ref(null)

const radarRef = ref(null)
let radarChart = null
const selectedGapId = ref(0)

/** 缺口卡片内嵌的六因子雷达图（每个缺口一个实例） */
const gapRadarRefs = ref({})
const gapRadarCharts = {}
/** 缺口卡片高度模式：标准 / 加高（含雷达图） */
const showGapRadar = ref(true)
/** 雷达图悬浮信息层：{ id, x, y } —— x/y 为相对雷达容器的像素坐标 */
const hoverTip = ref({ id: 0, x: 0, y: 0 })

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
  { layer: '其他', color: '#8c8c8c' },
]

const LEVEL_COLORS = { 高: '#f56c6c', 中: '#e6a23c', 低: '#909399' }

/** 大类分组配色（与后端 GROUP_COLORS 保持一致） */
const GROUP_COLORS = {
  农业生产投入品: '#5b9bd5',
  食品与农产品加工: '#2f7f5f',
  食品加工: '#c98b2e',
  饮料酒: '#a0518c',
  纤维与纺织: '#7b6fd4',
  科技产品: '#13c2c2',
  生产性服务: '#d48806',
  装备与设施: '#4a7ebb',
  非农业关联产业: '#8c8c8c',
}

const FACTOR_DEFS = [
  { key: 'f1', name: '需求刚性', max: 25, color: '#f56c6c' },
  { key: 'f2', name: '支撑企业数', max: 20, color: '#e6a23c' },
  { key: 'f3', name: '本地缺失度', max: 20, color: '#409eff' },
  { key: 'f4', name: '链主牵引', max: 10, color: '#67c23a' },
  { key: 'f5', name: '落地可行性', max: 10, color: '#7b6fd4' },
  { key: 'f6', name: '企业与承载实力', max: 15, color: '#14b8a6' },
]

/** 链作用配色（补链/延链/强链） */
const ROLE_COLORS = { 补链: '#f56c6c', 延链: '#e6a23c', 强链: '#2f7f5f' }

/** 投资可行性配色 */
const FIT_COLORS = { 高: '#f56c6c', 中: '#e6a23c', 低: '#909399' }

/** 地域类型配色 */
const REGION_COLORS = { 省外: '#f56c6c', 湖北省内市域外: '#e6a23c', 襄阳市域内: '#409eff' }

/** 企业实力评分配色（按分值分档，与缺口优先级无关） */
function strengthColor(score) {
  const s = Number(score) || 0
  if (s >= 80) return '#2f7f5f'
  if (s >= 60) return '#409eff'
  if (s >= 40) return '#e6a23c'
  return '#909399'
}

/** 注册资本格式化：数据库单位为万元 → 优先显示亿元 */
function fmtCapital(rc) {
  const v = Number(rc) || 0
  if (!v) return ''
  if (v >= 10000) return `${(v / 10000).toFixed(2)} 亿元`
  return `${v} 万元`
}

/**
 * 近三年营收 / 净利格式化
 * 原始形如 "2023:236900万;2024:265121万;2025:293373万"
 * 转成 "2023 23.69亿 / 2024 26.51亿 / 2025 29.34亿" 便于阅读
 */
function fmtSeries(text) {
  if (!text) return ''
  const parts = String(text).split(/[;；]/).filter(Boolean)
  const out = []
  for (const p of parts) {
    const m = p.match(/^\s*(\d{4})\s*[:：]\s*([\d.]+)\s*(万|亿)?\s*$/)
    if (!m) { out.push(p.trim()); continue }
    const [, year, num, unit] = m
    const n = parseFloat(num)
    if (unit === '亿') out.push(`${year} ${n.toFixed(2)}亿`)
    else if (n >= 10000) out.push(`${year} ${(n / 10000).toFixed(2)}亿`)
    else out.push(`${year} ${n}万`)
  }
  return out.join(' / ')
}

// ===== 计算属性 =====
const ruleFactors = computed(() => overview.value.rules?.factors || [])
const ruleLevels = computed(() => overview.value.rules?.levels || [])
const ruleVeto = computed(() => overview.value.rules?.veto || '')
const ruleStrengthFactors = computed(() => overview.value.rules?.strength_factors || [])
const ruleChainRoles = computed(() => overview.value.rules?.chain_roles || [])
const ruleInvestFit = computed(() => overview.value.rules?.invest_fit || [])
const regionStats = computed(() => overview.value.region_stats || [])
const chainRoleStats = computed(() => overview.value.chain_role_stats || [])
const fitStats = computed(() => overview.value.fit_stats || [])
const groupStats = computed(() => overview.value.group_stats || [])
const regionEntStats = computed(() => overview.value.region_ent_stats || [])
const strongTargetCount = computed(() => {
  const s = chainRoleStats.value.find(x => x.role === '强链')
  return s ? s.count : 0
})

/** 按大类分组的节点（层级 → 大类 → 环节 三级结构），用于图谱分栏 */
const nodesByGroup = computed(() => {
  const map = new Map()
  for (const n of nodes.value) {
    const g = n.group_name || '未分组'
    if (!map.has(g)) map.set(g, [])
    map.get(g).push(n)
  }
  // 按层级顺序 → 大类首次出现顺序排列
  const order = []
  for (const n of nodes.value) {
    const g = n.group_name || '未分组'
    if (!order.includes(g)) order.push(g)
  }
  return order.map(g => ({
    group_name: g,
    color: GROUP_COLORS[g] || '#5b9bd5',
    layer: (map.get(g)[0] || {}).layer || '',
    nodes: map.get(g),
  }))
})

/** 当前目标企业可对接的本地链主名称 */
const matchedChainNames = computed(() => {
  const ml = currentTarget.value?.match_local_chain
  if (!ml) return []
  if (Array.isArray(ml)) return ml
  try {
    const arr = JSON.parse(ml)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
})

/** 当前目标企业的多来源链接（带内容小标题） */
const currentSourceLinks = computed(() => {
  const sl = currentTarget.value?.source_links
  if (!sl) return []
  if (Array.isArray(sl)) return sl.filter(x => x && (x.title || x.url))
  try {
    const arr = JSON.parse(sl)
    return Array.isArray(arr) ? arr.filter(x => x && (x.title || x.url)) : []
  } catch {
    return []
  }
})

const visibleNodes = computed(() => {
  if (!graphLayerFilter.value) return nodes.value
  return nodes.value.filter(n => n.layer === graphLayerFilter.value)
})

/** 每个环节所属大类（用于图谱分栏标题） */
function groupOf(node) {
  return node.group_name || '未分组'
}

/** 每组节点按 PER_ROW 分行，返回行分组 */
function groupRows(layerNodes) {
  const rows = []
  for (let i = 0; i < layerNodes.length; i += PER_ROW) {
    rows.push(layerNodes.slice(i, i + PER_ROW))
  }
  return rows
}

/**
 * 泳道：层级 → 大类 → 环节 三级
 * 每个大类一条子泳道（带大类标题），子泳道内按每行 PER_ROW 个排环节节点。
 */
const lanes = computed(() => {
  const result = []
  let y = 10
  for (const l of LAYERS) {
    const layerNodes = visibleNodes.value.filter(n => n.layer === l.layer)
    if (!layerNodes.length) continue

    // 按大类分组，保持节点原有 sort_order 顺序
    const groups = []
    const gmap = new Map()
    for (const n of layerNodes) {
      const g = groupOf(n)
      if (!gmap.has(g)) {
        const grp = { group_name: g, color: GROUP_COLORS[g] || l.color, nodes: [] }
        gmap.set(g, grp)
        groups.push(grp)
      }
      gmap.get(g).nodes.push(n)
    }

    const subLanes = []
    let subY = y + LANE_PAD
    for (const grp of groups) {
      const rows = groupRows(grp.nodes)
      const h = rows.length * ROW_H + 34   // 34 = 大类标题条高度
      subLanes.push({
        layer: l.layer,
        layerColor: l.color,
        group_name: grp.group_name,
        color: grp.color,
        x: NODE_AREA_X,
        y: subY,
        w: NODE_AREA_W,
        h,
        rows,
      })
      subY += h + 10
    }

    const laneH = subY - y - 10 + LANE_PAD
    result.push({
      layer: l.layer,
      color: l.color,
      x: 8,
      y,
      w: SVG_W - 16,
      h: laneH,
      badgeX: 20,
      subLanes,
    })
    y += laneH + LANE_GAP
  }
  return result
})

const svgHeight = computed(() => {
  const ls = lanes.value
  if (!ls.length) return 200
  const last = ls[ls.length - 1]
  return last.y + last.h + 10
})

/** 节点坐标：子类泳道内分行横排，整行居中 */
const graphNodes = computed(() => {
  const out = []
  for (const lane of lanes.value) {
    for (const sub of lane.subLanes) {
      const titleH = 30
      sub.rows.forEach((row, ri) => {
        const totalW = row.length * NODE_W + (row.length - 1) * COL_GAP
        const startX = sub.x + (sub.w - totalW) / 2
        const y = sub.y + titleH + ri * ROW_H
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
  }
  return out
})

/** 大类分组条（泳道内的分类标题） */
const groupBars = computed(() => {
  const out = []
  for (const lane of lanes.value) {
    for (const sub of lane.subLanes) {
      out.push({
        key: lane.layer + '-' + sub.group_name,
        layer: lane.layer,
        group_name: sub.group_name,
        color: sub.color,
        x: sub.x + 6,
        y: sub.y + 4,
        w: sub.w - 12,
        nodeCount: sub.rows.reduce((a, r) => a + r.length, 0),
      })
    }
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

/** 缺口 / 目标企业的六因子构成（用于堆叠条与详情） */
function factorChips(item) {
  const src = item.factors || item.scores || {}
  return FACTOR_DEFS.map(f => {
    const raw = src[f.key] || 0
    // 缺口为百分制得分（0-25/20/10/15），目标企业为 0-100 评分
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

/**
 * 富文本渲染：段落分段 + **加粗** 关键句。
 * 内容来自平台内部种子数据（可信），但仍做基础 HTML 转义，避免尖括号被当作标签。
 */
function renderRichText(text) {
  if (!text) return ''
  const esc = String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  return esc
    .split(/\n{2,}/)
    .map(p => `<p class="advice-para">${p.replace(/\n/g, '<br />').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</p>`)
    .join('')
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
    if (targetFilter.value.region_type) params.region_type = targetFilter.value.region_type
    if (targetFilter.value.chain_role) params.chain_role = targetFilter.value.chain_role
    if (targetFilter.value.invest_fit) params.invest_fit = targetFilter.value.invest_fit
    if (targetFilter.value.province) params.province = targetFilter.value.province
    if (targetFilter.value.keyword) params.keyword = targetFilter.value.keyword
    const res = await chainApi.getTargets(params)
    if (res.code === 0) targets.value = res.data || []
  } finally {
    targetLoading.value = false
  }
}

/** 拉取目标企业库可用筛选项（省份 / 地域类型 / 链作用 / 投资可行性） */
async function fetchTargetFilters() {
  const res = await chainApi.getTargetFilters()
  if (res.code === 0) targetFilters.value = res.data || {}
}

/** 一键筛选：省外企业（招商引资主视角） */
function applyOutprovFilter() {
  targetFilter.value.region_type = targetFilter.value.region_type === '省外' ? '' : '省外'
  fetchTargets()
}

/** 一键筛选：投资可行性高 */
function applyHighFitFilter() {
  targetFilter.value.invest_fit = targetFilter.value.invest_fit === '高' ? '' : '高'
  fetchTargets()
}

/** 一键筛选：强链目标（可做链主或与本地链主绑定） */
function applyStrongChainFilter() {
  targetFilter.value.chain_role = targetFilter.value.chain_role === '强链' ? '' : '强链'
  fetchTargets()
}

/** 重置全部筛选条件 */
function resetTargetFilters() {
  targetFilter.value = {
    gap_id: '', node_code: '', is_local: '', region_type: '',
    chain_role: '', invest_fit: '', province: '', keyword: '',
  }
  fetchTargets()
}

async function fetchAdvice() {
  const res = await chainApi.getAdvice()
  if (res.code === 0) advice.value = res.data || []
}

async function fetchChangelog() {
  const res = await chainApi.getChangelog()
  if (res.code === 0) changelog.value = res.data || []
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
    await Promise.all([
      fetchOverview(), fetchNodes(), fetchGaps(), fetchTargets(),
      fetchAdvice(), fetchTargetFilters(), fetchChangelog(),
    ])
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
      changelog: '更新日志',
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
  Object.values(gapRadarCharts).forEach(c => c && c.resize())
}

// ===== 缺口卡片内嵌雷达图 =====

/** 设置缺口雷达图的 DOM 引用（v-for 中用 :ref 回调） */
function setGapRadarRef(id, el) {
  if (el) gapRadarRefs.value[id] = el
  else delete gapRadarRefs.value[id]
}

/**
 * 绘制单个缺口的六因子雷达图。
 * 每个卡片一个独立实例，18 个缺口 → 18 个 canvas，故只在页签可见时初始化。
 */
function renderGapRadar(id) {
  const el = gapRadarRefs.value[id]
  if (!el) return
  const gap = gaps.value.find(g => g.id === id)
  if (!gap) return
  if (!el.offsetWidth || !el.offsetHeight) return

  if (!gapRadarCharts[id]) {
    gapRadarCharts[id] = echarts.init(el)
  }
  const chart = gapRadarCharts[id]
  chart.resize()

  const color = LEVEL_COLORS[gap.level] || '#409eff'
  const values = FACTOR_DEFS.map(f => {
    const raw = (gap.factors || {})[f.key] || 0
    return Math.round(raw / f.max * 100)
  })
  const rawVals = FACTOR_DEFS.map(f => (gap.factors || {})[f.key] || 0)

  chart.setOption({
    tooltip: { show: false },
    radar: {
      indicator: FACTOR_DEFS.map(f => ({ name: f.name, max: 100 })),
      radius: '66%',
      center: ['50%', '52%'],
      splitNumber: 4,
      axisName: { fontSize: 10, color: '#606266' },
      splitArea: { areaStyle: { color: ['#fbfcfd', '#f5f7fa'] } },
      splitLine: { lineStyle: { color: '#e4e7ed' } },
      axisLine: { lineStyle: { color: '#e4e7ed' } },
    },
    series: [{
      type: 'radar',
      symbolSize: 5,
      emphasis: { focus: 'series', lineStyle: { width: 3 } },
      data: [{
        value: values,
        name: gap.title,
        areaStyle: { color: color + '2e' },
        lineStyle: { color, width: 2 },
        itemStyle: { color },
      }],
    }],
  }, true)

  // ---- 悬浮信息层 ----
  // ECharts 6 的 radar 序列不支持 tooltip.axis 触发，item 触发又必须精确命中 5px 数据点。
  // 因此改用 DOM 鼠标事件 + 雷达几何量（中心 50%/52%、半径 66%×min(w,h)/2）做命中检测，
  // 自建 HTML 信息层，并高亮鼠标所指向的指标轴。
  if (!el.__hoverBound) {
    el.__hoverBound = true
    const RADAR_CENTER_Y = 0.52
    const RADAR_RADIUS = 0.66
    const AXIS_STEP = 360 / FACTOR_DEFS.length

    el.addEventListener('mousemove', (e) => {
      const r = el.getBoundingClientRect()
      const x = e.clientX - r.left
      const y = e.clientY - r.top
      const cx = r.width / 2
      const cy = r.height * RADAR_CENTER_Y
      const dx = x - cx
      const dy = y - cy
      const rad = Math.min(r.width, r.height) / 2 * RADAR_RADIUS
      if (Math.sqrt(dx * dx + dy * dy) > rad) {
        if (hoverTip.value.id === id) hoverTip.value = { id: 0, x: 0, y: 0, axis: -1 }
        return
      }
      // 起始角 90°（正上方），顺时针递增
      let ang = Math.atan2(dx, -dy) * 180 / Math.PI
      if (ang < 0) ang += 360
      const axis = Math.round(ang / AXIS_STEP) % FACTOR_DEFS.length
      hoverTip.value = { id, x, y, axis }
    })
    el.addEventListener('mouseleave', () => {
      if (hoverTip.value.id === id) hoverTip.value = { id: 0, x: 0, y: 0, axis: -1 }
    })
  }
}

/** 批量渲染所有可见缺口雷达图 */
function renderAllGapRadars() {
  if (!showGapRadar.value) return
  for (const g of gaps.value) renderGapRadar(g.id)
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
  Object.keys(gapRadarCharts).forEach(k => {
    if (gapRadarCharts[k]) gapRadarCharts[k].dispose()
    delete gapRadarCharts[k]
  })
})

watch(activeTab, (val) => {
  if (val === 'gap') {
    // 等页签完成切换、容器恢复显示后再初始化/重绘，避免画布尺寸塌陷
    nextTick(() => {
      setTimeout(() => {
        if (!radarChart && radarRef.value) radarChart = echarts.init(radarRef.value)
        renderRadar()
        renderAllGapRadars()
      }, 150)
    })
  }
})

watch(selectedGapId, () => {
  nextTick(() => setTimeout(renderRadar, 60))
})

watch(gaps, () => {
  nextTick(() => setTimeout(renderAllGapRadars, 120))
})

watch(showGapRadar, (val) => {
  if (val) {
    nextTick(() => setTimeout(renderAllGapRadars, 80))
  } else {
    Object.keys(gapRadarCharts).forEach(k => {
      if (gapRadarCharts[k]) gapRadarCharts[k].dispose()
      delete gapRadarCharts[k]
    })
  }
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
.stat-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
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
.stat-fit .stat-card-icon { background: #fef0f0; color: #f56c6c; }
.stat-strong .stat-card-icon { background: #e8f3ee; color: #2f7f5f; }
.stat-xz .stat-card-icon { background: #ecf5ff; color: #409eff; }
.stat-kx .stat-card-icon { background: #fef0f0; color: #f56c6c; }
.stat-kexiao .stat-card-icon { background: #fdf6ec; color: #e6a23c; }
.stat-group .stat-card-icon { background: #f4f4f5; color: #7b6fd4; }
.stat-card-body { display: flex; flex-direction: column; }
.stat-card-value { font-size: 26px; font-weight: 700; color: #303133; line-height: 1.2; }
.stat-card-label { font-size: 13px; color: #909399; margin-top: 2px; }

/* 大类分组概览 */
.group-panel { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; }
.group-card {
  background: #fff; border: 1px solid #ebeef5; border-top: 3px solid #5b9bd5;
  border-radius: 8px; padding: 12px 14px;
  transition: box-shadow 0.2s, transform 0.2s;
}
.group-card:hover { box-shadow: 0 3px 12px rgba(0,0,0,0.08); transform: translateY(-1px); }
.group-card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.group-card-name { font-size: 14px; font-weight: 700; }
.group-card-layer { font-size: 11px; color: #909399; background: #f4f4f5; border-radius: 9px; padding: 1px 7px; }
.group-card-stats { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 12px; color: #909399; }
.group-card-stats b { color: #303133; font-size: 14px; }

/* 本地企业属地分布 */
.region-ent-panel {
  display: flex; flex-direction: column; gap: 10px;
  background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 8px; padding: 14px 16px;
}
.region-ent-item { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.region-ent-name { flex-shrink: 0; width: 92px; font-size: 13px; font-weight: 600; color: #303133; }
.region-ent-bar { flex: 1; min-width: 160px; height: 14px; background: #ebeef5; border-radius: 7px; overflow: hidden; }
.region-ent-fill { height: 100%; border-radius: 7px; transition: width 0.4s; }
.region-ent-count { flex-shrink: 0; width: 62px; text-align: right; font-size: 13px; font-weight: 700; color: #303133; }
.region-ent-extra { flex-shrink: 0; font-size: 12px; color: #909399; }

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

/* 缺口卡片：每行两个 */
.gap-cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; align-items: start; }
@media (max-width: 1280px) { .gap-cards { grid-template-columns: 1fr; } }
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
.gap-meta { display: flex; gap: 14px; font-size: 12px; color: #909399; margin-bottom: 10px; flex-wrap: wrap; }
.meta-item { display: inline-flex; align-items: center; gap: 5px; }
.meta-item b { color: #303133; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }

/* 缺口卡片内嵌雷达图 + 因子明细 */
.gap-radar-wrap {
  display: grid; grid-template-columns: 186px 1fr; gap: 12px; align-items: center;
  background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 8px;
  padding: 10px 12px; margin-bottom: 10px;
}
@media (max-width: 1500px) { .gap-radar-wrap { grid-template-columns: 166px 1fr; } }
.gap-radar-box { position: relative; width: 100%; height: 158px; }
.gap-radar { width: 100%; height: 158px; min-height: 158px; cursor: crosshair; transition: opacity 0.15s; }
/* 悬停时雷达淡化到仍可辨轮廓，信息层完整可读 */
.gap-radar-box:hover .gap-radar { opacity: 0.42; }
.gap-radar-tip {
  position: absolute; z-index: 12; pointer-events: none;
  left: 50%; top: 50%; transform: translate(-50%, -50%);
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid #409eff; border-radius: 7px;
  box-shadow: 0 3px 14px rgba(0, 0, 0, 0.14);
  padding: 7px 9px; width: 150px; box-sizing: border-box;
}
.gap-radar-tip-title {
  font-size: 11px; font-weight: 700; color: #1a3a5c;
  padding-bottom: 4px; margin-bottom: 3px; border-bottom: 1px solid #ebeef5;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.gap-radar-tip-row {
  display: flex; align-items: center; justify-content: space-between; gap: 6px;
  font-size: 11px; line-height: 1.8;
}
.gap-radar-tip-row.active { background: #eaf3ff; border-radius: 3px; }
.gap-radar-tip-name {
  font-weight: 600; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; min-width: 0; flex: 1;
}
.gap-radar-tip-val { color: #303133; flex-shrink: 0; white-space: nowrap; }
.gap-radar-tip-val b { font-size: 12px; }
.gap-radar-tip-val i { font-style: normal; font-size: 10px; color: #909399; }
.gap-factor-list { display: flex; flex-direction: column; gap: 5px; }
.gap-factor-row { display: flex; align-items: center; gap: 8px; }
.gap-factor-name { width: 88px; font-size: 11px; font-weight: 600; flex-shrink: 0; }
.gap-factor-track { flex: 1; height: 7px; background: #ebeef5; border-radius: 4px; overflow: hidden; }
.gap-factor-fill { height: 100%; border-radius: 4px; }
.gap-factor-val { width: 40px; text-align: right; font-size: 11px; font-weight: 700; color: #303133; flex-shrink: 0; }
.gap-factor-val i { font-style: normal; font-size: 10px; color: #909399; }

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

/* 图谱大类标题条 */
.group-bar-text { font-size: 12px; font-weight: 700; }
.group-bar-count { font-size: 11px; fill: #909399; }

.chart-panel {
  background: #fff; border: 1px solid #ebeef5; border-radius: 10px; padding: 16px;
}
.chart-box { width: 100%; height: 420px; min-height: 420px; }

/* 目标企业 */
.target-toolbar { display: flex; align-items: center; gap: 10px; margin: 14px 0; flex-wrap: wrap; }
.quick-filters { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.quick-filters .qf-count {
  display: inline-block; margin-left: 4px; padding: 0 6px;
  background: rgba(0, 0, 0, 0.06); border-radius: 9px;
  font-size: 12px; font-weight: 600;
}
.result-count { font-size: 13px; color: #909399; }
.score-badge { display: inline-block; min-width: 34px; padding: 2px 8px; border-radius: 10px; font-weight: 700; font-size: 13px; text-align: center; }
.prov-tag {
  display: inline-block; padding: 1px 8px; border-radius: 10px;
  background: #f4f4f5; color: #606266; font-size: 12px; font-weight: 600;
}
.region-type-tag, .role-tag, .fit-tag {
  display: inline-block; min-width: 34px; padding: 1px 8px; border-radius: 10px;
  font-size: 12px; font-weight: 600; text-align: center;
}

/* 企业实力五维面板 */
.strength-panel {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 14px; margin-bottom: 6px;
}
.strength-item { background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 8px; padding: 12px 14px; }
.strength-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }
.strength-name { font-size: 13px; font-weight: 600; color: #303133; }
.strength-weight { font-size: 13px; font-weight: 700; color: #14b8a6; }
.factor-bar-fill.strength-fill { background: linear-gradient(90deg, #0d9488, #14b8a6); }
.strength-desc { font-size: 12px; color: #909399; line-height: 1.6; }

/* 链作用 / 投资可行性 判定面板 */
.role-fit-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 6px; }
@media (max-width: 1100px) { .role-fit-panel { grid-template-columns: 1fr; } }
.role-block { background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 8px; padding: 14px; }
.block-title { font-size: 13px; font-weight: 700; color: #1a3a5c; margin-bottom: 10px; }
.role-item { display: flex; align-items: flex-start; gap: 9px; margin-bottom: 10px; font-size: 12px; }
.role-item:last-child { margin-bottom: 0; }
.role-badge {
  flex-shrink: 0; min-width: 34px; height: 22px; padding: 0 8px; border-radius: 11px;
  color: #fff; font-size: 12px; font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center;
}
.role-desc { flex: 1; color: #606266; line-height: 1.6; }
.role-count { flex-shrink: 0; color: #909399; font-weight: 600; }

/* 地域来源分布 */
.region-panel {
  display: flex; flex-direction: column; gap: 12px;
  background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 8px; padding: 16px;
}
.region-bar-wrap { display: flex; align-items: center; gap: 12px; }
.region-name { flex-shrink: 0; width: 110px; font-size: 13px; font-weight: 600; color: #303133; }
.region-bar { flex: 1; height: 14px; background: #ebeef5; border-radius: 7px; overflow: hidden; }
.region-bar-fill { height: 100%; border-radius: 7px; transition: width 0.4s; }
.region-count { flex-shrink: 0; width: 56px; text-align: right; font-size: 13px; font-weight: 700; color: #303133; }
.region-high { flex-shrink: 0; width: 110px; font-size: 12px; color: #909399; }

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
.advice-content { font-size: 14px; color: #303133; line-height: 2; }
.advice-para { margin: 0 0 10px; text-indent: 2em; }
.advice-para:last-child { margin-bottom: 0; }
.advice-content :deep(strong) { color: #1a3a5c; font-weight: 700; }

/* 更新日志 */
.changelog-list { display: flex; flex-direction: column; gap: 14px; }
.changelog-card {
  background: #fff; border: 1px solid #ebeef5; border-radius: 10px;
  padding: 16px 20px; border-left: 4px solid #7b6fd4;
}
.changelog-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.changelog-date { font-size: 13px; color: #909399; }
.changelog-title { font-size: 15px; font-weight: 700; color: #1a3a5c; }
.changelog-summary {
  margin: 0 0 12px; font-size: 13px; color: #4a5568; line-height: 1.9;
  background: #f7f9fc; border-radius: 6px; padding: 10px 14px;
}
.changelog-blocks { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
@media (max-width: 1280px) { .changelog-blocks { grid-template-columns: 1fr; } }
.changelog-block {
  background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 8px; padding: 12px 14px;
}
.changelog-block.risk { background: #fef9f5; border-color: #f5dab1; }
.changelog-block.next { background: #f4fbf7; border-color: #b9e3cd; }
.changelog-block-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 700; color: #1a3a5c; margin-bottom: 8px;
}
.changelog-block.risk .changelog-block-title { color: #8b6914; }
.changelog-block.next .changelog-block-title { color: #2f7f5f; }
.changelog-block ul { margin: 0; padding-left: 18px; }
.changelog-block li { font-size: 12.5px; color: #4a5568; line-height: 1.85; margin-bottom: 5px; }
.changelog-block li:last-child { margin-bottom: 0; }

/* 来源链接列表 */
.source-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.source-item {
  display: flex; align-items: flex-start; gap: 10px;
  background: #fbfcfd; border: 1px solid #ebeef5; border-radius: 8px;
  padding: 10px 12px; text-decoration: none; transition: all 0.2s;
}
.source-item:hover { border-color: #409eff; background: #f5f9ff; box-shadow: 0 2px 8px rgba(64,158,255,0.12); }
.source-idx {
  flex-shrink: 0; width: 20px; height: 20px; border-radius: 50%;
  background: #ecf5ff; color: #409eff; font-size: 11px; font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center; margin-top: 1px;
}
.source-body { flex: 1; display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.source-title { font-size: 13px; font-weight: 600; color: #303133; line-height: 1.5; }
.source-url { font-size: 11.5px; color: #909399; word-break: break-all; line-height: 1.5; }
.source-arrow { flex-shrink: 0; color: #c0c4cc; margin-top: 3px; }
.source-item:hover .source-arrow { color: #409eff; }

/* 大类标签 */
.group-tag {
  display: inline-block; padding: 1px 8px; border-radius: 10px;
  font-size: 12px; font-weight: 600;
}

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
.detail-section-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 700; color: #1a3a5c;
  margin: 18px 0 10px; padding-left: 8px;
  border-left: 3px solid #409eff; line-height: 1.3;
}
.detail-desc { margin-bottom: 6px; }
.detail-desc ::v-deep(.el-descriptions__label) { width: 92px; color: #606266; }
.fit-reason { margin-left: 8px; font-size: 12px; color: #909399; line-height: 1.6; }
.strength-num { font-size: 16px; font-weight: 700; }
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
