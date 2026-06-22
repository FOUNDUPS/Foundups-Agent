# REDDOG_WORKING_TRAIL_PHASE1 — Design Contract

**Slice:** REDDOG_WORKING_TRAIL_PHASE1
**Worker-Lane:** AUTHOR
**Calibration:** DECISION_ONLY_DOCS
**Branch:** feat/reddog-working-trail-phase1
**Base SHA:** 4a345d8677fe948bee2d2337eb19fb985a15baa6 (origin/main at 2026-06-23)
**Date:** 2026-06-23
**Status:** Phase 1 design only. Phase 2 (implementation) is a separate CODE_NON_SPINE slice.

---

## Problem Statement

012 observes long Fusion runs (104s-172s) as apparent stalls. The webview receives no visible
signal between "Bridge started" and "Complete" except sparse status text appended to the
scrollback log. The working trail closes this gap by mapping every existing bridge progress
event to a visible RedDog action, rendered as a persistent strip in the webview.

---

## 1. UI Contract: `reddogWorkingTrail`

### HTML Structure

```html
<div id="reddogWorkingTrail" class="reddog-working-trail" aria-live="polite" aria-atomic="false">
  <span data-reddog-pixel>.ᴥ.</span>
  <span data-reddog-action>idle</span>
  <span data-reddog-elapsed></span>
</div>
```

### DOM Placement

The trail strip is inserted as the **last child of `<form id="form">`**, below the textarea
and the hint line. It does NOT replace the scrollback log entries; those remain unchanged.

```html
<form id="form">
  <div class="toolbar">...</div>
  <textarea id="workFocus">...</textarea>
  <div class="hint">...</div>
  <!-- TRAIL STRIP INSERTED HERE -->
  <div id="reddogWorkingTrail" class="reddog-working-trail" aria-live="polite" aria-atomic="false">
    <span data-reddog-pixel>.ᴥ.</span>
    <span data-reddog-action>idle</span>
    <span data-reddog-elapsed></span>
  </div>
</form>
```

### CSS Contract

```css
.reddog-working-trail {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0 2px 0;
  font-size: 11px;
  font-family: var(--vscode-editor-font-family);
  color: var(--vscode-descriptionForeground);
  min-height: 18px;
  user-select: none;
}
.reddog-working-trail[data-active="true"] {
  color: var(--vscode-charts-green);
}
.reddog-working-trail[data-active="error"] {
  color: var(--vscode-errorForeground);
}
[data-reddog-elapsed] {
  font-variant-numeric: tabular-nums;
}
```

### Update Frequency

- Updated on every `event.event === 'progress'` received from the bridge via `onProgress`.
- Elapsed time refreshed every **1000ms** via `setInterval` while `running === true`.
- The interval is created in `setRunning(true)` and cleared in `setRunning(false)`.

### Elapsed Time Format

- `0s` through `9s`: display as `0s` ... `9s`
- `10s` and above: display as `10s`, `11s`, etc.
- Above 60s: display as `1m02s`, `1m30s`, etc.

```js
function formatElapsed(ms) {
  const s = Math.floor(ms / 1000);
  if (s < 60) return s + 's';
  return Math.floor(s / 60) + 'm' + String(s % 60).padStart(2, '0') + 's';
}
```

### Idle Behavior

When `running === false` the trail displays:

| `data-reddog-pixel` | `data-reddog-action` | `data-reddog-elapsed` | `data-active` |
|---------------------|---------------------|-----------------------|---------------|
| `~~~`               | `idle`              | _(empty)_             | _(absent)_    |

The idle pixel cycles through `~~~ -> .ᴥ. -> •ᴥ• -> .ᴥ. -> ~~~` at 800ms per frame ONLY
when `running === true`. When idle the pixel is static `~~~`.

### Reset Trigger

`updateReddogTrail('idle', '~~~', 0)` is called as the **first line** of
`setRunning(false)`. This ensures the trail resets before the scrollback receives the
"Complete" or "Stopped" entry, so there is no transient state where the trail shows an
active action after the run ends.

