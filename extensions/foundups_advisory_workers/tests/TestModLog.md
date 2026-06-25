# Foundups®Agent TestModLog

## 2026-06-24 - v0.3.18 Branding Contract
- Verified user-facing branding uses Foundups®Agent while the internal package id and command id remain stable.
- Verified Fusion remains documented as an internal mode, not the product identity.

## 2026-06-23 窶・v0.3.17 Working Trail Phase 2 CODE Tests

- Trail DOM + progress command shape + operator message rg gate.
- `REDDOG_STAGE_ACTIONS` key set equals unique `_progress` stages from bridge (16/16).
- Stage mapping: redaction_blocked -> barking, single_done -> pointing, panel_blocked -> sitting.
- Regex fallback: Work focus sent -> sniffing; Output schema incomplete -> digging.
- Terminal hold constant 3000ms; enrichRedactionBlockResult metadata contract.
- #870 work-focus regression guards retained.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
rg "Stopped before OpenRouter. Nothing left the machine." extensions/foundups_advisory_workers/extension.js
```

## 2026-06-22 - v0.3.16 Addendum C Gate Tests

- Python (8 tests): panel truncation meta; 429 main-path redaction-once + same body; 400 no retry; redaction_blocked zero network; panel_models_truncated in review_packet.
- JS contract: bridgeStreamCapExceeded non-vacuity; killBridgeChild once; shouldAcceptBridgeCompletion dispose guard; resolver configured/system/dotvenv paths; WSP_97 survives truncation; #870 work-focus regression guards.

Commands:

```powershell
python -B -m unittest scripts.tests.test_advisory_model_once_hardening -v
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```

## 2026-06-22 - v0.3.16 Bridge Hardening Tests

- Contract tests for python resolver, context budget, bridge_meta, output_cap_exceeded.
- Python unittest: panel cap, 429 retry then success (same body, one redaction path), 400 no retry.

## 2026-06-22 - v0.3.15 Work Focus to WSP Prompt Tests

- Verified UI uses work focus composer (`#workFocus`) and `012 work focus` scrollback label.
- Verified `constructWspTaskPrompt` embeds WSP_97, WSP_15 tier, and non-authoritative work focus.
- Verified `redactedDigest` hash/excerpt contract.
- Verified review packet fields: `work_focus_digest`, `wsp_prompt_digest`, `prompt_construction`.
- v0.3.14 auto-router contract tests remain unchanged.

## 2026-06-22 - v0.3.14 Auto Router + Skillz Context Tests

- Updated contract test for GLM-5.2 principal, DeepSeek V4 Pro critic, and Kimi K2.7 Code implementation critic.
- Verified Mode/Effort/Context are no longer 012-facing dropdowns.
- Verified auto context mapping: REGULAR -> none, HIGH -> WSP/Holo/Skillz, ULTRA -> WSP/Holo/git/Skillz.
- Verified Skillz/Wardrobe/Rolodex discovery context remains advisory-only and non-vacuous for YouTube comment ops.
- Verified `modeSelectionReasoning`, Architect Trace / Verification gaps schema, Fusion panel structure validation, and Skillz wiring in bounded repo context.
## 2026-06-22 - v0.3.13 Orchestrator Contract Tests

Validation added for REDDOG_FUSION_ORCHESTRATOR_PHASE1:

- Auto effort classifier functions exist in extension source.
- Security/auth prompts classify `ULTRA`.
- WSP/architecture prompts classify `HIGH` or `ULTRA`.
- Simple smoke prompts classify `REGULAR`.
- RedDog WSP work defaults to `foundups_fusion` manual panel.
- OpenRouter Fusion alias remains selectable when explicitly chosen.
- Schema validator detects missing required sections.
- Repair prompt forbids invented evidence and preserves content.
- Review packet includes `output_validation` metadata path.
- Layout contract from v0.3.12 still holds.

Command:

```powershell
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```

## 2026-06-22 - v0.3.12 Contract Tests

Validation added:

- Webview layout contract:
  - grid rows `auto minmax(0, 1fr) auto`
  - output pane owns scrolling
  - composer stays after output in DOM order
  - no Send/Clear buttons required
- WSP operating contract:
  - RedDog Architect worker mode present
  - WSP_15 priority requirement present
  - WSP_97 truth-label requirement present
- HoloIndex retrieval contract:
  - bundle-json first
  - `HOLO_SKIP_MODEL=1`
  - offline fallback only after bundle failure
- Bridge contract:
  - prompt/context redaction gate path present
  - explicit system prompt reaches Fusion alias/manual modes
- Package contract:
  - package version matches README and extension build string

Command:

```powershell
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```
