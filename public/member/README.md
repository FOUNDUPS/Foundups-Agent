# FoundUPS Member Mall

**Status**: Invite-gated p.fMALL shell live
**Location**: `public/member/`

## Overview

`/member/` is no longer a placeholder member shell.

It is now the admitted-user Mall experience that sits behind the existing FoundUPS invite gateway:
- Clerk session check
- invite validation
- username claim
- then swipe into the Mall

The gateway is preserved. The change is the admitted state.

## Runtime Shape

```text
public/member/
|- index.html
|- foundup.html
|- css/member.css
|- mall-catalog.json
|- README.md
|- INTERFACE.md
|- ModLog.md
```

## Current UX

- swipe or scroll horizontally through FoundUps
- tap a card to navigate to its dedicated entry page (`foundup.html?id={foundup_id}`)
- entry page shows readiness posture, details, and what-happens-next copy
- use the Red Dog icon to open concierge context
- invite codes remain available from the Red Dog sheet

## Out of Scope

- direct tenant execution
- wallet flows
- `/f/{foundup_id}` domain routing
- restoring the legacy member shell

## Source Of Truth

`mall-catalog.json` is a **generated artifact**, not hand-maintained.

Canonical source: `modules/foundups/pfmall/` (manifests + presentation overrides).

Regenerate:
```bash
python -m modules.foundups.pfmall.member_catalog_export
```

This keeps the live site compatible with Firebase hosting while the deeper p.fMALL transport surfaces continue maturing elsewhere in the repo. Do not hand-edit `mall-catalog.json` — edit the source manifests or `member_presentation.py` instead, then regenerate.

---

*Last Updated: 2026-03-31*
