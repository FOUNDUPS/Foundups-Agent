**Bridge interface: Repository And Conversation.**

[Interface directory](../../INTERFACE.md). Qualification boundaries below remain as recorded.

<a id="contract-069"></a>

## HoloIndex runtime interface

`run_holoindex_postmerge_runtime_once(...)` owns one clean exact-main maintenance lifecycle;
`query_holoindex_owner(...)` and `GenerationBoundHoloIndexQueryAdapter.query(...)` own reads.
The controller and JSON CLI accept optional `resume_incident_id`; results add
`incident_id` after accepted admission. The pointer selects an existing durable
incident, and `resume_holoindex_incident_repair(...)` revalidates its task/request
and current HEAD/root before existing bounded retry. Generic stale-index errors
do not authorize recovery. Resumed retry-wait returns non-success without runtime
startup. The existing [runtime contract](../../docs/HOLOINDEX_RUNTIME.md#post-merge-controller)
defines states, evidence, limits and source-change behavior.
Success requires exact task/completion, HEAD/root/generation, replica, ranker, runtime, CURRENT,
and no-reindex evidence. A canonical-store lease contains owned runtime start/stop and cleanup.
Holo-only launch receives the exact task ID and requires same-root/mode resident acknowledgment; its sealed receipt authority digest is rechecked against AgentDB. Pre-existing bindings release exactly, while owned supervisors stay bound until stop; runtime/task drift rejects during polling;
pending/assigned phases have 60-second progress bounds; execution observation uses the canonical
7,500-second v2 integrity-bound AgentDB lease over claim ID, issued time, expiry, assignee, and
complete task context; first completion after expiry rejects in the same transaction.
Post-completion permits at most two proofs inside the 300-second/transaction bound. Only a receipt-bound exhausted transient admits proof two on a distinct result/receipt-bound port cycle; no reindex, route, Git, model, Hermes, or promotion authority is granted. Every owner requery enters `query_once` through the internal original `workspace_repo_root` and is classified against the independently captured `HoloIndexAuthoritySelection.selected_root`; the authority must not replace the workspace, and query payloads cannot select either root. The separate pre-owner `REPO_HEAD_MISMATCH` has zero attempts and no receipt; `coordinate_holoindex_incident_repair(...)` admits it only after exact authority/no-effect binding and an independent match of stale HEAD/generation/freshness/reasons, then creates/reconciles only `holoindex_postmerge_refresh:<HEAD>`. Shared owner classification remains receipt-bound.

The current environment exact-closure flag is false; an already-started external authority
transaction has no cancellation/route-effect lease guard, so A-grade and retrieval RSI remain
rejected. Detailed schemas, lifecycle, budgets, failure reasons, and scale boundaries are in
[docs/HOLOINDEX_RUNTIME.md](../../docs/HOLOINDEX_RUNTIME.md).

<a id="contract-070"></a>

## Receipt-bound artifact generation models

`ArchitectProposalExecutabilityReceipt.bounded_worker_plan` is optional in v3.
Omission preserves the 60-field legacy wire; `{}` adds a distinct 61st field.
`ArchitectDeterminationReceipt.to_dict()` uses canonical child serializers for result
and persistence; absent plans stay omitted. Null, unknown fields, invalid typed/ASCII
data and changed receipt digests reject; no stored-wire migration is performed.
Proposal snapshots precede callbacks. Declared operation/domain/tests, paths/artifacts
and recognized packet `I` mirrors are checked without inferring mirrors or `S`/`A`/`T`
prose authority. Conservative lexical checks reject uncertain wildcard/deny overlap,
case aliases, trailing dots/spaces and controls; filesystem/use-time guards remain.

`snapshot_seed_worker_plan` now lives in the existing profile rehydration owner and
is re-exported under its unchanged seed-supplier import name. Closed profile readers
admit the plan only at the root and the two declared proposal receipt locations,
including `operational_context_binding.proposal_admission`. Non-plain ancestors reject
before reconstruction. Existing M2M codec bounds are unchanged. Whole-plan completeness,
current authenticity/admission and startup forwarding remain separate requirements;
direct profile agreement is checked by the preparation contract below; no provider, signer, worker or promotion authority is added.

`prepare_architect_fix_promotion_inputs(determination, profile)` lives in the
existing promotion profile owner and returns detached raw/wrapped input, a typed
source profile and rejection reasons. Public promotion calls it before store.load;
bootstrap calls it after artifact reads and before runtime capability verification,
output probing, locks, store construction or publication recovery. One nonempty
plain-dict receipt wrapper is selected; ordinary empty/None fallback is retained.
Absence is detached too, preventing a callback from introducing a new plan.

A declared proposal plan requires explicit canonical root-plan equality, existing
receipt/candidate lineage and declared effective profile scope. Failure uses
`REJECT_ARCHITECT_FIX_PROMOTION_AUTHORITY_PROFILE_INCOMPLETE:proposal_plan_binding`;
generic profile diagnostics retain their existing codes. Legacy receipts without
a plan still permit a separately supplied plan. Current authenticity, revision,
HEAD/Holo, model and worker authority remain downstream. Direct calls to internal
post-verification transaction/projection helpers are outside this ingress contract.

`run_reddog_authority_profile_seed_supply(...)` retains `bounded_worker_plan=None`.
Its bootstrap distinguishes an omitted argument: select only a declared plan from
the single raw determination read and freeze that determination before later reads.
Explicit `None`/`{}` remain explicit; legacy absence retains identical seed bytes.
`snapshot_seed_worker_plan` detaches explicit typed/ASCII input before receipt reads; invalid
explicit input returns `authority_seed_bounded_worker_plan_invalid`. Selected plans
reuse proposal/determination/candidate validation; malformed/null or tampered lineage
returns `authority_seed_proposal_plan_invalid`. Wrappers are not unwrapped.
`snapshot_architect_fix_plan_lineage` and the pure lineage comparator live in the
existing candidate gate; current work-state/HEAD/Holo and authenticity checks remain
in promotion. Reused `worker_plan_matches_execution_scope` lives in typed rehydration
and remains importable from the proposal contract. It checks operation/domain tests,
requested paths/artifacts, and explicit `I` mirrors of requested_operation, allowed_paths,
denied_paths, required_tests and required_policy_gates against effective seed values.
Contradictions return `authority_seed_worker_plan_scope_invalid`; no S/A/T inference or
other packet identity mapping is added. Rejection preserves existing output. Seed
digest coverage and nonce derivation remain unchanged; the lower supplier still requires explicit plan agreement.
No scope inference, parser, env option or main.py read is added. Generation checks the complete signed `work_order_digest`; mismatch
returns `FAIL_ARTIFACT_GENERATION_WORK_ORDER_BINDING` before model admission.
Explicit `m2m_envelope` becomes detached canonical JSON before one-use authority
consumption. `FAIL_ARTIFACT_GENERATION_M2M_ENVELOPE` burns only the matching handle.
Absent input preserves legacy bytes; prompt/context share the 24,000-character cap.
`validate_provider_m2m_prompt` takes optional fourth raw `context`, required with
all three canonical binding fields; changed/partial input returns `FAIL_ARTIFACT_GENERATION_M2M_PROMPT_BINDING` before effects.
Legitimate context redaction and all-absent legacy behavior remain. Gateway, inventory,
authority and output rules remain; provenance/native-child/live admission/retained learning are unqualified.

<a id="contract-071"></a>

## RedDog advisory bridge support

`reddog_advisory_bridge_support.py` owns only deterministic, bounded input
normalization, audit telemetry projection, prompt assembly, and review-packet
formatting for `scripts/advisory_model_once.py`. Provider calls, environment
access, redaction admission, and stdin/stdout lifecycle remain in the one-shot
script. The extraction adds no model, worker, repository, or fallback authority.

<a id="contract-072"></a>

## RedDog architect FIX promotion HoloIndex proof

`run_reddog_main_architect_fix_promotion_bootstrap(..., environment=...)` snapshots
the supplied host environment and resolves the explicit
`REDDOG_HOLOINDEX_QUERY_ROUTE_FILE` against the freshness receipt's canonical SSD root and exact route binding. The legacy direct replica-root variable is valid
only when the route-file value is absent; both together fail closed. The
bounded promotion execution adapter passes that sealed capability to
`verify_reddog_holoindex_owner_binding`; resolution failure returns `holoindex_query_replica_route_not_current` before owner verification or
publication. Input preparation, locked execution, and the public startup adapter
are separate modules capped at 500 lines and 50 lines per function. The
bootstrap does not materialize or re-index.

<a id="contract-073"></a>

## Governed repository-state intake

`observe_repo_state(repo_root, governed_receipt)` accepts only
`reddog_governed_git_repo_state.v2`. It validates the exact root digest, HEAD,
sorted normalized dirty paths, state digests, readiness v2, and digest-only
`reddog_governed_git_executable.v1` public receipt. The executable validator
rejects unknown/missing keys, bool-as-int values, invalid digest/size/link
bounds, partial or unequal portable/native identities, and platform signature
shape drift. Windows additionally requires signer/thumbprint digests and a
separately identity/hash-bound fixed-SystemRoot verifier containment proof;
non-Windows accepts exactly `status: not_applicable`. No raw absolute executable
path is accepted or returned. The unkeyed receipt digest is necessary but not
an independent origin authenticator; Git DLL/helper closure is outside scope.

<a id="contract-074"></a>

## Exact-Git grant-authority effect admission

`create_grant_runtime_atomic_provisioning_context()` fixes the exact-Git profile,
loads owner-config-v4 policy internally, and requires config v2. The existing
provisioner derives three-artifact leases, activation and recovery from the v3
manifest; its final transactional guard can roll back. Manifest production
signs repository, commit, object-format, source-policy and source-descriptor
bindings. No production bootstrap calls this foundation or gains work authority.

`authorize_current_grant_authority_wsp71_use()` is the final effect boundary.
It requires signed E0 policy v7, re-reads the current v3 manifest and all three
grant artifacts, revalidates the exact Git objects and signed provenance under
the current-generation lease, and only then invokes one callback under the
durable revocation fence. V6/v2 may be inspected through the hash-only binding
API but cannot authorize an effect.

<a id="contract-075"></a>

## Principal Memex live resident source
`lease_current_generation_conversation_session()` can atomically split one
authenticated session capability into FoundUp-use and Principal-read children.
The Principal child authorizes only one pre-issued
`reddog_principal_memex_disclosure.v2` admission. The live supplier binds the
current principal record, conversation revision, disclosure nonce, runtime
generation, model binding, grounding receipt, exact cycle, expiry, revocation,
and durable replay state before exposing the signed accepted-decision subset
to the final backend architect call.
Principal Memex-informed model output is decoded in serialized field order,
NFKC-normalized, and token-counted across all fields. It rejects complete
statement-token reproduction regardless of field order, plus residual
non-ASCII or control characters that could disguise reproduction.
Raw and aggregate decoded output are bounded before admission, and JSON field
names are inspected with values so unknown-key disclosure cannot bypass it.
The disclosure never enters resident intent, audit-worker context, AgentDB,
logs, status, or receipts. Memex-informed durable determinations persist only
a report-bound action/slice, fixed advisory metadata, and opaque digests; no
model-authored free text, proposal body, or queue candidate survives. This
interface grants no work, repository, signer, merge, FoundUp projection, or
HoloIndex authority. Disclosure issuance remains outside this module.
<a id="contract-076"></a>

## Exact-request signer admission
`run_reddog_signer_socket_service_runtime_wiring(..., secret_grant_admission=...)`
opts one existing owner-selected target into resolve-per-sign composition.
`SignerSocketServiceGrantAdmission` contains the owner path/policy, durable
replay store and registered root protected-use oracle; this data is not authority.
The existing current-generation admission reconstructs the complete selected
configuration. Owner, oracle and replay-store provenance must match before
serving; proposal, conversation and verified-outcome profiles are outside this
single-target mode. Omitting the argument preserves the existing runtime path.

The resolve-per-sign backend requires the exact owner-bound
`Wsp71EphemeralSignerBackendFactory`; a callable factory or lease-shaped hook
does not confer admission. Its current lease must derive the same binding as the
consuming backend, and the consuming grant boundary must use the admission's
exact replay store and root revocation oracle. Ownerless factories and substituted
boundaries reject before key resolution. Security-critical lease/protected-use
calls use the checked class implementations rather than instance-shadowed methods.
This deliberately tightens the generic constructor contract; synthetic unit
fixtures do not qualify the public admission path.

The assembly lease ends before serving. Each request consumes its verified grant,
obtains root ACQUIRE, then obtains a fresh generation lease for key resolution,
exact-request signing and signature verification. The generation lease ends
before root FINISH. Holding it across a root exchange would deadlock against the
root service's generation lock. Generation drift rejects before key resolution;
expiry after resolution rejects before signing. Python backend references are
released within the callback lease; this is not native-memory zeroization.
FINISH failure rejects the result and leaves cleanup unconfirmed. A bounded
service receipt alone does not mean a signing request succeeded.

The public system-service entrypoint does not yet supply this opt-in admission.
This interface neither establishes first trust nor activates an unattended agent.

Descriptor `foundup_verified_outcome_root_authority.v2` adds exactly
`root_control_authentication = {purpose, public_key, key_epoch}`. Purpose is
`protected-use-acquire-finish.v1`; epoch is nonblank ASCII, at most128 characters;
all three values are exact strings. The decoded Ed25519 control key must differ
from the work key. The binding participates in both descriptor identity and
co-signed authority context: v1 grants cannot be transferred to v2. Missing,
unknown or mixed fields reject; v2 never falls back to work-key control proof.
Only protected-use ACQUIRE/FINISH uses this identity. Other root operations and
v1 preserve their existing proofs. Descriptor lifetime/current-owner checks and
FINISH failure semantics remain in force. The injected request-signer callback
is a source-composition dependency, not a qualified custody/provider capability.
A distinct authentic control credential and public startup composition remain
prerequisites to native activation.

`load_system_service_root_protected_use_authority()` derives an opaque client from the existing root owner configuration and Unix transport. Only that exact factory-issued capability may compose the durable revocation oracle.
Root ACQUIRE must precede the callback and exact FINISH must succeed before its result is returned; durable per-use replay markers and the global active-use high-water remain in the existing mirrored root state.
No caller can construct, copy, pickle, or substitute the capability.
`Ed25519SignerBackend` rejects policy-less delegated signing. The
resolve-per-sign E0 boundary consumes the independently authenticated grant,
then immutably binds the ephemeral backend to that grant's exact request
digest. Altered operation, prefix, payload, nonce, peer, tier, or key binding
cannot reuse the backend. Specialized proposal, control-loop, manifest,
verified-outcome, conversation, and peer-handshake policies retain their own
domain-specific validation.
<a id="contract-077"></a>

## Authenticated RedDog conversation scope

`authenticate_conversation_scope()`, create/resume/advance, the existing-scope binder, durable request journal, and `reserve_current_generation_resident_conversation_request(...)` form the authenticated AgentDB existing-conversation path.
It consumes opaque authority, verifies current record/revision/turn lineage, and returns content-free evidence without reserving conversation CAS or granting effects.

`resolve_resident_conversation_new_scope_request(...)` plus `create_current_generation_resident_conversation_scope(...)` form the separate empty-ID TURN path. Exact v2 intent/request/grounding/FoundUp bindings precede the current-generation E0 lease; signed session identity fences nonce divergence and exact authenticated recovery is the only replay accepted.

`resolve_current_generation_resident_conversation_first_turn(...)` atomically obtains two one-use FoundUp authority siblings, creates/exactly recovers scope-schema-v4 E0 with an immutable signed source/resolved request commitment, and stores explicit v2 `RESOLVED_INITIAL_TURN` digests in the existing journal; replay derives the ID before exact four-key lookup, atomically consumes its verified authority, and validates the retained E0 receipt through the current signed revision chain.
`authenticate_signed_conversation_scope()` remains the production credential source; legacy HMAC is test/backward-compatible only. `prepare_conversation_work_context()` and proposal promotion remain later, independently authorized stages.
These aggregates expose no traffic, handler, CAS, model/worker, or work authority; see `docs/clarity/REDDOG_RESIDENT_CONVERSATION_*_PHASE1.md`, including `REDDOG_RESIDENT_CONVERSATION_FIRST_TURN_RESOLUTION_PHASE1.md`, for exact locking, expiry, failure, and recovery contracts.


[Return to the interface directory](../../INTERFACE.md).
