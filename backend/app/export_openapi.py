"""Выгрузка OpenAPI-схемы в `backend/openapi.json`.

Запуск:
    uv run python -m app.export_openapi
"""

import json
from pathlib import Path

from app.main import create_app

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "openapi.json"


def export_openapi(output: Path = DEFAULT_OUTPUT) -> Path:
    app = create_app()
    output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


if __name__ == "__main__":
    path = export_openapi()
    print(f"OpenAPI сохранён: {path}")
