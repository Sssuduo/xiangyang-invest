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

// ---- 城市高亮（省份子级） ----
export function getProvinceCities(provinceId) {
  return api.get(`/provinces/${provinceId}/cities`)
}

export function getAdminProvinceCities(provinceId) {
  return api.get(`/admin/provinces/${provinceId}/cities`)
}

export function updateCity(provinceId, cityId, data) {
  return api.put(`/admin/provinces/${provinceId}/cities/${cityId}`, data)
}

export function batchUpdateCityHighlights(provinceId, highlightIds) {
  return api.post(`/admin/provinces/${provinceId}/cities/batch`, { highlight_ids: highlightIds })
}

export function seedCitiesFromGeoJson(provinceId) {
  return api.post(`/admin/provinces/${provinceId}/cities/seed`)
}
