import api from './index'

export function login(username, password) {
  return api.post('/admin/login', { username, password })
}

export function logout() {
  return api.post('/admin/logout')
}

export function checkLogin() {
  return api.get('/admin/check')
}
