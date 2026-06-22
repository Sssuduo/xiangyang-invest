import api from './index'

// 导入字段配置
export function getActivityImportFields() {
  return api.get('/admin/activity-import/fields')
}

export function updateActivityImportFields(data) {
  return api.put('/admin/activity-import/fields', data)
}

// 获取模板项目列表（供模板下载弹窗）
export function getTemplateProjects(followStatus = '') {
  const params = followStatus ? `?follow_status=${encodeURIComponent(followStatus)}` : ''
  return api.get(`/admin/activity-import/projects-for-template${params}`)
}

// 下载导入模板（可选传入项目ID列表，预填到模板中）
export async function downloadActivityImportTemplate(projectIds = []) {
  let url = '/api/admin/activity-import/template'
  if (projectIds && projectIds.length > 0) {
    url += '?project_ids=' + projectIds.join(',')
  }
  const resp = await fetch(url, { credentials: 'same-origin' })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: '下载失败' }))
    throw new Error(err.message || '下载失败')
  }
  const blob = await resp.blob()
  const urlObj = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = urlObj
  a.download = '招商动态导入模板.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(urlObj)
}

// 导入预览（使用 fetch 支持 FormData）
export async function activityImportPreviewApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  const resp = await fetch('/api/admin/activity-import/preview', {
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

// 执行导入
export function activityImportExecute(rows) {
  return api.post('/admin/activity-import/execute', { rows })
}
