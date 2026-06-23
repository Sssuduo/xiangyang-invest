import api from './index'

// 公开 API
export function getPublicDemands(params = {}) {
  return api.get('/investment/demands', { params })
}

export function getDemandDicts() {
  return api.get('/investment/demand-dicts')
}

// 管理 API — CRUD
export function getDemands(params = {}) {
  return api.get('/admin/demand/demands', { params })
}

export function createDemand(data) {
  return api.post('/admin/demand/demands', data)
}

export function getDemand(id) {
  return api.get(`/admin/demand/demands/${id}`)
}

export function updateDemand(id, data) {
  return api.put(`/admin/demand/demands/${id}`, data)
}

export function deleteDemand(id) {
  return api.delete(`/admin/demand/demands/${id}`)
}

export function batchDeleteDemands(ids) {
  return api.post('/admin/demand/demands/batch-delete', { ids })
}

// 导入字段配置
export function getDemandImportFields() {
  return api.get('/admin/demand-import/fields')
}

export function updateDemandImportFields(data) {
  return api.put('/admin/demand-import/fields', data)
}

// 获取模板项目列表（供模板下载弹窗）
export function getTemplateProjects(followStatus = '') {
  const params = followStatus ? `?follow_status=${encodeURIComponent(followStatus)}` : ''
  return api.get(`/admin/demand-import/projects-for-template${params}`)
}

// 下载导入模板（可选传入项目ID列表，预填到模板中）
export async function downloadDemandImportTemplate(projectIds = []) {
  let url = '/api/admin/demand-import/template'
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
  a.download = '企业诉求导入模板.xlsx'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(urlObj)
}

// 导入预览（使用 fetch 支持 FormData）
export async function demandImportPreview(file) {
  const fd = new FormData()
  fd.append('file', file)
  const resp = await fetch('/api/admin/demand-import/preview', {
    method: 'POST',
    credentials: 'same-origin',
    body: fd
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: '请求失败' }))
    throw new Error(err.message || '请求失败')
  }
  return resp.json()
}

// 执行导入
export function demandImportExecute(rows) {
  return api.post('/admin/demand-import/execute', { rows })
}
