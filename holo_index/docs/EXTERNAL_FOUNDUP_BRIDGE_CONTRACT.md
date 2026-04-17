# HoloIndex FoundUp Bridge Contract

**Status**: Architecture Stub
**Owner**: 0102
**Slice**: `HOLOINDEX_EXTERNAL_FOUNDUP_BRIDGE_STUB_PHASE1`
**WSP References**: WSP 15, WSP 97

## 1. Purpose

Defines the explicit boundary contract between the Internal HoloIndex core (Python/MCP) and the External HoloIndex FoundUp (PWA/UI). This ensures the structural separation is code-real without claiming full network externalization yet.

### 1.1 Product Role

This bridge exists to support a spawned external HoloIndex FoundUp UI.

- It is **not** a required dependency for pfMALL core Mall / player / concierge runtime.
- It is an adjacent shell-facing surface for future **search and intelligence** use.
- Its likely future value is helping users and agents find:
  - code
  - WSPs
  - contracts
  - docs
  - prior artifacts
  across the FoundUps ecosystem before higher-level agent action is taken elsewhere.

## 2. Inbound Contract (From External UI -> Shell -> Core)

The external UI operates within an iframe or window controlled by p.fMALL. All requests are formatted as `agent_request` postMessage payloads, intercepted by the shell, and handed to the internal adapter stub.

### 2.1 Semantic Search Request
```json
{
  "type": "agent_request",
  "route": "openclaw_search",
  "payload": {
    "action": "semantic_search",
    "query": "WSP 97 routing rules",
    "limit": 5
  }
}
```

### 2.2 WSP Lookup Request
```json
{
  "type": "agent_request",
  "route": "openclaw_search",
  "payload": {
    "action": "wsp_lookup",
    "protocol_number": "97"
  }
}
```

## 3. Outbound Contract (From Core -> Shell -> External UI)

The Python stub handles the specific intents, converts them into FastMCP calls or direct `HoloIndex` queries, and returns a predictable response format wrapper.

### 3.1 Standard Response payload format
```json
{
  "type": "agent_response",
  "service": "holoindex",
  "status": "success",
  "data": {
    "results": [
      {
        "content": "... snippet ...",
        "path": "o:/Foundups-Agent/.../foo.py",
        "relevance": 0.95
      }
    ],
    "quantum_coherence": 0.8
  }
}
```

## 4. Metadata & Status Surface (HTTP Stub)

For catalog integration via `pfMALL`, the following HTTP/JSON endpoints are stubbed by the Adapter to mimic what a standalone FoundUp REST container would eventually provide.

- `GET /metadata`: Returns FoundUp identity metadata and life-cycle.
- `GET /status`: Returns index health, vector capabilities, Memory usage constraints.
- `GET /tasks`: Returns available capabilities for shell enumeration (e.g., `["semantic_search", "wsp_lookup", "conversation_mining"]`).

## 5. Shell-side backend registration (browser, explicit seam)

The pfMALL shell interceptor does **not** call HoloIndex over HTTP from the browser. Hosts that can supply real bridge behavior register a **local** `window.shellBridgeBackend` with:

- `search(query, limit)` → `Promise` resolving to `{ results: [...], quantum_coherence?: number }` (and optional `stub: true` if the implementation is still simulated).
- `wspLookup(protocolNumber)` → `Promise` resolving to the same envelope shape (or a single protocol-shaped object normalized by the interceptor).
- `health()` → `Promise` resolving to the same envelope shape.

Registration API (exposed after interceptor init): `window.shellBridgeInterceptor.registerShellBridgeBackend(backend, { label? })`. If absent or invalid, responses stay in **stub** mode with `data.stub === true` where applicable. Use `getShellBridgeBackendStatus()` for `{ mode: 'stub'|'registered', registered, label }` — **not** a claim of full production “live” search.
