/** Отчёты «у кого что» и «просроченные» плюс Excel-выгрузка за период. */

import { useState } from 'react'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import {
  Alert,
  Anchor,
  Badge,
  Button,
  Center,
  Group,
  Loader,
  Paper,
  ScrollArea,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from '@mantine/core'

import { ApiError } from '../../api/client'
import {
  exportUrl,
  fetchHoldersReport,
  fetchOverdueReport,
} from '../../api/reports'
import { formatDate, formatDays } from '../../lib/format'

const STATUS_LABELS: Record<string, string> = {
  active: 'Активно',
  repair: 'В ремонте',
  lost: 'Утерян',
}

export function ReportsPage() {
  const [tab, setTab] = useState<string | null>('holders')
  const holders = useQuery({ queryKey: ['reports', 'holders'], queryFn: fetchHoldersReport })
  const overdue = useQuery({ queryKey: ['reports', 'overdue'], queryFn: fetchOverdueReport })

  return (
    <Stack gap="md">
      <Title order={3}>Отчёты</Title>
      <ExportPanel />

      <Tabs value={tab} onChange={setTab}>
        <Tabs.List>
          <Tabs.Tab value="holders">У кого что</Tabs.Tab>
          <Tabs.Tab value="overdue">Просроченные</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="holders" pt="md">
          <QueryFrame
            query={holders}
            empty="Активных устройств нет"
            render={(items) => (
              <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Инв. №</Table.Th>
                    <Table.Th>Модель</Table.Th>
                    <Table.Th>Статус</Table.Th>
                    <Table.Th>Владелец</Table.Th>
                    <Table.Th>На руках у</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {items.map((row) => (
                    <Table.Tr key={row.device_id}>
                      <Table.Td>
                        <Anchor component={Link} to={`/devices/${row.device_id}`} size="sm">
                          {row.inventory_no}
                        </Anchor>
                      </Table.Td>
                      <Table.Td>{row.model}</Table.Td>
                      <Table.Td>
                        <Badge variant="light" color={row.status === 'lost' ? 'red' : undefined}>
                          {STATUS_LABELS[row.status] ?? row.status}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{row.owner.full_name}</Table.Td>
                      <Table.Td>
                        {row.holder.id === row.owner.id ? (
                          <Text size="sm" c="dimmed">
                            у владельца
                          </Text>
                        ) : (
                          row.holder.full_name
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          />
        </Tabs.Panel>

        <Tabs.Panel value="overdue" pt="md">
          <QueryFrame
            query={overdue}
            empty="Просрочек нет"
            render={(items) => (
              <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Инв. №</Table.Th>
                    <Table.Th>Модель</Table.Th>
                    <Table.Th>Владелец</Table.Th>
                    <Table.Th>Держатель</Table.Th>
                    <Table.Th>Выдано</Table.Th>
                    <Table.Th>Возврат до</Table.Th>
                    <Table.Th>Просрочка</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {items.map((row) => (
                    <Table.Tr key={row.device_id}>
                      <Table.Td>
                        <Anchor component={Link} to={`/devices/${row.device_id}`} size="sm">
                          {row.inventory_no}
                        </Anchor>
                      </Table.Td>
                      <Table.Td>{row.model}</Table.Td>
                      <Table.Td>{row.owner.full_name}</Table.Td>
                      <Table.Td>{row.holder.full_name}</Table.Td>
                      <Table.Td>{formatDate(row.taken_at) || '—'}</Table.Td>
                      <Table.Td>{formatDate(row.expected_return_at) || '—'}</Table.Td>
                      <Table.Td>
                        <Badge color="red" variant="light">
                          {formatDays(row.days_overdue)}
                        </Badge>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}

function QueryFrame<T>({
  query,
  empty,
  render,
}: {
  query: { isPending: boolean; isError: boolean; error: unknown; data?: { items: T[] } }
  empty: string
  render: (items: T[]) => React.ReactNode
}) {
  if (query.isPending) {
    return (
      <Center mih={160}>
        <Loader />
      </Center>
    )
  }
  if (query.isError || !query.data) {
    return (
      <Alert color="red" title="Не удалось загрузить отчёт">
        {query.error instanceof ApiError ? query.error.message : 'Ошибка сети. Повторите попытку'}
      </Alert>
    )
  }
  if (query.data.items.length === 0) {
    return <Text c="dimmed">{empty}</Text>
  }
  return (
    <Paper withBorder radius="md">
      <ScrollArea>
        {render(query.data.items)}
      </ScrollArea>
    </Paper>
  )
}

function ExportPanel() {
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [onlyOverdue, setOnlyOverdue] = useState(false)

  // Бэк отклонит обратный период 422 — не даём скачать ошибку
  const invalidPeriod = from !== '' && to !== '' && from > to
  const url = exportUrl({
    from_date: from || undefined,
    to_date: to || undefined,
    overdue: onlyOverdue || undefined,
  })

  return (
    <Paper withBorder radius="md" p="md">
      <Stack gap="sm">
        <Group justify="space-between" align="flex-end" wrap="wrap">
          <Group align="flex-end" gap="sm">
            <TextInput
              type="date"
              label="Период с"
              value={from}
              onChange={(event) => setFrom(event.currentTarget.value)}
            />
            <TextInput
              type="date"
              label="по"
              value={to}
              onChange={(event) => setTo(event.currentTarget.value)}
            />
            <Switch
              label="Только просроченные"
              checked={onlyOverdue}
              onChange={(event) => setOnlyOverdue(event.currentTarget.checked)}
              mb={6}
            />
          </Group>
          <Button
            component="a"
            href={invalidPeriod ? undefined : url}
            download
            aria-disabled={invalidPeriod}
            disabled={invalidPeriod}
          >
            Скачать Excel
          </Button>
        </Group>
        <Text size="xs" c="dimmed">
          Файл содержит листы «Все устройства», «Просроченные» и «История выдач» за
          период. Без дат берётся период с начала года по сегодня.
        </Text>
        {invalidPeriod && (
          <Text size="sm" c="red">
            Дата начала не может быть позже даты окончания
          </Text>
        )}
      </Stack>
    </Paper>
  )
}
