# OpenClaw Bridge = 012's Digital Twin

## Canonical elevated-authority consensus capability

[OBSERVED] HIGH delegated-authority requests can now be projected onto exact
identity and work-authority signer requests, verified against current policy,
sovereign authorization, distinct signed reviewer decisions, model/runtime
evidence, and signer-side transactional replay admission. The resulting process-local
capability is non-constructible, non-copyable, non-serializable, and usable only
for its exact two child requests. The signer re-verifies the complete proof at
the independent secret-grant boundary before key resolution.

[OBSERVED] Signed child inputs must be byte-canonical JSON with no duplicate
keys, and their payload digest is recomputed before consensus projection.
Elevated grant-authority transport is socket v2 only. Principal and RedDog
children use distinct target-bound grant-provider identities. Signer replay state is
reserved before policy/signing and committed only after an accepted signature;
every prior rejection rolls it back.

[SPECIFIED_NOT_IMPLEMENTED] Production HIGH authority remains fail closed. The
signed E0 generation does not yet supply authenticated author runtime evidence,
reviewer provider membership, reviewer keys/runtime evidence, exact sovereign
delegated-request authorization, or the durable consensus nonce authority. Production signer
composition therefore does not instantiate this path. ULTRA remains closed.

## Independent signer secret-grant provider

[OBSERVED] Production grant-authority effects now require signed owner policy
v7 and signed runtime-artifact manifest v3. Both bind one exact repository-root
digest, authorized Git commit, Git object format, canonical source-policy
digest, and archive source-descriptor digest. Manifest production, isolated
signer admission, current E0 rehydration, and the final WSP 71 callback each
re-verify the exact committed archive lineage. Legacy v6/v2 remains readable
for diagnostics but cannot reach the WSP 71 effect callback.

[OBSERVED] The authorized commit must agree across the top-level authority
profile, operational-context binding, and embedded proposal admission. Dirty
checkout bytes, alternate committed sources, attacker-selected source maps,
replacement refs, inherited Git authority variables, rehashed artifacts, and
re-signed legacy manifests do not establish effect authority.

[OBSERVED] Grant-authority service archive bytes now use one deterministic,
uncompressed zipapp representation. Production manifest creation and use-time
grant-manifest rehydration both reject noncanonical ZIP metadata, traversal,
links, duplicate members, compression, trailing bytes, changed member digests,
missing package initializers, unresolved direct archive-local imports, common
dynamic-loader spellings, standard-library shadowing, and an entrypoint that the fixed shim
cannot call. Every Python member and the complete claimed-source descriptor are
bound by the inner manifest; the signed outer runtime manifest still binds the
exact archive bytes.

[OBSERVED] A separate v2 build-provenance foundation can construct the archive
only from exact committed Git blobs and independently verify every
non-synthetic member against the same commit tree and an explicit source-path
policy. Dirty checkout bytes, uncommitted files, arbitrary committed source
paths, object-ID substitution, and v1 claimed-commit metadata do not satisfy
that verifier. Git replacement objects and inherited `GIT_*` authority
overrides are disabled; aggregate blob reads use one bounded batch process.
The verifier also requires independent expected repository-root, commit,
object-format, and source-policy digests.

[SPECIFIED_NOT_IMPLEMENTED] This remains archive admission, not a Python
sandbox or hermetic-runtime claim. Python reflection is not certified safe by
AST inspection. Interpreter,
standard-library, external executable, OS-principal, resolver, socket,
supervision, crash-recovery, pinned-descriptor execution, and production
archive-build authority remain unimplemented and block all execution.

[OBSERVED] Signed owner policy v6 preserves v5 validation while adding an exact
grant-service signer profile, public identity, pairwise-distinct key-reference
hashes, permission evidence identifiers, manifest generation, config, and run
packet. Signed runtime-artifact manifest v2 covers exactly one bounded
content-addressed service archive, one exact public config, and one inert run
packet. Each binding reloads current signed E0 and securely re-reads every
artifact under the existing runtime-generation lock. The immutable result
contains hashes only. Public agent, profile, and epoch fields use exact inert
grammars; URI-shaped or raw vault references are rejected by this boundary.

[OBSERVED] Downgraded v1 manifests, altered bytes including archive tails past
one MiB, substituted profile identity or key references, policy/manifest
disagreement, unknown config fields, and run-packet/archive disagreement reject
before service start or WSP 71 resolution.

[OBSERVED] The bounded provider foundation can obtain a LOW-tier secret grant
from a separately bound Ed25519 grant signer while one current-generation E0
lease remains held through target-signature rehydration. It reuses the isolated
signer, WSP 71 backend factory, signed owner policy and durable replay/high-water
store.

[OBSERVED] Owner config v3 can now bind a disjoint grant-authority root, fixed
Unix socket, and exact non-root UID/GID. The uncomposed client supply verifies
authenticated current-generation E0 admission, rejects link components, pins
the protected socket identity, verifies `SO_PEERCRED`, rejects overlap with
target, outcome, replay, and revocation authority, and derives the public grant
identity only from authenticated signed owner policy v5.

[OBSERVED] Owner config v4 additively binds the complete canonical
grant-service archive-to-repository source map and its digest to the existing
root-owned signer configuration. The loader returns only an opaque,
process-local capability whose sole admission method re-reads the current
owner configuration, so caller-selected or stale source policies cannot
become build authority. V3 remains readable for the existing grant client but
cannot issue source-policy authority.

[OBSERVED] The existing atomic signer-generation provisioner now has one fixed
grant-authority profile factory. It consumes the v4 source-policy capability,
requires grant config v2 to bind the owner-config, repository-root, and source-
policy digests, revalidates exact-Git provenance during manifest production,
commit guarding, and recovery, and activates only the three profile-specific
artifacts. A root-owner operation fence serializes compliant owner rotation;
replacement observed by the final transactional commit guard rolls back both
anchor and high-water state. Later replacement makes the generation stale at
the existing use-time authority boundary.

