import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, logout as apiLogout, checkAuth } from '@/api/auth'

export const useBusinessAuthStore = defineStore('businessAuth', () => {
  const user = ref(null)
  const isLoggedIn = ref(false)
  const permissions = ref({})
  const loading = ref(false)

  async function check() {
    try {
      const res = await checkAuth()
      if (res.code === 0) {
        user.value = res.data
        isLoggedIn.value = true
        permissions.value = res.data.permissions || {}
      } else {
        clear()
      }
    } catch {
      clear()
    }
  }

  async function login(username, password) {
    loading.value = true
    try {
      const res = await apiLogin(username, password)
      if (res.code === 0) {
        user.value = res.data
        isLoggedIn.value = true
        permissions.value = res.data.permissions || {}
        return { success: true }
      }
      return { success: false, message: res.message || '登录失败' }
    } catch (err) {
      return { success: false, message: err.message || '登录失败' }
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await apiLogout()
    } catch {
      // ignore logout errors
    }
    clear()
  }

  function clear() {
    user.value = null
    isLoggedIn.value = false
    permissions.value = {}
  }

  function hasPermission(module, action) {
    return permissions.value?.[module]?.[action] === true
  }

  return { user, isLoggedIn, permissions, loading, check, login, logout, hasPermission }
})
