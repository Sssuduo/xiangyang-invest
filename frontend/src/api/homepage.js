import api from './index'

export function getHomepageConfig() {
  return api.get('/homepage')
}

export function updateHomepageConfig(data) {
  return api.put('/admin/homepage', data)
}

export function getAdminHomepageConfig() {
  return api.get('/admin/homepage')
}
