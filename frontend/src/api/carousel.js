import api from './index'

export function getCarouselPages() {
  return api.get('/carousel/pages')
}

export function getCarouselPage(id) {
  return api.get(`/carousel/pages/${id}`)
}

export function getAdminPages() {
  return api.get('/admin/pages')
}

export function getAdminPage(id) {
  return api.get(`/admin/pages/${id}`)
}

export function createPage(data) {
  return api.post('/admin/pages', data)
}

export function updatePage(id, data) {
  return api.put(`/admin/pages/${id}`, data)
}

export function deletePage(id) {
  return api.delete(`/admin/pages/${id}`)
}

export function reorderPages(orders) {
  return api.put('/admin/pages/reorder', { orders })
}
