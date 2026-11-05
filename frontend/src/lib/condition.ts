/** Состояния устройства: значения бэка, подписи и цвета бейджей. */

export type ConditionValue = 'ok' | 'scratches' | 'damaged' | 'not_working'

export const CONDITION_OPTIONS: { value: ConditionValue; label: string }[] = [
  { value: 'ok', label: 'В порядке' },
  { value: 'scratches', label: 'Царапины' },
  { value: 'damaged', label: 'Повреждён' },
  { value: 'not_working', label: 'Не работает' },
]

const COLORS: Record<ConditionValue, string> = {
  ok: 'teal',
  scratches: 'yellow',
  damaged: 'orange',
  not_working: 'red',
}

export function conditionLabel(value: string): string {
  return CONDITION_OPTIONS.find((option) => option.value === value)?.label ?? value
}

export function conditionColor(value: string): string {
  return COLORS[value as ConditionValue] ?? 'gray'
}
