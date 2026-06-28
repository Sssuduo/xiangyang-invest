/**
 * 在建项目打印 API
 */
import api from './index'

// ---- 打印模板 ----
export function getConstructionPrintTemplates(entityType = 'construction') {
  return api.get('/admin/construction-print/templates', { params: { entity_type: entityType } })
}

export function createConstructionPrintTemplate(data) {
  return api.post('/admin/construction-print/templates', data)
}

export function updateConstructionPrintTemplate(id, data) {
  return api.put(`/admin/construction-print/templates/${id}`, data)
}

export function deleteConstructionPrintTemplate(id) {
  return api.delete(`/admin/construction-print/templates/${id}`)
}

// ---- 打印字段配置 ----
export function getConstructionPrintFields(templateId) {
  return api.get('/admin/construction-print/fields', { params: { template_id: templateId } })
}

export function updateConstructionPrintFields(data) {
  return api.put('/admin/construction-print/fields', data)
}

// ---- 打印数据 ----
export function fetchConstructionPrintData(projectIds, options = {}) {
  const params = {
    project_ids: projectIds.join(','),
    template_id: options.templateId || 0,
    progress_range: options.progressRange || '',
    progress_mode: options.progressMode || 'aggregate'
  }
  return api.get('/admin/construction-print/data', { params })
}

// ---- 下载 Excel（使用 fetch 以支持 blob 响应） ----
export async function downloadConstructionPrintExcel(projectIds = [], options = {}) {
  const params = []
  if (projectIds && projectIds.length > 0) {
    params.push('project_ids=' + projectIds.join(','))
  }
  if (options.templateId) {
    params.push('template_id=' + options.templateId)
  }
  if (options.progressRange) {
    params.push('progress_range=' + encodeURIComponent(options.progressRange))
  }
  if (options.progressMode) {
    params.push('progress_mode=' + encodeURIComponent(options.progressMode))
  }
  const query = params.length > 0 ? '?' + params.join('&') : ''

  const resp = await fetch(`/api/admin/construction-print/download${query}`, { credentials: 'same-origin' })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: '下载失败' }))
    throw new Error(err.message || '下载失败')
  }
  const blob = await resp.blob()
  const disposition = resp.headers.get('Content-Disposition') || ''
  let filename = '在建项目库.xlsx'
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
