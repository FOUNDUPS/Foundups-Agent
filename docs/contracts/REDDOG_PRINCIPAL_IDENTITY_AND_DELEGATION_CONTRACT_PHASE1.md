# REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE1

Status: RATIFIED CONTRACT SPEC (decision-only; no implementation, no keys, no chain, no wallet, no permission change).
Base: 8bb140f89ac8ca406176c6e3b5143593662d34dd (origin/main HEAD at write-time)
Author-role: 0102 architect (contract author, not implementer)
Ratifies: docs/audits/architecture/REDDOG_PRINCIPAL_IDENTITY_DELEGATION_AND_REWARD_CONTRACT_PHASE1.md (audit PR #926, squash 2555d9b68)
WSP: WSP_97 (truth boundary), WSP_50 (pre-action), WSP_54, WSP_58, WSP_96, WSP_100, WSP_46, WSP_48 (Sec 8.3), WSP_109

Truth-label legend (WSP_97):
- OBSERVED                    = read directly from source at the cited file:line
- INFERRED                    = concluded from OBSERVED evidence, not itself a literal
- SPECIFIED_NOT_IMPLEMENTED   = defined by this contract; does NOT exist in code yet
- NEEDS_VERIFICATION          = asserted elsewhere, not confirmed here

Relationship to predecessor (WSP_50):
This document does NOT re-derive the audit. It RATIFIES it. The schema below is the
audit's Section 4 frozen to wire-level truth. The threat model below is the audit's
Section 8 turned into a fail-closed matrix. The evidence anchors are the audit's
Sections 2-3. Where this contract cites file:line, those lines were re-verified live
against Base above (intake HMAC discipline at intake_auth_provider.py:413-430,505-528).

---

## 0. Purpose and scope

Purpose: turn the audit's SPECIFIED_NOT_IMPLEMENTED schema into a ratified contract
that leaves a future verifier ZERO ambiguity about what is signed, what is checked,
and what fails closed. This slice DEFINES the wire-level truth. It does NOT build it.

The single certifying sentence (OBSERVED from audit Section 0, verbatim):

    Role text is never authority.
    Signed identity + fresh permission + scoped delegation is authority input.

A pasted "I am 012" is prompt text. Under this contract that text confers nothing
unless a work packet carries a valid signature by the delegated RedDog identity
(rooted in the authenticated principal) AND matches a fresh permission snapshot
AND matches explicit repo + FoundUp scope AND is not replayed AND is not revoked.

Out of scope for THIS slice (enforced as contract invariants, see Section 20):
key generation, verifier code, signing functions, crypto-library calls, chain writes,
wallet creation, payout, and any permission grant/revoke. This is the document only.

---

## 1. Canonical schema (Item 1) [SPECIFIED_NOT_IMPLEMENTED]

Field names below are FROZEN by this contract. A future implementation MUST use these
exact names. "required" means the field MUST be present and non-null for the record to
be valid; "optional" means it MAY be null. Types are wire types (JSON), not language
types. No field may be added to the signed set without a new contract revision.

### 1a. RedDogPrincipalIdentity

| Field | Type | Req/Opt | Nullable | Allowed values / constraints |
|-------|------|---------|----------|------------------------------|
| principal_id | string | required | no | Stable id of the authenticated 012 principal. Format "github:<login>" or "intake:<subject>". MUST equal a token-verified subject at issuance (see Section 5 principal-authentication basis), never free text. |
| principal_provider | string (enum) | required | no | One of: "github", "intake_session", "intake_invite". No other value is valid. This names the token-verification basis that gated issuance (Section 5). |
| principal_public_key | string | required | no | The PRINCIPAL's PUBLIC key, encoded per Section 4a. The principal (NOT the RedDog) signs this identity record with the matching private half (Section 2, Section 5). Private half never appears (Section 4d). |
| principal_key_fingerprint | string | required | no | Public-only fingerprint of principal_public_key, derived per Section 4b. Used for display and principal revocation lookup. |
| principal_wallet | string | optional | yes | PUBLIC reward address only. NEVER a private key. May be null pre-OPO. Presence does NOT confer repo authority. |
| reddog_id | string | required | no | Stable public id of THIS RedDog instance. Format "reddog:<fingerprint-prefix>". Absent in code today (INFERRED from audit Section 3). |
| reddog_public_key | string | required | no | Instance PUBLIC key, encoded per Section 4. The private half NEVER appears in this record or anywhere (invariant, Section 4d). |
| reddog_key_fingerprint | string | required | no | Public-only fingerprint derived per Section 4b. Used for display and revocation lookup. |
| repo_scope | array of string | required | no | Allowlist of repo_full_name values ("owner/name") this RedDog may act within. Empty array = no repo authority. |
| foundup_scope | array of string | required | no | Allowlist of foundup_id values this RedDog may act for. Empty array = no FoundUp authority. |
| reward_account | string | optional | yes | Public account/handle rewards accrue to. NEVER implies repo authority. May be null. |
| owner_dae | string | optional | yes | The DAE that owns the RedDog's target FoundUp(s). Maps to foundup_registry owner_dae (OBSERVED unpopulated in data, audit Section 2e). Intended binding in Section 6. |
| revocation_policy | object | required | no | See Section 9. MUST carry ttl_seconds (integer), allowlist_bound (bool), kill_switch_ref (string|null). |
| identity_nonce | string | required | no | Single-use issuance nonce per Section 3. Consumed on first acceptance. |
| issued_at | integer (unix seconds) | required | no | Issuance time. Part of expiry semantics (Section 3), therefore INCLUDED in signed payload. |
| expires_at | integer (unix seconds) | required | no | Identity TTL bound per Section 3. Fail-closed when now > expires_at. |
| signature | string | required | no | The PRINCIPAL's signature over the canonical payload (Section 2, prefix "reddog-identity.v1"), verifiable against principal_public_key. This is a DELEGATION instrument: it MUST be signed by the principal, NEVER by reddog_public_key (a RedDog cannot sign its own scope grant, Section 5). EXCLUDED from the payload it signs (Addendum A). |

### 1b. RedDogDelegatedWorkAuthority

| Field | Type | Req/Opt | Nullable | Allowed values / constraints |
|-------|------|---------|----------|------------------------------|
| work_order_id | string | required | no | Unique id for this work order. |
| principal_id | string | required | no | Who authorized. MUST match a live, non-revoked RedDogPrincipalIdentity.principal_id. |
| reddog_id | string | required | no | Which instance is delegated. MUST match that identity's reddog_id. |
| repo_full_name | string | required | no | Target repo ("owner/name"). MUST be a member of the identity's repo_scope. |
| foundup_id | string | required | no | Target FoundUp. MUST be a member of the identity's foundup_scope (Section 6). |
| allowed_paths | array of string | required | no | Explicit path allowlist. Empty = nothing writable. |
| denied_paths | array of string | required | no | Explicit path denylist. Deny WINS over allow. May be empty. |
| requested_operation | string | required | no | Verb. MUST NOT match FORBIDDEN_OPERATION_TOKENS (OBSERVED present in reddog_governed_work_order_dryrun.py, audit Section 2a). |
| permission_snapshot_digest | string | required | no | Digest of a FRESH RepoPermissionProbeSnapshot, bound into the signed payload (Section 7). |
| nonce | string | required | no | Single-use work-order nonce. Consumed atomically per Section 3. |
| issued_at | integer (unix seconds) | required | no | Issue time; part of expiry semantics; INCLUDED in signed payload. |
| expires_at | integer (unix seconds) | required | no | Short TTL per Section 3. Fail-closed on now > expires_at. |
| valve_state_required | string | required | no | Required execution-valve state. Replaces the plain env-var token (OBSERVED fabricatable in reddog_wre_execution_valve.py, audit Section 2a). |
| receipt_chain | array of SignedReceipt | required | no | Ordered SIGNED receipts (Section 8). May be empty at issuance; grows POST-issuance with signed receipts. EXCLUDED from the work-authority signed payload (Addendum A): a signature fixed at issuance cannot cover a growing array. Chain integrity derives from each receipt's own signature + prev_receipt_hash, and each receipt binds to this order via work_order_id in ITS signed payload, NOT via the work-order signature. |
| signature | string | required | no | The delegated reddog_id's signature over the canonical payload (Section 2, prefix "reddog-workauth.v1"), verifiable against the reddog_public_key of a PRINCIPAL-authenticated identity that grants this scope. Covers EVERY included field EXCEPT signature itself and receipt_chain. EXCLUDED from the payload it signs (Addendum A). |

### 1c. SignedReceipt (referenced by receipt_chain) [SPECIFIED_NOT_IMPLEMENTED]

| Field | Type | Req/Opt | Nullable | Allowed values / constraints |
|-------|------|---------|----------|------------------------------|
| receipt_id | string | required | no | Unique receipt id. |
| work_order_id | string | required | no | The authority this receipt executed under. |
| reddog_id | string | required | no | The signing instance; MUST be the delegated reddog_id. |
| prev_receipt_hash | string | required | yes | Hash of the previous SIGNED receipt payload; null only for the first receipt. |
| covered_action_digest | string | required | no | Digest of the action + evidence this receipt attests. |
| reward_account | string | optional | yes | Public account this receipt accrues to; MUST match the identity reward_account when non-null. |
| issued_at | integer (unix seconds) | required | no | Receipt time; part of chain ordering; INCLUDED in receipt payload. |
| signature | string | required | no | Signature over the canonical receipt payload (Section 8). EXCLUDED from that payload. |

---

## 2. Signature payload canonicalization (Item 2) [SPECIFIED_NOT_IMPLEMENTED]

The verifier and signer MUST agree byte-for-byte on the "signing input". This section
freezes that form. It mirrors the intake discipline: HMAC-SHA256 is computed over the
WHOLE signing_input string, and the verified identity is taken ONLY from the verified
subject, never from an unverified payload field (OBSERVED intake_auth_provider.py
_sig L413-416, _verify_sig L419-430, _clean_handle L505-528).

Canonical form (frozen):
1. Take the record's INCLUDED fields (Section 1 minus the exclusions in Addendum A).
2. Serialize as UTF-8 JSON with:
   - object keys sorted lexicographically by Unicode code point (ascending),
   - no insignificant whitespace (separators are "," between items and ":" between
     key and value, with NO spaces),
   - arrays preserved in their given order (order is authoritative for scope lists
     and path lists). receipt_chain is NOT part of any signed payload (Addendum A):
     receipt-chain integrity derives from per-receipt signatures + prev_receipt_hash
     links, NOT from the work-order signature, so it is never serialized into
     signing_input for the work authority.
   - integers emitted in base-10 with no leading zeros and no fractional part,
   - strings emitted as minimal JSON strings (no non-ASCII; ASCII-only per Section 20).
3. Prepend a domain-separation prefix literal that names the record kind and version,
   consumed by LITERAL strip on the verify side (NOT by delimiter split), so a
   delimiter inside a field can never alter the parsed field count (this is the exact
   safeguard OBSERVED at intake_auth_provider.py _split_kindver L433-439):
   - RedDogPrincipalIdentity  -> prefix literal "reddog-identity.v1"
   - RedDogDelegatedWorkAuthority -> prefix literal "reddog-workauth.v1"
   - SignedReceipt            -> prefix literal "reddog-receipt.v1"
   The signing_input is: <prefix-literal> + "." + <canonical-json>.
4. The signature is computed over that entire signing_input string. The verify side
   recomputes the identical signing_input from the INCLUDED fields and checks the
   signature; the signature field itself is never part of the input (Addendum A).

Signer per record kind (frozen; this is the anti-self-grant rule):
- RedDogPrincipalIdentity (the DELEGATION instrument that confers scope) is signed by
  the PRINCIPAL's key. Its signature is verified against principal_public_key. The
  RedDog's own key CANNOT sign its identity/scope; a RedDog-signed identity record is
  invalid (Section 5, Section 11 step 2). This is what makes a pasted or forged identity
  inert: only the principal's signature (rooted in a token-verified session at issuance)
  grants scope.
- RedDogDelegatedWorkAuthority is signed by the delegated reddog_id. Its signature is
  verified against reddog_public_key, and is valid ONLY if that reddog_id resolves to a
  live, PRINCIPAL-authenticated identity granting the requested scope.
- SignedReceipt is signed by the delegated reddog_id (verified against reddog_public_key).

Algorithm family (frozen as a PLACEHOLDER, no key chosen or generated here):
- All three signatures use an ASYMMETRIC keypair signature (public-verify / private-sign).
  The public halves are principal_public_key (identity) and reddog_public_key (work
  authority + receipt); the private halves never appear (Section 4d). This contract does
  NOT choose a curve, does NOT choose a library, and does NOT generate any key.
  Curve/library selection is a SEPARATE later slice (SPECIFIED_NOT_IMPLEMENTED).
- Rationale for asymmetric (INFERRED): intake's HMAC (symmetric shared secret) proves
  a holder of the shared secret, which is correct for a single-issuer intake but not
  for independent principals and RedDog instances whose verifiers must NOT hold a signing
  secret. A keypair lets a verifier check a signature WITHOUT the power to forge one, and
  lets the principal (not the RedDog) hold the key that grants scope.

Determinism requirement: two correct implementations MUST produce byte-identical
signing_input for the same INCLUDED fields. Any ambiguity (key order, spacing, number
form, array order) is resolved by this section; if a future implementation disagrees,
this section governs.

---

## 3. Nonce and expiry rules (Item 3) [SPECIFIED_NOT_IMPLEMENTED]

Generalizes the intake durable single-use nonce store (OBSERVED SQLiteNonceStore in
intake_auth_provider.py, audit Section 2b) to identities, work orders, and receipts.

Nonce format:
- Opaque high-entropy string (at least 128 bits of entropy), ASCII, unique per issue.
- Fields: identity_nonce (on RedDogPrincipalIdentity), nonce (on
  RedDogDelegatedWorkAuthority). Receipts chain by hash (Section 8), not by nonce.

Single-use durable-consume semantics:
- A durable nonce store records each accepted nonce. Acceptance MUST atomically
  consume the nonce (check-and-insert in one transaction). A nonce already present =
  REPLAY = reject (fail-closed). This generalizes the OBSERVED durable nonce store.
- Consume happens ONLY after signature verification succeeds, so an attacker cannot
  burn a victim's nonce with an unsigned packet.

TTL bounds:
- RedDogPrincipalIdentity: expires_at MUST be present; recommended identity TTL is
  bounded (e.g. hours to days) and MUST NOT be unbounded. An identity past expires_at
  is invalid and cannot authorize any work order.
- RedDogDelegatedWorkAuthority: expires_at MUST be SHORT (work orders are transient).
  A work order past expires_at is invalid; its receipts already produced remain valid
  only if each was signed while the order was live.
- Exact numeric TTLs are a policy parameter set at implementation; this contract fixes
  the RULE (bounded, non-null, fail-closed), not the specific seconds.

Clock-skew handling:
- Verification uses a SINGLE shared time gate with a small, explicit skew tolerance
  (a fixed leeway applied symmetrically to issued_at and expires_at). The intake code
  already centralizes a shared time gate (OBSERVED "Shared time gate" section header at
  intake_auth_provider.py:531-534); this contract requires the same single gate here.
- issued_at in the future beyond the leeway = reject. now beyond expires_at plus leeway
  = reject. Leeway is a fixed small constant, never caller-supplied.

Fail-closed on expiry: any expiry or nonce check that cannot be positively satisfied
(including store unavailable, ambiguous time, missing field) MUST reject. There is no
"allow on doubt" path.

---

## 4. Public key and fingerprint format (Item 4) [SPECIFIED_NOT_IMPLEMENTED]

### 4a. reddog_public_key encoding
- Encoded as an ASCII, self-describing PUBLIC key string (base64url of the public key
  bytes with an algorithm-family tag prefix). No binary blobs on the wire; ASCII only
  (Section 20). The exact key type is deferred with the algorithm choice (Section 2).
- Applies identically to reddog_public_key and principal_public_key; both are public,
  both use this encoding, and 4b derives their respective fingerprints.

### 4b. reddog_key_fingerprint derivation (public-only)
- fingerprint = a cryptographic hash (SHA-256 family) of the CANONICAL public key
  encoding ONLY. It is derived from public material exclusively; it NEVER involves the
  private key. Two records with the same public key MUST yield the same fingerprint.

### 4c. Display form
- Display uses a short prefix of the fingerprint (human-readable, e.g. first bytes in
  hex), and reddog_id embeds that prefix ("reddog:<fingerprint-prefix>"). The display
  form is NON-AUTHORITATIVE: it is for humans and revocation lookup, and is EXCLUDED
  from the signed payload (Addendum A). Authority checks use the full public key, not
  the display prefix.

### 4d. Private-key invariant [CONTRACT INVARIANT]
- NO private signing key (RedDog instance private key OR principal private key) EVER
  appears in: this record, any repo file, any prompt, any Copy-MD, the receipt chain,
  any receipt, any log, or any chain write. Only the PUBLIC keys and their fingerprints
  are ever serialized. A future implementation that serializes any private key VIOLATES
  this contract. (This restates the audit Section 6 off-chain/on-chain boundary as a
  hard invariant, and extends it to the principal key introduced by this revision.)

---

## 5. Principal -> RedDog delegation (Item 5) [SPECIFIED_NOT_IMPLEMENTED]

How a principal_id authorizes a reddog_id, and what binds them:
- A RedDogPrincipalIdentity record is the delegation instrument. It names the
  principal_id (the authenticated 012 principal) AND the reddog_id (the instance) AND
  the scopes (repo_scope, foundup_scope) the principal confers.

Principal-authentication basis [CONTRACT INVARIANT] (the anti-self-grant root):
- The identity record MUST be authenticated by the PRINCIPAL, via BOTH layers:
  (a) SIGNATURE: the identity's signature field is a PRINCIPAL signature over the
      canonical identity payload (Section 2, prefix "reddog-identity.v1"), verifiable
      against principal_public_key. The RedDog's key CANNOT sign this record.
  (b) ISSUANCE GATE: principal_id MUST equal a token-verified subject at issuance time,
      via one of principal_provider in {"github","intake_session","intake_invite"},
      reusing the OBSERVED intake discipline (subject-not-payload, HMAC-verified token,
      durable nonce; intake_auth_provider.py L413-430, L505-528, audit Section 2b).
      A record whose principal_id did not come from a verified session is invalid.
- Consequence: a rogue RedDog instance CANNOT emit an identity record with an arbitrary
  principal_id and arbitrary repo_scope/foundup_scope signed with its own key. Without a
  valid principal signature AND a token-verified issuance, the record is inert. This is
  the direct code enforcement of "RedDog never self-grants authority" (Section 20).

Binding of the two records:
- The BINDING is the PRINCIPAL's signature on the identity (this section) PLUS the
  delegated reddog_id's signature on the work order (Section 2), each with the
  freshness/nonce gates (Section 3): a record is valid only if correctly signed by the
  correct signer, unexpired, and with its nonce unconsumed.
- A RedDogDelegatedWorkAuthority is subordinate: its principal_id and reddog_id MUST
  match a live, non-revoked, PRINCIPAL-authenticated RedDogPrincipalIdentity. A work
  order whose parent identity is missing, revoked, or NOT principal-signed = reject
  (fail-closed), even if the work-order's own reddog signature verifies.

Scope conferral and the no-escalation rule [CONTRACT INVARIANT]:
- Delegation CANNOT exceed the principal's own permission. The effective authority of a
  work order is the INTERSECTION of (a) what the identity's scopes allow and (b) what a
  FRESH RepoPermissionProbeSnapshot for that principal actually grants (Section 7).
- Therefore repo_scope/foundup_scope are a CEILING, not a grant: they can only NARROW
  what the fresh permission snapshot already permits. A scope list can never widen
  actual repo/FoundUp permission. If the identity lists a repo the principal cannot
  write, the fresh snapshot denies it and execution fails closed.
- allowed_paths minus denied_paths is a further narrowing WITHIN the repo. Deny wins.

---

## 6. foundup_scope binding (Item 6) [SPECIFIED_NOT_IMPLEMENTED]

- A work order's foundup_id MUST be a member of the delegating identity's foundup_scope
  (explicit allowlist; membership is exact-string, not prefix or glob). foundup_id not
  in foundup_scope = reject (fail-closed).
- Empty foundup_scope = the RedDog may act for NO FoundUp. There is no implicit
  wildcard; absence of an entry is denial.
- Tie to owner_dae: the intended binding (SPECIFIED_NOT_IMPLEMENTED) is that the target
  foundup_id's owner_dae in foundup_registry MUST resolve to the principal_id (or a DAE
  the principal controls). OBSERVED today: owner_dae is defined in the schema but
  UNPOPULATED in foundup_registry.json data (audit Section 2e). Until owner_dae is
  populated, the ownership tie CANNOT be checked, so a future verifier MUST fail closed
  on an unpopulated owner_dae for a write-bearing work order (no ownership proof = no
  authority). This contract specifies the intended binding; it does not populate data.

