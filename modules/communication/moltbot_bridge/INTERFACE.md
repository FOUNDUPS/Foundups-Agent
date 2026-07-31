# OpenClaw Bridge Interface

## Public API
### Architect proposal validity and execution readiness

`evaluate_architect_proposal_executability()` runs after backend Fusion output
validation and before a FIX becomes an architect queue candidate. It requires
an audit-supported `REUSE_EXISTING`, `EXTEND_EXISTING`, or separately gated
`CREATE_NEW` decision plus exact paths, tests, policy gates, capabilities,
expected evidence, and stop conditions.

The resulting
`reddog_architect_proposal_executability_admission.v1` receipt separates
proposal validity from current execution readiness. A valid prerequisite slice
may persist as `BLOCKED_CANDIDATE`; it does not mutate the authoritative queue.
Model-supplied readiness booleans and capabilities produced by the proposed
slice are never current authority.

`promote_reddog_architect_fix_to_signed_wsp15_work_order()` canonically
rehydrates the receipt and rechecks platform, repository HEAD, HoloIndex freshness,
work-state revision, snapshot, audit bundle, candidate identity, future capabilities,
and WSP 15 lineage. A valid `BLOCKED_CANDIDATE` may reach promotion because proposal
authenticity cannot exist before that stage. Promotion rebuilds and verifies the proposal
before queue mutation. Missing execution capabilities remain fail-closed at
the use-time valve; promotion grants no ambient authority. The authorized base
is the immutable admission SHA, not a branch. INDEX_GAP blocks ordinary work;
the maintenance exception requires exact supporting direct-read paths.

The receipt's SHA is integrity evidence, not authentication.
`reddog_architect_proposal_authenticity.py` defines a domain-separated Ed25519
attestation, an exact signer-owned proposal policy, transactional signer-side
nonce reservation, and strict serialized-attestation integrity validation.
The public validated attestation remains evidence, not authority.
`reddog_architect_proposal_verified_authority.py` adds the promotion boundary:
it rebuilds the exact proposal payload from current records, reconstructs the
active isolated-signer context, resolves the principal key independently, and
re-verifies both the principal-signed signer policy and RedDog proposal
attestation at promotion use time. The canonical authority-profile source
receipt is recomputed, so identity, scope, operation, or permission changes are
rejected alongside test-only mode, signer substitution, expiry, and revocation.
Successful authoritative work-state publication persists the attestation ID as
a restart-durable replay guard. The attestation,
policy-authorization, and signer-runtime context IDs/digests are bound into the
claim, queue item, promotion record, promotion receipt, and promoted authority
profile. There is no process-local authority registry or serializable promotion
capability. Production startup remains fail closed until it receives the
attestation, a current signer-runtime configuration, and an independently
administered principal-key resolver.
`reddog_architect_fix_promotion_transaction.py` isolates record construction and publication; `reddog_architect_fix_promotion_publication.py` confines all artifacts, while `reddog_architect_fix_publication_effect_binding.py` binds current COMMITTED lineage into signer and worker-dispatch admission. Queue authority verification derives a canonical receipt from the recorded signed authority and accepted verification result. The dry-run receipt, each intent, the runtime receipt, and each AgentDB task retain that receipt ID/digest and exact work-authority digest. Immediately before AgentDB publication, the runtime reloads both stages, recomputes the lineage, obtains fresh time from a required production clock, binds the effective work order, FoundUp, operation, and exact worker roles to the signed authority plus authoritative WSP 15 plan, and re-verifies the principal and work-authority signatures, revocation, permission snapshot, scope, paths, freshness, and valve binding. Final admission uses `AUTHORITATIVE_USE` and consumes the durable nonce once before the writer; any later writer failure requires freshly signed authority. Static validation failures do not consume the nonce. Missing verifier/clock dependencies, forged signatures or substituted operations with attacker-recomputed local receipts, role/capability substitution, replay, expired authority reopened with an old environment epoch, synthetic dry-runs, and substituted authority all reject before the writer.
AgentDB publication persists a canonical `reddog_signed_worker_agentdb_envelope.v1` containing the complete signed authority runtime, authoritative WSP 15 allocation, exact dispatch receipt, and exact worker intent. Both `OpenClawSupervisor` and direct `scripts/run_task.py` execution independently rehydrate and reverify it before runner selection; runner context comes from verified evidence, outer metadata is not authority, and inconsistent routing cannot fall through to generic WRE. The optional signed Memex supply ID/digest pair remains bound through profile materialization, dispatch, restart, claim, executor, read-only 0102 assignment, and independent slice verification; half-pairs, malformed digests, or conflicts reject and absence remains valid. `AuthoritativeWorkStateStore.locked_snapshot()` is the shared mutation fence for refresh, promotion, and AgentDB publication; its file-backed implementation is confined to an explicit outside-repository runtime root and uses a sibling operation lock.
Canonical rehydration returns an opaque process-local verification proof that
cannot be reconstructed from a serialized mapping. Execution admission accepts
only that proof, rejects stale assignments, validates the durable result
history, and then performs the assigned-to-executing CAS. Invalid protected
rows are quarantined transactionally with any verifier reservation, and a
poisoned row does not prevent OpenClaw from considering the next valid task.
Publication runs `STATE_PREPARED -> immutable content-addressed inert profile artifact -> COMMITTED authoritative state -> derived fixed-path inert cache`.
PREPARED has no executable claim or queue item. Recovery never advances it: a compare-and-swap rollback preserves concurrent authoritative-state changes, removes exact staged artifacts, and requires a fresh authenticated publish attempt.
Every staged digest, revision, attestation, and record remains bound; tampering, drift, altered retries, and attacker-recomputed internal receipts fail closed without granting unanchored stages immutable-artifact deletion authority.
COMMITTED proves local publication integrity, not late-bound authentication. Both high-authority signer consumers require the explicitly selected, confined durable authoritative work state, even without removable publication or queue/claim markers; caller-injected state is corroborative only and must match that durable payload exactly. If durable state contains any architect promotion, absent or ambiguous profile provenance fails closed rather than being treated as generic. Architect-derived profiles must also prove current COMMITTED state at valve and signer use time; `main.py` keeps `architect_fix_inert_profile.json` separate and inactive.
A signer-owned commitment and authenticated activation covering the immutable publication tuple remain SPECIFIED_NOT_IMPLEMENTED.

The signer-service configuration and runtime wiring can provision one exact
proposal policy only with a fresh, principal-signed, domain-separated policy
authorization. An independently injected principal resolver supplies the
trusted public verification key; proposal mode never resolves or loads the
principal private key. WSP71 resolves only the RedDog 0102 proposal profile,
and the socket exposes only that proposal-domain backend. The signer validates
the exact payload and consumes a MAC-authenticated, bounded nonce store before
returning an accepted signature. Replay rollback is checked against an
independently injected monotonic high-water authority outside the nonce-state
rollback domain. Production mode additionally requires that injected authority
to be supplied by trusted signer-runtime composition, declare durable storage,
and present the exact SHA-256 durability receipt bound into signer
configuration and its normalized security-context digest; the in-memory test
store is rejected. This slice validates capability and receipt agreement at
that injection boundary; it does not issue or independently authenticate the
durability receipt. The signed replay binding includes the authority's
immutable identifier. Runtime rejects a mismatched, missing, or volatile
authority. One atomic state document, a canonical transaction lock beside that
document under the signer-owned runtime root, compare-and-swap commits, and
one-step crash roll-forward prevent split-file ambiguity. The transaction lock
is descriptor-path verified and does not depend on process-local temporary
directories. Descriptor verification supports Windows and Linux with procfs;
other POSIX environments fail closed. Nonce freshness is checked at durable
reservation and again at durable
commit. The principal policy authorization is durably
consumed before the backend is exposed; service failure never restores it.
Runtime recomputes the signed security-context digest over paths, peer policy,
limits, key profile, policy, durability receipt, and replay namespace. Startup
also requires the exact serialized config digest from outside the config file.
Unsigned, expired, altered, self-consistently re-digested,
profile/key-substituted, replayed, rolled-back, deleted,
high-water-mismatched, and out-of-root inputs fail closed. Runtime receipts
stop claiming that no file I/O occurred once injected proposal trust, key, or
replay dependencies have been invoked. Once any injected dependency is called,
every negative side-effect attestation that the runtime cannot directly
observe is false; the receipt does not infer purity from the dependency
interface.

