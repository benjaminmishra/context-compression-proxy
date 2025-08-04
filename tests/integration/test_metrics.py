import os
from fastapi.testclient import TestClient

from proxy.main import app
from proxy.metrics import TOKENS_IN_TOTAL
from proxy.settings import get_settings


def setup_module(module):
    get_settings.cache_clear()
    os.environ["CCP_USER_TOKENS"] = "key:user"
    TOKENS_IN_TOTAL._value.set(0)  # reset metric


def test_metrics_increment():
    client = TestClient(app)
    client.post(
        "/v1/chat/completions",
        headers={"x-api-key": "key"},
        json={"messages": [{"role": "user", "content": "hello"}, {"role":"user","content":"there"}]},
    )
    resp = client.get("/metrics")
    assert "tokens_in_total" in resp.text
