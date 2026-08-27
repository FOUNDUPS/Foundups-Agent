# WRE Core

WRE Core is the governed recursive-work control plane for FoundUps. It admits
Skillz, routes bounded work, records execution truth, and provides evidence
surfaces for learning. WRE is intended to become the system's RSI engine, but
the current repository does not yet prove end-to-end production RSI.

**012 remains sovereign.** WRE, RedDog, OpenClaw, Hermes, local models,
fidelity scores, and consensus do not independently grant effect or promotion
authority.

## Current responsibility

WRE Core owns:

- registry-bound Skillz discovery and production admission;
- content-bound supply-chain scanning and manifest verification;
- registry-adjacent programmatic executor dispatch;
- proposal-only local model inference;
- structural fidelity and durable execution-outcome storage;
- bounded ReAct retries;
- candidate variation storage;
- FoundUp job envelopes, route decisions, queue retention, and dry-run
  OpenClaw/Hermes adapters;
- independent autonomous-slice verification contracts.
- canonical test-registry shards and differential test-evidence contracts.

It does not yet own a complete authenticated production promoter, automatic
artifact activation/rollback, a hundred-agent scheduler, or a proven
production RSI canary.

## Execution-truth pipeline

```text
registry entry
  -> exact production frontmatter match
  -> checkout/link/reparse validation
  -> manifest + scanner admission with stable pre/post fingerprint
  -> captured exact-fingerprint adjacent executor OR proposal-only local inference
  -> typed effect result
  -> structural fidelity
  -> PatternMemory execution record
  -> independent outcome evaluation (missing in generic path)
  -> candidate nomination
  -> governed promotion authority (missing)
```

Fail-closed rules:

- Missing, unhealthy, retired, malformed, unregistered, or non-production
  Skillz stop the execution.
- Synthetic fallback instructions cannot create success.
- Loader caches are source-digest-bound and never bypass hygiene.
- Local model text is a proposal, not effect evidence.
- CABR means **Consensus-Driven Autonomous Benefit Rate**. Generic WRE job,
  admission, and worker paths keep `cabr_ready=false`; legacy calculation
  helpers do not prove CABR consensus, payout, or production authority.
- A single registered Skillz bundle uses Cisco `scan --skill-file SKILLz.md`;
  wardrobe roots use `scan-all --recursive`.
- Production admission rejects disabled scanner-required or enforcement policy.
- Executor success requires an exact Boolean and typed effect receipts.
- Executor dispatch rejects any bundle changed after scanner admission.
- Structural fidelity never becomes outcome quality.
- Active A/B runtime selection is blocked until candidate/runtime binding is
  authenticated.
- ReAct success requires effect success and the requested fidelity threshold.
- Legacy pattern recall is blocked unless real WSP verification and violation-
  prevention callbacks are injected; unknown patterns are never invented.
- Direct legacy Agentic RAG and generic CodeAct execution are blocked until
  their governed owner/admission contracts exist.
- `WREMonitor` observes and proposes only; its legacy application methods never
  write live configuration or claim an effect.

The normative contract is
[WSP 95](../../../WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md).

## Main LEGO blocks

| Block | Responsibility |
|---|---|
| `skillz/wre_skills_loader.py` | Registry resolution, hygiene, digest-bound content loading |
| `src/skill_runtime_admission.py` | Production metadata, bundle fingerprint, manifest/scanner admission |
| `src/registered_skill_executor.py` | Adjacent executor resolution, admitted-fingerprint capture/dispatch, result schema |
| `src/local_skill_inference.py` | Qwen proposal generation with stable fail-closed errors |
| `src/skill_execution_truth.py` | Meaningful structural evidence projection |
| `src/skill_path_security.py` | Shared unresolved link, junction, and reparse rejection |
| `src/pattern_memory.py` | Execution outcomes, learning events, candidate storage |
| `src/pattern_ab_evidence.py` | Non-production A/B sampling, winner evidence, candidate state |
| `src/libido_monitor.py` | Frequency control and structural fidelity |
| `wre_monitor.py` | Observability and proposal-only improvement suggestions |
| `wre_master_orchestrator/src/wre_master_orchestrator.py` | Thin public coordination surface |
| `wre_master_orchestrator/src/wre_runtime_support.py` | Legacy pattern/plugin compatibility types |
| `src/foundup_job_router.py` | Governed FoundUp job admission and route selection |
| `src/foundup_job_consumer.py` | Queue retention and dry-run dispatch consumers |
| `src/wre_autonomous_slice_verifier_runtime.py` | Independent verifier boundary |
| `src/fmas_finding_contract.py` | Normalized FMAS observation schema |
| `src/fmas_wsp62_contract.py` | Syntactic WSP 62 parser; grants no provenance |
| `src/fmas_health_triage.py` | Exact-HEAD WSP 62 admission and proposal receipt |
| `src/fmas_improvement_bridge.py` | Finding-to-ImprovementJob mapping |

