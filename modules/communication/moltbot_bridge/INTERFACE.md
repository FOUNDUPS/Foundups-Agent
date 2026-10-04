## Current-generation review-set API — 2026-10-04

```python
verify_current_effect_reviewer_decisions(
    *, owner_config_path, repo_root, decisions, context, authority_request,
    target, expected_target, policy, runtime_evidence_resolver,
    revoked_key_epochs=frozenset(),
) -> bool
```

Both current single/plural entry points remain exposed by the existing consensus
verification facade; their thin wrappers live in the existing leased owner.
The single signature/defaults are unchanged. Plural input is an exact list/tuple
of1–8 strict effect reviews; the shared internal entry rejects both/neither mode
before owner selection. Conditional quorum wire/role/independence rules still apply.

The caller cannot inject a clock, key resolver, signature verifier or generation
selection. One owner-derived selection lease encloses principal artifact loading,
scoped key projection, actual Ed25519 verification, final owner/time/input checks
and projection cleanup. Ordinary lease-exit failures returnFalse; interrupts
propagate after cleanup. No success is delivered before normal lease exit.

Every resolved runtime object is retained with its immediate defensive field
snapshot, including repeated object identities. At most eight resolver calls;
the ninth rejects before calling the resolver. Final checks never refresh the
supplied evidence: every retained record must still match and remain current.
All reviewer-key expiries are checked against the same trusted finish time.
Inputs are compared after final owner reread and clock sampling. Changed owner,
clock rollback, input mutation, expired evidence or cleanup exceptions reject.

This supplies current scoped key authentication and quorum relative to the
supplied runtime evidence. It does not authenticate that producer, prove continuous
immutability across arbitrary concurrent changes, authenticate sovereign effect
authority, issue a permit, consume an effect lease or admit an autonomous worker.

## Bounded effect-review quorum API — 2026-10-04

`verify_effect_reviewer_decisions(*, decisions, context, authority_request,
target, expected_target, policy, signature_verifier, reviewer_key_resolver,
runtime_evidence_resolver, now, revoked_key_epochs=frozenset()) -> bool` extends
`src/reddog_elevated_authority_consensus_verification.py`.

- Accept an exact list/tuple containing 1–8 strict effect-review dictionaries.
  The canonical sorted compact ASCII JSON `{"decisions": [...]}` envelope must
  be at most 8192 bytes. This bounds accepted wire data, not peak memory.
- Freeze decoded reviews; validate actual parent/target/context and supplied
  policy before resolvers. Require minimum approvals and every required role.
- Every review must approve this exact effect context and match membership.
  Invalid extras are rejected, never dropped to obtain a passing subset.
- Require distinct reviewer identities, public keys, model IDs and runtime
  binding digests. Exclude parent/RedDog/worker identities, parent/RedDog keys,
  and author runtime. Use each resolved verified key/runtime pair once.
- Preserve `reddog-effect-consensus-review.v1.` signing bytes and effect schema.
  Malformed data, stale/revoked/substituted evidence or collaborator exceptions
  return `False`; no nonce is consumed and no permit is issued.

Success is conditional on the supplied trusted policy, verifier and resolvers.
An arbitrary sovereign digest can still pass structural review; authenticating
sovereign effect authority is a separate mandatory gate. This API is not yet
composed with the current-generation multi-review owner, deployed independent
runtime provenance, a single-target effect permit or native worker admission.
The old single-review and delegated consensus APIs remain compatible.

## Single-effect proof handoff design — 2026-10-01

**Pure binding API implemented; authenticated effect handoff remains planned.**
Implementation source base: `252f700fbac4c4adb98f3dd81c3d05eadb8fce66`.
PR#2001's eleven local and exact PR/main controls established the existing domain
separation. The current layer adds structural construction and correlation in
existing owners. The delegated v1 two-child path remains unchanged.

`reddog_elevated_authority_consensus_evidence` now exposes:

```python
build_effect_target_binding(*, parent, target, expected_target, now) -> dict[str, str] | None
effect_target_binding_matches(binding, *, parent, target, expected_target, now) -> bool
```

The builder returns a fresh four-field mapping or `None`; the matcher recomputes
it and returns `False` on invalid input, including `None` supplied with invalid
construction inputs. Neither function authenticates a principal or producer,
issues a grant or permit, signs a request, consumes a lease, or admits a worker.
Local qualification: all 32 frozen new cases passed after all 32 baseline cases
failed at the expected missing-API assertion; both runs had zero errors/skips.
The prior pure-binding PR#2003 is merged/main-verified; see the current layer below.

### Conditional effect-review verification API — 2026-10-01

`verify_effect_reviewer_decision(*, decision, context, authority_request, target,
expected_target, policy, signature_verifier, reviewer_key_resolver,
runtime_evidence_resolver, now, revoked_key_epochs=frozenset()) -> bool` lives in
the existing `reddog_elevated_authority_consensus_verification.py` owner.

- Decode a plain dictionary with exactly the existing reviewer-decision fields:
  every value nonempty ASCII text, at most4096 characters, total canonical JSON
  at most8192 bytes, with strict lowercase SHA-256 context/selection/runtime
  digests. The fixed schema is `reddog_effect_reviewer_decision.v1`.
- Correlate the exact validated effect context with the current actual parent,
  target and expected target through `effect_approval_context_matches`.
- Require a valid supplied policy whose digest, roles and minimum approvals
  match the context, with context lifetime no greater than policy maximum TTL.
- Require exact reviewer id/provider/role membership; exclude parent, RedDog and
  queue worker identities, parent/RedDog keys, and the author's runtime binding.
- Resolve exact key/runtime evidence classes; match key epoch, model and receipt
  identities/digests; reject revoked epochs and non-integer or expired timestamps
  before signature verification. Verifier result must be exactly `True`.
- Signed input is `reddog-effect-consensus-review.v1.` followed by sorted compact
  ASCII JSON containing every validated decision field except `signature`.
  The opaque nonempty signature is passed unchanged to the supplied verifier.
  All invalid inputs and collaborator exceptions return `False`.

`rehydrate_effect_reviewer_decision(value)` in the existing rehydration owner
only decodes this strict data boundary; it does not authenticate a review.
Delegated public receipt decoding and signing domains remain unchanged.

One-review validity is conditional on supplied policy/resolvers/verifier. It is
not authenticated production provenance, quorum, sovereign effect authority,
requester/beneficiary authorization, a capability/permit, replay consumption or
native admission. No production consumer is wired. An inert recording verifier
tests byte/decision logic; these fixtures are not independent runtime receipts.

Frozen qualification: 82 expected missing-API baseline failures → 82 local
passes. PR #2010 is merged/main-verified at `f4978e12`: exact PR and main CI
each passed all 222 selected cases, plus 74 correspondence, 308 measurement
(two known pytest configuration warnings) and 85 caller cases. All ten PR
checks and both main workflows succeeded; the owned lane is closed. These are
regression counts, not independent proof of runtime authority or retained gain.
Historical pending prose below is superseded by the canonical backlog closure.

Historical PR #2013 prerequisite (now merged/main-verified and closed): 6 frozen
test-only Ed25519 cases through
this unchanged API and the actual public verifier: valid signature accepts;
payload/signature/key tampering and two wrong-domain signatures reject. Local 95
cases pass including 82 prior and 7 structural controls; hosted 228 pending. Keys
exist only in test memory. Supplied resolver provenance and inner-designation
authentication remain unproven; no production caller or authority is added.

### Connected current reviewer verification API — 2026-10-01

**Implemented in the current 15/P1 layer; locally verified, hosted/publication pending.**
PR #2013 closed at `c9d1273`. The existing consensus verification owner now exposes:

```python
verify_current_effect_reviewer_decision(
    *, owner_config_path, repo_root, decision, context, authority_request,
    target, expected_target, policy, runtime_evidence_resolver,
    revoked_key_epochs=frozenset(),
) -> bool
```

The caller does not inject owner data, a generation boundary, signature verifier or
reviewer-key resolver. The private current-review leaf loads authenticated owner
v5, derives one selection from that same config identity and holds its lease
through confined principal-artifact reading and effect review. The strict
`reddog_reviewer_designation_contract.py` leaf owns the exact 12/14/7-field root,
inner designation and reviewer-entry wire shapes. It bounds the complete prefixed
canonical signing input to 65536 bytes; validation alone authenticates nothing.
Both designation and review use the existing real Ed25519 backend.

