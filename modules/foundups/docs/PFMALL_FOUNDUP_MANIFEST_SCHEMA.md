# FoundUp Manifest / Template Schema

**Status**: Architecture specification (first tranche)
**Owner**: 0102
**Slice**: `pfmall_architecture_and_template_contract`
**WSP References**: WSP 49 (Structure), WSP 97 (Concatenation Gate), WSP 29 (CABR Engine)

---

## 1. Purpose

Every FoundUp that runs inside p.fMALL declares itself through a `foundup_manifest.json`. This manifest is the contract between a FoundUp and the shell. It tells the shell what the FoundUp needs, what it provides, and how to load it.

---

## 2. Manifest Schema

### 2.1 Full Schema Definition

```json
{
  "$schema": "https://foundups.org/schemas/foundup-manifest/v1.json",

  "foundup_id": "string",
  "name": "string",
  "version": "string (semver)",
  "description": "string (max 280 chars)",
  "tagline": "string (max 80 chars)",

  "tier": "F0_DAE | F1_OPO | F2_GROWTH | F3_INFRA | F4_MEGA | F5_SYSTEMIC",
  "lifecycle_stage": "incubating | proto | externalized | federated",

  "entry_url": "string (relative or absolute URL to FoundUp bundle)",
  "routing_prefix": "/f/{foundup_id}",
  "icon_url": "string (path to icon, min 192x192)",

  "required_subscription_tier": "free | starter | plus | pro | angel | ultimate",
  "is_invite_only": "boolean",

  "capabilities": ["string"],
  "agent_routes": ["string"],
  "holo_collections": ["string"],

  "data_namespace": "string (idb_{foundup_id})",

  "cabr_contract": {
    "v1_gate": "string (validation rule name or 'default')",
    "v2_proof": "string (verification rule name or 'default')",
    "v3_score_min": "number (0.0 - 1.0)"
  },

  "min_shell_version": "string (semver)",
  "owner_id": "string",
  "token_symbol": "string",
  "created_at": "string (ISO 8601)",

  "signature": "string (HMAC-SHA256 hex)"
}
```

### 2.2 Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `foundup_id` | string | YES | Deterministic ID: `sha256(name:owner_id:created_at)[:16]` |
| `name` | string | YES | Human-readable FoundUp name |
| `version` | semver | YES | FoundUp version (independent of shell version) |
| `description` | string (max 280) | YES | Short description for catalog display |
| `tagline` | string (max 80) | YES | One-line tagline for catalog cards |
| `tier` | enum | YES | DAO tier per `smartdao_spawning.py` (`DAOTier` enum) |
| `lifecycle_stage` | enum | YES | Per Exfoliation Protocol stages |
| `entry_url` | string | YES | URL to load the FoundUp bundle (JS entry point) |
| `routing_prefix` | string | YES | Always `/f/{foundup_id}` |
| `icon_url` | string | YES | App icon (min 192x192 for PWA) |
| `required_subscription_tier` | enum | YES | Minimum tier from `subscription_tiers.py` |
| `is_invite_only` | boolean | YES | `true` for pre-OPO FoundUps (F0_DAE) |
| `capabilities` | string[] | YES | Declared capabilities (see Section 3) |
| `agent_routes` | string[] | YES | OpenClaw routes this FoundUp may invoke |
| `holo_collections` | string[] | NO | HoloIndex collections this FoundUp reads |
| `data_namespace` | string | YES | IndexedDB namespace: `idb_{foundup_id}` |
| `cabr_contract` | object | YES | CABR 3V validation rules |
| `min_shell_version` | semver | NO | Minimum compatible shell version |
| `owner_id` | string | YES | FoundUp creator/owner identifier |
| `token_symbol` | string | YES | Token symbol per `TokenTerms` model |
| `created_at` | ISO 8601 | YES | Creation timestamp |
| `signature` | hex string | YES | HMAC-SHA256 of manifest body |

---

## 3. Capabilities Registry

Capabilities declare what platform features a FoundUp uses. The shell uses these to gate access and display appropriate UI.

| Capability | Description | Requires Tier |
|------------|-------------|---------------|
| `search` | Can use HoloIndex search | free |
| `agents_basic` | Can invoke basic OpenClaw queries | starter |
| `agents_standard` | Can invoke standard OpenClaw tasks | plus |
| `agents_pro` | Can invoke pro OpenClaw tasks | pro |
| `marketplace` | Can list/sell/buy items | plus |
| `notifications` | Can send cross-FoundUp notifications | plus |
| `offline` | Supports offline mode | free |
| `analytics` | Can access usage analytics | pro |

---

## 4. Agent Routes

Agent routes map to OpenClaw execution paths. Each FoundUp declares which routes it needs.

```json
{
  "agent_routes": [
    "openclaw_query",
    "openclaw_task",
    "openclaw_search"
  ]
}
```

The shell gates agent requests against:
1. The FoundUp's declared `agent_routes` (reject undeclared routes)
2. The user's subscription tier (reject if tier insufficient)
3. The user's UPs balance (reject if insufficient UPs)
4. The CABR contract (reject if V1 gate fails)

---

## 5. CABR Contract

The CABR contract defines quality gates for agent work within this FoundUp.

```json
{
  "cabr_contract": {
    "v1_gate": "default",
    "v2_proof": "default",
    "v3_score_min": 0.5
  }
}
```

| Field | Description |
|-------|-------------|
| `v1_gate` | Validation rule name. `"default"` uses standard CABR V1. Custom rules registered in WRE. |
| `v2_proof` | Verification rule name. `"default"` uses standard CABR V2. |
| `v3_score_min` | Minimum V3 valuation score (0.0-1.0) for agent results to be accepted. |

