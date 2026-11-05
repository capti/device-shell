/** Раздел «Состояние»: отчёты о состоянии и возврат телефона с фото. */

import { useState } from 'react'
import {
  Badge,
  Button,
  Group,
  Image,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  Textarea,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'

import {
  createConditionReport,
  fetchConditionReports,
} from '../api/maintenance'
import type { ConditionReportRead } from '../api/maintenance'
import { uploadPhotos } from '../api/photos'
import { returnDevice } from '../api/rotation'
import { CONDITION_OPTIONS, conditionColor, conditionLabel } from '../lib/condition'
import type { ConditionValue } from '../lib/condition'
import { errorMessage } from '../lib/errors'
import { formatDateTime } from '../lib/format'
import { PHOTO_LIMIT } from './PhotoGallery'
import { PhotoPicker } from './PhotoPicker'

interface ConditionReportsProps {
  deviceId: number
  reports: ConditionReportRead[]
  photosCount: number
  canReport: boolean
  canReturn: boolean
  isArchived: boolean
  onChanged: () => void
}

export function ConditionReports({
  deviceId,
  reports,
  photosCount,
  canReport,
  canReturn,
  isArchived,
  onChanged,
}: ConditionReportsProps) {
  const [reportOpen, setReportOpen] = useState(false)
  const [returnOpen, setReturnOpen] = useState(false)
  const freeSlots = Math.max(PHOTO_LIMIT - photosCount, 0)

  return (
    <Stack gap="xs">
      <Group justify="space-between" align="center">
        <Text fw={500}>Состояние</Text>
        {canReport && !isArchived && (
          <Group gap="xs">
            <Button size="xs" variant="default" onClick={() => setReportOpen(true)}>
              Добавить отчёт
            </Button>
            {canReturn && (
              <Button size="xs" onClick={() => setReturnOpen(true)}>
                Вернуть
              </Button>
            )}
          </Group>
        )}
      </Group>

      {reports.length === 0 ? (
        <Text size="sm" c="dimmed">
          Отчётов пока нет
        </Text>
      ) : (
        <Stack gap="sm">
          {reports.map((report) => (
            <ReportRow key={report.id} report={report} />
          ))}
        </Stack>
      )}

      <ReportModal
        deviceId={deviceId}
        opened={reportOpen}
        maxFiles={freeSlots}
        onClose={() => setReportOpen(false)}
        onSaved={onChanged}
      />
      <ReturnModal
        deviceId={deviceId}
        opened={returnOpen}
        maxFiles={freeSlots}
        onClose={() => setReturnOpen(false)}
        onReturned={onChanged}
      />
    </Stack>
  )
}

function ReportRow({ report }: { report: ConditionReportRead }) {
  return (
    <Stack gap={4}>
      <Group gap="xs">
        <Badge color={conditionColor(report.condition)}>
          {conditionLabel(report.condition)}
        </Badge>
        {report.requires_repair && (
          <Badge color="orange" variant="light">
            Требует ремонта
          </Badge>
        )}
        {report.checkout_id !== null && (
          <Badge color="gray" variant="light">
            При возврате
          </Badge>
        )}
        <Text size="xs" c="dimmed">
          {formatDateTime(report.created_at)} · {report.author.full_name}
        </Text>
      </Group>
      {report.comment && <Text size="sm">{report.comment}</Text>}
      {report.photos.length > 0 && (
        <SimpleGrid cols={{ base: 3, sm: 5 }} spacing={4}>
          {report.photos.map((photo) => (
            <Image
              key={photo.id}
              src={photo.thumb_url}
              alt="Фотография состояния"
              radius="sm"
              h={80}
              fit="cover"
            />
          ))}
        </SimpleGrid>
      )}
    </Stack>
  )
}

interface ConditionFieldsProps {
  condition: string | null
  onCondition: (value: string | null) => void
  requiresRepair: boolean
  onRequiresRepair: (value: boolean) => void
  comment: string
  onComment: (value: string) => void
  files: File[]
  onFiles: (files: File[]) => void
  maxFiles: number
  commentLabel: string
}

/** Общие поля обоих окон: состояние, флаг ремонта, комментарий и фото. */
function ConditionFields({
  condition,
  onCondition,
  requiresRepair,
  onRequiresRepair,
  comment,
  onComment,
  files,
  onFiles,
  maxFiles,
  commentLabel,
}: ConditionFieldsProps) {
  return (
    <Stack gap="md">
      <Select
        label="Состояние"
        placeholder="Выберите состояние"
        data={CONDITION_OPTIONS}
        value={condition}
        allowDeselect={false}
        required
        onChange={onCondition}
      />
      <Switch
        label="Требует ремонта"
        checked={requiresRepair}
        onChange={(event) => onRequiresRepair(event.currentTarget.checked)}
      />
      <Textarea
        label={commentLabel}
        value={comment}
        autosize
        minRows={2}
        onChange={(event) => onComment(event.currentTarget.value)}
      />
      <PhotoPicker files={files} maxFiles={maxFiles} onChange={onFiles} />
    </Stack>
  )
}

function ModalActions({
  busy,
  disabled,
  confirmLabel,
  onClose,
  onConfirm,
}: {
  busy: boolean
  disabled: boolean
  confirmLabel: string
  onClose: () => void
  onConfirm: () => void
}) {
  return (
    <Group justify="flex-end">
      <Button variant="default" onClick={onClose}>
        Отмена
      </Button>
      <Button loading={busy} disabled={disabled} onClick={onConfirm}>
        {confirmLabel}
      </Button>
    </Group>
  )
}

function ReportModal({
  deviceId,
  opened,
  maxFiles,
  onClose,
  onSaved,
}: {
  deviceId: number
  opened: boolean
  maxFiles: number
  onClose: () => void
  onSaved: () => void
}) {
  const [condition, setCondition] = useState<string | null>(null)
  const [requiresRepair, setRequiresRepair] = useState(false)
  const [comment, setComment] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const close = () => {
    setCondition(null)
    setRequiresRepair(false)
    setComment('')
    setFiles([])
    setError(null)
    onClose()
  }

  const submit = async () => {
    if (!condition) return
    setBusy(true)
    setError(null)
    try {
      const report = await createConditionReport(deviceId, {
        condition: condition as ConditionValue,
        requires_repair: requiresRepair,
        ...(comment.trim() === '' ? {} : { comment: comment.trim() }),
      })
      if (files.length > 0) {
        try {
          await uploadPhotos(deviceId, files, report.id)
        } catch (cause) {
          notifications.show({
            message: `Отчёт сохранён, фото не загрузились: ${errorMessage(cause)}`,
            color: 'orange',
          })
        }
      }
      notifications.show({ message: 'Отчёт о состоянии сохранён', color: 'green' })
      close()
      onSaved()
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal opened={opened} onClose={close} title="Добавить отчёт о состоянии" centered>
      <Stack gap="md">
        <ConditionFields
          condition={condition}
          onCondition={setCondition}
          requiresRepair={requiresRepair}
          onRequiresRepair={setRequiresRepair}
          comment={comment}
          onComment={setComment}
          files={files}
          onFiles={setFiles}
          maxFiles={maxFiles}
          commentLabel="Комментарий"
        />
        {error && (
          <Text size="sm" c="red">
            {error}
          </Text>
        )}
        <ModalActions
          busy={busy}
          disabled={condition === null}
          confirmLabel="Сохранить отчёт"
          onClose={close}
          onConfirm={submit}
        />
      </Stack>
    </Modal>
  )
}

function ReturnModal({
  deviceId,
  opened,
  maxFiles,
  onClose,
  onReturned,
}: {
  deviceId: number
  opened: boolean
  maxFiles: number
  onClose: () => void
  onReturned: () => void
}) {
  const [condition, setCondition] = useState<string | null>(null)
  const [requiresRepair, setRequiresRepair] = useState(false)
  const [comment, setComment] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const close = () => {
    setCondition(null)
    setRequiresRepair(false)
    setComment('')
    setFiles([])
    setError(null)
    onClose()
  }

  const submit = async () => {
    if (!condition) return
    setBusy(true)
    setError(null)
    try {
      await returnDevice(deviceId, {
        condition_in: condition as ConditionValue,
        requires_repair: requiresRepair,
        ...(comment.trim() === '' ? {} : { comment_in: comment.trim() }),
      })
      if (files.length > 0) {
        // Возврат создаёт отчёт; его id в ответе нет, берём самый свежий.
        const reports = await fetchConditionReports(deviceId)
        const report = reports[0]
        if (report) {
          try {
            await uploadPhotos(deviceId, files, report.id)
          } catch (cause) {
            notifications.show({
              message: `Возврат принят, фото не загрузились: ${errorMessage(cause)}`,
              color: 'orange',
            })
          }
        }
      }
      notifications.show({ message: 'Устройство возвращено', color: 'green' })
      close()
      onReturned()
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal opened={opened} onClose={close} title="Вернуть устройство" centered>
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Укажите состояние телефона: отчёт сохранится в истории и уйдёт владельцу.
        </Text>
        <ConditionFields
          condition={condition}
          onCondition={setCondition}
          requiresRepair={requiresRepair}
          onRequiresRepair={setRequiresRepair}
          comment={comment}
          onComment={setComment}
          files={files}
          onFiles={setFiles}
          maxFiles={maxFiles}
          commentLabel="Комментарий при возврате"
        />
        {error && (
          <Text size="sm" c="red">
            {error}
          </Text>
        )}
        <ModalActions
          busy={busy}
          disabled={condition === null}
          confirmLabel="Вернуть"
          onClose={close}
          onConfirm={submit}
        />
      </Stack>
    </Modal>
  )
}
