# Tests - OpenClaw Bridge

## Exact-main post-merge lifecycle

`test_reddog_holoindex_owner_query_root_binding.py` proves all post-completion,
incident-recheck, CURRENT-coordination, and blocked-recovery queries enter through
the original workspace/control root while results remain classified against the
independently captured authority. The authority selector separately proves a
configured authority equal to the workspace is rejected. The focused root and
affected lifecycle selection is 190 passed. Merged exact-main `da558d51` passed
the repaired controller on its first real OpenClaw transaction; a fresh owner
query and full 33-artifact post-query verification retained the exact binding.
That live result is commit-bound and does not prove runtime closure or A-grade.

`test_holoindex_postmerge_runtime_owner_proof.py` owns the distinct
post-completion readiness contract. It proves one fully receipt-bound exhausted
transient can receive exactly one immediate reproof on acquisition cycles zero
then one, both queries share the remaining transaction/300-second budget, and
two transients remain terminal. Cycle telemetry must match its sealed receipt.
Rejected authority, stale/deterministic/malformed/forged results, wrong
completion generation or freshness digest, zero/consumed budgets, and
`KeyboardInterrupt`/`SystemExit` all reject without weakening owned-runtime
cleanup. It also pins the controller below the communication WSP_62 ceiling.

`test_holoindex_postmerge_runtime_admission.py` proves missing dispatch-chain
imports reject before coordination, exact-task registration waits only for live
readiness, short admission bounds reject stalls, and a healthy 2,400-second
execution remains inside the canonical 7,500-second v2 integrity-bound lease.
`test_holoindex_postmerge_runtime_liveness.py` separately falsifies broker
death, terminal/retry task state, request/authority/claim drift, wrong assignee,
expired claims, and invalid completed state. Database claim regressions bind ID,
issued time, expiry, assignment time, and digest; reject late first completion;
and preserve exact post-expiry replay. Three claim-clock contention falsifiers
raise the affected Python surface to 309 passed.

`test_holoindex_postmerge_runtime_controller.py` proves dirty/non-main
admission closes before query effects, an already-CURRENT owner starts no
runtime, transaction-owned OpenClaw runtimes start and stop in dependency order,
pre-existing broker runtimes remain resident, direct register-only bootstrap
touches no ambient autostart flags, the exact task ID reaches Holo-only launch,
exact completion generation equals the final owner receipt, and a
still-live owned thread turns apparent success into rejection.

The same file proves the canonical-store controller lease rejects contention,
both lost-start races reject without claiming foreign ownership, every accepted
OWNER_READY path repeats the exact-main Git proof, and final-Git interrupts
become fixed rejections after cleanup. Owned supervisors receive the explicit
`holoindex_postmerge_only` mode; supervisor coverage proves hostile ambient
flags cannot activate self-audit or any non-Holo task family.
Bound-poller tests prove exact bind/release/rebind identity and no independent
coordinator scheduling. Controller cases prove pre-existing release and owned
binding retention through stop. Launch tests prove same-root/Holo-only
attestation and fail-closed full dependency preflight.
Direct execute-gate cases additionally prove forged and structurally malformed
plans cannot bypass the Holo-only triage boundary or escape its fixed rejection.
Those focused cases live in
`test_openclaw_supervisor_holoindex_postmerge.py`; the inherited supervisor
test host remains below its base line count instead of ratcheting WSP 62 debt.

The launch/supervisor regressions independently prove register-only bootstrap
directly registers exactly two OpenClaw specs, starts nothing, and leaves
hostile ambient autostart flags unchanged. A generic completed task row remains
insufficient, malformed exact-head bindings reject, and a canonical atomic
completion receipt succeeds.
`test_openclaw_maintenance_selector.py` also proves this self-hosting task family
does not recursively build a Holo execution bundle before it can be claimed.

## Resident governed Holo usability

