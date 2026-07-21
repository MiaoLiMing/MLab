import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/api/client'
import type { TokenResponse, User } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)
  const isAuthenticated = computed(() => Boolean(user.value || localStorage.getItem('mlab_access_token')))

  function persistTokens(data: TokenResponse) {
    localStorage.setItem('mlab_access_token', data.access_token)
    localStorage.setItem('mlab_refresh_token', data.refresh_token)
    user.value = data.user
    applyTheme(data.user.theme)
  }

  async function login(email: string, password: string) {
    loading.value = true
    try {
      const data = await api<TokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      persistTokens(data)
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string, displayName: string) {
    loading.value = true
    try {
      const data = await api<TokenResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, display_name: displayName }),
      })
      persistTokens(data)
    } finally {
      loading.value = false
    }
  }

  async function restore() {
    if (!localStorage.getItem('mlab_access_token')) return
    try {
      user.value = await api<User>('/users/me')
      applyTheme(user.value.theme)
    } catch {
      clearSession()
    }
  }

  async function updateProfile(payload: Partial<User>) {
    user.value = await api<User>('/users/me', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
    applyTheme(user.value.theme)
  }

  async function logout() {
    const refreshToken = localStorage.getItem('mlab_refresh_token')
    if (refreshToken) {
      await api('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => undefined)
    }
    clearSession()
  }

  function clearSession() {
    user.value = null
    localStorage.removeItem('mlab_access_token')
    localStorage.removeItem('mlab_refresh_token')
  }

  function applyTheme(theme: User['theme']) {
    const dark = theme === 'dark' || (theme === 'system' && matchMedia('(prefers-color-scheme: dark)').matches)
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
  }

  return { user, loading, isAuthenticated, login, register, restore, updateProfile, logout }
})

