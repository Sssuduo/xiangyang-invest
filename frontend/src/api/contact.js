import api from './index'

export function getContactInfo() {
  return api.get('/contact')
}

export function getAdminContactInfo() {
  return api.get('/admin/contact')
}

export function updateContactInfo(data) {
  return api.put('/admin/contact', data)
}