The production signer CLI accepts the exact outside-repository run packet
named by `--run-packet` only after a process-local one-shot launch selection
has been minted by the existing signed runtime-manifest verifier. The
selection binds the exact config/run-packet bytes, repository/runtime roots,
and generation; copied, serialized, replayed, or caller-created values reject
before any caller-selected file read, key-resolver construction, or socket
startup. The production bootstrap accepts only `WSP71_PERMISSIONED`;
`TEST_ONLY_DRYRUN` remains confined to lower-level test APIs. The signer then
derives an immutable
instance binding covering the recomputed packet ID, config digest, session,
socket, exact `(profile_id, public_key, key_epoch)` tuples, CLI arguments, and
fixed no-spawn/no-shell safety fields. `reddog_signer_mutual_peer_handshake.py`
provides a fresh short-lived challenge whose Ed25519 response is checked
against that signer-owned binding, configured key, fingerprint, epoch, and
kernel-attested requester. The response carries a second, domain-separated
signature covering its audit metadata and acceptance attestations. A matching
public-key string or serialized `peer_handshake_verified` flag is not
authority. `reddog_current_generation_manifest_launch_selection.py` now
supplies the verifier-only selection boundary for an externally managed signer:
it reads the authenticated durable generation, ignores caller manifest data,
verifies the content-addressed manifest with the canonical Ed25519 backend,
and rechecks all seven current artifact bytes before issuing a one-shot
process-local capability. The CLI accepts `--owner-authority-config` only
through a root-owned, non-group/world-writable Linux/WSL file outside the
repository. One no-follow descriptor chain reads the checked directory and
file, and every ancestor must be root-owned and non-writable. That file pins
the generation public key, anchor, high-water
identity, monotonic witness, and three disjoint persistence roots; it rebuilds
read-only verifier capabilities, mints an opaque process-local owner authority,
and rejects config/run-packet path substitution. The public CLI cannot accept
an injected manifest selector. RedDog and `main.py` do not load this file and cannot spawn or
stop the signer. Distinct-principal service-manager deployment and use-time
consumption at every authority call remain fail closed.
Production bootstrap also requires the exact generation-bound selection;
legacy manifest-selection compatibility is confined below service admission.

Signer generation persistence separates the signer-side authentication
capability from the verifier supplied to RedDog. The concrete high-water store
uses an authenticated pending transaction outside the anchor rollback domain;
restart recovery may commit or abort only that exact pending transition.
`DurableSignerRuntimeGenerationReader` is the lifecycle-facing API. It uses
dedicated confined read-only JSON loaders and a factory-issued Ed25519
public-key verifier authority; its reachable object graph retains no signer or
mutable runtime store. Nontransactional high-water implementations are
rejected. An authenticated store is not by itself production
authority: an independently administered authority boundary and immutable
generation-bundle activation are still required.

Atomic generation provisioning signs the final seven-artifact runtime root
and activates its authenticated generation only after a last-byte check. The
atomic coordinator discards caller-selected verifiers and directly applies canonical Ed25519 verification to the authority key and key epoch. Python in-process objects are not claimed as a hostile-code boundary; distinct-principal signer lifecycle admission remains separate. The
activation lease is production-capable on Windows, where open handles deny
write/delete sharing. POSIX/WSL callers receive
`runtime_artifact_activation_lease_external_owner_required`; file modes are
not represented as a same-principal immutability boundary.
The generation high-water writer intentionally requires a signer-owned
`SqliteMonotonicAuthorityStore`. Verifier-only construction must pass
`store.reader()`, which exposes `load()` but no `advance()` capability; passing
the writer fails closed. The verifier snapshots an internally owned reader and
checks SQLite identity on every open; legacy pending
records that omit `previous_anchor_state_json` reject, while every
accepted record persists the authenticated prior anchor snapshot explicitly.
Crash recovery uses normal freshness verification unless the independent
monotonic witness already proves the exact generation committed. That
committed-witness path may structurally and cryptographically roll forward an
expired manifest, but it cannot authorize a new activation. Typed recovery prevents a committed witness from being misreported when its anchor already exists.

The public generic key-provider API has no architect-proposal policy or nonce
parameters. Proposal backend construction is an internal runtime-only path
reached after principal authorization, replay-authority, durability-receipt,
and path validation. It always constructs the canonical atomic nonce store;
callers cannot inject a volatile proposal nonce store through the public
provider boundary. Proposal-enabled configuration is intentionally rejected by
the signer run-packet supplier until production principal resolution and
durable replay-authority composition exist in the CLI sidecar. Direct runtime
and bootstrap injection remain the tested integration seams in this slice.

Production policy still keeps `architect_proposal_admission_authenticity`
unavailable because the resident proposal path does not yet derive the exact
signer policy from authoritative work state, produce its principal-signed
policy authorization, configure a production principal-key resolver, request
proposal signing, supply the independently administered production high-water
authority and an authenticated durability receipt issuer/verifier, resolve
independent key/revocation/freshness trust, or supply the current attestation,
signer-runtime configuration, and principal-key resolver into `main.py`.
Direct runtime injection is tested, but the startup adapter deliberately fails
closed without all three inputs. Serialized signatures remain evidence that is
re-verified against current runtime trust; they are never authority by presence.

### Resident queue exact-SHA commit stage

The resident queue runs `exact_sha_commit` after `bounded_worker_pilot` and
before `slice_verifier`. The bounded author owns both the write and commit
steps in one claim; the reserved independent verifier remains a separate
AgentDB assignment.

`ResidentQueueExactShaCommitStageHandler` accepts only the worktree, branch,
work order, and exact artifact set already bound by worktree and bounded-worker
receipts. Artifact generation first requires one canonical production model
selection plus a verification-admitted runtime binding whose exact topology
and proof digest match signed authority at use time; self-rehashed evidence and
model substitution fail before the provider. The commit handler then rejects
pre-staged, undeclared, changed, protected, or base-mismatched state.

The resulting `reddog_resident_queue_exact_sha_commit_receipt.v1` is
canonically revalidated before the verifier request is built. The stage does
not push, publish a PR, merge, re-index HoloIndex, write PatternMemory, or
settle rewards.

### Independent assurance capacity admission

The resident queue inserts `assurance_capacity_admission` after isolated
worktree creation and before `bounded_worker_pilot`.
`ResidentQueueAssuranceCapacityAdmissionHandler` requires the AgentDB
dispatch to contain one author task and one distinct
`independent_slice_verification` task. It atomically reserves the verifier
through `AgentDB.reserve_independent_assurance()` or returns
`BLOCKED_ASSURANCE_CAPACITY` with a durable retry time. No code stage runs
without the reservation.

Successful admission is a yield boundary. The queue-stage owner persists the
admission result and returns without running `bounded_worker_pilot` or
`slice_verifier`. OpenClaw separately claims the bounded author task; the
reserved verifier remains assigned to its distinct principal until the exact
slice-verifier stage is ready. Author failure revokes the reservation and
cancels the verifier task. An expired verifier lease may be renewed only at
that ready stage, with a bounded renewal count and maximum lease horizon.

