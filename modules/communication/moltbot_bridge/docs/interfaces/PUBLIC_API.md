**Bridge interface: Public Api.**

[Interface directory](../../INTERFACE.md). Qualification boundaries below remain as recorded.

<a id="contract-078"></a>

## Public API
<a id="contract-079"></a>

### Architect proposal validity and execution readiness

`evaluate_architect_proposal_executability()` requires audit-supported reuse, exact
scope/tests/gates/evidence, and emits admission v2. Validity remains separate from readiness;
model claims and future capabilities are not current authority. Promotion rechecks platform,
HEAD, HoloIndex, work state, snapshot, candidate, WSP 15, and conversation authority before
queue mutation. The immutable admission SHA is the authorized base; INDEX_GAP requires the
existing maintenance exception. The main bootstrap re-exports its stable result class and
READY/NOT_READY constants from `reddog_main_readonly_operational_bootstrap_result`; all 53
projection fields retain their prior ready/not-ready enqueue and no-effect semantics.

The receipt's SHA is integrity evidence, not authentication.
Operational Memex supply receipts are exact-schema rehydrated before resident
artifact handoff, authority-profile seed creation, proposal signing, and final
promotion. The gate recomputes the receipt ID, enforces principal, FoundUp,
snapshot, HoloIndex-generation, and source-revision bindings, and applies a
300-second maximum age plus 600-second maximum policy lifetime. The complete
canonical receipt digest is covered by the signed proposal attestation; a
syntactically valid or attacker-rehashed `sha256:` identifier is not authority.
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

<a id="contract-080"></a>

### Verified-outcome authority, signing and memory

