<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>导入配置</h2>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon> 保存配置
          </el-button>
        </div>
        <p class="page-desc">配置项目导入模板的字段列。勾选「导出」的字段将出现在下载的导入模板中，「必填」标记的字段在导入时会进行非空校验。</p>

        <el-row :gutter="24">
          <el-col :span="14">
            <div class="card">
              <h4 class="card-title">导入字段列表</h4>
              <el-table :data="fields" row-key="id" stripe size="small" v-loading="loading">
                <el-table-column label="排序" width="60" align="center">
                  <template #default="{ $index }">{{ $index + 1 }}</template>
                </el-table-column>
                <el-table-column prop="field_key" label="字段标识" width="150" />
                <el-table-column label="列标题" min-width="150">
                  <template #default="{ row }">
                    <el-input v-model="row.field_label" size="small" placeholder="列标题" />
                  </template>
                </el-table-column>
                <el-table-column label="导出" width="70" align="center">
                  <template #default="{ row }">
                    <el-switch v-model="row.is_enabled" size="small" />
                  </template>
                </el-table-column>
                <el-table-column label="必填" width="70" align="center">
                  <template #default="{ row }">
                    <el-switch v-model="row.is_required" size="small" />
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <!-- 导入模板预览 -->
            <div class="card" style="margin-top: 20px;">
              <h4 class="card-title">导入模板预览</h4>
              <div class="preview-table-wrapper" v-if="enabledFields.length > 0">
                <div class="preview-table">
                  <div class="preview-header-row">
                    <div
                      v-for="f in enabledFields"
                      :key="f.field_key"
                      class="preview-header-cell"
                    >
                      {{ f.field_label }}
                      <span v-if="f.is_required" class="required-star">*</span>
                    </div>
                  </div>
                  <div class="preview-data-row">
                    <div
                      v-for="f in enabledFields"
                      :key="f.field_key"
                      class="preview-data-cell"
                    >
                      {{ sampleData[f.field_key] || '' }}
                    </div>
                  </div>
                  <div class="preview-mark-row">
                    <div
                      v-for="f in enabledFields"
                      :key="f.field_key"
                      :class="['preview-mark-cell', f.is_required ? 'mark-required' : 'mark-optional']"
                    >
                      {{ f.is_required ? '（必填）' : '（选填）' }}
                    </div>
                  </div>
                </div>
              </div>
              <el-empty v-else description="请至少启用一个字段" :image-size="50" />
            </div>
          </el-col>

          <!-- 右侧：模板下载 -->
          <el-col :span="10">
            <div class="card preview-card">
              <h4 class="card-title">下载模板</h4>
              <p style="font-size:13px;color:#909399;margin-bottom:16px;">
                点击下方按钮下载当前配置的导入模板，模板包含表头和示例数据行。
              </p>
              <el-button type="primary" @click="handleDownload">
                <el-icon><Download /></el-icon> 下载导入模板
              </el-button>
              <el-divider />
              <h4 class="card-title">导入说明</h4>
              <ul class="import-guide">
                <li>下载模板后，按模板格式填写数据</li>
                <li><strong>项目名称</strong>必须唯一，不可与已有项目重复</li>
                <li>字典字段（跟进状态/上会状态/单位/项目类型）填写<strong>中文名称</strong></li>
                <li>日期格式：YYYY-MM-DD（如 2026-01-01）</li>
                <li>投资金额填写数字（单位：万元）</li>
                <li>删除模板中的示例行后填写真实数据</li>
                <li>标记行（必填/选填）可以删除</li>
              </ul>
            </div>
          </el-col>
        </el-row>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getImportFields, updateImportFields, downloadImportTemplate } from '@/api/import_api'

const fields = ref([])
const loading = ref(false)
const saving = ref(false)

const enabledFields = computed(() =>
  fields.value.filter(f => f.is_enabled).sort((a, b) => a.sort_order - b.sort_order)
)

const sampleData = {
  order_no: '1',
  project_name: '示例项目名称',
  project_type_code: '设施农业',
  invest_enterprise: '示例企业名称',
  enterprise_info: '企业简介示例',
  project_content: '项目内容描述',
  invest_amount: '5000',
  follow_status_code: '重点跟进',
  meeting_status_code: '未上会',
  recommend_unit_code: '区招商服务中心',
  responsible_unit_code: '农高区创建专班',
  person_in_charge: '张三',
  first_contact_date: '2026-01-01',
}

onMounted(() => loadFields())

async function loadFields() {
  loading.value = true
  try {
    const res = await getImportFields()
    if (res.code === 0) fields.value = res.data.map(f => ({ ...f }))
  } catch { /* ignore */ }
  finally { loading.value = false }
}

async function handleSave() {
  saving.value = true
  try {
    const data = fields.value.map((f, i) => ({
      id: f.id,
      field_label: f.field_label,
      is_enabled: f.is_enabled,
      is_required: f.is_required,
      sort_order: i + 1
    }))
    const res = await updateImportFields(data)
    if (res.code === 0) ElMessage.success('导入配置已保存')
  } catch (err) { ElMessage.error(err.message) }
  finally { saving.value = false }
}

async function handleDownload() {
  try { await downloadImportTemplate(); ElMessage.success('模板下载成功') }
  catch (err) { ElMessage.error(err.message) }
}
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: #f5f7fa; }
.admin-content { padding: 28px 32px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.page-header h2 { color: #1a3a5c; margin: 0; }
.page-desc { color: #909399; font-size: 13px; margin-bottom: 24px; }

.card { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 8px rgba(0,0,0,0.04); }
.card-title { margin: 0 0 14px; font-size: 15px; color: #303133; padding-bottom: 10px; border-bottom: 2px solid #1a3a5c; display: inline-block; }

/* 预览表格 */
.preview-card { position: sticky; top: 20px; }
.preview-table-wrapper { overflow-x: auto; border: 1px solid #e0e0e0; border-radius: 6px; }
.preview-table { min-width: max-content; }
.preview-header-row { display: flex; background: #3a7abd; color: #fff; font-size: 12px; font-weight: 600; }
.preview-header-cell { padding: 8px 10px; border-right: 1px solid rgba(255,255,255,0.2); white-space: nowrap; min-width: 100px; position: relative; }
.preview-header-cell:last-child { border-right: none; }
.required-star { color: #ffd666; margin-left: 2px; }
.preview-data-row { display: flex; border-bottom: 1px solid #f0f0f0; background: #fff; }
.preview-data-cell { padding: 7px 10px; font-size: 12px; color: #909090; border-right: 1px solid #f0f0f0; white-space: nowrap; min-width: 100px; }
.preview-data-cell:last-child { border-right: none; }
.preview-mark-row { display: flex; background: #fafafa; }
.preview-mark-cell { padding: 5px 10px; font-size: 11px; border-right: 1px solid #f0f0f0; white-space: nowrap; min-width: 100px; }
.preview-mark-cell:last-child { border-right: none; }
.mark-required { color: #c00000; }
.mark-optional { color: #909090; }

.import-guide { padding-left: 18px; font-size: 13px; color: #606266; line-height: 2; }
.import-guide li { margin-bottom: 2px; }
</style>