[SPECIFIED_NOT_IMPLEMENTED] Atomic activation is not service launch or live
authority. External lifecycle supervision, pinned-descriptor execution,
interpreter/OS-principal isolation, secret resolution, and the production live
canary remain blocked. Legacy config v1 remains readable for established
diagnostic paths but cannot enter the new grant-profile provisioner. No
production bootstrap invokes this provisioning foundation yet.

[OBSERVED] Grant-service WSP 71 permission evidence is now an exact canonical
receipt, not a SHA-shaped identifier. Admission securely reads the fixed
root-confined artifact and recomputes both its full-byte digest and receipt ID
while the authenticated current-generation E0 lease remains held. The acyclic
chain is receipt -> service config -> authenticated service manifest -> signed
E0 policy. The receipt binds the root-selected generation, issuer,
agent/profile, key-reference hashes, `SECRETS_READ`, and `get_secret`. No
reusable permission object is released. One callback runs while both the E0
lease and matching durable revocation writer fence remain held, with key-epoch
revocation and expiry checked before and after use. Generation, grant,
revocation, and target-signer public keys must remain role-distinct.
Repository-write permission snapshots, grant-authority-only rehashes,
wrong-policy oracles, oversized canonical-prefix tails, noncanonical JSON, and
detached authority reject.

[SPECIFIED_NOT_IMPLEMENTED] Permission-receipt rehydration is implemented, but
receipt-specific revocation is not added to the
secret-grant ID namespace; rotation, expiry, and issuer-key revocation remain
the admitted controls. This foundation cannot activate the production
authoritative-use path: HIGH now accepts only the canonical opaque consensus
capability, but grant-service lifecycle and signer-service composition remain
absent. ULTRA, root-owned service provisioning,
distinct-OS-principal supervision and the live canary remain unimplemented.

## Root-served signer-revocation anchor

The existing root verified-outcome Unix service now routes a domain-separated
revocation protocol. An opaque signer-side client sends the current signed E0
policy and requested signed snapshot ID; the root service independently holds
the current-generation selection lease, validates policy authorities and exact
topology, reads the local durable snapshot and witness, derives the monotonic
high-water value, and advances the existing three-domain root state. Callers
cannot supply arbitrary expected or next values, receive a root-state object,
or construct/copy/serialize either service authority. Signed request nonces,
kernel peer credentials, signer-key proofs, bounded ASCII messages, exact
response context, CAS convergence, and lost-response retry are fail closed.

The same root service now also linearizes one exact signer callback against
revocation. It consumes a signed, request-bound protected-use ID durably,
marks one global odd-sequence use active, blocks revocation advancement until
an exact FINISH, and retains replay evidence after completion. The signer
boundary accepts only the factory-issued root capability; the older durable
oracle alone remains explicitly non-atomic. A lost FINISH response retries
idempotently, while a crashed active use remains fail closed.

This closes the revocation-check-to-sign race but does not activate production
signing. Independent grant issuance, WSP 71 secret resolution, signer lifecycle
activation, worker/repository/PR/merge effects, and HoloIndex mutation remain
unavailable.

## External signer exact-effect authority

The bridge now contains the smallest reusable authoritative-use lease primitive.
It extends the existing E0 secret-grant and isolated signer socket instead of
adding a signer or trust store. A strict signed request can be rehydrated into
one opaque, process-local, one-shot capability for an exact worktree-create or
live-enqueue request. The capability cannot be directly constructed, copied,
pickled, or replayed. The signer recomputes the complete typed effect digest,
requires socket v2 plus the exact one-use E0 grant, and checks the root-selected
manifest, generation, owner config, run packet, session, and socket identity.
Client rehydration uses the same durable E0 replay root and current root-owned
generation artifacts. The current config selects the exact signer profile,
public key, and key epoch; all four E0 replay-store identities are signed and
checked both signer-side and client-side. Lease expiry cannot exceed the current
generation and process-local monotonic expiry prevents wall-clock rollback
revival. Callers cannot inject verifier, replay, time, or parent-authority
verdicts.

This is a foundation, not production activation. Worktree admission and direct
WRE integration seams accept the capability, but the repository supplies no
local grant issuer and the resident resolver never supplies a production lease.
Queue, OpenClaw, Hermes, shell, PR, merge, learning, and HoloIndex effects remain
fail closed until their independent exact-effect and crash-recovery gates exist.

## Principal Memex resident admission

The backend architect can consume one opaque Principal Memex context prepared
from the current signed `principal` conversation scope. Preparation consumes
the existing conversation-scope capability and verifies a separate
principal-signed disclosure. Use time reloads the exact AgentDB revision,
rechecks the model-runtime binding, expiry and revocation, then atomically
consumes the disclosure nonce in the authority runtime store. Only public
accepted `operator_statement` decisions reach model context. Rejected options,
open questions, objectives, credentials, raw history, and FoundUp state do not.
The admitted receipt and context are deeply immutable, revalidated immediately
before use, and duplicate-cycle identity excludes volatile disclosure metadata.

The editor resident bridge can accept one complete pre-issued Principal Memex
disclosure tuple. It deletes the tuple from SecretStorage before the bridge
call and removes it before intent persistence. Python authenticates the current
session, atomically separates FoundUp and Principal scope capabilities, and
defers Principal admission until audit collection and the durable cycle's final
RUNNING checkpoint. The editor retains the packet only in a process-local
closure and serializes all SecretStorage effects across concurrent calls.
The editor restores it only when the durable cycle explicitly reports
`consumed=false`; final admission, an indeterminate result, or bridge failure
retires it. The bridge returns no disclosure content.
Only the final backend architect call can consume the
signed subset of accepted public decisions, in signed order, after a fresh
expiry check. Audit workers, AgentDB, receipts, logs, and status output never
receive Principal Memex content.

