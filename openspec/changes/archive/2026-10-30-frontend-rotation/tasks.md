## 1. API-клиент

- [x] 1.1 `api/rotation.ts`: `checkoutDevice`, `transferDevice`, payload-типы.
- [x] 1.2 `lib/format.ts`: `toIsoDateTime` для `<input type="date">` → ISO datetime.

## 2. Диалоги

- [x] 2.1 `components/RotationDialogs.tsx`: общий `RotationModal` (держатель, срок,
      состояние, комментарий) + `CheckoutModal` и `TransferModal`.
- [x] 2.2 Список сотрудников без неактивных и без владельца/текущего держателя.
- [x] 2.3 Пустые необязательные поля не отправляются; ошибка показывается в диалоге.

## 3. Карточка

- [x] 3.1 Права `canCheckout` / `canTransfer`.
- [x] 3.2 Кнопки «Выдать» и «Передать» в шапке карточки.
- [x] 3.3 Обновление устройства, истории, фото и отчётов после действия.

## 4. Проверка

- [x] 4.1 `npm run build`, `npm run lint`.
- [x] 4.2 Сквозная проверка выдачи и передачи на изолированном бэкенде.
- [x] 4.3 `openspec validate --all --strict`.
