# FOUNDUPS_AGENT_EXTENSION_F0_SAFETY_PHASE1 — Audit

**Slice:** FOUNDUPS_AGENT_EXTENSION_BRANDING_AND_F0_SAFETY_PHASE1  
**Calibration:** DECISION_ONLY_DOCS + manifest  
**Base:** post-#874 `origin/main` (`51ba16dfb`)  
**Date:** 2026-06-24  
**Package id (unchanged):** `foundups-fusion-worker`

---

## 1. Manifest audit

| Field | Before | After (this slice) | Notes |
| --- | --- | --- | --- |
| `name` | `foundups-fusion-worker` | **unchanged** | Avoid breaking installs/settings |
| `displayName` | FoundUps Fusion Worker | **FoundUps Agent** | Product surface name |
| `description` | Fusion advisory worker | **WSP-guided advisory coding architect** | RedDog persona inside product |
| Command title | FoundUps Fusion: Open | **FoundUps Agent: Open RedDog** | Persona explicit |
| Configuration title | FoundUps Fusion Worker | **FoundUps Agent** | Settings namespace still `foundupsFusion.*` |
| `activationEvents` | `onCommand:foundupsFusion.open` | **unchanged** | Command id stable |
| Categories | Other | **unchanged** | No capability expansion |

**Deferred (follow-up slice):** webview header strings in `extension.js` still say "FoundUps Fusion" until `FOUNDUPS_AGENT_UI_LABELS_PHASE1`.

---

## 2. Capability matrix (current truth)

### Can do now

| Capability | Status | Boundary |
| --- | --- | --- |
| Read bounded repo context | OBSERVED | Extension-gathered packet only; no model filesystem access |
| HoloIndex / git diff context | OBSERVED | Tiered by WSP_15 classification; bundle-json first |
| Redaction-gated OpenRouter egress | OBSERVED | `advisory_model_once.py` + Fusion redaction gate |
| WSP_00 / WSP_97 / WSP_15 advisory reviews | OBSERVED | Schema validator + one repair pass |
| Skillz / OpenClaw / Hermes / WRE handoff **recommendations** | OBSERVED | Advisory text only |
| Review packet copy for 0102 | OBSERVED | Digests, not raw context |
| Working trail (v0.3.17) | OBSERVED | Progress/status separation; no execution |

### Cannot do now

| Capability | Status |
| --- | --- |
| Edit code directly | BLOCKED |
| Run arbitrary shell for the model | BLOCKED |
| Merge PRs | BLOCKED |
| Create repos | BLOCKED |
| Execute Skillz / OpenClaw / Hermes | BLOCKED |
| Mutate F0 (FoundUps-Agent repo) automatically | BLOCKED |
| Safe arbitrary-repo integration without audit | NEEDS_VERIFICATION |

---

## 3. F0 safety threat model

| Threat | Vector | Current control | Residual |
| --- | --- | --- | --- |
| Malicious prompt injection | 012 work focus or repo context steers model | WSP_97 labels; advisory-only; no tool execution | Model may still recommend unsafe actions in text |
| Malicious repo content | HoloIndex/git/editor context includes hostile text | Bounded caps; redaction gate; no auto-execution | INFERRED content can influence recommendations |
| `.env` / gitignored secret leakage | Context gather reads sensitive files | Redaction gate; no `.env` in prompt contract; git ls-files bounded | Host git/HoloIndex paths NEEDS_VERIFICATION per workspace |
| Extension host command execution | `cp.spawn` for bridge/context | Fixed scripts only; model cannot invoke | Bridge compromise out of scope |
| OpenRouter data egress | Prompt/context after redaction | Redaction before network; digests in packet | Provider trust boundary |
| Model-generated malware instructions | Advisory output | No auto-run; 012 sovereign review | Human must not paste-run blindly |
| Accidental F0 mutation | Extension writes repo | **No write path in extension** | Other Cursor tools out of scope |
| Worm / viral self-propagation | Auto-install, hooks, spread | No auto-install; no hook writes; no dispatch | Future intake mode must preserve gates |

---

## 4. Required safeguards (documented)

- Advisory-only by default  
- Redaction before network  
- No `.env` / gitignored secret ingestion by design intent  
- No automatic writes from extension  
- No automatic shell execution from model output  
- No auto-install hooks  
- No repo mutation without WRE-governed handoff  
- 012 sovereign approval for merges/publish  
- WSP_97 truth labels on substantive claims  

---

## 5. Future path: FoundUps Agent Intake Mode

```text
external repo
  -> FoundUps Agent scans bounded context
  -> WSP readiness audit
  -> FoundUp intake packet (WSP_109)
  -> Skillz map
  -> integration risk / safety report
  -> optional governed WRE handoff recommendation
  -> NO automatic onboarding without verification
```

**F0 rule:** FoundUps-Agent repo (F0) must never be mutated automatically by the extension.

**External repos:** Assessed through advisory WSP intake, not automatic execution.

---

## 6. WSP_97 truth table (this slice)

| Claim | Status |
| --- | --- |
| PRODUCT_NAME_IS_FOUNDUPS_AGENT | OBSERVED (manifest + docs) |
| PACKAGE_ID_UNCHANGED | OBSERVED (`foundups-fusion-worker`) |
| REDDOG_IS_ARCHITECT_PERSONA | OBSERVED |
| FUSION_IS_INTERNAL_MODE_NOT_PRODUCT | OBSERVED (docs) |
| EXTENSION_REMAINS_ADVISORY_ONLY | OBSERVED |
| NO_REPO_WRITE_AUTHORITY | OBSERVED |
| NO_MODEL_SHELL_AUTHORITY | OBSERVED |
| F0_NO_AUTO_MUTATION | OBSERVED (by absence of write paths) |
| INTAKE_MODE_FUTURE_NOT_IMPLEMENTED | SPECIFIED_NOT_IMPLEMENTED |
| WEBVIEW_HEADER_LABELS_LAG_MANIFEST | NEEDS_VERIFICATION (extension.js follow-up) |

---

## 7. Residual NEEDS_VERIFICATION

1. Webview runtime strings (`extension.js`) still say "FoundUps Fusion" until UI labels slice.  
2. VSIX marketplace/install display vs manifest-only rename on existing installs.  
3. External-repo safety for Intake Mode requires separate threat review before implementation.  
4. Legal/trademark review before any `FoundUps(R)Agent` registered-mark styling.
