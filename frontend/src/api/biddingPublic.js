// 揭榜挂帅 — 对外端口 API（揭榜方门户）
import api from './index'

export const biddingPublicApi = {
  register: (data) => api.post('/bidding/register', data),
  login: (data) => api.post('/bidding/login', data),
  logout: () => api.post('/bidding/logout'),
  me: () => api.get('/bidding/me'),
  updateMe: (data) => api.put('/bidding/me', data),
  changePassword: (data) => api.post('/bidding/me/password', data),

  listBoards: () => api.get('/bidding/boards'),
  getBoard: (id) => api.get(`/bidding/boards/${id}`),
  apply: (projectId, data) => api.post(`/bidding/boards/${projectId}/apply`, data),

  myApplications: () => api.get('/bidding/my-applications'),
  myApplicationDetail: (bidId) => api.get(`/bidding/my-applications/${bidId}`),
}