The [complete contract](../../../../../docs/operations/RSI_SWARM_DISPATCH.md#verified-outcome-api-reference) retains the root, signer, publication and memory boundaries previously listed here. The [activation recovery checkpoint](../../../../../docs/operations/RSI_SWARM_DISPATCH.md#activation-recovery-checkpoint--2026-09-14) records the latest local layer and the unimplemented acceptance transaction contract.

| Existing API / owner | Current contract |
|---|---|
| Root service / `commit_service_authority(...)` / `commit_service_response_record(...)` | V1 signature-digest commitment remains separate. V2 commits the full record after exact pending-byte readback under current peer/proof/grant checks; requires exact v2 digest acknowledgment. Its proof-input companion bounds the complete 64 KiB wire before signing; one exchange, no implicit retry or read authority. |
| `validate_verified_outcome_signing_response(response, signing_input, *, signer_public_key, key_epoch, requester_principal_id, signature_verifier)` | Exact-True attestations, empty rejection code and verified receipt/audit signatures; a predicate cannot confer authority. |
| `VerifiedOutcomeResponseBinding(descriptor_id, owner_config_id, authorization_id, reservation_id)` | Frozen public identifiers, never a root capability. |
| `build_verified_outcome_response_record(request, response, *, descriptor, binding, signature_verifier) -> bytes` | Canonical v1 full signed history, exact types/schema, complete 64 KiB cap. |
| `parse_verified_outcome_response_record(raw, *, expected_binding, expected_record_digest, signature_verifier) -> tuple[SigningRequest, SigningResponse]` | Checks independently supplied pins and historical signatures; supplies no current read authorization. |
| Root response storage: `persist_pending_response(...)`, `commit_pending_response(...)`, `load_committed_response_for_root(*, expected_binding, expected_record_digest, expected_generation, now_epoch) -> bytes` | Pending preserves sequence 1; commit binds sequence 2 to the full record digest. Root storage read requires exact current generation/selection/terminal pins, ownership, signatures and the original authority time window. It grants no read permission and enables no RPC; current independent admission remains required before disclosure. |
| `AuthorityRuntimeVerifiedOutcomeStore.load_publication(record_id)` / `publish()` | Validated STAGED/ACTIVE retry evidence; three revision attempts preserve the signed envelope and unrelated state. Staging is invisible to consumable readers. |
| `SignedVerifiedOutcomeEvidencePublisher.publish()` | Exact durable winner acknowledgment preserves original issuance/signature; no re-signing, renewal or activation. |
| `ResidentQueueChainResultReceipt.recorded_at` | Canonical held-out event time supplies admission `verified_at`; bootstrap time cannot repair absent historical time. |
| PatternMemory staging / authority-envelope consumption | `AuthorityRuntimeVerifiedOutcomeStore(store, *, accepted_outcome_source=None)` requires its configured source's `load_verified_outcome(record_id)` to return the exact accepted canonical record before/after new activation and at envelope reads. Unbound/missing/changed/unreadable sources reject; ACTIVE retries recheck memory. Activation reloads exact durable evidence after each commit attempt, recovers an identical ACTIVE winner/lost reply, and retries only revision conflicts up to three commits. Cancellation propagates; unreadable/substituted or uncommitted state cannot acknowledge success. Staging/publication retry remains separate. Current source binding, durable authority and opaque one-use capability remain required; the real sink rejects direct activation. |
| Learning-candidate gate / reconstruction verifier | Bounded `STRUCTURAL_ONLY` evidence, not authenticated provenance, work authority or runtime admission. |

Pending payloads use the fixed primary-root file `verified-outcome-pending-responses.json`, the existing atomic store, at most eight records and a complete 512 KiB snapshot. The payload has one copy; mirrored digests cannot reconstruct lost bytes. Only retained exact bytes can repair a missing file.
`SqliteMonotonicAuthorityStore.restore_missing_from_witness(binding_digest, *, witness, expected)` copies an exact checkpoint from an identity-checked readonly witness in a disjoint storage root. The root owner serializes recovery; conflicting destination state rejects and ordinary CAS retains None → 1 / exact +1. See the checkpoint for post-commit uncertainty and store-reopening conditions. Authenticated readback, ordinary v2 signer/publisher wiring, process/volume qualification, operation deadlines, independent activation and retained improvement remain open.

`build_grant_service_archive_from_git()` reads only exact commit-tree blobs and
emits canonical archive schema v2. `validate_grant_service_archive_git_provenance()`
requires the independently expected archive-to-repository source map and
re-reads each bounded Git object. These APIs prove source lineage but grant no
build, manifest-signing, launch, socket, secret, or repository authority;
production policy does not yet admit them.

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
principal private key. Socket v2 accepts one exact request-bound secret-access
grant and rejects v1 grant smuggling. The E0 signer boundary verifies that
grant, its attested peer, replay-store instance, permission snapshot, owner
configuration, signer generation, operation, tier, request digest, and key
identity before resolving WSP71 keys. It atomically consumes durable replay
state before resolution and linearizes revocation, expiry, signing, and the
post-sign checks under one authority fence. The returned signature is verified
against the bound public key; backend self-reporting is never authority. Replay
rollback uses the existing MAC nonce state and independently durable SQLite
high-water store, with exact absolute paths bound into the store-instance
digest. Production composition rejects missing, mismatched, alternate-path, or
volatile stores. An exact signed revocation-snapshot contract now binds the
current E0 policy, generation, authority, target signer, and durable store.
An uncomposed local witness and policy v3 bind the root-state anchor; the oracle
requires three-way agreement; two mutable root mirrors can be rolled back while the
static installation domain remains unchanged. Root-service transport, protected-use client,
and composed oracle exist. Owner config v3 plus the uncomposed independent-grant client supply bind a disjoint Unix socket, exact non-root peer UID/GID, and signed policy identity; the WSP71 resolver factory and client remain uncomposed, so system-service signing fails closed.
The standalone WSP71 ephemeral factory validates each successful resolver result's
exact reference and expected short audit hash or full E0 digest, then returns
full grant-binding hashes using `signer_key_reference_digest`. The original
resolver must pass provider-mode checks before adaptation. This metadata check
does not authenticate the resolver; global audit hashes and legacy provider
results retain their existing format. Synthetic socket-v2 composition is tested;
the production system-service entrypoint remains uncomposed and fail-closed.
`Wsp71EphemeralSignerBackendFactory` also accepts optional
`signer_peer_instance_binding: SignerPeerInstanceBinding | None`, appended after
its existing fields. Each fresh backend receives this same binding. The default
remains `None`, so unbound handshakes still reject. The existing handshake validator
checks request/instance equality; the factory neither authenticates supplied
bindings nor grants a current-generation lease. Synthetic direct/factory handshake
tests verify matching signatures and session/generation/profile rejection.
Native-memory zeroization and complete signer lifecycle supervision remain
SPECIFIED_NOT_IMPLEMENTED.
No private key, resolved secret, grant signature, or audit key is serialized.
The existing proposal policy, atomic state, canonical transaction lock, and
compare-and-swap crash recovery remain unchanged. Descriptor verification
supports Windows and Linux with procfs; other POSIX environments fail closed.
Nonce freshness is checked at durable reservation and again at durable
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
authority. `ExternalSignerLifecycleAdmissionReceipt` preserves exact nonblank string `requester_principal_id` and `signer_profile_id` from the matching healthcheck in its digest-bound audit payload; receipt IDs change with either identity. These are required fields, not an authorization or a decoder for older receipts. `consume_verified_external_signer_lifecycle_admission(boundary, capability, *, requester_principal_id, signer_profile_id, require_default_dependencies=False)` captures the canonical registry/exact boundary type and consumes through its registered closure before exact identity correlation; it never trusts public `consume` dispatch or a receipt supplied as a capability. Malformed expected identities and foreign boundaries preserve the original handle; valid owned identity mismatch spends it. Returned flags remain false. Resident integration and live authority remain separate. `reddog_current_generation_manifest_launch_selection.py` now
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
provider boundary. Proposal-enabled configuration can be serialized by the
run-packet supplier. The public service entrypoint composes existing current-owner
principal resolution and provisioned durable replay authority after isolation.
Connected tests exercise that path with explicit enrollment/OS/transport fixtures;
packet creation does not start a service or establish native admission.

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

<a id="contract-081"></a>

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
model substitution fails before `foundups_fusion`, sandbox-verified upstream
`openclaw agent`, or the upstream Hermes API; actual invocation effects remain
receipt-bound. `hermes_api` consumes the signed principal model/provider route,
fixed authenticated loopback `/v1/runs`, exact version/profile and bearer checks,
sole `delegation`/`delegate_task`, zero skills and one stable completed leaf.
Empty child file arrays, ordered delegate completion and unchanged postflight
policy are required; final event and polled output must match. Server tool execution
without split-runtime confinement excludes shell/file/web/browser/MCP/memory/approval tools.
Second children, other tools, approvals, timeout, malformed output or drift reject.
Stop/status remain best-effort. Parent-only stop or noncompleted/forbidden terminal
rejection reports `effect_observation_complete=false` and `run_abort_confirmed=false`;
effects remain possible and artifacts are withheld. This establishes neither child
cancellation nor delivery and leaves successful acceptance gates unchanged. Accepted
maps pass bounded relative-path/non-empty UTF-8 validation to the existing materializer;
commit rejects pre-staged, undeclared, changed, protected or base-mismatched state.

The resulting `reddog_resident_queue_exact_sha_commit_receipt.v1` is
canonically revalidated before the verifier request is built. The stage does
not push, publish a PR, merge, re-index HoloIndex, write PatternMemory, or
settle rewards.

<a id="contract-082"></a>

### Independent assurance capacity admission

Main's enabled resident serial preflight supplies the existing AgentDB store,
using the same configured DatabaseManager backend as signed-worker dispatch.
No new database or environment selector is introduced. Initialization errors
record an unaccepted startup result before dispatch; enforced startup fails.
Disabled startup and earlier rejected draft-runner modes do not open this store.
This connection does not supply missing signer, consensus or lease authority.

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

<a id="contract-083"></a>

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

<a id="contract-084"></a>

### FoundUpJob intake and create_foundup lineage

`dispatch_foundup()` requires existing commander authority before mutation intake. It accepts a plain `metadata.genesis_envelope` (compatible legacy `payload.genesis_envelope` only if unambiguous), revalidates a detached copy and queues the frozen envelope with tenant/session/FoundUp identity. Malformed declared data and conflicting parsed targets return `NOT_READY`; bare explicit builds retain their queue behavior. Draft public authentication and `requested_by` are not commander authority. Jobs remain dry-run with no fabricated execution evidence, creation mode or typed digest. Separately, `FoundUpJob` exposes `creation_mode`, `genesis_envelope_digest`, and `scaffold_contract_digest` through `create_job()` and round-trip serialization. The admitted `create_foundup` route requires `new_scaffold`, explicit dry-run policy, planner-compatible digests and `payload.genesis_envelope`; WRE never aliases that route to build/extract. This handoff does not grant scaffold or worker admission.

<a id="contract-085"></a>

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

<a id="contract-086"></a>

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
immutable, one-shot launch selection. Activation remains blocked by the peer
handshake and six other anchors. The resolver consumes the root-owned selection
and verifies its manifest/config/run-packet, replay high-water, generation, and
freshness using the resolver's trusted clock. Its audit receipt cannot become
effect authority; only the isolated signer peer may issue a future live lease.

Production bootstrap and the resident registry accept only
`GovernedExecutionValveEnvironment`; legacy token mappings are rejected before
the dependency bundle or effectful handlers are constructed. The legacy
evaluator remains available only as an explicit non-effectful compatibility
API. Authority verification retains two typed phases. Queue and use-time
preflight use `PREFLIGHT_NON_CONSUMING`. Current resolver output is audit
evidence only: it records the manifest/replay/generation receipt while external
peer-authenticated effect-lease issuance remains unimplemented. It cannot invoke
`AUTHORITATIVE_USE`, consume a nonce, or authorize an effect.
Persisted stage and model-runtime verification mappings are audit evidence and
cannot recreate an external lease. Use-time validation rehydrates signed SINGLE
or PANEL evidence and binds current revocation plus promoted claim, model,
Memex, identity, FoundUp, and WSP 15 lineage before returning its audit
decision.

Delegated authority additionally signs the exact explicit `base_ref` and the
canonical digest of the complete work order. The executor plan carries those
bindings in its verified plan digest, and the effect runner reads `base_ref`
only from that validated plan snapshot. Future terminal `AUTHORITATIVE_USE`
must use a fresh invocation clock before atomic nonce consumption.

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

<a id="contract-087"></a>

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

`GenerationBoundHoloIndexQueryAdapter.query(...)` is the production default
for resident/OpenClaw read-only audit workers when no adapter is injected. It
reuses `scripts/reddog_holoindex_owner_query_once.py` through its intended
one-shot child-process boundary. The child receives a strict internal deadline;
the parent enforces a final wall timeout with bounded file-backed stdout/stderr
capture. The shared one-shot serializes its complete process-owned owner
lifecycle, so concurrent direct callers cannot clean up an owner still in use.

A successful resident result must be CURRENT semantic evidence, have no gap or
stale reasons, match repository/authority HEAD and root identities, match the
canonical generation to all four immutable replica fields, and reproduce the
one-shot query receipt exactly before that receipt body is discarded. Only
allowed-path normalized hits and safe public scalar bindings survive. The audit
worker creates its own scoped generation-bound receipt. The adapter never
forwards route variables or owner credentials to Fusion, never reindexes, and
does not turn Hermes-compatible evidence into live Hermes dispatch.

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

<a id="contract-088"></a>

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

<a id="contract-089"></a>

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

<a id="contract-090"></a>

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

<a id="contract-091"></a>

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

<a id="contract-092"></a>

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
`http_error`/`malformed_response`). SERVER_TOOL / LOCAL_FALLBACK remain blocked. The existing `requests`
transport disables redirects; non-200 responses are rejected before reading JSON. No new dependency.

