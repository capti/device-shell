/** Отчёты: дашборд, «у кого что», «просроченные» и ссылка на Excel-выгрузку. */

import { apiGet, apiUrl } from './client'

export interface Counters {
  total_active: number
  with_owners: number
  checked_out: number
  in_repair: number
  lost: number
  archived: number
  overdue: number
}

export interface Person {
  id: number
  username: string
  full_name: string
}

export interface OverdueTile {
  device_id: number
  inventory_no: string
  model: string
  holder: Person
  days_overdue: number
}

export interface DashboardStats {
  counters: Counters
  top_overdue: OverdueTile[]
}

export interface TurnoverPoint {
  month: string
  checked_out: number
  returned: number
}

export interface OverdueBucket {
  bucket: string
  count: number
}

export interface DashboardCharts {
  turnover: TurnoverPoint[]
  overdue_buckets: OverdueBucket[]
}

export type ReportStatus = 'active' | 'repair' | 'lost'

export interface HoldersRow {
  device_id: number
  inventory_no: string
  model: string
  status: ReportStatus
  owner: Person
  holder: Person
}

export interface HoldersReport {
  items: HoldersRow[]
}

export interface OverdueRow {
  device_id: number
  inventory_no: string
  model: string
  owner: Person
  holder: Person
  taken_at: string | null
  expected_return_at: string | null
  days_overdue: number
}

export interface OverdueReport {
  items: OverdueRow[]
}

export interface ExportQuery {
  from_date?: string
  to_date?: string
  overdue?: boolean
  status?: ReportStatus
  q?: string
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  return apiGet<DashboardStats>('/dashboard/stats')
}

export async function fetchDashboardCharts(): Promise<DashboardCharts> {
  return apiGet<DashboardCharts>('/dashboard/charts')
}

export async function fetchHoldersReport(): Promise<HoldersReport> {
  return apiGet<HoldersReport>('/reports/holders')
}

export async function fetchOverdueReport(): Promise<OverdueReport> {
  return apiGet<OverdueReport>('/reports/overdue')
}

/** Ссылка на скачивание: файл отдаёт бэк, cookie сессии уходит сама. */
export function exportUrl(query: ExportQuery): string {
  const search = new URLSearchParams()
  if (query.from_date) search.set('from_date', query.from_date)
  if (query.to_date) search.set('to_date', query.to_date)
  if (query.overdue) search.set('overdue', 'true')
  if (query.status) search.set('status', query.status)
  if (query.q) search.set('q', query.q)
  const suffix = search.toString()
  return apiUrl(suffix ? `/reports/export.xlsx?${suffix}` : '/reports/export.xlsx')
}
