/** Даты интерфейса — `ДД.ММ.ГГГГ` (конвенция UI); пусто для отсутствующих. */

const pad = (value: number) => String(value).padStart(2, '0')

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) return ''
  return `${pad(moment.getDate())}.${pad(moment.getMonth() + 1)}.${moment.getFullYear()}`
}

/** Дата со временем для таймлайна: `ДД.ММ.ГГГГ ЧЧ:ММ`. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) return ''
  return `${formatDate(iso)} ${pad(moment.getHours())}:${pad(moment.getMinutes())}`
}

/** Значение `<input type="date">` (`2026-11-15`) → ISO datetime для API. */
export function toIsoDateTime(value: string): string {
  return value.length === 10 ? `${value}T00:00:00` : value
}

/** Локальная дата ISO-строки в формате `YYYY-MM-DD` для `<input type="date">`. */
export function toDateInput(iso: string): string {
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) return ''
  return `${moment.getFullYear()}-${pad(moment.getMonth() + 1)}-${pad(moment.getDate())}`
}

/** Сегодняшний день в формате `YYYY-MM-DD` для `<input type="date">`. */
export function todayInput(): string {
  return toDateInput(new Date().toISOString())
}

/** Список просрочек и дней — уже числа от бэка; формат дней: «3 дн.» */
export function formatDays(days: number): string {
  return `${days} дн.`
}
