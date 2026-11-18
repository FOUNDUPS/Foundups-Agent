# GetK INTERFACE (WSP 11)

Pure, declarative PoC contracts. No side effects, no network, no IO.

## `getk_contracts` (modules/foundups/getk/src/getk_contracts.py)

### Dataclasses

- `MediaRef(ref, sha256=None, role="photo")` -- pointer to captured media; never
  a media body.
- `VehicleCapturePacket(item_id, category="kei_truck", media_refs=[], declared_fields={}, capture_source="scout_declared", auction_lookup="deferred", regulatory_status="deferred", notes="")`
  -- a captured item. Construction RAISES if `auction_lookup` or
  `regulatory_status` is anything other than `"deferred"` (no live auction/legal
  truth in the PoC).
- `GetKListingPacket(listing_id, item_id, title, description="", media_refs=[], visibility="public_browse", stakeholder_required_for_bid=True)`
  -- `from_capture(listing_id, capture, title)` classmethod.
- `CostEstimatePacket(item_id, estimated_low, estimated_high, currency="USD", basis="comparable_mock", is_authoritative=False, disclaimer=...)`
  -- RAISES if `is_authoritative` is True or if `estimated_high < estimated_low`.
  Estimates are never authoritative.

### Rules

- `StakeholderBidGate().allows(action, *, is_stakeholder) -> bool`
  -- `PUBLIC_ACTIONS` ({browse, view, watch}) allowed for all;
  `STAKEHOLDER_ACTIONS` ({bid, offer, inspect_deep, settle}) require a
  stakeholder; unknown actions fail closed (False).
- `TokenUtilityRules(symbol="GETK").validate_use(use) -> bool`
  -- returns True for `ALLOWED_TOKEN_USES` ({offset_internal_service_fee});
  RAISES `TokenUtilityError` for `FORBIDDEN_TOKEN_USES`
  ({vehicle_bid, vehicle_ownership, payment_for_vehicle}) and for unknown uses.

### Deferred provider

- `DeferredAuctionLookupProvider` -- `deferred=True`,
  `followup_slice="GETK_IMPORT_REGULATORY_PROVIDER_AUDIT_PHASE1"`;
  `lookup(query)` RAISES `NotImplementedError`. No network, no scraping.

### Constants

`REGULATORY_FOLLOWUP_SLICE`, `DEFAULT_POC_CATEGORY`, `PUBLIC_ACTIONS`,
`STAKEHOLDER_ACTIONS`, `ALLOWED_TOKEN_USES`, `FORBIDDEN_TOKEN_USES`.

## Truth boundaries

Public browse is open; bidding/deeper participation is stakeholder-gated. The
GETK token is internal utility only. Auction lookup and regulatory/import
legality are deferred to named follow-ups, never asserted here as truth.
