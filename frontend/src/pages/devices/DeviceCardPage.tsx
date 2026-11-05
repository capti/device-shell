/** Карточка устройства: характеристики, владелец/держатель, история, архив. */

import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import {
  Alert,
  Badge,
  Button,
  Center,
  Group,
  Loader,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Timeline,
  Title,
} from '@mantine/core'

import { ApiError } from '../../api/client'
import { fetchDevice, fetchDeviceHistory, archiveDevice, restoreDevice } from '../../api/devices'
import type { DeviceEventRead, DeviceRead, DeviceStatus } from '../../api/devices'
import { fetchConditionReports } from '../../api/maintenance'
import type { ConditionReportRead } from '../../api/maintenance'
import { fetchRepairs } from '../../api/repairs'
import type { RepairRead } from '../../api/repairs'
import { fetchPhotos } from '../../api/photos'
import type { PhotoRead } from '../../api/photos'
import { fetchUsers } from '../../api/users'
import { me } from '../../api/auth'
import { ConditionReports } from '../../components/ConditionReports'
import { PhotoGallery } from '../../components/PhotoGallery'
import { RepairsJournal } from '../../components/RepairsJournal'
import { MarkLostModal, RestoreFromLostModal } from '../../components/StatusDialogs'
import { CheckoutModal, TransferModal } from '../../components/RotationDialogs'
import { deviceState, eventLabel } from '../../lib/device'
import { errorMessage } from '../../lib/errors'
import { formatDate, formatDateTime } from '../../lib/format'

const STATUS_OPTIONS = [
  { value: 'active', label: 'Активен' },
  { value: 'repair', label: 'В ремонте' },
  { value: 'lost', label: 'Утерян' },
]

const FIELD_LABELS: Record<string, string> = {
  inventory_no: 'Инв. №',
  serial_no: 'Serial',
  imei: 'IMEI',
  brand: 'Производитель',
  model: 'Модель',
  os: 'ОС',
  os_version: 'Версия ОС',
  storage: 'Память',
  color: 'Цвет',
  device_type: 'Тип устройства',
  purchase_year: 'Год покупки',
  notes: 'Заметки',
  accounts_note: 'Учётные записи',
}

export function DeviceCardPage() {
  const { id } = useParams()
  const deviceId = Number(id)

  const deviceQuery = useQuery({
    queryKey: ['device', deviceId],
    queryFn: () => fetchDevice(deviceId),
  })
  const historyQuery = useQuery({
    queryKey: ['device-history', deviceId],
    queryFn: () => fetchDeviceHistory(deviceId),
  })
  const photosQuery = useQuery({
    queryKey: ['device-photos', deviceId],
    queryFn: () => fetchPhotos(deviceId),
  })
  const reportsQuery = useQuery({
    queryKey: ['device-reports', deviceId],
    queryFn: () => fetchConditionReports(deviceId),
  })
  const repairsQuery = useQuery({
    queryKey: ['device-repairs', deviceId],
    queryFn: () => fetchRepairs(deviceId),
  })
  const meQuery = useQuery({ queryKey: ['me'], queryFn: me })

  if (deviceQuery.isPending) {
    return (
      <Center mih={300}>
        <Loader />
      </Center>
    )
  }
  if (deviceQuery.isError || !deviceQuery.data) {
    const message =
      deviceQuery.error instanceof ApiError
        ? deviceQuery.error.message
        : 'Ошибка сети. Повторите попытку'
    return (
      <Alert color="red" title="Не удалось загрузить устройство">
        {message}
      </Alert>
    )
  }

  const device = deviceQuery.data
  const currentUser = meQuery.data
  const canManage =
    currentUser !== undefined &&
    (currentUser.role === 'admin' || currentUser.id === device.owner.id)
  const canUpload =
    device.archived_at === null &&
    (canManage || (currentUser !== undefined && currentUser.id === device.holder.id))
  const canDeletePhoto = (photo: PhotoRead) =>
    canManage || (currentUser !== undefined && currentUser.id === photo.uploaded_by.id)
  // Выдача — только владелец/admin и только когда телефон у владельца
  const canCheckout =
    canManage &&
    device.archived_at === null &&
    device.status === 'active' &&
    device.holder.id === device.owner.id
  // Передача — владелец, admin или текущий держатель
  const canTransfer =
    device.archived_at === null &&
    device.holder.id !== device.owner.id &&
    (canManage || (currentUser !== undefined && currentUser.id === device.holder.id))

  return (
    <DeviceCard
      device={device}
      history={historyQuery.data ?? []}
      photos={photosQuery.data ?? []}
      reports={reportsQuery.data ?? []}
      repairs={repairsQuery.data ?? []}
      canManage={canManage}
      canUpload={canUpload}
      canCheckout={canCheckout}
      canTransfer={canTransfer}
      canDeletePhoto={canDeletePhoto}
      onMutated={() => {
        deviceQuery.refetch()
        historyQuery.refetch()
        photosQuery.refetch()
        reportsQuery.refetch()
        repairsQuery.refetch()
      }}
    />
  )
}

