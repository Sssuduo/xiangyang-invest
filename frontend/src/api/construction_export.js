import api from './index'

// ============================================================
// 模板 CRUD
// ============================================================

export function getConstructionExportTemplates(entityType = 'construction') {
  return api.get('/admin/construction-export/templates', { params: { entity_type: entityType } })
}

export function createConstructionExportTemplate(data) {
  return api.post('/admin/construction-export/templates', data)
}

export function updateConstructionExportTemplate(id, data) {
  return api.put(`/admin/construction-export/templates/${id}`, data)
}

export function deleteConstructionExportTemplate(id) {
  return api.delete(`/admin/construction-export/templates/${id}`)
}

// ============================================================
// 导出字段配置
// ============================================================

export function getConstructionExportFields(templateId) {
  const params = templateId ? `?template_id=${templateId}` : ''
  return api.get(`/admin/construction-export/fields${params}`)
}

export function updateConstructionExportFields(data) {
  return api.put('/admin/construction-export/fields', data)
}

// ============================================================
// 导出预览
// ============================================================

export function constructionExportPreview(projectIds, templateId) {
  return api.post('/admin/construction-export/preview', { project_ids: projectIds, template_id: templateId })
}

// ============================================================
// 下载 Excel（使用 fetch 以支持 blob 响应）
// ============================================================

export async function downloadConstructionExcel(projectIds = [], options = {}) {
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

  const resp = await fetch(`/api/admin/construction-export/download${query}`, { credentials: 'same-origin' })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: '下载失败' }))
    throw new Error(err.message || '下载失败')
  }
  const blob = await resp.blob()
  // 从响应头提取后端 send_file 设置的文件名
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
