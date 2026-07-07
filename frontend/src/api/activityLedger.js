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

// 录音文件上传（FormData）
export function uploadAudio(id, file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/admin/activity-ledger/${id}/audio`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
    timeout: 600000  // 10 分钟超时
  })
}

// 获取录音详情
export function getAudioDetail(id) {
  return api.get(`/admin/activity-ledger/${id}/audio`)
}

// 删除录音
export function deleteAudio(id) {
  return api.delete(`/admin/activity-ledger/${id}/audio`)
}
