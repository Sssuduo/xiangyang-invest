import api from './index'

export function getPrompts() {
  return api.get('/prompts')
}

export function getAdminPrompts() {
  return api.get('/admin/prompts')
}

export function getAdminPrompt(id) {
  return api.get(`/admin/prompts/${id}`)
}

export function createPrompt(data) {
  return api.post('/admin/prompts', data)
}

export function updatePrompt(id, data) {
  return api.put(`/admin/prompts/${id}`, data)
}

export function deletePrompt(id) {
  return api.delete(`/admin/prompts/${id}`)
}
