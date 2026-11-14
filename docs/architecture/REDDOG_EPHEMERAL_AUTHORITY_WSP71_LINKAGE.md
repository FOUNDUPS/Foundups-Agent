# RedDog Ephemeral Authority — WSP 71 Linkage Note

**Status:** DOCS_ONLY / SPECIFIED_NOT_IMPLEMENTED
**Canonical policy:** `WSP_framework/src/WSP_71_Secrets_Management_Protocol.md`
**Detailed architecture:** `docs/architecture/REDDOG_EPHEMERAL_AUTHORITY_WORKER_ROUTING.md`
**Implementation tracking:** GitHub issue #1584

This note records the intended WSP 71 linkage without creating a second security protocol.

WSP 71 remains the canonical secrets/security policy. The RedDog architecture document defines the derived implementation model for autonomous workers: workers have identity, work orders carry bounded authority, and durable credentials do not move into worker prompts, model context, inherited environments, logs, AgentDB, HoloIndex, or normal IPC.

The target implementation prefers gateway/proxy execution in which the worker never receives the underlying credential. Where a provider requires temporary credential delivery, authority must be task-scoped, resource/action-scoped, non-delegable, auditable, short-lived, and bounded by use count. Sensitive writes should expire on the earliest applicable condition, including single use, TTL expiry, work-order completion, worker lease loss, runtime-binding expiry, policy failure, or orchestrator revocation.

This derived document does not override WSP 71. If any derived architecture conflicts with the numbered WSP, `WSP_framework/src/WSP_71_Secrets_Management_Protocol.md` controls. Per WSP 81, `WSP_knowledge/src/` is the governed backup/mirror of canonical WSPs, not a second authority.

A future governed WSP 71 edit should add only a short reciprocal reference to `docs/architecture/REDDOG_EPHEMERAL_AUTHORITY_WORKER_ROUTING.md`; the detailed mechanics should remain in the architecture document to avoid duplicating policy text.