The request binds reservation ID/digest, verifier task, principals, work order, snapshot, and WSP 15 allocation. Renewed leases cannot replace
that lineage. The verifier stage rehydrates the durable reservation and
emits a receipt-bound completion request only when the receipt repeats the same
bindings; it does not complete the task or reservation. The signed-worker
AgentDB finalizer reauthenticates the durable staged request and atomically
commits the task, assurance, and result ledger. CI, CodeQL, and red-team checks are
additional evidence; they do not replace the independent reservation.

### Generic provider-call evidence

`create_precall_evidence()`, `arm_provider_call()`, and
`terminalize_provider_call()` define the exact
`reddog_provider_call_evidence.v1` state machine. `call_id` is stable for one
request envelope; each state has a different canonical `receipt_id`.
`AtomicJsonProviderCallEvidenceStore` retains every validated transition under
one operation lock and commits with fsync plus atomic replace. Exact replay is
idempotent; divergent replay and non-monotonic transitions are rejected.

Production audit/architect runners require an injected store or the explicit
outside-repository `REDDOG_PROVIDER_CALL_EVIDENCE_STORE_PATH`. They persist
`BLOCKED_PRECALL` (`attempted=false`), atomically arm `INDETERMINATE`
(`attempted=true`), invoke the provider only after both writes, then persist
`COMPLETED` or `FAILED`. Any normal post-invocation exception carries the last
content-free local evidence through `ProviderCallAttemptError`; a failed
terminal write therefore returns armed `INDETERMINATE` truth without depending
on a recovery read. Output promotion remains blocked. Served provider/model
are nullable unless the returned `provider_call_metadata` exact schema supplies
both canonical, secret-free identifiers. Requested and served providers are
canonical slugs; requested and served models are canonical `provider/model`
identifiers. URI/path/traversal, query/fragment, bearer-like, high-entropy, and
raw-sentence values are rejected. Requested configuration is never used as
served identity.

Audit rejection results retain the canonical provider-call evidence mapping
after a model attempt. Before acceptance, both consumers compare surface,
task/work-order/queue/run/cycle lineage, runtime-binding ID and digest,
requested provider/model, attempted state, and terminal outcome field by field
against the invocation binding. Any lineage field without an expected binding
must be null, and the receipt must be canonical, attempted, and `COMPLETED`.
Omitted, extra, forged, mismatched, or non-completed evidence fails before
report acceptance or queue construction. Accepted architect determination
identity is computed from the provider call ID, provider receipt ID, and
canonical evidence digest, so the queue parent cannot outlive or substitute
its provider lineage.

`FusionProgressRecorder.record_provider_call_evidence()` embeds the canonical
generic receipt as an optional all-or-none extension of
`reddog_fusion_progress_receipt.v1`. Frozen legacy-v1 receipts without those
fields remain valid. Legacy OpenRouter data remains compatibility telemetry,
not a second authoritative provider-call identity.

### FoundUpJob create_foundup Lineage

`FoundUpJob` exposes typed top-level `creation_mode`, `genesis_envelope_digest`, and `scaffold_contract_digest` fields through `create_job()` and `to_dict()` / `from_dict()`. For `create_foundup`, use `creation_mode="new_scaffold"`, explicit `PolicyFlags(dry_run_mode=True)`, canonical SHA-256 digests, and `payload.genesis_envelope`; WRE validates the route and never aliases it to build/extract.

### Durable Resident Architect Cycle

`run_reddog_resident_architect_durable_agentdb_cycle()` creates one intent-bound AgentDB cycle and advances it only through revision-checked status transitions. `AgentDbResidentArchitectCycleStore.create_cycle()` is insert-only; `transition_cycle()` requires the exact revision and allowed current status. Stored intent identity and nine process-local read-only self-attestations are immutable at this boundary. These fields are not external proof that effects did not occur. Cancellation checkpoints run between OpenClaw claims and before/following architect determination, so a stale caller cannot overwrite `CANCELLED`.

`RedDogResidentArchitectClient` revalidates the authenticated principal, FoundUp scope, grounding receipt, full intent digest, and all nine persisted process-local self-attestations on reconnect. Hash-chained transition history is recomputed internal-integrity telemetry, not signer authority, external authentication, or independently observed effect evidence.

The editor bridge and `main.py` resident host require host-supplied `REDDOG_AUTHENTICATED_PRINCIPAL_ID` and `REDDOG_AUTHORIZED_FOUNDUP_IDS`, then invoke this canonical client. The main host first emits a verified `reddog_intent.v2` through `ground_transport_work_focus()` with source `main_resident_host` and origin `main.py`; it cannot call the durable cycle directly. `REDDOG_RESIDENT_ARCHITECT_CLIENT_REQUEST_ID` controls new-request idempotency, while `REDDOG_RESIDENT_ARCHITECT_INTENT_ID` addresses an existing canonical cycle for status, cancel, or retry.

`CANCELLED` and `DETERMINED` are permanently terminal. Only `FAILED` and `TIMED_OUT` cycles may enter a revision-checked retry, and each retry appends one immutable prior-attempt summary. Persisted main-host v1 intents in both historical v1 and integrity-valid transitional v2 cycle rows have a main-transport-only status/CAS-cancel compatibility path with exact principal, FoundUp, requested-ID, row-ID, and embedded-ID checks. Historical rows remain status/cancel-only. New v1 submissions and legacy resume remain rejected; no legacy record can become an authority-bearing v2 intent.

Resident model execution requires separate runtime-binding inputs
for the read-only audit and backend architect surfaces. The audit binding is
carried content-bearing through WSP 15, swarm planning, assignment, enqueue,
and AgentDB/OpenClaw claim execution. The architect binding is separately
bound into WSP 15 and revalidated at bootstrap and determination. Both exact
receipt ID/digest pairs are part of durable intent identity, so retry/resume
cannot substitute another valid same-surface artifact. Missing, invalid,
rejected, cross-surface, or pair-mismatched receipts stop before index/model
calls or persistence; a model-selection receipt is not a runtime authorization
substitute. Fake runner injection remains a test-only seam but obeys the same
required binding checks.

### Canonical RedDog execution-valve readiness

`reddog_execution_valve_environment_supply_cli` reads the authoritative work
state, promoted authority profile, permission snapshots, and principal records
from absolute outside-repository paths and atomically supplies
`reddog_execution_valve_environment.v1`. The artifact contains no legacy token
keys or freshness controls. `GovernedExecutionValveEnvironment` enforces the
exact allowlist; a trusted caller explicitly selects canonical evaluation and
provides independently reconstructed bindings and freshness bounds.

`validate_reddog_resident_runtime_artifacts` cross-validates the seven live
artifacts but never treats the pack as authority. A content-addressed Ed25519
manifest can be produced only from verified delegated authority; the signer
rereads the artifacts and reserves a transactional nonce. Canonical artifact
writers and manifest publication share one runtime-generation fence; the
manifest binds the exact generation digest and is finalized with OS-level
no-replace semantics. Verified manifests now mint a signer-process-local,
immutable, one-shot launch selection. Activation remains blocked pending
external lifecycle composition with durable replay high-water and
current-generation verification, plus per-signing-call consumption of the
mutual peer handshake; use-time execution remains forced closed until they
exist.

