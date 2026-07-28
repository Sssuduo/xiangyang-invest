import api from './index'

// 获取启用的模型列表
export function getModels() {
  return api.get('/models')
}

// 生成提纲
export function generateOutline(data) {
  return api.post('/official-doc/generate-outline', data)
}

// 生成成文
export function generateDocument(data) {
  return api.post('/official-doc/generate-document', data)
}

// 获取模板列表
export function getTemplates() {
  return api.get('/official-doc/templates')
}

// 上传模板
export function uploadTemplate(formData) {
  return api.post('/official-doc/templates', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 删除模板
export function deleteTemplate(id) {
  return api.delete(`/official-doc/templates/${id}`)
}

// 上传素材文件
export function uploadMaterial(formData) {
  return api.post('/official-doc/upload-material', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 下载 Word（后端生成 .docx 并返回下载地址）
export function downloadWord(data) {
  return api.post('/official-doc/download-word', data)
}

// 下载 HTML
export function downloadHtml(data) {
  return api.post('/official-doc/download-html', data, {
    responseType: 'blob'
  })
}
