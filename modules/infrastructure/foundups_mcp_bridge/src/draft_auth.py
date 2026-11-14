"""Bounded OAuth resource-server verification for private MCP endpoints."""

from __future__ import annotations

import asyncio
import json
import re
import time
from urllib.parse import quote_plus, urlsplit

import httpx
from mcp.server.auth.provider import AccessToken, TokenVerifier


DRAFT_READ_SCOPE = "draft:read"
DRAFT_WRITE_SCOPE = "draft:write"
_DRAFT_SCOPES = frozenset({DRAFT_READ_SCOPE, DRAFT_WRITE_SCOPE})
_BEARER = re.compile(r"[A-Za-z0-9._~+/-]+=*", re.ASCII)
_MAX_TOKEN = 8192
_MAX_INTROSPECTION_BYTES = 8192
_INTROSPECTION_TIMEOUT = 5.0


def _valid_text(value: str, limit: int) -> bool:
    return isinstance(value, str) and 0 < len(value) <= limit and all(
        "!" <= char <= "~" for char in value
    )


def _https_url(value: str) -> bool:
    if not _valid_text(value, 2048) or any(char in value for char in "\\?#"):
        return False
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and (parsed.port is None or 0 < parsed.port <= 65535)
        )
    except ValueError:
        return False


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("DUPLICATE_INTROSPECTION_CLAIM")
        obj[key] = value
    return obj


class ScopedTokenVerifier(TokenVerifier):
    """Verify each request via an operator-configured RFC 7662 endpoint.

    The issuer must report ``token_type=Bearer`` only for bearer access
    tokens. The caller registration and introspection client are distinct.
    """

    def __init__(
        self,
        *,
        issuer: str,
        introspection_url: str,
        resource_url: str,
        subject: str,
        client_id: str,
        introspection_client_id: str,
        introspection_client_secret: str,
        required_scope: str,
        allowed_scopes: frozenset[str],
    ) -> None:
        if not all(_https_url(value) for value in (issuer, introspection_url, resource_url)):
            raise ValueError("INVALID_DRAFT_OAUTH_URL")
        if not all(_valid_text(value, 512) for value in (subject, client_id, introspection_client_id)):
            raise ValueError("INVALID_DRAFT_OAUTH_IDENTITY")
        if introspection_client_id == client_id or not _valid_text(
            introspection_client_secret, 2048,
        ):
            raise ValueError("INVALID_DRAFT_INTROSPECTION_CREDENTIALS")
        self._issuer = issuer
        self._introspection_url = introspection_url
        self._resource_url = resource_url
        self._subject = subject
        self._client_id = client_id
        self._required_scope = required_scope
        self._allowed_scopes = allowed_scopes
        self._introspection_auth = httpx.BasicAuth(
            quote_plus(introspection_client_id), quote_plus(introspection_client_secret)
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        if not isinstance(token, str) or len(token) > _MAX_TOKEN or not _BEARER.fullmatch(token):
            return None
        try:
            async with asyncio.timeout(_INTROSPECTION_TIMEOUT):
                claims = await self._introspect(token)
        except (httpx.HTTPError, TimeoutError, ValueError, RecursionError):
            return None
        if not isinstance(claims, dict) or claims.get("active") is not True:
            return None
        token_type = claims.get("token_type")
        if not isinstance(token_type, str) or token_type.lower() != "bearer":
            return None
        if claims.get("token_use", "access") != "access":
            return None
        audience = claims.get("aud")
        if audience != self._resource_url and audience != [self._resource_url]:
            return None
        if (claims.get("iss"), claims.get("sub"), claims.get("client_id")) != (
            self._issuer, self._subject, self._client_id
        ):
            return None
        now = time.time()
        expires_at = claims.get("exp")
        not_before = claims.get("nbf", 0)
        if type(expires_at) is not int or expires_at <= now:
            return None
        if type(not_before) is not int or not_before > now:
            return None
        scope = claims.get("scope")
        if not isinstance(scope, str):
            return None
        scopes = scope.split(" ")
        if (
            self._required_scope not in scopes
            or not self._allowed_scopes.issuperset(scopes)
            or len(scopes) != len(set(scopes))
        ):
            return None
        return AccessToken(
            token=token, client_id=self._client_id, scopes=scopes,
            expires_at=expires_at, resource=self._resource_url,
        )

    async def _introspect(self, token: str) -> object:
        async with httpx.AsyncClient(
            trust_env=False, follow_redirects=False, timeout=_INTROSPECTION_TIMEOUT,
        ) as client, client.stream(
            "POST", self._introspection_url,
            auth=self._introspection_auth,
            headers={"Accept": "application/json", "Accept-Encoding": "identity"},
            data={"token": token, "token_type_hint": "access_token"},
        ) as response:
            if response.status_code != 200:
                return None
            media_type = response.headers.get("content-type", "").partition(";")[0].strip().lower()
            encoding = response.headers.get("content-encoding", "identity").lower()
            if media_type != "application/json" or encoding != "identity":
                return None
            body = bytearray()
            async for chunk in response.aiter_raw():
                if len(body) + len(chunk) > _MAX_INTROSPECTION_BYTES:
                    return None
                body.extend(chunk)
            return json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object)


class DraftTokenVerifier(ScopedTokenVerifier):
    """Preserve the draft caller's fixed read and optional write scopes."""

    def __init__(self, *, issuer: str, introspection_url: str, resource_url: str,
                 subject: str, client_id: str, introspection_client_id: str,
                 introspection_client_secret: str) -> None:
        super().__init__(
            issuer=issuer, introspection_url=introspection_url, resource_url=resource_url,
            subject=subject, client_id=client_id, introspection_client_id=introspection_client_id,
            introspection_client_secret=introspection_client_secret,
            required_scope=DRAFT_READ_SCOPE, allowed_scopes=_DRAFT_SCOPES,
        )
