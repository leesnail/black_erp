import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const siderCollapsed = ref(false)
  const unreadCount = ref(0)

  function toggleSider() {
    siderCollapsed.value = !siderCollapsed.value
  }

  function setUnread(n: number) {
    unreadCount.value = n
  }

  return { siderCollapsed, unreadCount, toggleSider, setUnread }
})
