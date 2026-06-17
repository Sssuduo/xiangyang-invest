<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>轮播页管理</h2>
          <el-button type="primary" @click="$router.push('/admin/pages/new')">
            新建轮播页
          </el-button>
        </div>

        <el-table :data="pages" stripe style="width: 100%; margin-top: 20px">
          <el-table-column prop="sort_order" label="排序" width="80" />
          <el-table-column prop="title" label="标题" min-width="160" />
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="row.page_type === 'map' ? 'warning' : 'info'" size="small">
                {{ row.page_type === 'map' ? '地图页' : '图文页' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-switch
                :model-value="row.is_active"
                @change="(val) => toggleActive(row, val)"
                size="small"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240">
            <template #default="{ row }">
              <el-button size="small" @click="$router.push(`/admin/pages/${row.id}/edit`)">
                编辑
              </el-button>
              <el-button
                v-if="row.sort_order > 0"
                size="small"
                @click="moveUp(row)"
              >
                上移
              </el-button>
              <el-button size="small" @click="moveDown(row)">
                下移
              </el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="pages.length === 0" class="empty-state">
          暂无轮播页，请点击"新建轮播页"创建
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getAdminPages, updatePage, deletePage, reorderPages } from '@/api/carousel'

const router = useRouter()
const pages = ref([])

async function loadPages() {
  try {
    const res = await getAdminPages()
    if (res.code === 0) pages.value = res.data || []
  } catch { /* ignore */ }
}

async function toggleActive(page, val) {
  try {
    await updatePage(page.id, { is_active: val })
    page.is_active = val
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch (err) {
    ElMessage.error(err.message)
  }
}

async function moveUp(page) {
  const index = pages.value.findIndex(p => p.id === page.id)
  if (index <= 0) return
  pages.value[index].sort_order--
  pages.value[index - 1].sort_order++
  await syncOrder()
}

async function moveDown(page) {
  const index = pages.value.findIndex(p => p.id === page.id)
  if (index >= pages.value.length - 1) return
  pages.value[index].sort_order++
  pages.value[index + 1].sort_order--
  await syncOrder()
}

async function syncOrder() {
  try {
    const orders = pages.value.map(p => ({ id: p.id, sort_order: p.sort_order }))
    await reorderPages(orders)
    await loadPages()
  } catch (err) {
    ElMessage.error(err.message)
  }
}

async function handleDelete(page) {
  try {
    await ElMessageBox.confirm(`确定删除"${page.title}"吗？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deletePage(page.id)
    ElMessage.success('删除成功')
    await loadPages()
  } catch { /* cancelled or error */ }
}

onMounted(loadPages)
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: var(--bg-light); }
.admin-content { padding: 32px; max-width: 1200px; }
.page-header { display: flex; justify-content: space-between; align-items: center; }
h2 { color: var(--primary-color); }
.empty-state { text-align: center; padding: 60px 0; color: var(--text-secondary); }
</style>