---

## 2. Event-to-Action Mapping

### Bridge Progress Events (complete inventory from pre-read)

All `_progress(stage, text)` calls in `advisory_model_once.py` and all `onProgress(text)`
calls in `extension.js` (`callFusion`) and the webview's `sendWorkFocus()`.

#### Source: webview JS (`sendWorkFocus`)

| Event text (prefix match) | RedDog action | Pixel | Notes |
|---------------------------|--------------|-------|-------|
| `Work focus sent.` | `sniffing` | `.ᴥ.` | First visible signal; 012 submitted work focus |

#### Source: extension.js `callFusion` via `onProgress`

| Event text (prefix match) | RedDog action | Pixel | Notes |
|---------------------------|--------------|-------|-------|
| `Mode: ` | `sorting` | `•ᴥ•` | Mode resolved; entering routing phase |
| `Python interpreter: ` | `sorting` | `•ᴥ•` | Interpreter located; same routing phase |
| `Bridge process starting` | `sorting` | `•ᴥ•` | Subprocess spawning |
| `Context budget applied: ` | `tracking` | `•ᴥ•` | Truncation applied; context assembled |
| Orchestrator routing summary (`Orchestrator: effort=`) | `sorting` | `•ᴥ•` | Routing resolved |
| `Bridge started. Redaction gate runs` | `nosing` | `•ᴥ•` | About to enter redaction gate |
| `Repo context attached: ` | `tracking` | `•ᴥ•` | Context/HoloIndex assembled |
| `Repo context: WSP operating contract only.` | `tracking` | `•ᴥ•` | Minimal context mode |
| `0102 assembled WSP task prompt` | `sniffing` | `.ᴥ.` | Work focus -> WSP prompt conversion done |
| `Output schema incomplete. Missing: ` | `digging` | `•ᴥ•` | Entering repair pass |

#### Source: advisory_model_once.py `_progress` calls

| Stage | Text pattern | RedDog action | Pixel |
|-------|-------------|--------------|-------|
| `bridge_start` | `Bridge Python started.` | `sorting` | `•ᴥ•` |
| `env_check` | `OPENROUTER_API_KEY visible` | `nosing` | `•ᴥ•` |
| `redaction_start` | `Redaction gate started.` | `nosing` | `•ᴥ•` |
| `redaction_blocked` | `Redaction gate blocked` | `barking` | `!ᴥ!` |
| `redaction_pass` | `Redaction gate passed.` | `nosing` | `•ᴥ•` |
| `fusion_alias_start` | `OpenRouter Fusion alias request started.` | `fetching` | `•ᴥ•` |
| `fusion_alias_done` | `OpenRouter Fusion alias response received.` | `crystallizing` | `•ᴥ•` |
| `lead_start` | `Lead request started:` | `fetching` | `•ᴥ•` |
| `lead_done` | `Lead response received:` | `herding` | `•ᴥ•` |
| `panel_start` | `Panel requests started:` | `herding` | `•ᴥ•` |
| `panel_done` | `Panel response received:` | `herding` | `•ᴥ•` |
| `panel_blocked` | `Panel blocked:` / `Panel network error:` / `Panel malformed response:` | `sitting` | `.ᴥ.` |
| `synthesis_start` | `Synthesis request started:` | `crystallizing` | `•ᴥ•` |
| `synthesis_done` | `Synthesis complete.` | `pointing` | `ᐡᴥᐡ` |
| `single_start` | `Regular OpenRouter request started:` | `fetching` | `•ᴥ•` |
| `single_done` | `Regular OpenRouter response received:` | `pointing` | `ᐡᴥᐡ` |

#### Completion and Error (from extension.js `window.addEventListener('message')`)

