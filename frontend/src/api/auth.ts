import { get, post } from './request'

export interface UserOut {
  id: number
  account: string
  display_name: string
  role: string
  perms: string[]
  csrf_token: string
}

export const authApi = {
  login(account: string, password: string) {
    return post<UserOut>('/auth/login', { account, password })
  },
  logout() {
    return post('/auth/logout')
  },
  me() {
    return get<UserOut>('/auth/me')
  },
  changePassword(old_password: string, new_password: string) {
    return post('/auth/change-password', { old_password, new_password })
  },
}