Direct statement reproduction is rejected before persistence, including
ordered cross-field, JSON-escaped, and Unicode-disguised forms. A
Memex-informed run persists no model-authored free text or proposal body; only
a report-bound action/slice, fixed advisory metadata, and opaque evidence
digests survive, and no queue candidate is emitted.

This path grants no work, repository, signer, merge, FoundUp-projection, or
HoloIndex authority. Principal Memex disclosure issuance, automatic learning,
and conversation-to-work authorization remain separate work.

The isolated Ed25519 backend also rejects delegated identity or work-authority
requests unless the backend has a signer-owned domain policy or the existing
E0 secret-access grant has bound one ephemeral backend to the exact canonical
signing-request digest. A loaded key profile is not signing authority.

## RedDog conversational state boundary

RedDog has an AgentDB-backed authenticated conversation-scope runtime. It
stores only typed, bounded continuity state; raw provider history is never
stored by this runtime. Every scope requires a fresh principal-signed session.
`foundup` scope additionally requires current repository, FoundUp, snapshot,
and HoloIndex grounding. `principal` and `comparison` scopes forbid those
operational bindings and cannot enter work promotion. Comparison permits only
two or more FoundUps already in the principal credential and never unions their
authority. Expiry, principal key, transport/session, or turn lineage fails closed.

This state helps RedDog interpret follow-up requests. It is not work authority.
The backend can now bind one authenticated scope revision and resident intent
to an immutable architect proposal preview. AgentDB persists the exact pending
proposal by CAS. Promotion then requires both a fresh one-use pending-proposal
capability and the existing principal-signed proposal policy authorization.
The binding covers the operational snapshot, repository HEAD, HoloIndex
generation/freshness receipt, FoundUp, grounding receipt, and intent.

Conversation state and the pending capability do not grant work authority.
Only a `foundup` scope may request the existing proposal-promotion chain.
WRE/OpenClaw/Hermes dispatch, repository mutation, and merge remain downstream
gates. The extension now has a public-key-only authenticated-session source.
Durable conversation-state consumption remains blocked until that source
receipt is bound into the P1 state lifecycle.

## Upstream Agent Execution Boundary

RedDog's bounded author stage can use the installed upstream agent runtimes,
not repository-local classes that merely carry their names:

- `openclaw_gateway` invokes `/usr/local/bin/openclaw agent` through the
  upstream loopback Gateway. It requires a dedicated sandboxed agent, a live
  version-matched Gateway, no elevated mode, exactly one canonical read-only
  sandbox workspace mount, and a wildcard tool deny policy. OpenClaw
  generates the artifact map; the existing Foundups writer alone materializes
  the already-authorized paths in the isolated worktree.
- `hermes_api` calls the installed upstream Hermes Agent `/v1/runs` API through
  authenticated loopback HTTP. It requires the fixed `reddogartifact` profile,
  the pinned upstream version, bearer authentication, a complete disabled
  API-server toolset inventory, zero visible skills, and the same closed surface
  after the run. The adapter drains the complete run-event queue and rejects
  any tool, approval, or subagent event, including events overwritten in the
  pollable `last_event` field. Hermes performs text generation only; Foundups retains all
  file, worktree, commit, verification, PR, and merge effects.

Both modes consume the existing signed model-runtime binding and remain below
the AgentDB/WRE work-order, WSP 15, exact-path, commit, and independent-verifier
authority chain. Provider invocation and worker-process effects are recorded
in the resident-cycle result instead of being reported as dry-run purity.
`foundups_fusion` remains supported; unknown provider modes fail closed. The
legacy repository `HermesJobExecutor` is not used by this route and no local
class is presented as the upstream Hermes runtime.

The Hermes bearer key is read only from
`<resident-runtime-root>/hermes-api/api-key` through the confined runtime-file
reader. It never appears in prompts, argv, receipts, logs, or repository files.
The upstream Hermes API currently executes tools in its server process and does
not expose split-runtime confinement. Therefore any enabled toolset, visible
skill, approval request, tool event, subagent event, or pre/post-run policy
drift rejects the artifact result. This is an artifact-generation adapter, not
Hermes shell authority.

