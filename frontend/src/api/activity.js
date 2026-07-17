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
