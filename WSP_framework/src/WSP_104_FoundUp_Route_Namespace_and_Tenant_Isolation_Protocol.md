# WSP 104: FoundUp Route Namespace and Tenant Isolation Protocol

**Status**: ACTIVE
**Version**: 1.0
**Date**: 2026-04-10
**Author**: 0102 (architect)
**Dependencies**: WSP 3 (Domain Organization), WSP 49 (Structure), WSP 57 (Naming), WSP 71 (Secrets), WSP 78 (Database Scaling), WSP 83 (Documentation Tree Attachment), WSP 85 (Root Directory Protection), WSP 97 (Execution Prompting), WSP 98 (Mesh-Native Architecture), WSP 102 (FoundUps Web Design)

---

## Executive Summary

WSP 104 establishes the canonical growth contract for hosting many FoundUps on one FoundUps shell without route collisions, root pollution, or tenant bleed.

It answers the concrete scaling question:

> Can the system add 100 more FoundUps safely?

**Yes, but only if growth happens by registry and namespace, not by root-page sprawl.**

The core rule is:

- the shell owns discovery and route families
- each FoundUp owns exactly one stable namespace under `/f/{foundup_id}`
- tenant apps, data, caches, and runtime scopes stay isolated to that namespace
- no FoundUp may claim arbitrary root pages

This protocol consolidates route/runtime truths that were previously split across shell, routing, manifest, and data-isolation architecture notes.

Companion documents:
- `modules/foundups/docs/PFMALL_SHELL_CONTRACT.md`
- `modules/foundups/docs/PFMALL_ROUTING_DISCOVERY_MODEL.md`
- `modules/foundups/docs/PFMALL_FOUNDUP_MANIFEST_SCHEMA.md`
- `modules/foundups/docs/PFMALL_DATA_ISOLATION_MODEL.md`

---

## 1. Purpose

Define the route, namespace, asset, and tenant-isolation rules required for p.fMALL to scale from a handful of FoundUps to 100+ FoundUps without:

- root-level page collisions
- ambiguous route ownership
- shared storage contamination
- service-worker scope bleed
- tenant runtime confusion between shell, landing, and app surfaces

This WSP governs **growth architecture**, not a single FoundUp implementation.

---

## 2. Scope

This protocol applies to:

- p.fMALL shell routes
- FoundUp route families
- `foundup_manifest.json` route and namespace fields
- tenant app mount points
- FoundUp data namespaces
- service-worker and cache scope for in-shell PWAs
- onboarding additional FoundUps into catalog and routing

This protocol does **not** define:

- FoundUp token economics
- detailed landing-page UI
- PWA product behavior
- external repo federation mechanics beyond route/runtime isolation

---

## 3. Canonical Namespace Model

### 3.1 Shell-Owned Route Families

The shell owns the global browse/discovery experience and the root route families reserved for platform use.

Current/allowed shell-owned families:

- `/member/` - active p.fMALL shell and member-facing browse surface
- `/discover` - reserved canonical browse route family
- `/search` - reserved shell search family
- `/wallet` - reserved shell wallet/entitlement family
- `/settings` - reserved shell preferences family
- `/f/` - reserved FoundUp namespace family managed by the shell

### 3.2 FoundUp-Owned Route Family

Every FoundUp receives exactly one canonical namespace:

```text
/f/{foundup_id}
```

That namespace is the only route family a FoundUp may own inside the shared host.

### 3.3 Reserved Subroutes Inside the FoundUp Family

Each FoundUp namespace reserves these meanings:

- `/f/{foundup_id}` - FoundUp landing / about / trust / entry surface
- `/f/{foundup_id}/app` - tenant app runtime root
- `/f/{foundup_id}/app/{path...}` - tenant-internal deep links

Additional subroutes may exist later, but they must not redefine the meanings above.

---

## 4. Required Route Invariants

### 4.1 `foundup_id`

`foundup_id` is the permanent tenant identity key.

Rules:

- must be globally unique within the FoundUps registry
- must be stable once published
- must be safe for URLs, storage namespaces, and cache keys
- must not be recycled for a different FoundUp

