# FoundUps Fusion Worker

Version: 0.3.15

This local Cursor/VS Code extension opens one RedDog Architect advisory worker as an editor webview tab, similar in ergonomics to `Claude Code: Open` but without repo, shell, browser, merge, CABR, or payout authority.

Command:

- `FoundUps Fusion: Open`

Default panel:

- Principal/synthesis: `z-ai/glm-5.2`
- Critics: `deepseek/deepseek-v4-pro` and `moonshotai/kimi-k2.7-code`

## Operating Contract

The extension is a bounded 0102 advisory surface:

- WSP_00: role defaults to RedDog Architect; 012 remains the external principal and final decision holder.
- WSP_97: answers must separate observed evidence, inference, and needs-verification.
- WSP_15: substantive answers must end with a priority block: Complexity, Importance, Deferability, Impact, MPS total, and P0-P4 class.
- Findings must include proposed fixes or an explicit defer/block reason.
- HoloIndex recall uses WSP_00 `HOLO_SKIP_MODEL=1 --bundle-json` first, then falls back to offline lexical search only if bundle recall fails.

The extension does not grant repo authority. **012 supplies work focus only**; 0102 assembles a WSP task prompt before the bridge runs. Work focus and bounded repo context are sent through `scripts/advisory_model_once.py`, which runs the landed Fusion redaction gate before making OpenRouter requests. The webview receives only advisory text and redacted local history.

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
- Context: automatic. ULTRA tasks attach WSP + HoloIndex + active editor + git diff + Skillz/Wardrobe/Rolodex discovery; HIGH tasks attach WSP + HoloIndex + active editor + Skillz/Wardrobe/Rolodex discovery; REGULAR smoke avoids repo context.
- Tests: regular smoke, Fusion smoke, WSP_97 repo review, RedDog architect review.

For WSP/security/runtime/architecture work, RedDog auto-routes to `foundups_fusion` because it preserves a review packet with principal, critic, and synthesis excerpts. Regular smoke/simple prompts auto-route to a single GLM principal call. OpenRouter Fusion alias remains implemented in the bridge for explicit future use, but is not a 012-facing default control because individual critic traces are not exposed by the API response.

Substantive RedDog answers must include: Decision, Findings, Evidence, Proposed fixes, Uncertainties, Architect Trace (structured evidence/alternatives/critic rationale — never raw hidden chain-of-thought), WSP_97 Truth Labels, WSP_15 Priority, Verification gaps, Next safest step. Fusion runs also expose Lead/Critic/Synthesis panel structure from the bridge. If sections are missing, the extension runs one repair pass through the same redaction-gated bridge before showing the final answer.

Output is prefixed with a visible **RedDog Routing** block (tier, effort, mode, mode-selection reasoning, principal, panel, context, advisory boundary).

## WSP_97 Truth Table (v0.3.15)

| Claim | Status |
| --- | --- |
| Principal default `z-ai/glm-5.2` | OBSERVED |
| Critics default DeepSeek V4 Pro + Kimi K2.7 Code | OBSERVED |
| 012 work focus -> 0102 WSP task prompt | OBSERVED |
| Review packet work_focus_digest + wsp_prompt_digest | OBSERVED |
| Mode/Effort/Context not 012-facing dropdowns | OBSERVED |
| REGULAR → `openrouter_single`, no repo context | OBSERVED |
| HIGH → `foundups_fusion` + WSP/Holo/Skillz context | OBSERVED |
| ULTRA → `foundups_fusion` + WSP/Holo/git/Skillz context | OBSERVED |
| Skillz/Rolodex discovery for operational prompts | OBSERVED |
| Filesystem fallback when git spawn fails | OBSERVED |
| RedDog Routing block in output | OBSERVED |
| Review packet: resolved mode/effort/context/principal/panel/validation | OBSERVED |
| Architect Trace + Verification gaps in schema | OBSERVED |
| Mode-selection reasoning in routing + review packet | OBSERVED |
| Fusion Lead/Critic/Synthesis structure validated | OBSERVED |
| Governed Skillz/OpenClaw/Hermes handoff execution | SPECIFIED_NOT_IMPLEMENTED |
| pfMALL RedDog surface binding | SPECIFIED_NOT_IMPLEMENTED |
| Review packet persistent memory | SPECIFIED_NOT_IMPLEMENTED |
| OpenRouter Fusion alias as default RedDog path | SPECIFIED_NOT_IMPLEMENTED (explicit path only) |

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

After a successful run, focus the prompt box and press `Ctrl+Shift+C` to copy a redacted review packet. Paste that packet into Codex for 0102 review. The packet contains the redacted prompt, model slugs, bounded excerpts, task classification, resolved effort/mode, and output validator/repair status; it does not contain the OpenRouter key.

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
2. Run `Extensions: Install from VSIX...` and select the generated `foundups-fusion-worker-0.3.15-work-focus.vsix` (or current package version).
3. Do not use workspace-extension install for normal operation; install the VSIX and reload the window.
4. Run `FoundUps Fusion: Open` from Command Palette or the three-dot command list.
