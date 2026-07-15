import api from './index'

// ---- 语音知识库 ----
export function getKnowledgeList() {
  return api.get('/api/admin/voice-knowledge')
}

export function createKnowledgeEntry(data) {
  return api.post('/api/admin/voice-knowledge', data)
}

export function deleteKnowledgeEntry(id) {
  return api.delete(`/api/admin/voice-knowledge/${id}`)
}

export function detectHomophones(text, minConfidence = 0.70) {
  return api.post('/api/admin/voice-knowledge/detect', { text, min_confidence: minConfidence })
}

// ---- 文本校正页 ----
export function getSummaryPageData(ledgerId) {
  return api.get(`/api/admin/voice-knowledge/activity-ledger/${ledgerId}/summary-data`)
}

// 前端导入使用 saveCorrections (原名 saveCorrections 保持兼容)
export const saveCorrections = saveTextCorrections
export function saveTextCorrections(ledgerId, corrections, persistToKnowledge = false) {
  return api.post(`/api/admin/voice-knowledge/activity-ledger/${ledgerId}/save-corrections`, {
    corrections,
    persist_to_knowledge: persistToKnowledge,
  })
}