Production bootstrap and the resident registry accept only
`GovernedExecutionValveEnvironment`; legacy token mappings are rejected before
the dependency bundle or effectful handlers are constructed. The legacy
evaluator remains available only as an explicit non-effectful compatibility
API. Authority verification has two typed phases. Queue and canonical use-time
preflight use `PREFLIGHT_NON_CONSUMING`. Only after all non-mutating gates pass
does the resolver issue an opaque process-local lease; the final effect boundary
invokes `AUTHORITATIVE_USE` and transactionally consumes the nonce exactly once.
That boundary reads a fresh trusted clock first; expiry or clock failure returns
without consuming the nonce or invoking the effect.
Persisted stage and model-runtime verification mappings are audit evidence and
cannot recreate either lease. Use-time validation rehydrates signed SINGLE or
PANEL evidence and binds current revocation plus promoted claim, model, Memex,
identity, FoundUp, and WSP 15 lineage before issuing a one-shot capability.

Delegated authority additionally signs the exact explicit `base_ref` and the
canonical digest of the complete work order. The executor plan carries those
bindings in its verified plan digest, and the effect runner reads `base_ref`
only from that validated plan snapshot. Terminal `AUTHORITATIVE_USE`
verification uses a fresh invocation clock before atomic nonce consumption.

Worktree creation and live OpenClaw enqueue additionally require digest-bound,
one-shot in-memory admissions. Fabricated, replayed, restarted, or spliced
serialized acceptance chains fail before the injected runner/writer is called.
The admission digest covers the complete work order, plan, and valve. Runtime
JSON dependency, authority-store, canary, and evidence reads use an independently
configured allowed root, are locked and bounded, and reject any symlink,
junction, or reparse component before resolution. Caller paths remain raw;
neither a resolved path nor the file's own parent becomes a trust root. The
use-time authority reload reads every artifact under its exact operation lock
and verifies a second locked collection before using the snapshot. Any
replacement observed across the two collections discards the complete set and
fails closed; a mixed authority set is never returned for valve evaluation.

Effect results expose `COMMITTED`, `NOT_COMMITTED`, or `INDETERMINATE`, plus a
stable attempt key and reconciliation data. A writer/runner exception after an
attempt is `INDETERMINATE`; callers must query the external system by attempt
key and cannot treat it as proof that no effect occurred. Model-selection and
Memex ID/digest pairs are propagated into signed delegated work authority, but
production remains closed because independent signed-evidence verifiers for
those pairs and the other named trust anchors are absent.

### RedDog HoloIndex Query Adapter

    from modules.communication.moltbot_bridge.src.reddog_holoindex_query_adapter import (
        HoloIndexReadOnlyQueryAdapter,
        holoindex_hits,
    )

HoloIndexReadOnlyQueryAdapter.query accepts a query, allowed-path evidence, and
a bounded result limit. Explicit constructor values or
HOLOINDEX_QUERY_SERVICE_URL/token select an externally supervised owner.
Otherwise the adapter resolves the host bootstrap's authenticated
process-private handoff. The supported owner URL uses literal `127.0.0.1`.
The adapter never exports that handoff, opens Chroma, or indexes. Each request
sends the exact clean local repository HEAD. The adapter
preserves canonical WSP, docs, knowledge, tests, skills, work-ledger, code, and
symbol buckets before normalizing hits.

The returned freshness field is CURRENT only for semantic retrieval with an
exact SHA, non-empty generation and receipt digest, and complete seven-
collection proof. Any missing, stale, lexical, or changed-generation condition
is an explicit index gap; RedDog's audit executor blocks model invocation on
that evidence. Active or unprovable maintenance fails with a stable error
code. The owner's authenticated health gate also requires a non-empty semantic
canary and repository/generation binding.

Passing an explicit SSD/receipt enables a diagnostic-only direct adapter. It
derives the only admissible receipt from `freshness_receipt_path(ssd)`. A
supplied receipt path must stable-ancestor-canonicalize to that exact path and
cannot have a link/reparse final component. Mismatch denies before receipt
loading or backend construction. The canonical receipt must then prove the
explicit invoking repository root and SSD, clean exact HEAD, generation,
complete canonical baseline and embedding space, with no active or unprovable
maintenance. Denial returns stable content-free reasons with zero hits. An
admitted result still returns a non-operational freshness state and can never
satisfy CURRENT.
Only the trusted host maintenance handshake may refresh the canonical store;
startup may route the request through governed WRE dispatch, and the RedDog
adapter has no index-write surface. This is not an OS privilege boundary:
filesystem/process isolation remains a deployment responsibility. Phase 1 is
limited to the wired RedDog operational consumers; legacy
foundups_mcp_bridge `holo_tools.py` remains a direct-store path.

### FusionAdapter (advisory Fusion worker-panel, CONTRACT-ONLY)

`reddog_fusion_progress_receipt.py` records one process-local, digest-bound lifecycle receipt for each RedDog bridge invocation. It allows only stage, role, requested/served model, provider route, generation ID, retry, timing, token, and OpenRouter cost-credit fields. Missing, malformed, or retry-ambiguous provider accounting is marked incomplete rather than reported as zero cost. Prompt/context/output/reasoning content and secret-like values are excluded. These unkeyed receipts prove internal consistency, not signer authenticity, and never grant execution or promotion authority.

```python
from modules.communication.moltbot_bridge.src.fusion_adapter import (
    FusionAdapter,            # runtime_checkable Protocol: run(FusionRequest) -> ModelContributionReceipt
    FusionRequest,            # digests/refs only; panel_models bounded 1-8; use FusionRequest.for_mock(...)
    FusionAnalysis,           # consensus / contradictions / partial_coverage / unique_insights / blind_spots
    ModelContributionReceipt, # advisory_not_canonical=True; redaction_status=BLOCKED_PENDING_REDACTION_GATE
    FusionMode,               # MOCK/DRY_RUN execute; ALIAS/SERVER_TOOL/LOCAL_FALLBACK raise RedactionGateBlocked
    FusionProvider,           # OPENROUTER/LOCAL/MOCK (only MOCK reachable in this slice)
    MockFusionAdapter,        # deterministic mock/dry-run; no network, no key read, no OpenRouter client
    RedactionGateBlocked,     # raised for any live/future mode
)
```

Contract-only (`HERMES_FUSION_ADAPTER_CONTRACT_PHASE1`). Fusion output is ADVISORY and never canonical.
Live OpenRouter is `BLOCKED_PENDING_REDACTION_GATE`. `prompt_digest` / `context_digest` must be
`sha256:<64 hex>` (raw prompt/context bodies are rejected by `FusionRequest.__post_init__`). Spec:
`docs/audits/architecture/OPENROUTER_FUSION_FOUNDUPS_INTEGRATION_AUDIT_PHASE1.md`.