| Condition | RedDog action | Pixel | Trigger |
|-----------|--------------|-------|---------|
| `msg.result.ok === true` | `pointing` | `ᐡᴥᐡ` | `result` message with ok |
| `msg.result.ok === false` | `growling` | `!ᴥ!` | `result` message with failure |
| `reason === 'redaction_blocked'` | `barking` | `!ᴥ!` | Redaction failed; no network call made |

#### Gap Events: Long Wait / Rate Limit

**Gap identified:** There is no bridge progress event emitted during the HTTP request
in-flight window (between `lead_start` / `fetching` and `lead_done`). This is the source
of the apparent stall on 104s-172s runs.

**Phase 2 action:** The elapsed timer covers this gap visually. No new progress events are
required from the bridge for Phase 2. The `sitting` action with `.ᴥ.` fires automatically
if no progress event arrives for >10s via a fallback timer in `updateReddogTrail`.

Specifically: if `running === true` and no progress event has updated the trail for 10
consecutive seconds, the trail transitions to `sitting / .ᴥ. / <elapsed>`. This is a
pure JS-side heuristic with no bridge changes.

#### Complete Action Table (all 12 actions used)

| Action | Pixel | Coverage |
|--------|-------|----------|
| `sniffing` | `.ᴥ.` | Work focus received; WSP prompt assembled |
| `sorting` | `•ᴥ•` | Bridge started; mode/routing resolved |
| `tracking` | `•ᴥ•` | Context assembled; HoloIndex/budget applied |
| `nosing` | `•ᴥ•` | Redaction gate checking and pass |
| `barking` | `!ᴥ!` | Redaction blocked (pre-network) |
| `fetching` | `•ᴥ•` | Model request in flight (lead or single) |
| `herding` | `•ᴥ•` | Fusion critics running; panel done events |
| `sitting` | `.ᴥ.` | Panel blocked (partial fail); long-wait fallback |
| `digging` | `•ᴥ•` | Repair pass started |
| `crystallizing` | `•ᴥ•` | Synthesis / Fusion alias response |
| `pointing` | `ᐡᴥᐡ` | Completion (synthesis done or single done) |
| `growling` | `!ᴥ!` | Failed/error result |

#### Pixel Idle Cycle

When `running === true` and the trail is in `idle` state (before first event), the pixel
cycles at 800ms intervals:

```
~~~ -> .ᴥ. -> •ᴥ• -> .ᴥ. -> ~~~
```

Once the first progress event fires, the pixel freezes at the event-assigned value and
cycling stops.

---

## 3. Minimal Implementation Plan

### Phase 1 (this slice)

Design contract document only. No code changes. This document IS the deliverable.

### Phase 2 (next slice: CODE_NON_SPINE)

#### Files to touch in `extension.js`

| Location | Change |
|----------|--------|
| `renderHtml` CSS block (inside the `<style>` tag) | Add `.reddog-working-trail` and related CSS rules |
| `renderHtml` HTML body (inside `<form id="form">`) | Add `<div id="reddogWorkingTrail" ...>` strip after the hint line |
| `renderHtml` `<script>` block | Add `updateReddogTrail`, `formatElapsed`, `REDDOG_PROGRESS_ACTIONS`, idle pixel cycler, and elapsed `setInterval` |
| `setRunning(value)` | On `true`: start elapsed interval, call `updateReddogTrail('sniffing', '.ᴥ.', 0)` when work focus sent; on `false`: call `updateReddogTrail('idle', '~~~', 0)`, clear interval |
| `addStatus(text)` | After appending status, call `matchReddogProgress(text)` to check the text against `REDDOG_PROGRESS_ACTIONS` |
| `window.addEventListener('message')` result handler | On `ok`: call `updateReddogTrail('pointing', 'ᐡᴥᐡ', ...)`, or `updateReddogTrail('growling', '!ᴥ!', ...)` on failure |

Approximate line counts: +45 CSS lines, +8 HTML lines, +70 JS lines. Total: ~123 lines added, 0 lines removed.

#### Files to touch in `advisory_model_once.py`

No changes required in Phase 2. All existing `_progress` stage strings are already
sufficient for the trail mapping. The phase 2 implementation is extension.js-only.

