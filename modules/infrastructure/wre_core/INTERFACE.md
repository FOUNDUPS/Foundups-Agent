# WRE Core Interface

**Version:** 0.8.0
**Status:** Execution-truth hardening implemented; production RSI incomplete

This document describes current callable contracts. Historical promoter,
automatic rollback, automatic reindex, and model-autonomy sketches are not
public implementation truth.

## Authority boundary

A WRE return value is an execution record, not repository, Git, network,
external-service, or production-promotion authority. 012 remains sovereign.
Callers must preserve the narrower authority of the work item and runtime
binding.

## WREMasterOrchestrator

```python
from modules.infrastructure.wre_core.wre_master_orchestrator import (
    WREMasterOrchestrator,
)

wre = WREMasterOrchestrator()
result = wre.execute_skill(
    skill_name="auto_test_registry_audit",
    agent="qwen",
    input_context={"scope": "registered-tests"},
    force=False,
)
```

### `execute_skill(skill_name, agent, input_context, force=False) -> dict`

Routes either one admitted attempt or the bounded ReAct wrapper according to
runtime configuration.

The legacy `recall_pattern()` compatibility surface is fail closed by default.
It requires independently injected WSP verification and violation-prevention
callbacks, and it returns only a pre-registered pattern. It is not an execution
or compliance authority for RedDog Skillz.

Common success fields:

- `execution_id: str`
- `skill_name: str`
- `agent: str`
- `success: bool`
- `pattern_fidelity: float`
- `execution_time_ms: int`
- `result: dict`

Common fail-closed fields:

- `success: false`
- `blocked: true` when admission prevented dispatch
- `blocked_by: str`
- `reason: str` containing stable redacted text

Known `blocked_by` values include `wre_skill_scan`, `skill_load`, and
`ab_variant_binding`.

## Bounded Git byte I/O

`run_bounded_stdout(argv, *, cwd, max_bytes, timeout_s, environment=None,
stdin_bytes=None) -> bytes` captures stdout under an exact byte ceiling. Optional
binary stdin is limited to 8 MiB and is written concurrently with stdout reads
so `git cat-file --batch` cannot deadlock on full pipes. Timeout, output
overflow, early child exit/broken pipe, reader/writer failure, and nonzero exit
all terminate or fail closed; process pipes and named I/O threads are closed.

`run_bounded_stdout_file(...)` retains the same stdout/time behavior and does
not accept stdin. These helpers grant no repository, mutation, commit, or Git
trust authority; callers must supply their own sanitized environment, exact
executable/repository binding, and object validation.

### `execute_skill_with_reasoning(...) -> dict`

Adds:

- `execution_success: bool`: exact effect execution evidence existed;
- `success: bool`: execution success plus requested fidelity acceptance;
- `_react_metadata.iterations`;
- `_react_metadata.max_iterations`;
- `_react_metadata.all_attempts`;
- `_react_metadata.early_success`.

Retry exhaustion with low fidelity returns `success: false`.

## WRESkillsLoader

```python
from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader

loader = WRESkillsLoader(repo_root=repo_root)
path = loader.resolve_skill_file("auto_test_registry_audit")
content = loader.load_skill("auto_test_registry_audit", "qwen")
metadata = loader.get_skill_metadata("auto_test_registry_audit")
```

### Runtime invariants

- Registry locations are checkout-relative.
- `SKILLz.md` is preferred; `SKILL.md` is compatibility fallback.
- Link, junction, reparse, traversal, drive, and checkout-escape paths fail.
- Hygiene executes before every cache return.
- Cached filtered content is bound to the current source SHA-256.
- `enforce_hygiene=False` is diagnostic and grants no production execution.

## Production admission

```python
from modules.infrastructure.wre_core.src.registered_skill_executor import (
    validate_runtime_skill_admission,
)

ok, message = validate_runtime_skill_admission(
    skills_loader=loader,
    skill_name="auto_test_registry_audit",
)
```

Admission requires exact production registry/frontmatter agreement for
`name`, `version`, `intent_type`, and `promotion_state`.

`ensure_runtime_skill_safety(...)` additionally binds the current Skillz
bundle fingerprint, manifest verification, and required/enforced scanner
result. An exact bundle uses Cisco `scan` with `SKILLz.md`; a wardrobe root uses
`scan-all --recursive`. Its cache key changes when Skillz, executor, or
manifest bytes change.

