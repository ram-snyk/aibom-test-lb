"""Smoke tests for the FastAPI app."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"


def test_agent_returns_503_when_not_configured(client: TestClient):
    r = client.post("/agent", json={"input": "hello"})
    assert r.status_code == 503
