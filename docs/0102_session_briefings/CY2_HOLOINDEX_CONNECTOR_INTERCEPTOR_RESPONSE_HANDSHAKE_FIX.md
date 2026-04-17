# CY2 — HoloIndex Connector/Interceptor Response Handshake Fix

**Worker**: CY2
**Date**: 2026-04-17
**Slice**: `HOLOINDEX_CONNECTOR_INTERCEPTOR_RESPONSE_HANDSHAKE_FIX`
**WSP Lock**: WSP 15 (pre-read), WSP 97 (no overclaiming)
**Depends On**: CY — HOLOINDEX_EXTERNAL_BRIDGE_CONTRACT_VERIFICATION_PHASE1

---

## 1. Problem Statement

CY documented two handshake mismatches preventing the HoloIndex iframe scaffold from receiving responses:

| Mismatch | Connector expects | Interceptor sends |
|----------|-------------------|-------------------|
| **Service field** | `event.data.service === 'holoindex'` | No `service` field |
| **Data field** | `event.data.payload` | `event.data.data` |

Both mismatches mean the connector's `message` event listener **never fires** for interceptor responses.

---

## 2. Convention Decision

**Service field**: Add `service: 'holoindex'` to interceptor responses for the `openclaw_search` route. This matches the connector's existing check and allows multiple FoundUp iframes to filter for their own responses.

**Data field**: Fix connector to read `event.data.data` (matching contract Section 3.1 and interceptor implementation). The connector was the outlier.

---

## 3. Changes

### 3.1 `shell-bridge-interceptor.js`

Added `ROUTE_SERVICE_MAP` (route-to-service lookup) and modified `dispatchRequest` callback to inject `response.service` before posting to the source iframe.

```javascript
var ROUTE_SERVICE_MAP = {
    'openclaw_search': 'holoindex'
};

// In dispatchRequest callback:
if (ROUTE_SERVICE_MAP[route]) {
    response.service = ROUTE_SERVICE_MAP[route];
}
```

**Why a map, not hardcoded**: When future FoundUps register routes, they add one line to `ROUTE_SERVICE_MAP`. The injection point in `dispatchRequest` stays unchanged.

### 3.2 `connector.js`

Fixed response data access path:

```javascript
// Before (wrong — "payload" is not a field in the response):
resultsPanel.textContent = JSON.stringify(event.data.payload, null, 2);

// After (correct — per contract Section 3.1):
resultsPanel.textContent = JSON.stringify(event.data.data, null, 2);
```

### 3.3 `EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md`

Updated Section 3.1 response shape to include `service` field:

```json
{
  "type": "agent_response",
  "service": "holoindex",
  "status": "success",
  "data": { ... }
}
```

---

## 4. Tests Added

### `test_bridge_contract.py` — 8 new tests (38 → 46)

| Test | What it verifies |
|------|-----------------|
| `test_contract_response_has_service_field` | Contract doc defines `"service": "holoindex"` |
| `test_interceptor_has_route_service_map` | `ROUTE_SERVICE_MAP` exists in interceptor |
| `test_interceptor_injects_service_in_response` | `response.service` assignment in dispatch |
| `test_interceptor_maps_openclaw_to_holoindex` | `openclaw_search` → `holoindex` mapping |
| `test_connector_checks_service_holoindex` | Connector filters by `service` |
| `test_connector_checks_agent_response_type` | Connector filters by `agent_response` type |
| `test_interceptor_and_connector_agree_on_service_name` | Both reference `holoindex` |
| `test_connector_reads_data_from_response` | Connector reads `event.data.data` (not `.payload`) |

### `test_shell_bridge_interceptor.py` — 2 new tests (42 → 44)

| Test | What it verifies |
|------|-----------------|
| `test_response_has_service_field` | `ROUTE_SERVICE_MAP` and `holoindex` in source |
| `test_service_injected_in_dispatch` | `response.service` in source |

### `shell_bridge_interceptor_vm.mjs` — 2 new assertions

| Assertion | Where |
|-----------|-------|
| `resolved.service === 'holoindex'` | Stub search response |
| `resolved.service === 'holoindex'` | Registered backend search response |

---

## 5. Full Test Results

| Suite | Count | Result |
|-------|-------|--------|
| `test_bridge_contract.py` | 46 | PASS |
| `test_shell_bridge_interceptor.py` | 44 | PASS |
| `test_route_contract_bridge.py` | 45 | PASS |
| **Total** | **135** | **135 PASS** |

---

## 6. Response Flow (After Fix)

```
1. Connector sends:
   window.parent.postMessage({
     type: 'agent_request',
     route: 'openclaw_search',
     payload: { action: 'semantic_search', query: '...' }
   }, '*');

2. Interceptor receives agent_request, dispatches to openclaw_search handler

3. Handler builds response:
   { type: 'agent_response', status: 'success', data: { results: [...], stub: true } }

4. dispatchRequest injects service from ROUTE_SERVICE_MAP:
   response.service = 'holoindex'

5. Interceptor posts back to iframe:
   sourceWindow.postMessage(response, origin)

6. Connector receives, filters:
   event.data.type === 'agent_response' && event.data.service === 'holoindex'
   → resultsPanel.textContent = JSON.stringify(event.data.data, null, 2)
```

**End-to-end stub response path is now wired.** No backend needed — the iframe will display stub results with `stub: true`.

---

## 7. What Was NOT Changed

- `launch_readiness` remains `discoverable_only`
- No real HoloIndex backend wired
- `bridge_stub.py` untouched (Python adapter — browser path only)
- No `entry_url` added to catalog

---

## 8. WSP 97 Statement

No readiness promotion. Bridge remains stub-only. The handshake fix enables the UI scaffold to **display** stub responses, not to claim live search capability. `launch_readiness: discoverable_only` is still truthful.

---

*CY2 complete. Connector/interceptor response handshake is wired. 135 tests pass. Iframe scaffold can now receive and display stub responses end-to-end.*