`test_reddog_generation_bound_holoindex_query_adapter.py` proves the resident
adapter preserves the owner-loaded runtime ranker digest in its safe result and
receipt. Owner client tests reject missing or malformed ranker attestations.
adapter admits a separate committed same-HEAD authority for both clean and
overlaid callers, while a workspace authority with an overlay and unknown
authority labels still fail closed. It also proves the child reuses the owner
supervisor's runtime/site-packages, scrubs ambient secrets before `-S -B`, and retains the 60-second parent,
57-second operation, and three-second cleanup bounds. The focused suite is 25
passed; the expanded adapter/worker/one-shot/supervisor matrix is 428 passed / 1 skipped. The
historical commit-bound canary at
`61c2c3003bc4c2086f105f4c39effd499a026627` returned CURRENT with two scoped
hits and no reindex in 32.5 seconds; it did not mutate Holo or the repository
and does not authorize the candidate or any later commit.
The candidate's earlier 60-second cold one-shot timed out twice. A later
base-bound governed query passed on attempt one inside the 300-second CLI wall;
this proves base usability, not exact-current-main readiness or scale.

## Main bootstrap WSP 62 extraction

The existing authority exact-schema suite now covers list, tuple, empty, and
invalid mapping-list rehydration with exact nested rejection order. The
existing bootstrap and durable-authentication WSP 62 suites prove the extracted
result module stays bounded, the original public symbols retain exact identity,
cold imports work in either order, and the remaining 432-line orchestration
entrypoint cannot grow. No parallel test file or runtime authority was added.

## FoundUp Memex learning-candidate gate

`test_foundup_memex_learning_candidate.py` proves deterministic read-only
candidate projection from exact FoundUp/snapshot/source receipts. Its positive
and adversarial cases cover contradiction preservation, supersession pointers,
proposed salience/confidence, reconstruction fidelity, forged and cross-FoundUp
receipts, governed-research fail-closed behavior, verified-outcome HEAD binding,
ambiguous outcome-receipt rejection, proposal-bound local-resigning rejection,
canonical Unicode/time/score output, immutable result receipts, pre-dedup
collection bounds, exact view receipt/invariant enforcement,
tampering, secret text, invalid/overflowing scores, extreme timestamps, nested
callback-bearing values, future evidence/proposals, hostile runtime types, and
nested source/view callbacks, safe fallback attribute access, exact evidence
closure, oversized/cumulative nested keys and values, storage/network/model
import prohibitions.

```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_foundup_memex_learning_candidate.py -q
```

## Resident conversation admission and request idempotency

`test_reddog_resident_conversation_new_scope_admission.py` proves the separate
trusted empty-ID TURN aggregate: exact v2 intent/request/grounding/FoundUp
binding before credential use, required E0 signer context, generation-lease
lifetime, one-use authority consumption, content-minimized scope persistence,
authenticated exact replay, divergent nonce conflict, expiry, concurrency, and
stable failure projection. Production-shaped signed-session cases deliberately
change the intent-derived session binding and prove one stable signed session
cannot split one nonce into multiple scopes. The aggregate neither journals nor
executes the first turn and contains no handler/model/worker/CAS effect wiring.

`test_reddog_resident_conversation_first_turn_resolution.py` owns the distinct
durable-link aggregate. It proves explicit v2/source-vs-derived request digest
semantics, two separately registered FoundUp authority siblings, content-free
storage, exact restart and scope-only crash recovery, related-key and nonce
divergence rejection, concurrent convergence, authenticated replay through a
later signed scope revision, signed immutable E0 request-identity commitment,
full-row journal rewrite rejection, atomic same-authority replay consumption,
and WSP 62/effect ceilings. It does not test handler execution or conversation
CAS.

`test_reddog_resident_conversation_scope_binding.py` uses the existing
temporary SQLite AgentDB fixture and opaque conversation capabilities. It
proves existing TURN/STATUS/CANCEL admission, content-free output, zero
mutation, one-use consumption, exact revision/turn checks, expiry, missing
state, current principal-signed E0 scope, forged/cross-session/cross-principal
authority, attacker-rehashed record tampering, dependency failure, and WSP 62
file/function limits.

`test_reddog_resident_conversation_request_journal.py` proves the admission
service: atomic live-parent consumption and opaque proof issuance, constructed-binding
and unregistered-parent forgery rejection,
content-free reservation, restart-safe exact replay, divergent/concurrent
collision rejection, scope-expiry/change fencing, TURN/STATUS/CANCEL behavior,
malformed store closure, and WSP 62 limits. The companion
`test_reddog_resident_conversation_request_journal_store.py` proves unified
mapping rows, portable PostgreSQL row locks/UPSERT SQL, SQLite serialization,
global/per-conversation capacity, store-owned-clock expiry/backdating, direct
store admission rejection, and JSON/digest/all-index-column corruption.
The production-shaped fixture also exposed and now guards prior positional-row
drift in signed pending conversation scope. No test executes a handler or
reserves conversation CAS.

