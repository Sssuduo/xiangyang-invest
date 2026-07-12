import api from './index'

export function getDicts() {
  return api.get('/admin/lead/dicts')
}
export function getLeads(params = {}) {
  return api.get('/admin/lead/leads', { params })
}
export function getLead(id) {
  return api.get(`/admin/lead/leads/${id}`)
}
export function createLead(data) {
  return api.post('/admin/lead/leads', data)
}
export function updateLead(id, data) {
  return api.put(`/admin/lead/leads/${id}`, data)
}
export function deleteLead(id) {
  return api.delete(`/admin/lead/leads/${id}`)
}
export function batchDeleteLeads(ids) {
  return api.post('/admin/lead/leads/batch-delete', { ids })
}
export function getMaxOrderNo() {
  return api.get('/admin/lead/max-order-no')
}
export function assessLead(id, modelId = null) {
  return api.post(`/admin/lead/leads/${id}/assess`, { model_id: modelId })
}
export function getAssessmentStatus(id) {
  return api.get(`/admin/lead/leads/${id}/assessment-status`)
}
export function convertLead(id) {
  return api.post(`/admin/lead/leads/${id}/convert`)
}

// AI 研判会话
export function createAssessmentSession(leadId, data) {
  return api.post(`/admin/lead/leads/${leadId}/assessment-sessions`, data)
}
export function getAssessmentSessions(leadId) {
  return api.get(`/admin/lead/leads/${leadId}/assessment-sessions`)
}
export function getSessionMessages(sessionId) {
  return api.get(`/admin/lead/assessment-sessions/${sessionId}/messages`)
}
export function sendFollowUpQuestion(sessionId, data) {
  return api.post(`/admin/lead/assessment-sessions/${sessionId}/messages`, data)
}
export function getDownloadUrl(sessionId, messageId) {
  return `/api/admin/lead/assessment-sessions/${sessionId}/messages/${messageId}/download`
}
export function getPromptPreview(leadId, modelId = null) {
  const params = modelId ? { model_id: modelId } : {}
  return api.get(`/admin/lead/leads/${leadId}/prompt-preview`, { params })
}
export function deleteAssessmentSession(sessionId) {
  return api.delete(`/admin/lead/assessment-sessions/${sessionId}`)
}
export function deleteAssessmentMessage(sessionId, messageId) {
  return api.delete(`/admin/lead/assessment-sessions/${sessionId}/messages/${messageId}`)
}
