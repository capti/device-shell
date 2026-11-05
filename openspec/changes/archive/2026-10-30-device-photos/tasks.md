# Tasks

## 1. Конфигурация media-каталога

- [x] 1.1 `backend/app/config.py`: свойство `media_dir` (`data_dir / "media"`);
      `tests/conftest.py` — переменная `DATA_DIR` во временный каталог до
      импорта приложения. Проверка: `uv run pytest` зелёный (существующие
      тесты не пишут в рабочий `data/`).

## 2. Схемы и сериализация

- [x] 2.1 `backend/app/schemas/photos.py`: `PhotoRead` (id, device_id,
      report_id, url, thumb_url, uploaded_by, created_at); поле
      `photos: list[PhotoRead]` в `ConditionReportRead`. Проверка:
      `uv run pytest backend/tests/test_condition_reports.py` зелёный.

## 3. Сервис загрузки и валидации

- [x] 3.1 `backend/app/services/photos.py`: валидация размера (10 МБ) и
      формата по содержимому (JPEG/PNG/WEBP) с кодами `PHOTO_TOO_LARGE`,
      `UNSUPPORTED_FORMAT`; сохранение оригинала без EXIF и превью 400 px в
      `media_dir/devices/{device_id}/`, относительные пути в БД.
      Проверка: тесты `test_photos.py` на превышение размера, недопустимый
      формат и успешную загрузку (201, файлы существуют, EXIF вычищен) —
      `uv run pytest backend/tests/test_photos.py` зелёный.
- [x] 3.2 Лимит 5 фото на устройство (`PHOTO_LIMIT`, 422, файл не
      сохраняется) и привязка `report_id` (чужой отчёт → `REPORT_DEVICE_MISMATCH`).
      Проверка: тесты на 6-ю фотографию и чужой `report_id` —
      `uv run pytest backend/tests/test_photos.py` зелёный.
- [x] 3.3 Компенсация: при ошибке сохранения уже записанные файлы удаляются.
      Проверка: тест имитирует ошибку на коммите (monkeypatch) и убеждается,
      что каталог устройства остался пустым —
      `uv run pytest backend/tests/test_photos.py` зелёный.

## 4. Права и события

- [x] 4.1 Загрузка: `ensure_can_act_on_hold` + запрет архива
      (403 постороннему, 409 `DEVICE_ARCHIVED`); событие `photo_added` в той же
      транзакции. Проверка: тесты на постороннего, архив и наличие события
      `photo_added` в `device_events` — `uv run pytest backend/tests/test_photos.py` зелёный.
- [x] 4.2 Удаление `DELETE /photos/{pid}`: автор/владелец/admin, иначе 403;
      архив → 409 `DEVICE_ARCHIVED`; файлы удаляются, пишется
      `photo_removed`. Проверка: тесты удаления (успех, 403, архив, файлы
      исчезли) — `uv run pytest backend/tests/test_photos.py` зелёный.

## 5. API и раздача

- [x] 5.1 `backend/app/api/photos.py`: `POST /devices/{id}/photos`
      (multipart, `files` + `report_id`), `GET /devices/{id}/photos`
      (401 без сессии), `DELETE /photos/{pid}`; роутер подключён в
      `main.py`. Проверка: `uv run pytest backend/tests/test_photos.py`
      зелёный (успешная загрузка, список по убыванию, 401 без сессии).
- [x] 5.2 Mount `/media` (StaticFiles) в `create_app()` с созданием каталога.
      Проверка: тест `GET /media/...` без cookie отвечает 200, а не 401 —
      `uv run pytest backend/tests/test_photos.py` зелёный.

## 6. Фото в отчётах о состоянии

- [x] 6.1 Сериализатор `maintenance._report_list` заполняет `photos` одним
      запросом по `device_id` (без N+1). Проверка:
      `uv run pytest backend/tests/test_condition_reports.py backend/tests/test_photos.py`
      зелёный: отчёт с фото возвращает список, отчёт без фото — пустой.

## 7. Проверка этапа

- [x] 7.1 `uv run python -m app.export_openapi` и тест
      `test_openapi_contains_photo_endpoints` в `test_openapi.py` —
      `/devices/{device_id}/photos` и `/photos/{photo_id}` в схеме.
      Проверка: `uv run pytest backend/tests/test_openapi.py` зелёный.
- [x] 7.2 Полный ревью-набор: `uv run pytest`, `uv run ruff check .`,
      `openspec validate --all --strict` зелёные; пройти `crapper`, `dryer`,
      `mutator` (команды из AGENTS.md) и закрыть найденные пробелы.
- [x] 7.3 Сквозная проверка с запущенным backend: загрузка фото через
      `curl -F` под сессией, чтение `/media/*` без сессии, удаление, отчёт
      с фото в `GET /devices/{id}/condition-reports`. Проверка: сценарии
      отвечают как в спеке.
- [x] 7.4 Локальный коммит этапа:
      `feat(backend): device photos upload, media and reports (B8)`.

## Workflow follow-up

- `openspec archive device-photos` после принятия ревью.
- Локальный коммит архива: `chore(openspec): archive device-photos`.
