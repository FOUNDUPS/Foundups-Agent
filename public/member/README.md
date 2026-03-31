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
|- css/member.css
|- mall-catalog.json
|- README.md
|- INTERFACE.md
|- ModLog.md
```

## Current UX

- swipe or scroll horizontally through FoundUps
- tap a card to open its shell handoff sheet
- use the Red Dog icon to open concierge context
- invite codes remain available from the Red Dog sheet

## Out of Scope

- direct tenant execution
- wallet flows
- `/f/{foundup_id}` domain routing
- restoring the legacy member shell

## Source Of Truth

The current catalog is a Firebase-hosted static seed at:

```text
/member/mall-catalog.json
```

This keeps the live site compatible with Firebase hosting while the deeper p.fMALL transport surfaces continue maturing elsewhere in the repo.

---

*Last Updated: 2026-03-31*
