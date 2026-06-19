<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>编辑省份信息 — {{ form.region_name }}</h2>
          <el-button @click="$router.push('/admin/provinces')">返回列表</el-button>
        </div>

        <el-form :model="form" label-width="100px" class="edit-form">
          <el-form-item label="名称">
            <el-input v-model="form.region_name" disabled />
          </el-form-item>
          <el-form-item label="卡片标题">
            <el-input v-model="form.card_title" placeholder="鼠标悬停时显示的标题" />
          </el-form-item>
          <el-form-item label="卡片内容">
            <div class="editor-wrapper">
              <div id="quill-editor" ref="editorRef" />
            </div>
            <span class="editor-hint">支持加粗、斜体、换行、有序/无序列表。鼠标悬停地图省份时展示。</span>
          </el-form-item>
          <el-form-item label="高亮">
            <el-switch v-model="form.is_highlighted" />
          </el-form-item>
        </el-form>

        <!-- ===== 城市高亮配置 ===== -->
        <el-divider content-position="left">城市高亮配置</el-divider>
        <div class="city-section">
          <div class="city-toolbar">
            <el-button size="small" :loading="seedingCities" @click="handleSeedCities">
              从地图数据初始化城市列表
            </el-button>
            <span class="city-hint">仅在 GeoJSON 数据中存在该省份城市边界时可用</span>
          </div>

          <el-table
            v-if="cities.length > 0"
            ref="cityTableRef"
            :data="cities"
            stripe
            size="small"
            max-height="400"
            @selection-change="handleCitySelectionChange"
          >
            <el-table-column type="selection" width="50" />
            <el-table-column prop="city_name" label="城市名称" width="160" />
            <el-table-column prop="city_code" label="编码" width="100" />
            <el-table-column label="高亮" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_highlighted ? 'warning' : 'info'" size="small">
                  {{ row.is_highlighted ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="card_title" label="卡片标题" min-width="140" />
          </el-table>
          <el-empty v-else description="暂未配置城市数据，请先点击「从地图数据初始化城市列表」" :image-size="60" />
        </div>

        <el-form class="edit-form" style="margin-top: 24px;">
          <el-form-item>
            <el-button type="primary" size="large" :loading="saving" @click="handleSave">
              保 存
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getAdminProvince, updateProvince, getAdminProvinceCities, batchUpdateCityHighlights, seedCitiesFromGeoJson } from '@/api/province'
import Quill from 'quill'
import 'quill/dist/quill.snow.css'

const route = useRoute()
const router = useRouter()
const saving = ref(false)
const form = ref({})
const editorRef = ref(null)
let quillEditor = null

// 城市高亮配置
const cities = ref([])
const selectedCities = ref([])
const seedingCities = ref(false)
const cityTableRef = ref(null)

onMounted(async () => {
  try {
    const res = await getAdminProvince(route.params.id)
    if (res.code === 0) {
      form.value = res.data
      await nextTick()
      initQuill()
      await loadCities()
    }
  } catch (err) {
    ElMessage.error(err.message)
    router.push('/admin/provinces')
  }
})

onUnmounted(() => {
  quillEditor = null
})

function initQuill() {
  if (quillEditor) return

  const toolbarOptions = [
    ['bold', 'italic'],
    [{ list: 'ordered' }, { list: 'bullet' }],
    ['clean']
  ]

  quillEditor = new Quill('#quill-editor', {
    theme: 'snow',
    modules: { toolbar: toolbarOptions },
    placeholder: '鼠标悬停时显示的详细内容...'
  })

  if (form.value.card_content) {
    quillEditor.root.innerHTML = form.value.card_content
  }

  quillEditor.on('text-change', () => {
    form.value.card_content = quillEditor.root.innerHTML
  })
}

async function loadCities() {
  try {
    const res = await getAdminProvinceCities(route.params.id)
    if (res.code === 0) {
      cities.value = res.data || []
      await nextTick()
      // 勾选已高亮的城市
      cities.value.forEach(city => {
        if (city.is_highlighted) {
          cityTableRef.value?.toggleRowSelection(city, true)
        }
      })
    }
  } catch {
    cities.value = []
  }
}

function handleCitySelectionChange(rows) {
  selectedCities.value = rows
}

async function handleSeedCities() {
  seedingCities.value = true
  try {
    await seedCitiesFromGeoJson(route.params.id)
    ElMessage.success('城市数据已从地图数据初始化')
    await loadCities()
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    seedingCities.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    if (quillEditor) {
      form.value.card_content = quillEditor.root.innerHTML
    }
    await updateProvince(route.params.id, form.value)

    // 保存城市高亮
    if (cities.value.length > 0) {
      const highlightIds = selectedCities.value.map(c => c.id)
      await batchUpdateCityHighlights(route.params.id, highlightIds)
    }

    ElMessage.success('保存成功')
    router.push('/admin/provinces')
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
.admin-content { padding: 32px; max-width: 700px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
h2 { color: var(--primary-color); }
.edit-form { background: #fff; padding: 32px; border-radius: 12px; box-shadow: var(--shadow-sm); }
.editor-wrapper { border: 1px solid #dcdfe6; border-radius: 6px; overflow: hidden; }
#quill-editor { min-height: 180px; }
.editor-hint { font-size: 12px; color: #909399; margin-top: 4px; display: inline-block; }

/* 城市高亮配置 */
.city-section {
  background: #fff; padding: 24px; border-radius: 12px;
  box-shadow: var(--shadow-sm); margin-bottom: 0;
}
.city-toolbar {
  display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
}
.city-hint { font-size: 12px; color: #909399; }
</style>