## Code-health admission

`run_wsp62_health_audit()` is the bounded code-health entry point. It requires
a clean candidate checkout and binds exact Git HEAD, canonical scanner bytes,
optional exact-base authority, the full producer observation digest, exclusion
reasons, and exact tracked-file scope. Only baseline-attributed `WSP 62 ERROR`
findings can become capped, deterministic, dry-run `ImprovementJob` proposals.
No-baseline critical findings remain health debt; they are not candidate jobs.

Direct string or structured WSP 62 input through the legacy FMAS bridge is
blocked. The triage layer invokes no model, queue, worker, source mutation, Git
mutation, or promoter; its Git operations are read-only authority checks. It
currently has no non-test runtime caller. Its
legacy `WSP15Priority` value contains execution-risk hints, not canonical
numeric WSP 15 MPS or an allocation receipt.

FMAS now inventories Git-tracked module files before size inspection. On the
2026-08-27 repository candidate this reduced the raw scan from 4,955 findings
in roughly 64 seconds to 471 findings in 16.3 seconds; critical observations
fell from 2,665 to 67 because 2,598 ignored/runtime/vendor paths no longer
entered the producer. Incremental changed-file scanning remains roadmap work.

## RedDog relationship

RedDog is the principal-scoped conversational 0102 interface. WRE is its
governed work/learning control plane; they are not the same process.

- RedDog interprets conversation and work intent.
- Principal/FoundUp Memex provides scoped memory.
- WRE admits and records governed work.
- OpenClaw supplies policy-constrained hub scaffolding.
- Hermes supplies bounded leaf-worker scaffolding.
- p.fMALL and IDE/phone surfaces are clients, not authority owners.

Durable conversation binding, Principal Memex ingestion, production OpenClaw
and Hermes effect chains, and automatic conversation-to-work lineage remain
separate RedDog P0 work.

Legacy direct FMAS direction remains advisory: RedDog may prioritize or
escalate a proposal, but it never marks those proposals ready to execute.

## Production Skillz

The executable registry is
[skills_registry_v2.json](skillz/skills_registry_v2.json). A production Skillz
must have matching registry/frontmatter metadata and an adjacent
`SKILL_MANIFEST.json`. JSON command configurations belong to their owning
handlers and are not executable Skillz.

Generic local inference currently supports Qwen proposal generation only.
Gemma/Qwen names in old design documents do not prove a live model binding.
Runtime model selection requires a separate verified binding receipt.

Low-fidelity evolution may store that proposal as a non-production candidate.
It reports attempted versus created state separately and does not schedule,
evaluate, activate, or promote the candidate.

## Verification

All test state must stay outside production databases:

```powershell
$root = 'O:\pytest_tmp\reddog_wre_truth'
$env:TMP = $root
$env:TEMP = $root
$env:FOUNDUPS_DB_PATH = Join-Path $root 'foundups.db'
$env:WRE_PATTERN_MEMORY_DB = Join-Path $root 'pattern_memory.db'
python -m pytest -q `
  modules/infrastructure/wre_core/tests/test_wre_execution_truth.py `
  modules/infrastructure/wre_core/tests/test_wre_skills_loader_hygiene.py `
  modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py `
  modules/infrastructure/wre_core/tests/test_pattern_memory.py `
  modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py
```

The focused tier proves only the named contracts. It does not prove the full
WRE suite, live provider effects, production promotion, or RSI.

## Documentation

- [INTERFACE.md](INTERFACE.md): current public contracts
- [ROADMAP.md](ROADMAP.md): verified missing work and decomposition debt
- [ModLog.md](ModLog.md): append-only change record
- [tests/README.md](tests/README.md): test execution and isolation
- [tests/TestModLog.md](tests/TestModLog.md): test evolution record
