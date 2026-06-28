<template>
  <el-drawer
    v-model="visible"
    direction="rtl"
    size="780px"
    @closed="project = null"
  >
    <template #header>
      <div class="drawer-title-bar">
        <span class="drawer-title">
          <el-icon><View /></el-icon>
          {{ dn(project?.project_name) || '项目详情' }}
        </span>
      </div>
    </template>
    <template v-if="project">
      <el-descriptions :column="2" border size="small" class="detail-desc">
        <el-descriptions-item label="序号">{{ project.order_no }}</el-descriptions-item>
        <el-descriptions-item label="项目类型">
          <span class="project-type-tag">{{ project.project_type_name || project.project_type_code }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="调度状态">
          <el-tag effect="dark" size="small" :color="dispatchColor(project.dispatch_status_code)" style="border:none;color:#fff;">
            {{ project.dispatch_status_name || project.dispatch_status_code }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="建设单位">{{ dn(project.construction_unit) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="责任单位">{{ dn(project.responsible_unit_name || project.responsible_unit_code) || '-' }}</el-descriptions-item>
        <el-descriptions-item label="责任人">{{ dn(project.responsible_person) || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="detail-section" v-if="project.construction_content">
        <h4>建设内容</h4>
        <p>{{ dc(project.construction_content) }}</p>
      </div>

      <div class="detail-section" v-if="project.work_roadmap_items && project.work_roadmap_items.length > 0">
        <h4>工作路径图 ({{ project.work_roadmap_items.length }}条)</h4>
        <div v-for="(wri, i) in project.work_roadmap_items" :key="i" class="detail-sub-item">
          <div class="roadmap-detail-header">
            <span class="sub-index">{{ i + 1 }}.</span>
            <span class="sub-text">{{ dc(wri.content) }}</span>
            <el-tag v-if="wri.status === 'completed'" type="success" size="small" effect="dark" style="margin-left:8px;">已完成</el-tag>
            <el-tag v-else-if="wri.status === 'cancelled'" type="info" size="small" effect="dark" style="margin-left:8px;">已作废</el-tag>
            <el-tag v-else :type="wri.is_delayed ? 'warning' : ''" size="small" effect="dark" style="margin-left:8px;">
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

      <div class="detail-section" v-if="project.work_progresses && project.work_progresses.length > 0">
        <h4>工作进展 ({{ project.work_progresses.length }}条)</h4>
        <div v-for="(wp, i) in project.work_progresses" :key="i" class="detail-sub-item">
          <span class="sub-date">{{ wp.start_date }} ~ {{ wp.end_date }}</span>
          <p>{{ dc(wp.content) }}</p>
        </div>
      </div>

      <div class="detail-section" v-if="project.issues && project.issues.length > 0">
        <h4>存在问题 ({{ project.issues.length }}条)</h4>
        <div v-for="(iss, i) in project.issues" :key="i" class="detail-sub-item">
          <el-tag size="small" effect="plain">{{ iss.issue_type_name || iss.issue_type_code }}</el-tag>
          <el-tag size="small" effect="dark" :color="resolveColor(iss.resolution_status_code)" style="margin-left:8px;border:none;color:#fff;">{{ iss.resolution_status_name || iss.resolution_status_code }}</el-tag>
          <p v-if="iss.issue_description" style="margin-top:6px;">{{ dc(iss.issue_description) }}</p>
          <p v-if="iss.resolution_note" style="color:#909399;font-size:12px;">解决措施：{{ dc(iss.resolution_note) }}</p>
        </div>
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
import { ref, computed } from 'vue'
import { View } from '@element-plus/icons-vue'
import { getProject } from '@/api/construction'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import { maskName, maskContent, maskPhone } from '@/utils/mask'

const businessAuth = useBusinessAuthStore()

function dn(v) { return businessAuth.isVisitor ? maskName(v) : (v || '') }
function dc(v) { return businessAuth.isVisitor ? maskContent(v) : (v || '') }
function dp(v) { return businessAuth.isVisitor ? maskPhone(v) : (v || '') }

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  projectId: { type: Number, default: null }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const project = ref(null)

// Watch for projectId changes and fetch data
import { watch } from 'vue'
watch(() => props.projectId, async (id) => {
  if (!id) {
    project.value = null
    return
  }
  try {
    const res = await getProject(id)
    if (res.code === 0) project.value = res.data
  } catch { project.value = null }
})

function dispatchColor(code) {
  return code === 'dispatching' ? '#409eff' : '#909399'
}

function resolveColor(code) {
  const map = { pending: '#f56c6c', processing: '#e6a23c', resolved: '#67c23a' }
  return map[code] || '#909399'
}
</script>

<style scoped>
.drawer-title-bar {
  background: linear-gradient(135deg, #5b9bd5 0%, #8ab8e8 100%);
  margin: 0 -20px 0 -20px; padding: 20px 20px 20px 40px;
}
.drawer-title { color: #fff; font-size: 16px; font-weight: 600; letter-spacing: 1px; display: flex; align-items: center; gap: 8px; }
.detail-desc :deep(.el-descriptions__label) { width: 100px; font-weight: 500; color: #606266; }
.project-type-tag {
  display: inline-block; padding: 3px 10px; font-size: 12px; font-weight: 500;
  color: #1a3a5c; background: #e0ecf6; border: 1px solid #b8d4ec; border-radius: 4px;
}
.detail-section { margin-top: 16px; padding-top: 12px; border-top: 1px solid #ebeef5; }
.detail-section h4 { font-size: 14px; color: #303133; margin: 0 0 8px; font-weight: 600; }
.detail-section p { font-size: 13px; color: #606266; line-height: 1.7; white-space: pre-wrap; }
.detail-sub-item { padding: 8px 12px; margin-bottom: 8px; background: #f5f7fa; border-radius: 6px; }
.sub-date { font-size: 12px; color: #409eff; font-weight: 500; }
.detail-sub-item p { margin: 4px 0 0; }
.roadmap-detail-header { display: flex; align-items: center; gap: 4px; }
.sub-index { font-weight: 600; color: #1a3a5c; font-size: 13px; }
.sub-text { flex: 1; font-size: 13px; color: #303133; }
.roadmap-detail-dates { margin-top: 4px; font-size: 12px; color: #606266; }
</style>

<style>
.el-drawer__header { margin-bottom: 0 !important; padding: 0 !important; }
.el-drawer__body { padding: 12px 20px 20px !important; }
</style>
