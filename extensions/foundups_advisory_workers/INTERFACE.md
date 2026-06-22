# FoundUps Fusion Worker Interface

## Purpose

`foundups-fusion-worker` is a local Cursor/VS Code extension that opens a RedDog Architect advisory surface backed by OpenRouter models through `scripts/advisory_model_once.py`.

It is an IDE-side proof surface for the future RedDog/pfMALL/WRE intake pattern. It does not implement pfMALL runtime wiring, WRE dispatch, FoundUp registration, repository creation, or CABR verification.

## Authority Boundary

| Capability | Status | Boundary |
|---|---|---|
| Advisory model review | YES | OpenRouter request after Fusion redaction gate passes |
| Bounded repo context | YES | Extension auto-gathers WSP/HoloIndex/editor/git/Skillz context by WSP_15 tier and sends it through redaction gate |
| HoloIndex recall | YES | `HOLO_SKIP_MODEL=1 --bundle-json` first; offline lexical fallback only if bundle recall fails |
| WSP_00/WSP_97/WSP_15 prompting | YES | System prompt requires role lock, truth labels, proposed fixes, and MPS priority |
| Repo edits | NO | No write tool exposed to model |
| Shell execution by model | NO | Extension host runs only bounded local context/bridge commands; model cannot execute Skillz/OpenClaw/Hermes |
| Merge/PR authority | NO | Advisory output only |
| CABR/payout/source authority | NO | Blocked by Fusion redaction gate and prompt contract |
| pfMALL integration | SPECIFIED_NOT_IMPLEMENTED | Roadmap only |
| FoundUp onboarding automation | SPECIFIED_NOT_IMPLEMENTED | Roadmap only; WSP_109 packet production is not implemented here |

## Webview Contract

The UI copies the VS Code terminal/chat layout:

1. Header: build/model metadata only.
2. Output scrollback: status, 012 work focus, 0102 output, and errors.
3. Bottom composer: fixed **work focus** input and controls.

The output pane owns scrolling. Content must not pass behind the composer.

Keyboard:

- `Enter`: send work focus.
- `Shift+Enter`: newline.
- `Ctrl+Shift+C`: copy redacted review packet.

Copy:

- `Copy MD`: copies the latest assistant answer only.
- Status/progress logs are visible in output but excluded from markdown copy.

## Worker Modes

| Worker | Intended Use |
|---|---|
| RedDog Architect | Default architecture review and FoundUps intake/orchestration reasoning |
| WSP Gate Critic | Gate reports, return-to-author findings, WSP_97 critique |
| Repair Planner | Smallest valid implementation and test-slice planning |
| Smoke Test | Bounded API/bridge checks without broad architecture review |

## Model Modes

| Mode | Traceability | Notes |
|---|---|---|
| FoundUps manual lead + panel | Higher | Stores lead, panel, and synthesis excerpts in review packet |
| OpenRouter Fusion alias | Lower | Black-box Fusion synthesis; individual critic transcripts are not exposed |
| Regular OpenRouter | Single-model | Fast direct lead review |

## HoloIndex Truth Boundary

The model cannot access the filesystem. It receives only the bounded context packet.

If HoloIndex recall reports zero WSP hits, missing Tier-0 docs, stale/offline fallback, or unavailable output, the answer must treat protocol claims as `NEEDS_VERIFICATION` and propose retrieval/index repair before strong claims.

## WSP_97 Truth Boundary

Every substantive answer should classify claims:

- `OBSERVED`: present in supplied context.
- `INFERRED`: derived from supplied context but not directly proven.
- `NEEDS_VERIFICATION`: requires local read, test, live run, or external decision.
- `SPECIFIED_NOT_IMPLEMENTED`: documented requirement, not current behavior.

## WSP_15 Output Requirement

Every substantive answer ends with:

```text
## WSP_15 Priority
| Action | Complexity | Importance | Deferability | Impact | MPS | Priority |
|---|---:|---:|---:|---:|---:|---|
| ... | ... | ... | ... | ... | ... | P0-P4 |

## Next Safest Step
...
```

## RedDog Fusion Orchestrator (v0.3.14)

Internal contract layer. Advisory-only. No new authority.

| Function | Purpose |
|---|---|
| `classifyTaskForRedDog(prompt, contextMode, workerType)` | WSP_15-style effort/risk classification |
| `resolveAutoContextMode(classification, selectedContextMode)` | Maps Auto context to none / WSP+Holo+Skillz / WSP+Holo+git+Skillz |
| `resolveAutoEffort(classification, selectedEffort)` | Maps Auto -> regular/high/ultra |
| `resolveModelMode(classification, selectedMode, workerType)` | RedDog WSP work defaults to auditable manual panel |
| `validateRedDogOutput(markdown)` | Required schema section check |
| `buildRepairPrompt(originalPrompt, badOutput, missingSections)` | One bounded repair pass |

