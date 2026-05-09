"""Tests for app.main (FastAPI surface and security defaults)."""

import io
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_health_returns_ok(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["environment"] == "development"


def test_security_headers_on_health(client: TestClient):
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"


def test_invoke_request_validation_empty_prompt(client: TestClient):
    r = client.post("/invoke", json={"prompt": "", "max_tokens": 100})
    assert r.status_code == 422


def test_invoke_request_validation_max_tokens_too_high(client: TestClient):
    r = client.post(
        "/invoke",
        json={"prompt": "hi", "max_tokens": 99999},
    )
    assert r.status_code == 422


@patch("app.main.boto3.client")
def test_invoke_success(mock_boto_client, client: TestClient):
    mock_rt = MagicMock()
    mock_rt.invoke_model.return_value = {
        "body": io.BytesIO(
            json.dumps(
                {
                    "content": [{"text": "hello"}],
                    "usage": {"input_tokens": 1},
                }
            ).encode()
        ),
    }
    mock_boto_client.return_value = mock_rt

    r = client.post(
        "/invoke",
        json={"prompt": "ping", "max_tokens": 50},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["response"] == "hello"
    assert data["model"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"


@patch("app.main.boto3.client")
def test_invoke_production_hides_exception_detail(mock_boto_client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    prod_client = TestClient(app)

    mock_rt = MagicMock()
    mock_rt.invoke_model.side_effect = RuntimeError("secret aws detail")
    mock_boto_client.return_value = mock_rt

    r = prod_client.post("/invoke", json={"prompt": "x", "max_tokens": 10})
    assert r.status_code == 500
    assert r.json()["detail"] == "Internal server error"


def test_agent_not_configured(client: TestClient):
    r = client.post("/agent", json={"input": "hello"})
    assert r.status_code == 503


@patch("app.main.boto3.client")
def test_list_models_success(mock_boto_client, client: TestClient):
    mock_bedrock = MagicMock()
    mock_bedrock.list_foundation_models.return_value = {
        "modelSummaries": [
            {
                "modelId": "anthropic.claude-v2",
                "modelName": "Claude",
                "providerName": "Anthropic",
                "inputModalities": ["TEXT"],
                "outputModalities": ["TEXT"],
            }
        ]
    }
    mock_boto_client.return_value = mock_bedrock

    r = client.get("/models")
    assert r.status_code == 200
    assert len(r.json()["models"]) == 1
    assert r.json()["models"][0]["model_id"] == "anthropic.claude-v2"
