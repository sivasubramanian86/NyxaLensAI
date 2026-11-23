"""
NyxaLensAI — Bedrock Converse API Wrapper
Unified client for Nova Lite (fast classification) and Claude Sonnet (synthesis).
Uses pre-compiled tool schemas (Slab Allocator pattern PAT-015) and exponential backoff.
"""
from __future__ import annotations

import json
import os
import time
import logging
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Model IDs — override via environment variables for testing
LITE_MODEL_ID   = os.environ.get("LITE_MODEL_ID",   "amazon.nova-lite-v1:0")
SONNET_MODEL_ID = os.environ.get("SONNET_MODEL_ID",  "us.anthropic.claude-sonnet-4-6")
EMBED_MODEL_ID  = os.environ.get("EMBED_MODEL_ID",   "amazon.titan-embed-text-v2:0")

_MAX_RETRIES = 3
_BACKOFF_BASE = 1.5  # seconds


@lru_cache(maxsize=1)
def _bedrock_runtime_client():
    return boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def _invoke_with_retry(model_id: str, messages: list[dict], system: str = "",
                        tools: list[dict] | None = None,
                        max_tokens: int = 4096) -> dict:
    """Invoke Bedrock Converse API with exponential backoff."""
    client = _bedrock_runtime_client()
    kwargs: dict[str, Any] = {
        "modelId": model_id,
        "messages": messages,
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.1},
    }
    if system:
        kwargs["system"] = [{"text": system}]
    if tools:
        kwargs["toolConfig"] = {"tools": tools}

    for attempt in range(_MAX_RETRIES):
        try:
            response = client.converse(**kwargs)
            return response
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("ThrottlingException", "ServiceUnavailableException") and attempt < _MAX_RETRIES - 1:
                wait = _BACKOFF_BASE ** attempt
                logger.warning("Bedrock throttled (attempt %d/%d); retrying in %.1fs", attempt + 1, _MAX_RETRIES, wait)
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"Bedrock invocation failed after {_MAX_RETRIES} attempts")


def invoke_lite(prompt: str, system: str = "", max_tokens: int = 2048) -> str:
    """Fast Nova Lite call — for classification, extraction, keyword stripping."""
    response = _invoke_with_retry(
        LITE_MODEL_ID,
        [{"role": "user", "content": [{"text": prompt}]}],
        system=system,
        max_tokens=max_tokens,
    )
    return response["output"]["message"]["content"][0]["text"]


def invoke_sonnet_json(prompt: str, tool_schema: dict, system: str = "",
                        max_tokens: int = 8192) -> dict:
    """
    Claude Sonnet call with structured JSON tool use.
    Returns the parsed tool_use input dict — zero free-form text parsing.
    """
    tool_name = tool_schema["name"]
    response = _invoke_with_retry(
        SONNET_MODEL_ID,
        [{"role": "user", "content": [{"text": prompt}]}],
        system=system,
        tools=[{"toolSpec": tool_schema}],
        max_tokens=max_tokens,
    )
    content = response["output"]["message"]["content"]
    # The Converse API returns tool calls as {"toolUse": {"name", "input", ...}}.
    for block in content:
        tool_use = block.get("toolUse")
        if tool_use and tool_use.get("name") == tool_name:
            return tool_use["input"]
    # Fallback: try to parse a plain text block as JSON
    for block in content:
        text = block.get("text")
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
    raise ValueError(f"No structured tool_use block returned by {SONNET_MODEL_ID}")


def embed(text: str) -> list[float]:
    """Generate a 1024-dimensional Titan Embeddings v2 vector."""
    client = _bedrock_runtime_client()
    response = client.invoke_model(
        modelId=EMBED_MODEL_ID,
        body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True}),
        contentType="application/json",
        accept="application/json",
    )
    body = json.loads(response["body"].read())
    return body["embedding"]
