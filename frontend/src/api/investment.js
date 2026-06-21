import api from './index'

// 公开 API
export function getPublicProjects(params = {}) {
  return api.get('/investment/projects', { params })
}

// 后台字典
export function getDicts() {
  return api.get('/admin/investment/dicts')
}

// 后台项目 CRUD
export function getProjects(params = {}) {
  return api.get('/admin/investment/projects', { params })
}

export function createProject(data) {
  return api.post('/admin/investment/projects', data)
}

export function getProject(id) {
  return api.get(`/admin/investment/projects/${id}`)
}

export function updateProject(id, data) {
  return api.put(`/admin/investment/projects/${id}`, data)
}

export function deleteProject(id) {
  return api.delete(`/admin/investment/projects/${id}`)
}

// 获取最大顺序号
export function getMaxOrderNo() {
  return api.get('/admin/investment/max-order-no')
}

// 企业诉求 CRUD
export function getDemands(projectId) {
  return api.get(`/admin/investment/projects/${projectId}/demands`)
}

export function createDemand(projectId, data) {
  return api.post(`/admin/investment/projects/${projectId}/demands`, data)
}

export function updateDemand(projectId, demandId, data) {
  return api.put(`/admin/investment/projects/${projectId}/demands/${demandId}`, data)
}

export function deleteDemand(projectId, demandId) {
  return api.delete(`/admin/investment/projects/${projectId}/demands/${demandId}`)
}
