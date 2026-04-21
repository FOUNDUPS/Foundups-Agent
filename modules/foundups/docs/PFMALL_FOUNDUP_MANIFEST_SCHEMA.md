# FoundUp Manifest / Template Schema

**Status**: Architecture specification (first tranche) — reconciled 2026-04-21
**Owner**: 0102
**Slice**: `pfmall_architecture_and_template_contract`
**Reconciled**: PFMALL-MANIFEST-SCHEMA-RECON (W2, 2026-04-21)
**WSP References**: WSP 49 (Structure), WSP 97 (Truth), WSP 29 (CABR Engine), WSP 104 (Namespace)

---

## 1. Purpose

Every FoundUp that runs inside p.fMALL declares itself through a `foundup_manifest.json`. This manifest is the contract between a FoundUp and the shell. It tells the shell what the FoundUp needs, what it provides, and how to load it.

### 1.1 Relationship to Video Mall Catalog

This document describes the **full FoundUp runtime manifest** — a signed contract for shell loading with CABR, capabilities, and agent routes.

The **Video Mall Catalog** (`mall-video-catalog.json`) is a separate, simpler schema for Mall tile projection. See `PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md` for that schema.

| Concern | This Schema | Video Mall Catalog |
|---------|-------------|-------------------|
| Purpose | Shell runtime loading | Mall field projection |
| File | `foundup_manifest.json` | `mall-video-catalog.json` |
| Signing | HMAC-SHA256 specified (`SPECIFIED_NOT_IMPLEMENTED`) | Not required |
| CABR | V1/V2/V3 contract | Not included |
| Capabilities | Declared | Not included |
| Videos | Not included | Primary content |

---

## 2. Manifest Schema

### 2.1 Full Schema Definition

```json
{
  "$schema": "https://foundups.org/schemas/foundup-manifest/v1.json",

  "foundup_id": "string (human-readable slug, e.g. 'gotjunk_001')",
  "name": "string",
  "version": "string (semver)",
  "description": "string (max 280 chars)",
  "tagline": "string (max 80 chars)",

  "tier": "F0_DAE | F1_OPO | F2_GROWTH | F3_INFRA | F4_MEGA | F5_SYSTEMIC",
  "lifecycle_stage": "incubating | proto | externalized | federated  (see Section 2.3)",

  "entry_url": "string (relative or absolute URL to FoundUp bundle)",
  "routing_prefix": "/f/{foundup_id}",
  "icon_url": "string (path to icon, min 192x192)",

  "required_subscription_tier": "free | starter | basic | plus | pro | enterprise",
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

  "category": "string (e.g. 'marketplace', 'media')",
  "launch_readiness": "ready | conditional | discoverable_only",

  "min_shell_version": "string (semver)",
  "owner_id": "string",
  "token_symbol": "string",
  "created_at": "string (ISO 8601)",

  "signature": "string (HMAC-SHA256 hex)  [SPECIFIED_NOT_IMPLEMENTED]"
}
```

### 2.2 Field Definitions

