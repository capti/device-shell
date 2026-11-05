/** Уведомления текущего пользователя: список со счётчиком, прочтение. */

import { apiGet, apiPost } from './client'

export interface NotificationActor {
  id: number
  username: string
  full_name: string
}

export interface NotificationRead {
  id: number
  type: string
  actor: NotificationActor | null
  device_id: number | null
  payload: Record<string, unknown> | null
  read_at: string | null
  created_at: string
}

export interface NotificationListResponse {
  items: NotificationRead[]
  total: number
  page: number
  page_size: number
  unread: number
}

export async function fetchNotifications(
  pageSize: number,
  page = 1,
): Promise<NotificationListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  return apiGet<NotificationListResponse>(`/notifications?${params.toString()}`)
}

export async function markNotificationRead(id: number): Promise<NotificationRead> {
  return apiPost<NotificationRead>(`/notifications/${id}/read`)
}

export async function markAllNotificationsRead(): Promise<{ updated: number }> {
  return apiPost<{ updated: number }>('/notifications/read-all')
}
