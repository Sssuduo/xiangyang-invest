import api from './index'

export function getCategories() {
  return api.get('/admin/knowledge/categories')
}
export function getEntries(params = {}) {
  return api.get('/admin/knowledge/entries', { params })
}
export function getEntry(id) {
  return api.get(`/admin/knowledge/entries/${id}`)
}
export function createEntry(data) {
  return api.post('/admin/knowledge/entries', data)
}
export function updateEntry(id, data) {
  return api.put(`/admin/knowledge/entries/${id}`, data)
}
export function deleteEntry(id) {
  return api.delete(`/admin/knowledge/entries/${id}`)
}
export function embedEntry(id) {
  return api.post(`/admin/knowledge/entries/${id}/embed`)
}
export function batchEmbedEntries(ids = null) {
  return api.post('/admin/knowledge/entries/batch-embed', ids ? { ids } : {})
}
export function getDrafts(params = {}) {
  return api.get('/admin/knowledge/drafts', { params })
}
export function approveDraft(id, data = {}) {
  return api.post(`/admin/knowledge/drafts/${id}/approve`, data)
}
export function rejectDraft(id, data = {}) {
  return api.post(`/admin/knowledge/drafts/${id}/reject`, data)
}