The external signer uses a stable signer-owned system-service command:
`reddog_signer_system_service_entrypoint`. Its v2 run packet contains the
rotating current-generation configuration, but the service manager receives
only the fixed repository root and root-owned owner-authority configuration
path. The entrypoint revalidates the authenticated current generation before
service admission and never executes packet argv. The signer-side E0 boundary
now verifies one request-bound secret-access grant, atomically consumes durable
replay state, resolves WSP71 keys for that sign only, and rechecks revocation,
expiry, provider identity, and the returned signature. The stable entrypoint
now applies the executable OS-isolation boundary before resolver construction.
An uncomposed WSP71 factory reuses `OpCliSecretResolver` and accepts only a
fixed root-owned, executable, non-writable `/usr/bin/op`. The production
entrypoint retains its unavailable resolver until the existing grant-aware
resolve-per-sign backend is composed, so system-service signing fails closed.
The owner-controlled E0 admission layer binds one signed
policy to the exact current signer generation, key-reference digests,
manifest-bound grant/revocation authorities, disjoint durable-state roots,
operation/tier consensus rules, and rate limits. Its opaque one-use capability
cannot be copied or serialized. Consumption revalidates while the canonical
current-generation fence is held and returns only a non-authoritative receipt;
it does not release signer composition authority or grant an effect.
The E0 path also has an exact independently signed revocation-snapshot contract
bound to the current policy, generation, store, and target signer. Grant and
revocation authority identities remain separate from one another and from the
target signer key. Policy v3 additionally freezes the exact primary store,
separate local monotonic witness, and shared cross-process operation-lock
topology plus the identity, durability receipt, and three-domain topology
digest of a root-owned monotonic anchor. The revocation high-water is mirrored
by that authority's primary and witness stores; its third installation store
authenticates initialization but does not witness each high-water update. The append-only SQLite supply orders
prepare, local witness, root anchor, and finalize; it recovers each publication
crash window without unrevocation. Its detached oracle requires three-way
agreement under the same lock. Coordinated rollback of the two local domains
therefore rejects while the root anchor remains intact. Expired state remains unusable, while a locked
publisher may authenticate an expired predecessor solely to append its fresh,
monotonic successor. Canonical snapshot validation remains a separate bounded
module from authority/signature verification. This is a partially composed durability
foundation, not production authority: root-service transport/client and the atomic
protected-use oracle now exist; independently administered grant issuance, production
backend-factory wiring, and stable signer lifecycle composition remain absent. Root compromise or coordinated rollback of both
mutable root-state mirrors is outside this foundation's claim; leaving the
static installation store unchanged does not detect that rollback. Future
composition must consume the opaque root-owned service boundary rather than a
caller-constructed state object.
RedDog and `main.py` remain clients and cannot spawn the signer.
The older `reddog_signer_socket_service_runtime_cli` is retained only to return
a structured retirement rejection. It cannot load authority, construct a
secret resolver, or bind a socket. The system-service entrypoint also loads the
current generation, a lazy outcome-authority supplier, and exact signer UID/GID
from one immutable v2 read. The supplier runs only for a selected outcome policy;
the live process must match both
identity values before resolver construction. The older one-shot
`reddog_isolated_signer_process_entrypoint` accepts test-only dry-run providers
only; every WSP71/production provider mode rejects before key resolution.
Legacy v1 owner configs remain readable by the lower-level manifest migration
loader but cannot start the production signer service.

Verified-outcome admission also requires the separately supervised root service:

```bash
python -m modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_provision_entrypoint \
  --repo-root /srv/foundups-agent \
  --owner-authority-config /etc/foundups/reddog-signer-owner.json

python -m modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service_entrypoint \
  --repo-root /srv/foundups-agent \
  --owner-authority-config /etc/foundups/reddog-signer-owner.json
```

The primary/witness state and generation anchor are provisioned once by the
separate root installer. A third disjoint installation witness commits that
provisioning event; later replay-store deletion cannot invoke the installer to
reopen consumed grants. Runtime startup has no state-reset or initialization
switch. The service loads no private signing key and grants no
repository, queue, worker, PR, or merge authority.
Each live owner-config reload also binds the resolved roots, database paths,
store IDs, and durability receipts for all three state domains. Store rotation
requires a supervised service restart; a running service never combines a new
config with stores opened from an older config. Before any production WSP71
key resolution, the existing isolated-signer entrypoint enforces a distinct
non-root signer UID/GID exactly matching the root-owned owner config, YAMA
ptrace protection, absence of `CAP_SYS_PTRACE`,
`RLIMIT_CORE=0`, `PR_SET_DUMPABLE=0`, and a cleared inherited environment.
Test-only dry-run keys remain non-authoritative and do not claim this boundary.

`start operations` binds the production `reddog_operations` Skillz from the
manifest-authenticated runtime before model selection or grounding. The
Skillz defines only logical roles and WSP_00/WSP_97/WSP_15 operating
discipline; actual models are selected by the existing signed audit and
architect runtime-binding receipts. Its content and registry-entry digests
are carried on the durable intent and revalidated at submit/resume use time.
A missing, retired, model-pinned, role-drifted, or otherwise unhealthy Skillz
fails closed before a model or resident client is invoked. The read-only
Start Operations authority boundary is unchanged.

Governed read-only audit and backend-architect FoundUps Fusion calls now use
`reddog_provider_call_evidence.v1`. The content-free receipt binds task/work
lineage, the validated runtime-model binding, requested identity, a
domain-separated redacted-input request digest, exact response bytes by digest
and count, bounded numeric usage, and only explicitly returned served identity.
The outside-repository store path is supplied by
`REDDOG_PROVIDER_CALL_EVIDENCE_STORE_PATH`; absence or a failed PRECALL/arm
write blocks the provider call. Terminal-write uncertainty remains durably
`INDETERMINATE` and cannot be promoted or automatically retried. Requested and
served providers use a canonical provider-slug grammar; requested and served
models use a distinct `provider/model` grammar. URI, filesystem, traversal,
dot-segment, query/fragment, bearer-like, high-entropy, and raw-sentence shapes
fail closed.
Post-invocation failures carry the last content-free local evidence to the
audit/architect result even when extraction, terminal persistence, and
recovery reads fail. Audit and architect acceptance independently revalidate
the canonical receipt and its exact surface, complete task/work/queue/run/cycle
lineage, runtime binding, requested runtime identity, attempted state, and
`COMPLETED` outcome before a report or queue candidate can be accepted.
Unbound lineage fields must remain null.

RedDog Fusion progress observability is implemented by `src/reddog_fusion_progress_receipt.py`: bounded hash-chained stage events plus content-free OpenRouter usage and routing receipts. The original frozen `reddog_fusion_progress_receipt.v1` shape remains valid; generic provider evidence is an all-or-none optional v1 extension. It does not retain prompts, outputs, hidden reasoning, or secrets, and it grants no action authority.

The durable resident architect cycle in `src/reddog_resident_architect_durable_agentdb_cycle.py` is intent-digest-bound and revision-CAS protected. Its nine process-local read-only self-attestations are persisted and enforced at this code boundary; they are not externally observed or signer-authenticated effect receipts. Cancellation is terminal against stale workers, and retries retain monotonic attempt history. Transition receipts are recomputed internal-integrity telemetry only, not execution authority or external authentication.

