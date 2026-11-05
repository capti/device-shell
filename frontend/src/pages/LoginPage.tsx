/** Страница входа: username + пароль, ошибки — русскими сообщениями бэка. */

import { useForm } from '@mantine/form'
import { Button, Center, Paper, PasswordInput, Stack, Text, TextInput, Title } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useState } from 'react'
import { useLocation } from 'react-router'

import { ApiError } from '../api/client'
import { login } from '../api/auth'

export default function LoginPage() {
  const location = useLocation()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const form = useForm({
    mode: 'uncontrolled',
    initialValues: { username: '', password: '' },
    validate: {
      username: (value: string) => (value.trim() ? null : 'Введите имя пользователя'),
      password: (value: string) => (value ? null : 'Введите пароль'),
    },
  })

  const requestedPath = (location.state as { from?: unknown } | null)?.from
  const back =
    typeof requestedPath === 'string' &&
    requestedPath.startsWith('/') &&
    !requestedPath.startsWith('//') &&
    !requestedPath.startsWith('/\\')
      ? requestedPath
      : '/dashboard'

  const submit = async (values: { username: string; password: string }) => {
    setBusy(true)
    setError(null)
    try {
      await login(values.username.trim(), values.password)
      window.location.replace(back)
    } catch (cause) {
      const message =
        cause instanceof ApiError ? cause.message : 'Ошибка сети. Повторите попытку'
      setError(message)
      notifications.show({ message, color: 'red' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Center mih="100vh">
      <Paper w={360} p="xl" radius="md" withBorder>
        <Stack>
          <Title order={2} ta="center">
            Вход
          </Title>
          <Text c="dimmed" ta="center">
            Внутренний учёт тестовых устройств
          </Text>
          <form onSubmit={form.onSubmit(submit)}>
            <Stack>
              <TextInput
                label="Имя пользователя"
                placeholder="username"
                key={form.key('username')}
                {...form.getInputProps('username')}
                data-autofocus
              />
              <PasswordInput
                label="Пароль"
                key={form.key('password')}
                {...form.getInputProps('password')}
              />
              {error && (
                <Text c="red" size="sm">
                  {error}
                </Text>
              )}
              <Button type="submit" loading={busy}>
                Войти
              </Button>
            </Stack>
          </form>
        </Stack>
      </Paper>
    </Center>
  )
}

export const defaultNavTarget = '/dashboard'
