"""Durable rate authority composed from the signer grant replay store."""

from __future__ import annotations

from dataclasses import dataclass

from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
)


@dataclass(frozen=True, slots=True)
class DurableSignerSecretGrantRateAuthority:
    """Consume signed-policy rate slots through the canonical durable store."""

    replay_store: DurableSignerSecretGrantNonceStore

    def __post_init__(self) -> None:
        if type(self.replay_store) is not DurableSignerSecretGrantNonceStore:
            raise ValueError("secret_grant_rate_store_invalid")

    @property
    def replay_store_id(self) -> str:
        return self.replay_store.replay_store_id

    @property
    def durability_receipt_id(self) -> str:
        return self.replay_store.durability_receipt_id

    @property
    def replay_store_binding_digest(self) -> str:
        return self.replay_store.replay_store_binding_digest

    @property
    def replay_store_instance_digest(self) -> str:
        return self.replay_store.replay_store_instance_digest

    def consume_issuance_attempt(
        self,
        *,
        authority_subject: str,
        now_epoch: int,
        window_seconds: int,
        max_requests: int,
    ) -> bool:
        """Atomically consume one bounded slot in the active fixed window."""

        if _rate_request_rejected(
            authority_subject, now_epoch, window_seconds, max_requests
        ):
            return False
        window = now_epoch // window_seconds
        subject = f"secret-grant-rate:{authority_subject}:{window}"
        expires_at = (window + 1) * window_seconds + 1
        for slot in range(max_requests):
            if self.replay_store.consume_scoped_nonce(
                nonce=f"issuance-slot:{slot}",
                expires_at=expires_at,
                subject=subject,
            ):
                return True
        return False


def _rate_request_rejected(
    authority_subject: object,
    now_epoch: object,
    window_seconds: object,
    max_requests: object,
) -> bool:
    return bool(
        type(authority_subject) is not str
        or not authority_subject
        or not authority_subject.isascii()
        or type(now_epoch) is not int
        or now_epoch < 0
        or type(window_seconds) is not int
        or not 1 <= window_seconds <= 3600
        or type(max_requests) is not int
        or not 1 <= max_requests <= 1000
    )


__all__ = ["DurableSignerSecretGrantRateAuthority"]