---

## 7. Permission-snapshot binding (Item 7) [SPECIFIED_NOT_IMPLEMENTED]

- permission_snapshot_digest is the digest of a FRESH RepoPermissionProbeSnapshot
  (OBSERVED RepoPermissionProbeSnapshot with checked_at/expires_at/evidence_digest and
  is_snapshot_fresh() enforcing now <= expires_at, in reddog_github_permission_probe.py,
  audit Section 2d).
- Binding rule: permission_snapshot_digest is one of the INCLUDED fields in the work
  authority's signed payload (Section 2). The snapshot is thus cryptographically tied
  to the work order; it cannot be swapped for a different (e.g. more permissive) or
  stale snapshot without invalidating the signature.
- Freshness rule: at verify time the digest MUST resolve to an actual snapshot whose
  is_snapshot_fresh() is true (now <= expires_at). A stale or missing snapshot =
  fail-closed. The snapshot must also positively grant the requested_operation on
  repo_full_name (can_write/can_admin as required by the verb).
- Point-in-time, not a stream: the snapshot is a fresh point-in-time probe (OBSERVED
  "Point-in-time, not a stream" in audit Section 2d). Re-use of an expired snapshot
  digest is a stale-permission escalation attempt and MUST reject.

---

## 8. Receipt signing requirements (Item 8) [SPECIFIED_NOT_IMPLEMENTED]