## Programmatic executor

```python
from modules.infrastructure.wre_core.src.registered_skill_executor import (
    resolve_registered_skill_executor,
    dispatch_registered_skill_executor,
)
```

`resolve_registered_skill_executor()` returns only the regular adjacent
`executor.py` under the exact registered Skillz directory.

`dispatch_registered_skill_executor()` requires the exact bundle fingerprint
that passed the scanner. It captures the current bundle, rejects a fingerprint
change, and validates the captured executor against the captured adjacent
manifest before compiling those same bytes. A successful executor result has
this minimum shape:

```python
{
    "success": True,
    "output": "...",
    "effect_receipts": [
        {"receipt_id": "stable-id", "effect_type": "bounded-effect"}
    ],
}
```

`success` must be an exact built-in Boolean. Missing/malformed receipts,
reported failure, compile/import failure, or an exception returns stable
failure with `_effect_evidence: false`. Raw exception text is not returned or
logged.

Typed receipts are necessary execution evidence; they are not an independent
production verifier or promoter.

## Local inference

```python
from modules.infrastructure.wre_core.src.local_skill_inference import (
    execute_local_skill_inference,
)
```

The implemented local path supports Qwen proposal generation. It always
returns `success: false`, `_effect_evidence: false`, and either a
`proposal` or a stable `error_code`. Model text never proves effects.

Unsupported agent: `unsupported_local_agent`.
Unavailable/import/init/generation failure: `local_model_unavailable`.
Generated proposal: `unverified_model_proposal`.

## PatternMemory

`PatternMemory.store_outcome()` records actual post-dispatch execution
success and structural fidelity. `outcome_quality` remains `0.0` until an
independent authenticated evaluator supplies quality evidence.

`stage_variation_candidate(variation_id)` sets a non-production
`candidate_ready` state. `promote_variation()` is a fail-closed compatibility
method until the independent signed promoter is implemented.

Generic runtime A/B selection is blocked while authenticated
candidate/runtime binding is absent. Generic evolution stores variations but
does not auto-schedule a runtime test. A statistical test requires exact named
variants, exact-Boolean outcomes, and the configured sample target in each arm;
its durable winner label is nomination evidence only.

`evolve_skill()` returns `True` only when a proposal variation was actually
stored. Execution results expose `evolution_attempted` separately from
`variation_created`; `evolution_triggered` remains a compatibility alias for
the latter. Stored proposals are not independent evaluation or promotion.

## Master-orchestrator compatibility surface

The following existing callables remain supported with bounded authority:

- `register_plugin()` / `get_plugin()`: in-process compatibility plugins;
- `validate_module_path()`: accepts only existing directories inside the exact
  checkout;
- `execute()`: legacy pattern recall crosses both injected WSP callbacks, but
  plugin dispatch remains blocked because those callbacks authenticate neither
  executors nor effects; direct Holo names the governed owner-query route and
  other plugins must migrate to WSP 95 admission;
- `select_skill_tot()` / `find_skill_candidates()`: candidate selection only;
- `execute_skill()`: WSP 95 admitted generic Skillz entry point;
- `execute_codeact_skill()`: compatibility API that always returns a
  `codeact_prototype_boundary` block;
- `evolve_skill()`: stores only a non-production proposal candidate;
- `get_skill_statistics()`: historical structural/outcome observations;
- `get_metrics()`: observed component counts; it explicitly reports
  `token_reduction_measured: false` and contains no synthetic reduction claim.

`WRESkillsLoader` retains `list_skills()`, `discover_skills()`,
`discover_healthy_skills()`, `load_skill()`, `resolve_skill_file()`,
`get_skill_metadata()`, `check_skill_hygiene()`, `inject_skill_into_prompt()`,
`has_skill()`, `list_healthy_skills()`, `get_skill_location()`, and
`reload_registry()`. Registry locations remain checkout-relative and metadata
loading is fail-closed for non-mapping YAML roots. `get_skill_location()` is a
location resolver only; it is not production admission.

`PatternMemory` retains these callable groups:

- outcomes: `store_outcome()`, `recall_successful_patterns()`,
  `recall_failure_patterns()`, `get_skill_metrics()`;
- false-positive records: `record_false_positive()`, `is_false_positive()`,
  `get_false_positive_reason()`;
