/** Типы уведомлений бэка: подписи на русском и цвета акцента. */

import type { NotificationRead } from '../api/notifications'

const LABELS: Record<string, string> = {
  owner_changed: 'Сменён владелец устройства',
  device_archived: 'Устройство отправлено в архив',
  device_restored: 'Устройство восстановлено',
  device_lost: 'Устройство помечено утерянным',
  requires_repair: 'В отчёте отмечен ремонт',
  device_checked_out: 'Устройство выдано',
  device_returned: 'Устройство возвращено',
  condition_reported: 'Новый отчёт о состоянии',
  checkout_overdue: 'Просрочен возврат',
  user_deactivated: 'Сотрудник деактивирован',
  role_changed: 'Изменена роль',
  password_reset: 'Пароль сброшен',
}

const COLORS: Record<string, string> = {
  checkout_overdue: 'red',
  device_lost: 'red',
  requires_repair: 'orange',
  device_checked_out: 'blue',
  device_returned: 'teal',
  password_reset: 'grape',
}

/** Неизвестный тип показываем как есть — новые события не должны прятаться. */
export function notificationLabel(type: string): string {
  return LABELS[type] ?? type
}

export function notificationColor(type: string): string {
  return COLORS[type] ?? 'gray'
}

/** Инвентарный номер из payload: бэк кладёт его для событий по устройству. */
export function notificationInventory(notification: NotificationRead): string | null {
  const value = notification.payload?.inventory_no
  return typeof value === 'string' ? value : null
}
