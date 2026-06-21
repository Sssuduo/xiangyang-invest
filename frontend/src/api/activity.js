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
