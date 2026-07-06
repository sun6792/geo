import http from './index'

export const rolesApi = {
  list() {
    return http.get('/roles/').then(r => r.data)
  },
  create(data: { name: string; code: string; description?: string; permission_ids?: string[] }) {
    return http.post('/roles/', data).then(r => r.data)
  },
  update(id: string, data: any) {
    return http.patch(`/roles/${id}`, data).then(r => r.data)
  },
  delete(id: string) {
    return http.delete(`/roles/${id}`).then(r => r.data)
  },
  setPermissions(id: string, permissionIds: string[]) {
    return http.post(`/roles/${id}/permissions`, permissionIds).then(r => r.data)
  },
}

export const permissionsApi = {
  list() {
    return http.get('/permissions/').then(r => r.data)
  },
}
