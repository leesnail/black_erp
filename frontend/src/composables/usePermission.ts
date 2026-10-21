import type { App, Directive } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermission() {
  const auth = useAuthStore()
  const has = (code?: string | null) => auth.has(code)
  return { has }
}

const permDirective: Directive<HTMLElement, string | undefined> = {
  mounted(el, binding) {
    const auth = useAuthStore()
    if (!auth.has(binding.value)) {
      el.parentNode?.removeChild(el)
    }
  },
  updated(el, binding) {
    const auth = useAuthStore()
    if (!auth.has(binding.value) && el.parentNode) {
      el.parentNode.removeChild(el)
    }
  },
}

export function setupPermissionDirective(app: App) {
  app.directive('perm', permDirective)
}
