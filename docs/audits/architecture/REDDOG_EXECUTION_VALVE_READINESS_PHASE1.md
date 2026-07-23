# RedDog Execution-Valve Readiness Phase 1

## Decision

BLOCKED for live/worktree execution. The governed execution-valve path is now
wired from main bootstrap through the resident handler to the canonical
evaluator, but it deliberately returns `VALVE_CLOSED`. The legacy
`ExecutionValveEnvironment` remains compatibility-only; its token fields are
not canonical authority.

## WSP 97 truth boundary

This slice supplies one deterministic, outside-repository
`reddog_execution_valve_environment.v1` artifact. It cross-binds one promoted
queue lineage, WSP 15 receipt, permission/principal resolver supply, model
selection/runtime pair, Memex receipt, repository, FoundUp, key epoch,
consensus evidence, and sovereign authorization digest. It writes atomically,
serializes no token or secret field, and defaults to `VALVE_CLOSED`.

The supplier does not sign or verify authority, call a model, start a signer,
open a valve, execute work, create a worktree, publish a PR, mutate the
repository, or run the live canary. Its provenance receipt is integrity
evidence, not authority.

## Authority boundary

- `GovernedExecutionValveEnvironment` has an exact allowlist serializer and no
  legacy token keys, including null or empty variants.
- A trusted caller must explicitly select
  `evaluate_reddog_execution_valve_canonical`; JSON content cannot switch the
  legacy evaluator into canonical mode.
- Canonical evaluation requires independently loaded expected bindings. The
  environment cannot supply its own expected values.
- Permission TTL and expiry are trusted caller inputs derived from verified
  authority and the permission snapshot; they are absent from the artifact.
- WORKTREE and LIVE_ENQUEUE authority is HIGH regardless of a LOW-looking
  operation label and requires consensus plus sovereign evidence.
- The authorization mode and binding digest are included in the valve decision
  digest and live-canary receipt seed.

## High-risk assumptions and failure modes

1. A promoted authority profile is mutable. Equality between the profile and
   environment is defense-in-depth only; use-time acceptance must derive the
   expected binding from accepted signed work authority and independent runtime
   artifacts.
2. The current signature verifier returns an in-memory boolean result, not a
   durable self-verifying receipt. Therefore static live-canary readiness alone
   cannot authorize execution; the execution stage must revalidate prior
   authority-runtime and verification stages to prevent TOCTOU.
3. Model-runtime receipt ID and digest are a both-or-neither pair. Half-pairs,
   top-level/operational-context disagreement, and queue/profile receipt
   splicing fail closed.
4. The promoted work-order ID is derived from the queue item. Caller-provided
   work-order IDs are ignored so a profile cannot detach work authority from
   its queue lineage.
5. The seven JSON artifacts have no independently signed immutable manifest.
   Their internal digests and provenance receipts are integrity checks only.
6. The signer server authenticates clients, but the client has no fresh signed
   challenge or server-peer credential proof. The health check is not a trusted
   handshake.
7. No production verifier exists for the consensus or sovereign digests; the
   principal subject-to-key source is not independently attested; model signed
   evidence lacks complete durable nonce/revocation/trusted-key provenance.
   The authority and nonce store is cross-process atomic under its canonical
   `.operation` lock, but that serialization is not an independent trust anchor.

## Alternatives rejected

- Nonempty sovereign token strings: model-fabricatable and not evidence.
- A `canonical_required` JSON flag: lets untrusted data select enforcement.
- Trusting environment TTL/expiry: permits freshness extension by file edit.
- Readiness-only semantic checks: insufficient at the execution TOCTOU point.

## Production behavior and remaining operational gate

The resident execution-valve stage now secure-reloads the governed artifacts,
validates the current chain revision, checks queue/claim/work-order equality,
recomputes the signed work-authority receipt digest, and re-runs signed-authority
verification without consuming a second nonce. The earlier authority stage
and the recorded verification stage both use `PREFLIGHT_NON_CONSUMING`. Only
the terminal authoritative-use lease consumes the nonce, under the same
cross-process `.operation` lock used by the canonical store writer.

The signed work authority now binds the exact explicit `base_ref` and the
canonical digest of every full work-order field. Use-time resolution recomputes
that digest, the executor plan carries both bindings in its own verified digest,
and the effect runner uses only the validated plan snapshot. A mutable work
order is never consulted for `base_ref` after authoritative admission. Terminal
`AUTHORITATIVE_USE` verification also receives a fresh invocation clock, so an
identity or permission snapshot that expires after preflight still fails closed
before nonce consumption and before the runner.

The canonical evaluator is invoked, then forced closed with exact missing-anchor
reasons. In particular,
`canonical_signed_runtime_artifact_manifest_producer_missing` is always present
until an independent descriptor-derived immutable manifest is signed and
verified. Consensus, sovereign, principal-key, model-evidence, signer-handshake,
and nonce-store anchors must also land before the blocker can be removed. No
READY result, worktree creation, signer start, model call, or live canary was
produced by this slice.
