<template>
  <div class="official-doc-page">
    <!-- 顶部导航 -->
    <header class="doc-header">
      <el-button text @click="$router.push('/')" class="back-link">
        ← 返回首页
      </el-button>
      <h2 class="doc-title">公文写作</h2>
      <el-button text @click="showHelp = true" class="help-btn">
        <el-icon><QuestionFilled /></el-icon> 使用帮助
      </el-button>
    </header>

    <!-- 主体区域 -->
    <div class="doc-body">
      <!-- 左侧面板 -->
      <aside class="doc-sidebar">
        <!-- 模板/范本 -->
        <div class="sidebar-section">
          <label class="section-label">📄 模板 / 范本</label>
          <el-select
            v-model="selectedTemplateId"
            placeholder="选择模板或上传范本"
            style="width: 100%"
            @change="handleTemplateChange"
          >
            <el-option-group label="内置模板">
              <el-option
                v-for="tpl in builtinTemplates"
                :key="tpl.id"
                :label="tpl.name"
                :value="tpl.id"
              />
            </el-option-group>
            <el-option-group label="我的范本" v-if="userTemplates.length">
              <el-option
                v-for="tpl in userTemplates"
                :key="tpl.id"
                :label="tpl.name"
                :value="'tpl_' + tpl.id"
              />
            </el-option-group>
          </el-select>
          <div class="template-actions">
            <el-button size="small" @click="showUploadTemplate = true">上传范本</el-button>
            <el-button
              size="small"
              type="danger"
              plain
              v-if="selectedUserTemplate"
              @click="handleDeleteTemplate"
            >删除当前范本</el-button>
          </div>
          <div class="template-hint">上传过往公文（.docx/.md/.txt），生成时沿用其格式、仅替换最新数据。</div>
        </div>

        <!-- 模型选择 -->
        <div class="sidebar-section">
          <label class="section-label">🤖 选择模型</label>
          <el-select
            v-model="selectedModelId"
            placeholder="请选择大模型"
            style="width: 100%"
          >
            <el-option
              v-for="model in models"
              :key="model.id"
              :label="model.name"
              :value="model.id"
            />
          </el-select>
        </div>

        <!-- 文体选择 -->
        <div class="sidebar-section">
          <label class="section-label">📝 文体类型</label>
          <el-radio-group v-model="selectedDocType" style="width: 100%">
            <el-radio-button
              v-for="dt in docTypes"
              :key="dt.code"
              :label="dt.code"
            >
              {{ dt.icon }} {{ dt.name }}
            </el-radio-button>
          </el-radio-group>
        </div>

        <!-- 风格参数 -->
        <div class="sidebar-section">
          <label class="section-label">🎨 风格参数</label>
          <div class="style-slider">
            <span class="slider-label">详略度</span>
            <el-slider
              v-model="styleConfig.detailLevel"
              :min="1" :max="5"
              :marks="{ 1: '简', 3: '中', 5: '详' }"
              :show-tooltip="false"
            />
          </div>
          <div class="style-slider">
            <span class="slider-label">数据密度</span>
            <el-slider
              v-model="styleConfig.dataDensity"
              :min="1" :max="5"
              :marks="{ 1: '低', 3: '中', 5: '高' }"
              :show-tooltip="false"
            />
          </div>
          <div class="style-slider">
            <span class="slider-label">政治站位</span>
            <el-slider
              v-model="styleConfig.politicalStance"
              :min="1" :max="5"
              :marks="{ 1: '业务', 3: '均衡', 5: '高举' }"
              :show-tooltip="false"
            />
          </div>
          <div class="style-slider">
            <span class="slider-label">反思深度</span>
            <el-slider
              v-model="styleConfig.reflectionDepth"
              :min="1" :max="5"
              :marks="{ 1: '成绩', 3: '均衡', 5: '问题' }"
              :show-tooltip="false"
            />
          </div>
          <div class="style-slider">
            <span class="slider-label">句式复杂度</span>
            <el-slider
              v-model="styleConfig.sentenceComplexity"
              :min="1" :max="3"
              :marks="{ 1: '简', 2: '中', 3: '繁' }"
              :show-tooltip="false"
            />
          </div>
        </div>
      </aside>

      <!-- 右侧主内容 -->
      <main class="doc-main">
        <!-- 模式切换 -->
        <div class="mode-switch">
          <el-radio-group v-model="workMode" size="small">
            <el-radio-button value="create">✍️ 从零创作</el-radio-button>
            <el-radio-button value="reuse">🔁 框架复用（旧材料换数据）</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 模式 B：框架复用 -->
        <template v-if="workMode === 'reuse'">
          <div v-if="!skeletonTemplateId" class="mode-b-hint">
            <el-empty description="请先在左侧选择「我的范本」——上传过同类材料的范本后，这里会展示骨架结构" :image-size="100" />
          </div>
          <SkeletonEditor
            v-else
            v-model:skeleton="skeletonData"
            :model-id="selectedModelId"
            :template-id="skeletonTemplateId"
            @generated="handleSkeletonGenerated"
          />
        </template>

        <!-- 模式 A：从零创作（三步流程） -->
        <template v-else>
        <!-- 步骤条 -->
        <el-steps :active="currentStep" finish-status="success" align-center>
          <el-step title="准备素材" description="输入或导入写作素材" />
          <el-step title="生成提纲" description="AI生成文章提纲" />
          <el-step title="生成成文" description="AI生成完整文档" />
        </el-steps>

        <!-- 步骤内容区 -->
        <div class="step-content">
          <!-- 步骤一：准备素材 -->
          <MaterialEditor
            v-if="currentStep === 0"
            v-model="material"
            :selected-projects="selectedProjects"
            :import-fields="importFields"
            @update:selected-projects="selectedProjects = $event"
            @update:import-fields="importFields = $event"
            @next="handleGenerateOutline"
          />

          <!-- 步骤二：生成提纲 -->
          <OutlineEditor
            v-if="currentStep === 1"
            v-model="outline"
            :generating="outlineGenerating"
            :progress="outlineProgress"
            :status-text="outlineStatusText"
            @prev="currentStep = 0"
            @next="handleGenerateDocument"
            @regenerate="handleGenerateOutline"
          />

          <!-- 步骤三：生成成文 -->
          <DocumentPreview
            v-if="currentStep === 2"
            v-model="document"
            :generating="docGenerating"
            :progress="docProgress"
            :status-text="docStatusText"
            :doc-title="material.title"
            @prev="currentStep = 1"
            @regenerate="handleGenerateDocument"
          />
        </div>
        </template>
      </main>
    </div>

    <!-- 帮助弹窗 -->
    <el-dialog v-model="showHelp" title="公文写作工具使用帮助" width="600px">
      <div class="help-content">
        <h4>功能介绍</h4>
        <p>公文写作工具基于 AI 大模型，结合《公文写作算法》方法论，帮助您快速生成规范的公文材料。</p>

        <h4>使用流程</h4>
        <ol>
          <li><strong>准备素材</strong>：手动输入写作内容，或从招商项目库导入项目数据</li>
          <li><strong>生成提纲</strong>：AI 根据素材自动生成符合文体规范的提纲</li>
          <li><strong>生成成文</strong>：AI 根据提纲生成完整的公文文档</li>
        </ol>

        <h4>模板 / 范本</h4>
        <p>可将过往公文（如招商情况汇报）上传为「范本」。再次生成时选择该范本，系统会沿用其格式与结构，仅用最新素材 / 项目数据替换具体内容，实现「同格式内容更新」。</p>

        <h4>文体类型</h4>
        <ul>
          <li>工作总结、工作计划、工作汇报</li>
          <li>领导讲话、调研报告、工作方案</li>
          <li>先进事迹、会议纪要</li>
        </ul>

        <h4>风格参数</h4>
        <ul>
          <li><strong>详略度</strong>：控制文章篇幅长短</li>
          <li><strong>数据密度</strong>：控制数据引用频率</li>
          <li><strong>政治站位</strong>：控制政策理论高度</li>
          <li><strong>反思深度</strong>：控制问题分析比重</li>
          <li><strong>句式复杂度</strong>：控制排比/对仗等气势</li>
        </ul>
      </div>
    </el-dialog>

    <!-- 上传范本弹窗 -->
    <el-dialog v-model="showUploadTemplate" title="上传公文范本" width="480px">
      <el-form label-width="90px">
        <el-form-item label="范本名称" required>
          <el-input v-model="uploadForm.name" placeholder="如：2026年招商情况汇报" />
        </el-form-item>
        <el-form-item label="文体类型">
          <el-select v-model="uploadForm.docType" placeholder="请选择（可选）" clearable style="width:100%">
            <el-option v-for="dt in docTypes" :key="dt.code" :label="dt.name" :value="dt.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="范本文件">
          <el-upload
            drag
            action="#"
            :auto-upload="false"
            :limit="1"
            accept=".docx,.md,.txt,.doc"
            :on-change="handleUploadFileChange"
            :on-exceed="() => ElMessage.warning('只能上传一个文件')"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处或 <em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 .docx / .md / .txt，不超过 10MB</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadTemplate = false">取消</el-button>
        <el-button type="primary" :loading="uploadingTemplate" @click="handleUploadTemplate">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { getModels } from '@/api/model'
