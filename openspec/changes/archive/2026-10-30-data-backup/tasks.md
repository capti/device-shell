# Tasks

## 1. Каталог копий в настройках

- [x] 1.1 `backend/app/config.py`: свойство `backup_dir` (`data_dir / "backups"`);
      `tests/conftest.py` — чистить каталог копий перед каждым тестом.
      Проверка: `uv run pytest` зелёный, копии не протекают между тестами.

## 2. Сервис бэкапа

- [x] 2.1 `backend/app/services/backup.py`: `database_path()` из
      `settings.database_url`, `create_backup(keep, now)` — каталог
      `qa-backup-<дата>_<время>` с базой (через `sqlite3.backup`) и копией
      `media`; при ошибке каталог удаляется. Проверка: тест на создание копии
      (каталог, файл базы, файл media) — `uv run pytest backend/tests/test_backup.py`.
- [x] 2.2 Ошибки сервиса: `BACKUP_NO_DATABASE` при отсутствии базы,
      `BACKUP_EXISTS` при повторе в ту же секунду, `BACKUP_UNSUPPORTED` для
      не-SQLite базы. Проверка: тесты на каждый код.
- [x] 2.3 Ретенция: `prune_backups(keep)` оставляет `keep` самых новых копий;
      `--keep < 1` → `BACKUP_KEEP_INVALID` без удалений. Проверка: тест на 16
      копий (остаются 14 последних) и тест на некорректный лимит.
- [x] 2.4 Восстановление `restore_backup(path)`: заменяет базу и `media`;
      каталог без `qa.db` → `BACKUP_INVALID` без изменения данных. Проверка:
      тест восстановления (записи и файлы после копии исчезают) и тест на
      некорректную копию.

## 3. CLI и обёртка

- [x] 3.1 `backend/app/cli.py`: подкоманды `backup [--keep N]` и
      `restore <path> [--yes]`, ошибки `AppError` → сообщение в stderr и код 1.
      Проверка: тесты CLI в `test_backup.py` (код 0 и сообщение о копии,
      `restore` без `--yes` ничего не меняет).
- [x] 3.2 `backup.ps1` в корне — запуск через `uv`, готовый `.venv` или
      `python -m uv` без интерактивных запросов (планировщик даёт минимальный
      PATH). Проверка: `powershell -File backup.ps1` создаёт копию (см. 4.2).

## 4. Проверка этапа

- [x] 4.1 `uv run pytest` и `uv run ruff check .` зелёные;
      `openspec validate --all --strict` зелёный (15/15).
- [x] 4.2 Сквозная проверка на отдельном каталоге данных: `backup.ps1`
      создаёт копию с базой и media, `restore --yes` возвращает записи и файлы,
      лишняя копия сверх лимита удаляется.
- [x] 4.3 Ревью через `crapper`, `dryer`, `mutator`: покрытие нового кода
      100%, `dryer` дублей не нашёл; остались только эквивалентные мутанты
      (пустой срез при равном числе копий, `ignore_errors` и `parents`).
- [x] 4.4 README: раздел «Бэкап и восстановление» (команды, планировщик,
      порядок восстановления).
- [x] 4.5 Локальный коммит этапа: `feat(backend): data and media backup (B9)`.

## Workflow follow-up

- `openspec archive data-backup` после принятия ревью.
- Локальный коммит архива: `chore(openspec): archive data-backup`.
