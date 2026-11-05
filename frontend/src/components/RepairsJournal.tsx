/** Раздел «Ремонты»: журнал обслуживания, отправка в ремонт и его завершение. */

import { useState } from 'react'
import {
  Badge,
  Button,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'

import { ApiError } from '../api/client'
import type { DeviceStatus } from '../api/devices'
import { finishRepair, startRepair } from '../api/repairs'
import type { RepairRead } from '../api/repairs'
import { errorMessage } from '../lib/errors'
import {
  formatDate,
  formatDateTime,
  toDateInput,
  toIsoDateTime,
  todayInput,
} from '../lib/format'

interface RepairsJournalProps {
  deviceId: number
  repairs: RepairRead[]
  status: DeviceStatus
  canManage: boolean
  isArchived: boolean
  onChanged: () => void
}

export function RepairsJournal({
  deviceId,
  repairs,
  status,
  canManage,
  isArchived,
  onChanged,
}: RepairsJournalProps) {
  const [startOpen, setStartOpen] = useState(false)
  const [finishFor, setFinishFor] = useState<RepairRead | null>(null)

  const openRepair = repairs.find((repair) => repair.returned_at === null)
  // Отправка имеет смысл только на активном устройстве; `lost` меняется отдельным
  // действием, `repair` — уже в ремонте, остаётся завершение
  const canStart = canManage && !isArchived && status === 'active'
  const canFinish = canManage && !isArchived && openRepair !== undefined

  return (
    <Stack gap="xs">
      <Group justify="space-between">
        <Text fw={500}>Ремонты</Text>
        <Group gap="xs">
          {canStart && (
            <Button size="xs" variant="default" onClick={() => setStartOpen(true)}>
              Отправить в ремонт
            </Button>
          )}
          {canFinish && (
            <Button size="xs" onClick={() => setFinishFor(openRepair)}>
              Завершить ремонт
            </Button>
          )}
        </Group>
      </Group>

      {repairs.length === 0 ? (
        <Text size="sm" c="dimmed">
          Ремонтов не было
        </Text>
      ) : (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Отправлен</Table.Th>
              <Table.Th>Возвращён</Table.Th>
              <Table.Th>Сервис</Table.Th>
              <Table.Th>Описание</Table.Th>
              <Table.Th>Стоимость</Table.Th>
              <Table.Th>Автор</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {repairs.map((repair) => (
              <Table.Tr key={repair.id}>
                <Table.Td>{formatDateTime(repair.sent_at)}</Table.Td>
                <Table.Td>
                  {repair.returned_at === null ? (
                    <Badge color="orange" variant="light">
                      В ремонте
                    </Badge>
                  ) : (
                    formatDate(repair.returned_at)
                  )}
                </Table.Td>
                <Table.Td>{repair.service ?? '—'}</Table.Td>
                <Table.Td>
                  {repair.description ?? '—'}
                  {repair.comment && (
                    <Text size="xs" c="dimmed">
                      {repair.comment}
                    </Text>
                  )}
                </Table.Td>
                <Table.Td>{formatCost(repair.cost)}</Table.Td>
                <Table.Td>{repair.created_by?.full_name ?? '—'}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {startOpen && (
        <StartRepairModal
          deviceId={deviceId}
          onClose={() => setStartOpen(false)}
          onDone={onChanged}
        />
      )}
      {finishFor && (
        <FinishRepairModal
          deviceId={deviceId}
          repair={finishFor}
          onClose={() => setFinishFor(null)}
          onDone={onChanged}
        />
      )}
    </Stack>
  )
}

/** `Decimal` приходит строкой (`"12000.00"`); пустая стоимость — прочерк. */
function formatCost(cost: string | null): string {
  if (cost === null) return '—'
  const value = Number(cost)
  return Number.isFinite(value) ? value.toLocaleString('ru-RU') : cost
}

function StartRepairModal({
  deviceId,
  onClose,
  onDone,
}: {
  deviceId: number
  onClose: () => void
  onDone: () => void
}) {
  const [service, setService] = useState('')
  const [description, setDescription] = useState('')
  const [cost, setCost] = useState('')
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [costError, setCostError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    const trimmedCost = cost.trim().replace(',', '.')
    if (trimmedCost !== '') {
      const value = Number(trimmedCost)
      if (!Number.isFinite(value) || value < 0) {
        setCostError('Стоимость — неотрицательное число')
        return
      }
    }
    setBusy(true)
    setCostError(null)
    setError(null)
    const trimmed = (value: string) => (value.trim() === '' ? undefined : value.trim())
    try {
      await startRepair(deviceId, {
        ...(trimmed(service) === undefined ? {} : { service: trimmed(service) }),
        ...(trimmed(description) === undefined
          ? {}
          : { description: trimmed(description) }),
        ...(trimmedCost === '' ? {} : { cost: Number(trimmedCost) }),
        ...(trimmed(comment) === undefined ? {} : { comment: trimmed(comment) }),
      })
      notifications.show({ message: 'Устройство отправлено в ремонт', color: 'green' })
      onClose()
      onDone()
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 409) {
        // ACTIVE_CHECKOUT / DEVICE_UNAVAILABLE — состояние не изменилось, окно не нужно
        notifications.show({ message: errorMessage(cause), color: 'red' })
        onClose()
        onDone()
      } else {
        setError(errorMessage(cause))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal opened onClose={onClose} title="Отправить в ремонт" centered>
      <Stack gap="md">
        <TextInput
          label="Сервис"
          value={service}
          onChange={(event) => setService(event.currentTarget.value)}
        />
        <Textarea
          label="Описание работ"
          autosize
          minRows={2}
          value={description}
          onChange={(event) => setDescription(event.currentTarget.value)}
        />
        <TextInput
          label="Стоимость"
          description="Число, можно с копейками"
          value={cost}
          error={costError}
          onChange={(event) => {
            setCost(event.currentTarget.value)
            setCostError(null)
          }}
        />
        <Textarea
          label="Комментарий"
          autosize
          minRows={2}
          value={comment}
          onChange={(event) => setComment(event.currentTarget.value)}
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
          <Button loading={busy} onClick={submit}>
            Отправить
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}

function FinishRepairModal({
  deviceId,
  repair,
  onClose,
  onDone,
}: {
  deviceId: number
  repair: RepairRead
  onClose: () => void
  onDone: () => void
}) {
  // Дата не раньше отправки — иначе бэк отвечает 422
  const minDate = toDateInput(repair.sent_at)
  const [date, setDate] = useState(() => {
    const today = todayInput()
    return today < minDate ? minDate : today
  })
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [dateError, setDateError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    if (date === '') return
    setBusy(true)
    setDateError(null)
    setError(null)
    try {
      await finishRepair(deviceId, repair.id, {
        returned_at: toIsoDateTime(date),
        ...(comment.trim() === '' ? {} : { comment: comment.trim() }),
      })
      notifications.show({ message: 'Ремонт завершён', color: 'green' })
      onClose()
      onDone()
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === 'REPAIR_ALREADY_FINISHED') {
        // В другой вкладке уже закрыли — показываем тост и перечитываем журнал
        notifications.show({ message: errorMessage(cause), color: 'red' })
        onClose()
        onDone()
      } else if (cause instanceof ApiError && cause.status === 422) {
        // Дата возврата раньше отправки — текст остаётся под полем, ввод сохраняется
        setDateError(errorMessage(cause))
      } else {
        setError(errorMessage(cause))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal opened onClose={onClose} title="Завершить ремонт" centered>
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Отправлен {formatDateTime(repair.sent_at)}
          {repair.service ? ` · ${repair.service}` : ''}
        </Text>
        <TextInput
          type="date"
          label="Дата возврата"
          required
          min={minDate}
          value={date}
          error={dateError}
          onChange={(event) => {
            setDate(event.currentTarget.value)
            setDateError(null)
          }}
        />
        <Textarea
          label="Комментарий"
          autosize
          minRows={2}
          value={comment}
          onChange={(event) => setComment(event.currentTarget.value)}
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
          <Button loading={busy} disabled={date === ''} onClick={submit}>
            Завершить
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
