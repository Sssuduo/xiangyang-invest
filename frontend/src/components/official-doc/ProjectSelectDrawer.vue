<template>
  <el-drawer
    v-model="visible"
    title="选择招商项目"
    direction="rtl"
    size="780px"
    :close-on-click-modal="true"
    append-to-body
  >
    <div class="project-select-drawer">
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索项目名称/投资企业..."
          clearable
          prefix-icon="Search"
          style="width: 300px;"
        />
        <el-select v-model="filterFollowStatus" placeholder="跟进状态" clearable style="width: 140px;">
          <el-option
            v-for="item in dicts.follow_statuses"
            :key="item.code"
            :label="item.name"
            :value="item.code"
          />
        </el-select>
        <el-select v-model="filterProjectType" placeholder="项目类型" clearable style="width: 140px;">
          <el-option
            v-for="item in dicts.project_types"
            :key="item.code"
            :label="item.name"
            :value="item.code"
          />
        </el-select>
      </div>

      <!-- 项目列表 -->
      <el-table
        ref="tableRef"
        :data="filteredProjects"
        height="calc(100vh - 220px)"
        @selection-change="handleSelectionChange"
        row-key="id"
        border
        size="small"
      >
        <el-table-column type="selection" width="50" :selectable="isSelectable" />
        <el-table-column prop="project_name" label="项目名称" min-width="150" show-overflow-tooltip />
        <el-table-column prop="invest_enterprise" label="投资企业" min-width="120" show-overflow-tooltip />
        <el-table-column prop="invest_amount" label="投资规模" width="100">
          <template #default="{ row }">
            {{ row.invest_amount ? row.invest_amount + '万' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="project_type_name" label="项目类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.project_type_name" size="small">{{ row.project_type_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="follow_status_name" label="跟进状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.follow_status_name" size="small" :type="getStatusType(row.follow_status_code)">
              {{ row.follow_status_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="person_in_charge" label="负责人" width="90" />
      </el-table>

      <!-- 底部操作 -->
      <div class="drawer-footer">
        <span class="selected-count">已选 {{ selectedList.length }} 项</span>
        <div class="footer-actions">
          <el-button @click="visible = false">取消</el-button>
          <el-button type="primary" @click="handleConfirm" :disabled="selectedList.length === 0">
            确认选择
          </el-button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { getInvestmentProjects, getDicts } from '@/api/investment'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  selectedIds: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'confirm'])

// 抽屉显示
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 项目列表
const projects = ref([])
const dicts = ref({
  follow_statuses: [],
  project_types: []
})
const loading = ref(false)

// 搜索筛选
const searchKeyword = ref('')
const filterFollowStatus = ref('')
const filterProjectType = ref('')

// 选中列表
const selectedList = ref([])
const tableRef = ref(null)

// 已选ID集合（用于禁用已选项）
const selectedIdsSet = computed(() => new Set(props.selectedIds || []))

// 加载项目列表
async function loadProjects() {
  loading.value = true
  try {
    const res = await getInvestmentProjects({
      page: 1,
      page_size: 1000,
      search: searchKeyword.value,
      follow_status: filterFollowStatus.value,
      project_type: filterProjectType.value
    })
    if (res.code === 0) {
      projects.value = res.data || []
      // 回显已选项
      await nextTick()
      restoreSelection()
    }
  } catch (err) {
    ElMessage.error('加载项目列表失败')
  } finally {
    loading.value = false
  }
}

// 加载字典
async function loadDicts() {
  try {
    const res = await getDicts()
    if (res.code === 0) {
      dicts.value = res.data || {}
    }
  } catch {
    // 静默处理
  }
}

// 恢复选中状态
function restoreSelection() {
  if (!tableRef.value) return
  const table = tableRef.value
  projects.value.forEach(row => {
    if (selectedIdsSet.value.has(row.id)) {
      table.toggleRowSelection(row, true)
    }
  })
}

// 筛选后的项目
const filteredProjects = computed(() => {
  let list = projects.value

  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase()
    list = list.filter(p =>
      (p.project_name || '').toLowerCase().includes(kw) ||
      (p.invest_enterprise || '').toLowerCase().includes(kw)
    )
  }

  if (filterFollowStatus.value) {
    list = list.filter(p => p.follow_status_code === filterFollowStatus.value)
  }

  if (filterProjectType.value) {
    list = list.filter(p => p.project_type_code === filterProjectType.value)
  }

  return list
})

// 选择变化
function handleSelectionChange(selection) {
  selectedList.value = selection
}

// 是否可选
function isSelectable(row) {
  return !selectedIdsSet.value.has(row.id)
}

// 确认选择
function handleConfirm() {
  emit('confirm', selectedList.value)
  visible.value = false
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

// 监听抽屉打开
watch(visible, (val) => {
  if (val) {
    loadProjects()
  }
})

// 初始化
onMounted(() => {
  loadDicts()
})
</script>

<style scoped>
.project-select-drawer {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0 20px 20px;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.drawer-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
  margin-top: 16px;
}

.selected-count {
  font-size: 14px;
  color: var(--text-secondary);
}

.footer-actions {
  display: flex;
  gap: 12px;
}
</style>
