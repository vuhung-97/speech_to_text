"""HTTP surface: versioned alias and SPA deep links must both behave."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import create_app


class StubPipeline:
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def snapshot(self) -> dict:
        return {"ok": True, "engine": {}, "queue": 0}

    def status_event(self) -> dict:
        return {"type": "status", "state": "listening"}


def make_client(tmp_path: Path) -> TestClient:
    (tmp_path / "index.html").write_text("<!doctype html><title>spa</title>", encoding="utf-8")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log(1)", encoding="utf-8")
    app = create_app(None, StubPipeline(), None, None, dist_dir=tmp_path)  # type: ignore[arg-type]
    return TestClient(app)


def test_versioned_state_alias(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        legacy = client.get("/api/state")
        versioned = client.get("/api/v1/state")
        assert legacy.status_code == versioned.status_code == 200
        assert legacy.json() == versioned.json()


def test_spa_deep_link_serves_index(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        for path in ("/", "/sessions", "/sessions/abc", "/faq", "/settings", "/nope"):
            response = client.get(path)
            assert response.status_code == 200, path
            assert "spa" in response.text, path


def test_spa_serves_real_files(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/assets/app.js")
        assert response.status_code == 200
        assert "console.log" in response.text


def test_unknown_api_path_stays_json_404(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        for path in ("/api/does-not-exist", "/api", "/api/v1/nope"):
            response = client.get(path)
            assert response.status_code == 404, path
            assert response.json()["ok"] is False


def test_path_traversal_does_not_escape_dist(tmp_path: Path) -> None:
    secret = tmp_path.parent / "secret.txt"
    secret.write_text("nope", encoding="utf-8")
    with make_client(tmp_path) as client:
        response = client.get("/../secret.txt")
        assert response.status_code == 200
        assert "nope" not in response.text