#### WSP_97 Truth Boundary Checklist (HERMES_FUSION_ADAPTER_CONTRACT_PHASE1)

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | CONTRACT_ONLY_NO_LIVE_CALL | YES | `fusion_adapter.py` mock/dry-run only; live modes raise; no network import |
| 2 | NO_API_KEY_READ | YES | `fusion_adapter.py` never imports `os`; `test_module_does_not_import_os` |
| 3 | NO_DEPENDENCY_ADDED | YES | stdlib-only imports; no requirements change |
| 4 | NO_RUNTIME_WIRING | YES | no consumer imports the adapter (standalone) |
| 5 | MOCK_DRY_RUN_ONLY | YES | `EXECUTABLE_MODES = {MOCK, DRY_RUN}` |
| 6 | OUTPUT_ADVISORY_NOT_CANONICAL | YES | `ModelContributionReceipt` forces `advisory_not_canonical=True` at construction + `to_dict` |
| 7 | PRIVACY_BLOCKED_PENDING_REDACTION_GATE | YES | `redaction_status` default BLOCKED; live modes raise `RedactionGateBlocked` |
| 8 | AST_GUARD_ENFORCES_NO_LIVE | YES | `test_ast_guard_real_module_clean` (module scans clean) |
| 9 | MANIFEST_LANDED_CLAIM_CORRECTED | YES | `openclaw_integration_manifest.json` OpenRouter status `landed` -> `parked` |
| 10 | STALE_SHELL_CORRECTED | YES | `modules/infrastructure/openrouter_client/README.md` dormant marker; untracked `.pyc` left alone |
| 11 | NO_MERGE_OR_CABR_AUTHORITY | YES | no merge/CABR/payout/source-authority symbols (AST `_FORBIDDEN_NAMES`) |
| 12 | TESTS_EXERCISE_CONTRACT | YES | `test_fusion_adapter.py` calls `run()` and asserts real behavior |
| 13 | NO_SKIP_XFAIL | YES | no skip/xfail in the test file |
| 14 | FILE_SCOPE_EXACT | YES | contract module + test + manifest + README + INTERFACE + ModLogs |
| 15 | HOLOINDEX_RESULTS_RATED | YES | architect-pinned targets confirmed by direct read; ratings carried from #829 |
| 16 | INTERNAL_SENTINEL_READY | YES | adversarial SENTINEL ran; findings fixed |
| 17 | MANIFEST_STATUS_NO_LONGER_OVERCLAIMS | YES | status `parked`; no landed/ready/runtime_enabled |
| 18 | AST_GUARD_NON_VACUOUS_NEGATIVE_CONTROL | YES | `test_ast_guard_is_non_vacuous_negative_control` (>=8 violations on bad fixture) |
| 19 | HERMES_PLACEMENT_NOT_INFRA_OPENROUTER_CLIENT | YES | contract in `moltbot_bridge/src`; `openrouter_client` dormant |
| 20 | MODEL_CONTRIBUTION_RECEIPT_DEFINED | YES | `ModelContributionReceipt` dataclass (full field set) |
| 21 | RECEIPT_DIGESTS_REFS_NOT_RAW_CONTEXT | YES | `FusionRequest` has no raw field; `is_valid_digest` enforces `sha256:<64 hex>`; `test_for_mock_produces_valid_digests_and_no_raw_in_receipt` |
| 22 | FUTURE_LIVE_MODES_DECLARED_BUT_BLOCKED | YES | alias/server_tool/local_fallback declared, raise `RedactionGateBlocked` |
| 23 | REDACTION_GATE_HARD_BLOCKER_NOT_TODO | YES | `redaction_status` is a hard field default BLOCKED; live modes refuse |

Declared == Actual == 23 / 23 YES.

### Fusion Redaction Gate (CONTRACT-ONLY precondition; does NOT enable live modes)

```python
from modules.communication.moltbot_bridge.src.fusion_redaction_gate import (
    evaluate_redaction_gate,   # (prompt, context=None, audit_mode=False) -> RedactionGateResult (FAIL-CLOSED)
    redaction_status_for,      # (prompt, context=None, audit_mode=False) -> "REDACTION_GATE_PASSED" | "BLOCKED_PENDING_REDACTION_GATE"
    redact_text,               # (text, audit_mode=False) -> (redacted_text, RedactionReport)
    scan_forbidden,            # (text, audit_mode=False) -> [category, ...]   (empty == clean)
    RedactionGateResult,       # status/reason/redacted_prompt/redacted_context/prompt_digest/context_digest/report
    RedactionReport,           # policy_version / categories_hit:dict / blocked_categories:tuple / residual_forbidden_count:int
    REDACT_CATEGORIES, BLOCK_CATEGORIES,   # REDACT vs BLOCK action classes (disjoint)
    AUDIT_STRUCTURAL_CATEGORIES,           # frozenset of BLOCK cats made audit-visible (subset of BLOCK)
    REDACTION_GATE_PASSED, REDACTION_BLOCKED, ALLOWED_REASONS,
)
```

**Audit mode** (`audit_mode=True`, default `False` -> non-audit path byte-identical;
REDDOG_AUDIT_MODE_REDACTION_PHASE1, slice 3/3): governance audits must READ governance STRUCTURE.
The four `AUDIT_STRUCTURAL_CATEGORIES` (`source_authority`, `merge_authorization`,
`cabr_payout_authority`, `governance_instruction`) match on the bare identifier and so BLOCK the whole
payload on the default path. In audit_mode those identifiers are PRESERVED (readable enum/field/gate/
action names + WSP refs) while dedicated audit VALUE redactors + every always-on REDACT detector STILL
remove any secret VALUE / payout AMOUNT / authorization TOKEN. Audit mode NEVER relaxes
`private_reasoning` (free-text always BLOCKS), `private_key_residual` (ambiguous -> BLOCKS), or any
REDACT category. Rule: keep the left-hand key/identifier; redact the right-hand value; when ambiguous,
REDACT (fail-closed). `run_alias_live(..., audit_context=True)` threads the flag from an audit-context
retrieval (slice-2 direct-read fallback of required governance targets).

Two action classes. **REDACT** (API keys, bearer, .env secrets, complete private-key blocks, member
PII, credential URLs) are replaced; the payload may PASS if the post-redaction re-scan is clean.
**BLOCK** (private chain-of-thought, merge-authorization tokens, source_authority, CABR/payout/benefit
authority, governance instructions, malformed key headers) keep status `BLOCKED_PENDING_REDACTION_GATE`
even if a token were swapped. Digests are computed FROM the redacted output. Reasons are low-cardinality
(`clean`/`redacted`/`blocked_policy`/`residual_forbidden_pattern`/`redactor_error`) and never echo raw
input. This slice does NOT enable live OpenRouter -- alias/server_tool/local_fallback still raise
`RedactionGateBlocked`. Spec: audit `OPENROUTER_FUSION_FOUNDUPS_INTEGRATION_AUDIT_PHASE1.md` Section 9.

