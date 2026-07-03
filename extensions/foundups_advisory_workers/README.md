# Foundups®Agent

Version: 0.3.41

This local Cursor/VS Code extension opens one RedDog Architect advisory worker as an editor webview tab, similar in ergonomics to `Claude Code: Open` but without repo, shell, browser, merge, CABR, or payout authority.

Foundups®Agent is the product surface. RedDog is the 0102 digital-twin architect inside it. Fusion is one internal reasoning mode, not the product identity.

Command:

- `Foundups®Agent: Open`

Default panel:

- Principal/synthesis: `z-ai/glm-5.2`
- Critics: `deepseek/deepseek-v4-pro` and `moonshotai/kimi-k2.7-code`

## RedDog and the Recursive 0102 DAE Ecosystem

012 does not orchestrate every worker. 012 talks to RedDog. RedDog participates in the recursive 0102 DAE ecosystem. Autonomous WRE/DAE agents perform bounded system work under Hermes/OpenClaw/WRE governance.

### Architecture Stack

```text
012 work focus
  -> RedDog digital twin / architect interface
  -> recursive 0102 DAE ecosystem
```

### Layer Roles

| Layer | Role |
| --- | --- |
| RedDog | Digital-twin architect/interface. 012's first contact point. Assembles WSP task prompts, classifies work focus, recommends handoffs. |
| Hermes | Scaffolding, lifecycle, scheduling, queues, receipts. Infrastructure coordination. Not policy authority. |
| OpenClaw | Policy and intent gate. Validates FoundUp onboarding, enforces WSP boundaries, governs dispatch. |
| HoloIndex | Memory and retrieval. Semantic code search, WSP lookup, module discovery. |
| Skillz/Rolodex | Capability catalog. Wardrobe discovery for governed handoff recommendations. |
| Autonomous WRE/DAE agents | Code, docs, tests, ops, promotion, FoundUp launch. Bounded work under WRE verification. |
| Sentinels | Critique, truth, drift, regression review. Observe and flag, do not execute. |
| WRE | Repo and process authority. Verification, dispatch, coordination. Retains execution control. |
| CABR/pAVS | Benefit validation, routing, reputation. Proof-of-Benefit scoring for FoundUp work. |
| 012 | Work focus, testing, sovereign authorization, override. Harmonic Recursive Partner role (WSP 54). |

### Autonomy Boundary

Autonomous WRE/DAE agents are NOT 012 work. 012 provides work focus, testing, sovereign approval, and override. 0102 DAEs communicate recursively and perform bounded autonomous work under WRE governance. The extension remains advisory; WRE retains execution authority.

## Operating Contract

The extension is a bounded 0102 advisory surface:

- WSP_00: role defaults to RedDog Architect; 012 remains the external principal and final decision holder.
- WSP_97: answers must separate observed evidence, inference, and needs-verification.
- WSP_15: substantive answers must end with a priority block: Complexity, Importance, Deferability, Impact, MPS total, and P0-P4 class.
- Findings must include proposed fixes or an explicit defer/block reason.
- HoloIndex recall uses WSP_00 `HOLO_SKIP_MODEL=1 --bundle-json` first, then falls back to offline lexical search only if bundle recall fails.

The extension does not grant repo authority. **012 supplies work focus only**; 0102 assembles a WSP task prompt before the bridge runs. Work focus and bounded repo context are sent through `scripts/advisory_model_once.py`, which runs the landed Fusion redaction gate before making OpenRouter requests. The webview receives only advisory text and redacted local history.

## F0 Safety Boundary

F0 is the foundation Foundups-Agent repo. Foundups®Agent must never mutate F0 automatically.

Current behavior is advisory-only:

- no model-controlled shell execution
- no automatic file edits
- no automatic PR creation, merge, deployment, or repository creation
- no CABR, payout, source-authority, or verification claims
- no direct Skillz/OpenClaw/Hermes/WRE execution from the extension
- redaction gate runs before any OpenRouter egress

External repositories can be assessed for FoundUps integration through advisory WSP intake, not automatic execution. The future path is FoundUps Agent Intake Mode: WSP readiness audit, FoundUp intake packet, Skillz map, integration risk report, and governed WRE handoff recommendation.

## Governed Repo Work Order (contract)

