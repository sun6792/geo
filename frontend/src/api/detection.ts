import http from './index'

export const detectionApi = {
  // Tasks
  listTasks(params?: any) { return http.get('/detection/tasks', { params }).then(r => r.data) },
  createTask(data: any) { return http.post('/detection/tasks', data).then(r => r.data) },
  getTask(id: string) { return http.get(`/detection/tasks/${id}`).then(r => r.data) },
  updateTask(id: string, data: any) { return http.patch(`/detection/tasks/${id}`, data).then(r => r.data) },
  deleteTask(id: string) { return http.delete(`/detection/tasks/${id}`).then(r => r.data) },
  runTask(id: string) { return http.post(`/detection/tasks/${id}/run`).then(r => r.data) },

  // Results
  listResults(params?: any) { return http.get('/detection/results', { params }).then(r => r.data) },
  getSummary() { return http.get('/detection/summary').then(r => r.data) },

  // Competitors
  listCompetitors() { return http.get('/detection/competitors').then(r => r.data) },
  createCompetitor(data: any) { return http.post('/detection/competitors', data).then(r => r.data) },

  // Source Verifications
  listSourceVerifications(params?: any) { return http.get('/detection/source-verifications', { params }).then(r => r.data) },

  // Sentiment
  listSentiment(params?: any) { return http.get('/detection/sentiment', { params }).then(r => r.data) },
  getSentimentSummary() { return http.get('/detection/sentiment/summary').then(r => r.data) },
}

export const diagnosisApi = {
  listReports(params?: any) { return http.get('/diagnosis/reports', { params }).then(r => r.data) },
  generateReport() { return http.post('/diagnosis/reports/generate').then(r => r.data) },
  getReport(id: string) { return http.get(`/diagnosis/reports/${id}`).then(r => r.data) },
  getScores(reportId: string) { return http.get(`/diagnosis/reports/${reportId}/scores`).then(r => r.data) },
  listOptimizationItems(params?: any) { return http.get('/diagnosis/optimization-items', { params }).then(r => r.data) },
  updateOptimizationItem(id: string, data: any) { return http.patch(`/diagnosis/optimization-items/${id}`, data).then(r => r.data) },
}

export const weeklyReviewApi = {
  listReviews(params?: any) { return http.get('/weekly-review/reviews', { params }).then(r => r.data) },
  getLatest() { return http.get('/weekly-review/reviews/latest').then(r => r.data) },
  getReview(id: string) { return http.get(`/weekly-review/reviews/${id}`).then(r => r.data) },
  generateReview() { return http.post('/weekly-review/reviews/generate').then(r => r.data) },
  getMetrics(reviewId: string) { return http.get(`/weekly-review/reviews/${reviewId}/metrics`).then(r => r.data) },
  listRules(params?: any) { return http.get('/weekly-review/rules', { params }).then(r => r.data) },
  updateRule(id: string, data: any) { return http.patch(`/weekly-review/rules/${id}`, data).then(r => r.data) },
  getRuleVersions(id: string) { return http.get(`/weekly-review/rules/${id}/versions`).then(r => r.data) },
}
