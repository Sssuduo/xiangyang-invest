<template>
  <el-drawer v-model="visible" title="项目详情" direction="rtl" size="560px" :before-close="handleClose">
    <template v-if="project">
      <el-descriptions :column="2" border size="small" class="detail-desc">
        <el-descriptions-item label="项目名称" :span="2">
          <strong>{{ project.project_name }}</strong>
        </el-descriptions-item>
        <el-descriptions-item label="顺序号">{{ project.order_no }}</el-descriptions-item>
        <el-descriptions-item label="项目类型">
          <el-tag effect="dark" size="small" :color="dictMatch('project_types', project.project_type_code)?.display_color">
            {{ project.project_type_name || project.project_type_code }}
          </el-tag>
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
          <div class="text-block">{{ project.project_content }}</div>
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
          <el-descriptions-item label="企业诉求" :span="2">
            <div class="demand-list">
              <div v-for="(d, i) in project.demands" :key="d.id" class="demand-item">
                <div class="demand-header">
                  <span class="demand-index">{{ i + 1 }}. {{ d.demand_content }}</span>
                  <el-tag :color="dStatusColor(d.status)" effect="dark" size="small">{{ dStatusName(d.status) }}</el-tag>
                </div>
                <div v-if="d.resolution" class="demand-resolution">
                  <span class="res-label">解决措施：</span>{{ d.resolution }}
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
import { Document } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  project: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue'])
const visible = computed({ get: () => props.modelValue, set: v => emit('update:modelValue', v) })
function handleClose() { emit('update:modelValue', false) }

function formatAmount(a) { if (!a && a !== 0) return '-'; const n = Number(a); return n >= 10000 ? (n / 10000).toFixed(2) + ' 亿元' : n.toLocaleString('zh-CN') + ' 万元' }
function fmtDt(d) { if (!d) return '-'; return new Date(d).toLocaleString('zh-CN', { hour12: false }) }
function dictMatch(key, code) {
  // 从 project 数据中查找对应的 color
  const colorMap = {
    follow_statuses: 'follow_status_color',
    meeting_statuses: 'meeting_status_color'
  }
  const colorKey = colorMap[key]
  if (colorKey && props.project?.[colorKey]) {
    return { display_color: props.project[colorKey] }
  }
  return null
}
function dStatusColor(s) { return { pending: '#e6a23c', processing: '#409eff', resolved: '#67c23a' }[s] || '#909399' }
function dStatusName(s) { return { pending: '待处理', processing: '处理中', resolved: '已解决' }[s] || s }
</script>

<style scoped>
.detail-desc :deep(.el-descriptions__label) { width: 100px; font-weight: 500; color: #606266; }
.text-block { white-space: pre-wrap; line-height: 1.7; font-size: 13px; color: #303133; max-height: 200px; overflow-y: auto; }
.amount-txt { color: #e6a23c; font-size: 16px; }
.doc-link { color: #409eff; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }
.doc-link:hover { text-decoration: underline; }
.demand-list { width: 100%; }
.demand-item { padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.demand-item:last-child { border-bottom: none; }
.demand-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.demand-index { font-size: 13px; color: #303133; flex: 1; }
.demand-resolution { margin-top: 6px; font-size: 12px; color: #606266; padding-left: 20px; }
.res-label { font-weight: 500; color: #909399; }
</style>