- Receipts MUST be SIGNED, replacing the OBSERVED unsigned hash-linked receipts
  (proof_of_compute_receipt.py hash-linked UNSIGNED, audit Section 2a). A SignedReceipt
  (Section 1c) carries a signature over its canonical receipt payload (Section 2, using
  the "reddog-receipt.v1" prefix), produced by the delegated reddog_id.
- What each receipt covers: the covered_action_digest attests the specific action and
  its evidence executed under work_order_id. The receipt does NOT re-grant authority;
  it only attests that a signed, in-scope action occurred.
- Chain linkage: receipt_chain is ordered. Each receipt's prev_receipt_hash equals the
  hash of the previous SIGNED receipt's canonical payload (null for the first). A break
  in the hash link, or an out-of-order receipt, invalidates the chain from that point.
- Unsigned = not in chain = no reward [CONTRACT INVARIANT]: a receipt lacking a valid
  signature by the delegated reddog_id is NOT a member of the chain and confers NO
  reward. Hash-linkage alone (integrity) is insufficient; authenticity (signature) is
  required. This closes the OBSERVED "receipts are hash-linked but unsigned" gap.

---

## 9. Revocation policy (Item 9) [SPECIFIED_NOT_IMPLEMENTED]

A principal revokes a reddog_id by any of these, all fail-closed:
- TTL expiry: once now > identity expires_at, the identity is dead; no work order may
  cite it. This is passive revocation (no action needed).
