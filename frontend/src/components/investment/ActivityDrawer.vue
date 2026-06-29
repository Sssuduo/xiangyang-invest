<template>
  <el-drawer v-model="visible" direction="rtl" size="560px" :before-close="handleClose">
    <template #header>
      <div class="drawer-title-bar">
        <span class="drawer-title">
          <el-icon><View /></el-icon>
          动态详情
        </span>
      </div>
    </template>
    <template v-if="activity">
      <el-descriptions :column="2" border size="small" class="detail-desc">
        <el-descriptions-item label="项目" :span="2">
          <strong>{{ dn(activity.project_name) }}</strong>
        </el-descriptions-item>
        <el-descriptions-item label="日期" :span="2">
          {{ activity.date || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="动态内容" :span="2">
          <div class="text-block">{{ dc(activity.content) || '-' }}</div>
        </el-descriptions-item>
        <el-descriptions-item v-if="activity._tagNames && activity._tagNames.length > 0" label="动态标签" :span="2">
          <el-tag v-for="(name, idx) in activity._tagNames" :key="idx" size="small" effect="plain" style="margin-right: 6px; margin-bottom: 4px;">
            {{ name }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="附件" :span="2">
          <template v-if="activity.files && activity.files.length > 0">
            <div class="file-thumbnail-grid">
              <div v-for="(url, idx) in activity.files" :key="idx" class="file-thumb-card" @click="openFile(url)">
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
                <div class="thumb-name" :title="getFileName(url)">{{ getFileName(url) }}</div>
              </div>
            </div>
          </template>
          <span v-else class="no-data">暂无附件</span>
        </el-descriptions-item>
        <el-descriptions-item label="写入时间">{{ fmtDt(activity.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="最后更新">{{ fmtDt(activity.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </template>
  </el-drawer>
</template>

<script setup>
import { computed } from 'vue'
import { Document, View } from '@element-plus/icons-vue'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import { maskName, maskContent } from '@/utils/mask'

const businessAuth = useBusinessAuthStore()

function dn(v) { return businessAuth.isVisitor ? maskName(v) : (v || '') }
function dc(v) { return businessAuth.isVisitor ? maskContent(v) : (v || '') }

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  activity: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue'])
const visible = computed({ get: () => props.modelValue, set: v => emit('update:modelValue', v) })

function handleClose() { emit('update:modelValue', false) }

function fmtDt(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN', { hour12: false })
}

function getFileName(url) {
  if (!url) return ''
  const parts = url.split('/')
  return decodeURIComponent(parts[parts.length - 1] || url)
}

function getFileExt(url) {
  const name = getFileName(url)
  return name.split('.').pop().toLowerCase()
}
function isImageUrl(url) {
  const ext = getFileExt(url)
  return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)
}
function isPdfUrl(url) {
  return getFileExt(url) === 'pdf' || (url || '').toLowerCase().includes('.pdf')
}
function openFile(url) {
  if (url) window.open(url, '_blank')
}
</script>

<style scoped>
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

.detail-desc :deep(.el-descriptions__label) {
  width: 100px; font-weight: 500; color: #606266;
}
.text-block {
  white-space: pre-wrap; line-height: 1.7; font-size: 13px;
  color: #303133; max-height: 300px; overflow-y: auto;
}
.no-data { color: #909399; }

/* 文件缩略图网格 */
.file-thumbnail-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.file-thumb-card {
  width: 120px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.file-thumb-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.12); }
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
.thumb-name {
  padding: 4px 8px;
  font-size: 11px;
  color: #606266;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

<style>
.el-drawer__header {
  margin-bottom: 0 !important;
  padding: 0 !important;
}
.el-drawer__body {
  padding: 12px 20px 20px !important;
}
</style>