Principal v2 adds exactly one designation to the existing identity envelope;
`PrincipalAuthorityRecord` and strict v1 parsing remain unchanged. The existing
supplier's optional `reviewer_authorizations` and `reviewer_principal_records`
carry 1–8 distinct reviewer identities with exact pair/key/repository/FoundUp
coverage; defaults retain v1 and the permission snapshot remains singular v1.
Readiness accepts the v2 principal shape without claiming signature authentication.
Existing grant-owner, transport and source-policy consumers recognize v5; their
separate grant/replay semantics are preserved.

Projection requires every role assigned to the reviewer pair in the pinned policy
to be authorized by the signed designation. Explicit owner/designation/entry and
manifest expiries bound the key; selection lifetime is checked separately. Inputs
are captured and compared after callbacks. Before success, authenticated owner
identity and trusted time are rechecked while the lease is held; the private key
resolver is closed on exit. These sampled checks are not atomic revocation or a
guarantee after return. Runtime evidence is still supplied by the caller.

Local candidate-4 passed 198/198 with no failures/errors/skips, exact IDs, stable
source samples and no unexpected denials. Hosted 331 portable and 8 Linux cases
are pending. The five actual-root cases cover positive, UID, mode, symlink and
anchor-tamper rejection; the last is not a valid signed-rotation proof. Three
existing transport v3/v4/v5 cases complete the Linux selection. This is one scoped
reviewer's conditional validity, not quorum, independent runtime provenance,
effect-scoped sovereign permission, a permit, native admission or retained gain.

### Authenticated effect-authority qualification — 2026-10-01

Source-qualified at `f4978e12e94e1b0d151b38b16c295d2bda374b23` after
PR #2010's verified merge. The conditional reviewer API above is implemented;
the table below records the **historical pre-composition gaps**. The connected
key portion is now implemented as documented above; runtime/effect authority
and admission remain open.
The earlier scoped absence finding applies to effect-consensus adapters, not
to all identity/runtime verification infrastructure.

| Existing owner | Evidence it actually supplies | Missing effect-review bridge |
|---|---|---|
| `modules/ai_intelligence/ai_gateway/src/model_runtime_binding_use_time_verifier.py` | Re-verifies persisted signed model evidence and issues a one-shot runtime capability; the existing topology consumes that capability. | Bind that authenticated runtime and selection to this reviewer principal and decision. A model capability alone is not review authority. |
| `src/reddog_signer_current_principal_authority_resolver.py` | Selects and leases a signed generation for each resolution. | This is an effectful lease operation, not a passive lookup. Composition needs explicit lifetime/cleanup accounting. |
| `src/reddog_signer_owner_e0_principal_authority.py` and `src/reddog_authority_runtime_store.py` | Confined, digest-bound principal records provide identity, key and repo/FoundUp scopes. | `PrincipalAuthorityRecord` has no reviewer role membership, key epoch/expiry or authorization of this effect. Do not synthesize them from identity. |
| `src/reddog_elevated_authority_consensus_policy.py` | Protocols and strict supplied policy/evidence types; existing sovereign evidence binds a delegated parent. | Trusted policy origin, current reviewer key authority and explicit B/P/T/E plus requester/beneficiary authorization remain unresolved. |
| `src/reddog_elevated_authority_consensus_verification.py` | Conditional verification of one effect review, including actual-input correlation. | Supplied resolver results do not authenticate their own provenance; quorum/permit/replay remain later gates. |

#### Reviewer-key designation contract — 2026-10-01

**Historical design contract, qualified at `1ff01a9`.** Its connected key
implementation is documented above; this original design is not a runtime grant. The architect selects an explicit, opt-in designation block in
the existing root-owned signer owner configuration as the trust source. This
resolves the source-design choice; it does not select real issuer identities,
provision keys, write operational configuration or authorize a worker.

**Version and ownership:** reserve owner-config v5 as v4 plus
`reviewer_designation_authority`, validated by the existing
`reddog_signer_system_service_manifest_selection_loader.py`. Preserve exact
v1–v4 behavior; none implicitly grants reviewer-designation permission. Reuse
the authenticated-read/revalidation pattern in
`reddog_grant_authority_source_policy_authority.py`; do not reuse its privilege
or secret-grant revocation evidence. The existing owner loader requires Linux,
root ownership, confined paths and secure ancestors; Windows must keep rejecting
this production path. An isolated Linux fixture is not a live installation.

The principal artifact remains `principal_authority_records.json`. A versioned
v2 envelope adds a sibling `reviewer_authorizations` collection to its existing
identity collection. `PrincipalAuthorityRecord` and strict v1 parsing remain
unchanged. Extend the existing resolver artifact supplier, principal parser/
loader and current-principal resolver; no new registry, database or orchestrator.
The outer manifest authenticates generation membership and artifact bytes;
the separately signed inner designation authenticates reviewer permission.

| Boundary | Required signed or trusted fields and semantics |
|---|---|
| Root-owned designation block | Exact schema; explicit `designate_effect_reviewers` privilege; issuer principal/provider/public key/key epoch; exact repository, FoundUp, consensus-policy digest and `reddog_effect_reviewer_decision.v1` domain; exact integer issuance/expiry. Actual values are separately authorized installation inputs. Neither the inner artifact nor manifest signer may supply its own trust anchor. |
| Inner designation | Distinct `reddog-reviewer-designation.v1.` signing domain; issuer identity/epoch and privilege; digest of the trusted designation block; exact repository/FoundUp/policy/decision-domain binding; issuance/expiry; bounded reviewer entries; signature. Canonical sorted compact ASCII JSON excludes only the signature from the signing input. Derive any audit digest; do not accept a self-asserted verified flag. |
| Reviewer entry | Exact principal/provider, public key, reviewer key epoch, authorized roles and issuance/expiry. Require the public key and identity to match the current manifest-bound principal record and its repository/FoundUp scope. Reviewer epoch/expiry are explicit values, never the manifest-signing epoch or selection TTL renamed. |
| Shape and bounds | Freeze exact wire keys before code; reject unknown/duplicate JSON keys and implicit coercions. Retain the existing 64 KiB owner-config and 1 MiB artifact ceilings. At most eight unique reviewer pairs, each with one key/epoch and 1–8 unique bounded ASCII roles. Exact integers only for time; false/zero/unknown evidence cannot become authenticated success. All lifetime intervals must be nonempty. |

The table fixes required semantics and domain separation; final spelling of the
new wire fields and canonical golden bytes must be frozen by the independent
test plan before implementation. Existing v1 field sets are not relaxed.
One exact scope/policy per verification keeps this first layer small; multiple
FoundUps use separately authorized scoped instances, not a wildcard grant.

**Connected use-time contract:** the narrow composition entry remains in the
existing effect-verification owner. It loads one authenticated owner snapshot,
checks the actual parent repository/FoundUp, actual policy digest and effect
decision domain, and derives the generation boundary from that same config ID.
Never combine a refreshed designation allowlist with a cached older boundary.
It validates the current policy shape/digest and captures the exact policy and
actual inputs used by `verify_effect_reviewer_decision`.

Acquire the existing one-use selection and hold its generation lease through
confined artifact reading, inner signature verification, scoped key resolution
and the conditional effect check. Issuer key/privilege must match the explicit
root-owned block before trusting any inner designation. The production composition
uses the existing `reddog_ed25519_signature_verifier_backend.py` public verifier
for designation and review signatures; caller-supplied recording or always-true
verifiers cannot establish authenticated acceptance. The earlier conditional API
keeps its explicit limits. Runtime evidence remains an independent required
input; this slice cannot authenticate it by assertion.
The consumer must not expose a reusable bare reviewer-key resolver/capability
that remains accepted after this composition/lease ends.

The existing `resolve(principal_id, provider)` cannot see a decision role.
Therefore collect **all** roles assigned to that pair in the exact pinned
policy's `reviewer_membership`; require a nonempty set wholly contained in the
signed entry's authorized roles before projecting key/epoch/expiry. Checking
only intersection or `required_roles` is insufficient. A policy assigning
critic+verifier with only a critic grant must reject the projection, even for
critic; this deliberate conservative rule preserves the existing protocol.
Using that projection with another policy or actual scope must fail.

