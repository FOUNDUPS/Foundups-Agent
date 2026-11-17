---
name: reddog-correspondence-state
description: Apply the canonical Red Dog correspondence continuity contract for provider-delta sync, stable ask accounting, privacy-bounded runtime persistence, and fail-closed freshness.
---

# Red Dog Correspondence State

Canonical Skillz: `modules/communication/moltbot_bridge/skillz/reddog_correspondence_state/SKILLz.md`.

Apply that file as the source of truth.

Key invariants:

- Provider systems remain transaction truth.
- Native runtime correspondence state is a rebuildable continuity projection.
- One scope = stakeholder/organization × topic/ask.
- Use stable ask IDs and explicit ask states.
- Compare provider watermark before using cached state.
- On changed/unknown/stale state, reconcile only the provider delta needed for the scope.
- Never persist raw mailbox bodies, full recipient dumps, credentials, or hidden reasoning.
- Cached state never authorizes a send.
- Run current routing + `reddog_recipient_preflight` immediately before send-capable actions.
- Do not create a correspondence Moshpit or parallel contact database.
