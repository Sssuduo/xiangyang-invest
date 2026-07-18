import api from './index'

export function login(username, password) {
  return api.post('/admin/login', { username, password })
}

export function logout() {
  return api.post('/admin/logout')
}

export function checkLogin() {
  return api.get('/admin/check')
}

// ============================================================
// 消息提醒规则
// ============================================================
export function listMessageRules() {
  return api.get('/admin/message-rules')
}
export function createMessageRule(data) {
  return api.post('/admin/message-rules', data)
}
export function updateMessageRule(id, data) {
  return api.put(`/admin/message-rules/${id}`, data)
}
export function deleteMessageRule(id) {
  return api.delete(`/admin/message-rules/${id}`)
}
export function toggleMessageRule(id) {
  return api.post(`/admin/message-rules/${id}/toggle`)
}
