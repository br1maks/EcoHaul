import os
import subprocess
import sys

import pytest


@pytest.mark.integration
def test_worker_database_connections_do_not_cross_event_loops():
    environment = {**os.environ, "DB_USE_NULL_POOL": "True"}
    result = subprocess.run(
        [sys.executable, "-c", "import asyncio; from app.tasks.orders import _cancel_expired; "
         "asyncio.run(_cancel_expired()); asyncio.run(_cancel_expired())"],
        env=environment, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
