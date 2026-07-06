import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const currentCustomerId = ref<string>('')

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setCustomerId(id: string) {
    currentCustomerId.value = id
  }

  return { sidebarCollapsed, currentCustomerId, toggleSidebar, setCustomerId }
})