#### WSP_97 Truth Boundary Checklist (HERMES_FUSION_REDACTION_GATE_PHASE1)

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | REDACTOR_FAILS_CLOSED | YES | `evaluate_redaction_gate` default BLOCKED; non-text/error -> BLOCKED (`test_non_text_prompt_fails_closed`) |
| 2 | NO_SENSITIVE_LEAK_IN_CORPUS | YES | `test_redactable_item_passes_clean`: post-gate `scan_forbidden`==[] for every corpus item |
| 3 | GATE_PASSED_ONLY_ON_CLEAN_OUTPUT | YES | PASS requires zero residual + zero block markers (`evaluate_redaction_gate`) |
| 4 | LIVE_MODES_STILL_BLOCKED | YES | `test_live_modes_remain_blocked` |
| 5 | NO_LIVE_OPENROUTER_CALL | YES | gate is text-only; no client; `test_gate_makes_zero_network` |
| 6 | NO_API_KEY_READ | YES | gate never imports `os` (`test_gate_module_imports_no_os_no_network`) |
| 7 | NO_DEPENDENCY_ADDED | YES | stdlib-only (`re`, `dataclasses`, `typing`) + intra-module import |
| 8 | REDACTOR_NO_NETWORK | YES | `test_gate_makes_zero_network` (socket patched to raise) |
| 9 | DETERMINISTIC_REDACTION | YES | `test_deterministic` |
| 10 | NO_REAL_SECRET_IN_TESTS | YES | synthetic split-fragment fixtures only |
| 11 | BLOCKED_IS_DEFAULT_UNTIL_PASS | YES | `_blocked` default; status flips only on clean pass |
| 12 | NO_MERGE_OR_CABR_AUTHORITY | YES | gate touches no merge/CABR/payout/authority; those are BLOCK categories |
| 13 | TESTS_ADVERSARIAL_CORPUS_NON_VACUOUS | YES | `test_no_leak_assertion_is_non_vacuous` |
| 14 | NO_SKIP_XFAIL | YES | none in the test file |
| 15 | FILE_SCOPE_EXACT | YES | gate module + test + INTERFACE + module ModLog + root ModLog |
| 16 | HOLOINDEX_RESULTS_RATED | YES | Phase 0 ratings recorded (module ModLog); reuse evaluated (WSP 84) |
| 17 | INTERNAL_SENTINEL_READY | YES | 6 sentinel lanes ran; findings folded |
| 18 | REDACT_VS_BLOCK_POLICY_DEFINED | YES | `REDACT_CATEGORIES`/`BLOCK_CATEGORIES` (`test_redact_and_block_categories_disjoint_and_populated`) |
| 19 | BLOCK_CATEGORIES_NEVER_PASS | YES | `test_block_item_is_blocked`, `test_block_categories_never_pass_even_when_mixed_with_redactable` |
| 20 | PRIVATE_REASONING_BLOCKED | YES | `test_private_reasoning_is_blocked_not_merely_redacted` |
| 21 | DIGESTS_FROM_REDACTED_OUTPUT_ONLY | YES | `prompt_digest == digest(redacted_prompt) != digest(raw)` (`test_digests_are_from_redacted_output_not_raw`) |
| 22 | REPORT_HAS_COUNTS_NOT_SNIPPETS | YES | `categories_hit: dict[str,int]`; no raw in serialized report (`test_report_has_counts_not_snippets`) |
| 23 | NO_RAW_EXCEPTION_ECHO | YES | `test_exception_fails_closed_no_raw_echo` (raw never in reason/report) |
| 24 | NO_LITERAL_SECRET_PATTERN_IN_SOURCE | YES | `test_no_literal_secret_pattern_in_source` scans gate + test source |
| 25 | POST_REDACTION_RESCAN_REQUIRED | YES | `test_residual_forbidden_fails_closed` |
| 26 | LIVE_MODES_REMAIN_BLOCKED_AFTER_GATE | YES | `test_live_modes_remain_blocked` (fusion_adapter unchanged) |
| 27 | AUDIT_MODE_PRESERVES_STRUCTURE | YES | `test_audit_mode_preserves_governance_structure` (enum/field/action/WSP identifiers survive) |
| 28 | AUDIT_MODE_OFF_BYTE_IDENTICAL | YES | `test_audit_mode_off_is_byte_identical_default` (default path unchanged) |
| 29 | AUDIT_MODE_STILL_REDACTS_SECRETS | YES | `test_audit_mode_still_redacts_fake_api_key`, `..._oauth_token`, `..._mixed_line_keeps_key_redacts_value` |
| 30 | AUDIT_MODE_REDACTS_PAYOUT_AND_TOKEN | YES | `test_audit_mode_redacts_cabr_payout_amount_keeps_identifier`, `..._merge_authorization_token_keeps_gate_name` |
| 31 | AUDIT_MODE_NEVER_RELAXES_PRIVATE_OR_MALFORMED | YES | `test_audit_mode_private_reasoning_still_blocks`, `..._malformed_private_key_still_blocks` |
| 32 | AUDIT_STRUCTURAL_SUBSET_OF_BLOCK | YES | `test_audit_structural_categories_are_subset_of_block` (excludes private_reasoning/private_key_residual) |

Declared == Actual == 32 / 32 YES.

### Fusion ALIAS live path (VALVE-GATED OFF by default; first live OpenRouter integration)

```python
from modules.communication.moltbot_bridge.src.fusion_alias_live import (
    run_alias_live,            # (prompt, context=None, *, authorization, ..., audit_context=False) -> AliasLiveResult
    LiveFusionAuthorization,   # typed sovereign auth (authorized=True, authority="012", purpose="fusion_alias_live_call")
    AliasLiveResult,           # status / reason / made_network_call / receipt
    run_manual_smoke,          # MANUAL live smoke (module __main__); NOT a pytest, never in CI
)
```

`audit_context=True` (default `False`) threads audit-mode into the entry redaction gate for an
audit-context retrieval (slice-2 direct-read fallback of required governance targets): governance
STRUCTURE stays readable while secret VALUES / payout AMOUNTS / authorization TOKENS are still
redacted. The request body is always built from the REDACTED text only; secret redaction is never
weakened. Default `False` keeps the live path byte-identical.

Landing this makes **ZERO** live calls. A network call requires ALL of: (1) `FUSION_ALIAS_LIVE_ENABLED`
env flag ON (default OFF), (2) a valid `LiveFusionAuthorization` object (authority `012` -- a bool/int/
str/dict cannot satisfy it), (3) the redaction gate PASSED, (4) `OPENROUTER_API_KEY` present, (5) budget/
timeout within bounds. Raw text is redacted ON ENTRY; only the REDACTED prompt/context is sent to the
`openrouter/fusion` alias; only digests are retained; the API key is never logged. Output is ADVISORY
(`advisory_not_canonical=True`). All failure paths fail closed with a low-cardinality reason
(`valve_closed`/`redaction_blocked`/`authorization_missing`/`missing_api_key`/`budget_exceeded`/`timeout`/
`http_error`/`malformed_response`). SERVER_TOOL / LOCAL_FALLBACK remain blocked. HTTP client reused from
`ai_gateway` (`requests`) -- no new dependency.

**Manual live smoke (NOT CI; requires explicit 012 opt-in):**
```
FUSION_ALIAS_LIVE_ENABLED=1 OPENROUTER_API_KEY=<real-key> \
  python -m modules.communication.moltbot_bridge.src.fusion_alias_live --authorize-012
```
Without `--authorize-012` it refuses. With the valve OFF it prints `valve_closed` and makes no call.