function DeviceCard({
  device,
  history,
  photos,
  reports,
  repairs,
  canManage,
  canUpload,
  canCheckout,
  canTransfer,
  canDeletePhoto,
  onMutated,
}: {
  device: DeviceRead
  history: DeviceEventRead[]
  photos: PhotoRead[]
  reports: ConditionReportRead[]
  repairs: RepairRead[]
  canManage: boolean
  canUpload: boolean
  canCheckout: boolean
  canTransfer: boolean
  canDeletePhoto: (photo: PhotoRead) => boolean
  onMutated: () => void
}) {
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [restoreOpen, setRestoreOpen] = useState(false)
  const [checkoutOpen, setCheckoutOpen] = useState(false)
  const [transferOpen, setTransferOpen] = useState(false)
  const [lostOpen, setLostOpen] = useState(false)
  const [foundOpen, setFoundOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  const state = deviceState(device)
  const isArchived = device.archived_at !== null
  const isCheckedOut = device.holder.id !== device.owner.id
  // Переходы только туда, куда их принимает бэк: lost — из active, active — из lost
  const canMarkLost = canManage && !isArchived && device.status === 'active'
  const canRestoreFromLost = canManage && !isArchived && device.status === 'lost'

  const confirmArchive = async () => {
    setBusy(true)
    try {
      await archiveDevice(device.id)
      setArchiveOpen(false)
      onMutated()
    } catch (cause) {
      // 409 ACTIVE_CHECKOUT — показываем сообщение бэка, устройство не меняем
      notifications.show({ message: errorMessage(cause), color: 'red' })
    } finally {
      setBusy(false)
      setArchiveOpen(false)
    }
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <Group gap="sm">
          <Button
            variant="default"
            size="sm"
            component={Link}
            to={`/devices${device.archived_at ? '?archived=true' : ''}`}
          >
            ← К списку
          </Button>
          <Title order={3}>
            {device.inventory_no} · {device.brand} {device.model}
          </Title>
          <Badge color={state.color}>{state.label}</Badge>
          {device.overdue && !isArchived && <Badge color="red">Просрочен</Badge>}
        </Group>
        <Group gap="xs">
          {canCheckout && <Button onClick={() => setCheckoutOpen(true)}>Выдать</Button>}
          {canTransfer && (
            <Button variant="default" onClick={() => setTransferOpen(true)}>
              Передать
            </Button>
          )}
          {canMarkLost && (
            <Button color="red" variant="default" onClick={() => setLostOpen(true)}>
              Потерян
            </Button>
          )}
          {canRestoreFromLost && (
            <Button onClick={() => setFoundOpen(true)}>Найден</Button>
          )}
          {canManage && (
            <>
              {!isArchived && (
                <>
                  <Button
                    variant="default"
                    component={Link}
                    to={`/devices/${device.id}/edit`}
                  >
                    Редактировать
                  </Button>
                  <Button color="red" onClick={() => setArchiveOpen(true)}>
                    В архив
                  </Button>
                </>
              )}
              {isArchived && (
                <Button onClick={() => setRestoreOpen(true)}>Восстановить</Button>
              )}
            </>
          )}
        </Group>
      </Group>

      {isArchived && (
        <Alert color="gray" title="Устройство в архиве">
          Карточка доступна только для просмотра, изменить её нельзя. Дата архивации:{' '}
          {formatDate(device.archived_at)}
        </Alert>
      )}

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Stack gap="xs">
          <Title order={5}>Владелец и держатель</Title>
          <Field label="Владелец" value={device.owner.full_name} />
          <Field
            label="На руках у"
            value={isCheckedOut ? device.holder.full_name : 'Владелец (не выдано)'}
          />
          {isCheckedOut && (
            <Field
              label="Возврат до"
              value={
                device.expected_return_at
                  ? formatDate(device.expected_return_at)
                  : 'Без срока'
              }
            />
          )}
        </Stack>

        <Stack gap="xs">
          <Title order={5}>Характеристики</Title>
          <Field label="Статус" value={statusLabel(device.status)} />
          <Field label="Serial" value={device.serial_no} />
          <Field label="IMEI" value={device.imei} />
          <Field label="ОС" value={join(device.os, device.os_version)} />
          <Field label="Память" value={device.storage} />
          <Field label="Цвет" value={device.color} />
          <Field label="Тип устройства" value={device.device_type} />
          <Field
            label="Год покупки"
            value={device.purchase_year === null ? null : String(device.purchase_year)}
          />
          <Field label="Учётные записи" value={device.accounts_note} />
        </Stack>
      </SimpleGrid>

      {device.notes && (
        <Stack gap={4}>
          <Title order={5}>Заметки</Title>
          <Text size="sm">{device.notes}</Text>
        </Stack>
      )}

      <PhotoGallery
        deviceId={device.id}
        photos={photos}
        canUpload={canUpload}
        canDelete={canDeletePhoto}
        isArchived={isArchived}
        onChanged={onMutated}
      />

      <ConditionReports
        deviceId={device.id}
        reports={reports}
        photosCount={photos.length}
        canReport={canUpload}
        canReturn={canUpload && isCheckedOut}
        isArchived={isArchived}
        onChanged={onMutated}
      />

      <RepairsJournal
        deviceId={device.id}
        repairs={repairs}
        status={device.status}
        canManage={canManage}
        isArchived={isArchived}
        onChanged={onMutated}
      />

      <Stack gap="xs">
        <Title order={5}>История</Title>
        {history.length === 0 ? (
          <Text c="dimmed">Событий пока нет</Text>
        ) : (
          <Timeline active={0} bulletSize={16}>
            {history.map((event) => (
              <Timeline.Item
                key={event.id}
                title={
                  <Group gap="xs">
                    <Text size="sm" fw={600}>
                      {eventLabel(event.type)}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {formatDateTime(event.created_at)}
                      {event.actor ? ` · ${event.actor.full_name}` : ''}
                    </Text>
                  </Group>
                }
              >
                <Changes payload={event.payload} />
              </Timeline.Item>
            ))}
          </Timeline>
        )}
      </Stack>

      <Modal
        opened={archiveOpen}
        onClose={() => setArchiveOpen(false)}
        title="Отправить устройство в архив?"
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            {device.inventory_no} · {device.brand} {device.model} перестанет быть
            доступным для изменений. Вернуть его можно будет из архива.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setArchiveOpen(false)}>
              Отмена
            </Button>
            <Button color="red" loading={busy} onClick={confirmArchive}>
              В архив
            </Button>
          </Group>
        </Stack>
      </Modal>

      <CheckoutModal
        device={device}
        opened={checkoutOpen}
        onClose={() => setCheckoutOpen(false)}
        onDone={() => {
          setCheckoutOpen(false)
          onMutated()
        }}
      />

      <TransferModal
        device={device}
        opened={transferOpen}
        onClose={() => setTransferOpen(false)}
        onDone={() => {
          setTransferOpen(false)
          onMutated()
        }}
      />

      <RestoreModal
        device={device}
        opened={restoreOpen}
        onClose={() => setRestoreOpen(false)}
        onRestored={() => {
          setRestoreOpen(false)
          notifications.show({ message: 'Устройство восстановлено', color: 'green' })
          onMutated()
        }}
      />

      <MarkLostModal
        device={device}
        opened={lostOpen}
        onClose={() => setLostOpen(false)}
        onDone={() => {
          setLostOpen(false)
          onMutated()
        }}
      />

      <RestoreFromLostModal
        device={device}
        opened={foundOpen}
        onClose={() => setFoundOpen(false)}
        onDone={() => {
          setFoundOpen(false)
          onMutated()
        }}
      />
    </Stack>
  )
}

