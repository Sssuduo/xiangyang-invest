<template>
  <div class="skeleton-editor">
    <!-- 顶部操作栏 -->
    <div class="sk-toolbar">
      <div class="sk-toolbar-left">
        <el-tag type="info" size="small">范本骨架</el-tag>
        <span class="sk-hint">🔒 定型段落保留原文 · 🔁 槽位段落用新数据替换</span>
      </div>
      <div class="sk-toolbar-right">
        <el-button size="small" :loading="savingSkeleton" @click="handleSaveSkeleton">保存骨架</el-button>
        <el-button size="small" type="primary" :loading="generating" @click="handleGenerate">
          <el-icon><MagicStick /></el-icon> 一键成文
        </el-button>
      </div>
    </div>

    <!-- 槽位数据映射区 -->
    <div v-if="slotKeys.length" class="sk-slots">
      <div class="sk-slots-title">🔁 槽位数据（新数据映射）</div>
      <div v-for="key in slotKeys" :key="key" class="sk-slot-row">
        <span class="sk-slot-key">{{ slotLabel(key) }}</span>
        <el-input
          v-model="slotData[key]"
          type="textarea"
          :rows="2"
          :placeholder="slotPlaceholder(key)"
        />
      </div>
      <div class="sk-slots-actions">
        <el-button size="small" @click="openProjectDrawer">
          <el-icon><FolderAdd /></el-icon> 从招商项目导入数据
        </el-button>
        <span class="sk-hint">导入后自动按槽位类型匹配项目字段</span>
      </div>
    </div>

    <!-- 骨架列表 -->
    <div class="sk-list">
      <div v-for="(block, idx) in skeleton" :key="block.id" class="sk-block"
           :class="[`sk-level-${block.level}`, block.type === 'slot' ? 'sk-slot' : 'sk-fixed']">
        <div class="sk-block-head">
          <span class="sk-type-toggle" @click="toggleType(block)">
            <el-tooltip :content="block.type === 'slot' ? '点击改为定型段落' : '点击改为槽位段落'" placement="top">
              <el-icon>
                <Lock v-if="block.type === 'fixed'" />
                <RefreshRight v-else />
              </el-icon>
            </el-tooltip>
          </span>
          <el-input
            v-model="block.heading"
            size="small"
            class="sk-heading-input"
            placeholder="标题"
          />
          <el-select
            v-if="block.type === 'slot'"
            v-model="block.slot_key"
            size="small"
            class="sk-slotkey-select"
            @change="syncSlotKeys"
          >
            <el-option v-for="k in SLOT_KEY_OPTIONS" :key="k.value" :label="k.label" :value="k.value" />
          </el-select>
          <el-button size="small" text type="danger" class="sk-del" @click="removeBlock(idx)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <div class="sk-block-body">
          <template v-if="block.type === 'fixed'">
            <el-input
              v-model="block.original"
              type="textarea"
              :rows="2"
              placeholder="该段原文（保留）——若无原文可留空，生成时按标题撰写"
            />
          </template>
          <template v-else>
            <span class="sk-slot-desc">{{ block.summary || '（槽位段，生成时用左侧新数据替换）' }}</span>
          </template>
        </div>
      </div>
    </div>

    <!-- 项目选择抽屉 -->
    <el-drawer v-model="projectDrawerVisible" title="从招商项目导入数据" size="480px" append-to-body>
      <div class="pd-body">
        <el-input v-model="projectSearch" placeholder="搜索项目名称" clearable style="margin-bottom: 12px;" />
        <el-checkbox-group v-model="selectedProjectIds">
          <div v-for="p in filteredProjects" :key="p.id" class="pd-item">
            <el-checkbox :value="p.id">
              {{ p.project_name }}
              <span class="pd-amount" v-if="p.invest_amount">（{{ formatAmount(p.invest_amount) }}）</span>
            </el-checkbox>
          </div>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="projectDrawerVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmProjectImport">导入到槽位</el-button>
      </template>
    </el-drawer>

    <!-- 生成结果 -->
    <div v-if="generatedDoc" class="sk-result">
      <div class="sk-result-head">
        <span>📄 生成结果</span>
        <el-button size="small" @click="copyResult">复制</el-button>
      </div>
      <div class="sk-result-body" v-html="renderMarkdown(generatedDoc)" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, RefreshRight, Delete, MagicStick, FolderAdd } from '@element-plus/icons-vue'
