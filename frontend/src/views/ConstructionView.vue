<!-- ConstructionView.vue: 在建项目库管理 — CRUD + 工作路径 + 调度问题 + 批量操作 + 导入导出 + 打印 -->
<template>
  <div class="construction-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 工具栏 -->
        <div class="toolbar">
          <el-input
            v-model="searchText"
            placeholder="搜索项目名称、建设内容..."
            :prefix-icon="Search"
            clearable
            class="search-input"
            @input="handleSearch"
          />
          <el-input
            v-model="filterConstructionUnit"
            placeholder="建设单位"
            clearable
            style="width: 180px;"
            @input="handleSearch"
          />
          <el-select
            v-model="filterDispatchStatus"
            placeholder="调度状态"
            clearable
            style="width: 140px;"
            @change="currentPage = 1; fetchData()"
          >
            <el-option
              v-for="d in dicts.dispatch_statuses"
              :key="d.code"
              :label="d.name"
              :value="d.code"
            />
          </el-select>
          <el-select
            v-model="filterProjectType"
            placeholder="项目类型"
            clearable
            style="width: 140px;"
            @change="currentPage = 1; fetchData()"
          >
            <el-option
              v-for="d in dicts.project_types"
              :key="d.code"
              :label="d.name"
              :value="d.code"
            />
          </el-select>
          <el-select
            v-model="filterResponsibleUnit"
            placeholder="责任单位"
            clearable
            style="width: 160px;"
            @change="currentPage = 1; fetchData()"
          >
            <el-option
              v-for="d in dicts.organizations"
              :key="d.code"
              :label="d.name"
              :value="d.code"
            />
          </el-select>
          <el-radio-group v-model="recentProgressDays" size="small" @change="currentPage = 1; fetchData()">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="7">7日内更新</el-radio-button>
            <el-radio-button value="15">15日内更新</el-radio-button>
          </el-radio-group>
          <div class="toolbar-spacer" />
          <el-dropdown
            v-if="businessAuth.hasPermission('construction', 'import')"
            trigger="click"
            @command="handleImportCmd"
          >
            <el-button type="success" plain>
              <el-icon><Upload /></el-icon> 导入项目
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="download-template">
                  <el-icon><Download /></el-icon> 下载模板
                </el-dropdown-item>
                <el-dropdown-item command="import-data">
                  <el-icon><Upload /></el-icon> 导入数据
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button
            v-if="businessAuth.hasPermission('construction', 'add')"
            type="primary"
            @click="openCreate"
          >
            <el-icon><Plus /></el-icon> 添加在建项目
          </el-button>
          <el-dropdown
            v-if="selectedIds.length > 0"
            trigger="hover"
            @command="handleBatchCmd"
          >
            <el-button type="primary" plain>
              <el-icon><Operation /></el-icon> 批量操作 ({{ selectedIds.length }})
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="export-print">
                  <el-icon><Finished /></el-icon> 导出并打印
                </el-dropdown-item>
                <el-dropdown-item
                  v-if="businessAuth.hasPermission('construction', 'batch_delete')"
                  command="batch-delete"
                  divided
                  style="color: #f56c6c;"
                >
                  <el-icon><Delete /></el-icon> 批量删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <!-- 表格 -->
        <el-table
          ref="tableRef"
          :data="pagedProjects"
          stripe
          row-key="id"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          @expand-change="onExpandChange"
          empty-text="暂无在建项目数据"
          style="width: 100%"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column type="expand" width="42">
            <template #default="{ row }">
              <div class="expand-content" :style="{ width: expandWidth + 'px', maxWidth: expandWidth + 'px' }">
                <!-- 顶部切换栏 -->
                <div class="expand-toggle-bar expand-toggle-top">
                  <el-button size="small" link type="primary" @click="toggleCardExpand(row.id)">
                    <el-icon><ArrowUp v-if="expandedCardIds.has(row.id)" /><ArrowDown v-else /></el-icon>
                    {{ expandedCardIds.has(row.id) ? '收起基础信息' : '展开基础信息' }}
                  </el-button>
                </div>

                <!-- 基础信息 (可折叠) -->
                <template v-if="expandedCardIds.has(row.id)">
                  <div class="expand-block">
                    <div class="expand-block-title">基础信息</div>
                    <div class="expand-grid">
                      <div class="expand-item"><label>项目名称</label><span>{{ dn(row.project_name) }}</span></div>
                      <div class="expand-item"><label>建设单位</label><span>{{ dn(row.construction_unit) || '-' }}</span></div>
                      <div class="expand-item"><label>项目类型</label><span>{{ row.project_type_name || row.project_type_code }}</span></div>
                      <div class="expand-item"><label>调度状态</label><span>{{ row.dispatch_status_name || row.dispatch_status_code }}</span></div>
                      <div class="expand-item"><label>责任单位</label><span>{{ dn(row.responsible_unit_name || row.responsible_unit_code) || '-' }}</span></div>
                      <div class="expand-item"><label>责任人</label><span>{{ dn(row.responsible_person) || '-' }}</span></div>
                      <div class="expand-item"><label>联系电话</label><span>{{ dp(row.responsible_person_phone) || '-' }}</span></div>
                    </div>
                  </div>
                  <div class="expand-block" v-if="row.construction_content">
                    <div class="expand-block-title">建设内容</div>
                    <p class="expand-text-block">{{ dc(row.construction_content) }}</p>
                  </div>
                </template>

                <!-- 工作路径图 — 时间轴 (始终可见) -->
                <div class="expand-block" v-if="row.work_roadmap_items && row.work_roadmap_items.length > 0">
                  <div class="expand-block-title">工作路径图</div>
                  <div class="timeline">
                    <div
                      v-for="(item, i) in row.work_roadmap_items"
                      :key="i"
                      class="timeline-item"
                      :class="{ 'is-delayed': item.is_delayed, 'is-cancelled': item.status === 'cancelled', 'is-completed': item.status === 'completed' }"
                    >
                      <div class="timeline-dot"></div>
                      <div class="timeline-body">
                        <div class="timeline-row">
                          <span class="timeline-index">{{ i + 1 }}</span>
                          <span class="timeline-content">{{ dc(item.content) }}</span>
                          <span class="timeline-date">{{ item.planned_date || '暂未明确' }}</span>
                          <span class="timeline-status">{{ roadmapStatusLabel(item) }}</span>
                        </div>
                        <div class="timeline-extra" v-if="item.actual_date || item.is_delayed || item.status === 'cancelled'">
                          <span v-if="item.actual_date" class="timeline-actual">实际：{{ item.actual_date }}</span>
                          <span v-if="item.is_delayed && item.delay_reason" class="timeline-reason">延期：{{ dc(item.delay_reason) }}</span>
                          <span v-if="item.status === 'cancelled' && item.cancel_reason" class="timeline-reason cancel">作废：{{ dc(item.cancel_reason) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 工作进展 -->
                <div class="expand-block" v-if="row.work_progresses && row.work_progresses.length > 0">
                  <div class="expand-block-title">工作进展</div>
                  <div class="demand-summary-card">
                    <div class="demand-summary-text">
                      共 <strong>{{ row.work_progresses.length }}</strong> 条进展记录
                    </div>
                    <el-button size="small" link type="primary" @click="toggleProgressExpand(row.id)">
                      <el-icon><ArrowUp v-if="expandedProgressIds.has(row.id)" /><ArrowDown v-else /></el-icon>
                      {{ expandedProgressIds.has(row.id) ? '收起进展明细' : '展开进展明细' }}
                    </el-button>
                  </div>
                  <div class="progress-list" v-if="expandedProgressIds.has(row.id)">
                    <div v-for="(pg, i) in row.work_progresses" :key="i" class="progress-card">
                      <div class="progress-card-header">
                        <span class="progress-index">{{ i + 1 }}</span>
                        <span class="progress-date-range">{{ pg.start_date }} ~ {{ pg.end_date }}</span>
                      </div>
                      <p class="progress-content-text">{{ dc(pg.content) }}</p>
                    </div>
                  </div>
                </div>

                <!-- 存在问题 -->
                <div class="expand-block" v-if="row.issues && row.issues.length > 0">
                  <div class="expand-block-title">存在问题</div>
                  <div class="demand-summary-card">
                    <div class="demand-summary-text">
                      共 <strong>{{ row.issues.length }}</strong> 条问题
                      <template v-if="pendingIssueCount(row) > 0">
                        ，<span class="text-warning">{{ pendingIssueCount(row) }} 条待解决</span>
                      </template>
                    </div>
                    <el-button size="small" link type="primary" @click="toggleIssueExpand(row.id)">
                      <el-icon><ArrowUp v-if="expandedIssueIds.has(row.id)" /><ArrowDown v-else /></el-icon>
                      {{ expandedIssueIds.has(row.id) ? '收起问题明细' : '展开问题明细' }}
                    </el-button>
                  </div>
                  <div class="issue-list" v-if="expandedIssueIds.has(row.id)">
                    <div v-for="(iss, i) in row.issues" :key="i" class="issue-card" :class="{ 'is-resolved': iss.resolution_status_code === 'resolved' }">
                      <div class="issue-card-header">
                        <span class="issue-index">{{ i + 1 }}</span>
                        <span class="issue-type-tag">{{ iss.issue_type_name || iss.issue_type_code || '问题' }}</span>
                        <span class="issue-status-tag" :class="iss.resolution_status_code">{{ iss.resolution_status_name || iss.resolution_status_code }}</span>
                        <span v-if="iss.main_department_name" class="issue-dept">{{ iss.main_department_name }}</span>
                      </div>
                      <p class="issue-desc">{{ dc(iss.issue_description) }}</p>
                      <p v-if="iss.resolution_note" class="issue-resolution">措施: {{ dc(iss.resolution_note) }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="order_no" label="序号" width="60" align="center" />
          <el-table-column label="在建项目名称" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">{{ dn(row.project_name) }}</template>
          </el-table-column>
          <el-table-column label="项目类型" width="110">
            <template #default="{ row }">
              <span class="project-type-tag">{{ row.project_type_name || row.project_type_code }}</span>
            </template>
          </el-table-column>
          <el-table-column label="建设单位" width="130" show-overflow-tooltip>
            <template #default="{ row }">{{ dn(row.construction_unit) }}</template>
          </el-table-column>
          <el-table-column label="建设内容" min-width="160">
            <template #default="{ row }">
              <el-tooltip :content="businessAuth.isVisitor ? '' : row.construction_content" placement="top" :show-after="300" popper-class="content-tooltip">
                <span class="content-preview">{{ dc(truncate(row.construction_content, 40)) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="调度状态" width="95" align="center">
            <template #default="{ row }">
              <el-tag
                effect="dark"
                size="small"
                :color="dispatchStatusColor(row.dispatch_status_code)"
                style="border: none; color: #fff;"
              >
                {{ row.dispatch_status_name || row.dispatch_status_code }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="责任单位" width="120" show-overflow-tooltip>
            <template #default="{ row }">
              {{ dn(row.responsible_unit_name || row.responsible_unit_code) || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="责任人" width="70" align="center">
            <template #default="{ row }">{{ dn(row.responsible_person) }}</template>
          </el-table-column>
          <el-table-column label="建设地点" width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ dn(row.construction_location) || '-' }}</template>
          </el-table-column>
          <el-table-column label="开工时间" width="110" align="center">
            <template #default="{ row }">{{ row.start_date || '-' }}</template>
          </el-table-column>
          <el-table-column label="完工时间" width="110" align="center">
            <template #default="{ row }">{{ row.end_date || '-' }}</template>
          </el-table-column>
          <el-table-column label="资金来源" width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ dn(row.funding_source) || '-' }}</template>
          </el-table-column>
          <el-table-column label="五化平台" width="80" align="center">
            <template #default="{ row }">{{ row.wuhua_platform || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <div class="action-cell">
                <el-button
                  v-if="businessAuth.hasPermission('construction', 'edit')"
                  size="small"
                  link
                  type="success"
                  @click="openEdit(row)"
                >编辑</el-button>
                <el-button
                  size="small"
                  link
                  type="warning"
                  @click="handleProgress(row)"
                >进展</el-button>
                <el-dropdown trigger="click" @command="(cmd) => handleRowCmd(cmd, row)">
                  <el-button size="small" link type="info" class="more-btn">
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="view">
                        <el-icon><View /></el-icon> 项目详情
                      </el-dropdown-item>
                      <el-dropdown-item
                        v-if="businessAuth.hasPermission('construction', 'delete')"
                        command="delete"
                        style="color: #f56c6c;"
                      >
                        <el-icon><Delete /></el-icon> 删除
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[5, 10, 20, 50]"
            :total="projects.length"
            layout="total, sizes, prev, pager, next"
            background
            small
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
          <el-checkbox v-model="showAll" class="show-all-check" @change="handleShowAllChange">
            展示全部
          </el-checkbox>
        </div>
      </div>
    </div>

    <!-- 编辑抽屉 -->
    <el-drawer
      v-model="editDrawerVisible"
      direction="rtl"
      size="780px"
      @closed="resetForm"
    >
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">
            <el-icon><Edit /></el-icon>
            {{ editMode === 'create' ? '新建在建项目' : '编辑在建项目' }}
          </span>
        </div>
      </template>
      <div class="drawer-form">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" label-position="right">
          <!-- 基础信息 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><InfoFilled /></el-icon></span>
            <span class="section-title">基础信息</span>
          </div>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="顺序号">
                <el-input-number
                  v-model="form.order_no"
                  :min="0"
                  :max="9999"
                  controls-position="right"
                  style="width: 100%;"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="项目类型" prop="project_type_code">
                <el-select v-model="form.project_type_code" placeholder="请选择项目类型" style="width: 100%;">
                  <el-option
                    v-for="d in dicts.project_types"
                    :key="d.code"
                    :label="d.name"
                    :value="d.code"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="项目名称" prop="project_name">
            <el-input v-model="form.project_name" placeholder="请输入项目名称" maxlength="255" show-word-limit />
          </el-form-item>
          <el-form-item label="调度状态">
            <el-select v-model="form.dispatch_status_code" placeholder="请选择调度状态" style="width: 100%;">
              <el-option
                v-for="d in dicts.dispatch_statuses"
                :key="d.code"
                :label="d.name"
                :value="d.code"
              />
            </el-select>
          </el-form-item>

          <!-- 建设内容 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><Document /></el-icon></span>
            <span class="section-title">建设内容</span>
          </div>
          <el-form-item label="建设内容">
            <el-input
              v-model="form.construction_content"
              type="textarea"
              :rows="6"
              placeholder="请输入建设内容..."
              maxlength="5000"
              show-word-limit
            />
          </el-form-item>

          <!-- 项目信息 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><InfoFilled /></el-icon></span>
            <span class="section-title">项目信息</span>
          </div>
          <el-form-item label="建设地点">
            <el-input v-model="form.construction_location" placeholder="请输入建设地点" maxlength="255" />
          </el-form-item>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="开工时间">
                <el-date-picker
                  v-model="form.start_date"
                  type="date"
                  placeholder="选择开工日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width:100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="完工时间">
                <el-date-picker
                  v-model="form.end_date"
                  type="date"
                  placeholder="选择完工日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width:100%"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="资金来源">
                <el-input v-model="form.funding_source" placeholder="请输入资金来源" maxlength="255" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="五化平台">
                <el-select v-model="form.wuhua_platform" placeholder="请选择" style="width: 100%;">
                  <el-option label="是" value="是" />
                  <el-option label="否" value="否" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 工作路径图 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><Guide /></el-icon></span>
            <span class="section-title">工作路径图</span>
          </div>
          <el-form-item label="工作路径图">
            <div class="roadmap-list">
              <div
                v-for="(item, idx) in form.work_roadmap_items"
                :key="idx"
                class="roadmap-card"
                :class="{ 'roadmap-completed': item.status === 'completed', 'roadmap-cancelled': item.status === 'cancelled' }"
              >
                <div class="roadmap-row">
                  <div class="roadmap-main">
                    <div class="roadmap-content">
                      <span class="roadmap-index">{{ idx + 1 }}</span>
                      <el-input
                        v-model="item.content"
                        placeholder="请输入工作路径内容，如：项目签约2025年07月"
                        maxlength="500"
                        style="flex:1;"
                      />
                    </div>
                    <div class="roadmap-dates">
                      <div class="date-group">
                        <label>预计完成日期</label>
                        <el-date-picker
                          v-model="item.planned_date"
                          type="date"
                          placeholder="选择日期（暂未明确）"
                          value-format="YYYY-MM-DD"
                          style="width:170px;"
                        />
                      </div>
                      <div class="date-group" v-if="item.status === 'completed'">
                        <label>实际完成日期</label>
                        <el-date-picker
                          v-model="item.actual_date"
                          type="date"
                          placeholder="实际完成日"
                          value-format="YYYY-MM-DD"
                          style="width:170px;"
                        />
                      </div>
                    </div>
                  </div>
                  <div class="roadmap-meta">
                    <el-tag
                      v-if="item.status === 'completed'"
                      type="success"
                      size="small"
                      effect="dark"
                    >已完成</el-tag>
                    <el-tag
                      v-else-if="item.status === 'cancelled'"
                      type="info"
                      size="small"
                      effect="dark"
                    >已作废</el-tag>
                    <el-tag
                      v-else
                      :type="item.is_delayed ? 'warning' : ''"
                      size="small"
                      effect="dark"
                    >
                      待完成<template v-if="item.is_delayed">（已延期）</template>
                    </el-tag>
                    <span v-if="item.delay_reason" class="roadmap-reason">延期原因：{{ dc(item.delay_reason) }}</span>
                    <span v-if="item.cancel_reason" class="roadmap-reason cancel">作废原因：{{ dc(item.cancel_reason) }}</span>
                  </div>
                  <div class="roadmap-actions" v-if="item.status === 'pending'">
                    <el-button size="small" type="success" plain @click="handleRoadmapComplete(item)">
                      <el-icon><Check /></el-icon> 完成
                    </el-button>
                    <el-button size="small" type="warning" plain @click="handleRoadmapDelay(item)">
                      <el-icon><Clock /></el-icon> 延期
                    </el-button>
                    <el-button size="small" type="danger" plain @click="handleRoadmapCancel(item)">
                      <el-icon><Close /></el-icon> 作废
                    </el-button>
                  </div>
                  <el-button
                    size="small"
                    type="danger"
                    circle
                    :icon="Delete"
                    class="roadmap-delete-btn"
                    @click="removeRoadmapItem(idx)"
                  />
                </div>
              </div>
              <el-button
                type="primary"
                plain
                style="width: 100%; margin-top: 4px;"
                @click="addRoadmapItem"
              >
                <el-icon><Plus /></el-icon> 添加工作路径节点
              </el-button>
            </div>
          </el-form-item>

          <!-- 单位信息 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><OfficeBuilding /></el-icon></span>
            <span class="section-title">单位信息</span>
          </div>
          <el-form-item label="建设单位">
            <el-input v-model="form.construction_unit" placeholder="请输入建设单位" maxlength="255" />
          </el-form-item>
          <el-form-item label="责任单位">
            <el-select v-model="form.responsible_unit_code" placeholder="请选择责任单位" clearable style="width: 100%;">
              <el-option
                v-for="d in dicts.organizations"
                :key="d.code"
                :label="d.name"
                :value="d.code"
              />
            </el-select>
          </el-form-item>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="责任人">
                <el-input v-model="form.responsible_person" placeholder="请输入责任人" maxlength="64" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="联系电话">
                <el-input v-model="form.responsible_person_phone" placeholder="联系电话" maxlength="32" />
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 专班负责人 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><User /></el-icon></span>
            <span class="section-title">专班负责人</span>
          </div>
          <el-form-item label="专班负责人">
            <el-select v-model="form.team_leader_ids" multiple placeholder="请选择专班负责人" style="width: 100%;">
              <el-option v-for="s in dicts.staff" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </el-form-item>

          <!-- 存在问题 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><WarningFilled /></el-icon></span>
            <span class="section-title">存在问题</span>
            <el-button size="small" type="primary" link @click="addIssue" style="margin-left: auto;">
              <el-icon><Plus /></el-icon>添加问题
            </el-button>
          </div>
          <div v-if="form.issues.length === 0" class="empty-hint">暂无调度问题</div>
          <div v-for="(iss, i) in form.issues" :key="i" class="issue-edit-card">
            <div class="issue-edit-card-header">
              <span class="issue-edit-index">问题 {{ i + 1 }}</span>
              <el-button size="small" type="danger" link @click="form.issues.splice(i, 1)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="问题类型" label-width="80px">
                  <el-select v-model="iss.issue_type_code" placeholder="选择类型" clearable style="width:100%">
                    <el-option v-for="d in dicts.issue_types" :key="d.code" :label="d.name" :value="d.code" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="解决状态" label-width="80px">
                  <el-select v-model="iss.resolution_status_code" placeholder="选择状态" style="width:100%">
                    <el-option v-for="d in dicts.resolution_statuses" :key="d.code" :label="d.name" :value="d.code" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="问题描述" label-width="80px">
              <el-input v-model="iss.issue_description" placeholder="请输入问题描述" type="textarea" :rows="2" maxlength="500" show-word-limit />
            </el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="责任部门" label-width="80px">
                  <el-select v-model="iss.main_department_code" placeholder="选择部门" clearable style="width:100%">
                    <el-option v-for="d in dicts.organizations" :key="d.code" :label="d.name" :value="d.code" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="解决措施" label-width="80px">
                  <el-input v-model="iss.resolution_note" placeholder="解决措施" maxlength="300" />
                </el-form-item>
              </el-col>
            </el-row>
          </div>

          <div class="drawer-footer">
            <el-button @click="editDrawerVisible = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">
              {{ editMode === 'create' ? '创建' : '保存' }}
            </el-button>
          </div>
        </el-form>
      </div>
    </el-drawer>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailVisible"
      direction="rtl"
      size="780px"
      @closed="detailProject = null"
    >
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">
            <el-icon><View /></el-icon>
            {{ detailProject?.project_name || '项目详情' }}
          </span>
        </div>
      </template>
      <template v-if="detailProject">
        <el-descriptions :column="2" border size="small" class="detail-desc">
          <el-descriptions-item label="序号">{{ detailProject.order_no }}</el-descriptions-item>
          <el-descriptions-item label="项目类型">
            <span class="project-type-tag">{{ detailProject.project_type_name || detailProject.project_type_code }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="调度状态">
            <el-tag effect="dark" size="small" :color="dispatchStatusColor(detailProject.dispatch_status_code)" style="border:none;color:#fff;">{{ detailProject.dispatch_status_name || detailProject.dispatch_status_code }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="建设单位">{{ dn(detailProject.construction_unit) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="责任单位">{{ dn(detailProject.responsible_unit_name || detailProject.responsible_unit_code) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="责任人">{{ dn(detailProject.responsible_person) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ dp(detailProject.responsible_person_phone) || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-section" v-if="detailProject.construction_content">
          <h4>建设内容</h4>
          <p>{{ dc(detailProject.construction_content) }}</p>
        </div>
        <div class="detail-section" v-if="detailProject.work_roadmap_items && detailProject.work_roadmap_items.length > 0">
          <h4>工作路径图 ({{ detailProject.work_roadmap_items.length }}条)</h4>
          <div v-for="(wri, i) in detailProject.work_roadmap_items" :key="i" class="detail-sub-item">
            <div class="roadmap-detail-header">
              <span class="sub-index">{{ i + 1 }}.</span>
              <span class="sub-text">{{ dc(wri.content) }}</span>
              <el-tag
                v-if="wri.status === 'completed'"
                type="success"
                size="small"
                effect="dark"
                style="margin-left:8px;"
              >已完成</el-tag>
              <el-tag
                v-else-if="wri.status === 'cancelled'"
                type="info"
                size="small"
                effect="dark"
                style="margin-left:8px;"
              >已作废</el-tag>
              <el-tag
                v-else
                :type="wri.is_delayed ? 'warning' : ''"
                size="small"
                effect="dark"
                style="margin-left:8px;"
              >
                待完成<template v-if="wri.is_delayed">（已延期）</template>
              </el-tag>
            </div>
            <div class="roadmap-detail-dates" v-if="wri.planned_date || wri.actual_date">
              <span v-if="wri.planned_date">预计：{{ wri.planned_date }}</span>
              <span v-if="wri.actual_date" style="margin-left:12px;">实际：{{ wri.actual_date }}</span>
              <span v-if="!wri.planned_date" style="color:#909399;">预计：暂未明确</span>
            </div>
            <p v-if="wri.delay_reason" style="color:#e6a23c;">延期原因：{{ dc(wri.delay_reason) }}</p>
            <p v-if="wri.cancel_reason" style="color:#f56c6c;">作废原因：{{ dc(wri.cancel_reason) }}</p>
          </div>
        </div>
        <!-- 工作进展 -->
        <div class="detail-section" v-if="detailProject.work_progresses && detailProject.work_progresses.length > 0">
          <h4>工作进展 ({{ detailProject.work_progresses.length }}条)</h4>
          <div v-for="(wp, i) in detailProject.work_progresses" :key="i" class="detail-sub-item">
            <span class="sub-date">{{ wp.start_date }} ~ {{ wp.end_date }}</span>
            <p>{{ dc(wp.content) }}</p>
          </div>
        </div>
        <!-- 存在问题 -->
        <div class="detail-section" v-if="detailProject.issues && detailProject.issues.length > 0">
          <h4>存在问题 ({{ detailProject.issues.length }}条)</h4>
          <div v-for="(iss, i) in detailProject.issues" :key="i" class="detail-sub-item">
            <el-tag size="small" effect="plain">{{ iss.issue_type_name || iss.issue_type_code }}</el-tag>
            <el-tag size="small" effect="dark" :color="resolutionStatusColor(iss.resolution_status_code)" style="margin-left: 8px; border: none; color: #fff;">{{ iss.resolution_status_name || iss.resolution_status_code }}</el-tag>
            <p v-if="iss.issue_description" style="margin-top: 6px;">{{ dc(iss.issue_description) }}</p>
            <p v-if="iss.resolution_note" style="color: #909399; font-size: 12px;">解决措施：{{ dc(iss.resolution_note) }}</p>
          </div>
        </div>
      </template>
    </el-drawer>

    <!-- 导入对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入在建项目"
      width="900px"
      :close-on-click-modal="false"
      @close="resetImport"
    >
      <!-- Step 1: 选择文件 -->
      <div v-if="importStep === 'select'">
        <el-alert
          title="操作说明"
          type="info"
          :closable="false"
          style="margin-bottom: 16px;"
        >
          <p style="margin: 2px 0; font-size: 13px;">
            1. 首次使用请先<strong>下载模板</strong>，按模板格式填写数据<br />
            2. 工作路径、工作进展、调度问题列使用<strong>分号（;）分隔</strong>多条记录，<strong>竖线（|）分隔</strong>字段<br />
            3. 上传填写好的 Excel 文件，预览无误后执行导入
          </p>
        </el-alert>
        <el-upload
          ref="importUploadRef"
          :auto-upload="false"
          :on-change="handleImportFile"
          :file-list="importFileList"
          :limit="1"
          accept=".xlsx"
          drag
        >
          <el-icon style="font-size: 48px; color: #c0c4cc;"><UploadFilled /></el-icon>
          <div style="margin-top: 8px; color: #606266;">
            将 Excel 文件拖到此处，或<em style="color: #409eff;">点击上传</em>
          </div>
          <template #tip>
            <div style="margin-top: 6px; font-size: 12px; color: #909399;">
              仅支持 .xlsx 格式，请使用下载的模板填写数据
            </div>
          </template>
        </el-upload>
      </div>

      <!-- Step 2: 预览 -->
      <div v-else>
        <div class="import-summary">
          <el-tag type="success" effect="plain">有效：{{ importValidCount }} 行</el-tag>
          <el-tag v-if="importErrorCount > 0" type="danger" effect="plain" style="margin-left: 8px;">错误：{{ importErrorCount }} 行</el-tag>
          <span style="margin-left: 12px; font-size: 12px; color: #909399;">共 {{ importRows.length }} 行</span>
        </div>
        <el-table
          :data="importRows"
          stripe
          max-height="400"
          :row-class-name="importRowClass"
          style="margin-top: 12px;"
        >
          <el-table-column type="index" label="#" width="40" />
          <el-table-column prop="data.project_name" label="项目名称" min-width="140" show-overflow-tooltip />
          <el-table-column prop="data.project_type_code" label="项目类型" width="100" />
          <el-table-column prop="data.dispatch_status_code" label="调度状态" width="90" />
          <el-table-column label="工作路径" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.parsed.roadmap_count > 0 ? 'success' : 'info'" size="small" effect="plain">
                {{ row.parsed.roadmap_count }} 条
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="工作进展" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.parsed.progress_count > 0 ? '' : 'info'" size="small" effect="plain">
                {{ row.parsed.progress_count }} 条
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="调度问题" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.parsed.issue_count > 0 ? 'warning' : 'info'" size="small" effect="plain">
                {{ row.parsed.issue_count }} 条
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="错误" min-width="180">
            <template #default="{ row }">
              <div v-if="row.errors && row.errors.length > 0" class="import-errors">
                <span v-for="(e, i) in row.errors" :key="i" class="import-error-item">{{ e }}</span>
              </div>
              <span v-else style="color: #67c23a;">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="60" align="center">
            <template #default="{ $index }">
              <el-button size="small" type="danger" link @click="removeImportRow($index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button v-if="importStep === 'preview'" @click="importStep = 'select'; importFileList = []; importRows = []; importHeaders = []">返回</el-button>
        <el-button
          v-if="importStep === 'preview'"
          type="primary"
          :loading="importing"
          :disabled="importValidCount === 0"
          @click="handleImportExecute"
        >
          执行导入（{{ importValidCount }} 行）
        </el-button>
      </template>
    </el-dialog>

    <!-- 进展抽屉 -->
    <ProgressTimelineDrawer
      v-model="progressDrawerVisible"
      :project-id="progressProjectId"
      :project-name="progressProjectName"
    />

    <!-- 打印/导出弹窗 -->
    <SimplePrintExportDialog
      v-model="printExportDialogVisible"
      entity-type="construction"
      :project-ids="selectedIds"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, MoreFilled, View, Delete,
  InfoFilled, Document, OfficeBuilding, Guide,
  Check, Clock, Close, Edit,
  Upload, UploadFilled, Download, User,
  ArrowUp, ArrowDown, Operation, Printer, Finished,
  WarningFilled
} from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import ProgressTimelineDrawer from '@/components/investment/ProgressTimelineDrawer.vue'
import SimplePrintExportDialog from '@/components/common/SimplePrintExportDialog.vue'
import {
  getDicts, getProjects, createProject, updateProject,
  getProject, deleteProject, getMaxOrderNo
} from '@/api/construction'
import {
  downloadTemplate, previewImport, executeImport
} from '@/api/construction_import'
import { downloadConstructionExcel, getConstructionExportTemplates } from '@/api/construction_export'
// import { getConstructionPrintTemplates, downloadConstructionPrintExcel } from '@/api/construction_print'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import { maskName, maskContent, maskPhone } from '@/utils/mask'

const businessAuth = useBusinessAuthStore()

function dn(v) { return businessAuth.isVisitor ? maskName(v) : (v || '') }
function dc(v) { return businessAuth.isVisitor ? maskContent(v) : (v || '') }
function dp(v) { return businessAuth.isVisitor ? maskPhone(v) : (v || '') }
const tableRef = ref(null)
const projects = ref([])
const loading = ref(false)
const searchText = ref('')
const filterConstructionUnit = ref('')
const filterDispatchStatus = ref('')
const filterProjectType = ref('')
const filterResponsibleUnit = ref('')
const selectedIds = ref([])

// ---- 打印 / 导出 ----
const printExportDialogVisible = ref(false)

// ---- 批量操作 ----
function handleBatchCmd(cmd) {
  if (cmd === 'export-print') {
    printExportDialogVisible.value = true
  } else if (cmd === 'batch-delete') { handleBatchDelete() }
}

// ---- 展开卡片 ----
const expandedCardIds = ref(new Set())
const expandedProgressIds = ref(new Set())
const expandedIssueIds = ref(new Set())

function toggleCardExpand(rowId) {
  const next = new Set(expandedCardIds.value)
  if (next.has(rowId)) { next.delete(rowId) } else { next.add(rowId) }
  expandedCardIds.value = next
}

function toggleProgressExpand(rowId) {
  const next = new Set(expandedProgressIds.value)
  if (next.has(rowId)) { next.delete(rowId) } else { next.add(rowId) }
  expandedProgressIds.value = next
}

function toggleIssueExpand(rowId) {
  const next = new Set(expandedIssueIds.value)
  if (next.has(rowId)) { next.delete(rowId) } else { next.add(rowId) }
  expandedIssueIds.value = next
}

function roadmapStatusLabel(item) {
  if (item.status === 'completed') return '已完成'
  if (item.status === 'cancelled') return '已作废'
  if (item.is_delayed) return '待完成（已延期）'
  return '待完成'
}

function pendingIssueCount(row) {
  if (!row.issues) return 0
  return row.issues.filter(iss => iss.resolution_status_code === 'pending').length
}

// 展开宽度 + 横向滚动冻结
const expandWidth = ref(1488)
let tableScrollWrapper = null

function updateExpandWidth() {
  const el = tableRef.value?.$el
  if (el) {
    expandWidth.value = el.clientWidth || 1488
  }
}

function onTableScroll(e) {
  const sl = e.target.scrollLeft
  const cells = tableRef.value?.$el?.querySelectorAll('.el-table__expanded-cell')
  cells?.forEach(c => {
    c.style.transform = `translateX(${sl}px)`
  })
}

function onExpandChange() {
  nextTick(() => {
    updateExpandWidth()
  })
}

const dicts = reactive({
  project_types: [],
  dispatch_statuses: [],
  issue_types: [],
  resolution_statuses: [],
  organizations: [],
  staff: []
})

// 分页
const currentPage = ref(1)
const pageSize = ref(15)
const showAll = ref(false)
const recentProgressDays = ref('')

const pagedProjects = computed(() => {
  if (showAll.value) return projects.value
  const start = (currentPage.value - 1) * pageSize.value
  return projects.value.slice(start, start + pageSize.value)
})

// 编辑抽屉
const editDrawerVisible = ref(false)
const editMode = ref('create')
const editingId = ref(null)
const formRef = ref(null)
const saving = ref(false)

const defaultForm = () => ({
  order_no: 0,
  project_name: '',
  project_type_code: '',
  dispatch_status_code: 'dispatching',
  construction_content: '',
  work_roadmap_items: [],
  construction_unit: '',
  construction_location: '',
  start_date: '',
  end_date: '',
  funding_source: '',
  wuhua_platform: '',
  responsible_unit_code: '',
  responsible_person: '',
  responsible_person_phone: '',
  team_leader_ids: [],
  issues: []
})
const form = reactive(defaultForm())

const rules = {
  project_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  project_type_code: [{ required: true, message: '请选择项目类型', trigger: 'change' }]
}

// 详情抽屉
const detailVisible = ref(false)
const detailProject = ref(null)

// 进展抽屉
const progressDrawerVisible = ref(false)
const progressProjectId = ref(null)
const progressProjectName = ref('')

// 导入
const importDialogVisible = ref(false)
const importStep = ref('select')
const importFileList = ref([])
const importUploadRef = ref(null)
const importHeaders = ref([])
const importRows = ref([])
const importing = ref(false)
const importValidCount = ref(0)
const importErrorCount = ref(0)

let searchTimer = null

// ---- 工具函数 ----
function truncate(text, max) {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}

function dispatchStatusColor(code) {
  return code === 'dispatching' ? '#409eff' : '#909399'
}

function resolutionStatusColor(code) {
  const map = { pending: '#f56c6c', processing: '#e6a23c', resolved: '#67c23a' }
  return map[code] || '#909399'
}

// ---- 数据加载 ----
onMounted(async () => {
  loadDicts()   // 字典不阻塞数据加载，改为并行（字典失败不影响列表展示）
  fetchData()
  nextTick(() => {
    updateExpandWidth()
    tableScrollWrapper = tableRef.value?.$el?.querySelector('.el-table__body-wrapper')
    if (tableScrollWrapper) {
      tableScrollWrapper.addEventListener('scroll', onTableScroll)
    }
    window.addEventListener('resize', updateExpandWidth)
  })
})

onBeforeUnmount(() => {
  if (tableScrollWrapper) {
    tableScrollWrapper.removeEventListener('scroll', onTableScroll)
  }
  window.removeEventListener('resize', updateExpandWidth)
})

async function loadDicts() {
  try {
    const res = await getDicts()
    if (res.code === 0) Object.assign(dicts, res.data)
  } catch (err) {
    ElMessage.error(err.message || '加载字典数据失败')
  }
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (searchText.value) params.search = searchText.value
    if (filterConstructionUnit.value) params.construction_unit = filterConstructionUnit.value
    if (filterDispatchStatus.value) params.dispatch_status = filterDispatchStatus.value
    if (filterProjectType.value) params.project_type = filterProjectType.value
    if (filterResponsibleUnit.value) params.responsible_unit = filterResponsibleUnit.value
    if (recentProgressDays.value) params.recent_progress_days = recentProgressDays.value
    const res = await getProjects(params)
    projects.value = res.data || []
    currentPage.value = 1
  } catch (err) {
    projects.value = []
    ElMessage.error(err.message || '加载在建项目数据失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchData, 300)
}

function handleSelectionChange(selection) {
  selectedIds.value = selection.map(s => s.id)
}

// ---- 分页 ----
function handlePageChange(page) { currentPage.value = page }
function handleSizeChange(size) { pageSize.value = size; currentPage.value = 1 }
function handleShowAllChange(val) { currentPage.value = 1 }

// ---- 新建 ----
async function openCreate() {
  editMode.value = 'create'
  editingId.value = null
  resetForm()
  try {
    const res = await getMaxOrderNo()
    if (res.code === 0) {
      form.order_no = (res.data?.max_order_no || 0) + 1
    }
  } catch { form.order_no = 0 }
  editDrawerVisible.value = true
}

// ---- 编辑 ----
async function openEdit(row) {
  editMode.value = 'edit'
  editingId.value = row.id
  try {
    const res = await getProject(row.id)
    if (res.code === 0) {
      const d = res.data
      form.order_no = d.order_no ?? 0
      form.project_name = d.project_name || ''
      form.project_type_code = d.project_type_code || ''
      form.dispatch_status_code = d.dispatch_status_code || 'dispatching'
      form.construction_content = d.construction_content || ''
      form.work_roadmap_items = (d.work_roadmap_items || []).map(item => ({
        sort_order: item.sort_order ?? 0,
        content: item.content || '',
        planned_date: item.planned_date || null,
        actual_date: item.actual_date || null,
        status: item.status || 'pending',
        is_delayed: item.is_delayed || false,
        delay_reason: item.delay_reason || '',
        cancel_reason: item.cancel_reason || ''
      }))
      form.construction_unit = d.construction_unit || ''
      form.construction_location = d.construction_location || ''
      form.start_date = d.start_date || ''
      form.end_date = d.end_date || ''
      form.funding_source = d.funding_source || ''
      form.wuhua_platform = d.wuhua_platform || ''
      form.responsible_unit_code = d.responsible_unit_code || ''
      form.responsible_person = d.responsible_person || ''
      form.responsible_person_phone = d.responsible_person_phone || ''
      form.team_leader_ids = Array.isArray(d.team_leader_ids) ? [...d.team_leader_ids] : []
      form.issues = (d.issues || []).map(iss => ({
        issue_type_code: iss.issue_type_code || '',
        issue_description: iss.issue_description || '',
        resolution_status_code: iss.resolution_status_code || 'pending',
        resolution_note: iss.resolution_note || '',
        main_department_code: iss.main_department_code || ''
      }))
    }
    editDrawerVisible.value = true
  } catch (err) {
    ElMessage.error(err.message || '获取项目详情失败')
  }
}

function addIssue() {
  form.issues.push({
    issue_type_code: '',
    issue_description: '',
    resolution_status_code: 'pending',
    resolution_note: '',
    main_department_code: ''
  })
}

function resetForm() {
  Object.assign(form, defaultForm())
  formRef.value?.clearValidate()
}

// ---- 保存 ----
async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const data = { ...form }

    let res
    if (editMode.value === 'create') {
      res = await createProject(data)
    } else {
      res = await updateProject(editingId.value, data)
    }

    if (res.code === 0) {
      ElMessage.success(editMode.value === 'create' ? '项目已创建' : '项目已更新')
      editDrawerVisible.value = false
      fetchData()
    } else if (res.code === 2) {
      // 序号冲突
      try {
        await ElMessageBox.confirm(
          res.message + '，是否强制调整序号？',
          '序号冲突',
          { confirmButtonText: '强制调整', cancelButtonText: '取消', type: 'warning' }
        )
        data.force_reorder = true
        const retryRes = editMode.value === 'create'
          ? await createProject(data)
          : await updateProject(editingId.value, data)
        if (retryRes.code === 0) {
          ElMessage.success(editMode.value === 'create' ? '项目已创建' : '项目已更新')
          editDrawerVisible.value = false
          fetchData()
        }
      } catch { /* cancelled */ }
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

// ---- 删除 ----
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除在建项目「${row.project_name}」吗？此操作不可恢复。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteProject(row.id)
    ElMessage.success('项目已删除')
    fetchData()
  } catch { /* cancelled */ }
}

// ---- 进展 ----
function handleProgress(row) {
  progressProjectId.value = row.id
  progressProjectName.value = row.project_name
  progressDrawerVisible.value = true
}

// ---- 工作路径图操作 ----
function newRoadmapItem(order) {
  return {
    sort_order: order ?? 0,
    content: '',
    planned_date: null,
    actual_date: null,
    status: 'pending',
    is_delayed: false,
    delay_reason: '',
    cancel_reason: ''
  }
}

function addRoadmapItem() {
  form.work_roadmap_items.push(newRoadmapItem(form.work_roadmap_items.length))
}

function removeRoadmapItem(idx) {
  form.work_roadmap_items.splice(idx, 1)
  form.work_roadmap_items.forEach((item, i) => { item.sort_order = i })
}

async function handleRoadmapComplete(item) {
  try {
    await ElMessageBox.confirm(
      '是否确认这条工作已完成？',
      '确认完成',
      { confirmButtonText: '确认完成', cancelButtonText: '取消', type: 'success' }
    )
  } catch {
    return
  }
  // 第二步：选择实际完成日期
  try {
    const { value } = await ElMessageBox.prompt(
      '请选择实际完成日期：',
      '实际完成日期',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputType: 'date',
        inputValue: item.planned_date || '',
        inputPlaceholder: '选择日期',
        inputValidator: (val) => {
          if (!val) return '请选择实际完成日期'
          return true
        }
      }
    )
    item.status = 'completed'
    item.actual_date = value || item.planned_date
    ElMessage.success('该工作路径节点已完成')
  } catch {
    /* 取消日期选择 */
  }
}

async function handleRoadmapDelay(item) {
  // 第一步：选择新的预计完成日期
  let newDate
  try {
    const { value } = await ElMessageBox.prompt(
      '请选择新的预计完成日期：',
      '延期 — 新预计完成日期',
      {
        confirmButtonText: '下一步',
        cancelButtonText: '取消',
        inputType: 'date',
        inputValue: item.planned_date || '',
        inputPlaceholder: '选择新日期',
        inputValidator: (val) => {
          if (!val) return '请选择新的预计完成日期'
          return true
        }
      }
    )
    newDate = value
  } catch {
    return
  }
  // 第二步：输入延期原因
  try {
    const { value: reason } = await ElMessageBox.prompt(
      '请输入延期原因：',
      '延期 — 延期原因',
      {
        confirmButtonText: '确认延期',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputPlaceholder: '请在此输入延期原因...',
        inputValidator: (val) => {
          if (!val || !val.trim()) return '请输入延期原因'
          return true
        }
      }
    )
    item.is_delayed = true
    item.planned_date = newDate
    item.delay_reason = reason || ''
    ElMessage.success('该工作路径节点已延期')
  } catch {
    /* 取消原因输入 */
  }
}

async function handleRoadmapCancel(item) {
  try {
    const { value } = await ElMessageBox.prompt(
      '确认作废后，该工作路径节点将不再有效。\n请输入作废原因：',
      '确认作废',
      {
        confirmButtonText: '确认作废',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputPlaceholder: '请在此输入作废原因...',
        inputValidator: (val) => {
          if (!val || !val.trim()) return '请输入作废原因'
          return true
        }
      }
    )
    item.status = 'cancelled'
    item.cancel_reason = value || ''
    ElMessage.success('已作废该工作路径节点')
  } catch {
    /* 取消 */
  }
}

// ---- 导入 ----
function handleImportCmd(cmd) {
  if (cmd === 'download-template') {
    downloadTemplate().catch(err => ElMessage.error(err.message))
  } else if (cmd === 'import-data') {
    resetImport()
    importDialogVisible.value = true
  }
}

function resetImport() {
  importStep.value = 'select'
  importFileList.value = []
  importHeaders.value = []
  importRows.value = []
  importValidCount.value = 0
  importErrorCount.value = 0
}

async function handleImportFile(file) {
  importFileList.value = [file]
  try {
    const res = await previewImport(file.raw)
    importHeaders.value = res.data.headers
    importRows.value = res.data.rows
    importValidCount.value = res.data.valid_count
    importErrorCount.value = res.data.error_count
    importStep.value = 'preview'
  } catch (err) {
    ElMessage.error(err.message || '预览失败')
    importFileList.value = []
  }
}

function importRowClass({ row }) {
  return !row._valid ? 'import-error-row' : ''
}

function removeImportRow(idx) {
  importRows.value.splice(idx, 1)
  importValidCount.value = importRows.value.filter(r => r._valid).length
  importErrorCount.value = importRows.value.length - importValidCount.value
}

async function handleImportExecute() {
  const validRows = importRows.value.filter(r => r._valid)
  if (validRows.length === 0) {
    ElMessage.warning('没有有效数据可导入')
    return
  }
  importing.value = true
  try {
    const res = await executeImport(validRows)
    if (res.code === 0) {
      ElMessage.success(`成功导入 ${res.data?.count || validRows.length} 个项目`)
      importDialogVisible.value = false
      fetchData()
    } else {
      ElMessage.error(res.message || '导入失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '导入失败')
  } finally {
    importing.value = false
  }
}

// ---- 操作下拉 ----
function handleRowCmd(cmd, row) {
  if (cmd === 'view') {
    handleViewDetail(row)
  } else if (cmd === 'delete') {
    handleDelete(row)
  }
}

// ---- 查看详情 ----
async function handleViewDetail(row) {
  try {
    const res = await getProject(row.id)
    if (res.code === 0) {
      detailProject.value = res.data
      detailVisible.value = true
    }
  } catch (err) {
    ElMessage.error(err.message || '获取项目详情失败')
  }
}
</script>

<style scoped>
.construction-page { min-height: 100vh; background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%); }
.page-body { max-width: 1600px; margin: 0 auto; padding: 28px 32px 60px; }
.content-card { background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 2px 20px rgba(0,0,0,0.06); }

/* 工具栏 */
.toolbar { display: flex; gap: 16px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
.toolbar-spacer { flex: 1; }
.search-input { width: 320px; }

/* 表格 */
.content-preview { cursor: default; color: #606266; }
.project-type-tag {
  display: inline-block;
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 500;
  color: #1a3a5c;
  background: #e0ecf6;
  border: 1px solid #b8d4ec;
  border-radius: 4px;
}
.action-cell { display: flex; align-items: center; gap: 2px; }
.more-btn { padding: 2px 4px !important; font-size: 16px; }

/* 分页 */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  gap: 16px;
}
.show-all-check { margin-left: 8px; }

/* 抽屉 */
.drawer-title-bar {
  background: linear-gradient(135deg, #5b9bd5 0%, #8ab8e8 100%);
  margin: 0 -20px 0 -20px;
  padding: 20px 20px 20px 40px;
}
.drawer-title { color: #fff; font-size: 16px; font-weight: 600; letter-spacing: 1px; display: flex; align-items: center; gap: 8px; }
.drawer-form { padding: 0 4px; }
.drawer-form :deep(.el-form-item) { margin-bottom: 16px; }
.drawer-form :deep(.el-input-number .el-input__inner) { text-align: left; }

/* 分区标题 */
.section-header {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; margin: 20px 0 14px;
  background: #f5f7fa; border-radius: 6px;
  border-left: 3px solid #1a3a5c;
}
.section-icon { color: #1a3a5c; font-size: 16px; display: flex; align-items: center; }
.section-title { font-size: 14px; font-weight: 600; color: #303133; }

.drawer-footer { display: flex; justify-content: center; gap: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #ebeef5; }

/* 详情抽屉 */
.detail-desc :deep(.el-descriptions__label) { width: 100px; font-weight: 500; color: #606266; }

/* 详情弹窗 */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 24px;
  margin-bottom: 16px;
}
.detail-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.detail-label {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
  min-width: 56px;
}
.detail-section {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}
.detail-section h4 {
  font-size: 14px;
  color: #303133;
  margin: 0 0 8px;
  font-weight: 600;
}
.detail-section p {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  white-space: pre-wrap;
}
.detail-sub-item {
  padding: 8px 12px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 6px;
}
.sub-date {
  font-size: 12px;
  color: #409eff;
  font-weight: 500;
}
.detail-sub-item p {
  margin: 4px 0 0;
}

/* 工作路径图子表 */
.roadmap-list { display: flex; flex-direction: column; gap: 8px; }
.roadmap-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  background: #fafbfc;
  transition: all 0.2s;
}
.roadmap-card:hover { border-color: #b8d4ec; background: #f5f8fc; }
.roadmap-card.roadmap-completed { background: #f0f9eb; border-color: #c2e7b0; }
.roadmap-card.roadmap-cancelled { background: #fef0f0; border-color: #fbc4c4; }
.roadmap-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.roadmap-main { flex: 1; min-width: 0; }
.roadmap-content {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.roadmap-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px; height: 22px;
  background: #1a3a5c;
  color: #fff;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}
.roadmap-dates {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}
.date-group { display: flex; align-items: center; gap: 6px; }
.date-group label {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}
.roadmap-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 6px;
  flex-shrink: 0;
}
.roadmap-reason {
  font-size: 12px;
  color: #e6a23c;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.roadmap-reason.cancel { color: #f56c6c; }
.roadmap-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
  padding-top: 2px;
}
.roadmap-delete-btn {
  flex-shrink: 0;
  margin-top: 2px;
}

/* 详情弹窗 — 工作路径图 */
.roadmap-detail-header {
  display: flex;
  align-items: center;
  gap: 4px;
}
.sub-index {
  font-weight: 600;
  color: #1a3a5c;
  font-size: 13px;
}
.sub-text { flex: 1; font-size: 13px; color: #303133; }
.roadmap-detail-dates {
  margin-top: 4px;
  font-size: 12px;
  color: #606266;
}

/* 表格行 hover */
:deep(.el-table__body tr:hover > td) { background-color: #fef7e8 !important; }
:deep(.el-table td.el-table__cell) { padding: 6px 2px; }

/* 展开图标 */
:deep(.el-table__expand-icon) {
  font-size: 15px;
  color: #409eff;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}
:deep(.el-table__expand-icon::before) { display: none !important; }
:deep(.el-table__expand-column .cell::before),
:deep(.el-table__expand-column .cell::after) { display: none !important; }
:deep(.el-table__expand-icon:hover) {
  background: #ecf5ff;
  color: #1a3a5c;
  transform: scale(1.15);
}
:deep(.el-table__expand-icon--expanded) { color: #1a3a5c; }
:deep(.el-table__expand-icon--expanded:hover) {
  background: #ecf5ff;
  color: #1a3a5c;
  transform: rotate(90deg) scale(1.15);
}

/* ===== 展开卡片 ===== */
.expand-content {
  padding: 8px 20px 16px;
  background: #f5f7fa;
  box-sizing: border-box;
  overflow: hidden;
}

.expand-block {
  margin-top: 14px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  box-sizing: border-box;
}
.expand-block:first-child { margin-top: 6px; }

.expand-block-title {
  font-size: 12px; font-weight: 600; color: #1a3a5c;
  margin-bottom: 8px; padding-bottom: 6px;
  border-bottom: 1px dashed #e4e7ed;
  text-transform: uppercase; letter-spacing: 1px;
}

.expand-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 28px;
}
.expand-item { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.expand-item label { font-size: 12px; color: #909399; font-weight: 500; }
.expand-item span { font-size: 14px; color: #303133; word-break: break-word; }

.expand-text-block {
  font-size: 13px; color: #4a5568; line-height: 1.7;
  margin: 0; white-space: pre-wrap; word-break: break-word;
}

.expand-toggle-bar {
  display: flex; justify-content: center;
  padding: 10px 0 4px;
  border-top: 1px dashed #d0d7de; margin-top: 6px;
}
.expand-toggle-top {
  padding: 0 0 10px; border-top: none;
  border-bottom: 1px dashed #d0d7de; margin-top: 0; margin-bottom: 6px;
}

.demand-summary-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px;
  background: #fafbfc; border-radius: 6px; border: 1px dashed #d4d9e1;
}
.demand-summary-text { font-size: 13px; color: #606266; }
.text-warning { color: #e6a23c; }

/* 工作路径图 — 时间轴 */
.timeline {
  position: relative;
  padding-left: 24px;
}
.timeline::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: #dcdfe6;
  border-radius: 1px;
}
.timeline-item {
  position: relative;
  padding: 5px 0;
}
.timeline-item:first-child { padding-top: 0; }
.timeline-item:last-child { padding-bottom: 0; }

.timeline-dot {
  position: absolute;
  left: -16px;
  top: 11px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #409eff;
  border: 2px solid #fff;
  box-shadow: 0 0 0 2px #409eff;
  z-index: 1;
}
.timeline-item.is-completed .timeline-dot {
  background: #67c23a;
  box-shadow: 0 0 0 2px #67c23a;
}
.timeline-item.is-delayed .timeline-dot {
  background: #e6a23c;
  box-shadow: 0 0 0 2px #e6a23c;
}
.timeline-item.is-cancelled .timeline-dot {
  background: #f56c6c;
  box-shadow: 0 0 0 2px #f56c6c;
}

.timeline-body {
  background: #fafbfc;
  border-radius: 6px;
  padding: 6px 12px;
  border: 1px solid #ebeef5;
}
.timeline-item.is-completed .timeline-body { background: #f0f9eb; border-color: #d2eac2; }
.timeline-item.is-delayed .timeline-body { background: #fdf6ec; border-color: #f5dab1; }
.timeline-item.is-cancelled .timeline-body { background: #fef0f0; border-color: #fbc4c4; }

.timeline-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.timeline-index {
  font-size: 12px;
  font-weight: 700;
  color: #909399;
  min-width: 18px;
}
.timeline-content {
  flex: 1;
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}
.timeline-date {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}
.timeline-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #ecf5ff;
  color: #409eff;
  white-space: nowrap;
  font-weight: 500;
  flex-shrink: 0;
}
.timeline-item.is-completed .timeline-status { background: #e1f0d8; color: #529b2e; }
.timeline-item.is-delayed .timeline-status { background: #faecd8; color: #b88230; }
.timeline-item.is-cancelled .timeline-status { background: #fbc4c4; color: #c45656; }

.timeline-extra {
  margin-top: 5px;
  padding-top: 5px;
  border-top: 1px dashed #e4e7ed;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 12px;
}
.timeline-actual { color: #67c23a; }
.timeline-reason { color: #e6a23c; }
.timeline-reason.cancel { color: #f56c6c; }

/* 工作进展卡片 */
.progress-list { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
.progress-card { padding: 10px 14px; background: #f5f7fa; border-radius: 6px; border: 1px solid #ebeef5; }
.progress-card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.progress-index { font-weight: 600; color: #1a3a5c; font-size: 13px; }
.progress-date-range { font-size: 12px; color: #909399; }
.progress-content-text { font-size: 13px; color: #4a5568; margin: 0; line-height: 1.6; white-space: pre-wrap; }

/* 存在问题卡片 */
.issue-list { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
.issue-card { padding: 10px 14px; background: #f5f7fa; border-radius: 6px; border: 1px solid #ebeef5; }
.issue-card.is-resolved { opacity: 0.7; }
.issue-card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.issue-index { font-weight: 600; color: #1a3a5c; font-size: 13px; }
.issue-type-tag {
  font-size: 12px; padding: 1px 8px; border-radius: 10px;
  background: #ecf5ff; color: #409eff;
}
.issue-status-tag {
  font-size: 12px; padding: 1px 8px; border-radius: 10px;
  background: #fdf6ec; color: #e6a23c;
}
.issue-status-tag.resolved { background: #f0f9eb; color: #67c23a; }
.issue-dept { font-size: 12px; color: #909399; }
.issue-desc { font-size: 13px; color: #4a5568; margin: 0 0 4px; line-height: 1.6; }
.issue-resolution { font-size: 13px; color: #67c23a; margin: 0; }
.issue-edit-card {
  padding: 12px 14px; background: #fafbfc; border-radius: 6px;
  border: 1px solid #e4e7ed; margin-bottom: 10px;
}
.issue-edit-card-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed #dcdfe6;
}
.issue-edit-index { font-weight: 600; font-size: 13px; color: #1a3a5c; }
.empty-hint { text-align: center; color: #c0c4cc; padding: 16px 0; font-size: 13px; }
</style>

<!-- 非 scoped 样式 -->
<style>
.content-tooltip { max-width: 480px !important; white-space: pre-wrap !important; }
.el-drawer__header { margin-bottom: 0 !important; padding: 0 !important; }
.el-drawer__body { padding: 12px 20px 20px !important; }

/* 导入预览 */
.import-summary { display: flex; align-items: center; margin-bottom: 4px; }
.import-error-row { background-color: #fef0f0 !important; }
.import-errors { display: flex; flex-direction: column; gap: 2px; }
.import-error-item { font-size: 12px; color: #f56c6c; }

/* 展开卡片 — 横向滚动冻结 */
.el-table__expanded-cell {
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}
</style>
