# Context Compression Proxy

Minimal MVP of a proxy that compresses chat context before forwarding to an
OpenAI-compatible endpoint.  See `requirements.md` for the original vision and
roadmap.

The proxy validates requests against a list of API tokens and applies a simple
per-minute rate limit. No chat payloads are persisted.

## Development

```bash
pip install -r requirements.txt
pytest
```

## Configuration

Environment variables:

- `CCP_USER_TOKENS` – comma-separated `token:user` pairs (e.g.
  `dev-token:alice,other-token:bob`).
- `CCP_RATE_LIMIT_PER_MINUTE` – number of requests per minute allowed for each
  token (default `60`).

## Docker

Build and run the proxy:

```bash
docker compose up --build
```

The service will listen on port `8000` and expose `/healthz`, `/metrics`, and
`/v1/chat/completions` routes.
