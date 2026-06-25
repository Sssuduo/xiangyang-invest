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
        </div>

        <!-- 表格 -->
        <el-table
          ref="tableRef"
          :data="pagedProjects"
          stripe
          row-key="id"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          empty-text="暂无在建项目数据"
          style="width: 100%"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column prop="order_no" label="序号" width="60" align="center" />
          <el-table-column prop="project_name" label="在建项目名称" min-width="220" show-overflow-tooltip />
          <el-table-column label="项目类型" width="110">
            <template #default="{ row }">
              <span class="project-type-tag">{{ row.project_type_name || row.project_type_code }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="construction_unit" label="建设单位" width="130" show-overflow-tooltip />
          <el-table-column label="建设内容" min-width="160">
            <template #default="{ row }">
              <el-tooltip :content="row.construction_content" placement="top" :show-after="300" popper-class="content-tooltip">
                <span class="content-preview">{{ truncate(row.construction_content, 40) }}</span>
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
              {{ row.responsible_unit_name || row.responsible_unit_code || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="responsible_person" label="责任人" width="70" align="center" />
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
                    <span v-if="item.delay_reason" class="roadmap-reason">延期原因：{{ item.delay_reason }}</span>
                    <span v-if="item.cancel_reason" class="roadmap-reason cancel">作废原因：{{ item.cancel_reason }}</span>
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
          <el-descriptions-item label="建设单位">{{ detailProject.construction_unit || '-' }}</el-descriptions-item>
          <el-descriptions-item label="责任单位">{{ detailProject.responsible_unit_name || detailProject.responsible_unit_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="责任人">{{ detailProject.responsible_person || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ detailProject.responsible_person_phone || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-section" v-if="detailProject.construction_content">
          <h4>建设内容</h4>
          <p>{{ detailProject.construction_content }}</p>
        </div>
        <div class="detail-section" v-if="detailProject.work_roadmap_items && detailProject.work_roadmap_items.length > 0">
          <h4>工作路径图 ({{ detailProject.work_roadmap_items.length }}条)</h4>
          <div v-for="(wri, i) in detailProject.work_roadmap_items" :key="i" class="detail-sub-item">
            <div class="roadmap-detail-header">
              <span class="sub-index">{{ i + 1 }}.</span>
              <span class="sub-text">{{ wri.content }}</span>
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
            <p v-if="wri.delay_reason" style="color:#e6a23c;">延期原因：{{ wri.delay_reason }}</p>
            <p v-if="wri.cancel_reason" style="color:#f56c6c;">作废原因：{{ wri.cancel_reason }}</p>
          </div>
        </div>
        <!-- 工作进展 -->
        <div class="detail-section" v-if="detailProject.work_progresses && detailProject.work_progresses.length > 0">
          <h4>工作进展 ({{ detailProject.work_progresses.length }}条)</h4>
          <div v-for="(wp, i) in detailProject.work_progresses" :key="i" class="detail-sub-item">
            <span class="sub-date">{{ wp.start_date }} ~ {{ wp.end_date }}</span>
            <p>{{ wp.content }}</p>
          </div>
        </div>
        <!-- 存在问题 -->
        <div class="detail-section" v-if="detailProject.issues && detailProject.issues.length > 0">
          <h4>存在问题 ({{ detailProject.issues.length }}条)</h4>
          <div v-for="(iss, i) in detailProject.issues" :key="i" class="detail-sub-item">
            <el-tag size="small" effect="plain">{{ iss.issue_type_name || iss.issue_type_code }}</el-tag>
            <el-tag size="small" effect="dark" :color="resolutionStatusColor(iss.resolution_status_code)" style="margin-left: 8px; border: none; color: #fff;">{{ iss.resolution_status_name || iss.resolution_status_code }}</el-tag>
            <p v-if="iss.issue_description" style="margin-top: 6px;">{{ iss.issue_description }}</p>
            <p v-if="iss.resolution_note" style="color: #909399; font-size: 12px;">解决措施：{{ iss.resolution_note }}</p>
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, MoreFilled, View, Delete,
  InfoFilled, Document, OfficeBuilding, Guide,
  Check, Clock, Close, Edit,
  Upload, UploadFilled, Download
} from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import ProgressTimelineDrawer from '@/components/investment/ProgressTimelineDrawer.vue'
import {
  getDicts, getProjects, createProject, updateProject,
  getProject, deleteProject, getMaxOrderNo
} from '@/api/construction'
import {
  downloadTemplate, previewImport, executeImport
} from '@/api/construction_import'
import { useBusinessAuthStore } from '@/stores/businessAuth'

const businessAuth = useBusinessAuthStore()
const tableRef = ref(null)
const projects = ref([])
const loading = ref(false)
const searchText = ref('')
const filterConstructionUnit = ref('')
const filterDispatchStatus = ref('')
const filterProjectType = ref('')
const filterResponsibleUnit = ref('')
const selectedIds = ref([])

const dicts = reactive({
  project_types: [],
  dispatch_statuses: [],
  issue_types: [],
  resolution_statuses: [],
  organizations: []
})

// 分页
const currentPage = ref(1)
const pageSize = ref(5)
const showAll = ref(false)

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
  responsible_unit_code: '',
  responsible_person: '',
  responsible_person_phone: ''
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
  await loadDicts()
  fetchData()
})

async function loadDicts() {
  try {
    const res = await getDicts()
    if (res.code === 0) Object.assign(dicts, res.data)
  } catch { /* ignore */ }
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
    const res = await getProjects(params)
    projects.value = res.data || []
    currentPage.value = 1
  } catch {
    projects.value = []
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
      form.responsible_unit_code = d.responsible_unit_code || ''
      form.responsible_person = d.responsible_person || ''
      form.responsible_person_phone = d.responsible_person_phone || ''
    }
    editDrawerVisible.value = true
  } catch (err) {
    ElMessage.error(err.message || '获取项目详情失败')
  }
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
</style>
