/** Дерево маршрутов и защита сессией через /auth/me. */

import { Navigate, Route, Routes, useLocation } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { Center, Loader } from '@mantine/core'

import { me } from './api/auth'
import { AppShellFrame } from './components/AppShell'
import LoginPage from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { DevicesListPage } from './pages/devices/DevicesListPage'
import { DeviceFormPage } from './pages/devices/DeviceFormPage'
import { DeviceCardPage } from './pages/devices/DeviceCardPage'
import { PeoplePage } from './pages/people/PeoplePage'
import { ReportsPage } from './pages/reports/ReportsPage'
import { ProfilePage } from './pages/profile/ProfilePage'

function ProtectedLayout() {
  const location = useLocation()
  const { isPending, isError, data } = useQuery({
    queryKey: ['me'],
    queryFn: me,
    retry: false,
  })

  if (isPending) {
    return (
      <Center mih="100vh">
        <Loader />
      </Center>
    )
  }
  if (isError || !data) {
    // 401 — тихий редирект; прочие ошибки покажет страница входа своим состоянием
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <AppShellFrame user={data} />
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/devices" element={<DevicesListPage />} />
        <Route path="/devices/new" element={<DeviceFormPage />} />
        <Route path="/devices/:id" element={<DeviceCardPage />} />
        <Route path="/devices/:id/edit" element={<DeviceFormPage />} />
        <Route path="/people" element={<PeoplePage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/me" element={<ProfilePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
