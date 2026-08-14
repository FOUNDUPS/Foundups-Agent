# Tests - OpenClaw Bridge

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
