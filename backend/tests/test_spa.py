"""Раздача собранного SPA: index.html браузеру, файлы как есть, API не тронут."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.spa import resolve_file

# Accept навигационного запроса браузера: SPA получает index.html.
BROWSER_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"


@pytest.fixture()
def dist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Каталог сборки фронтенда с index.html и одним бандлом."""
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<html><body>SPA</body></html>", encoding="utf-8")
    (root / "assets" / "app-abc123.js").write_text("console.log(1)", encoding="utf-8")
    monkeypatch.setattr(settings, "frontend_dist", root)
    return root


def test_browser_route_returns_index(client: TestClient, dist: Path) -> None:
    response = client.get("/login", headers={"Accept": BROWSER_ACCEPT})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "SPA" in response.text
    assert response.headers["cache-control"] == "no-cache"


def test_root_is_served_even_without_html_accept(client: TestClient, dist: Path) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "SPA" in response.text


def test_built_bundle_is_served(client: TestClient, dist: Path) -> None:
    response = client.get("/assets/app-abc123.js")

    assert response.status_code == 200
    assert "console.log(1)" in response.text
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_unknown_api_path_keeps_json_error_envelope(client: TestClient, dist: Path) -> None:
    response = client.get("/missing-endpoint")

    # Конверт совпадает с тем, что отдавался до появления SPA-маршрута.
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["message"]
    assert "detail" not in body


def test_json_client_does_not_fall_back_to_index(client: TestClient, dist: Path) -> None:
    response = client.get("/login", headers={"Accept": "application/json"})

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_api_routes_are_not_shadowed(client: TestClient, dist: Path) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_missing_bundle_is_404_for_script_request(client: TestClient, dist: Path) -> None:
    response = client.get("/assets/gone.js")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_without_dist_everything_is_404(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "frontend_dist", tmp_path / "no-such-dir")

    response = client.get("/", headers={"Accept": BROWSER_ACCEPT})

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_resolve_file_returns_existing_file(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    bundle = dist / "assets" / "app.js"
    bundle.write_text("x", encoding="utf-8")

    assert resolve_file(dist, "assets/app.js") == bundle


def test_resolve_file_blocks_path_traversal(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")

    assert resolve_file(dist, "../secret.txt") is None
    assert resolve_file(dist, "..") is None
    assert resolve_file(dist, str(secret)) is None
    assert resolve_file(dist, "missing.html") is None