- Allowlist removal: removing a repo from repo_scope or a foundup_id from foundup_scope
  (or emptying them) immediately narrows authority; a subsequently issued work order
  citing the removed entry fails the scope check.
- Kill-switch: revocation_policy.kill_switch_ref names a revocation record; if that
  record marks the reddog_id (or its fingerprint) revoked, verification MUST reject even
  a signature that is otherwise valid and unexpired.

Revocation precedence [CONTRACT INVARIANT]:
- Revocation WINS over a still-valid signature. The verifier checks revocation BEFORE
  accepting a signature: a revoked reddog_id / fingerprint is rejected even if the
  signature verifies and the record has not yet expired. Order of checks is
  revocation-first, then signature, then freshness/scope. There is no path where a
  cryptographically valid but revoked packet executes.

---

## 10. Reward-account boundary (Item 10) [SPECIFIED_NOT_IMPLEMENTED, FUTURE_BLOCKED]

- reward_account accrues ONLY via a SIGNED receipt in receipt_chain, never via a model
  claim or free text. The receipt's reward_account MUST match the identity's
  reward_account when non-null.
- Separation invariants [CONTRACT INVARIANT], restating audit Section 7:
  - Execution authority does NOT imply fund custody. Being allowed to write a repo is
    not being allowed to move value.
  - reward_account does NOT imply repo authority. Being paid to an account is not being
    allowed to write a repo.
  - Consensus (CABR approved) is NOT settlement (send tokens); they remain distinct.
