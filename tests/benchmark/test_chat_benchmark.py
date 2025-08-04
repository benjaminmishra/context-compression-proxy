import os
import time

from fastapi.testclient import TestClient

from proxy.main import app
from proxy.settings import get_settings


def setup_module(module):
    """Configure settings for benchmark tests."""
    get_settings.cache_clear()
    os.environ["CCP_USER_TOKENS"] = "bench-key:bench"
    os.environ["CCP_RATE_LIMIT_PER_MINUTE"] = "1000"


def test_chat_completion_latency_under_half_second():
    """Ensure the chat completion endpoint responds quickly."""
    client = TestClient(app)
    start = time.perf_counter()
    resp = client.post(
        "/v1/chat/completions",
        headers={"x-api-key": "bench-key"},
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    duration = time.perf_counter() - start
    assert resp.status_code == 200
    assert duration < 0.5