**Exception path:** If 012 decides to add normalized events for JSONL training (Section 4),
a separate `_training_event` emitter would be added to `advisory_model_once.py` in a
Phase 3 slice. This is NOT part of Phase 2.

#### JS Function Signatures

```js
/**
 * Update the RedDog working trail strip.
 * @param {string} action  - one of the 12 defined action names
 * @param {string} pixel   - one of '.ᴥ.', '•ᴥ•', '!ᴥ!', 'ᐡᴥᐡ', '~~~'
 * @param {number} elapsedMs - milliseconds since startedAt (0 = use current)
 */
function updateReddogTrail(action, pixel, elapsedMs) { ... }

/**
 * Match a status text string against REDDOG_PROGRESS_ACTIONS and update trail.
 * @param {string} text - the status text emitted by onProgress or sendWorkFocus
 */
function matchReddogProgress(text) { ... }

/**
 * Format elapsed milliseconds as a human-readable string.
 * @param {number} ms
 * @returns {string}  e.g. '0s', '45s', '1m02s'
 */
function formatElapsed(ms) { ... }
```

#### `REDDOG_PROGRESS_ACTIONS` Pattern Table

```js
// One entry per bridge progress event found in pre-read.
// Matched top-to-bottom; first match wins.
const REDDOG_PROGRESS_ACTIONS = [
  // webview-local events
  [/Work focus sent\./i,                              { action: 'sniffing',      pixel: '.ᴥ.'  }],
  [/0102 assembled WSP task prompt/i,                 { action: 'sniffing',      pixel: '.ᴥ.'  }],
  // bridge routing/startup (extension.js onProgress)
  [/Orchestrator: effort=/i,                          { action: 'sorting',       pixel: '•ᴥ•' }],
  [/Bridge started\. Redaction gate/i,                { action: 'nosing',        pixel: '•ᴥ•' }],
  [/^Mode: /i,                                        { action: 'sorting',       pixel: '•ᴥ•' }],
  [/^Python interpreter: /i,                          { action: 'sorting',       pixel: '•ᴥ•' }],
  [/^Bridge process starting/i,                       { action: 'sorting',       pixel: '•ᴥ•' }],
  [/^Context budget applied:/i,                       { action: 'tracking',      pixel: '•ᴥ•' }],
  [/^Repo context attached:/i,                        { action: 'tracking',      pixel: '•ᴥ•' }],
  [/^Repo context: WSP operating contract/i,          { action: 'tracking',      pixel: '•ᴥ•' }],
  [/^Output schema incomplete\. Missing:/i,           { action: 'digging',       pixel: '•ᴥ•' }],
  // advisory_model_once.py _progress stages
  [/^Bridge Python started\./i,                       { action: 'sorting',       pixel: '•ᴥ•' }],
  [/^OPENROUTER_API_KEY visible/i,                    { action: 'nosing',        pixel: '•ᴥ•' }],
  [/^Redaction gate started\./i,                      { action: 'nosing',        pixel: '•ᴥ•' }],
  [/^Redaction gate blocked/i,                        { action: 'barking',       pixel: '!ᴥ!', isError: true }],
  [/^Redaction gate passed\./i,                       { action: 'nosing',        pixel: '•ᴥ•' }],
  [/^OpenRouter Fusion alias request started\./i,     { action: 'fetching',      pixel: '•ᴥ•' }],
  [/^OpenRouter Fusion alias response received\./i,   { action: 'crystallizing', pixel: '•ᴥ•' }],
  [/^Lead request started:/i,                         { action: 'fetching',      pixel: '•ᴥ•' }],
  [/^Lead response received:/i,                       { action: 'herding',       pixel: '•ᴥ•' }],
  [/^Panel requests started:/i,                       { action: 'herding',       pixel: '•ᴥ•' }],
  [/^Panel response received:/i,                      { action: 'herding',       pixel: '•ᴥ•' }],
  [/^Panel (?:blocked|network error|malformed):/i,    { action: 'sitting',       pixel: '.ᴥ.'  }],
  [/^Synthesis request started:/i,                    { action: 'crystallizing', pixel: '•ᴥ•' }],
  [/^Synthesis complete\./i,                          { action: 'pointing',      pixel: 'ᐡᴥᐡ' }],
  [/^Regular OpenRouter request started:/i,           { action: 'fetching',      pixel: '•ᴥ•' }],
  [/^Regular OpenRouter response received:/i,         { action: 'pointing',      pixel: 'ᐡᴥᐡ' }],
];
```

