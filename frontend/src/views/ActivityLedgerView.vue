<template>
  <div class="activity-page">
    <BusinessNavbar variant="light" />

    <div class="page-body">
      <div class="content-card">
        <!-- 工具栏 -->
        <div class="toolbar">
          <el-input v-model="searchText" placeholder="搜索活动内容..." :prefix-icon="Search" clearable class="search-input" @input="handleSearch" />
          <el-date-picker
            v-model="filterDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="onDateRangeChange"
            style="width: 260px;"
          />
          <el-select v-model="filterTags" multiple collapse-tags placeholder="标签筛选" clearable @change="currentPage = 1; fetchData()" style="width: 200px;">
            <el-option v-for="d in activityTagDicts" :key="d.code" :label="d.name" :value="d.code" />
          </el-select>
          <el-select v-model="filterLinked" placeholder="关联状态" clearable @change="currentPage = 1; fetchData()" style="width: 130px;">
            <el-option label="已关联" value="1" />
            <el-option label="未关联" value="0" />
          </el-select>
          <el-button v-if="selectedIds.length > 0 && businessAuth.hasPermission('activity', 'batch_delete')" type="danger" @click="handleBatchDelete">
            <el-icon><Delete /></el-icon> 批量删除 ({{ selectedIds.length }})
          </el-button>
          <div class="toolbar-spacer" />
          <el-button v-if="businessAuth.hasPermission('activity', 'add')" type="primary" @click="openCreate">
            <el-icon><Plus /></el-icon> 添加活动
          </el-button>
        </div>

        <!-- 表格 -->
        <el-table
          ref="tableRef"
          :data="items"
          stripe
          row-key="id"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          empty-text="暂无活动台账数据"
          style="width: 100%"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column label="日期" width="140" align="center">
            <template #default="{ row }">
              <span class="date-cell">{{ row.date || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="活动内容" min-width="280">
            <template #default="{ row }">
              <el-tooltip :content="businessAuth.isVisitor ? '' : row.content" placement="top" :show-after="300" popper-class="content-tooltip">
                <span class="content-preview">{{ dc(truncate(row.content, 60)) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column label="附件" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.files && row.files.length > 0" effect="plain" size="small" type="success">{{ row.files.length }}</el-tag>
              <span v-else class="no-data">-</span>
            </template>
          </el-table-column>
          <el-table-column label="录音" width="60" align="center">
            <template #default="{ row }">
              <el-tooltip v-if="row.audio_file" :content="'录音时长: ' + formatDuration(row.audio_duration) + ' | 转写 ' + (row.audio_transcript?.length || 0) + ' 字'" placement="top">
                <el-icon :size="18" color="#409eff"><Headset /></el-icon>
              </el-tooltip>
              <span v-else class="no-data">-</span>
            </template>
          </el-table-column>
          <el-table-column label="标签" width="180">
            <template #default="{ row }">
              <el-tag v-for="tag in (row.tags || [])" :key="tag" size="small" effect="plain" style="margin-right: 4px; margin-bottom: 2px;">
                {{ getTagName(tag) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="关联项目" width="160">
            <template #default="{ row }">
              <template v-if="row.linked_project_id">
                <el-tag type="warning" effect="plain" size="small" style="cursor: pointer;" @click="handleProjectClick(row)">
                  {{ dn(row.linked_project_name) }}
                </el-tag>
              </template>
              <span v-else class="no-data">未关联</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="handleView(row)">查看</el-button>
              <el-button v-if="businessAuth.hasPermission('activity', 'edit')" size="small" link type="success" @click="openEdit(row)">编辑</el-button>
              <el-button v-if="businessAuth.hasPermission('activity', 'delete')" size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
          style="margin-top: 20px; justify-content: flex-end;"
        />
      </div>
    </div>

    <!-- 查看抽屉 -->
    <el-drawer v-model="viewDrawerVisible" direction="rtl" size="680px">
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">
            <el-icon><View /></el-icon>
            活动台账详情
          </span>
        </div>
      </template>
      <template v-if="viewItem">
        <el-descriptions :column="2" border size="small" class="detail-desc">
          <el-descriptions-item label="日期" :span="2">{{ viewItem.date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="活动内容" :span="2">
            <div class="text-block">{{ dc(viewItem.content) }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="标签" :span="2">
            <el-tag v-for="tag in (viewItem.tags || [])" :key="tag" size="small" effect="plain" style="margin-right: 6px; margin-bottom: 2px;">
              {{ getTagName(tag) }}
            </el-tag>
            <span v-if="!viewItem.tags || viewItem.tags.length === 0" class="no-data">-</span>
          </el-descriptions-item>
          <el-descriptions-item label="附件" :span="2">
            <template v-if="viewItem.files && viewItem.files.length > 0">
              <div class="file-thumbnail-grid">
                <div v-for="(url, idx) in viewItem.files" :key="idx" class="file-thumb-card" @click="openFile(url)">
                  <div class="thumb-preview">
                    <img v-if="isImageUrl(url)" :src="url" class="thumb-img" />
                    <div v-else-if="isPdfUrl(url)" class="thumb-pdf">
                      <el-icon :size="32"><Document /></el-icon>
                      <span>PDF</span>
                    </div>
                    <div v-else class="thumb-generic">
                      <el-icon :size="28"><Document /></el-icon>
                    </div>
                  </div>
                  <div class="thumb-name" :title="getViewFileName(url)">{{ getViewFileName(url) }}</div>
                </div>
              </div>
            </template>
            <span v-else class="no-data">暂无附件</span>
          </el-descriptions-item>
          <el-descriptions-item label="关联项目" :span="2">
            <template v-if="viewItem.linked_project_id">
              <el-tag type="warning" effect="plain">{{ viewItem.linked_project_name }}</el-tag>
            </template>
            <span v-else class="no-data">未关联</span>
          </el-descriptions-item>
          <!-- 录音信息 -->
          <template v-if="viewItem.audio_file">
            <el-descriptions-item label="会议录音" :span="2">
              <div class="view-audio-card">
                <div class="view-audio-row">
                  <audio :src="viewItem.audio_file" controls class="view-audio-player" />
                  <el-tag size="small" type="info" effect="plain" v-if="viewItem.audio_duration">{{ formatDuration(viewItem.audio_duration) }}</el-tag>
                </div>
                <div v-if="viewItem.audio_transcript" class="view-audio-text" style="margin-top: 8px;">
                  <div class="audio-section-header">
                    <span class="section-label">语音转文字</span>
                    <el-tag size="small" type="primary" effect="plain">{{ viewItem.audio_transcript.length }} 字</el-tag>
                  </div>
                  <div class="audio-text-content">{{ viewItem.audio_transcript }}</div>
                </div>
                <div v-if="viewItem.audio_summary" class="view-audio-summary" style="margin-top: 8px;">
                  <div class="audio-section-header">
                    <span class="section-label">AI 总结</span>
                  </div>
                  <div class="audio-summary-content">{{ viewItem.audio_summary }}</div>
                </div>
              </div>
            </el-descriptions-item>
          </template>
          <el-descriptions-item label="写入时间">{{ fmtDt(viewItem.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="最后更新">{{ fmtDt(viewItem.updated_at) }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>

    <!-- 项目详情抽屉 -->
    <ProjectDrawer v-model="projectDrawerVisible" :project="projectDrawerProject" />

    <!-- 编辑抽屉（新建/编辑共用） -->
    <el-drawer v-model="editDrawerVisible" direction="rtl" size="680px" @closed="resetForm">
      <template #header>
        <div class="drawer-title-bar">
          <span class="drawer-title">
            <el-icon><Edit /></el-icon>
            {{ editMode === 'create' ? '新建活动台账' : '编辑活动台账' }}
          </span>
        </div>
      </template>
      <div class="drawer-form">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" label-position="right">
          <!-- 基础信息 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><InfoFilled /></el-icon></span>
            <span class="section-title">基础信息</span>
          </div>
          <el-form-item label="日期" prop="date">
            <el-date-picker
              v-model="form.date"
              type="date"
              placeholder="选择日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              style="width: 100%;"
            />
          </el-form-item>

          <!-- 活动内容 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><Document /></el-icon></span>
            <span class="section-title">活动内容</span>
          </div>
          <el-form-item label="活动内容" prop="content">
            <el-input v-model="form.content" type="textarea" :rows="4" placeholder="请输入活动内容..." maxlength="5000" show-word-limit />
          </el-form-item>
          <el-form-item label="附件">
            <div class="upload-wrapper" @paste="handleClipboardPaste">
              <el-upload
                ref="uploadRef"
                v-model:file-list="fileList"
                :action="uploadUrl"
                :headers="uploadHeaders"
                :on-success="handleUploadSuccess"
                :on-error="handleUploadError"
                :before-upload="beforeUpload"
                :on-remove="handleFileRemove"
                :show-file-list="false"
                multiple
                drag
                accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.png,.jpg,.jpeg"
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖动文件到此处 或 <em>点击上传</em></div>
                <template #tip>
                  <div class="el-upload__tip">支持 PDF/DOC/DOCX/PPT/XLS/图片，可多个上传；也可 <kbd>Ctrl+V</kbd> 粘贴图片</div>
                </template>
              </el-upload>
              <!-- 文件缩略图网格 -->
              <div v-if="fileList.length > 0" class="file-thumbnail-grid">
                <div v-for="(file, idx) in fileList" :key="file.uid || idx" class="file-thumb-card">
                  <div class="thumb-preview">
                    <img v-if="isImageFile(file)" :src="getFilePreviewUrl(file)" class="thumb-img" />
                    <div v-else-if="isPdfFile(file)" class="thumb-pdf">
                      <el-icon :size="32"><Document /></el-icon>
                      <span>PDF</span>
                    </div>
                    <div v-else class="thumb-generic">
                      <el-icon :size="28"><Document /></el-icon>
                    </div>
                    <div class="thumb-remove" @click="handleThumbRemove(idx)">
                      <el-icon><Close /></el-icon>
                    </div>
                  </div>
                  <div class="thumb-name" :title="getFileName(file)">{{ getFileName(file) }}</div>
                </div>
              </div>
            </div>
          </el-form-item>

          <!-- 录音上传（仅编辑模式） -->
          <template v-if="editMode === 'edit' && editingId">
            <div class="section-header">
              <span class="section-icon"><el-icon><Headset /></el-icon></span>
              <span class="section-title">会议录音</span>
            </div>
            <el-form-item label="录音文件">
              <div class="audio-section">
                <!-- 已有录音，显示详情 -->
                <div v-if="audioFile && audioFile.audio_file" class="audio-loaded">
                  <div class="audio-player-card">
                    <div class="audio-info">
                      <el-icon :size="20"><Headset /></el-icon>
                      <span>录音文件</span>
                      <el-tag size="small" type="success" effect="plain" v-if="audioDetail?.compression_ratio">
                        压缩 {{ audioDetail.compression_ratio }}x
                      </el-tag>
                      <el-tag size="small" type="info" effect="plain" v-if="audioDetail?.audio_duration">
                        {{ formatDuration(audioDetail.audio_duration) }}
                      </el-tag>
                      <span class="audio-size" v-if="audioDetail?.compressed_size">
                        压缩后 {{ formatFileSize(audioDetail.compressed_size) }}
                      </span>
                    </div>
                    <div class="audio-actions">
                      <audio v-if="audioFile.audio_file" :src="audioFile.audio_file" controls class="mini-audio-player" />
                      <el-button type="danger" size="small" plain @click="handleDeleteAudio">删除录音</el-button>
                    </div>
                  </div>

                  <!-- 转写文本 -->
                  <div v-if="audioDetail?.audio_transcript" class="audio-transcript-section">
                    <div class="audio-section-header">
                      <span class="section-label">
                        <el-icon><Document /></el-icon> 语音转文字结果
                      </span>
                      <el-tag size="small" type="primary" effect="plain">{{ audioDetail.audio_transcript.length }} 字</el-tag>
                    </div>
                    <div class="audio-text-content">{{ audioDetail.audio_transcript }}</div>
                  </div>

                  <!-- 内容总结 -->
                  <div v-if="audioDetail?.audio_summary" class="audio-summary-section">
                    <div class="audio-section-header">
                      <span class="section-label">
                        <el-icon><InfoFilled /></el-icon> AI 内容总结
                      </span>
                    </div>
                    <div class="audio-summary-content">{{ audioDetail.audio_summary }}</div>
                  </div>
                </div>

                <!-- 未上传录音：上传区域 -->
                <div v-else class="audio-upload-wrapper">
                  <el-upload
                    :auto-upload="false"
                    :show-file-list="false"
                    :on-change="onAudioFileChange"
                    accept=".wav,.mp3,.m4a,.ogg,.flac,.wma,.aac,.amr,.opus,.weba,.webm"
                    drag
                    :disabled="audioUploading"
                  >
                    <el-icon class="el-icon--upload"><Headset /></el-icon>
                    <div class="el-upload__text">
                      <span v-if="audioUploading">
                        <el-icon class="is-loading"><Loading /></el-icon> 正在处理录音...
                      </span>
                      <span v-else>拖拽录音文件 或 <em>点击上传</em></span>
                    </div>
                    <template #tip>
                      <div class="el-upload__tip">
                        <span v-if="audioUploading">
                          进度 {{ audioUploadProgress }}% —
                          <template v-if="audioUploadProgress < 50">压缩音频中...</template>
                          <template v-else-if="audioUploadProgress < 80">语音识别中...</template>
                          <template v-else>生成总结中...</template>
                        </span>
                        <span v-else>支持 WAV/MP3/M4A/OGG/FLAC/AAC/OPUS，压缩后 32kbps 存储</span>
                      </div>
                    </template>
                  </el-upload>
                  <el-progress v-if="audioUploading" :percentage="audioUploadProgress" :stroke-width="6" style="margin-top: 12px;" />
                </div>
              </div>
            </el-form-item>
          </template>

          <!-- 标签 -->
          <div class="section-header">
            <span class="section-icon"><el-icon><PriceTag /></el-icon></span>
            <span class="section-title">活动标签</span>
          </div>
          <el-form-item label="标签">
            <el-select v-model="form.tags" multiple placeholder="请选择标签" style="width: 100%;">
              <el-option v-for="d in activityTagDicts" :key="d.code" :label="d.name" :value="d.code" />
            </el-select>
          </el-form-item>

          <!-- 关联项目（仅编辑模式或已关联时显示） -->
          <template v-if="editMode === 'create' || editingItem.linked_project_id || form._linkProject">
            <div class="section-header">
              <span class="section-icon"><el-icon><Connection /></el-icon></span>
              <span class="section-title">关联项目</span>
            </div>
            <el-form-item v-if="editingItem.linked_project_id" label="已关联项目">
              <div class="linked-project-display">
                <el-tag type="warning" effect="plain" size="large">{{ editingItem.linked_project_name }}</el-tag>
                <el-popconfirm title="确定取消与该项目的关联吗？（招商动态记录将保留）" confirm-button-text="确定" cancel-button-text="取消" @confirm="handleUnlink">
                  <template #reference>
                    <el-button type="danger" size="small" :loading="unlinking" style="margin-left: 10px;">取消关联</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </el-form-item>
            <el-form-item v-else label="关联项目">
              <div class="link-project-row">
                <el-select v-model="form._linkProjectId" placeholder="选择要关联的招商项目" filterable clearable style="flex: 1;">
                  <el-option v-for="p in projectList" :key="p.id" :label="p.project_name" :value="p.id" />
                </el-select>
                <span class="link-hint">选择项目后保存，系统将自动把该活动写入对应项目的招商动态</span>
              </div>
            </el-form-item>
          </template>

          <div class="drawer-footer">
            <el-button @click="editDrawerVisible = false">取消</el-button>
            <el-button v-if="editMode === 'edit' && !editingItem.linked_project_id" type="warning" @click="form._linkProject = !form._linkProject">
              <el-icon><Connection /></el-icon> {{ form._linkProject ? '取消关联' : '关联项目' }}
            </el-button>
            <el-button type="primary" :loading="saving" @click="handleSave">{{ editMode === 'create' ? '创建' : '保存' }}</el-button>
          </div>
        </el-form>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Document, Plus, Delete, UploadFilled, InfoFilled, PriceTag, Connection, View, Close, Edit, Headset, Loading, VideoPlay } from '@element-plus/icons-vue'
import BusinessNavbar from '@/components/common/BusinessNavbar.vue'
import ProjectDrawer from '@/components/investment/ProjectDrawer.vue'
import { getLedgerList, createLedger, updateLedger, getLedger, deleteLedger, batchDeleteLedger, linkToProject, unlinkFromProject, uploadAudio, getAudioDetail, deleteAudio } from '@/api/activityLedger'
import { getPublicProjects, getProject } from '@/api/investment'
import { getDictItems } from '@/api/dict'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import { maskName, maskContent } from '@/utils/mask'

const businessAuth = useBusinessAuthStore()

function dn(v) { return businessAuth.isVisitor ? maskName(v) : (v || '') }
function dc(v) { return businessAuth.isVisitor ? maskContent(v) : (v || '') }

const tableRef = ref(null)
const items = ref([])
const loading = ref(false)
const searchText = ref('')
const filterTags = ref([])
const filterLinked = ref('')
const filterDateRange = ref([])
const filterDateFrom = ref('')
const filterDateTo = ref('')
const selectedIds = ref([])
const projectList = ref([])

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 字典
const activityTagDicts = ref([])

let searchTimer = null

// 查看抽屉
const viewDrawerVisible = ref(false)
const viewItem = ref(null)

// 项目详情抽屉
const projectDrawerVisible = ref(false)
const projectDrawerProject = ref(null)

// 编辑抽屉
const editDrawerVisible = ref(false)
const editMode = ref('create')
const editingId = ref(null)
const editingItem = ref({})
const formRef = ref(null)
const uploadRef = ref(null)
const saving = ref(false)
const unlinking = ref(false)
const fileList = ref([])
const audioUploading = ref(false)
const audioUploadProgress = ref(0)
const audioFile = ref(null)       // 当前录音文件信息
const audioDetail = ref(null)     // 录音详情（转写+总结）
const audioLoading = ref(false)   // 正在获取录音详情
const uploadUrl = '/api/upload'
const uploadHeaders = {}

const defaultForm = () => ({
  date: '',
  content: '',
  files: [],
  tags: [],
  _linkProject: false,
  _linkProjectId: ''
})

const form = reactive(defaultForm())

const rules = {
  content: [{ required: true, message: '请输入活动内容', trigger: 'blur' }]
}

onMounted(async () => {
  await loadProjects()
  await loadDicts()
  fetchData()
})

async function loadDicts() {
  try {
    const res = await getDictItems('activity_tags')
    if (res.code === 0) activityTagDicts.value = res.data || []
  } catch { /* ignore */ }
}

function getTagName(code) {
  return activityTagDicts.value.find(d => d.code === code)?.name || code
}

async function loadProjects() {
  try {
    const res = await getPublicProjects()
    if (res.code === 0) projectList.value = res.data || []
  } catch { /* ignore */ }
}

async function fetchData() {
  loading.value = true
  try {
    const params = { page: currentPage.value, page_size: pageSize.value }
    if (searchText.value) params.search = searchText.value
    if (filterDateFrom.value) params.date_from = filterDateFrom.value
    if (filterDateTo.value) params.date_to = filterDateTo.value
    if (filterTags.value.length > 0) params.tags = filterTags.value.join(',')
    if (filterLinked.value) params.linked = filterLinked.value
    const res = await getLedgerList(params)
    items.value = res.data || []
    total.value = res.total || 0
  } catch { items.value = [] }
  finally { loading.value = false }
}

function handleSearch() { currentPage.value = 1; clearTimeout(searchTimer); searchTimer = setTimeout(fetchData, 300) }

function onDateRangeChange(vals) {
  if (vals && vals.length === 2) {
    filterDateFrom.value = vals[0]
    filterDateTo.value = vals[1]
  } else {
    filterDateFrom.value = ''
    filterDateTo.value = ''
  }
  currentPage.value = 1
  fetchData()
}

function handlePageChange(page) { currentPage.value = page; fetchData() }
function handlePageSizeChange(size) { pageSize.value = size; currentPage.value = 1; fetchData() }
function handleSelectionChange(selection) { selectedIds.value = selection.map(s => s.id) }

function truncate(text, max) { if (!text) return ''; return text.length > max ? text.slice(0, max) + '...' : text }
function fmtDt(d) { if (!d) return '-'; return new Date(d + 'Z').toLocaleString('zh-CN', { hour12: false }) }

// ---- 查看抽屉文件辅助 ----
function getViewFileName(url) {
  if (!url) return ''
  return decodeURIComponent(url.split('/').pop() || url)
}
function getViewFileExt(url) {
  const name = getViewFileName(url)
  return name.split('.').pop().toLowerCase()
}
function isImageUrl(url) {
  const ext = getViewFileExt(url)
  return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)
}
function isPdfUrl(url) {
  return getViewFileExt(url) === 'pdf' || (url || '').toLowerCase().includes('.pdf')
}
function openFile(url) {
  if (url) window.open(url, '_blank')
}

// ---- 查看 ----
function handleView(row) {
  viewItem.value = row
  viewDrawerVisible.value = true
}

// ---- 项目详情 ----
async function handleProjectClick(row) {
  if (!row.linked_project_id) return
  try {
    const res = await getProject(row.linked_project_id)
    if (res.code === 0) {
      projectDrawerProject.value = res.data
      projectDrawerVisible.value = true
    }
  } catch (err) {
    ElMessage.error('获取项目详情失败')
  }
}

// ---- 批量删除 ----
async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedIds.value.length} 条活动台账吗？此操作不可恢复。`,
      '批量删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    const res = await batchDeleteLedger(selectedIds.value)
    if (res.code === 0) {
      ElMessage.success(res.message)
      selectedIds.value = []
      fetchData()
    }
  } catch { /* cancelled */ }
}

// ---- 新建 ----
function openCreate() {
  editMode.value = 'create'
  editingId.value = null
  editingItem.value = {}
  resetForm()
  fileList.value = []
  audioFile.value = null
  audioDetail.value = null
  editDrawerVisible.value = true
}

// ---- 编辑 ----
async function openEdit(row) {
  editMode.value = 'edit'
  editingId.value = row.id
  audioFile.value = null
  audioDetail.value = null
  try {
    const res = await getLedger(row.id)
    if (res.code === 0) {
      const d = res.data
      editingItem.value = d
      form.date = d.date ? d.date.substring(0, 10) : ''
      form.content = d.content || ''
      form.files = d.files || []
      form.tags = Array.isArray(d.tags) ? [...d.tags] : []
      form._linkProject = !!d.linked_project_id
      form._linkProjectId = ''
      // 加载录音详情
      if (d.audio_file) {
        audioFile.value = { audio_file: d.audio_file, audio_duration: d.audio_duration }
        audioDetail.value = {
          audio_transcript: d.audio_transcript,
          audio_summary: d.audio_summary,
          audio_duration: d.audio_duration,
          compression_ratio: null
        }
      }
      try {
        fileList.value = Array.isArray(d.files) ? d.files.map((url, i) => ({ name: url.split('/').pop() || `文件${i+1}`, url })) : []
      } catch { fileList.value = [] }
    }
    editDrawerVisible.value = true
  } catch (err) { ElMessage.error(err.message) }
}

function resetForm() {
  Object.assign(form, defaultForm())
  fileList.value = []
  audioFile.value = null
  audioDetail.value = null
  audioUploading.value = false
  audioUploadProgress.value = 0
  editingItem.value = {}
  formRef.value?.clearValidate()
}

// ---- 文件上传 ----
function handleUploadSuccess(response, file) {
  if (response.code === 0) { file.url = response.data.url }
}
function handleUploadError() { ElMessage.error('文件上传失败') }
function beforeUpload(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  const allowed = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg']
  if (!allowed.includes(ext)) {
    ElMessage.error(`不支持的文件类型: .${ext}`)
    return false
  }
  return true
}
function handleFileRemove(file) {
  const idx = fileList.value.findIndex(f => f.url === file.url || f.uid === file.uid)
  if (idx > -1) fileList.value.splice(idx, 1)
}

// ---- 剪贴板粘贴图片 ----
async function handleClipboardPaste(event) {
  const items = event.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      event.preventDefault()
      const blob = item.getAsFile()
      if (!blob) continue
      const ext = item.type.split('/')[1] || 'png'
      const filename = `paste-${Date.now()}.${ext}`
      const file = new File([blob], filename, { type: item.type })
      const formData = new FormData()
      formData.append('file', file)
      try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData })
        const data = await res.json()
        if (data.code === 0) {
          fileList.value.push({
            name: filename,
            url: data.data.url,
            uid: Date.now() + Math.random()
          })
          ElMessage.success('图片已粘贴上传')
        } else {
          ElMessage.error(data.message || '图片上传失败')
        }
      } catch {
        ElMessage.error('图片上传失败')
      }
    }
  }
}

// ---- 文件缩略图辅助 ----
function getFileExtension(file) {
  const name = getFileName(file)
  return name.split('.').pop().toLowerCase()
}
function getFileName(file) {
  return file.name || (file.url ? file.url.split('/').pop() : '未知文件')
}
function isImageFile(file) {
  const ext = getFileExtension(file)
  const query = (file.url || '').split('?')[0]
  const urlExt = query.split('.').pop().toLowerCase()
  return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext) ||
         ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(urlExt)
}
function isPdfFile(file) {
  return getFileExtension(file) === 'pdf' || (file.url || '').toLowerCase().includes('.pdf')
}
function getFilePreviewUrl(file) {
  if (file.url) return file.url
  if (file.raw) return URL.createObjectURL(file.raw)
  return ''
}
function handleThumbRemove(idx) {
  const file = fileList.value[idx]
  if (file) {
    if (file.previewUrl && file.raw) {
      URL.revokeObjectURL(file.previewUrl)
    }
  }
  fileList.value.splice(idx, 1)
}

// ---- 录音上传 ----
async function handleAudioUpload(file) {
  if (!editingId.value) {
    ElMessage.warning('请先保存活动台账，再上传录音文件')
    return
  }
  const ext = file.name.split('.').pop().toLowerCase()
  const audioExts = ['wav', 'mp3', 'm4a', 'ogg', 'flac', 'wma', 'aac', 'amr', 'opus', 'weba', 'webm']
  if (!audioExts.includes(ext)) {
    ElMessage.error(`不支持的音频格式：.${ext}，支持：${audioExts.join(', ')}`)
    return
  }
  audioUploading.value = true
  audioUploadProgress.value = 0
  try {
    const res = await uploadAudio(editingId.value, file, (progressEvent) => {
      audioUploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 50)
    })
    // 模拟处理阶段的进度（50%-100%）
    audioUploadProgress.value = 60
    if (res.code === 0) {
      audioUploadProgress.value = 100
      audioFile.value = res.data
      audioDetail.value = {
        audio_transcript: res.data.audio_transcript,
        audio_summary: res.data.audio_summary,
        audio_duration: res.data.audio_duration,
        audio_file: res.data.audio_file,
        compressed_size: res.data.compressed_size,
        compression_ratio: res.data.compression_ratio
      }
      ElMessage.success('录音处理完成！已自动生成转写文本和内容总结')
      // 同步刷新表格
      fetchData()
    } else {
      ElMessage.error(res.message || '录音处理失败')
    }
  } catch (err) {
    ElMessage.error('录音上传失败：' + (err.message || '网络错误'))
  } finally {
    audioUploading.value = false
  }
}

// 手动选择音频文件
function onAudioFileChange(file) {
  handleAudioUpload(file.raw || file)
}

// 加载录音详情
async function loadAudioDetail(id) {
  audioLoading.value = true
  try {
    const res = await getAudioDetail(id)
    if (res.code === 0 && res.data?.audio_file) {
      audioDetail.value = res.data
      audioFile.value = { audio_file: res.data.audio_file, audio_duration: res.data.audio_duration }
    } else {
      audioDetail.value = null
      audioFile.value = null
    }
  } catch {
    audioDetail.value = null
    audioFile.value = null
  } finally {
    audioLoading.value = false
  }
}

// 删除录音
async function handleDeleteAudio() {
  if (!editingId.value) return
  try {
    await ElMessageBox.confirm('确定要删除该录音文件及转写/总结数据吗？', '删除确认', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    const res = await deleteAudio(editingId.value)
    if (res.code === 0) {
      ElMessage.success('录音已删除')
      audioFile.value = null
      audioDetail.value = null
      fetchData()
    }
  } catch { /* cancelled */ }
}

// 格式化文件大小
function formatFileSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / 1024 / 1024).toFixed(1) + 'MB'
}

// 格式化时长
function formatDuration(seconds) {
  if (!seconds) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return m > 0 ? `${m}分${s}秒` : `${s}秒`
}

// ---- 保存 ----
async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    ElMessage.warning('请填写必填字段（活动内容不能为空）')
    return
  }

  saving.value = true
  try {
    const docUrls = fileList.value.filter(f => f.url).map(f => f.url)
    const data = {
      date: form.date,
      content: form.content,
      files: docUrls,
      tags: form.tags
    }

    if (editMode.value === 'create') {
      await createLedger(data)
      ElMessage.success('活动台账创建成功')
      editDrawerVisible.value = false
      fetchData()
    } else {
      await updateLedger(editingId.value, data)
      // 如果设置了关联项目，执行关联
      if (form._linkProjectId) {
        try {
          const linkRes = await linkToProject(editingId.value, form._linkProjectId)
          ElMessage.success(linkRes.message || '已关联至项目')
        } catch (err) {
          ElMessage.warning('内容已更新，但关联项目失败：' + (err.message || '未知错误'))
        }
      }
      ElMessage.success('活动台账更新成功')
      editDrawerVisible.value = false
      fetchData()
    }
  } catch (err) { ElMessage.error(err.message) }
  finally { saving.value = false }
}

// ---- 取消关联 ----
async function handleUnlink() {
  unlinking.value = true
  try {
    const res = await unlinkFromProject(editingId.value)
    ElMessage.success(res.message || '已取消关联')
    editingItem.value = { ...editingItem.value, linked_project_id: null, linked_project_name: '' }
    form._linkProject = false
    form._linkProjectId = ''
    fetchData()
  } catch (err) { ElMessage.error(err.message) }
  finally { unlinking.value = false }
}

// ---- 删除 ----
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除该活动台账吗？`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    await deleteLedger(row.id)
    ElMessage.success('活动台账已删除')
    fetchData()
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.activity-page { min-height: 100vh; background: linear-gradient(160deg, #dce8f5 0%, #c8daf0 50%, #b0c8e8 100%); }
.page-body { max-width: 1600px; margin: 0 auto; padding: 28px 32px 60px; }

.content-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.search-input { width: 260px; }
.toolbar-spacer { flex: 1; }

/* 表格内样式 */
.date-cell { font-size: 13px; color: #606266; }
.content-preview { font-size: 13px; color: #303133; cursor: default; }
.no-data { color: #c0c4cc; font-size: 13px; }

/* 详情抽屉 */
.drawer-title-bar {
  background: linear-gradient(135deg, #5b9bd5 0%, #8ab8e8 100%);
  margin: 0 -20px 0 -20px;
  padding: 20px 20px 20px 40px;
}
.drawer-title {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.detail-desc :deep(.el-descriptions__label) { width: 100px; font-weight: 500; color: #606266; }
.text-block { white-space: pre-wrap; line-height: 1.7; font-size: 13px; color: #303133; max-height: 300px; overflow-y: auto; }
.doc-link { color: #409eff; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }
.doc-link:hover { text-decoration: underline; }

/* 编辑抽屉 */
.drawer-form { padding: 0 10px; }
.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}
.section-header:first-child { margin-top: 0; }
.section-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: #ecf5ff;
  color: #409eff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
}
.section-title { font-weight: 600; font-size: 14px; color: #303133; }

.drawer-footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.upload-wrapper { width: 100%; }

/* 文件缩略图网格 */
.file-thumbnail-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}
.file-thumb-card {
  width: 120px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  transition: box-shadow 0.2s;
}
.file-thumb-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.thumb-preview {
  width: 100%;
  height: 90px;
  position: relative;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
}
.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-pdf {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: #e6a23c;
}
.thumb-pdf span {
  font-size: 11px;
  font-weight: 600;
  color: #e6a23c;
}
.thumb-generic {
  color: #909399;
}
.thumb-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0,0,0,0.5);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
}
.thumb-preview:hover .thumb-remove { opacity: 1; }
.thumb-name {
  padding: 4px 8px;
  font-size: 11px;
  color: #606266;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.linked-project-display {
  display: flex;
  align-items: center;
}
.link-project-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.link-hint { font-size: 12px; color: #909399; }
</style>

<style>
.el-drawer__header {
  margin-bottom: 0 !important;
  padding: 0 !important;
}
.el-drawer__body {
  padding: 12px 20px 20px !important;
}

/* 录音上传区域 */
.audio-section {
  width: 100%;
}
.audio-loaded {
  width: 100%;
}
.audio-player-card {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  background: #f0f9ff;
  border: 1px solid #d0e8ff;
  border-radius: 8px;
  margin-bottom: 12px;
}
.audio-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #409eff;
  font-size: 13px;
  font-weight: 500;
}
.audio-size {
  color: #909399;
  font-size: 12px;
}
.audio-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.mini-audio-player {
  height: 32px;
  max-width: 220px;
}
.audio-upload-wrapper {
  width: 100%;
}
.audio-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px dashed #e0e0e0;
}
.section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}
.audio-text-content {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 13px;
  color: #303133;
  max-height: 240px;
  overflow-y: auto;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}
.audio-summary-content {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 13px;
  color: #303133;
  max-height: 300px;
  overflow-y: auto;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}
.audio-transcript-section,
.audio-summary-section {
  margin-top: 12px;
}

/* 查看抽屉中的录音卡片 */
.view-audio-card {
  width: 100%;
}
.view-audio-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.view-audio-player {
  height: 36px;
  max-width: 300px;
}
.view-audio-text,
.view-audio-summary {
  margin-top: 0;
}
</style>
