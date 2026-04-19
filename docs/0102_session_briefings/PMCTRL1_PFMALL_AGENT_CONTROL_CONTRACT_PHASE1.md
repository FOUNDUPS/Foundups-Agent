# Worker PMCTRL1 — PFMALL_AGENT_CONTROL_CONTRACT_PHASE1

**Issued by**: 012 (architect)
**Routed to**: Antigravity3
**Routed via**: 0102 (CTO auditor lane)
**Issued**: 2026-04-19
**Directive**: **Go**, but stop if the preflight detects activity.

---

## Required Preflight - Activity Collision Check

Before making changes:

- Run `git status --short`.
- Inspect recent changes in:
  - `public/member/`
  - `modules/ai_intelligence/pfmall_discovery/`
  - `modules/communication/youtube_channel_pull/`
  - RedDog / account concierge files
- Check for active frontend/test/python/node processes.
- If activity is detected, STOP and report:
  - active paths
  - timestamps/evidence
  - likely owning slice if inferable
  - recommendation: wait / stand down / ask 012

## Goal

Define and implement the first safe pfMALL agent control contract so 012, RedDog, 0102, and native agents can control the video wall through structured commands instead of ad hoc DOM/UI driving.

## Architecture

- pfMALL remains the video wall runtime.
- Agent/native/RedDog control must use structured commands.
- Temporary session wall state must remain separate from permanent FoundUp catalog state.

## Scope

1. Inspect current pfMALL tile field runtime, shell bridge, account concierge / RedDog density policy, and tests.
2. Add a browser-side command dispatcher with structured commands:
   - `inspect_state`
   - `set_layout`
   - `load_videos`
   - `play_tile`
   - `expand_tile`
   - `collapse_tile`
   - `reset_session`
3. Support postMessage/WebView-style command input and response:
   - request includes `source`, `target`, `command`, `request_id`, `payload`
   - response includes `source`, `request_id`, `status`, `result` or `error`
4. Enforce existing device policy on layout commands:
   - phones cannot force desktop presets like `6x3`
   - manual/user override behavior must remain intact
5. Add event emission:
   - `layout_denied`
   - `video_loaded`
   - `video_failed`
   - `state_changed`
6. `load_videos` must create temporary/session wall state only.
   - No mutation of `mall-video-catalog.json`
   - No permanent FoundUp catalog apply
7. Add tests for:
   - valid command dispatch
   - invalid command rejection
   - phone layout denial
   - desktop layout allowed
   - `inspect_state` returns truthful state
   - `load_videos` does not mutate catalog
   - reset session restores prior catalog-backed state or a clean empty session, depending current runtime design
8. Document command schema in:
   - `public/member/INTERFACE.md`
9. Update:
   - `public/member/ModLog.md`
   - `public/member/tests/TestModLog.md` if test convention requires it

## Out of scope

- No floating search UI.
- No live YouTube web search.
- No permanent catalog apply.
- No native app implementation.
- No backend service.
- No RedDog autonomous repair yet.
- No broad UI redesign.
- No merge of unrelated PRs.

## Dependency / branch note

- YT1 PR #368 is unrelated to PMCTRL1. Do not wait on it unless local branch state requires sync.
- Branch from current clean `main`.
- If #368 is still open, leave it alone.

## Deliverables

- pfMALL control dispatcher
- tests
- INTERFACE update
- ModLog/TestModLog update
- completion report with command examples and exact tests

## WSP 97

Truthfully distinguish:

- temporary session wall state
- permanent FoundUp catalog state
- command accepted
- command denied by policy
- command failed
- state changed

Do not claim RedDog/native control is complete beyond this browser-side command contract.
