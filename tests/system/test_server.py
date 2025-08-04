import multiprocessing
import os
import time

import httpx
import uvicorn

from proxy.main import app
from proxy.settings import get_settings


def run() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")


def test_server_health_endpoint():
    get_settings.cache_clear()
    os.environ["CCP_USER_TOKENS"] = "sys-key:sys"
    proc = multiprocessing.Process(target=run)
    proc.start()
    time.sleep(1)
    try:
        resp = httpx.get("http://127.0.0.1:8001/healthz")
        assert resp.status_code == 200
    finally:
        proc.terminate()
        proc.join()
