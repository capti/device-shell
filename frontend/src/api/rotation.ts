/** Оборот устройства: выдача, передача, возврат и смена статуса. */

import type { DeviceRead } from './devices'
import type { ConditionValue } from '../lib/condition'
import { apiPost } from './client'

export interface ReturnPayload {
  condition_in: ConditionValue
  comment_in?: string
  requires_repair?: boolean
}

export interface CheckoutPayload {
  holder_id: number
  expected_return_at?: string
  condition_out?: ConditionValue
  comment_out?: string
}

export interface TransferPayload {
  holder_id: number
  expected_return_at?: string
  condition_in?: ConditionValue
  comment?: string
}

/** Только `lost` и `active`: `repair` меняется журналом ремонтов. */
export interface StatusPayload {
  status: 'lost' | 'active'
  /** Обязателен бэком при возврате из `lost`. */
  comment?: string
}

export async function returnDevice(
  deviceId: number,
  payload: ReturnPayload,
): Promise<DeviceRead> {
  return apiPost<DeviceRead>(`/devices/${deviceId}/return`, payload)
}

export async function checkoutDevice(
  deviceId: number,
  payload: CheckoutPayload,
): Promise<DeviceRead> {
  return apiPost<DeviceRead>(`/devices/${deviceId}/checkout`, payload)
}

export async function transferDevice(
  deviceId: number,
  payload: TransferPayload,
): Promise<DeviceRead> {
  return apiPost<DeviceRead>(`/devices/${deviceId}/transfer`, payload)
}

/** `POST /devices/{id}/status`: 409 `INVALID_STATUS_TRANSITION`, 422 `COMMENT_REQUIRED`. */
export async function changeStatus(
  deviceId: number,
  payload: StatusPayload,
): Promise<DeviceRead> {
  return apiPost<DeviceRead>(`/devices/${deviceId}/status`, payload)
}
