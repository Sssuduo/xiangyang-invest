<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>省份信息管理</h2>
          <div>
            <el-radio-group v-model="currentScope" size="small" @change="loadProvinces">
              <el-radio-button value="china">全国省份</el-radio-button>
              <el-radio-button value="hubei">湖北省城市</el-radio-button>
            </el-radio-group>
            <el-button
              type="primary"
              style="margin-left: 12px"
              @click="handleBatchSave"
              :loading="saving"
            >
              保存高亮设置
            </el-button>
          </div>
        </div>

        <el-table
          :data="provinces"
          stripe
          style="width: 100%; margin-top: 20px"
          ref="tableRef"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column prop="region_name" label="名称" width="180" />
          <el-table-column prop="region_code" label="编码" width="100" />
          <el-table-column label="高亮" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_highlighted ? 'warning' : 'info'" size="small">
                {{ row.is_highlighted ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="card_title" label="卡片标题" min-width="160" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" @click="$router.push(`/admin/provinces/${row.id}/edit`)">
                编辑
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getAdminProvinces, batchUpdateHighlights } from '@/api/province'

const provinces = ref([])
const currentScope = ref('china')
const selectedRows = ref([])
const saving = ref(false)
const tableRef = ref(null)

onMounted(() => loadProvinces())

async function loadProvinces() {
  try {
    const res = await getAdminProvinces(currentScope.value)
    if (res.code === 0) {
      provinces.value = res.data || []
      await nextTick()
      // 选中已高亮的行
      if (tableRef.value) {
        provinces.value.forEach(row => {
          if (row.is_highlighted) {
            tableRef.value.toggleRowSelection(row, true)
          }
        })
      }
    }
  } catch (err) {
    ElMessage.error(err.message)
  }
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

async function handleBatchSave() {
  saving.value = true
  try {
    const highlightIds = selectedRows.value.map(r => r.id)
    await batchUpdateHighlights(highlightIds, currentScope.value)
    ElMessage.success('高亮设置已保存')
    await loadProvinces()
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: var(--bg-light); }
.admin-content { padding: 32px; max-width: 1100px; }
.page-header { display: flex; justify-content: space-between; align-items: center; }
h2 { color: var(--primary-color); }
</style>