---

## 4. JSONL Training-Event Schema

Training events are emitted for Qwen3 4B Instruct specialist/sentinel training. They record
observable pipeline phases without capturing any secret or raw content.

### Schema Definition

```json
{
  "timestamp_ms": 1750684800000,
  "phase": "redaction_passed",
  "dog_action": "nosing",
  "route_tier": "HIGH",
  "mode": "foundups_fusion",
  "context_mode": "wsp_holo_skillz",
  "truth_label": "OBSERVED",
  "safe_for_training": true
}
```

### Field Definitions

| Field | Type | Allowed Values | Description |
|-------|------|----------------|-------------|
| `timestamp_ms` | integer | Unix epoch ms | Wall-clock time at event emission |
| `phase` | string | See phase table below | Pipeline phase identifier |
| `dog_action` | string | 12 defined actions | Corresponding RedDog action |
| `route_tier` | string | `"REGULAR"`, `"HIGH"`, `"ULTRA"` | WSP_15 classification tier |
| `mode` | string | `"openrouter_single"`, `"foundups_fusion"`, `"openrouter_fusion_alias"` | Resolved model mode |
| `context_mode` | string | `"none"`, `"wsp_holo"`, `"wsp_holo_git"`, `"wsp_holo_skillz"`, `"wsp_holo_git_skillz"`, `"active_editor"`, `"git_diff"` | Resolved context mode |
| `truth_label` | string | `"OBSERVED"` | Always OBSERVED for training events; pipeline phases are directly witnessed |
| `safe_for_training` | boolean | `true`, `false` | `false` if event emitted during error path or redaction-blocked; `true` otherwise |

### Phase Table

| Phase name | Dog action | Emitted by | Safe for training |
|-----------|-----------|------------|-------------------|
| `work_focus_received` | `sniffing` | Extension JS | `true` |
| `routing_resolved` | `sorting` | Extension JS | `true` |
| `context_assembled` | `tracking` | Extension JS | `true` |
| `redaction_started` | `nosing` | advisory_model_once.py | `true` |
| `redaction_passed` | `nosing` | advisory_model_once.py | `true` |
| `redaction_blocked` | `barking` | advisory_model_once.py | `false` |
| `lead_started` | `fetching` | advisory_model_once.py | `true` |
| `lead_done` | `herding` | advisory_model_once.py | `true` |
| `panel_started` | `herding` | advisory_model_once.py | `true` |
| `panel_done` | `herding` | advisory_model_once.py | `true` |
| `panel_blocked` | `sitting` | advisory_model_once.py | `false` |
| `synthesis_started` | `crystallizing` | advisory_model_once.py | `true` |
| `synthesis_done` | `pointing` | advisory_model_once.py | `true` |
| `single_started` | `fetching` | advisory_model_once.py | `true` |
| `single_done` | `pointing` | advisory_model_once.py | `true` |
| `repair_started` | `digging` | Extension JS | `true` |
| `completion_ok` | `pointing` | Extension JS | `true` |
| `completion_failed` | `growling` | Extension JS | `false` |
| `fusion_alias_started` | `fetching` | advisory_model_once.py | `true` |
| `fusion_alias_done` | `crystallizing` | advisory_model_once.py | `true` |

### Phases That Do NOT Emit Training Events