RedDog does **not** hold standing repository authority. RedDog **receives a bounded delegated capability for one work order after fresh verification** (authenticated principal, GitHub permission snapshot, OpenClaw policy gate, WRE execution).

Canonical architecture contract (docs only, v0.3.27):

- `docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md`
- Schema draft: `RedDogGovernedWorkOrder` (see audit doc)
- F0 autonomous merge: **SPECIFIED_NOT_IMPLEMENTED** — not planned until prior gates land

Future RedDog runtime must run **WSP Applicability Preflight** before emitting any work order (identify WSPs + Skillz from HoloIndex; block if recall is weak).

## Work Focus Contract (v0.3.15)

012 does not prompt RedDog directly. The operating flow is:

```text
012 work focus -> 0102 constructWspTaskPrompt -> redaction gate -> OpenRouter bridge -> RedDog architect output
```

- Composer label: **work focus** (not "prompt")
- Bridge receives the **WSP task prompt** assembled by 0102, not raw composer text alone
- Review packet stores `work_focus_digest`, `wsp_prompt_digest`, and `prompt_construction: 0102_generated_from_work_focus`

## Surface Layout

The webview follows the VS Code terminal/chat shape:

1. Compact header.
2. One scrollable output pane for status, work focus, responses, and errors.
3. Fixed bottom composer (work focus input).

`Enter` sends work focus, `Shift+Enter` adds a newline, and `Ctrl+Shift+C` copies the redacted review packet. `Copy MD` copies the latest assistant markdown only, not status logs.

## Controls

- Worker: RedDog Architect, WSP Gate Critic, Repair Planner, Smoke Test.
- Routing: automatic via WSP_15-style task classification; 012 no longer picks Mode/Effort/Context for normal use.
- Context: automatic. ULTRA tasks attach WSP + HoloIndex + active editor + git diff + Skillz/Wardrobe/Rolodex discovery; HIGH tasks attach WSP + HoloIndex + active editor + Skillz/Wardrobe/Rolodex discovery; REGULAR attaches WSP + HoloIndex only (`wsp_holo`, no Skillz/git).
- Tests: regular smoke, Fusion smoke, WSP_97 repo review, RedDog architect review.

For WSP/security/runtime/architecture work, RedDog auto-routes to `foundups_fusion` because it preserves a review packet with principal, critic, and synthesis excerpts. Regular smoke/simple prompts auto-route to a single GLM principal call. OpenRouter Fusion alias remains implemented in the bridge for explicit future use, but is not a 012-facing default control because individual critic traces are not exposed by the API response.

Substantive RedDog answers must include: Decision, Findings, Evidence, Proposed fixes, Uncertainties, Architect Trace (structured evidence/alternatives/critic rationale 窶・never raw hidden chain-of-thought), WSP_97 Truth Labels, WSP_15 Priority, Verification gaps, Next safest step. Fusion runs also expose Lead/Critic/Synthesis panel structure from the bridge. If sections are missing, the extension runs one repair pass through the same redaction-gated bridge before showing the final answer.

Output is prefixed with a visible **RedDog Routing** block (tier, effort, mode, mode-selection reasoning, principal, panel, context, advisory boundary).

## WSP_97 Truth Table (v0.3.15)

