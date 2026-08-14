<!-- BiddingUsers.vue: 揭榜方用户管理（对外端口注册的用户，内部可禁用） -->
<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>揭榜方用户管理</h2>
          <div class="page-header-actions">
            <el-button @click="$router.push('/admin/bidding')">返回揭榜挂帅</el-button>
          </div>
        </div>

        <el-table :data="users" v-loading="loading" stripe>
          <el-table-column prop="id" label="ID" width="60" align="center" />
          <el-table-column prop="org_name" label="单位/团队" min-width="180" show-overflow-tooltip />
          <el-table-column prop="org_type" label="类型" width="100" align="center" />
          <el-table-column prop="contact_name" label="联系人" width="100" />
          <el-table-column prop="contact_phone" label="电话" width="130" />
          <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
          <el-table-column prop="bid_count" label="申请数" width="80" align="center" />
          <el-table-column prop="created_at" label="注册时间" width="150" align="center" />
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                {{ row.is_active ? '正常' : '已禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center">
            <template #default="{ row }">
              <el-button
                size="small"
                :type="row.is_active ? 'danger' : 'success'"
                link
                @click="toggleUser(row)"
              >
                {{ row.is_active ? '禁用' : '启用' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { biddingApi } from '@/api/bidding'

const users = ref([])
const loading = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const res = await biddingApi.listUsers()
    if (res.code === 0) users.value = res.data
  } finally {
    loading.value = false
  }
}

function toggleUser(row) {
  const action = row.is_active ? '禁用' : '启用'
  ElMessageBox.confirm(`确认${action}用户「${row.org_name}」？${row.is_active ? '禁用后该用户将无法登录平台。' : ''}`, '确认', { type: 'warning' })
    .then(async () => {
      const res = await biddingApi.updateUser(row.id, { is_active: !row.is_active })
      if (res.code === 0) { ElMessage.success(res.message); fetchData() }
    }).catch(() => {})
}

onMounted(fetchData)
</script>

<style scoped>
.admin-layout { display: flex; }
.admin-main { flex: 1; overflow-y: auto; height: 100vh; background: #f5f6f8; }
.admin-content { padding: 20px; max-width: 1400px; margin: 0 auto; }
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
</style>