import { getPublicProjectsLite } from '@/api/investment'
import { generateFromSkeleton } from '@/api/official-doc'

const props = defineProps({
  skeleton: { type: Array, default: () => [] },
  modelId: { type: [String, Number], default: null },
  templateId: { type: [String, Number], default: null },
})

const emit = defineEmits(['update:skeleton', 'generated'])

const SLOT_KEY_OPTIONS = [
  { value: 'project_name', label: '项目名称' },
  { value: 'amount', label: '金额' },
  { value: 'date', label: '日期' },
  { value: 'percentage', label: '百分比' },
  { value: 'count', label: '数量' },
  { value: 'enterprise', label: '企业名称' },
  { value: 'area', label: '面积' },
  { value: 'other', label: '其他' },
]

const savingSkeleton = ref(false)
const generating = ref(false)
const generatedDoc = ref('')
const projectDrawerVisible = ref(false)
const projectSearch = ref('')
const selectedProjectIds = ref([])
const projects = ref([])

const slotData = ref({})

// 槽位 key 去重列表
const slotKeys = computed(() => {
  const keys = []
  for (const b of props.skeleton) {
    if (b.type === 'slot' && b.slot_key && !keys.includes(b.slot_key)) {
      keys.push(b.slot_key)
    }
  }
  return keys
})

const filteredProjects = computed(() => {
  if (!projectSearch.value) return projects.value
  const kw = projectSearch.value.toLowerCase()
  return projects.value.filter(p => (p.project_name || '').toLowerCase().includes(kw))
})

function slotLabel(key) {
  return SLOT_KEY_OPTIONS.find(k => k.value === key)?.label || key
}

function slotPlaceholder(key) {
  const map = {
    project_name: '如：零碳冷链产业园项目、生物育种项目',
    amount: '如：总投资 20 亿元',
    date: '如：2026 年 1-6 月',
    percentage: '如：同比增长 15%',
    count: '如：12 个',
    enterprise: '如：湖北华维科技、君华高科集团',
    area: '如：500 亩',
    other: '输入该槽位的新数据',
  }
  return map[key] || '输入该槽位的新数据'
}

function toggleType(block) {
  block.type = block.type === 'slot' ? 'fixed' : 'slot'
  if (block.type === 'slot' && !block.slot_key) block.slot_key = 'other'
  if (block.type === 'fixed') block.slot_key = null
  emit('update:skeleton', props.skeleton)
}

function removeBlock(idx) {
  props.skeleton.splice(idx, 1)
  emit('update:skeleton', props.skeleton)
}

function syncSlotKeys() {
  emit('update:skeleton', props.skeleton)
}

async function handleSaveSkeleton() {
  if (!props.templateId) {
    ElMessage.warning('请先选择范本')
    return
  }
  savingSkeleton.value = true
  try {
    const { saveTemplateSkeleton } = await import('@/api/official-doc')
    const res = await saveTemplateSkeleton(props.templateId, props.skeleton)
    if (res.code === 0) ElMessage.success('骨架已保存')
    else ElMessage.error(res.message || '保存失败')
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    savingSkeleton.value = false
  }
}

