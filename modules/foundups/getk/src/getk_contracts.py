#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GetK PoC Contracts -- pure, declarative marketplace contract model.

GetK = "Get a Kei Truck". The PoC category is Kei trucks; the long-term
architecture is a reusable AI-managed marketplace for ANY used item. This module
is the PoC CONTRACT layer only: typed packets + gate/utility rules. It builds no
marketplace, performs no auction lookup, runs no network, and encodes no
regulatory/import claims as truth.

WSP 97 TRUTH BOUNDARIES:
  - Pure data + rules. No network, no subprocess, no file IO, no external imports
    (stdlib + dataclasses + typing only).
  - Auction lookup is MOCKED/DEFERRED (see DeferredAuctionLookupProvider): it
    raises rather than pretending to look anything up.
  - Cost estimates are ESTIMATES, never authoritative (is_authoritative is always
    False; a disclaimer is always present).
  - Regulatory/import legality is DEFERRED to a separate provider/audit
    (REGULATORY_FOLLOWUP_SLICE), never asserted here as product truth.
  - The GETK token is internal utility only. It can offset internal service fees;
    it can NEVER be a vehicle bid, vehicle ownership, or payment for the vehicle.

NAVIGATION:
  -> Tested by: modules/foundups/getk/tests/test_getk_contracts.py
  -> Manifest:  modules/foundups/getk/foundup_manifest.json
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Named follow-up that owns the deferred, time-sensitive regulatory/import work.
REGULATORY_FOLLOWUP_SLICE = "GETK_IMPORT_REGULATORY_PROVIDER_AUDIT_PHASE1"

# PoC category. The model is item-agnostic; "kei_truck" is only the first vertical.
DEFAULT_POC_CATEGORY = "kei_truck"


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

@dataclass
class MediaRef:
    """A reference to captured media -- a pointer, never the media body."""

    ref: str
    sha256: Optional[str] = None
    role: str = "photo"


@dataclass
class VehicleCapturePacket:
    """A captured used-item packet (PoC: a Kei truck).

    Declared fields are SCOUT/SELLER-declared inputs, not verified truth: no VIN
    decode, no plate OCR, no auction lookup is performed. ``auction_lookup`` is a
    deferred-provider marker, never a real result.
    """

    item_id: str
    category: str = DEFAULT_POC_CATEGORY
    media_refs: List[MediaRef] = field(default_factory=list)
    declared_fields: Dict[str, str] = field(default_factory=dict)
    capture_source: str = "scout_declared"
    auction_lookup: str = "deferred"
    regulatory_status: str = "deferred"
    notes: str = ""

    def __post_init__(self) -> None:
        # Capture never carries verified auction/regulatory truth in the PoC.
        if self.auction_lookup != "deferred":
            raise ValueError("auction_lookup must be 'deferred' in the PoC")
        if self.regulatory_status != "deferred":
            raise ValueError("regulatory_status must be 'deferred' in the PoC")


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

@dataclass
class GetKListingPacket:
    """A listing assembled from a capture packet.

    Public browse is allowed for everyone; bidding/deeper participation requires
    a stakeholder (enforced by StakeholderBidGate, not by this packet).
    """

    listing_id: str
    item_id: str
    title: str
    description: str = ""
    media_refs: List[MediaRef] = field(default_factory=list)
    visibility: str = "public_browse"
    stakeholder_required_for_bid: bool = True

    @classmethod
    def from_capture(cls, listing_id: str, capture: VehicleCapturePacket, title: str) -> "GetKListingPacket":
        return cls(
            listing_id=listing_id,
            item_id=capture.item_id,
            title=title,
            media_refs=list(capture.media_refs),
        )


# ---------------------------------------------------------------------------
# Estimate
# ---------------------------------------------------------------------------

@dataclass
class CostEstimatePacket:
    """A value/cost estimate. ALWAYS an estimate, never authoritative."""

    item_id: str
    estimated_low: float
    estimated_high: float
    currency: str = "USD"
    basis: str = "comparable_mock"
    is_authoritative: bool = False
    disclaimer: str = (
        "Estimate only; not an appraisal, offer, or authoritative valuation. "
        "Comparable data is mocked/deferred in the PoC."
    )

    def __post_init__(self) -> None:
        # Truth boundary: an estimate can never be promoted to authoritative.
        if self.is_authoritative:
            raise ValueError("CostEstimatePacket.is_authoritative must be False")
        if self.estimated_high < self.estimated_low:
            raise ValueError("estimated_high must be >= estimated_low")


# ---------------------------------------------------------------------------
# Stakeholder gate
# ---------------------------------------------------------------------------

# Actions anyone may take (no stakeholder required).
PUBLIC_ACTIONS = frozenset({"browse", "view", "watch"})
# Actions that require a stakeholder.
STAKEHOLDER_ACTIONS = frozenset({"bid", "offer", "inspect_deep", "settle"})


@dataclass
class StakeholderBidGate:
    """Gate: public browse for all; bid/deeper participation for stakeholders."""

    def allows(self, action: str, *, is_stakeholder: bool) -> bool:
        if action in PUBLIC_ACTIONS:
            return True
        if action in STAKEHOLDER_ACTIONS:
            return bool(is_stakeholder)
        # Unknown actions are denied by default (fail-closed).
        return False


# ---------------------------------------------------------------------------
# Token utility rules
# ---------------------------------------------------------------------------

# The ONLY allowed token use in the PoC.
ALLOWED_TOKEN_USES = frozenset({"offset_internal_service_fee"})
# Uses the GETK token can NEVER serve.
FORBIDDEN_TOKEN_USES = frozenset(
    {"vehicle_bid", "vehicle_ownership", "payment_for_vehicle"}
)


class TokenUtilityError(ValueError):
    """Raised when a token use violates the utility-only boundary."""


@dataclass
class TokenUtilityRules:
    """GETK token = internal utility only.

    It may offset internal marketplace/service fees. It is NOT the vehicle bid,
    NOT ownership in the vehicle, and does NOT replace the transaction.
    """

    symbol: str = "GETK"

    def validate_use(self, use: str) -> bool:
        if use in FORBIDDEN_TOKEN_USES:
            raise TokenUtilityError(
                f"GETK token cannot be used for '{use}'; it is internal utility "
                f"only (not bid, ownership, or payment for the vehicle)."
            )
        if use in ALLOWED_TOKEN_USES:
            return True
        raise TokenUtilityError(f"Unknown token use '{use}' is not permitted")


# ---------------------------------------------------------------------------
# Auction lookup -- mocked / deferred (no network, no real provider)
# ---------------------------------------------------------------------------

class DeferredAuctionLookupProvider:
    """A deferred auction-lookup provider.

    The PoC performs NO real auction lookup, login, session automation, or
    scraping. Any attempt to look up raises -- the real provider is a separate,
    explicitly-named follow-up. This class exists so callers can depend on a
    provider seam without a real implementation leaking in.
    """

    deferred = True
    followup_slice = REGULATORY_FOLLOWUP_SLICE

    def lookup(self, query: str) -> None:
        raise NotImplementedError(
            "Auction lookup is deferred in the GetK PoC. Real lookup is owned by "
            f"{REGULATORY_FOLLOWUP_SLICE}; no scraping/login/network here."
        )
