/** Диалоги оборота: выдача телефона сотруднику и передача с рук на руки. */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import {
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core'

import type { DeviceRead } from '../api/devices'
import { checkoutDevice, transferDevice } from '../api/rotation'
import { fetchUsers } from '../api/users'
import { CONDITION_OPTIONS } from '../lib/condition'
import type { ConditionValue } from '../lib/condition'
import { errorMessage } from '../lib/errors'
import { toIsoDateTime, todayInput } from '../lib/format'

type Mode = 'checkout' | 'transfer'

const TEXTS: Record<Mode, { title: string; submit: string; holder: string; success: string }> = {
  checkout: {
    title: 'Выдать устройство',
    submit: 'Выдать',
    holder: 'Кому выдать',
    success: 'Устройство выдано',
  },
  transfer: {
    title: 'Передать устройство',
    submit: 'Передать',
    holder: 'Новый держатель',
    success: 'Устройство передано',
  },
}

export function CheckoutModal({
  device,
  opened,
  onClose,
  onDone,
}: {
  device: DeviceRead
  opened: boolean
  onClose: () => void
  onDone: () => void
}) {
  return (
    <RotationModal
      mode="checkout"
      device={device}
      opened={opened}
      onClose={onClose}
      onDone={onDone}
    />
  )
}

export function TransferModal({
  device,
  opened,
  onClose,
  onDone,
}: {
  device: DeviceRead
  opened: boolean
  onClose: () => void
  onDone: () => void
}) {
  return (
    <RotationModal
      mode="transfer"
      device={device}
      opened={opened}
      onClose={onClose}
      onDone={onDone}
    />
  )
}

function RotationModal({
  mode,
  device,
  opened,
  onClose,
  onDone,
}: {
  mode: Mode
  device: DeviceRead
  opened: boolean
  onClose: () => void
  onDone: () => void
}) {
  const texts = TEXTS[mode]
  const [busy, setBusy] = useState(false)
  const [holderId, setHolderId] = useState<string | null>(null)
  const [dueDate, setDueDate] = useState('')
  const [condition, setCondition] = useState<ConditionValue | null>(null)
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)

  const usersQuery = useQuery({
    queryKey: ['users', 'active'],
    queryFn: () => fetchUsers(),
    enabled: opened,
  })

  // Владельца выдать нельзя (бэк вернёт SELF_CHECKOUT), текущего держателя — тоже
  const excluded = [device.owner.id]
  if (mode === 'transfer') excluded.push(device.holder.id)
  const candidates = (usersQuery.data ?? [])
    .filter((user) => user.is_active && !excluded.includes(user.id))
    .map((user) => ({ value: String(user.id), label: user.full_name }))

  const reset = () => {
    setHolderId(null)
    setDueDate('')
    setCondition(null)
    setComment('')
    setError(null)
  }

  const close = () => {
    reset()
    onClose()
  }

  const submit = async () => {
    if (holderId === null) return
    setBusy(true)
    setError(null)
    const trimmed = comment.trim()
    const schedule = dueDate === '' ? {} : { expected_return_at: toIsoDateTime(dueDate) }
    const note = trimmed === '' ? {} : { comment: trimmed }
    try {
      if (mode === 'checkout') {
        await checkoutDevice(device.id, {
          holder_id: Number(holderId),
          ...schedule,
          ...(condition === null ? {} : { condition_out: condition }),
          ...(note.comment === undefined ? {} : { comment_out: note.comment }),
        })
      } else {
        await transferDevice(device.id, {
          holder_id: Number(holderId),
          ...schedule,
          ...(condition === null ? {} : { condition_in: condition }),
          ...note,
        })
      }
      notifications.show({ message: texts.success, color: 'green' })
      reset()
      onDone()
    } catch (cause) {
      // 409 ALREADY_CHECKED_OUT / SELF_CHECKOUT / 422 — текст бэка остаётся в диалоге
      setError(errorMessage(cause))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal opened={opened} onClose={close} title={texts.title} centered>
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          {device.inventory_no} · {device.brand} {device.model}
        </Text>
        <Select
          label={texts.holder}
          data={candidates}
          value={holderId}
          searchable
          required
          disabled={usersQuery.isLoading}
          placeholder={usersQuery.isLoading ? 'Загрузка…' : 'Выберите сотрудника'}
          onChange={setHolderId}
        />
        <TextInput
          type="date"
          label="Вернуть до"
          description="Пусто — 14 дней по умолчанию"
          min={todayInput()}
          value={dueDate}
          onChange={(event) => setDueDate(event.currentTarget.value)}
        />
        <Select
          label={mode === 'checkout' ? 'Состояние при выдаче' : 'Состояние при передаче'}
          data={CONDITION_OPTIONS}
          value={condition}
          clearable
          onChange={(value) => setCondition((value as ConditionValue | null) ?? null)}
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
          <Button variant="default" onClick={close}>
            Отмена
          </Button>
          <Button loading={busy} disabled={holderId === null} onClick={submit}>
            {texts.submit}
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