`test_reddog_resident_conversation_admission.py` proves the current-session
aggregate holds the signed-session lease across binding and reservation,
passes the exact authority-source inputs without exposing them in results or
storage, and consumes the verified parent. It covers restart replay, pre-lease
malformed/new-scope rejection, stable and unexpected source failures,
directly allocated opaque authority, cross-session mismatch, journal failure,
direct E0 session transplant, hostile record mapping, and WSP 62/effect-wiring
boundaries. The authority source is replaced only by
a controlled context-manager fixture; its independent production suite owns
generation/config/socket/signature verification.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_resident_conversation_scope_binding.py modules/communication/moltbot_bridge/tests/test_reddog_resident_conversation_request_journal.py modules/communication/moltbot_bridge/tests/test_reddog_resident_conversation_request_journal_store.py modules/communication/moltbot_bridge/tests/test_reddog_resident_conversation_admission.py -q
```

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_resident_conversation_new_scope_admission.py -q --basetemp O:\reddog-test-runtime\pytest-new-scope
```

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_resident_conversation_first_turn_resolution.py -q --basetemp O:\reddog-test-runtime\pytest-first-turn
```

## HoloIndex owner replica response contracts

`test_reddog_holoindex_owner_client_transport.py` proves a successful owner
response retains all four exact replica fields and fails closed when any field
is missing. `scripts/tests/test_reddog_holoindex_owner_query_once.py` proves a
valid-but-different returned replica cannot be bound to the verified route.
`test_reddog_generation_bound_holoindex_query_adapter.py` additionally proves
the resident default uses the one-shot contract, filters before limiting,
removes raw/semantic/nested receipt bodies and arbitrary fields, rejects every
split binding, serializes concurrent lifecycles, bounds lock wait, rejects
hostile timeouts, and enforces the production child-process wall. The one-shot
suite independently proves its shared lifecycle lock and strict CLI deadline.
The canonical worker matrix also preserves the legacy direct/query/transport
adapter export so existing diagnostic callers remain import-compatible while
fresh resident workers use the generation-bound default.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_holoindex_owner_client_transport.py modules/communication/moltbot_bridge/tests/test_reddog_holoindex_direct_query_boundary.py modules/communication/moltbot_bridge/tests/test_reddog_holoindex_receipt_binding.py modules/communication/moltbot_bridge/tests/test_reddog_holoindex_query_boundary.py -q
```

## WSP 62 decomposition coverage

`test_reddog_runtime_module_static_boundaries.py` preserves the resident-loop
and signed-worker executor effect/import prohibitions extracted from the large
integration matrices. `test_reddog_wsp62_security_repair_exemptions.py` also
caps the architect promotion and queue-loop decomposition modules at 500 file
lines and 50 lines per function, without a new exemption.

## Verified model-topology consumers

The model runtime query, bounded runtime, authority, provider bootstrap,
OpenClaw, Hermes, and resident integration matrices prove exact
role/provider/model preservation with explicit availability. Negative coverage
includes stale evidence, missing/unavailable providers, replay, retargeting,
payload mismatch, and wrong provider; each path asserts zero network/process
egress where applicable.

## Current upstream worker providers

`test_reddog_hermes_api_artifact_provider.py` proves Hermes API `0.20.4`
accepts only one stable completed native leaf, paired delegate-only telemetry,
explicit zero child file reads/writes, ordered final completion, zero skills,
and unchanged pre/postflight policy.
`test_reddog_openclaw_gateway_artifact_provider.py` proves OpenClaw
`2026.7.1-2` service/plugin identity, WSL cold-start-safe RPC ordering, exact
sandbox policy, signed provider-prefixed routing, and bounded non-empty artifact
output on canonical relative paths.

```powershell
python -m pytest -q `
  modules/communication/moltbot_bridge/tests/test_reddog_hermes_api_artifact_provider.py `
  modules/communication/moltbot_bridge/tests/test_reddog_openclaw_gateway_artifact_provider.py
```

