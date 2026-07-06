import http from './index'

export const contentApi = {
  // Briefs
  listBriefs(params?: any) { return http.get('/content/briefs', { params }).then(r => r.data) },
  createBrief(data: any) { return http.post('/content/briefs', data).then(r => r.data) },
  getBrief(id: string) { return http.get(`/content/briefs/${id}`).then(r => r.data) },
  updateBrief(id: string, data: any) { return http.patch(`/content/briefs/${id}`, data).then(r => r.data) },

  // Generation
  generate(briefId: string, data?: any) { return http.post(`/content/briefs/${briefId}/generate`, data || {}).then(r => r.data) },

  // Drafts
  listDrafts(briefId: string) { return http.get('/content/drafts', { params: { brief_id: briefId } }).then(r => r.data) },
  getDraft(id: string) { return http.get(`/content/drafts/${id}`).then(r => r.data) },
  updateDraft(id: string, data: any) { return http.patch(`/content/drafts/${id}`, data).then(r => r.data) },

  // Templates
  listTemplates() { return http.get('/content/templates').then(r => r.data) },
  createTemplate(data: any) { return http.post('/content/templates', data).then(r => r.data) },
}
