// 揭榜挂帅 — 内部端口 API（专班/业务用户）
import api from './index'

export const biddingApi = {
  // 字典
  getDicts: () => api.get('/admin/bidding/dicts'),

  // 榜单项目
  listProjects: (params) => api.get('/admin/bidding/projects', { params }),
  createProject: (data) => api.post('/admin/bidding/projects', data),
  getProject: (id) => api.get(`/admin/bidding/projects/${id}`),
  updateProject: (id, data) => api.put(`/admin/bidding/projects/${id}`, data),
  deleteProject: (id) => api.delete(`/admin/bidding/projects/${id}`),
  transition: (id, data) => api.post(`/admin/bidding/projects/${id}/transition`, data),

  // 揭榜申请
  createBid: (projectId, data) => api.post(`/admin/bidding/projects/${projectId}/bids`, data),
  updateBid: (projectId, bidId, data) => api.put(`/admin/bidding/projects/${projectId}/bids/${bidId}`, data),
  deleteBid: (projectId, bidId) => api.delete(`/admin/bidding/projects/${projectId}/bids/${bidId}`),

  // 里程碑
  createMilestone: (projectId, data) => api.post(`/admin/bidding/projects/${projectId}/milestones`, data),
  updateMilestone: (projectId, mid, data) => api.put(`/admin/bidding/projects/${projectId}/milestones/${mid}`, data),
  deleteMilestone: (projectId, mid) => api.delete(`/admin/bidding/projects/${projectId}/milestones/${mid}`),
  updateMilestoneStatus: (projectId, mid, data) => api.post(`/admin/bidding/projects/${projectId}/milestones/${mid}/status`, data),

  // 全周期服务跟踪
  addTimeline: (projectId, data) => api.post(`/admin/bidding/projects/${projectId}/timeline`, data),
  deleteTimeline: (projectId, tid) => api.delete(`/admin/bidding/projects/${projectId}/timeline/${tid}`),

  // 揭榜方用户管理
  listUsers: () => api.get('/admin/bidding/users'),
  updateUser: (userId, data) => api.put(`/admin/bidding/users/${userId}`, data),

  // 看板
  getStats: () => api.get('/admin/bidding/stats'),

  // 企业档案（1 企业可发布多个需求）
  listEnterprises: (params) => api.get('/admin/bidding/enterprises', { params }),
  createEnterprise: (data) => api.post('/admin/bidding/enterprises', data),
  updateEnterprise: (id, data) => api.put(`/admin/bidding/enterprises/${id}`, data),
}
