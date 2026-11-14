**Bridge interface: Auth And Operations.**

[Interface directory](../../INTERFACE.md). Qualification boundaries below remain as recorded.

<a id="contract-098"></a>

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FOUNDUPS_WEBHOOK_TOKEN` | Yes | Shared secret with OpenClaw |
| `OPENCLAW_GATEWAY_URL` | No | OpenClaw gateway (default: ws://127.0.0.1:18789) |
| `MOLTBOT_GATEWAY_URL` | No | Legacy name (fallback) |
| `OPENCLAW_RESIDENT_ENABLED` | No | Register resident OpenClaw webhook runtime at startup (default on) |
| `OPENCLAW_RESIDENT_AUTOSTART` | No | Auto-start broker-managed resident OpenClaw service after preflights (default on) |
| `OPENCLAW_SUPERVISOR_ENABLED` | No | Register broker-managed OpenClaw supervisor runtime at startup (default on) |
| `OPENCLAW_SUPERVISOR_AUTOSTART` | No | Auto-start the OpenClaw supervisor after bootstrap (default on) |
| `OPENCLAW_SUPERVISOR_POLL_SEC` | No | Poll interval for the OpenClaw supervisor state machine (default `10`) |
| `OPENCLAW_SUPERVISOR_ALLOW_RESTART` | No | Allow the supervisor to restart resident OpenClaw when it is down (default on) |
| `OPENCLAW_SUPERVISOR_MAX_RESTARTS` | No | Maximum resident OpenClaw restart attempts allowed inside the supervisor repair window (default `3`) |
| `OPENCLAW_SUPERVISOR_RESTART_WINDOW_SEC` | No | Rolling window used for restart-budget enforcement before escalation (default `900`) |
| `OPENCLAW_RESIDENT_HOST` | No | Host for resident OpenClaw webhook service (default `127.0.0.1`) |
| `OPENCLAW_RESIDENT_PORT` | No | Port for resident OpenClaw webhook service (default `18800`) |
| `OPENCLAW_RESIDENT_LOG_LEVEL` | No | Uvicorn log level for resident service (default `info`) |
| `OPENCLAW_CONVERSATION_BACKEND` | No | `openclaw` (default) or `ironclaw` for sidecar conversational runtime |
| `OPENCLAW_IRONCLAW_PREFLIGHT` | No | Enable IronClaw startup readiness preflight (default on) |
| `OPENCLAW_IRONCLAW_PREFLIGHT_ALWAYS` | No | Run IronClaw readiness preflight even when backend is not `ironclaw` (default off) |
| `OPENCLAW_IRONCLAW_PREFLIGHT_ENFORCED` | No | Explicitly block startup when IronClaw readiness fails |
| `OPENCLAW_NO_API_KEYS` | No | `1` disables external/cloud LLM calls in OpenClaw/FAM paths |
| `OPENCLAW_ALLOW_EXTERNAL_LLM` | No | `1` allows AI Gateway cloud fallback (auto-disabled when `*_NO_API_KEYS=1`) |
| `OPENCLAW_OLLAMA_MODEL` | No | Ollama model ID for local fallback (default `qwen2.5-coder:7b`) |
| `IRONCLAW_BASE_URL` | No | IronClaw OpenAI-compatible endpoint (default `http://127.0.0.1:3000`) |
| `IRONCLAW_MODEL` | No | Model ID sent to IronClaw `/v1/chat/completions` |
| `IRONCLAW_AUTH_TOKEN` | No | Optional bearer token for IronClaw gateway auth |
| `IRONCLAW_NO_API_KEYS` | No | `1` enables key-isolation mode for IronClaw runtime launch |
| `IRONCLAW_START_CMD` | No | Command used by CLI submenu to start IronClaw gateway |

<a id="contract-099"></a>

## Auth Headers

- `Authorization: Bearer <token>`
- `x-openclaw-token: <token>` (preferred)
- `x-moltbot-token: <token>` (legacy)

<a id="contract-100"></a>

### OpenClaw DAE and ExecutionBundle

The bounded DAE loop, WSP 77 operating contract, example, and field contract
are preserved in
[`docs/OPENCLAW_DAE_EXECUTION_BUNDLE_INTERFACE_ARCHIVE.md`](../../docs/OPENCLAW_DAE_EXECUTION_BUNDLE_INTERFACE_ARCHIVE.md).
0102 remains architecture authority; OpenClaw remains a bounded executor.

Design principles:
- Bundles are execution aids, not architecture authorities
- Compact only — no giant context dumps
- Deterministic — same query produces same bundle shape
- Suitable for bounded doer, not open-ended cognition

<a id="contract-101"></a>

### Intent Categories

| Category | Route | Permission | Description |
|----------|-------|------------|-------------|
| QUERY | holo_index | ADVISORY | Read-only search/lookup |
| COMMAND | wre_orchestrator | DOCS_TESTS+ | Execute tasks via WRE |
| MONITOR | ai_overseer | ADVISORY | System status/health |
| SCHEDULE | youtube_shorts_scheduler | METRICS | Time-bound scheduling |
| SOCIAL | communication | METRICS | Engagement (comment/post) |
| SYSTEM | infrastructure | SOURCE | System admin (commander only) |
| AUTOMATION | auto_moderator_bridge | METRICS | YouTube automation routing |
| FOUNDUP | fam_adapter | METRICS | FoundUp launch and FAM workflows |
| CONVERSATION | digital_twin | ADVISORY | Casual dialogue |

