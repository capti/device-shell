# Design

## Контекст

Существующая обвязка:

- `vite.config.ts`: `server.proxy['/api'] → http://localhost:8000` с
  `rewrite`, снимающим `/api`, и `changeOrigin: false` (cookie нужны на том же
  origin).
- `src/api/client.ts`: единая точка всех запросов (`apiFetch`), голые пути.
- `src/api/reports.ts`: `exportUrl()` возвращает голый путь — ссылка
  скачивания Excel, используется как `href`, мимо `apiFetch`.
- Backend отдаёт фото по относительным URL `/media/<path>` (`photo_url` в
  `services/photos.py`).

## Решение

**Префикс `/api` добавляется на стороне клиента, только в dev-сборке.**

1. `client.ts` объявляет `API_BASE = import.meta.env.DEV ? '/api' : ''` и
   хелпер `apiUrl(path)`. `apiFetch` и `exportUrl` строят URL через него.
   Модули `src/api/*` не меняются — префикс решается в одном месте.

2. В production-сборке `API_BASE = ''`: контракт API остаётся голыми путями,
   как в спеках (`frontend-shell`: «POST /auth/login») и в `openapi.json`.
   Backend роуты под `/api` не монтируются — это зафиксировано как
   «не входит», см. proposal.

3. `vite.config.ts` получает вторую запись прокси: `'/media' → :8000` без
   rewrite. Без неё фотографии в галерее карточки устройства в dev отдают 404.

## Почему не другие варианты

- **Монтировать backend под `/api`** — меняет контракт API и `openapi.json`,
  дублирует маршруты, разрывает прямые проверки `Invoke-RestMethod :8000`,
  которыми пользовались все прошлые изменения.
- **Проксировать каждый голый путь** (`/auth`, `/devices`, `/notifications`, …)
  — список будет расходиться с роутами backend при каждом новом префиксе;
  ложные срабатывания на статические файлы с такими именами.
- **Абсолютный base URL с хостом** — ломает `changeOrigin: false`-контракт
  с cookie и привязывает код к адресу.

## Точка отказа / проверка

`import.meta.env.DEV` — типизирован через `types: ["vite/client"]` в
`tsconfig.app.json`. Проверка: `npm run build` (tsc) и ручной проход через
прокси `:5173`.