import { generateOutline, generateDocument, getTemplates, uploadTemplate, deleteTemplate } from '@/api/official-doc'
import { ElMessage } from 'element-plus'
import { QuestionFilled, UploadFilled } from '@element-plus/icons-vue'
import MaterialEditor from '@/components/official-doc/MaterialEditor.vue'
import OutlineEditor from '@/components/official-doc/OutlineEditor.vue'
import DocumentPreview from '@/components/official-doc/DocumentPreview.vue'
import SkeletonEditor from '@/components/official-doc/SkeletonEditor.vue'
import { getTemplateSkeleton } from '@/api/official-doc'
import { docTypes, builtinTemplates } from '@/config/officialDocRules'

// 当前步骤
const currentStep = ref(0)

// 工作模式：create=从零创作（三步）| reuse=框架复用（旧材料换数据）
const workMode = ref('create')
// 模式 B 状态
const skeletonTemplateId = ref(null)   // 当前骨架对应的范本 ID
const skeletonData = ref([])           // 骨架列表（可编辑）
const skeletonLoading = ref(false)

// 模型列表
const models = ref([])
const selectedModelId = ref(null)

// 模板 / 范本
const builtinTemplatesRef = builtinTemplates
const userTemplates = ref([])
const selectedTemplateId = ref('blank')
const templateContent = ref('')

