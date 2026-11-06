/** Оболочка: шапка с профилем и выходом + боковая навигация по маршруту. */

import { AppShell as MantineAppShell, AppShellHeader, AppShellNavbar, AppShellSection, Box, Button, Group, NavLink, Text, UnstyledButton } from '@mantine/core'
import { useState } from 'react'
import { Outlet, useLocation, useNavigate, Link } from 'react-router'
import { notifications } from '@mantine/notifications'
import { useQueryClient } from '@tanstack/react-query'

import { ApiError } from '../api/client'
import { logout } from '../api/auth'
import type { UserBrief } from '../api/auth'
import { NotificationsBell } from './NotificationsBell'

const NAV_ITEMS: { label: string; to: string; adminOnly?: boolean }[] = [
  { label: 'Дашборд', to: '/dashboard', adminOnly: true },
  { label: 'Устройства', to: '/devices' },
  { label: 'Люди', to: '/people' },
  { label: 'Отчёты', to: '/reports' },
  { label: 'Мои', to: '/me' },
]

export function AppShellFrame({ user }: { user: UserBrief }) {
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [busy, setBusy] = useState(false)

  const signOut = async () => {
    setBusy(true)
    try {
      await logout()
      queryClient.clear()
      navigate('/login', { replace: true })
    } catch (cause) {
      const message = cause instanceof ApiError ? cause.message : 'Ошибка сети. Повторите попытку'
      notifications.show({ message, color: 'red' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <MantineAppShell header={{ height: 56 }} navbar={{ width: 220, breakpoint: 'sm' }} padding="md">
      <AppShellHeader>
        <Group h="100%" px="md" justify="space-between">
          <Text fw={700}>QA Тестовые устройства</Text>
          <Group gap="sm">
            <NotificationsBell />
            <UnstyledButton component={Link} to="/me">
              <Text size="sm" c="dimmed">
                {user.full_name}
                {user.role === 'admin' ? ' · админ' : ''}
              </Text>
            </UnstyledButton>
            <Button variant="default" size="compact-sm" loading={busy} onClick={signOut}>
              Выйти
            </Button>
          </Group>
        </Group>
      </AppShellHeader>
      <AppShellNavbar>
        <AppShellSection grow>
          {NAV_ITEMS.filter(
            (item) => !item.adminOnly || user.role === 'admin',
          ).map((item) => (
            <NavLink
              key={item.to}
              component={Link}
              to={item.to}
              label={item.label}
              active={isActive(location.pathname, item.to)}
            />
          ))}
        </AppShellSection>
        <AppShellSection p="md">
          <Box>Тестовый учёт устройств</Box>
        </AppShellSection>
      </AppShellNavbar>
      <MantineAppShell.Main>
        <Outlet />
      </MantineAppShell.Main>
    </MantineAppShell>
  )
}

function isActive(pathname: string, to: string): boolean {
  if (pathname === to) return true
  return pathname.startsWith(`${to}/`)
}
