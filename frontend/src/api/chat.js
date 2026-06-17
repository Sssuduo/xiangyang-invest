import api from './index'

export function sendChat(data) {
  return api.post('/chat', data)
}
