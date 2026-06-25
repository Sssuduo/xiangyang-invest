import api from './index'

export function getConstructionStats(params = {}) {
  return api.get('/admin/construction/stats', { params })
}
