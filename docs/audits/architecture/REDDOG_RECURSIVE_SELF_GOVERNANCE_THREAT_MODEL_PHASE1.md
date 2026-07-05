# REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL_PHASE1

Status: DECISION-ONLY threat model (docs + static tests only; no runtime code, no verifier, no keys, no wallet, no chain, no permission change).
Base: c7bb3ff523a790f03b4dd5514e36e9f4af1c9c20 (origin/main HEAD at write-time)
Author-role: 0102 architect (threat-model author, not implementer)
Ratifies-on-top-of: docs/contracts/REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE1.md (ratified contract #928 -- "the contract" / "#928" below)
Anchors: docs/audits/architecture/REDDOG_PRINCIPAL_IDENTITY_DELEGATION_AND_REWARD_CONTRACT_PHASE1.md (audit #926 -- "the audit" / "#926" below)
Sequence position: step 2 "threat-model / static tests" (the "C" decision PR) of the audit Section 12 ratified sequence.
WSP: WSP_97 (truth boundary), WSP_50 (pre-action: ratify, do not re-derive), WSP_48 (Sec 8.3), WSP_96, WSP_100, WSP_58, WSP_54, WSP_46, WSP_64.

Truth-label legend (WSP_97):
- OBSERVED                    = read directly from #926/#928 or cited source at the named location
- INFERRED                    = concluded from OBSERVED evidence, not itself a literal
- SPECIFIED_NOT_IMPLEMENTED   = proposed by this doc; does NOT exist in code yet
- NEEDS_VERIFICATION          = asserted elsewhere, not confirmed here

---

## A. Purpose and relationship to #928 (WSP_50: ratify, do not re-derive)

Purpose: build the recursive-self-governance threat model ON TOP of the ratified
principal-identity and delegation contract (#928), certifying the guards a future
verifier and its prerequisite key-isolation contract MUST honor, and locking the
implementation order so no signature verifier is built before its signing key is
isolated. This slice is docs + static tests ONLY.

Relationship to #928 (WSP_50):
- This document does NOT re-derive the contract. #928 already froze the wire-level
  schema (RedDogPrincipalIdentity, RedDogDelegatedWorkAuthority, SignedReceipt), the
  canonicalization form, the signer-per-record-kind rule, the nonce/expiry rules, the
  revocation-first verification order, and the CoR that closed ten adversarial rounds.
  Those are OBSERVED substrate here and are cited, not restated.
- What this document ADDS on top of #928: (1) the seven governance guards G1..G7 stated
  as invariants the verifier must enforce; (2) the recursive-self-governance and
  implementation-hardening threats that arise once RedDog is execution-capable and could
  act on itself; (3) an explicit E0-before-E1 sequence lock that makes signing-key
  isolation a prerequisite of the signature verifier, not an afterthought.
- WSP_64 (extend, do not duplicate): where #928 already owns a control, this doc points
  to it; it does not re-specify it. The guards below are the #928 invariants named as
  guards so a test can assert their presence and a verifier can honor them.

The single certifying sentence (OBSERVED from the audit and contract Section 0, verbatim):

    Role text is never authority.
    Signed identity + fresh permission + scoped delegation is authority input.

---

## B. Seven governance guards (G1..G7) [SPECIFIED_NOT_IMPLEMENTED]

These seven guards are the #928 invariants named as guards. Each is derived from a
contract section (cited). A future verifier MUST enforce all seven; the E0 key-isolation
contract and the E1 verifier (Section E) MUST honor them. Labels are literal G1..G7.

- G1: Signed identity required -- role/prompt text is never authority (integrity is not
  authenticity). A pasted "I am 012" is inert prompt text. Authority input requires a
  signature over the canonical payload, not a role string and not a hash. (Anchors #928
  Section 0, Section 2; #928 Addendum B "RedDog prompt text" row.) [SPECIFIED_NOT_IMPLEMENTED]

- G2: The delegation instrument (RedDogPrincipalIdentity) is PRINCIPAL-signed, never
  RedDog-signed -- no self-mint of scope. The identity record that confers repo_scope /
  foundup_scope MUST verify against principal_public_key; a RedDog-signed identity record
  is invalid. A RedDog cannot sign its own scope grant. (Anchors #928 Section 2
  signer-per-record-kind, Section 5 principal-authentication basis, Section 11 step 2a;
  #928 Addendum B "RedDog self-mint" row.) [SPECIFIED_NOT_IMPLEMENTED]

- G3: Fresh permission snapshot bound into the signed payload; scope is a ceiling
  intersected with it. permission_snapshot_digest is one of the INCLUDED signed fields;
  the effective authority is the intersection of the identity's scope ceiling and a
  FRESH RepoPermissionProbeSnapshot for that principal. Scope can only NARROW, never
  widen, actual permission. A stale, missing, or insufficient snapshot fails closed.
  (Anchors #928 Section 5 no-escalation rule, Section 7 permission-snapshot binding.)
  [SPECIFIED_NOT_IMPLEMENTED]

- G4: Explicit repo_scope + foundup_scope; empty = deny; fail-closed on unpopulated
  owner_dae for writes. repo_scope and foundup_scope are explicit allowlists; an empty
  list is denial, not a wildcard. A write-bearing work order whose target foundup_id has
  an unpopulated owner_dae has no ownership proof and MUST fail closed. (Anchors #928
  Section 1a repo_scope/foundup_scope, Section 6 foundup_scope binding + owner_dae tie.)
  [SPECIFIED_NOT_IMPLEMENTED]

- G5: Signed receipts only -- unsigned = not in chain = no reward; reward_account is not
  custody, reward_account is not repo authority. A receipt lacking a valid signature by
  the delegated reddog_id is NOT a member of receipt_chain and confers NO reward.
  Hash-linkage (integrity) is insufficient; authenticity (signature) is required.
  reward_account never implies fund custody and never implies repo authority. (Anchors
  #928 Section 8 receipt signing, Section 10 reward-account boundary separation invariants.)
  [SPECIFIED_NOT_IMPLEMENTED]

- G6: Revocation-first verification + single-use durable nonce + bounded TTL (anti-replay,
  anti revoked-but-unexpired). The verifier checks revocation BEFORE accepting a
  signature: a revoked reddog_id / fingerprint is rejected even when the signature verifies
  and the record has not expired. Nonces are durable single-use, consumed atomically ONLY
  after signature success; TTLs are bounded and non-null; expired = reject. (Anchors #928
  Section 3 nonce/expiry, Section 9 revocation precedence, Section 11 step 1 + step 3.)
  [SPECIFIED_NOT_IMPLEMENTED]

- G7: RedDog never self-grants / never self-approves authority broadening. Broadening
  execution authority is a high-risk change requiring WSP_96 3-agent consensus with 0102
  veto, and MUST NOT be self-approved (WSP_48 Sec 8.3 "0102/DAE proposes, does NOT
  self-approve"; WSP_100 payout_ready/cabr_ready hard-false, no agent self-approves tier
  escalation). At the instrument level, a RedDog-signed identity is invalid (only a
  principal signature grants scope). (Anchors #928 Section 20 hard invariants; audit
  Section 1 WSP bindings.) [SPECIFIED_NOT_IMPLEMENTED]

---

## C. Core principle: integrity is not authenticity

Stated verbatim (frozen):

    integrity is not authenticity

A SHA256 hash proves tamper-evidence (integrity): it shows the bytes were not altered
after the hash was taken. It does NOT prove who authored the bytes. Only a signature over
the canonical payload, verifiable against a known public key, proves authorship
(authenticity).

Tie to the OBSERVED audit finding (#926 Section 2a): the work-order spine has scope FIELDS
but ZERO signatures -- "every digest is a SHA256 hash = integrity (tamper-evidence), NOT a
signature (authenticity). authenticated_principal is an UNSIGNED string." The spine digests
are hashes, not signatures. Under G1, a hash may never be passed off as authority; a digest
chain that is self-consistent is still not authenticated. Every guard in Section B rests on
this distinction: the guards convert hashed CLAIMS into signed AUTHORITY INPUT.

---

## D. Recursive self-governance + implementation-hardening threats [SPECIFIED_NOT_IMPLEMENTED]

Once RedDog is execution-capable and could act on itself, new threat classes arise beyond
#928's identity/replay matrix. Each subsection below is a labeled threat the E0 contract and
E1 verifier MUST close. These are proposed controls (SPECIFIED_NOT_IMPLEMENTED); none is
implemented in this slice.

### D1. Key isolation / supply-chain poisoning

The signing and verification context MUST NOT load plugin code, Skillz code, or arbitrary
dependency code. A poisoned plugin, Skillz, or transitive dependency loaded INTO the
signing process could exfiltrate the private signing key or forge a fully-VALID signed
authority -- defeating every guard downstream, because a signature produced with the real
key verifies. Signing-key isolation is therefore a PREREQUISITE, not an afterthought:
- the key material lives in a host vault isolated from loaded plugin/Skillz/dependency code;
- the process that touches the key loads no plugin/Skillz/arbitrary dependency code;
- dependencies in the signing/verify path are pinned and hash-verified; Skillz reaching the
  signing path require a WSP_95 prototype->production promotion gate RedDog cannot
  self-approve and a WSP_96 supply-chain gate that fails closed.
This is the reason E0 (Section E) must land BEFORE E1: an isolated key is a precondition of
a trustworthy verifier. (Extends #926 Section 6 off-chain boundary and #928 Section 4d
private-key invariant to the LOADED-AND-EXECUTED code surface.) [SPECIFIED_NOT_IMPLEMENTED]

### D2. Constant-time compare / no timing leak

Signature and digest comparisons in the verifier MUST use a constant-time compare; the
comparison MUST be constant-time to avoid a timing leak. A non-constant-time comparison
(e.g. a byte-by-byte early-return equality check) leaks, via timing, how many leading bytes
matched, letting an attacker recover a secret or forge a matching value one byte at a time.
The verifier MUST use a constant-time comparison primitive (e.g. secrets.compare_digest) for
every signature/digest check, and MUST NOT include the expected material in any error
string, log, receipt, telemetry, or Copy-MD surface. (Derived from
#928 Section 2 canonicalization + the audit's HMAC-verify discipline; hardens E1.)
[SPECIFIED_NOT_IMPLEMENTED]

### D3. Concurrency / TOCTOU

Nonce consume-after-verify and snapshot-freshness checks MUST be atomic. A check-then-use
race allows: (a) double-spend of a nonce, if two acceptances both observe the nonce as
unconsumed before either inserts it; or (b) a stale snapshot slipping through, if the
permission snapshot is validated at T0 but consumed at T1 after the world mutated
(permission revoked, denied_path added, valve_state flipped). The verifier MUST evaluate
the nonce consume and the freshness/permission checks in a single atomic critical section
(check-and-insert in one transaction; re-check external mutable state at the write boundary
with optimistic-concurrency / compare-and-swap), failing closed on any intra-pipeline drift.
(Generalizes #928 Section 3 "atomically consume" and Section 11 to concurrent, continuous,
multi-instance operation.) [SPECIFIED_NOT_IMPLEMENTED]

### D4. Economic gaming

Economic gaming -- reward and receipt manipulation -- MUST be closed by signed-receipts-only plus chain linkage
plus reward_account match. Concretely: self-dealing receipts (accrue reward to an account
the same principal controls), replayed receipts (resubmit a prior signed receipt), and
reward_account swap (bind a receipt to a different payout account than the identity's) are
all defeated by requiring (a) each receipt be SIGNED by the delegated reddog_id, (b) each
receipt be hash-linked in order via prev_receipt_hash, and (c) the receipt reward_account
match the identity reward_account when non-null. Reward accrual is bound to signed receipts,
never to a model claim; settlement stays FUTURE_BLOCKED. This economic gaming class is
closed by signed-receipts-only + chain linkage + reward_account match. (Anchors #928
Section 8, Section 10; G5.) [SPECIFIED_NOT_IMPLEMENTED]

### D5. DoS / fail-open

Under load, store-unavailability, or ambiguous time, the system MUST fail CLOSED. There is
no "allow on doubt" path. If the nonce store is unavailable, the permission snapshot cannot
be resolved, the revocation list cannot be read, or the time gate is ambiguous, the verifier
MUST reject (deny), never fall open to allow. Flooding the permission probe, nonce store, or
oracle MUST produce sustained denial, not a fail-open bug, and MUST NOT let RedDog self-clear
an alarm on sustained fail-closed. (Anchors #928 Section 3 "Fail-closed on expiry ... no
allow-on-doubt path" and Section 11 "any miss = fail-closed".) [SPECIFIED_NOT_IMPLEMENTED]

---

## E. E0/E1 sequence lock [SPECIFIED_NOT_IMPLEMENTED]

Sequence lock (required, explicit):

    E0 before E1.

- E0 = REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1 (the signing-key isolation contract).
- E1 = REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1 (the work-order signature verifier).

Rule: REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1 (E1) is BLOCKED until
REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1 (E0) lands. E1 MUST NOT be started, and no
verifier code MUST be opened, until E0 has landed. Building the verifier before the signing
key is isolated is forbidden: a verifier is only as trustworthy as the isolation of the key
it depends on (Section D1). E1 is blocked until E0 lands.

Verifier constraints that E0 MUST establish and E1 MUST honor:
- (i) the verifier MUST NOT load plugin / Skillz / dependency code in the signing context
  (key isolation, Section D1);
- (ii) the verifier MUST use constant-time comparison for every signature/digest check
  (no timing leak, Section D2).

Ratified sequence (now, in order):
1. contract -- #928 principal-identity and delegation contract (DONE).
2. this threat model (C) -- REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL_PHASE1.
3. E0 -- REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1 (signing-key isolation contract).
4. E1 -- REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1 (work-order signature verifier).
5. signed receipts -- signed receipt chain replacing unsigned hash-linked receipts.
6. reward mapping -- bind signed receipt -> reward_account (settlement FUTURE_BLOCKED).
7. authority broadening -- WSP_96 3-agent consensus + 0102 veto gated; never self-approved.

---

## F. Truth Boundary Checklist (contract invariants for THIS slice)

- DOCS_AND_STATIC_TESTS_ONLY  -- deliverable is this document plus one static doc-guard test.
- NO_RUNTIME_CODE             -- zero runtime logic authored in this slice.
- NO_VERIFIER_IMPLEMENTATION  -- verifier constraints are specified; no verifier is built.
- NO_KEYS                     -- no key generated, no key material, no signing code.
- NO_WALLET                   -- no wallet created or bound; reward path FUTURE_BLOCKED.
- NO_CHAIN                    -- no on-chain write; no chain library.
- NO_PERMISSION_CHANGE        -- no grant/revoke; permission model referenced only.

---

## G. Chain-of-refutation (CoR) rounds

Adversarial passes trying to defeat the guards (Section B) or the sequence lock (Section E).
Each round records the attack, the result, the tightening, and closure.

Round 1 -- "Skip E0 and build the verifier anyway."
- Attack: argue E0 (key isolation) is optional cleanup; build E1 (the signature verifier)
  first, isolate the key later.
- Result: SUCCEEDS at defeating the whole layer -- if the signing key is reachable by loaded
  plugin/Skillz/dependency code (Section D1), that code can forge a fully-VALID signature, so
  a "working" verifier accepts forged authority. The verifier is only as trustworthy as the
  key isolation beneath it.
- Tightening: Section E freezes "E0 before E1" as a hard sequence lock: E1 is BLOCKED until
  E0 lands, and E1 MUST honor constraint (i) no plugin/Skillz/dependency code in the signing
  context. Building the verifier first is forbidden. CLOSED.

Round 2 -- "Hash passed off as a signature."
- Attack: present a SHA256 digest chain (self-consistent, tamper-evident) as authority, or
  reuse the spine's evidence_digest / permission_snapshot_digest as if it authenticated the
  author.
- Result: SUCCEEDS against any reader that conflates integrity with authenticity -- exactly
  the OBSERVED audit finding (#926 Section 2a: spine digests are hashes, not signatures;
  authenticated_principal is an unsigned string).
- Tightening: Section C states verbatim "integrity is not authenticity" and G1 requires a
  signature (not a hash, not a role string) as authority input. A digest proves the bytes are
  unaltered, not who authored them; only a signature verifiable against a known public key is
  authority. CLOSED.

Round 3 -- "Fail-open under store outage."
- Attack: take the nonce store / permission-snapshot store / revocation list offline (or
  flood it), betting the verifier falls open to "allow on doubt" so a replayed or revoked
  packet slips through.
- Result: SUCCEEDS if any gate input defaults to allow when its store is unavailable or its
  time gate is ambiguous.
- Tightening: Section D5 (and #928 Section 3 / Section 11) mandate fail CLOSED on load,
  store-unavailability, or ambiguous time -- no allow-on-doubt path; Section D3 requires the
  nonce consume + freshness checks be atomic so a race cannot double-spend a nonce or slip a
  stale snapshot; Section D5 forbids RedDog self-clearing a sustained fail-closed alarm.
  Under outage the answer is deny, never allow. CLOSED.

Round 4 -- "RedDog self-signs its own scope, then self-approves broadening."
- Attack: a rogue RedDog emits a RedDogPrincipalIdentity with wide repo_scope/foundup_scope
  signed with its OWN key, then marks its own authority-broadening consensus as approved.
- Result: SUCCEEDS under any single-signer rule or any self-approval path.
- Tightening: G2 requires the delegation instrument be PRINCIPAL-signed (verified against
  principal_public_key); a RedDog-signed identity is invalid (#928 Section 2, Section 5,
  Section 11 step 2a). G7 forbids self-granting: broadening execution authority requires
  WSP_96 3-agent consensus + 0102 veto and MUST NOT be self-approved (WSP_48 Sec 8.3,
  WSP_100). Self-mint and self-approve both fail closed. CLOSED.

Round 5 (completeness sweep) -- "Is any guard or threat class unbound to a control?"
- Attempt: enumerate G1..G7 and D1..D5; confirm each guard cites a #928 section it derives
  from and each threat class names the control (E0/E1 constraint or #928 invariant) that
  closes it. No guard is left without an anchor; no threat class is left fail-open; the
  sequence lock binds E1 to E0. No residual bypass constructed in this pass. RESULT: no
  residual gap found.

Outcome: all constructed attacks (Rounds 1-4) were closed by the guards + the sequence lock;
Round 5 found no residual unbound guard or fail-open threat class. Nothing in this pass
satisfied the letter of the guards while still forging authority, replaying, self-granting,
or failing open.

---

## H. WSP_97 truth table (labels)

| Item | Label | Basis |
|------|-------|-------|
| Spine digests are hashes not signatures; authenticated_principal unsigned | OBSERVED | audit #926 Section 2a |
| Intake HMAC subject-not-payload + durable nonce is the proven pattern to generalize | OBSERVED | audit #926 Section 2b; contract #928 Section 2 |
| #928 froze schema, canonicalization, signer-per-record-kind, revocation-first order, CoR | OBSERVED | contract #928 Sections 1-11, 20, 21 |
| Guards G1..G7 (as verifier invariants) | SPECIFIED_NOT_IMPLEMENTED | this doc Section B (anchored on #928) |
| Threats D1..D5 and their controls | SPECIFIED_NOT_IMPLEMENTED | this doc Section D |
| E0 before E1 sequence lock | SPECIFIED_NOT_IMPLEMENTED | this doc Section E |
| No verifier, no keys, no wallet, no chain, no permission change in this slice | OBSERVED (this PR) | this doc Section F |

---

## I. Verdict + next slice

Verdict: RATIFY the seven guards G1..G7 as the verifier's invariants and the D1..D5 threats
as the recursive-safety hardening backlog; LOCK E0 before E1. This threat model is the
assertion target for the audit Section 12 step 2 (threat-model / static tests); the static
doc-guard test in this PR asserts its required content is present.

Next executable slice (only after this doc is finalized + reviewed): E0 --
REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1. E1 --
REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1 -- is BLOCKED until E0 lands, MUST NOT load
plugin/Skillz/dependency code in the signing context, and MUST use constant-time comparison.
No keys, no verifier code, no wallet, no chain, no permission change in this slice.
