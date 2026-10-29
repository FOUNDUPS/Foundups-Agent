# FoundUps Agent Market (FAM)

## Purpose
FoundUps Agent Market (FAM) is the outer layer for launching tokenized FoundUps and coordinating agent swarms through a task to proof to verification to payout pipeline.

### Exact quantity admission — 2026-10-29

Domain quantity constructors require built-in integers: booleans, numeric strings,
floats and integer subclasses are invalid. Positive/nonnegative minima remain.
Launch validates its optional initial task before registry, token or repository
adapter calls; an invalid reward returns the existing failed launch/audit result.
Separate compute dictionary/ORM ingress, asset units and funded caps remain
unqualified. This admission boundary does not sign or settle a chain payment.

## CABR Canonical Intent

- CABR = Consensus-Driven Autonomous Benefit Rate (also referred to as Collective Autonomous Benefit Rate).
- WHY: CABR exists to power Proof of Benefit (PoB).
- HOW: Collective 0102 consensus determines CABR (consensus-driven process).
- RESULT: PoB drives protocol allocation/distribution; ROI is a downstream financial readout.

This module is intentionally generic and chain-agnostic through Prototype, with persistence adapters behind stable contracts.

## Compute Access (Paywall) Direction

FAM is also the website execution surface for paid build compute (not an idea-submission paywall).
The access layer is defined in:

- `modules/foundups/agent_market/docs/COMPUTE_ACCESS_PAYWALL_SPEC.md`

Design intent:
- Discovery remains low-friction.
- Execution actions are metered.
- CABR keeps PoB quality-gated.
- pAVS receives policy-defined treasury flows from metered usage.
- Current status: P0 in-memory + persistence compute gates implemented; persistent registry/task pipeline wiring is active.

## Scope in This PoC
- Foundup registry with immutable vs mutable metadata rules.
- Token factory adapter interface (no chain lock-in).
- Agent join requests and capability tagging.
- In-memory task lifecycle simulation: `open -> claimed -> submitted -> verified -> paid`. Persistent SQLite initiation leaves a task `verified` with a pending payout; it does not confirm payment.
- Treasury and governance boundaries as interfaces.
- CABR integration hooks as interfaces.
- Event audit trail linking payout to proof to task to foundup.
- Verified milestone distribution contract with idempotent publish semantics.
- F_0 investor program for MVP pre-launch bidding (200 UPS/term, max 5-term hoard).
- In-memory adapter for deterministic tests.
- SQLite persistence adapter with schema migrations and query indexes.
- Postgres adapter boundary and backend factory selection.

### Persistent initiation boundary

SQLite `trigger_payout` records payout, task linkage, configured compute charge and event atomically. An exact retry returns the same pending result, including after reopen, without duplicate effects. Ambiguous legacy records are held for reconciliation; no automatic refund, deletion or settlement occurs. Non-SQLite initiation is unsupported. Persistent role authentication and live rewards remain unproved; see [the interface](INTERFACE.md#taskpipelineservice) and [R24 contract](../../../docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md#persistent-reward-initiation-contract--2026-09-22).

## Out of Scope in This PoC
- Production blockchain writes.
- Production DAO/multisig execution.
- UI implementation.
- External DB dependencies.

## Directory Layout
- `src/models.py`: core schemas and validation.
- `src/interfaces.py`: service contracts and adapter boundaries.
- `src/in_memory.py`: PoC in-memory implementation.
- `src/persistence/`: SQLite/Postgres adapters, migration manager, repository factory.
- `src/persistence/orm_models.py`: single shared Base/13 ORM row mappings; legacy `sqlite_adapter` Base/row imports remain compatible. Domain dataclasses stay in `src/models.py`.
- `src/persistence/verification.py`: internal atomic SQLite verification used by the existing task pipeline; one decision/debit/event, exact replay and fail-closed legacy history. This records a supplied decision without granting verifier authority.
- `src/exceptions.py`: domain errors.
- `tests/`: schema, lifecycle, and permission tests.
- `memory/`: module memory artifacts.

## Quick Start
```powershell
cd o:\Foundups-Agent
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest modules/foundups/agent_market/tests -q
```

## Token factory backend selection

`ChainAgnosticTokenFactory` resolves exactly one backend for deployment and
vesting. `TokenTerms.chain_hint=None` selects the configured default; the
constructor/getter default remains `ChainType.MOCK` for local PoC compatibility.
An explicit `chain_hint="mock"` also selects simulation. Mock results retain
`chain_type=MOCK`, `metadata["mock"]=True` and synthetic addresses/transaction IDs.

Chain names are case-insensitive with outer whitespace removed. Empty, unknown
or non-string hints raise FAM `ValidationError`. A missing/disconnected selected
backend, failed health check or changed chain identity also rejects, including
when selecting the configured default. There is no fallback to another chain.
Successful deployment results must report the selected `ChainType` before they
are cached or returned as success. Only the mock backend ships here; a chain
enum is not a real integration.

This validates adapter selection and result consistency, not independently
confirmed blockchain effects. Deployment caching and treasury-address helpers
remain local PoC behavior. The launch orchestrator reports selection errors as
failed launches before token-success/repo/task completion; its earlier registry
creation is not rolled back by this change.

## Privileged task operations

Verification and payout initiation require explicit `CallerAuthorization` from
the trusted host, in both memory and persistent implementations. Missing context
denies by default. This changes callers that previously relied only on
`actor_roles`, a supplied verifier ID or compute credits.

```python
from modules.foundups.agent_market.src.authorization import CallerAuthorization

# Both inputs come from the authenticated host and approved grant policy.
# They must not be copied from the submitted task/decision/profile payload.
authority = CallerAuthorization(authenticated_subject, approved_frozen_role_grants)
pipeline.verify_proof(task_id, decision, authorization=authority)
# A treasury caller supplies its own exact FoundUp/treasury grant.
pipeline.trigger_payout(task_id, treasury_subject, authorization=treasury_authority)
```

Grants are exact `(foundup_id, role)` pairs. Verification requires `verifier` and
independence from the stored proof submitter/assignee; initiation requires
`treasury`. Wildcards and administrator labels do not imply those permissions.
Current context is required on retries as well. SQLite preserves its existing
atomic operations and honest pending-payment state; this adds no settlement.
The simulator bridge supplies explicitly configured simulation identities.
The host must resolve current grants on every call; this class itself cannot
detect expiry or revocation of a previously constructed context.

An authenticated transport and signed/domain issuer remain separate integration
work. This Python context is a host boundary, not a portable credential or a
repository claim. See [the interface](INTERFACE.md#taskpipelineservice).

## OpenClaw Execution Arm Alignment
OpenClaw remains the execution ingress for intent routing. FAM provides explicit contracts that OpenClaw/WRE can call for launch and execution flows.