- evolution and continuity: `store_variation()`, `record_learning_event()`,
  `get_evolution_history()`, `get_evolution_by_continuity()`,
  `get_evolution_by_execution()`;
- counters and retrieval observations: `increment_counter()`, `get_counter()`,
  `get_telemetry_dashboard()`, `record_retrieval()`,
  `get_retrieval_stats()`;
- relationship and selection evidence: `add_skill_edge()`,
  `get_related_skills()`, `get_skill_graph()`, `transfer_learning()`,
  `get_skill_fidelity_stats()`, `rank_skills_for_context()`;
- lifecycle: `close()`.

These storage surfaces do not authenticate effects or grant runtime/promotion
authority. Historical fidelity and ranking are proposal inputs, not production
selection proof.

## Filesystem discovery compatibility

`WRESkillsDiscovery` remains callable through
`skillz/wre_skills_discovery.py`. It exposes `discover_all_skills()`,
`discover_by_agent()`, `discover_by_module()`, `discover_production_ready()`,
`discover_healthy_skills()`, `export_discovered_to_registry()`,
`start_watcher()`, `stop_watcher()`, `load_command_rolodex()`,
`discover_orphan_clis()`, `suggest_skillz_md_for_orphan()`, and
`get_orphan_reduction_progress()`.

Discovery and generated registry/Skillz suggestions are diagnostic inventory.
`export_discovered_to_registry()` writes only the explicit caller-selected
output path; it is not the canonical production registry. The watcher can call
the callback supplied by its caller. These surfaces do not satisfy WSP 95
admission, execute a bundle, authenticate an effect, or promote an artifact.

## Structural fidelity

`GemmaLibidoMonitor.validate_step_fidelity()` is a structural-key check. It
does not prove correctness, effect success, outcome quality, security, or
promotion readiness. The class name is historical and does not prove a live
Gemma model invocation.

## Recursive-improvement compatibility

`RecursiveLearningEngine.process_error()` produces durable pattern, solution,
and improvement proposals. `apply_improvement()` is intentionally fail closed:
it returns `False`, keeps `applied=False`, and records
`application_status=blocked_unimplemented`. Its public metrics keep
`tokens_saved=None` and `token_reduction_measured=False`. This prototype does
not edit, evaluate, promote, activate, or roll back artifacts.

## FMAS / WSP 62 health admission

```python
from modules.infrastructure.wre_core.src.fmas_health_triage import (
    run_wsp62_health_audit,
)

result = run_wsp62_health_audit(
    candidate_repo_root=repo_root,
    baseline_repo_root=exact_merge_base_checkout,  # optional
    candidate_job_limit=50,
)
```

The candidate must be a clean Git checkout. The optional baseline must pass
FMAS exact merge-base authority. The imported canonical scanner must be a
regular, non-reparse file inside the candidate. Pre/post HEAD, tool, and
tracked-inventory checks reject drift observable at either gate. This is a
proposal-only detection boundary, not a filesystem lock: a transient
mutate/scan/restore race is not excluded and no result is execution authority.

`result.receipt` binds the producer observation count/digest, all exclusion
reason counts, authoritative finding-set digest, dispositions, selected IDs,
stable proposal digest, candidate/baseline HEADs, and scanner digest. Receipt
maps/IDs are immutable snapshots; `validate_health_audit_result()` recomputes
receipt, finding, audit, and mutable-job evidence identities before consumption.
Only exact-HEAD tracked WSP 62
observations enter the authoritative finding set. Excluded ignored, malformed,
or non-WSP62 observations remain visible through receipt counts and cannot be
silently dropped without changing the receipt identity.

Without a baseline, `CRITICAL`/`ERROR` size observations are `health_debt` and
emit no jobs. With an authoritative baseline, only candidate-attributed
`ERROR` findings may emit capped PENDING/dry-run jobs. This API does not call a
model, persist or mutate a queue, dispatch OpenClaw/Hermes, edit source, or
promote an artifact.

`parse_fmas_finding()` and `parse_fmas_strings()` are compatibility parsers,
not WSP 62 authority. Both quarantine direct WSP 62 input. The internal
normalized factory is used only after the health gate has admitted evidence.
`RedDogDirector` never marks direct FMAS input ready-to-advance.

`WSP15Priority` is a legacy compatibility name for qualitative execution-risk
hints. It is not the canonical numeric C/I/D/Impact MPS contract and must not
be used as a signed WSP 15 allocation receipt.

