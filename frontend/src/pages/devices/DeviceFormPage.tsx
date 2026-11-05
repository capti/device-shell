/** Создание и редактирование устройства: одна форма для обоих маршрутов. */

import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import {
  Alert,
  Button,
  Center,
  Group,
  Loader,
  NumberInput,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core'

import { ApiError } from '../../api/client'
import { fetchDevice, createDevice, updateDevice } from '../../api/devices'
import type { DevicePayload, DeviceRead } from '../../api/devices'
import { fetchUsers } from '../../api/users'
import type { UserListItem } from '../../api/users'
import { me } from '../../api/auth'
import type { UserBrief } from '../../api/auth'

interface FormValues {
  inventory_no: string
  serial_no: string
  imei: string
  brand: string
  model: string
  os: string
  os_version: string
  storage: string
  color: string
  device_type: string
  purchase_year: string
  notes: string
  accounts_note: string
  owner_id: string
}

function emptyValues(): FormValues {
  return {
    inventory_no: '',
    serial_no: '',
    imei: '',
    brand: '',
    model: '',
    os: '',
    os_version: '',
    storage: '',
    color: '',
    device_type: '',
    purchase_year: '',
    notes: '',
    accounts_note: '',
    owner_id: '',
  }
}

function valuesOf(device: DeviceRead): FormValues {
  const text = (value: string | null) => value ?? ''
  return {
    inventory_no: text(device.inventory_no),
    serial_no: text(device.serial_no),
    imei: text(device.imei),
    brand: device.brand,
    model: device.model,
    os: text(device.os),
    os_version: text(device.os_version),
    storage: text(device.storage),
    color: text(device.color),
    device_type: text(device.device_type),
    purchase_year: device.purchase_year === null ? '' : String(device.purchase_year),
    notes: text(device.notes),
    accounts_note: text(device.accounts_note),
    owner_id: '',
  }
}

/** Пустые строки уходят в бэк как `null`: так можно и очистить поле, и не тронуть его. */
function toPayload(values: FormValues, ownerId?: number): DevicePayload {
  const blank = (value: string) => (value.trim() === '' ? null : value.trim())
  return {
    inventory_no: blank(values.inventory_no),
    serial_no: blank(values.serial_no),
    imei: blank(values.imei),
    brand: values.brand.trim(),
    model: values.model.trim(),
    os: blank(values.os),
    os_version: blank(values.os_version),
    storage: blank(values.storage),
    color: blank(values.color),
    device_type: blank(values.device_type),
    purchase_year: values.purchase_year === '' ? null : Number(values.purchase_year),
    notes: blank(values.notes),
    accounts_note: blank(values.accounts_note),
    ...(ownerId === undefined ? {} : { owner_id: ownerId }),
  }
}

export function DeviceFormPage() {
  const { id } = useParams()
  const deviceId = id === undefined ? undefined : Number(id)
  const isEdit = deviceId !== undefined

  const deviceQuery = useQuery({
    queryKey: ['device', deviceId],
    queryFn: () => fetchDevice(deviceId as number),
    enabled: isEdit,
  })
  const meQuery = useQuery({ queryKey: ['me'], queryFn: me })

  if (!isEdit) {
    return <DeviceForm me={meQuery.data} />
  }
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
  return <DeviceForm me={meQuery.data} device={deviceQuery.data} />
}

function DeviceForm({ me, device }: { me?: UserBrief; device?: DeviceRead }) {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const isEdit = device !== undefined
  const isAdmin = me?.role === 'admin'

  const usersQuery = useQuery({
    queryKey: ['users', 'active'],
    queryFn: () => fetchUsers(),
    enabled: isAdmin,
  })

  const form = useForm<FormValues>({
    initialValues: device ? valuesOf(device) : emptyValues(),
    validate: {
      brand: (value) => (value.trim() === '' ? 'Укажите производителя' : null),
      model: (value) => (value.trim() === '' ? 'Укажите модель' : null),
      purchase_year: (value) => {
        if (value.trim() === '') return null
        const year = Number(value)
        return Number.isInteger(year) && year >= 1980 && year <= 2100
          ? null
          : 'Год покупки — целое число от 1980 до 2100'
      },
    },
  })

  const requiredFilled =
    form.values.brand.trim() !== '' && form.values.model.trim() !== ''

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitting(true)
    try {
      if (device) {
        await updateDevice(device.id, toPayload(values))
        notifications.show({ message: 'Изменения сохранены', color: 'green' })
        navigate(`/devices/${device.id}`)
      } else {
        const ownerId =
          isAdmin && values.owner_id !== '' ? Number(values.owner_id) : undefined
        const created = await createDevice(toPayload(values, ownerId))
        notifications.show({ message: 'Устройство создано', color: 'green' })
        navigate(`/devices/${created.id}`)
      }
    } catch (cause) {
      const message =
        cause instanceof ApiError ? cause.message : 'Ошибка сети. Повторите попытку'
      notifications.show({ message, color: 'red' })
    } finally {
      setSubmitting(false)
    }
  })

  const ownerOptions: { value: string; label: string }[] = (
    usersQuery.data ?? []
  )
    .filter((user: UserListItem) => user.is_active)
    .map((user) => ({ value: String(user.id), label: user.full_name }))

  return (
    <Stack gap="md" maw={720}>
      <Group justify="space-between">
        <Title order={3}>{isEdit ? 'Редактирование устройства' : 'Новое устройство'}</Title>
        <Button
          variant="default"
          component={Link}
          to={isEdit ? `/devices/${device.id}` : '/devices'}
        >
          Отмена
        </Button>
      </Group>

      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          <TextInput
            label="Инвентарный номер"
            description="Оставьте пустым — бэк присвоит следующий QA-PH-NNN"
            withAsterisk={false}
            {...form.getInputProps('inventory_no')}
          />
          <Group grow align="flex-start">
            <TextInput
              label="Производитель"
              withAsterisk
              {...form.getInputProps('brand')}
            />
            <TextInput label="Модель" withAsterisk {...form.getInputProps('model')} />
          </Group>

          {isAdmin && !isEdit && (
            <Select
              label="Владелец"
              description="За кем будет закреплено устройство"
              data={ownerOptions}
              placeholder={ownerOptions.length === 0 ? 'Загрузка…' : 'Текущий пользователь'}
              searchable
              clearable
              {...form.getInputProps('owner_id')}
            />
          )}

          <Group grow align="flex-start">
            <TextInput label="Serial" withAsterisk={false} {...form.getInputProps('serial_no')} />
            <TextInput label="IMEI" withAsterisk={false} {...form.getInputProps('imei')} />
          </Group>
          <Group grow align="flex-start">
            <TextInput label="ОС" withAsterisk={false} {...form.getInputProps('os')} />
            <TextInput
              label="Версия ОС"
              withAsterisk={false}
              {...form.getInputProps('os_version')}
            />
          </Group>
          <Group grow align="flex-start">
            <TextInput label="Память" withAsterisk={false} {...form.getInputProps('storage')} />
            <TextInput label="Цвет" withAsterisk={false} {...form.getInputProps('color')} />
          </Group>
          <Group grow align="flex-start">
            <TextInput
              label="Тип устройства"
              description="Смартфон, планшет, другое"
              withAsterisk={false}
              {...form.getInputProps('device_type')}
            />
            <NumberInput
              label="Год покупки"
              min={1980}
              max={2100}
              allowDecimal={false}
              allowNegative={false}
              withAsterisk={false}
              value={
                form.values.purchase_year === '' ? '' : Number(form.values.purchase_year)
              }
              onChange={(value) =>
                form.setFieldValue('purchase_year', value === '' ? '' : String(value))
              }
              error={form.errors.purchase_year}
            />
          </Group>
          <TextInput
            label="Учётные записи"
            description="Какие аккаунты настроены (Google, Apple). Пароли не сохраняем"
            withAsterisk={false}
            {...form.getInputProps('accounts_note')}
          />
          <Textarea
            label="Заметки"
            minRows={3}
            withAsterisk={false}
            {...form.getInputProps('notes')}
          />

          <Group justify="flex-end" mt="sm">
            <Text size="sm" c="dimmed">
              Обязательные поля отмечены звёздочкой
            </Text>
            <Button type="submit" loading={submitting} disabled={!requiredFilled}>
              Сохранить
            </Button>
          </Group>
        </Stack>
      </form>
    </Stack>
  )
}