#### WSP_97 Truth Boundary Checklist (HERMES_FUSION_ALIAS_MODE_PHASE2)

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | ALIAS_REQUIRES_PASSED_REDACTION_GATE | YES | `run_alias_live` calls `evaluate_redaction_gate` first; not-passed -> `redaction_blocked`, no call |
| 2 | VALVE_OFF_BY_DEFAULT_NO_LIVE_CALL | YES | `test_valve_off_by_default_makes_zero_network` (socket-blocked, 0 calls) |
| 3 | ONLY_REDACTED_TEXT_SENT | YES | `test_only_redacted_text_is_sent` (body == gate.redacted_prompt) |
| 4 | NO_RAW_RETAINED_OR_LOGGED | YES | `test_no_raw_prompt_or_secret_retained_in_receipt` |
| 5 | KEY_NEVER_LOGGED | YES | `test_key_never_in_result_or_receipt` |
| 6 | FAIL_CLOSED_ALL_BRANCHES | YES | timeout/http/malformed/missing-key/budget tests -> blocked, no crash |
| 7 | OUTPUT_ADVISORY_NOT_CANONICAL | YES | receipt forces `advisory_not_canonical=True` (`test_receipt_invariants`) |
| 8 | NO_NEW_DEPENDENCY_REUSE_GATEWAY | YES | reuses `requests` (ai_gateway); `test_module_no_new_dependency_imports` |
| 9 | SERVER_TOOL_LOCALFALLBACK_STILL_BLOCKED | YES | `test_mock_adapter_live_modes_still_blocked` (incl. ALIAS via mock) |
| 10 | NETWORK_MOCKED_IN_TESTS_NO_LIVE_CI | YES | all tests monkeypatch `requests.post`; no real call |
| 11 | NO_CABR_OR_MERGE_AUTHORITY | YES | gate blocks authority/merge markers; alias touches none |
| 12 | NO_REAL_KEY_COMMITTED | YES | synthetic split-fragment fake key only |
| 13 | NO_SKIP_XFAIL | YES | `test_test_file_has_no_skip_or_xfail` (AST) |
| 14 | FILE_SCOPE_EXACT | YES | alias module + test + INTERFACE + module ModLog + root ModLog |
| 15 | HOLOINDEX_RESULTS_RATED | YES | Phase 0 ratings recorded (module ModLog) |
| 16 | INTERNAL_SENTINEL_READY | YES | 5 sentinel lanes ran; findings folded |
| 17 | FUSIONREQUEST_REMAINS_DIGEST_ONLY | YES | `fusion_adapter` unchanged; raw text is a function arg, never a FusionRequest field |
| 18 | LIVE_INPUT_NOT_PERSISTED_OR_LOGGED | YES | raw prompt/context only function-local; never stored/logged |
| 19 | AUTHORIZATION_NOT_BOOL_COERCIBLE | YES | `isinstance LiveFusionAuthorization` (`test_env_flag_alone_cannot_enable_network`) |
| 20 | ENV_FLAG_ALONE_CANNOT_ENABLE_NETWORK | YES | env on + bad/no auth -> `authorization_missing`, 0 calls |
| 21 | RAW_PROMPT_ABSENT_FROM_HTTP_BODY | YES | `test_only_redacted_text_is_sent` (raw absent, `scan_forbidden`==[]) |
| 22 | RAW_CONTEXT_ABSENT_FROM_HTTP_BODY | YES | `test_redacted_context_sent_raw_context_absent` |
| 23 | BLOCK_CATEGORY_BUILDS_NO_REQUEST | YES | `test_redaction_blocked_builds_no_request` (0 calls) |
| 24 | RESPONSE_RECEIPT_ADVISORY_ONLY | YES | receipt advisory; `redaction_status=REDACTION_GATE_PASSED` |
| 25 | RESPONSE_DOES_NOT_RETAIN_REQUEST_RAW | YES | response re-scanned; `test_response_secret_is_redacted_in_summary` / `_block_marker_is_withheld` |
| 26 | TIMEOUT_AND_BUDGET_BOUNDED | YES | bounded timeout + `MAX_TOKENS_CEILING`; `test_budget_exceeded_fails_closed` |
| 27 | NO_STREAMING_PHASE2 | YES | `test_no_streaming` (`stream=False`) |
| 28 | LIVE_SMOKE_MANUAL_NOT_CI_SKIP | YES | smoke in `__main__`; `test_manual_smoke_is_main_guarded_not_collected` |

Declared == Actual == 28 / 28 YES.

### WebhookReceiver

```python
from modules.communication.moltbot_bridge.src.webhook_receiver import app

# FastAPI app exposing:
# POST /webhook/openclaw - Receives messages from OpenClaw Gateway
# POST /webhook/moltbot - Legacy endpoint (compat)
# GET /health - Health check endpoint
```

### Message Format (Inbound from OpenClaw)

```python
class MoltbotMessage(BaseModel):
    message: str                    # User's message text
    sessionKey: str                 # Session identifier
    channel: str                    # Source channel (whatsapp, telegram, etc.)
    sender: str                     # Sender identifier
    metadata: dict = {}             # Additional context

# OpenClawMessage is an alias of MoltbotMessage (preferred naming)
```

### Response Format (Outbound to OpenClaw)

```python
class FoundupsResponse(BaseModel):
    text: str                       # Response text
    deliver: bool = True            # Whether OpenClaw should deliver response
    channel: str | None = None      # Override delivery channel
    to: str | None = None           # Override recipient
```

### Standalone Action CLI (Direct Agent Invocation)

```bash
python -m modules.communication.moltbot_bridge.src.action_cli \
  --command "linkedin action read_feed max_posts=3"
```

Supported command families:
- `linkedin action <action> key=value`
- `x action <action> key=value`
- `social campaign <campaign_name> key=value`
- `youtube action <action> key=value`
- `yt action <action> key=value`

Optional routing controls:
- `--via-dae` (use full OpenClawDAE intent + permission path)
- `--backend openclaw|ironclaw` (with `--via-dae`)
- `--no-api-keys auto|on|off` (with `--via-dae`)
- `--repeat N --interval-sec S` for repeatable standalone runs

Safety note:
- Direct adapter mode now runs Cisco skill-safety gate before execution.
- `--via-dae` mode also applies OpenClawDAE skill-safety gating.

LinkedIn `digital_twin` action parameters:
- required: `comment_text`, `repost_text`, `schedule_date`, `schedule_time`
- optional: `mentions` (comma-separated), `identity_cycle` (comma-separated), `dry_run`

Current adapter behavior:
- `execute_linkedin_action(action="digital_twin", ...)` forwards all above params to `LinkedInActions.run_digital_twin_flow(...)`.

Structured result contract:

```json
{
  "success": true,
  "command": "youtube action comments channel=move2japan ...",
  "mode": "adapter|dae",
  "repeat": 1,
  "results": [
    {
      "success": true,
      "route": "youtube",
      "action": "comments",
      "iteration": 1,
      "duration_ms": 1234,
      "memory_stored": true
    }
  ]
}
```

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

## Auth Headers

- `Authorization: Bearer <token>`
- `x-openclaw-token: <token>` (preferred)
- `x-moltbot-token: <token>` (legacy)

### OpenClaw DAE (Frontal Lobe)

```python
from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE

dae = OpenClawDAE(repo_root=Path("O:/Foundups-Agent"))

# Full autonomy loop:
# Ingress -> Intent -> Preflight -> Plan -> Permission -> Execute -> Validate -> Remember
response = await dae.process(
    message="What is the WRE orchestrator?",
    sender="user123",
    channel="telegram",
    session_key="session-id",
    metadata={},
)
```

### 2026-03-28 Operating Contract

Per `WSP 77`, OpenClaw is currently a bounded execution surface, not the primary architect.

- `0102` = architecture authority, prioritization, review
- `OpenClaw / Kohi` = bounded maintenance execution
- `HoloIndex` = retrieval bundle for direction and available subroutines
- `WRE` = deterministic execution plane

Current OpenClaw use case:
- fix simple codebase issues
- run focused checks
- emit runtime events
- write durable reports / knowledge artifacts

Current execution contract:

`assigned work -> retrieve bounded HoloIndex bundle -> execute -> verify -> emit -> remember`

### ExecutionBundle (WSP 87/97)

```python
from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
    ExecutionBundle,
    build_execution_bundle,
    retrieve_bundle_for_memory_query,
)

# Build pre-execution context for any query
bundle = build_execution_bundle(
    query="find test fixtures",
    route="holo_index",
    limit=5,
    include_patterns=True,
    include_docs=True,
)

# Bundle fields:
# - query: The original request
# - route: Execution route (holo_index, wre_orchestrator, etc.)
# - docs: Relevant doc paths (README, INTERFACE, ModLog)
# - patterns: Prior successful patterns from breadcrumbs
# - candidate_paths: File paths likely relevant to execution
# - constraints: WSP constraints or permission requirements
# - verification_hints: Signals for verifying successful execution
# - confidence: Bundle quality score (0.0-1.0)
# - code_hits: Raw HoloIndex code search results (for route consumption)
# - wsp_hits: Raw HoloIndex WSP search results (for route consumption)

# Check if bundle has enough context
if bundle.is_actionable():
    # proceed with execution
    pass

# Specialized memory query bundle
memory_bundle = retrieve_bundle_for_memory_query("decisions", topic="architecture")
# Always high confidence (0.9) for deterministic memory queries
```

Design principles:
- Bundles are execution aids, not architecture authorities
- Compact only — no giant context dumps
- Deterministic — same query produces same bundle shape
- Suitable for bounded doer, not open-ended cognition

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

