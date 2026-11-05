/** Текст ошибки для пользователя: сообщение конверта бэка или текст сети. */

import { ApiError } from '../api/client'

const NETWORK_ERROR_MESSAGE = 'Ошибка сети. Повторите попытку'

export function errorMessage(cause: unknown): string {
  return cause instanceof ApiError ? cause.message : NETWORK_ERROR_MESSAGE
}
