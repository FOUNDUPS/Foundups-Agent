# p.fMALL Data Isolation / Encryption / Sentinel Layer Model

**Status**: Architecture specification (first tranche)
**Owner**: 0102
**Slice**: `pfmall_architecture_and_template_contract`
**WSP References**: WSP 29 (CABR Engine), WSP 72 (Independence), WSP 97 (Concatenation Gate)

---

## 1. Purpose

Define how p.fMALL isolates FoundUp data from each other, encrypts data at rest, and monitors inter-component communication for anomalous patterns.

---

## 2. Data Isolation Architecture

### 2.1 Isolation Layers

```
Layer 1: iframe Origin Isolation
  - Each FoundUp runs in a sandboxed iframe
  - Same-origin policy prevents cross-FoundUp DOM/JS access
  - No shared global state

Layer 2: IndexedDB Namespace Isolation
  - Each FoundUp uses namespace: idb_{foundup_id}
  - FoundUp can only access its own databases
  - iframe origin enforcement prevents cross-namespace access

Layer 3: HoloIndex Collection ACL
  - Each FoundUp reads from: holo_{foundup_id}_*
  - Write access only via agent backend (not direct from PWA)
  - Cross-FoundUp search filtered by user subscription tier

Layer 4: Agent Execution Isolation
  - OpenClaw gates agent requests by foundup_id
  - Agent results scoped to requesting FoundUp
  - No agent can access another FoundUp's data without explicit grant
```

### 2.2 What Each Layer Prevents

| Attack Vector | Prevented By |
|---------------|-------------|
| FoundUp A reads FoundUp B's DOM | Layer 1 (iframe origin) |
| FoundUp A reads FoundUp B's IndexedDB | Layer 2 (namespace + origin) |
| FoundUp A searches FoundUp B's private data | Layer 3 (HoloIndex ACL) |
| FoundUp A triggers agents on behalf of FoundUp B | Layer 4 (OpenClaw foundup_id gate) |
| FoundUp A intercepts shell messages to FoundUp B | postMessage origin checking |
| FoundUp A navigates shell away | iframe sandbox (no `allow-top-navigation`) |
| FoundUp A exhausts shared resources | Sentinel rate limiting (Section 4) |

---

## 3. Encryption at Rest

### 3.1 IndexedDB Encryption

FoundUp data stored in IndexedDB is encrypted using the Web Crypto API.

```
Encryption scheme:
  Algorithm: AES-256-GCM
  Key derivation: PBKDF2 from user wallet seed + foundup_id salt
  IV: Random 12-byte per record
  AAD: foundup_id (additional authenticated data)
```

### 3.2 Key Management

```
User wallet seed (derived at auth)
  → PBKDF2(seed, salt=foundup_id, iterations=100000)
  → AES-256 key per FoundUp
```

- Each FoundUp gets a unique encryption key (derived from wallet + foundup_id)
- Keys are held in memory only during FoundUp session
- Keys are NOT stored in IndexedDB or localStorage
- On logout: keys cleared from memory, encrypted data remains at rest

### 3.3 Encryption Scope

| Data | Encrypted | Rationale |
|------|-----------|-----------|
| FoundUp IndexedDB records | YES | User-owned data at rest |
| Catalog entries | NO | Public metadata |
| FoundUp bundle (JS/CSS) | NO | Public code |
| HoloIndex collections | NO (server-side) | Encrypted by HoloIndex backend |
| Shell preferences | NO | Non-sensitive settings |
| UPs balance (cached) | YES | Financial data |

### 3.4 Phase 1 Simplification

Phase 1 may defer client-side encryption and rely on:
- iframe isolation (prevents cross-FoundUp reads)
- Server-side encryption for HoloIndex
- HTTPS for transport

Full client-side encryption (AES-GCM) is a Phase 2 hardening step.

---

## 4. Sentinel Layer

The sentinel monitors all postMessage traffic between the shell and FoundUps. It runs inside the shell, not inside FoundUps.

### 4.1 Sentinel Responsibilities

```
1. Schema validation   → Reject malformed messages
2. Rate limiting       → Prevent message flooding
3. Size enforcement    → Prevent memory exhaustion
4. Origin verification → Reject messages from unknown origins
5. Pattern detection   → Flag anomalous communication patterns
6. Audit logging       → Record all sentinel events
```

### 4.2 Rate Limits

| Limit | Value | Action on Breach |
|-------|-------|-----------------|
| Messages per second (per FoundUp) | 100 | Drop excess, log warning |
| Messages per minute (per FoundUp) | 2000 | Drop excess, log warning |
| Agent requests per minute (per FoundUp) | 20 | Reject with "rate_limited" error |
| UPs spend per session (per FoundUp) | Configurable (default 5000) | Reject with "spending_cap" error |
| Consecutive failed validations | 10 | Quarantine FoundUp (reload required) |

### 4.3 Schema Validation

Every message is validated against the postMessage schema defined in `PFMALL_SHELL_CONTRACT.md` Section 5.

