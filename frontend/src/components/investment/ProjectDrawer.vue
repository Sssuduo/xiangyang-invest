<template>
  <el-drawer v-model="visible" title="项目详情" direction="rtl" size="560px" :before-close="handleClose">
    <template v-if="project">
      <el-descriptions :column="2" border size="small" class="detail-desc">
        <el-descriptions-item label="项目名称" :span="2">
          <strong>{{ project.project_name }}</strong>
        </el-descriptions-item>
        <el-descriptions-item label="顺序号">{{ project.order_no }}</el-descriptions-item>
        <el-descriptions-item label="项目类型">
          <span class="project-type-tag">{{ project.project_type_name || project.project_type_code }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="投资金额">
          <strong class="amount-txt">{{ formatAmount(project.invest_amount) }}</strong>
        </el-descriptions-item>
        <el-descriptions-item label="首次对接时间">{{ project.first_contact_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="投资商名称" :span="2">{{ project.invest_enterprise }}</el-descriptions-item>
        <el-descriptions-item label="企业简介" :span="2">
          <div class="text-block">{{ project.enterprise_info }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="项目内容" :span="2">
          <div class="text-block text-block-lg">{{ project.project_content }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="跟进状态">
          <el-tag :color="project.follow_status_color" effect="dark" size="small">{{ project.follow_status_name || project.follow_status_code }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="上会状态">
          <el-tag :color="project.meeting_status_color" effect="dark" size="small">{{ project.meeting_status_name || project.meeting_status_code }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="推介单位">{{ project.recommend_unit_name || project.recommend_unit_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="责任单位">{{ project.responsible_unit_name || project.responsible_unit_code }}</el-descriptions-item>
        <el-descriptions-item label="责任人">{{ project.person_in_charge || '-' }}</el-descriptions-item>
        <el-descriptions-item v-if="project.project_doc" label="项目文档" :span="2">
          <a :href="project.project_doc" target="_blank" class="doc-link"><el-icon><Document /></el-icon> 查看文档</a>
        </el-descriptions-item>

        <!-- 企业诉求 -->
        <template v-if="project.demands && project.demands.length > 0">
          <el-descriptions-item label="企业诉求" :span="2" label-class-name="demand-label-top">
            <div class="demand-list-drawer">
              <div v-for="(d, i) in project.demands" :key="d.id" class="demand-card-drawer">
                <div class="dmd-header">
                  <span class="dmd-idx">诉求 {{ i + 1 }}</span>
                  <span v-if="d.demand_type_name || d.demand_type_code" class="dmd-type-badge">{{ d.demand_type_name || d.demand_type_code }}</span>
                  <span v-if="d.unit_name || d.unit_code" class="dmd-unit-tag"><el-icon><OfficeBuilding /></el-icon> {{ d.unit_name || d.unit_code }}</span>
                  <div class="dmd-top-spacer"></div>
                  <el-tag :color="dStatusColor(d.status)" effect="dark" size="small">{{ dStatusName(d.status) }}</el-tag>
                </div>
                <div class="dmd-body">{{ d.demand_content }}</div>
                <div v-if="d.resolution" class="dmd-res">
                  <span class="dmd-res-label"><el-icon><ArrowRight /></el-icon> 解决措施</span>
                  <span class="dmd-res-text">{{ d.resolution }}</span>
                </div>
              </div>
            </div>
          </el-descriptions-item>
        </template>

        <el-descriptions-item label="写入时间">{{ fmtDt(project.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="最后更新">{{ fmtDt(project.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </template>
  </el-drawer>
</template>

<script setup>
import { computed } from 'vue'
import { Document, OfficeBuilding, ArrowRight } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  project: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue'])
const visible = computed({ get: () => props.modelValue, set: v => emit('update:modelValue', v) })
function handleClose() { emit('update:modelValue', false) }

function formatAmount(a) { if (!a && a !== 0) return '-'; const n = Number(a); return n >= 10000 ? (n / 10000).toFixed(2) + ' 亿元' : n.toLocaleString('zh-CN') + ' 万元' }
function fmtDt(d) { if (!d) return '-'; return new Date(d).toLocaleString('zh-CN', { hour12: false }) }
function dStatusColor(s) { return { pending: '#e6a23c', processing: '#409eff', resolved: '#67c23a' }[s] || '#909399' }
function dStatusName(s) { return { pending: '待处理', processing: '处理中', resolved: '已解决' }[s] || s }
</script>

<style scoped>
.detail-desc :deep(.el-descriptions__label) { width: 100px; font-weight: 500; color: #606266; }
.detail-desc :deep(.demand-label-top .el-descriptions__label) { vertical-align: top; padding-top: 14px; }
.text-block { white-space: pre-wrap; line-height: 1.7; font-size: 13px; color: #303133; max-height: 200px; overflow-y: auto; }
.text-block-lg { max-height: 400px; }
.amount-txt { color: #e6a23c; font-size: 16px; }
.doc-link { color: #409eff; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }
.doc-link:hover { text-decoration: underline; }
.project-type-tag {
  display: inline-block;
  padding: 2px 10px;
  font-size: 12px;
  color: #1a3a5c;
  background: #e8f0f8;
  border: 1px solid #c8daf0;
  border-radius: 4px;
}

/* 诉求卡片 */
.demand-list-drawer { width: 100%; }
.demand-card-drawer {
  background: #f8f9fb;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 8px;
}
.demand-card-drawer:last-child { margin-bottom: 0; }
.dmd-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.dmd-idx { font-size: 13px; font-weight: 600; color: #606266; }
.dmd-type-badge {
  display: inline-block;
  padding: 1px 8px;
  font-size: 11px;
  color: #1a3a5c;
  background: #e8f0f8;
  border: 1px solid #c8daf0;
  border-radius: 3px;
}
.dmd-unit-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: #1a3a5c;
  background: #f0f5ff;
  border: 1px solid #c8daf0;
  border-radius: 3px;
  padding: 1px 8px;
}
.dmd-top-spacer { flex: 1; }
.dmd-body {
  font-size: 13px;
  color: #303133;
  line-height: 1.6;
  margin-bottom: 6px;
  padding-bottom: 6px;
  border-bottom: 1px dashed #e4e7ed;
  white-space: pre-wrap;
}
.dmd-res {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
}
.dmd-res-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
  color: #409eff;
  white-space: nowrap;
  flex-shrink: 0;
}
.dmd-res-text {
  color: #606266;
  line-height: 1.6;
}
</style>
