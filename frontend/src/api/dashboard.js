import api from './index'

export function getDemandStats(params = {}) {
  return api.get('/admin/demand-stats', { params })
}
