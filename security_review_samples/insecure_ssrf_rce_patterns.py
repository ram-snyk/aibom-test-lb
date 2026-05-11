"""
Golden BAD samples for security tooling (Snyk Code, Cursor PR review).

NOT imported by the application. DO NOT copy into production code.
Remove this folder after demo if desired.

Contains intentional SSRF, RCE, SQL injection, and unsafe deserialization patterns
written to maximize signal for automated and LLM-assisted reviews.
"""

from __future__ import annotations

import asyncio
import http.client
import marshal
import os
import pickle
import sqlite3
import subprocess
import urllib.request
from ftplib import FTP
from typing import Any

import aiohttp
import boto3
import requests


# --------------------------------------------------------------------------- SSRF-style (user-controlled network targets)
def fetch_remote_resource(url: str) -> bytes:
    """SSRF: open arbitrary URL (file://, gopher://, internal IPs in real apps)."""
    with urllib.request.urlopen(url) as response:
        return response.read()


def fetch_with_request_object(url: str, headers: dict[str, str] | None = None) -> bytes:
    """SSRF: Request object still uses attacker-controlled URL."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as response:
        return response.read()


def fetch_user_supplied_url(url: str) -> bytes:
    """SSRF: requests.get with fully user-controlled URL (metadata service, etc.)."""
    return requests.get(url, timeout=5).content


def post_user_url_no_tls_verify(url: str, body: dict[str, Any]) -> requests.Response:
    """SSRF + bad TLS hygiene: user URL and verify=False (amplifies static rules)."""
    return requests.post(url, json=body, timeout=10, verify=False)


def requests_session_get_chain(base_url: str, path: str) -> bytes:
    """SSRF: URL built from partially controlled segments (still attacker-driven)."""
    session = requests.Session()
    return session.get(f"{base_url.rstrip('/')}/{path.lstrip('/')}", timeout=5).content


async def aiohttp_get_user_url(url: str) -> bytes:
    """SSRF: async client with user-controlled URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            return await resp.read()


def run_aiohttp_ssrf(url: str) -> bytes:
    """Sync wrapper so demos can call SSRF without an event loop."""
    return asyncio.run(aiohttp_get_user_url(url))


def http_client_raw_get(host: str, path_and_query: str) -> tuple[int, bytes]:
    """SSRF: raw HTTP to user-supplied host (internal services, cloud metadata)."""
    conn = http.client.HTTPConnection(host, timeout=5)
    conn.request("GET", path_and_query)
    resp = conn.getresponse()
    code = resp.status
    body = resp.read()
    conn.close()
    return code, body


def ftp_user_controlled_host(host: str, remote_path: str) -> None:
    """SSRF-style: outbound connection + path controlled by caller (FTP bounce / exfil patterns)."""
    with FTP(host) as ftp:
        ftp.retrbinary(f"RETR {remote_path}", lambda _: None)


def boto3_endpoint_override(endpoint_url: str, bucket: str, key: str) -> dict[str, Any]:
    """SSRF-style: custom S3 endpoint URL (classic redirect to IMDS / internal HTTP)."""
    client = boto3.client("s3", endpoint_url=endpoint_url)
    return client.get_object(Bucket=bucket, Key=key)


# --------------------------------------------------------------------------- RCE-style (command / code execution)
def run_admin_task(command: str) -> int:
    """RCE: os.system with interpolated shell command."""
    return os.system(command)


def run_via_popen(command: str) -> str:
    """RCE: os.popen reads attacker shell output."""
    with os.popen(command) as handle:
        return handle.read()


def diagnose_host(hostname: str) -> None:
    """RCE: shell=True with interpolated user input."""
    subprocess.call(f"ping -c 1 {hostname}", shell=True)


def run_shell_pipeline(user_input: str) -> subprocess.CompletedProcess[str]:
    """RCE: subprocess.run shell=True."""
    return subprocess.run(user_input, shell=True, capture_output=True, text=True)


def run_shell_check_output(user_input: str) -> str:
    """RCE: check_output with shell=True."""
    return subprocess.check_output(user_input, shell=True, text=True)


def popen_shell(user_input: str) -> subprocess.Popen[str]:
    """RCE: Popen with shell=True."""
    return subprocess.Popen(user_input, shell=True, stdout=subprocess.PIPE, text=True)


def calculate_expression(expression: str) -> object:
    """RCE: eval of user expression."""
    return eval(expression)


def compile_then_exec(source: str) -> None:
    """RCE: compile + exec of dynamic source."""
    code = compile(source, "<user>", "exec")
    exec(code, {}, {})


def dynamic_logic(source: str) -> None:
    """RCE: exec of dynamic source."""
    exec(source, {}, {})


def restore_session(serialized: bytes) -> object:
    """Insecure deserialization (pickle → arbitrary object / RCE gadgets)."""
    return pickle.loads(serialized)


def restore_marshal(blob: bytes) -> object:
    """Insecure deserialization: marshal is not a safe interchange format for untrusted bytes."""
    return marshal.loads(blob)


# --------------------------------------------------------------------------- SQL injection (paired with SSRF/RCE in reviews)
def lookup_user_by_id(db_path: str, user_id: str) -> list[tuple[Any, ...]]:
    """SQLi: string interpolation into SQL (never do this)."""
    conn = sqlite3.connect(db_path)
    try:
        return list(conn.execute(f"SELECT * FROM users WHERE id = {user_id}"))
    finally:
        conn.close()
