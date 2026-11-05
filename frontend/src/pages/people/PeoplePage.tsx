/** Справочник сотрудников: счётчики устройств, роли, деактивация и пароли. */

import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
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
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'

import { ApiError } from '../../api/client'
import { me } from '../../api/auth'
import {
  activateUser,
  createUser,
  deactivateUser,
  fetchUsers,
  resetUserPassword,
  updateUser,
} from '../../api/users'
import type { Role, UserListItem } from '../../api/users'
import { errorMessage } from '../../lib/errors'
import { formatDate } from '../../lib/format'

const MIN_PASSWORD_LENGTH = 8

const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: 'user', label: 'Пользователь' },
  { value: 'admin', label: 'Администратор' },
]

export function PeoplePage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<UserListItem | null>(null)
  const [passwordFor, setPasswordFor] = useState<UserListItem | null>(null)
  const [deactivating, setDeactivating] = useState<UserListItem | null>(null)
  const [deactivateError, setDeactivateError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const meQuery = useQuery({ queryKey: ['me'], queryFn: me })
  const isAdmin = meQuery.data?.role === 'admin'

  const usersQuery = useQuery({
    queryKey: ['users', showInactive ? 'all' : 'active'],
    queryFn: () => fetchUsers(showInactive),
  })

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['users'] })

  const users = useMemo(() => {
    const term = search.trim().toLowerCase()
    const rows = usersQuery.data ?? []
    if (term === '') return rows
    return rows.filter((user) =>
      [user.full_name, user.username, user.team, user.email].some((value) =>
        value?.toLowerCase().includes(term),
      ),
    )
  }, [search, usersQuery.data])

  const closeCard = () => {
    setCreating(false)
    setEditing(null)
  }

  const confirmDeactivate = async () => {
    if (deactivating === null) return
    setBusy(true)
    setDeactivateError(null)
    try {
      await deactivateUser(deactivating.id)
      notifications.show({ message: 'Сотрудник деактивирован', color: 'green' })
      setDeactivating(null)
      refresh()
      // деактивация архивирует устройства — список устройств тоже устарел
      queryClient.invalidateQueries({ queryKey: ['devices'] })
    } catch (cause) {
      // 409 HAS_DEVICES перечисляет инвентарные номера — читаем прямо в диалоге
      setDeactivateError(errorMessage(cause))
    } finally {
      setBusy(false)
    }
  }

  const restore = async (user: UserListItem) => {
    try {
      await activateUser(user.id)
      notifications.show({ message: 'Доступ восстановлен', color: 'green' })
      refresh()
    } catch (cause) {
      notifications.show({ message: errorMessage(cause), color: 'red' })
    }
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Сотрудники</Title>
        {isAdmin && <Button onClick={() => setCreating(true)}>Добавить сотрудника</Button>}
      </Group>

      <Group align="flex-end" justify="space-between">
        <TextInput
          label="Поиск"
          placeholder="ФИО, логин, команда, email"
          w={320}
          value={search}
          onChange={(event) => setSearch(event.currentTarget.value)}
        />
        {isAdmin && (
          <Switch
            label="Показывать деактивированных"
            checked={showInactive}
            onChange={(event) => setShowInactive(event.currentTarget.checked)}
          />
        )}
      </Group>

      {usersQuery.isPending && (
        <Center mih={200}>
          <Loader />
        </Center>
      )}

      {usersQuery.isError && (
        <Alert color="red" title="Не удалось загрузить список">
          {usersQuery.error instanceof ApiError
            ? usersQuery.error.message
            : 'Ошибка сети. Повторите попытку'}
        </Alert>
      )}

      {usersQuery.data && users.length === 0 && (
        <Text c="dimmed">
          {search.trim() === '' ? 'Сотрудников пока нет' : 'Ничего не найдено'}
        </Text>
      )}

      {users.length > 0 && (
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Сотрудник</Table.Th>
              <Table.Th>Команда</Table.Th>
              <Table.Th>Контакты</Table.Th>
              <Table.Th>Роль</Table.Th>
              <Table.Th>Владеет</Table.Th>
              <Table.Th>На руках</Table.Th>
              <Table.Th>Последний вход</Table.Th>
              <Table.Th>Статус</Table.Th>
              {isAdmin && <Table.Th>Действия</Table.Th>}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {users.map((user) => (
              <Table.Tr key={user.id}>
                <Table.Td>
                  <Stack gap={0}>
                    <Text size="sm" fw={500}>
                      {user.full_name}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {user.username}
                    </Text>
                  </Stack>
                </Table.Td>
                <Table.Td>{user.team ?? '—'}</Table.Td>
                <Table.Td>
                  <Stack gap={0}>
                    <Text size="sm">{user.email ?? '—'}</Text>
                    {user.telegram && (
                      <Text size="xs" c="dimmed">
                        {user.telegram}
                      </Text>
                    )}
                  </Stack>
                </Table.Td>
                <Table.Td>
                  <Badge variant="light" color={user.role === 'admin' ? 'grape' : 'blue'}>
                    {roleLabel(user.role)}
                  </Badge>
                </Table.Td>
                <Table.Td>{user.devices_owned}</Table.Td>
                <Table.Td>{user.devices_held}</Table.Td>
                <Table.Td>{user.last_login_at ? formatDate(user.last_login_at) : '—'}</Table.Td>
                <Table.Td>
                  <Badge color={user.is_active ? 'teal' : 'gray'}>
                    {user.is_active ? 'Активен' : 'Деактивирован'}
                  </Badge>
                </Table.Td>
                {isAdmin && (
                  <Table.Td>
                    <Group gap="xs" wrap="nowrap">
                      <Button
                        size="compact-xs"
                        variant="default"
                        onClick={() => setEditing(user)}
                      >
                        Изменить
                      </Button>
                      <Button
                        size="compact-xs"
                        variant="default"
                        onClick={() => setPasswordFor(user)}
                      >
                        Пароль
                      </Button>
                      {user.is_active ? (
                        <Button
                          size="compact-xs"
                          variant="light"
                          color="red"
                          onClick={() => {
                            setDeactivateError(null)
                            setDeactivating(user)
                          }}
                        >
                          Деактивировать
                        </Button>
                      ) : (
                        <Button size="compact-xs" onClick={() => restore(user)}>
                          Восстановить
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                )}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {(creating || editing !== null) && (
        <UserFormModal
          key={editing?.id ?? 'new'}
          user={editing}
          onClose={closeCard}
          onSaved={() => {
            closeCard()
            refresh()
          }}
        />
      )}

      {passwordFor && (
        <PasswordModal
          key={`password-${passwordFor.id}`}
          user={passwordFor}
          onClose={() => setPasswordFor(null)}
          onSaved={() => setPasswordFor(null)}
        />
      )}

      <Modal
        opened={deactivating !== null}
        onClose={() => {
          setDeactivating(null)
          setDeactivateError(null)
        }}
        title="Деактивировать сотрудника?"
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            {deactivating?.full_name} потеряет доступ к системе, а его устройства
            ({deactivating?.devices_owned ?? 0}) уйдут в архив. Восстановить их можно
            будет только с новым владельцем.
          </Text>
          {deactivateError && (
            <Text size="sm" c="red">
              {deactivateError}
            </Text>
          )}
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setDeactivating(null)
                setDeactivateError(null)
              }}
            >
              Отмена
            </Button>
            <Button color="red" loading={busy} onClick={confirmDeactivate}>
              Деактивировать
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}

function roleLabel(role: Role): string {
  return role === 'admin' ? 'Администратор' : 'Пользователь'
}

function UserFormModal({
  user,
  onClose,
  onSaved,
}: {
  user: UserListItem | null
  onClose: () => void
  onSaved: () => void
}) {
  const isEdit = user !== null
  const [username, setUsername] = useState(user?.username ?? '')
  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Role>(user?.role ?? 'user')
  const [email, setEmail] = useState(user?.email ?? '')
  const [team, setTeam] = useState(user?.team ?? '')
  const [telegram, setTelegram] = useState(user?.telegram ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const passwordTooShort = password.length > 0 && password.length < MIN_PASSWORD_LENGTH
  const canSubmit =
    fullName.trim() !== '' &&
    (isEdit || (username.trim() !== '' && password.length >= MIN_PASSWORD_LENGTH))

  const contact = (value: string) => (value.trim() === '' ? null : value.trim())

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      if (isEdit) {
        await updateUser(user.id, {
          full_name: fullName.trim(),
          role,
          email: contact(email),
          team: contact(team),
          telegram: contact(telegram),
        })
        notifications.show({ message: 'Карточка обновлена', color: 'green' })
      } else {
        await createUser({
          username: username.trim(),
          full_name: fullName.trim(),
          password,
          role,
          email: contact(email),
          team: contact(team),
          telegram: contact(telegram),
        })
        notifications.show({ message: 'Сотрудник добавлен', color: 'green' })
      }
      onSaved()
    } catch (cause) {
      // 409 USERNAME_TAKEN / 409 LAST_ADMIN — текст бэка в диалоге, ввод сохраняется
      setError(errorMessage(cause))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      opened
      onClose={onClose}
      title={isEdit ? 'Карточка сотрудника' : 'Новый сотрудник'}
      centered
    >
      <Stack gap="md">
        <TextInput
          label="Логин"
          description={isEdit ? 'Логин после создания не меняется' : 'Используется для входа'}
          value={username}
          required={!isEdit}
          disabled={isEdit}
          onChange={(event) => setUsername(event.currentTarget.value)}
        />
        <TextInput
          label="ФИО"
          value={fullName}
          required
          onChange={(event) => setFullName(event.currentTarget.value)}
        />
        {!isEdit && (
          <TextInput
            label="Пароль"
            type="password"
            description={`Минимум ${MIN_PASSWORD_LENGTH} символов`}
            value={password}
            required
            error={passwordTooShort ? `Минимум ${MIN_PASSWORD_LENGTH} символов` : null}
            onChange={(event) => setPassword(event.currentTarget.value)}
          />
        )}
        <Select
          label="Роль"
          data={ROLE_OPTIONS}
          value={role}
          allowDeselect={false}
          onChange={(value) => setRole((value as Role | null) ?? 'user')}
        />
        <TextInput
          label="Email"
          value={email}
          onChange={(event) => setEmail(event.currentTarget.value)}
        />
        <TextInput
          label="Команда"
          value={team}
          onChange={(event) => setTeam(event.currentTarget.value)}
        />
        <TextInput
          label="Telegram"
          value={telegram}
          onChange={(event) => setTelegram(event.currentTarget.value)}
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
            {isEdit ? 'Сохранить' : 'Создать'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}

function PasswordModal({
  user,
  onClose,
  onSaved,
}: {
  user: UserListItem
  onClose: () => void
  onSaved: () => void
}) {
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const tooShort = password.length > 0 && password.length < MIN_PASSWORD_LENGTH

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      await resetUserPassword(user.id, password)
      notifications.show({ message: 'Пароль обновлён', color: 'green' })
      onSaved()
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal opened onClose={onClose} title={`Новый пароль: ${user.full_name}`} centered>
      <Stack gap="md">
        <TextInput
          label="Новый пароль"
          type="password"
          description={`Минимум ${MIN_PASSWORD_LENGTH} символов`}
          value={password}
          error={tooShort ? `Минимум ${MIN_PASSWORD_LENGTH} символов` : null}
          onChange={(event) => setPassword(event.currentTarget.value)}
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
          <Button
            loading={busy}
            disabled={password.length < MIN_PASSWORD_LENGTH}
            onClick={submit}
          >
            Сохранить
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