- Settlement stays FUTURE_BLOCKED (WSP_100: payout_ready/cabr_ready hard-false by
  design; WSP_58: split governance-gated). OBSERVED: cabr_store_export.py header states
  it "DOES NOT: Write to wallet / Trigger payouts / Issue tokens or UPS / Allocate
  rewards" and its ready flags are always FALSE (audit Section 2e). This contract
  defines the future path only; it creates NO wallet and NO payout path, and RedDog can
  neither amend the split (WSP_58) nor self-approve settlement (WSP_48 Sec 8.3, WSP_100).

---

## Addendum A. Canonicalization negative space (REQUIRED) [SPECIFIED_NOT_IMPLEMENTED]

Fields EXCLUDED from the signed payload, and WHY. Excluding a field means it is NOT part
of signing_input (Section 2) and therefore carries no authority; a verifier ignores it
for authority decisions.

| Excluded field / class | Why excluded |
|------------------------|--------------|
| signature (the field itself) | A signature cannot sign itself; it is computed over the other INCLUDED fields and appended. Including it is logically impossible and would be a canonicalization bug. |
| derived display labels (e.g. reddog_key_fingerprint DISPLAY prefix, human names) | Derived from included material (the public key); signing them adds nothing and risks divergence. Authority uses the full public key, not the display prefix. |
| non-authoritative UI text (status strings, banners, hints) | Presentation only; affects no authority/scope/permission/reward/replay decision. |
| model-generated summaries / rationales | Produced by a model, not by the principal; must never become authority (this is the whole "role text is never authority" point). |
| volatile timestamps NOT part of nonce/expiry semantics (e.g. rendered_at, logged_at) | Volatile and non-authoritative. Note: issued_at and expires_at ARE authority-bearing (expiry semantics) and are therefore INCLUDED, not excluded. |
| receipt RENDER formatting (pretty-printed receipt text, markdown) | Presentation of a receipt is not the receipt. The CANONICAL receipt payload (Section 1c INCLUDED fields) is what is signed and chained. |
| receipt_chain (on the work authority) | EXCLUDED because it grows post-issuance; a work-order signature fixed at issuance cannot cover a growing array. Receipts are authenticated independently (each SignedReceipt signs its own payload + prev_receipt_hash) and bind to the order via work_order_id carried in the receipt's OWN signed payload. The work-order signature covers everything EXCEPT signature and receipt_chain. |