## Governed repository-state v2 intake

`test_reddog_operational_context_snapshot.py` covers the digest-only executable
v1 receipt accepted from JavaScript, exact readiness/repository schemas, and
rejection of incomplete identities, malformed or boolean numeric fields,
signature/verifier containment drift, raw paths, and non-Windows shape drift.
The production snapshot module remains free of `subprocess` and bare Git.

## Grant-profile atomic runtime provisioning

```powershell
python -m pytest -q `
  modules/communication/moltbot_bridge/tests/test_reddog_grant_runtime_atomic_provisioning.py `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_runtime_atomic_provisioning.py `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_runtime_atomic_provisioning_recovery.py `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_runtime_atomic_provisioning_wsp62.py
```

The matrix proves the existing atomic provisioner can admit exactly one
source-policy-capability-bound grant profile, activate only its three artifacts,
bind config/run-packet bytes into durable generation state, reject config-v1
downgrade and alternate committed source maps, detect owner replacement during
commit, and serialize compliant rotation. It starts no service and grants no
secret, worker, repository, PR, or merge authority.

## Root-owned grant-service source-policy authority

```powershell
python -m pytest -q `
  modules/communication/moltbot_bridge/tests/test_reddog_grant_authority_source_policy_authority.py `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_independent_grant_authority_client_supply.py
```

The matrix proves exact owner-config v4 source-map binding, cross-repository
and stale-policy rejection, opaque capability confinement, and continued v3/v4
grant-client support. It performs no archive build, service launch, secret
resolution, repository effect, or HoloIndex mutation.

## Grant-authority executable archive validation

```powershell
python -m pytest -q `
  modules/communication/moltbot_bridge/tests/test_reddog_grant_authority_service_archive_validation.py `
  modules/communication/moltbot_bridge/tests/test_reddog_grant_authority_service_authenticated_manifest_binding.py
```

The matrix proves deterministic archive bytes, production and use-time
validation, exact member/manifest binding, direct static-import reference
checks, common loader-alias rejection, standard-library shadow rejection,
beyond-top-level relative-import and control-path rejection, and the fixed
non-generator callable entrypoint ABI. It does not prove Git provenance, interpreter
identity, Python sandboxing, hermetic process isolation, service lifecycle, secret resolution, or
live authority.

## Grant-authority WSP 71 permission rehydration

```powershell
python -m pytest -q `
  modules/communication/moltbot_bridge/tests/test_reddog_grant_authority_wsp71_permission_rehydration.py `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_secret_grant_revocation_durable_authority.py `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_root_protected_use_composition.py
```

The matrix proves root-generation binding, canonical receipt rehydration,
real config/manifest verification, same-lease callback use under the matching
durable revocation fence, role-separated generation authority, and rejection
of self-rehash, wrong-policy oracle use, repository-permission substitution,
path/symlink replacement, duplicate keys, trailing bytes, canonical-prefix
tails, non-ASCII and oversized input. It performs no secret resolution, service
startup, socket connection, or worker effect.

## Authenticated grant-service manifest binding

```powershell
python -m pytest -q `
  modules/communication/moltbot_bridge/tests/test_reddog_grant_authority_service_authenticated_manifest_binding.py `
  modules/communication/moltbot_bridge/tests/test_reddog_signed_runtime_artifact_manifest.py `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_owner_controlled_e0_admission.py `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_owner_e0_static_contract.py
```

The matrix proves v1/v5 compatibility, v2/v6 grant-service binding, central
signer-domain admission, exact config/run-packet schemas, all-artifact use-time
rehydration, archive-tail replacement rejection, pairwise key-reference
separation, signed-policy substitution rejection, and secret-free output. It
does not start a grant service, resolve WSP 71 values,
dispatch a worker, or grant repository authority.

## Independent grant-authority client supply

```powershell
python -m pytest -q `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_independent_grant_authority_client_supply.py `
  modules/communication/moltbot_bridge/tests/test_reddog_isolated_signer_socket_client.py `
  modules/communication/moltbot_bridge/tests/test_reddog_isolated_signer_socket_client_linux.py `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_system_service_manifest_selection_loader.py