| Claim | Status |
| --- | --- |
| Principal default `z-ai/glm-5.2` | OBSERVED |
| Critics default DeepSeek V4 Pro + Kimi K2.7 Code | OBSERVED |
| 012 work focus -> 0102 WSP task prompt | OBSERVED |
| Review packet work_focus_digest + wsp_prompt_digest | OBSERVED |
| WORK_FOCUS_NOT_AUTHORITY | OBSERVED |
| WSP_PROMPT_0102_GENERATED | OBSERVED |
| RAW_FOCUS_NOT_SENT_AS_SOLE_AUTHORITY | OBSERVED |
| DIGESTS_NOT_RAW_CONTEXT | OBSERVED |
| ROUTING_UNCHANGED_FROM_0_3_14 | OBSERVED |
| Mode/Effort/Context not 012-facing dropdowns | OBSERVED |
| REGULAR -> `openrouter_single` + `wsp_holo` (HoloIndex only; no Skillz/git) | OBSERVED |
| HIGH -> `foundups_fusion` + WSP/Holo/Skillz context | OBSERVED |
| ULTRA -> `foundups_fusion` + WSP/Holo/git/Skillz context | OBSERVED |
| Skillz/Rolodex discovery for operational prompts | OBSERVED |
| Filesystem fallback when git spawn fails | OBSERVED |
| RedDog Routing block in output | OBSERVED |
| Review packet: resolved mode/effort/context/principal/panel/validation | OBSERVED |
| Architect Trace + Verification gaps in schema | OBSERVED |
| Mode-selection reasoning in routing + review packet | OBSERVED |
| Fusion Lead/Critic/Synthesis structure validated | OBSERVED |
| Governed handoff contract (typed WRE dispatch) | SPECIFIED_NOT_IMPLEMENTED |
| Governed repo work order contract | OBSERVED (audit doc); RUNTIME_EMISSION SPECIFIED_NOT_IMPLEMENTED |
| RedDogGovernedWorkOrder dry-run validator | OBSERVED (OpenClaw bridge module) |
| RedDogGovernedWorkOrder schema | SPECIFIED_NOT_IMPLEMENTED (extension emission) |
| GitHub permission probe per work order | SPECIFIED_NOT_IMPLEMENTED |
| F0 autonomous merge | SPECIFIED_NOT_IMPLEMENTED (not planned) |
| WSP Applicability Preflight before work order | SPECIFIED_NOT_IMPLEMENTED |
| pfMALL surface binding | SPECIFIED_NOT_IMPLEMENTED |
| Review packet persistent memory | SPECIFIED_NOT_IMPLEMENTED |
| OpenRouter Fusion alias as default RedDog path | SPECIFIED_NOT_IMPLEMENTED (explicit path only) |
| REDDOG_IS_ARCHITECT_INTERFACE | OBSERVED |
| AUTONOMOUS_DAE_WORK_NOT_012_WORK | OBSERVED |
| HERMES_IS_SCAFFOLDING_NOT_POLICY | OBSERVED |
| OPENCLAW_IS_POLICY_GATE | OBSERVED |
| WRE_RETAINS_REPO_AUTHORITY | OBSERVED |
| SENTINELS_REVIEW_NOT_EXECUTE | OBSERVED |
| CABR_PAVS_VALIDATES_BENEFIT | OBSERVED |
| EXTENSION_REMAINS_ADVISORY_ONLY | OBSERVED |

## Settings

The lead is configurable. Use Cursor settings or workspace/user settings:

```json
{
  "foundupsFusion.leadModel": "z-ai/glm-5.2",
  "foundupsFusion.panelModels": [
    "deepseek/deepseek-v4-pro",
    "moonshotai/kimi-k2.7-code"
  ]
}
```

The extension uses up to four panel models. RedDog defaults to GLM-5.2 as principal, DeepSeek V4 Pro as adversarial critic, and Kimi K2.7 Code as implementation critic.

## Bounded Repo Context

The worker has no direct filesystem authority. The extension automatically attaches a bounded context packet from WSP operating rules, HoloIndex recall, the active editor, local git diff when risk warrants it, and Skillz/Wardrobe/Rolodex discovery for governed handoff recommendations. Prompt and context are redaction-gated separately before any OpenRouter request.

## Review Packet

After a successful run, focus the work focus composer and press `Ctrl+Shift+C` to copy a redacted review packet. Paste that packet into Codex for 0102 review. The packet contains digested work focus and WSP prompt excerpts (not full raw context), model slugs, bounded excerpts, task classification, resolved effort/mode, and output validator/repair status; it does not contain the OpenRouter key.

**Follow-up memory (v0.3.28):** Enable **Use last RedDog packet** (default ON) to append a WSP_97-safe continuation summary to the next prompt instead of pasting raw Copy MD back into the composer. In-memory per tab only; no cross-reload persistence yet.

## Setup

Set `OPENROUTER_API_KEY` in the environment used to launch Cursor. Do not store the key in repo settings.

## Install

Build the VSIX locally from tracked source with `vsce package --no-dependencies`. Do not commit `*.vsix`.

```powershell
cd extensions/foundups_advisory_workers
vsce package --no-dependencies
```

From Cursor:

1. Open Command Palette.
2. Run `Extensions: Install from VSIX...` and select the generated `foundups-fusion-worker-0.3.18.vsix` (or current package version).
3. Do not use workspace-extension install for normal operation; install the VSIX and reload the window.
4. Run `Foundups®Agent: Open` from Command Palette or the three-dot command list.
