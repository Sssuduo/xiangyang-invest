<template>
  <el-drawer v-model="visible" direction="rtl" size="780px" :before-close="handleClose">
    <template #header>
      <div class="drawer-title-bar">
        <span class="drawer-title">
          <el-icon><View /></el-icon>
          项目详情
        </span>
      </div>
    </template>
    <template v-if="project">
      <el-descriptions :column="2" border size="small" class="detail-desc">
        <el-descriptions-item label="项目名称" :span="2">
          <strong>{{ dn(project.project_name) }}</strong>
        </el-descriptions-item>
        <el-descriptions-item label="顺序号">{{ project.order_no }}</el-descriptions-item>
        <el-descriptions-item label="项目类型">
          <span class="project-type-tag">{{ project.project_type_name || project.project_type_code }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="投资金额">
          <strong class="amount-txt">{{ formatAmount(project.invest_amount) }}</strong>
        </el-descriptions-item>
        <el-descriptions-item label="首次对接时间">{{ project.first_contact_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="投资商名称" :span="2">{{ dn(project.invest_enterprise) }}</el-descriptions-item>
        <el-descriptions-item label="企业简介" :span="2">
          <div class="text-block">{{ project.enterprise_info }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="项目内容" :span="2">
          <div class="text-block text-block-lg">{{ dc(project.project_content) }}</div>
        </el-descriptions-item>
        <el-descriptions-item v-if="project.conclusion" label="专班研判结论" :span="2">
          <div class="text-block text-block-lg">{{ project.conclusion }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="跟进状态">
          <el-tag :color="project.follow_status_color" effect="dark" size="small">{{ project.follow_status_name || project.follow_status_code }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="上会状态">
          <el-tag :color="project.meeting_status_color" effect="dark" size="small">{{ project.meeting_status_name || project.meeting_status_code }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="推介单位">{{ project.recommend_unit_name || project.recommend_unit_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="责任单位">{{ dn(project.responsible_unit_name || project.responsible_unit_code) }}</el-descriptions-item>
        <el-descriptions-item label="责任人">{{ dn(project.person_in_charge || '-') }}</el-descriptions-item>
        <el-descriptions-item v-if="project._tagNames && project._tagNames.length > 0" label="项目标签" :span="2">
          <el-tag v-for="(name, idx) in project._tagNames" :key="idx" size="small" effect="plain" style="margin-right: 6px; margin-bottom: 4px;">
            {{ name }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item v-if="projectDocs.length > 0" label="项目文档" :span="2">
          <div class="doc-list">
            <div v-for="(doc, idx) in projectDocs" :key="idx" class="doc-item">
              <el-icon class="doc-item-icon"><Document /></el-icon>
              <span class="doc-item-name" :title="doc.name">{{ doc.name }}</span>
              <el-button size="small" link type="primary" @click="previewFile(doc.url, doc.name)">预览</el-button>
              <el-button size="small" link type="success" @click="downloadFile(doc.url, doc.name)">下载</el-button>
            </div>
          </div>
        </el-descriptions-item>
        <el-descriptions-item v-if="planDocs.length > 0" label="投资计划书" :span="2">
          <div class="doc-list">
            <div v-for="(doc, idx) in planDocs" :key="idx" class="doc-item">
              <el-icon class="doc-item-icon"><Document /></el-icon>
              <span class="doc-item-name" :title="doc.name">{{ doc.name }}</span>
              <el-button size="small" link type="primary" @click="previewFile(doc.url, doc.name)">预览</el-button>
              <el-button size="small" link type="success" @click="downloadFile(doc.url, doc.name)">下载</el-button>
            </div>
          </div>
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
import { maskName, maskContent, maskPhone } from '@/utils/mask'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import { ElMessage } from 'element-plus'

const businessAuth = useBusinessAuthStore()
function dn(v) { return businessAuth.isVisitor ? maskName(v) : (v || '') }
function dc(v) { return businessAuth.isVisitor ? maskContent(v) : (v || '') }
function dp(v) { return businessAuth.isVisitor ? maskPhone(v) : (v || '') }

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  project: { type: Object, default: null }
})

function parseDocList(raw) {
  if (!raw) return []
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!Array.isArray(parsed)) return []
    return parsed.map((item, i) => {
      if (typeof item === 'string') return { url: item, name: item.split('/').pop() || `文件${i + 1}` }
      return { url: item.url, name: item.original_name || item.url?.split('/').pop() || `文件${i + 1}` }
    })
  } catch { return [] }
}

const projectDocs = computed(() => parseDocList(props.project?.project_doc))
const planDocs = computed(() => parseDocList(props.project?.investment_plan))

// 支持在线预览的文件类型
const PREVIEWABLE = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp']
function getFileExt(name) { return (name || '').split('.').pop().toLowerCase() }
function canPreview(name) { return PREVIEWABLE.includes(getFileExt(name)) }

// Office 文件预览提示
const OFFICE_EXTS = ['doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx']
function isOfficeFile(name) { return OFFICE_EXTS.includes(getFileExt(name)) }

function previewFile(url, name) {
  if (canPreview(name)) {
    window.open(url, '_blank')
  } else if (isOfficeFile(name)) {
    ElMessage.info('Office 文件需下载后查看，点击"下载"按钮即可')
  } else {
    ElMessage.info('该文件类型不支持在线预览，请下载后查看')
  }
}

function downloadFile(url, name) {
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.target = '_blank'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

const emit = defineEmits(['update:modelValue'])
const visible = computed({ get: () => props.modelValue, set: v => emit('update:modelValue', v) })
function handleClose() { emit('update:modelValue', false) }

function formatAmount(a) { if (!a && a !== 0) return '暂未明确'; const n = Number(a); if (n === 0) return '暂未明确'; return n >= 10000 ? (n / 10000).toFixed(2) + ' 亿元' : n.toLocaleString('zh-CN') + ' 万元' }
function fmtDt(d) { if (!d) return '-'; return new Date(d + 'Z').toLocaleString('zh-CN', { hour12: false }) }
function dStatusColor(s) { return { pending: '#e6a23c', processing: '#409eff', resolved: '#67c23a' }[s] || '#909399' }
function dStatusName(s) { return { pending: '待回应', processing: '协调中', resolved: '已回应' }[s] || s }
</script>

<style scoped>
/* 标题栏 */
.drawer-title-bar {
  background: linear-gradient(135deg, #5b9bd5 0%, #8ab8e8 100%);
  margin: 0 -20px 0 -20px;
  padding: 20px 20px 20px 40px;
}
.drawer-title {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-desc :deep(.el-descriptions__label) { width: 100px; font-weight: 500; color: #606266; }
.detail-desc :deep(.demand-label-top .el-descriptions__label) { vertical-align: top; padding-top: 14px; }
.text-block { white-space: pre-wrap; line-height: 1.7; font-size: 13px; color: #303133; max-height: 200px; overflow-y: auto; }
.text-block-lg { max-height: 400px; }
.amount-txt { color: #e6a23c; font-size: 16px; }

/* 文件列表 */
.doc-list { width: 100%; }
.doc-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  margin-bottom: 4px;
  background: #f8f9fb;
  border-radius: 4px;
  border: 1px solid #ebeef5;
}
.doc-item:last-child { margin-bottom: 0; }
.doc-item-icon { color: #409eff; flex-shrink: 0; }
.doc-item-name {
  flex: 1;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
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