Before acceptance, re-read authenticated owner configuration while the lease
is still held and reject observed config identity changes; recheck trusted time.
Effective authority expiry is the minimum of explicit owner/designation/entry
and manifest expiries, additionally respecting the effect context's existing
policy maximum-TTL/current-time checks. `ElevatedConsensusPolicy` has no absolute
expiry field: do not invent one. Selection lifetime is an additional use-time
gate, not reviewer-key lifetime. Every exception releases the lease and rejects.

**Temporal limit:** these are authenticated sampled owner reads and a fenced
generation at checked boundaries. They do not establish an atomic owner-config
and generation transaction, detect all change-and-restore events, guarantee
authority after return, or make revocation permanent across root-config rollback.
Current-generation reviewer removal/key rotation and explicit owner-block
removal/rotation revoke on the next observed use. Stronger monotonic revocation
requires separate authorized evidence; no new revocation store is selected.

**Historical implementation prerequisites:** loader changes alone cannot advertise v5
support. Existing `reddog_grant_authority_service_owner_binding.py` and
`reddog_signer_independent_grant_authority_client_supply.py` accept v3/v4, while
`reddog_grant_authority_source_policy_authority.py` load/revalidate requires v4.
The principal readiness consumer also requires v1 today; qualify its v2 branch
without widening permission snapshots. Bound the entire inner signing input,
including prefix, to the public verifier's 65536-byte ceiling. Expose trusted
manifest expiry through the current selection without changing legacy launch
values; selection expiry is not a substitute. Reuse the selection already
returned by `_manifest_selection_from_owner` rather than abandoning an extra one.

Qualify all affected schema consumers and preserve v1–v4 rejection/acceptance
behavior before allowing a v5 startup composition. Keep independent grant
re-verification/nonce ownership in the existing signer path; no effect permit,
sovereign authorization or worker activation is added by the key layer.

**Frozen acceptance before code:** legacy v1–v4 controls; exact-field/duplicate/
size/time bounds; unauthorized issuer despite a valid outer manifest/signature;
wrong issuer/key epoch/provider/role/repository/FoundUp/policy/domain; the
critic-only projection and cross-policy reuse counterexamples; owner A versus
boundary B; observed removal/rotation and stale selection; expiration during
verification; lease cleanup and escaped-resolver use; an independently supplied
signed positive reaching the existing effect verifier. Public vectors for other
messages or a recording verifier cannot supply that positive. Test-signing
budget/fixtures and installed authority are separate inputs; this document
authorizes neither operational signing nor production configuration.

Historical next selection: one connected, nonactivating reviewer-key implementation with independent
oracles and version-consumer tests, re-observed under WSP15. Runtime-to-reviewer,
sovereign B/P/T/E/requester/beneficiary authority, quorum/permit/replay and native
admission remain later gates. No source/runtime calls or retained RSI benefit
were produced by this contract-design sprint.

### Pure effect-context correlation API — 2026-10-01

`effect_approval_context_matches(context, *, parent, target, expected_target, now)`
extends `reddog_elevated_authority_consensus_effect_context.py`. It returns an
exact Boolean. `True` means structural, current correlation, never approval.

- Require the exact `EffectApprovalContext` class and its strict canonical
  validation, including tuple roles; reject malformed manually built values.
- Require exact integer `now`; enforce `issued_at <= now < expires_at`.
- Recompute B through existing `effect_target_binding_matches` using the
  context's binding schema and P/T/E fields plus actual parent/target inputs.
- Revalidate the target payload and require context expiry no later than target
  expiry. The existing B matcher also bounds the target by both parent expiries.
- Return `False` for invalid input or a rejected existing validator. Preserve
  inputs and delegated v1. No production consumer is wired.

Well-formed policy/sovereign references remain untrusted assertions. This does
not resolve them, compare principal and requester identities, equate context
and target nonces, require context issuance after target issuance, limit policy
TTL/skew, or require approvals to be no greater than the number of roles.
Authenticated provenance, independent review and promotion remain separate.

The context decoder from PR #2008 is merged/main-verified (97 hosted controls).
New frozen correlation cases: 43 expected missing-API baseline failures → 43
candidate passes; existing CI now selects 140 cases, hosted results pending.
The guarded local runner is not an OS sandbox or an admitted WRE execution.

### Inert effect-approval context API — 2026-10-01

The pure binding and structural checks are merged/main-verified in PR#2003/2005;
their owned lanes are closed. At source base `ae922cc30`, the focused sibling
`src/reddog_elevated_authority_consensus_effect_context.py` adds a data carrier
and decoder, not an authenticated producer or a production consumer.

Public APIs: `EffectApprovalContext.to_dict()`,
`rehydrate_effect_approval_context(value)`,
`canonical_effect_approval_context_bytes(context)` and
`canonical_effect_approval_context_digest(context)`.

The wire mapping has exactly these12 fields:

| Fields | Contract |
|---|---|
| `schema_version`, `binding_schema_version` | Exactly `reddog_effect_approval_context.v1` and existing `reddog_effect_target_binding.v1`. |
| `parent_authority_request_digest`, `target_signing_request_digest`, `effect_request_digest` | Declared P/T/E; together with the binding schema they reconstruct B. No digest is recomputed from an actual target at this layer. |
| `sovereign_authorization_digest`, `consensus_policy_digest` | Untrusted references to later independently resolved evidence. All five digests are exact strings containing canonical lowercase SHA-256. |
| `required_approvals`, `required_roles` | Exact integer1–8; plain list of1–8 unique nonempty ASCII strings of at most256 characters. Multiple reviewers may share a role; no approvals≤roles rule. These are policy assertions, not policy decisions. |
| `nonce`, `issued_at`, `expires_at` | Nonempty ASCII nonce≤256 characters; exact integers `0 <= issued_at < expires_at`. No clock, maximum TTL, provenance or freshness decision here. |

The entire sorted compact ASCII JSON wire representation is bounded by the
existing8192-byte consensus limit. No extra keys, subclasses or Boolean-as-integer
coercion. The frozen internal context uses a tuple of roles; exports contain a
fresh list. Canonical APIs reject malformed manually constructed contexts and
non-tuple internal roles. Invalid data raises `ValueError`.

Canonical bytes are `b"reddog-effect-approval-context.v1."` followed by that JSON;
the digest is `sha256:` plus SHA-256 of those bytes. This is deliberately distinct
from delegated v1 context/decision bytes. It is not a signature API or verified
receipt, and cannot enter the existing delegated decoder or two-child permit.
Future signed reviewer decisions must bind reviewer identity, role and admitted
runtime as well as this context; no incomplete context-only approval is issued.

Independent frozen47 cases: baseline47 expected missing-API failures; candidate
47pass/0fail/0error/0skip, exact case IDs and stable source samples. Existing CI
retains50 controls and adds47 (97total); PR #2008 and exact main checks passed.
The pure correlation API above now recomputes B. Next qualify the existing-owner
signed-decision/provenance boundary before permit/provider integration. Registry/identity evidence
alone does not establish explicit effect approval. Native RSI remains unadmitted.

### Decision and evidence

Select explicit effect-domain authorization; reject implicit conversion of a
delegated-work receipt into an effect permit. The implemented pure adaptation
covers **HIGH / worktree_create only**. ULTRA and live_enqueue remain outside
this adaptation; their existing request schemas are not removed or downgraded.

`reddog_elevated_authority_consensus_evidence._sovereign_matches` binds sovereign
evidence to a delegated request, work order and identities. Reviewer evidence
signs its exact consensus context. Neither the scoped producer search nor the
existing two-HIGH-child permit establishes authenticated approval of the later
effect target. This is an evidence gap; installed runtime state is unknown.

An authentic producer must explicitly authorize the precise effect binding.
Its principal authority, policy membership, independent reviewer evidence,
scope, expiry and revocation must be resolved through existing trusted owners.
A matching work-order ID, signed parent receipt, self-asserted approval or a
synthetic test fixture is insufficient. Producer admission remains blocked
until that provenance is independently qualified.

### Digest and carrier contract