```

The matrix proves authenticated current-generation policy admission, exact
owner-config binding, disjoint signer/outcome/replay/revocation roots, socket
link rejection and inode pinning, protected ancestry, Linux connected-peer
UID/GID, attacker-rehashed policy rejection, and no request during client
construction. It does not start a grant service, resolve a secret, compose a
signer, or grant work.

## Signer system-service WSP 71 resolver

```powershell
python -m pytest -q `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_system_service_wsp71_resolver_supply.py `
  modules/communication/moltbot_bridge/tests/test_reddog_signer_system_service_entrypoint.py `
  modules/infrastructure/secrets_mcp/tests/test_op_cli_secret_resolver.py
```

The matrix proves owner-ID binding, fixed executable policy, fail-closed
unsafe/missing executable handling, in-memory secret use, and no shell or
secret persistence. The supply remains uncomposed and claims no grant issuance,
service deployment, or live worker authority.

## Canonical elevated-authority consensus capability

```powershell
python -m pytest `
  modules/communication/moltbot_bridge/tests/test_reddog_elevated_authority_consensus_capability.py `
  modules/communication/moltbot_bridge/tests/test_reddog_elevated_authority_consensus_verification.py `
  modules/communication/moltbot_bridge/tests/test_reddog_elevated_authority_consensus_signer.py `
  modules/communication/moltbot_bridge/tests/test_reddog_elevated_authority_consensus_structure.py -q
```

The matrix proves exact two-child capability use, strict proof rehydration,
reviewer/key/model/runtime independence, current policy and sovereign binding,
signer-side full-grant verification, replay and concurrent admission closure,
and bounded production/test modules and functions without shell, network, or
crypto-key generation.
It does not claim authenticated production authority supply or signer-service
composition.

## Independent signer secret-grant provider

`python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_signer_independent_secret_grant_provider.py -q`

The matrix covers canonical signing, durable concurrent rate limits, distinct
caller and beneficiary identities, generation lease lifetime, authority and
replay-store substitution, signed grant-authority key-epoch substitution,
exact owner-policy schema, audit-attestation tampering, elevated-tier closure
and WSP 62 boundaries.

## Root-served signer revocation

```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_foundup_verified_outcome_root_revocation_service.py modules/communication/moltbot_bridge/tests/test_foundup_verified_outcome_root_revocation_hardening.py modules/communication/moltbot_bridge/tests/test_reddog_signer_secret_grant_revocation_durable_authority.py -q
```

The matrix integrates current signed E0 policy admission, signed revocation
snapshots, durable primary/witness state, root high-water state, opaque client
transport and kernel-peer/root-service validation. It rejects arbitrary
bindings, policy drift, forged/cross-operation proofs, wrong peers, stale time,
missing witnesses, tampered snapshots, stale replay, response substitution and
fabricated capabilities. It proves exact retry and concurrent convergence and
enforces WSP 62 without an exemption. It does not activate protected signing.

## External authoritative-use lease

```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_external_signer_authoritative_use_lease.py modules/communication/moltbot_bridge/tests/test_reddog_authoritative_use_lease_contract_security.py modules/communication/moltbot_bridge/tests/test_reddog_authoritative_use_lease_adversarial.py modules/communication/moltbot_bridge/tests/test_reddog_isolated_signer_socket_client.py modules/communication/moltbot_bridge/tests/test_reddog_isolated_signer_socket_protocol.py modules/communication/moltbot_bridge/tests/test_reddog_ed25519_signer_backend.py modules/communication/moltbot_bridge/tests/test_reddog_signer_secret_access_grant.py modules/communication/moltbot_bridge/tests/test_reddog_signer_resolve_per_sign_backend.py modules/communication/moltbot_bridge/tests/test_reddog_signer_mutual_peer_handshake.py modules/communication/moltbot_bridge/tests/test_reddog_external_signer_lifecycle_admission.py modules/communication/moltbot_bridge/tests/test_reddog_signer_current_generation_use_time_binding.py modules/communication/moltbot_bridge/tests/test_reddog_execution_valve_queue_use_time_binding.py modules/communication/moltbot_bridge/tests/test_reddog_extension_wre_operational_spine_invoke.py modules/communication/moltbot_bridge/tests/test_reddog_wre_operational_spine.py -q
```

