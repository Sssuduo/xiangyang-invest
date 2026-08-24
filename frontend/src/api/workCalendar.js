/**
 * 工作日历 API
 */
import request from './index'

export const workCalendarApi = {
  /**
   * 获取工作日历列表（按时间范围）
   * @param {Object} params - { start: ISO日期字符串, end: ISO日期字符串 }
   */
  getList(params) {
    // 注意：axios 实例 baseURL 为 '/api'，此处用相对路径，避免拼成 /api/api/...
    return request.get('/work-calendar', { params })
  },

  /**
   * 创建工作日历条目
   * @param {Object} data - 工作日历数据
   */
  create(data) {
    return request.post('/work-calendar', data)
  },

  /**
   * 更新工作日历条目
   * @param {Number} id - 条目ID
   * @param {Object} data - 更新数据
   */
  update(id, data) {
    return request.put(`/work-calendar/${id}`, data)
  },

  /**
   * 删除工作日历条目
   * @param {Number} id - 条目ID
   */
  delete(id) {
    return request.delete(`/work-calendar/${id}`)
  },

  /**
   * 导出为 Word 文档
   * @param {Object} data - { start: ISO日期字符串, end: ISO日期字符串 }
   * @returns {Blob} Word 文档二进制数据
   */
  async exportWord(data) {
    const response = await fetch('/api/work-calendar/export/word', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(data)
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || '导出失败')
    }
    
    return await response.blob()
  }
}
