import { MantineProvider } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router'
import { createRoot } from 'react-dom/client'

import '@mantine/core/styles.css'
import '@mantine/charts/styles.css'
import '@mantine/notifications/styles.css'

import App from './App'
import { setUnauthorizedHandler } from './api/client'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 15_000,
      refetchOnWindowFocus: false,
    },
  },
})

// 401 вне страниц входа — переводим на /login целиком, как требует спека.
setUnauthorizedHandler(() => {
  queryClient.clear()
  window.location.assign('/login')
})

createRoot(document.getElementById('root')!).render(
  <MantineProvider defaultColorScheme="dark">
    <Notifications />
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </MantineProvider>,
)