### 4.2 `routing_prefix`

The manifest `routing_prefix` is canonical and must equal:

```text
/f/{foundup_id}
```

No FoundUp may declare:

- a root-level prefix like `/gotjunk`
- a shared prefix like `/apps`
- another FoundUp's prefix
- a prefix outside `/f/`

### 4.3 Landing and App Are Separate Layers

The route contract is:

```text
/f/{foundup_id}          -> landing / about / trust / token / launch surface
/f/{foundup_id}/app      -> product runtime mount
```

This separation is mandatory because the landing surface and the app runtime are different responsibilities:

- landing = trust, token, Discord, readiness, app launch
- app = actual tenant product surface

---

## 5. Transitional Bridge Rule

Current deployment truth may still use a bridge such as:

```text
/f/{foundup_id} -> /member/foundup.html?id={foundup_id}
```

This is allowed only as a **transitional adapter**, not as the permanent architecture.

Transitional bridge requirements:

- the canonical visible route family remains `/f/{foundup_id}`
- the bridge must preserve `foundup_id`
- the bridge must not introduce tenant-specific root pages
- the bridge must not bypass shell validation or namespace checks

The transition layer exists to preserve canonical routes while the shell-owned FoundUp landing continues to harden.

---

## 6. Tenant Runtime Isolation Rules

### 6.1 Asset Scope

A FoundUp app must not sprawl across shared root pages.

Allowed app bundle strategies:

- relative app bundle loaded through the FoundUp namespace contract
- absolute HTTPS tenant entry URL
- shell-mounted app runtime under `/f/{foundup_id}/app`

Disallowed:

- arbitrary root-level tenant HTML pages
- tenant-specific ad hoc rewrites outside `/f/{foundup_id}`
- multiple unrelated route families for one FoundUp

### 6.2 Data Namespace

Each FoundUp must declare:

```text
data_namespace = idb_{foundup_id}
```

This namespace is required for:

- IndexedDB separation
- cached state isolation
- future quota assignment

No FoundUp may read or write another FoundUp's namespace.

### 6.3 Service Worker Scope

If a FoundUp app uses a service worker while hosted under the shell, its scope must be limited to:

```text
/f/{foundup_id}/app/
```

The shell service worker must not grant tenant apps authority over unrelated routes.

### 6.4 Cache Namespace

Tenant runtime caches must be prefixed by `foundup_id`.

Examples:

- `cache_gotjunk_001_shell_bridge`
- `cache_gotjunk_001_app_static_v1`

This prevents cache poisoning and makes quota/cleanup tractable at 100+ FoundUps.

---

## 7. Shell vs Tenant Responsibility Split

### 7.1 Shell Owns

- discovery and browse
- route family registration
- manifest validation
- entitlement and launch gating
- shell navigation chrome
- cross-FoundUp search entry
- cross-tenant handoff rules

### 7.2 FoundUp Owns

- landing content specifics within its namespace
- product UI and business logic
- tenant-local storage and state
- tenant app routing under `/app`
- tenant-specific service worker and caches

### 7.3 Prohibited Mixed Ownership

The following are architectural violations:

- shell copying tenant product logic into global routes
- FoundUp bypassing shell route family and mounting at root
- multiple FoundUps sharing one runtime namespace
- a tenant service worker controlling shell routes

---

## 8. Registry-Driven Growth Rule

Scale happens by **registry growth**, not by custom page growth.

To add one more FoundUp, the system should need:

1. a unique `foundup_id`
2. a valid `foundup_manifest.json`
3. a catalog/registry entry
4. a canonical `routing_prefix`
5. isolated data/cache/runtime scopes

To add 100 more FoundUps, the system should repeat those same five steps 100 times.

If adding more FoundUps requires:

- new root HTML pages
- new one-off rewrites
- per-tenant shell hacks
- bespoke top-level directories under `public/`

then the architecture is violating this WSP.

---

## 9. Namespace Guardrails (Compliance Gate)