| Name | Meaning and existing owner | Binding and later handoff rule |
|---|---|---|
| E | `authoritative_use_effect_digest(kind, payload)` in `reddog_authoritative_use_lease_contract` | Exact worktree effect; retain queue/slice/work-order, plan and valve bindings. |
| T | `signer_secret_access_request_digest(request.to_dict())` in `reddog_signer_secret_access_grant_contract` | Complete canonical effect SigningRequest, including requester, signer/key epoch, generation, session/replay identity, nonce and lifetime through its payload. No proof inserted into the target. |
| P | `canonical_authority_request_digest(parent)` in `reddog_elevated_authority_consensus_contract` | Parent reference only. Its projection removes back-references; P alone grants no authority. |
| B | Domain-separated single-effect binding over P, T and E | Implemented pure structural contract in existing contract/evidence owners; cannot reuse the delegated signing-input projection C, which hashes a different request domain. |
| G | Existing `signer_secret_access_grant_id(grant)` | Grant continues to bind T, exact beneficiary, operation, tier and replay owner. Grant issuer/requester and effect beneficiary stay distinct. |

The B mapping has exactly `schema_version`,
`parent_authority_request_digest`, `target_signing_request_digest`, and
`effect_request_digest`. Schema label: `reddog_effect_target_binding.v1`.
Hash it with the existing strict canonical JSON digest. Recompute P/T/E from
validated inputs; never accept supplied digests as independent evidence. T must
be formed after the issuer's existing replay-store binding is final; later
rebinding invalidates B and requires fresh authorization, not digest rewriting.

The pure builder requires exact `DelegatedAuthorityRuntimeRequest` and
`SigningRequest` types, parent `requested_operation == "worktree_create"`,
and HIGH derived by
`delegated_authority_tier(parent)`; there is no parent `authority_tier` field.
Both effect `work_order_id` and `work_order_digest` must equal the parent.
Check canonical HIGH/worktree_create target shape, its existing freshness
rules, and a plain `expected_target` dictionary whose strict canonical JSON
digest equals that of `target.to_dict()`. Python Boolean/integer equality is
insufficient. `now` and parent timestamps must be exact integers, with
`issued_at <= now` and both declared identity/work-authority
expiries greater than now; target expiry must not exceed either declared expiry.
These are structural comparisons, not authenticated parent freshness or scope.
Caller-supplied expected values remain untrusted test or planning inputs. Do
not infer that the parent principal equals the actual effect requester:
that mapping needs separately authenticated evidence.

The future effect proof has a distinct explicit domain/version and travels
**outside** the effect target. The existing lease request builder leaves proof and consensus
absent; `_request_matches` explicitly checks only consensus absence. The implemented
pure binding requires typed `SigningRequest.elevated_consensus_proof is None`
and canonical `to_dict()` omission of that key. This additional binding check
does not change the existing lease validator. The future provider handoff must
obtain the outer grant's receipt digest from a
verified effect proof, not copy the target's `None` or fill it from an arbitrary
mapping. The grant signer must independently reverify the same B and exact T.
The v1 delegated rehydrator and generic permit must not accept this by widening
their roles. Final effect-proof fields and authenticated producer registration
are a later gate; the B mapping is not a completed proof schema.

### Existing ownership and lifecycle

| Stage | Extend only after its preceding gate passes |
|---|---|
| Canonical binding | `reddog_authoritative_use_lease_contract`, `reddog_elevated_authority_consensus_contract` and `reddog_elevated_authority_consensus_evidence`: pure validation/correlation only. |
| Authentic authorization | Existing sovereign/policy/reviewer resolver and verification owners: bind fresh authorized effect context to B; preserve independent review and revocation. No producer is admitted by this plan. |
| Local handoff | Existing consensus capability and issuer/provider owners: separately typed single-target permit, exact provider/beneficiary binding; never repurpose the two-child delegated permit. |
| Grant boundary | Existing grant issuance/admission and consensus signer verification owners: explicit proof-domain dispatch, re-verification and existing durable reservation. |
| Effect consumption | Existing resolve-per-sign backend, lease rehydration and effect registries: retain grant consumption, generation fencing and one-use exact-effect consumption. |

Proposed expiry is the earliest applicable bound: effect target (at most30s),
effect approval, parent authorization, independent grant policy, current owner
generation/selection and grant TTL. Check at each use; a later stage never
extends an earlier expiry. Unknown bounds reject. Numeric/type and clock rules
must remain explicit; no implicit Boolean-to-integer coercion.

Local permit consumption and durable signer reservation are separate events.
Use one target per effect permit and an explicit effect-domain durable nonce
binding B plus receipt identity in the existing replay owner. Do not reuse the
delegated two-child nonce domain. Successful grant signing consumes its own
authorization; it is not proof the final effect ran. A downstream failure must
not remint an equivalent permit or erase prior consumption. Ambiguous cleanup
stops and records the attempt for reconciliation. Existing rollback attempts
can suppress errors; they do not establish all-failure restoration. Detailed
restart/recovery behavior must be qualified before issuer composition.

### Layer gates and acceptance

1. **Current pure layer, 13/P1 (C2/I4/D4/Impact3):** 32 new cases were frozen
   before implementation in the existing canonicalization test owner, including
   independent golden P/T/E values, work-order/time correlation, exact expected
   target and B substitution, and valid HIGH/live_enqueue rejection. Baseline:
   32 expected missing-API failures. Candidate: 32 passes. Both had zero
   errors/skips and the same exact case IDs. The original four cases remain
   unchanged and are excluded locally because their fixture invokes a signing
   helper. Synthetic positives establish structural agreement only; the later
   proof schema is not parsed here. Hosted checks and publication remain pending.
2. Qualify authentic effect-specific authorization provenance and independent
   signer re-verification; only then adapt the typed permit/provider handoff.
3. Test disposable full issuer composition, one-use/restart/rollback outcomes,
   then the remaining resident/supervision prerequisites. Re-observe before
   admitting one worker. AmIBot remains downstream of that gate.
4. Measure a held-out baseline/candidate outcome and retained use on a later
   invocation before calling the result RSI improvement; worker count is not
   an improvement metric.

Do not repeat PR#2001's eleven negative controls as new progress. No new
orchestrator, registry, storage family or skill is selected. This layer does
not clear the seven remaining resident trust reasons or the supervisor blocker.
Canonical sequencing and closure evidence: `docs/roadmaps/rsi_swarm_backlog.json`,
historical observation `effect_proof_design_20261001`. Current local evidence:
`O:/Foundups-Agent-audits/20261001-rsi-effect-binding/`, including frozen
`test-plan.json`, baseline/candidate XML and receipts, and independent source/
execution gate `execution-review-candidate.json`. No retained RSI gain is claimed.

## Effect-lease consensus qualification — 2026-10-01

The finite existing-owner qualification passed **11/11 local cases**, with zero
failures, errors or skips. HIGH/ULTRA effect requests are valid in their own
contract but cannot enter the actual independent grant provider without its
typed consensus permit. The client rejects the effect role, and the existing
delegated pair remains valid while effect substitutions fail. No production
policy was changed; this is measured rejection/domain evidence, not successful
issuer composition, native admission or retained RSI improvement.

The first attempt stopped at collection (exit4, one collection error, zero case
bodies): pytest accessed an empty package initializer omitted from the source
inventory. A separately reviewed retry added only that binding; all eleven
case IDs, expectations and production sources stayed fixed. No database opened
and no unexpected guard denial occurred on the retry. Downstream counters stayed
untouched except for the declared local clock/provider identity calls.

Existing CI now selects these exact eleven cases with namespace isolation and
the same Python audit constraints. Hosted results are recorded separately after
execution. These constraints are not OS isolation or general native containment;
model-framework imports are denied, while reviewed dependency imports remain.
Source hashes are sampled before/after. The inherited local receipt field
`loaded_source_bindings` includes hash-check reads and is **not an import trace**;
CI uses the accurate `observed_source_read_bindings` name.

Evidence: `O:/Foundups-Agent-audits/20261001-rsi-effect-consensus/` and canonical
backlog `current_observation.effect_consensus_qualification_20261001`.

Next WSP15 13/P1: Specify the existing-owner effect-lease consensus proof handoff before any compatibility repair. No runtime activation is granted.

## Effect-lease admission map — 2026-10-01

