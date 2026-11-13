/**
 * 产业链招商智能分析 API
 */
import request from './index'

export const chainApi = {
  /**
   * 总览：统计口径 + 层级分布 + 优先级分布 + 优先级规则
   */
  getOverview() {
    return request.get('/chain/overview')
  },

  /**
   * 产业链环节本体（含企业数、缺口标记）
   */
  getNodes() {
    return request.get('/chain/nodes')
  },

  /**
   * 企业清单
   * @param {Object} params - { node_code, layer, role, keyword, min_strength, order_by }
   */
  getEnterprises(params) {
    return request.get('/chain/enterprises', { params })
  },

  /**
   * 共性配套缺口（含六因子得分）
   */
  getGaps() {
    return request.get('/chain/gaps')
  },

  /**
   * 目标企业候选库
   * @param {Object} params - { gap_id, node_code, is_local, region_type, chain_role, invest_fit, province, keyword }
   */
  getTargets(params) {
    return request.get('/chain/targets', { params })
  },

  /**
   * 目标企业库筛选项（省份 / 地域类型 / 链作用 / 投资可行性）
   */
  getTargetFilters() {
    return request.get('/chain/target-filters')
  },

  /**
   * 招商建议
   */
  getAdvice() {
    return request.get('/chain/advice')
  },

  /**
   * 将目标企业转为招商线索
   * @param {Number} id - 目标企业ID
   */
  convertTarget(id) {
    return request.post(`/chain/targets/${id}/convert`)
  },

  /**
   * 更新目标企业复核状态
   * @param {Number} id - 目标企业ID
   * @param {String} reviewStatus - 待复核 / 已复核 / 已排除
   */
  updateReview(id, reviewStatus) {
    return request.put(`/chain/targets/${id}/review`, { review_status: reviewStatus })
  },

  /**
   * 导出 CSV（带 BOM，Excel 直接打开）
   * @param {String} dataset - enterprises / gaps / targets
   */
  async exportCsv(dataset) {
    const response = await fetch(`/api/chain/export/${dataset}.csv`, {
      method: 'GET',
      credentials: 'include',
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || '导出失败')
    }
    return await response.blob()
  },

  /**
   * 导出招商分析报告 Word
   */
  async exportWord() {
    const response = await fetch('/api/chain/export/word', {
      method: 'GET',
      credentials: 'include',
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || '导出失败')
    }
    return await response.blob()
  }
}

/** 触发浏览器下载 Blob */
export function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