async function handleGenerate() {
  if (!props.modelId) {
    ElMessage.warning('请先在左侧选择模型')
    return
  }
  generating.value = true
  generatedDoc.value = ''
  try {
    const res = await generateFromSkeleton({
      model_id: props.modelId,
      skeleton: props.skeleton,
      replacements: { ...slotData.value },
    })
    if (res.code === 0) {
      generatedDoc.value = res.data.document || ''
      emit('generated', generatedDoc.value)
      ElMessage.success('成文生成成功')
    } else {
      ElMessage.error(res.message || '生成失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '生成失败，请重试')
  } finally {
    generating.value = false
  }
}

async function openProjectDrawer() {
  projectDrawerVisible.value = true
  if (!projects.value.length) {
    try {
      const res = await getPublicProjectsLite()
      if (res.code === 0) projects.value = res.data || []
    } catch { /* ignore */ }
  }
}

function formatAmount(amount) {
  const n = Number(amount)
  if (!n) return ''
  if (n >= 10000) return (n / 10000).toFixed(1) + ' 亿元'
  return n.toLocaleString('zh-CN') + ' 万元'
}

function confirmProjectImport() {
  const selected = projects.value.filter(p => selectedProjectIds.value.includes(p.id))
  if (!selected.length) {
    ElMessage.warning('请选择至少一个项目')
    return
  }
  // 按槽位类型匹配项目字段
  const names = selected.map(p => p.project_name).join('、')
  const totalAmount = selected.reduce((sum, p) => sum + Number(p.invest_amount || 0), 0)
  const enterprises = [...new Set(selected.map(p => p.invest_enterprise).filter(Boolean))].join('、')

  if (slotKeys.value.includes('project_name') && !slotData.value.project_name) {
    slotData.value.project_name = names
  }
  if (slotKeys.value.includes('amount') && !slotData.value.amount) {
    slotData.value.amount = totalAmount >= 10000
      ? `总投资 ${(totalAmount / 10000).toFixed(1)} 亿元`
      : `总投资 ${totalAmount} 万元`
  }
  if (slotKeys.value.includes('enterprise') && !slotData.value.enterprise) {
    slotData.value.enterprise = enterprises
  }

  projectDrawerVisible.value = false
  ElMessage.success(`已导入 ${selected.length} 个项目数据，请检查槽位内容`)
}

async function copyResult() {
  try {
    await navigator.clipboard.writeText(generatedDoc.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选择复制')
  }
}

function renderMarkdown(text) {
  if (!text) return ''
  // 简单 Markdown 转 HTML（标题/粗体/换行）
  return text
    .replace(/^###\s+(.+)$/gm, '<h4>$1</h4>')
    .replace(/^##\s+(.+)$/gm, '<h3>$1</h3>')
    .replace(/^#\s+(.+)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>')
}

// 当骨架从父组件变化时同步
watch(() => props.skeleton, (val) => {
  if (val) emit('update:skeleton', val)
}, { deep: true, immediate: false })
</script>

<style scoped>
.skeleton-editor {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 300px;
}
.sk-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid #e4e7ed;
}
.sk-toolbar-left { display: flex; align-items: center; gap: 8px; }
.sk-hint { font-size: 12px; color: #909399; }
.sk-slots {
  background: #f0f9ff;
  border: 1px solid #d0e8ff;
  border-radius: 8px;
  padding: 12px;
}
.sk-slots-title { font-weight: 600; font-size: 13px; color: #1a3a5c; margin-bottom: 10px; }
.sk-slot-row { display: flex; gap: 10px; margin-bottom: 8px; align-items: flex-start; }
.sk-slot-key {
  width: 90px;
  flex-shrink: 0;
  font-size: 13px;
  color: #409eff;
  padding-top: 6px;
}
.sk-slots-actions { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.sk-list { display: flex; flex-direction: column; gap: 8px; max-height: 420px; overflow-y: auto; }
.sk-block {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 10px;
  transition: border-color 0.2s;
}
.sk-block.sk-fixed { background: #fafafa; }
.sk-block.sk-slot { background: #fff7e6; border-color: #f5dab1; }
.sk-level-1 { margin-left: 0; }
.sk-level-2 { margin-left: 20px; }
.sk-level-3 { margin-left: 40px; }
.sk-block-head { display: flex; align-items: center; gap: 6px; }
.sk-type-toggle { cursor: pointer; color: #909399; font-size: 15px; }
.sk-block.sk-slot .sk-type-toggle { color: #e6a23c; }
.sk-heading-input { flex: 1; }
.sk-slotkey-select { width: 110px; flex-shrink: 0; }
.sk-del { flex-shrink: 0; }
.sk-block-body { margin-top: 8px; }
.sk-slot-desc { font-size: 12px; color: #b88230; }
.sk-result {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}
.sk-result-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-weight: 600; }
.sk-result-body { font-size: 14px; line-height: 1.8; color: #303133; max-height: 500px; overflow-y: auto; white-space: pre-wrap; }
.pd-item { padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
.pd-amount { font-size: 12px; color: #909399; }
</style>