**Manual live smoke (NOT CI; requires explicit 012 opt-in):**
```
FUSION_ALIAS_LIVE_ENABLED=1 OPENROUTER_API_KEY=<real-key> \
  python -m modules.communication.moltbot_bridge.src.fusion_alias_live --authorize-012
```
Without `--authorize-012` it refuses. With the valve OFF it prints `valve_closed` and makes no call.

<a id="contract-093"></a>

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

<a id="contract-094"></a>

### WebhookReceiver

```python
from modules.communication.moltbot_bridge.src.webhook_receiver import app

# FastAPI app exposing:
# POST /webhook/openclaw - Receives messages from OpenClaw Gateway
# POST /webhook/moltbot - Legacy endpoint (compat)
# GET /health - Health check endpoint
```

<a id="contract-095"></a>

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

<a id="contract-096"></a>

### Response Format (Outbound to OpenClaw)

```python
class FoundupsResponse(BaseModel):
    text: str                       # Response text
    deliver: bool = True            # Whether OpenClaw should deliver response
    channel: str | None = None      # Override delivery channel
    to: str | None = None           # Override recipient
```

<a id="contract-097"></a>

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
- `execute_linkedin_action(action="digital_twin", ...)` forwards all above params to `LinkedInActions.run_digital_twin_flow(...)`. Direct `like_post`/`like_reply` truthy dry-run now returns a target preview before browser import/construction; see [exact fields and limits](../../../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-dry-run-repair--2026-09-22). Session truthy dry-run also returns configuration before browser access ([fields and limits](../../../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-session-preview--2026-09-22)). Agentic delegation and omitted/false live behavior are preserved; other routes remain separately qualified.

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


[Return to the interface directory](../../INTERFACE.md).
