import api from './index'

// 导出字段配置
export function getExportFields() {
  return api.get('/admin/export/fields')
}

export function updateExportFields(data) {
  return api.put('/admin/export/fields', data)
}

// 导出预览
export function exportPreview(projectIds = []) {
  return api.post('/admin/export/preview', { project_ids: projectIds })
}

// 下载 Excel（使用 fetch 以支持 blob 响应）
export async function downloadExcel(projectIds = []) {
  const params = projectIds.length > 0 ? `?project_ids=${projectIds.join(',')}` : ''
  const resp = await fetch(`/api/admin/export/download${params}`, { credentials: 'same-origin' })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: '下载失败' }))
    throw new Error(err.message || '下载失败')
  }
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '招商项目库.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
