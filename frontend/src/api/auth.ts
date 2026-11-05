import { apiGet, apiPost } from './client'

export interface UserBrief {
  id: number
  username: string
  full_name: string
  role: 'admin' | 'user'
}

export async function login(username: string, password: string): Promise<UserBrief> {
  return apiPost<UserBrief>('/auth/login', { username, password })
}

export async function logout(): Promise<void> {
  await apiPost<null>('/auth/logout')
}

export async function me(): Promise<UserBrief> {
  return apiGet<UserBrief>('/auth/me')
}
