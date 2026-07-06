import { App } from 'vue'
import { createPinia } from 'pinia'

export function setupStores(app: App) {
  app.use(createPinia())
}

export { useAuthStore } from './auth'
export { useAppStore } from './app'
export { usePermissionStore } from './permission'
