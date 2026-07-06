import http from './index'

export const reviewApi = {
  list(params?: any) { return http.get('/reviews/', { params }).then(r => r.data) },
  get(id: string) { return http.get(`/reviews/${id}`).then(r => r.data) },

  // Submit & advance
  submitForReview(draftId: string) { return http.post(`/reviews/drafts/${draftId}/submit`).then(r => r.data) },
  advanceToClient(draftId: string, data: { client_email: string; client_name: string }) {
    return http.post(`/reviews/drafts/${draftId}/advance-to-client`, data).then(r => r.data)
  },

  // Actions
  approve(id: string, comment?: string) { return http.post(`/reviews/${id}/approve`, { comment }).then(r => r.data) },
  reject(id: string, comment?: string) { return http.post(`/reviews/${id}/reject`, { comment }).then(r => r.data) },
  requestChanges(id: string, comment?: string) { return http.post(`/reviews/${id}/request-changes`, { comment }).then(r => r.data) },

  // Comments
  addComment(reviewId: string, data: any) { return http.post(`/reviews/${reviewId}/comments`, data).then(r => r.data) },
  resolveComment(commentId: string) { return http.patch(`/reviews/comments/${commentId}/resolve`).then(r => r.data) },

  // Checklists
  getChecklists(stage: string) { return http.get(`/reviews/checklists/${stage}`).then(r => r.data) },
}

export const publishApi = {
  // Channels
  listChannels() { return http.get('/publish/channels').then(r => r.data) },
  createChannel(data: any) { return http.post('/publish/channels', data).then(r => r.data) },
  updateChannel(id: string, data: any) { return http.patch(`/publish/channels/${id}`, data).then(r => r.data) },
  deleteChannel(id: string) { return http.delete(`/publish/channels/${id}`).then(r => r.data) },

  // Schedules
  listSchedules(params?: any) { return http.get('/publish/schedules', { params }).then(r => r.data) },
  createSchedule(data: any) { return http.post('/publish/schedules', data).then(r => r.data) },
  publishNow(id: string, data?: any) { return http.post(`/publish/schedules/${id}/publish-now`, data || {}).then(r => r.data) },
  cancelSchedule(id: string) { return http.delete(`/publish/schedules/${id}`).then(r => r.data) },

  // Performance
  listPerformance(params?: any) { return http.get('/publish/performance', { params }).then(r => r.data) },
  recordPerformance(data: any) { return http.post('/publish/performance', data).then(r => r.data) },
}
