/** Профиль «Мои»: устройства во владении и на руках + смена своего пароля в модалке. */

import { useState } from 'react'
import { Link } from 'react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import {
  Badge,
  Button,
  Center,
  Group,
  Loader,
  Modal,
  PasswordInput,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core'

import { me } from '../../api/auth'
import { fetchDevices } from '../../api/devices'
import type { DeviceListResponse } from '../../api/devices'
import { changePassword } from '../../api/profile'
import { errorMessage } from '../../lib/errors'
import { deviceState } from '../../lib/device'

const MIN_PASSWORD_LENGTH = 8

export function ProfilePage() {
  const meQuery = useQuery({ queryKey: ['me'], queryFn: me })
  const userId = meQuery.data?.id
  const [passwordOpened, setPasswordOpened] = useState(false)

  const ownedQuery = useQuery({
    queryKey: ['profile-devices', 'owned', userId],
    queryFn: () => fetchDevices({ owner_id: userId, page_size: 100 }),
    enabled: userId !== undefined,
  })
  const heldQuery = useQuery({
    queryKey: ['profile-devices', 'held', userId],
    queryFn: () => fetchDevices({ holder_id: userId, page_size: 100 }),
    enabled: userId !== undefined,
  })

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Мои устройства</Title>
        <Button variant="default" onClick={() => setPasswordOpened(true)}>
          Сменить пароль
        </Button>
      </Group>

      {meQuery.data && (
        <Text size="sm" c="dimmed">
          {meQuery.data.full_name} · {meQuery.data.username}
          {meQuery.data.role === 'admin' ? ' · администратор' : ''}
        </Text>
      )}

      <DeviceBlock
        title="Владею (закреплено)"
        empty="За вами пока нет закреплённых устройств"
        query={ownedQuery}
      />
      <DeviceBlock
        title="На руках сейчас"
        empty="У вас нет телефонов на руках"
        query={heldQuery}
      />

      {passwordOpened && (
        <ChangePasswordModal
          key="change-password"
          onClose={() => setPasswordOpened(false)}
        />
      )}
    </Stack>
  )
}

function DeviceBlock({
  title,
  empty,
  query,
}: {
  title: string
  empty: string
  query: ReturnType<typeof useQuery<DeviceListResponse>>
}) {
  return (
    <Paper withBorder radius="md" p="md">
      <Stack gap="sm">
        <Text fw={500}>{title}</Text>

        {query.isPending && (
          <Center mih={80}>
            <Loader />
          </Center>
        )}

        {query.isError && (
          <Text size="sm" c="red">
            Не удалось загрузить устройства
          </Text>
        )}

        {query.data && query.data.items.length === 0 && (
          <Text size="sm" c="dimmed">
            {empty}
          </Text>
        )}

        {query.data && query.data.items.length > 0 && (
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Инв. №</Table.Th>
                <Table.Th>Модель</Table.Th>
                <Table.Th>Состояние</Table.Th>
                <Table.Th>Владелец</Table.Th>
                <Table.Th>На руках у</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {query.data.items.map((device) => {
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
                  </Table.Tr>
                )
              })}
            </Table.Tbody>
          </Table>
        )}
      </Stack>
    </Paper>
  )
}

function ChangePasswordModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const tooShort = next.length > 0 && next.length < MIN_PASSWORD_LENGTH
  const mismatch = confirm.length > 0 && next !== confirm
  const canSubmit =
    current.length > 0 && next.length >= MIN_PASSWORD_LENGTH && next === confirm

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      await changePassword(current, next)
      notifications.show({ message: 'Пароль обновлён', color: 'green' })
      queryClient.invalidateQueries({ queryKey: ['me'] })
      onClose()
    } catch (cause) {
      // 422 INVALID_PASSWORD / WEAK_PASSWORD — текст бэка под полем, ввод сохраняется
      setError(errorMessage(cause))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal opened onClose={onClose} title="Смена пароля" centered>
      <Stack gap="md">
        <PasswordInput
          label="Текущий пароль"
          value={current}
          required
          onChange={(event) => setCurrent(event.currentTarget.value)}
        />
        <PasswordInput
          label="Новый пароль"
          description={`Минимум ${MIN_PASSWORD_LENGTH} символов`}
          value={next}
          required
          error={tooShort ? `Минимум ${MIN_PASSWORD_LENGTH} символов` : null}
          onChange={(event) => setNext(event.currentTarget.value)}
        />
        <PasswordInput
          label="Повторите новый пароль"
          value={confirm}
          required
          error={mismatch ? 'Пароли не совпадают' : null}
          onChange={(event) => setConfirm(event.currentTarget.value)}
        />
        {error && (
          <Text size="sm" c="red">
            {error}
          </Text>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Отмена
          </Button>
          <Button loading={busy} disabled={!canSubmit} onClick={submit}>
            Сменить пароль
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
