"""Pytest configuration."""

import pytest


@pytest.fixture(autouse=True)
def test_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("BEDROCK_AGENT_ID", "")