| Field | Type | Required | Implementation Status | Description |
|-------|------|----------|----------------------|-------------|
| `foundup_id` | string | YES | `IMPLEMENTED_IN_MANIFESTS` | Human-readable slug (e.g. `gotjunk_001`, `kosei`). Min 3 chars, validated by `shell_core.py`. |
| `name` | string | YES | `IMPLEMENTED_IN_MANIFESTS` | Human-readable FoundUp name |
| `version` | semver | YES | `IMPLEMENTED_IN_MANIFESTS` | FoundUp version (independent of shell version) |
| `description` | string (max 280) | YES | `IMPLEMENTED_IN_MANIFESTS` | Short description for catalog display |
| `tagline` | string (max 80) | YES | `IMPLEMENTED_IN_MANIFESTS` | One-line tagline for catalog cards |
| `tier` | enum | YES | `IMPLEMENTED_IN_MANIFESTS` | DAO tier per `smartdao_spawning.py` (`DAOTier` enum). Validated by `shell_core.py`. |
| `lifecycle_stage` | enum | YES | `IMPLEMENTED_IN_MANIFESTS` | See Section 2.3 for dual stage sets. Validated by `shell_core.py`. |
| `entry_url` | string | YES | `IMPLEMENTED_IN_MANIFESTS` | URL to load the FoundUp bundle (JS entry point) |
| `routing_prefix` | string | YES | `IMPLEMENTED_IN_MANIFESTS` | Always `/f/{foundup_id}`. Validated by `test_namespace_guardrail.py` (WSP 104). |
| `icon_url` | string | YES | `IMPLEMENTED_IN_MANIFESTS` | App icon (min 192x192 for PWA). May be `null` for incubating FoundUps. |
| `required_subscription_tier` | enum | YES | `IMPLEMENTED_IN_MANIFESTS` | Minimum tier from `subscription_tiers.py` TIERS dict: `free, starter, basic, plus, pro, enterprise`. Angel tier is a separate class, not in this enum. |
| `is_invite_only` | boolean | YES | `IMPLEMENTED_IN_MANIFESTS` | `true` for pre-OPO FoundUps (F0_DAE) |
| `capabilities` | string[] | YES | `IMPLEMENTED_IN_MANIFESTS` | Declared capabilities (see Section 3) |
| `agent_routes` | string[] | YES | `IMPLEMENTED_IN_MANIFESTS` | OpenClaw routes this FoundUp may invoke |
| `holo_collections` | string[] | NO | `IMPLEMENTED_IN_MANIFESTS` | HoloIndex collections this FoundUp reads |
| `data_namespace` | string | YES | `IMPLEMENTED_IN_MANIFESTS` | IndexedDB namespace: `idb_{foundup_id}`. Validated by `test_namespace_guardrail.py`. |
| `cabr_contract` | object | YES | `IMPLEMENTED_IN_MANIFESTS` | CABR 3V validation rules |
| `category` | string | NO | `IMPLEMENTED_IN_MANIFESTS` | FoundUp category (e.g. `marketplace`, `media`). Present in actual manifests, used by catalog export. |
| `launch_readiness` | enum | NO | `IMPLEMENTED_IN_MANIFESTS` | One of: `ready`, `conditional`, `discoverable_only`. Validated by `shell_core.py`. |
| `min_shell_version` | semver | NO | `SPECIFIED_NOT_IMPLEMENTED` | Minimum compatible shell version. Not present in any current manifest. |
| `owner_id` | string | YES | `IMPLEMENTED_IN_MANIFESTS` | FoundUp creator/owner identifier |
| `token_symbol` | string | YES | `IMPLEMENTED_IN_MANIFESTS` | Token symbol per `TokenTerms` model |
| `created_at` | ISO 8601 | YES | `IMPLEMENTED_IN_MANIFESTS` | Creation timestamp |
| `signature` | hex string | YES | `SPECIFIED_NOT_IMPLEMENTED` | HMAC-SHA256 of manifest body. All current manifests have `signature: ""`. No enforcement code exists in `shell_core.py`. See Section 6. |

### 2.3 Lifecycle Stage — Dual Stage Sets

> **WSP 97 note**: Two overlapping stage vocabularies exist in the codebase.

| Stage Set | Values | Source | Where Used |
|-----------|--------|--------|------------|
| **Exfoliation Protocol** | `incubating`, `proto`, `externalized`, `federated` | Architecture spec, manifest schema | `foundup_manifest.json`, `gotjunk/tests/test_manifest.py` |
| **Simulator** | `idea`, `poc`, `soft-proto`, `proto`, `mvp`, `launch` | `state_store.py` (FoundUpTile), cube_view | Simulator runtime, SSE server |

`shell_core.py` VALID_STAGES accepts **both sets** (union). The gotjunk manifest test validates only the Exfoliation set. Simulator `state_store.py` uses `PoC / Proto / MVP` (capitalized). The canonical manifest schema uses the Exfoliation set; simulator stages appear only in the state overlay layer.

### 2.4 `foundup_id` Format — Specification vs Implementation

> **WSP 97 `SPECIFIED_NOT_IMPLEMENTED`**: The original plan specified deterministic IDs via `sha256(name:owner_id:created_at)[:16]` (16-char hex). Actual manifests use human-readable slugs (`gotjunk_001`, `kosei`). `shell_core.py` validates minimum 3 characters but does not enforce SHA256 format. The deterministic generation function is not implemented in any code path.

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

> **WSP 97 `SPECIFIED_NOT_IMPLEMENTED`**: The signing contract below is an architectural specification. No manifest in the repo has a populated `signature` field (all are `""`). `shell_core.py` does not verify signatures. `skill_manifest_guard.py` exists in `wre_core` for WRE skill manifests but has not been extended to FoundUp manifests. Signing is a prerequisite for production deployment but is not enforced today.

Manifests are specified to be signed using HMAC-SHA256, extending the existing `skill_manifest_guard.py` pattern.

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

The shell is specified to verify manifest signatures at:
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

The following is the **actual** `modules/foundups/gotjunk/foundup_manifest.json` (as of 2026-04-21):

```json
{
  "$schema": "https://foundups.org/schemas/foundup-manifest/v1.json",
  "foundup_id": "gotjunk_001",
  "name": "GotJunk",
  "version": "0.3.0",
  "description": "Peer-to-peer marketplace for selling unwanted items. List it, price it, move it.",
  "tagline": "Turn your junk into someone's treasure",
  "tier": "F0_DAE",
  "lifecycle_stage": "proto",
  "entry_url": "https://gotjunk-56566376153.us-west1.run.app/",
  "routing_prefix": "/f/gotjunk_001",
  "icon_url": "frontend/public/icon-192.svg",
  "required_subscription_tier": "free",
  "is_invite_only": true,
  "capabilities": ["search", "agents_basic", "marketplace", "offline"],
  "agent_routes": ["openclaw_query", "openclaw_task"],
  "holo_collections": [],
  "data_namespace": "idb_gotjunk_001",
  "cabr_contract": {
    "v1_gate": "default",
    "v2_proof": "default",
    "v3_score_min": 0.5
  },
  "owner_id": "012",
  "token_symbol": "JUNK",
  "category": "marketplace",
  "launch_readiness": "conditional",
  "created_at": "2026-03-01T00:00:00Z",
  "signature": ""
}
```

