"""Simple in-memory sliding-window rate limiter, one bucket per profile
(mục 9.5). Fine for a single-process bridge behind Caddy; swap for Redis
if the bridge is ever scaled to multiple replicas.
"""

import threading
import time
from collections import defaultdict, deque

from .config import settings

_lock = threading.Lock()
_calls = defaultdict(deque)


def check_rate_limit(profile: str) -> bool:
    now = time.time()
    window_start = now - 60
    with _lock:
        q = _calls[profile]
        while q and q[0] < window_start:
            q.popleft()
        if len(q) >= settings.rate_limit_per_minute:
            return False
        q.append(now)
        return True
