"""Firebase bearer authentication and bounded, fail-closed API admission.

Cloud Run's frontend deployment does not establish this separate API's identity.
FIREBASE_PROJECT_ID (or GOOGLE_CLOUD_PROJECT) must name the client Firebase project.
"""
from collections import OrderedDict, deque
from functools import lru_cache
import os
import threading
import time

from fastapi import HTTPException, Request
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token


@lru_cache(maxsize=1)
def firebase_project() -> str:
    project = os.environ.get("FIREBASE_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    return project


class WriteLimiter:
    """Per-process defense; deployment must also enforce an edge/global quota.

    Do not evict active keys to admit a new attacker identity. Fail closed when
    capacity is reached. Never trust caller-supplied X-Forwarded-For headers.
    """
    def __init__(self, limit=10, window=60, capacity=4096, clock=time.monotonic):
        self.limit, self.window, self.capacity, self.clock = limit, window, capacity, clock
        self.events = OrderedDict()
        self.lock = threading.Lock()

    def admit(self, key):
        now = self.clock()
        with self.lock:
            stale = [k for k, values in self.events.items() if values[-1] <= now - self.window]
            for k in stale:
                del self.events[k]
            if key not in self.events and len(self.events) >= self.capacity:
                raise HTTPException(status_code=503, detail="Write admission unavailable")
            values = self.events.setdefault(key, deque())
            while values and values[0] <= now - self.window:
                values.popleft()
            if len(values) >= self.limit:
                raise HTTPException(status_code=429, detail="Write limit exceeded", headers={"Retry-After": str(self.window)})
            values.append(now)


write_limiter = WriteLimiter()


def require_writer(request: Request) -> str:
    project = firebase_project()
    # Limit invalid-token attempts as well as authenticated writes.
    write_limiter.admit("ip:" + (request.client.host if request.client else "unknown"))
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 8192:
        raise HTTPException(status_code=401, detail="Firebase bearer token required")
    try:
        claims = id_token.verify_firebase_token(token, GoogleRequest(), audience=project)
        uid = claims.get("sub")
        if claims.get("iss") != "https://securetoken.google.com/" + project or not isinstance(uid, str) or not uid or len(uid) > 128:
            raise ValueError("Invalid Firebase identity")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Firebase token") from None
    write_limiter.admit("uid:" + uid)
    return uid


class BodyLimitMiddleware:
    """Bound request bytes before multipart/JSON parsing, including chunked bodies."""
    def __init__(self, app, max_bytes=1024 * 1024):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        payload = bytearray()
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                return
            body = event.get("body", b"")
            if len(payload) + len(body) > self.max_bytes:
                await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"detail":"Request body too large"}'})
                return
            payload.extend(body)
            if not event.get("more_body", False):
                break
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(payload), "more_body": False}
        await self.app(scope, bounded_receive, send)
