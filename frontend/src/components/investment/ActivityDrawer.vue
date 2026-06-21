<template>
  <el-drawer v-model="visible" title="动态详情" direction="rtl" size="560px" :before-close="handleClose">
    <template v-if="activity">
      <el-descriptions :column="2" border size="small" class="detail-desc">
        <el-descriptions-item label="所属项目" :span="2">
          <strong>{{ activity.project_name }}</strong>
        </el-descriptions-item>
        <el-descriptions-item label="日期" :span="2">
          {{ activity.date || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="动态内容" :span="2">
          <div class="text-block">{{ activity.content || '-' }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="附件" :span="2">
          <template v-if="activity.files && activity.files.length > 0">
            <div class="file-list">
              <a
                v-for="(url, idx) in activity.files"
                :key="idx"
                :href="url"
                target="_blank"
                class="file-link"
              >
                <el-icon><Document /></el-icon>
                <span class="file-name">{{ getFileName(url) }}</span>
              </a>
            </div>
          </template>
          <span v-else class="no-data">-</span>
        </el-descriptions-item>
        <el-descriptions-item label="写入时间">{{ fmtDt(activity.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="最后更新">{{ fmtDt(activity.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </template>
  </el-drawer>
</template>

<script setup>
import { computed } from 'vue'
import { Document } from '@element-plus/icons-vue'

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
</script>

<style scoped>
.detail-desc :deep(.el-descriptions__label) {
  width: 100px; font-weight: 500; color: #606266;
}
.text-block {
  white-space: pre-wrap; line-height: 1.7; font-size: 13px;
  color: #303133; max-height: 300px; overflow-y: auto;
}
.file-list {
  display: flex; flex-direction: column; gap: 6px;
}
.file-link {
  display: inline-flex; align-items: center; gap: 6px;
  color: #409eff; text-decoration: none; font-size: 13px;
}
.file-link:hover { text-decoration: underline; }
.file-name {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: 400px;
}
.no-data { color: #909399; }
</style>
