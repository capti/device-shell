/** Уведомления в шапке: счётчик непрочитанных, список и переход к устройству. */

import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import {
  Badge,
  Button,
  Divider,
  Group,
  Popover,
  ScrollArea,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core'

import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../api/notifications'
import type { NotificationRead } from '../api/notifications'
import { errorMessage } from '../lib/errors'
import { formatDateTime } from '../lib/format'
import {
  notificationColor,
  notificationInventory,
  notificationLabel,
} from '../lib/notifications'

const PAGE_SIZE = 20
const POLL_MS = 60_000

export function NotificationsBell() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [opened, setOpened] = useState(false)
  const [shown, setShown] = useState(PAGE_SIZE)
  const [markingAll, setMarkingAll] = useState(false)

  const query = useQuery({
    queryKey: ['notifications', shown],
    queryFn: () => fetchNotifications(shown, 1),
    refetchInterval: POLL_MS,
  })

  const unread = query.data?.unread ?? 0
  const items = query.data?.items ?? []
  const total = query.data?.total ?? 0

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['notifications'] })

  const open = async (item: NotificationRead) => {
    setOpened(false)
    // Переход важнее отметки: закрываем панель, ошибку прочтения показываем тостом
    if (item.read_at === null) {
      try {
        await markNotificationRead(item.id)
        refresh()
      } catch (cause) {
        notifications.show({ message: errorMessage(cause), color: 'red' })
      }
    }
    if (item.device_id !== null) navigate(`/devices/${item.device_id}`)
  }

  const readAll = async () => {
    setMarkingAll(true)
    try {
      await markAllNotificationsRead()
      refresh()
    } catch (cause) {
      notifications.show({ message: errorMessage(cause), color: 'red' })
    } finally {
      setMarkingAll(false)
    }
  }

  return (
    <Popover
      opened={opened}
      onChange={setOpened}
      position="bottom-end"
      width={400}
      shadow="md"
      withinPortal
    >
      <Popover.Target>
        <Button
          variant="default"
          size="compact-sm"
          onClick={() => setOpened((value) => !value)}
        >
          Уведомления
          {unread > 0 && (
            <Badge ml={6} size="sm" color="red" circle>
              {unread > 99 ? '99+' : unread}
            </Badge>
          )}
        </Button>
      </Popover.Target>

      <Popover.Dropdown p={0}>
        <Group justify="space-between" p="sm">
          <Text size="sm" fw={500}>
            Уведомления
          </Text>
          <Button
            size="compact-xs"
            variant="subtle"
            loading={markingAll}
            disabled={unread === 0}
            onClick={readAll}
          >
            Прочитать всё
          </Button>
        </Group>
        <Divider />

        {query.isError && (
          <Text p="md" size="sm" c="red">
            {errorMessage(query.error)}
          </Text>
        )}

        {!query.isError && items.length === 0 && (
          <Text p="md" size="sm" c="dimmed">
            Уведомлений нет
          </Text>
        )}

        {items.length > 0 && (
          <ScrollArea.Autosize mah={420}>
            <Stack gap={0}>
              {items.map((item) => (
                <NotificationRow key={item.id} item={item} onOpen={open} />
              ))}
            </Stack>
          </ScrollArea.Autosize>
        )}

        {items.length < total && (
          <>
            <Divider />
            <Group justify="center" p="xs">
              <Button size="compact-xs" variant="subtle" onClick={() => setShown((v) => v + PAGE_SIZE)}>
                Показать ещё
              </Button>
            </Group>
          </>
        )}
      </Popover.Dropdown>
    </Popover>
  )
}

function NotificationRow({
  item,
  onOpen,
}: {
  item: NotificationRead
  onOpen: (item: NotificationRead) => void
}) {
  const details = [notificationInventory(item), item.actor?.full_name]
    .filter((value): value is string => Boolean(value))
    .join(' · ')
  const color = notificationColor(item.type)

  return (
    <UnstyledButton
      onClick={() => onOpen(item)}
      p="sm"
      style={{
        width: '100%',
        backgroundColor: item.read_at === null ? 'var(--mantine-color-blue-0)' : undefined,
      }}
    >
      <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
        <Stack gap={2}>
          <Group gap={6} wrap="nowrap">
            <Badge size="xs" variant="light" color={color}>
              {notificationLabel(item.type)}
            </Badge>
          </Group>
          {details && (
            <Text size="xs" c="dimmed">
              {details}
            </Text>
          )}
        </Stack>
        <Text size="xs" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
          {formatDateTime(item.created_at)}
        </Text>
      </Group>
    </UnstyledButton>
  )
}
