# Kosei AI Systems FoundUp

**Domain**: `foundups/kosei`
**Type**: FoundUp instance under `modules/foundups/`
**Status**: Scaffold (Phase 0)

---

## Overview

Kosei AI Systems is the **business layer** for AI-powered content automation services. It handles the audit funnel, onboarding, client workspace, admin/operator workspace, trial management, support, and white-label configuration.

Kosei is the service orchestration and commercial surface. It is **not** the content engine itself.

## Core Responsibilities

| Responsibility | Description |
|---------------|-------------|
| **Audit funnel** | Lead capture, content audit, gap analysis, recommendation engine |
| **Onboarding** | Client workspace provisioning, account setup, preference capture |
| **Service orchestration** | Route client intent to correct automation tools and workflows |
| **Client workspace** | Dashboard for content review, approval, scheduling, analytics |
| **Admin/operator workspace** | 012/agent management console, client overview, billing |
| **Trial + support** | Trial provisioning, support ticket routing, escalation |
| **White-label config** | Branding, domain, theme, and feature toggles per client |

## Boundary: Kosei vs AutoPost

| Concern | Kosei AI Systems | AutoPost |
|---------|-----------------|----------|
| **What** | Business/service layer | Content creation engine |
| **Scope** | Audit, onboard, orchestrate, bill | Capture, process, publish |
| **Repo** | `modules/foundups/kosei/` | External: `O:\repos\AutoPost` (separate repo) |
| **Users** | Clients, operators, agents | End users (direct tool) |
| **Relationship** | Consumes AutoPost as a service | Independent open-source tool |
| **pAVS role** | FoundUp (commercial entity) | Product/tool (may become FoundUp later) |

AutoPost is an **external sibling dependency**. Kosei orchestrates it but does not contain it. AutoPost may be consumed by Kosei clients, but AutoPost also operates independently as a standalone tool.

## Integration Points

```
Client -> Kosei Audit Funnel -> Content Gap Analysis
                              -> Service Recommendation
                              -> Onboarding Flow
                              -> Client Workspace (approve, schedule, review)
                                   |
                                   v
                              AutoPost (external) -> capture -> process -> publish
                                   |
                                   v
                              Analytics -> Client Dashboard
```

## WSP Compliance

| WSP | Concern |
|-----|---------|
| WSP 3 | Domain placement: `foundups/kosei` |
| WSP 11 | Interface contract: `INTERFACE.md` |
| WSP 22 | Change log: `ModLog.md` |
| WSP 49 | Module structure: README, INTERFACE, ROADMAP, tests |
| WSP 72 | Module independence: Kosei does not embed AutoPost |

---

## Route Namespace

Canonical contract: `modules/foundups/docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`. Routing follows **WSP 104** (`/f/{foundup_id}`).

| Field | Value |
|-------|-------|
| `foundup_id` | `kosei` |
| `routing_prefix` | `/f/kosei` |
| Landing route | `/f/kosei` |
| App mount | `/f/kosei/app` |

---

## App Mount

Shell contract: **`/f/kosei/app`**. App bundle deployed at `https://foundupscom.web.app/kosei/app/`.

**Embedding status** (verified 2026-04-13): **APP READY**

In-browser iframe test confirmed: Kosei app successfully renders inside the FoundUps shell iframe. CSP `frame-ancestors` takes precedence over `X-Frame-Options: DENY` in modern browsers as per W3C CSP3 spec.

**entry_url**: `https://foundupscom.web.app/kosei/app/` (restored in BX5)

**Remaining blockers** (P2):
- Landing page (`/kosei/`) not deployed — source needs cleanup

---

## AI Capability Hooks

Contract surface (implementation staged): `get_status`, `get_context`, `navigate`, `launch_capability`, shell handoff/return — see `FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`.

---

## DAEmon Outputs

Per **WSP 91** (when DAEMON workers attach): health status, last action, error state, recommended next action, queue/work state (audit funnel, client workspace, trial management), telemetry scoped by `foundup_id` / `data_namespace`.

---

## Data / Telemetry Namespace

| Field | Value |
|-------|-------|
| `foundup_id` | `kosei` |
| `data_namespace` | `idb_kosei` |
| Tenant bounds | Client data, audit records, workspace state — all tenant-scoped per WSP 104 |

---

## WSP References

- **WSP 91** — DAEMON observability (`WSP_knowledge/src/WSP_91_DAEMON_Observability_Protocol.md`)
- **WSP 104** — FoundUp route namespace (`WSP_knowledge/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md`)
