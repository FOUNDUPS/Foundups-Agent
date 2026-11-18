# REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1

**Type:** Decision / contract ONLY. No code, no keys, no vault config, no chain, no authority change, no re-index.
**Author:** 0102 (RedDog Architect) | Commander: 012
**WSP:** 00, 15, 50, 97 (method); 71 (primary -- Secrets Management), 95, 96, 54, 64, 48 (governing).
**Base:** `62e6e7a48` (main; after #925/#926/#927/#928/#929).
**Sequence position:** E0 (mandatory precondition for E1; E1 implementation is BLOCKED until E0 merges -- see the Sequence Lock in s5).

---

## 0. Purpose + why E0 gates E1 (the G5.1 finding)

Slice C (#929) established **G5.1**: a poisoned Skill / dependency / MCP tool loaded INTO RedDog's own process can reach the host vault where the signing key lives and **emit a fully-VALID signed authority**. A signature verifier (E1) is therefore necessary but **not sufficient**: over signatures produced by a poisonable signer, the verifier faithfully accepts forgeries. This slice specifies the **isolation boundary** that keeps the signing key unreachable by any code RedDog loads and executes.

This contract was hardened by a 4-lens adversarial CoR (11 blocker / 12 major DESIGN findings) whose theme is: **same-user process separation is not a security boundary, request-body identity is not identity, and scope re-validation does not stop in-scope abuse.** All folded below.

**This slice writes a contract only** -- no signer code, no keys, no vault items, no WSP framework edit.

## 1. Governing WSPs

- **WSP 71 (Secrets Management -- PRIMARY):** the denial of the signing key to the runtime is WSP 71 s3.2 **permission-validated retrieval** (`get_secret` gated by `agent_id` -> `PermissionDeniedError`), NOT possession of an `op://` reference string. WSP 71 Rule 4 + s3.4 **SkillSafetyGate** own the skill supply-chain gate. E0 EXTENDS WSP 71 (WSP 64); it does not mint a new WSP and does not define its own scanner.
- **WSP 95 (Skillz Wardrobe):** prototype->production promotion evidence; E0 CONSUMES this gate, does not restate it.
- **WSP 96 (Governance & Consensus):** high-authority signing is a high-risk issuance -> consensus + 0102 veto.
- **WSP 54 / 48:** the Signer is not self-extensible by the agent it serves; propose-not-self-approve.
- Cross-ref: #926 s6 (private half never leaves the host vault); C G5.1 (this threat), G7.2 (no key leak), G2.1 (signer not self-modifiable), G4.2/G4.5 (atomic pinned snapshot), G4.6 (audit anchoring), G6.1/G7.1 (abuse + availability).

## 2. As-built evidence (OBSERVED) -- corrected claims

- **`secrets_mcp/vault_resolver.py` (WSP 71 Annex A):** a **MOCK PoC** (`NO_REAL_SECRET_ACCESS`, no principal scoping). It illustrates the *shape* to reuse -- `op://vault/item/field`, TTL 300s, `FAIL_CLOSED`, `SECRET_VALUE_NEVER_LOGGED`, `AUDIT_HASH_ONLY` -- but is NOT the real credential authority. Note: its `hash_secret()` returns the **full sha256 of the secret**; that MUST NOT be reused for any public fingerprint.
- **`intake_auth_provider.py`:** the pattern to generalize -- injectable secret seam, rotation (current+previous), **`hmac.compare_digest` constant-time (L428)**, sign=[current] / verify=[current,previous], never load dotenv / print / log / return a secret, fail-closed. But it loads the secret via `os.getenv` **in-process**.
- **`agent_work_batcher/executor.py:199`:** runs `git log` via `subprocess.run` with **no `env=` (full parent-env inheritance)** and `capture_output=True`. This is process separation for a trusted binary; it is **NOT a secrets boundary** and is cited here only as a counter-example (env-inheritance + stdout capture are exactly what the Signer must forbid).
- **The concrete gap (INFERRED):** whether from `os.getenv` or a resolved vault value, the secret becomes **plaintext bytes in the same process memory that loads plugin code**. Reference-by-handle hides *storage*, not the *resolved value*. G5.1 is open until resolve+sign moves behind a boundary that loaded code -- running as the same OS principal -- cannot cross (ptrace / `/proc/<pid>/mem` / core dump / env / argv / shared memory).

## 3. The isolation contract (SPECIFIED_NOT_IMPLEMENTED)

**Core invariant:** the signing key MUST NEVER be resolvable-to-plaintext in, or reachable by, a process that loads untrusted code. It is used only inside an isolated **Signer** under a **distinct OS principal**; the RedDog runtime receives signatures, never the key.

### 3a. Signer isolation (OS-level, mandatory -- an AND-list, not options)
1. **Distinct OS principal.** The Signer runs as a dedicated least-privileged OS user the runtime **cannot ptrace or read** (`/proc/<pid>/mem`). Same-user process separation is **explicitly insufficient and forbidden as the sole boundary**. Required hardening: runtime UID has no `CAP_SYS_PTRACE`; YAMA `ptrace_scope` prevents cross-uid attach; Signer sets `PR_SET_DUMPABLE=0` and `RLIMIT_CORE=0` (no core dumps).
2. **No inherited environment.** The Signer does NOT inherit the runtime's environment; the signing-key handle is NEVER passed via env or argv (both are same-user readable via `/proc/<pid>/environ|cmdline`).
3. **Host connects, does not spawn.** Prefer a long-lived Signer daemon under the distinct principal that the runtime CONNECTS to over an authenticated local IPC channel (unix socket with restrictive perms owned by the Signer principal) -- never a child the runtime spawns and could env-poison or ptrace.
4. **Loads no untrusted code.** The Signer imports no Skillz / third-party plugins / MCP tools; its code path is fixed and governance-protected (C G2.1). It CONSUMES the WSP 71 s3.4 SkillSafetyGate + WSP 95 promotion evidence; it does not run a scanner itself.

### 3b. Requester identity + scope (kernel-attested, not request-body)
1. **Identity from the kernel peer credential.** The Signer derives the requester principal from `SO_PEERCRED` / `getpeereid` (unix socket) or the named-pipe peer token -- NOT from any field in the request. An in-request `requester_principal_id` is advisory/audit-only and MUST match the attested peer or fail closed.
2. **Scope from a runtime-unwritable source.** Authorized scope is looked up by the **attested uid** against an authorization source the RedDog runtime CANNOT write (a trusted WSP-framework/permission path), with an atomically **pinned** permission + valve snapshot (CAS re-check at sign; ties C G4.2/G4.5). The Signer MUST NOT re-validate against HoloIndex / pattern-memory / task-text (C G1.3/G1.4).

### 3c. Sign-what-you-validate + authority tiering
1. **`canonical_payload` is the SINGLE source of truth.** The Signer canonically decodes it, extracts the capability it encodes, and validates THAT. `claimed_capability` is removed from the authority path (accepted only if byte-identical to the re-derived capability; otherwise reject). The Signer signs exactly the bytes it validated.
2. **Scope re-validation does NOT close in-scope abuse.** A compromised but in-scope caller can request a malicious-but-in-scope authority. Therefore **high-authority tiers** (create_foundup, repo write, promotion) require a **consensus / 012-DAO co-sign gate** (WSP 96) -- signing alone is never sufficient for high-authority issuance. Low-authority/dry-run tiers may be autonomous.
3. **Anti-abuse metering.** Per-principal **signing rate + volume cap**, fail-closed on exceed, with an alarm on sustained saturation the runtime **cannot self-clear** (C G7.1); receipt de-dup + minimum-substance threshold on signed work orders (partially owns C G6.1; value-weighting is downstream). The nonce prevents replay of ONE request only -- it is NOT anti-abuse; prefer a Signer-issued challenge nonce.

### 3d. Key lifecycle, fingerprint, audit (no leak channels)
1. **Sign current key only.** The previous/rotated key is NEVER loadable for signing; on rotation the previous signing `op://` handle is revoked at the vault (not demoted to verify-only -- verify overlap belongs to E1). The **key epoch/generation** is committed inside `canonical_payload` (or an authenticated header) so E1 can reject a revoked generation.
2. **No persistent plaintext key.** Resolve-per-sign (resolve -> sign -> **zeroize**), never cache plaintext beyond a single signing call; TTL is enforced at **use** time, not only resolve time; a sign past the resolve-time TTL fails closed and re-resolves.
3. **`key_fingerprint`** is derived from PUBLIC verification material only, OR is a random rotation-stable key-id assigned at key creation -- **never `sha256(secret)`**; do not reuse `vault_resolver.hash_secret()` on the signing key. No `SigningResponse` field is derived from secret bytes.
4. **`audit_mac`** is a KEYED MAC (Signer-held audit key **distinct** from the signing key) or predecessor-chained, over `(canonical_payload_digest || decision || monotonic_counter || signer_nonce)` -- it MUST include a value the caller cannot supply or predict; the audit/nonce store lives inside the Signer domain on a path the runtime cannot write/delete/truncate, and its rollback is detectable (monotonic counter / external checkpoint, C G4.6) forcing fail-closed.
5. **Constant-time + memory hygiene, both sides.** All principal/capability/scope comparisons use constant-time compare with no positional-match leak; failures reveal no expected-value material; no secret in argv/exit-code/shared-memory/core-dump/exception-frame locals or the resolver audit trail.

### 3e. Schema (decision-only)
```yaml
SigningRequest:
  canonical_payload:      # SINGLE source of truth; the exact bytes signed; encodes the capability + key_epoch
  nonce:                  # anti-replay of THIS request only (prefer Signer-issued challenge); not anti-abuse
  requester_principal_id: # ADVISORY/AUDIT ONLY; must equal the kernel-attested peer or fail closed
SigningResponse:
  signature:              # over canonical_payload; produced only inside the Signer
  key_fingerprint:        # PUBLIC material or random key-id; NEVER sha256(secret)
  key_epoch:              # generation used; verifiable by E1 for revocation
  audit_mac:              # keyed/chained; over signer-side uncontrollable values; NEVER the key/secret
  ok / rejection_code:    # fail-closed on any miss (no secret-derived exit values)
SignerBoundaryInvariants:
  - signer_principal_distinct_and_non_ptraceable_by_runtime   # + PR_SET_DUMPABLE=0, RLIMIT_CORE=0
  - signer_does_not_inherit_runtime_env; key_handle_never_via_env_or_argv
  - host_connects_to_long_lived_signer_over_perm_restricted_socket   # not spawn
  - signer_loads_no_untrusted_code (consumes WSP71 s3.4 + WSP95)
  - requester_identity_from_kernel_peer_credential_not_payload
  - scope_lookup_keyed_by_attested_uid_against_runtime_unwritable_source_pinned_CAS
  - sign_only_capability_decoded_from_canonical_payload
  - high_authority_tiers_require_consensus_cosign   # signing alone never sufficient
  - per_principal_signing_rate_and_volume_cap_fail_closed_with_unclearable_alarm
  - sign_current_key_only; previous_signing_handle_revoked_at_vault; key_epoch_in_payload
  - no_persistent_plaintext_key_cache; resolve_per_sign; zeroize_after_sign; ttl_enforced_at_use
  - key_fingerprint_from_public_material_never_sha256_of_secret
  - audit_mac_keyed_or_chained_over_signer_uncontrollable_value; tamper_detectable_nonce_store
  - constant_time_no_positional_leak_and_no_secret_in_argv_exit_shm_coredump_or_error
  - key_grant_denied_to_runtime_via_WSP71_permission_validated_retrieval
  - fail_closed
```

## 4. Threat coverage

- **Closes G5.1** (in-process poison -> valid forged signature): distinct-principal isolation + no env/argv/ptrace path + kernel-attested identity + sign-what-you-validate. A poisoned in-process caller can neither read the key nor forge the requester principal.
- **Partially owns G6.1 / G7.1** (rate/volume cap + unclearable alarm) and **G4.2/G4.5** (pinned-snapshot CAS at sign).
- **Contributes G7.2** (fingerprint/audit/timing/memory leak channels closed), **G2.1** (signer not self-extensible), **G4.6** (tamper-detectable audit anchor).
- **Does NOT close** in-scope high-authority abuse by itself -> deferred to the consensus/co-sign gate (WSP 96) named in 3c.2.

## 5. Relationship to E1 -- strict E0-before-E1 Sequence Lock

- **E0 (this):** the SIGNING side -- the key cannot be reached or misused by loaded code; the constant-time / no-leak rules apply signing-side here (not merely "inherited from E1").
- **E1 `REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1`:** the VERIFY side -- generalize intake_auth (verified subject NOT payload text, signed prefix, nonce, expiry, durable consume-once, fail-closed, `secrets.compare_digest`, no expected-value in failures) + reject a revoked `key_epoch`.
- **E1 verifier implementation is BLOCKED until E0 lands.** E1 encodes assumptions from E0's boundary; if E0 changes in review, parallel E1 builds against a stale boundary. This is security-sensitive and not worth the concurrency gain.

```
E0/E1 Sequence Lock:
- REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1 MUST NOT begin implementation until
  REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1 is merged.
- Tests, verifier APIs, or signature-acceptance semantics authored before E0 merge are
  non-authoritative and must be discarded or revalidated after E0 lands.
- No signature may be treated as authority until both E0 and E1 have landed and passed
  gate review.
```

## 6. Truth boundaries

- OBSERVED: vault_resolver is a mock (no principal scoping; hash_secret = full sha256 of secret); intake_auth uses os.getenv in-process + compare_digest + sign-current/verify-current+previous; agent_work_batcher subprocess inherits env + captures stdout.
- INFERRED: same-user separation is penetrable; request-body identity and scope re-validation are insufficient; the resolve+sign step must be moved behind a distinct-principal boundary with kernel-attested identity.
- SPECIFIED_NOT_IMPLEMENTED: the isolated Signer, the schema + invariants, the WSP 71 permission-validated denial of the key to the runtime, the consensus co-sign gate, the rate cap. This doc adds NO code, NO keys, NO vault items, NO WSP edit.

## 7. Verdict + next slice

Verdict: **AUTHOR_DECISION_CONTRACT_NOW; IMPLEMENT_LATER; E0 STRICTLY GATES E1.** Next only after E0 lands + is reviewed: `REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1` (E1). Per the Sequence Lock (s5), E1 implementation MUST NOT begin until E0 is merged; any E1 tests/APIs/semantics authored earlier are non-authoritative and discarded/revalidated after E0 lands.

## 8. Out of scope (this slice)
Any signer/crypto/key/vault code; creating or configuring vault items or OS principals; editing #925-#929 or the valve/gate/WSP framework; the verifier (E1) as an authority path; running the live writer; opening authority; adding Skillz; re-indexing.

---

*Central rule: a signature proves authenticity ONLY if the key that made it could not be reached by the code the agent loads, AND the requester could not lie about who they are, AND the signer signs only what it validated. Same-user separation, request-body identity, and scope-checks-alone are none of these. Key isolation under a distinct principal is a precondition of signature authority -- so it gates the verifier.*