function RestoreModal({
  device,
  opened,
  onClose,
  onRestored,
}: {
  device: DeviceRead
  opened: boolean
  onClose: () => void
  onRestored: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState<string | null>('active')
  const [ownerRequired, setOwnerRequired] = useState(false)
  const [ownerId, setOwnerId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const usersQuery = useQuery({
    queryKey: ['users', 'active'],
    queryFn: () => fetchUsers(),
    enabled: opened,
  })

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      await restoreDevice(device.id, {
        status: (status ?? 'active') as DeviceStatus,
        ...(ownerId === null ? {} : { owner_id: Number(ownerId) }),
      })
      onRestored()
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === 'OWNER_REQUIRED') {
        setOwnerRequired(true)
      }
      setError(errorMessage(cause))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal opened={opened} onClose={onClose} title="Восстановить из архива?" centered>
      <Stack gap="md">
        <Select
          label="Целевой статус"
          data={STATUS_OPTIONS}
          value={status}
          allowDeselect={false}
          onChange={setStatus}
        />
        {ownerRequired && (
          <Select
            label="Новый владелец"
            description="Прежний владелец деактивирован — выберите нового"
            data={(usersQuery.data ?? []).map((user) => ({
              value: String(user.id),
              label: user.full_name,
            }))}
            value={ownerId}
            searchable
            required
            onChange={setOwnerId}
          />
        )}
        {error && (
          <Text size="sm" c="red">
            {error}
          </Text>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Отмена
          </Button>
          <Button
            loading={busy}
            disabled={ownerRequired && ownerId === null}
            onClick={submit}
          >
            Восстановить
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}

function Changes({ payload }: { payload: Record<string, unknown> | null }) {
  if (!payload) return null
  const changes = payload.changes
  if (!changes || typeof changes !== 'object') return null
  const entries = Object.entries(changes as Record<string, { from?: unknown; to?: unknown }>)
  if (entries.length === 0) return null
  return (
    <Stack gap={2}>
      {entries.map(([field, change]) => (
        <Text key={field} size="xs" c="dimmed">
          {FIELD_LABELS[field] ?? field}: {display(change.from)} → {display(change.to)}
        </Text>
      ))}
    </Stack>
  )
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <Group gap="xs" wrap="nowrap">
      <Text size="sm" c="dimmed" w={150}>
        {label}
      </Text>
      <Text size="sm">{value}</Text>
    </Group>
  )
}

function statusLabel(status: DeviceStatus): string {
  return STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status
}

function join(...parts: (string | null | undefined)[]): string | null {
  const filled = parts.filter((part): part is string => Boolean(part))
  return filled.length === 0 ? null : filled.join(' ')
}
