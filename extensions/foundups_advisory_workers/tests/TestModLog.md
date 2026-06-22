# FoundUps Fusion Worker TestModLog

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
