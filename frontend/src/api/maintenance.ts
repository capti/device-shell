/** Отчёты о состоянии устройства: список и создание. */

import { apiGet, apiPost } from './client'
import type { DeviceUser } from './devices'
import type { PhotoRead } from './photos'
import type { ConditionValue } from '../lib/condition'

export interface ConditionReportRead {
  id: number
  device_id: number
  checkout_id: number | null
  author: DeviceUser
  condition: ConditionValue
  requires_repair: boolean
  comment: string | null
  photos: PhotoRead[]
  created_at: string
}

export interface ConditionReportPayload {
  condition: ConditionValue
  requires_repair?: boolean
  comment?: string
}

export async function fetchConditionReports(
  deviceId: number,
): Promise<ConditionReportRead[]> {
  return apiGet<ConditionReportRead[]>(`/devices/${deviceId}/condition-reports`)
}

export async function createConditionReport(
  deviceId: number,
  payload: ConditionReportPayload,
): Promise<ConditionReportRead> {
  return apiPost<ConditionReportRead>(`/devices/${deviceId}/condition-reports`, payload)
}
