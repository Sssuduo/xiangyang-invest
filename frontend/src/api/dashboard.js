import api from './index'

export function getDemandStats(params = {}) {
  return api.get('/admin/demand-stats', { params })
}

export function getInvestmentStats() {
  return api.get('/admin/investment-stats')
}
