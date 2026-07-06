import { defineStore } from 'pinia'
import { ref } from 'vue'
import { rolesApi, permissionsApi } from '@/api/roles'

export const usePermissionStore = defineStore('permission', () => {
  const allPermissions = ref<{ code: string; resource: string; action: string }[]>([])
  const allRoles = ref<any[]>([])

  async function fetchPermissions() {
    const perms = await permissionsApi.list()
    allPermissions.value = perms
  }

  async function fetchRoles() {
    const roles = await rolesApi.list()
    allRoles.value = roles
  }

  return { allPermissions, allRoles, fetchPermissions, fetchRoles }
})
