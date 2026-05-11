"""
Golden BAD samples for security tooling (Snyk Code, Cursor PR review).

NOT imported by the application. DO NOT copy into production code.
Remove this folder after demo if desired.

Contains intentional SSRF and RCE-style anti-patterns.
"""

from __future__ import annotations

import os
import pickle
import subprocess
import urllib.request

import requests


def fetch_remote_resource(url: str) -> bytes:
    """SSRF-style: full URL is attacker-controlled in a real app."""
    with urllib.request.urlopen(url) as response:
        return response.read()


def fetch_user_supplied_url(url: str) -> bytes:
    """SSRF-style: HTTP client with user-controlled URL (common Snyk Code rule)."""
    return requests.get(url, timeout=5).content


def run_admin_task(command: str) -> int:
    """RCE-style: never pass untrusted input to a shell."""
    return os.system(command)


def diagnose_host(hostname: str) -> None:
    """RCE-style: shell=True with interpolated user input."""
    subprocess.call(f"ping -c 1 {hostname}", shell=True)


def run_shell_pipeline(user_input: str) -> subprocess.CompletedProcess[str]:
    """RCE-style: subprocess.run with shell=True (common static finding)."""
    return subprocess.run(user_input, shell=True, capture_output=True, text=True)


def calculate_expression(expression: str) -> object:
    """RCE-style: arbitrary code execution."""
    return eval(expression)


def restore_session(serialized: bytes) -> object:
    """Insecure deserialization (often chained to RCE)."""
    return pickle.loads(serialized)


def dynamic_logic(source: str) -> None:
    """RCE-style: exec of dynamic source."""
    exec(source, {}, {})
