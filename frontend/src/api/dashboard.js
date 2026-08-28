import api from './index'

export function getDemandStats(params = {}) {
  return api.get('/admin/demand-stats', { params })
}

export function getInvestmentStats(params = {}) {
  return api.get('/admin/investment-stats', { params })
}

export function getActivityTags(params = {}) {
  return api.get('/admin/investment/activity-tags', { params })
}

export function exportActivityTags(params = {}) {
  return api.get('/admin/investment/activity-tags/export', { params, responseType: 'blob' })
}

export function getOverdueAlerts(params = {}) {
  return api.get('/admin/investment/overdue-alerts', { params })
}