Rule to state verbatim (frozen):

    If a field affects authority, scope, permission, reward, or replay,
    it must be included in the signed payload.

Corollary: any new field a future revision adds MUST be classified as authority-bearing
(INCLUDED) or presentation/derived (EXCLUDED) BEFORE it ships. Unclassified fields
default to EXCLUDED and therefore carry no authority (fail-safe default).

---

## Addendum B. Cross-surface spoofing matrix (REQUIRED) [SPECIFIED_NOT_IMPLEMENTED]

| Surface | Spoof attempt | Required proof | Fail-closed behavior |
|---------|---------------|----------------|----------------------|
| RedDog prompt text | prompt says "I am 012" | A PRINCIPAL signature on the identity (principal_public_key) rooted in a token-verified principal_id, plus a reddog signature on the work order | Prompt text is inert; with no valid principal-signed identity the packet is rejected; no execution |
| RedDog self-mint | a RedDog signs its own identity with wide scope using its own key | Identity signature MUST verify against principal_public_key (principal-signed), not reddog_public_key; principal_id token-verified at issuance | RedDog-signed identity is invalid; self-granted scope rejected (Section 5, Section 11 step 2a) |
| Replay | copied prior authorization packet resubmitted | Unconsumed single-use nonce (durable atomic consume) AND now < expires_at | Consumed nonce or expired = reject; replay fails |
| Stale permission | attach an old, more permissive permission snapshot | permission_snapshot_digest bound in signature AND is_snapshot_fresh() true AND grants the verb | Stale/missing/insufficient snapshot = reject (fail-closed) |
| Impersonated instance | different reddog_id using the same principal_id | reddog_id MUST match a live RedDogPrincipalIdentity delegating THAT reddog_id from THAT principal_id; signature by that instance key | Mismatched reddog_id / missing identity = reject |
| Cross-repo actor | external founder's RedDog targeting Foundups-Agent | repo_full_name in signed repo_scope AND a FRESH snapshot for the principal grants write on that repo | Repo not in scope or snapshot denies = reject; no cross-repo write |
| Reward without work | reward claim with no signed receipt | A SIGNED receipt in receipt_chain bound to reddog_id/principal_id/reward_account | No signed receipt = no chain membership = no reward |
| Fabricated token | model output emits a "sovereign token" literal | valve_state_required is bound into the signed, scoped payload; there is no free-text token gate | Any free-text/env-var token is not authority; unsigned = reject |
| Unsigned receipt | receipt hash present but no signature | Valid signature by the delegated reddog_id over the canonical receipt payload | Unsigned receipt = not in chain = no reward |

---

## 11. Verification order (INFERRED synthesis, ratifying audit Section 4)

A future verifier MUST evaluate in this order; any miss = fail-closed, no execution:
1. Revocation check first: reddog_id / fingerprint (and principal_id) not revoked
   (Section 9).
2. TWO signatures, checked SEPARATELY (Section 2 signer-per-record-kind):
   2a. Parent identity: its signature verifies against principal_public_key over the
       canonical identity payload, AND its principal_id was token-verified at issuance
       (Section 5 basis). A work order whose parent identity is NOT principal-signed (or
       is RedDog-signed) = reject, regardless of the work order's own signature.
   2b. Work order: its signature verifies against the reddog_public_key of that
       principal-authenticated identity over the canonical work-authority payload.
   A valid reddog signature on the work order does NOT substitute for a valid principal
   signature on the identity; both are required.