```
Validation checks:
  1. type field present and valid ("shell_event" or "foundup_event")
  2. foundup_id matches the source iframe's registered FoundUp
  3. event field is a known event type
  4. payload is a plain object (no functions, no prototypes)
  5. timestamp is valid ISO 8601
  6. nonce is present and not a duplicate (60-second window)
  7. Total message size <= 64KB
```

### 4.4 Quarantine Protocol

When a FoundUp exceeds breach thresholds:

```
1. Sentinel marks FoundUp as quarantined
2. All further messages from FoundUp are dropped
3. Shell shows warning: "This FoundUp has been paused due to unusual activity"
4. User can choose:
   a. Reload FoundUp (clears quarantine)
   b. Close FoundUp (navigate away)
   c. Report issue
5. Quarantine event logged to telemetry
```

### 4.5 Audit Log

Sentinel events are logged locally (not sent to server unless telemetry enabled):

```json
{
  "timestamp": "2026-03-28T12:00:00Z",
  "event": "rate_limit_breach",
  "foundup_id": "a3f8c1d2e4b67890",
  "details": {
    "messages_per_second": 150,
    "limit": 100,
    "action": "drop_excess"
  }
}
```

Audit log stored in shell's own IndexedDB (`idb_pfmall_sentinel`), capped at 10,000 entries (FIFO).

---

## 5. Agent Data Flow

### 5.1 Request Path

```
FoundUp (iframe)
  → postMessage: { event: "agent_request", payload: { route, params } }
  → Shell Sentinel: validate schema, rate check, UPs check
  → Shell: forward to OpenClaw API
  → OpenClaw: permission gate (graduated autonomy)
  → WRE: execute agent skill
  → Agent: may read/write HoloIndex collections for this foundup_id
  → Result flows back: WRE → OpenClaw → Shell → postMessage → FoundUp
```

### 5.2 Data Flow Rules

| Rule | Enforcement |
|------|-------------|
| FoundUp cannot write to HoloIndex directly | No HoloIndex client in FoundUp; writes go through agents only |
| FoundUp cannot read other FoundUp's HoloIndex data | Agent backend filters by foundup_id |
| Agent results scoped to requesting FoundUp | OpenClaw attaches foundup_id to all agent contexts |
| UPs deducted per agent request | Shell deducts before forwarding to OpenClaw |
| Failed agent requests do not deduct UPs | Deduction reversed on failure |

### 5.3 Cross-FoundUp Notifications

FoundUps can send notifications to other FoundUps through the shell's notification bus:

```
FoundUp A: { event: "notification_send", payload: { target_foundup: "B", message: "..." } }
  → Shell Sentinel: validate, rate check
  → Shell: check if user has access to FoundUp B
  → Shell: store notification in notification queue
  → If FoundUp B is loaded: deliver via postMessage
  → If FoundUp B is not loaded: show in shell notification area
```

Notifications are text-only (no code, no HTML). Max 500 characters. Rate limited to 10/minute per FoundUp.

---

## 6. Telemetry Isolation

### 6.1 What is Collected

```json
{
  "foundup_id": "a3f8c1d2e4b67890",
  "event": "agent_request",
  "timestamp": "2026-03-28T12:00:00Z",
  "duration_ms": 450,
  "ups_spent": 110,
  "agent_route": "openclaw_task",
  "success": true
}
```

### 6.2 What is NOT Collected

- FoundUp internal state or user data
- Agent request payloads or results
- IndexedDB contents
- User identity (anonymized session IDs only)
- postMessage contents (only message counts and sizes)

### 6.3 Anonymization

- User ID replaced with session hash: `sha256(user_id + date)[:12]`
- FoundUp-specific data aggregated before transmission
- No individual request details leave the device unless telemetry enabled

---

## 7. Security Boundary Summary

```
+------------------------------------------+
|  p.fMALL Shell                           |
|  +------------------------------------+  |
|  | Sentinel Layer                      |  |
|  | - Schema validation                 |  |
|  | - Rate limiting                     |  |
|  | - Origin checking                   |  |
|  | - Audit logging                     |  |
|  +------------------------------------+  |
|                                          |
|  +-----------+  +-----------+            |
|  | FoundUp A |  | FoundUp B |  ...       |
|  | (iframe)  |  | (iframe)  |            |
|  |           |  |           |            |
|  | idb_A     |  | idb_B     |            |
|  | holo_A_*  |  | holo_B_*  |            |
|  +-----------+  +-----------+            |
|       |              |                   |
|  postMessage    postMessage              |
|       |              |                   |
|  +------------------------------------+  |
|  | Shell Router + Auth + HoloClient   |  |
|  +------------------------------------+  |
|       |                                  |
|  +------------------------------------+  |
|  | OpenClaw API (agent execution)      |  |
|  +------------------------------------+  |
+------------------------------------------+
```

**Fail-closed at every boundary**: If validation fails at any layer, the request is rejected and the FoundUp continues operating in its sandbox without the requested capability.
