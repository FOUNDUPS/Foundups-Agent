"""Trusted-time campaign-authority refresh for production binding."""

from __future__ import annotations

from typing import Any

from .model_autoresearch_production_authority_use import (
    trusted_campaign_authority_time,
    validate_campaign_promotion_authority_use,
)


def refresh_production_authority(inputs: dict[str, Any]) -> int:
    now = trusted_campaign_authority_time(inputs["authority_use"])
    validate_campaign_promotion_authority_use(
        inputs["authenticated_promotion"].authority,
        inputs["authority_use"],
        now=now,
    )
    inputs["now"] = now
    return now


__all__ = ["refresh_production_authority"]
