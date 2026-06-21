# FoundUps Fusion Worker

Version: 0.3.13

This local Cursor/VS Code extension opens one RedDog Architect advisory worker as an editor webview tab, similar in ergonomics to `Claude Code: Open` but without repo, shell, browser, merge, CABR, or payout authority.

Command:

- `FoundUps Fusion: Open`

Default panel:

- Lead/synthesis: `deepseek/deepseek-v3.2`
- Critics: `z-ai/glm-5.2` and `moonshotai/kimi-k2.7-code`

## Operating Contract

The extension is a bounded 0102 advisory surface:

- WSP_00: role defaults to RedDog Architect; 012 remains the external principal and final decision holder.
- WSP_97: answers must separate observed evidence, inference, and needs-verification.
- WSP_15: substantive answers must end with a priority block: Complexity, Importance, Deferability, Impact, MPS total, and P0-P4 class.
- Findings must include proposed fixes or an explicit defer/block reason.
- HoloIndex recall uses WSP_00 `HOLO_SKIP_MODEL=1 --bundle-json` first, then falls back to offline lexical search only if bundle recall fails.

The extension does not grant repo authority. Prompts and bounded repo context are sent through `scripts/advisory_model_once.py`, which runs the landed Fusion redaction gate before making OpenRouter requests. The webview receives only advisory text and redacted local history.

## Surface Layout

The webview follows the VS Code terminal/chat shape:

1. Compact header.
2. One scrollable output pane for status, prompts, responses, and errors.
3. Fixed bottom composer.

`Enter` sends, `Shift+Enter` adds a newline, and `Ctrl+Shift+C` copies the redacted review packet. `Copy MD` copies the latest assistant markdown only, not status logs.

## Controls

- Worker: RedDog Architect, WSP Gate Critic, Repair Planner, Smoke Test.
- Effort: Auto (WSP_15-style internal classifier), Regular, High, Ultra.
- Mode: FoundUps manual lead + panel (RedDog WSP default), OpenRouter Fusion alias (fast/black-box), Regular OpenRouter.
- Context: WSP + HoloIndex + active editor, WSP + HoloIndex + git diff, git diff, active editor, WSP only.
- Tests: regular smoke, Fusion smoke, WSP_97 repo review, RedDog architect review.

For WSP work, prefer `FoundUps manual lead + panel` because it preserves a review packet with lead, critic, and synthesis excerpts. The extension auto-selects effort from prompt/context when Effort=Auto and routes RedDog WSP work to the auditable manual panel by default. OpenRouter Fusion alias remains selectable for fast black-box synthesis, but individual critic traces are not exposed by the API response.

Substantive RedDog answers must include: Decision, Findings, Evidence, Proposed fixes, Uncertainties, WSP_97 Truth Labels, WSP_15 Priority, Next safest step. If sections are missing, the extension runs one repair pass through the same redaction-gated bridge before showing the final answer.

## Settings

The lead is configurable. Use Cursor settings or workspace/user settings:

```json
{
  "foundupsFusion.leadModel": "deepseek/deepseek-v3.2",
  "foundupsFusion.panelModels": [
    "z-ai/glm-5.2",
    "moonshotai/kimi-k2.7-code"
  ]
}
```

The extension uses up to four panel models.

## Bounded Repo Context

The worker has no direct filesystem authority. The extension can attach a bounded context packet from WSP operating rules, HoloIndex recall, the active editor, and local git diff. Prompt and context are redaction-gated separately before any OpenRouter request.

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
2. Run `Extensions: Install from VSIX...` and select the generated `foundups-fusion-worker-0.3.13.vsix` (or current package version).
3. Do not use workspace-extension install for normal operation; install the VSIX and reload the window.
4. Run `FoundUps Fusion: Open` from Command Palette or the three-dot command list.
