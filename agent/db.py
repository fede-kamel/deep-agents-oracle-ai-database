"""Database connections that survive a sandbox's transient network refusals.

Inside an OpenShell 0.1.2 sandbox a new TCP connection can be refused for a
moment: the first settings poll closes open connections, and the proxy can
deny a connection whose fresh DNS mapping it already considers expired
("transparent TCP mapping is expired"). Both surface as DPY-6005 with
Errno 13. They clear within seconds, so a connection is retried a few times
with backoff before the error reaches the caller.
"""

from __future__ import annotations

import sys
import time

RETRIES = 6
TRANSIENT = ("DPY-6005", "DPY-4011", "Errno 13", "Connection reset")


def is_transient(exc: Exception) -> bool:
    text = str(exc)
    return any(marker in text for marker in TRANSIENT)


def connect(**kwargs):
    """oracledb.connect with retries on transient sandbox network refusals."""
    import oracledb

    for attempt in range(RETRIES):
        try:
            return oracledb.connect(**kwargs)
        except oracledb.Error as exc:
            if attempt == RETRIES - 1 or not is_transient(exc):
                raise
            print(f"[agent:runner] database connect refused ({str(exc).splitlines()[0][:60]}); retry {attempt + 1}",
                  file=sys.stderr, flush=True)
            time.sleep(1.0 + attempt)
    raise RuntimeError("unreachable")