const selectedUserTemplate = computed(() => {
  if (typeof selectedTemplateId.value === 'string' && selectedTemplateId.value.startsWith('tpl_')) {
    const id = parseInt(selectedTemplateId.value.slice(4), 10)
    return userTemplates.value.find(t => t.id === id) || null
  }
  return null
})

// 文体类型
const selectedDocType = ref('work_report')

// 风格参数
const styleConfig = reactive({
  detailLevel: 3,
  dataDensity: 3,
  politicalStance: 2,
  reflectionDepth: 3,
  sentenceComplexity: 2
})

// 素材
const material = reactive({
  title: '',
  background: '',
  practices: '',
  problems: '',
  nextSteps: ''
})

// 项目导入
const selectedProjects = ref([])
const importFields = ref(['project_name', 'invest_enterprise', 'invest_amount', 'project_content', 'follow_status', 'person_in_charge', 'activities', 'demands'])

// 提纲
const outline = ref([])
const outlineGenerating = ref(false)
const outlineProgress = ref(0)
const outlineStatusText = ref('')

// 成文
const document = ref('')
const docGenerating = ref(false)
const docProgress = ref(0)
const docStatusText = ref('')

// 弹窗
const showHelp = ref(false)
const showUploadTemplate = ref(false)
const uploadingTemplate = ref(false)
const uploadForm = reactive({ name: '', docType: '', file: null })

// 加载模型列表
onMounted(async () => {
  try {
    const res = await getModels()
    if (res.code === 0) {
      models.value = res.data || []
      if (models.value.length > 0) {
        selectedModelId.value = models.value[0].id
      }
    }
  } catch {
    // 静默处理
  }
  // 加载用户范本
  loadTemplates()
})

async function loadTemplates() {
  try {
    const res = await getTemplates()
    if (res.code === 0) {
      userTemplates.value = res.data || []
    }
  } catch {
    // 静默处理
  }
}

