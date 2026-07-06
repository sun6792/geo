import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { UserInfo } from '@/types/user'

const TOKEN_KEY = 'geoai_access_token'
const REFRESH_KEY = 'geoai_refresh_token'
const USER_KEY = 'geoai_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const refreshToken = ref<string>(localStorage.getItem(REFRESH_KEY) || '')
  const user = ref<UserInfo | null>(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))
  const permissions = ref<string[]>([])

  const isLoggedIn = computed(() => !!token.value)

  // Verify role from server on every page load (prevents stale localStorage bypass)
  async function initAuth() {
    if (!token.value) return
    try {
      const profile = await authApi.getMe()
      user.value = profile
      localStorage.setItem(USER_KEY, JSON.stringify(profile))
    } catch {
      clearAuth()
    }
  }

  function hasPermission(perm: string): boolean {
    return permissions.value.includes(perm) || user.value?.is_super_admin === true
  }

  async function login(email: string, password: string) {
    const res = await authApi.login(email, password)
    token.value = res.access_token
    refreshToken.value = res.refresh_token
    localStorage.setItem(TOKEN_KEY, res.access_token)
    localStorage.setItem(REFRESH_KEY, res.refresh_token)

    // Fetch user profile
    const profile = await authApi.getMe()
    user.value = profile
    localStorage.setItem(USER_KEY, JSON.stringify(profile))

    // Extract permissions from roles
    permissions.value = profile.roles?.flatMap((r: any) =>
      r.permissions?.map((p: any) => p.code) || []
    ) || []

    return profile
  }

  async function logout() {
    try {
      await authApi.logout(refreshToken.value)
    } catch { /* ignore */ }
    clearAuth()
  }

  function clearAuth() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
    permissions.value = []
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, refreshToken, user, permissions, isLoggedIn, login, logout, hasPermission, clearAuth }
})
