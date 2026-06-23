import api from './index'

export function getBusinessUsers() {
  return api.get('/admin/business-users')
}

export function getBusinessUser(id) {
  return api.get(`/admin/business-users/${id}`)
}

export function createBusinessUser(data) {
  return api.post('/admin/business-users', data)
}

export function updateBusinessUser(id, data) {
  return api.put(`/admin/business-users/${id}`, data)
}

export function deleteBusinessUser(id) {
  return api.delete(`/admin/business-users/${id}`)
}