## Monitor compatibility

`WREMonitor` exposes `track_api_call()`, `track_stream_transition()`,
`track_pattern_learned()`, `track_action_experience()`, and `track_error()` for
caller-supplied observations; these methods do not authenticate their inputs.
`get_status()` returns current counters, `save_report()` writes a local report,
`stop()` stops monitoring and saves that report, and `get_monitor()` returns the
process-global monitor.

The monitor records observations and produces suggestions. Its historical
`apply_improvement()`, `_apply_quota_improvement()`, and
`_apply_stream_improvement()` surfaces are fail-closed compatibility methods:
they return `False`, write no configuration, append no applied-effect record,
and require a future WSP 95 admitted executor with a typed effect receipt.
Dashboard token efficiency remains `None` until authenticated usage evidence
exists; legacy improvement records are displayed as unverified.

## FoundUp job surfaces

The FoundUp job router/consumer contracts are separate from generic Skillz
execution. They provide typed envelopes, stable route decisions, queue
retention, capability projection, and dry-run OpenClaw/Hermes adapters. Current
dry-run success is simulated evidence only; it is not live provider or
filesystem effect proof.

See the focused source interfaces and tests for:

- `src/foundup_job_router.py`
- `src/foundup_job_consumer.py`
- `src/foundup_job_contract.py`
- `src/foundup_job_model_capability_projection.py`
- `src/wre_autonomous_slice_verifier_runtime.py`

## Test differential and independent verification

`load_canonical_test_registry()`, `collect_registered_test_shards()`,
`make_test_impact_plan()`, `make_test_run_snapshot()`, and
`evaluate_test_differential()` preserve the canonical registry/shard and
candidate-vs-base integrity contracts. Collection imports test modules and is
diagnostic execution, not an OS sandbox or promotion authority. Differential
receipts reject binding drift, removed coverage, weaker candidate results, and
evidence below the derived tier; authentication remains a separate boundary.

`verify_autonomous_slice_runtime()` remains the independent verifier boundary.
When assurance lineage is declared, its request, durable reservation, exact
artifact, verifier identity, work order, operational snapshot, WSP 15
allocation, and terminal receipt must agree. The independently recorded
`trusted_work_authority_digest` cannot be copied from the author request.
Verifier, CI, CodeQL, and red-team evidence do not independently publish or
promote an artifact.

## Configuration

| Variable | Meaning |
|---|---|
| `WRE_REACT_MODE` | Enable bounded ReAct wrapper |
| `WRE_REACT_MAX_ITER` | Retry attempts clamped to `1..10` |
| `WRE_REACT_FIDELITY` | Acceptance threshold clamped to `0..1` |
| `WRE_PATTERN_MEMORY_DB` | Explicit PatternMemory database path |
| `WRE_AGENTIC_RAG` | Legacy flag; `1` is blocked until the governed Holo owner adapter exists |
| `WRE_CODEACT_ENABLED` | Legacy flag; CodeAct remains blocked as a non-admitted prototype |
| `WRE_SKILL_SCAN_REQUIRED` | Must remain `1`; `0` blocks production Skillz admission |
| `WRE_SKILL_SCAN_ENFORCED` | Must remain `1`; `0` blocks production Skillz admission |
| `WRE_SKILL_SCAN_ALWAYS` | Disable scanner cache reuse |
| `WRE_SKILL_SCAN_TTL_SEC` | Content-bound cache TTL |
| `WRE_SKILL_SCAN_MAX_SEVERITY` | Scanner severity policy |
| `FOUNDUPS_DB_PATH` | AgentDB/breadcrumb database path |

Production defaults require and enforce the Skillz scanner. Tests must set
explicit non-production database and temporary paths.

## Not implemented or not proven

- authenticated independent outcome evaluator for generic Skillz;
- durable signed production promoter;
- automatic production artifact mutation or governed rollback;
- HoloIndex promotion activation;
- authenticated A/B candidate/runtime execution binding;
- governed generation-bound Holo owner retrieval adapter;
- WSP 95 admission/effect receipts for generic CodeAct;
- Gemma/Grok/UI-TARS generic local execution;
- hundred-agent distributed scheduler;
- production end-to-end RSI canary.

The current contract is fail-closed at these boundaries.
