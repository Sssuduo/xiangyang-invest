import api from './index'

// 下载更新导入模板（使用 fetch 支持 blob）
export async function downloadUpdateTemplate() {
  const resp = await fetch('/api/admin/construction-progress-update-import/template', { credentials: 'same-origin' })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: '下载失败' }))
    throw new Error(err.message || '下载失败')
  }
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '工作进展更新导入模板.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 更新导入预览（使用 fetch 支持 FormData）
export async function previewUpdateImport(file, startDate, endDate) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('start_date', startDate)
  formData.append('end_date', endDate)
  const resp = await fetch('/api/admin/construction-progress-update-import/preview', {
    method: 'POST',
    credentials: 'same-origin',
    body: formData
  })
  const data = await resp.json()
  if (!resp.ok || data.code !== 0) {
    throw new Error(data.message || '预览失败')
  }
  return data
}

// 执行更新导入
export function executeUpdateImport(rows, startDate, endDate) {
  return api.post('/api/admin/construction-progress-update-import/execute', {
    rows,
    start_date: startDate,
    end_date: endDate,
  })
}
