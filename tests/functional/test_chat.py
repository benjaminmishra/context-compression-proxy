import os
from fastapi.testclient import TestClient

from proxy.main import app
from proxy.settings import get_settings


def setup_module(module):
    get_settings.cache_clear()
    os.environ["CCP_USER_TOKENS"] = "test-key:tester"
    os.environ["CCP_RATE_LIMIT_PER_MINUTE"] = "2"


def test_chat_requires_valid_token():
    client = TestClient(app)
    resp = client.post(
        "/v1/chat/completions",
        headers={"x-api-key": "bad"},
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 401


def test_chat_rate_limit():
    client = TestClient(app)
    for _ in range(2):
        assert (
            client.post(
                "/v1/chat/completions",
                headers={"x-api-key": "test-key"},
                json={"messages": [{"role": "user", "content": "hi"}]},
            ).status_code
            == 200
        )
    resp = client.post(
        "/v1/chat/completions",
        headers={"x-api-key": "test-key"},
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 429
