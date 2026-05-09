"""Pytest configuration for API tests."""

import pytest


@pytest.fixture(autouse=True)
def test_env(monkeypatch: pytest.MonkeyPatch):
    """Stable defaults so AWS calls are never made accidentally."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("BEDROCK_AGENT_ID", "")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ALLOW_CREDENTIALS", raising=False)