Source-only trace at `71e26ea598dae90865b16bf8dfd9eb9a34117088`; installed
runtime/configuration remains **unknown**. No authority, model, socket, service,
operational-store or application-test call was made. This map names existing
owners and composition prerequisites; it does not admit a worker.

| Boundary | Existing producer → consumer | Required evidence / present gap |
|---|---|---|
| Work identity | `reddog_main_resident_queue_serial_loop_bootstrap` → `GovernedValveUseTimeAuthorityResolver` | Exact queue/slice, full work-order/base digest, runtime root, trusted time and signed authority. No concrete selected runtime ticket was supplied or observed in this slice. |
| Generation | Root-owned manifest selection → `verify_signer_current_generation_runtime_binding` → use-time collector | Accepted typed evidence removes only three of ten named trust reasons. Binding verification consumes a selection capability; it is not a passive status probe. |
| Readiness | `reddog_resident_runtime_artifact_readiness` → canary readiness projection | Seven artifact files are checked; three generation reasons are added independently. This is not the resolver's complete reason set or authority. |
| Remaining trust | Existing consensus, sovereign, principal, model, Memex and peer owners → resolver | Seven reasons remain even after accepted generation. This does not mean every lower-level verifier is absent; authentic consumer composition remains unqualified. |
| Effect-lease request | `reddog_authoritative_use_lease_contract` → `ExternalSignerAuthoritativeUseLeaseIssuer` | Only HIGH/ULTRA; role `signer:authoritative-use-lease`. Builder and validator require absent consensus digest. |
| Grant handoff | External issuer → `IndependentSignerSecretGrantProvider.lease` | Issuer supplies no elevated-consensus permit. Real provider rejects non-LOW without a consumed typed permit before owner/grant work. Positive issuer tests substitute `_LeasedGrantProvider`; they do not prove this direct production pairing. |
| Permit domain | `prepare_elevated_authority_signing_permit` / `ElevatedConsensusExternalSignerClient` | Existing permit preparation binds exactly two HIGH principal/reddog requests and their consensus digest; client dispatch supports those roles. Adding a keyword alone cannot qualify the effect-lease role or ULTRA. Effect requests also hash the payload directly, while elevated canonical requests hash the signing-input mapping; these digest contracts are distinct. |
| Effect consumer | Resolver → valve handler → worktree/live-enqueue admission registries | Resolver currently returns `authoritative_use_lease=None`. Rejection reasons close the valve; registries require an opaque exact-effect/digest lease and consume it once. Serialized acceptance is insufficient. |
| Skill safety | `skill_runtime_admission.admit_runtime_skill` → registered skill executor | Exact bundle/manifest/scanner fingerprint is separate from signed per-effect permission. |
| External supervision | Root-selected supervisor observation + actual requester → existing lifecycle owner | Existing corrected contract still needs authenticated transport, canonical consumption and qualified visibility. Earlier strict-decoder candidates remain rejected; no retry or new parser is selected here. |

The seven remaining resolver anchors are consensus receipt, sovereign
authorization, principal subject-key attestation, model signed-evidence trust,
model-selection signed-evidence verification, Memex signed-evidence verification,
and signer/client peer handshake. Other validation failures may also occur;
ten/three/seven describes this named subset, not every possible rejection.

`ExternalSignerAuthoritativeUseLeaseIssuer.issue` enters a grant lease, external
signing and response rehydration. Rehydration consumes durable replay state;
later effect use consumes the process-local one-use lease handle.
Do not use these calls as read-only probes. The existing
`load_system_service_signer_identity(owner_config_path, repo_root)` is a narrower
non-consuming identity reader, but requires an explicit root-owned absolute
owner-config path and Linux ownership checks. It was not called. Do not guess a
service/path, infer installation absence, or turn a test receipt into live authority.

**Next qualification, 13/P1 (C2/I4/D4/Impact3):** Qualify the existing elevated-consensus and effect-lease request domains before issuer/provider integration.
Freeze finite cases using actual existing issuer/provider/consensus leaves in
the existing test owners, with isolated fake outer dependencies and no service,
secret resolution or signing authority. First demonstrate the current rejection
and identify the exact supported domain. Then select a separately reviewed
contract repair only if justified. Preserve HIGH/ULTRA and independent consensus;
do not demote to LOW, fabricate permits, relax validators, or extend role/tier
coverage merely to make a test pass. Supervisor/transport and resident trust
prerequisites remain separate; no generic orchestrator or new authority registry.

Evidence: RSI backlog `current_observation.admission_prerequisites_20261001`,
`O:/Foundups-Agent-audits/20261001-rsi-admission-prerequisites/resident-map.json`
and `issuer-map.json`. Their hashes/source bindings distinguish this static
assessment from the earlier portable and native-call experiments.

## Process visibility qualification boundary — 2026-09-27