3. Freshness/replay: identity and work order unexpired (single shared time gate,
   Section 3); nonce unconsumed then atomically consumed AFTER signature success.
4. Permission: permission_snapshot_digest resolves to a FRESH snapshot granting the
   verb on repo_full_name (Section 7).
5. Scope: repo_full_name in repo_scope AND foundup_id in foundup_scope; owner_dae ties
   to principal_id (fail closed if owner_dae unpopulated for a write, Section 6).
6. Path/verb: requested_operation not forbidden; allowed_paths minus denied_paths
   non-empty and in-scope; deny wins.
7. Valve: valve_state_required satisfied.
Only when ALL pass does the work authority become executable. This is the audit's
"authority input" pipeline made ordered and revocation-first.

---

## 20. Truth Boundary Checklist (scope guards) [CONTRACT INVARIANTS]

- NO_KEY_IMPLEMENTATION   -- schema/canonicalization defined only; zero keys generated, zero signing code.
- NO_VERIFIER_CODE        -- verification ORDER is specified; no verifier is implemented.
- NO_CHAIN               -- on/off-chain boundary described; no chain write; no chain library.
- NO_WALLET              -- reward path SPECIFIED + FUTURE_BLOCKED; no wallet created/bound.
- NO_PERMISSION_CHANGE   -- permission model mapped only; no grant/revoke performed.
- DOCS_ONLY              -- deliverable is this document; zero .py created or modified; no crypto/signing/keygen library added.

Hard invariants restated (contract must enforce in any future implementation):
- No private keys anywhere (repo, prompt, Copy-MD, chain, receipt, log) (Section 4d).
- The DELEGATION instrument (RedDogPrincipalIdentity) MUST be signed by the PRINCIPAL's
  key and its principal_id token-verified at issuance; the RedDog key CANNOT sign its own
  identity/scope (Section 5, Section 2, Section 11 step 2a). Work order MUST be signed by
  the delegated reddog key (Section 2); permission snapshot MUST be fresh AND bound into
  the signed payload (Section 7); foundup_scope MUST be explicit (Section 6); receipt_chain
  is NOT in the work-order signed payload and each receipt is independently signed
  (Sections 1b, 8, Addendum A); rewards attach to SIGNED receipts, not model claims
  (Sections 8, 10).
- RedDog NEVER self-grants authority: (a) at the instrument level, a RedDog-signed
  identity is invalid (only a principal signature grants scope, Section 5); and (b)
  broadening execution authority is a high-risk change requiring WSP_96 3-agent consensus
  + 0102 veto, and MUST NOT be self-approved (WSP_48 Sec 8.3, WSP_100). (OBSERVED WSP
  bindings, audit Section 1.)

---

## 21. Chain-of-refutation (CoR) rounds

Adversarial passes: try to build a packet that satisfies the LETTER of the schema yet
still spoofs identity, replays, or over-scopes. Each round records the attack and the
tightening applied to this contract.

Round 1 -- "Satisfy every field but sign nothing meaningful."
- Attack: emit a fully-populated RedDogDelegatedWorkAuthority with a signature computed
  over ONLY a subset of fields (e.g. sign work_order_id but leave allowed_paths out of
  the signed set), then widen allowed_paths after signing.
- Result: SUCCEEDS against a naive reader that does not fix WHICH fields are signed.
- Tightening: Section 2 + Addendum A now FREEZE the INCLUDED set and state the verbatim
  rule "if a field affects authority, scope, permission, reward, or replay, it must be
  included." allowed_paths/denied_paths/repo_full_name/foundup_id/permission_snapshot_
  digest/valve_state_required are all authority-bearing -> INCLUDED. Post-sign widening
  now breaks the signature. CLOSED.

Round 2 -- "Delimiter-injection to miscount fields."
- Attack: put a "." or JSON-structural character inside principal_id so the parser
  miscounts fields or reassigns the subject.
- Result: SUCCEEDS if the prefix is consumed by delimiter-splitting.
- Tightening: Section 2 step 3 requires the domain prefix be consumed by LITERAL strip,
  not delimiter split, and canonical JSON with sorted keys (OBSERVED safeguard mirrored
  from intake_auth_provider.py:433-439). A delimiter inside a value cannot change the
  parsed field count. CLOSED.

Round 3 -- "Valid signature, but replay it tomorrow."
- Attack: capture a fully-valid signed work order and resubmit it later.
- Result: SUCCEEDS if nonce is not durably single-use or expiry is unbounded.
- Tightening: Section 3 mandates durable atomic consume (generalizing the OBSERVED
  SQLiteNonceStore) AND bounded short expires_at AND a single shared time gate with
  fixed leeway. Consumed nonce or expired = reject. Consume occurs only AFTER signature
  success so a victim's nonce cannot be pre-burned. CLOSED.

Round 4 -- "Scope list widens my real permission."
- Attack: list a repo/foundup in repo_scope/foundup_scope that the principal cannot
  actually write, and rely on the scope list as a grant.
