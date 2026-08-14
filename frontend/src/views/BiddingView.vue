<!-- BiddingView.vue: 揭榜挂帅 — 业务端主视图（列表 + 七步流程详情 + 全周期跟踪） -->
<template>
  <div class="bidding-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 工具栏 -->
        <div class="toolbar">
          <el-input
            v-model="searchText"
            placeholder="搜索榜单名称、发榜企业、需求描述..."
            :prefix-icon="Search"
            clearable
            class="search-input"
            @input="fetchList"
          />
          <el-select
            v-model="filterStage"
            placeholder="当前阶段"
            clearable
            style="width: 150px;"
            @change="fetchList"
          >
            <el-option
              v-for="s in allStageOptions"
              :key="s.key"
              :label="s.name"
              :value="s.key"
            />
          </el-select>
          <el-select
            v-model="filterCategory"
            placeholder="技术领域"
            clearable
            style="width: 150px;"
            @change="fetchList"
          >
            <el-option
              v-for="c in dicts.categories"
              :key="c.code"
              :label="c.name"
              :value="c.code"
            />
          </el-select>
          <div class="toolbar-spacer" />
          <el-button type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 登记需求
          </el-button>
        </div>

        <!-- 列表 -->
        <el-table :data="projects" v-loading="loading" stripe style="width: 100%">
          <el-table-column prop="order_no" label="序号" width="60" align="center" />
          <el-table-column prop="title" label="榜单名称" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <el-link type="primary" @click="openDetail(row)">{{ row.title }}</el-link>
            </template>
          </el-table-column>
          <el-table-column prop="demander_name" label="发榜企业" min-width="140" show-overflow-tooltip />
          <el-table-column prop="category_name" label="技术领域" width="120" />
          <el-table-column label="当前阶段" width="110" align="center">
            <template #default="{ row }">
              <el-tag :type="stageTagType(row.current_stage)" size="small">
                {{ stageName(row.current_stage) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="悬赏(万元)" width="100" align="right">
            <template #default="{ row }">
              {{ row.bounty_amount ? row.bounty_amount : (row.expected_budget || '-') }}
            </template>
          </el-table-column>
          <el-table-column label="揭榜截止" width="110" align="center">
            <template #default="{ row }">{{ row.deadline_date || '-' }}</template>
          </el-table-column>
          <el-table-column prop="last_updated_at" label="更新时间" width="140" align="center" />
          <el-table-column label="操作" width="120" fixed="right" align="center">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="openDetail(row)">详情</el-button>
              <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- ==================== 详情抽屉（AppDrawer 固化风格） ==================== -->
    <AppDrawer
      v-model="showDetail"
      :title="detail ? detail.title : '榜单详情'"
      :icon="Flag"
      size="920px"
    >
      <template v-if="detail">
        <div class="detail-head">
          <el-tag :type="stageTagType(detail.current_stage)" size="large">
            {{ stageName(detail.current_stage) }}
          </el-tag>
          <span class="detail-cat">{{ detail.category_name || '未分类' }}</span>
          <span class="detail-demander">{{ detail.demander_name || '未填写发榜企业' }}</span>
        </div>

        <!-- 七步流程条 -->
        <el-steps :active="stepActiveIndex" align-center finish-status="success" class="steps-bar">
          <el-step
            v-for="s in BIDDING_STAGES"
            :key="s.key"
            :title="s.name"
            :description="s.desc"
          />
        </el-steps>
        <el-alert
          v-if="TERMINAL_STAGES.includes(detail.current_stage)"
          type="error"
          :title="`项目已终止（${TERMINAL_LABELS[detail.current_stage] || detail.current_stage}）`"
          :description="terminalReason"
          show-icon
          :closable="false"
          class="terminal-alert"
        />

        <!-- 当前阶段操作区 -->
        <div v-if="!TERMINAL_STAGES.includes(detail.current_stage)" class="action-bar">
          <span class="action-label">当前操作：</span>
          <el-button
            v-for="a in STAGE_ACTIONS[detail.current_stage] || []"
            :key="a.action"
            :type="a.type"
            size="small"
            @click="openAction(a.action)"
          >
            {{ a.label }}
          </el-button>
        </div>

        <!-- 阶段信息卡片 -->
        <el-collapse v-model="activePanels" class="stage-cards">
          <!-- 阶段1 需求信息 -->
          <el-collapse-item :title="`① 需求征集 — ${detail.title}`" name="stage1">
            <div class="field-label">基本信息</div>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="技术领域">{{ detail.category_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="需求来源">{{ detail.demand_source || '-' }}</el-descriptions-item>
              <el-descriptions-item label="预期投入(万元)">{{ detail.expected_budget || '-' }}</el-descriptions-item>
              <el-descriptions-item label="期望解决时限">{{ detail.expected_deadline || '-' }}</el-descriptions-item>
              <el-descriptions-item label="服务专班">{{ (detail.service_leader_names || []).join('、') || '-' }}</el-descriptions-item>
            </el-descriptions>

            <div class="field-label" style="margin-top: 12px;">企业概况</div>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="企业名称">{{ detail.demander_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="企业地址">{{ detail.enterprise_address || '-' }}</el-descriptions-item>
              <el-descriptions-item label="资质/荣誉" :span="2">
                {{ (detail.enterprise_qualifications || []).join('、') || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="所属行业">{{ detail.industry_code || '-' }}</el-descriptions-item>
              <el-descriptions-item label="企业性质">{{ detail.enterprise_nature || '-' }}</el-descriptions-item>
              <el-descriptions-item label="注册资本">{{ detail.registered_capital || '-' }}</el-descriptions-item>
              <el-descriptions-item label="成立时间">{{ detail.founded_year || '-' }}</el-descriptions-item>
              <el-descriptions-item label="人员规模">{{ detail.staff_size || '-' }}</el-descriptions-item>
              <el-descriptions-item label="上年度营收">{{ detail.last_year_revenue || '-' }}</el-descriptions-item>
              <el-descriptions-item label="联系人/电话" :span="2">
                {{ detail.demander_contact || '-' }} {{ detail.demander_phone || '' }}
              </el-descriptions-item>
            </el-descriptions>
            <div class="field-block" v-if="detail.main_products">
              <div class="field-label">主要产品或服务</div>
              <div class="field-text">{{ detail.main_products }}</div>
            </div>

            <div class="field-label" style="margin-top: 12px;">需求描述</div>
            <div class="field-block" v-if="detail.tech_difficulties">
              <div class="field-label">主要技术难点</div>
              <div class="field-text">{{ detail.tech_difficulties }}</div>
            </div>
            <div class="field-block" v-if="detail.tech_indicators">
              <div class="field-label">主要技术指标</div>
              <div class="field-text">{{ detail.tech_indicators }}</div>
            </div>
            <div class="field-block" v-if="detail.research_content">
              <div class="field-label">主要研究内容</div>
              <div class="field-text">{{ detail.research_content }}</div>
            </div>
            <div class="field-block" v-if="!detail.tech_difficulties && !detail.tech_indicators && !detail.research_content && detail.requirement_desc">
              <div class="field-label">技术需求描述</div>
              <div class="field-text">{{ detail.requirement_desc }}</div>
            </div>

            <div class="field-label" style="margin-top: 12px;">合作意向</div>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="拟短期合作">
                {{ (detail.short_term_cooperation || []).join('、') || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="拟长期合作">
                {{ (detail.long_term_cooperation || []).join('、') || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="意向合作专家">
                {{ detail.expert_intent === 'yes' ? (detail.expert_names || '有') : '无' }}
              </el-descriptions-item>
            </el-descriptions>

            <el-button size="small" style="margin-top: 12px;" @click="openEditBasic">编辑需求信息</el-button>
          </el-collapse-item>

          <!-- 阶段2 专家论证 -->
          <el-collapse-item title="② 专家论证" name="stage2">
            <template v-if="detail.argument_experts && detail.argument_experts.length">
              <el-table :data="detail.argument_experts" size="small" border>
                <el-table-column prop="name" label="专家姓名" />
                <el-table-column prop="org" label="单位" />
                <el-table-column prop="title" label="职称/职务" />
              </el-table>
            </template>
            <el-empty v-else description="尚未登记论证专家" :image-size="60" />
            <div class="field-block" v-if="detail.argument_opinion">
              <div class="field-label">论证意见</div>
              <div class="field-text">{{ detail.argument_opinion }}</div>
            </div>
            <div class="field-block" v-if="detail.argument_result">
              <div class="field-label">论证结论</div>
              <el-tag :type="detail.argument_status === 'passed' ? 'success' : 'danger'">
                {{ detail.argument_result }}
              </el-tag>
            </div>
          </el-collapse-item>

          <!-- 阶段3 发榜公告 -->
          <el-collapse-item title="③ 发榜公告" name="stage3">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="发布状态">
                <el-tag size="small" :type="detail.publish_status === 'published' ? 'success' : 'info'">
                  {{ { unpublished: '未发布', published: '已发布', expired: '已截止' }[detail.publish_status] }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="发布时间">{{ detail.publish_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="悬赏金额(万元)">{{ detail.bounty_amount || '-' }}</el-descriptions-item>
              <el-descriptions-item label="揭榜截止">{{ detail.deadline_date || '-' }}</el-descriptions-item>
            </el-descriptions>
            <div class="field-block" v-if="detail.accept_conditions">
              <div class="field-label">揭榜条件</div>
              <div class="field-text">{{ detail.accept_conditions }}</div>
            </div>
          </el-collapse-item>

          <!-- 阶段4 揭榜评审 -->
          <el-collapse-item title="④ 揭榜评审" name="stage4">
            <div class="sub-toolbar">
              <span class="sub-title">揭榜申请（{{ detail.bids.length }}）</span>
              <el-button size="small" type="primary" @click="openBidForm()">
                <el-icon><Plus /></el-icon> 内部代录
              </el-button>
            </div>
            <el-table :data="detail.bids" size="small" border>
              <el-table-column prop="bidder_name" label="揭榜方" min-width="130" show-overflow-tooltip />
              <el-table-column prop="bidder_type" label="类型" width="90" />
              <el-table-column prop="team_leader" label="负责人" width="90" />
              <el-table-column label="报价(万元)" width="90" align="right">
                <template #default="{ row }">{{ row.expected_amount }}</template>
              </el-table-column>
              <el-table-column label="评分" width="80" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.score !== null && row.score !== undefined" size="small">{{ row.score }}</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="90" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="bidStatusType(row.status)">{{ BID_STATUS_LABELS[row.status] || row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="来源" width="80" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.is_external" size="small" type="warning">外部提交</el-tag>
                  <el-tag v-else size="small" type="info">内部代录</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150" align="center">
                <template #default="{ row }">
                  <el-button size="small" link type="primary" @click="openBidForm(row)">编辑/评分</el-button>
                  <el-button size="small" link type="danger" @click="deleteBid(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="field-block" v-if="detail.review_result">
              <div class="field-label">评审结论</div>
              <div class="field-text">{{ detail.review_result }}</div>
            </div>
          </el-collapse-item>

          <!-- 阶段5 任务签订 -->
          <el-collapse-item title="⑤ 任务签订" name="stage5">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="签订状态">
                <el-tag size="small" :type="detail.task_status === 'signed' ? 'success' : 'info'">
                  {{ detail.task_status === 'signed' ? '已签订' : '未签订' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="签订日期">{{ detail.task_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="任务经费(万元)">{{ detail.task_amount || '-' }}</el-descriptions-item>
              <el-descriptions-item label="任务期限">{{ detail.task_duration || '-' }}</el-descriptions-item>
              <el-descriptions-item v-if="detail.selected_bid" label="揭榜方" :span="2">
                {{ detail.selected_bid.bidder_name }}（{{ detail.selected_bid.bidder_type }}）
              </el-descriptions-item>
            </el-descriptions>
            <div class="field-block" v-if="detail.task_notes">
              <div class="field-label">任务书备注</div>
              <div class="field-text">{{ detail.task_notes }}</div>
            </div>
          </el-collapse-item>

          <!-- 阶段6 过程管理 -->
          <el-collapse-item title="⑥ 过程管理" name="stage6">
            <div class="sub-toolbar">
              <span class="sub-title">任务书里程碑（{{ detail.milestones.length }}）</span>
              <el-button size="small" type="primary" @click="openMilestoneForm()">
                <el-icon><Plus /></el-icon> 新增里程碑
              </el-button>
            </div>
            <el-table :data="detail.milestones" size="small" border>
              <el-table-column prop="sort_order" label="#" width="40" align="center" />
              <el-table-column prop="content" label="里程碑内容" min-width="160" show-overflow-tooltip />
              <el-table-column prop="planned_date" label="计划完成" width="100" align="center" />
              <el-table-column prop="actual_date" label="实际完成" width="100" align="center" />
              <el-table-column label="状态" width="90" align="center">
                <template #default="{ row }">
                  <el-select :model-value="row.status" size="small" style="width: 84px;"
                    @change="(v) => updateMilestoneStatus(row, v)">
                    <el-option
                      v-for="(label, key) in MILESTONE_STATUS_LABELS"
                      :key="key"
                      :label="label"
                      :value="key"
                    />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="130" align="center">
                <template #default="{ row }">
                  <el-button size="small" link type="primary" @click="openMilestoneForm(row)">编辑</el-button>
                  <el-button size="small" link type="danger" @click="deleteMilestone(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-collapse-item>

          <!-- 阶段7 绩效评价 -->
          <el-collapse-item title="⑦ 绩效评价" name="stage7">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="评价状态">
                <el-tag size="small" :type="detail.eval_status === 'evaluated' ? 'success' : 'info'">
                  {{ detail.eval_status === 'evaluated' ? '已评价' : '未评价' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="评价日期">{{ detail.eval_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="绩效评分">{{ detail.eval_score ?? '-' }}</el-descriptions-item>
              <el-descriptions-item label="评价等级">
                <el-tag v-if="detail.eval_level" size="small" type="success">{{ detail.eval_level }}</el-tag>
                <span v-else>-</span>
              </el-descriptions-item>
            </el-descriptions>
            <div class="field-block" v-if="detail.eval_report">
              <div class="field-label">评价报告</div>
              <div class="field-text">{{ detail.eval_report }}</div>
            </div>
          </el-collapse-item>
        </el-collapse>

        <!-- 全周期服务跟踪时间线 -->
        <div class="timeline-block">
          <div class="sub-toolbar">
            <span class="sub-title">全周期服务跟踪</span>
            <el-button size="small" type="primary" @click="openTimelineForm">
              <el-icon><Plus /></el-icon> 添加服务记录
            </el-button>
          </div>
          <el-timeline v-if="detail.timeline.length" class="timeline-list">
            <el-timeline-item
              v-for="t in detail.timeline"
              :key="t.id"
              :timestamp="`${t.created_at} · ${t.record_by}`"
              :type="timelineType(t.record_type)"
              placement="top"
            >
              <div class="timeline-item">
                <el-tag size="small" :type="timelineType(t.record_type)">
                  {{ TIMELINE_TYPE_LABELS[t.record_type] || t.record_type }}
                </el-tag>
                <span v-if="t.stage" class="timeline-stage">{{ stageName(t.stage) }}</span>
                <div class="timeline-content">{{ t.content }}</div>
                <el-button size="small" link type="danger" @click="deleteTimeline(t)">删除</el-button>
              </div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无跟踪记录" :image-size="60" />
        </div>
      </template>
      <template #footer>
        <el-button type="primary" plain @click="showDetail = false">关闭</el-button>
      </template>
    </AppDrawer>

    <!-- ==================== 企业需求申报抽屉（固化风格 AppDrawer + 3 tab） ==================== -->
    <AppDrawer
      v-model="showBasicForm"
      :title="editingProject ? '编辑企业需求申报' : '企业需求申报'"
      :icon="Document"
      size="720px"
      @update:model-value="onDeclareClose"
    >
      <div class="sticky-tabs">
        <el-tabs v-model="declareTab">
          <!-- 企业概况：选择已有企业 或 新建 -->
          <el-tab-pane label="企业概况" name="enterprise">
            <!-- 企业选择行：下拉选择（默认，右侧新建 icon 切换） -->
            <div class="enterprise-row">
              <template v-if="!isNewEnterprise">
                <el-select
                  v-model="basicForm.enterprise_id"
                  filterable
                  placeholder="选择企业名称"
                  class="enterprise-select"
                  :loading="enterpriseLoading"
                  @change="onEnterpriseSelected"
                >
                  <el-option v-for="e in enterprises" :key="e.id" :label="e.org_name" :value="e.id">
                    <span>{{ e.org_name }}</span>
                    <span style="float: right; color: #909399; font-size: 12px;">{{ e.industry_code || '' }}</span>
                  </el-option>
                </el-select>
                <el-tooltip content="新建企业" placement="top">
                  <el-button circle class="enterprise-new-btn" @click="isNewEnterprise = true">
                    <el-icon><Plus /></el-icon>
                  </el-button>
                </el-tooltip>
              </template>
              <template v-else>
                <el-tooltip content="选择已有企业" placement="top">
                  <el-button circle class="enterprise-new-btn" @click="isNewEnterprise = false">
                    <el-icon><Search /></el-icon>
                  </el-button>
                </el-tooltip>
              </template>
            </div>

            <!-- 企业字段：选择模式带出可编辑；新建模式输入 -->
            <el-form :model="basicForm" label-width="120px" label-position="left" class="declare-form enterprise-form">
              <el-form-item v-if="isNewEnterprise" label="企业名称" required>
                <el-input v-model="basicForm.org_name" placeholder="企业名称" maxlength="100" show-word-limit />
              </el-form-item>
              <el-form-item label="企业地址">
                <el-input v-model="basicForm.enterprise_address" placeholder="企业地址" maxlength="120" show-word-limit />
              </el-form-item>
              <el-form-item label="资质荣誉">
                <el-tooltip content="资质/荣誉，可多选" placement="top">
                  <el-checkbox-group v-model="basicForm.enterprise_qualifications">
                    <el-checkbox v-for="q in QUALIFICATION_OPTIONS" :key="q" :label="q" />
                  </el-checkbox-group>
                </el-tooltip>
              </el-form-item>
              <el-form-item label="所属行业">
                <el-select v-model="basicForm.industry_code" placeholder="选择行业" style="width: 100%">
                  <el-option v-for="i in INDUSTRY_OPTIONS" :key="i" :label="i" :value="i" />
                </el-select>
              </el-form-item>
              <el-form-item label="注册资本">
                <el-input v-model="basicForm.registered_capital" placeholder="如：1.44亿" maxlength="32" />
              </el-form-item>
              <el-form-item label="成立时间">
                <el-input v-model="basicForm.founded_year" placeholder="如：1996年" maxlength="16" />
              </el-form-item>
              <el-form-item label="人员规模">
                <el-input v-model="basicForm.staff_size" placeholder="如：220" maxlength="16" />
              </el-form-item>
              <el-form-item label="企业性质">
                <el-radio-group v-model="basicForm.enterprise_nature">
                  <el-radio v-for="n in ENTERPRISE_NATURES" :key="n" :label="n" />
                </el-radio-group>
              </el-form-item>
              <el-form-item label="主要产品或服务">
                <el-input v-model="basicForm.main_products" type="textarea" :rows="3" maxlength="300" show-word-limit
                  placeholder="如：玉米种子选育、加工、销售" />
              </el-form-item>
              <el-form-item label="上年度营业收入">
                <el-input v-model="basicForm.last_year_revenue" placeholder="如：3.61亿" maxlength="32" />
              </el-form-item>
              <el-form-item label="联系人及职务">
                <el-input v-model="basicForm.contact_name" placeholder="联系人及职务（如：王勇，市场部总经理）" maxlength="64" />
              </el-form-item>
              <el-form-item label="手机号码">
                <el-input v-model="basicForm.contact_phone" placeholder="手机号码" maxlength="20" />
              </el-form-item>
            </el-form>
            <el-empty v-if="!isNewEnterprise && !basicForm.enterprise_id"
              description="请选择企业名称，或点击右侧新建按钮" :image-size="60" />
          </el-tab-pane>

          <!-- 需求描述 -->
          <el-tab-pane label="需求描述" name="demand">
            <el-form :model="basicForm" label-width="120px" label-position="left" class="declare-form">
              <el-form-item label="需求名称" required>
                <el-input v-model="basicForm.title" maxlength="80" show-word-limit
                  placeholder="一句话概括（如：耐热高蛋白玉米新品种选育及应用）" />
              </el-form-item>
              <el-form-item label="主要技术难点">
                <el-input v-model="basicForm.tech_difficulties" type="textarea" :rows="5" maxlength="1000" show-word-limit
                  placeholder="具体难题及需求、现有基础和研发能力" />
              </el-form-item>
              <el-form-item label="主要技术指标">
                <el-input v-model="basicForm.tech_indicators" type="textarea" :rows="5" maxlength="1000" show-word-limit
                  placeholder="预期目标与量化指标（如：较对照增产5%以上、含量≥12%）" />
              </el-form-item>
              <el-form-item label="主要研究内容">
                <el-input v-model="basicForm.research_content" type="textarea" :rows="5" maxlength="1000" show-word-limit
                  placeholder="拟开展的研究内容与技术路线" />
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <!-- 合作意向 -->
          <el-tab-pane label="合作意向" name="coop">
            <el-form :model="basicForm" label-width="120px" label-position="left" class="declare-form">
              <el-form-item label="拟短期合作方式">
                <el-tooltip content="拟短期合作方式，可多选" placement="top">
                  <el-checkbox-group v-model="basicForm.short_term_cooperation">
                    <el-checkbox v-for="c in SHORT_TERM_COOPERATION_OPTIONS" :key="c" :label="c" />
                  </el-checkbox-group>
                </el-tooltip>
              </el-form-item>
              <el-form-item label="拟长期合作方式">
                <el-tooltip content="拟长期合作方式，可多选" placement="top">
                  <el-checkbox-group v-model="basicForm.long_term_cooperation">
                    <el-checkbox v-for="c in LONG_TERM_COOPERATION_OPTIONS" :key="c" :label="c" />
                  </el-checkbox-group>
                </el-tooltip>
              </el-form-item>
              <el-form-item label="意向合作专家">
                <el-radio-group v-model="basicForm.expert_intent">
                  <el-radio label="yes">有</el-radio>
                  <el-radio label="no">无</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="basicForm.expert_intent === 'yes'" label="专家及单位">
                <el-input v-model="basicForm.expert_names" type="textarea" :rows="3" maxlength="300" show-word-limit
                  placeholder="如：严建兵、邱法展（华中农业大学）" />
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>

      <template #footer>
        <el-button @click="showBasicForm = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBasic">保存</el-button>
      </template>
    </AppDrawer>

    <!-- ==================== 阶段操作表单 ==================== -->
    <el-dialog v-model="showActionForm" :title="actionMeta ? actionMeta.label : ''" width="560px">
      <!-- 专家论证 -->
      <template v-if="currentAction === 'argument_pass' || currentAction === 'argument_reject'">
        <div class="field-label">论证专家</div>
        <div v-for="(exp, i) in actionForm.argument_experts" :key="i" class="expert-row">
          <el-input v-model="exp.name" placeholder="专家姓名" style="width: 30%" />
          <el-input v-model="exp.org" placeholder="单位" style="width: 34%; margin-left: 2%;" />
          <el-input v-model="exp.title" placeholder="职称/职务" style="width: 28%; margin-left: 2%;" />
          <el-button link type="danger" @click="actionForm.argument_experts.splice(i, 1)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-button size="small" @click="actionForm.argument_experts.push({ name: '', org: '', title: '' })">
          <el-icon><Plus /></el-icon> 添加专家
        </el-button>
        <el-form-item label="论证意见" label-width="90px" style="margin-top: 12px">
          <el-input v-model="actionForm.argument_opinion" type="textarea" :rows="3" placeholder="论证意见" />
        </el-form-item>
        <el-form-item label="论证结论" label-width="90px">
          <el-input v-model="actionForm.argument_result" type="textarea" :rows="2"
            :placeholder="currentAction === 'argument_pass' ? '如：同意发榜' : '如：需求已由企业自行解决'" />
        </el-form-item>
      </template>

      <!-- 发榜公告 -->
      <template v-else-if="currentAction === 'publish'">
        <el-form-item label="悬赏金额(万元)" label-width="120px">
          <el-input-number v-model="actionForm.bounty_amount" :min="0" :precision="2" style="width: 200px" />
        </el-form-item>
        <el-form-item label="揭榜截止日期" label-width="120px" required>
          <el-date-picker v-model="actionForm.deadline_date" type="date" value-format="YYYY-MM-DD" style="width: 200px" />
        </el-form-item>
        <el-form-item label="揭榜条件" label-width="120px">
          <el-input v-model="actionForm.accept_conditions" type="textarea" :rows="3"
            placeholder="如：具有种质资源库的高校或科研院所优先" />
        </el-form-item>
      </template>

      <!-- 定标 -->
      <template v-else-if="currentAction === 'select_bid'">
        <el-form-item label="选择揭榜方" label-width="110px" required>
          <el-radio-group v-model="actionForm.bid_id">
            <el-radio v-for="b in detail.bids" :key="b.id" :value="b.id" style="display: flex; margin-bottom: 6px;">
              {{ b.bidder_name }}（{{ b.bidder_type }}，报价 {{ b.expected_amount }} 万元）
              <el-tag v-if="b.score !== null && b.score !== undefined" size="small" style="margin-left: 6px;">评分 {{ b.score }}</el-tag>
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="评审结论" label-width="110px">
          <el-input v-model="actionForm.review_result" type="textarea" :rows="2" placeholder="评审结论" />
        </el-form-item>
      </template>

      <!-- 任务签订 -->
      <template v-else-if="currentAction === 'sign'">
        <el-form-item label="任务经费(万元)" label-width="110px">
          <el-input-number v-model="actionForm.task_amount" :min="0" :precision="2" style="width: 200px" />
        </el-form-item>
        <el-form-item label="任务期限" label-width="110px">
          <el-input v-model="actionForm.task_duration" placeholder="如：24个月" style="width: 200px" />
        </el-form-item>
        <el-form-item label="签订日期" label-width="110px">
          <el-date-picker v-model="actionForm.task_date" type="date" value-format="YYYY-MM-DD" style="width: 200px" />
        </el-form-item>
        <el-form-item label="任务书备注" label-width="110px">
          <el-input v-model="actionForm.task_notes" type="textarea" :rows="3" placeholder="任务书备注" />
        </el-form-item>
      </template>

      <!-- 绩效评价 -->
      <template v-else-if="currentAction === 'evaluate'">
        <el-form-item label="绩效评分(0-100)" label-width="120px" required>
          <el-input-number v-model="actionForm.eval_score" :min="0" :max="100" style="width: 200px" />
        </el-form-item>
        <el-form-item label="评价等级" label-width="120px" required>
          <el-select v-model="actionForm.eval_level" style="width: 200px">
            <el-option v-for="l in EVAL_LEVELS" :key="l" :label="l" :value="l" />
          </el-select>
        </el-form-item>
        <el-form-item label="评价报告" label-width="120px">
          <el-input v-model="actionForm.eval_report" type="textarea" :rows="4" placeholder="绩效评价报告/成果说明" />
        </el-form-item>
        <el-form-item label="评价日期" label-width="120px">
          <el-date-picker v-model="actionForm.eval_date" type="date" value-format="YYYY-MM-DD" style="width: 200px" />
        </el-form-item>
      </template>

      <!-- 通用文本（驳回/流标/完成/终止/取消） -->
      <template v-else>
        <el-form-item
          v-if="['argument_reject', 'fail_bid', 'complete', 'terminate', 'cancel'].includes(currentAction)"
          :label="currentAction === 'complete' || currentAction === 'terminate' ? '过程备注' :
                  currentAction === 'cancel' ? '取消原因' :
                  currentAction === 'fail_bid' ? '流标原因' : '论证驳回说明'"
          label-width="110px"
        >
          <el-input v-model="actionForm.reason" type="textarea" :rows="3" />
        </el-form-item>
        <el-alert
          v-if="currentAction === 'submit_argument' || currentAction === 'expire'"
          :title="currentAction === 'submit_argument'
            ? '确认将该项目提交专家论证（进入阶段2）？'
            : '确认截止揭榜，进入评审阶段？'"
          type="info" :closable="false" show-icon
        />
      </template>

      <template #footer>
        <el-button @click="showActionForm = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitAction">确认{{ actionMeta ? actionMeta.label : '' }}</el-button>
      </template>
    </el-dialog>

    <!-- ==================== 揭榜申请表单 ==================== -->
    <el-dialog v-model="showBidForm" :title="editingBid ? '编辑揭榜申请 / 评分' : '内部代录揭榜申请'" width="600px">
      <el-form :model="bidForm" label-width="100px">
        <el-form-item label="揭榜方名称" required>
          <el-input v-model="bidForm.bidder_name" />
        </el-form-item>
        <el-form-item label="单位性质">
          <el-select v-model="bidForm.bidder_type" style="width: 100%">
            <el-option v-for="t in BIDDER_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="团队负责人">
          <el-input v-model="bidForm.team_leader" style="width: 46%" />
          <el-input v-model="bidForm.team_leader_phone" placeholder="电话" style="width: 51%; margin-left: 3%;" />
        </el-form-item>
        <el-form-item label="技术方案">
          <el-input v-model="bidForm.tech_solution" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="团队优势">
          <el-input v-model="bidForm.team_advantage" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="报价(万元)">
          <el-input-number v-model="bidForm.expected_amount" :min="0" :precision="2" style="width: 200px" />
        </el-form-item>
        <template v-if="editingBid">
          <el-form-item label="评审评分">
            <el-input-number v-model="bidForm.score" :min="0" :max="100" :precision="1" style="width: 200px" />
          </el-form-item>
          <el-form-item label="评审意见">
            <el-input v-model="bidForm.score_note" type="textarea" :rows="2" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showBidForm = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBid">保存</el-button>
      </template>
    </el-dialog>

    <!-- ==================== 里程碑表单 ==================== -->
    <el-dialog v-model="showMilestoneForm" :title="editingMilestone ? '编辑里程碑' : '新增里程碑'" width="520px">
      <el-form :model="milestoneForm" label-width="100px">
        <el-form-item label="里程碑内容" required>
          <el-input v-model="milestoneForm.content" placeholder="如：完成抗病基因聚合" />
        </el-form-item>
        <el-form-item label="计划完成时间">
          <el-date-picker v-model="milestoneForm.planned_date" type="date" value-format="YYYY-MM-DD" style="width: 200px" />
        </el-form-item>
        <el-form-item label="完成说明">
          <el-input v-model="milestoneForm.result_note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMilestoneForm = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveMilestone">保存</el-button>
      </template>
    </el-dialog>

    <!-- ==================== 时间线记录表单 ==================== -->
    <el-dialog v-model="showTimelineForm" title="添加服务跟踪记录" width="520px">
      <el-form label-width="100px">
        <el-form-item label="记录类型">
          <el-select v-model="timelineForm.record_type" style="width: 200px">
            <el-option label="服务记录" value="service" />
            <el-option label="通知" value="notice" />
          </el-select>
        </el-form-item>
        <el-form-item label="记录内容" required>
          <el-input v-model="timelineForm.content" type="textarea" :rows="4"
            placeholder="如：电话回访企业，确认技术需求补充材料已收到" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTimelineForm = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveTimeline">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Delete, Flag, Document } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import AppDrawer from '@/components/common/AppDrawer.vue'
import { biddingApi } from '@/api/bidding'
import {
  BIDDING_STAGES, STAGE_NAME_MAP, TERMINAL_STAGES, TERMINAL_LABELS,
  STAGE_ACTIONS, STAGE_COLORS, DEMAND_SOURCES, BIDDER_TYPES, EVAL_LEVELS,
  BID_STATUS_LABELS, MILESTONE_STATUS_LABELS, TIMELINE_TYPE_LABELS,
  ENTERPRISE_NATURES, QUALIFICATION_OPTIONS, INDUSTRY_OPTIONS,
  SHORT_TERM_COOPERATION_OPTIONS, LONG_TERM_COOPERATION_OPTIONS,
} from '@/config/biddingStages'

const projects = ref([])
const loading = ref(false)
const dicts = ref({ categories: [], stages: [], staff: [] })
const searchText = ref('')
const filterStage = ref('')
const filterCategory = ref('')
const saving = ref(false)
const route = useRoute()

const allStageOptions = computed(() => [
  ...BIDDING_STAGES,
  ...Object.entries(TERMINAL_LABELS).map(([key, name]) => ({ key, name })),
])

function stageName(key) { return STAGE_NAME_MAP[key] || TERMINAL_LABELS[key] || key }
function stageTagType(key) {
  return TERMINAL_STAGES.includes(key) ? 'danger' : (STAGE_COLORS[key] || 'info')
}
function bidStatusType(s) {
  return { submitted: 'info', reviewing: 'warning', selected: 'success', rejected: 'danger' }[s] || 'info'
}
function timelineType(t) { return { system: 'primary', service: 'success', notice: 'warning' }[t] || 'info' }

async function fetchDicts() {
  const res = await biddingApi.getDicts()
  if (res.code === 0) dicts.value = res.data
}

async function fetchList() {
  loading.value = true
  try {
    const res = await biddingApi.listProjects({
      search: searchText.value || undefined,
      stage: filterStage.value || undefined,
      category: filterCategory.value || undefined,
    })
    if (res.code === 0) projects.value = res.data
  } finally {
    loading.value = false
  }
}

// ==================== 详情 ====================
const showDetail = ref(false)
const detail = ref(null)
const activePanels = ref(['stage1'])
const stepActiveIndex = computed(() => {
  const idx = BIDDING_STAGES.findIndex(s => s.key === detail.value?.current_stage)
  return idx === -1 ? 7 : idx
})
const terminalReason = computed(() => {
  const d = detail.value
  if (!d) return ''
  if (d.current_stage === 'rejected') return d.argument_result || d.argument_opinion || ''
  if (d.current_stage === 'failed') return d.review_result || ''
  return d.process_notes || ''
})

async function openDetail(row) {
  const res = await biddingApi.getProject(row.id)
  if (res.code === 0) {
    detail.value = res.data
    activePanels.value = ['stage1']
    showDetail.value = true
  }
}

function refreshDetail() {
  return biddingApi.getProject(detail.value.id).then(res => {
    if (res.code === 0) detail.value = res.data
  })
}

// ==================== 新建/编辑需求 ====================
const showBasicForm = ref(false)
const declareTab = ref('enterprise')
const editingProject = ref(null)
const basicForm = reactive({})

// ===== 企业档案 =====
const enterprises = ref([])
const enterpriseLoading = ref(false)
const isNewEnterprise = ref(false)   // false=选择已有企业（下拉+带出可编辑）；true=新建企业
const currentEnterprise = computed(() =>
  enterprises.value.find(e => e.id === basicForm.enterprise_id) || null)

async function fetchEnterprises() {
  enterpriseLoading.value = true
  try {
    const res = await biddingApi.listEnterprises()
    if (res.code === 0) enterprises.value = res.data
  } finally {
    enterpriseLoading.value = false
  }
}

function onEnterpriseSelected() {
  // 选择已有企业：回填表单企业字段（提交时仅传 enterprise_id）
  const e = currentEnterprise.value
  if (e) {
    basicForm.org_name = e.org_name
    basicForm.enterprise_address = e.enterprise_address
    basicForm.enterprise_qualifications = [...e.enterprise_qualifications]
    basicForm.industry_code = e.industry_code
    basicForm.registered_capital = e.registered_capital
    basicForm.founded_year = e.founded_year
    basicForm.staff_size = e.staff_size
    basicForm.enterprise_nature = e.enterprise_nature
    basicForm.main_products = e.main_products
    basicForm.last_year_revenue = e.last_year_revenue
    basicForm.contact_name = e.contact_name
    basicForm.contact_phone = e.contact_phone
  }
}

function onDeclareClose(val) {
  // 抽屉关闭（含点击取消/保存后）：重置 tab 与企业模式
  if (!val) {
    declareTab.value = 'enterprise'
    isNewEnterprise.value = false
  }
}

function openCreate() {
  editingProject.value = null
  Object.assign(basicForm, emptyBasicForm())
  declareTab.value = 'enterprise'
  isNewEnterprise.value = false
  showBasicForm.value = true
}

function emptyBasicForm() {
  return {
    title: '',
    // 企业（选择/新建）
    enterprise_id: null, org_name: '',
    enterprise_address: '', enterprise_qualifications: [], industry_code: '',
    registered_capital: '', founded_year: '', staff_size: '', enterprise_nature: '',
    main_products: '', last_year_revenue: '', contact_name: '', contact_phone: '',
    // 需求描述
    tech_difficulties: '', tech_indicators: '', research_content: '',
    // 合作意向
    short_term_cooperation: [], long_term_cooperation: [], expert_intent: 'no', expert_names: '',
  }
}

function openEditBasic() {
  editingProject.value = detail.value
  const d = detail.value
  Object.assign(basicForm, {
    title: d.title,
    enterprise_id: d.enterprise_id || null,
    org_name: d.demander_name || '',
    enterprise_address: d.enterprise_address || '',
    enterprise_qualifications: [...(d.enterprise_qualifications || [])],
    industry_code: d.industry_code || '',
    registered_capital: d.registered_capital || '',
    founded_year: d.founded_year || '',
    staff_size: d.staff_size || '',
    enterprise_nature: d.enterprise_nature || '',
    main_products: d.main_products || '',
    last_year_revenue: d.last_year_revenue || '',
    contact_name: d.demander_contact || '',
    contact_phone: d.demander_phone || '',
    tech_difficulties: d.tech_difficulties || '',
    tech_indicators: d.tech_indicators || '',
    research_content: d.research_content || '',
    short_term_cooperation: [...(d.short_term_cooperation || [])],
    long_term_cooperation: [...(d.long_term_cooperation || [])],
    expert_intent: d.expert_intent || 'no',
    expert_names: d.expert_names || '',
  })
  // 编辑回显：有关联企业档案 → 选择模式（下拉回显）；否则新建模式
  isNewEnterprise.value = !d.enterprise_id
  declareTab.value = 'enterprise'
  showBasicForm.value = true
}

function buildDeclarePayload() {
  // 只提交申报表相关字段（严格按企业需求申报表）
  const payload = {
    title: basicForm.title,
    tech_difficulties: basicForm.tech_difficulties,
    tech_indicators: basicForm.tech_indicators,
    research_content: basicForm.research_content,
    short_term_cooperation: basicForm.short_term_cooperation,
    long_term_cooperation: basicForm.long_term_cooperation,
    expert_intent: basicForm.expert_intent,
    expert_names: basicForm.expert_names,
  }
  // 企业字段：选择模式带 enterprise_id + 可编辑字段（后端更新档案）；新建模式带 org_name + 字段
  Object.assign(payload, {
    enterprise_address: basicForm.enterprise_address,
    enterprise_qualifications: basicForm.enterprise_qualifications,
    industry_code: basicForm.industry_code,
    registered_capital: basicForm.registered_capital,
    founded_year: basicForm.founded_year,
    staff_size: basicForm.staff_size,
    enterprise_nature: basicForm.enterprise_nature,
    main_products: basicForm.main_products,
    last_year_revenue: basicForm.last_year_revenue,
    contact_name: basicForm.contact_name,
    contact_phone: basicForm.contact_phone,
  })
  if (!isNewEnterprise.value && basicForm.enterprise_id) {
    payload.enterprise_id = basicForm.enterprise_id
  } else {
    payload.org_name = basicForm.org_name
  }
  return payload
}

async function saveBasic() {
  if (!basicForm.title.trim()) {
    ElMessage.warning('请填写需求名称')
    return
  }
  if (isNewEnterprise.value && !basicForm.org_name.trim()) {
    ElMessage.warning('请填写企业名称')
    return
  }
  if (!isNewEnterprise.value && !basicForm.enterprise_id) {
    ElMessage.warning('请选择企业名称，或点击右侧按钮新建企业')
    return
  }
  saving.value = true
  try {
    const payload = buildDeclarePayload()
    const res = editingProject.value
      ? await biddingApi.updateProject(editingProject.value.id, payload)
      : await biddingApi.createProject(payload)
    if (res.code === 0) {
      ElMessage.success(res.message)
      showBasicForm.value = false
      fetchList()
      fetchEnterprises()
      if (editingProject.value && detail.value) await refreshDetail()
    } else {
      ElMessage.error(res.message)
    }
  } finally {
    saving.value = false
  }
}

function handleDelete(row) {
  ElMessageBox.confirm(`确认删除榜单「${row.title}」？`, '删除确认', { type: 'warning' })
    .then(async () => {
      const res = await biddingApi.deleteProject(row.id)
      if (res.code === 0) { ElMessage.success('已删除'); fetchList() }
    })
    .catch(() => {})
}

// ==================== 阶段操作 ====================
const showActionForm = ref(false)
const currentAction = ref('')
const actionForm = reactive({})
const actionMeta = computed(() => {
  const acts = STAGE_ACTIONS[detail.value?.current_stage] || []
  return acts.find(a => a.action === currentAction.value)
})

function openAction(action) {
  currentAction.value = action
  Object.assign(actionForm, {
    argument_experts: [], argument_opinion: '', argument_result: '',
    bounty_amount: detail.value?.bounty_amount || 0, deadline_date: '',
    accept_conditions: detail.value?.accept_conditions || '',
    bid_id: detail.value?.selected_bid_id, review_result: '',
    task_amount: detail.value?.task_amount || 0, task_duration: detail.value?.task_duration || '',
    task_date: '', task_notes: detail.value?.task_notes || '',
    eval_score: detail.value?.eval_score, eval_level: detail.value?.eval_level || '',
    eval_report: detail.value?.eval_report || '', eval_date: '',
    process_notes: '', reason: '',
  })
  showActionForm.value = true
}

async function submitAction() {
  saving.value = true
  try {
    const payload = { action: currentAction.value }
    const a = currentAction.value
    if (a === 'argument_pass' || a === 'argument_reject') {
      payload.argument_experts = actionForm.argument_experts
      payload.argument_opinion = actionForm.argument_opinion
      payload.argument_result = actionForm.argument_result
      if (a === 'argument_reject' && !actionForm.argument_result.trim()) {
        ElMessage.warning('请填写论证驳回说明'); saving.value = false; return
      }
    } else if (a === 'publish') {
      Object.assign(payload, {
        bounty_amount: actionForm.bounty_amount, deadline_date: actionForm.deadline_date,
        accept_conditions: actionForm.accept_conditions,
      })
    } else if (a === 'select_bid') {
      payload.bid_id = actionForm.bid_id
      payload.review_result = actionForm.review_result
      if (!payload.bid_id) { ElMessage.warning('请选择揭榜方'); saving.value = false; return }
    } else if (a === 'sign') {
      Object.assign(payload, {
        task_amount: actionForm.task_amount, task_duration: actionForm.task_duration,
        task_date: actionForm.task_date, task_notes: actionForm.task_notes,
      })
    } else if (a === 'evaluate') {
      Object.assign(payload, {
        eval_score: actionForm.eval_score, eval_level: actionForm.eval_level,
        eval_report: actionForm.eval_report, eval_date: actionForm.eval_date,
      })
    } else if (['argument_reject', 'fail_bid', 'complete', 'terminate', 'cancel'].includes(a)) {
      const key = a === 'fail_bid' ? 'review_result'
        : (a === 'argument_reject' ? 'argument_result'
          : (a === 'cancel' ? 'reason' : 'process_notes'))
      payload[key] = actionForm.reason
    }
    const res = await biddingApi.transition(detail.value.id, payload)
    if (res.code === 0) {
      ElMessage.success(res.message)
      showActionForm.value = false
      detail.value = res.data
      fetchList()
    } else {
      ElMessage.error(res.message)
    }
  } finally {
    saving.value = false
  }
}

// ==================== 揭榜申请 ====================
const showBidForm = ref(false)
const editingBid = ref(null)
const bidForm = reactive({})

function openBidForm(row) {
  editingBid.value = row || null
  Object.assign(bidForm, row ? {
    bidder_name: row.bidder_name, bidder_type: row.bidder_type,
    team_leader: row.team_leader, team_leader_phone: row.team_leader_phone,
    tech_solution: row.tech_solution, team_advantage: row.team_advantage,
    expected_amount: row.expected_amount, score: row.score, score_note: row.score_note,
  } : {
    bidder_name: '', bidder_type: '高校', team_leader: '', team_leader_phone: '',
    tech_solution: '', team_advantage: '', expected_amount: 0, score: null, score_note: '',
  })
  showBidForm.value = true
}

async function saveBid() {
  if (!bidForm.bidder_name.trim()) { ElMessage.warning('请填写揭榜方名称'); return }
  saving.value = true
  try {
    const res = editingBid.value
      ? await biddingApi.updateBid(detail.value.id, editingBid.value.id, bidForm)
      : await biddingApi.createBid(detail.value.id, bidForm)
    if (res.code === 0) {
      ElMessage.success(res.message)
      showBidForm.value = false
      await refreshDetail()
    } else {
      ElMessage.error(res.message)
    }
  } finally {
    saving.value = false
  }
}

async function deleteBid(row) {
  await ElMessageBox.confirm(`确认删除「${row.bidder_name}」的揭榜申请？`, '删除确认', { type: 'warning' })
    .then(async () => {
      const res = await biddingApi.deleteBid(detail.value.id, row.id)
      if (res.code === 0) { ElMessage.success('已删除'); await refreshDetail() }
    }).catch(() => {})
}

// ==================== 里程碑 ====================
const showMilestoneForm = ref(false)
const editingMilestone = ref(null)
const milestoneForm = reactive({})

function openMilestoneForm(row) {
  editingMilestone.value = row || null
  Object.assign(milestoneForm, row ? {
    content: row.content, planned_date: row.planned_date, result_note: row.result_note,
  } : { content: '', planned_date: '', result_note: '' })
  showMilestoneForm.value = true
}

async function saveMilestone() {
  if (!milestoneForm.content.trim()) { ElMessage.warning('请填写里程碑内容'); return }
  saving.value = true
  try {
    const res = editingMilestone.value
      ? await biddingApi.updateMilestone(detail.value.id, editingMilestone.value.id, milestoneForm)
      : await biddingApi.createMilestone(detail.value.id, milestoneForm)
    if (res.code === 0) { ElMessage.success(res.message); showMilestoneForm.value = false; await refreshDetail() }
  } finally {
    saving.value = false
  }
}

async function updateMilestoneStatus(row, status) {
  const res = await biddingApi.updateMilestoneStatus(detail.value.id, row.id, { status })
  if (res.code === 0) { ElMessage.success('已更新'); await refreshDetail() }
}

async function deleteMilestone(row) {
  await ElMessageBox.confirm(`确认删除里程碑「${row.content}」？`, '删除确认', { type: 'warning' })
    .then(async () => {
      const res = await biddingApi.deleteMilestone(detail.value.id, row.id)
      if (res.code === 0) { ElMessage.success('已删除'); await refreshDetail() }
    }).catch(() => {})
}

// ==================== 时间线 ====================
const showTimelineForm = ref(false)
const timelineForm = reactive({})

function openTimelineForm() {
  Object.assign(timelineForm, { record_type: 'service', content: '' })
  showTimelineForm.value = true
}

async function saveTimeline() {
  if (!timelineForm.content.trim()) { ElMessage.warning('请填写记录内容'); return }
  saving.value = true
  try {
    const res = await biddingApi.addTimeline(detail.value.id, timelineForm)
    if (res.code === 0) { ElMessage.success('已记录'); showTimelineForm.value = false; await refreshDetail() }
  } finally {
    saving.value = false
  }
}

async function deleteTimeline(t) {
  const res = await biddingApi.deleteTimeline(detail.value.id, t.id)
  if (res.code === 0) { ElMessage.success('已删除'); await refreshDetail() }
}

onMounted(async () => {
  await fetchDicts()
  fetchEnterprises()
  // 看板跳转联动：?stage=xxx 预置阶段筛选，?focus=xxx 自动打开详情
  if (route.query.stage) filterStage.value = route.query.stage
  await fetchList()
  if (route.query.focus) {
    const target = projects.value.find(p => String(p.id) === String(route.query.focus))
    if (target) openDetail(target)
  }
})
</script>

<style scoped>
.bidding-page {
  min-height: 100vh;
  background: var(--bg-light);
}
.page-body {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}
.content-card {
  background: var(--bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 20px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.search-input { width: 260px; }
.toolbar-spacer { flex: 1; }

/* 详情 */
.detail-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.detail-cat { color: var(--text-secondary); }
.detail-demander { color: var(--text-secondary); }
.steps-bar { margin: 8px 0 20px; }
.terminal-alert { margin-bottom: 16px; }
.action-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f0f7ff;
  border: 1px solid #d6e4ff;
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
}
.action-label { font-weight: 600; color: var(--primary-color); }

.stage-cards { margin-bottom: 20px; }
.field-block { margin: 12px 0; }
.field-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.field-text {
  white-space: pre-wrap;
  line-height: 1.8;
  background: #f8f9fb;
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}
.sub-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.sub-title { font-weight: 600; }

/* 时间线 */
.timeline-block { margin-top: 8px; }
.timeline-list { padding-left: 4px; }
.timeline-item { position: relative; }
.timeline-stage { margin-left: 8px; color: var(--text-secondary); font-size: 12px; }
.timeline-content {
  margin: 6px 0;
  white-space: pre-wrap;
  line-height: 1.7;
}
.expert-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

/* 企业需求申报：企业选择行（下拉 + 新建 icon）+ 表单 */
.enterprise-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
}
.enterprise-select { flex: 1; }
.enterprise-new-btn { flex-shrink: 0; }
.enterprise-form { margin-top: 2px; }
</style>
