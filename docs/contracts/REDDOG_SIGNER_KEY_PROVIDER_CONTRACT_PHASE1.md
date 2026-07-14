# REDDOG_SIGNER_KEY_PROVIDER_CONTRACT_PHASE1

Status: CONTRACT SPEC, decision-only. No runtime key loading, no key generation,
no vault configuration, no signer process launch, no socket binding, no authority
change, no repository mutation, and no HoloIndex re-index.

Author: 0102 Codex | Commander: 012
Base: origin/main at write time, after REDDOG_ISOLATED_SIGNER_SOCKET_SERVICE_ONCE_PHASE1.
WSP: WSP_00, WSP_15, WSP_50, WSP_71, WSP_95, WSP_96, WSP_97.

Truth-label legend:
- OBSERVED: read directly from repository source.
- INFERRED: conclusion from observed source.
- SPECIFIED_NOT_IMPLEMENTED: required by this contract, not built here.

## 0. Purpose

RedDog now has the following signer pieces:

- OBSERVED: an isolated signer socket client and protocol.
- OBSERVED: a one-request local socket service with injected peer attestor and
  injected signer backend.
- OBSERVED: an Ed25519 signer backend that signs with an already-held private
  key object.
- OBSERVED: an Ed25519 verifier backend and resident queue verification bundle.

The missing boundary is the point where signer-owned secret material becomes an
Ed25519 private key object and audit-MAC key material. This contract freezes that
boundary before any implementation handles private key bytes.

## 1. Source Evidence

- OBSERVED: `docs/audits/architecture/REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1.md`
  requires a distinct OS-principal signer, no inherited runtime environment, a
  signer-held keyed audit MAC, public-only fingerprints, resolve-per-sign, TTL
  at use time, and WSP 71 permission-validated retrieval.
- OBSERVED: `modules/infrastructure/secrets_mcp/src/vault_resolver.py` is a
  mock proof of concept. It labels itself `MOCK_VAULT_ONLY` and
  `NO_REAL_SECRET_ACCESS`. It is not a production credential authority.
- OBSERVED: `WSP_framework/src/WSP_71_Secrets_Management_Protocol.md` defines
  the `op://vault/item/field` reference shape and requires secret values never
  be stored in prompts, logs, repository files, or terminal output.
- OBSERVED: `modules/communication/moltbot_bridge/src/reddog_ed25519_signer_backend.py`
  expects an already-held Ed25519 private key object and an injected
  audit-MAC builder. It does not load keys.
- INFERRED: without this contract, a later key loader could accidentally make
  RedDog runtime possession of an `op://` string equivalent to authority, or
  could resolve plaintext private key bytes inside a plugin-loaded process.

## 2. Contract Boundary

The SignerKeyProvider is a signer-domain boundary only. It lives inside the
isolated signer principal described by E0. The RedDog runtime may request a
signature through the socket protocol; it must not provide, read, log, or derive
the secret references or secret values used by this provider.

SPECIFIED_NOT_IMPLEMENTED:

```yaml
SignerKeyProviderProfile:
  signer_profile_id: string          # stable signer-owned profile id
  signer_agent_id: string            # WSP 71 permission principal, signer-owned
  signing_key_ref: string            # op:// reference, signer-owned config
  audit_mac_key_ref: string          # op:// reference, distinct from signing_key_ref
  expected_public_key: string        # ed25519-pub-v1 public material
  expected_key_fingerprint: string   # derived from expected_public_key only
  expected_key_epoch: string         # current signing generation
  permission_snapshot_digest: string # signer-side permission snapshot digest
  ttl_seconds: integer               # max age for resolved value at use time

SignerKeyProviderResult:
  ok: boolean
  rejection_code: string | null
  signer_profile_id: string
  key_epoch: string | null
  public_key: string | null
  key_fingerprint: string | null
  reference_hashes:
    signing_key_ref_hash: string | null
    audit_mac_key_ref_hash: string | null
  ttl_remaining_seconds: integer | null
  secret_values_returned: false
```

Field names above are frozen for the next implementation slice. A future code
slice may add language-specific wrapper fields only if they are excluded from
receipts and static tests prove no secret value can serialize.

## 3. Rules

### 3a. Runtime authority

- The RedDog runtime never sends `signing_key_ref` or `audit_mac_key_ref` over
  the signer socket.
- The runtime never learns the signing key reference, audit key reference,
  plaintext key bytes, or audit-MAC key material.
- Possession of an `op://` reference string is not authority. WSP 71
  permission-validated retrieval by `signer_agent_id` is authority input.
- The provider must fail closed when the signer principal lacks `SECRETS_READ`,
  when the permission snapshot is stale, or when the resolver is unavailable.

### 3b. Resolver and vault requirements

- Production code must not use `MockVaultResolver` as the credential authority.
  It may be used only in tests and dry-run fixtures labeled test-only.
