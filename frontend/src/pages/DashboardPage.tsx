/** Дашборд: счётчики, графики и топ просроченных возвратов. */

import { Suspense, lazy } from 'react'
import {
  Alert,
  Center,
  Loader,
  Paper,
  SimpleGrid,
  Table,
  Text,
  Title,
} from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import type { ReactNode } from 'react'

import { ApiError } from '../api/client'
import { fetchDashboardStats } from '../api/reports'
import { formatDays } from '../lib/format'

const DashboardCharts = lazy(() => import('./DashboardCharts'))

const COUNTER_LABELS = [
  ['total_active', 'Активно'],
  ['with_owners', 'У владельцев'],
  ['checked_out', 'Выдано'],
  ['in_repair', 'В ремонте'],
  ['lost', 'Утеряно'],
  ['archived', 'В архиве'],
  ['overdue', 'Просрочено'],
] as const

export function DashboardPage() {
  const { isPending, isError, error, data } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: fetchDashboardStats,
  })

  if (isPending) {
    return (
      <Center mih={300}>
        <Loader />
      </Center>
    )
  }
  if (isError || !data) {
    const message =
      error instanceof ApiError ? error.message : 'Ошибка сети. Повторите попытку'
    notifications.show({ message, color: 'red' })
    return (
      <Alert color="red" title="Не удалось загрузить дашборд">
        {message}
      </Alert>
    )
  }

  return (
    <StackGap>
      <Title order={3}>Дашборд</Title>
      <SimpleGrid cols={{ base: 2, sm: 4, md: 7 }} spacing="sm">
        {COUNTER_LABELS.map(([key, label]) => (
          <Paper key={key} p="sm" radius="md" withBorder>
            <Text c="dimmed" size="sm">
              {label}
            </Text>
            <Text fw={700} fz="xl">
              {data.counters[key]}
            </Text>
          </Paper>
        ))}
      </SimpleGrid>

      <Title order={4}>Сводка по парку</Title>
      <Suspense fallback={<Center mih={260}><Loader size="sm" /></Center>}>
        <DashboardCharts counters={data.counters} />
      </Suspense>

      <Title order={4}>Просроченные возвраты</Title>
      {data.top_overdue.length === 0 ? (
        <Text c="dimmed">Нет просроченных возвратов</Text>
      ) : (
        <Paper withBorder radius="md">
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Инв. №</Table.Th>
                <Table.Th>Модель</Table.Th>
                <Table.Th>У кого</Table.Th>
                <Table.Th>Просрочено</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.top_overdue.map((row) => (
                <Table.Tr key={row.device_id}>
                  <Table.Td>{row.inventory_no}</Table.Td>
                  <Table.Td>{row.model}</Table.Td>
                  <Table.Td>{row.holder.full_name}</Table.Td>
                  <Table.Td>{formatDays(row.days_overdue)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Paper>
      )}
    </StackGap>
  )
}

function StackGap({ children }: { children: ReactNode }) {
  return <div style={{ display: 'grid', gap: 16 }}>{children}</div>
}
