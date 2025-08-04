# Context‑Compression Proxy – Production Requirements & Implementation Plan

> **Goal**: Deliver a revenue‑ready, token‑saving proxy that transparently front‑ends any OpenAI‑compatible `/v1/chat/completions` endpoint by compressing conversational context with a QR‑HEAD retriever.

---

## 1 Scope

* **In** : Single‑tenant SaaS MVP (one GPU node) plus metered billing.
* **Out**: Multi‑GPU sharding, enterprise SSO, on‑prem installer.

## 2 User Stories (dev‑centric)

1. *As a developer* I point my SDK at `https://api.ccproxy.ai` instead of `https://api.openai.com` and add `X‑API‑Key`, and my bill drops by ≥ 40 %.
2. *As an account owner* I can query `/usage` and see tokens‑before, tokens‑after, and savings.
3. *As ops* I get a Slack alert if p99 latency > 5 s or GPU memory > 90 %.

## 3 Service‑level targets

| Metric                                          | Target     |
| ----------------------------------------------- | ---------- |
| p95 end‑to‑end latency (non‑streaming, 1 k ctx) | ≤ 1 .5 s   |
| Availability                                    | ≥ 99.5 %   |
| Token‑savings accuracy                          | ± 2 tokens |

---

## 4 Tech Stack (locked)

| Layer         | Choice                             | Why                |
| ------------- | ---------------------------------- | ------------------ |
| Runtime       | Python 3.10, FastAPI               | async + type hints |
| Model lib     | 🤗 Transformers v4.43 + PEFT v0.10 | LoRA support       |
| Base model    | `mistralai/Mistral‑7B‑v0.2` int4   | ≤ 24 GB VRAM       |
| GPU           | NVIDIA A10 / 24 GB                 | cheap spot         |
| Data          | Supabase (Postgres 15)             | auth + usage rows  |
| Billing       | Stripe Usage Records               | metered            |
| Infra         | Fly.io Machines (autoscale)        | zero‑ops GPU       |
| Observability | Prometheus OTLP → Grafana Cloud    | free tier          |

---

## 5 System Components & Files

```
repo/
 ├── proxy/
 │   ├── main.py            # FastAPI app (canvas code)
 │   ├── qr_retriever.py    # condense_context helper
 │   ├── metrics.py         # Prom + loguru config
 │   └── settings.py        # Pydantic‑based env loader
 ├── docker/
 │   └── Dockerfile
 ├── charts/                # Optional Helm chart
 ├── tests/
 │   ├── unit/              # pytest
 │   └── load/              # k6 scripts
 ├── scripts/
 │   └── train_qr_lora.py   # QR‑HEAD fine‑tune driver
 ├── ci/
 │   └── github‑workflow.yml
 └── README.md
```

### Key modules

* **`settings.py`** – centralised env var parsing, default fallbacks.
* **`qr_retriever.py`** – loads model & LoRA once (`@lru_cache`), exposes `reduce(query, context) -> str`.
* **`main.py`** – routes:

  * `POST /v1/chat/completions`
  * `GET  /healthz`
  * `GET  /metrics` (Prom)
* **`metrics.py`** – counters: `tokens_in_total`, `tokens_saved_total`, `req_latency_seconds` histogram.

---

## 6 Dev → Prod Pipeline

| Step                 | Tool           | Outcome                               |
| -------------------- | -------------- | ------------------------------------- |
| **1** Push to `main` | GitHub Actions | lint + mypy + tests                   |
| **2** Build          | Docker         | image `ghcr.io/you/ccproxy:<sha>`     |
| **3** Deploy         | Flyctl         | rolling restart with health probe     |
| **4** Smoke‑test     | curl in CI     | assert 20 %+ token savings on fixture |

Scripts in `ci/github‑workflow.yml` handle all four.

---

## 7 Implementation Milestones

| W‑end | Ticket                         | File(s)                  | Definition of Done                        |
| ----- | ------------------------------ | ------------------------ | ----------------------------------------- |
| 1     | 🚧 `settings.py`, health route | `main.py`, `settings.py` | `GET /healthz` → 200                      |
| 1     | Load model + retriever         | `qr_retriever.py`        | `pytest tests/unit/test_reduce.py` passes |
| 2     | Core proxy logic               | `main.py`                | `tokens_saved > 0` in local run           |
| 2     | Dockerfile build               | `docker/Dockerfile`      | `docker run ... /healthz`=ok              |
| 3     | Prom metrics                   | `metrics.py`             | `/metrics` exposé prom family             |
| 3     | Basic auth & API key           | `main.py` + DB stub      | 401 on missing key                        |
| 4     | Usage logging                  | DB migrations            | hourly totals row inserted                |
| 4     | Stripe integration             | `billing_job.py`         | invoice created in test mode              |
| 5     | Grafana alerts                 | cloud console            | alert fires on fake high latency          |
| 6     | Demo site & docs               | `docs/`, `static/`       | live token‑savings gif                    |

---

## 8 Acceptance Tests (excerpt)

1. **Compression ratio** – Given `20 k`‑token input, compressed output ≤ `4 k` tokens.
2. **Accuracy parity** – Answers using compressed context differ < 5 Levenshtein dist vs. full‑context baseline on 100 prompts.
3. **Throughput** – Sustains ≥ 15 req/s with p95 < 2 s on `A10`.
4. **Token counter** – `x‑tokens-before` − `x‑tokens-after` = `x‑tokens-saved`.
5. **Billing** – Stripe invoice matches `tokens_after * price_per_token`.

---

## 9 Security & Privacy Notes

* No context stored long‑term; logs redact user message text.
* All env secrets pulled from Fly.io secrets store; no plaintext in repo.
* `/metrics` protected by static token; disable in production if needed.

---

## 10 Next‑phase Nice‑to‑Haves

* Multi‑GPU horizontal scale (vLLM back‑end).
* “Lossless mode” that appends a pointer to full context for citation.
* Admin panel for per‑user savings chart.

---

*Document version 1.0 — 04 Aug 2025*
