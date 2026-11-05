/** Личный кабинет: смена собственного пароля. */

import { apiPost } from './client'

export interface PasswordChangePayload {
  current_password: string
  new_password: string
}

/** `POST /auth/change-password` → 204; ошибки `INVALID_PASSWORD`, `WEAK_PASSWORD`. */
export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const payload: PasswordChangePayload = {
    current_password: currentPassword,
    new_password: newPassword,
  }
  await apiPost<void>('/auth/change-password', payload)
}
