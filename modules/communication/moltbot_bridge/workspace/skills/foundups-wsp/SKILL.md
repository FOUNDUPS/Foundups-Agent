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
