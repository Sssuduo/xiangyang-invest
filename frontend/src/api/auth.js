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

export function updateProfile(data) {
  return api.put('/auth/profile', data)
}

export function changePassword(data) {
  return api.put('/auth/password', data)
}