Terminal resident `FIX` determinations cross the editor/main process boundary
through `reddog_fix_promotion_claims`. The coordination row is derived from the
integrity-checked terminal cycle, canonical architect determination, exact
queue candidate, and validated WSP 15 receipt. A bounded CAS lease permits one
main process to materialize the existing handoff artifacts. The row grants no
execution authority; signed promotion revalidates all authoritative inputs.
Expired claims recover, lease renewal is bounded, and successful promotion
completes exactly once. A monotonic claim revision is revalidated under an
AgentDB writer fence across the authoritative publication CAS; the applied row
binds the resulting promotion receipt and committed work-state revision before
the fence is released. Restart recovery re-enters the existing authenticated,
idempotent promotion path; claim coordination never infers completion from an
unsigned work-state mapping.

Fresh AgentDB cycle rows must be canonical `SUBMITTED` retry-zero records. `FAILED` and `TIMED_OUT` may retry through CAS; `CANCELLED` and `DETERMINED` never reopen. Legacy rows have a cancellation-only compatibility path and are otherwise rejected.

Signed worker tasks carry a canonical AgentDB envelope. The OpenClaw claim
path and direct task runner both reverify its signed authority, WSP 15
allocation, dispatch receipt, intent, and task binding before runner
selection. Unverified outer AgentDB metadata never widens role, capability,
operation, or routing authority.

Each signed-worker terminal or requeue result is appended to the durable
AgentDB result ledger in the same transaction as its exact task transition.
For independent verification, the verifier stage emits a receipt-bound
completion request; only that transaction may complete the durable assurance
reservation. Detached completion and generic task finalization reject.

> **OpenClaw** (formerly Moltbot/Clawdbot), trained on WSP framework, operating on Foundups-Agent codebase

## Version Note

| Date | Name | Package |
|------|------|---------|
| Jan 30, 2026 | **OpenClaw** (current) | `openclaw` |
| Jan 27, 2026 | Moltbot | `moltbot` |
| Pre-2026 | Clawdbot | `clawdbot` |

## Vision

OpenClaw becomes **0102** — the Digital Twin of 012:
- **Voice**: Multi-channel (WhatsApp, Telegram, Discord, Voice)
- **Brain**: WSP framework + HoloIndex semantic search
- **Body**: Foundups-Agent codebase

## Architecture

### Canonical create_foundup Job Bindings

`FoundUpJob` carries `creation_mode`, `genesis_envelope_digest`, and
`scaffold_contract_digest` as typed top-level fields. For
`requested_action="create_foundup"`, callers set
`creation_mode="new_scaffold"` and place the validated genesis envelope at
`payload.genesis_envelope`; WRE performs the fail-closed route validation.
These fields round-trip through `to_dict()` / `from_dict()` and are not an
alias for the existing-module build or extraction actions.

```
012 (Human) ──voice/chat──► OpenClaw Gateway ──WSP-trained──► Foundups Codebase
                                   │
                                   ├── AGENTS.md (WSP training)
                                   ├── SOUL.md (0102 identity)
                                   └── skills/ (foundups-wsp, holo-search)
```

## 2026-03-28 Operating Rule

Current OpenClaw execution mode is `Kohi`: a bounded maintainer under `WSP 77`.

- `0102` = architect / prioritizer / reviewer
- `OpenClaw` = doer / maintainer / reporter
- `HoloIndex` = retrieval and direction surface
- `WRE` = deterministic skill execution
- optional higher-compute reviewer = critique/tuning lane, not a second authority

Current OpenClaw job:
- work low-fruit codebase tasks
- run bounded checks
- create structured reports/artifacts
- hand results upward for review and tuning

Current OpenClaw loop:

`assigned work -> retrieve bounded HoloIndex bundle -> execute -> verify -> emit -> write durable knowledge`

RedDog's production execution valve is governed-only. Legacy sovereign-token
JSON cannot enter the bootstrap/registry/handler path. Signed-authority queue
preflight does not consume a nonce; the canonical use-time verifier performs
the transactional single consumption immediately before valve evaluation.
The lease checks a fresh trusted clock at that final boundary, so an expired
lease performs neither nonce consumption nor an effect. Runtime authority
artifacts are confined to one independently configured outside-repository root
and read through bounded no-follow descriptors under their exact operation
locks; a file's own parent never defines trust. Use-time authority artifacts
are collected twice, and any replacement between collections discards the
complete snapshot and fails closed. The strict promoted queue/claim/WSP 15
lineage is revalidated at use time.

Worktree and OpenClaw effects report `COMMITTED`, `NOT_COMMITTED`, or
`INDETERMINATE` with a stable attempt key. Exceptions after an effect attempt
are never reported as false non-events; they require reconciliation by that
key. Production remains `VALVE_CLOSED`. The optional Memex supply ID/digest
pair is signed and now remains bound through dispatch, AgentDB restart, claim,
executor, read-only 0102 assignment, and independent slice-verifier receipts.
Malformed or conflicting pairs reject before effects. That lineage does not
make Memex content current-code proof or replace projection/query verification.

### RedDog HoloIndex Query Boundary

The RedDog operational consumers migrated in this POC use an authenticated
owner service at literal `127.0.0.1`.
An explicit HOLOINDEX_QUERY_SERVICE_URL/token selects an externally supervised
owner; otherwise the adapter resolves the host bootstrap's authenticated
process-private handoff. Auto-generated tokens are never exported to the
parent environment. The worker never indexes or opens Chroma. It preserves
code, WSP, docs, knowledge, tests, skills, work-ledger, and symbol evidence
from the owner's raw result.