A FoundUp **must pass** the following namespace guardrails before onboarding to the registry, catalog, or any shell surface:

| Guardrail | Requirement |
|-----------|-------------|
| **Unique `foundup_id`** | Globally unique within the FoundUps registry; not recycled |
| **Unique `routing_prefix`** | Must equal `/f/{foundup_id}`; no root-level claims |
| **Unique `data_namespace`** | Must equal `idb_{foundup_id}`; no cross-tenant storage |
| **Canonical route shape** | Entry route is `/f/{foundup_id}` only |
| **Manifest/catalog consistency** | `foundup_manifest.json` fields match registry entry |
| **No root-level tenant routes** | No `/appname`, `/toolname`, or ad hoc rewrites outside `/f/` |

These guardrails are **normative**. A FoundUp that violates any guardrail is not WSP 104 compliant and must not be admitted.

Cross-references:
- WSP 98 (Mesh-Native Architecture): mesh-readiness requires WSP 104 compliance
- WSP_knowledge WSP 103 (FoundUp Federation Protocol): federation binding requires WSP 104 compliance
  - Note: framework WSP 103 is CLI Interface Standard; federation protocol is knowledge-tree only

---

## 10. Validation Checklist for Onboarding a FoundUp

Before a FoundUp is admitted to the shell catalog, validate:

- `foundup_id` is unique
- `routing_prefix == "/f/{foundup_id}"`
- `data_namespace == "idb_{foundup_id}"`
- app runtime does not claim a root-level route family
- any service worker scope is bounded to the tenant app path
- manifest fields and route values are internally coherent
- entry route preserves shell authority and tenant isolation

Optional but recommended:

- cache key prefix derived from `foundup_id`
- quota policy recorded for storage/network/agent usage
- telemetry attribution namespaced by `foundup_id`

---

## 11. Prohibited Patterns

The following patterns are explicitly banned:

1. **Root pollution**
   - creating `/autopost`, `/gotjunk`, `/fooapp` root pages for tenant apps

2. **Alias sprawl**
   - one FoundUp published under multiple route families without shell mediation

3. **Namespace collision**
   - two FoundUps sharing the same `foundup_id`, `routing_prefix`, or `data_namespace`

4. **Cross-tenant storage**
   - FoundUp A reading or writing FoundUp B data stores

5. **Unbounded worker scope**
   - tenant service workers or caches scoped beyond their app namespace

6. **Landing/app collapse**
   - making the tenant app runtime the only surface and skipping the FoundUp landing/trust layer by default

---

## 12. Growth Posture: 100+ FoundUps

This protocol is sufficient for 100+ FoundUps only if the following posture is maintained:

- one canonical route family per FoundUp
- one canonical identity key per FoundUp
- registry-driven onboarding
- isolated storage/cache/service-worker scopes
- shell-owned discovery and route orchestration

In other words:

```text
Scale = more manifests and more catalog entries
Scale != more root pages and more ad hoc rewrites
```

This is the core architectural answer to FoundUps Mall growth.

---

## 13. Implementation Notes for Current System

Current repo truths that align with this protocol:

- `firebase.json` already reserves `/f/**`
- `public/f/index.html` already acts as a route bridge
- `public/member/foundup.html` already acts as a landing/about entry surface
- `modules/foundups/gotjunk/foundup_manifest.json` already uses:
  - `foundup_id = gotjunk_001`
  - `routing_prefix = /f/gotjunk_001`
  - `data_namespace = idb_gotjunk_001`

Current gaps that remain after this WSP:

- make `/f/{foundup_id}` a first-class shell-owned landing route
- make `/f/{foundup_id}/app` the canonical app runtime mount
- validate manifest uniqueness at registry build time
- formalize tenant quota enforcement for many FoundUps

---

## 14. Compliance Summary

When in doubt, apply this operator:

```text
One FoundUp -> one foundup_id -> one /f/{foundup_id} family -> one isolated tenant runtime
```

If a proposed change breaks that chain, it violates WSP 104.

---

*WSP 104: FoundUps scale by namespace discipline, not by root sprawl.*
