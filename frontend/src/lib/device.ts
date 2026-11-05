/** Вычисляемое состояние устройства для бейджей: одно выражение — как на бэке. */

import type { DeviceRead } from '../api/devices'

export interface DeviceState {
  label: string
  color: string
}

export function deviceState(device: DeviceRead): DeviceState {
  if (device.archived_at) return { label: 'В архиве', color: 'gray' }
  if (device.status === 'lost') return { label: 'Утерян', color: 'red' }
  if (device.status === 'repair') return { label: 'В ремонте', color: 'orange' }
  if (device.holder.id !== device.owner.id) {
    return device.overdue
      ? { label: 'Выдан · просрочен', color: 'red' }
      : { label: 'Выдан', color: 'blue' }
  }
  return { label: 'У владельца', color: 'teal' }
}

/** События истории → подпись на русском; неизвестные типы показываем как есть. */
const EVENT_LABELS: Record<string, string> = {
  created: 'Создано',
  updated: 'Изменено',
  owner_changed: 'Сменён владелец',
  archived: 'Отправлено в архив',
  restored: 'Восстановлено',
  status_changed: 'Статус изменён',
  checked_out: 'Выдано',
  returned: 'Возвращено',
  transferred: 'Передано',
  ownership_transferred: 'Владение передано',
  checkout_closed: 'Выдача закрыта',
  condition_reported: 'Отчёт о состоянии',
  photo_added: 'Добавлено фото',
  photo_removed: 'Фото удалено',
  repair_started: 'Отправлено в ремонт',
  repair_finished: 'Ремонт завершён',
}

export function eventLabel(type: string): string {
  return EVENT_LABELS[type] ?? type
}
