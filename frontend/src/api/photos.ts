/** Фотографии устройства: список, загрузка multipart и удаление. */

import { apiFetch, apiGet } from './client'
import type { DeviceUser } from './devices'

export interface PhotoRead {
  id: number
  device_id: number
  report_id: number | null
  url: string
  thumb_url: string
  uploaded_by: DeviceUser
  created_at: string
}

export async function fetchPhotos(deviceId: number): Promise<PhotoRead[]> {
  return apiGet<PhotoRead[]>(`/devices/${deviceId}/photos`)
}

/**
 * Загрузка пачки файлов одним запросом.
 *
 * `Content-Type` не задаём: браузер сам проставит границу multipart, а явный
 * заголовок сломал бы разбор формы на бэкенде.
 */
export async function uploadPhotos(
  deviceId: number,
  files: File[],
  reportId?: number,
): Promise<PhotoRead[]> {
  const body = new FormData()
  for (const file of files) {
    body.append('files', file)
  }
  if (reportId !== undefined) {
    body.append('report_id', String(reportId))
  }
  return apiFetch<PhotoRead[]>(`/devices/${deviceId}/photos`, {
    method: 'POST',
    body,
  })
}

export async function deletePhoto(photoId: number): Promise<void> {
  return apiFetch<void>(`/photos/${photoId}`, { method: 'DELETE' })
}