Freshness is fail-closed: CURRENT means the owner proved the exact worker
repository HEAD, a stable generation and receipt digest, and all seven
baseline collection manifests before and after a semantic query. Missing,
lexical, stale, empty-canary, or changed-generation evidence blocks downstream
model work as an index gap. If neither an explicit service nor a live
private handoff exists, the adapter fails with
HOLOINDEX_QUERY_SERVICE_NOT_CONFIGURED and never opens local Chroma.

An explicit SSD enables direct host diagnostics only. The freshness receipt is
derived exclusively from `freshness_receipt_path(ssd)`. An explicitly supplied
receipt must canonicalize to that exact path and must not be a final-component
link/reparse point; otherwise the request fails before receipt or backend
access. The path then runs the same root/SSD/HEAD/generation/baseline/
maintenance admission proof. Failure returns content-free stale reasons and
zero hits. An admitted direct result is still labeled non-operational and can
never return CURRENT. Trusted
interactive/headless host preflight performs any required semantic full
refresh before worker dispatch; startup may route that request through
governed WRE dispatch, but the query adapter has no maintenance surface.

This is a supported adapter contract, not an OS privilege boundary. Hard
isolation requires host-level filesystem/process permissions. Phase-1 coverage
is limited to the preflight-wired read-only audit/research, report-collection,
audit-enqueue, and configured auto-task consumers. The legacy
foundups_mcp_bridge `holo_tools.py` path remains a direct-store consumer and is
not covered by an all-consumers migration claim.

For an entity-scoped repository/module audit, an unavailable, stale, or
insufficient owner result may enter the deterministic repository-audit fallback.
HoloIndex is always queried first. The fallback securely re-reads candidate
files under fixed path, file-count, and byte budgets; prunes private tool state,
generated/vendor roots, secrets, traversal, and links/reparse points; and accepts
only implementation source plus an independent test or contract whose paths
bind to the requested entity. The creation-time receipt records the fixed
policy, selected content digests, and local Git HEAD; it does not claim that
HEAD alone proves later working-tree content. Each read-only executor reopens
every selected file through the confined reader and requires exact path,
digest, byte-count, and truncation equality before consuming it. The
model-backed path repeats that check after the model returns. Any mismatch
rejects the result. The fallback grants no indexing, shell, mutation, or
execution authority.

### RedDog runtime model-binding boundary

The resident read-only audit cycle requires two independently issued,
surface-specific `reddog_model_runtime_binding_receipt.v1` artifacts: one for
`reddog_readonly_audit_worker` and one for `reddog_backend_architect`. The
audit and architect receipt pairs are both digest-bound into WSP 15 and the
durable intent identity. The audit pair continues through swarm, assignment,
and AgentDB task context; the architect pair continues through determination
and queue-candidate lineage. Every runner, including an injected test runner,
rejects a missing, malformed, rejected, wrong-surface, or pair-mismatched
receipt before index/provider access or persistence. Selection receipts alone
do not authorize either call.

At interactive startup, a missing or invalid binding disables the resident
cycle without blocking the main menu unless
`REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE_ENFORCED=1`.

Model identities and panel topology come only from the exact validated runtime
receipt. Same-surface substitution is rejected against task, assignment, WSP
15, and durable-intent bindings. The runners have no model fallback list.
Injected test runners remain available for deterministic read-only tests, but
must receive the same valid binding lineage as production runners.

## Setup

> ⚠️ **Important**: See [docs/INSTALL_OPENCLAW.md](docs/INSTALL_OPENCLAW.md) for full guide

1. **Install Node.js in WSL**: Required first! (not Windows Node)
2. **Install OpenClaw**: `npm i -g openclaw && openclaw onboard`
3. **Configure workspace**: Point to this module's `workspace/` directory
4. **Set env**: `DISCORD_0102_BOT_TOKEN`, `FOUNDUPS_WEBHOOK_TOKEN`

Legacy compatibility:
- Older OpenClaw gateway setups may still read `DISCORD_BOT_TOKEN`
- During transition, export both and map `DISCORD_BOT_TOKEN` to the same value as `DISCORD_0102_BOT_TOKEN`

### Discord Bot Install

> **OAuth Fix**: If you see `"Integration requires code grant"` when adding the bot, use a direct OAuth URL instead of Discord's Install Link (which defaults to `None`).

See [docs/DISCORD_OPERATOR_SURFACE.md](docs/DISCORD_OPERATOR_SURFACE.md) for:
- Verified install flow and OAuth URL
- Required scopes (`bot`) and optional scopes (`applications.commands`)
- Required intents (Message Content, Server Members) and optional (Presence)
- Operator runbook and smoke tests

## IronClaw Sidecar Mode (Optional)

OpenClaw DAE can route conversational responses through an IronClaw
OpenAI-compatible gateway while keeping existing WRE control-plane behavior.

- `OPENCLAW_CONVERSATION_BACKEND=ironclaw`
- `IRONCLAW_BASE_URL=http://127.0.0.1:3000`
- `IRONCLAW_MODEL=local/qwen-coder-7b`
- `IRONCLAW_AUTH_TOKEN=<token>` (optional, if gateway requires bearer auth)
- `IRONCLAW_NO_API_KEYS=1` (default): strips provider API keys from IronClaw launch env
- `OPENCLAW_NO_API_KEYS=1` (recommended): disables OpenClaw cloud LLM fallbacks
- `OPENCLAW_ALLOW_EXTERNAL_LLM=0` (recommended with key isolation)
- `IRONCLAW_START_CMD=<your start command>` (used by CLI submenu launcher)

CLI integration:
- Main menu -> `16. OpenClaw / IronClaw` -> options `5/6/7/8`
- Direct flags: `--ironclaw-chat`, `--ironclaw-voice`

