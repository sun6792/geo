import http from './index'

export const kbApi = {
  // Categories
  listCategories() { return http.get('/kb/categories').then(r => r.data) },
  createCategory(data: any) { return http.post('/kb/categories', data).then(r => r.data) },
  updateCategory(id: string, data: any) { return http.patch(`/kb/categories/${id}`, data).then(r => r.data) },
  deleteCategory(id: string) { return http.delete(`/kb/categories/${id}`).then(r => r.data) },

  // Assets
  listAssets(params?: any) { return http.get('/kb/assets', { params }).then(r => r.data) },
  createAsset(data: any) { return http.post('/kb/assets', data).then(r => r.data) },
  getAsset(id: string) { return http.get(`/kb/assets/${id}`).then(r => r.data) },
  updateAsset(id: string, data: any) { return http.patch(`/kb/assets/${id}`, data).then(r => r.data) },
  archiveAsset(id: string) { return http.delete(`/kb/assets/${id}`).then(r => r.data) },
  getVersions(slug: string) { return http.get(`/kb/assets/${slug}/versions`).then(r => r.data) },
}
