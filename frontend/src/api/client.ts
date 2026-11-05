/** Единый fetch-клиент API: JSON, cookie-сессия и конверт ошибок `{code, message}`. */

export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.code = code
    this.status = status
  }
}

const NETWORK_ERROR_MESSAGE = 'Ошибка сети. Повторите попытку'

/**
 * Базовый префикс API.
 *
 * В dev все запросы идут под `/api` — этот префикс проксирует Vite на
 * backend (:8000), сняв префикс перед отправкой. В production-сборке
 * SPA и API на одном origin, поэтому префикса нет.
 */
const API_BASE = import.meta.env.DEV ? '/api' : ''

/** Собирает полный путь запроса к API из голого пути роута. */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`
}

/** Роуты, где 401 — штатный ответ (выход, проверка сессии), а не сигнал сессии. */
const SESSION_EXEMPT_PATHS = new Set(['/auth/login', '/auth/me', '/auth/logout'])

let unauthorizedHandler: (() => void) | null = null

/** Провайдер подписывается, чтобы по 401 отправить пользователя на вход. */
export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(apiUrl(path), {
      credentials: 'include',
      ...init,
      headers: { Accept: 'application/json', ...init.headers },
    })
  } catch {
    throw new ApiError('NETWORK', NETWORK_ERROR_MESSAGE, 0)
  }
  if (!response.ok) {
    if (response.status === 401 && !SESSION_EXEMPT_PATHS.has(path)) {
      unauthorizedHandler?.()
    }
    throw await toApiError(response)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

async function toApiError(response: Response): Promise<ApiError> {
  const statusFallback = errorMessages.get(response.status) ?? 'Ошибка сервера'
  try {
    const body = await response.json()
    if (body && typeof body.code === 'string' && typeof body.message === 'string') {
      return new ApiError(body.code, body.message, response.status)
    }
  } catch {
    // не JSON — берём общий текст по статусу ниже
  }
  return new ApiError('ERROR', statusFallback, response.status)
}

const errorMessages = new Map<number, string>([
  [0, NETWORK_ERROR_MESSAGE],
  [401, 'Требуется вход в систему'],
  [403, 'Недостаточно прав'],
  [404, 'Запрос не найден'],
  [409, 'Конфликт данных'],
  [422, 'Некорректные данные запроса'],
  [500, 'Внутренняя ошибка сервера'],
])

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: 'POST',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export function apiGet<T>(path: string): Promise<T> {
  return apiFetch<T>(path)
}