- `env_check` (`OPENROUTER_API_KEY visible`): sensitive diagnostic; MUST NOT emit training event.
- Any `onProgress` that contains model name but is not a phase boundary (e.g. per-panel model names in `Panel requests started: deepseek/..., moonshotai/...`): MUST NOT emit; model names are infrastructure metadata, not semantic phase data.
- Raw prompt/context assembly steps: MUST NOT emit.

### Emission Location (Phase 2)

Training events are emitted **from `advisory_model_once.py`** via a separate
`_training_event(phase, dog_action, route_tier, mode, context_mode)` function that writes
to a **separate stderr line** with `event: "training_event"`. The extension.js bridge
receiver already iterates stderr lines looking for `event: "progress"`; the training event
receiver mirrors that pattern, checking for `event: "training_event"`. The extension
collects these events in a bounded in-memory buffer (max 50 entries) per run.

---

## 5. What MUST Be Captured / MUST NOT Be Captured

### MUST Capture

- `phase` — which pipeline stage fired (from the bounded phase table above)
- `dog_action` — the RedDog action label corresponding to the phase
- `route_tier` — REGULAR / HIGH / ULTRA (classification result, not the prompt)
- `mode` — resolved model mode (not the model name/identifier string)
- `elapsed_ms` — wall-clock milliseconds since work focus submitted (trail display only; not in training event)
- `truth_label` — always `"OBSERVED"` for pipeline events (not model output content)
- `safe_for_training` — `false` on error/blocked paths; `true` on nominal paths
- `context_mode` — which context bundle was assembled (not the content of the bundle)

### MUST NOT Capture

| Prohibited content | Reason |
|--------------------|--------|
| Raw prompt text (pre-redaction or post-redaction) | Secret/PII exposure risk |
| Raw hidden context (WSP/HoloIndex/git diff content) | Contains repo internals |
| Raw model response content | Proprietary output; PII risk |
| API keys, tokens, auth headers | Credential leak |
| Full chain-of-thought text | Proprietary; secret risk |
| Model name strings in training events | Infrastructure metadata; creates model lock-in signal |
| `OPENROUTER_API_KEY visible: yes/no` output | Key presence is itself a security signal |
| Panel model names from `panel_start` text | Infrastructure metadata |
| Redaction gate `reason` string | May contain excerpt of blocked content |

### Boundary Enforcement Mechanism

The boundary is enforced at the **code path level**, not by policy alone:

1. The `_training_event()` function in `advisory_model_once.py` accepts only the five
   enum-bounded parameters: `phase`, `dog_action`, `route_tier`, `mode`, `context_mode`.
   It has no parameter for prompt, context, response, or model name. There is no code path
   from those values into the training event emitter.

2. The `env_check` stage is explicitly excluded from the phase table. The `_progress()`
   call for `env_check` is NOT wrapped with a `_training_event()` call. No training event
   fires at that stage.

3. Training events emitted on stderr are received by extension.js and stored in a bounded
   in-memory array. They are NOT written to disk, NOT included in the review packet, and
   NOT sent to any external endpoint in Phase 2.

4. `safe_for_training: false` is set by code branch (blocked/error return paths), not by
   runtime inspection of content.

---

