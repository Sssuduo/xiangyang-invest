import api from './index'

// ---- 语音知识库 ----
export function getKnowledgeList() {
  return api.get('/admin/voice-knowledge')
}

export function createKnowledgeEntry(data) {
  return api.post('/admin/voice-knowledge', data)
}

export function deleteKnowledgeEntry(id) {
  return api.delete(`/admin/voice-knowledge/${id}`)
}

export function detectHomophones(text, minConfidence = 0.70) {
  return api.post('/admin/voice-knowledge/detect', { text, min_confidence: minConfidence })
}

// ---- 文本校正页 ----
// entityType: 'activity-ledger' (活动台账) | 'activity' (招商动态)
export function getSummaryPageData(entityType, ledgerId) {
  return api.get(`/admin/voice-knowledge/${entityType}/${ledgerId}/summary-data`)
}

// 前端导入使用 saveCorrections (原名 saveCorrections 保持兼容)
export const saveCorrections = saveTextCorrections
export function saveTextCorrections(entityType, ledgerId, corrections, persistToKnowledge = false, deletions = []) {
  return api.post(`/admin/voice-knowledge/${entityType}/${ledgerId}/save-corrections`, {
    corrections,
    persist_to_knowledge: persistToKnowledge,
    deletions,  // 删除列表（独立字段，不生成知识库映射）
  })
}

export function autoCorrect(entityType, ledgerId, minConfidence = 0.90) {
  return api.post(`/admin/voice-knowledge/${entityType}/${ledgerId}/auto-correct`, {
    min_confidence: minConfidence,
  })
}

export function saveCorrectedText(entityType, ledgerId, data) {
  return api.put(`/admin/voice-knowledge/${entityType}/${ledgerId}/save-corrected-text`, data)
}