This matrix validates the external-signer exact-effect primitive without
activating any repository, worker, queue, shell, PR, merge, or indexing effect.
It includes a composed socket-v2/E0/resolve-per-sign/issuer/WRE regression and
attacks for local signer substitution, split replay roots, generation overrun,
clock rollback, canonicalization, replay, and effect substitution.

## Coverage Goals
- Intent classification and routing behavior.
- WSP preflight + permission gates.
- End-to-end `process()` safety fallbacks.
- Cisco skill scanner guard behavior.
- Skill boundary policy enforcement (workspace skills vs internal `skillz`).
- SOURCE tier permission enforcement (AgentPermissionManager).
- Webhook rate limiting (token bucket per sender/channel).
- COMMAND graceful degradation (WRE unavailable fallback).

## Run
```powershell
cd o:\Foundups-Agent
.\modules\communication\moltbot_bridge\tests\run_tests.ps1
```

CI gate behavior:
- Runs security tests first and fails fast if any fail:
  - `test_skill_boundary_policy.py`
  - `test_skill_safety_guard.py`
  - `test_hardening_tranche.py`
- Use `-SkipSecurityGate` only for local diagnostics (never for CI/prod).

Optional custom args:
```powershell
.\modules\communication\moltbot_bridge\tests\run_tests.ps1 -PytestArgs @("-q", "-k", "skill_safety")
```

Focused authenticated conversation-scope runtime:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_conversation_scope_authentication.py modules/communication/moltbot_bridge/tests/test_reddog_authenticated_conversation_scope_state.py modules/communication/moltbot_bridge/tests/test_reddog_conversation_scope_tamper_and_rotation.py -q
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_conversation_session_authority_source.py modules/communication/moltbot_bridge/tests/test_reddog_resident_architect_session_bridge.py -q
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_principal_memex_live_resident_source_supply.py modules/communication/moltbot_bridge/tests/test_reddog_principal_memex_backend_architect_integration.py modules/communication/moltbot_bridge/tests/test_reddog_resident_architect_durable_agentdb_cycle.py -q
```

This suite uses a temporary SQLite AgentDB-shaped store plus current-checkout
FoundUp and grounding receipts. It covers restart recovery, one-use opaque
authentication, HMAC rotation, recomputed-hash tampering, cross-principal,
cross-session and cross-FoundUp rejection, stale grounding, expiry, CAS and
concurrent updates. It performs no provider call, dispatch, repository write,
HoloIndex reindex, signing operation, PR, or merge.

The Principal Memex matrix additionally proves that a pre-issued disclosure is
removed before resident intent persistence, uses a distinct one-use Principal
scope, is not consumed by duplicate/active/cancelled cycles, reaches only the
final architect model as the signed subset/order of bounded public decisions,
is expiry-checked immediately before invocation, and cannot grant FoundUp or
work authority.

Focused conversation-to-work promotion:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_conversation_work_promotion.py modules/communication/moltbot_bridge/tests/test_reddog_backend_architect_determination_runtime.py modules/communication/moltbot_bridge/tests/test_reddog_architect_fix_signed_wsp15_work_order_promotion.py -q
```

This matrix proves backend pre-model context binding, immutable pending proposal
CAS, one-use capability admission, principal-signature ordering, FoundUp scope,
stale-record rejection, and compatibility with the existing signed WSP 15
promotion path. It does not dispatch a worker or mutate repository content.

Focused owner-controlled signer E0 admission:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_signer_owner_controlled_e0_admission.py modules/communication/moltbot_bridge/tests/test_reddog_signer_owner_e0_static_contract.py -q
```

This suite uses only temporary runtime roots and generated public/private test
keys. It proves exact selection-tuple binding and fail-closed admission;
manifest-bound principal authority and generation-fenced consumption are also
covered. It does not resolve secrets, start a signer, bind a socket, or write
the repo.

Focused RedDog WRE operational spine:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_wre_operational_spine.py modules/communication/moltbot_bridge/tests/test_reddog_wre_worktree_create.py modules/communication/moltbot_bridge/tests/test_reddog_wre_execution_valve.py modules/communication/moltbot_bridge/tests/test_reddog_wre_executor_dryrun.py modules/communication/moltbot_bridge/tests/test_reddog_work_order_runtime_invocation.py -q
```

