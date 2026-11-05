/** Журнал ремонтов устройства: список, отправка в ремонт, завершение. */

import { apiGet, apiPost } from './client'
import type { DeviceUser } from './devices'

export interface RepairRead {
  id: number
  device_id: number
  sent_at: string
  returned_at: string | null
  service: string | null
  description: string | null
  /** `Decimal` на бэке приходит строкой: `"1500.00"`. */
  cost: string | null
  comment: string | null
  created_by: DeviceUser | null
}

export interface RepairCreatePayload {
  service?: string
  description?: string
  cost?: number
  comment?: string
}

export interface RepairFinishPayload {
  returned_at?: string
  comment?: string
}

export async function fetchRepairs(deviceId: number): Promise<RepairRead[]> {
  return apiGet<RepairRead[]>(`/devices/${deviceId}/repairs`)
}

export async function startRepair(
  deviceId: number,
  payload: RepairCreatePayload,
): Promise<RepairRead> {
  return apiPost<RepairRead>(`/devices/${deviceId}/repairs`, payload)
}

export async function finishRepair(
  deviceId: number,
  repairId: number,
  payload: RepairFinishPayload,
): Promise<RepairRead> {
  return apiPost<RepairRead>(
    `/devices/${deviceId}/repairs/${repairId}/finish`,
    payload,
  )
}
