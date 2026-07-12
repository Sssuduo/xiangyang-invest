import api from './index'

// 活动台账 CRUD
export function getLedgerList(params = {}) {
  return api.get('/admin/activity-ledger', { params })
}

export function createLedger(data) {
  return api.post('/admin/activity-ledger', data)
}

export function getLedger(id) {
  return api.get(`/admin/activity-ledger/${id}`)
}

export function updateLedger(id, data) {
  return api.put(`/admin/activity-ledger/${id}`, data)
}

export function deleteLedger(id) {
  return api.delete(`/admin/activity-ledger/${id}`)
}

export function batchDeleteLedger(ids) {
  return api.post('/admin/activity-ledger/batch-delete', { ids })
}

// 关联 / 取消关联项目
export function linkToProject(id, projectId) {
  return api.post(`/admin/activity-ledger/${id}/link`, { project_id: projectId })
}

export function unlinkFromProject(id) {
  return api.post(`/admin/activity-ledger/${id}/unlink`)
}

// 录音文件上传（FormData，异步处理：上传后立即返回，ASR 后台执行）
// appendMode: true 时追加到已有文件列表而非覆盖
export function uploadAudio(id, file, onProgress, appendMode = false) {
  const formData = new FormData()
  formData.append('file', file)
  if (appendMode) formData.append('append', 'true')
  return api.post(`/admin/activity-ledger/${id}/audio`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
    timeout: 600000  // 10 分钟超时
  })
}

// 获取录音处理状态及详情（用于轮询）
export function getAudioDetail(id) {
  return api.get(`/admin/activity-ledger/${id}/audio`)
}

// 手动编辑转写文本/总结
export function updateAudioTranscript(id, data) {
  return api.put(`/admin/activity-ledger/${id}/audio/transcript`, data)
}

// 重新识别（失败重试）
export function retryAudioRecognition(id) {
  return api.post(`/admin/activity-ledger/${id}/audio/retry`)
}

// 获取结构化总结多版本 (segmented/clean/summary/docx)
export function getAudioVersions(id) {
  return api.get(`/admin/activity-ledger/${id}/audio/versions`)
}

// 下载结构化总结 docx
export function getAudioDocxUrl(id) {
  return `/api/admin/activity-ledger/${id}/audio/docx`
}

// 单独重新总结（不重跑 ASR）
export function retryAudioSummary(id) {
  return api.post(`/admin/activity-ledger/${id}/audio/retry-summary`)
}

// ---- 术语校正 ----
export function getTermCorrections() {
  return api.get('/api/admin/term-corrections')
}
export function createTermCorrection(data) {
  return api.post('/api/admin/term-corrections', data)
}
export function updateTermCorrection(id, data) {
  return api.put(`/api/admin/term-corrections/${id}`, data)
}
export function deleteTermCorrection(id) {
  return api.delete(`/api/admin/term-corrections/${id}`)
}
export function applyTermCorrections(itemId) {
  return api.post('/api/admin/term-corrections/apply', { item_id: itemId })
}

// 删除录音
export function deleteAudio(id) {
  return api.delete(`/admin/activity-ledger/${id}/audio`)
}

// 删除单个录音文件
export function deleteAudioFile(id, fileIndex) {
  return api.delete(`/admin/activity-ledger/${id}/audio/${fileIndex}`)
}
