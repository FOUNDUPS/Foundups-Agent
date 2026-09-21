# Public catalog projector test inventory

## 2026-09-21 — Optional discovery aliases

Existing owner: `test_projector.py`. The suite covers allowlist/member-field
rejection, registry-derived values, portfolio filtering, committed artifact
parity, source independence and CLI exit behavior. The same fixture now covers
optional alias grammar, all visibility states, hidden/ineligible reservations,
self/canonical/alias collisions, duplicate targets, optional field omission or
injection, and the registry schema (including trailing-newline rejection).

Local result: 97 passed, no skips. Two pytest configuration warnings arise from
intentionally disabled plugin autoload. Node/mock-browser route controls live
in the existing `public/member/tests/test_route_contract_bridge.py` owner and
are recorded in that directory's TestModLog. No production data generated.

WSP 15/22/50/97: inventory added at the canonical missing TestModLog location;
the existing test file was extended, with no duplicate suite or new framework.
