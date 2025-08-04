# Context‑Compression Proxy – Detailed SaaS Requirements (v2)
*Updated 04 Aug 2025*

---
## 0 Vision
Create a **drop‑in HTTP proxy** that slashes LLM token spend ≥ 40 % for developers by compressing chat context on the fly.  The service must be:
* **Self‑serve** (signup → API key in < 60 s)
* **Metered & billable** (Stripe usage‑based plans)
* **Low‑latency** (p95 ≤ 1.5 s for 1 k‑token requests)
* **Secure & compliant** (SOC 2‑ready foundations)

---
## 1 Functional Requirements
### 1.1 API
| Route | Verb | Purpose | Auth |
|-------|------|---------|------|
| `/v1/chat/completions` | POST | OpenAI‑compatible; compresses context then forwards upstream | `X‑API‑Key` (required) |
| `/usage` | GET | Returns JSON of hourly token_in / token_out / savings | JWT (user) |
| `/keys` | POST/DELETE | Create or revoke API keys | JWT (user) |
| `/healthz` | GET | Liveness & model/device info | none |
| `/metrics` | GET | Prometheus exposition | token (internal) |

### 1.2 User management
* Email‑magic‑link signup (no passwords) via **Supabase Auth**.
* Each account may create multiple **API keys** (stored hashed, argon2id).
* Roles: `user`, `admin` (admin can view other users, plan limits).
* Monthly plan attributes: `token_quota`, `qps_limit`, `model_whitelist`.

### 1.3 Rate limiting & quotas
* **Soft limit**: Redis Leaky‑Bucket per key (`tokens_in`).

* **Hard limit**: Load‑balancer level (Cloudflare) ‑ 300 req/min per IP.
* Over‑quota response → **HTTP 429** with JSON `{error:{type:"quota_exceeded"}}`.

### 1.4 Billing
* Usage row written **per request**: `(account_id, ts_hour, tokens_in, tokens_out)`.
* Nightly cron aggregates into `usage_daily`, pushes **Stripe Usage Record**.
* Plans: *Hobby*, *Pro*, *Team*, *Enterprise* – metered overages.

### 1.5 Admin ops
* `/admin/dashboard` (behind Cloudflare Access) shows real‑time QPS, GPU %, top customers, error logs.
* CLI script `ccproxy admin ban <api_key>` immediately disables key via Redis set.

---
## 2 Non‑Functional Requirements
| Category | Target / practice |
|----------|------------------|
| **Performance** | p95 latency ≤ 1.5 s (1 k ctx non‑stream); throughput ≥ 15 req/s per A10. |
| **Availability** | ≥ 99.5 % monthly, multi‑AZ GPU standby; health probes every 15 s. |
| **Scalability** | Horizontal pod autoscale when GPU util > 70 % for 2 min. |
| **Security** | All transit TLS 1.3; HSTS; secrets via Fly.io machines; OWASP top‑10 scans monthly. |
| **Privacy** | No user content persisted > 24 h; logs redact message bodies. |
| **Observability** | Prom metrics + Loki JSON logs; dashboards for latency, error rate, token saved. |
| **Compliance readiness** | Audit trails (who created key, when); data‑retention configs; GDPR‑delete endpoint. |
| **Disaster recovery** | Postgres point‑in‑time restore; daily S3 snapshot of LoRA weights & DB. |
| **CI/CD** | Push → lint/test → Docker build → staging → canary 5 % traffic → prod promote. |

---
## 3 System Design
### 3.1 Services & containers
1. **Edge (LB + WAF)** – Cloudflare → handles TLS, IP‑level rate‑limit.
2. **API Gateway** – Small FastAPI pod (CPU) for auth, JWT, and key checks; forwards to GPU pod.
3. **GPU Worker** – FastAPI + Transformers; keeps model & LoRA in memory; exposes `/chat`, `/metrics`.
4. **Jobs Container** – Celery beat worker for nightly billing, email digests.
5. **Postgres** – Supabase db_micro; stores users, keys, usage.
6. **Redis** – Fly.io Redis‑lite for rate‑limit counters and key cache.

### 3.2 Data model (Postgres)
```sql
CREATE TABLE accounts (
  id uuid PRIMARY KEY,
  email text UNIQUE NOT NULL,
  tier text NOT NULL DEFAULT 'hobby',
  created_at timestamptz DEFAULT now()
);
CREATE TABLE api_keys (
  key_hash text PRIMARY KEY,
  account_id uuid REFERENCES accounts(id),
  created_at timestamptz DEFAULT now(),
  revoked boolean DEFAULT false
);
CREATE TABLE usage_hourly (
  account_id uuid,
  ts_hour timestamptz,
  tokens_in bigint,
  tokens_out bigint,
  PRIMARY KEY(account_id, ts_hour)
);
```

### 3.3 Sequence diagram (request path)
1. **Client** → `api.ccproxy.ai` with `X-API-Key`, JSON chat payload.
2. Cloudflare authenticates & rate‑limits.
3. API Gateway:

   * verifies key (Redis), checks quota.
4. Gateway forwards to **GPU Worker** internal URL.
5. GPU Worker:

   * condenses context → calls upstream LLM → returns answer & savings headers.
6. Gateway records `(tokens_in, tokens_out)` to Redis stream.
7. Response propagated back to client.
8. Background job flushes Redis stream to `usage_hourly` every minute.

---
## 4 Implementation Roadmap (code‑wise)
| Milestone | Tasks | PR files |
|-----------|-------|----------|
| **M0 Init** | Repo scaffold, `settings.py`, Dockerfile, health route | main.py, docker/ |
| **M1 Retrieval** | QR retriever util + unit tests | qr_retriever.py, tests/ |
| **M2 Proxy logic** | `/v1/chat/completions`, upstream client stub, token headers | main.py |
| **M3 Auth & keys** | Supabase SDK, `X‑API-Key` middleware, key CRUD routes | auth.py, db.py |
| **M4 Rate‑limit** | Redis leaky bucket, global error handler 429 | ratelimit.py |
| **M5 Usage & Stripe** | Redis → Postgres flusher job, Stripe usage record cron | billing.py |
| **M6 Observability** | metrics.py, Grafana JSON dashboards, alert rules | metrics.py, charts/ |
| **M7 Docs & demo** | `/demo` static page, README gif, Postman collection | docs/, static/ |

---
## 5 Risk & Mitigations
| Risk | Mitigation |
|------|-----------|
| GPU spot pre‑emption | Warm standby pod in second region; automatic reattach of volume cache. |
| LoRA corruption | Versioned uploads to S3 (R2); checksum on start. |
| Abuse / jailbreak prompts | Optional OpenAI moderation call before compression; plan to upsell “Safe‑mode”. |
| Quota accounting drift | Hourly flush + nightly reconciliation vs. Prom counters. |

---
## 6 Definition of “Production Ready”
* All milestone M0–M6 merged to **main**, CI green.
* p95 latency, availability, token‑savings acceptance tests pass for 3 days.
* On‑call alerting routed (PagerDuty/free tier) with runbooks in `/ops`.
* First paying customer live on **Pro** tier with Stripe charge succeeded.

---
## 7 Next‑Step Upgrades (post‑launch)
1. **Org accounts + RBAC**
2. **Bring‑your‑own‑model** via vLLM plugin
3. **Edge GPU caching** using NVIDIA HGX instances
4. **HIPAA log redaction bucket** with client‑side encryption
