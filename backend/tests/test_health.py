"""The health endpoint reports liveness, version and a UTC timestamp."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert set(body) == {"status", "version", "time"}


def test_health_timestamp_is_utc(client: TestClient) -> None:
    body = client.get("/api/health").json()
    parsed = datetime.fromisoformat(body["time"].replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)


def test_health_rejects_unsupported_method(client: TestClient) -> None:
    assert client.post("/api/health").status_code == 405