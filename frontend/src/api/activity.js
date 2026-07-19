import api from './index'

// 公开 API
export function getPublicActivities(params = {}) {
  return api.get('/investment/activities', { params })
}

// 管理 API — CRUD
export function getActivities(params = {}) {
  return api.get('/admin/activity/activities', { params })
}

export function createActivity(data) {
  return api.post('/admin/activity/activities', data)
}

export function getActivity(id) {
  return api.get(`/admin/activity/activities/${id}`)
}

export function updateActivity(id, data) {
  return api.put(`/admin/activity/activities/${id}`, data)
}

export function deleteActivity(id) {
  return api.delete(`/admin/activity/activities/${id}`)
}

export function batchDeleteActivities(ids) {
  return api.post('/admin/activity/activities/batch-delete', { ids })
}

// ---- 招商动态 - 录音识别（V15.4）----
export function uploadActivityAudio(id, file, onProgress, appendMode = false) {
  const formData = new FormData()
  formData.append('file', file)
  if (appendMode) formData.append('append', 'true')
  return api.post(`/admin/activity/${id}/audio`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
    timeout: 600000
  })
}

export function getActivityAudioDetail(id) {
  return api.get(`/admin/activity/${id}/audio`)
}

export function retryActivityAudio(id) {
  return api.post(`/admin/activity/${id}/audio/retry`)
}

export function cancelActivityAudio(id) {
  return api.post(`/admin/activity/${id}/audio/cancel`)
}

export function deleteActivityAudio(id) {
  return api.delete(`/admin/activity/${id}/audio`)
}

export function deleteActivityAudioFile(id, fileIndex) {
  return api.delete(`/admin/activity/${id}/audio/${fileIndex}`)
}

// ---- V15.1 招商动态录音能力升级（对齐活动台账）----
export function updateActivityAudioTranscript(id, data) {
  // data: { transcript?, summary? } 字段级独立保存（对齐 activityLedger.js:56）
  return api.put(`/admin/activity/${id}/audio/transcript`, data)
}

export function getActivityAudioVersions(id) {
  // 获取结构化总结多版本（对齐 activityLedger.js:66）
  return api.get(`/admin/activity/${id}/audio/versions`)
}

export function getActivityAudioDocxUrl(id) {
  // 返回 docx 下载 URL（对齐 activityLedger.js:71）
  return `/api/admin/activity/${id}/audio/docx`
}

export function retryActivityAudioSummary(id, data = {}) {
  // data: { model_id? } 单独重总结（对齐 activityLedger.js:77）
  return api.post(`/admin/activity/${id}/audio/retry-summary`, data)
}

export function getLLMModels() {
  // LLM 模型列表（对齐 activityLedger.js:82，共用 /llm-models）
  return api.get('/llm-models')
}

export function cancelActivityAudioProcessing(id) {
  // 取消处理（对齐 activityLedger.js:104）
  return api.post(`/admin/activity/${id}/audio/cancel`)
}

// ---- V15.1 术语校正（对齐活动台账，共用 /api/admin/term-corrections）----
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