// 模板切换
function handleTemplateChange(templateId) {
  if (typeof templateId === 'string' && templateId.startsWith('tpl_')) {
    const tpl = selectedUserTemplate.value
    if (tpl) {
      if (tpl.doc_type) selectedDocType.value = tpl.doc_type
      templateContent.value = tpl.content || ''
      // 模式 B：加载该范本骨架
      skeletonTemplateId.value = tpl.id
      loadSkeleton(tpl.id)
    }
  } else {
    const tpl = builtinTemplatesRef.find(t => t.id === templateId)
    templateContent.value = ''
    skeletonTemplateId.value = null
    skeletonData.value = []
    if (tpl && tpl.docType) {
      selectedDocType.value = tpl.docType
    }
  }
}

// 加载范本骨架（模式 B）
async function loadSkeleton(templateId) {
  skeletonLoading.value = true
  try {
    const res = await getTemplateSkeleton(templateId)
    if (res.code === 0) {
      const raw = res.data?.skeleton
      skeletonData.value = Array.isArray(raw) ? raw : (raw ? JSON.parse(raw) : [])
    }
  } catch {
    skeletonData.value = []
  } finally {
    skeletonLoading.value = false
  }
}

// 模式 B 生成完成：填入预览
function handleSkeletonGenerated(doc) {
  document.value = doc
}

// 上传范本
function handleUploadFileChange(file) {
  const isLt10M = file.raw.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB')
    return
  }
  uploadForm.file = file.raw
}

