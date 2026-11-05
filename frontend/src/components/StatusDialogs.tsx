/** Диалоги статуса: отметка устройства утерянным и возврат из утери. */

import { useState } from 'react'
import { Button, Group, Modal, Stack, Text, Textarea } from '@mantine/core'
import { notifications } from '@mantine/notifications'

import { ApiError } from '../api/client'
import type { DeviceRead } from '../api/devices'
import { changeStatus } from '../api/rotation'
import { errorMessage } from '../lib/errors'

type Mode = 'lost' | 'found'

const TEXTS: Record<
  Mode,
  { title: string; submit: string; success: string; commentLabel: string; commentDescription?: string; required?: boolean }
> = {
  lost: {
    title: 'Отметить устройство утерянным?',
    submit: 'Пометить утерянным',
    success: 'Устройство помечено утерянным',
    commentLabel: 'Обстоятельства',
    commentDescription: 'Необязательно: где и при каких обстоятельствах потерялось',
  },
  found: {
    title: 'Вернуть устройство в работу',
    submit: 'Найден',
    success: 'Устройство снова активно',
    commentLabel: 'Где нашлось',
    commentDescription: 'Обязательно: где и при каких обстоятельствах нашлось',
    required: true,
  },
}

/** Окно отметки об утере: доступно на `active`, отправляет `status: lost`. */
export function MarkLostModal({
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
    <StatusModal
      mode="lost"
      device={device}
      opened={opened}
      onClose={onClose}
      onDone={onDone}
    />
  )
}

/** Окно возврата из утери: доступно на `lost`, требует комментарий. */
export function RestoreFromLostModal({
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
    <StatusModal
      mode="found"
      device={device}
      opened={opened}
      onClose={onClose}
      onDone={onDone}
    />
  )
}

function StatusModal({
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
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const trimmed = comment.trim()
  const commentMissing = texts.required === true && trimmed === ''

  const close = () => {
    setComment('')
    setError(null)
    onClose()
  }

  const submit = async () => {
    if (commentMissing) return
    setBusy(true)
    setError(null)
    try {
      await changeStatus(device.id, {
        status: mode === 'lost' ? 'lost' : 'active',
        ...(trimmed === '' ? {} : { comment: trimmed }),
      })
      notifications.show({ message: texts.success, color: 'green' })
      close()
      onDone()
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 422) {
        // COMMENT_REQUIRED — текст бэка остаётся под полем, ввод сохраняется
        setError(errorMessage(cause))
      } else {
        // INVALID_STATUS_TRANSITION / DEVICE_ARCHIVED: состояние могло
        // устареть, форма без изменений не нужна
        notifications.show({ message: errorMessage(cause), color: 'red' })
        close()
        onDone()
      }
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
        <Textarea
          label={texts.commentLabel}
          description={texts.commentDescription}
          placeholder={mode === 'found' ? 'Например: нашли в переговорной' : undefined}
          required={texts.required === true}
          autosize
          minRows={3}
          value={comment}
          error={error}
          onChange={(event) => {
            setComment(event.currentTarget.value)
            setError(null)
          }}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={close}>
            Отмена
          </Button>
          <Button loading={busy} disabled={commentMissing} onClick={submit}>
            {texts.submit}
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
