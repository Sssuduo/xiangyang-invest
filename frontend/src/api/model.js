import api from './index'

export function getModels() {
  return api.get('/models')
}

export function getAdminModels() {
  return api.get('/admin/models')
}

export function getAdminModel(id) {
  return api.get(`/admin/models/${id}`)
}

export function createModel(data) {
  return api.post('/admin/models', data)
}

export function updateModel(id, data) {
  return api.put(`/admin/models/${id}`, data)
}

export function deleteModel(id) {
  return api.delete(`/admin/models/${id}`)
}

export function testModel(id) {
  return api.post(`/admin/models/${id}/test`)
}