async function handleUploadTemplate() {
  if (!uploadForm.name.trim()) {
    ElMessage.warning('请填写范本名称')
    return
  }
  if (!uploadForm.file) {
    ElMessage.warning('请选择范本文件')
    return
  }
  const formData = new FormData()
  formData.append('name', uploadForm.name.trim())
  formData.append('doc_type', uploadForm.docType || '')
  formData.append('file', uploadForm.file)

  uploadingTemplate.value = true
  try {
    const res = await uploadTemplate(formData)
    if (res.code === 0) {
      ElMessage.success('范本上传成功')
      showUploadTemplate.value = false
      uploadForm.name = ''
      uploadForm.docType = ''
      uploadForm.file = null
      await loadTemplates()
    } else {
      ElMessage.error(res.message || '上传失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '上传失败')
  } finally {
    uploadingTemplate.value = false
  }
}

async function handleDeleteTemplate() {
  const tpl = selectedUserTemplate.value
  if (!tpl) return
  try {
    const res = await deleteTemplate(tpl.id)
    if (res.code === 0) {
      ElMessage.success('已删除')
      selectedTemplateId.value = 'blank'
      templateContent.value = ''
      await loadTemplates()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '删除失败')
  }
}

// 格式化项目数据（前端拼装为文本，后端负责组装提示词）
function formatProjects(projects) {
  if (!projects || projects.length === 0) return ''

  return projects.map((p, index) => {
    const lines = [`### 项目${index + 1}：${p.project_name || ''}`]

    if (importFields.value.includes('invest_enterprise') && p.invest_enterprise) {
      lines.push(`- 投资企业：${p.invest_enterprise}`)
    }
    if (importFields.value.includes('invest_amount') && p.invest_amount) {
      lines.push(`- 投资规模：${p.invest_amount}万元`)
    }
    if (importFields.value.includes('project_content') && p.project_content) {
      lines.push(`- 建设内容：${p.project_content}`)
    }
    if (importFields.value.includes('follow_status') && p.follow_status_name) {
      lines.push(`- 当前状态：${p.follow_status_name}`)
    }
    if (importFields.value.includes('person_in_charge') && p.person_in_charge) {
      lines.push(`- 负责人：${p.person_in_charge}`)
    }
    if (importFields.value.includes('activities') && p.activities && p.activities.length) {
      lines.push(`- 最新动态：`)
      p.activities.slice(-3).forEach(a => {
        lines.push(`  · ${a.date || ''}：${(a.content || '').substring(0, 100)}...`)
      })
    }
    if (importFields.value.includes('demands') && p.demands && p.demands.length) {
      lines.push(`- 企业诉求：`)
      p.demands.forEach(d => {
        const statusStr = d.status ? `（${d.status}）` : ''
        lines.push(`  · ${d.demand_type_name || ''}：${d.demand_content || ''}${statusStr}`)
      })
    }

    return lines.join('\n')
  }).join('\n\n')
}

// 生成提纲
async function handleGenerateOutline() {
  if (!selectedModelId.value) {
    ElMessage.warning('请先选择模型')
    return
  }
  if (!material.title && !material.practices) {
    ElMessage.warning('请至少输入主题或主要做法')
    return
  }

  outlineGenerating.value = true
  outlineProgress.value = 0
  outlineStatusText.value = '正在分析素材内容...'
  let hasError = false

  const progressTimer = setInterval(() => {
    if (outlineProgress.value < 90) {
      outlineProgress.value += Math.random() * 15
      if (outlineProgress.value < 30) {
        outlineStatusText.value = '正在分析素材内容...'
      } else if (outlineProgress.value < 60) {
        outlineStatusText.value = '正在构建文章框架...'
      } else {
        outlineStatusText.value = '正在生成提纲结构...'
      }
    }
  }, 500)

  try {
    const res = await generateOutline({
      model_id: selectedModelId.value,
      doc_type: selectedDocType.value,
      style_config: { ...styleConfig },
      material: { ...material },
      projects_text: formatProjects(selectedProjects.value),
      template_content: templateContent.value
    })

    if (res.code === 0) {
      outline.value = res.data.outline || []
      currentStep.value = 1
      ElMessage.success('提纲生成成功')
    } else {
      hasError = true
      ElMessage.error(res.message || '生成失败')
    }
  } catch (err) {
    hasError = true
    ElMessage.error(err.message || '生成提纲失败，请重试')
  } finally {
    clearInterval(progressTimer)
    if (!hasError) {
      outlineProgress.value = 100
      outlineStatusText.value = '生成完成'
    } else {
      outlineProgress.value = 0
      outlineStatusText.value = '生成失败，请重试'
    }
    outlineGenerating.value = false
  }
}

// 生成成文
async function handleGenerateDocument() {
  if (!selectedModelId.value) {
    ElMessage.warning('请先选择模型')
    return
  }

  docGenerating.value = true
  docProgress.value = 0
  docStatusText.value = '正在准备素材...'
  let hasError = false

  const progressTimer = setInterval(() => {
    if (docProgress.value < 90) {
      docProgress.value += Math.random() * 10
      if (docProgress.value < 20) {
        docStatusText.value = '正在准备素材...'
      } else if (docProgress.value < 50) {
        docStatusText.value = '正在撰写文章主体...'
      } else if (docProgress.value < 80) {
        docStatusText.value = '正在补充细节数据...'
      } else {
        docStatusText.value = '正在润色优化...'
      }
    }
  }, 600)

  try {
    const res = await generateDocument({
      model_id: selectedModelId.value,
      doc_type: selectedDocType.value,
      style_config: { ...styleConfig },
      material: { ...material },
      projects_text: formatProjects(selectedProjects.value),
      template_content: templateContent.value,
      outline: outline.value
    })

    if (res.code === 0) {
      document.value = res.data.document || ''
      currentStep.value = 2
      ElMessage.success('文档生成成功')
    } else {
      hasError = true
      ElMessage.error(res.message || '生成失败')
    }
  } catch (err) {
    hasError = true
    ElMessage.error(err.message || '生成文档失败，请重试')
  } finally {
    clearInterval(progressTimer)
    if (!hasError) {
      docProgress.value = 100
      docStatusText.value = '生成完成'
    } else {
      docProgress.value = 0
      docStatusText.value = '生成失败，请重试'
    }
    docGenerating.value = false
  }
}
</script>

<style scoped>
.official-doc-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-light);
}

.doc-header {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  background: var(--bg-white);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
}

.back-link {
  font-size: 14px;
}

.doc-title {
  flex: 1;
  text-align: center;
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-color);
}

.help-btn {
  font-size: 14px;
  color: var(--text-secondary);
}

.doc-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.doc-sidebar {
  width: 280px;
  background: var(--bg-white);
  border-right: 1px solid var(--border-color);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.template-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.template-hint {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.style-slider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.slider-label {
  font-size: 12px;
  color: var(--text-secondary);
  width: 60px;
  flex-shrink: 0;
}

.style-slider :deep(.el-slider) {
  flex: 1;
}

.doc-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 20px;
}

.doc-main :deep(.el-steps) {
  margin-bottom: 20px;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 24px;
}

.help-content h4 {
  margin: 16px 0 8px;
  color: var(--primary-color);
}

.help-content p,
.help-content li {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.8;
}

.help-content ol,
.help-content ul {
  padding-left: 20px;
}

/* 模式切换 */
.mode-switch {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}
.mode-b-hint {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 10px;
  padding: 20px;
}
</style>
