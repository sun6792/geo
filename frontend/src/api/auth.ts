import http from './index'

export const authApi = {
  login(email: string, password: string) {
    return http.post('/auth/login', { email, password }).then(r => r.data)
  },
  refresh(refreshToken: string) {
    return http.post('/auth/refresh', { refresh_token: refreshToken }).then(r => r.data)
  },
  logout(refreshToken: string) {
    return http.post('/auth/logout', { refresh_token: refreshToken }).then(r => r.data)
  },
  getMe() {
    return http.get('/auth/me').then(r => r.data)
  },
  changePassword(oldPassword: string, newPassword: string) {
    return http.patch('/auth/password', { old_password: oldPassword, new_password: newPassword }).then(r => r.data)
  },
}
