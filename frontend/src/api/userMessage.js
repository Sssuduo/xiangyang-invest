import api from './index'

// 用户消息中心 API
export const userMessageApi = {
  listInbox(params = {}) {
    return api.get('/messages/inbox', { params })
  },
  unreadCount() {
    return api.get('/messages/unread-count')
  },
  snooze(id) {
    return api.post(`/messages/${id}/snooze`)
  },
  done(id) {
    return api.post(`/messages/${id}/done`)
  },
  readAll() {
    return api.post('/messages/read-all')
  },
}
