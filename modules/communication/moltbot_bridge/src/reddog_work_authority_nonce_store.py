"""In-memory work-authority nonce state used by deterministic tests."""

from __future__ import annotations

import hmac
import threading


def _is_sha256_digest(value: object) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 71 and text.startswith("sha256:") and all(
        character in "0123456789abcdef" for character in text[7:]
    )


class InMemoryNonceStore:
    """Single-process stand-in for atomic consume and publication transitions."""

    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._publications: dict[str, dict[str, str]] = {}
        self._lock = threading.Lock()

    def consume(self, nonce: str) -> bool:
        with self._lock:
            if not isinstance(nonce, str) or not nonce or nonce in self._seen:
                return False
            self._seen.add(nonce)
            return True

    def advance_publication(
        self, nonce: str, binding_digest: str, target_status: str
    ) -> str:
        with self._lock:
            return _advance_publication_state(
                seen=self._seen,
                publications=self._publications,
                nonce=nonce,
                binding_digest=binding_digest,
                target_status=target_status,
            )


def _advance_publication_state(
    *,
    seen: set[str],
    publications: dict[str, dict[str, str]],
    nonce: str,
    binding_digest: str,
    target_status: str,
) -> str:
    order = {"RESERVED": 0, "AUTHORIZED": 1, "APPLIED": 2}
    if not nonce or not _is_sha256_digest(binding_digest) or target_status not in order:
        return ""
    current = publications.get(nonce)
    if current is None:
        if nonce in seen or target_status != "RESERVED":
            return ""
        seen.add(nonce)
        publications[nonce] = {
            "binding_digest": binding_digest,
            "status": target_status,
        }
        return target_status
    if not hmac.compare_digest(
        str(current.get("binding_digest") or "").encode("utf-8"),
        binding_digest.encode("utf-8"),
    ):
        return ""
    current_status = str(current.get("status") or "")
    if current_status not in order or order[target_status] > order[current_status] + 1:
        return ""
    if order[target_status] > order[current_status]:
        current["status"] = target_status
        current_status = target_status
    return current_status


__all__ = ["InMemoryNonceStore"]
