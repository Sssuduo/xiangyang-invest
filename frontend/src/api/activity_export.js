import api from './index'

// 导出字段配置
export function getActivityExportFields() {
  return api.get('/admin/activity-export/fields')
}

export function updateActivityExportFields(data) {
  return api.put('/admin/activity-export/fields', data)
}

// 导出预览
export function activityExportPreview(activityIds = []) {
  return api.post('/admin/activity-export/preview', { activity_ids: activityIds })
}

// 下载 Excel（使用 fetch 以支持 blob 响应）
export async function downloadActivityExcel(activityIds = []) {
  const params = activityIds.length > 0 ? `?activity_ids=${activityIds.join(',')}` : ''
  const resp = await fetch(`/api/admin/activity-export/download${params}`, { credentials: 'same-origin' })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: '下载失败' }))
    throw new Error(err.message || '下载失败')
  }
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '招商动态库.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
