import { defineStore } from 'pinia'
import { ref } from 'vue'
import { checkLogin, login as loginApi, logout as logoutApi } from '@/api/admin'

export const useAdminStore = defineStore('admin', () => {
  const user = ref(null)
  const isLoggedIn = ref(false)

  async function check() {
    try {
      const res = await checkLogin()
      if (res.code === 0) {
        user.value = res.data
        isLoggedIn.value = true
      } else {
        user.value = null
        isLoggedIn.value = false
      }
    } catch {
      user.value = null
      isLoggedIn.value = false
    }
  }

  async function login(username, password) {
    const res = await loginApi(username, password)
    if (res.code === 0) {
      user.value = res.data
      isLoggedIn.value = true
    }
    return res
  }

  async function logout() {
    await logoutApi()
    user.value = null
    isLoggedIn.value = false
  }

  return { user, isLoggedIn, check, login, logout }
})