PR1922's connected socket mapper is merged/main-verified at `d6f9458b` with252
candidate cases passing. Its public policy, backend, receipt and lifecycle APIs
remain unchanged in this test-only slice. Two hosted child conditions exercise
the existing private association seam; [test contract](tests/README.md#cross-process-visibility-qualification--2026-09-27).
Same-UID readability/denial does not satisfy the public distinct-requester rule
or supply authenticated supervisor policy. Keep PR_SET_DUMPABLE=0 and all existing
signer restrictions. No new receipt schema, issuer or execution authority.

## Connected socket ownership observation — 2026-09-27

The existing `observe_external_signer_os_state` now associates process socket
FDs with pathname metadata using exact Linux `NETLINK_SOCK_DIAG` VFS replies.
The public policy, receipt v1 and lifecycle entry points are unchanged. The
backend protocol adds `current_pid()`, `monotonic()` and
`query_unix_socket(inode, cookie, timeout)`; unsupported custom backends reject.
The default backend uses bounded `scandir` and the private same-module
`_reddog_unix_socket_identity.py`. This is an observation, not policy issuance.

The former absolute no-socket restriction is narrowed explicitly: only local
kernel AF_NETLINK/SOCK_RAW/protocol4, exact per-inode request, no dump, kernel
address `(0,0)`, one4096-byte response and no retry. No target socket connection,
service control, namespace switch, key read, provider or authority grant.
The source-boundary test inspects both files; AST checks are not containment.

At most256 FD entries and16 unique socket candidates are inspected. Duplicate
FDs are deduplicated. Well-formed unrelated/no-VFS sockets and correlated
discovery ENOENT can be skipped; malformed replies and ambiguous matches reject.
VFS inode must fit u32; compare device major/minor without truncation. Matching
VFS requires AF_UNIX stream/listening state. A concrete returned cookie and the
original FD are checked on both sides of queries and reused in the second
observation; replacement discovery is forbidden there.

Require numeric `/proc/self` equals `getpid()`, singleton matching Pid/NSpid in
self/target status, and equal stable pid/net/mnt/user namespace handles. These
checks restrict support to the same procfs/PID/namespace view; they do not
authenticate supervision. A shared2-second acceptance deadline uses the
backend's monotonic-clock contract, with remaining receive time. Nonfinite or
expired values reject; this is not a hard wall-clock guarantee for blocking
kernel/filesystem calls or a detector for every injected backward-clock step.

Source prepared; exact source/hosted/main review remains required. Existing
process/path checks, audit-only receipt, seven resident reasons and absent
effect-use lease remain. Snapshots/cookies do not prevent every ABA, FD transfer,
exit or exec; cross-UID supervision and authentic policy issuance remain open.
The earlier characterization-only contract below is historical PR1921 scope.

## Socket characterization boundary — 2026-09-27

Production observer, policy, receipt and lifecycle APIs are unchanged. Two
hosted-only cases in the existing observer test owner characterize kernel socket
inode/cookie to VFS inode/device association, unlink/rebind and wrong-cookie
rejection. See [fixed effects and oracles](tests/README.md#hosted-socket-identity-characterization--2026-09-27).
This is a qualification experiment, not the production bridge or supervisor.

The reviewed test request is exact NETLINK_SOCK_DIAG for held test-created FDs;
it does not expand the production observer's no-network boundary. The first
query discovers a cookie; repeated queries use that concrete cookie. Scope is
one process in its recorded namespaces; it cannot prove external signer process
ownership or prevent exit/exec/ABA after observation. The old inode-comparison
helper's outcome is diagnostic and is not an ownership acceptance criterion.
All seven resident trust reasons and `authoritative_use_lease=None` remain.

Implementation qualification still requires an explicitly reviewed production
consumer/boundary, malformed/foreign/truncated-input controls, namespace and
cross-process FD/lifetime handling. No successful synthetic or disposable-kernel
result alone admits a signer or native RSI worker.

## External supervision source contract — 2026-09-27

**Corrected design merged in PR1924 at `1033310bc`; authenticated observation
transport, canonical consumer registration and deployment visibility remain
unimplemented.** PR1922 repaired
socket/VFS association; PR1923 qualified same-UID child visibility and denial.
Neither qualifies an authenticated supervisor or the full distinct-UID path.
This correction changes no API, process identity, privilege or service state.

**Backend qualification, 2026-09-28:** source review rejected dbus-fast 5.0.22
MessageBus (pre-auth/received-FD ownership), Jeepney 0.9.0 Parser (non-advancing
container parse), and dbus-fast's stream-only codec (missing strict consumed-byte
and wire-validity evidence). No package/runtime was exercised; this changes no
API or dependency pin. The existing owner must receive reviewed strict-decoder
evidence for complete frame/container consumption, terminator/header validity,
bounded malformed-length progress and usable interpreted/compiled APIs before
implementation can be selected. No parser fork, new grammar, third-library
search or unchanged retry is selected. The [canonical checkpoint](../../../docs/operations/RSI_SWARM_DISPATCH.md#manager-backend-qualification-closure--2026-09-28)
binds the findings, source identities and remaining separate runtime gates.

### Three roles and the current source constraint

| Role | Responsibility and boundary |
|---|---|
| Isolated signer | Existing system-service entrypoint enforces distinct non-root signer identity, no CAP_SYS_PTRACE, no tracer, core dumps disabled and `PR_SET_DUMPABLE=0` before secret resolution. Preserve these controls. |
| Authenticated supervisor observer | Observe only the owner-selected signer instance with independently qualified OS visibility; authenticate observation provenance and lifetime. It is not the requesting principal and must not perform the requester's handshake. No such production observer transport is currently admitted. |
| Actual handshake requester | Unprivileged process running the canonical healthcheck. Its effective UID/GID maps through authenticated current-generation `peer_policy/uid_to_principal`; the signer attests the actual connecting peer. Neither012, work subject nor supervisor identity substitutes. |

`reddog_external_signer_os_observer._validate_policy` currently requires the
observer's actual UID/GID to equal `policy.requester_uid/gid`. The default
`reddog_external_signer_lifecycle_admission._verified_admission_values` calls
that observer and the healthcheck sequentially in one process. Running this
unchanged path in a supervisor either rejects requester identity or changes the
connecting principal. Merely adding policy fields cannot resolve this constraint.
Do not override backend identity, relabel the supervisor, grant requester ptrace
access, or relax signer dumpability to obtain a positive result.

Keep the current public observer and audit injection behavior. A future distinct
supervisor path must reuse the kernel observation primitives under an explicit
observer-identity contract, then authenticate their result at the existing
lifecycle owner. It must not pretend to be the default requester-local observer.

### Source and ownership

`reddog_signer_system_service_manifest_selection_loader.py` remains the
authenticated root-owned configuration/generation owner, and
`reddog_signer_system_service_entrypoint.py` remains the isolated signer launch
owner. This code ownership does not make the signer process its own supervisor.
Public startup still has unavailable production dependencies. No installed
signer-specific unit, systemd version or privileged observation policy was
observed. Keep service startup and observation as separate process roles.

Choose read-only observation from an authenticated local systemd **system**
manager for an explicitly owner-selected, already-loaded service unit. Extend
the existing root-owned config through a versioned schema only when implementing;
exact v1-v4 schemas have no unit selector and must preserve compatibility and
unknown-field rejection. Never guess a unit, accept caller-selected PID/unit,
fall back to the user bus, or start/stop/reload/LoadUnit a service.

Require a qualified simple/exec main-process service, active/running state,
current nonzero `MainPID` and nonempty `InvocationID`, not historical ExecMainPID
or a control process. Pin the process with pidfd; verify unit/invocation through
`GetUnitByPIDFD` and reject manager-owner/lifetime changes. That method's systemd253
introduction does not prove deployed support. Systemd metadata and a pidfd do
not grant procfs visibility or authenticate a later observation handoff.

| Existing policy field | Expected provenance and binding |
|---|---|
| `pid`, `expected_process_start_identity` | Owner-selected current MainPID, boot ID/start ticks, pinned lifetime and repeated manager/unit/invocation checks. |
| `expected_signer_uid/gid` | Authenticated owner signer identity, checked against actual process credentials and kept separate from observer and requester roles. |
| `requester_uid/gid` | Actual healthcheck process effective identity and owner-selected peer mapping. These fields retain requester-local meaning; they are not supervisor identity fields. |
| `expected_executable`, `expected_executable_device/inode` | Current authenticated packet argv[0], owner-authorized launch path/argv and descriptor metadata compared with procfs before/after. This is not code-content attestation. |
| `socket_path`, `expected_socket_uid/gid/mode` | Current selected packet/config and explicit owner policy, protected ancestry, compatible namespaces and actual metadata. Fixture0600 is not production access policy. |
| `authority_receipt_id/source_id` | Future canonical issuer binding owner/config/generation/packet/session plus observer and signer-instance identities. Existing strings, unkeyed digests and serialized receipts confer no authority. |

### Authenticated handoff and canonical consumption (specified, not wired)

The future producer belongs to the existing external-supervision owner above.
The consumer belongs to `reddog_external_signer_lifecycle_admission.py`: verify
the authenticated observation before `_verified_admission_values` accepts it
and before `_make_admit` issues a local capability. Keep the actual healthcheck
in the requester process. This names extension seams, not an implemented verifier
or a new parallel authority registry.

The current `_verified_os_policy` checks the shape of an injected
`ExternalSignerOsPolicyAuthorityBoundary.require` result; it does not authenticate
a canonical supervisor. `VerifiedExternalSignerOsPolicy` construction or the
observation receipt's digest verifier cannot close that gap. Implementation must
bind a concrete producer/consumer pair and independently verify authenticated
transport, owner-selected issuer identity and replay state. The existing
verified-outcome root-authority signing service is not an observation authority;
its presence does not admit reuse of its socket or keys for this purpose.

One attempt must correlate authenticated observer issuer identity, intended
requester UID/GID/principal, accepted signer profile/public key/epoch, manifest,
generation/revision, config and raw digests, packet/session, manager/unit/invocation,
PID/start/boot identity, executable, namespace views, socket VFS identity and
concrete socket cookie. Bind a fresh requester-generated challenge/attempt ID,
observation time and expiry to that exchange and the actual handshake result.
Reject mismatches; never infer expected identities from the offered observation.
Wire format, transport mechanism, trust provisioning, bounded deadlines and
replay-store ownership must be frozen and reviewed before implementation.

Lifecycle capabilities are sealed, registered, process-local objects; their
copy/serialization hooks reject. Do not mint one in the supervisor and send its
JSON to the requester. Authenticate the observation in the requester process,
then issue and consume the local capability through
`consume_verified_external_signer_lifecycle_admission`. A cross-process resident
would require its own explicit verified handoff; current handles are not portable.

`require_default_dependencies=True` currently means exact captured original
observer/healthcheck and no clock overrides in the private registry. A future
authenticated-supervisor route cannot pass this by callback injection, alias,
boolean, public attribute or receipt label. Qualify a deliberate canonical mode
in that existing registration/consumer path, preserving current default/audit
semantics and rejection behavior. Do not silently broaden the meaning of default.
Resident bootstrap and `GovernedValveUseTimeAuthorityResolver` are downstream
integration seams only; their supplier and lifecycle consumption are not wired.

### One-attempt lifetime

1. Load authenticated owner/config/generation and independently select requester
   and accepted profile/public key/epoch. The current unprofiled resident
   generation collector is insufficient for that selection.
2. Authenticate observer transport/issuer and qualify actual procfs visibility
   without giving the requester additional privileges. Check compatible
   PID/user/network/mount views; do not reinterpret IDs or paths across namespaces.
3. Keep manager connection and pidfd alive across authenticated observation and
   the requester's actual handshake. Recheck generation/config, invocation,
   process/executable/credentials and socket before proof issuance. Restart, exit,
   PID reuse, exec, replacement, rotation, denied visibility or owner drift reject.
4. Consume only the locally issued capability, once and before expiry, after
   earlier queue/work checks. Preserve rejection-before-consumption for malformed
   identities/foreign boundaries and spending on valid owned identity mismatch.
   Release all resources on every result. Revalidate at use if time has passed;
   observation cannot prevent later exit/exec. The effect-bound lease is separate.

A connected-peer alternative remains more invasive: the current client closes
each roundtrip and discards peer PID. A preserved connection alone would still
not prove current executable, rightful service ownership or procfs visibility.
The external-manager design is retained with the missing handoff made explicit.

### Socket ownership prerequisite — source defect, not a live incident

**Historical defect repaired by PR1922; this is not an outstanding inode fix.**
The old pathname-inode/FD-inode equality and fake202/202 assumption are gone.
The existing observer now uses exact bounded VFS/socket association and concrete
cookie/namespace continuity. PR1923 main `5578f7bd` additionally records a readable
same-UID child and a live nondumpable child rejected with real permission errors.
Its254 candidate cases passed in PR/main;252 parent cases were preserved. This
qualifies the recorded permission boundary, not production cross-UID supervision.
See [socket contract](#connected-socket-ownership-observation--2026-09-27) and
[future connected acceptance](tests/README.md#supervisor-requester-connected-acceptance--2026-09-27).

Before any issuer implementation, freeze the transport/verifier/replay owner and
deployment observation policy above. Then qualify the connected producer-to-local
lifecycle consumer with real requester correlation; do not add disconnected
positive policy fixtures or duplicate the existing requester-mismatch test.
All seven native trust reasons and `authoritative_use_lease=None` remain.

Primary source references retained from the original design:
[systemd manager](https://raw.githubusercontent.com/systemd/systemd/v256/man/org.freedesktop.systemd1.xml),
[pidfd lifetime](https://man7.org/linux/man-pages/man2/pidfd_open.2.html),
[Linux pathname bind](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/unix/af_unix.c),
[socket FD naming](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/socket.c),
[diagnostic VFS association](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/unix/diag.c).

## Healthcheck requester selection — 2026-09-27

Only `requester_principal_id=None` requests default selection. The existing
healthcheck reuses `rehydrate_peer_credential_policy` and maps the connecting
process's effective UID, requiring its effective primary GID when `allowed_gids`
is nonempty. Missing effective-ID APIs, OS read errors, unknown UIDs and denied
GIDs return `signer_healthcheck_requester_invalid` before connector invocation.
An empty GID allow-list imposes no GID restriction. Real IDs, supplementary groups
and the first configured policy entry do not select the requester.

Valid explicit requesters bypass local inference; malformed explicit values do
not fall back. The existing server must still match the requested principal to
its kernel-attested peer. Local inference assumes compatible user namespaces
and unchanged credentials before connect; it is a routing hint, not attestation,
delegation or authenticated expected-requester provenance.

### Resident handoff ownership (specified, not wired)

The existing signer-owned `peer_policy/uid_to_principal` remains the mapping
owner. A same-process lifecycle producer must select from the authenticated
current-generation config and the actual handshake process's effective identity.
If another process performs the handshake, the resident process's UID cannot
substitute: the admitted external lifecycle owner must supply the independently
bound requester expectation and authenticated observation for each attempt; the
requester-local lifecycle owner must issue the opaque handle after verification.
Never derive the expectation from the offered receipt, external012 or work subject.

Thread that existing-owner supply through resident bootstrap into
`GovernedValveUseTimeAuthorityResolver`, after early work/queue checks. Reuse the
accepted signer profile and correlate manifest, generation/revision, config/raw
digest, run-packet and session; consume once with
the current `require_default_dependencies=True` contract. A future authenticated
supervisor mode needs deliberate canonical registration as specified above;
it cannot masquerade as the current default observer. This is a future integration contract.
The healthcheck fix does not fill lifecycle's mandatory requester parameter or
wire this supplier. All seven resident trust reasons and the absent effect-use
lease remain. No new profile field, identity registry or launch API is introduced.

## Lifecycle default-dependency requirement — 2026-09-27

`consume_verified_external_signer_lifecycle_admission` adds keyword-only
`require_default_dependencies: bool = False`. Omission/False retains the current
audit/one-use behavior. Non-bool values reject before consuming. With True,
the captured private registry must record the original default observer and
healthcheck callables plus no wall/monotonic overrides. Explicit original
callables and explicit None clocks qualify; wrappers/replacements and any
non-None clock value (including falsey values) do not. Rebinding module aliases
after factory creation cannot promote a replacement or demote captured defaults.
Unqualified selection raises `external_signer_lifecycle_default_dependencies_required`
before consuming the handle. Malformed identity and foreign-boundary guards still
precede consumption; a valid owned identity mismatch still spends the handle.

Factory signature, audit receipt schema/digests and false authority flags remain
unchanged. No public property, serialized label or caller declaration promotes
selection. The stricter flag requests an additional check; it cannot grant trust.
This metadata is not full manifest/OS/generation/cryptographic provenance,
continuous supervision or a hostile-Python boundary. No resident reason is
removed and no effect lease is issued; resident/bootstrap wiring remains separate.

# OpenClaw Bridge Interface

## Governed use-time supplier admission

`GovernedValveUseTimeAuthorityResolver.resolve(...)` requests current-generation
evidence only when signature re-verification succeeds and earlier artifact,
queue, recorded-authority and binding checks have no rejection. Rejected inputs
skip the injected trusted clock and generation verifier, retain all missing-anchor
diagnostics, and return no generation receipt. `signed_authority_reverified` still
reports the signature result independently. Generation evidence never supplies an
authoritative effect-use lease. See the existing execution-valve roadmap section.

## Public RedDog Lick PoC

`PublicSessionGate.open_lick_encounter(...)` accepts the exact open-source,
non-biometric consent/profile shape for the `autopost` public surface and
returns a bearer plus random challenge. `complete_lick_challenge(...)` consumes
that challenge once and returns a provisional `reddog.lick.receipt.v1` plus the
existing turn nonce. Lick-bound turns reject until challenge completion.

The bearer and challenge are not identity or capability material. The receipt
is unsigned, states that identity and human presence are unverified, states
that no biometrics were collected, and always grants `none` authority. Existing
origin/subject binding, quotas, idle/absolute expiry, replay defense,
withdrawal, and effect ceiling remain authoritative. The optional HTTP router
adds `lick` and `challenge` operations but remains unmounted and undeployed.

Canonical product and deployment boundaries are in
`extensions/reddog/docs/REDDOG_LICK_CONNECTION_HANDSHAKE.md` and
`extensions/reddog/docs/REDDOG_PUBLIC_SURFACE_ADMISSION.md`.

## HoloIndex runtime interface

`run_holoindex_postmerge_runtime_once(...)` owns one clean exact-main maintenance lifecycle;
`query_holoindex_owner(...)` and `GenerationBoundHoloIndexQueryAdapter.query(...)` own reads.
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
[docs/HOLOINDEX_RUNTIME.md](docs/HOLOINDEX_RUNTIME.md).

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

## RedDog advisory bridge support

`reddog_advisory_bridge_support.py` owns only deterministic, bounded input
normalization, audit telemetry projection, prompt assembly, and review-packet
formatting for `scripts/advisory_model_once.py`. Provider calls, environment
access, redaction admission, and stdin/stdout lifecycle remain in the one-shot
script. The extraction adds no model, worker, repository, or fallback authority.

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
## Exact-request signer admission
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
## Authenticated RedDog conversation scope

`authenticate_conversation_scope()`, create/resume/advance, the existing-scope binder, durable request journal, and `reserve_current_generation_resident_conversation_request(...)` form the authenticated AgentDB existing-conversation path.
It consumes opaque authority, verifies current record/revision/turn lineage, and returns content-free evidence without reserving conversation CAS or granting effects.

`resolve_resident_conversation_new_scope_request(...)` plus `create_current_generation_resident_conversation_scope(...)` form the separate empty-ID TURN path. Exact v2 intent/request/grounding/FoundUp bindings precede the current-generation E0 lease; signed session identity fences nonce divergence and exact authenticated recovery is the only replay accepted.

`resolve_current_generation_resident_conversation_first_turn(...)` atomically obtains two one-use FoundUp authority siblings, creates/exactly recovers scope-schema-v4 E0 with an immutable signed source/resolved request commitment, and stores explicit v2 `RESOLVED_INITIAL_TURN` digests in the existing journal; replay derives the ID before exact four-key lookup, atomically consumes its verified authority, and validates the retained E0 receipt through the current signed revision chain.
`authenticate_signed_conversation_scope()` remains the production credential source; legacy HMAC is test/backward-compatible only. `prepare_conversation_work_context()` and proposal promotion remain later, independently authorized stages.
These aggregates expose no traffic, handler, CAS, model/worker, or work authority; see `docs/clarity/REDDOG_RESIDENT_CONVERSATION_*_PHASE1.md`, including `REDDOG_RESIDENT_CONVERSATION_FIRST_TURN_RESOLUTION_PHASE1.md`, for exact locking, expiry, failure, and recovery contracts.

## Public API
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

### Verified-outcome authority, signing and memory

The [complete contract](../../../docs/operations/RSI_SWARM_DISPATCH.md#verified-outcome-api-reference) retains the root, signer, publication and memory boundaries previously listed here. The [activation recovery checkpoint](../../../docs/operations/RSI_SWARM_DISPATCH.md#activation-recovery-checkpoint--2026-09-14) records the latest local layer and the unimplemented acceptance transaction contract.

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

### FoundUpJob intake and create_foundup lineage

`dispatch_foundup()` requires existing commander authority before mutation intake. It accepts a plain `metadata.genesis_envelope` (compatible legacy `payload.genesis_envelope` only if unambiguous), revalidates a detached copy and queues the frozen envelope with tenant/session/FoundUp identity. Malformed declared data and conflicting parsed targets return `NOT_READY`; bare explicit builds retain their queue behavior. Draft public authentication and `requested_by` are not commander authority. Jobs remain dry-run with no fabricated execution evidence, creation mode or typed digest. Separately, `FoundUpJob` exposes `creation_mode`, `genesis_envelope_digest`, and `scaffold_contract_digest` through `create_job()` and round-trip serialization. The admitted `create_foundup` route requires `new_scaffold`, explicit dry-run policy, planner-compatible digests and `payload.genesis_envelope`; WRE never aliases that route to build/extract. This handoff does not grant scaffold or worker admission.

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
- `execute_linkedin_action(action="digital_twin", ...)` forwards all above params to `LinkedInActions.run_digital_twin_flow(...)`. Direct `like_post`/`like_reply` truthy dry-run now returns a target preview before browser import/construction; see [exact fields and limits](../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-dry-run-repair--2026-09-22). Session truthy dry-run also returns configuration before browser access ([fields and limits](../../platform_integration/linkedin_agent/docs/LINKEDIN_REVIEW_WORKFLOW.md#rsi-session-preview--2026-09-22)). Agentic delegation and omitted/false live behavior are preserved; other routes remain separately qualified.

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

### OpenClaw DAE and ExecutionBundle

The bounded DAE loop, WSP 77 operating contract, example, and field contract
are preserved in
[`docs/OPENCLAW_DAE_EXECUTION_BUNDLE_INTERFACE_ARCHIVE.md`](docs/OPENCLAW_DAE_EXECUTION_BUNDLE_INTERFACE_ARCHIVE.md).
0102 remains architecture authority; OpenClaw remains a bounded executor.

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

Authorization and acquisition (repair 2026-09-23):
- Unmatched/unresolved commands and unauthorized mutations acquire neither collaborator. `list`/`status` and authorized launch/start/run/stop acquire only broker; tail/follow/live status acquire only observer.
- `launch`/`stop` require `012` authority. Exact responses/callbacks and required creating-getter semantics remain; [fixed regression evidence](tests/README.md#rsi-adapter-acquisition-and-linkedin-previews) passes28 after26 baseline failures. Required getters can construct runtime components, so whole-command effect freedom is not established.

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

### OpenClaw Supervisor Contract

Canonical 0102 lifecycle owner:
- runtime id: `openclaw_supervisor`
- implementation: `src/openclaw_supervisor.py`
- broker launch wrapper: `scripts/launch.py`

Current explicit states: `BOOT -> PREFLIGHT -> OBSERVE -> TRIAGE -> PLAN -> EXECUTE -> VERIFY -> REMEMBER -> ESCALATE -> IDLE_WATCH`.
Current operational rule:
- the supervisor owns the enabled self-audit loop and exposes [per-attempt scan status](../../infrastructure/wre_core/INTERFACE.md#self-audit-scan-observations) separately from event count
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
- `run_skill_scan(skills_dir, report_dir=...)` owns private report/TMP files per call,
  validates before publishing a mutable latest diagnostic, and fails closed on errors.
  [Full scanner contract](README.md#skill-safety-gate-cisco-skill-scanner): `_ensure_skill_safety(force=False, *, details=False)` returns `bool`; literal `details=True` returns local `(bool, str)`. The process consumer validates both fields; malformed results raise `TypeError`/`ValueError` before downstream execution. Latest diagnostics and policy-drift rejection remain; no effect/promotion authority.
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
| `OPENCLAW_SKILL_SCAN_TTL_SEC` | No | Retained (`900`); workspace TTL reuse disabled, every call scans |
| `OPENCLAW_SKILL_SCAN_ALWAYS` | No | Retained; every guard call scans even with `0`/`force=False` |
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
- `openclaw_dae.py` is currently `1580` lines: inherited WSP 62 hard-limit debt; the facade split remains incomplete
- execution-plane resolution now matches `WSP_97`: resolve intent -> gate -> plan -> route -> validate -> remember

## Runtime Supervision Commands

OpenClaw can now read the DAEmon live ledger for itself and broker-managed DAEs:

- `tail openclaw`
- `status openclaw live`
- `tail pqn research`
- `status pqn research live`
- `tail holodae`

These commands request ledger reads and acquire only the observer. Required observer construction may still change runtime state; the inert regression evidence above does not certify whole-command effect freedom.

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


### RedDog Correspondence Sender Boundary

```javascript
// Load the checked-in dependency-free host source in the operator/runtime isolate.
// It exports:
buildRecipientPreflightReceipt(...)
prepareRecipientPreflightReceipt(...)
executeSenderBoundary(...)
```

Canonical host:
`modules/communication/moltbot_bridge/host/reddog_correspondence_sender_boundary.mjs`

This is the mechanical provider-call owner for correspondence. A composer, cached
state capsule, draft, prompt instruction or prior provider success cannot grant send
authority. The host adapter binds one fresh `SEND` receipt to the exact provider
operation, scope/purpose, identity IDs, To/CC/BCC roles and addresses, content digest,
draft/reply/thread identifiers and fresh Sent coverage.

Immediately before submission, `executeSenderBoundary(...)`:

1. rejects missing, `BLOCK`, malformed, expired or transaction-mismatched receipts
   before any provider mutation;
2. re-reads provider Sent coverage and rejects a changed watermark/coverage digest;
3. for `send_draft`, reads the exact draft and rejects recipient, body, message-ID or
   thread-ID drift before provider submission;
4. invokes the injected provider submission exactly once only after all checks pass;
5. reads the exact Sent message and requires exact message/thread identity and
   To/CC/BCC equality before returning `VERIFIED_SENT`.

The same boundary operation enum covers `send_email`, `reply`, `send_draft` and
`delivery_repair`; callers do not implement alternate send helpers outside it.
A provider exception returns `PROVIDER_STATE_UNKNOWN` and requires Sent
reconciliation before retry. Missing/failed provider readback returns
`PROVIDER_SENT_INTEGRITY_INCIDENT`; it never authorizes automatic resend.

The adapter is dependency-free ECMAScript so the connected operator can load the
exact verified `main` source into its V8 tool transaction and wrap Gmail calls.
Its Node contract test is:
`modules/communication/moltbot_bridge/tests/test_reddog_correspondence_sender_boundary.mjs`.


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
