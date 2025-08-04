"""Prometheus metric definitions for the proxy."""

from prometheus_client import Counter, Histogram

# Total tokens received before compression
TOKENS_IN_TOTAL = Counter(
    "tokens_in_total", "Number of tokens received before compression"
)

# Total tokens saved by compression
TOKENS_SAVED_TOTAL = Counter(
    "tokens_saved_total", "Number of tokens removed by compression"
)

# Request latency histogram
REQ_LATENCY_SECONDS = Histogram(
    "req_latency_seconds", "Latency for /v1/chat/completions requests"
)
