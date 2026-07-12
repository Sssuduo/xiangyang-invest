import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, logout as apiLogout, checkAuth, updateProfile as apiUpdateProfile, changePassword as apiChangePassword } from '@/api/auth'

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
    const perm = permissions.value?.[module]
    if (!perm) return false
    if (perm[action] !== undefined) return perm[action] === true
    // 向后兼容：历史数据未包含以下字段时，默认允许
    if (action === 'add' || action === 'import' || action === 'assess' || action === 'convert') return true
    return false
  }

  async function updateProfile(displayName) {
    try {
      const res = await apiUpdateProfile({ display_name: displayName })
      if (res.code === 0) {
        user.value = res.data
        return { success: true }
      }
      return { success: false, message: res.message || '更新失败' }
    } catch (err) {
      return { success: false, message: err.message || '更新失败' }
    }
  }

  async function changePassword(oldPassword, newPassword) {
    try {
      const res = await apiChangePassword({ old_password: oldPassword, new_password: newPassword })
      if (res.code === 0) {
        clear()
        return { success: true, message: res.message }
      }
      return { success: false, message: res.message || '修改失败' }
    } catch (err) {
      return { success: false, message: err.message || '修改失败' }
    }
  }

  const isVisitor = computed(() => user.value?.role === 'visitor')

  return { user, isLoggedIn, isVisitor, permissions, loading, check, login, logout, hasPermission, updateProfile, changePassword }
})
