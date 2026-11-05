import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Все запросы API идут под /api (см. src/api/client.ts), прокси снимает
      // префикс перед отправкой на backend.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: false, // cookie сессии нужны на том же origin
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // Фотоустройств backend отдаёт по относительным URL /media/<path>.
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: false,
      },
    },
  },
})
