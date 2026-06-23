import api from './index'

export function login(username, password) {
  return api.post('/auth/login', { username, password })
}

export function logout() {
  return api.post('/auth/logout')
}

export function checkAuth() {
  return api.get('/auth/check')
}