- Secret references must match the WSP 71 `op://vault/item/field` shape.
- Secret values must never appear in `repr`, `str`, logs, exceptions, receipts,
  terminal output, prompts, Copy-MD, HoloIndex, or Git history.
- A resolver result that contains a secret value is consumed only inside the
  signer principal and is converted immediately into signer-local key objects.
- TTL is enforced at use time. A value that expires between resolve and sign is
  rejected and must be re-resolved.

### 3c. Key material

- Signing key material and audit-MAC key material are separate secrets. A single
  reference used for both fails closed.
- The signing key must decode to Ed25519 private key material supported by the
  signer backend. Unsupported key formats fail closed.
- The public key derived from private key material must match
  `expected_public_key`.
- `expected_key_fingerprint` and all response fingerprints are derived only from public verification material.
  They must never be `sha256(secret)`.
- The provider resolves the current signing key only. Previous key epochs are
  verify-only and must not be loadable for signing.

### 3d. Audit MAC

- The audit-MAC key is signer-held and distinct from the signing key.
- Audit MACs are keyed or predecessor-chained over signer-side values the
  caller cannot provide or predict.
- A provider that cannot construct a non-empty audit-MAC builder fails closed.

### 3e. Error behavior

Failure reasons must be coarse and non-secret-bearing:

```text
FAIL_PROVIDER_PROFILE_INVALID
FAIL_PROVIDER_PERMISSION_DENIED
FAIL_PROVIDER_RESOLVER_UNAVAILABLE
FAIL_PROVIDER_REFERENCE_INVALID
FAIL_PROVIDER_REFERENCE_FORBIDDEN
FAIL_PROVIDER_TTL_EXPIRED
FAIL_PROVIDER_KEY_FORMAT
FAIL_PROVIDER_PUBLIC_KEY_MISMATCH
FAIL_PROVIDER_FINGERPRINT_MISMATCH
FAIL_PROVIDER_AUDIT_KEY_MISSING
FAIL_PROVIDER_MOCK_IN_PRODUCTION
```

Failures must not include expected public key fragments, secret lengths, vault
item names beyond reference hashes, or positional comparison details.

## 4. HoloIndex Boundary

HoloIndex may be queried before and after this slice to detect discoverability.
RedDog and the signer provider must not re-index HoloIndex during a reasoning,
signing, or authority issuance run.

INDEX_GAP for this slice:

```text
HOLOINDEX_REDDOG_SIGNER_KEY_PROVIDER_CONTRACT_INDEX_GAP_PHASE1
```

If a later runtime cannot find this contract semantically, the correct response
is a governed WRE or CI indexing work item, not signer-side re-indexing.

## 5. Required Tests For The Next Implementation Slice

The next implementation slice must include tests proving:

- Default path fails closed without an injected provider profile.
- `MockVaultResolver` is accepted only in test-only or dry-run mode and rejected
  for production.
- `signing_key_ref == audit_mac_key_ref` fails closed.
- A stale permission snapshot fails closed.
- A resolver unavailable result fails closed.
- A bad `op://` reference fails closed.
- Unsupported key encoding fails closed.
- Public key mismatch fails closed.
- Fingerprint mismatch fails closed.
- Secret values are absent from result serialization, logs, exceptions, and
  receipts.
- No environment variable, argv, shell command, repo file, OpenClaw, Hermes,
  WRE enqueue, or HoloIndex mutation is used.

## 6. Sequence

This contract does not authorize live signing. The next valid sequence is:

```text
REDDOG_SIGNER_KEY_PROVIDER_CONTRACT_PHASE1
-> REDDOG_SIGNER_KEY_PROVIDER_DRYRUN_PHASE1
-> REDDOG_SIGNER_SOCKET_PEER_CREDENTIAL_ATTESTOR_PHASE1
-> REDDOG_ISOLATED_SIGNER_PROCESS_ENTRYPOINT_PHASE1
-> REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_WIRING_PHASE1
-> bounded RedDog authority pilot
```

The dry-run provider may use injected test-only key material. Production vault resolution, OS-principal setup,
and live signing remain blocked until separately authorized.

## 7. Truth Boundary Checklist

- NO_KEY_GENERATION: PASS
- NO_KEY_LOADING: PASS
- NO_VAULT_CONFIGURATION: PASS
- NO_SIGNER_PROCESS_LAUNCH: PASS
- NO_SOCKET_BINDING: PASS
- NO_REPO_MUTATION: PASS
- NO_OPENCLAW_HERMES_WRE_WIRING: PASS
- NO_HOLOINDEX_REINDEX: PASS
- DOCS_AND_STATIC_TESTS_ONLY: PASS

## 8. Verdict

Proceed with this contract before any signer key provider implementation.
RedDog cannot become an autonomous executor until it can obtain authority from a
signer whose key material is not reachable by RedDog's plugin-loaded runtime.
This slice defines that boundary and keeps the private-key handling step
SPECIFIED_NOT_IMPLEMENTED.
