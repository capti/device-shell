/** Типы и запросы устройств: список, карточка, архив, восстановление, история. */

import { apiFetch, apiGet, apiPost } from './client'

export type DeviceStatus = 'active' | 'repair' | 'lost'
export type DeviceSort =
  | 'inventory_no'
  | '-inventory_no'
  | 'model'
  | '-model'
  | 'updated_at'
  | '-updated_at'

export interface DeviceUser {
  id: number
  username: string
  full_name: string
}

export interface DeviceRead {
  id: number
  inventory_no: string
  serial_no: string | null
  imei: string | null
  brand: string
  model: string
  os: string | null
  os_version: string | null
  storage: string | null
  color: string | null
  device_type: string | null
  purchase_year: number | null
  status: DeviceStatus
  notes: string | null
  accounts_note: string | null
  owner: DeviceUser
  holder: DeviceUser
  overdue: boolean
  expected_return_at: string | null
  archived_at: string | null
  created_at: string
  updated_at: string
}

export interface DeviceListResponse {
  items: DeviceRead[]
  total: number
  page: number
  page_size: number
}

export interface DeviceEventRead {
  id: number
  type: string
  actor: DeviceUser | null
  payload: Record<string, unknown> | null
  created_at: string
}

export interface DeviceQuery {
  q?: string
  status?: DeviceStatus
  overdue?: boolean
  mine?: boolean
  owner_id?: number
  holder_id?: number
  archived?: boolean
  sort?: DeviceSort
  page?: number
  page_size?: number
}

export interface DevicePayload {
  inventory_no?: string | null
  serial_no?: string | null
  imei?: string | null
  brand: string
  model: string
  os?: string | null
  os_version?: string | null
  storage?: string | null
  color?: string | null
  device_type?: string | null
  purchase_year?: number | null
  notes?: string | null
  accounts_note?: string | null
  owner_id?: number
}

function buildQuery(params: DeviceQuery): string {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  if (params.status) search.set('status', params.status)
  if (params.overdue) search.set('overdue', 'true')
  if (params.mine) search.set('mine', 'true')
  if (params.owner_id) search.set('owner_id', String(params.owner_id))
  if (params.holder_id) search.set('holder_id', String(params.holder_id))
  if (params.archived) search.set('archived', 'true')
  if (params.sort && params.sort !== 'inventory_no') search.set('sort', params.sort)
  if (params.page && params.page > 1) search.set('page', String(params.page))
  if (params.page_size && params.page_size !== 25) {
    search.set('page_size', String(params.page_size))
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

export async function fetchDevices(params: DeviceQuery): Promise<DeviceListResponse> {
  return apiGet<DeviceListResponse>(`/devices${buildQuery(params)}`)
}

export async function fetchDevice(id: number): Promise<DeviceRead> {
  return apiGet<DeviceRead>(`/devices/${id}`)
}

export async function createDevice(payload: DevicePayload): Promise<DeviceRead> {
  return apiPost<DeviceRead>('/devices', payload)
}

export async function updateDevice(
  id: number,
  payload: Partial<DevicePayload>,
): Promise<DeviceRead> {
  return apiFetch<DeviceRead>(`/devices/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function archiveDevice(id: number): Promise<DeviceRead> {
  return apiPost<DeviceRead>(`/devices/${id}/archive`)
}

export interface RestorePayload {
  owner_id?: number
  status?: DeviceStatus
}

export async function restoreDevice(id: number, payload: RestorePayload): Promise<DeviceRead> {
  return apiPost<DeviceRead>(`/devices/${id}/restore`, payload)
}

export async function fetchDeviceHistory(id: number): Promise<DeviceEventRead[]> {
  return apiGet<DeviceEventRead[]>(`/devices/${id}/history`)
}
