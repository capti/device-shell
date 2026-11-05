/** Справочник сотрудников: список, правка профиля, деактивация и пароли. */

import { apiFetch, apiGet, apiPost } from './client'

export type Role = 'admin' | 'user'

export interface UserListItem {
  id: number
  username: string
  full_name: string
  email: string | null
  team: string | null
  telegram: string | null
  role: Role
  is_active: boolean
  created_at: string
  last_login_at: string | null
  devices_owned: number
  devices_held: number
}

export interface UserCreatePayload {
  username: string
  full_name: string
  password: string
  role: Role
  email?: string | null
  team?: string | null
  telegram?: string | null
}

/** Логин после создания не меняется: его нет в схеме правки. */
export interface UserUpdatePayload {
  full_name?: string
  role?: Role
  email?: string | null
  team?: string | null
  telegram?: string | null
}

export async function fetchUsers(includeInactive = false): Promise<UserListItem[]> {
  const suffix = includeInactive ? '?include_inactive=true' : ''
  return apiGet<UserListItem[]>(`/users${suffix}`)
}

export async function createUser(payload: UserCreatePayload): Promise<UserListItem> {
  return apiPost<UserListItem>('/users', payload)
}

export async function updateUser(
  id: number,
  payload: UserUpdatePayload,
): Promise<UserListItem> {
  return apiFetch<UserListItem>(`/users/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function deactivateUser(id: number): Promise<UserListItem> {
  return apiPost<UserListItem>(`/users/${id}/deactivate`)
}

export async function activateUser(id: number): Promise<UserListItem> {
  return apiPost<UserListItem>(`/users/${id}/activate`)
}

export async function resetUserPassword(id: number, password: string): Promise<void> {
  return apiPost<void>(`/users/${id}/password`, { password })
}
