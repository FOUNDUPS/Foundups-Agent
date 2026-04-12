# FoundUp AI Hooks and DAEmon Surface Contract

**Status**: Canonical (FoundUp-local)  
**Version**: 1.0.0  
**Date**: 2026-04-11  
**Owner**: 0102  
**Scope**: Documentation and enforcement hooks only — not pfMALL runtime implementation in this slice  

---

## Purpose

Every FoundUp that declares itself with `module.json` and/or `foundup_manifest.json` must document a **small, stable architectural contract** so tenant routing, AI-facing surfaces, and DAEmon observability are never implicit or forgotten.

**Canonical backing standards (do not duplicate here):**

| Standard | Role |
|----------|------|
| **WSP 91** — `WSP_knowledge/src/WSP_91_DAEMON_Observability_Protocol.md` | DAEMON observability: logs, traces, metrics, health checks, decision-path visibility |
| **WSP 104** — `WSP_knowledge/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md` | Route family `/f/{foundup_id}`, app mount, tenant isolation, data/cache namespaces |

This file is the **FoundUp-local** contract: what each tenant must say in its own README (see `FOUNDUP_TEMPLATE.md`). It does **not** replace WSP 91 or WSP 104.

---

## 1. Route surface (WSP 104)

Each FoundUp MUST document:

| Item | Requirement |
|------|----------------|
| **`foundup_id`** | Stable tenant key; aligns with manifest when `foundup_manifest.json` exists |
| **`routing_prefix`** | Canonical `/f/{foundup_id}` |
| **Landing route** | `/f/{foundup_id}` — entry / trust / about surface |
| **App route** | `/f/{foundup_id}/app` — tenant app runtime root |
| **Deep links** | `/f/{foundup_id}/app/{path...}` — tenant-internal only; must not claim shell-owned root families |

Optional future subpaths under the FoundUp family MUST remain subordinate to WSP 104 reserved meanings (landing vs app).

---

## 2. App mount namespace

Document where the tenant app is mounted in the shell contract (`/f/{foundup_id}/app`). If the product is not yet hosted inside pfMALL, state the **declared** shell mount anyway and note the current dev/prod entry separately. This preserves alignment when the shell attaches the bundle.

---

## 3. AI hook surface (contract, not implementation)

FoundUps MUST name the **minimum documented hooks or equivalent capability bridges** so autonomous agents and shell orchestration have a consistent vocabulary. Implementations may be staged; the **documentation obligation** is immediate.

Minimum table (names are semantic; APIs may map 1:1 or via adapters):

| Hook / concept | Intent |
|----------------|--------|
| `get_status` | Short operational snapshot |
| `get_context` | Bounded context for a decision or turn |
| `navigate` | Change surface or route within tenant bounds |
| `launch_capability` | Invoke a declared capability from catalog/manifest |
| Shell handoff / return | Delegate to shell or return from external tool/session |

Do not claim runtime features that do not exist; use explicit **“planned / not implemented”** where needed while still documenting the contract row.

---

## 4. DAEmon output surface (WSP 91 alignment)

Each FoundUp with autonomous or long-running workers MUST document the **observable outputs** operators and agents rely on. Align with WSP 91’s three pillars and health expectations.

Minimum documented outputs:

| Output | Notes |
|--------|--------|
| Health status | e.g. healthy / degraded / critical |
| Last action | Last completed or attempted operation |
| Error state | Active error classification or clear “none” |
| Recommended next action | Operator or agent hint from the worker |
| Queue / work state | If applicable; else “N/A” with rationale |
| Telemetry namespace | Scopes for metrics/logs/traces by `foundup_id` / `data_namespace` |

---

## 5. Data and telemetry namespace (WSP 104)

Document:

| Field | Requirement |
|-------|-------------|
| `foundup_id` | Same key as routing |
| `data_namespace` | e.g. `idb_{foundup_id}` or equivalent from manifest |
| Tenant bounds | Expectation that cache, storage, and telemetry do not bleed across tenants |

See also: `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md`, `PFMALL_DATA_ISOLATION_MODEL.md`.

---

## 6. Enforcement

- **Template**: `FOUNDUP_TEMPLATE.md` — required README sections.  
- **Tests**: `modules/foundups/tests/test_foundup_ai_hooks_daemon_contract_compliance.py` — fails on missing headings, WSP 91/104 literals, or canonical doc pointer.

---

## WSP references

- **WSP 91** — DAEMON observability standard (mandatory backing for DAEmon outputs).  
- **WSP 104** — FoundUp route namespace and tenant isolation (mandatory backing for routes and data bounds).

---

*0102 pArtifact note: This contract exists so growth-by-registry stays safe without copy-pasting full WSP text into every tenant README.*
