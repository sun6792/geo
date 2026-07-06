import http from './index'

export const usersApi = {
  list(params?: { page?: number; page_size?: number; search?: string }) {
    return http.get('/users/', { params }).then(r => r.data)
  },
  create(data: { email: string; password: string; display_name: string; phone?: string; role_ids?: string[] }) {
    return http.post('/users/', data).then(r => r.data)
  },
  get(id: string) {
    return http.get(`/users/${id}`).then(r => r.data)
  },
  update(id: string, data: any) {
    return http.patch(`/users/${id}`, data).then(r => r.data)
  },
  deactivate(id: string) {
    return http.delete(`/users/${id}`).then(r => r.data)
  },
  assignRoles(id: string, roleIds: string[]) {
    return http.post(`/users/${id}/roles`, { role_ids: roleIds }).then(r => r.data)
  },
}
