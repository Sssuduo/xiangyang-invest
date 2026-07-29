<template>
  <div class="material-editor">
    <!-- 素材来源切换 -->
    <el-radio-group v-model="materialSource" size="large">
      <el-radio-button label="manual">✏️ 手动输入</el-radio-button>
      <el-radio-button label="project">📁 项目导入</el-radio-button>
      <el-radio-button label="upload">📤 文件上传</el-radio-button>
    </el-radio-group>

    <!-- 手动输入 -->
    <div v-if="materialSource === 'manual'" class="manual-input">
      <el-form label-width="110px" label-position="top">
        <el-form-item label="核心主题">
          <el-input
            v-model="localMaterial.title"
            placeholder="如：2026年上半年招商工作情况汇报"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="背景依据（按）">
          <el-input
            v-model="localMaterial.background"
            type="textarea"
            :rows="4"
            placeholder="按照市委、市政府关于招商引资工作的统一部署..."
            maxlength="2000"
            show-word-limit
          />
          <div class="field-tip">💡 提示：交代政策依据、上级要求、背景形势</div>
        </el-form-item>

        <el-form-item label="主要做法与成效（拿）">
          <el-input
            v-model="localMaterial.practices"
            type="textarea"
            :rows="6"
            placeholder="1. 深入开展招商活动，累计拜访企业50家...&#10;2. 推进重点项目落地，签约项目20个..."
            maxlength="5000"
            show-word-limit
          />
          <div class="field-tip">💡 提示：列举具体措施和量化成效，使用 V+N 结构</div>
        </el-form-item>

        <el-form-item label="存在问题">
          <el-input
            v-model="localMaterial.problems"
            type="textarea"
            :rows="4"
            placeholder="1. 部分项目进展缓慢...&#10;2. 要素保障压力较大..."
            maxlength="2000"
            show-word-limit
          />
          <div class="field-tip">💡 提示：客观分析存在的问题和不足</div>
        </el-form-item>

        <el-form-item label="下一步计划（推）">
          <el-input
            v-model="localMaterial.nextSteps"
            type="textarea"
            :rows="4"
            placeholder="1. 继续推进在谈项目...&#10;2. 加强要素保障..."
            maxlength="2000"
            show-word-limit
          />
          <div class="field-tip">💡 提示：明确下一步工作方向和目标</div>
        </el-form-item>
      </el-form>
    </div>

    <!-- 项目导入 -->
    <div v-if="materialSource === 'project'" class="project-import">
      <div class="import-header">
        <span class="import-title">已选项目（{{ localSelectedProjects.length }}个）</span>
        <el-button type="primary" @click="showProjectSelector = true">
          <el-icon><Plus /></el-icon> 添加项目
        </el-button>
      </div>

      <el-table
        v-if="localSelectedProjects.length > 0"
        :data="localSelectedProjects"
        size="small"
        border
        style="margin-bottom: 16px;"
      >
        <el-table-column type="index" width="50" />
        <el-table-column prop="project_name" label="项目名称" min-width="150" />
        <el-table-column prop="invest_enterprise" label="投资企业" min-width="120" />
        <el-table-column prop="invest_amount" label="投资规模" width="100">
          <template #default="{ row }">
            {{ row.invest_amount ? row.invest_amount + '万' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="follow_status_name" label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.follow_status_name" size="small" :type="getStatusType(row.follow_status_code)">
              {{ row.follow_status_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ $index }">
            <el-button type="danger" text size="small" @click="removeProject($index)">
              移除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-else description="暂未选择项目，请点击「添加项目」" :image-size="80" />

      <div class="import-options">
        <span class="options-label">导入内容：</span>
        <el-checkbox-group v-model="localImportFields">
          <el-checkbox label="project_name">项目名称</el-checkbox>
          <el-checkbox label="invest_enterprise">投资企业</el-checkbox>
          <el-checkbox label="invest_amount">投资规模</el-checkbox>
          <el-checkbox label="project_content">建设内容</el-checkbox>
          <el-checkbox label="follow_status">跟进状态</el-checkbox>
          <el-checkbox label="person_in_charge">负责人</el-checkbox>
          <el-checkbox label="activities">动态记录</el-checkbox>
          <el-checkbox label="demands">企业诉求</el-checkbox>
        </el-checkbox-group>
      </div>
    </div>

    <!-- 文件上传 -->
    <div v-if="materialSource === 'upload'" class="file-upload">
      <el-upload
        drag
        action="/api/official-doc/upload-material"
        accept=".docx,.md,.txt,.doc"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :before-upload="beforeUpload"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处或 <em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .docx / .doc / .md / .txt 格式，文件大小不超过 10MB
          </div>
        </template>
      </el-upload>

      <div v-if="uploadedContent" class="uploaded-preview">
        <div class="preview-header">
          <span>📄 已解析内容预览</span>
          <el-button text size="small" @click="uploadedContent = ''">清除</el-button>
        </div>
        <div class="preview-content">{{ uploadedContent }}</div>
      </div>
    </div>

    <!-- 下一步按钮 -->
    <div class="step-actions">
      <el-button
        type="primary"
        size="large"
        :disabled="!canProceed"
        @click="$emit('next')"
      >
        下一步：生成提纲 <el-icon><ArrowRight /></el-icon>
      </el-button>
    </div>

    <!-- 项目选择抽屉 -->
    <ProjectSelectDrawer
      v-model="showProjectSelector"
      :selected-ids="localSelectedProjects.map(p => p.id)"
      @confirm="handleProjectConfirm"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { Plus, ArrowRight, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ProjectSelectDrawer from '@/components/official-doc/ProjectSelectDrawer.vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  selectedProjects: { type: Array, default: () => [] },
  importFields: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'update:selectedProjects', 'update:importFields', 'next'])

// 素材来源
const materialSource = ref('manual')

// 本地素材数据
const localMaterial = reactive({
  title: '',
  background: '',
  practices: '',
  problems: '',
  nextSteps: ''
})

// 同步父组件数据
watch(() => props.modelValue, (val) => {
  if (val) {
    localMaterial.title = val.title || ''
    localMaterial.background = val.background || ''
    localMaterial.practices = val.practices || ''
    localMaterial.problems = val.problems || ''
    localMaterial.nextSteps = val.nextSteps || ''
  }
}, { immediate: true, deep: true })

// 同步到父组件
watch(localMaterial, (val) => {
  emit('update:modelValue', { ...val })
}, { deep: true })

// 项目导入
const localSelectedProjects = ref([])
const localImportFields = ref(['project_name', 'invest_enterprise', 'invest_amount', 'project_content', 'follow_status', 'person_in_charge', 'activities', 'demands'])

watch(() => props.selectedProjects, (val) => {
  localSelectedProjects.value = [...(val || [])]
}, { immediate: true })

watch(() => props.importFields, (val) => {
  localImportFields.value = [...(val || [])]
}, { immediate: true })

watch(localSelectedProjects, (val) => {
  emit('update:selectedProjects', [...val])
}, { deep: true })

watch(localImportFields, (val) => {
  emit('update:importFields', [...val])
}, { deep: true })

const showProjectSelector = ref(false)

// 移除项目
function removeProject(index) {
  localSelectedProjects.value.splice(index, 1)
}

// 确认项目选择
function handleProjectConfirm(projects) {
  localSelectedProjects.value = projects
  showProjectSelector.value = false
}

// 状态标签类型
function getStatusType(code) {
  const typeMap = {
    'follow_focus': 'danger',
    'follow_normal': 'warning',
    'follow_pause': 'info',
    'signed': 'success'
  }
  return typeMap[code] || 'info'
}

// 文件上传
const uploadedContent = ref('')

function beforeUpload(file) {
  const isValidType = ['application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword', 'text/markdown', 'text/plain'].includes(file.type)
  const isLt10M = file.size / 1024 / 1024 < 10

  if (!isValidType) {
    ElMessage.error('只支持 .docx / .doc / .md / .txt 格式')
    return false
  }
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB')
    return false
  }
  return true
}

function handleUploadSuccess(response) {
  if (response.code === 0) {
    ElMessage.success('文件上传成功')
    uploadedContent.value = response.data.content || ''
    // 自动填充到素材
    if (response.data.title) localMaterial.title = response.data.title
    if (response.data.content) localMaterial.practices = response.data.content
  } else {
    ElMessage.error(response.message || '上传失败')
  }
}

function handleUploadError(err) {
  ElMessage.error('文件上传失败：' + (err.message || '未知错误'))
}

// 是否可以继续
const canProceed = computed(() => {
  if (materialSource.value === 'manual') {
    return localMaterial.title || localMaterial.practices
  }
  if (materialSource.value === 'project') {
    return localSelectedProjects.value.length > 0
  }
  if (materialSource.value === 'upload') {
    return uploadedContent.value
  }
  return false
})
</script>

<style scoped>
.material-editor {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.manual-input :deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--text-primary);
}

.field-tip {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.import-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.import-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.import-options {
  padding: 16px;
  background: var(--bg-light);
  border-radius: var(--radius-sm);
}

.options-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  display: block;
  margin-bottom: 12px;
}

.import-options :deep(.el-checkbox-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.file-upload {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.uploaded-preview {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-light);
  font-size: 13px;
  font-weight: 500;
}

.preview-content {
  padding: 12px;
  max-height: 200px;
  overflow-y: auto;
  font-size: 13px;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

.step-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}
</style>