## 6. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | TRAIL_MAPS_EXISTING_EVENTS_ONLY | PASS | All 16 bridge progress events mapped from pre-read of advisory_model_once.py + extension.js. No invented event strings. |
| 2 | NO_NEW_INFRASTRUCTURE_INVENTED | PASS | Phase 2 adds ~123 lines to extension.js only. advisory_model_once.py unchanged in Phase 2. No new modules, no new IPC channels. |
| 3 | REDACTION_GATE_UNCHANGED | PASS | `evaluate_redaction_gate()` call site in advisory_model_once.py is not touched. Trail maps post-gate events only; does not receive pre-gate content. |
| 4 | ROUTING_LOGIC_UNCHANGED | PASS | `classifyTaskForRedDog`, `resolveModelMode`, `resolveAutoEffort`, `resolveAutoContextMode` are read-only for trail mapping. Trail does not influence routing decisions. |
| 5 | NO_REPO_WRITES_FROM_TRAIL | PASS | Trail is purely in-webview DOM. No `fs.writeFile`, no shell, no git from trail update code path. |
| 6 | NO_SHELL_EXEC_FROM_TRAIL | PASS | `updateReddogTrail` only touches DOM elements. No `cp.spawn`, `cp.exec`, `execFileSync` in trail update path. |
| 7 | TRAINING_EVENTS_SECRET_FREE | PASS | Schema in Section 4 has no field for prompt, response, model name, or key. Enforcement is structural (Section 5). |
| 8 | PIXEL_GRAMMAR_DEFINED | PASS | Five pixel values defined: `.ᴥ.`, `•ᴥ•`, `!ᴥ!`, `ᐡᴥᐡ`, `~~~`. Idle cycle and per-action assignments in Section 2. |
| 9 | GAP_EVENTS_DOCUMENTED | PASS | In-flight HTTP gap documented in Section 2. Covered by elapsed timer + 10s sitting fallback. No bridge change required. |
| 10 | PHASE2_SCOPE_BOUNDED | PASS | Phase 2 touches extension.js only. advisory_model_once.py changes deferred to Phase 3 (training events). Exact line areas identified in Section 3. |

---

## 7. WSP_15 Priority Table

| Priority | Item | Rationale |
|----------|------|-----------|
| P0 | Implement `updateReddogTrail` + `REDDOG_PROGRESS_ACTIONS` in extension.js | Directly solves the 012-visible stall problem. Unblocks trust in long Fusion runs. |
| P0 | Wire `matchReddogProgress` into `addStatus` | All existing bridge events start triggering the trail without changing bridge code. |
| P0 | Elapsed timer with `sitting` fallback at 10s no-event | Covers the in-flight HTTP gap (104s-172s) which is the primary stall window. |
| P1 | Idle pixel cycle animation | Improves perceived responsiveness when bridge has not yet emitted its first event. |
| P1 | `data-active` CSS attribute for color signaling | Makes error (`!ᴥ!`) and completion (`ᐡᴥᐡ`) visually distinct from active states. |
| P1 | Update `verify_extension_contract.js` with trail existence checks | Prevents regression of the trail strip in future hardening slices. |
| P2 | JSONL training event emission in advisory_model_once.py | Useful for Qwen3 specialist training but not required for 012-facing stall fix. |
| P2 | `REDDOG_WORKING_TRAIL_PHASE1` roadmap entry in ROADMAP.md | Documentation hygiene; does not affect runtime. |

---

## 8. Acceptance Criteria

All criteria must be verifiable by the gate reviewer without running live API calls.

1. **Visible within 1s:** Within 1 second of 012 submitting a work focus, the trail strip
   shows `.ᴥ. sniffing` (triggered by the webview-local `sendWorkFocus` event, before the
   bridge process even starts).

2. **Every bridge event mapped:** Every `_progress` call in `advisory_model_once.py` and
   every `onProgress` call in `callFusion` matches at least one pattern in
   `REDDOG_PROGRESS_ACTIONS`. No bridge event falls through without a trail update.

3. **Long Fusion runs covered:** When running for >30s with no new progress event, the
   trail shows `.ᴥ. sitting <elapsed>` via the 10s no-event fallback. Elapsed time
   updates every 1s via `setInterval`.

4. **Redaction block shows barking:** When `reason === 'redaction_blocked'` arrives in the
   result message, the trail shows `!ᴥ! barking` before `setRunning(false)` resets it,
   AND `addStatus` for the redaction-blocked progress line also shows `!ᴥ! barking`. The
   network is NOT called (this is verifiable from existing redaction gate tests).

5. **Completion shows pointing:** On a successful result (`msg.result.ok === true`), the
   trail shows `ᐡᴥᐡ pointing` for the duration of `setRunning(false)` processing, then
   resets to `~~~ idle`.

