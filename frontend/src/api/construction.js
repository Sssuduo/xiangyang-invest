import api from './index'

// 字典
export function getDicts() {
  return api.get('/admin/construction/dicts')
}

// 项目 CRUD
export function getProjects(params = {}) {
  return api.get('/admin/construction/projects', { params })
}

export function createProject(data) {
  return api.post('/admin/construction/projects', data)
}

export function getProject(id) {
  return api.get(`/admin/construction/projects/${id}`)
}

export function updateProject(id, data) {
  return api.put(`/admin/construction/projects/${id}`, data)
}

export function deleteProject(id) {
  return api.delete(`/admin/construction/projects/${id}`)
}

export function batchDeleteProjects(ids) {
  return api.post('/admin/construction/projects/batch-delete', { ids })
}

export function getMaxOrderNo() {
  return api.get('/admin/construction/max-order-no')
}