Authorization:
- `list` and `status` are read-only
- `launch` and `stop` require `012` authority

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
- `READY_FOR_EXECUTION` does not claim that a live canary ran. Missing authority artifacts, signer socket, Git/GitHub readiness, or OpenRouter key presence returns `BLOCKED` without exposing values.
- The surface has no signer launch, secret resolution, PR-ready, merge, reward, or HoloIndex re-index authority.

Transport-neutral grounding additionally supports a fail-closed repository
audit fallback for entity-scoped audits (including `pfmall`, `p.fMALL`,
`p-fmall`, and `PFMALL`). The owner query runs first. Only when that evidence is
unavailable, stale, or insufficient does the service use the shared bounded
repository discovery reader. Acceptance requires entity-bound paths, exact
fixed-policy limits, one implementation-source read, and one independent
test/contract read. The resulting `reddog_repo_audit_fallback.v1` records the
creation-time HEAD and evidence digests and is nested in the canonical
`reddog_grounded_target_receipt.v1`. At consumption, both deterministic and
model-backed audit executors reopen every selected path with the confined
reader and match path, digest, bytes, and truncation; the model-backed executor
checks again after the model returns. Thus an unstaged content change rejects
even when HEAD is unchanged. Selected paths replace the unresolved semantic
target only after these checks.

### OpenClaw Supervisor Contract

Canonical 0102 lifecycle owner:
- runtime id: `openclaw_supervisor`
- implementation: `src/openclaw_supervisor.py`
- broker launch wrapper: `scripts/launch.py`

Current explicit states:
- `BOOT`
- `PREFLIGHT`
- `OBSERVE`
- `TRIAGE`
- `PLAN`
- `EXECUTE`
- `VERIFY`
- `REMEMBER`
- `ESCALATE`
- `IDLE_WATCH`

Current operational rule:
- the supervisor owns the daemon self-audit loop when enabled
- `main.py` only starts direct self-audit as a fallback when supervisor is disabled
- resident OpenClaw restarts are policy-gated through the broker/runtime surface
- restart attempts are bounded by `OPENCLAW_SUPERVISOR_MAX_RESTARTS` within `OPENCLAW_SUPERVISOR_RESTART_WINDOW_SEC`
- when the repair budget is exhausted, the supervisor escalates instead of retrying indefinitely
- the supervisor advances a DAEmon follow cursor every cycle so repair decisions are tied to observed runtime history
- IronClaw runtime readiness is validated at startup before resident/runtime bootstrap when IronClaw is the selected backend
- optional post-merge HoloIndex observation runs on one background worker;
  OpenClaw claims each exact-SHA task with compare-and-swap semantics and the
  domain executor owns atomic completion
- the one-use claim ID and context digest are passed explicitly through
  `execute_task`; CLI or in-process calls without that capability stop before
  the authority transaction

Post-merge HoloIndex configuration:

- `HOLOINDEX_POSTMERGE_COORDINATOR_ENABLED=1` enables the observer.
- `HOLOINDEX_POSTMERGE_COORDINATOR_INTERVAL_SEC` sets its bounded polling
  interval (minimum 30 seconds).
- `REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT` selects the absolute dedicated clean
  authority worktree.

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

### FOUNDUP Route Contract (FAM Adapter)

#### Catalog Commands (p.fMALL Integration)

- `list foundups` - Show all FoundUps in catalog
- `foundup catalog [category]` - Browse catalog by category (marketplace, media, science, games, community)
- `foundup status <name>` - Show FoundUp status (manifest + state overlay)
- `open <foundup>` - Get routing target URL (`/f/{foundup_id}`)

Catalog commands consume:
- Static manifests from `foundup_manifest.json` (per PFMALL_FOUNDUP_MANIFEST_SCHEMA.md)
- State overlay via provider interface (per PFMALL_STATE_OVERLAY_CONTRACT.md)
- Degrades gracefully when state provider unavailable (shows "unknown" status)

#### Launch Commands

- `launch foundup <name> with token <SYMBOL>`
- `create foundup <name> token <SYMBOL>`

Token symbol resolution:
- If token is omitted, parser auto-generates from FoundUp name.
- If token is `AUTO` (or legacy `FUP` seed), adapter auto-generates and resolves collisions.
- Collision resolution is deterministic (`BASE`, `BASE2`, `BASE3`, ...), then handed to Agent Market.

### Autonomy Tiers (Graduated)

| Tier | Who | Can Do |
|------|-----|--------|
| ADVISORY | Anyone | Read-only: search, status, chat |
| METRICS | Commander | + Write metrics/logs |
| DOCS_TESTS | Commander | + Edit tests and docs |
| SOURCE | Commander (explicit) | + Edit source code |

### WSP 73 Partner-Principal-Associate

- **Partner**: OpenClaw bridge receives intent, owns dialogue
- **Principal**: OpenClaw DAE decomposes tasks, selects domain DAEs
- **Associates**: Domain DAEs execute (communication, platform, dev, content)

### Security

- Non-commanders: ADVISORY only (no mutations)
- COMMAND/SYSTEM intents blocked for non-commanders (WSP 50)
- Cisco skill scanner preflight runs before mutating/skill-driven routes:
  `command`, `system`, `schedule`, `social`, `automation`, `foundup`
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

### Skill Safety Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENCLAW_SKILL_SCAN_REQUIRED` | No | `1` fail-closed if scanner missing (default) |
| `OPENCLAW_SKILL_SCAN_ENFORCED` | No | `1` block risky scans above threshold (default) |
| `OPENCLAW_SKILL_SCAN_MAX_SEVERITY` | No | Scanner threshold (default `medium`) |
| `OPENCLAW_SKILL_SCAN_TTL_SEC` | No | Cached scan TTL in seconds (default `900`) |
| `OPENCLAW_SKILL_SCAN_ALWAYS` | No | `1` bypass TTL and scan every mutating route |
| `OPENCLAW_SKILL_MANIFEST_REQUIRED` | No | `1` require workspace skill hash manifest (default) |
| `OPENCLAW_SKILL_MANIFEST_ENFORCED` | No | `1` block on manifest mismatch/missing (default) |
| `OPENCLAW_SKILL_MANIFEST_VERIFY_SIGNATURE` | No | `1` verify HMAC signature in manifest |
| `OPENCLAW_SKILL_MANIFEST_ALLOW_EXTRA` | No | `1` allow skill files not listed in manifest |
| `OPENCLAW_SKILL_MANIFEST_FILE` | No | Optional override path to manifest JSON |
| `OPENCLAW_SKILL_MANIFEST_HMAC_KEY` | No | Optional HMAC key for signature verification |

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

### COMMAND Graceful Degradation

When WRE is unavailable, COMMAND intents return deterministic advisory fallback:

```python
# Returns advisory with:
# - "Advisory Mode" header
# - Command recognition
# - Three actionable options (CLI, retry, query mode)
# - Optional error detail
```

## WSP Compliance

- **WSP 46**: WRE Protocol (execution cortex)
- **WSP 49**: Standard module structure
- **WSP 50**: Pre-Action Verification (preflight gate)
- **WSP 73**: Digital Twin architecture integration
- **WSP 77**: Agent coordination (4-phase execution)
- **WSP 91**: Observability (structured logging)
- **WSP 96**: Skill execution (micro chain-of-thought)

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
- `openclaw_dae.py` now stays below the large-file threshold at `1342` lines
- execution-plane resolution now matches `WSP_97`: resolve intent -> gate -> plan -> route -> validate -> remember

## Runtime Supervision Commands

OpenClaw can now read the DAEmon live ledger for itself and broker-managed DAEs:

- `tail openclaw`
- `status openclaw live`
- `tail pqn research`
- `status pqn research live`
- `tail holodae`

These commands are read-only. They use the central DAEmon observer surface and do not mutate runtime state.

## Skill Evolution Loop

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