Required substantive output sections:

- Decision
- Findings
- Evidence
- Proposed fixes
- Uncertainties
- WSP_97 Truth Labels
- WSP_15 Priority
- Next safest step

Auto effort rules:

- `ULTRA`: auth/security/secrets/live runtime/public surface/pfMALL/WRE/OpenClaw/Hermes/Kanban/CABR/merge authority/repo creation.
- `HIGH`: architecture, WSP protocol, HoloIndex gaps, extension routing, FoundUp intake, RedDog/pfMALL planning.
- `REGULAR`: simple smoke tests, simple code explanation, non-runtime UI polish.
- If uncertain, choose `HIGH`.

Model and context routing:

- RedDog WSP/security/architecture/runtime work auto-routes to `foundups_fusion` (manual principal + panel).
- Principal/synthesis default: `z-ai/glm-5.2`.
- Adversarial critic default: `deepseek/deepseek-v4-pro`.
- Implementation critic default: `moonshotai/kimi-k2.7-code`.
- REGULAR smoke/simple prompts auto-route to `openrouter_single` with the GLM principal and no repo context.
- Context is not a 012-facing selector; it is resolved from WSP_15 tier.
- Skillz/Wardrobe/Rolodex/OpenClaw/Hermes discovery is context only. RedDog may recommend a governed handoff, but this extension cannot execute it.
- `openrouter_fusion_alias` remains implemented for future explicit use, but is not the RedDog default because critic traces are not exposed.
- Repair pass: at most one; uses the same redaction-gated bridge; must not invent evidence.

Review packet additions:

- `task_classification`
- `resolved_effort`
- `resolved_mode`
- `resolved_context`
- `principal_model`
- `panel_models`
- `mode_selection_reasoning`
- `work_focus_digest` (`hash`, `excerpt`, `length` - redacted)
- `wsp_prompt_digest` (`hash`, `excerpt`, `length` - redacted)
- `prompt_construction`: `0102_generated_from_work_focus`
- `output_validation` (`validated`, `missing_sections`, `repair_attempted`, `repair_ok`, `fusion_panel_ok`)

## 012 Work Focus to 0102 WSP Task Prompt (v0.3.15)

Formal contract:

```text
012 work focus (non-authoritative)
  -> 0102 constructWspTaskPrompt(workFocus, classification, contextQuality, workerType)
  -> redaction gate (prompt + bounded context separately)
  -> OpenRouter bridge
  -> RedDog architect output
```

012 does not prompt RedDog directly. The bridge receives the assembled WSP task prompt, not raw work focus alone. Work focus is embedded inside the WSP prompt under an explicit non-authoritative label.

## WSP_97 Truth Table (v0.3.15)

| Claim | Status |
| --- | --- |
| Auto router REGULAR/HIGH/ULTRA | OBSERVED |
| 012 work focus -> 0102 WSP task prompt layer | OBSERVED |
| Review packet work_focus_digest + wsp_prompt_digest | OBSERVED |
| Skillz/Rolodex non-vacuous for YouTube comment ops | OBSERVED |
| Advisory-only; no shell/repo/browser/OpenClaw/Hermes execution | OBSERVED |
| Redaction gate before OpenRouter | OBSERVED |
| Governed handoff contract (typed WRE dispatch) | SPECIFIED_NOT_IMPLEMENTED |
| pfMALL surface binding | SPECIFIED_NOT_IMPLEMENTED |
| Review packet memory / persistence | SPECIFIED_NOT_IMPLEMENTED |
| Bridge hardening (edge-case redaction/repair) | SPECIFIED_NOT_IMPLEMENTED |

## Public/RedDog Roadmap Boundary

The extension is the IDE-side model for a future RedDog operation surface:

```text
012 work focus
  -> 0102 WSP task prompt assembly
  -> RedDog Architect advisory review
  -> HoloIndex recall
  -> WSP_97 truth classification
  -> WSP_15 priority
  -> WSP_109 intake packet or WRE dispatch recommendation
  -> Skillz/Wardrobe/Rolodex match and WRE/OpenClaw/Hermes governed handoff recommendation
  -> WRE/OpenClaw/Hermes governed execution
  -> pfMALL-visible state after verification
```

This interface documents that direction only. It does not expose a public intake route.
