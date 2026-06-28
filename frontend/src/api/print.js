/**
 * 招商项目打印 API
 */
import api from './index'

// ---- 打印模板 ----
export function getPrintTemplates(entityType = 'investment') {
  return api.get('/admin/print/templates', { params: { entity_type: entityType } })
}

export function createPrintTemplate(data) {
  return api.post('/admin/print/templates', data)
}

export function updatePrintTemplate(id, data) {
  return api.put(`/admin/print/templates/${id}`, data)
}

export function deletePrintTemplate(id) {
  return api.delete(`/admin/print/templates/${id}`)
}

// ---- 打印字段配置 ----
export function getPrintFields(templateId) {
  return api.get('/admin/print/fields', { params: { template_id: templateId } })
}

export function updatePrintFields(data) {
  return api.put('/admin/print/fields', data)
}

// ---- 打印数据 ----
export function fetchPrintData(projectIds, options = {}) {
  const params = {
    project_ids: projectIds.join(','),
    template_id: options.templateId || 0,
    activity_range: options.activityRange || '',
    demand_mode: options.demandMode || 'aggregate'
  }
  return api.get('/admin/print/data', { params })
}

// ---- 下载 Excel（使用 fetch 以支持 blob 响应） ----
export async function downloadPrintExcel(projectIds = [], options = {}) {
  const params = []
  if (projectIds && projectIds.length > 0) {
    params.push('project_ids=' + projectIds.join(','))
  }
  if (options.templateId) {
    params.push('template_id=' + options.templateId)
  }
  if (options.activityRange) {
    params.push('activity_range=' + encodeURIComponent(options.activityRange))
  }
  if (options.demandMode) {
    params.push('demand_mode=' + encodeURIComponent(options.demandMode))
  }
  const query = params.length > 0 ? '?' + params.join('&') : ''

  const resp = await fetch(`/api/admin/print/download${query}`, { credentials: 'same-origin' })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: '下载失败' }))
    throw new Error(err.message || '下载失败')
  }
  const blob = await resp.blob()
  const disposition = resp.headers.get('Content-Disposition') || ''
  let filename = '招商项目库.xlsx'
  const starMatch = disposition.match(/filename\*=UTF-8''([^;]*)/i)
  if (starMatch && starMatch[1]) {
    try { filename = decodeURIComponent(starMatch[1]) } catch { filename = starMatch[1] }
  } else {
    const plainMatch = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
    if (plainMatch && plainMatch[1]) {
      filename = plainMatch[1].replace(/['"]/g, '')
      try { filename = decodeURIComponent(filename) } catch { /* keep as-is */ }
    }
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