Focused resident live-canary harness:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_resident_live_canary.py modules/communication/moltbot_bridge/tests/test_reddog_resident_runtime_artifact_readiness.py -q
```

This suite uses injected readiness/control-loop probes, a temporary local Git
repository with a registered worktree, the atomic chain store and planner, and
a temporary PatternMemory SQLite database. The draft-PR runner remains an
injected no-network test double. One bounded Python subprocess proves
interprocess lock exclusion. It does not start a signer, call OpenRouter, push
a branch, or create a PR.

Current-policy fixtures must project the legacy serial-loop snapshot through
the canonical queue WSP_15 allocation and governed progressive-stage helpers.
Manifest authority uses one exact edit operation, selected slice, and file
path; scalar or wildcard stand-ins are not valid live-canary evidence.

Focused canonical execution-valve supplier/evaluator:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_execution_valve_environment_supply.py modules/communication/moltbot_bridge/tests/test_reddog_wre_execution_valve.py -q
```

Focused signer resolve-per-sign E0 boundary:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_signer_secret_grant_revocation_contract.py modules/communication/moltbot_bridge/tests/test_reddog_signer_secret_grant_revocation_durable_authority.py modules/communication/moltbot_bridge/tests/test_reddog_signer_secret_access_grant.py modules/communication/moltbot_bridge/tests/test_reddog_isolated_signer_socket_protocol.py modules/communication/moltbot_bridge/tests/test_reddog_signer_resolve_per_sign_backend.py modules/communication/moltbot_bridge/tests/test_reddog_signer_wsp71_ephemeral_backend_factory.py -q
```

The revocation-contract cases use only signed test fixtures. They prove exact
authority/generation/store binding and attacker-rehash rejection. The durable
authority cases use temporary disjoint SQLite roots to prove monotonic publish,
both crash recoveries, status/metadata/witness tamper rejection, expiry,
one-winner concurrency, and lock coverage across the protected callback. They
do not issue grants, activate E0, resolve secrets, start a signer, bind a socket,
mutate a repository, detect coordinated two-domain rollback, or reindex
HoloIndex.

Focused architect-FIX two-phase publication:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_architect_fix_promotion_publication.py modules/communication/moltbot_bridge/tests/test_reddog_architect_fix_signed_wsp15_work_order_promotion.py modules/communication/moltbot_bridge/tests/test_reddog_architect_proposal_verified_authority.py modules/communication/moltbot_bridge/tests/test_reddog_authoritative_work_state_refresh_runtime.py modules/communication/moltbot_bridge/tests/test_reddog_authority_profile_source_artifact_supply.py modules/communication/moltbot_bridge/tests/test_reddog_execution_valve_environment_supply.py modules/communication/moltbot_bridge/tests/test_reddog_execution_valve_runtime_artifact_locking.py modules/communication/moltbot_bridge/tests/test_reddog_signer_socket_service_config_supply.py modules/communication/moltbot_bridge/tests/test_reddog_resident_control_loop_signing_context.py modules/communication/moltbot_bridge/tests/test_reddog_main_architect_fix_promotion_bootstrap.py modules/communication/moltbot_bridge/tests/test_reddog_wsp62_security_repair_exemptions.py -q
```

The main-bootstrap selection proves the exact query-replica capability reaches
owner binding verification and that route-resolution failure occurs before
verification or publication. Fixtures that exercise later promotion authority
inject an inert route capability rather than weakening production resolution.

Cross-process resident FIX promotion claim:

```bash
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_agentdb_fix_promotion_claim.py -q
```

The claim suite includes stale-owner fencing, monotonic reclaim revisions,
promotion-receipt completion binding, supplier short-circuiting, and exact
handoff lineage. Artifact-handoff tests separately reject aliased output paths
before either artifact is written.

The publication suite proves the exact fail-closed sequence:
`PREPARED -> immutable inert artifact -> COMMITTED state -> fixed inert cache`.
Recovery never advances PREPARED and never emits signer, queue, claim, shell,
worktree, OpenClaw, or execution-valve authority.
Signer regressions also require the explicitly selected durable authoritative
work state and reject missing state, split-path substitution, marker and
queue/claim stripping, or injected state that differs from the durable payload.