> **Note**: `signature` is empty (`SPECIFIED_NOT_IMPLEMENTED`). `category` and `launch_readiness` are fields present in deployed manifests but were missing from the original schema spec (now added in Section 2.2). `v2_proof` is `"default"` (not `"marketplace_proof"` as the original spec example showed). `holo_collections` is empty (HoloIndex integration not yet wired for gotjunk).

---

## 9. Validation Rules

The shell validates manifests at load time. Any validation failure blocks the FoundUp from loading.

| Rule | Check | Implementation Status |
|------|-------|----------------------|
| Required fields present | All fields marked YES in Section 2.2 | `IMPLEMENTED_IN_TESTS` (`shell_core.py` validate_manifest) |
| `foundup_id` format | Min 3 chars, lowercase alphanumeric + underscore | `IMPLEMENTED_IN_TESTS` (`shell_core.py`) |
| `version` format | Valid semver | `ARCHITECTURAL_CONTRACT` (not validated at runtime) |
| `tier` value | One of `DAOTier` enum values (F0_DAE through F5_SYSTEMIC) | `IMPLEMENTED_IN_TESTS` (`shell_core.py` VALID_TIERS) |
| `lifecycle_stage` value | Exfoliation set + simulator set (see Section 2.3) | `IMPLEMENTED_IN_TESTS` (`shell_core.py` VALID_STAGES) |
| `required_subscription_tier` value | One of: `free, starter, basic, plus, pro, enterprise` | `IMPLEMENTED_IN_MANIFESTS` (matches `subscription_tiers.py` TIERS dict) |
| `launch_readiness` value | One of: `ready, conditional, discoverable_only` | `IMPLEMENTED_IN_TESTS` (`shell_core.py` VALID_READINESS) |
| `capabilities` values | All entries in capabilities registry (Section 3) | `ARCHITECTURAL_CONTRACT` (not validated at runtime) |
| `agent_routes` values | All entries are known OpenClaw routes | `ARCHITECTURAL_CONTRACT` (not validated at runtime) |
| `data_namespace` format | Must be `idb_{foundup_id}` | `IMPLEMENTED_IN_TESTS` (`test_namespace_guardrail.py`) |
| `routing_prefix` format | Must be `/f/{foundup_id}` | `IMPLEMENTED_IN_TESTS` (`test_namespace_guardrail.py`, WSP 104) |
| `cabr_contract.v3_score_min` | Number between 0.0 and 1.0 | `ARCHITECTURAL_CONTRACT` (not validated at runtime) |
| `signature` valid | HMAC-SHA256 verification passes | `SPECIFIED_NOT_IMPLEMENTED` (see Section 6) |
| `description` length | Max 280 characters | `ARCHITECTURAL_CONTRACT` (not validated at runtime) |
| `tagline` length | Max 80 characters | `ARCHITECTURAL_CONTRACT` (not validated at runtime) |

---

## 10. Manifest Lifecycle

```
1. AUTHOR: FoundUp developer creates manifest
2. SIGN: Manifest signed with project secret key  [SPECIFIED_NOT_IMPLEMENTED]
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

---

## 12. WSP 97 Truth Summary (Reconciliation 2026-04-21)

| Area | Finding | Marker |
|------|---------|--------|
| `foundup_id` generation | Spec said SHA256 hash; actual manifests use human-readable slugs | `SPECIFIED_NOT_IMPLEMENTED` |
| HMAC signing | Spec says required; all manifests have `signature: ""`, no enforcement | `SPECIFIED_NOT_IMPLEMENTED` |
| `min_shell_version` | Spec says optional; no manifest includes it | `SPECIFIED_NOT_IMPLEMENTED` |
| `required_subscription_tier` enum | Spec said `angel, ultimate`; code has `basic, enterprise` | **Corrected** in this reconciliation |
| `category` field | Present in manifests, missing from spec | **Added** in this reconciliation |
| `launch_readiness` field | Present in manifests + shell_core, missing from spec | **Added** in this reconciliation |
| `lifecycle_stage` dual sets | Exfoliation + simulator stages coexist in `shell_core.py` | **Documented** in Section 2.3 |
| `tier` enum | Matches `DAOTier` in `smartdao_spawning.py` | Aligned |
| Shell contract consistency | `PFMALL_SHELL_CONTRACT.md` consistent with manifest schema | Verified |
| Namespace guardrail | `test_namespace_guardrail.py` enforces `routing_prefix` and `data_namespace` | `IMPLEMENTED_IN_TESTS` |
