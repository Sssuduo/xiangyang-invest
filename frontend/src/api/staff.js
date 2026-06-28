import api from './index'

export function getStaffList() {
  return api.get('/admin/staff')
}

export function createStaff(data) {
  return api.post('/admin/staff', data)
}

export function updateStaff(id, data) {
  return api.put(`/admin/staff/${id}`, data)
}

export function deleteStaff(id) {
  return api.delete(`/admin/staff/${id}`)
}

export function getAdminUsers() {
  return api.get('/admin/staff/admins')
}
