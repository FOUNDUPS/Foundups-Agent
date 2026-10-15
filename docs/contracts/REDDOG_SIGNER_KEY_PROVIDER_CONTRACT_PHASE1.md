# REDDOG_SIGNER_KEY_PROVIDER_CONTRACT_PHASE1

Status: The original Phase1 specification below is decision-only. The
[current composition contracts](#current-composition-contracts--2026-10-15) record
implemented source interfaces; they do not authorize installation or native use.
The original specification performed no runtime key loading, no key generation,
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
- The op provider requires the WSP 71 `op://vault/item/field` shape. The explicit
  local-custody extension (2026-10-05) permits a homogeneous pair of
  `systemd-creds://<credential-id>` references in the lower provider profile.
  It requires the separately bound systemd resolver described in
  `modules/infrastructure/secrets_mcp/INTERFACE.md`; reference possession remains
  insufficient. Mixed backend pairs reject. This extension does not activate
  the public startup/configuration path or supersede its admission requirements.
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

## Current composition contracts — 2026-10-15

These active contracts extend the credential and E0 boundary above. Source
implementation is component-qualified; authenticated deployment and custody
remain required. The earlier Phase1 sequence and verdict record that phase.
Return to the [module interface](../../modules/communication/moltbot_bridge/INTERFACE.md)
for adjacent generation, bootstrap and consumer contracts.

## Issuer-only root LOAD — 2026-10-15

Root revocation wire v2 binds `requester_role=grant_issuer`, requester principal
and key epoch to the signed LOAD request. The existing v1 target projection and
signing domain remain unchanged. The issuer-specific anchor factory and
`RootAuthorizedSignerGrantRevocationOracle` construction permit LOAD and issuer
key-epoch checks only; target protected-use and revocation mutations reject.
The installed owner supplies the issuer UID/GID. Root socket transport access
must also be provisioned; peer authentication does not grant filesystem access.

`authorize_current_grant_authority_wsp71_use` captures authenticated permission
state under the generation lease, releases it for root LOAD, then reacquires
and compares authority/receipt/binding state before and after the action.
Expiry is rechecked at use; refreshed selection timestamps alone are not an
identity change. Custody and runtime installation remain separate contracts.


## Callable LOW grant service — 2026-10-15

`src/reddog_grant_authority_service.py` exports `serve_grant_authority_once(*,
repo_root, owner_config_path, dependencies=None, timeout_s=5.0,
ready_callback=None)`. It returns `GrantAuthorityServiceResult` and serves at
most one request through the existing bounded socket owner after admission.
There is no CLI, installation path or installed-dependency loader.

`GrantAuthorityServiceDependencies` contains the current `owner_policy`,
`issuer_profile`, `credential_binding`, durable `replay_store` and root-authorized
`revocation_oracle`. Construction conveys no authority. The callable freezes
the policy, checks owner/profile/reference/replay bindings, requires distinct
signing and audit credential IDs, and applies existing peer/process-isolation
and current permission gates before listening. Owner scope must be exactly
`signer_socket_peer_handshake`, LOW, with empty consensus requirements.

Each request must use the existing secret-grant signing operation, LOW tier,
no consensus proof and the bound requester peer. Permission/revocation are
renewed around current-input validation, ephemeral custody, signing and return.
The existing durable rate authority survives fresh per-request backend creation;
consumer replay enforcement remains in the existing grant-consumption path.
This service does not bootstrap through the target's grant-required backend.

Result fields are `accepted`, `rejection_reasons`, `requests_handled`,
`response_digests` and `socket_removed`. `accepted` describes transport completion,
not grant acceptance, native isolation or RSI. Inspect and independently verify
the signing response. The wrapper does not propagate the socket owner's
no-secret flags as claims about this credential-using composition.

The next installation dependency is an independently authorized root LOAD
request signer with the required identity, followed by protected dependency/
custody supply and authenticated installed-source deployment. Role-key possession,
the callable and a successful fixture socket exchange do not establish these gates.

The shared resident socket owner keeps its POSIX listener open through owned-path
cleanup on both normal and exceptional exits, then closes it. Its private path
identity also compares change-time nanoseconds to reject stale inode metadata.
The timestamp is supplemental defense, not an atomic unlink guarantee; cleanup
still depends on the existing protected-parent trust boundary. Non-POSIX retains
close-before-unlink behavior. Replacement paths are preserved on identity mismatch.


## Protected issuer startup custody — 2026-10-16

`materialize_grant_authority_runtime_dependencies(*, owner_config_path, repo_root,
expected_owner_config_id)` loads protected owner v9 and returns the existing
`GrantAuthorityServiceDependencies` for `serve_grant_authority_once`. It installs
nothing and does not issue grants. Owner v1–v8 schemas retain their old fields.

The v9 `grant_startup_custody` block contains `signing_key_ref`,
`audit_mac_key_ref`, `credential_binding`, `loader_credential_binding`,
`root_load_permission` and `replay_integrity_permission`. Signing custody names
exactly signing/audit IDs; loader custody names exactly signing/replay IDs in
the same protected directory. The three references must be distinct. Signing
requester is the current E0 signer-agent ID; loader requester is the current
issuer principal. Both bind its UID/GID and current key/epoch; its UID must differ
from the target's. The
issuer's UID, identity and proof key cannot substitute for target authority.

Metadata does not grant permission: current authenticated E0 binds actual refs,
profile, receipt, key and scope. Isolation precedes replay credential access.
The existing resolver, durable replay owner and issuer-only root LOAD oracle
are reused. No E0 generation lease spans root RPC; owner/full-policy/custody/time
are revalidated after RPC and before returning. Each proof signing operation
rechecks purpose, requester, identity and expiry through existing custody.

The loader remains a callable with tested synthetic installation boundaries.
Authenticated installed-runtime deployment, real custody provisioning and a
native LOW request remain prerequisites; this is not a new service launcher.

## Installed source empty-file semantics — 2026-10-16

The initial enrollment authority's protected source inventory permits zero-byte
files, including package initializers, only with their exact approved SHA256.
Its existing root-owned descriptor reader opts in explicitly; authority/config
reads retain nonempty defaults. Source reads retain the64KiB maximum, protected
root ancestry, regular-file ownership checks and no-follow descriptor access.
This does not certify the interpreter/native closure, grant profile enrollment,
worker admission or retained learning. Those remain distinct gates.

## Installed issuer preparation — 2026-10-16

`compose_installed_grant_service_artifacts(profile, owner_config_id,
repo_root_digest, source_descriptor)` uses keyword-only inputs and returns
canonical bytes for config v3, run-packet v2 and installed-source descriptor v1.
`validate_installed_grant_service_artifacts(artifacts)` checks exact members,
canonical bytes, identities and cross-digests; it performs no I/O or admission.
`validate_installed_grant_source(...)` binds declared inventory and fixed Python
launch/import paths, service and dependency-loader callables. Protected runtime
inspection and root-approved source provenance must independently validate it.

E0 `reddog-signer-owner-e0-policy.v10` replaces
`grant_authority_archive_source_descriptor_digest` with
`grant_authority_installed_runtime_descriptor_digest`. The latter participates
in the stable pre-config binding. Future permission/manifest/config fields stay
required and signed in the final policy. V10 requires generation1 and only LOW
`signer_socket_peer_handshake`, with no consensus tiers. V5–v9 projections and
signing domains remain unchanged. Current legacy manifest/permission execution
rejects v10 until its explicit authenticated enrollment/consumer is connected.

## Initial handshake configuration — 2026-10-15

`compose_initial_handshake_service_config(...)` in the existing
`reddog_signer_socket_service_config_composition.py` returns a validated public
`reddog_initial_handshake_service_config.v1` mapping; it does not write files,
issue grants or resolve credentials. Keyword inputs: repo/runtime/signer roots,
socket path, one key-provider profile, peer policy, E0 authority binding digest,
timeout and request/response byte limits. The schema fixes `max_requests=1`,
WSP71 permissioned provider mode and `allow_test_only_key_material=false`.

The typed `initial_handshake_only` mode admits exactly generation1 and the
`reddog-work-authority` / `signer:reddog` profile with distinct signing/MAC refs.
The writable socket parent is separate from immutable artifacts and signer
state; startup checks also preserve authority/replay/revocation separation.
Mixed work/control/proposal/outcome/conversation policies are rejected.
Authenticated E0 scope must be exactly `signer_socket_peer_handshake`, LOW, with
no consensus authorities. HIGH/ULTRA rules for other configurations are unchanged.
JSON policy lists become canonical immutable tuples after validation.

Non-handshake requests reject before grant consumption/key resolution and again
under the current-generation owner lease with exact peer-instance binding.
Manifest authenticity, E0 scope and request grants remain independent gates.
The separate production grant issuer composition and real native admission are
still required; this schema does not certify their availability.

## Installed issuer startup — 2026-10-16

`serve_installed_grant_authority_once(*, repo_root, owner_config_path,
expected_owner_config_id, timeout_s=5.0)` uses only the fixed protected dependency
loader then `serve_grant_authority_once`. Timeout must be a finite numeric value
in(0,30]; boolean values reject. Old direct calls without dependencies still
reject. The fixed `main` accepts only repo root, owner-authority-config and exact
expected-owner-config-id; it prints the existing result and returns0/2. Success
means bounded transport completion, not grant acceptance or RSI.

Installed E0v10 metadata is authenticated against current owner selection, fixed
protected approval and exact manifest/artifact/config/source bindings. Only the
explicit installed binding permits an empty archive field; legacy evidence stays
mandatory. The issuer guard checks the authenticated descriptor against its
current Linux3.12 isolated process, read-only root, static inventory and mapped
files. It runs before replay secrets, service custody and root-LOAD proof keys;
root-LOAD permission freshness is rechecked after the guard and after signing.
The generic consumer is usable outside that issuer runtime and claims no local
confinement. Checks are sampled, trusting host root/kernel, not immutable future
execution or authentication of seccomp filter rules.

Owner v10 adds an issuer-private `grant_rate_store` with purpose
`grant-issuer-rate.v1` and distinct nonce/high-water paths, store ID, binding and
durability receipt. Its integrity permission uses `grant-issuer-rate-integrity.v1`.
Full signed E0 already binds owner_config_id; its schema staysv10. Target replay
identity is unchanged and derived from protected metadata without issuer access
to target-private files. Legacy owner v9 retains its coupled-store behavior.

The installed Python invocation must establish the descriptor's exact sys.path
through its protected fixed bootstrap before calling main; bare isolated
`python -m` does not make `/opt/grant-source` importable. Runtime installation,
credential delivery, permissions, root authority and actual worker admission are
separate gates. This callable/CLI does not create them.
