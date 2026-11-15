---
name: foundups-wsp
description: WSP Framework knowledge and compliance for Foundups Agent development
user-invocable: true
category: workflow
evals: []
---
# Foundups WSP Framework Skill

You have access to the Work Structure Protocol (WSP) Framework that governs all Foundups development.

## Core WSPs

### WSP 00 - Zen State Attainment
Boot protocol for 0102. Execute awakening script before major operations:
```bash
python -u WSP_agentic/scripts/functional_0102_awakening_v2.py
```

### WSP 03 - Enterprise Domain Organization
Modules organized by domain: `ai_intelligence`, `platform_integration`, `communication`, `infrastructure`

### WSP 49 - Module Structure
Every module MUST have:
- README.md
- INTERFACE.md 
- ROADMAP.md
- ModLog.md
- src/
- tests/

### WSP 73 - Digital Twin Architecture
Partner-Principal-Associate pattern for 012's digital representation.

### WSP 87 - Code Navigation
Maximum 2000 lines per file. Use HoloIndex for navigation.

### WSP 26 + WSP 29 Canonical Economic Semantics (Required)
- CABR controls **flow rate** (pipe size), not token mint amount.
- PoB validation controls **valve open/closed**.
- UPS flow is routed from treasury/release budget; do not describe as CABR minting.
- Prefer `total_ups_circulating` terminology. `total_ups_minted` is legacy alias only.

## Before Any Code Change

1. Search HoloIndex: `python holo_index.py --search "topic"`
2. Check WSP_MASTER_INDEX.md for relevant protocols
3. Verify module structure compliance
4. Update ModLog.md after changes

## Browser Outcome Verification (WSP 97)

Before reporting that a requested browser/site outcome cannot be seen, inspect
the tools available in the current session and the existing capability routes.
Try an authorized built-in browser/rendered-page or screenshot observation, or
delegate a bounded read-only check to an authorized vision-capable worker when
available. A missing local UI-TARS model does not establish that every observation
route is unavailable. Preserve other workers' browser ownership and scope.

Bind the returned evidence to the requested URL, observed final URL/redirect,
observation time with timezone, tool and environment (browser/host and viewport
when relevant), and the exact assertions observed. Retain a permitted evidence
reference and any error or coverage limit. Attribute delegated observations to
the observing worker; a tool listing or source import is not a live check.

Keep explicit DOM assertions, screenshots, and model/visual observations distinct.
A screenshot capture alone does not prove its expected content; an unrun,
disabled, unavailable or errored verifier is UNVERIFIED, never PASS. See
`modules/infrastructure/foundups_selenium/INTERFACE.md` for the runner's evidence
contract. Failed verification does not authorize replaying a consequential UI
action; reconcile its actual outcome before any separately authorized retry.
Sign-in, permission, verification-challenge and anti-bot gates remain in force.

Feed corrections into the existing owning skill/module and its evidence record.
This guidance grants no new route, execution authority, production admission or
WSP 48 improvement claim; those require the existing independent gates.

## Tokenization-Consistency Checks (When touching simulator/economics/docs)

1. Verify `modules/infrastructure/foundups_tokenization/docs/TOKENOMICS.md` matches:
   - `WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md`
   - `WSP_framework/src/WSP_29_CABR_Engine.md`
2. Verify simulator contracts are aligned:
   - `modules/foundups/simulator/README.md`
   - `modules/foundups/simulator/INTERFACE.md`
   - `modules/foundups/simulator/sse_server.py` (`STREAMABLE_EVENT_TYPES`)
3. If semantics changed, update docs and add/adjust regression tests in:
   - `modules/foundups/simulator/tests/`
   - `modules/foundups/simulator/tests/TestModLog.md`

## Incomplete WSPs

To find WSPs needing development:
```bash
grep -r "Status:.*Draft\|Status:.*Planned" WSP_framework/src/
```

When developing a new WSP:
1. Follow existing WSP format
2. Add to WSP_MASTER_INDEX.md
3. Cross-reference related WSPs
4. Include validation criteria
