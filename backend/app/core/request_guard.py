from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class _ExpiringRequestGuard:
    """In-process protection for the single-worker MVP deployment."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._events: dict[str, float] = {}

    def enforce_rate(self, key: str, *, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            requests = self._requests[key]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= limit:
                retry_after = max(1, int(window_seconds - (now - requests[0])))
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "Too many requests. Try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            requests.append(now)

    def first_event(self, key: str, *, ttl_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            for event_key, expiry in list(self._events.items()):
                if expiry <= now:
                    self._events.pop(event_key, None)
            if key in self._events:
                return False
            self._events[key] = now + ttl_seconds
            return True

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()
            self._events.clear()


request_guard = _ExpiringRequestGuard()


def client_ip(request: Request) -> str:
    # The production backend is reached through the bundled nginx container,
    # which replaces X-Real-IP with the connection address. Direct local and
    # test requests fall back to Starlette's client tuple.
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def stable_event_key(body: dict) -> str:
    callback_id = (body.get("callback") or {}).get("callback_id")
    if callback_id:
        return f"callback:{callback_id}"
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "update:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
