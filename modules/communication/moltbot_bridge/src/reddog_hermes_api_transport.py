"""Bounded loopback transport and secret source for upstream Hermes Agent."""

from __future__ import annotations

import http.client
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    validate_runtime_root_path,
)

HERMES_API_HOST = "127.0.0.1"
HERMES_API_PORT = 8642
HERMES_API_KEY_RELATIVE_PATH = Path("hermes-api") / "api-key"


@dataclass(frozen=True)
class HermesApiResponse:
    status: int
    body: str = ""
    output_limit_exceeded: bool = False


class HermesApiTransport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str],
        payload: Mapping[str, object] | None,
        timeout_seconds: int,
    ) -> HermesApiResponse: ...


@dataclass(frozen=True)
class RuntimeHermesApiKeyProvider:
    runtime_root: Path
    repo_root: Path

    def read_key(self) -> str:
        root = validate_runtime_root_path(self.runtime_root, repo_root=self.repo_root)
        value = secure_read_confined_text(
            root / HERMES_API_KEY_RELATIVE_PATH,
            allowed_root=root,
            max_bytes=512,
        ).strip()
        if not 32 <= len(value) <= 256 or any(char.isspace() for char in value):
            raise ValueError("hermes_api_key_invalid")
        return value


@dataclass(frozen=True)
class SystemHermesApiTransport:
    """Call only the fixed loopback Hermes API without redirects or proxies."""

    max_output_bytes: int = 1_000_000

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str],
        payload: Mapping[str, object] | None,
        timeout_seconds: int,
    ) -> HermesApiResponse:
        if not _valid_request(method, path, timeout_seconds):
            return HermesApiResponse(0)
        body = None
        request_headers = dict(headers)
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
            request_headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection(
            HERMES_API_HOST, HERMES_API_PORT, timeout=timeout_seconds
        )
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            declared = response.getheader("Content-Length")
            if declared and int(declared) > self.max_output_bytes:
                return HermesApiResponse(response.status, output_limit_exceeded=True)
            raw = response.read(self.max_output_bytes + 1)
            overflow = len(raw) > self.max_output_bytes
            return HermesApiResponse(
                response.status,
                raw[: self.max_output_bytes].decode("utf-8", errors="replace"),
                output_limit_exceeded=overflow,
            )
        except (OSError, ValueError, http.client.HTTPException):
            return HermesApiResponse(0)
        finally:
            connection.close()


def _valid_request(method: str, path: str, timeout_seconds: int) -> bool:
    return (
        method in {"GET", "POST"}
        and path.startswith("/")
        and not path.startswith("//")
        and "?" not in path
        and "#" not in path
        and type(timeout_seconds) is int
        and 1 <= timeout_seconds <= 3600
    )


__all__ = [
    "HERMES_API_HOST",
    "HERMES_API_PORT",
    "HermesApiResponse",
    "RuntimeHermesApiKeyProvider",
    "SystemHermesApiTransport",
]