<a id="contract-102"></a>

### Generic DAE Runtime Control

Broker-managed runtime commands are now available through OpenClaw:
- `list launchable daes`
- `status openclaw`
- `status openclaw live`
- `tail openclaw`
- `tail openclaw supervisor`
- `watch openclaw since 42`
- `status openclaw supervisor live`
- `status holodae`
- `stop holodae`
- `stop git push dae`
- `launch social media dae`
- `stop social media dae`
- `stop training system`
- `status liberty alert`

Routing contract:
- OpenClaw deterministic runtime classification
- `dae_runtime_adapter.py`
- central `DAELaunchBroker`

Authorization and acquisition (repair 2026-09-23):
- Unmatched/unresolved commands and unauthorized mutations acquire neither collaborator. `list`/`status` and authorized launch/start/run/stop acquire only broker; tail/follow/live status acquire only observer.
- `launch`/`stop` require `012` authority. Exact responses/callbacks and required creating-getter semantics remain; [fixed regression evidence](../../tests/README.md#rsi-adapter-acquisition-and-linkedin-previews) passes28 after26 baseline failures. Required getters can construct runtime components, so whole-command effect freedom is not established.

Resident OpenClaw contract:
- `main.py` registers `openclaw` as a launchable DAE using `scripts/launch.py`
- `main.py` registers `openclaw_supervisor` as a separate broker-managed runtime
- `main.py` runs IronClaw readiness preflight before runtime bootstrap when IronClaw is the active backend
- bootstrap can autostart the resident webhook service after preflight
- bootstrap can autostart the supervisor state machine after resident/runtime registration
- CLI menu option `3` now reuses the broker-managed runtime when available instead of spawning a competing subprocess
- live supervision now exposes a cursor contract:
  - `tail <dae>` = recent window
  - `watch|follow <dae> since <sequence>` = incremental follow with returned `next_cursor`

Resident RedDog live-canary contract:
- Entry point: `python -m modules.communication.moltbot_bridge.src.reddog_resident_live_canary`
- Default mode performs readiness checks only and writes an audit-safe receipt outside the repository.
- Live invocation requires Linux, `--execute`, and exact confirmation token `REDDOG_RESIDENT_LIVE_CANARY_PHASE1`.
- The selected profile is fixed to `signed_0102_bounded_code_fusion_worktree_draft_pr_pattern_memory`.
- The harness delegates to `main.run_reddog_resident_queue_control_loop_preflight`; it does not duplicate queue stages.
- `LIVE_PROOF_COMPLETE` requires a shared-lock-proven, newly persisted `reddog_resident_control_loop_receipt.v1` with accepted PASS, matching repository digest, and positive serial progress; changed pre/post chain revisions; a canonically recomputable chain revision and new persisted final-revision receipt witness; matching queue/slice and work-order/slice/head lineage; accepted verified draft-PR evidence; an external Git worktree present in the repository worktree registry with accepted invoke/create decisions and matching `HEAD`; and PatternMemory admission/record/digest identities recomputed from the canonical SQLite row.
- `--receipt-path` may name only canonical `live_canary_receipt.json` inside the runtime root. Any alternate receipt must resolve outside both repository and runtime roots; reserved runtime artifacts and nested collisions fail before execution.
- An explicit `artifact_generator_mode` / `--artifact-generator-mode` overrides `REDDOG_ARTIFACT_GENERATOR_MODE`; `foundups_fusion` is the default only when both are absent. Canonical alternatives are `openclaw_gateway` and `hermes_api`; explicit empty or unsupported values reject. The additive receipt field binds the selected mode into its identity, not proof of provider execution.
- `READY_FOR_EXECUTION` does not claim that a live canary ran. Missing authority artifacts, signer socket, Git/GitHub readiness, or declared model-provider identity returns `BLOCKED`. Fusion additionally checks OpenRouter identity/key presence; Hermes reads and discards its existing confined service credential; OpenClaw checks executable availability. No credential values are serialized.
- Provider-specific readiness does not replace invocation-time signed topology, capability, budget, service-identity, or confinement checks. The guarded profile and confirmation remain unchanged.
- The surface has no signer launch, principal signing-key resolution, PR-ready, merge, reward, or HoloIndex re-index authority. Readiness acquires the existing lock and writes its receipt; it is not an effect-free pure function.

Transport-neutral grounding runs at most two deterministic HoloIndex owner
queries per semantic target under one shared 16-query, 30-second budget.
Refinement derives only from the original target; model or result content cannot
choose a later query. Holo hits are candidate locators, not evidence. Selected
paths must be regular current-HEAD Git blobs with verified object IDs; broad
audits require implementation plus test, contract, or WSP corroboration.
Receipt v2 binds evidence, generation, root, HEAD, and resource bounds; model
consumption rehydrates it. Legacy producers retain receipt v1.

Entity-scoped audits may use the existing fail-closed repository fallback only
after bounded owner evidence remains unavailable, stale, or insufficient. Exact
fixed-policy limits require implementation plus test/contract evidence. Selection
and consumption read exact Git HEAD; dirty overlays are ignored and untracked
candidates reject. Grounding integrity never replaces signed work-order authority.

<a id="contract-103"></a>

### OpenClaw Supervisor Contract

Canonical 0102 lifecycle owner:
- runtime id: `openclaw_supervisor`
- implementation: `src/openclaw_supervisor.py`
- broker launch wrapper: `scripts/launch.py`

Current explicit states: `BOOT -> PREFLIGHT -> OBSERVE -> TRIAGE -> PLAN -> EXECUTE -> VERIFY -> REMEMBER -> ESCALATE -> IDLE_WATCH`.
Current operational rule:
- the supervisor owns the enabled self-audit loop and exposes [per-attempt scan status](../../../../infrastructure/wre_core/INTERFACE.md#self-audit-scan-observations) separately from event count
- `main.py` only starts direct self-audit as a fallback when supervisor is disabled
- resident OpenClaw restarts are policy-gated through the broker/runtime surface
- restart attempts use `OPENCLAW_SUPERVISOR_MAX_RESTARTS` and `OPENCLAW_SUPERVISOR_RESTART_WINDOW_SEC`
- when the repair budget is exhausted, the supervisor escalates instead of retrying indefinitely
- the supervisor advances a DAEmon follow cursor every cycle so repair decisions are tied to observed runtime history
- IronClaw runtime readiness is validated at startup before resident/runtime bootstrap when IronClaw is the selected backend
- post-merge HoloIndex observation uses one background worker; OpenClaw claims
  each exact-SHA task with compare-and-swap semantics and the domain executor
  owns atomic completion
- `execute_task` requires the one-use claim ID and context digest; calls
  without that capability stop before the authority transaction

Post-merge HoloIndex configuration (live path accepted at exact main `cfd1e0051`; later HEADs require new evidence):
- `HOLOINDEX_POSTMERGE_COORDINATOR_ENABLED` defaults to `1`; set `0` to disable.
- `HOLOINDEX_POSTMERGE_COORDINATOR_INTERVAL_SEC` sets polling (minimum 30 seconds).
- `REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT` selects the clean authority worktree.

<a id="contract-104"></a>

### PQN Runtime Control

PQN research runtime can now be controlled through research intent phrases:
- `launch pqn research`
- `status pqn research`
- `stop pqn research`
- `launch pqn architect`
- `status pqn architect`

Routing contract:
- OpenClaw -> `pqn_research_adapter.py`
- `pqn_research_adapter.py` -> central `DAELaunchBroker`
- `DAELaunchBroker` -> broker-managed PQN runtime entrypoints in `modules/ai_intelligence/pqn/scripts/launch.py`

<a id="contract-105"></a>

### PQN Theory-Archive Simulation Control

PQN simulation can now be triggered directly through research intent phrases:
- `run pqn simulation`
- `launch pqn simulation`
- `status pqn simulation`
- `stop pqn simulation`
- `tail pqn simulation`
- `watch pqn simulation since 42`
- `show pqn simulation plan`

Routing contract:
- `run|launch|status|stop pqn simulation`:
  - OpenClaw deterministic runtime classification or `pqn_research_adapter.py`
  - `DAELaunchBroker`
  - `modules/ai_intelligence/pqn/scripts/launch.py:run_pqn_simulation_once()`
- `show pqn simulation plan`:
  - OpenClaw RESEARCH route
  - `pqn_research_adapter.py`
  - `PQNAlignmentDAE.get_theory_archive_simulation_plan(...)`
- supervision:
  - generic DAE runtime observer surface
  - `tail|watch pqn simulation ...`

Operational rule:
- simulation execution is a broker-managed runtime lane
- simulation planning remains a read-only research query
- archive remains hypothesis input only
- returned interpretation remains comparative, not ontological

<a id="contract-106"></a>

### FOUNDUP Route Contract (FAM Adapter)

<a id="contract-107"></a>

#### Catalog Commands (p.fMALL Integration)

- `list foundups` - Show all FoundUps in catalog
- `foundup catalog [category]` - Browse catalog by category (marketplace, media, science, games, community)
- `foundup status <name>` - Show FoundUp status (manifest + state overlay)
- `open <foundup>` - Get routing target URL (`/f/{foundup_id}`)

Catalog commands consume:
- Static manifests from `foundup_manifest.json` (per PFMALL_FOUNDUP_MANIFEST_SCHEMA.md)
- State overlay via provider interface (per PFMALL_STATE_OVERLAY_CONTRACT.md)
- Degrades gracefully when state provider unavailable (shows "unknown" status)

<a id="contract-108"></a>

#### Launch Commands

- `launch foundup <name> with token <SYMBOL>`
- `create foundup <name> token <SYMBOL>`

Token symbol resolution:
- If token is omitted, parser auto-generates from FoundUp name.
- If token is `AUTO` (or legacy `FUP` seed), adapter auto-generates and resolves collisions.
- Collision resolution is deterministic (`BASE`, `BASE2`, `BASE3`, ...), then handed to Agent Market.

<a id="contract-109"></a>

### Autonomy Tiers (Graduated)

| Tier | Who | Can Do |
|------|-----|--------|
| ADVISORY | Anyone | Read-only: search, status, chat |
| METRICS | Commander | + Write metrics/logs |
| DOCS_TESTS | Commander | + Edit tests and docs |
| SOURCE | Commander (explicit) | + Edit source code |

<a id="contract-110"></a>

### WSP 73 Partner-Principal-Associate

- **Partner**: OpenClaw bridge receives intent, owns dialogue
- **Principal**: OpenClaw DAE decomposes tasks, selects domain DAEs
- **Associates**: Domain DAEs execute (communication, platform, dev, content)

<a id="contract-111"></a>

### Security
- Non-commanders: ADVISORY only (no mutations)
- COMMAND/SYSTEM intents blocked for non-commanders (WSP 50)
- `run_skill_scan(skills_dir, report_dir=...)` owns private report/TMP files per call,
  validates before publishing a mutable latest diagnostic, and fails closed on errors.
  [Full scanner contract](../../README.md#skill-safety-gate-cisco-skill-scanner): `_ensure_skill_safety(force=False, *, details=False)` returns `bool`; literal `details=True` returns local `(bool, str)`. The process consumer validates both fields; malformed results raise `TypeError`/`ValueError` before downstream execution. Latest diagnostics and policy-drift rejection remain; no effect/promotion authority.
- Secret patterns (AIza*, sk-*, oauth_token*) redacted from output
- Key-isolation mode:
  - `OPENCLAW_NO_API_KEYS=1` blocks cloud provider fallback in conversation/FAM paths.
  - `IRONCLAW_NO_API_KEYS=1` scrubs provider API keys from IronClaw launch subprocess env.
- All decisions logged to WRE pattern memory (WSP 22)
- Standalone action CLI writes `SkillOutcome` records to PatternMemory with
  `skill_name=action_cli_<route>_<action>` (WSP 60/48 memory recall path).
- Skill boundary policy (workspace skills vs internal `skillz`) is codified in:
  `modules/communication/moltbot_bridge/docs/SKILL_BOUNDARY_POLICY.md`
- MONITOR responses include OpenClaw skill safety gate state:
  - status, required/enforced, last check timestamp, and gate message.
- MONITOR/SYSTEM routes now expose broker-managed DAE runtime inspection and control.

<a id="contract-112"></a>

### Skill Safety Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENCLAW_SKILL_SCAN_REQUIRED` | No | `1` fail-closed if scanner missing (default) |
| `OPENCLAW_SKILL_SCAN_ENFORCED` | No | `1` block risky scans above threshold (default) |
| `OPENCLAW_SKILL_SCAN_MAX_SEVERITY` | No | Scanner threshold (default `medium`) |
| `OPENCLAW_SKILL_SCAN_TTL_SEC` | No | Retained (`900`); workspace TTL reuse disabled, every call scans |
| `OPENCLAW_SKILL_SCAN_ALWAYS` | No | Retained; every guard call scans even with `0`/`force=False` |
| `OPENCLAW_SKILL_MANIFEST_REQUIRED` | No | `1` require workspace skill hash manifest (default) |
| `OPENCLAW_SKILL_MANIFEST_ENFORCED` | No | `1` block on manifest mismatch/missing (default) |
| `OPENCLAW_SKILL_MANIFEST_VERIFY_SIGNATURE` | No | `1` verify HMAC signature in manifest |
| `OPENCLAW_SKILL_MANIFEST_ALLOW_EXTRA` | No | `1` allow skill files not listed in manifest |
| `OPENCLAW_SKILL_MANIFEST_FILE` | No | Optional override path to manifest JSON |
| `OPENCLAW_SKILL_MANIFEST_HMAC_KEY` | No | Optional HMAC key for signature verification |

<a id="contract-113"></a>

### Rate Limiting (Webhook)

Token bucket rate limiting per sender and channel (WSP 95 defense-in-depth):

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENCLAW_RATE_LIMITING_ENABLED` | No | `0` to disable rate limiting (default `1`) |
| `OPENCLAW_RATE_SENDER_PER_SEC` | No | Tokens/sec per sender (default `2.0`) |
| `OPENCLAW_RATE_SENDER_BURST` | No | Burst capacity per sender (default `10.0`) |
| `OPENCLAW_RATE_CHANNEL_PER_SEC` | No | Tokens/sec per channel (default `5.0`) |
| `OPENCLAW_RATE_CHANNEL_BURST` | No | Burst capacity per channel (default `20.0`) |

When limits exceeded, webhook returns HTTP 429 with `X-Retry-After` header.

```python
from modules.communication.moltbot_bridge.src.webhook_receiver import WebhookRateLimiter

limiter = WebhookRateLimiter()
allowed, bucket_type = limiter.check_allowed(sender="user123", channel="telegram")
# Returns (True, None) if allowed, or (False, "sender"|"channel") if blocked
```

<a id="contract-114"></a>

### SOURCE Tier Permission Check

SOURCE tier operations require explicit permission via AgentPermissionManager (fail-closed):

```python
from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE

dae = OpenClawDAE()
granted, reason = dae._check_source_permission(intent)
# granted=False, reason="permission manager unavailable" if manager missing
# granted=False, reason=<agent_permission_manager reason> if denied
# granted=True, reason="granted" if allowed
```

Permission denied events emitted with 60s dedupe window (WSP 71 forensics).

<a id="contract-115"></a>

### COMMAND Graceful Degradation

When WRE is unavailable, COMMAND intents return deterministic advisory fallback:

```python
# Returns advisory with:
# - "Advisory Mode" header
# - Command recognition
# - Three actionable options (CLI, retry, query mode)
# - Optional error detail
```

<a id="contract-116"></a>

## WSP Compliance

- **WSP 46**: WRE Protocol (execution cortex)
- **WSP 49**: Standard module structure
- **WSP 50**: Pre-Action Verification (preflight gate)
- **WSP 73**: Digital Twin architecture integration
- **WSP 77**: Agent coordination (4-phase execution)
- **WSP 91**: Observability (structured logging)
- **WSP 96**: Skill execution (micro chain-of-thought)

<a id="contract-117"></a>

## WSP 97 Internal Module Boundaries

OpenClaw runtime responsibilities are now split into dedicated modules under `src/`.
This is the canonical internal layout for future work:

- `openclaw_dae.py`: facade only
- `openclaw_intent_planner.py`: classify -> preflight -> plan
- `openclaw_permission_policy.py`: autonomy tier + containment + skill safety
- `openclaw_execution_routes.py`: non-social route execution
- `openclaw_social_controller.py`: social-routing bridge
- `openclaw_conversation_engine.py`: dialogue execution
- `openclaw_model_policy.py`: model selection and switching
- `openclaw_identity_context.py`: identity + context-pack builders
- `openclaw_runtime_support.py`: runtime/model probes and autostart
- `openclaw_status_surface.py`: operator-facing status helpers
- `openclaw_process_loop.py`: full autonomy loop orchestration
- `openclaw_result_memory.py`: validate + remember
- `openclaw_turn_state.py`: token telemetry and turn cancellation
- `openclaw_action_ledger.py`: DAEmon action reporting
- `openclaw_provider_chain.py`: external/IronClaw provider chain
- `openclaw_bootstrap_config.py`: constructor-time control-plane state

Refactor status:
- `openclaw_dae.py` is currently `1580` lines: inherited WSP 62 hard-limit debt; the facade split remains incomplete
- execution-plane resolution now matches `WSP_97`: resolve intent -> gate -> plan -> route -> validate -> remember

<a id="contract-118"></a>

## Runtime Supervision Commands

OpenClaw can now read the DAEmon live ledger for itself and broker-managed DAEs:

- `tail openclaw`
- `status openclaw live`
- `tail pqn research`
- `status pqn research live`
- `tail holodae`

These commands request ledger reads and acquire only the observer. Required observer construction may still change runtime state; the inert regression evidence above does not certify whole-command effect freedom.

<a id="contract-119"></a>

## Skill Evolution Loop

<a id="contract-120"></a>

### Phase 1: Report Surface (Read-Only)

```python
from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
    build_skill_evolution_report,
    skill_evolution_report_due,
    write_skill_evolution_report,
)

# Check if report generation is due (missing or stale)
if skill_evolution_report_due(repo_root, max_age_sec=3600):
    report = build_skill_evolution_report(pattern_memory)
    write_skill_evolution_report(repo_root, report)
```

Phase 1 is **read-only**: surfaces review candidates from PatternMemory without mutating WRE skills or scheduling promotions.

Report contract:
- `generated_on`: ISO timestamp
- `period_days`: Evaluation window
- `skills_evaluated`: Count of `openclaw_*` skills found
- `candidate_count`: Skills with `status=candidate_for_review`
- `candidates[]`: Array with `skill_name`, `execution_count`, `avg_fidelity`, `recommendation`

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCLAW_SKILL_EVOLUTION_ENABLED` | `0` | Enable Phase 1 report generation on idle path |

<a id="contract-121"></a>

### Phase 2: Mutation Surface (Bounded, Gated)

```python
from modules.communication.moltbot_bridge.src.openclaw_skill_evolution import (
    build_mutation_surface_report,
    mutation_surface_report_due,
    write_mutation_surface_report,
)

# Only due when gate enabled AND report missing/stale
if mutation_surface_report_due(repo_root, max_age_sec=3600):
    report = build_mutation_surface_report(pattern_memory)
    write_mutation_surface_report(repo_root, report)
```

Phase 2 adds a **bounded mutation surface** that:
- Surfaces A/B test status and promotion readiness per skill
- Gates all mutation operations behind explicit env vars (fail-closed)
- Reuses existing WRE primitives (PatternMemory, WRESkillsRegistryV2)
- Does NOT introduce duplicate A/B or promotion engines

Mutation status values:
- `stable`: High fidelity, no action needed
- `ab_test_active`: A/B test in progress
- `eligible_for_ab`: Candidate for A/B test scheduling
- `blocked`: Insufficient data or other blocker

Report contract (extends Phase 1):
- `enabled`: Whether mutation surface gate is on
- `summary`: Counts by mutation_status
- `gates`: Current gate states
- `candidates[]`: Extended with `mutation_status`, `active_ab_test`, `ab_promotion_status`, `promotion_readiness`

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCLAW_MUTATION_SURFACE_ENABLED` | `0` | Enable Phase 2 mutation surface report generation |
| `OPENCLAW_AB_SCHEDULING_ENABLED` | `0` | Enable A/B test scheduling (future) |
| `OPENCLAW_PROMOTION_ENABLED` | `0` | Enable skill promotion (future) |

**All gates are fail-closed by default**. Setting to `"0"` or leaving unset disables the feature.

<a id="contract-122"></a>

### Supervisor Integration

Both Phase 1 and Phase 2 reports are generated on the supervisor **idle path only** (lowest priority):

```python
# In openclaw_supervisor.py _triage()
idle_result = {"kind": "idle", "reason": "resident_openclaw_healthy"}
if skill_evolution_report:
    idle_result["skill_evolution_report"] = skill_evolution_report
if mutation_surface_report:
    idle_result["mutation_surface_report"] = mutation_surface_report
```

Higher-priority work (restarts, autonomous tasks, self-audit events) blocks skill evolution report generation.

<a id="contract-123"></a>

### RedDog Governed Work-Order Policy Gate (no execution)

```python
from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    evaluate_work_order_policy_gate,  # (order, *, now, seen_nonces, permission_ttl_seconds, permission_expires_at, require_signed_authority, signature_verification_result) -> PolicyGateReceipt
    evaluate_signed_work_order_policy_gate,  # verifies E1 identity/work-authority, then policy-gates
    PolicyGateReceipt,
    POLICY_ACCEPT,
    POLICY_REJECT,
    POLICY_ACCEPT_WITH_RETRIEVAL_GAP,
    permission_truth_label,
)
```

Composes `#890` `validate_work_order_dryrun()` and embedded `repo_permission_snapshot` freshness
(uses `#892` `permission_to_capabilities` only — does not call `probe_repo_permission` or `gh`).
Returns Hermes-shaped receipt with `no_execution_performed: true`. Spec:
`docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md`.

`REDDOG_WORK_ORDER_SIGNATURE_GATE_INTEGRATION_PHASE1`: callers that approach worktree
authority set `require_signed_authority=True` and provide the E1 verifier result as
`signature_verification_result`. The gate fails closed on missing, rejected, malformed,
or work-order-mismatched verifier output. Receipts include `signature_gate_status` and
`signature_gate_digest`.

Future live callers should prefer `evaluate_signed_work_order_policy_gate(...)`: it invokes
the E1 verifier first, then binds the signed authority to the actual work-order fields
(`work_order_id`, repo, operation, permission snapshot digest, allowed paths, denied paths)
before emitting the policy receipt.

<a id="contract-124"></a>

### RedDog Signed Receipt Chain (verification only)

```python
from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import (
    verify_signed_receipt_chain,       # verifies ordered externally signed receipts
    build_receipt_payload_for_signing, # unsigned canonical payload for external signer
    receipt_payload_hash,              # sha256 over reddog-receipt.v1 canonical input
    SignedReceipt,
    SignedReceiptChainVerificationResult,
    SIGNED_RECEIPT_CHAIN_ACCEPT,
    SIGNED_RECEIPT_CHAIN_REJECT,
)
```

`REDDOG_SIGNED_RECEIPT_CHAIN_PHASE1` verifies `reddog-receipt.v1` records against an
injected public-key verifier, then checks work-order identity, RedDog identity, optional
reward-account binding, issued-at freshness, ASCII-only payloads, and `prev_receipt_hash`
links. Empty chains are valid only as issuance-time "no reward yet"; unsigned receipts are
rejected and cannot be reward-bearing. This module does not sign, generate keys, settle
rewards, execute commands, enqueue OpenClaw/Hermes/WRE work, or mutate the repo.

<a id="contract-125"></a>

### RedDog OpenClaw Live Enqueue (valve-gated queue-write seam)

```python
from modules.communication.moltbot_bridge.src.reddog_openclaw_live_enqueue import (
    perform_reddog_openclaw_live_enqueue,  # adapter + policy + receipt-chain + valve + writer -> result
    RedDogOpenClawLiveEnqueueResult,
    RedDogOpenClawLiveEnqueueReceipt,
    LIVE_ENQUEUE_ACCEPT,
    LIVE_ENQUEUE_REJECT,
)
```

`REDDOG_OPENCLAW_LIVE_ENQUEUE_IMPLEMENTATION_PHASE1` is the first live OpenClaw
queue-write seam, but only through an injected writer and only when `VALVE_OPEN_LIVE_ENQUEUE`
is present. It requires accepted #904 adapter dry-run output, #950 signed work authority,
#951 signed receipt-chain verification, and a live enqueue writer. It does not import
AgentDB/OpenClaw queue modules directly, execute Hermes/WRE work, create worktrees, edit files,
create PRs, push, merge, or settle rewards.

```python
from modules.communication.moltbot_bridge.src.reddog_openclaw_live_enqueue_writer import (
    OpenClawLiveEnqueueWriter,  # concrete writer adapter: FoundUpJob queue or AgentDB task only
)
```

`REDDOG_OPENCLAW_LIVE_ENQUEUE_WRITER_ADAPTER_PHASE1` supplies the concrete writer for the
injected seam. `foundup_job` appends a typed `FoundUpJob` to OpenClaw's queue; `autonomous_task`
calls `AgentDB.create_autonomous_task()`. It does not drain the queue, execute tasks, dispatch
Hermes/WRE, create worktrees, edit files, create PRs, push, merge, or settle rewards.

<a id="contract-126"></a>

### RedDog Work-Order Receipt (Hermes-compatible audit trail, no execution)

```python
from modules.communication.moltbot_bridge.src.reddog_work_order_receipt import (
    build_reddog_work_order_receipt,   # PolicyGateReceipt -> RedDogWorkOrderReceipt
    emit_work_order_receipt,           # optional SQLite persist via RedDogWorkOrderReceiptStore
    RedDogWorkOrderReceipt,
    RedDogWorkOrderReceiptStore,
    RECEIPT_SOURCE,                    # "reddog_openclaw_policy_gate"
)
```

Pre-execution audit trail only. Maps #893 `PolicyGateReceipt` into durable Hermes-compatible
records (digests/refs only). NOT live Hermes queue dispatch, NOT WRE execution.

<a id="contract-127"></a>

### RedDog Work-Order Runtime Invocation Dry-Run (no execution)

```python
from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    invoke_reddog_work_order_dryrun,  # (work_order, permission_snapshot, *, now, seen_nonces, receipt_store) -> WorkOrderDryRunInvocationResult
    WorkOrderDryRunInvocationResult,
    INVOCATION_ACCEPT,
    INVOCATION_REJECT,
    INVOCATION_ACCEPT_WITH_RETRIEVAL_GAP,
)
```

Orchestrates #893 policy gate + #894 receipt emission/persistence. Returns audit result to caller.
No WRE, git, shell, live GitHub probe, or extension runtime wiring.

<a id="contract-128"></a>

### RedDog WRE Executor Dry-Run Planner (no mutation)

```python
from modules.communication.moltbot_bridge.src.reddog_wre_executor_dryrun import (
    plan_wre_isolated_worktree_execution_dryrun,  # (invocation_result, work_order, *, now, locks, repo_root) -> WREExecutorDryRunResult
    WREExecutorPlan,
    WREExecutorDryRunResult,
    ExecutorDryRunPhaseReceipt,
    EXECUTOR_PLAN_ACCEPT,
    EXECUTOR_PLAN_REJECT,
)
```

Consumes accepted #896 `WorkOrderDryRunInvocationResult`; validates #897 contract rules;
emits phase receipts (`plan_built`, `lock_checked`, `cleanup_planned`). No git, worktree,
file edits, task commands, PR, or merge.

<a id="contract-129"></a>

### RedDog WRE Worktree Create (worktree only, no task execution)

```python
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import (
    create_reddog_wre_worktree,  # (work_order, executor_plan_result, valve_decision, *, runner, repo_root, now, locks) -> RedDogWorktreeCreateResult
    RedDogWorktreeCreateResult,
    WORKTREE_CREATE_ACCEPT,
    WORKTREE_CREATE_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_runner import (
    RealRedDogWorktreeRunner,    # argv-only git worktree add/remove helper
)
```

Consumes an accepted executor dry-run plan plus `VALVE_OPEN_WORKTREE_CREATE`.
Creates only the isolated `.reddog/worktrees/<work_order_id>/<nonce>/` worktree through an
injected runner. No file edits, tests, PR, push, merge, Skillz execution, Hermes queue,
OpenClaw dispatch, or task command execution.

<a id="contract-130"></a>

### RedDog WRE Worktree Operational Spine (worktree-create only)

```python
from modules.communication.moltbot_bridge.src.reddog_wre_operational_spine import (
    run_reddog_wre_worktree_create_spine,  # (work_order, *, valve_environment, signature_verification_result, runner, repo_root, now, locks) -> RedDogWREOperationalSpineResult
    RedDogWREOperationalSpineResult,
    WORKTREE_SPINE_ACCEPT,
    WORKTREE_SPINE_REJECT,
)
```

Composes the governed RedDog path into one callable API:
runtime invocation dry-run, executor plan dry-run, execution valve, then isolated
worktree create. Requires accepted signed work authority and `VALVE_OPEN_WORKTREE_CREATE`
for acceptance. The result keeps WSP 97 truth fields explicit: no task execution,
no file edits, no PR, no OpenClaw enqueue, no Hermes dispatch, no push, and no merge.


<a id="contract-131"></a>

### RedDog Recipient Transaction Preflight

```python
from modules.communication.moltbot_bridge.src.reddog_recipient_preflight import (
    EvidenceLevel,
    ProposedRecipient,
    RecipientRole,
    RouteEvidence,
    RoutePolicy,
    preflight_recipients,
    verify_sent_readback,
)
```

`reddog_recipient_preflight.py` is a provider-agnostic, fail-closed sender-boundary
guard. It does not send correspondence. It resolves each intended recipient from
authoritative evidence, gives newer explicit provider instructions precedence over
stale Contacts/history, enforces closed/BCC-only/organization-only route policy,
requires exact normalized address equality, blocks duplicate sent coverage, and
returns a deterministic SEND/BLOCK receipt.

HIGH/CRITICAL correspondence should run this as an independent second pass after
composition and before provider transmission. After a successful provider send,
`verify_sent_readback(...)` compares actual To/CC/BCC against the approved receipt.
Search snippets, memory, autocomplete, and visually similar addresses are not exact
routing evidence. A one-character or punctuation difference blocks rather than being
silently corrected.


<a id="contract-132"></a>

### RedDog Correspondence Sender Boundary

Current authority is `src/reddog_correspondence_sender_boundary.py`, bootstrapped
by the trusted service owning provider credentials, reconciliation and private
state. The superseded caller-loadable V2 JavaScript host always BLOCKs; its
historical execution description is not an active provider-call interface.
The Python issue/execute contract owns current recipient preflight, state and
finalized-draft gating, private receipt registration, durable one-shot claims
and exact provider Sent readback. Cached context never grants send authority.
See the [current contact/communication protocol](../../../../../extensions/reddog/docs/CONTACT_COMMUNICATION_ACTION_PROTOCOL.md)
for operation scope, reconciliation and privacy requirements. Direct external
connector interception remains unproved; deployment requires alternate mutation
paths to be mechanically unavailable to governed AUTO sessions.
`012_DIRECTED_WORK` remains a separate policy lane with fresh live checks.

<a id="contract-133"></a>

### Moshpit projection layer

`src/moshpit_projection.py` defines `MoshpitRequest`,
`AuthorizedActivitySource`, `AuthorizedActivitySnapshot`, `MoshpitRejected` and
`project_moshpit(request, *, source, capability=None, now=None)`.
`src/openclaw_memory_queries.py::query_moshpit(request, *, source=None,
capability=None)` delegates only to this projector; no legacy memory fallback.
`src/moshpit_render.py::render_moshpit_html(projection)` escapes text for a
read-only activity/day/details view. It is not a browser or publication endpoint.

This component is **unmounted and unregistered**. The trusted source must verify
session, FoundUp membership, disclosure, revocation and snapshot identity before
reading data, then independently curate permitted strings for each audience.
Constructing the snapshot dataclass is not authentication; a view whitelist is
not a personal-data detector. Private contact fields must stay out of all history.
Only explicit `data.moshpit` views feed `moshpit_projection.v1`; old underscore
contracts are not inferred. Missing authority, mismatched scope, malformed bounds
or expired snapshots reject. Live calls recheck time after reading and before
release; explicit `now` is a trusted fixed-clock evaluation input, not live authority.
No AgentDB access, capture, persistence, Brain ingestion, WRE skill discovery or
runtime admission is provided. [PR1648 carries the remaining host, reader, skill,
Gmail-receipt and registration acceptance](https://github.com/FOUNDUPS/Foundups-Agent/pull/1648#issuecomment-6358466590).

<a id="contract-134"></a>

### RedDog Correspondence Continuity State

```python
from modules.communication.moltbot_bridge.src.reddog_correspondence_state import (
    AskRecord,
    AskStatus,
    CorrespondenceEvent,
    CorrespondenceState,
    FollowUpGate,
    Freshness,
    RedDogCorrespondenceStateStore,
    build_scope_key,
)
```

`reddog_correspondence_state.py` provides the private M2M continuity layer for
provider-backed correspondence. It stores append-only provider event metadata
and one materialized state per stakeholder/topic scope through WSP 78
`ModuleDB`. Provider systems remain transaction truth; cached state is
rebuildable and never authorizes a send.

The store intentionally excludes raw message bodies, complete recipient dumps,
credentials, attachments and hidden reasoning. Human Google Sheets/Docs may
project the state, but Red Dog does not require them as its memory substrate.
Before consequential send-capable work, provider freshness and current routing
must be rechecked and `reddog_recipient_preflight` still owns authorization.

`load_state(scope_key)` returns `None` for an absent scope. Before returning a
cached state, it requires an explicit supported payload schema, the existing
write-side state invariants, exact requested/payload scope agreement and the
stored digest. Rejection by these schema, scope, ask, count or digest checks raises
`ValueError` without rewriting the row; the caller must reconcile from provider
truth. Arbitrary malformed payload shapes and coercions are not covered by this
exception guarantee. `provider_refresh_required` uses the same read boundary and
propagates invalid-state rejection.

`provider_refresh_required(scope_key, observed_watermark)` requests reconciliation
for a missing, non-string or empty observed token, an empty cached token, absent
state, or non-VALID freshness. Only exact nonempty string equality can avoid a
refresh. Tokens are opaque: no string conversion, trimming or ordering. Literal
`"None"`, `"True"` and `"0"` remain valid string values. The stored digest/read
boundary is evaluated first, so invalid cached state still raises its existing
error even when the observation is invalid. This check does not authenticate a
provider or grant send authority.

[Return to the interface directory](../../INTERFACE.md).
