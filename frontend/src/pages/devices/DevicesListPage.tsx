/** Список устройств: серверный поиск, фильтры и страница в URL, сортировка. */

import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import {
  Alert,
  Badge,
  Button,
  Center,
  Chip,
  Group,
  Loader,
  Pagination,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  UnstyledButton,
} from '@mantine/core'

import { ApiError } from '../../api/client'
import { fetchDevices } from '../../api/devices'
import type { DeviceQuery, DeviceSort } from '../../api/devices'
import { deviceState } from '../../lib/device'
import { formatDate } from '../../lib/format'

const DEBOUNCE_MS = 300
const PAGE_SIZES = ['25', '50', '100']

/** Клик по заголовку: прямой порядок → обратный → снова прямой. */
const SORTS: { label: string; asc: DeviceSort; desc: DeviceSort }[] = [
  { label: 'Инв. №', asc: 'inventory_no', desc: '-inventory_no' },
  { label: 'Модель', asc: 'model', desc: '-model' },
  { label: 'Обновлено', asc: 'updated_at', desc: '-updated_at' },
]

function queryFromParams(params: URLSearchParams): DeviceQuery {
  const status = params.get('status')
  const sort = params.get('sort')
  return {
    q: params.get('q') ?? undefined,
    status: status === 'active' || status === 'repair' || status === 'lost' ? status : undefined,
    overdue: params.get('overdue') === 'true',
    mine: params.get('mine') === 'true',
    archived: params.get('archived') === 'true',
    sort: (sort as DeviceSort | null) ?? undefined,
    page: Number(params.get('page') ?? '1'),
    page_size: Number(params.get('page_size') ?? '25'),
  }
}

export function DevicesListPage() {
  const [params, setParams] = useSearchParams()
  const query = useMemo(() => queryFromParams(params), [params])
  const [search, setSearch] = useState(params.get('q') ?? '')

  const update = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(patch)) {
      if (value === null || value === '') next.delete(key)
      else next.set(key, value)
    }
    if (!('page' in patch)) next.delete('page')
    setParams(next, { replace: true })
  }

  // URL — источник истины: переход «назад» или по ссылке возвращает текст поиска.
  useEffect(() => {
    setSearch(params.get('q') ?? '')
  }, [params])

  // Серверный поиск с задержкой ввода; значение уже совпадает — не трогаем URL.
  useEffect(() => {
    const value = search.trim()
    const timer = window.setTimeout(() => {
      if (value !== (params.get('q') ?? '')) update({ q: value })
    }, DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

  const { isPending, isError, error, data } = useQuery({
    queryKey: ['devices', params.toString()],
    queryFn: () => fetchDevices(query),
  })

  const message = error instanceof ApiError ? error.message : 'Ошибка сети. Повторите попытку'
  useEffect(() => {
    if (isError) notifications.show({ message, color: 'red' })
  }, [isError, message])

  const hasFilters = Array.from(params.keys()).length > 0
  const pageSize = query.page_size ?? 25
  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1

  const toggleSort = (sort: { asc: DeviceSort; desc: DeviceSort }) => {
    const current = (params.get('sort') ?? 'inventory_no') as DeviceSort
    update({ sort: current === sort.asc ? sort.desc : sort.asc })
  }

  const resetFilters = () => setParams(new URLSearchParams(), { replace: true })

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Устройства</Title>
        <Button component={Link} to="/devices/new">
          Добавить устройство
        </Button>
      </Group>

      <Group align="flex-end" justify="space-between">
        <TextInput
          label="Поиск"
          placeholder="Инв. №, IMEI, serial, модель, ФИО"
          w={{ base: '100%', sm: 360 }}
          value={search}
          onChange={(event) => setSearch(event.currentTarget.value)}
        />
        <Group gap="xs">
          <Chip
            checked={params.get('mine') === 'true'}
            onChange={(checked) => update({ mine: checked ? 'true' : null })}
          >
            Мои
          </Chip>
          <Chip
            checked={params.get('overdue') === 'true'}
            onChange={(checked) => update({ overdue: checked ? 'true' : null })}
          >
            Просроченные
          </Chip>
          <Chip
            checked={params.get('status') === 'repair'}
            onChange={(checked) => update({ status: checked ? 'repair' : null })}
          >
            В ремонте
          </Chip>
          <Chip
            checked={params.get('archived') === 'true'}
            onChange={(checked) => update({ archived: checked ? 'true' : null })}
          >
            Архив
          </Chip>
        </Group>
      </Group>

      {isPending ? (
        <Center mih={300}>
          <Loader />
        </Center>
      ) : isError || !data ? (
        <Alert color="red" title="Не удалось загрузить устройства">
          {message}
        </Alert>
      ) : data.items.length === 0 ? (
        <Center mih={200}>
          <Stack align="center" gap="sm">
            <Text c="dimmed">
              {hasFilters ? 'Ничего не найдено' : 'Устройств пока нет'}
            </Text>
            {hasFilters ? (
              <Button variant="default" onClick={resetFilters}>
                Сбросить фильтры
              </Button>
            ) : (
              <Button component={Link} to="/devices/new">
                Добавить устройство
              </Button>
            )}
          </Stack>
        </Center>
      ) : (
        <>
          <Paper withBorder radius="md">
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  {SORTS.map((sort) => (
                    <Table.Th key={sort.asc}>
                      <UnstyledButton onClick={() => toggleSort(sort)}>
                        {sort.label}
                        {currentSortLabel(params.get('sort'), sort)}
                      </UnstyledButton>
                    </Table.Th>
                  ))}
                  <Table.Th>Владелец</Table.Th>
                  <Table.Th>На руках у</Table.Th>
                  <Table.Th>Возврат до</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.items.map((device) => {
                  const state = deviceState(device)
                  return (
                    <Table.Tr key={device.id}>
                      <Table.Td>
                        <Link to={`/devices/${device.id}`}>{device.inventory_no}</Link>
                      </Table.Td>
                      <Table.Td>
                        {device.brand} {device.model}
                      </Table.Td>
                      <Table.Td>
                        <Badge color={state.color}>{state.label}</Badge>
                      </Table.Td>
                      <Table.Td>{device.owner.full_name}</Table.Td>
                      <Table.Td>{device.holder.full_name}</Table.Td>
                      <Table.Td>{formatDate(device.expected_return_at)}</Table.Td>
                    </Table.Tr>
                  )
                })}
              </Table.Tbody>
            </Table>
          </Paper>

          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              Всего: {data.total}
            </Text>
            <Group gap="sm">
              <Select
                aria-label="Строк на страницу"
                data={PAGE_SIZES}
                value={String(pageSize)}
                allowDeselect={false}
                w={90}
                size="sm"
                onChange={(value) => {
                  if (value) update({ page_size: value })
                }}
              />
              <Pagination
                total={totalPages}
                value={query.page ?? 1}
                onChange={(page) => update({ page: String(page) })}
                size="sm"
              />
            </Group>
          </Group>
        </>
      )}
    </Stack>
  )
}

function currentSortLabel(
  current: string | null,
  sort: { asc: DeviceSort; desc: DeviceSort },
): string {
  if (current === sort.asc) return ' ↑'
  if (current === sort.desc) return ' ↓'
  return ''
}