- Result: SUCCEEDS if scope is treated as a grant rather than a ceiling.
- Tightening: Section 5 makes scope a CEILING intersected with a FRESH permission
  snapshot (Section 7); a scope entry can only NARROW, never widen. Unpopulated
  owner_dae for a write = fail closed (Section 6). CLOSED.

Round 5 -- "Swap a fresher-looking but more permissive snapshot."
- Attack: bind a digest of a different, more permissive (or stale-but-cached) snapshot.
- Result: SUCCEEDS if the digest is not part of the signed payload or freshness is not
  re-checked.
- Tightening: Section 7 puts permission_snapshot_digest INSIDE the signed payload and
  requires is_snapshot_fresh() true AND positive grant of the verb at verify time.
  Swapping the snapshot breaks the signature; a stale snapshot fails freshness. CLOSED.

Round 6 -- "Revoked but not yet expired."
- Attack: after a principal revokes a reddog_id, replay a still-unexpired, validly
  signed work order before its TTL lapses.
- Result: SUCCEEDS if signature is checked before revocation, or revocation only means
  TTL.
- Tightening: Section 9 makes revocation WIN over a valid signature and Section 11 puts
  the revocation check FIRST (before signature). A revoked id is rejected regardless of
  signature validity or remaining TTL. CLOSED.

Round 7 -- "Earn a reward with an unsigned receipt."
- Attack: append a hash-linked but unsigned receipt to receipt_chain to claim a reward.
- Result: SUCCEEDS if hash-linkage alone counts as chain membership.
- Tightening: Section 8 requires each receipt be SIGNED by the delegated reddog_id; an
  unsigned receipt is NOT in the chain and confers NO reward. Section 10 binds reward
  accrual to signed receipts only. CLOSED.

Round 8 (completeness sweep) -- "Is any authority-bearing field still excludable?"
- Attempt: enumerate every field in Section 1 and confirm each authority/scope/
  permission/reward/replay field is in the INCLUDED set and each presentation/derived
  field is in Addendum A. No authority-bearing field is found excluded; unclassified
  future fields default to EXCLUDED (fail-safe, carry no authority). No new spoof
  constructed. RESULT: no residual bypass found in this pass.

Round 9 -- "Append receipts under a fixed work-order signature."
- Attack: the work-order signature is fixed at issuance, yet receipt_chain was named as
  an authoritative-order array INSIDE the signed payload. Either (a) appending any
  receipt breaks the work-order signature (no receipts can ever be added), or (b) if the
  verifier tolerates the mismatch, an attacker swaps/reorders receipt_chain after signing
  because the signature no longer actually pins it.
- Result: SUCCEEDS as a contradiction that a verifier would resolve unsafely (tolerating
  a post-sign array = unpinned receipts = forgeable chain).
- Tightening: receipt_chain is now EXCLUDED from the work-authority signed payload
  (Addendum A row; Section 1b; Section 2 array-order note). Chain integrity derives from
  per-receipt signatures + prev_receipt_hash, and each receipt binds to the order via
  work_order_id in ITS OWN signed payload (Section 1c). The work-order signature covers
  everything EXCEPT signature and receipt_chain. No unpinned-array ambiguity remains, and
  receipts cannot be forged because each is independently signed. CLOSED.

Round 10 -- "RedDog self-mints its own identity and scope."
- Attack: a rogue RedDog instance emits a RedDogPrincipalIdentity naming an arbitrary
  principal_id with wide repo_scope/foundup_scope, signs it with its OWN reddog key, then
  issues work orders under it. Under the prior text ("identity and work-authority
  signatures use reddog_public_key") this self-grant would verify.
- Result: SUCCEEDS under the prior single-signer rule -- a direct violation of "RedDog
  never self-grants authority."
- Tightening: Section 2 now fixes the SIGNER per record kind -- the identity (the
  delegation instrument) is signed by the PRINCIPAL's key (principal_public_key) AND its
  principal_id must be token-verified at issuance (Section 5 basis); the work order and
  receipts are signed by the reddog key. Section 11 step 2 checks the principal signature
  on the identity SEPARATELY from the reddog signature on the work order and rejects any
  work order whose parent identity is not principal-signed. Section 4d extends the
  never-appears invariant to the principal private key. A RedDog-signed identity is now
  invalid, so the self-mint fails closed. CLOSED.

Outcome: all constructed attacks (Rounds 1-7, 9, 10) were closed by tightening the
referenced sections; Round 8 found no residual authority-bearing exclusion. No attack in
this pass satisfied the letter of the tightened schema while still spoofing, replaying,
self-granting, or over-scoping.

---

## 22. Sequence reminder (do not jump ahead)

This contract is step 1 of the audit's Section 12 sequence. Subsequent slices, each its
own gated slice (do NOT start here): (2) threat-model / static-contract tests asserting
the Addendum B rows and Section 20 invariants; (3) work-order signature verifier
(generalize the intake HMAC/subject-not-payload pattern to an asymmetric keypair);
(4) signed receipt chain; (5) reward-account mapping (settlement FUTURE_BLOCKED);
(6) WSP_96 consensus-gated + 0102-veto authority broadening. No key generation and no
verifier code in this slice.
