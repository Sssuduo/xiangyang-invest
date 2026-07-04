<template>
  <div class="admin-layout">
    <AdminSidebar />
    <main class="admin-main">
      <div class="admin-content">
        <div class="page-header">
          <h2>提示词管理</h2>
          <div style="display: flex; gap: 8px;">
            <el-button @click="importAssessmentTemplate" :loading="importing">
              <el-icon><Download /></el-icon> 导入研判提示词框架
            </el-button>
            <el-button type="primary" @click="$router.push('/admin/prompts/new')">新建提示词</el-button>
          </div>
        </div>

        <el-table :data="prompts" stripe style="width: 100%; margin-top: 20px">
          <el-table-column prop="button_text" label="按钮文字" width="200" />
          <el-table-column prop="prompt_template" label="提示词模板" min-width="300">
            <template #default="{ row }">
              <div class="template-preview">{{ row.prompt_template }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="category" label="分类" width="100" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-switch
                :model-value="row.is_active"
                @change="(val) => toggleActive(row, val)"
                size="small"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button size="small" @click="$router.push(`/admin/prompts/${row.id}/edit`)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="prompts.length === 0" class="empty-state">暂无提示词</div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import AdminSidebar from '@/components/common/AdminSidebar.vue'
import { getAdminPrompts, updatePrompt, deletePrompt, createPrompt } from '@/api/prompt'

const prompts = ref([])
const importing = ref(false)

// 一键导入：写入研判提示词框架到 QuickPrompt 表
async function importAssessmentTemplate() {
  try {
    await ElMessageBox.confirm(
      '将在「提示词管理」中新增一条招商线索研判提示词框架记录，确定导入？',
      '导入研判提示词框架',
      { confirmButtonText: '确定导入', cancelButtonText: '取消', type: 'info' }
    )
  } catch { return }

  importing.value = true
  try {
    const res = await createPrompt({
      button_text: '生成项目分析报告',
      prompt_template: DEFAULT_ASSESSMENT_TEMPLATE,
      description: '招商线索研判专用提示词框架，包含9大维度分析模板，通过「一键复制提示词」功能复制后在AI研判中使用',
      category: '线索研判',
      is_active: false,
      sort_order: 0
    })
    if (res.code === 0) {
      ElMessage.success('研判提示词框架已导入，可编辑后启用')
      await loadPrompts()
    } else {
      ElMessage.error(res.message || '导入失败')
    }
  } catch (err) {
    ElMessage.error(err.message || '导入失败')
  } finally {
    importing.value = false
  }
}

async function loadPrompts() {
  try {
    const res = await getAdminPrompts()
    if (res.code === 0) prompts.value = res.data || []
  } catch { /* ignore */ }
}

async function toggleActive(prompt, val) {
  try {
    await updatePrompt(prompt.id, { is_active: val })
    prompt.is_active = val
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch (err) {
    ElMessage.error(err.message)
  }
}

async function handleDelete(prompt) {
  try {
    await ElMessageBox.confirm(`确定删除"${prompt.button_text}"吗？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deletePrompt(prompt.id)
    ElMessage.success('删除成功')
    await loadPrompts()
  } catch { /* cancelled */ }
}

onMounted(loadPrompts)

const DEFAULT_ASSESSMENT_TEMPLATE = `你是一位专业的招商分析顾问。请根据以下招商线索信息，结合襄阳农高区的产业定位和本地招商知识库，进行全面、客观的研判分析。

【线索信息】
{{lead_context}}

【本地知识库参考】
{{knowledge_context}}

请从以下 9 个维度进行详细分析。**对于涉及外部信息的维度（尤其是舆情、市场调研、企业注册信息等），请务必列出具体的参考信息原文出处或新闻 URL 链接，以便人工核查。**

━━━━━━━━━━━━━━━━━━━━━━━━
一、企业基础信息
━━━━━━━━━━━━━━━━━━━━━━━━
1. **企业注册信息核查**：确认企业注册信息、经营状态、法人代表、注册资本、成立时间、股权结构等。
   - 请列出核查所使用的数据来源和查询平台。
2. **企业资信状况**：分析企业的信用评级、融资历史、经营风险、涉诉情况等。
   - 请列出所参考的裁判文书、失信被执行人查询等信息的来源。

━━━━━━━━━━━━━━━━━━━━━━━━
二、市场与竞争
━━━━━━━━━━━━━━━━━━━━━━━━
3. **正面负面舆情**：搜索企业相关的近期新闻、舆情走向、社会评价等。
   - **请明确列出每一条参考新闻的标题、媒体来源和 URL 链接**，至少列出 3-5 条。
4. **同类型项目市场调研**：分析市场上类似项目的竞争格局、发展趋势、成功/失败案例。
   - 请列出参考案例的项目名称、所在地、投资规模和来源链接。
5. **市场占有情况分析**：分析该项目所生产的主要产品，在襄阳本地、湖北省及周边地区（河南、陕西、重庆、湖南等）的现有市场规模、销售渠道、目标客户群体、市场占有率预期及潜在竞品情况。

━━━━━━━━━━━━━━━━━━━━━━━━
三、投资与回报
━━━━━━━━━━━━━━━━━━━━━━━━
6. **投资规模分析**：评估本项目投资规模的合理性，与同行业同类项目进行横向对比。
7. **投资回报模型**：按企业预计的投入（固定资产投资、流动资金、人员成本等）和投产后预计的收益（年产量、年销售收入、利润率等），测算投资回收期（年）。
   - 若项目涉及征地，需将土地购置成本（参考襄阳当地工业用地价格约 15-30 万元/亩）及基础设施建设成本纳入测算。
   - 请给出**乐观、中性、悲观三种情景**下的回本周期。

━━━━━━━━━━━━━━━━━━━━━━━━
四、配套与布局
━━━━━━━━━━━━━━━━━━━━━━━━
8. **经营配套分析**：分析该企业正常运营是否需要额外的配套设施或配套产业。例如：
   - 秸秆综合利用项目 → 需要秸秆收储运体系（收集半径、运输成本、仓储设施）
   - 粪污综合处理项目 → 需要污水处理厂配套（处理能力、管网覆盖）
   - 农产品深加工项目 → 需要冷链物流、原料基地配套
   - 新能源项目 → 需要电网接入、储能设施
   若存在配套缺口，需评估配套建设周期及对项目投产时间的影响。
9. **湖北及周边地区布局**：分析企业在湖北省及周边省份的现有产业布局、已投项目运营情况、未来投资计划，以及本项目与现有布局的协同效应。

━━━━━━━━━━━━━━━━━━━━━━━━
五、综合研判
━━━━━━━━━━━━━━━━━━━━━━━━

最后，请给出：
- **综合研判结论**（200 字以内摘要）
- **推荐等级**（★★★★★ 强烈推荐 / ★★★★ 推荐 / ★★★ 谨慎推荐 / ★★ 暂缓 / ★ 不推荐）
- **主要风险点**（列举 3-5 条）
- **下一步建议**（是否推荐跟进、需补充哪些材料、建议对接方式）

━━━━━━━━━━━━━━━━━━━━━━━━
六、参考来源汇总
━━━━━━━━━━━━━━━━━━━━━━━━
请以表格形式汇总本次研判中所有引用的外部信息来源：

| 序号 | 维度 | 来源名称 | 信息摘要 | URL链接 |
|------|------|---------|---------|---------|
| 1    | 舆情分析 | 天眼查企业信息 | xxx公司注册资本5000万... | https://... |
| 2    | 舆情分析 | 襄阳市招商局官网 | xxx项目签约仪式报道 | https://... |
| ...  | ...   | ...     | ...     | ...     |`
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100vh; }
.admin-main { flex: 1; background: var(--bg-light); }
.admin-content { padding: 32px; max-width: 1100px; }
.page-header { display: flex; justify-content: space-between; align-items: center; }
h2 { color: var(--primary-color); }
.template-preview { font-size: 13px; color: var(--text-secondary); max-height: 48px; overflow: hidden; }
.empty-state { text-align: center; padding: 60px 0; color: var(--text-secondary); }
</style>
