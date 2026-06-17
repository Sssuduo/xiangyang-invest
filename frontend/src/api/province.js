import api from './index'

export function getProvinces(scope = 'china') {
  return api.get('/provinces', { params: { scope } })
}

export function getAdminProvinces(scope = 'china') {
  return api.get('/admin/provinces', { params: { scope } })
}

export function getAdminProvince(id) {
  return api.get(`/admin/provinces/${id}`)
}

export function updateProvince(id, data) {
  return api.put(`/admin/provinces/${id}`, data)
}

export function batchUpdateHighlights(highlightIds, scope = 'china') {
  return api.post('/admin/provinces/batch', { highlight_ids: highlightIds, scope })
}