6. **Training event schema compliant:** Each training event emitted on stderr contains
   exactly the fields defined in Section 4. No prompt, response, model name, or key field
   is present. `safe_for_training` is `false` on blocked/error paths.

7. **Feature does NOT change routing:** `classifyTaskForRedDog`, `resolveModelMode`,
   `resolveAutoEffort`, `resolveAutoContextMode` return identical values with and without
   the trail code present.

8. **Feature does NOT change model calls:** The `callFusion` promise, `payload` object,
   `_run_foundups_fusion`, `_openrouter_fusion_alias`, and single-model paths are
   structurally unchanged. The only new code in those paths is `matchReddogProgress(text)`
   inside the `onProgress` callback.

9. **Tests cover all tier/mode combinations:**
   - REGULAR tier + `openrouter_single`: trail shows `pointing` on completion.
   - HIGH tier + `foundups_fusion`: trail shows `herding` during panel phase.
   - ULTRA tier + `foundups_fusion`: trail shows `nosing` at redaction gate.
   - Redaction blocked: trail shows `barking`; no model event fires after.
   - Repair pass: trail shows `digging` on "Output schema incomplete" event.
   - Fusion panel partial block: trail shows `sitting` on `Panel blocked:` event.

---

## 9. Stop Conditions

Implementation MUST stop immediately if any of the following conditions are detected:

1. **Raw hidden prompt/context exposure:** Any code path that passes the pre-redaction
   prompt text, the bounded context packet content, or the WSP task prompt body into the
   trail update or training event emitter.

2. **Secret persistence:** Any `fs.writeFile`, `fs.appendFile`, SQLite write, or
   `localStorage` write that stores training events or trail state across sessions.

3. **Raw API payload logging:** Any code that passes the full OpenRouter request body or
   response body to `addStatus`, `updateReddogTrail`, or any training event field.

4. **Repo writes from trail:** Any `cp.spawn`, `cp.exec`, `git`, or filesystem mutation
   triggered by a trail update or training event handler.

5. **Redaction gate bypass:** Any code path that sends content to `_post_openrouter` or
   `_chat_completion` that has not passed through `evaluate_redaction_gate`.

6. **HoloIndex/Fusion/Skillz readiness overclaim:** Any assertion in tests or docs that
   claims the working trail proves HoloIndex retrieval quality, Fusion panel correctness,
   or Skillz routing success without test evidence.

7. **Overlap with #841 livechat work:** Any change to `modules/communication/`,
   `livechat`, or YouTube comment handling triggered by this slice.

---

## 10. Open Questions for 012

These are genuine architect decisions required before Phase 2 implementation begins.

1. **Training event buffer disposition:** Phase 2 stores training events in a bounded
   in-memory array (max 50 per run). Should this array be (a) discarded at
   `setRunning(false)`, (b) appended to the review packet that `Ctrl+Shift+C` copies,
   or (c) written to a local `.jsonl` log file on disk? Option (b) is lowest risk.
   Option (c) requires a filesystem write path which conflicts with Stop Condition 4 unless
   scoped to an explicit 012-approved output path.

2. **Pixel character rendering scope:** The pixel characters `.ᴥ.`, `•ᴥ•`, `!ᴥ!`,
   `ᐡᴥᐡ` rely on Unicode characters that may not render in all VS Code font
   configurations. Should Phase 2 include a font-fallback test (checking that the
   characters render in the webview's `--vscode-editor-font-family`) or ship as-is and
   accept a text-only fallback?

3. **Elapsed timer reset on repair pass:** When a repair pass starts, should the elapsed
   timer (a) reset to 0 (so 012 sees the repair as a fresh run), or (b) continue from
   the point the repair was triggered (so 012 sees the total wall-clock time including
   the repair)? Option (b) is recommended as it makes long total durations visible.

---

*Design contract authored by 0102 (AUTHOR worker). Do not self-land. Awaiting independent gate verdict and sovereign nod from 012 before Phase 2 implementation.*
