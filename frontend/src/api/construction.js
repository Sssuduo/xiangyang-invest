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

// 工作进展 CRUD
export function getProgressList(params = {}) {
  return api.get('/admin/construction/progress', { params })
}

export function createProgress(data) {
  return api.post('/admin/construction/progress', data)
}

export function updateProgress(id, data) {
  return api.put(`/admin/construction/progress/${id}`, data)
}

export function deleteProgress(id) {
  return api.delete(`/admin/construction/progress/${id}`)
}

// 调度问题 CRUD
export function getIssueList(params = {}) {
  return api.get('/admin/construction/issues', { params })
}

export function createIssue(data) {
  return api.post('/admin/construction/issues', data)
}

export function updateIssue(id, data) {
  return api.put(`/admin/construction/issues/${id}`, data)
}

export function deleteIssue(id) {
  return api.delete(`/admin/construction/issues/${id}`)
}
