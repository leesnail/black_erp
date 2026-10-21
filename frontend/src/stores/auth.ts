import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserOut } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserOut | null>(null)
  const loaded = ref(false)

  const perms = computed(() => user.value?.perms ?? [])
  const csrfToken = computed(() => user.value?.csrf_token ?? '')
  const isLoggedIn = computed(() => !!user.value)
  const role = computed(() => user.value?.role ?? '')

  function has(code?: string | null): boolean {
    if (!code) return true
    if (!user.value) return false
    if (user.value.role === 'admin') return true
    if (perms.value.includes('*')) return true
    return perms.value.includes(code)
  }

  function defaultHome(): string {
    switch (role.value) {
      case 'cs':
        return '/service/aftersale'
      case 'po':
        return '/master/specs'
      case 'op':
        return '/master/shop-products'
      case 'fin':
        return '/calc/upload'
      case 'boss':
      case 'admin':
        return '/report/cockpit'
      default:
        return '/workbench'
    }
  }

  async function fetchMe() {
    user.value = await authApi.me()
    loaded.value = true
  }

  async function login(account: string, password: string) {
    user.value = await authApi.login(account, password)
    loaded.value = true
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
      /* 忽略 */
    }
    clear()
  }

  function clear() {
    user.value = null
    loaded.value = true
  }

  return {
    user,
    loaded,
    perms,
    csrfToken,
    isLoggedIn,
    role,
    has,
    defaultHome,
    fetchMe,
    login,
    logout,
    clear,
  }
})
