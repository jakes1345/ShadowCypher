"""Root conftest.py — starts Guardian API server for integration tests."""
import threading
import time
import requests
import pytest


def _start_guardian_server():
    import uvicorn
    from shadowcypher.api.local_api import app
    uvicorn.run(app, host="127.0.0.1", port=9999, log_level="error")


@pytest.fixture(scope="session", autouse=True)
def guardian_api_server():
    """Start the Guardian API server once per test session."""
    thread = threading.Thread(target=_start_guardian_server, daemon=True)
    thread.start()

    # Wait up to 10 seconds for the server to become ready
    for _ in range(50):
        try:
            resp = requests.get("http://localhost:9999/health", timeout=0.5)
            if resp.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.2)

    yield
    # Server thread is a daemon and will stop when the process exits
