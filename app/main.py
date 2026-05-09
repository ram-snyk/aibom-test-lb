"""
AIBOM Test Application - FastAPI Entry Point

A sample AI/ML application demonstrating AWS Bedrock and AgentCore integration.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import boto3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
BEDROCK_AGENT_ID = os.getenv("BEDROCK_AGENT_ID", "")
BEDROCK_AGENT_ALIAS_ID = os.getenv("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")

logger = logging.getLogger(__name__)


def _parse_cors_origins():
    """
    Build CORS settings. Wildcard origin must not be combined with credentials
    (browser behavior + security scanners flag allow_credentials=True with '*').
    """
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    allow_credentials_env = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    if "*" in origins:
        return ["*"], False
    return origins or ["http://localhost:3000"], allow_credentials_env


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline HTTP security headers for browser-facing API responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy",
            "strict-origin-when-cross-origin",
        )
        return response


def _public_error_detail(exc: Exception) -> str:
    env = os.getenv("ENVIRONMENT", "development").lower()
    if env in ("production", "staging"):
        return "Internal server error"
    return str(exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting AIBOM Application (%s)", ENVIRONMENT)
    yield
    logger.info("Shutting down AIBOM Application")


app = FastAPI(
    title="AIBOM Test Application",
    description="AI Bill of Materials Test Application with AWS Bedrock",
    version="1.0.0",
    lifespan=lifespan,
)

_cors_origins, _cors_credentials = _parse_cors_origins()
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# Pydantic models
class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str


class InvokeRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=100_000)
    model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        max_length=512,
    )
    max_tokens: int = Field(default=4096, ge=1, le=8192)


class InvokeResponse(BaseModel):
    response: str
    model: str
    usage: Optional[Dict[str, Any]] = None


class AgentRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=100_000)
    session_id: Optional[str] = Field(default=None, max_length=256)


class AgentResponse(BaseModel):
    response: str
    session_id: str


# Health check
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        environment=ENVIRONMENT,
        version="1.0.0",
    )


# Bedrock model invocation
@app.post("/invoke", response_model=InvokeResponse)
async def invoke_model(request: InvokeRequest):
    """Invoke a Bedrock model directly."""
    try:
        bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)

        response = bedrock_runtime.invoke_model(
            modelId=request.model_id,
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": request.max_tokens,
                    "messages": [{"role": "user", "content": request.prompt}],
                }
            ),
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())

        return InvokeResponse(
            response=response_body.get("content", [{}])[0].get("text", ""),
            model=request.model_id,
            usage=response_body.get("usage"),
        )
    except Exception as exc:
        logger.exception("Bedrock invoke_model failed")
        raise HTTPException(
            status_code=500,
            detail=_public_error_detail(exc),
        ) from exc


# Bedrock Agent invocation
@app.post("/agent", response_model=AgentResponse)
async def invoke_agent(request: AgentRequest):
    """Invoke the Bedrock Agent."""
    if not BEDROCK_AGENT_ID:
        raise HTTPException(status_code=503, detail="Bedrock Agent not configured")

    try:
        bedrock_agent_runtime = boto3.client(
            "bedrock-agent-runtime",
            region_name=AWS_REGION,
        )

        session_id = request.session_id or str(uuid.uuid4())

        response = bedrock_agent_runtime.invoke_agent(
            agentId=BEDROCK_AGENT_ID,
            agentAliasId=BEDROCK_AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=request.input,
        )

        # Collect response chunks
        output_text = ""
        for event in response.get("completion", []):
            if "chunk" in event:
                chunk = event["chunk"]
                if "bytes" in chunk:
                    output_text += chunk["bytes"].decode("utf-8")

        return AgentResponse(
            response=output_text,
            session_id=session_id,
        )
    except Exception as exc:
        logger.exception("Bedrock invoke_agent failed")
        raise HTTPException(
            status_code=500,
            detail=_public_error_detail(exc),
        ) from exc


# List available models
@app.get("/models")
async def list_models():
    """List available Bedrock foundation models."""
    try:
        bedrock = boto3.client("bedrock", region_name=AWS_REGION)

        response = bedrock.list_foundation_models(byOutputModality="TEXT")

        models = [
            {
                "model_id": model["modelId"],
                "model_name": model["modelName"],
                "provider": model["providerName"],
                "input_modalities": model.get("inputModalities", []),
                "output_modalities": model.get("outputModalities", []),
            }
            for model in response.get("modelSummaries", [])
        ]

        return {"models": models}
    except Exception as exc:
        logger.exception("Bedrock list_foundation_models failed")
        raise HTTPException(
            status_code=500,
            detail=_public_error_detail(exc),
        ) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