Reference: `WSP_knowledge/src/WSP_29_CABR_Engine.md`

---

## 6. Manifest Signing

Manifests are signed using HMAC-SHA256, extending the existing `skill_manifest_guard.py` pattern.

### 6.1 Signing Process

```python
import hashlib
import hmac
import json

def sign_manifest(manifest: dict, secret_key: bytes) -> str:
    """Sign a FoundUp manifest.

    The signature covers all fields EXCEPT 'signature' itself.
    """
    body = {k: v for k, v in manifest.items() if k != "signature"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hmac.new(secret_key, canonical.encode(), hashlib.sha256).hexdigest()
```

### 6.2 Verification

The shell verifies manifest signatures at:
1. **Catalog load** — reject unsigned or tampered manifests
2. **FoundUp load** — re-verify before iframe creation
3. **Agent request** — verify manifest hasn't changed mid-session

Failed verification = FoundUp not loaded. Fail-closed.

---

## 7. Template Inheritance

All FoundUp manifests share a base template. FoundUp-specific fields extend it.

### 7.1 Base Template (all FoundUps inherit)

```json
{
  "tier": "F0_DAE",
  "lifecycle_stage": "incubating",
  "required_subscription_tier": "free",
  "is_invite_only": true,
  "capabilities": ["search", "offline"],
  "agent_routes": ["openclaw_query"],
  "cabr_contract": {
    "v1_gate": "default",
    "v2_proof": "default",
    "v3_score_min": 0.5
  },
  "min_shell_version": "1.0.0"
}
```

### 7.2 Override Rules

- FoundUp manifests override base template values
- `capabilities` are merged (base + FoundUp-specific)
- `agent_routes` are merged (base + FoundUp-specific)
- `cabr_contract` is replaced entirely if specified
- `tier` and `lifecycle_stage` reflect current FoundUp state (not base defaults)

---

## 8. Example Manifest: gotjunk

```json
{
  "$schema": "https://foundups.org/schemas/foundup-manifest/v1.json",
  "foundup_id": "a3f8c1d2e4b67890",
  "name": "GotJunk",
  "version": "0.3.0",
  "description": "Peer-to-peer marketplace for selling unwanted items. List it, price it, move it.",
  "tagline": "Turn your junk into someone's treasure",
  "tier": "F0_DAE",
  "lifecycle_stage": "proto",
  "entry_url": "/foundups/gotjunk/bundle.js",
  "routing_prefix": "/f/a3f8c1d2e4b67890",
  "icon_url": "/foundups/gotjunk/icon-192.png",
  "required_subscription_tier": "free",
  "is_invite_only": true,
  "capabilities": ["search", "agents_basic", "marketplace", "offline"],
  "agent_routes": ["openclaw_query", "openclaw_task"],
  "holo_collections": ["holo_a3f8c1d2e4b67890_listings"],
  "data_namespace": "idb_a3f8c1d2e4b67890",
  "cabr_contract": {
    "v1_gate": "default",
    "v2_proof": "marketplace_proof",
    "v3_score_min": 0.6
  },
  "min_shell_version": "1.0.0",
  "owner_id": "012",
  "token_symbol": "JUNK",
  "created_at": "2026-03-01T00:00:00Z",
  "signature": "a1b2c3d4e5f6..."
}
```

---

## 9. Validation Rules

The shell validates manifests at load time. Any validation failure blocks the FoundUp from loading.

| Rule | Check |
|------|-------|
| Required fields present | All fields marked YES in Section 2.2 |
| `foundup_id` format | 16-char hex string |
| `version` format | Valid semver |
| `tier` value | One of `DAOTier` enum values |
| `lifecycle_stage` value | One of: incubating, proto, externalized, federated |
| `required_subscription_tier` value | One of: free, starter, plus, pro, angel, ultimate |
| `capabilities` values | All entries in capabilities registry (Section 3) |
| `agent_routes` values | All entries are known OpenClaw routes |
| `data_namespace` format | Must be `idb_{foundup_id}` |
| `cabr_contract.v3_score_min` | Number between 0.0 and 1.0 |
| `signature` valid | HMAC-SHA256 verification passes |
| `description` length | Max 280 characters |
| `tagline` length | Max 80 characters |

---

## 10. Manifest Lifecycle

```
1. AUTHOR: FoundUp developer creates manifest
2. SIGN: Manifest signed with project secret key
3. REGISTER: Manifest added to catalog.json
4. VALIDATE: Shell validates at catalog load
5. LOAD: Shell re-validates before creating iframe
6. UPDATE: New manifest version replaces old (re-sign required)
7. RETIRE: Manifest removed from catalog (FoundUp no longer discoverable)
```

Manifests are immutable per version. To change a manifest, bump the version and re-sign.

---

## 11. Manifest vs State Overlay

The manifest is a **static contract** — it declares what a FoundUp is, what it needs, and how to load it. It changes only on version bumps.

**Dynamic state** (lifecycle health, economics, agent activity) is NOT part of the manifest. It lives in a separate **state overlay** layer:

| Concern | Where It Lives | Update Frequency |
|---------|---------------|------------------|
| Identity, capabilities, CABR contract | `foundup_manifest.json` (static) | On version bump only |
| Lifecycle stage transitions | State overlay (dynamic) | On governance decision |
| Treasury balance, UPs flow | State overlay (dynamic) | Per epoch |
| Agent activity, ROC metrics | State overlay (dynamic) | Real-time |
| CABR scores (V3 valuation) | State overlay (dynamic) | Per validation cycle |

The simulator (`modules/foundups/simulator/`) may serve as one PoC provider of state overlay data, but it is not the permanent architecture. See `PFMALL_STATE_OVERLAY_CONTRACT.md` for the dynamic state plane contract.
