"""FastAPI entrypoint for the context-compression proxy."""

import time
from collections import deque
from typing import Any, Deque, Dict, List

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .metrics import REQ_LATENCY_SECONDS, TOKENS_IN_TOTAL, TOKENS_SAVED_TOTAL
from .qr_retriever import reduce
from .settings import get_settings

# Track request timestamps per API token for crude rate limiting
REQUEST_LOG: Dict[str, Deque[float]] = {}

app = FastAPI(title="Context Compression Proxy")


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, x_api_key: str = Header("")) -> Any:
    settings = get_settings()
    users = settings.user_tokens
    if not x_api_key or x_api_key not in users:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # crude in-memory rate limiting per token
    now = time.time()
    window = settings.rate_limit_per_minute
    log = REQUEST_LOG.setdefault(x_api_key, deque())
    while log and now - log[0] > 60:
        log.popleft()
    if len(log) >= window:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    log.append(now)

    payload = await request.json()
    messages: List[Dict[str, Any]] = payload.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="messages field required")

    # Separate query and context
    query = messages[-1]["content"]
    context = " ".join(m["content"] for m in messages[:-1])
    tokens_before = len((context + " " + query).split())

    reduced_context = reduce(query, context)
    tokens_after = len((reduced_context + " " + query).split())
    TOKENS_IN_TOTAL.inc(tokens_before)
    TOKENS_SAVED_TOTAL.inc(tokens_before - tokens_after)

    new_messages = [
        {"role": "system", "content": reduced_context},
        messages[-1],
    ]
    payload["messages"] = new_messages

    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    url = settings.openai_api_base.rstrip("/") + "/chat/completions"

    with REQ_LATENCY_SECONDS.time():
        if settings.openai_api_key:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers)
                data = resp.json()
                response = JSONResponse(data, status_code=resp.status_code)
        else:
            data = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "[stubbed response]",
                        }
                    }
                ]
            }
            response = JSONResponse(data)

    return response


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    data = generate_latest()
    return PlainTextResponse(data, media_type=CONTENT_TYPE_LATEST)