Startup readiness:
- `main.py` now runs an IronClaw runtime preflight before broker bootstrap when IronClaw is the active conversation backend.
- default behavior:
  - `OPENCLAW_CONVERSATION_BACKEND=openclaw` -> preflight prints `SKIP`
  - `OPENCLAW_CONVERSATION_BACKEND=ironclaw` with no fallback -> failed readiness blocks startup
  - `OPENCLAW_CONVERSATION_BACKEND=ironclaw` with `OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK=1` -> failed readiness warns but does not block

## Standalone Action CLI (Agent API Surface)

For autonomous execution outside menu navigation, use:

```bash
python -m modules.communication.moltbot_bridge.src.action_cli \
  --command "youtube action comments channel=move2japan max_comments=2 dry_run=true"
```

Optional DAE-routed mode:

```bash
python -m modules.communication.moltbot_bridge.src.action_cli \
  --command "x action post content=smoke_test dry_run=true" \
  --via-dae --backend ironclaw --no-api-keys on
```

Repeat mode for 012 observation/testing:

```bash
python -m modules.communication.moltbot_bridge.src.action_cli \
  --command "linkedin action read_feed max_posts=2" \
  --repeat 5 --interval-sec 60
```

LinkedIn digital twin command example:

```bash
python -m modules.communication.moltbot_bridge.src.action_cli \
  --command "linkedin action digital_twin comment_text='...' repost_text='...' schedule_date='Mar 12, 2026' schedule_time='10:00 PM' mentions='@foundups,@Mo Gawdat' identity_cycle='FOUNDUPS,Move2Japan,UnDaoDu'" \
  --via-dae
```

Adapter note:
- `linkedin_social_adapter` now passes `mentions` and `identity_cycle` through to the LinkedIn layered digital twin flow.

Security:
- Standalone adapter mode runs the same Cisco skill-safety gate before execution.
- DAE mode (`--via-dae`) also enforces skill safety through OpenClawDAE.

## Resident OpenClaw Service

OpenClaw now has a broker-managed resident service path built on the existing
webhook receiver instead of a separate daemon shape.

- `main.py` registers `openclaw` as a launchable DAE
- `main.py` registers `openclaw_supervisor` as the canonical 0102 state machine
- default bootstrap path autostarts it unless disabled
- runtime control works through Claw or the generic DAE broker surface

Environment:
- `OPENCLAW_RESIDENT_ENABLED=1`
- `OPENCLAW_RESIDENT_AUTOSTART=1`
- `OPENCLAW_SUPERVISOR_ENABLED=1`
- `OPENCLAW_SUPERVISOR_AUTOSTART=1`
- `OPENCLAW_SUPERVISOR_POLL_SEC=10`
- `OPENCLAW_SUPERVISOR_MAX_RESTARTS=3`
- `OPENCLAW_SUPERVISOR_RESTART_WINDOW_SEC=900`
- `OPENCLAW_RESIDENT_HOST=127.0.0.1`
- `OPENCLAW_RESIDENT_PORT=18800`
- `OPENCLAW_RESIDENT_LOG_LEVEL=info`

Runtime examples:
- `status openclaw`
- `status openclaw live`
- `tail openclaw`
- `stop openclaw`
- `status openclaw supervisor live`
- `tail openclaw supervisor`

Supervisor repair policy:
- resident OpenClaw restart attempts are bounded inside a rolling window
- exhausted restart budget escalates instead of looping forever
- every cycle advances a DAEmon follow cursor so repair decisions stay tied to observed runtime history

### Resident RedDog live canary

`reddog_resident_live_canary` is the operator admission surface for one run of
the existing highest guarded resident profile. Run it on Linux/WSL first
without `--execute`; readiness never invokes the control loop:

```bash
python -m modules.communication.moltbot_bridge.src.reddog_resident_live_canary \
  --repo-root /mnt/o/Foundups-Agent \
  --runtime-root /mnt/o/.reddog/resident/Foundups-Agent
```

Execution additionally requires `--execute --confirm
REDDOG_RESIDENT_LIVE_CANARY_PHASE1`. The runtime root must be outside the
repository and already contain the authority, permission, execution-valve,
signer config/run-packet, and live signer socket artifacts named by the CLI
receipt. The harness never starts the signer or resolves secret values.
The signed runtime-artifact manifest producer is available as a
content-addressed foundation. Canonical artifact writers and publication share
a runtime-generation fence, and final publication uses OS-level no-replace
semantics. A verified manifest can now mint one opaque, non-serializable,
one-shot launch selection inside the signer process. The selection binds the
exact config and run-packet bytes, repository/runtime roots, and generation.
The canary remains blocked until the external signer lifecycle supplies that
selector from current-generation and durable replay authority, and until the
mutual peer proof is consumed at each authoritative signing boundary. The
explicit signer healthcheck proves a fresh Ed25519 response from the signer
instance bound to the exact production run packet; it does not by itself
authorize a later signing call or execution effect.

`READY_FOR_EXECUTION` is only static readiness. Every main control-loop caller
uses one shared OS advisory lock. `LIVE_PROOF_COMPLETE` requires the matching
new v1 control receipt to prove lock ownership, accepted PASS, repository
binding, and positive serial progress; changed pre/post chain revisions; an
exact completed chain envelope with a new final-revision store receipt;
work-order/slice/head lineage; accepted draft-only PR evidence; an external
Git worktree registered by the repository with matching `HEAD`; and
PatternMemory identities recomputed from the canonical SQLite record. The
chain revision is non-circular: the store normalizes the newest receipt witness
for hashing, then persists the same revision in the envelope and that receipt.
It never marks a PR ready or merges it. Inside the runtime root, receipt output
is reserved to canonical `live_canary_receipt.json`; other outputs must be
outside both the runtime root and repository.

PQN runtime examples:
- `run pqn simulation`
- `status pqn simulation`
- `tail pqn simulation`
- `show pqn simulation plan`

### Memory Writeback (WSP 60 / WSP 48)

Standalone action runs are now persisted into WRE PatternMemory as `skill_outcomes`
records (`action_cli_<route>_<action>`), enabling recall of:
- what command ran,
- whether it succeeded,
- response summary,
- execution duration.

## Files

| Path | Purpose |
|------|---------|
| `scripts/launch.py` | Broker-managed resident OpenClaw service hooks |
| `workspace/AGENTS.md` | WSP framework training |
| `workspace/SOUL.md` | 0102 identity/voice |
| `workspace/TOOLS.md` | Foundups CLI commands |
| `workspace/skills/` | OpenClaw skills |
| `config/moltbot.json` | Legacy sample config (OpenClaw uses `~/.openclaw/openclaw.json`) |

## Skill Safety Gate (Cisco Skill Scanner)

OpenClaw DAE now runs a cached safety preflight on local skills before mutating routes
(`command`, `system`, `schedule`, `social`, `automation`, `foundup`).

- Scanner package: `cisco-ai-skill-scanner`
- CLI: `skill-scanner`
- Skills path scanned: `modules/communication/moltbot_bridge/workspace/skills`
- Report path: `modules/communication/moltbot_bridge/reports/openclaw_skill_scan_report.json`

Environment toggles:
- `OPENCLAW_SKILL_SCAN_REQUIRED=1` (default): fail closed if scanner missing
- `OPENCLAW_SKILL_SCAN_ENFORCED=1` (default): block risky scans above threshold
- `OPENCLAW_SKILL_SCAN_MAX_SEVERITY=medium` (default)
- `OPENCLAW_SKILL_SCAN_TTL_SEC=900` (default cache window)
- `OPENCLAW_SKILL_SCAN_ALWAYS=0` (default): set `1` to force scan on every mutating route
- `OPENCLAW_SKILL_MANIFEST_REQUIRED=1` (default): require `workspace/skills/SKILL_MANIFEST.json`
- `OPENCLAW_SKILL_MANIFEST_ENFORCED=1` (default): block on missing/mismatched manifest
- `OPENCLAW_SKILL_MANIFEST_VERIFY_SIGNATURE=0` (default): verify HMAC signature when enabled
- `OPENCLAW_SKILL_MANIFEST_ALLOW_EXTRA=0` (default): block unlisted `SKILL.md/SKILLz.md` files
- `OPENCLAW_SKILL_MANIFEST_FILE=` (optional): override manifest path
- `OPENCLAW_SKILL_MANIFEST_HMAC_KEY=` (optional): key for signature verification

## Skill Boundary Policy

OpenClaw workspace skills and internal `skillz` are intentionally separated.

- Policy: `docs/SKILL_BOUNDARY_POLICY.md`
- OpenClaw workspace skills: `workspace/skills/**/SKILL.md` (operator workflow layer)
- Internal execution skillz: `modules/**/skillz/**/SKILLz.md` (trusted module layer)

## Security Hardening

### SOURCE Tier Permission Check
SOURCE tier operations (code edits) require explicit permission via AgentPermissionManager.
Fail-closed: blocked if manager unavailable or check fails. Permission denied events emitted with 60s dedupe.

### Webhook Rate Limiting
Token bucket rate limiting per sender and channel (defense-in-depth):
- `OPENCLAW_RATE_LIMITING_ENABLED=1` (default)
- `OPENCLAW_RATE_SENDER_PER_SEC=2.0` / `OPENCLAW_RATE_SENDER_BURST=10.0`
- `OPENCLAW_RATE_CHANNEL_PER_SEC=5.0` / `OPENCLAW_RATE_CHANNEL_BURST=20.0`

Returns HTTP 429 with `X-Retry-After` when exceeded.

### COMMAND Graceful Degradation
When WRE is unavailable, COMMAND intents return deterministic advisory fallback with:
- Advisory Mode header
- Command recognition
- Three actionable options (CLI, retry, query mode)

## WSP 97 Control-Plane Module Map

OpenClaw now follows a facade + delegated-module design.
`OpenClawDAE` remains the public contract surface, while the runtime is split into focused control-plane modules.

| Module | Responsibility |
|------|------|
| `src/openclaw_dae.py` | Facade, public contract, dependency wiring |
| `src/openclaw_intent_planner.py` | Intent classification, WSP preflight, plan construction |
| `src/openclaw_permission_policy.py` | Autonomy tiers, SOURCE gating, containment, skill safety |
| `src/openclaw_execution_routes.py` | Post-plan route dispatch |
| `src/openclaw_conversation_engine.py` | Conversation execution and response shaping |
| `src/openclaw_model_policy.py` | Agentic model routing and live model switching |
| `src/openclaw_identity_context.py` | Identity card, platform context pack, WSP_00 prompt assembly |
| `src/openclaw_runtime_support.py` | Runtime probing, IronClaw autostart, model availability |
| `src/openclaw_status_surface.py` | `connect wre` readiness/status and outward status push |
| `src/openclaw_process_loop.py` | Full autonomy loop orchestration |
| `src/openclaw_result_memory.py` | Validate + remember (WRE pattern memory writeback) |
| `src/openclaw_turn_state.py` | Token telemetry and cooperative turn cancellation |
| `src/openclaw_action_ledger.py` | Structured DAEmon action emission |
| `src/openclaw_social_controller.py` | Social-routing bridge and LinkedIn mission control |
| `src/openclaw_provider_chain.py` | Preferred external / IronClaw provider call chain |
| `src/openclaw_bootstrap_config.py` | Constructor-time state/bootstrap wiring |

Current refactor result:
- `openclaw_dae.py` reduced from `2638` lines to `1342`
- remaining file content is predominantly facade wrappers, dataclasses, and the honeypot surface
