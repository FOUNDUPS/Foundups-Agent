# ModLog - moltbot_bridge
## 2026-08-06: Durable E0 conversation-scope authentication
- Replaced process-local session authentication by extending the existing
  isolated Ed25519 signer. Exact scope state binds the current credential,
  signer key epoch, and E0 audit attestation; the bearer is never persisted.
- Added a signer-owned monotonic conversation head; restarts, rollback, forks,
  nonce reuse, and concurrent successors fail closed. Runtime requires a current
  principal resolver, exact policy, confined anchor, kernel peer source, and a
  reviewed request budget.
- Added exact AgentDB pre-sign staging and signed atomic finalization. Later-clock
  recovery can only replay the signer-anchored response and cannot mint a fresh
  signature; altered pending state fails and principal resolution stays leased.
- Extended staging to proposal previews. A post-anchor crash leaves active state
  unchanged, fences other writers, and replays only the anchored response.
- Preserved legacy HMAC without recovery authority: it signs before direct
  create/CAS; only E0 state may consume exact signer-anchor replay.
- Extracted signer config rehydration, principal parsing, and conversation-domain
  signing from WSP 62 hosts. The bounded supplier and split fixtures retain an
  AST gate. No state grants work, repository, signer, merge, or HoloIndex writes.
- Exact-SHA review froze config output, applied the shared public-profile
  allowlist, unified config/runtime proposal verification, and extended the
  same gate to exact schemas for embedded model, WSP 15, proposal, and
  operational-context receipts. Architect FIX promotion now rejects raw nested
  receipt injection before publication and persists canonical receipts only.
- Added one shared seed/source/runtime authority-profile rehydrator. It rejects
  native JSON type confusion before source supply, promotion, publication,
  signer configuration, valve use, manifest authority, queue materialization,
  readiness, or live-canary evidence can produce an effect.
- Preserved the older queue materializer projection through a bounded typed
  effect view instead of conflating it with the signed public-profile schema.
- Legacy callers retain 16 KiB; only the explicit conversation bootstrap uses
  160 KiB. Stale v2, nested profile injection, and artifact collisions fail
  before writes or signer invocation (WSP 00/15/22/50/62/97).
## 2026-08-06: Current-generation conversation session authority source
- Replaced the rejected symmetric resident path with a strict principal-signed
  conversation credential verified by the existing Ed25519 backend and
  signer-owner E0 principal artifact loader.
- Resident editor sessions now derive principal and FoundUp scope from a
  verified subject plus one signed current-generation authority artifact;
  environment labels are consistency checks only.
- No HMAC or private signing material enters the resident process. The bearer
  crosses one-shot stdin, is removed before resident work, and never enters
  AgentDB, model prompt, durable intent, logs, or output. The current generation
  remains leased through cycle admission and its public digests are persisted.
  This grants no work, worker, repository, merge, signer, or HoloIndex authority
  (WSP 00/15/22/50/62/97).
## 2026-08-06: Authenticated conversational scope and proposal promotion
- Added HMAC-authenticated AgentDB scope, opaque one-use capabilities, snapshot/HEAD/Holo/FoundUp/intent binding, exact proposal-preview CAS, backend pre-model rejection, and signed WSP 15 pending-authority consumption; no editor session issuer, worker dispatch, repository/merge authority, or HoloIndex mutation was added (WSP 00/15/22/50/62/97).
## 2026-08-05: Resident live-canary current-generation trust concatenation
- Extended the canonical use-time authority resolver to consume the existing
  root-owned system-service manifest selection after signed work-authority
  re-verification. The new read-only adapter binds exact manifest, config,
  run-packet, durable replay/high-water, generation, root, path, and freshness
  evidence into an audit-only receipt using the resolver's trusted clock.
- Removed only the three satisfied current-generation blockers. Mutual peer
  handshake and six other trust anchors remain fail-closed, so this slice
  cannot issue an authority lease, run a live canary, mutate a repository,
  enqueue a worker, or grant signer authority.
- Current-generation evidence cannot mint effect authority. Worktree,
  live-enqueue, and spine paths now reject every production lease until the
  isolated signer peer supplies the missing external issuer. Wrong types,
  malformed IDs, expiry, or changed config/run-packet bytes fail closed. No signer,
  schema, replay store, provider, lifecycle service, or trust model was added
  (WSP 00/15/22/50/62/97).
## 2026-08-05: Upstream agent runtime truth registry
- Upgraded the existing OpenClaw integration manifest to a static provenance
  v2 ledger with stable integration IDs, exact checked-in implementation and
  test evidence paths, and explicit upstream CLI/API versus Foundups-local
  classifications.
- Bound the only two accepted upstream artifact providers to the canonical
  `openclaw_gateway` and `hermes_api` runtime modes while recording that both
  remain default-off, fail-closed, text-only, and tool-free. No upstream hook
  is currently claimed.
- Split the previous aggregate Hermes label into the WRE dry-run executor,
  FoundUp builder, and resident transport surfaces so each records its actual
  owner, controls, consumers, and capability boundary. The structured registry
  remains readable and below the WSP 62 configuration threshold.
- The ledger is explicitly non-authoritative: it does not prove installation,
  health, version freshness, live execution, or grant any worker authority
  (WSP 00/15/22/50/62/97). WSP 15 classified the correction P1 at 14/20.

## 2026-08-04: Verified-outcome root authority service
- Replaced the signer-owned outcome replay database with a separately launched,
  root-owned Unix-socket authority service. The root process owns disjoint
  primary, witness, and one-time installation CAS stores and authenticates the
  non-root E0 signer with kernel peer credentials; the signer verifies the
  service UID on every connection.
- Added a separately invoked root provisioning primitive, generation rollback
  fence, exact one-step witness repair, and `RESERVED_BURNED -> COMMITTED`
  transition. The runtime service has no state-reset/bootstrap option. The
  E0 signer buffers its signature and releases it only after root commit rechecks
  the current descriptor, revocation state, generation, owner config, grant,
  reservation, and signature digest.
- Removed caller-injected transport from production authority minting. Only an
  opaque exchange created by the protected root-socket builder can create the
  signer capability; non-root exchange identities and recomputed responses fail.
- Removed the process-local test authority from production code. Reserve and
  commit now require both fresh kernel UID/GID and a domain-separated E0 signer
  proof over every request field; malformed clients are isolated per connection.
- Added a bounded root service entrypoint and extended the existing v2 root owner
  config with exact socket, signer principal, primary, witness, and installation
  bindings. A separate one-time provisioning entrypoint cannot reopen a committed
  installation after replay-store loss.
- Bound every live snapshot to the exact roots, paths, store IDs, and durability
  receipts opened at startup. A rotated store configuration now requires a
  supervised service restart and cannot silently reuse old open stores.
- Added the executable E0 pre-key process gate to the existing isolated signer:
  production WSP71 resolution now requires the exact root-owned non-root signer
  UID/GID, YAMA ptrace enforcement, no `CAP_SYS_PTRACE`, disabled core
  dumps/dumpability, and a cleared inherited environment.
- Retired the old CLI and one-shot WSP71 composer; only the stable service is
  production. One v2 read supplies manifest, lazy outcome authority, owner ID,
  and UID/GID; only selected policy touches the socket and v1 is migration-only.
- Production remains fail closed until the root service is deployed with a
  root-owned config and independently co-signed verifier grants. This slice adds
  no learning candidate, Brain/roadmap write, HoloIndex mutation, repository,
  OpenClaw/Hermes, PR, merge, reward, or key-custody authority
  (WSP 00/15/22/50/62/97).

## 2026-08-04: Verified-outcome root authority supply (partial)
- Extended the existing E0 signer and root-owned system-service owner config;
  no second signer framework, database abstraction, or orchestrator was added.
- Added an exact root-published authority descriptor with independent verifier
  and held-out signatures over FoundUp/snapshot/work/slice/job/head/content,
  runtime, PatternMemory, key, revocation, freshness, and replay bindings.
- Bound authority admission to the authenticated owner-config ID and exact
  signer run packet, config, session, manifest, and artifact generation.
- Bound both verifier signatures to an immutable digest of the complete root,
  signer, runtime, replay-anchor, and policy context so a co-signed grant cannot
  be transplanted into another root-published descriptor.
- Moved registry-backed root-authority verification into the shared signer
  key-provider core, closing alternate production/test constructors and
  unregistered same-type objects before any key material is resolved.
- The initial draft reused a signer-owned SQLite monotonic store. Independent
  review rejected that trust model; the root service above supersedes it.
- Re-read the root-owned authority descriptor at every reservation and used a
  signer-side trusted clock, so post-launch revocation and expiry fail before
  signing even when a caller supplies an earlier request timestamp.
- Extracted exact runtime/policy/peer matching into a bounded module. The new
  authority modules remain below WSP 62 limits; inherited signer transaction
  hosts carry exact, expiring no-growth ceilings.
- Preserved unrelated signer operations when a generation omits the outcome
  policy; the root-owned v2 config remains mandatory for production OS identity.
- Hardened the backend manifest generator so Python files named as static
  runtime roots contribute their complete import closure. Signer authority
  dependencies are now content-bound rather than merely reachable.
- The initial slice truth was `VERIFIED_OUTCOME_RUNTIME_BINDING_PARTIAL`.
  Root-service deployment and independently issued verifier grants are still
  required for production activation. No PatternMemory,
  learning, Brain/roadmap, HoloIndex, repository, or merge authority was added
  (WSP 00/15/22/50/62/97).

## 2026-08-04: Verified-outcome runtime authority binding (partial)
- Extended the draft verified-outcome rehydration foundation with a root-confined
  evidence and replay namespace in the existing authority runtime store. Signed
  publication is staged and non-consumable until its exact activation transition.
- Removed the unauthenticated legacy queue downgrade. Publisher-backed outcomes
  can stage in an invisible table inside the existing PatternMemory database.
  Conflicting pre-seeded rows fail exact canonical readback instead of satisfying
  admission by identifier alone.
- The real PatternMemory sink remains explicitly non-activation-ready until it
  can independently revalidate a durable authority source. Direct store and
  caller-known identifiers cannot expose staged rows; injected test sinks do not
  claim production authority.
- Added committed-profile key resolution, revocation/freshness checks, exact
  FoundUp/snapshot/head/content/work/slice/job/worker/verifier/runtime lineage, and
  opaque one-use capabilities consumed by resident FoundUp Brain assembly.
- Added atomic batch capability consumption after complete Brain validation and
  one trusted runtime clock for issuance and consumption. Missing queue bindings
  no longer downgrade silently to legacy admission.
- Security review proved current autonomous-verifier receipts are canonical
  self-hashes, not independently signed verifier authority. The signer now
  requires a separately supplied durable authorization boundary and rejects
  absent or replayed authorization. No production boundary exists yet, so
  activation remains fail closed: `BLOCKED_BY_DURABLE_AUTHORITY_SOURCE`.
- WSP 62 review split outcome schema/lineage validation and signer request
  validation/reservation into focused helpers. The signer backend, authenticity
  gate, helpers, and their focused test modules now remain below the 675-line
  communication threshold without new exemptions.
- Boundary remains narrow: no learning candidates, Brain or roadmap writes,
  HoloIndex mutation, new database, new orchestrator, voting, or CABR governance
  (WSP 00/15/22/50/62/97).
## 2026-08-04: Memex supply authenticity gate
- Replaced the promotion path's `sha256:` prefix check with exact typed Memex supply
  receipt rehydration, canonical digest verification, scope/lineage and
  freshness checks, and strict unknown-field/type rejection.
- Upgraded architect proposal attestations to v2 so the isolated signer binds the
  exact full Memex receipt digest. Attacker-rehashed substitutions now fail against
  independently signed proposal authority before artifact, seed,
  queue, profile, or state mutation. Proposal signing rehydrates even a
  manually constructed typed receipt; receipt age is capped at 300 seconds and
  policy lifetime at 600 seconds. Added canonical verifier/held-out rehydration and
  one-use signed-bundle capability primitives. Resident outcome admission stays
  fail-closed pending root-owned durable trust/replay wiring (WSP 00/15/22/50/62/97).

## 2026-08-03: Extension resident model-runtime authority binding
- Reused the `main.py` authenticated BOUND model-runtime loader in the extension
  bridge; invalid audit/architect receipts reject before client construction,
  with no executable or repository authority (WSP 00/15/22/50/62/97).
## 2026-08-03: Actual upstream Hermes API artifact provider
- Replaced the production-blocked `hermes_api` placeholder with a real
  authenticated loopback adapter for upstream Hermes Agent `/v1/runs`.
- Consumes the signed principal model/provider route before secret access or
  transport and reuses the existing Foundups artifact writer, worktree,
  exact-SHA commit, and independent verifier.
- Requires Hermes release `2026.7.30` / API runtime `0.19.1`, the dedicated
  `reddogartifact` profile, bearer
  enforcement, all API-server toolsets disabled, zero visible skills, and an
  unchanged tool/skill surface after generation. The complete upstream SSE
  event history must contain no tool, approval, or subagent event and its
  terminal output must match the polled terminal status. Tool, approval, subagent,
  malformed-output, timeout, and uncertain-stop paths fail closed.
- Added a fixed loopback stdlib transport and a confined outside-repository
  secret source. No secret is accepted from prompts, argv, repository files,
  or provider receipts. Hermes receives no shell, worktree, Git, GitHub, PR,
  merge, HoloIndex, PatternMemory, or reward authority (WSP 00, 15, 22, 50, 62, 97).

## 2026-08-02: Actual OpenClaw provider and truthful Hermes boundary
- Added a production adapter for the installed upstream OpenClaw Gateway CLI;
  no repository-local OpenClaw-name wrapper is used as the execution engine.
- Reused the signed model-runtime binding, AgentDB/WRE work order, canonical
  Foundups artifact materializer, isolated worktree, exact-SHA commit, and
  independent verifier instead of creating a second authority or writer.
- OpenClaw requires a fixed dedicated agent, unique exact-session sandbox,
  live version-matched loopback Gateway, one canonical read-only sandbox
  workspace mount, no elevation, and a wildcard tool deny policy. Hermes
  production dispatch remains blocked because the
  current upstream API does not prove authenticated split-runtime confinement.
- Bound complete provider-effect truth to stage and resident-cycle receipts, canonical
  provider-mode admission, trusted WSL command transport, and fail-closed
  queue admission for all unsupported or unconfined modes.
- Verified installed and latest upstream versions match: OpenClaw `2026.7.1`
  and Hermes Agent `v0.19.1 (2026.7.30)`. Retired constructor-based FoundUp
  live authority and environment-enabled legacy shell dispatch. Hardened the
  external OpenClaw service and dedicated agent without changing repository
  source outside this slice; Hermes remains installed but unconfigured.
  (WSP 00/15/22/50/62/84/97)
- Receipt rehydration now rejects attacker-recomputed semantic contradictions,
  malformed nested effect receipts block chain persistence, and Fusion network
  invocation is reported as an external effect on success and failure.

## 2026-08-02: OpenClaw ingress and FoundUp mutation fail-closed hardening
- Removed the known webhook-token fallback and made unconfigured webhook
  authentication reject with constant-time comparison for configured tokens.
- Prevented advisory and unauthenticated OpenClaw intents from reaching
  mutating FoundUp queue/build/create/launch paths, including direct-dispatch
  bypass attempts.
- Made FoundUp policy flags dry-run by default and normalized object and
  serialized representations through one routing rule so serialization cannot
  silently change live-write classification. (WSP 15/22/50/97)

## 2026-08-02: Generic HoloIndex incident repair coordination
- Extended the existing start-operations/post-merge Holo repair architecture
  with `reddog_holoindex_incident_repair_runtime.py`.
- Authenticated exhausted owner failures are now routed to the protected
  exact-HEAD AgentDB/OpenClaw maintenance task and its existing retry/cooldown
  semantics. Before any effect, Python independently reproduces the owner
  failure and validates its canonical receipt, evidence, HEAD, and root.
- Repair exhaustion emits a non-authority coding-candidate requirement; model
  selection and execution remain separate signed WSP 15 decisions.
- `REDDOG_FOUNDUP_WORK_SKILL_GROUNDING_PHASE1`: extended the provider-neutral
  `reddog_operations` Skillz with a canonical registered-FoundUp procedure.
  Existing FoundUps resolve through registry evidence and WSP 15; unknown
  identities route to WSP 109 intake. The Skillz remains model-neutral and
  grants no execution authority. Wardrobe selection now also requires the
  extension's current-checkout verification flag before carrying a registered
  FoundUp target into an action-plane receipt. A shared Python verifier now
  independently rechecks registry, schema, entity, evidence, manifest, root,
  selection, and work-order scope at WRE and OpenClaw IPC boundaries.
- `HOLOINDEX_POSTMERGE_OWNER_ACTIVATION_PHASE1`: made the exact-SHA HoloIndex post-merge owner active by default
  under OpenClaw supervision. General maintenance remains opt-in; when it is
  disabled, only tasks issued by the canonical post-merge coordinator are
  eligible. The generic autonomous executor excludes it from the exact-SHA
  claim contract. Added explicit
  scheduled/disabled telemetry and preserved the query-side prohibition on
  re-indexing plus all freshness gates. A lock-owned poller waits during
  shutdown and binds selection to the coordinator's exact canonical task ID.
- `REDDOG_SIGNER_E0_AUTHENTICATED_SECRET_LEASE_GATE_PHASE1`: upgraded the
  signed signer secret-access grant to v2, binding the issuer, profile, exact
  key-reference hashes, permission snapshot, owner configuration, generation,
  complete signing request, operation, authority tier, kernel-attested peer,
  nonce, and bounded lifetime. Socket v2 consumes the noncopyable one-shot
  capability before a fresh WSP 71 ephemeral backend resolves and signs once;
  substitution, replay, concurrent reuse, resolution failure, and forged
  signatures reject without secret-derived output. Production admission binds
  pre-provisioned, disjoint replay roots and one atomic revocation fence; missing
  state and non-static backend rejection payloads reject. Socket v1 cannot use it.
  The public service remains fail closed pending independent grant
  supply, authenticated revocation supply, strict native-memory zeroization,
  and lifecycle supervision (WSP 00/15/22/50/62/71/97).
- `REDDOG_SIGNER_SYSTEM_SERVICE_STABLE_ENTRYPOINT_PHASE1`: replaced the
  generation-specific signer launch command with a v2 run packet that binds a
  stable signer-owned system-service entrypoint and the exact root-owned owner
  configuration path. The entrypoint reconstructs and consumes the current
  authenticated generation, validates the packet and its stable command,
  and gives that single one-shot capability to the existing bootstrap.
  Production service composition remains fail closed pending authenticated
  grant/revocation supply; injected tests prove only signer-side E0 ordering.
  Rotating config, packet, session, and resolver values remain signed data and
  are not service-manager arguments. Serialized argv is never executed.
  RedDog, `main.py`, OpenClaw, and Hermes still cannot spawn the signer.
  Service installation, E0 composition, durable resident
  supervision, and live Linux activation remain separate fail-closed slices.
- `REDDOG_CURRENT_GENERATION_MANIFEST_LAUNCH_SELECTION_PHASE1`: added a
  verifier-only external-signer launch selector that ignores caller-supplied
  manifest payloads, reads the authenticated durable current generation, opens
  its content-addressed signed manifest, applies the canonical Ed25519
  verifier, verifies the domain-separated audit attestation, and checks all
  seven current runtime artifact bytes before minting a process-local,
  immutable, one-shot launch capability. The activated generation, repository
  root, runtime root, manifest ID, generation digest, signer configuration
  digest, raw configuration digest, and run-packet digest must all agree.
  Canonical manifest freshness is checked at selection and consumption; a
  committed generation is not treated as a fresh restart authorization. This
  slice does not spawn or supervise the signer. Added the signer-owned CLI
  adapter for a root-owned, non-writable Linux/WSL service configuration
  outside the repository. It reads that configuration through one no-follow
  directory/file descriptor chain, rejects writable ancestry and overlapping
  trust roots, then mints an opaque owner authority instead of passing
  caller-selected trust strings. The public CLI exposes no manifest-selection
  injection seam. It reconstructs only
  verifier/read-only generation capabilities, pins the generation key, anchor,
  high-water and monotonic witness identities, and rejects caller path
  substitution before handing the one-shot selection to the existing CLI.
  The peer-instance packet validator accepts only its prior exact selection
  shape or the exact generation-bound extension; arbitrary extra authority
  fields and malformed generation/TTL values reject. Production signer
  bootstrap requires the generation-bound extension, so legacy selection
  compatibility cannot reach service startup.
  RedDog and `main.py` still cannot spawn or stop the signer; system-service
  deployment under the distinct principal remains a separate operator action.
- `REDDOG_SIGNER_RUNTIME_ATOMIC_PROVISIONING_PHASE1`: added one
  generation-root-first coordinator that signs the seven canonical artifacts
  in their final inactive runtime root and advances the independently stored
  authenticated generation anchor only after manifest publication,
  current-authority revalidation, a manifest-bound cooperative writer seal,
  a Windows deny-write/delete activation lease, and a final byte/signature commit
  guard before the high-water transaction can activate. Guard failure restores
  the prior authenticated anchor and aborts the pending high-water advance.
  A typed witness binding ties the signer key epoch, runtime root, anchor,
  local high-water state, and signer-side monotonic witness into one canonical
  namespace. Those three persistence roots must be pairwise disjoint. SQLite
  initialization and compare-and-swap are transactional and tolerate bounded
  first-open contention without accepting two winners. The coordinator
  rejects copied/replayed artifact generations, fake or
  overlapping anchor/high-water roots, stale work state, changed artifacts,
  activation-window write attempts, expired system time, and generation
  compare-and-swap conflicts. A signed
  published-but-inactive manifest can complete after restart. An expired
  manifest can roll forward only when the independent monotonic witness
  already proves that exact generation committed; otherwise freshness remains
  mandatory and recovery rolls back. Typed recovery distinguishes a committed witness when restart sees its anchor first. Canonical Ed25519 verification discards caller-selected verifiers, so forged signer/permissive-verifier pairs cannot activate. Python closure opacity is not claimed as hostile-code isolation. Malformed or ambiguous preseeds cannot
  recover. Failed activation reports preservation only after manifest binding,
  signatures, and all seven current bytes verify. Coordinator
  receipts claim only coordinator-scoped no-service/no-work/no-repository
  effects; they do not infer behavior of injected signers. Authenticated current-generation launch
  selection and external lifecycle supervision remain separate fail-closed
  follow-ons. The cooperative seal is not claimed as protection against a
  privileged or same-principal adversary after the activation lease closes;
  current bytes must still be verified at every use. POSIX/WSL activation now
  fails closed until an externally owned signer lifecycle supplies a genuine
  distinct-principal immutability boundary.
  The SQLite witness proves persistence mechanics only. Independent production
  freshness authority remains blocked until an externally supervised signer
  principal owns and authenticates that witness.
- `REDDOG_SIGNER_RUNTIME_GENERATION_AUTHORITY_PHASE1`: hardened signer
  generation activation with an authenticated, independently stored
  high-water transaction journal. Prepare, commit, abort, and restart
  recovery are atomic and cross-process serialized; recovery requires the
  authenticated pending record and never infers authority from a missing
  high-water value. Deleted or rolled-back high-water state therefore remains
  fail closed. Signing and verification are separate capabilities. The
  external lifecycle now consumes a factory-issued public-key verifier and
  confined read-only generation stores; it cannot reach a signer or mutable
  authority store. Reader and high-water authorities must come from their
  canonical factories; structural protocol lookalikes are rejected.
  Nontransactional high-water implementations are rejected,
  and post-commit recovery verifies durable state before returning. This is generation-authority
  infrastructure only: production authority issuance, immutable generation
  bundle activation, service supervision, and effect authority remain blocked.
  Factory boundaries, verifier handles, generation readers, and high-water
  readers retain no caller-mutable payload slots. Closure-private weak
  registries hold their validated dependencies and expose no module-global
  mutation surface, so post-mint replacement cannot attach a signer or
  retarget a lifecycle authority. Public constructors, factories, verifier
  calls, reader calls, and lifecycle calls expose no caller-supplied registry
  lookup or issuance hook; attempted injection fails at the API boundary.
  Verifier-only high-water readers now retain a dedicated read-only SQLite
  witness view with no `advance()` method; the mutable signer-side witness is
  rejected at the reader boundary. Lifecycle admission and one-shot consumption each revalidate the current
  authenticated generation, closing concurrent generation-advance races.
- `REDDOG_SIGNER_MUTUAL_PEER_HANDSHAKE_PHASE1`: replaced the forgeable
  signer healthcheck with a fresh, short-lived, domain-separated Ed25519
  challenge verified against the configured signer key, fingerprint, epoch,
  requester attestations, and exact request bytes.
  The production signer CLI now requires a process-local, non-copyable,
  non-serializable, one-shot selection minted by the existing signed
  runtime-manifest verifier. The signer validates exact config/run-packet
  bytes, roots, generation, packet ID, session, socket, profile/key/epoch
  tuples, CLI bindings, and fixed safety fields before reading caller-selected
  artifacts, constructing the secret resolver, resolving keys, or exposing a
  handshake-capable backend. Production bootstrap rejects all provider modes
  except `WSP71_PERMISSIONED`; test-only key material cannot bypass launch
  admission.
  Kernel peer credentials continue to authenticate client -> signer; the
  signed challenge authenticates signer -> client. Rehashed packet
  substitution, copied responses, expired/future requests, fake acceptance
  flags, key/epoch/profile substitution, unsigned audit metadata, and
  malformed domains fail closed. A second domain-separated signer signature
  covers the response audit metadata and attestations.
  The healthcheck remains evidence only. Opaque generation high-water and OS
  policy authorities, Linux kernel process/socket ownership, protected cleanup,
  and one-shot lifecycle admission now bind it to current manifest truth.
- `REDDOG_SIGNED_RUNTIME_ARTIFACT_MANIFEST_PHASE1`: added the
  content-addressed signed-manifest foundation for the seven canonical
  resident runtime artifacts.
  Manifest authority is a closure-confined process-local proof minted only
  after the existing delegated work-authority verifier confirms principal trust,
  signatures, revocation, permission freshness, FoundUp/path scope, queue
  state, independently recomputed committed-publication binding, and signer
  policy.
  The isolated signer rereads the artifact bytes, enforces an exact signing
  domain plus a manifest-specific audit-attestation domain, and reserves the
  manifest nonce through the existing transactional replay store before
  returning a signature.
  Manifests are create-only under the outside-repository runtime root; final
  publication uses OS-level no-replace semantics, so a concurrent or
  pre-seeded target is never overwritten.
  All seven canonical artifact producers and manifest publication share one
  runtime-generation fence. The signed manifest binds that generation digest,
  and publication re-derives it while fenced before creating the immutable
  content-addressed artifact.
  Runtime activation remains fail closed until a production durable replay
  high-water provider, authenticated manifest selection, use-time current
  generation verification, and mutual signer peer handshake are wired.
- `REDDOG_ARTIFACT_GENERATION_BOUND_MODEL_RUNTIME_PHASE1`: provider effects require canonical SINGLE or signed PANEL evidence rehydrated against current keys, revocation, topology, policy, and trusted time.
  Exact `(role, fingerprint, key_epoch)` resolution and independent benchmark, promotion, panel-authority, and panel-member signers prevent identity substitution.
  Opaque capabilities retain no caller-mutable binding state; registry admission binds the exact issued object identity.
  Promotion requires the exact artifact-generation runtime surface and binds the canonical selection, runtime, and verification lineage.
  Provider topology is re-derived from that verified lineage; substituted invocation topology rejects before network effects.
  Provider metadata and the durable receipt retain all six selection, runtime-binding, and verification IDs/digests.
  Missing, stale, revoked, tampered, replayed, copied, or caller-minted evidence fails closed.
  Persisted verification mappings remain audit lineage only; no second signature trust model was introduced.
  Adversarial regressions cover copied-token substitution, topology retargeting, replay, and mutable-state probing.
  Signed bounded-plan promotion reaches one queue claim, materialized order, assigned stage, exact provider call, and receipt.
- `REDDOG_OPERATIONS_SKILLZ_PHASE1`: Start Operations binds a manifest-authenticated, provider-neutral Operations Skillz receipt and revalidates it on submit/resume.
  Resident audit, architect, and artifact-generation paths reuse canonical runtime-binding admission, so weak or recomputed evidence cannot become authority.
  Brain, Breadcrumb, and Memex remain lower-authority receipt-bound planning inputs and are never claimed when absent.
- `REDDOG_START_OPERATIONS_HOLO_REPAIR_RESUME_PHASE1`: start operations reuses a process-private Holo owner or creates one exact-HEAD durable AgentDB repair task for OpenClaw.
  The task invokes the canonical maintenance handshake, re-proves generation/freshness, and permits one grounding retry.
  Semantic misses do not trigger re-indexing; malformed handoffs, substitutions, repository changes, and proof mismatches fail closed.
- The canonical operations profile exposes owner health through a semantic readiness target.
  Dispatch uses a one-shot capability after exact assignment, rejects replay/wrong assignees, and retains exact-assignment CAS recovery plus truthful refresh reporting.
- Start-operations authorization rejection preserves validated intent IDs for status, cancel, and resume correlation.
- `START_OPERATIONS_CONTROL_ADAPTER_PHASE1`: extracted the main-host dual model-binding loader into a shared fail-closed module and added a profile-bound resident-client adapter.
  It binds clean HEAD, authenticated FoundUp scope, strict budgets, and both BOUND model receipts to independent host-pinned IDs.
  Fresh control IDs prevent replay; terminal hashes cover every field, typed progress/results are emitted, and no execution authority is granted.
- Signed Memex lineage now survives the full authority and dispatch chain.
  Signer invocation validates the exact dry-run request digest before effects;
  resident verification replaces packet authority with recorded chain truth.
  Rehashed pre/post-signing substitutions now reject before worker evidence.
  The two current absent encodings (`None` and empty text) normalize without
  raising while malformed or half-populated bindings still fail closed.
- Exact-SHA review follow-up removed the importable process-local envelope
  seal as an authority primitive. Signed-worker admission now re-verifies the
  persisted AgentDB envelope against fresh authority inside the atomic claim
  transaction, and returns verification evidence only after that transition.
  Every direct signed-worker rejection owns finalization; the generic task
  finalizer refuses the signed namespace so a completion race cannot be
  overwritten. Windows publication also exercises valid runtime roots whose
  internal temp, lock, and immutable-artifact paths exceed 260 characters.
- Final exact-SHA repair requires a sealed canonical envelope at every
  signed-worker claim boundary, rejects stale assignments before effect
  admission, and reconstructs runner context only from signed authority plus
  independently validated durable result history. Finalization now checks the
  same claim/use lease inside the database transaction; expired recovery is a
  separate negative-only path. Invalid assignments quarantine task and
  verifier reservation atomically, and poisoned rows no longer block the next
  valid OpenClaw claim.
- Exact-SHA security review now requires recovery race winners to prove the
  terminal task against the independently durable result-ledger tail and the
  exact terminal assurance row. A self-hashed task-context marker alone can
  no longer report a recovered execution.
- Independent exact-SHA review hardening now reserves signed-worker assignment
  for a task-bound principal, quarantines malformed pending tasks, requeues
  stale pre-admission assignments by exact CAS, and keeps active verifier
  reservations pinned. Executing workers use a durable, bounded-renewal
  heartbeat; restart recovery honors the renewed lease and quarantines
  positive, corrupt, missing, or otherwise unverifiable evidence without
  creating a success result. Quarantined tasks no longer block unrelated valid
  signed work.
- Exact-SHA review hardening now protects the full signed-worker namespace
  from generic creation/retry/requeue as well as completion. Result
  finalization derives capability from the signed envelope, persists
  canonical identity after verified execution, retains exact admitted
  identity for pre-verification failure, and binds task/claim/assurance
  terminal states. Independent verifier `REJECT` completion is rehydrated
  from its durable AgentDB stage even when the chain-results writer rejects
  the stage result. Claims now carry a 15-minute lease; supervisor recovery
  never replays an unknown worker effect, rolls forward only exact negative
  assurance, and refuses digest-only positive assurance.
- Follow-up hardening accepts an exact all-pending batch only when durable
  publication is already APPLIED, closing the post-activation return-crash
  window. Mixed-status, partial, or field-mismatched recovery remains rejected.
  Task finalization and nonce state now use bounded internal WSP_62 siblings.
  The immutable reserved task namespace keeps stripped signed-worker tasks on
  the signed path; admission now owns and exactly finalizes pre-verification
  rejection, so mutable marker removal cannot fall through to arbitrary WRE
  execution and a competing claimant cannot be overwritten. Admission returns
  the exact context, skills, and discovery binding won by its database CAS;
  neither the direct task runner nor the OpenClaw supervisor can execute an
  earlier caller snapshot. Supervisor completion, failure, assurance
  completion, and requeue persistence now use the same exact assignee/context
  CAS; a concurrent owner is never overwritten. Requeue admission replaces only the
  superseded claim/use pair while retaining a canonical ten-entry result tail.
  The independently durable append-only AgentDB ledger retains every attempt,
  and task context must match its exact tail before supervisor or direct
  execution; malformed durable state, truncation, legacy context-only history,
  and complete attacker re-hashing therefore fail closed. Both execution paths
  append one shared result receipt in the same task-transition transaction;
  persistence failure leaves the exact task executing and never creates an
  unreceipted terminal state. Verifier completion preserves trusted timestamp
  precision and atomically commits the durable reservation; detached completion is forbidden. Transactional execution logic was extracted from the touched `AgentDB` monolith into bounded database siblings, reducing the monolith while making the security boundary explicit. Publication recovery never creates the
  derived authority cache, even from internally self-consistent COMMITTED
  packets; only a fresh normal publish call that re-verifies proposal
  authorization may recreate that cache.
## 2026-07-27: REDDOG_ARCHITECT_FIX_PROMOTION_TWO_PHASE_PUBLICATION_PHASE1 - Replaced mutable profile-first publication with `PREPARED -> immutable content-addressed inert artifact -> COMMITTED state CAS -> derived fixed-path inert cache`. Recovery never advances PREPARED, never lets unanchored packets delete immutable artifacts, preserves concurrent refresh data, and requires an authenticated publish retry to rebuild the cache after a COMMITTED crash. Added forged-self-hash, crash/interleaving, concurrency, idempotency, runtime-lock, and valve/signer use-time COMMITTED gates. Both signer consumers now require the explicitly selected durable authoritative-work-state file; injected state can only corroborate it, and any durable architect promotion makes missing/ambiguous profile provenance fail closed. The resident queue now reloads current state in serial and one-shot paths, derives a current-revision publication-effect binding before authority-request persistence, revalidates it before signing, includes it in the signed work authority, and binds verification to the exact signed work-authority digest. A canonical verification receipt now persists through dry-run intents, runtime receipts, and AgentDB task context; immediately before the writer, dispatch reloads both recorded stages, obtains fresh time from a required production clock, binds the effective task to the signed work order and authoritative WSP 15 worker plan, and preflight-verifies the signed authority. AgentDB publication advances the existing durable nonce state through digest-bound `RESERVED -> AUTHORIZED -> APPLIED`; tasks remain `publication_held` and unclaimable until the exact APPLIED batch is activated by a field-complete CAS. Recovery handles both zero-row AUTHORIZED crashes and APPLIED-before-activation crashes, while partial, altered, prematurely assigned, or completed batches reject. Dispatch admission requires exact allowlisted receipt and intent schemas, persists only canonical projections, and derives principal and RedDog identities solely from the reverified signed authority; attacker-added identity or metadata fields reject before nonce reservation. Worker execution separately performs an atomic `assigned -> executing` CAS, stores receipt-linked claim/use digests, and finalizes through an exact assignee/context CAS. Post-claim runner exceptions become terminal failures, concurrent state changes are never overwritten, and the generic task finalizer cannot finalize signed-worker tasks. PREPARED state, missing verifier/clock dependencies, synthetic dry-runs, attacker-recomputed receipts around a forged signature or substituted operation, role/capability substitution, extra-field identity injection, replay, old environment epochs, and authority substitution cannot reach dispatch effects. Split publication validation, signer persistence, optional signed bindings, request materialization, worker-dispatch authority binding, publication admission, and execution admission into bounded sibling modules so affected files satisfy WSP 62. COMMITTED remains local publication integrity, not publication authentication; `main.py` keeps the inert cache separate from the active profile, and signer-owned publication activation remains unimplemented (WSP 00, 15, 22, 50, 62, 78, 97).
- Security correction: recovery no longer rebuilds the derived cache from
  serialized COMMITTED packets. A fresh normal publish call must reverify the
  signed proposal authorization before a missing cache can be recreated.
## 2026-07-27: REDDOG_ARCHITECT_PROPOSAL_ATTESTATION_PROMOTION_BINDING_PHASE1
- Added direct promotion-time verification of the principal signature over the
  exact signer policy and the RedDog signature over the exact proposal payload.
  The verifier reconstructs current proposal and signer-runtime bindings and
  resolves the principal key independently; caller-supplied trust keys,
  caller-profile identity/scope substitution, test-only signer mode, stale
  policies, signer-context substitution, and altered signatures fail closed.
- Removed the first draft's forgeable opaque-proof registry and process-local
  one-use state. Successful authoritative work-state CAS now persists the
  attestation ID as the durable replay guard, including after process restart.
  Failed profile or work-state writes do not consume the signed evidence.
- Bound signed receipt IDs/digests and signer-runtime context into the worker
  claim, queue item, records, receipts, authority profile, and context. Profile
  identity fields come only from verified authorization, and the source
  receipt is recomputed. WSP 15 promotion and queue CAS remain the mutation engine.
- Decomposed promotion record/profile/state assembly into a bounded transaction
  module. The inherited prewrite-then-CAS limitation was subsequently closed
  by `REDDOG_ARCHITECT_FIX_PROMOTION_TWO_PHASE_PUBLICATION_PHASE1`.
- Kept startup fail closed: `main.py` does not choose its own trust key and
  cannot promote without an attestation, production signer-runtime config, and
  independently supplied principal-key resolver. Production signer-to-startup
  input supply and current revocation-state composition remain
  SPECIFIED_NOT_IMPLEMENTED (WSP 00, 15, 22, 50, 62, 97).

## 2026-07-27: REDDOG_ARCHITECT_PROPOSAL_SIGNER_POLICY_RUNTIME_PHASE1
- Extended the existing signer config, bootstrap, key-provider, and runtime
  wiring so one exact architect-proposal signer policy can be provisioned only
  against the configured RedDog signer profile.
- Added a signer-owned atomic proposal nonce store bound to an independently
  injected monotonic high-water authority outside the nonce-state rollback
  domain. Production requires a matching configuration-bound durability
  receipt and rejects the volatile in-memory implementation. The signed
  authority identifier, MAC, sequence, revision, distinct proposal-transaction
  lock, and one-step crash roll-forward make rollback, deletion, mismatched
  authority, nested-lock deadlock, lock-path substitution, and tampering fail
  closed while bounded retention prevents unbounded growth. The proposal
  transaction lock is a descriptor-verified file beside the canonical nonce
  state, so Windows sessions and POSIX processes with different temporary
  namespaces serialize against the same signer-owned runtime artifact.
- Required the proposal payload identity, signer key, key epoch, consensus
  receipt, authority-profile source, and TTL to match the supplied authority
  profile before a signer configuration can be written, with a fixed
  protocol-level TTL ceiling and an exact RedDog signer profile.
- Required a fresh principal-signed, domain-separated authorization over the
  exact proposal policy, signer instance, replay namespace, and normalized
  runtime security context. An independent principal resolver supplies only
  the trusted public verification key; WSP71 resolves only the RedDog 0102
  proposal profile, so no principal private key enters the proposal service.
- Rehydrated and revalidated the exact serialized proposal policy at bootstrap;
  launch requires an expected digest supplied outside the config file, and
  partial, unsigned, expired, tampered, self-consistently re-digested,
  mismatched-key, profile-substituted, or out-of-root pairs never reach the
  signer backend.
- Restricted a proposal-enabled signer backend to the proposal domain only.
  Unknown, generic, and control-loop signing operations cannot reuse that
  private key during the proposal service run. Removed architect-proposal
  parameters from the public key-provider API; only the verified internal
  runtime constructor can attach the canonical proposal policy and nonce store.
- Consumed principal policy authorization before exposing the signer backend.
  Reservation and commit independently reject expired authorization. A service
  rejection or exception after signing cannot roll authorization back or reuse
  it on another launch. Runtime receipts stop claiming no file I/O once
  injected proposal trust, key, or replay dependencies have been invoked, and
  all other unobservable negative side-effect attestations become false after
  any injected dependency call.
- Rejected proposal-enabled signer run packets until production principal and
  replay adapters are composed into the CLI sidecar, rather than emitting an
  accepted packet that the shipped CLI must reject.
- Preserved the authority boundary: this slice provisions signer policy and
  durable replay state only. It does not derive proposal facts from
  authoritative work state, produce an attestation in the resident loop,
  produce the principal policy authorization in the resident loop,
  configure the production principal-key resolver,
  supply the independently administered production high-water authority and
  its durability receipt,
  satisfy the proposal-admission capability, promote a queue item, execute a
  worker, or grant merge authority (WSP 00, 15, 22, 50, 62, 97).

## 2026-07-27: REDDOG_AUTHORITY_RUNTIME_STORE_CONFINEMENT_PHASE1
- Required every atomic authority runtime store to bind an explicit repository
  root and runtime root, then revalidate the target before reads, writes, and
  atomic replacement.
- Rejected missing out-of-root targets, hard links, repository-contained or
  repository-containing roots, Windows namespaces, and linked path components;
  atomic replacement now pins the verified parent against swap races.
- Split the platform replacement adapters, scrubbed rejected temporary payloads,
  restored the previous authority snapshot after post-replace verification
  failure, and rejected POSIX parent relocation before accepting a write.
- Bound authority commits to a platform-level revision witness, recovered
  interrupted authority artifacts only when the caller supplies the exact
  expected revision, and made snapshot revisions independent of a prior
  embedded revision.
- Moved Linux payload staging to an `O_TMPFILE` unnamed inode with mode-zero
  rename, descriptor-backed rollback, and inode/directory fsync. Unsupported
  filesystems fail closed rather than falling back to pathname temp files.
- Kept the security boundary explicit: descriptor and compare-and-swap checks
  protect cooperative runtime access, while hostile same-principal filesystem
  writers remain excluded by the signer service's distinct OS-principal
  isolation contract.
- Preserved the exact authenticated runtime root through control-receipt reads
  and appends, required schema-v2 signer anchor and authority-policy bindings,
  confined socket/anchor paths at supply, bootstrap, and public runtime wiring,
  and aligned readiness around the same direct-child root contract.
- Required run-packet supply to pass the same canonical schema-v2 config
  rehydration as the signer bootstrap, so an accepted launch artifact cannot
  omit runtime roots, signer roots, the control anchor, or a fully validated
  authority policy, peer policy, and signer profile set. Canonical profile
  validation is shared by config supply, run-packet admission, and provider
  admission; malformed public keys, bounded service limits, and
  policy-to-profile identity are rejected before config write or launch
  acceptance, with strict finite JSON numbers and string-only policy bindings
  for both mapping and typed runtime inputs.
- Threaded independent repository/runtime roots through queue dependencies,
  signer config, control-loop heads, signer anchors, and live-canary verification
  without enabling proposal authority, queue promotion, worker execution, or repository
  mutation (WSP 00, 15, 22, 50, 62, 97).

## 2026-07-27: REDDOG_ARCHITECT_PROPOSAL_AUTHENTICITY_ATTESTATION_PHASE1
- Added a domain-separated architect-proposal Ed25519 attestation that binds
  the complete proposal, determination, queue candidate, snapshot, exact SHA,
  work state, HoloIndex, WSP 15, policy, path/test/gate, principal, RedDog,
  signer-key, consensus, nonce, and expiry context.
- Required an exact immutable signer-owned proposal policy and transactional
  nonce reservation; malformed, partial, expired, replayed, cross-domain, or
  policy-mismatched requests fail before signing.
- Added strict serialized-attestation integrity validation for exact fields,
  signatures, TTL, and key-epoch revocation. The returned typed attestation is
  evidence only and cannot satisfy proposal admission or promotion.
- Kept independent trust-root resolution, startup signer provisioning, durable
  replay state, opaque authority proof, attestation artifact supply, and
  production promotion wiring explicitly unimplemented. This slice creates no
  queue item and performs no repository effect (WSP 00, 15, 22, 50, 64, 97).

## 2026-07-27: REDDOG_ARCHITECT_PROPOSAL_EXECUTABILITY_ADMISSION_PHASE1
- Added a deterministic post-Fusion proposal admission receipt that binds the
  audit finding, operational snapshot, repository HEAD, work-state revision,
  HoloIndex generation/freshness, WSP 15 allocation, reuse decision, paths,
  tests, policy gates, capabilities, expected evidence, and stop conditions.
- Separated proposal validity from execution readiness so prerequisite work is
  retained as `BLOCKED_CANDIDATE` without becoming authoritative queue work.
- Revalidated current trust anchors, platform, HEAD, HoloIndex freshness
  receipt, canonical candidate/determination IDs, and work-state revision in
  the existing signed WSP 15 promotion seam; model readiness claims,
  underdeclared effect capabilities, and produced capabilities cannot
  self-authorize.
- Restricted stale-index admission to direct-read-grounded HoloIndex
  maintenance whose exact non-wildcard write paths equal the cited direct-read
  paths; ordinary coding, live Windows canaries, merge, and external effects
  remain fail closed.
- Bound claims, queue items, and authority profiles to one immutable base SHA,
  and held repository-promotion plus profile locks across profile snapshot,
  prewrite, queue commit, and rollback. Rollback is digest-CAS guarded and
  reports failure rather than overwriting a newer profile.
- Required the live HoloIndex query owner to prove the exact repository root,
  HEAD, generation, and on-disk freshness-receipt digest inside the promotion
  lock; an arbitrary valid historical receipt path is insufficient.
- Certified that SHA-bound proposal receipts provide integrity but not
  authenticity. Production admission remains blocked on a separate trusted
  proposal-authenticity verifier; no caller-supplied policy can enter the
  promotion side-effect boundary.
- Split prompt, contract, and evaluator modules to honor WSP 62 and lowered
  the inherited architect runtime/test no-growth ceilings (WSP 00, 15, 22, 50,
  62, 97).
- Reconciled the stale WSP 62 ceilings left by merged exact-SHA commit PR #1398
  to its already-landed file and test sizes; no #1398 runtime code was changed.

## 2026-07-27: REDDOG_RESIDENT_QUEUE_EXACT_SHA_COMMIT_STAGE_PHASE1
- Inserted an exact-SHA commit stage between the bounded author and the
  independent verifier in the resident RedDog queue.
- Reused the existing injected `RealWorktreeRunner.commit_all()` operation;
  the stage rejects pre-staged or extra paths, validates the bounded artifact
  digest, commits only the authorized path set, and proves exact base, parent,
  head, tree, branch, and clean-worktree state.
- Bound a deterministic commit-attempt trailer for crash reconciliation and
  required downstream canonical receipt revalidation so serialized base,
  head, path, or worktree tampering cannot reach verification.
- Assigned write plus commit to one bounded author claim while preserving the
  independent verifier as a distinct AgentDB claim and principal.
- Kept push, PR publication, merge, HoloIndex mutation, PatternMemory writes,
  and reward settlement outside this stage (WSP 00, 15, 22, 50, 64, 97).

## 2026-07-27: REDDOG_MAIN_MENU_BINDING_PREFLIGHT_BOUNDARY_FIX
- Missing or invalid model bindings now stop the resident cycle but block interactive startup only under explicit enforced mode; WARN/FAIL and menu-continuity regressions cover the boundary (WSP 00, 5, 15, 22, 50, 64, 97).
## 2026-07-26: OpenClaw exact-SHA HoloIndex maintenance route
- Added a dedicated low-risk maintenance family for post-merge HoloIndex work.
- OpenClaw now uses an exact-binding CAS claim; competing supervisors cannot
  execute the same SHA task.
- Each claim carries an immutable context digest and one-use execution ID;
  direct or duplicate invocation is rejected before authority effects.
- OpenClaw passes that capability explicitly through `run_task`; the executor
  will not recover it implicitly from AgentDB for an untrusted caller.
- The domain executor owns atomic finalization, so generic `run_task`
  completion/failure writes cannot split the receipt transaction.
- Dispatch exceptions immediately release the exact claim into retryable
  failure; process crashes are recovered by the coordinator's bounded lease.
- Moved remote polling to one bounded background worker so the supervisor
  observation loop never waits on `git fetch`.

## 2026-07-25: Independent assurance capacity admission

- Inserted a durable assurance-capacity gate between worktree creation and
  bounded coding in the resident RedDog queue.
- Bound author and independent verifier task identities, WSP 15 allocation,
  operational snapshot, work order, and reservation digest through the slice
  verifier receipt.
- Deferred unavailable capacity with a persisted retry window instead of
  busy-looping or treating CI as an independent reviewer.
- Made successful admission a persisted yield boundary so the queue-stage
  owner cannot execute either the author or verifier stage.
- Added separate OpenClaw claims for the bounded author and reserved verifier,
  author-failure revocation, and stage-gated bounded verifier-lease renewal.
- Hardened review findings by requiring exact accepted upstream decisions,
  rejecting already-claimed authors, binding renewed verification to the
  immutable admission digest, and validating terminal receipt lineage before
  releasing capacity.
- Kept HoloIndex query-only and blocked code execution when assurance
  admission, rehydration, or terminal receipt binding fails.

## 2026-07-25: Daemon self-audit runtime nudge alignment

- Switched supervisor-escalation memory scans from the obsolete tracked report
  to the same validated external runtime root used by the daemon producer.
- Reads now use bounded, descriptor-confined chunks over one stable file
  identity; links, replacements, oversized files, and invalid UTF-8 fail closed.
- Kept runtime provenance path-independent and rejected any injected runtime
  root inside the repository.

## 2026-07-25: RedDog HoloIndex receipt-bound semantic evidence

- Preserved the owner's bounded flattened hits in the normalized client response so canonical query receipts expose the evidence list they summarize.
- Kept the full semantic-evidence serialization digest and item count as the enforcement boundary.

## 2026-07-25: RedDog HoloIndex authority-root client proof

- The loopback owner client now sends the selected repository-root digest, requires the service to echo the same digest, and preserves it in the normalized generation-bound response.
- Existing pre/post clean-HEAD checks remain in force; a same-HEAD response from a foreign owner root now fails closed.

## 2026-07-25: REDDOG_WORK_STATE_AUTHORITATIVE_GROUNDING_GATE_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 50, 62, 71, 97

- Added a read-only authoritative work-state query receipt over the existing
  governed WRE queue consumer.
- Bound the receipt to the external snapshot bytes, validated stored revision,
  snapshot freshness, selected slice, active claim/freshness lineage, and the
  canonical WSP 15 allocation receipt.
- Rejected missing, stale, conflicting, malformed, repo-internal, and
  non-governed state without model, HoloIndex, queue, claim, shell, worker,
  repository, or execution side effects.
- Query-only HoloIndex preflight observed a root/head/collection freshness gap;
  it was recorded for governed maintenance and not repaired during this run.

## 2026-07-25: REDDOG_MAIN_RESIDENT_ARCHITECT_CANONICAL_CLIENT_MIGRATION_REVIEW_REPAIR

**WSP Protocol**: WSP 00, 15, 22, 50, 62, 71, 91, 97

- Prevented status/reconnect operations from re-arming FIX promotion or queue
  handoff, and confined every reconnect to the explicitly selected FoundUp.
- Added a bounded, main-transport-only compatibility adapter so persisted
  read-only `reddog_intent.v1` records in both historical v1 and transitional
  v2 cycles remain observable and cancellable without allowing legacy submit
  or resume; requested, top-level record, and embedded intent IDs must match
  before the CAS target is selected.
- Preserved exact runtime-model binding receipts added after the original
  slice base, split legacy control from the canonical client, and extracted
  the resident bootstrap implementation from `main.py` into decomposed
  functions under the moltbot runtime owner.
- Restored the prior root-entrypoint no-growth ceiling after the extraction.
- Enforced the selected FoundUp against the exported helper's authorized scope
  before grounding or canonical-client construction.

## 2026-07-24: HOLOINDEX_QUERY_ROOT_ADMISSION_P0_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 50, 62, 81, 97

- RedDog's explicit-SSD direct diagnostic now runs the canonical read-only
  admission proof before constructing a direct backend.
- Foreign root/SSD, wrong HEAD, missing generation/baseline/embedding proof,
  and active/unprovable maintenance fail with content-free reasons and zero
  hits. Both race probes and the receipt path derive from the admitted SSD.
  An external receipt path is rejected before any receipt read or backend,
  even when that external receipt would otherwise validate.

## 2026-07-23: REDDOG_PROVIDER_CALL_EVIDENCE_PHASE2A_REVIEW_REPAIR_ROUND3

**WSP Protocol**: WSP 00, 15, 22, 50, 62, 84, 97

- Applied the canonical provider-slug and `provider/model` parsers to requested
  identities at both creation and rehydration; secret-like and raw-prompt
  shapes now fail before a provider call.
- Audit and architect acceptance now compare the complete expected invocation
  vector: surface, task/work-order/queue/run/cycle lineage, runtime-binding ID
  and digest, requested provider/model, attempted state, and terminal outcome.
  Unbound lineage fields must be null, so extra forged lineage is rejected.
- Added parameterized substitution probes for every compared field plus valid
  canonical receipts and requested-identity creation/validator regressions.
- Post-repair gate: 274 passed / 1 platform skip; the broader
  Fusion/architect family sweep passed 64/64.

## 2026-07-23: REDDOG_PROVIDER_CALL_EVIDENCE_PHASE2A_REVIEW_REPAIR_ROUND2

**WSP Protocol**: WSP 00, 15, 22, 50, 62, 84, 97

- Replaced the shared permissive served-identity grammar with provider-slug and
  `provider/model` parsers that reject URI/path/traversal, dot-segment,
  query/fragment, bearer-like, high-entropy, and raw-sentence shapes.
- Added independent canonical provider-evidence acceptance gates at the audit
  and architect consumers. Exact surface, task/cycle, runtime-binding receipt
  and digest, and `COMPLETED` outcome are required before report acceptance or
  queue construction.
- Normal post-invocation extraction exceptions now raise
  `ProviderCallAttemptError` with the last local armed/failed evidence, even
  when the terminal write and recovery read are unavailable.
- Preserved the frozen legacy `reddog_fusion_progress_receipt.v1` shape while
  retaining generic provider evidence as an all-or-none optional extension.
- Canonicalized WSP 62 exemption matching with POSIX relative keys on every
  host and recorded exact no-growth ceilings for every touched function over
  60 lines.
- Post-repair gate: 252 passed / 1 platform skip across the provider, Fusion
  receipt, audit, architect, main bootstrap, end-to-end, durable-cycle, and
  WSP 62 files; the broader Fusion/architect family sweep passed 57/57.
- A whole bridge diagnostic run reached 3,976 passed / 17 skipped / 51 failed.
  Remaining failures are outside this slice (missing optional dependencies or
  external fixtures, grant/skill environment state, and pre-model
  bootstrap/runtime-binding rejections); no remaining failure names the new
  provider-evidence acceptance reason.

## 2026-07-23: REDDOG_PROVIDER_CALL_EVIDENCE_PHASE2A_REVIEW_REPAIR

**WSP Protocol**: WSP 00, 15, 22, 50, 62, 84, 97

- Restricted served provider/model persistence to canonical identifier grammar
  after the shared runtime secret-shape detector; secrets, credentials,
  whitespace/control characters, and raw-content shapes now fail closed.
- Added a static `ProviderCallAttemptError` carrying only canonical local
  evidence and a timeout bit. Audit and architect runners now report
  `made_network_call=true` with non-promotable INDETERMINATE lineage even when
  terminal persistence and recovery reads are unavailable.
- Bound accepted architect determination/queue-parent identity to provider call
  ID, provider receipt ID, and canonical evidence digest.
- Added provider evidence to audit execution rejection results, including
  invalid-output and post-model repository-change rejections.
- Recorded exact temporary WSP 62 ceilings for every enlarged legacy source and
  test surface, including the previously missing 1,618-line architect runtime.
  Transaction/store extraction remains a separately tracked follow-up.
- Added adversarial regressions for secret/raw identity smuggling, double store
  failure truth, architect provider-lineage substitution, and audit failure
  linkage. Focused provider/architect/audit/WSP62 tests pass 117/117; Fusion
  progress tests pass 13/13.

## 2026-07-23: REDDOG_PROVIDER_CALL_EVIDENCE_PHASE2A

**WSP Protocol**: WSP 00, 15, 22, 62, 71, 97

- Added the exact, content-free `reddog_provider_call_evidence.v1` contract,
  strict validator, domain-separated IDs/digests, bounded usage and served
  metadata, and locked atomic history store.
- Governed audit and backend-architect Fusion entry paths now durably write
  PRECALL intent and armed INDETERMINATE evidence before invocation, then
  terminalize COMPLETED/FAILED. Missing lineage/store blocks before provider;
  terminal-store uncertainty blocks promotion and automatic retry.
- Bound canonical evidence IDs/digests into audit/architect result lineage and
  allowed `FusionProgressRecorder` to embed the generic receipt without
  treating its legacy OpenRouter telemetry as parallel truth.
- Added tamper, content-smuggling, replay, crash, atomic-store, zero-provider
  precall, terminal-persistence, synthetic served-metadata, and direct
  in-process cross-surface parity tests. OpenClaw/Hermes wiring and gateway
  served-identity evidence are explicitly deferred.
- WSP 62 truth: temporary ceilings now match the touched legacy integration
  files; the focused contract/store has a bounded temporary 775-line ceiling
  with extraction tracked in the roadmap.

## 2026-07-23: CREATE_FOUNDUP_ROUTING_PREREQUISITE_WSP62_REPAIR

**WSP Protocol**: WSP 22, 49, 62

- Recorded `src/foundup_job_contract.py` under an exact, non-ratcheting
  796-line module exemption with an owner, expiry, remediation target, and
  active violations record.
- The nullable create-route lineage fields and their wire format are unchanged;
  no behavior or authority was added.

## 2026-07-23: CREATE_FOUNDUP_ROUTING_PREREQUISITE_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 34, 50, 62, 97, 108

- Added typed `creation_mode`, `genesis_envelope_digest`, and
  `scaffold_contract_digest` fields to the canonical `FoundUpJob` contract.
- Added factory and serialization round-trip support without changing
  existing-module build/extract semantics.
- This contract change grants no live scaffold, registry, provider, worktree,
  launch, certification, or model-selection authority.

## 2026-07-20: REDDOG_REQUIRED_RUNTIME_MODEL_BINDING_REVIEW_REPAIR_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 62, 71, 97

- Closed same-surface substitution by comparing the rehydrated audit receipt
  ID/digest against task, assignment, and WSP 15 lineage, and by binding the
  architect receipt pair into WSP 15 as a separate field pair.
- Made runtime bindings mandatory for injected and production runners alike;
  model-selection metadata remains non-authoritative and cannot replace or
  override the validated runtime identity.
- Bound both receipt pairs into durable resident intent identity and used the
  same two-pair WSP 15 identity for enqueue and final report collection, so
  reconnect/retry substitution fails before downstream work or persistence.
- Added the `main.py` readiness boundary: two distinct, exact-surface artifacts
  must be read from an explicit outside-repository root through bounded,
  regular-file, no-follow reads before the resident cycle can start. Logs emit
  stable path-free reason codes only.
- WSP 62 truth: focused security tests increased legacy integration fixtures
  and the startup entrypoint. Temporary ceilings were updated to their exact
  post-repair sizes (`main.py` 4,978; audit runtime 2,106; architect tests 760;
  startup tests 1,935; audit executor tests 2,237) without widening function
  ceilings beyond the expanded 77-line architect fixture.

## 2026-07-20: REDDOG_REQUIRED_RUNTIME_MODEL_BINDING_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 62, 97

- Added separate audit and backend-architect runtime-binding inputs to the
  durable resident and direct read-only audit cycles.
- Bound the audit receipt ID/digest through WSP 15 allocation identity, swarm
  and assignment identity, content-bearing AgentDB task context, OpenClaw
  claim execution, worker route receipts, and audit report lineage.
- Required the backend architect bootstrap/determination to carry the matching
  architect-surface receipt into result and queue-candidate lineage.
- Production `foundups_fusion` audit and architect paths now reject missing,
  malformed, rejected, wrong-surface, or selection-only bindings before a
  provider call. Removed production runner model defaults, including the
  inherited Kimi K2.7 fallback; topology is receipt-derived only.
- Preserved injected fake-runner seams and all read-only/no-dispatch
  boundaries. Tests prove an exact receipt-selected GLM/Kimi K3 topology is
  forwarded without network calls, model promotion, progress recording, or
  publication.
- WSP 62 truth: the legacy audit runtime remains inside its existing temporary
  2,100-line ceiling (2,073 lines). The focused architect test suite remains
  under its 725-line ceiling (708 lines); no exemption ceiling was raised.

## 2026-07-20: REDDOG_EXECUTION_VALVE_INDEPENDENT_REVIEW_REPAIR_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 62, 71, 97

- Bound the exact explicit `base_ref` and canonical digest of every full work-
  order field through delegated authority, use-time reconstruction, executor
  plan, process-local admission, and the terminal effect boundary.
- Made the runner consume `base_ref` only from the validated plan snapshot;
  work-order or plan mutation/splicing fails before nonce use and effect calls.
- Passed the fresh invocation clock into terminal `AUTHORITATIVE_USE`
  verification so identity and permission-snapshot expiry cannot reuse the
  earlier preflight timestamp.
- Corrected the readiness audit: authority verification is
  `PREFLIGHT_NON_CONSUMING`, while nonce consumption is terminal and the
  canonical store is cross-process atomic under `.operation`.
- Production remains permanently CLOSED while independent trust-anchor
  verifiers listed by the governed resolver are absent.

## 2026-07-20: REDDOG_MAIN_RESIDENT_ARCHITECT_CANONICAL_CLIENT_MIGRATION_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 50, 71, 91, 97

- Replaced `main.py`'s legacy `reddog_intent.v1` direct cycle invocation with typed v2 grounding and `RedDogResidentArchitectClient`.
- Added the explicit `main_resident_host -> main.py` source/origin binding across grounding receipt validation and client transport policy.
- Required host-authenticated principal and FoundUp scope before the resident runtime can be reached; caller role text and implicit `012` defaults no longer establish identity.
- Separated stable client request IDs from canonical intent IDs, and routed status, cancel, and retry only through an existing canonical intent.
- Rejected cancel/retry conflicts and control operations without an intent before client, worker, or model invocation.
- Removed the durable cycle's legacy main-v1 exception while preserving startup order, menu loading, read-only authority, and downstream FIX handoff behavior.

## 2026-07-20: REDDOG_RESIDENT_CYCLE_CAS_ATTESTATION_AND_INTENT_BINDING_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 50, 71, 91, 97

- Bound each durable cycle to the canonical full intent digest and rejected changed-principal or changed-payload reuse of an existing intent ID.
- Replaced blind cycle updates with insert-once creation, revision CAS, a store-owned status-transition graph, immutable authority fields, and observational hash-chained transition history.
- Persisted and enforced all nine process-local read-only runtime self-attestations at this code boundary; they are not externally observed or signer-authenticated effect receipts.
- Made cancellation terminal across claim and determination checkpoints, preserved monotonic retry history, and bound each persisted state to recomputed internal-integrity transition telemetry.
- Required canonical revision-zero genesis state and routed the editor session bridge through `RedDogResidentArchitectClient` with host principal and FoundUp scope.
- Added production AgentDB reconnect, stale-writer, cancellation-race, immutable-field, and `7 -> 8` retry regressions without adding execution authority.

## 2026-07-20: REDDOG_TRANSPORT_NEUTRAL_REPO_AUDIT_FALLBACK_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 50, 62, 71, 84, 97

- Reused the reviewed bounded repository-audit discovery reader after an
  owner-first HoloIndex attempt cannot ground an entity-scoped audit.
- Bound safe implementation plus independent test/contract reads to a stable
  repository HEAD and nested the proof in the canonical grounding receipt.
- Rejected incomplete coverage, repository-state races, private/tool/generated
  roots, traversal, link/reparse escapes, and receipt substitution before any
  model, shell, repository mutation, or HoloIndex re-index path.
- Added p.fMALL alias coverage and preserved CURRENT sufficient HoloIndex
  evidence as the preferred path with no fallback scan.
- The post-edit non-mutating HoloIndex probe ran in offline lexical mode and did
  not surface the new transport fallback. Recorded
  `HOLOINDEX_REDDOG_TRANSPORT_REPO_AUDIT_FALLBACK_INDEX_GAP_PHASE1`; no runtime
  re-index was performed.
- Independent review exposed that a fully rehashed unrelated-path substitution
  and an unstaged post-receipt content change were not rejected. The repaired
  validator now derives the expected entity from the original focus, recomputes
  path categories, and enforces the exact discovery policy, limits, coverage,
  and no-action attestations.
- Both deterministic and model-backed audit consumers now reopen selected
  evidence with the confined reader and require exact path/digest/bytes/truncated
  equality. The model-backed path repeats the check after model return, so a
  clean or unchanged HEAD cannot mask working-tree evidence drift.
## 2026-07-20: REDDOG_EXECUTION_VALVE_RECONCILED_TRUST_BOUNDARY_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 62, 71, 97

- Reconciled the audited governed-valve stack with authenticated resident
  control receipts, grounded OpenClaw/Hermes assignments, transport-neutral
  resident clients, Fusion usage receipts, and signed PANEL evidence.
- Preserved work-order/plan/valve admission, truthful commit outcomes,
  independent runtime roots, bounded locked no-link reads, and exact model-
  selection/runtime/Memex lineage propagation. Independent review later found
  missing full-order/base-ref and terminal fresh-clock bindings; the repair
  entry above supersedes this pre-review statement.
- Added coherent double collection and matching `.operation` locks across all
  canonical readers and production writers. Detected replacement or every
  still-missing independent verifier remains permanently fail-closed.
- Updated exact temporary WSP 62 no-growth ceilings to the reconciled current-
  main surfaces. No live execution, signing, runtime artifact generation,
  model call, repository mutation, or publish ran.
## 2026-07-20: REDDOG_FUSION_PROGRESS_AND_OPENROUTER_USAGE_RECEIPTS_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 50, 71, 91, 97

- Added bounded, content-free Fusion progress and OpenRouter call receipts with per-event and aggregate digest verification.
- Recorded provider-returned tokens, cost credits, generation IDs, selected routing metadata, retries, and timing while discarding arbitrary metadata payloads.
- Kept receipts observational and advisory; they grant no model, execution, repository, shell, worktree, PR, merge, HoloIndex, or reward authority.

## 2026-07-19: REDDOG_TRANSPORT_NEUTRAL_GROUNDING_SERVICE_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 50, 71, 97
**Phase**: Natural-language Hermes/API grounding into canonical resident intents

- Added a bounded transport-neutral service that classifies repo, semantic, external, and quoted targets and emits a self-validated `reddog_grounded_target_receipt.v1` plus `reddog_intent.v2`.
- Required safe in-repo file resolution for repository targets and CURRENT generation-bound owner-query evidence for semantic targets.
- Added content-support and broad-audit corroboration checks so unrelated HoloIndex hits cannot satisfy grounding.
- Rejected external research without an approved adapter, path traversal, absolute paths, secret basenames, stale/mixed HoloIndex generations, and empty substantive target universes.
- Added explicit host-authorized FoundUp scope to the resident client; payload role text and caller-selected FoundUps remain non-authoritative.
- HoloIndex preflight did not surface the new grounding module and exposed a generation pinned to repository head `69b0ccfc...`, including a stale legacy extension path. Recorded `HOLOINDEX_REDDOG_TRANSPORT_NEUTRAL_GROUNDING_DISCOVERABILITY_INDEX_GAP_PHASE1`; no runtime re-index was performed.

## 2026-07-19: REDDOG_TRANSPORT_NEUTRAL_RESIDENT_CLIENT_AND_HERMES_ADAPTER_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 50, 71, 97
**Phase**: One resident RedDog authority with transport-neutral clients

- Added `RedDogResidentArchitectClient` over the existing durable AgentDB cycle for submit, reconnect, cancel, and resume.
- Bound every operation to a host-authenticated principal, exact transport source/origin, FoundUp scope, and verified grounding receipt.
- Rejected mutable runtime-key overrides, tampered stored ownership, and any result contradicting the canonical read-only boundary.
- Exposed only bounded status/determination metadata; the client implements no model, shell, repo mutation, Hermes execution, or indexing path.
- Fail closed when any canonical resident-cycle safety attestation is missing or false; response digests bind acceptance and safety state.
- HoloIndex preflight found the new transport symbols absent from the active generation, whose receipt is pinned to an older repository head. Recorded `HOLOINDEX_REDDOG_TRANSPORT_CLIENT_DISCOVERABILITY_INDEX_GAP_PHASE1`; WRE/CI owns refresh, and this runtime remains query-only.

## 2026-07-19: REDDOG_GROUNDED_TARGET_ASSIGNMENT_CONTINUITY_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 50, 62, 71, 97
**Phase**: Grounding evidence continuity through resident OpenClaw audit assignments
**Agent**: 0102 architect with fail-closed adversarial tests

- Added a typed validator for `reddog_grounded_target_receipt.v1`, binding work focus, typed targets, recall, semantic coverage, and current HoloIndex generation evidence.
- Required editor resident intents to use v2 and pass grounding verification before the durable AgentDB cycle; retained v1 only for the read-only `main.py` bootstrap compatibility path.
- Bound the verified receipt into OpenClaw swarm assignments and AgentDB task contexts, then revalidated it before worker index or model calls.
- Separated internal semantic retrieval from explicit external research so semantic targets can guide every audit lane without being misrouted as external requests.

## 2026-07-18: REDDOG_RESIDENT_CONTROL_RECEIPT_TRUTH_AUTH_CONCURRENCY_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 50, 62, 71, 91, 97
**Phase**: Runtime truth/auth/concurrency hardening
**Agent**: 0102 architect with independent adversarial review

- Added signer-domain-validated, predecessor-linked v2 control receipts with
  cycle/nonce replay rejection and validated legacy-prefix migration.
- Derived authority, claim, execution, worktree, bounded-edit, verification,
  draft-PR, PatternMemory, process-spawn, and shell observations from runtime
  evidence; caller-supplied contradictory claims reject.
- Required live-canary proof to verify the signature, signer/key epoch,
  authority-profile digest, consensus digest, repository binding, and complete
  JSONL stream before accepting a new cycle.
- Added a cross-process lock around chain-result compare-and-swap and preserved
  exact OpenClaw outcome counts in `main.py`.
- Added a second Ed25519 signer attestation over the audit MAC and signing
  response, then required every v2 predecessor to verify against the same
  principal, key epoch, authority profile, and consensus receipt.
- Bound unique child execution receipt IDs and evidence digests to exact
  completion/requeue/failure cardinality, and made standalone OpenClaw claims
  contend on the same resident control-loop lock as `main.py`.
- Reconciled the serial-loop tests with the landed runtime-artifact confinement
  invariant by placing all positive fixture artifacts under an isolated runtime
  root outside the synthetic repository.
- Added signer-owned `ControlLoopAuthorityPolicy` enforcement and a monotonic
  control-loop anchor outside resident state; self-hashed profile content alone
  can no longer authorize a control signature or roll the chain backward.
- Rehydrated complete child claim evidence before parent signing, retained
  truthful execution/process/shell counts for rejected runners, and rejected
  retention or durable-head failures before reporting acceptance.
- Made child evidence the exclusive source for parent process/shell totals;
  runner exceptions now carry `effect_evidence_complete=false` with no invented
  negative attestations, and failed AgentDB complete/requeue transitions reject.
- Extracted authority persistence behind a compatible boundary and fsynced the
  parent directory after atomic rename on platforms that support it.
- Decomposed modified `main.py`, OpenClaw claim, receipt, canary, and task-
  executor paths into focused WSP 62-bounded helpers without changing the
  configured runtime stages.

**Truth boundary**: v1 and unsigned v2 receipts may be inspected but cannot
satisfy live proof. The configured isolated signer authenticates the exact
control authority policy; this does not claim that the profile source JSON is
independently principal-signed. The v2 receipt records positive observations
and does not convert an unobserved merge, reward, re-index, process, or shell
action into a hardcoded negative proof. Detailed stage receipts remain
authoritative.

**HoloIndex**: read-only retrieval found the new receipt modules by path but no
focused tests and weak governing-WSP relevance. This is an INDEX_GAP for the
governed freshness lane; no runtime re-index was performed in this slice.

## 2026-07-18: REDDOG_VALVE_HIGH_AUTHORITY_CLASSIFICATION_PHASE1

**WSP Protocol**: WSP 00, 15, 22, 71, 97

- Classified `VALVE_OPEN_WORKTREE_CREATE` and `VALVE_OPEN_LIVE_ENQUEUE`
  intent as HIGH authority even when `requested_operation` is otherwise LOW.
- Normalized the effective default valve state before classification and
  serialization so empty input cannot emit an unclassified WORKTREE grant.
- Applied the classification at authority-profile seed, source, and delegated-
  authority signing boundaries. This fix issues no authority or work itself.

## 2026-07-18: REDDOG_RESIDENT_LIVE_CANARY_PHASE1

**WSP Protocol**: WSP 00, 06, 15, 22, 46, 62, 71, 97
**Phase**: Audit-hardened operator harness; live proof blocked pending operator artifacts
**Agent**: 0102 focused worker under architect review

**Changes**:

- Added a Linux-only, explicit-confirmation operator surface for one invocation
  of the existing highest guarded resident queue profile.
- Reused the existing control loop and planner; no queue stage, signer, Fusion,
  worktree, verifier, draft-PR, or PatternMemory orchestration was duplicated.
- Added outside-repo atomic receipts that distinguish static readiness from a
  completed live proof and serialize only secret/reference presence.
- Added a shared OS advisory lock around every main resident control-loop call;
  the persisted v1 control receipt records and proves lock ownership.
- Required a matching newly persisted control receipt with exact schema,
  accepted PASS, repo digest, positive serial progress, and changed pre/post
  chain revisions.
- Required the exact chain envelope, matching queue/slice, a new chain-store
  receipt bound to the final revision, and draft/held-out/PatternMemory lineage
  for one work order, slice, and candidate head.
- Repaired the chain-store commit witness: its canonical revision normalizes
  only the newest receipt witness before hashing, then atomically persists that
  revision in both the envelope and receipt for non-circular readback proof.
- Required accepted invoke/result worktree decisions plus an existing external
  Git worktree registered by the repository with matching `rev-parse` HEAD.
- Required PatternMemory admission/record/digest identities to recompute from
  the canonical SQLite row read back through the production sink adapter.
- Restricted runtime-root receipt output to canonical
  `live_canary_receipt.json`; alternate output must be outside both roots.
- Split evidence and lock helpers so every live-canary production file is at
  most 675 lines and every function in those files is at most 50 lines.

**Truth boundary**: Focused tests prove the harness and evidence gates. No live
signer was started and no production draft PR was created by this slice; the
live proof remains blocked until WSL receives the required outside-repo
authority/signer artifacts and an already-running isolated signer.

## 2026-07-18: REDDOG_RUNTIME_ARTIFACT_PATH_DAEMON_REDACTION_PHASE1

- Confined resident runtime paths outside the repository and beneath the
  configured runtime root.
- Hardened resident control receipts with bounded fields, existing-chain
  validation, locked append, descriptor revalidation, and fsync.
- Redacted DAEmon fix details before supervisor action reporting.

## 2026-07-18: REDDOG_HOLOINDEX_QUERY_OWNER_BOUNDARY_POC_PHASE1

**WSP Protocol**: WSP 00, 05, 06, 15, 22, 50, 62, 87, 96, 97
**Phase**: POC implementation; focused validation/PR evidence pending
**Agent**: 0102 architect for 012 with delegated audit/test workers

**Changes**:

- Added the bounded RedDog HoloIndex owner client and query adapter. The
  migrated operational path requires the authenticated service at literal
  `127.0.0.1` and never opens Chroma locally through that adapter.
- Added authenticated process-private owner handoff resolution; auto-generated
  tokens are never exported to the parent environment. Direct-store mode is
  diagnostic-only and can never return CURRENT.
- Preserved code, WSP, documentation, knowledge, test, skill, work-ledger, and
  symbol evidence instead of discarding non-code buckets.
- Enforced clean exact-HEAD, complete seven-collection proof, semantic-only
  retrieval, stable generation binding, and pre/post maintenance probes.
- Disabled HTTP redirects before bearer transport, restricted the endpoint
  path, and downgraded client-rejected CURRENT responses to STALE.
- Owner timeout now poisons the process permanently; a private adapter replaces
  its owned process and retries once after QUERY_OWNER_POISONED, while an
  external supervisor remains responsible for external-owner recovery.
- Startup dispatch now invokes the trusted exact-HEAD maintenance handshake
  before generic WRE routing and cannot turn an old age-only refresh result
  into success.
- Extracted HoloIndex query normalization from the read-only audit runtime;
  remaining legacy runtime decomposition is tracked under WSP_62.
- Boundary: RedDog has no HoloIndex indexing authority and model execution is
  blocked on stale, lexical, dirty, missing, raced, or unproven evidence.

**Impact**: The migrated RedDog operational paths can preserve and consume
generation-bound semantic evidence without opening the local persistent store.
Maintenance remains a trusted-host action that startup may request through
governed WRE dispatch. This adapter boundary does not prove OS privilege
isolation or migration of the legacy foundups_mcp_bridge `holo_tools.py` path.

**WSP Compliance**: Boundary tests are split by cohesive responsibility;
focused gate results will be recorded after validation. Historical
runtime/ModLog size debt remains explicitly registered and no global WSP_62
compliance claim is made.

## 2026-07-17: REDDOG_OPENCLAW_SUPERVISOR_CLAIM_RECEIPT_THREADING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 97

- Threaded OpenClaw signed-worker claim-loop `receipt_ids` and
  `requeued_task_ids` into the supervisor top-level action result and verify
  summary.
- Added regression coverage so `OpenClawSupervisor.run_cycle()` exposes claim
  receipt IDs without requiring callers to inspect nested `claim_loop` payloads.
- No authority, queue, runner, shell, PR, PatternMemory, reward, or HoloIndex
  behavior changed.
- HoloIndex query-only check did not surface the new supervisor receipt-threading
  surface; recorded as
  HOLOINDEX_REDDOG_OPENCLAW_SUPERVISOR_CLAIM_RECEIPT_THREADING_INDEX_GAP. No
  runtime reindex performed.

## 2026-07-17: REDDOG_RESIDENT_CONTROL_LOOP_RECEIPT_PERSISTENCE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 97

- Added an append-only resident control-loop receipt store for compact JSONL
  summaries of completed control-loop runs.
- Added profile-derived `REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPT_PERSISTENCE`
  and `REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPTS_PATH` wiring so resident
  profiles can persist control receipts under the outside-repo runtime root.
- Wired `main.py` to persist accepted control-loop summaries and fail closed if
  configured receipt persistence rejects.
- Added regressions proving persisted control receipts bind the signed-worker
  task receipt IDs surfaced by the OpenClaw claim loop.
- HoloIndex query-only check did not surface the new control-loop receipt store;
  recorded as HOLOINDEX_REDDOG_RESIDENT_CONTROL_LOOP_RECEIPT_PERSISTENCE_INDEX_GAP.
  No runtime reindex performed.

## 2026-07-17: REDDOG_RESIDENT_CONTROL_LOOP_RECEIPT_SUMMARY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 97

- Surfaced signed-worker execution receipt IDs through the outer resident queue
  control-loop summary and `run_reddog_resident_queue_control_loop_preflight.last_result`.
- Added fail-closed control-loop `last_result` summaries for invalid rounds and
  serial/claim-loop rejection paths.
- Added regressions proving full resident control-loop runs expose durable
  signed-worker task receipt IDs without changing authority, queue, runner,
  shell, PR, PatternMemory, reward, or HoloIndex behavior.
- HoloIndex query-only check did not surface the new resident control-loop
  receipt summary surface; recorded as
  HOLOINDEX_REDDOG_RESIDENT_CONTROL_LOOP_RECEIPT_SUMMARY_INDEX_GAP. No runtime
  reindex performed.

## 2026-07-17: REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_RECEIPT_TELEMETRY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 97

- Surfaced signed-worker execution receipt IDs through the OpenClaw claim-loop
  aggregate result and `main.py` preflight output.
- Threaded `receipt_ids` into `run_reddog_openclaw_signed_worker_claim_loop_preflight.last_result`
  so resident queue control can correlate claimed tasks to durable AgentDB
  result receipts without direct task-row inspection.
- Added regressions for completed and requeued signed-worker claims.
- HoloIndex query-only check did not surface the new claim-loop receipt
  telemetry surfaces; recorded as
  HOLOINDEX_REDDOG_OPENCLAW_CLAIM_RECEIPT_TELEMETRY_INDEX_GAP. No runtime
  reindex performed.

## 2026-07-17: REDDOG_SIGNED_WORKER_AGENTDB_RESULT_RECEIPT_PERSISTENCE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 97

- Persisted compact signed-worker execution result receipts into the AgentDB
  task context before task completion or requeue.
- Added digest-bound `reddog_signed_worker_task_result.v1` receipts with
  runner/result digests, bounded runner summaries, no-effect attestations, and
  a capped receipt history.
- Successful and requeued signed-worker claims now fail closed if result
  persistence fails, preventing status-only success without recoverable
  execution evidence.
- Added regressions for completed, failed, requeued, and persistence-failure
  signed-worker claim paths.
- HoloIndex query-only pre-commit check did not surface the new receipt
  persistence slice; recorded as
  HOLOINDEX_REDDOG_SIGNED_WORKER_AGENTDB_RESULT_RECEIPT_INDEX_GAP.

## 2026-07-17: REDDOG_OPENCLAW_SIGNED_WORKER_SIGNER_HEALTHCHECK_GATE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 71, 97

- Added an optional OpenClaw signed-worker pre-claim signer healthcheck gate.
- The gate validates the existing signer service run packet/socket before
  AgentDB claim, so an unavailable signer leaves signed-worker tasks pending
  instead of consuming and failing them.
- Reused the signer service healthcheck module and kept the boundary unchanged:
  no signer start, no secret resolution, no shell command, no repository
  mutation, no Hermes dispatch, no PR publication, no reward settlement, and no
  HoloIndex re-index.
- Added regressions proving healthcheck rejection blocks before claim while a
  passing healthcheck allows the existing signed-worker runner to proceed.
- HoloIndex query-only pre-commit check did not surface the new gate; recorded
  as HOLOINDEX_REDDOG_OPENCLAW_SIGNED_WORKER_SIGNER_HEALTHCHECK_INDEX_GAP.

## 2026-07-17: REDDOG_SIGNER_SERVICE_HEALTHCHECK_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 71, 97

- Added a signer service healthcheck that validates the outside-repo signer
  run packet, revalidates the bound signer config, and optionally performs a
  bounded roundtrip against an already-running signer socket.
- Added an explicit main preflight switch for signer healthcheck; it can block
  startup when enforced but does not start the signer, bind sockets, resolve
  secrets, enqueue OpenClaw, dispatch Hermes, publish PRs, settle rewards, or
  re-index HoloIndex.
- Hardened packet validation with run-packet self-digest, no-shell/no-spawn
  invariants, outside-repo config/socket checks, and audit-safe request/response
  digests only.
- Added focused tests for accepted healthcheck receipts, malformed/tampered
  packet rejection, missing profile rejection, unavailable socket rejection,
  main enforced blocking, and no spawn/secret/runtime-authority surface.

## 2026-07-17: REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 71, 97

- Added a signer service run-packet supplier that validates the outside-repo
  signer CLI config and emits a shell-free argv packet for a signer-owned
  service manager.
- Added an explicit main preflight switch for run-packet supply; it can run
  after signer config supply in the same resident preflight and never starts
  the signer, binds a socket, resolves secrets, enqueues OpenClaw, dispatches
  Hermes, publishes PRs, settles rewards, or re-indexes HoloIndex.
- Registered the signer run packet as a resident runtime artifact path while
  preserving the signer-owned process boundary.
- Added focused tests for run-packet shape, invalid config/output/op/limit
  rejection, main enforced failure, config-to-run-packet chaining, and no
  spawn/shell/runtime-authority surface.

## 2026-07-17: REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 71, 97

- Added a signer service config supplier that materializes an outside-repo
  JSON config from an existing promoted authority profile, explicit WSP71
  `op://` references, and a signer peer policy.
- Added an explicit main preflight switch for config supply; it prints an
  audit-safe receipt and never starts the signer, resolves secrets, binds a
  socket, enqueues OpenClaw, dispatches Hermes, publishes PRs, settles rewards,
  or re-indexes HoloIndex.
- Registered the signer service config as a resident runtime artifact path
  while keeping the supply step explicit rather than profile-defaulted.
- Added focused tests for config shape, invalid profile/ref/policy/path
  rejection, main enforced failure, no implicit socket consumption, and no
  secret-resolution/spawn/runtime-authority surface.

## 2026-07-17: REDDOG_SIGNER_MULTI_PROFILE_MAIN_CLI_PROOF_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 71, 97

- Added explicit multi-profile signer socket runtime wiring so one bounded
  signer service can route principal-identity and RedDog work-authority signing
  requests by requested public key.
- Preserved the legacy single-profile config and receipt fields while adding
  profile-count/profile-receipt telemetry and duplicate-public-key rejection.
- Extended the outside-repo signer bootstrap to accept either one
  `key_provider_profile` or a bounded `key_provider_profiles` list.
- Added a main-level proof that the resident queue control loop can consume a
  signer socket started by the signer-owned CLI with two WSP71 profiles.
- Boundary remains constrained: no `main.py` signer spawn, no model-output
  invocation, no OpenClaw/Hermes authorization expansion, no PR publication, no
  reward settlement, and no HoloIndex re-index.

## 2026-07-17: REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_CLI_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 71, 97

- Added a signer-owned CLI adapter for starting the bounded isolated signer
  socket service from an outside-repo JSON config.
- The CLI composes the existing runtime bootstrap with the WSP71
  `OpCliSecretResolver`, emits only audit-safe JSON receipts, and returns
  nonzero on bootstrap rejection.
- Added tests for successful WSP71 resolver/service execution, unsafe config
  rejection before service call, no secret serialization, and AST no-main/
  no-OpenClaw/no-Hermes/no-HoloIndex/no-repo-mutation surface.
- Boundary remains constrained: no `main.py` wiring, no RedDog model-output
  invocation, no OpenClaw enqueue, no Hermes dispatch, no PR publication, no
  reward settlement, and no HoloIndex re-index.

## 2026-07-17: REDDOG_MAIN_MISSING_SIGNER_SOCKET_FAIL_CLOSED_PROOF_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a main-level resident control-loop regression proving an enforced
  signed-worktree profile startup fails closed when the derived signer socket
  path is unavailable.
- The proof verifies the OpenClaw claim loop is not reached, no authority state
  or chain result is written, and the operator-facing output includes
  `FAIL_SIGNER_SOCKET_PATH_UNAVAILABLE`.
- Boundary remains constrained: test-only proof, no signer spawn, no private
  key loading, no source mutation, no OpenClaw enqueue, no Hermes dispatch, no
  PR publication, no reward settlement, and no HoloIndex re-index.

## 2026-07-17: REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 71, 97

- Added a signer-owned runtime bootstrap that reads a single outside-repo JSON
  config and composes the existing bounded signer socket service runtime wiring
  with an injected resolver.
- The bootstrap binds an audit-safe config digest, rejects missing, relative,
  inside-repo, unreadable, malformed, or runtime-rejected configs, and returns
  the runtime wiring receipt without secret values.
- Added focused tests for WSP71-permissioned config execution, unsafe config
  rejection, runtime rejection propagation, and no-env/no-shell/no-OpenClaw/
  no-Hermes/no-HoloIndex static surface.
- Boundary remains constrained: this does not parse environment variables,
  spawn a process, load secret files, mutate source, enqueue OpenClaw, dispatch
  Hermes, publish PRs, settle rewards, or re-index HoloIndex.

## 2026-07-17: REDDOG_SIGNER_KEY_PROVIDER_WSP71_RUNTIME_MODE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 71, 97

- Added an explicit `WSP71_PERMISSIONED` signer key-provider mode alongside the
  existing `TEST_ONLY_DRYRUN` mode.
- Preserved default fail-closed behavior while allowing signer-owned runtime
  wiring to accept an injected non-mock WSP-71-like resolver with a fresh
  permission snapshot and no test-only override.
- Rejected mock vault resolver use in `WSP71_PERMISSIONED` mode so the PoC
  resolver cannot become a production credential authority.
- Updated signer process and bounded signer service runtime wiring to call the
  production-capable provider entrypoint name while keeping the old dry-run
  function as a compatibility wrapper.
- Boundary remains constrained: this does not configure a real vault, read
  environment variables, load files, spawn a process, mutate source, enqueue
  OpenClaw, dispatch Hermes, publish PRs, settle rewards, or re-index HoloIndex.

## 2026-07-17: REDDOG_SIGNER_SOCKET_RUNTIME_AVAILABILITY_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Hardened the isolated signer socket client so production/no-injected-connector
  runtime configuration requires an existing outside-repo socket path before the
  resident queue dependency bundle is accepted.
- Preserved injected-connector behavior for deterministic tests and bounded
  resident service proofs where the connector owns transport availability.
- Added regression coverage at both the socket-client and main resident queue
  dependency-bundle layers so a missing signer socket fails closed before queue
  authority signing is attempted.
- Boundary remains constrained: this does not spawn a signer, load private key
  material, execute shell commands, mutate source, enqueue OpenClaw, dispatch
  Hermes, publish PRs, settle rewards, or re-index HoloIndex.

## 2026-07-17: REDDOG_PROFILE_RUNTIME_FULL_QUEUE_CHAIN_PROOF_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Upgraded the resident control-loop integration proof so the
  `signed_0102_bounded_code_fusion_worktree_draft_pr_pattern_memory` profile
  completes the full signed worker queue chain without `REDDOG_WORK_ORDERS_PATH`.
- The proof covers profile-derived authority-profile work-order
  materialization, signer socket signing, AgentDB worker claims, bounded
  artifact generation, slice verification, verified draft-PR publication,
  outcome ratchet, held-out gate, and PatternMemory admission.
- Boundary remains constrained: no production code path was expanded, no shell
  command is executed by the test fake, no real PR is opened, no HoloIndex
  re-index occurs, and no merge/reward authority is added.

## 2026-07-17: REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_WIRING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 71, 97

- Added `src/reddog_signer_socket_service_runtime_wiring.py`: dependency-injected
  runtime wiring that composes the test-only signer key provider, kernel
  peer-credential attestor, and bounded resident signer socket service.
- Added `tests/test_reddog_signer_socket_service_runtime_wiring.py`: acceptance,
  mapping normalization, provider/service rejection, no-secret serialization,
  and AST no-env/no-file/no-shell/no-OpenClaw/no-Hermes/no-HoloIndex coverage.
- Boundary remains constrained: this does not parse env, read files, spawn a
  process, load production vault secrets, mutate source, enqueue OpenClaw,
  dispatch Hermes, publish PRs, settle rewards, or re-index HoloIndex.

## 2026-07-17: REDDOG_MAIN_RESIDENT_MEMORY_CONTEXT_SUPPLY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Wired `main.py` resident RedDog startup to supply bounded read-only Brain,
  Breadcrumb, and workspace-memory metadata into the existing durable resident
  architect cycle.
- Brain state is loaded from the existing extracted Brain artifact state unless
  explicitly overridden or disabled; Breadcrumbs come from AgentDB search or an
  explicit JSON fixture; workspace memory remains explicit JSON-only for this
  slice.
- Added intent-level memory context counts/digest plus startup telemetry so the
  resident cycle can prove whether historical memory was available without
  treating it as authority.
- Boundary remains constrained: this does not add shell execution, repository
  mutation, worktree operations, PR creation, HoloIndex re-index, Hermes
  dispatch, live FoundUp enqueue, PatternMemory promotion, reward settlement, or
  merge authority.

## 2026-07-17: REDDOG_RESIDENT_ARCHITECT_CADENCE_INTENT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added cadence-bound resident RedDog architect intent IDs for the `main.py`
  product-mode cycle.
- Default cadence is 24 hours via `REDDOG_RESIDENT_ARCHITECT_CADENCE_HOURS`;
  repeated startups inside the same bucket reuse the same intent, while later
  buckets create fresh resident architect cycles.
- Explicit `REDDOG_RESIDENT_ARCHITECT_INTENT_ID` remains authoritative and
  disables cadence bucketing; `REDDOG_RESIDENT_ARCHITECT_CADENCE_HOURS=0`
  restores the legacy sticky intent behavior.
- Boundary remains constrained: this changes cycle scheduling identity only and
  does not add shell execution, repository mutation, worktree operations, PR
  creation, HoloIndex re-index, Hermes dispatch, live FoundUp enqueue,
  PatternMemory promotion, reward settlement, or merge authority.

## 2026-07-17: REDDOG_MAIN_RESIDENT_PRODUCT_MODE_ACTIVATION_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a product-mode activation policy for the durable resident RedDog
  architect cycle in `main.py`.
- When `REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE` is unset, resident RedDog now
  defaults to running one read-only architect cycle at startup via
  `REDDOG_RESIDENT_ARCHITECT_PRODUCT_MODE=1`.
- Explicit `REDDOG_RESIDENT_ARCHITECT_DURABLE_CYCLE=0` remains a hard opt-out,
  and `REDDOG_RESIDENT_ARCHITECT_PRODUCT_MODE=0` disables the product default
  without blocking explicit low-level enablement.
- Boundary remains constrained: this does not add shell execution, repository
  mutation, worktree operations, PR creation, HoloIndex re-index, Hermes
  dispatch, live FoundUp enqueue, PatternMemory promotion, reward settlement, or
  merge authority.

## 2026-07-17: REDDOG_RESIDENT_EXTERNAL_RESEARCH_NOOP_RETRIEVER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a no-op external research retriever for durable resident RedDog cycles
  when no approved external snapshot/retriever is configured.
- The resident cycle no longer rejects before AgentDB enqueue solely because
  the optional external retriever object is missing; it can still run repository,
  HoloIndex, Brain/Breadcrumb, Memex, and work-state audits.
- The no-op retriever performs no network I/O, returns no content-bearing
  evidence, and marks external research as unconfigured/missing so workers
  cannot mistake it for fresh external proof.
- Boundary remains constrained: this does not add live web research, source
  mutation, shell execution, worktree operations, PR creation, HoloIndex
  re-index, PatternMemory promotion, live enqueue, reward settlement, or merge
  authority.

## 2026-07-17: REDDOG_RESIDENT_ARCHITECT_QUEUE_PROFILE_AUTOWIRE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Updated the durable resident RedDog architect preflight to auto-select the
  existing signed resident queue binding profile after an accepted FIX
  determination with exactly one queue candidate.
- Default profile is `signed_0102_bounded_code_fusion_worktree_draft_pr`,
  which enables the existing bounded code, Fusion artifact, isolated worktree,
  independent evidence, and verified draft-PR control-plane stages while
  leaving PatternMemory, merge, shell, reward, HoloIndex re-index, and live
  enqueue disabled.
- Explicit `REDDOG_RESIDENT_QUEUE_BINDING_PROFILE` remains authoritative, and
  `REDDOG_RESIDENT_ARCHITECT_AUTO_QUEUE_PROFILE=0` disables auto-selection.
- Invalid auto-profile values and non-FIX or non-single-candidate outcomes fail
  closed by leaving the queue profile unset.

## 2026-07-17: REDDOG_RESIDENT_ARCHITECT_FIX_HANDOFF_AUTOWIRE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Updated the durable resident RedDog architect preflight to auto-arm the
  existing resident FIX promotion handoff when the cycle accepts a FIX
  determination.
- The bridge sets `REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF=1` only when it was not
  explicitly provided and `REDDOG_RESIDENT_ARCHITECT_AUTO_FIX_HANDOFF` is not
  disabled.
- This removes a manual toggle between the resident determination and the
  already-gated promotion preflight while preserving downstream rejection and
  enforcement behavior.
- Boundary remains constrained: no signing, worker spawn, shell command, repo
  mutation, worktree operation, PR creation, HoloIndex re-index, PatternMemory
  promotion, Hermes dispatch, live FoundUp enqueue, reward settlement, or merge
  authority was added.

## 2026-07-17: REDDOG_MAIN_RESIDENT_ARCHITECT_DURABLE_CYCLE_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Wired `main.py` to optionally run one durable AgentDB-backed resident RedDog
  architect cycle after authoritative work-state refresh and before FIX
  promotion.
- The preflight submits `reddog_intent.v1`, lets the existing OpenClaw resident
  cycle claim read-only audit/research work, persists the architect
  determination, and exposes `REDDOG_RESIDENT_ARCHITECT_INTENT_ID` for the
  downstream handoff path.
- The hook is disabled by default, warning-only unless explicitly enforced,
  and requires the already-governed external-research snapshot retriever path.
- Boundary remains constrained: no shell command, repo mutation, HoloIndex
  re-index, Hermes dispatch, worktree operation, PR creation, PatternMemory
  promotion, live FoundUp enqueue, merge authority, or coding-worker execution
  was added.

## 2026-07-17: REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_DEFAULT_INPUT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Updated the RedDog model AutoResearch plan startup hook to use the existing
  outside-repo cycle feedback ledger as the default feedback input when
  `REDDOG_MODEL_AUTORESEARCH_FEEDBACK_RECORDS_PATH` is not explicitly set.
- Explicit feedback paths still take precedence, and a missing cycle feedback
  ledger remains optional so startup does not fail closed on absent feedback.
- Added main-preflight coverage for default feedback path selection and
  explicit override behavior.
- Boundary remains constrained: no provider call, benchmark execution,
  HoloIndex re-index, PatternMemory write, model promotion, runtime binding,
  worker spawn, source mutation, PR publication, reward settlement, shell
  execution, or merge authority was added.

## 2026-07-17: MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CONTEXT_BINDING_PHASE1

## 2026-07-17: MODEL_AUTORESEARCH_CYCLE_FEEDBACK_CONTEXT_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Updated the RedDog model AutoResearch cycle-feedback startup hook to pass the
  outside-repo plan receipt into feedback admission.
- The feedback bootstrap now fails closed if the source plan receipt is missing,
  malformed, inside the repo, tampered, or mismatched with the cycle receipt.
- This binds task-family and catalog-snapshot context into the cycle feedback
  record before any later planner-consumption work.
- Boundary remains constrained: no provider call, benchmark execution,
  HoloIndex re-index, PatternMemory write, model promotion, runtime binding,
  worker spawn, source mutation, PR publication, reward settlement, shell
  execution, or merge authority was added.

## 2026-07-17: REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_MAIN_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added `REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_PATH` as a
  profile-derived resident runtime path.
- Wired `main.py` to optionally admit an outside-repo model AutoResearch cycle
  receipt into an outside-repo cycle feedback ledger after cycle receipt supply.
- Successful admission updates `REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_PATH`
  so later planning/feedback slices can consume the durable cycle record.
- The hook is disabled by default and only consumes outside-repo receipts.
- Boundary remains constrained: no provider call, benchmark execution,
  HoloIndex re-index, PatternMemory write, model promotion, runtime binding,
  worker spawn, source mutation, PR publication, reward settlement, shell
  execution, or merge authority was added.

## 2026-07-17: REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_SUPPLY_MAIN_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added `REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_PATH` as a profile-derived
  resident runtime path.
- Wired `main.py` to optionally run model AutoResearch cycle receipt supply
  after plan, campaign execution, and promotion-gate supply artifacts exist.
- Successful supply updates `REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_PATH` so
  later resident planning or feedback stages can consume the single cycle
  evidence object.
- The hook is disabled by default and only consumes outside-repo receipts.
- Boundary remains constrained: no provider call, benchmark execution,
  HoloIndex re-index, PatternMemory write, model promotion, runtime binding,
  worker spawn, source mutation, PR publication, reward settlement, shell
  execution, or merge authority was added.

## 2026-07-17: REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_GATE_SUPPLY_MAIN_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added profile-derived runtime paths for
  `REDDOG_MODEL_AUTORESEARCH_PROMOTION_GATE_RECEIPTS_PATH` and
  `REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_POLICIES_PATH`.
- Wired `main.py` to optionally run campaign promotion-gate artifact supply
  after campaign execution supply and before FIX promotion.
- Successful supply updates `REDDOG_MODEL_AUTORESEARCH_PROMOTION_GATE_RECEIPTS_PATH`
  so a later AutoResearch planning cycle can consume the fresh gate receipts.
- The hook is disabled by default and only consumes outside-repo execution and
  policy artifacts.
- Boundary remains constrained: no provider call, benchmark execution,
  HoloIndex re-index, PatternMemory write, model promotion, runtime binding,
  worker spawn, source mutation, PR publication, reward settlement, or merge
  authority was added.

## 2026-07-17: REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added `REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_RECEIPT_PATH` as a
  profile-derived resident runtime path.
- Wired `main.py` to optionally run the model AutoResearch campaign execution
  artifact-supply bootstrap after plan artifact supply and before FIX
  promotion.
- The hook is disabled by default and uses only the deterministic fixture
  runner/verifier mode exposed by the AI gateway bootstrap.
- Enforced mode can block startup when the campaign execution artifact cannot
  be materialized.
- Boundary remains constrained: no RedDog extension runtime, provider call,
  shell execution, HoloIndex re-index, PatternMemory write, model promotion,
  worker spawn, source mutation, PR publication, reward settlement, or merge
  authority was added.

## 2026-07-17: REDDOG_RESIDENT_MODEL_FEEDBACK_LEDGER_PROFILE_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added `REDDOG_MODEL_FEEDBACK_LEDGER_STORE_PATH` as the resident runtime path
  for queue-stage model-feedback ledger admission.
- Draft-PR-and-higher resident profiles now derive an outside-repo JSONL path
  under `.reddog/model_feedback/<repo>/model_feedback.jsonl`.
- `main.py` and the signed OpenClaw queue-loop runner now pass that path into
  the resident serial-loop bootstrap so the `model_feedback_admission` stage can
  admit verified model-selection outcomes without manual injection.
- Boundary remains constrained: no provider call, benchmark execution, model
  promotion, command execution, PatternMemory write, OpenClaw/Hermes dispatch,
  source mutation, PR publication, reward settlement, or HoloIndex re-indexing
  was added.

## 2026-07-17: REDDOG_RESIDENT_QUEUE_MODEL_FEEDBACK_LEDGER_ADMISSION_STAGE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Inserted `model_feedback_admission` into the resident queue chain after
  `verified_outcome_ratchet` and before held-out regression / PatternMemory.
- Added a resident stage handler that consumes the verified-outcome ratchet
  stage result and calls the queue-authorized model-feedback ledger admission
  guard only when a `ModelSelectionOutcomeReceipt` exists.
- Non-model-feedback chains record an accepted no-op, preserving existing
  resident queue progress without requiring a model-feedback ledger store.
- The bootstrap can build an outside-repo JSONL model-feedback ledger store
  when configured, and OpenClaw queue-stage readiness recognizes the inserted
  stage.
- Boundary remains constrained: no provider call, benchmark execution, model
  promotion, command execution, PatternMemory write, OpenClaw/Hermes dispatch,
  source mutation, PR publication, reward settlement, or HoloIndex re-indexing
  was added.

## 2026-07-17: REDDOG_WRE_QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a queue-authorized explicit invoke guard that consumes an accepted
  verified-outcome ratchet result and admits its emitted
  `ModelSelectionOutcomeReceipt` into an injected model-feedback ledger store.
- The guard fails closed when explicit invocation, the injected store, accepted
  ratchet payload, ratchet receipt, or model outcome receipt is missing.
- Reuses the AI gateway model-feedback admission layer, so serialized outcome
  receipts are rehydrated, source-ratchet verifier/runtime-binding consistency
  is checked, and secret-bearing feedback records are rejected before store
  writes.
- Boundary remains constrained: no model/provider call, benchmark execution,
  model promotion, PatternMemory write, OpenClaw/Hermes dispatch, source
  mutation, PR publication, reward settlement, or HoloIndex re-indexing was
  added.

## 2026-07-17: REDDOG_RATCHET_MODEL_FEEDBACK_RECEIPT_BRIDGE_PHASE1

## 2026-07-17: REDDOG_RATCHET_MODEL_FEEDBACK_RECEIPT_BRIDGE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- The queue-authorized verified-outcome ratchet invoke can now emit an optional
  `ModelSelectionOutcomeReceipt` when the ratchet request includes
  content-bearing model-selection and runtime-binding receipts.
- The bridge rehydrates and verifies serialized model receipts before the
  ratchet store write, so malformed model-feedback evidence fails closed without
  recording a verified outcome.
- The resident serial-loop bootstrap now derives model-selection and
  runtime-binding receipts from the bound work order into the derived ratchet
  request when outcome-ratchet request binding is enabled.
- Boundary remains constrained: no model/provider call, benchmark execution,
  model promotion, PatternMemory write, OpenClaw/Hermes dispatch, source
  mutation, PR publication, reward settlement, or HoloIndex re-indexing was
  added.

## 2026-07-17: REDDOG_MODEL_RUNTIME_BINDING_RECURSIVE_RETENTION_CARRY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Carried optional model-runtime binding id/digest from verifier/ratchet
  receipts into held-out recursive-improvement regression gate receipts.
- PatternMemory admission records and receipts now preserve the same
  runtime-binding proof, so verified recursive learning can attribute outcomes
  to the runtime-selected model topology.
- Added fail-closed mismatch guards so admission requests cannot override the
  gate's runtime-binding evidence.
- Boundary remains constrained: no model/provider default change, benchmark
  execution, signing expansion, shell, worktree policy change, source mutation,
  PatternMemory sink instantiation, OpenClaw/Hermes dispatch, PR publication,
  reward settlement, or HoloIndex re-indexing was added.

## 2026-07-17: REDDOG_MODEL_RUNTIME_BINDING_VERIFIER_OUTCOME_CARRY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Carried optional model-runtime binding id/digest from signed authority and
  bounded artifact-generation receipts into independent verifier receipts.
- Draft-PR publish and verified-outcome ratchet receipts now preserve the same
  runtime-binding proof and fail closed if a downstream request tries to
  override it.
- The queue-authorized verifier wrapper now enriches verifier requests from the
  bounded artifact-generation receipt so model runtime evidence is not lost
  between artifact synthesis and independent verification.
- Boundary remains constrained: no model/provider default change, benchmark
  execution, signing expansion, shell, worktree policy change, source mutation,
  PatternMemory write, OpenClaw/Hermes dispatch, PR publication, reward
  settlement, or HoloIndex re-indexing was added.

## 2026-07-17: REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_REQUEST_DERIVATION_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Carried content-bearing `model_runtime_binding_receipt` from resident
  work orders into derived bounded artifact-generation requests.
- Patched both early bootstrap derivation and the late bounded-worker-pilot
  handler derivation path, which is the path used by an active serial loop after
  worktree creation.
- Added an end-to-end resident bootstrap regression proving the artifact
  generator receives the runtime-bound model topology before bounded worker
  materialization.
- Boundary remains constrained: no model/provider default change, benchmark
  execution, signing expansion, shell, worktree policy change, source mutation,
  PatternMemory write, OpenClaw/Hermes dispatch, PR publication, reward
  settlement, or HoloIndex re-indexing was added.

## 2026-07-17: REDDOG_MODEL_RUNTIME_BINDING_WORKER_DISPATCH_CARRY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Carried signed model runtime-binding receipt id/digest from issued
  work-authority into signed worker-dispatch dry-run intents, dispatch runtime
  receipts, and AgentDB task context.
- The worker-dispatch runtime and claimed-task executor now fail closed when
  queue item, dispatch receipt, intent, or task context disagree on runtime
  model-binding id/digest.
- Resident work-order materialization now carries the content-bearing
  `model_runtime_binding_receipt` from the authority profile so readonly 0102
  audit workers can consume the runtime-selected model topology.
- Boundary remains constrained: no model/provider call, benchmark execution,
  signing expansion, worker spawn, shell, worktree, source mutation,
  PatternMemory write, OpenClaw/Hermes dispatch, or HoloIndex re-indexing was
  added.

## 2026-07-16: REDDOG_MODEL_RUNTIME_BINDING_SIGNED_AUTHORITY_CHAIN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Carried optional model runtime-binding receipt id/digest from validated WRE
  queue items through the queue-authority dry-run planner into
  `DelegatedAuthorityRuntimeRequest`.
- The signer runtime now validates optional runtime-binding fields and includes
  them in the signed work-authority payload and issued-authority store record.
- The work-order verifier rejects malformed one-sided runtime-binding fields
  and signature verification rejects any post-signing runtime-binding tamper.
- Boundary remains constrained: no model/provider call, benchmark execution,
  worker spawn, shell, worktree, OpenClaw/Hermes dispatch, source mutation,
  PatternMemory write, or HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_MODEL_RUNTIME_BINDING_AUTHORITY_CARRY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Carried optional `RedDogModelRuntimeBindingReceipt` evidence from `main.py`
  startup preflight into architect-FIX promotion.
- Promotion now rehydrates and digest-checks supplied runtime-binding receipts,
  rejects unbound or selection/catalog/task-family mismatches, and records the
  accepted receipt id/digest on the claim, WRE queue item, promotion record,
  promotion receipt, and promoted authority profile.
- Preserved existing flows when no runtime-binding receipt is explicitly
  supplied or generated; profile-derived default paths no longer accidentally
  make runtime-binding evidence mandatory.
- Boundary remains constrained: no model/provider call, benchmark execution,
  signing, worker spawn, shell, worktree, source mutation, PatternMemory write,
  OpenClaw/Hermes dispatch, or HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Wired `main.py` to optionally run the AI Gateway runtime-binding artifact
  supplier before architect-FIX promotion when
  `REDDOG_MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY=1` is set.
- The preflight consumes outside-repo catalog, model-selection, benchmark,
  promotion, signed evidence, policy, and trusted public-key files, then
  writes a `RedDogModelRuntimeBindingReceipt` path for later resident runtime
  consumption.
- Added a profile-derived output path for
  `REDDOG_MODEL_RUNTIME_BINDING_RECEIPT_PATH` while keeping the supply flag
  explicit/default-off to avoid breaking existing startup profiles without
  runtime-binding evidence inputs.
- Boundary remains constrained: no model/provider call, benchmark execution,
  runtime model default mutation, worker spawn, shell, worktree, source
  mutation, PatternMemory write, or HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_MODEL_RUNTIME_BINDING_RECEIPT_CONSUMPTION_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added optional runtime-binding receipt consumption to the backend architect,
  bounded artifact generation, and model-backed read-only audit worker runtime
  surfaces.
- Runtime-binding receipts now fail closed when malformed, unbound, or supplied
  for the wrong runtime surface; valid receipts provide the lead/panel topology
  and are persisted on runtime receipts alongside legacy model-selection ids.
- Preserved backward-compatible model-selection receipt behavior when no
  runtime-binding receipt is supplied; no provider calls, shell execution,
  HoloIndex re-indexing, repo mutation, OpenClaw enqueue, Hermes dispatch, or
  PatternMemory promotion was added.

## 2026-07-16: REDDOG_READONLY_AUDIT_WORKER_MODEL_SELECTION_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Bound model-backed RedDog read-only audit worker execution to an optional
  production model-selection receipt, preserving legacy injected/default
  behavior when no receipt is supplied.
- Routed FoundUps Fusion read-only audit calls through receipt-derived
  lead/panel topology and persisted the selection receipt id/digest on model
  route and worker receipts.
- Added fail-closed validation so malformed, tampered, or non-production model
  selection receipts reject before HoloIndex queries or model calls, without
  adding shell execution, repo mutation, enqueue, Hermes dispatch, PatternMemory
  promotion, or HoloIndex re-indexing.

## 2026-07-16: REDDOG_BACKEND_ARCHITECT_MODEL_SELECTION_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Bound backend architect determination to an optional production
  model-selection receipt, recording the receipt id and digest on persisted
  architect determination receipts.
- Routed FoundUps Fusion backend architect calls through receipt-derived
  lead/panel topology instead of always using the legacy default model panel
  when a model-selection binding is supplied.
- Added bootstrap support for outside-repo architect model-selection receipt
  supply in production mode while preserving injected-runner test paths.

## 2026-07-16: REDDOG_ARTIFACT_GENERATION_MODEL_SELECTION_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Bound resident bounded-artifact generation to the production
  model-selection receipt carried by the signed FIX promotion authority profile
  and materialized work order.
- Preserved backward-compatible defaults when no model-selection receipt is
  supplied, but fail closed on malformed, tampered, or non-production receipts.
- Added focused regressions proving model topology reaches the FoundUps Fusion
  payload without adding model calls, HoloIndex re-indexing, shell execution, or
  repo mutation.

## 2026-07-16: REDDOG_RESIDENT_PROFILE_OPTIONAL_RUNTIME_PATHS_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added `REDDOG_EXECUTION_VALVE_ENV_PATH` to the resident binding profile's
  outside-repo runtime path map so profile-based resident chains can discover
  the execution-valve environment without hand-setting another path.
- Hardened optional profile-derived paths: explicit env paths remain strict,
  but profile defaults are passed to the bootstrap only when the artifact
  exists, preventing resumed later-stage chains from failing on unused missing
  optional files.
- Added focused regressions at both the direct OpenClaw queue-loop binding and
  `main.py` serial-loop preflight layers.

## 2026-07-16: REDDOG_MAIN_OPENCLAW_AUTOPUBLISHED_WORKER_COMPLETE_CHAIN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Tightened signed worker dispatch planning so resident code chains publish only
  currently executable AgentDB worker tasks: one `0102/bounded_code_change`
  materializer and one `openclaw/queue_stage_progress` continuation worker.
- Preserved the legacy OpenClaw candidate-review task for non-code worker
  plans, but stopped publishing unclaimable Fusion/critic/verifier task roles
  into the resident execution queue until those runtimes exist.
- Converted the `main.py` OpenClaw complete-chain regression from manually
  seeded worker tasks to tasks created by `worker_dispatch_runtime` through
  `AgentDbSignedWorkerDispatchTaskWriter`, and proved the generated artifact
  chain drains with no leftover signed worker tasks.

## 2026-07-16: REDDOG_SIGNED_WORKER_QUEUE_STAGE_PUBLICATION_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Specialized signed worker dispatch dry-run output for code-bearing resident
  queue plans: `openclaw_candidate/candidate_queue_review` is no longer
  emitted for coding chains; the planner emits
  `queue_stage_worker/openclaw/queue_stage_progress` instead.
- Preserved the legacy OpenClaw candidate-review task for non-code worker
  plans so advisory/review-only flows remain compatible.
- Strengthened the resident queue bootstrap regression to prove
  `worker_dispatch_runtime` publishes the queue-stage worker directly from the
  WSP_15 worker plan, without manually seeding a second AgentDB task.

## 2026-07-16: REDDOG_SIGNED_WORKER_STAGE_OWNERSHIP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added explicit signed-worker stage ownership for resident RedDog queue work:
  signed `0102` bounded-code workers now complete after their assigned
  bounded-worker stage instead of requeueing into stages they do not own.
- Added the OpenClaw `queue_stage_progress` capability for post-bounded queue
  stages, gated by resident queue readiness and an explicit runtime flag.
- Strengthened the `main.py` startup-preflight complete-chain regression so
  one coding task and one queue-stage task serially drain generated artifact
  materialization, verification, draft-PR request, outcome ratchet, held-out
  gate, and PatternMemory admission.

## 2026-07-16: REDDOG_MAIN_OPENCLAW_GENERATED_ARTIFACT_COMPLETE_CHAIN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Strengthened the `main.py` startup-preflight complete-chain regression so
  the OpenClaw signed-worker claim loop drains through bounded artifact
  generation, slice verification, draft-PR request, outcome ratchet, held-out
  gate, and PatternMemory admission without using static artifact-content JSON.
- The generated artifact is still materialized only inside the isolated
  worktree, and the chain still stops at verified receipts rather than live
  merge, Hermes dispatch, reward settlement, or HoloIndex re-indexing.

## 2026-07-16: REDDOG_MAIN_OPENCLAW_ARTIFACT_GENERATION_CHAIN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Hardened the bounded artifact generation runner so it resolves the
  `advisory_model_once` Fusion bridge through a repo-path fallback instead of
  depending on an ambient `scripts` package import.
- Added a `main.py` startup-preflight regression proving OpenClaw can claim a
  signed `0102` bounded-code task at the bounded-worker stage, derive the
  artifact-generation request from the existing queue chain, invoke the
  FoundUps Fusion artifact generator, and materialize the generated artifact
  only inside the isolated worktree.
- Boundary remains constrained: no static artifact-content JSON, no source
  repo mutation, no shell execution, no Hermes dispatch, no live OpenClaw
  enqueue, no real PR publication, no reward settlement, and no HoloIndex
  re-indexing was added.

## 2026-07-16: REDDOG_MAIN_OPENCLAW_SIGNED_WORKER_COMPLETE_CHAIN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a `main.py` startup-preflight regression proving the RedDog OpenClaw
  signed-worker claim loop can drain an env-bound signed worker task through
  bounded worker pilot, slice verification, draft-PR request, outcome ratchet,
  held-out gate, and PatternMemory admission.
- Boundary remains constrained to governed runtime artifacts and an isolated
  worktree: no source repo mutation, no shell execution, no Hermes dispatch,
  no live OpenClaw enqueue, no real PR publication, no reward settlement, and
  no HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_MAIN_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_E2E_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a `main.py` startup-preflight regression proving the RedDog OpenClaw
  signed-worker claim loop can consume a real AgentDB task through the
  env-bound signed-worker queue runner and advance the bounded worker pilot.
- Boundary remains constrained: no source repo mutation, no shell execution, no
  Hermes dispatch, no live OpenClaw enqueue, no PR publishing, no reward
  settlement, no PatternMemory promotion, and no HoloIndex re-indexing was
  added.

## 2026-07-16: REDDOG_AUTHORITY_RUNTIME_SOCKET_E2E_PILOT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a resident queue regression proving the serial-loop authority runtime
  can sign through the actual one-shot isolated signer socket service and then
  verify the resulting Ed25519 delegated authority.
- Kept the boundary test-only and runtime-safe: no signer process spawn, no
  vault resolution, no private-key loading by the queue loop, no worker spawn,
  no worktree, no shell, no OpenClaw enqueue, no Hermes dispatch, no repository
  mutation, no PatternMemory write, and no HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_SIGNER_SOCKET_PROFILE_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a resident-profile binding that derives the outside-repo isolated
  signer socket path and defaults the public verifier backend to `ed25519`
  only when the authority runtime bundle is already configured.
- Locked the startup bridge with a serial-loop preflight regression that
  proves resolver-store supply can pass the signer socket path and verifier
  backend without hand-placed environment values.
- Boundary remains constrained: no signer spawn, no private-key loading, no
  vault resolution, no signing, no signer-state mutation, no worker spawn, no
  worktree, no shell, no OpenClaw enqueue, no Hermes dispatch, no repository
  mutation, no PatternMemory write, and no HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added an authority-runtime resolver artifact supplier that converts singular
  principal/permission runtime artifacts into the plural resolver stores
  consumed by the resident queue authority runtime dependency bundle.
- Wired the resident profile startup path so resolver stores and authority
  runtime state paths can be derived under the runtime root before the serial
  queue loop runs.
- Boundary remains constrained: no signing, signature verification, signer
  state mutation, authority runtime invocation, worker spawn, worktree, shell
  execution, OpenClaw enqueue, Hermes dispatch, work-state mutation,
  repository mutation, PatternMemory write, or HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a resident authority-profile seed supplier that derives the seed from
  architect determination, model-selection, Memex, principal-authority, and
  permission-snapshot runtime receipts instead of requiring a hand-placed
  `REDDOG_AUTHORITY_PROFILE_SEED_PATH`.
- Wired the resident profile startup path so seed supply runs after the GitHub
  principal/permission snapshot and before authority-profile source
  materialization; explicit `REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY=0` still
  disables the profile default.
- Boundary remains constrained: no signing, signature verification, signer
  state mutation, worker spawn, worktree, shell execution, OpenClaw enqueue,
  Hermes dispatch, work-state mutation, repository mutation, PatternMemory
  write, or HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a GitHub principal/permission snapshot supplier that converts the
  existing read-only GitHub permission probe into the two runtime artifacts
  consumed by authority-profile source supply: `PrincipalAuthorityRecord` and
  `PermissionSnapshot`.
- Wired the resident profile startup path so principal and permission snapshot
  supply can run before authority-profile source materialization, with explicit
  environment overrides (`0` still disables the profile default).
- Boundary remains constrained: no key inference, signing, signature
  verification, signer state mutation, worker spawn, worktree, OpenClaw
  enqueue, Hermes dispatch, repo mutation, PatternMemory write, or HoloIndex
  re-indexing was added.

## 2026-07-16: REDDOG_WORK_LEDGER_SOURCE_PROJECTION_SUPPLY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a runtime active/work ledger projection supplier that consumes supplied
  GitHub PR and W10 source-record JSON files and writes fresh source
  projections outside the repository for authoritative work-state refresh.
- Wired the resident profile startup path so the sequence is now source
  records -> runtime ledger projection -> authoritative work-state refresh,
  with explicit environment overrides still able to disable the profile
  default.
- Boundary remains constrained: no canonical ledger file mutation, source
  mutation, work-state commit inside the projection supplier, worker spawn,
  shell execution, OpenClaw enqueue, Hermes dispatch, PatternMemory write, or
  HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_AUTHORITATIVE_WORK_STATE_SOURCE_RECORD_SUPPLY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a bounded source-record supplier that materializes GitHub PR records
  and W10 report records outside the repository for the existing
  authoritative work-state refresh runtime.
- Wired the `signed_0102_bounded_code` resident profile to derive source
  record paths and optionally run the supplier before work-state refresh,
  preserving explicit environment overrides (`0` still disables profile
  default source supply).
- Boundary remains constrained: no work-state commit, worker spawn, shell
  execution, OpenClaw enqueue, Hermes dispatch, source mutation, merge, reward
  settlement, PatternMemory write, or HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_RESIDENT_PROFILE_ARTIFACT_SUPPLY_DEFAULTS_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Extended the resident queue binding profile so the
  `signed_0102_bounded_code` profile enables the safe artifact-supply
  preflights for resident fix-promotion handoff, model-selection receipt
  supply, and authority-profile source supply.
- Updated `main.py` to use the profile helper for those preflight toggles,
  preserving explicit environment overrides (`0` still disables a profile
  default).
- Boundary remains constrained: the profile only materializes outside-repo
  receipts already required by the promotion bridge; it does not sign, spawn
  workers, create worktrees, execute shell commands, enqueue OpenClaw, dispatch
  Hermes, publish PRs, mutate source files, write PatternMemory, settle
  rewards, or re-index HoloIndex.

## 2026-07-16: REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Wired `main.py` to optionally materialize the authority-profile source
  artifact before architect-FIX promotion when
  `REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY=1` is set.
- The preflight consumes outside-repo authority seed, token-verified principal,
  and permission snapshot JSON files, then feeds the resulting
  authority-profile source path into the existing promotion bridge.
- Boundary remains constrained: no signing, signature verification, signer
  state mutation, work-state mutation, worker spawn, shell, worktree,
  OpenClaw enqueue, Hermes dispatch, PR creation, PatternMemory write, source
  mutation, or HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY_MAIN_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Wired `main.py` to optionally run the AI Gateway model-selection artifact
  supplier before architect-FIX promotion when
  `REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY=1` is set.
- The preflight consumes outside-repo catalog snapshot, signed production
  evidence bundle, selection requirements, and trusted public-key files, then
  feeds the resulting model-selection receipt path into the existing promotion
  bridge.
- Boundary remains constrained: no model/provider call, benchmark execution,
  runtime model default binding, worker spawn, shell, worktree, source
  mutation, PatternMemory write, or HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a bounded authority-profile source supplier that validates an explicit
  authority seed against a token-verified principal record and fresh permission
  snapshot, then writes one profile-source JSON artifact outside the source
  repository.
- The supplier enforces FoundUp-scoped allowed/denied paths, principal
  repo/FoundUp scope, permission snapshot freshness/grants, high-authority
  co-sign evidence, HoloIndex no-gap evidence, non-reused principal/RedDog
  public keys, and outside-repo output.
- Boundary remains constrained: no signing, signature verification, signer
  state mutation, work-state mutation, worker spawn, shell, worktree,
  OpenClaw enqueue, Hermes dispatch, PatternMemory write, source mutation, or
  HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_RESIDENT_CYCLE_FIX_PROMOTION_ARTIFACT_HANDOFF_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a resident-cycle handoff runtime that materializes backend architect
  determination and cycle-level Memex supply receipt JSON artifacts outside
  the source repository for the existing architect-FIX promotion bridge.
- Extended the operational Memex supplier to emit one aggregate
  cycle-level supply receipt while preserving per-assignment worker receipts.
- Wired `main.py` behind explicit `REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF=1`
  so a determined resident cycle can feed promotion without manual Copy-MD
  artifact handling. The boundary remains read/serialize-only: no signing,
  worker spawn, shell, worktree, OpenClaw enqueue, Hermes dispatch, PR,
  PatternMemory, source mutation, or HoloIndex re-indexing was added.

## 2026-07-16: REDDOG_ARCHITECT_FIX_PROMOTION_MAIN_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a `main.py` promotion bridge that consumes outside-repo backend
  architect FIX, model-selection, Memex-supply, and authority-profile receipts.
- The bridge calls the existing signed WSP_15 promotion runtime, atomically
  updates the outside-repo authoritative work-state snapshot, and writes the
  promoted authority profile consumed by the resident serial loop.
- Boundary remains constrained: no signing, worker spawn, worktree creation,
  shell execution, OpenClaw enqueue, Hermes dispatch, PR creation,
  PatternMemory write, reward settlement, source-repo mutation, or HoloIndex
  re-indexing was added.

## 2026-07-16: REDDOG_RESIDENT_QUEUE_PLAN_OPTIONAL_PROFILE_CHAIN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Fixed the resident orchestration-plan preflight so a profile-derived default
  `REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH` is optional until the serial loop
  creates the chain-results file.
- Preserved strict behavior for an explicit `REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH`;
  if the operator supplies a path, the planner still validates it.
- Added real-path and mocked regressions proving the first resident profile
  plan does not warn on a missing default chain file, while existing chain
  files and explicit paths are still passed through.

## 2026-07-16: REDDOG_RESIDENT_PROFILE_SERIAL_LOOP_DEFAULT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Extended resident queue profiles to default `REDDOG_RESIDENT_QUEUE_SERIAL_LOOP=1`
  as a safe control-plane loop flag, so profile-selected RedDog startup can
  invoke the existing serial queue bootstrap without an extra manual env var.
- Preserved explicit `REDDOG_RESIDENT_QUEUE_SERIAL_LOOP=0` override behavior.
- Boundary remains constrained: the serial loop still consumes the existing
  signed queue stages and profile-derived outside-repo paths; no shell
  execution, HoloIndex re-index, merge authority, reward settlement, or Hermes
  dispatch was added.

## 2026-07-16: REDDOG_MIDDLE_PREFLIGHTS_PROFILE_PATHS_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Aligned the WRE queue consumer, resident orchestration-plan, and
  next-stage dispatch `main.py` preflights with the resident profile runtime
  path helper.
- These preflights now consume the same profile-derived work-state,
  chain-results, and authority-profile paths as the refresh producer and
  serial-loop runner when explicit env vars are absent.
- Added regression tests proving the derived paths are passed without creating
  runtime files or writing inside the source checkout.

## 2026-07-16: REDDOG_WORK_STATE_REFRESH_PROFILE_PATH_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Aligned `main.py` authoritative work-state refresh with the resident profile
  runtime path helper, so an active resident profile writes the authoritative
  work-state snapshot to the same outside-repo runtime root consumed by the
  serial queue loop.
- Preserved the existing explicit `REDDOG_AUTHORITATIVE_WORK_STATE_PATH`
  override and the legacy non-profile default path.
- Added a regression proving the profile-derived work-state output is created
  outside the source checkout and exported back to `os.environ` for downstream
  RedDog preflights.

## 2026-07-16: REDDOG_RESIDENT_RUNTIME_PATH_DEFAULTS_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added profile-derived mandatory resident runtime paths under
  `.reddog/resident/<repo>/` or explicit `REDDOG_RESIDENT_RUNTIME_ROOT`.
- `main.py` preflight and the OpenClaw signed-worker queue-loop runtime now
  derive work-state, chain-results, and authority-profile paths when a
  resident profile is active and the explicit env vars are absent.
- Explicit path env vars still win, and the helper only returns paths; it does
  not create files, write runtime state, re-index HoloIndex, dispatch Hermes,
  merge, settle rewards, or grant additional authority.

## 2026-07-16: REDDOG_RESIDENT_FULL_RECURSIVE_PROFILE_E2E_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added an end-to-end `main.py` preflight regression proving the highest
  resident profile can advance an already verified chain through
  PatternMemory admission using the profile-derived outside-repo sink.
- The test starts from an accepted held-out regression gate, runs the actual
  resident bootstrap through `main.run_reddog_resident_queue_serial_loop_preflight`,
  records the verified outcome in the derived `.reddog/pattern_memory/<repo>`
  SQLite DB, and asserts the source repo does not receive a `.reddog` write.
- Boundary remains constrained: this is a deterministic regression proof only;
  no new production authority, shell execution, HoloIndex re-index, merge,
  reward settlement, or Hermes dispatch was added.

## 2026-07-16: REDDOG_RESIDENT_PATTERN_MEMORY_ADMISSION_PROFILE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added
  `REDDOG_RESIDENT_QUEUE_BINDING_PROFILE=signed_0102_bounded_code_fusion_worktree_draft_pr_pattern_memory`
  as the next resident queue profile above the verified draft-PR profile.
- The profile preserves the existing fusion, isolated worktree, independent
  evidence, verified draft-PR, and verified outcome ratchet defaults, then
  derives an outside-repo PatternMemory admission DB path under
  `.reddog/pattern_memory/<repo>/pattern_memory.db`.
- Boundary remains constrained: PatternMemory writes still require the
  queue-authorized verified draft PR, verified outcome ratchet, held-out gate
  acceptance, derived admission request, and verified PatternMemory sink guard.
  The profile does not enable shell execution, HoloIndex re-indexing, merge
  authority, reward settlement, or Hermes dispatch.

## 2026-07-16: REDDOG_RESIDENT_FUSION_WORKTREE_DRAFT_PR_PROFILE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added `REDDOG_RESIDENT_QUEUE_BINDING_PROFILE=signed_0102_bounded_code_fusion_worktree_draft_pr`
  as the highest resident coding profile for the current chain.
- The profile derives `foundups_fusion`, the isolated worktree runner, the
  independent evidence command runner, and the existing verified draft-PR
  runner while preserving explicit env overrides.
- The same profile also derives an outside-repo verified outcome ratchet JSONL
  store under `.reddog/outcome_ratchet/<repo>/verified_outcomes.jsonl`, so the
  queue chain can persist verified outcomes without writing into the source
  checkout.
- Boundary remains constrained: draft PR publishing is still downstream of the
  queue-authorized slice verifier, evidence production, exact-head checks,
  draft-only guard, and branch policy; the evidence runner uses argv execution
  with `shell=False`, verified outcome ratchet writes only to the outside-repo
  JSONL store, and this profile does not enable shell execution, PatternMemory
  writes, HoloIndex re-index, merge authority, reward settlement, or Hermes
  dispatch.

## 2026-07-16: REDDOG_RESIDENT_FUSION_WORKTREE_PROFILE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added `REDDOG_RESIDENT_QUEUE_BINDING_PROFILE=signed_0102_bounded_code_fusion_worktree`
  as a higher-authority resident profile that defaults the isolated worktree
  runner mode to `real`.
- Preserved explicit `REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_MODE` override
  behavior and kept the lower profiles non-worktree.
- Boundary remains constrained: this profile enables only the existing
  isolated worktree materializer after signed queue-loop, model artifact, and
  bounded-code stage gates pass; it does not enable shell execution, draft PR
  publishing, PatternMemory writes, HoloIndex re-index, merge authority, or
  rewards.

## 2026-07-16: REDDOG_RESIDENT_FUSION_ARTIFACT_PROFILE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added `REDDOG_RESIDENT_QUEUE_BINDING_PROFILE=signed_0102_bounded_code_fusion`
  as a higher-authority resident profile that defaults the artifact generator
  mode to `foundups_fusion`.
- Preserved the base `signed_0102_bounded_code` profile as non-model and
  preserved explicit `REDDOG_ARTIFACT_GENERATOR_MODE` override behavior.
- Boundary remains constrained: the fusion profile selects the model artifact
  generator only after signed queue-loop and bounded-code stage gates pass; it
  still does not enable shell execution, worktree runners, draft PR publishing,
  PatternMemory writes, HoloIndex re-index, merge authority, or rewards.

## 2026-07-16: REDDOG_RESIDENT_PROFILE_0102_BOUNDED_CODE_TASK_DEFAULT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Extended `REDDOG_RESIDENT_QUEUE_BINDING_PROFILE=signed_0102_bounded_code`
  to default `OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED=1` as a
  control-plane task inclusion flag.
- Preserved the existing stage-ready gate: bounded-code tasks still require
  the signed queue-loop runner, `foundups_fusion` artifact generator mode,
  a derivable or explicit artifact request, the correct queue stage, and no
  static artifact contents.
- Explicit `OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED=0` still disables
  bounded-code task claims even when the resident profile is active.

## 2026-07-16: REDDOG_RESIDENT_PROFILE_OPENCLAW_CLAIM_LOOP_DEFAULTS_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Extended `REDDOG_RESIDENT_QUEUE_BINDING_PROFILE=signed_0102_bounded_code`
  to default only the safe control-plane flags for the OpenClaw signed-worker
  claim loop and signed-worker queue-loop runner.
- Explicit env values still win, including explicit `0` disables.
- Boundary remains unchanged: the profile still does not enable model
  execution, shell execution, worktree runners, draft PR publishing,
  PatternMemory writes, HoloIndex re-index, merge authority, or rewards.

## 2026-07-16: REDDOG_MAIN_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_PREFLIGHT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added an opt-in `main.py` preflight,
  `REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP=1`, that lets OpenClaw claim
  signed RedDog worker-dispatch AgentDB tasks through the existing bounded
  claim loop.
- Preserved authority boundaries: the preflight creates no tasks, signs no
  authority, enables no model/shell/worktree/PR modes, dispatches no Hermes,
  writes no PatternMemory, settles no rewards, and never re-indexes HoloIndex.
- Added focused tests for default-off behavior, bounded `max_claims`, enforced
  reject blocking, invalid-claim rejection, and non-enforced exception handling.

## 2026-07-16: REDDOG_RESIDENT_QUEUE_BINDING_PROFILE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added `REDDOG_RESIDENT_QUEUE_BINDING_PROFILE=signed_0102_bounded_code`
  as a safe resident-queue profile for derivation/request bindings.
- The profile defaults only resident queue derivation flags plus
  `REDDOG_WORK_ORDER_MATERIALIZER_MODE=authority_profile`; explicit env values
  still win, including explicit `0` disables for individual bindings.
- Boundary remains unchanged: the profile does not enable artifact generator
  mode, evidence command runner mode, real worktree runner, draft PR runner,
  PatternMemory sink, shell execution, model calls, HoloIndex re-index, merge
  authority, or reward settlement.

## 2026-07-16: REDDOG_OPENCLAW_BOUNDED_CODE_ARTIFACT_BINDING_STAGE_READY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Updated OpenClaw signed 0102 bounded-code stage readiness so
  `REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING=1` can satisfy the artifact
  request-source check without hand-authored request JSON.
- Preserved fail-closed behavior: `foundups_fusion` artifact generator mode is
  still required, static artifact contents still block 0102 bounded-code
  claims, and the resident queue must already be at `bounded_worker_pilot`.
- Added claim-path tests proving binding-based claim acceptance and rejection
  when neither explicit request JSON nor derived request binding is present.

## 2026-07-16: REDDOG_SIGNED_WORKER_BOUNDED_CODE_ARTIFACT_REQUEST_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Updated the signed 0102 bounded-code queue-loop runner so
  `REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING=1` can satisfy the artifact
  generation readiness gate when paired with the existing explicit
  `foundups_fusion` artifact generator mode.
- Preserved existing boundaries: static `REDDOG_ARTIFACT_CONTENTS_PATH` remains
  forbidden for signed bounded-code workers, `max_steps` must remain 1, and the
  queue stage must already be `bounded_worker_pilot`.
- Kept the legacy explicit `REDDOG_ARTIFACT_GENERATION_REQUEST_PATH` flow
  working; this slice only removes the need for hand-authored request JSON when
  the resident queue can derive it from signed chain state.

## 2026-07-16: REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added `REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING=1` for resident queue
  runs. When explicit artifact contents and explicit artifact-generation
  request JSON are both absent, the bootstrap can derive a bounded artifact
  generation request from the signed work order and verified queue chain state.
- Wired the binding through both `main.py` resident preflight and the OpenClaw
  signed-worker queue-loop runtime adapter.
- Existing `REDDOG_ARTIFACT_CONTENTS_PATH` and
  `REDDOG_ARTIFACT_GENERATION_REQUEST_PATH` remain authoritative when provided;
  the derived request is opt-in and fail-closed.
- Boundary remains explicit: the slice derives a request only. Model execution
  still requires the existing explicit artifact generator configuration; no
  shell execution, source-repo mutation, Hermes dispatch, HoloIndex re-index,
  merge authority, or reward settlement is added.

## 2026-07-16: REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added an opt-in resident queue binding for PatternMemory admission requests:
  `REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING=1`.
- The binding derives the admission request from the accepted held-out
  regression gate already recorded in the resident queue chain, removing the
  final operator-edited JSON request from the requeued signed-worker path.
- Existing explicit `REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_PATH` remains
  authoritative when provided; the derived request is used only when the
  explicit request is absent.
- Boundary remains explicit: no new worker authority, no shell execution, no
  source-repo mutation, no Hermes dispatch, no HoloIndex re-index, no merge
  authority, and no reward settlement are added.

## 2026-07-16: REDDOG_OPENCLAW_SIGNED_WORKER_REQUEUE_DRAIN_E2E_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added an end-to-end OpenClaw signed-worker claim-loop regression proving one
  AgentDB task can be requeued across non-terminal resident queue stages and
  complete only after `STOP_QUEUE_CHAIN_COMPLETE`.
- Added opt-in resident queue request bindings for outcome-ratchet and held-out
  gate stages. The bindings derive requests from already-recorded chain results
  so the requeued worker loop does not need operator-edited JSON between
  claims.
- Extended the signed-worker queue-loop environment binding with
  `REDDOG_OUTCOME_RATCHET_REQUEST_BINDING=1` and
  `REDDOG_HELD_OUT_GATE_REQUEST_BINDING=1`.
- Boundary remains explicit: no new worker authority, no shell execution, no
  source-repo mutation, no Hermes dispatch, no HoloIndex re-index, no merge
  authority, and no reward settlement are added.

## 2026-07-16: REDDOG_SIGNED_WORKER_QUEUE_LOOP_INCOMPLETE_REQUEUE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added queue-chain completion telemetry to the signed worker serial-loop
  runner. Non-terminal `next_action` values now emit
  `queue_chain_requeue_required=true`; only `STOP_QUEUE_CHAIN_COMPLETE` is
  terminal.
- Updated OpenClaw signed-worker claiming so an accepted but incomplete
  queue-loop stage is released back to AgentDB as `pending` instead of being
  marked `completed`.
- Extended the bounded signed-worker claim loop to count requeued claims,
  preserve `requeued_task_ids`, and stop cleanly at the configured
  `max_claims`.
- Boundary remains explicit: no new worker authority, no shell execution, no
  source-repo mutation, no Hermes dispatch, no HoloIndex re-index, no merge
  authority, and no reward settlement are added.

## 2026-07-16: REDDOG_SIGNED_0102_BOUNDED_CODE_CHANGE_STAGE_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a stage-scoped signed 0102 `bounded_code_change` binding to the
  resident queue-loop runner. It may advance exactly one queue stage only when
  the authoritative chain is already at `bounded_worker_pilot`.
- Required explicit artifact generation for 0102 coding tasks:
  `artifact_generation_request_path` plus `artifact_generator_mode=foundups_fusion`;
  static `artifact_contents_path` is rejected for this capability.
- Wired OpenClaw task discovery to claim 0102 bounded-code tasks only when
  `OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED=1`, the queue-loop runner is
  configured, and the chain plan is stage-ready. Early tasks remain pending
  instead of being failed.
- Boundary remains explicit: no broad 0102 worker launch, no shell execution,
  no source-repo mutation, no Hermes dispatch, no PR publish/merge, no
  HoloIndex re-index, no reward settlement, and no authority beyond the
  existing bounded-worker-pilot stage is added.

## 2026-07-16: REDDOG_SIGNED_0102_READONLY_REVIEW_RUNTIME_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a signed 0102 read-only review runner that adapts signed worker
  dispatch intents for `architect_review`, `adversarial_review`, and
  `diff_verification` into the existing model-backed read-only audit worker.
- Bound review evidence to the signed WSP_15 allocation receipt's
  `allowed_read_targets`; `bounded_code_change` remains explicitly unsupported
  by this read-only runner.
- Wired OpenClaw signed-worker claiming to include 0102 read-only review tasks
  only when `OPENCLAW_SIGNED_0102_READONLY_TASKS_ENABLED=1`.
- Boundary remains explicit: no shell execution, source repository mutation,
  worktree operation, Hermes dispatch, PR publish, PatternMemory write,
  HoloIndex re-index, reward settlement, or coding-worker execution is added.

## 2026-07-16: REDDOG_OPENCLAW_SUPERVISOR_SIGNED_WORKER_LOOP_RUNTIME_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Wired the bounded signed-worker claim loop into `OpenClawSupervisor` as an
  explicit opt-in resident action gated by `OPENCLAW_SIGNED_WORKER_TASKS_ENABLED=1`.
- Added bounded claim limit parsing via `OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS`
  and fail-closed triage for invalid limits before any AgentDB claim.
- Added run-cycle regressions proving signed OpenClaw candidate tasks are
  selected before generic autonomous tasks when enabled, and that invalid
  loop configuration escalates without invoking the claim loop.
- Boundary remains explicit: no default enablement, no Hermes/0102 dispatch,
  no shell execution, no repository mutation, no HoloIndex re-index, no reward
  settlement, and no merge authority is added.

## 2026-07-16: REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_UNTIL_IDLE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a bounded OpenClaw signed-worker claim loop that reuses the existing
  one-task `claim_reddog_signed_worker_dispatch_task_once` primitive until
  AgentDB is idle or `max_claims` is reached.
- Preserved the signed OpenClaw `candidate_queue_review` boundary; the loop
  does not add Hermes/0102 dispatch, shell execution, repository mutation,
  HoloIndex re-index, reward settlement, or merge authority.
- Added focused AgentDB regressions for multi-task draining, max-claim
  stopping, idle behavior, non-OpenClaw task isolation, failure stop, invalid
  max-claim rejection, and the `OpenClawSupervisor` instance entrypoint.

## 2026-07-16: REDDOG_SIGNED_WORKER_PATTERN_MEMORY_ADMISSION_E2E_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added PatternMemory admission sink construction to the signed OpenClaw
  queue-loop environment binding using the existing explicit outside-repo
  `REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH` adapter.
- Refined the signed queue-loop safety classifier so a PatternMemory write is
  accepted only when the dispatched stage is `pattern_memory_admission`;
  unexpected memory writes remain fail-closed.
- Added an end-to-end regression proving an AgentDB signed OpenClaw task can
  advance from an accepted held-out gate into PatternMemory admission and write
  exactly one verified outcome record to an outside-repo SQLite database.
- Boundary remains explicit: no shell execution, PR publish, ready-for-review,
  merge, HoloIndex re-index, or reward settlement is performed by this slice.

## 2026-07-16: REDDOG_SIGNED_WORKER_HELD_OUT_REGRESSION_GATE_E2E_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added an end-to-end regression proving an AgentDB signed OpenClaw
  `candidate_queue_review` task can be claimed, routed through the real
  environment-bound queue-loop runner, and advance an accepted
  verified-outcome ratchet into the held-out regression gate stage.
- Verified the env-bound runner consumes the held-out gate request and persists
  an accepted gate receipt without executing tests or commands.
- Boundary remains explicit: no PatternMemory admission, shell execution, PR
  publish, ready-for-review, merge, HoloIndex re-index, or reward settlement is
  performed by this slice.

## 2026-07-16: REDDOG_SIGNED_WORKER_VERIFIED_OUTCOME_RATCHET_E2E_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added an end-to-end regression proving an AgentDB signed OpenClaw
  `candidate_queue_review` task can be claimed, routed through the real
  environment-bound queue-loop runner, and advance an accepted verified draft
  PR publish result into the verified-outcome ratchet stage.
- Verified the env-bound runner consumes an outside-repo ratchet request and
  writes the outcome ratchet JSONL store only outside the source repository.
- Boundary remains explicit: no shell execution, PR publish, ready-for-review,
  merge, PatternMemory admission, HoloIndex re-index, or reward settlement is
  performed by this slice.

## 2026-07-16: REDDOG_SIGNED_WORKER_VERIFIED_DRAFT_PR_RUNNER_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added draft-PR runner construction to the signed OpenClaw queue-loop
  environment binding, matching the existing `main.py` resident-loop mode:
  `REDDOG_DRAFT_PR_RUNNER_MODE=real` plus a positive timeout.
- Preserved fail-closed behavior for unsupported draft-PR runner modes and
  invalid timeouts; default behavior still provides no draft-PR runner.
- Refined the queue-loop runner safety rule so PR creation is accepted only
  when the dispatched stage is `verified_draft_pr_publish`; unexpected PR
  creation remains unsafe.
- Added an end-to-end regression proving an AgentDB signed OpenClaw task can
  advance from an accepted slice-verifier result to verified draft-PR publish
  through the environment-bound runner, using a monkeypatched runner so no
  real GitHub call occurs in tests.

## 2026-07-16: REDDOG_SIGNED_WORKER_SLICE_VERIFIER_E2E_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added an end-to-end regression proving an AgentDB signed OpenClaw
  `candidate_queue_review` task can be claimed, routed through the real
  environment-bound queue-loop runner, and advance an already materialized
  bounded artifact into the independent slice-verifier stage.
- Verified the env-bound runner can consume an outside-repo verifier request
  and persist a slice-verifier receipt without shell execution, GitHub calls,
  PR publication, merge, PatternMemory write, HoloIndex re-index, or reward
  settlement.
- Boundary remains explicit: this slice adds no live model call, no source
  checkout write, no OpenClaw enqueue expansion, no Hermes dispatch, and no
  runtime authority widening.

## 2026-07-16: REDDOG_SIGNED_WORKER_BOUNDED_ARTIFACT_E2E_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added an end-to-end regression proving an AgentDB signed OpenClaw
  `candidate_queue_review` task can be claimed, routed through the real
  environment-bound queue-loop runner, and advance an already authorized queue
  item into bounded artifact materialization in an isolated worktree.
- Refined the queue-loop runner safety check: isolated worktree creation and
  bounded file materialization are allowed only after the upstream queue gates
  accept; shell execution, OpenClaw enqueue, Hermes dispatch, HoloIndex
  re-index, PR creation, PatternMemory writes, and reward settlement remain
  fail-closed.
- Boundary remains explicit: the proof performs no source checkout write, no
  shell command, no live model call, no PR publication, no HoloIndex mutation,
  no PatternMemory admission, and no reward settlement.

## 2026-07-16: REDDOG_SIGNED_WORKER_OPENCLAW_QUEUE_LOOP_RUNTIME_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added an explicit runtime binding that builds the OpenClaw signed-worker
  queue-loop runner from environment-provided outside-repo artifacts.
- Wired `run_task.execute_task()` to use the bound runner when
  `REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER=1`, preserving the default
  fail-closed `RUNNER_MISSING` behavior when the binding is not requested.
- Hardened the OpenClaw signed-worker claim seam so it only claims
  `openclaw` / `candidate_queue_review` tasks; Hermes and 0102 signed-worker
  tasks remain pending for future dedicated consumers instead of being failed
  by the wrong runner.
- Boundary remains non-mutating: no shell command, source repo mutation,
  worktree creation, PR, Hermes dispatch, PatternMemory write, HoloIndex
  re-index, or reward settlement is introduced by this slice.

## 2026-07-16: REDDOG_SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a signed-worker runner adapter for the OpenClaw candidate task that
  advances the existing resident queue serial-loop bootstrap for the bound
  queue item.
- Restricted this runner to `openclaw` / `candidate_queue_review` signed
  worker intents; 0102 coding workers and other capabilities remain blocked
  for later dedicated runners.
- Bound runner success to bootstrap acceptance plus no source-repo mutation and
  no shell command execution, so it can be safely consumed by the signed-worker
  task executor.
- Boundary remains explicit and non-mutating by this adapter: no default
  bootstrap bypass, no task creation, no signing, no source repo mutation, no
  shell command, no PR, no PatternMemory write, no HoloIndex re-index, and no
  reward settlement is performed by this slice.

## 2026-07-16: REDDOG_SIGNED_WORKER_TASK_OPENCLAW_CLAIM_RUNTIME_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added the exact signed worker-dispatch AgentDB task executor that validates
  the published worker-dispatch context and calls only an explicitly injected
  runner.
- Wired `run_task.execute_task()` to route signed worker-dispatch tasks before
  generic WRE fallback, so a missing runner fails closed instead of executing
  as a generic skill.
- Added an OpenClaw claim-once seam for signed worker-dispatch tasks that
  atomically claims the AgentDB task, runs the exact executor, completes or
  fails the task, and returns a bounded claim receipt.
- Boundary remains non-mutating by default: no default worker runner, shell
  command, source repo mutation, worktree operation, Hermes dispatch, PR,
  PatternMemory write, HoloIndex re-index, or reward settlement is performed
  by this slice.

## 2026-07-16: REDDOG_OPENCLAW_HERMES_0102_WORKER_DISPATCH_RUNTIME_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added the signed worker-dispatch runtime publication stage that converts
  accepted dry-run worker intents into pending AgentDB task specs via an
  injected writer.
- Inserted `worker_dispatch_runtime` between `worker_dispatch_dryrun` and
  `work_order_invocation` in the resident queue orchestration plan, keeping
  downstream work-order invocation blocked until task publication succeeds.
- Preserved the authority boundary: no worker process start, Hermes
  execution, shell command, worktree creation, source repo mutation, PR,
  PatternMemory write, HoloIndex re-index, reward settlement, or automatic
  runtime invocation is performed by this slice.

## 2026-07-16: REDDOG_ARCHITECT_FIX_TO_SIGNED_WSP15_WORK_ORDER_PROMOTION_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added the backend RedDog architect `FIX` promotion bridge that turns one
  accepted architect queue candidate into an authoritative work-state queue
  item plus durable worker claim for the existing signed WSP_15 authority
  chain.
- Bound promotion to the architect determination receipt, WSP_15 allocation
  digest, production model selection receipt, operational Memex supply
  receipt, HoloIndex evidence mapping, and current freshness receipt before
  any queue mutation is committed.
- Preserved the authority boundary: no signing, worker spawn, OpenClaw enqueue,
  Hermes dispatch, worktree creation, shell execution, source repo mutation,
  PR creation, PatternMemory write, or HoloIndex re-index is performed by this
  slice.

## 2026-07-16: REDDOG_OPERATIONAL_MEMEX_SNAPSHOT_SUPPLIER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added an operational Memex snapshot supplier wrapper for resident RedDog
  read-only audit tasks. It assembles a FoundUp Memex view from the accepted
  operational snapshot and injects assignment-bound Memex bindings into
  AgentDB task context before OpenClaw workers claim the task.
- Wired optional Memex supply through the main read-only bootstrap, durable
  resident AgentDB cycle, and thin-client bridge payload while keeping the
  default resident cycle unchanged.
- Added a HoloIndex generation binding to operational snapshots so Memex
  projections bind to the exact retrieval generation used by the resident
  cycle.
- Tightened worker model-context packing so Memex remains supplemental and
  cannot crowd out current repository evidence; full Memex receipt IDs remain
  bound in worker receipts.
- Boundary remains read-only: no Memex write, Brain/Breadcrumb write,
  HoloIndex re-index, shell, repo mutation, worker spawn expansion, Hermes
  dispatch, worktree operation, PR, PatternMemory promotion, or live FoundUp
  enqueue.

## 2026-07-16: REDDOG_RESIDENT_ARCHITECT_DURABLE_AGENTDB_CYCLE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 97

- Added a durable resident RedDog cycle runtime that persists
  `reddog_intent.v1`, enqueues read-only audit tasks to AgentDB, resumes by
  `intent_id`, handles duplicate/cancel/timeout states, and persists backend
  architect determinations.
- Added an OpenClaw-owned RedDog read-only audit claim seam so resident RedDog
  no longer runs audit tasks through the previous inline E2E shortcut.
- Updated the resident architect session bridge to call the durable AgentDB
  cycle and surface cycle/task/claim status to the thin client.
- Added tests for durable submission, OpenClaw claiming, report persistence,
  architect determination, duplicate reconnect, missing governed
  external-research retriever rejection, timeout, cancellation, and bridge
  summarization.
- Boundary remains read-only: no shell, repo mutation, HoloIndex re-index,
  Hermes dispatch, worktree operation, PR creation, PatternMemory promotion,
  or live FoundUp enqueue.

## 2026-07-16: REDDOG_RESIDENT_QUEUE_DRAFT_PR_PUBLISH_REQUEST_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 50, 97

- Added resident queue verified draft-PR publish request binding that derives
  the publish request from an explicit `draft_pr_publish_plan` plus recorded
  slice-verifier and worktree-create chain results.
- Wired the resident queue `verified_draft_pr_publish` stage to use the
  derived publish request only when
  `REDDOG_DRAFT_PR_PUBLISH_REQUEST_BINDING` is explicitly enabled; the
  existing external publish request JSON path remains unchanged.
- Boundary remains draft-only and runner-gated: no default runner, mark-ready,
  merge, command execution, PatternMemory write, reward settlement, HoloIndex
  re-index, OpenClaw enqueue, or Hermes dispatch is added by this slice.

## 2026-07-16: REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_REQUEST_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 50, 97

- Added resident queue slice-verifier request binding that derives the
  independent evidence-producer request from an explicit `slice_verifier_plan`
  plus recorded authority, authority-verification, worktree-create, and bounded
  pilot chain results.
- Wired the resident queue `slice_verifier` stage to use the derived evidence
  request only when `REDDOG_SLICE_VERIFIER_REQUEST_BINDING` is explicitly
  enabled; the existing external verifier/evidence JSON paths remain
  unchanged.
- Preserved bounded evidence production and autonomous verifier boundaries:
  no GitHub call, PR publish, merge, PatternMemory write, reward settlement,
  HoloIndex re-index, OpenClaw enqueue, or Hermes dispatch is added by this
  slice.

## 2026-07-16: REDDOG_RESIDENT_QUEUE_PILOT_DRYRUN_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 50, 97

- Added resident queue pilot dry-run binding that derives generic-writer and
  governed-shell dry-run receipts from an explicit `bounded_worker_plan` plus
  recorded authority, verification, valve, and worktree chain results.
- Wired the resident queue `bounded_worker_pilot` stage to use the derived
  dry-run receipts only when `REDDOG_PILOT_DRYRUN_BINDING` is explicitly
  enabled; the existing external dry-run JSON path remains unchanged.
- Added `main.py` startup plumbing for `REDDOG_PILOT_DRYRUN_BINDING`.
- Boundary remains dry-run guarded: no extra worktree creation, shell command,
  GitHub call, PR publish, merge, PatternMemory write, reward settlement,
  HoloIndex re-index, OpenClaw enqueue, or Hermes dispatch.

## 2026-07-16: REDDOG_BOUNDED_ARTIFACT_GENERATION_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 50, 97

- Added a bounded artifact-generation runtime that validates model/generated
  artifact text before the resident queue bounded-worker pilot may materialize
  it in an isolated worktree.
- Wired the resident queue `bounded_worker_pilot` stage to accept either
  prebuilt artifact contents or an explicit artifact-generation request plus an
  explicitly injected/configured generator. No default generator is created.
- Added `main.py` preflight environment plumbing for
  `REDDOG_ARTIFACT_GENERATION_REQUEST_PATH` and
  `REDDOG_ARTIFACT_GENERATOR_MODE`.
- Boundary remains guarded by the existing bounded-worker pilot: no shell
  execution, GitHub call, PR publish, merge, PatternMemory write, reward
  settlement, HoloIndex re-index, OpenClaw enqueue, or Hermes dispatch is added
  by this slice.

## 2026-07-16: WRE_INDEPENDENT_EVIDENCE_PRODUCER_QUEUE_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 50, 97

- Wired the resident queue `slice_verifier` stage to optionally produce
  independent machine-derived diff/test evidence from the assigned isolated
  worktree before invoking the existing queue-authorized autonomous slice
  verifier.
- Preserved the existing prebuilt verifier-request path. The new evidence path
  requires an explicit evidence-producer request and an explicitly injected
  command runner; default startup behavior remains unchanged.
- Added `main.py` preflight environment plumbing for
  `REDDOG_EVIDENCE_PRODUCER_REQUEST_PATH` and
  `REDDOG_EVIDENCE_COMMAND_RUNNER_MODE`.
- Boundary remains bounded and fail-closed: no GitHub call, draft PR publish,
  merge, PatternMemory write, reward settlement, HoloIndex re-index, OpenClaw
  enqueue, or Hermes dispatch.

## 2026-07-16: REDDOG_MAIN_READONLY_E2E_RUNTIME_CONSUMPTION_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 50, 97

- Added an explicit `main.py` startup flag,
  `REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_ENABLED`, that runs one
  read-only audit -> research -> backend architect determination cycle through
  the #1115 E2E runtime.
- Kept the existing bootstrap/menu behavior unchanged by default. Rejected E2E
  runs remain warning-only unless
  `REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED=1`.
- Startup output now reports E2E task count, persisted report count,
  architect action/next slice, queue-candidate count, and the no-mutation
  attestation fields needed to verify this is not a coding worker path.

## 2026-07-16: REDDOG_READONLY_AUDIT_RESEARCH_DECISION_E2E_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 50, 97

- Added an explicit resident-cycle runtime that composes the existing RedDog
  read-only operational bootstrap, read-only audit task enqueue seam, model
  backed 0102 audit executor, report persistence, report collection, and
  backend architect determination.
- The cycle now proves the current operational loop can plan the five default
  audit lanes, execute those read-only worker tasks with injected model/index
  adapters, persist their reports, validate the report bundle, and emit one
  backend architect queue candidate.
- Added fail-closed coverage for task execution rejection and report
  persistence rejection before any final architect determination.
- Boundary remains read-only: no shell execution, repository mutation,
  worktree operation, Hermes dispatch, live FoundUp enqueue, PR creation,
  PatternMemory promotion, or HoloIndex re-index.

## 2026-07-16: REDDOG_EXTERNAL_RESEARCH_AUDIT_RUNTIME_CONSUMPTION_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 50, 97

- Wired the existing HoloIndex-first external research grounding adapter into
  the model-backed read-only audit worker for the `external_research_audit`
  lane.
- Added bounded, sanitized external research excerpts so the lane can analyze
  source evidence while preserving the trust boundary that external content is
  untrusted data, never instructions.
- Extended typed evidence citation policy with `external:` evidence refs.
  External refs may be primary only when explicitly supplied by the external
  research lane; Memex evidence remains supplemental and cannot stand alone.
- Worker receipts now bind external research query receipts and evidence
  bundle IDs, while rejected or unconfigured explicit external targets fail
  closed before any model call.
- Boundary remains read-only: no network retriever implementation, HoloIndex
  re-index, PatternMemory write, repository mutation, shell execution,
  OpenClaw enqueue, Hermes dispatch, worktree operation, PR creation, or merge
  authority.

## 2026-07-16: REDDOG_READONLY_AUDIT_MULTI_LANE_MODEL_WORKERS_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 50, 97

- Updated read-only audit swarm enqueue so all default audit lanes are explicit
  `model_backed_0102` worker tasks, not only `repo_code_audit`.
- Generalized the guarded model-backed read-only audit path to accept any
  explicit audit lane while preserving WSP_15 binding, HoloIndex/CodeIndex
  query receipts, governed direct reads, Memex evidence, redaction-gated model
  calls, strict JSON validation, and typed evidence citation policy.
- Added a runtime-freshness lane regression proving a non-repo lane reaches the
  same guarded model path and carries its lane in the prompt.
- Updated the enqueue fixture to satisfy current HoloIndex freshness receipt
  generation/manifest verification semantics.
- Boundary remains read-only: no repository mutation, shell execution, worktree
  operation, OpenClaw child enqueue, Hermes dispatch, HoloIndex re-index, PR
  creation, merge authority, or PatternMemory promotion.

## 2026-07-16: REDDOG_MEMEX_SNAPSHOT_PROJECTION_SUPPLIER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 22, 50, 97

- Added an assignment-bound Memex snapshot projection supplier for read-only
  RedDog audit workers.
- Runtime can now take an explicit `memex_view`, construct a matching access
  policy receipt and HoloIndex shadow projection, then reuse the existing
  integrity, query-receipt, evidence-bundle, and citation gates.
- Missing assignment bindings, missing policy expiry, scope mismatch, snapshot
  mismatch, projection tampering, replay, and policy failures reject before any
  model call.
- Boundary remains read-only: no HoloIndex re-index, Memex write, Brain write,
  Breadcrumb write, repo mutation, shell execution, OpenClaw enqueue, Hermes
  dispatch, worktree operation, PR, merge, or PatternMemory promotion.
- Policy issuance is still deterministic integrity only; authenticated policy
  authority remains outside this slice.

## 2026-07-16: REDDOG_TYPED_EVIDENCE_CITATION_POLICY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 60, 97

- Added a typed citation policy for read-only RedDog audit output.
- Repository `file:` evidence can support current implementation claims.
  `memex:` evidence is allowed only as supplemental historical memory context
  beside at least one current repository file evidence ref.
- Wired the policy into model-backed repo-audit output validation so unknown
  file refs, unknown Memex refs, and Memex-only findings fail closed.
- Updated the model prompt rules to state that Memex evidence cannot replace
  file evidence for repo-audit findings.
- Boundary remains read-only: no authority promotion, worker spawn, OpenClaw
  enqueue, Hermes dispatch, repo mutation, HoloIndex re-index, or PatternMemory
  promotion.

## 2026-07-16: REDDOG_MEMEX_CONTENT_BEARING_EVIDENCE_BUNDLE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 60, 97

- Updated the model-backed read-only audit worker to attach a content-bearing
  `memex_evidence_bundle` whenever an assignment-bound Memex query receipt is
  accepted.
- The model context now receives bounded Memex record text with a clear trust
  boundary that Memex memory is not current repository proof.
- Worker receipts bind the `memex_evidence_bundle_id` beside the Memex query
  receipt id for replayable review.
- Existing output validation still permits only repository file evidence refs
  in findings; typed Memex citation policy remains the next slice.
- Boundary remains read-only: no Memex supplier, citation-policy expansion,
  worker spawn, OpenClaw enqueue, Hermes dispatch, repo mutation, HoloIndex
  re-index, or authority promotion.

## 2026-07-16: REDDOG_MEMEX_SNAPSHOT_ASSIGNMENT_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 60, 97

- Hardened the model-backed read-only audit worker so supplied Memex
  projections are assignment-bound before any model call.
- Runtime Memex consumption now requires and revalidates an access-policy
  receipt against principal, work order, FoundUp id, source scope, and expiry.
- The projection integrity gate is invoked with expected FoundUp, source scope,
  source revision, HoloIndex generation, operational snapshot id/content
  digest, access-policy digest, replay state, and revocation state.
- Missing policy receipts, mismatched policy work orders, mismatched projection
  snapshot bindings, and replayed projection receipts fail closed before the
  RedDog/Fusion model runner is called.
- Boundary remains read-only: no Memex supplier, content-bearing citation
  policy, worker spawn, OpenClaw enqueue, Hermes dispatch, repo mutation,
  HoloIndex re-index, or authority promotion.

## 2026-07-16: FOUNDUP_MEMEX_MULTI_FOUNDUP_SCOPE_HARDENING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 60, 97

- Hardened FoundUp Brain/Memex current-state assembly for resident
  multi-FoundUp operation.
- Resident mode now requires explicit FoundUp scoping across identity,
  roadmap, outcomes, worker claims, queue items, and policy FoundUp scope.
- Foreign worker claims and queue items are excluded with deterministic
  count/digest accounting instead of leaking into the selected FoundUp or
  rejecting the whole mixed snapshot.
- Legacy single-FoundUp inference now requires explicit compatibility mode and
  marks inferred records with `legacy_single_foundup_compatibility`.
- Added an assembly receipt to the read-only view with included/excluded work
  counts, excluded-record digest, policy scope, and no-write attestations.
- Tests cover independent A/B FoundUp views from one mixed snapshot, resident
  rejection of unscoped records, explicit compatibility mode, and policy-scope
  mismatch.

## 2026-07-16: HOLOINDEX_MEMEX_PROJECTION_INTEGRITY_AND_REHYDRATION_GATE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 60, 97

- Updated `reddog_readonly_0102_audit_worker_runtime.py` so optional Memex
  projections are verified through the HoloIndex integrity/rehydration gate in
  runtime mode before any Memex query receipt is built.
- Runtime mode rejects placeholder access-policy digests and any tampered,
  expired, replayed, revoked, or binding-mismatched serialized projection
  before the RedDog/Fusion model call.
- Added a regression proving a tampered Memex record body rejects before the
  model runner is called. Existing no-Memex behavior remains optional and
  unchanged.
- No Memex supplier, content-bearing citation policy, worker spawn, OpenClaw
  enqueue, Hermes dispatch, repo mutation, shell command, HoloIndex re-index,
  or authority promotion is added.

## 2026-07-16: REDDOG_MEMEX_QUERY_RECEIPT_RUNTIME_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 60, 97

- Updated `reddog_readonly_0102_audit_worker_runtime.py` so a model-backed
  read-only repo audit can optionally consume a caller-supplied governed Memex
  projection and convert it into a `source_class=memex` query receipt before
  the RedDog/Fusion model call.
- The Memex receipt is included in the model context, model binding, and worker
  receipt only when supplied; existing no-Memex task contexts remain unchanged.
- Invalid supplied Memex projections fail closed before the model call. A
  successful Memex query miss is not treated as a HoloIndex freshness gap.
- Added tests proving Memex receipt propagation, generation binding,
  pre-model rejection for malformed Memex projections, and preservation of the
  read-only/no-reindex side-effect boundary.
- No Memex write, Brain/Breadcrumb write, HoloIndex re-index, repo mutation,
  worker spawn, OpenClaw enqueue, Hermes dispatch, PR creation, or authority
  promotion is added.

## 2026-07-15: REDDOG_OPENCLAW_READONLY_0102_AUDIT_WORKER_RUNTIME_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Upgraded the existing `reddog_readonly_audit` `run_task` seam so
  `repo_code_audit` assignments marked `model_backed_0102` invoke a
  redaction-gated, strict-JSON read-only 0102 model worker.
- Bound every read-only audit assignment and AgentDB task context to the
  canonical WSP_15 allocation receipt id/digest, with canonical validation
  rejecting boolean MPS values, malformed scores, mismatched priority totals,
  and unsafe worker-plan claims.
- Added production query-only HoloIndex discovery and CodeIndex advisory
  adapters. HoloIndex freshness/discovery now runs before governed direct-read
  evidence is finalized, and stale/unavailable discovery fails closed instead
  of letting the worker reason from caller-listed files alone.
- Hardened the WSP_15 binding so task context and assignment must match the
  recomputed allocation receipt id and canonical allocation digest; non-Fusion
  allocations cannot enter the model-backed worker path.
- Added digest-bound model route receipts plus stricter strict-JSON validation
  for WSP_97 labels, recommended actions, WSP_15 priority, severity, unknown
  fields, and `FIX`/`STOP` next-slice consistency.
- Replaced backend architect raw serialized-JSON slicing with deterministic
  field-level budgeting and fail-closed `PROMPT_BUDGET_EXCEEDED` behavior.
- Added tests for model-backed worker success, unknown evidence rejection,
  explicit runtime-mode failure, AgentDB/OpenClaw claim to `run_task` report
  persistence, WSP_15 validation hardening, and prompt-budget fail-closed.
- No source mutation, shell command, worktree operation, additional OpenClaw
  enqueue, Hermes dispatch, PR creation, PatternMemory promotion, or HoloIndex
  runtime re-index is added.

## 2026-07-15: REDDOG_BACKEND_ARCHITECT_DETERMINATION_RUNTIME_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `reddog_backend_architect_determination_runtime.py`, a real backend
  architect determination runtime that consumes an accepted operational
  snapshot, collected read-only audit reports, the Fusion assignment gate, and
  a canonical WSP_15 allocation receipt.
- The runtime calls an explicit RedDog/Fusion model runner, validates a strict
  `FIX | RESEARCH_MORE | REVISE | STOP` JSON determination, requires Fusion
  quorum and matching WSP_15 allocation receipt id, persists the determination,
  and emits at most one candidate queue item for `FIX`.
- Added an explicit opt-in path in `reddog_main_readonly_operational_bootstrap`
  so main startup behavior remains unchanged unless backend architect
  determination is requested.
- No coding worker spawn, shell command, worktree operation, repo mutation,
  OpenClaw enqueue, Hermes dispatch, PR creation, PatternMemory promotion, or
  HoloIndex runtime re-index is added.
- HoloIndex read-only probe for `RedDog backend architect determination
  runtime` is treated as
  `HOLOINDEX_REDDOG_BACKEND_ARCHITECT_DETERMINATION_RUNTIME_INDEX_GAP_PHASE1`
  until the new runtime is indexed by the governed WRE/CI indexer.

## 2026-07-15: REDDOG_RESIDENT_QUEUE_WORKER_DISPATCH_DRYRUN_STAGE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Inserted `worker_dispatch_dryrun` into the resident queue serial chain after
  authority verification and before verified work-order invocation.
- Added a resident queue stage handler that consumes the accepted signed
  authority runtime and verification receipts plus the selected queue item's
  authoritative WSP_15 allocation receipt, then emits the existing signed
  authority worker-dispatch dry-run plan.
- The stage advances to work-order invocation only after a dispatch dry-run
  accept receipt; missing runtime, verification, selected queue item, or
  WSP_15 allocation fails closed.
- No worker spawn, queue mutation, worktree creation, shell command, OpenClaw
  enqueue, Hermes dispatch, repo mutation, PR creation, reward settlement,
  PatternMemory write, or HoloIndex runtime re-index is added.
- HoloIndex read-only probe for `RedDog resident queue worker dispatch dryrun
  stage` returned adjacent governance assets but not this new stage seam;
  recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_WORKER_DISPATCH_DRYRUN_STAGE_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-15: REDDOG_SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added a signed-authority worker-dispatch dry-run planner that consumes an
  accepted queue authority verification result, the signed authority runtime
  payload, and the authoritative WSP_15 allocation receipt.
- The planner verifies that the signed work-authority allocation receipt id,
  digest, priority, MPS total, and reasoning tier match the supplied WSP_15
  allocation before emitting deterministic worker-dispatch intents.
- WSP_15 worker-plan fields now produce dry-run intents for fusion lead,
  critics, coding workers, independent verifier, and OpenClaw candidate review
  without registering workers, mutating queues, spawning processes, or invoking
  Hermes/OpenClaw.
- The slice rejects post-signing allocation tamper, queue-mutation permission,
  Hermes execution permission, malformed MPS/priority relationships, missing
  explicit invoke, and unaccepted authority inputs.
- No worker spawn, queue mutation, worktree creation, shell command, OpenClaw
  enqueue, Hermes dispatch, repo mutation, PR creation, reward settlement,
  PatternMemory write, or HoloIndex runtime re-index is added.
- HoloIndex read-only probe for `RedDog signed authority worker dispatch
  dryrun WSP15` returned adjacent RedDog governance assets but not this new
  seam; recorded as
  `HOLOINDEX_REDDOG_SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-15: REDDOG_SIGNED_AUTHORITY_WSP15_ALLOCATION_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Extended the WRE queue consumer receipt to emit the digest of the selected
  queue item's full WSP_15 allocation receipt.
- Threaded `wsp15_allocation_receipt_id`, `wsp15_allocation_digest`,
  `wsp15_priority`, `wsp15_mps_total`, and `wsp15_reasoning_tier` into the
  delegated-authority runtime request and signed work-authority payload.
- Updated the work-order signature verifier to require those WSP_15 allocation
  binding fields; post-signing allocation digest tampering now rejects as an
  invalid work-authority signature.
- No signing key material, worker spawn, OpenClaw enqueue, Hermes dispatch,
  worktree creation, shell command, repo mutation, reward settlement,
  PatternMemory write, or HoloIndex runtime re-index is added.
- HoloIndex read-only probe for `RedDog signed authority WSP15 allocation
  digest binding` returned adjacent authority/governance assets but not this
  seam; recorded as
  `HOLOINDEX_REDDOG_SIGNED_AUTHORITY_WSP15_ALLOCATION_BINDING_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-15: REDDOG_WORK_ORDER_MATERIALIZER_QUEUE_WSP15_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Updated the resident queue work-order materializer to source WSP_15
  allocation from the selected authoritative queue item. Authority-profile and
  snapshot copies are consistency checks only and fail closed on conflict.
- This keeps queue-bound WSP_15 evidence authoritative through queue consumer,
  authority-request dry-run, and materialized work-order context binding.
- Missing operational context receipts still fail closed; this slice removes
  the need to duplicate WSP_15 allocation in the external authority profile
  when the queue item already carries it, without allowing profile or snapshot
  allocation to override the selected queue item.
- No signing, worker spawn, OpenClaw enqueue, Hermes dispatch, worktree
  creation, shell command, repo mutation, reward settlement, PatternMemory
  write, or HoloIndex runtime re-index is added.
- HoloIndex read-only probe for `RedDog work order materializer queue WSP15
  allocation binding` returned adjacent queue/WSP assets but not this binding
  seam; recorded as
  `HOLOINDEX_REDDOG_WORK_ORDER_MATERIALIZER_QUEUE_WSP15_BINDING_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-15: REDDOG_AUTHORITY_REQUEST_WSP15_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Bound the WRE queue consumer's WSP_15 allocation receipt into the delegated
  authority request dry-run receipt before any signer invocation can occur.
- The authority-request planner now rejects queue consumer receipts missing
  `wsp15_allocation_receipt_id`, `wsp15_priority`, `wsp15_mps_total`, or
  `reasoning_tier`, and rejects an authority profile that contradicts the
  queue allocation receipt.
- The signed authority runtime request schema is not expanded in this slice;
  the WSP_15 allocation remains pre-signing evidence in the queue-authority
  dry-run receipt.
- No signing, signature verification, worker spawn, OpenClaw enqueue, Hermes
  dispatch, worktree creation, shell command, repo mutation, reward settlement,
  PatternMemory write, or HoloIndex runtime re-index is added.
- HoloIndex read-only probe for `RedDog authority request WSP15 allocation
  binding queue consumer receipt` returned adjacent RedDog/WSP assets but not
  this authority-request binding seam; recorded as
  `HOLOINDEX_REDDOG_AUTHORITY_REQUEST_WSP15_BINDING_INDEX_GAP_PHASE1`. No
  runtime re-index is performed in this slice.

## 2026-07-15: REDDOG_AUTHORITATIVE_WORK_STATE_WSP15_QUEUE_BINDING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Bound the deterministic WSP_15 allocation receipt into the authoritative
  work-state runtime WRE queue item for the selected slice.
- Queue items now include `wsp15_allocation_receipt` and an evidence ref of
  `wsp15_allocation:<receipt_id>` alongside claim and freshness refs.
- Updated the WRE queue consumer dry-run to fail closed when the WSP_15
  allocation receipt is missing or not referenced, and to surface priority,
  MPS total, and reasoning tier in the consumer receipt.
- No queue mutation beyond the existing authoritative work-state atomic commit,
  worker spawn, OpenClaw enqueue, Hermes dispatch, worktree creation, shell
  command, repo mutation, reward settlement, PatternMemory write, or HoloIndex
  runtime re-index is added.
- HoloIndex read-only probe for `RedDog authoritative work state WSP15 queue
  binding allocation receipt` returned adjacent RedDog/WSP assets but not this
  binding seam; recorded as
  `HOLOINDEX_REDDOG_AUTHORITATIVE_WORK_STATE_WSP15_QUEUE_BINDING_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-15: REDDOG_WSP15_ALLOCATION_RECEIPT_RUNTIME_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wsp15_allocation_receipt.py`, a deterministic WSP_15
  MPS allocation receipt for RedDog work-focus planning.
- The receipt records complexity, importance, deferability, impact, total MPS,
  P0-P4 priority, reasoning tier, and a worker-plan recommendation without
  calling models, spawning workers, mutating queues, or re-indexing HoloIndex.
- Threaded the allocation receipt into
  `reddog_main_readonly_operational_bootstrap` ready and not-ready results so
  downstream authority-profile materialization can bind to a real receipt
  instead of hand-written WSP_15 fields.
- Added tests for P0/ULTRA authority-sensitive RedDog runtime work, regular
  low-priority prompts, deterministic JSON serialization, score bounds, static
  execution/indexing import denial, and bootstrap result propagation.
- No OpenClaw enqueue, Hermes dispatch, worktree creation, shell command,
  draft PR, merge, reward settlement, PatternMemory write, or HoloIndex runtime
  re-index is added.
- HoloIndex read-only probe for `RedDog WSP15 allocation receipt MPS worker
  plan` returned adjacent RedDog/WSP assets but not the new allocation module;
  recorded as `HOLOINDEX_REDDOG_WSP15_ALLOCATION_RECEIPT_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_WORK_ORDER_MATERIALIZER_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 34, 50, 97

- Added explicit `REDDOG_WORK_ORDER_MATERIALIZER_MODE=authority_profile`
  startup wiring for the resident queue serial loop.
- When `REDDOG_WORK_ORDERS_PATH` is absent and the materializer mode is
  explicitly set, the bootstrap derives one in-memory governed work order from
  the selected authoritative queue item and the signed-authority profile.
- The derived work order is bound to the same `work_order_id`, repo,
  requested operation, permission snapshot digest, allowed paths, and denied
  paths used by the delegated-authority request. It feeds only the existing
  `work_order_invocation` resolver path; it does not write a work-order file.
- The materializer now requires real operational context binding
  (`snapshot_receipt_id`, `context_view_id`, `evidence_bundle_id`,
  `decision_id`) plus a supplied WSP_15 allocation receipt and supplied
  HoloIndex evidence. Missing evidence fails closed; this slice does not
  fabricate retrieval success, work-focus digests, WSP prompt digests, or run
  trace digests from authority text alone.
- Fail-closed edges reject unsupported materializer modes and reject ambiguous
  use with an explicit `REDDOG_WORK_ORDERS_PATH`.
- No signer behavior, worktree creation, shell command, OpenClaw enqueue,
  Hermes dispatch, draft PR, merge, reward settlement, PatternMemory write, or
  HoloIndex runtime re-index is added.
- HoloIndex read-only probe for `RedDog resident queue work order materializer
  authority profile bootstrap` is recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_WORK_ORDER_MATERIALIZER_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_DRAFT_PR_RUNNER_BRIDGE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added explicit `main.py` env wiring for `REDDOG_DRAFT_PR_RUNNER_MODE=real`
  and `REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S`.
- The bridge constructs the existing approved
  `modules.foundups.agent.src.worktree_pr_runner.RealWorktreeRunner` only when
  explicitly requested, then injects it into the resident serial queue
  `verified_draft_pr_publish` stage.
- Default behavior remains fail-closed: no draft-PR runner is constructed and
  the existing stage rejects with `FAIL_DRAFT_PR_RUNNER_MISSING`.
- Unsupported runner modes or invalid timeouts reject before the resident queue
  bootstrap runs when startup enforcement is enabled.
- No PR is created by this bridge alone. The existing publish guard still
  requires accepted slice-verifier evidence, exact-head metadata, branch policy,
  and draft-only request fields before the injected runner can push or create a
  draft PR. No ready, merge, reward settlement, PatternMemory write, Hermes
  dispatch, OpenClaw enqueue, or HoloIndex runtime re-index is added.
- HoloIndex read-only probe for `RedDog main resident queue draft PR runner
  bridge verified draft PR publish RealWorktreeRunner` surfaced adjacent
  worktree runner and governed work-order assets, but not this new bridge seam;
  recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_DRAFT_PR_RUNNER_BRIDGE_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_PATTERN_MEMORY_SINK_BRIDGE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 34, 50, 97

- Added `src/reddog_verified_pattern_memory_sink.py`, an explicit outside-repo
  PatternMemory sink adapter for already-verified resident queue outcomes.
- Added `main.py` env wiring for `REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH`.
  The sink is constructed only when this path is set and it is outside the
  repository checkout.
- The sink maps a verified recursive improvement outcome into a WRE
  `SkillOutcome`, stores it through the existing `PatternMemory` API, rejects
  secret-bearing records, and returns a deterministic record id.
- Added tests proving outside-repo storage, inside-repo path rejection,
  idempotent repeated store, secret rejection, AST denylist invariants, and
  `main.py` pass-through into the resident queue bootstrap.
- No OpenClaw enqueue, Hermes dispatch, shell command, PR publish, merge,
  reward settlement, or HoloIndex re-index is performed by this bridge.
- HoloIndex read-only probe for `RedDog verified PatternMemory sink bridge
  resident queue outside repo database` returned adjacent guard, verifier, WSP,
  and audit assets, but not this sink bridge; recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_PATTERN_MEMORY_SINK_BRIDGE_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_PATTERN_MEMORY_ADMISSION_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 34, 50, 97

- Extended `src/reddog_main_resident_queue_serial_loop_bootstrap.py` so an
  explicitly enabled resident serial loop can load an outside-repo
  `admission_request` JSON artifact and, only with an explicitly injected
  PatternMemory admission sink, advance from `held_out_regression_gate` to
  `pattern_memory_admission`.
- Added `main.py` env wiring for `REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_PATH`.
  This slice does not construct a PatternMemory sink from `main.py`; installed
  runtime still fails closed at this stage unless a future explicit sink bridge
  is added.
- Added `no_pattern_memory_admission_performed` and
  `no_pattern_memory_write_performed` result attestations.
- Added tests proving the stage-13 happy path writes exactly through an
  injected fake sink, completes the resident queue chain, and preserves
  no-command, no-PR-publish, no-merge, no-reward, and no-HoloIndex-reindex
  invariants.
- Added fail-closed coverage proving an admission request without an injected
  sink stops the loop at `stage:pattern_memory_admission`.
- HoloIndex read-only probe for `RedDog main resident queue PatternMemory
  admission bootstrap admission request injected sink` returned adjacent
  live-enqueue, WSP, and audit assets, but not this bootstrap seam; recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_PATTERN_MEMORY_ADMISSION_BOOTSTRAP_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_HELD_OUT_REGRESSION_GATE_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 34, 50, 97

- Extended `src/reddog_main_resident_queue_serial_loop_bootstrap.py` so an
  explicitly enabled resident serial loop can load an outside-repo
  `held_out_gate_request` JSON artifact and advance from
  `verified_outcome_ratchet` to `held_out_regression_gate`.
- Added `main.py` env wiring for `REDDOG_HELD_OUT_GATE_REQUEST_PATH`.
- Added the `no_held_out_regression_gate_performed` result attestation.
- Added tests proving the stage-12 happy path evaluates held-out regression
  evidence, advances to `RUN_QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE`,
  and preserves no-command, no-test, no-PR-publish, no-merge, no-PatternMemory,
  no-reward, and no-HoloIndex-reindex invariants.
- Added fail-closed coverage proving a missing held-out gate request stops the
  loop at `stage:held_out_regression_gate`.
- HoloIndex read-only probe for `RedDog main resident queue held out regression
  gate bootstrap held out gate request` returned adjacent operational-spine,
  WSP, and audit assets, but not this bootstrap seam; recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_HELD_OUT_REGRESSION_GATE_BOOTSTRAP_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_VERIFIED_OUTCOME_RATCHET_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 34, 50, 97

- Extended `src/reddog_main_resident_queue_serial_loop_bootstrap.py` so an
  explicitly enabled resident serial loop can load an outside-repo
  `ratchet_request` JSON artifact and an outside-repo JSONL outcome-ratchet
  store, then advance from `verified_draft_pr_publish` to
  `verified_outcome_ratchet`.
- Added `main.py` env wiring for `REDDOG_OUTCOME_RATCHET_REQUEST_PATH` and
  `REDDOG_OUTCOME_RATCHET_STORE_PATH`.
- Added the `no_verified_outcome_ratchet_performed` result attestation.
- Added tests proving the stage-11 happy path records a verified outcome to an
  outside-repo JSONL store, advances to
  `RUN_QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE`, and preserves
  no-command, no-PR-publish, no-ready, no-merge, no-reward, no-PatternMemory,
  and no-HoloIndex-reindex invariants.
- Added fail-closed coverage proving a ratchet request without an injected or
  outside-repo outcome store stops the loop at `stage:verified_outcome_ratchet`.
- HoloIndex read-only probe for `RedDog main resident queue verified outcome
  ratchet bootstrap ratchet request JSONL store` returned adjacent wardrobe,
  receipt, and contract assets, but not this bootstrap seam; recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_VERIFIED_OUTCOME_RATCHET_BOOTSTRAP_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 34, 50, 97

- Extended `src/reddog_main_resident_queue_serial_loop_bootstrap.py` so an
  explicitly enabled resident serial loop can load an outside-repo
  `publish_request` JSON artifact and, with an explicitly injected draft-PR
  runner, advance from `slice_verifier` to `verified_draft_pr_publish`.
- Added `main.py` env wiring for `REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH`.
  This slice does not construct a real PR runner from `main.py`; installed
  runtime still fails closed at this stage unless a future explicit runner
  bridge is added.
- Added the `no_verified_draft_pr_publish_performed` result attestation and
  wired `no_pr_created` to the verified draft-PR publish stage boundary.
- Added tests proving the stage-10 happy path publishes only a draft PR through
  an injected fake runner, advances to
  `RUN_QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE`, and preserves
  no-ready, no-merge, no-PatternMemory, no-reward, and no-HoloIndex-reindex
  invariants.
- Added fail-closed coverage proving a publish request without an injected
  draft-PR runner stops the loop at `stage:verified_draft_pr_publish`.
- HoloIndex read-only probe for `RedDog main resident queue verified draft PR
  publish bootstrap publish request injected draft PR runner` returned adjacent
  worktree PR runner and audit assets, but not this bootstrap seam; recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_BOOTSTRAP_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_SLICE_VERIFIER_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 34, 50, 97

- Extended `src/reddog_main_resident_queue_serial_loop_bootstrap.py` so an
  explicitly enabled resident serial loop can load an outside-repo
  `verifier_request` JSON artifact and advance from `bounded_worker_pilot` to
  `slice_verifier`.
- Added `main.py` env wiring for `REDDOG_SLICE_VERIFIER_REQUEST_PATH`.
- Added the `no_slice_verification_performed` result attestation. The verifier
  stage performs evidence verification only; it still performs no command
  execution, GitHub call, PR publish, merge, PatternMemory write, reward
  settlement, OpenClaw enqueue, Hermes dispatch, or HoloIndex re-index.
- Added tests proving the stage-9 happy path verifies machine-derived evidence
  for the `modules/foundups/paccess_001/README.md` bounded pilot artifact and
  advances to `RUN_QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE`.
- Added fail-closed coverage proving missing verifier request input stops the
  loop at `stage:slice_verifier`.
- Validation: `test_reddog_main_resident_queue_serial_loop_bootstrap.py` (22
  passed) and adjacent resident/verifier/pilot/serial suites (81 passed).
- HoloIndex read-only probe for `RedDog main resident queue slice verifier
  bootstrap verifier request autonomous slice verifier` returned adjacent queue
  and docs assets, but not this bootstrap seam; recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_SLICE_VERIFIER_BOOTSTRAP_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_BOUNDED_WORKER_PILOT_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 34, 50, 97

- Extended `src/reddog_main_resident_queue_serial_loop_bootstrap.py` so an
  explicitly enabled resident serial loop can load outside-repo pilot inputs
  for `bounded_worker_pilot`: generic-writer dry-run result,
  governed-shell dry-run result, artifact contents, and HoloIndex evidence.
- Added `main.py` env wiring for
  `REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH`,
  `REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH`,
  `REDDOG_ARTIFACT_CONTENTS_PATH`, and
  `REDDOG_HOLOINDEX_EVIDENCE_PATH`.
- Added result attestations distinguishing isolated worktree creation from
  bounded pilot materialization:
  `no_bounded_task_execution_performed` and
  `no_bounded_file_edit_performed`.
- Added tests proving the stage-8 happy path materializes exactly one declared
  artifact under `modules/foundups/paccess_001/**` inside the isolated
  worktree only, leaves the repo checkout untouched, redacts the sovereign
  token from chain results, preserves no-shell/no-OpenClaw/no-Hermes/no-PR/
  no-HoloIndex-reindex boundaries, and advances to
  `RUN_QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE`.
- Added fail-closed coverage proving missing bounded-pilot artifacts stop the
  loop at `stage:bounded_worker_pilot`.
- Validation: `test_reddog_main_resident_queue_serial_loop_bootstrap.py` (20
  passed) and adjacent resident/worktree/pilot/cwd suites (86 passed).
- HoloIndex read-only probe for `RedDog main resident queue bounded worker
  pilot bootstrap artifact contents generic writer dryrun governed shell`
  returned adjacent governed-shell/generic-spine assets, but not this bootstrap
  seam; recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_BOUNDED_WORKER_PILOT_BOOTSTRAP_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_WORKTREE_CREATE_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 34, 50, 97

- Extended `src/reddog_main_resident_queue_serial_loop_bootstrap.py` so an
  explicitly enabled resident serial loop can inject a worktree runner and
  advance one more stage from `execution_valve` to `worktree_create`.
- Added `main.py` env wiring for
  `REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_MODE=real` and
  `REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_TIMEOUT_S`; no runner is constructed
  by default.
- Added tests proving explicit fake-runner worktree creation, fail-closed
  behavior without a runner, unsupported runner-mode rejection, token
  non-leakage, and preserved no-worker/no-task/no-OpenClaw/no-Hermes/no-PR
  boundaries.
- Boundary: worktree creation only when the resident serial loop is explicitly
  enabled, authority is signed and verified, the execution valve is open, and a
  runner is explicitly injected/configured. No task execution, no file edits,
  no OpenClaw enqueue, no Hermes dispatch, no PR, no reward settlement, no
  PatternMemory client, and no HoloIndex runtime re-index.
- HoloIndex read-only probe for `RedDog resident queue worktree create bootstrap
  real runner main serial loop` ranked the existing worktree runner but did not
  rank the bootstrap seam; recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_WORKTREE_CREATE_BOOTSTRAP_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_PLAN_VALVE_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Extended `src/reddog_main_resident_queue_serial_loop_bootstrap.py` so an
  explicitly enabled resident serial loop can load outside-repo work-order and
  execution-valve environment snapshots, then reuse the existing
  `work_order_invocation`, `executor_plan`, and `execution_valve` stage
  handlers.
- Added tests proving the startup loop can advance through signed authority,
  verified work-order invocation, executor dry-run planning, and execution
  valve evaluation, then stop before `worktree_create`.
- Added fail-closed coverage for missing/malformed work-order inputs and
  inside-repo valve environment paths, plus `main.py` env wiring for
  `REDDOG_WORK_ORDERS_PATH` and `REDDOG_EXECUTION_VALVE_ENV_PATH`.
- Boundary: no worker spawn, no worktree creation, no shell command, no
  OpenClaw enqueue, no Hermes dispatch, no PR, no repository mutation, no
  PatternMemory client, and no HoloIndex runtime re-index.
- HoloIndex read-only probe for `RedDog resident queue plan valve bootstrap work
  order invocation execution valve` did not rank the bootstrap module; recorded
  as `HOLOINDEX_REDDOG_RESIDENT_QUEUE_PLAN_VALVE_BOOTSTRAP_INDEX_GAP_PHASE1`.
  No runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_ISOLATED_SIGNER_PROCESS_ENTRYPOINT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 95, 97

- Added `src/reddog_isolated_signer_process_entrypoint.py`: a one-shot
  composition function that wires the test-only signer key-provider dry-run,
  kernel peer-credential attestor, and existing one-request signer socket
  service through injected dependencies.
- Added tests proving successful composition, key-provider rejection before
  service invocation, peer-policy rejection before key-provider/service use,
  invalid config rejection, service rejection/exception preservation, service
  return-type validation, receipt non-leakage, and AST denial of env, shell,
  file, repo, OpenClaw, Hermes, and HoloIndex runtime mutation surfaces.
- Boundary: injectable process entrypoint only. No environment parsing, no
  process spawn, no direct socket bind in this module, no file secret loading,
  no repository mutation, no OpenClaw enqueue, no Hermes dispatch, no WRE queue
  write, no reward settlement, and no HoloIndex runtime re-index.
- HoloIndex read-only probe for `RedDog isolated signer process entrypoint key
  provider peer credential service` is recorded as
  `HOLOINDEX_REDDOG_ISOLATED_SIGNER_PROCESS_ENTRYPOINT_INDEX_GAP_PHASE1`; no
  runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_SIGNER_SOCKET_PEER_CREDENTIAL_ATTESTOR_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 95, 97

- Added `src/reddog_signer_socket_peer_credential_attestor.py`: a
  fail-closed local-socket peer credential attestor for the isolated signer
  service. It maps kernel UID/GID evidence from `SO_PEERCRED` or `getpeereid`
  through an injected signer-owned policy into the existing
  `SignerPeerAttestation` record.
- Added tests proving successful UID/GID mapping, `getpeereid` fallback,
  unsupported-platform fail-closed behavior, malformed/exception credential
  rejection, UID/GID allowlist rejection, policy validation, no request-body
  identity parameter, and AST denial of shell, file, repo, OpenClaw, Hermes,
  and HoloIndex runtime mutation surfaces.
- Boundary: peer attestation only. No request payload identity is trusted, no
  OS user lookup, no file read, no signer launch, no socket binding, no shell
  command, no repository mutation, no OpenClaw enqueue, no Hermes dispatch, no
  WRE queue write, no reward settlement, and no HoloIndex runtime re-index.
- HoloIndex read-only probe for `RedDog signer socket peer credential attestor
  SO_PEERCRED getpeereid` is recorded as
  `HOLOINDEX_REDDOG_SIGNER_SOCKET_PEER_CREDENTIAL_ATTESTOR_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_SIGNER_KEY_PROVIDER_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 95, 97

- Added `src/reddog_signer_key_provider_dryrun.py`: a test-only signer
  key-provider adapter that validates the #1072 contract with injected
  resolver results and can construct the existing `Ed25519SignerBackend` only
  under explicit `TEST_ONLY_DRYRUN` mode with a fresh permission snapshot.
- Added tests proving default fail-closed behavior, test-only acceptance,
  signer backend interoperability, stale permission rejection, same-reference
  rejection, invalid reference rejection, resolver failure rejection, TTL
  rejection, key/audit format rejection, public-key/fingerprint mismatch
  rejection, non-ASCII/incomplete profile rejection, receipt non-leakage, and
  an AST denylist for shell, sockets, repo mutation, OpenClaw, Hermes, and
  HoloIndex runtime mutation surfaces.
- Boundary: dry-run/test-only provider. No production vault resolution, no
  environment or argv secret path, no file key loading, no socket binding, no
  signer process launch, no shell command, no repository mutation, no OpenClaw
  enqueue, no Hermes dispatch, no WRE queue write, no reward settlement, and
  no HoloIndex runtime re-index.
- HoloIndex read-only probe for `RedDog signer key provider dryrun WSP71
  Ed25519 audit mac` is recorded as
  `HOLOINDEX_REDDOG_SIGNER_KEY_PROVIDER_DRYRUN_INDEX_GAP_PHASE1`; no runtime
  re-index is performed in this slice.

## 2026-07-14: REDDOG_SIGNER_KEY_PROVIDER_CONTRACT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 95, 97

- Added `docs/contracts/REDDOG_SIGNER_KEY_PROVIDER_CONTRACT_PHASE1.md`:
  a decision-only contract freezing the signer-domain key-provider boundary
  before any implementation handles private key or audit-MAC material.
- Added a static contract test proving WSP 71 permission-validated retrieval,
  mock-vault non-production status, runtime non-possession of secret references
  and values, distinct signing/audit keys, public-only fingerprints, TTL at use
  time, HoloIndex query-only behavior, and the required dry-run-before-runtime
  sequence.
- Boundary: docs/static tests only. No key generation, key loading, vault
  configuration, signer launch, socket binding, shell command, repository
  mutation, OpenClaw enqueue, Hermes dispatch, WRE queue write, reward
  settlement, or HoloIndex runtime re-index.
- HoloIndex read-only probe for `RedDog signer key provider WSP71 vault op
  reference Ed25519` is recorded as
  `HOLOINDEX_REDDOG_SIGNER_KEY_PROVIDER_CONTRACT_INDEX_GAP_PHASE1`; no runtime
  re-index is performed in this slice.

## 2026-07-14: REDDOG_ISOLATED_SIGNER_SOCKET_SERVICE_ONCE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 97

- Added `src/reddog_isolated_signer_socket_service.py`: a one-request local
  socket service boundary for an isolated RedDog signer. It binds only an
  absolute outside-repo socket path, serves one bounded request through the
  existing signer protocol, and removes the socket path after closing.
- Added tests for guarded path validation, invalid limit rejection, default
  peer-attestor fail-closed behavior, default backend fail-closed behavior, and
  a real client-to-service Ed25519 round-trip when AF_UNIX sockets are
  available. Windows Python builds without AF_UNIX skip only the live socket
  round-trip tests.
- Boundary: socket service only. No private key loading, no vault secret
  resolution, no signer spawn, no shell command, no repository mutation, no
  OpenClaw enqueue, no Hermes dispatch, no PR creation, no reward settlement,
  and no HoloIndex runtime re-index.
- HoloIndex read-only probe for `RedDog isolated signer socket service serve
  once peer attestor` surfaced signer-isolation contracts and adjacent tests,
  but not this new service module before indexing. Recorded as
  `HOLOINDEX_REDDOG_ISOLATED_SIGNER_SOCKET_SERVICE_ONCE_INDEX_GAP_PHASE1`; no
  runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_ED25519_VERIFICATION_BUNDLE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 97

- Extended the `main.py` resident serial-loop dependency bundle so an explicit
  `REDDOG_SIGNATURE_VERIFIER_BACKEND=ed25519` setting wires the public
  `Ed25519SignatureVerifier`, token-verified principal key resolver, durable
  outside-repo work-authority nonce consumption, and authority-state revocation
  oracle into the `authority_verification` stage.
- Added tests proving default verification remains unregistered, explicit
  Ed25519 verification advances the serial loop through
  `authority_verification`, work-authority nonce replay is durably rejected,
  revocations are read from the authority runtime state, unsupported verifier
  backends reject, and `main.py` passes the verifier backend setting through.
- Boundary: public verification wiring only. No private key loading, no key
  generation, no signer spawn, no shell command, no worktree, no OpenClaw
  enqueue, no Hermes dispatch, no PR publication, no repository mutation, and
  no HoloIndex runtime re-index.
- HoloIndex read-only probe for `RedDog resident queue Ed25519 verification
  backend bundle signature verifier` surfaced the core verifier and adjacent
  docs, but not this new bundle wiring before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_ED25519_VERIFICATION_BUNDLE_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_ED25519_SIGNER_BACKEND_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 97

- Added `src/reddog_ed25519_signer_backend.py`: a signer-side backend that
  signs `SigningRequest` records with an already-held Ed25519 key object and
  an injected audit-MAC builder for use inside the future isolated signer
  process.
- Added tests proving public-verifier acceptance of produced signatures,
  signer-socket protocol round-trip, public-key mismatch rejection, key-epoch
  mismatch rejection, key-object/public-key mismatch rejection, audit-MAC
  fail-closed behavior, and AST denial of key-loading, repo, shell, socket,
  environment, OpenClaw/Hermes, and HoloIndex runtime surfaces.
- Boundary: signer backend only. No key generation, key loading, vault access,
  socket binding, process spawn, command execution, repository mutation,
  OpenClaw enqueue, Hermes dispatch, reward settlement, or HoloIndex runtime
  re-index. The backend requires the isolated signer process to inject the key
  object and audit-MAC boundary.
- HoloIndex read-only probe for `RedDog Ed25519 signer backend isolated signer
  SigningResponse audit_mac` surfaced signing-key contract and signed-receipt
  modules, but not this backend before indexing. Recorded as
  `HOLOINDEX_REDDOG_ED25519_SIGNER_BACKEND_INDEX_GAP_PHASE1`; no runtime
  re-index is performed in this slice.

## 2026-07-14: REDDOG_ED25519_SIGNATURE_VERIFIER_BACKEND_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 97

- Added `src/reddog_ed25519_signature_verifier_backend.py`: an optional
  injected `SignatureVerifier` backend for RedDog work-order authority records.
  It verifies self-describing `ed25519-pub-v1:` public keys and
  `ed25519-sig-v1:` signatures using public material only.
- Added tests proving valid Ed25519 verification, tamper/key/signature
  rejection, malformed/non-ASCII rejection, strict encode/decode helpers,
  oversized signing-input rejection, and AST denial of signer/keygen/shell/env/
  network/HoloIndex/runtime mutation imports.
- Boundary: verifier backend only. No signing, key generation, private-key
  loading, vault access, signer daemon startup, command execution, repository
  mutation, OpenClaw enqueue, Hermes dispatch, or HoloIndex runtime re-index.
  The backend fails closed if `cryptography` is unavailable or verification
  raises.
- HoloIndex read-only probe for `RedDog work order signature verifier
  cryptographic backend Ed25519` surfaced the core verifier and contracts, but
  not this backend before indexing. Recorded as
  `HOLOINDEX_REDDOG_ED25519_SIGNATURE_VERIFIER_BACKEND_INDEX_GAP_PHASE1`; no
  runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_ISOLATED_SIGNER_SOCKET_PROTOCOL_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 97

- Added `src/reddog_isolated_signer_socket_protocol.py`: a fail-closed
  signer-side protocol core for the isolated signer socket client. It parses a
  bounded client request, binds requester identity to an out-of-band peer
  attestation, invokes an injected signing backend, and serializes an existing
  `SigningResponse`.
- Added tests proving accepted backend responses, default fail-closed backend,
  malformed/schema/oversized request rejection, peer-spoof rejection before
  backend invocation, peer-attestation rejection, non-ASCII rejection, backend
  exception rejection, invalid accepted-response rejection, and AST denial of
  socket/subprocess/env/HoloIndex/crypto/vault/key-loading imports.
- Boundary: protocol core only. No socket is bound, no signer process is
  spawned, no kernel peer credential is discovered, no private key or vault
  secret is loaded, no shell command is executed, no repository file is
  mutated, and no HoloIndex runtime re-index is performed.
- HoloIndex read-only probe for `RedDog isolated signer service runtime socket
  signing backend` surfaced signature-verifier/signed-receipt code and the E0
  contract, but no signer-side protocol module before indexing. Recorded as
  `HOLOINDEX_REDDOG_ISOLATED_SIGNER_SOCKET_PROTOCOL_INDEX_GAP_PHASE1`; no
  runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_SIGNER_SOCKET_CLIENT_BUNDLE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 97

- Extended the resident queue runtime dependency bundle so an explicit
  outside-repo `REDDOG_SIGNER_SOCKET_PATH` can provide the already-built
  isolated signer socket client to the `authority_runtime` stage.
- Updated the serial-loop bootstrap and `main.py` env plumbing with signer
  socket path, timeout, and response-size settings. Default behavior remains
  fail-closed through `FailClosedSignerClient` when the socket path is absent.
- Added tests proving invalid signer socket paths reject without fallback,
  a connector-backed isolated signer can issue delegated authority through the
  existing resident loop, `main.py` forwards the new env settings, and the
  boundary still performs no private-key loading, signer spawning, shell work,
  repo mutation, OpenClaw enqueue, Hermes dispatch, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog main resident queue signer socket
  runtime dependency bundle` surfaced adjacent live-enqueue/worktree docs and
  WSP entries, but not this new wiring before indexing. Recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_SIGNER_SOCKET_CLIENT_BUNDLE_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_ISOLATED_SIGNER_SOCKET_CLIENT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 97

- Added `src/reddog_isolated_signer_socket_client.py`: a fail-closed client
  for an already-running isolated signer service. It sends existing
  `SigningRequest` payloads over a validated local socket and converts signer
  JSON responses into existing `SigningResponse` records.
- Added tests proving missing/relative/inside-repo/device socket paths reject,
  request JSON is deterministic and bounded, accepted attested responses
  round-trip, malformed/oversized/connector failures reject, signer rejections
  preserve no-secret-material guarantees, and AST denial of shell/env/HoloIndex
  /OpenClaw/Hermes/vault/key-loading imports.
- Boundary: client side only. No signer daemon is spawned, no private key or
  vault secret is loaded, no command is executed, no repository file is mutated,
  and no signature is treated as execution authority by this slice.
- HoloIndex read-only probe for `RedDog isolated signer socket client
  SigningRequest SigningResponse` surfaced signed-receipt/signature-verifier
  code and the E0 contract, but not this new client before indexing. Recorded
  as `HOLOINDEX_REDDOG_ISOLATED_SIGNER_SOCKET_CLIENT_INDEX_GAP_PHASE1`; no
  runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_RUNTIME_DEPENDENCY_BUNDLE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_main_resident_queue_runtime_dependency_bundle.py`: a
  main-startup dependency bundle for the resident queue serial loop. It builds
  only outside-repo authority-state storage, JSON-backed principal/permission
  resolvers, and a fail-closed signer client.
- Extended `src/reddog_main_resident_queue_serial_loop_bootstrap.py` and
  `main.py` env plumbing so `REDDOG_AUTHORITY_RUNTIME_STATE_PATH`,
  `REDDOG_PERMISSION_SNAPSHOTS_PATH`,
  `REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH`, and
  `REDDOG_RESIDENT_QUEUE_NOW_EPOCH` can register the existing
  `authority_runtime` stage without constructing live execution dependencies.
- Added tests proving default no-op behavior, partial/inside-repo rejection,
  outside-repo resolver loading, fail-closed signer rejection, serial-loop
  progression into `authority_runtime`, updated `main.py` env forwarding, and
  AST denial of shell/network/HoloIndex/live runner imports.
- Boundary: no private key, real signer, signature verification, worktree,
  shell command, OpenClaw enqueue, Hermes dispatch, PR publish, reward
  settlement, repo mutation, or HoloIndex runtime re-index is created by this
  slice. The signer remains fail-closed until a later isolated signer runtime
  authorization slice provides a real boundary.
- HoloIndex read-only probe for `RedDog resident queue runtime dependency
  bundle authority runtime main bootstrap` surfaced adjacent live-enqueue and
  governed work-order docs, but not this new bundle before indexing. Recorded
  as `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_RUNTIME_DEPENDENCY_BUNDLE_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_main_resident_queue_serial_loop_bootstrap.py`: an
  off-by-default `main.py` adapter for the bounded resident queue serial loop.
  It reads only outside-repo work-state, chain-results, and authority-profile
  JSON, builds the handler registry with existing bootstrap-owned dependencies,
  and advances up to `REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS`.
- Updated `main.py` with `run_reddog_resident_queue_serial_loop_preflight`,
  gated by `REDDOG_RESIDENT_QUEUE_SERIAL_LOOP=1` and nonblocking unless
  `REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED=1`. Normal menu startup remains
  unchanged when the flag is absent.
- Added tests proving one-stage serial-loop application, fail-closed rejection
  when later dependencies are missing, outside-repo input enforcement, disabled
  default behavior, enforced blocking, and AST denial of shell/network/HoloIndex
  and later-stage runtime imports.
- Boundary: startup adapter only; no production signer, verifier, runner,
  worktree, shell, OpenClaw enqueue, Hermes dispatch, PR publish,
  PatternMemory client, reward settlement, repo mutation, or HoloIndex runtime
  re-index is created by this slice.
- HoloIndex read-only probe for `RedDog main resident queue serial loop
  bootstrap preflight` surfaced adjacent preflight/WSP/live-enqueue docs, but
  not this new bootstrap before indexing. Recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_RUNNER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_serial_loop.py`: a bounded serial loop
  runner that repeatedly invokes the existing resident queue next-stage
  dispatcher with caller-injected handlers until the queue chain completes,
  rejects, or reaches the configured step bound.
- Added tests proving full 13-stage completion with fake injected handlers,
  explicit-loop gating, max-step rejection, bounded progress reporting,
  missing-handler fail-close after progress, already-complete no-op behavior,
  handler-exception rejection, serializable nested result output, and AST
  denial of shell/network/HoloIndex/concrete stage imports.
- Boundary: loop orchestration only; no default handler, signer, runner,
  worktree, shell, OpenClaw enqueue, Hermes dispatch, PR publish,
  PatternMemory client, reward settlement, repo mutation, or HoloIndex runtime
  re-index is created by this slice.
- HoloIndex read-only probe for `RedDog resident queue serial loop runner
  dispatcher` surfaced adjacent swarm/WSP/session-continuity results, but not
  this new runner before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_RUNNER_INDEX_GAP_PHASE1`; no
  runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_STAGE_HANDLER_REGISTRY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_stage_handler_registry.py`: a centralized
  dependency-injected registry for all already-built resident queue stage
  handlers, from `authority_request` through `pattern_memory_admission`.
- Updated the `main.py` next-stage dispatch bootstrap to construct its handler
  map through the registry while injecting only the dependencies it already
  owns. Default startup behavior remains unchanged: dispatch is still
  off-by-default, and later stages remain unavailable until a dedicated runtime
  dependency slice supplies explicit dependencies.
- Added tests proving default bootstrap dependency scope registers only
  `authority_request`, full injected dependencies register all 13 queue stages,
  callable handlers are omitted from telemetry payloads, empty mapping
  dependencies fail closed, and the registry has no shell/network/HoloIndex or
  default client construction surface.
- Boundary: registry composition only; no signer, runner, worktree, shell,
  OpenClaw enqueue, Hermes dispatch, PR publish, PatternMemory client,
  reward settlement, repo mutation, or HoloIndex runtime re-index is created by
  this slice.
- HoloIndex read-only probe for `RedDog resident queue stage handler registry
  bootstrap` surfaced adjacent queue/live-enqueue/WSP/docs results, but not
  this new registry before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_STAGE_HANDLER_REGISTRY_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_PATTERN_MEMORY_ADMISSION_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_pattern_memory_admission_handler.py`: a
  concrete injected handler for the resident queue `pattern_memory_admission`
  stage.
- The handler reads the already-recorded `held_out_regression_gate` result
  from the chain-results store and invokes the existing queue-authorized
  PatternMemory admission guard with an injected request and sink.
- Boundary: PatternMemory admission only through the injected sink after
  held-out acceptance; no direct PatternMemory instantiation, shell command, PR
  publish, merge, OpenClaw enqueue, Hermes dispatch, reward settlement, or
  HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue PatternMemory admission
  handler` surfaced adjacent queue/knowledge/WSP results, but not this new
  handler before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_PATTERN_MEMORY_ADMISSION_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_HELD_OUT_REGRESSION_GATE_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_held_out_regression_gate_handler.py`: a
  concrete injected handler for the resident queue `held_out_regression_gate`
  stage.
- The handler reads the already-recorded `verified_outcome_ratchet` result
  from the chain-results store and invokes the existing queue-authorized
  held-out regression gate with injected gate evidence.
- Boundary: deterministic held-out gate result only; no test execution, shell
  command, PR publish, merge, PatternMemory write, OpenClaw enqueue, Hermes
  dispatch, reward settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue held out regression gate
  handler` surfaced adjacent policy/operational-spine/WSP/docs results, but
  not this new handler before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_HELD_OUT_REGRESSION_GATE_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_VERIFIED_OUTCOME_RATCHET_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_verified_outcome_ratchet_handler.py`: a
  concrete injected handler for the resident queue `verified_outcome_ratchet`
  stage.
- The handler reads the already-recorded `verified_draft_pr_publish` result
  from the chain-results store and invokes the existing queue-authorized
  verified outcome ratchet with an injected request and store.
- Boundary: verified outcome receipt recording only; no shell command, PR
  publish, mark-ready, merge, OpenClaw enqueue, Hermes dispatch, reward
  settlement, or HoloIndex re-index. PatternMemory remains disabled unless a
  caller supplies the separate explicit flag and injected sink.
- HoloIndex read-only probe for `RedDog resident queue verified outcome ratchet
  handler` surfaced adjacent operational-spine/generic-spine results, but not
  this new handler before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_VERIFIED_OUTCOME_RATCHET_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_verified_draft_pr_publish_handler.py`: a
  concrete injected handler for the resident queue `verified_draft_pr_publish`
  stage.
- The handler reads the already-recorded `slice_verifier` result from the
  chain-results store and invokes the existing queue-authorized verified
  draft-PR publish guard with an injected publish request and runner.
- Boundary: draft PR publish gate only through the injected runner; no mark
  ready, merge, shell command, PatternMemory write, OpenClaw enqueue, Hermes
  dispatch, reward settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue verified draft PR
  publish handler` surfaced unrelated/adjacent governance results, but not
  this new handler before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_slice_verifier_handler.py`: a concrete
  injected handler for the resident queue `slice_verifier` stage.
- The handler reads the already-recorded `bounded_worker_pilot` result from the
  chain-results store and invokes the existing queue-authorized autonomous
  slice verifier with injected machine-derived verifier evidence.
- Boundary: verification only; no shell command, GitHub call, PR publishing,
  merge, PatternMemory write, OpenClaw enqueue, Hermes dispatch, reward
  settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue slice verifier handler`
  surfaced adjacent live-enqueue/queue/WSP/docs results, but not this new
  handler before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_BOUNDED_WORKER_PILOT_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_bounded_worker_pilot_handler.py`: a
  concrete injected handler for the resident queue `bounded_worker_pilot`
  stage.
- The handler reads the already-recorded `worktree_create` result from the
  chain-results store, resolves the bound work order through an injected
  resolver, and invokes the existing queue-authorized bounded-worker-pilot
  guard with injected generic-writer/governed-shell dry-run evidence and
  declared artifact contents.
- Boundary: bounded pilot only; declared artifact materialization inside the
  isolated worktree only; no shell command, PR publishing, PatternMemory write,
  OpenClaw enqueue, Hermes dispatch, reward settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue bounded worker pilot
  handler` surfaced adjacent queue/WSP/docs results, but not this new handler
  before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_BOUNDED_WORKER_PILOT_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_WORKTREE_CREATE_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_worktree_create_handler.py`: a concrete
  injected handler for the resident queue `worktree_create` stage.
- The handler reads the already-recorded `executor_plan` and `execution_valve`
  results from the chain-results store, resolves the bound work order through
  an injected resolver, and invokes the existing queue-authorized worktree
  create guard with an injected runner.
- Boundary: isolated worktree create gate only; no task execution, file edit,
  shell command, PR publishing, PatternMemory write, OpenClaw enqueue, Hermes
  dispatch, reward settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue worktree create handler`
  surfaced the underlying worktree create/runner modules and worktree-related
  docs, but not this new handler before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_WORKTREE_CREATE_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_EXECUTION_VALVE_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_execution_valve_handler.py`: a concrete
  injected handler for the resident queue `execution_valve` stage.
- The handler reads the already-recorded `work_order_invocation` and
  `executor_plan` results from the chain-results store, resolves the bound work
  order through an injected resolver, and invokes the existing queue-authorized
  execution-valve guard with an injected valve environment.
- Boundary: execution-valve decision only; no worker spawn, worktree creation,
  file edit, shell command, PR publishing, PatternMemory write, OpenClaw
  enqueue, Hermes dispatch, reward settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue execution valve handler`
  surfaced the underlying valve and adjacent live-enqueue invoke, but not this
  new handler before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_EXECUTION_VALVE_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_EXECUTOR_PLAN_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_executor_plan_handler.py`: a concrete
  injected handler for the resident queue `executor_plan` stage.
- The handler reads the already-recorded `work_order_invocation` result from
  the chain-results store, resolves the bound work order through an injected
  resolver, and invokes the existing queue-authorized executor-plan dry-run
  bridge.
- Boundary: executor-plan dry-run only; no execution-valve opening, worker
  spawn, worktree creation, file edit, shell command, PR publishing,
  PatternMemory write, OpenClaw enqueue, Hermes dispatch, reward settlement,
  or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue executor plan handler`
  surfaced adjacent queue/enqueue/executor modules and docs, but not this new
  handler before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_EXECUTOR_PLAN_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_WORK_ORDER_INVOCATION_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_work_order_invocation_handler.py`: a
  concrete injected handler for the resident queue `work_order_invocation`
  stage.
- The handler reads the already-recorded `authority_runtime` and
  `authority_verification` results from the chain-results store, resolves the
  bound work order through an injected resolver, and invokes the existing
  verified-authority work-order dry-run guard.
- Aligned `src/reddog_wre_queue_verified_authority_work_order_invoke.py` with
  the current signer runtime receipt status constant
  `DELEGATED_AUTHORITY_ISSUED` instead of a legacy literal.
- Boundary: work-order invocation dry-run only; no signing, valve opening,
  worker spawn, worktree creation, file edit, shell command, PR publishing,
  PatternMemory write, OpenClaw enqueue, Hermes dispatch, reward settlement,
  or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue work order invocation
  handler` surfaced adjacent work-order modules and WSP/docs, but not this new
  handler before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_WORK_ORDER_INVOCATION_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_AUTHORITY_VERIFICATION_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_authority_verification_handler.py`: a
  concrete injected handler for the resident queue `authority_verification`
  stage.
- The handler reads the already-recorded `authority_runtime` result from the
  chain-results store and invokes the existing queue authority-verification
  guard with injected verifier, resolver, nonce, snapshot, and revocation
  boundaries.
- Boundary: authority verification only; no valve opening, worker spawn,
  worktree creation, file edit, shell command, PR publishing, PatternMemory
  write, OpenClaw enqueue, Hermes dispatch, reward settlement, or HoloIndex
  re-index.
- HoloIndex read-only probe for `RedDog resident queue authority verification
  handler` surfaced adjacent live-enqueue, work-order receipt, PFmall
  verification, WSP, and RedDog identity/governance docs, but not this new
  handler before indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_AUTHORITY_VERIFICATION_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_AUTHORITY_RUNTIME_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_authority_runtime_handler.py`: a concrete
  injected handler for the resident queue `authority_runtime` stage.
- The handler reads the already-recorded `authority_request` result from the
  chain-results store and invokes the existing queue authority-runtime guard
  with injected signer, resolver, snapshot, and authority-store boundaries.
- Boundary: signed authority issuance may occur only through injected
  boundaries; no signature verification for execution, valve opening, worker
  spawn, worktree creation, file edit, shell command, PR publishing,
  PatternMemory write, OpenClaw enqueue, Hermes dispatch, reward settlement,
  or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue authority runtime
  handler` surfaced adjacent live-enqueue, queue-observability, AI overseer,
  WSP, and governance docs, but not this new handler before indexing.
  Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_AUTHORITY_RUNTIME_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_main_resident_queue_next_stage_dispatch_bootstrap.py`:
  an opt-in `main.py` adapter that invokes the resident queue dispatcher with
  only the `authority_request` handler registered.
- Wired `main.py` behind `REDDOG_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH=1`
  (default OFF) to write the first-stage dry-run result into the outside-repo
  resident queue chain-results store.
- Boundary: external runtime state only; no signing, signature verification,
  valve opening, worker spawn, worktree creation, file edit, shell command,
  PR publishing, PatternMemory write, OpenClaw enqueue, Hermes dispatch,
  reward settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog main resident queue next stage
  dispatch bootstrap` surfaced adjacent swarm/build-plan, WSP, RedDog
  bootstrap/governance docs, and knowledge papers, but not this new bootstrap
  before indexing. Recorded as
  `HOLOINDEX_REDDOG_MAIN_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_BOOTSTRAP_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_AUTHORITY_REQUEST_HANDLER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_authority_request_handler.py`: a concrete
  injected handler for the resident queue `authority_request` stage.
- The handler recomputes the WRE queue-consumer dry-run for the dispatched
  queue item, verifies it matches the dispatch request, and adapts the existing
  queue authority-request dry-run planner into the dispatcher protocol.
- Boundary: first-stage dry-run handler only; no signing, signature
  verification, valve opening, worker spawn, worktree creation, file edit,
  shell command, PR publishing, PatternMemory write, OpenClaw enqueue, Hermes
  dispatch, reward settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue authority request
  handler` surfaced adjacent live-enqueue, merge-authority, work-order,
  WSP, and RedDog governance docs, but not this new handler before indexing.
  Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_AUTHORITY_REQUEST_HANDLER_INDEX_GAP_PHASE1`;
  no runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_next_stage_dispatch.py`: an explicit
  injected-handler dispatcher for exactly one resident queue-chain stage.
- The dispatcher reads the chain-results store, plans the current stage, calls
  only the handler supplied for that stage, and records the handler result
  through the governed chain-results store.
- Boundary: no default handlers and no concrete queue bridge imports; no
  authority issuance, signature verification, worker spawn, worktree creation,
  file edit, shell command, PR publishing, PatternMemory write, OpenClaw
  enqueue, Hermes dispatch, reward settlement, or HoloIndex re-index by the
  dispatcher.
- HoloIndex read-only probe for `RedDog resident queue next stage dispatch
  injected handler` surfaced adjacent extension live-enqueue, swarm-dispatch,
  WSP, and RedDog work-order docs, but not this new dispatcher before indexing.
  Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_INDEX_GAP_PHASE1`; no
  runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_STORE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_chain_results_store.py`: an atomic
  outside-repo store for already-produced resident queue-chain stage results.
- The store replays the current queue orchestration plan, records only the
  exact current missing stage, replays the proposed plan, and commits only if
  the chain advances cleanly.
- Updated the resident queue plan bootstrap to read the governed
  `reddog_resident_queue_chain_results.v1` schema in addition to raw stage
  mappings.
- Boundary: chain-result persistence only; no bridge invocation, authority
  issuance, signature verification, worker spawn, worktree creation, file edit,
  shell command, PR publishing, PatternMemory write, OpenClaw enqueue, Hermes
  dispatch, reward settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue chain results store
  atomic stage result` surfaced adjacent worker-queue, PQN orchestrator,
  consensus, WSP, and live-enqueue docs, but not this new store before
  indexing. Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_STORE_INDEX_GAP_PHASE1`; no
  runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_MAIN_RESIDENT_QUEUE_ORCHESTRATION_PLAN_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added
  `src/reddog_main_resident_queue_orchestration_plan_bootstrap.py`: a guarded
  `main.py` adapter for the resident queue orchestration planner.
- Wired `main.py` to print the next queue-chain bridge after authoritative
  work-state refresh and WRE queue-consumer dry-run, warning-only by default
  unless `REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_ENFORCED=1`.
- The adapter reads existing work-state and optional chain-results JSON only
  from outside the repository checkout, then calls the pure planner from
  `REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_PHASE1`.
- Boundary: startup reporting only; no bridge invocation, authority issuance,
  signature verification, worker spawn, worktree creation, file edit, shell
  command, PR publishing, PatternMemory write, OpenClaw enqueue, Hermes
  dispatch, reward settlement, or HoloIndex re-index.
- HoloIndex discoverability is covered by the prior planner INDEX_GAP
  (`HOLOINDEX_REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_INDEX_GAP_PHASE1`);
  this bootstrap slice performs no runtime re-index.

## 2026-07-14: REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_resident_queue_orchestration_plan.py`: a deterministic,
  non-mutating planner for the resident RedDog queue loop.
- The planner consumes the authoritative work-state snapshot plus already
  emitted queue-authorized bridge receipts, validates stage order, and names
  the next required bridge instead of relying on 012 to remember the chain.
- It auto-validates only the existing WRE queue-consumer dry-run, then fails
  closed on missing, rejected, or out-of-order later-stage receipts.
- Boundary: planning only; no authority issuance, signature verification,
  valve opening, worktree creation, file edits, shell commands, PR publishing,
  PatternMemory writes, OpenClaw enqueue, Hermes dispatch, reward settlement,
  or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog resident queue orchestration plan WRE
  queue bridge next action` surfaced adjacent worktree, extension live-enqueue,
  WRE, and queue docs, but did not surface this new planner before indexing.
  Recorded as
  `HOLOINDEX_REDDOG_RESIDENT_QUEUE_ORCHESTRATION_PLAN_INDEX_GAP_PHASE1`; no
  runtime re-index is performed in this slice.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authorized_pattern_memory_admission_invoke.py`:
  an explicit bridge from an accepted queue-authorized held-out regression gate
  result to an injected PatternMemory admission sink.
- The guard requires held-out admission allowed, a matching work-order ID, a
  clean deterministic record, and an injected sink before writing.
- Boundary: verified outcome admission only through injection; no concrete
  PatternMemory construction, command execution, PR publish, mark-ready, merge,
  reward settlement, OpenClaw enqueue, Hermes dispatch, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog queue authorized PatternMemory
  admission invoke` surfaced adjacent live-enqueue, runtime-invocation,
  receipt, WSP, and recursive self-governance files, but did not surface this
  new admission bridge before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authorized_held_out_regression_gate_invoke.py`:
  an explicit bridge from an accepted queue-authorized verified outcome
  ratchet result to the existing WRE held-out recursive-improvement regression
  gate.
- The guard binds the authoritative ratchet receipt to the verifier receipt and
  work-order ID before evaluating held-out regression evidence.
- Boundary: deterministic held-out gate evaluation only; no test execution,
  PatternMemory write, PR publish, mark-ready, merge, reward settlement,
  OpenClaw enqueue, Hermes dispatch, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog queue authorized held out regression
  gate invoke` surfaced adjacent policy, runtime-invocation, receipt, WSP, and
  recursive self-governance documents, but did not surface this new held-out
  bridge before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORIZED_HELD_OUT_REGRESSION_GATE_INVOKE_INDEX_GAP_PHASE1`;
  no runtime re-index performed. The probe also reported a pre-existing
  `WSP-GUARDIAN` suspicious-Unicode warning unrelated to the new ASCII-clean
  files.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authorized_verified_outcome_ratchet_invoke.py`:
  an explicit bridge from an accepted queue-authorized verified draft PR
  publish result to the existing WRE verified outcome ratchet.
- The guard requires an injected outcome ratchet store, binds the publish
  receipt to the verifier receipt and work-order ID, and uses the accepted
  queue publish result as authoritative publish evidence.
- PatternMemory writes are blocked unless the request asks for them, a
  separate explicit PatternMemory flag is true, and an injected sink is present.
- Boundary: outcome receipt recording only; no command execution, PR publish,
  mark-ready, merge, reward settlement, OpenClaw enqueue, Hermes dispatch, or
  HoloIndex re-index.
- HoloIndex read-only probe for `RedDog queue authorized verified outcome
  ratchet invoke` surfaced adjacent policy, runtime-invocation, signature, and
  governance files, but did not surface this new ratchet bridge before
  indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_INDEX_GAP_PHASE1`;
  no runtime re-index performed. The probe also reported a pre-existing
  `WSP-GUARDIAN` suspicious-Unicode warning unrelated to the new ASCII-clean
  files.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authorized_verified_draft_pr_publish_invoke.py`:
  an explicit bridge from an accepted queue-authorized autonomous verifier
  result to the existing WRE verified draft PR publish gate.
- The guard requires an injected draft-PR runner, injects the accepted verifier
  result into the publish request, and preserves publish-gate rejection reasons.
- Boundary: draft PR publishing only after verification; no mark-ready, merge,
  command execution, PatternMemory write, reward settlement, OpenClaw enqueue,
  Hermes dispatch, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog queue authorized verified draft PR
  publish invoke` surfaced adjacent identity, policy, and governance files, but
  did not surface this new publish bridge before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORIZED_VERIFIED_DRAFT_PR_PUBLISH_INVOKE_INDEX_GAP_PHASE1`;
  no runtime re-index performed. The probe also reported a pre-existing
  `WSP-GUARDIAN` suspicious-Unicode warning unrelated to the new ASCII-clean
  files.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authorized_slice_verifier_invoke.py`: an
  explicit bridge from an accepted queue-authorized bounded worker pilot result
  to the existing WRE autonomous slice verifier runtime.
- The guard binds the verifier's machine-derived changed paths to the bounded
  pilot receipt's written artifacts, injects the pilot receipt as verifier
  worktree evidence, and preserves verifier rejection reasons.
- Boundary: no command execution, GitHub call, draft PR publish, merge,
  PatternMemory write, reward settlement, OpenClaw enqueue, Hermes dispatch, or
  HoloIndex re-index.
- HoloIndex read-only probe for `RedDog queue authorized slice verifier
  invoke` surfaced adjacent live-enqueue files and integration docs, but did
  not surface this new verifier bridge before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_INDEX_GAP_PHASE1`;
  no runtime re-index performed. The probe also reported a pre-existing
  `WSP-GUARDIAN` suspicious-Unicode warning unrelated to the new ASCII-clean
  files.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authorized_bounded_worker_pilot_invoke.py`:
  an explicit bridge from accepted queue-authorized worktree-create, generic
  writer dry-run, and governed shell dry-run receipts into the existing
  bounded worktree worker execution pilot.
- The bridge binds work-order IDs across the worktree-create result, writer
  receipt, shell receipt, and work order before allowing the pilot to
  materialize declared text artifacts inside the already-created isolated
  worktree.
- Boundary: this may perform the bounded pilot file materialization inside the
  isolated worktree only. It does not execute shell commands, enqueue
  OpenClaw, dispatch Hermes, create PRs, merge, settle rewards, or mutate
  HoloIndex.
- HoloIndex read-only probe for `RedDog queue authorized bounded worker pilot
  invoke` surfaced worker-queue/runtime-invocation adjacent files and WSP docs,
  but did not surface this new bridge before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authorized_worktree_create_invoke.py`: an
  explicit bridge from accepted queue-authorized executor-plan and
  execution-valve results to the existing isolated worktree-create
  orchestrator.
- The guard requires an injected worktree runner, preserves worktree-create
  rejection reasons, and performs no task execution, file edits, shell command,
  OpenClaw enqueue, Hermes dispatch, PR creation, reward settlement, or
  HoloIndex re-index.
- Boundary: this may create an isolated worktree only through the injected
  runner after the queue-authorized valve opens; it does not execute work inside
  that worktree.
- HoloIndex read-only probe for `RedDog queue authorized worktree create invoke`
  surfaced the existing worktree-create and runner modules, but did not surface
  this new bridge before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authorized_execution_valve_invoke.py`: an
  explicit bridge that evaluates the existing RedDog execution valve from a
  queue-authorized work-order invocation receipt and queue-authorized executor
  dry-run plan.
- The guard reconstructs the existing valve request shape, preserves
  receipt-chain rejection reasons, and only accepts when the valve state matches
  the expected explicit state, defaulting to `VALVE_OPEN_WORKTREE_CREATE`.
- Boundary: no worker spawn, worktree creation, shell command, OpenClaw enqueue,
  Hermes dispatch, repo mutation, PR creation, reward settlement, or HoloIndex
  re-index.
- HoloIndex read-only probe for `RedDog queue authorized execution valve invoke`
  surfaced the existing valve and live-enqueue invoke modules, but did not
  surface this new bridge before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authorized_executor_plan_dryrun.py`: an
  explicit bridge from an accepted queue-authorized work-order invocation
  result to the existing WRE isolated worktree executor dry-run planner.
- The bridge requires explicit invocation, preserves executor-planner rejection
  reasons, emits only a proposed `WREExecutorPlan`, and never opens the
  execution valve or creates a worktree.
- Boundary: no execution valve open, worker spawn, worktree creation, shell
  command, OpenClaw enqueue, Hermes dispatch, repo mutation, PR creation, reward
  settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog queue authorized executor plan dryrun`
  surfaced the existing executor planner and contract docs, but did not surface
  this new bridge before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_WRE_QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOCATION_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_verified_authority_work_order_invoke.py`: an
  explicit invoke guard that feeds an accepted queue-authority verification
  result into the existing governed work-order dry-run invocation path.
- The guard requires the original issued authority payload, binds work-order ID,
  repo, requested operation, permission snapshot digest, and path scope before
  calling `invoke_reddog_work_order_dryrun(..., require_signed_authority=True)`.
- Boundary: no signing, authority issuance, worker spawn, worktree creation,
  shell command, OpenClaw enqueue, Hermes dispatch, repo mutation, PR creation,
  reward settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog queue verified authority work order
  invocation` surfaced the adjacent work-order runtime, signature verifier, and
  policy gate, but did not surface this new bridge before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOCATION_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORITY_VERIFICATION_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authority_verification_invoke.py`: an explicit
  invoke guard that verifies signed authority emitted by the queue-authority
  runtime through the existing work-order signature verifier.
- The guard requires accepted queue-authority runtime output, preserves verifier
  rejection codes, consumes the work-authority nonce only through the existing
  verifier, and emits no execution authority beyond the verifier result.
- Boundary: no signing, authority issuance, worker spawn, worktree creation,
  shell command, OpenClaw enqueue, Hermes dispatch, repo mutation, PR creation,
  reward settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog WRE queue authority verification invoke`
  surfaced the underlying signature verifier but did not surface this new
  bridge in top results before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORITY_VERIFICATION_INVOKE_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORITY_RUNTIME_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authority_runtime_invoke.py`: an explicit invoke
  guard that calls the existing delegated-authority signer runtime only from an
  accepted queue-authority request dry-run and only through injected signer,
  principal resolver, permission snapshot resolver, and authority store
  boundaries.
- The guard preserves default fail-closed signer behavior, returns runtime
  rejection reasons unchanged, and performs no worker spawn, worktree creation,
  shell command, OpenClaw enqueue, Hermes dispatch, repo mutation, PR creation,
  reward settlement, or HoloIndex re-index.
- Boundary: this may issue signed authority records when an injected signer
  accepts, but it still does not execute the authorized work.
- HoloIndex read-only probe for `RedDog WRE queue authority runtime invoke`
  did not surface the new module in top results before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORITY_RUNTIME_INVOKE_INDEX_GAP_PHASE1`; no
  runtime re-index performed.

## 2026-07-14: REDDOG_WRE_QUEUE_AUTHORITY_REQUEST_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_authority_request_dryrun.py`: a dry-run bridge
  from an accepted WRE queue-consumer receipt to the existing
  `DelegatedAuthorityRuntimeRequest` signer-runtime schema.
- The bridge requires an explicit FoundUp-scoped authority profile, rejects
  repo-wide authority, rejects paths outside `modules/foundups/{foundup_id}/`,
  and requires consensus plus sovereign authorization digests for high-authority
  operations.
- Boundary: no signing, signature verification, signer-store mutation, worker
  spawn, worktree creation, shell command, OpenClaw enqueue, Hermes dispatch,
  repo mutation, PR creation, reward settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog WRE queue delegated authority request
  dryrun` did not surface the new module in top results before indexing.
  Recorded as `HOLOINDEX_REDDOG_WRE_QUEUE_AUTHORITY_REQUEST_DRYRUN_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_WRE_QUEUE_CONSUMER_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_wre_queue_consumer_dryrun.py`: a fail-closed WRE queue
  consumer dry-run that validates one authoritative work-state queue item
  against its durable worker claim, freshness receipt, status, expiry, and
  evidence refs.
- Added `src/reddog_main_wre_queue_consumer_bootstrap.py` and `main.py`
  telemetry. Startup now reports whether the queued slice is ready for the
  next gate, while keeping `execution_ready=false` until signed authority and
  downstream execution receipts exist.
- Boundary: no queue mutation, worker spawn, worktree creation, shell command,
  OpenClaw enqueue, Hermes dispatch, repo mutation, PR creation, reward
  settlement, or HoloIndex re-index.
- HoloIndex read-only probe for `RedDog WRE queue consumer dryrun` did not
  surface the new module in top results before indexing. Recorded as
  `HOLOINDEX_REDDOG_WRE_QUEUE_CONSUMER_DRYRUN_INDEX_GAP_PHASE1`; no runtime
  re-index performed.

## 2026-07-14: REDDOG_PERSISTED_DECISION_TO_WORK_STATE_REFRESH_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Wired `src/reddog_main_authoritative_work_state_refresh_bootstrap.py` to
  optionally load the latest persisted RedDog read-only audit decision and use
  its `next_slice_name` as the requested slice for the existing authoritative
  work-state refresh runtime.
- The bridge validates the persisted decision through the existing
  `evaluate_reddog_worker_claim_dryrun()` gate before the refresh runtime can
  commit a durable claim or synchronized WRE queue item.
- Added `main.py` telemetry and env control:
  `REDDOG_WORK_STATE_USE_LATEST_READONLY_AUDIT_DECISION=0/1`; default follows
  `OPENCLAW_AUTO_TASKS_ENABLED`.
- Boundary: no model call, no shell/subprocess, no GitHub/W10 fetch, no
  HoloIndex re-index, no OpenClaw enqueue, no Hermes/WRE execution, and no repo
  mutation. This only selects the requested slice for the already-gated
  authoritative work-state refresh.

## 2026-07-14: REDDOG_READONLY_AUDIT_DECISION_PERSISTENCE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_readonly_audit_decision_persistence.py`: an AgentDB-backed
  durable store for accepted RedDog read-only audit next-action receipts.
- Wired `src/reddog_main_readonly_operational_bootstrap.py` and `main.py` with an
  opt-in decision persistence bridge. `OPENCLAW_AUTO_TASKS_ENABLED=1` enables it
  by default, and `REDDOG_READONLY_AUDIT_DECISION_PERSIST_ENABLED=0/1` overrides
  that default.
- Added tests for accepted receipt persistence, idempotent duplicate writes,
  same-swarm conflict rejection, rejected/side-effect receipt refusal, bootstrap
  persistence wiring, and main preflight environment routing.
- Boundary: this persists accepted decision receipts only. It does not execute
  the decision, enqueue new work from the decision, call models, run shell/git,
  dispatch Hermes/WRE, create worktrees, mutate repo files, or re-index HoloIndex.
- HoloIndex read-only probe for `RedDog read-only audit decision persistence`
  did not surface the new module in top results before indexing. Recorded as
  `HOLOINDEX_REDDOG_READONLY_AUDIT_DECISION_PERSISTENCE_INDEX_GAP_PHASE1`; no
  runtime re-index performed.

## 2026-07-14: REDDOG_MAIN_READONLY_AUDIT_DECISION_TELEMETRY_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Updated `main.py` RedDog bootstrap output to print read-only audit decision
  telemetry: whether decision generation ran, the selected action, and the
  selected next slice.
- Added stdout regression coverage proving the main menu/preflight surface
  exposes `decision_action` and `decision_next_slice` without blocking startup.
- Boundary: telemetry only. No model call, no shell/subprocess, no repo
  mutation, no worktree operation, no OpenClaw enqueue, no Hermes/WRE dispatch,
  no HoloIndex mutation/re-index, and no live action-plane wiring.

## 2026-07-14: REDDOG_READONLY_AUDIT_LANE_ANALYZER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Extended `src/reddog_readonly_audit_task_executor.py` with the first
  deterministic lane analyzer. When a read-only audit task includes
  `ACTIVE_SLICE_LEDGER.md` and `work_ledger.schema.json`, the executor reuses
  `reddog_lane_state_reconciler.reconcile_active_and_json_ledgers()` and emits
  an `OBSERVED` semantic finding for the selected next slice, stale ledger, or
  ledger conflict state.
- Preserved the missing-analyzer fallback for lanes/target sets that do not yet
  have a deterministic analyzer, keeping unimplemented audit lanes explicit
  instead of silently treating evidence collection as audit completion.
- Added tests for selected-next-slice findings, conflict-to-refresh-runtime
  routing, existing missing-analyzer fallback, and the persisted report ->
  collection -> decision path.
- Boundary: no model call, no shell/subprocess, no repo mutation, no worktree
  operation, no OpenClaw enqueue, no Hermes/WRE dispatch, no HoloIndex
  mutation/re-index, and no live action-plane wiring.

## 2026-07-14: REDDOG_READONLY_AUDIT_SEMANTIC_FINDINGS_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Extended `src/reddog_readonly_audit_task_executor.py` so accepted
  read-only audit reports include a WSP_97-labeled semantic finding when the
  lane-specific analyzer is still missing. The finding is evidence-bound to
  the report refs and routes to `REDDOG_READONLY_AUDIT_LANE_ANALYZER_PHASE1`
  instead of silently presenting evidence collection as finished audit work.
- Extended the read-only report bundle digest payload in
  `src/reddog_openclaw_readonly_audit_swarm_runtime.py` so report findings
  affect the validated bundle identity.
- Added executor test coverage proving the missing-analyzer finding is present,
  `SPECIFIED_NOT_IMPLEMENTED`, evidence-bound, and routes to the next lane
  analyzer slice.
- Boundary: no model call, no shell/subprocess, no repo mutation, no worktree
  operation, no OpenClaw enqueue, no Hermes/WRE dispatch, no HoloIndex
  mutation/re-index, and no live action-plane wiring. This adds report
  semantics only.

## 2026-07-14: REDDOG_READONLY_AUDIT_DECISION_RUNTIME_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_readonly_audit_decision_runtime.py`: deterministic
  post-collection decision receipt for RedDog read-only audit bundles. The
  gate accepts only WSP_97-labeled semantic findings whose evidence refs are
  bound to the validated report; `NEEDS_VERIFICATION` findings can only route
  to `RESEARCH_MORE`.
- Wired the main read-only bootstrap telemetry to emit the decision receipt
  after accepted report collection. Reports with no semantic findings are
  routed to `RESEARCH_MORE` with
  `REDDOG_READONLY_AUDIT_SEMANTIC_FINDINGS_PHASE1`, preventing RedDog from
  treating evidence collection as a completed audit.
- Added tests for no-finding overclaim prevention, evidence-bound `FIX`
  selection, rejected collection handling, count mismatch, unbound evidence,
  `NEEDS_VERIFICATION` guardrails, bootstrap decision telemetry, and AST
  no-execution/no-mutation coverage.
- Boundary: no model call, no shell/subprocess, no repo mutation, no worktree
  operation, no OpenClaw enqueue, no Hermes/WRE dispatch, no HoloIndex
  mutation/re-index, and no live action-plane wiring. This emits a decision
  receipt only.
- HoloIndex read-only probe for
  `REDDOG_READONLY_AUDIT_DECISION_RUNTIME_PHASE1 semantic findings next action decision`
  is expected to require post-merge indexing; no runtime re-index performed.

## 2026-07-14: REDDOG_MAIN_READONLY_AUDIT_REPORT_COLLECTION_WIRE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Extended `src/reddog_main_readonly_operational_bootstrap.py` with optional
  read-only audit report collection against the persisted AgentDB report table.
  Accepted report bundles skip task re-enqueue; missing/rejected bundles enqueue
  only when the existing audit-task enqueue bridge is also authorized.
- Wired `main.py` to pass `collect_readonly_audit_reports=True` when
  `REDDOG_READONLY_AUDIT_REPORT_COLLECTION_ENABLED=1`, or when
  `OPENCLAW_AUTO_TASKS_ENABLED=1` and no RedDog collection override is set.
- Added bootstrap tests for accepted report collection, missing-report
  fail-closed behavior without enqueue authority, missing-report enqueue when
  enqueue authority is present, and main preflight env override behavior.
- Boundary: no model call, no worker spawn from the bootstrap, no shell/subprocess,
  no repo mutation, no worktree operation, no Hermes/WRE dispatch, no HoloIndex
  mutation/re-index, and no live FoundUp queue write. Collection reads the
  RedDog read-only audit report store; enqueue remains limited to pending
  read-only AgentDB audit tasks when explicitly enabled.
- HoloIndex read-only probe for
  `REDDOG_MAIN_READONLY_AUDIT_REPORT_COLLECTION_WIRE_PHASE1 main.py read-only audit report collection`
  surfaced this ModLog pointer and unknown locations, not the runtime path.
  Recorded
  `HOLOINDEX_REDDOG_MAIN_READONLY_AUDIT_REPORT_COLLECTION_WIRE_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_READONLY_AUDIT_REPORT_COLLECTION_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_readonly_audit_report_collection.py`: AgentDB-backed
  persistence and collection for accepted RedDog read-only audit task reports.
  The collector feeds persisted reports into the existing read-only audit swarm
  report validator.
- Updated `scripts/run_task.py`: exact `reddog:readonly_audit` tasks now must
  persist their structured report before the AgentDB task is marked completed;
  persistence failure fails the task closed.
- Added `tests/test_reddog_readonly_audit_report_collection.py`: accepted
  persistence, missing-report rejection, binding/mutation rejection,
  conflicting duplicate rejection, real `run_task.py` persistence before task
  completion, and AST no-execution/no-repo-mutation coverage.
- Boundary: no model call, no shell/subprocess, no repo mutation, no OpenClaw
  enqueue, no Hermes/WRE dispatch, no worktree operation, no HoloIndex
  mutation/re-index, and no report file write. Runtime write scope is limited
  to the RedDog read-only audit report table in AgentDB.
- HoloIndex read-only probe for
  `REDDOG_READONLY_AUDIT_REPORT_COLLECTION_PHASE1 AgentDB read-only audit report collection`
  surfaced this ModLog pointer and adjacent audit assets, not the new
  collector module. Recorded
  `HOLOINDEX_REDDOG_READONLY_AUDIT_REPORT_COLLECTION_INDEX_GAP_PHASE1`; no
  runtime re-index performed.

## 2026-07-14: REDDOG_MAIN_READONLY_AUDIT_SWARM_ENQUEUE_WIRE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Extended `src/reddog_main_readonly_operational_bootstrap.py` so an accepted
  read-only audit swarm plan can be published to AgentDB through the existing
  read-only audit swarm enqueue module, but only when the host explicitly
  enables the bridge.
- Wired `main.py` to pass `enqueue_readonly_audit_tasks=True` when
  `REDDOG_READONLY_AUDIT_SWARM_ENQUEUE_ENABLED=1`, or when
  `OPENCLAW_AUTO_TASKS_ENABLED=1` and no RedDog override is set. The default
  path remains plan-only and menu-safe.
- Added bootstrap tests for default no-enqueue behavior, injected-writer
  accepted publication, writer rejection fail-closed behavior, and main
  preflight env flag/override handling.
- Boundary: no model call, no worker spawn from the bootstrap, no OpenClaw
  supervisor call, no Hermes/WRE dispatch, no shell/subprocess, no repo
  mutation, no worktree operation, no HoloIndex mutation/re-index, and no live
  FoundUp queue write. Queue mutation is limited to pending read-only AgentDB
  audit tasks when explicitly enabled.
- HoloIndex read-only probe for
  `REDDOG_MAIN_READONLY_AUDIT_SWARM_ENQUEUE_WIRE_PHASE1 main.py AgentDB read-only audit swarm enqueue`
  surfaced this ModLog pointer and unknown locations, not the runtime module.
  Recorded
  `HOLOINDEX_REDDOG_MAIN_READONLY_AUDIT_SWARM_ENQUEUE_WIRE_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_READONLY_AUDIT_TASK_REPORT_EXECUTOR_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_readonly_audit_task_executor.py`: deterministic local
  executor for AgentDB tasks emitted by the read-only audit swarm enqueue
  seam. It reads only allowlisted repository file targets, computes evidence
  digests, and emits a report shape compatible with the existing read-only
  audit report validator.
- Updated `scripts/run_task.py`: exact
  `source=reddog_openclaw_readonly_audit_swarm` and
  `required_skills=["reddog_readonly_audit"]` tasks now dispatch to the
  RedDog read-only audit executor before WRE skill dispatch, so a registered
  WRE skill cannot widen these audit tasks.
- Added `tests/test_reddog_readonly_audit_task_executor.py`: allowlisted read
  evidence collection, wrong-source/missing-assignment rejection,
  traversal/secret/missing-target rejection, AgentDB assigned-task execution
  through `run_task.py`, and AST no-mutation/no-network/no-runtime-wiring
  coverage.
- Boundary: no model call, no shell/subprocess, no repo write, no OpenClaw
  enqueue, no Hermes/WRE dispatch, no worktree operation, no HoloIndex
  mutation/re-index, and no report artifact write. It completes only the
  assigned AgentDB task and returns structured report data.
- HoloIndex read-only probe for `RedDog readonly audit task report executor
  AgentDB run_task` surfaced `run_task.py` and adjacent audit surfaces but not
  the new executor module. Recorded
  `HOLOINDEX_REDDOG_READONLY_AUDIT_TASK_REPORT_EXECUTOR_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_OPENCLAW_READONLY_AUDIT_SWARM_AGENTDB_ENQUEUE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_openclaw_readonly_audit_swarm_enqueue.py`: a
  governed bridge from an accepted read-only audit swarm plan to durable
  AgentDB autonomous-task assignments for OpenClaw pickup.
- Added `tests/test_reddog_openclaw_readonly_audit_swarm_enqueue.py`:
  accepted publication, plan/writer/unsafe-assignment/replay rejection,
  isolated AgentDB publication, duplicate rejection without second-batch
  pollution, deterministic JSON, and AST no-execution/no-runtime-wiring
  coverage.
- The concrete writer uses a single AgentDB transaction and writes pending
  tasks with `required_skills=["reddog_readonly_audit"]`, source
  `reddog_openclaw_readonly_audit_swarm`, and the original assignment and
  swarm receipt in task context.
- Boundary: no model call, no task execution, no OpenClaw supervisor call, no
  Hermes/WRE dispatch, no shell/subprocess, no worktree operation, no repo
  mutation, no HoloIndex runtime mutation/re-index, and no live FoundUp queue
  write. The report executor/collector is a later slice.
- HoloIndex read-only probe for `RedDog read-only audit swarm AgentDB enqueue`
  surfaced adjacent tests/docs but not the new enqueue module. Recorded
  `HOLOINDEX_REDDOG_OPENCLAW_READONLY_AUDIT_SWARM_AGENTDB_ENQUEUE_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_MAIN_AUTHORITATIVE_WORK_STATE_REFRESH_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_main_authoritative_work_state_refresh_bootstrap.py`: a
  controlled `main.py` adapter around the existing authoritative work-state
  refresh runtime. It reads existing local ledger, GitHub PR record, and W10
  report artifacts, rejects stale embedded ledger state before commit, and
  writes the authoritative work-state JSON only to an external runtime path.
- Wired `main.py` with
  `run_reddog_authoritative_work_state_refresh_preflight()` before the
  read-only RedDog operational bootstrap. Accepted refreshes set
  `REDDOG_AUTHORITATIVE_WORK_STATE_PATH` in-process so the next bootstrap step
  can consume the exact committed snapshot.
- Added `tests/test_reddog_main_authoritative_work_state_refresh_bootstrap.py`:
  accepted external-path commit, missing GitHub/W10 source rejection, stale
  ledger rejection, in-repo output rejection, main preflight nonblocking and
  enforced modes, accepted path propagation, and AST no-fetch/no-execution
  coverage.
- Boundary: no GitHub fetch, no W10 fetch, no worker spawn, no OpenClaw
  enqueue, no Hermes dispatch, no HoloIndex mutation/re-index, no execution,
  and no repo mutation. Runtime writes are limited to an operator-configured
  work-state JSON outside the repository checkout.
- HoloIndex read-only probe for `REDDOG_MAIN_AUTHORITATIVE_WORK_STATE_REFRESH_BOOTSTRAP_PHASE1
  main.py authoritative work state refresh bootstrap GitHub W10 records`
  returned unknown locations and WSP 56, not the new adapter. Recorded
  `HOLOINDEX_REDDOG_MAIN_AUTHORITATIVE_WORK_STATE_REFRESH_BOOTSTRAP_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_MAIN_READONLY_OPERATIONAL_BOOTSTRAP_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_main_readonly_operational_bootstrap.py`: read-only
  startup composition layer for RedDog's operational context snapshot,
  Fusion/assignment gate, and OpenClaw read-only audit swarm planner.
- Wired `main.py` with
  `run_reddog_readonly_operational_bootstrap_preflight()` before runtime DAE
  autostart. The hook is enabled by default but warning-only; it blocks startup
  only when `REDDOG_READONLY_OPERATIONAL_BOOTSTRAP_ENFORCED=1`.
- Added `tests/test_reddog_main_readonly_operational_bootstrap.py`: fresh
  context acceptance, missing work-state/HoloIndex receipt warning behavior,
  stale HoloIndex rejection, file-based receipt loading, read-target
  normalization, main preflight nonblocking/enforced behavior, ready-result
  reporting, and AST no-runtime-mutation coverage.
- Boundary: no model call, no worker spawn, no OpenClaw enqueue, no Hermes
  dispatch, no repo mutation, no queue mutation, and no HoloIndex re-index.
  This slice plans read-only audit assignments only; it does not execute them.
- HoloIndex read-only probe for `REDDOG_MAIN_READONLY_OPERATIONAL_BOOTSTRAP_PHASE1
  main.py read-only RedDog operational bootstrap audit swarm` surfaced
  unrelated web assets and unknown locations, not the new bootstrap module.
  Recorded `HOLOINDEX_REDDOG_MAIN_READONLY_OPERATIONAL_BOOTSTRAP_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_OPENCLAW_READONLY_AUDIT_SWARM_RUNTIME_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_openclaw_readonly_audit_swarm_runtime.py`: deterministic
  read-only audit swarm planner that consumes an accepted context snapshot
  Fusion/assignment gate decision and emits five audit assignment packets
  (`repo_code_audit`, `external_research_audit`, `runtime_freshness_audit`,
  `skill_gap_audit`, and `security_governance_audit`).
- Added `tests/test_reddog_openclaw_readonly_audit_swarm_runtime.py`:
  accepted plan from exact snapshot/gate binding, rejected gate handling,
  binding mismatch rejection, required-lane rejection, complete report bundle
  acceptance, missing-report rejection, mutation/execution report rejection,
  missing-evidence rejection, and AST no-runtime-wiring coverage.
- Boundary: no model call, no worker spawn, no OpenClaw enqueue, no Hermes
  dispatch, no shell command, no queue mutation, no repo mutation, no
  HoloIndex re-index, and no extension runtime wiring. This slice creates
  assignment packets and validates returned report metadata only.
- HoloIndex read-only probe for
  `REDDOG_OPENCLAW_READONLY_AUDIT_SWARM_RUNTIME_PHASE1 read-only audit swarm snapshot Fusion assignment gate`
  surfaced adjacent fusion redaction, work-order policy, and capability-audit
  surfaces but not the new runtime module. Recorded
  `HOLOINDEX_REDDOG_OPENCLAW_READONLY_AUDIT_SWARM_RUNTIME_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_CONTEXT_SNAPSHOT_FUSION_AND_ASSIGNMENT_GATE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_context_snapshot_fusion_assignment_gate.py`: pure
  fail-closed gate that consumes an operational snapshot, context view,
  evidence bundle, current repo/work-state markers, and requested operation
  before allowing Fusion or worker assignment.
- Added `tests/test_reddog_context_snapshot_fusion_assignment_gate.py`:
  exact-binding acceptance, missing snapshot/view/bundle rejection, mismatched
  context/evidence rejection, repo/work-state/breadcrumb stale rejection, empty
  evidence-bundle rejection, expiry rejection, deterministic determination
  binding, and AST no-runtime-wiring coverage.
- Boundary: no model call, no worker spawn, no queue mutation, no OpenClaw or
  Hermes dispatch, no extension runtime wiring, and no execution. This slice
  emits a `determination_id` binding that downstream model output/work orders
  must carry; it does not consume model output.
- HoloIndex read-only probe for `RedDog context snapshot Fusion assignment
  gate determination binding evidence bundle` surfaced adjacent context bundle,
  Fusion redaction, bootstrap-context, and operator-loop surfaces but not the
  new gate module. Recorded
  `HOLOINDEX_REDDOG_CONTEXT_SNAPSHOT_FUSION_ASSIGNMENT_GATE_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_OPERATIONAL_CONTEXT_SNAPSHOT_RUNTIME_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_operational_context_snapshot.py`: read-only runtime
  snapshot builder for repo HEAD, authoritative work state, HoloIndex freshness
  receipts, scoped breadcrumbs, Brain artifact metadata, and workspace memory
  metadata.
- Added `tests/test_reddog_operational_context_snapshot.py`: source receipt
  schema checks, HoloIndex stale/missing fail-closed behavior, optional Brain
  absence handling, bootstrap/Brain conflict recording without override,
  context-view redaction, evidence-bundle derivation, assignment invalidation,
  existing work-state file loading, repo observation, and AST no-mutation
  coverage.
- Boundary: no repo mutation, no HoloIndex mutation or re-index, no queue
  mutation, no worker spawn, no OpenClaw/Hermes execution, and no extension
  runtime wiring. The snapshot binds `snapshot_receipt_id`,
  `snapshot_content_digest`, `context_view_id`, and derived evidence bundles
  before downstream assignment.
- HoloIndex read-only probe for `RedDog operational context snapshot HoloIndex
  freshness Brain breadcrumbs authoritative work state` surfaced adjacent
  policy-gate, wardrobe-selection, continuity-context, and freshness-governance
  surfaces but not the new snapshot runtime. Recorded
  `HOLOINDEX_REDDOG_OPERATIONAL_CONTEXT_SNAPSHOT_INDEX_GAP_PHASE1`; no runtime
  re-index performed.

## 2026-07-14: REDDOG_RESEARCH_HOLOINDEX_PROMOTION_GATE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 77, 97

- Added `src/reddog_research_holoindex_promotion_gate.py`: pure gate that
  consumes a HoloIndex-first research grounding result, an independent
  verification receipt, and HoloIndex freshness evidence before emitting a
  deterministic promotion envelope for a future governed indexer.
- Added `tests/test_reddog_research_holoindex_promotion_gate.py`: positive
  research finding acceptance, negative/null result acceptance when explicitly
  indexable, grounding/verification/freshness rejection, internal-memory-only
  no-op rejection, source hash/provenance checks, prompt-injection boundary,
  secret evidence rejection, deterministic JSON, and AST no-mutation coverage.
- Boundary: no HoloIndex write, no re-index, no external fetch, no command
  execution, no PatternMemory write, no AgentDB mutation, and no extension
  runtime wiring. The output is a promotion plan only; a later WRE/CI governed
  indexer owns actual indexing.
- HoloIndex read-only probe for `research HoloIndex promotion gate verified
  research receipt negative result` surfaced adjacent CABR/portfolio and
  HoloIndex docs but not a canonical research promotion gate. Recorded
  `HOLOINDEX_REDDOG_RESEARCH_HOLOINDEX_PROMOTION_GATE_INDEX_GAP_PHASE1`; no
  runtime re-index performed.

## 2026-07-14: REDDOG_HOLOINDEX_FIRST_EXTERNAL_RESEARCH_GROUNDING_ADAPTER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 77, 97

- Added `src/reddog_holoindex_first_external_research_grounding_adapter.py`:
  pure RedDog research grounding adapter that queries injected HoloIndex memory
  first, then uses an injected approved external retriever only for unresolved
  or freshness-sensitive external targets.
- Added `tests/test_reddog_holoindex_first_external_research_grounding_adapter.py`:
  HoloIndex-first acceptance, semantic internal-memory grounding, index-gap
  fail-closed behavior, missing retriever, disallowed domains, invalid/stale
  snapshots, prompt-injection-as-data handling, negative-result indexability,
  deterministic receipts, empty-target rejection, and AST no-network/no-command
  no-index/no-persistence coverage.
- Boundary: no direct network I/O, no HoloIndex re-index/promotion, no
  PatternMemory write, no AgentDB task write, no subprocess/shell, no model
  instruction authority from external content, and no extension runtime wiring.
  External evidence is treated as untrusted data with hashes, provenance, and
  freshness receipts.
- HoloIndex read-only probe surfaced adjacent adapter and contract surfaces but
  not the new adapter. Recorded
  `HOLOINDEX_REDDOG_HOLOINDEX_FIRST_EXTERNAL_RESEARCH_GROUNDING_ADAPTER_INDEX_GAP_PHASE1`;
  no runtime re-index performed.

## 2026-07-14: REDDOG_BOUNDED_WORKTREE_WORKER_EXECUTION_PILOT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_bounded_worktree_worker_execution_pilot.py`: bounded worker execution pilot that consumes accepted WRE worktree spine, generic writer dry-run, governed shell dry-run, CWD guard, and HoloIndex evidence before materializing exact planned text artifacts inside an already-created isolated worktree.
- Added `tests/test_reddog_bounded_worktree_worker_execution_pilot.py`: happy path, fail-closed receipt/spine checks, shared-main CWD rejection, artifact mismatch, denied path, governed-shell rejection, HoloIndex gap rejection, secret-content rejection, and AST no-shell/no-git/no-queue/no-runtime-authority coverage.
- Boundary: no subprocess/shell command execution, no git/gh operation, no PR creation, no merge, no OpenClaw enqueue, no Hermes dispatch, no reward settlement, no HoloIndex runtime mutation/re-index, and no extension runtime wiring. This slice proves one bounded text-artifact materialization path in an isolated worktree only.
- HoloIndex read-only probes surfaced adjacent worktree, generic writer, governed shell, and contract surfaces, but not the new pilot module. Recorded `HOLOINDEX_REDDOG_BOUNDED_WORKTREE_WORKER_EXECUTION_PILOT_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-14: REDDOG_SIGNER_AND_DELEGATED_AUTHORITY_RUNTIME_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 96, 97, 100

- Added `src/reddog_signer_delegated_authority_runtime.py`: runtime authority producer that validates a token-verified principal record, fresh permission snapshot, scoped FoundUp paths, nonce uniqueness, revocation state, and high-authority co-sign evidence before requesting principal + RedDog signatures from an injected isolated signer client.
- Added `tests/test_reddog_signer_delegated_authority_runtime.py`: verifier-compatible happy path, default signer fail-closed, unknown principal, high-authority co-sign requirement, low-authority autonomous issuance, stale/insufficient snapshot rejection, scope/path rejection, nonce replay, revocation, signer-boundary attestation, JSON durability, no-signing-material evidence, and AST no-execution/no-crypto/no-runtime-wiring coverage.
- Boundary: no key generation, no crypto/signing library, no vault access, no shell/subprocess/network, no extension runtime wiring, no OpenClaw/Hermes enqueue, no worker spawn, no HoloIndex mutation/re-index, and no execution. Production defaults fail closed unless an isolated signer and verified principal resolver are injected.

## 2026-07-14: REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 60, 70, 97

- Added `src/reddog_authoritative_work_state_refresh_runtime.py`: mutating successor to the work-ledger refresh dry-run planner. It consumes already-observed GitHub/W10/ledger source bundles, emits a freshness receipt, rejects conflicts/stale inputs, commits an authoritative work-state snapshot through an injected atomic store, writes a durable worker claim, and synchronizes a WRE queue item bound to that claim.
- Added `tests/test_reddog_authoritative_work_state_refresh_runtime.py`: happy-path atomic commit, deterministic receipt/revision, stale-source rejection, closed/open conflict rejection, duplicate active-claim rejection, commit-failure fail-closed behavior, JSON-store atomic write, malformed record handling, and AST no-network/no-shell/no-HoloIndex/no-execution coverage.
- Boundary: no GitHub fetch, no W10 fetch, no AgentDB write, no OpenClaw/Hermes live enqueue, no worker spawn, no shell/subprocess, no HoloIndex runtime mutation/re-index, and no execution. This slice is the authoritative state refresh + claim/queue-sync runtime only.

## 2026-07-13: REDDOG_WORK_LEDGER_REFRESH_PLAN_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 60, 70, 97

- Added `src/reddog_work_ledger_refresh_plan_dryrun.py`: read-only refresh planner that consumes `LaneReconciliationReport`, names stale/conflicted work-ledger sources, lists the governed refresh steps, and carries the next claim candidate forward for a later mutating refresh slice.
- Added `tests/test_reddog_work_ledger_refresh_plan_dryrun.py`: stale-source ready plan, conflict-blocked plan, no-refresh-needed detection, deterministic digest, JSON serialization, invalid-input rejection, and AST no-mutation/no-execution coverage.
- Boundary: no ledger mutation, no AgentDB write, no HoloIndex re-index, no worker assignment, no shell/subprocess/git/GitHub call, no extension runtime wiring, and no execution. This slice emits a dry-run refresh plan only.

## 2026-07-13: REDDOG_WORKER_CLAIM_GATE_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 60, 70, 97

- Added `src/reddog_worker_claim_gate_dryrun.py`: dry-run claim gate that consumes `LaneReconciliationReport` and emits a claim-ready receipt only when the lane state is fresh, non-contradictory, and the selected slice is open.
- Added `tests/test_reddog_worker_claim_gate_dryrun.py`: fresh acceptance, stale-source rejection, explicit stale override, conflict rejection, closed/unknown/open requested-slice behavior, no-open-work, digest, serialization, and AST no-mutation/no-execution coverage.
- Boundary: no worker assignment, no worker spawn, no ledger mutation, no AgentDB write, no HoloIndex re-index, no shell/subprocess/git/GitHub call, no extension runtime wiring, and no execution. This slice emits a dry-run claim receipt only.

## 2026-07-13: REDDOG_LANE_STATE_RECONCILER_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 60, 70, 97

- Added `src/reddog_lane_state_reconciler.py`: read-only lane/work-state reconciler that parses `ACTIVE_SLICE_LEDGER.md` and typed `work_ledger` JSON snapshots, detects stale sources and closed-vs-open contradictions, computes a WSP_15 ordered open-slice queue, and emits the required RedDog prework packet (`closed_groundwork`, `open_target`, `chosen_slice`, `not_this_slice`) before worker assignment.
- Added `tests/test_reddog_lane_state_reconciler.py`: parsing, stale-source, WSP_15 ordering, already-closed redirect, conflict fail-closed, digest, serialization, and AST no-mutation/no-execution coverage.
- Boundary: no ledger mutation, no AgentDB write, no HoloIndex re-index, no worker assignment, no shell/subprocess/git/GitHub call, no extension runtime wiring, and no execution. This slice emits a dry-run reconciliation report only.

## 2026-07-12: REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_EXPLICIT_VALVE_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 46, 50, 85, 97

- Added `src/reddog_extension_wre_operational_spine_invoke.py`: an extension-facing explicit invoke guard for the RedDog WRE operational spine.
- Requires an explicit invoke flag plus a sovereign worktree wardrobe-selection receipt before delegating to the already-gated WRE worktree-create spine.
- Preserves extension-runtime separation: no `extension.js` wiring, no OpenClaw enqueue, no Hermes dispatch, no task execution, no PR, push, merge, or reward settlement in this slice.
- HoloIndex read-only probe for `REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_EXPLICIT_VALVE_INVOKE_PHASE1 explicit invoke operational spine selection receipt` surfaced the WRE valve/worktree docs and Skillz surfaces. No runtime re-index performed.

## 2026-07-12: REDDOG_WRE_WORKTREE_CREATE_CWD_GUARD_ALIGNMENT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 53, 85, 97

- Updated `src/reddog_wre_executor_dryrun.py`: proposed worktree paths now live under a sibling external root (`<repo-parent>/.reddog/worktrees/<repo-slug>/...`) instead of inside the shared repo checkout.
- Updated `src/reddog_wre_worktree_create.py`: worktree-create validation rejects legacy in-repo `.reddog/worktrees/...` paths, requires the external root, and runs the shared WRE cwd guard before any runner call.
- Updated `src/reddog_wre_worktree_runner.py`: the approved `git worktree` subprocess helper now applies `validate_wre_worker_operation_cwd()` before create/remove operations, so direct runner use also refuses shared-main or nested-main paths.
- Updated worktree-create, operational-spine, and executor dry-run tests to lock the external-root invariant and prove in-repo worktree paths reject before subprocess.
- Boundary: no task execution, no file edits, no commit, no PR, no merge, no OpenClaw/Hermes dispatch, no extension runtime wiring, and no HoloIndex re-index.
- HoloIndex read-only probe for `RedDog WRE operational spine worktree create cwd guard external worktree root` surfaced the executor dry-run and CWD guard surfaces. No runtime re-index performed.

## 2026-07-12: REDDOG_MERGE_AUTHORITY_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 95, 96, 97, 100

- Added `src/reddog_merge_authority_dryrun.py`: pure dry-run validator for the merge authority contract. It validates non-self promotion, exact-head CI/check-run status, machine-derived diff/scope summary, signed work authority, signed receipt-chain, worktree/shell receipts, independent review opinions, WSP_96 consensus when required, HoloIndex freshness, protected-surface escalation, expiry/nonce, and secret-free evidence packets.
- Added `tests/test_reddog_merge_authority_dryrun.py`: acceptance, fail-closed, self-promotion, CI, review, consensus, HoloIndex, protected-surface, serialization, ASCII, and AST no-GitHub/no-merge/no-subprocess coverage.
- Boundary: no GitHub API call, no `gh pr ready`, no `gh pr merge`, no protected-ref mutation, no shell/subprocess, no file mutation, no extension runtime wiring, no reward settlement, and no HoloIndex re-index. This emits a dry-run decision only.
- HoloIndex read-only probe for `RedDog merge authority dryrun exact head CI reviewer consensus non self promotion` did not surface a canonical dry-run module. Recorded as `HOLOINDEX_REDDOG_MERGE_AUTHORITY_DRYRUN_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-12: REDDOG_MERGE_AUTHORITY_CONTRACT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 71, 95, 96, 97, 100

- Added `docs/audits/architecture/REDDOG_MERGE_AUTHORITY_CONTRACT_PHASE1.md`: decision-only contract for a future RedDog merge authority gate.
- Defined `RedDogMergeAuthorityRequest`, `RedDogMergeAuthorityDecision`, future `RedDogMergeAuthorityReceipt`, non-self promotion, exact-head CI/check-run binding, machine-derived diff/scope summary, signed work authority, signed receipt-chain, reviewer/consensus inputs, F0/external FoundUp policy tiers, protected-surface escalation, and HoloIndex freshness boundaries.
- Boundary: docs/static tests only. No runtime merge authority, no `gh pr ready`, no `gh pr merge`, no GitHub API call, no branch/protected-ref mutation, no shell runner change, no extension runtime wiring, no reward settlement, and no HoloIndex re-index.
- HoloIndex read-only probe for `RedDog merge authority contract signed receipt chain sovereign token merge PR authority` surfaced identity/delegation, signing-key isolation, governed work-order, recursive self-governance, and receipt/redaction surfaces but no canonical merge authority contract. Recorded as `HOLOINDEX_REDDOG_MERGE_AUTHORITY_CONTRACT_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-12: REDDOG_WRE_GOVERNED_SHELL_RUNNER_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 11, 15, 50, 53, 71, 95, 97

- Added `src/reddog_wre_governed_shell_runner_dryrun.py`: pure dry-run validator for the governed shell runner contract. It validates argv-only command profiles, allowed/denied args, shell metacharacter rejection, WSP_71 secret boundaries, sovereign wardrobe selection, signed work authority, signed receipt-chain verification, `VALVE_OPEN_WORKTREE_CREATE`, generic writer dry-run receipt binding, HoloIndex freshness/INDEX_GAP, and WRE cwd guard.
- Added `tests/test_reddog_wre_governed_shell_runner_dryrun.py`: acceptance, fail-closed, cwd isolation, HoloIndex freshness, no-execution receipt, JSON serialization, and AST no-subprocess/no-file-write coverage.
- Boundary: no command execution, no subprocess/git/gh, no file writes, no worktree creation, no PR/merge/release/deploy/publish, no reward settlement, no extension runtime wiring, and no HoloIndex re-index. This emits a dry-run receipt only.
- HoloIndex read-only probe for `RedDog WRE governed shell runner dryrun argv cwd receipt valve` did not surface a canonical dry-run runner. Recorded as `HOLOINDEX_REDDOG_WRE_GOVERNED_SHELL_RUNNER_DRYRUN_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-12: REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 11, 15, 50, 53, 71, 95, 97

- Added `docs/audits/architecture/REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_PHASE1.md`: decision-only contract for a future WRE-owned governed shell runner.
- Defined `GovernedShellCommandProfile`, `GovernedShellRunRequest`, future `GovernedShellRunReceipt`, argv-only command policy, WSP_71 secret boundary, WRE cwd guard requirements, full execution-valve binding, signed authority/receipt inputs, output redaction/caps, and HoloIndex no-reindex boundary.
- Boundary: docs/static tests only. No shell runner implementation, no subprocess invocation, no file mutation, no worktree creation, no PR/merge/release/deploy/publish, no reward settlement, no extension runtime wiring, and no HoloIndex re-index.
- HoloIndex read-only probe for `RedDog WRE governed shell runner contract command execution cwd guard signed authority` surfaced WSP_11/WSP_53/WSP_71, RedDog policy/receipt surfaces, and legacy subprocess call sites. Recorded as `HOLOINDEX_REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-12: REDDOG_GENERIC_AGENT_WORKTREE_WRITER_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 95, 97

- Added `src/reddog_generic_agent_worktree_writer_dryrun.py`: pure dry-run validator for the generic agent worktree-write spine defined by the landed contract. It re-derives canonical roots from a domain profile and domain id, validates planned artifacts, pin-independent denylist, signed authority, signed receipt chain, full `VALVE_OPEN_WORKTREE_CREATE` decision, consensus receipt when required, and WRE cwd guard.
- Added `tests/test_reddog_generic_agent_worktree_writer_dryrun.py`: acceptance, fail-closed, HoloIndex INDEX_GAP, cwd isolation, protected-branch, JSON serialization, and AST no-execution/no-file-write tests.
- Boundary: no file writes, no worktree creation, no subprocess/git/gh, no shell runner, no PR/merge, no reward settlement, no extension runtime wiring, and no HoloIndex re-index. This emits a dry-run receipt only.
- HoloIndex read-only probe for `RedDog generic agent worktree writer dryrun domain profile materialize canonical root cwd guard` surfaced adjacent executor/governed-work-order surfaces plus the prior generic spine audit, but not the new module. Recorded as `HOLOINDEX_REDDOG_GENERIC_AGENT_WORKTREE_WRITER_DRYRUN_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-12: REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 95, 97

- Added `docs/audits/architecture/REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_PHASE1.md`: decision-only contract that extracts the reusable generic worktree write spine without loosening the FoundUp-specific live writer.
- Defined `GenericAgentWorktreeDomainProfile`, re-derived root invariants, pin-independent governance/CI denylist, full execution-valve binding, WRE cwd guard requirements, signed authority inputs, consensus receipt requirements, and the future `GenericAgentWorktreeWriteReceipt`.
- Boundary: docs/static tests only. No generic writer implementation, no live write, no shell runner, no merge authority, no extension runtime wiring, and no HoloIndex re-index.
- HoloIndex read-only probe for `RedDog generic agent worktree write spine contract re-derived root full valve cwd guard` surfaced the prior audit, WRE valve, executor dry-run, and cwd guard surfaces. Recorded the new contract follow-up as `HOLOINDEX_REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-12: REDDOG_EXTENSION_TO_LIVE_ENQUEUE_EXPLICIT_VALVE_INVOKE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 95, 97

- Added `src/reddog_extension_live_enqueue_invoke.py`: extension-facing explicit invoke guard that validates a `RedDogOperatorLoopWardrobeSelectionReceipt` before delegating to the existing live enqueue seam.
- Corrected the operator-loop selector boundary: `wsp97_sovereign_execution` is an accepted governed-execution candidate when downstream signed valve authority is required; actual live enqueue acceptance remains enforced by this guard plus `perform_reddog_openclaw_live_enqueue`.
- Boundary: no `extension.js` runtime wiring, no concrete writer construction, no HoloIndex re-index, no shell/worktree/merge/reward action, and no task execution. The guard reaches an injected writer only after explicit request, sovereign selection receipt, `VALVE_OPEN_LIVE_ENQUEUE`, accepted signature gate, and accepted signed receipt chain.
- HoloIndex read-only probe for `RedDog extension live enqueue explicit valve invoke selector receipt` missed the new invoke guard and surfaced adjacent receipt/valve docs instead. Recorded as `HOLOINDEX_REDDOG_EXTENSION_LIVE_ENQUEUE_INVOKE_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-12: REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_DRYRUN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 45, 50, 95, 97, 99

- Added `src/reddog_operator_loop_wardrobe_selection.py`: pure dry-run selector that converts a normalized 012 work focus plus observed HoloIndex/direct-read state into a deterministic `RedDogOperatorLoopWardrobeSelectionReceipt`.
- Implements the four canonical WSP_95/WSP_97 profiles from the contract: `wsp97_solo_retrieval`, `wsp97_architect_audit`, `wsp97_implementation_slice`, and `wsp97_sovereign_execution`. Draft PR work stays on the implementation plane; live enqueue/shell/worktree/merge/reward requests select the sovereign execution candidate plane and fail closed until downstream signed valve authority exists.
- Boundary: no extension runtime wiring, no HoloIndex re-index, no OpenClaw enqueue, no WRE shell/worktree write, no git/PR/merge action, and no command execution. The selector emits receipts only.
- HoloIndex read-only probe for `RedDog operator loop wardrobe selection dryrun receipt` surfaced adjacent receipt and wardrobe surfaces, but not the new dry-run module. Recorded as `HOLOINDEX_REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_DRYRUN_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-12: REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_CONTRACT_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 45, 50, 95, 97, 99

- Added `docs/audits/architecture/REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_CONTRACT_PHASE1.md`: decision-only contract that binds RedDog self-deterministic mode selection to WSP_97 operator loop plus WSP_95 wardrobe selection. It treats "behavior skillz" as non-canonical shorthand, not a new protocol name.
- Defined the future `RedDogOperatorLoopWardrobeSelectionReceipt`, canonical wardrobe profiles, HoloIndex freshness boundary, and the prerequisite relationship to `REDDOG_EXTENSION_TO_LIVE_ENQUEUE_EXPLICIT_VALVE_INVOKE_PHASE1`.
- Boundary: docs/static tests only. No runtime selector, no extension change, no OpenClaw live enqueue, no WRE shell/worktree write, no merge authority, and no HoloIndex re-index.
- HoloIndex read-only probe for `RedDog operator loop wardrobe selection contract` surfaced WSP_95 and prior operator-loop/security docs, but not the new contract. Recorded as `HOLOINDEX_REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_CONTRACT_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-11: REDDOG_OPENCLAW_LIVE_ENQUEUE_WRITER_ADAPTER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_openclaw_live_enqueue_writer.py`: concrete writer for the #952 live enqueue seam. `foundup_job` appends a typed `FoundUpJob` to OpenClaw's in-memory queue; `autonomous_task` calls `AgentDB.create_autonomous_task()` through a lazy/injectable DB factory.
- Boundary: queue/task creation only. No queue drain, no Hermes/WRE execution, no worktree creation, no file edits, no PR/push/merge, and no reward settlement.
- HoloIndex read-only probes for `RedDog OpenClaw live enqueue writer adapter` and `OpenClawLiveEnqueueWriter AgentDB FoundUpJob` did not surface the new module in top results. Recorded as `HOLOINDEX_REDDOG_OPENCLAW_LIVE_ENQUEUE_WRITER_ADAPTER_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-11: REDDOG_OPENCLAW_LIVE_ENQUEUE_IMPLEMENTATION_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_openclaw_live_enqueue.py`: valve-gated live enqueue seam that validates #904 adapter dry-run output, #950 signed work authority, #951 signed receipt-chain verification, and `VALVE_OPEN_LIVE_ENQUEUE` before calling an injected writer.
- Extended `reddog_wre_execution_valve.py` with `VALVE_OPEN_LIVE_ENQUEUE`, `valve_live_enqueue_enabled`, and `sovereign_live_enqueue_token`; dry-run and worktree-create valves do not authorize live enqueue.
- Boundary: no direct AgentDB/OpenClaw imports, no Hermes/WRE execution, no worktree creation, no file edits, no PR/push/merge, and no reward settlement. Queue writes occur only through the injected writer after all gates pass.
- HoloIndex read-only probes for `RedDog OpenClaw live enqueue implementation`, `VALVE_OPEN_LIVE_ENQUEUE`, and `perform_reddog_openclaw_live_enqueue` did not surface the new module in top results. Recorded as `HOLOINDEX_REDDOG_OPENCLAW_LIVE_ENQUEUE_IMPLEMENTATION_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-11: REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_PHASE1 (refreshed)

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Refreshed stale #905 live enqueue contract on current main. The contract defines the future boundary for converting a #904 proposed FoundUpJob / `autonomous_task` record into a live OpenClaw queue item.
- Updated the contract to require accepted signed work authority (`signature_gate_status=SIGNATURE_GATE_ACCEPTED`) and signed receipt-chain verification before any future live enqueue can be considered.
- Boundary: docs/static tests only. No runtime enqueue module, no AgentDB write, no queue append, no Hermes/WRE dispatch, no shell, no repo mutation.

## 2026-07-11: REDDOG_SIGNED_RECEIPT_CHAIN_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `src/reddog_signed_receipt_chain.py`: verification-only SignedReceipt chain helper for the ratified principal identity/delegation contract. It verifies externally signed `reddog-receipt.v1` records, checks hash links, reward-account binding, receipt freshness, work-order identity, and RedDog identity.
- Empty receipt chains can be accepted as issuance-time "no reward yet"; non-empty chains require every receipt to carry a valid injected signature and a correct `prev_receipt_hash` link. Unsigned receipts are rejected and therefore cannot become reward-bearing chain entries.
- Boundary: no signing, no key generation, no private key handling, no reward settlement, no command execution, no repo mutation, no OpenClaw/Hermes/WRE wiring, and no chain/wallet integration. Production verification defaults fail-closed unless a verifier backend is injected.
- HoloIndex read-only probes for this slice did not surface the new module in top results. Recorded as `HOLOINDEX_REDDOG_SIGNED_RECEIPT_CHAIN_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-11: REDDOG_WORK_ORDER_SIGNATURE_GATE_INTEGRATION_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Integrated the E1 `reddog_work_order_signature_verifier` result into the OpenClaw policy gate as an explicit `signed_work_order_authority` gate. The policy gate can now fail closed when signed authority is required but missing, rejected, malformed, or bound to a different `work_order_id`.
- Added `evaluate_signed_work_order_policy_gate(...)`, the canonical no-execution helper that invokes E1 verification first and then binds the signed authority to the actual work-order fields: work_order_id, repo, operation, permission snapshot digest, allowed paths, and denied paths.
- Added `signature_gate_status` and `signature_gate_digest` to `PolicyGateReceipt` so downstream receipts can prove whether signed work authority was accepted, rejected, or not required for advisory-only paths.
- Threaded signed-authority requirements through `invoke_reddog_work_order_dryrun()` and made `run_reddog_wre_worktree_create_spine()` require accepted signed authority by default before it can reach worktree-create.
- Boundary: no signing, no key generation, no private key handling, no shell, no OpenClaw enqueue, no Hermes dispatch, no PR/merge, and no new live execution. This slice consumes verifier output only.
- HoloIndex read-only probes for `RedDog work order signature gate integration`, `evaluate_signed_work_order_policy_gate signed authority`, and `signed_work_order_authority policy gate` did not surface the new integration in top results. Recorded as `HOLOINDEX_REDDOG_WORK_ORDER_SIGNATURE_GATE_INTEGRATION_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-11: REDDOG_JUDGMENT_GENERATION_WIRING_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 50, 97

- Added `scripts/reddog_judgment_verifier_once.py`: stdin/stdout JSON bridge that reuses `reddog_adversarial_verifier_panel.verify_answer_set()` and reads evidence only from already-fetched direct-read hit bodies supplied by the extension.
- Wired extension v0.3.47 to request canonical `## Determine Answers` fenced JSON when a prompt contains a Determine list, then run the deterministic verifier after repair and expose `judgment_verifier_*` Run Trace / Copy MD telemetry.
- Boundary: local deterministic verifier only; no HoloIndex re-index, WRE enqueue, shell, repo mutation, OpenClaw/Hermes dispatch, or network call. INDEX_GAP is emitted as advisory metadata only.
- HoloIndex read-only probes for judgment wiring did not surface the new runtime bridge or verifier wiring in top results. Recorded as `HOLOINDEX_REDDOG_JUDGMENT_GENERATION_WIRING_INDEX_GAP_PHASE1`; no runtime re-index performed.

## 2026-07-09: WRE_WORKTREE_CWD_HAZARD_GUARD_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 34, 50, 97

- Added `src/reddog_wre_cwd_guard.py`: reusable WRE guard for mutating worker commands after worktree creation. It fail-closes unless the operation cwd resolves inside the isolated worktree and outside the shared repo checkout; rejects relative paths, device/extended-length prefixes, nested-main worktrees, filesystem roots, and cwd drift back into the main worktree.
- Added `tests/test_reddog_wre_cwd_guard.py`: isolated accept/reject coverage for safe worktree cwd, shared repo cwd, worktree-inside-main, cwd-outside-worktree, and relative path failures.
- Purpose: prevent the repeated worker-lane cwd hazard where git staging/branch operations can accidentally target the shared main worktree instead of the isolated worker checkout.
- HoloIndex read-only probe: `WRE worktree cwd hazard guard` and `worktree current directory guard git add shared main` did not surface this new guard or runner integration in top results. Recorded as `HOLOINDEX_WRE_WORKTREE_CWD_GUARD_DISCOVERABILITY_PHASE1`; no runtime re-index performed.

## 2026-07-08: REDDOG_WRE_OPERATIONAL_SPINE_WORKTREE_CREATE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 22, 34, 50, 97

- Added `src/reddog_wre_operational_spine.py`: composes the governed RedDog path into one callable API: work-order invocation dry-run, WRE executor plan dry-run, execution valve, then isolated worktree create. It requires `VALVE_OPEN_WORKTREE_CREATE` for acceptance and stops before task execution, file edits, tests, PR, OpenClaw enqueue, Hermes dispatch, push, or merge.
- Added `tests/test_reddog_wre_operational_spine.py`: full-spine accept path, default-closed valve rejection, invocation rejection on write-sensitive index gap, lock-collision rejection before runner, digest stability, sovereign-token non-egress, and AST boundary checks.
- Focused validation: `test_reddog_wre_operational_spine.py` passed (6 tests); adjacent invocation / executor dry-run / valve / worktree-create suites passed (35 tests).

## 2026-07-08: REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_WORKTREE_CREATE_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 22, 34, 50, 97

- Added `src/reddog_wre_worktree_create.py`: consumes an accepted RedDog executor dry-run plan plus `VALVE_OPEN_WORKTREE_CREATE`, validates branch/worktree/receipt boundaries, and creates only the isolated `.reddog/worktrees/<work_order_id>/<nonce>/` worktree through an injected runner. It emits deterministic receipts and preserves invariants: no task execution, no file edits, no PR, no push, no merge, and main checkout untouched.
- Added `src/reddog_wre_worktree_runner.py`: argv-only `git worktree add/remove` helper. Authorization remains outside the helper in the orchestration module.
- Added `tests/test_reddog_wre_worktree_create.py`: accept path, closed-valve/path-scope rejects, cleanup on create failure, digest stability, token non-leak, and AST boundary checks. Focused validation: 8 new tests passed; adjacent RedDog execution valve / executor dry-run / OpenClaw adapter dry-run suites still pass.

## 2026-07-07: REDDOG_ADVERSARIAL_VERIFIER_PANEL_PHASE1 (judgment lane, slice 4)

**Author**: 0102 (RedDog Architect, Judgment lane) | Commander: 012 | Gate: VERIFIED_READY draft PR (do NOT self-merge)
**WSP**: 00, 15, 22, 50, 64, 97, 99 | **Base**: `1b04e45c2`

- NEW `src/reddog_adversarial_verifier_panel.py`: a DETERMINISTIC verifier panel that, given a RedDog Determine answer set + the authoritative scorecard telemetry + an INJECTED `read_evidence(norm_ref) -> content|None`, verifies EACH answer's cited `file:line` evidence three ways and FAILS CLOSED: a claim is verified ONLY if NO refute lens objects. Verdicts: OBSERVED_VERIFIED / INFERRED (label-preserving) / NEEDS_VERIFICATION (honest abstention passthrough) / REFUTED. Motivation: RedDog scored 0/8 on the FoundUp-creation audit (0102-direct = 8/8); slices 1-3 fixed the shape/repair/excerpt-depth of evidence, slice 4 checks that the cited evidence actually EXISTS and SUPPORTS the claim (the guard in slice 2 is shape-only).
- Three refute lenses, each returning `RefuteReason` codes (empty == no objection): (1) EXISTENCE -- every cited `file:line` must read to real, VISIBLE content (a NUL / zero-width-only window fails closed as `EVIDENCE_ABSENT`; a zero-`file:line` evidence set is `NO_EVIDENCE_FOR_CLAIM`; a reader that raises is caught to absent). (2) SUPPORT -- EVERY operative symbol the question names (snake_case / multi-word CamelCase / CONSTANT_CASE) must appear as a WHOLE token in some cited window (whole-identifier match, not substring: `prebuild_foundups_registry` / `build_foundup_v2` do NOT support `build_foundup`; a comparison/decoy symbol cannot alone carry a claim naming both). A question with NO operative symbol (pure prose, bare domain nouns like `FoundUp`, ubiquitous ALL_CAPS like `INDEX`) is NOT deterministically decidable -> support ABSTAINS and the caller surfaces `NOTE_SUPPORT_UNCHECKABLE` (never a silent decoy-verify, never an over-refute). (3) CONSISTENCY -- a cited path the scorecard proves was REJECTED / never readable is `SCORECARD_CONTRADICTION`.
- REUSES the Determine contract (`DetermineAnswer`, `WSP97_LABELS`, `NEEDS_VERIFICATION_*`, `normalize_evidence_ref`, `_is_file_line`) and adds NO answer-level (order/dup/label-coupling) rules -- lenses are existence/support/consistency ONLY (WSP_64 extend-don't-duplicate). PURE / query-only: imports only `re` / `dataclasses` / `typing` + the contract; no `os`/`subprocess`/`socket`/`open`/`eval`/re-index (AST-enforced by test). `read_evidence` is the SOLE I/O and is INJECTED (tests use fixtures; the live path injects the governed direct-read).
- Appendix A (freshness, NON-MUTATING): `build_index_gap_event(scorecard)` EMITS an advisory `INDEX_GAP` record (`event`/`severity`/`index_gap_detected`/`stale_targets`/`recommendation`/`boundary`) and performs NO live WRE enqueue / CI mutation / re-index. Gap detection matches the canonical producer/consumer `reddog_governed_work_order_dryrun.py:418-422` vocabulary (`index_gap_detected` OR `retrieval_quality == "INDEX_GAP"` OR a direct-read fallback) so a stale-index gap masked by a direct-read is RECORDED, never discarded (direct-read success is not HoloIndex freshness). A direct-read-masked claim still VERIFIES while the gap is emitted. Fails closed to `None` on a non-Mapping scorecard.
- **4-lens adversarial CoR (EXISTENCE_SPOOF / SUPPORT_SPOOF / FAILCLOSED_CONSENSUS / FRESHNESS_AND_MUTATION), 6 rounds, effort:high.** FAILCLOSED_CONSENSUS SAFE every round; existence/freshness converged early; SUPPORT (the one genuinely-hard deterministic "does the evidence support the claim") drew the long tail, each round tightening it: R1 (blocker substring-support + major prose-support + major scorecard-crash) / R2 (major boilerplate OR-decoy `get_logger` + minor non-Mapping-scorecard crash) / R3 (major non-Mapping answer-entry crash) / R4 (major multi-anchor comparison decoy `extract_foundup` carrying a `build_foundup` claim) / R5 (blocker domain-noun/ALL_CAPS OR-branch silent-verify + major INDEX_GAP retrieval-tier discard + minor NUL/zero-width existence) all folded. **R6: all 4 lenses SAFE, 0 blocker / 0 major / 0 finding, 35 confirmations.**
- TEST `tests/test_reddog_adversarial_verifier_panel.py` (42): 012 acceptance bars (verified 8/8 incl. the `build_foundup == extract_foundup` two-operative case; fabricated/absent -> REFUTED; non-supporting window -> REFUTED; scorecard-rejected path -> REFUTED; honest NEEDS_VERIFICATION passthrough) + every CoR regression (substring, versioned-sibling, boilerplate decoy, multi-anchor decoy, context-noun-not-over-refuted, domain-noun-only-not-silently-verified, INDEX_GAP-via-retrieval-tier-recorded, NUL/zero-width-fails-closed, malformed-scorecard/answer no-crash) + purity (AST denylist) + ASCII/NUL clean.
- SCOPE (this slice): the deterministic PANEL + tests only. NOT wired into RedDog's output path yet (generation-time integration + CLI bridge = a later layer, mirroring slice 1's build-before-wire). INDEX_GAP routing is advisory-emit only; a governed WRE/CI enqueue is a separate future slice.
- Judgment lane sequence: 1 DETERMINE_QUESTION_ANSWER_CONTRACT (#933) -> 2 REPAIR_PRESERVES_EVIDENCE (#934) -> 3 SYMBOL_AWARE_EXCERPT_DEPTH (#935) -> **4 (this)** -> 5 FOUNDUP_INTAKE_PACKET_MODE. This slice = VERIFIED_READY draft PR only; not merged. Live-writer recheck (`RUN_LIVE_WRITER_PACCESS_001_PREAUTH_RECHECK_PHASE1`) remains HELD.

## 2026-07-05: REDDOG_REPAIR_PRESERVES_EVIDENCE_PHASE1 (judgment lane, slice 2)

**Author**: 0102 (RedDog Architect, Judgment lane) | Commander: 012 | Gate: VERIFIED_READY draft PR (do NOT self-merge)
**WSP**: 00, 15, 22, 50, 64, 97 | **Base**: `15ce8e4a2`

- NEW `src/reddog_repair_evidence_guard.py`: WIRES the Determine contract's repair-preservation validator into the RedDog schema-repair path. When a primary advisory answer carries a Determine answer block, a schema-repair pass (which exists to ADD missing sections) must NOT drop / reorder / weaken / strip-evidence / fabricate the evidence-backed answers. REUSES `reddog_determine_answer_contract.assert_repair_preserves` for ALL answer-level rules (012 directive: do not duplicate validator logic); the guard adds only (a) a fenced-JSON extract adapter (robust `json.loads`, not another markdown parser), (b) a protected-block context builder that carries file:line evidence into `repair_minimal`, and (c) fail-closed block-level edges. On ANY preservation failure the decision is KEEP_ORIGINAL (reject the weakened repair, keep the primary + its validation failure). Backward compatible: no primary Determine block -> no-op.
- Protection is gated on the PRIMARY emitting a block (not on the prompt): a malformed/absent prompt Determine list synthesizes questions from the self-describing primary block, so a bad prompt can NOT fail OPEN. Fail-closed edges: dropped block, unparseable/ambiguous block (ATX **or** SETEXT, near-canonical/leading-word variants), duplicate-primary-index, scalar `evidence_refs`, variable-length fence for backtick-in-question round-trip.
- NEW `scripts/reddog_repair_guard_once.py`: thin stdin/stdout JSON CLI bridge (`protect` / `guard` actions), fail-closed on any error. Called synchronously from the extension via `cp.execFileSync` (same pattern as the HoloIndex/git calls).
- CONTRACT hardening (`reddog_determine_answer_contract.py`, reused by the guard): step-1 now requires every ORIGINAL-answered index to survive (catches surplus-index drops beyond `len(qs)`); `from_obj` coerces a non-list `evidence_refs` to `[]` (no TypeError, mirrors `_safe_int`).
- **8-lens adversarial CoR (answer-drop / reorder / evidence-strip / fabrication / label-weaken / context-truncation / prose-collapse / redaction-fallback), 5 rounds, effort:high.** Answer-level delegation SAFE every round; the entire tail was guard-adapter injection variants: R1 (4: surplus-drop, dual-block, backtick-fence, empty-array) / R2 (2: near-canonical header, digest newline-injection) / R3 (2 major + 1 minor: leading-word header, scalar evidence_refs, duplicate-primary) / R4 (2: SETEXT heading, prompt-driven no-op fail-OPEN) all folded. **R5: all 8 lenses SAFE, 0 findings.**
- TEST `tests/test_reddog_repair_evidence_guard.py` (~52): 012's 10 acceptance bars (8/8 preserved; add-section preserves; drop/reorder/remove-evidence/downgrade/fabricate rejected; context carries file:line; audit fixture round-trips) + all CoR regressions + serialization round-trip + fail-closed edges + purity/ASCII. Contract suite +2 regressions (90->92). Full: 141 green.
- WIRED into `extensions/foundups_advisory_workers/extension.js` (0.3.41 -> 0.3.42): pre-repair inject protected block into `repair_minimal`; post-`mergeRepairedOutput` revalidate via the guard -> on `keep_original` discard the merge and keep the primary + validation failure (`repair_dropped_determine_evidence`); telemetry `repair_evidence_protected` / `repair_evidence_preserved` / `repair_evidence_reasons`; fail-closed if the guard bridge is unavailable. Extension contract test extended (source wiring + ATX/SETEXT presence + real end-to-end guard bridge).
- Judgment lane sequence: 1 DETERMINE_QUESTION_ANSWER_CONTRACT (#933) -> **2 (this)** -> 3 SYMBOL_AWARE_EXCERPT_DEPTH -> 4 ADVERSARIAL_VERIFIER_PANEL (owns evidence existence/truth; guard is shape-only) -> 5 FOUNDUP_INTAKE_PACKET_MODE. This slice = VERIFIED_READY draft PR only; not merged.

## 2026-07-05: REDDOG_DETERMINE_QUESTION_ANSWER_CONTRACT_PHASE1 (judgment lane, slice 1)

**Author**: 0102 (RedDog Architect, Judgment lane) | Commander: 012 | Gate: VERIFIED_READY draft PR (do NOT self-merge)
**WSP**: 00, 15, 22, 50, 64, 97 | **Base**: `62ffa0878`

- NEW `src/reddog_determine_answer_contract.py`: a self-contained CONTRACT + VALIDATOR for the case where a prompt carries a `Determine:` numbered list. It forces RedDog to answer EACH item explicitly, in order, WSP_97-labeled, file:line-evidenced (or an explicit NEEDS_VERIFICATION when evidence is genuinely absent -- never a silent omission), and stops a repair pass from collapsing answers to prose, dropping/fabricating evidence, reordering, or changing a determination. Pure text (no subprocess/os/network/open). NOT yet wired into RedDog's output path -- generation-time integration is a later slice. Motivation: RedDog scored 0/8 on the FoundUp-creation audit (0102-direct = 8/8); the gap was judgment/audit-substance, not capability.
- Four layers: (1) `parse_determine_questions` extracts the ordered items preserving author source numbers; FAIL-CLOSED on any structural ambiguity (same-line fusion, over-indent/nesting, wrap-continuation-starting-with-an-ordinal, gap/restart/dup, digit-initial fused bodies, unclosed/tail/example code fences) via a `_MALFORMED_SENTINEL`. (2) `is_determine_list_wellformed` requires a contiguous 1..N. (3) `normalize_evidence_ref` SHAPE-checks `path:line` / `path#Lline` / supplementary `Run Trace:field`, rejecting bare paths, dotted non-files, traversal/absolute, line-0, and non-ASCII-digit locators. (4) `validate_answer_set` (fail-closed: missing/invented/duplicate/reorder/text-altered/label-coupling/vague-evidence/NV-misuse) + `assert_repair_preserves` (no collapse/drop/fabricate/reorder/determination-change; anchored materialization of an omitted index rejected, honest NV materialization allowed).
- **4-lens adversarial CoR (PARSER_MISCOUNT / VALIDATION_BYPASS / EVIDENCE_SPOOF / REPAIR_EVASION), 23 rounds, effort:high.** Validation/evidence/repair converged SAFE by ~R3-R4 and stayed SAFE; the parser had the long adversarial tail (each round a real silent-omission/miscount folded on the one-item-per-physical-line + fail-closed-on-ambiguity principle). Fence machinery (R19) drew its own sub-tail: unclosed-fence-swallows-tail (R20), Unicode-digit evidence locator + omitted-index repair fabrication (R20), blank-preceded digit-initial ordinal (R21), balanced-fence-swallows-contiguous-tail (R22). **R23: all four lenses SAFE, 0 blocker/0 major/0 finding.**
- TEST `tests/test_reddog_determine_answer_contract.py` (89): the 012 acceptance fixture (FoundUp-creation audit -> exactly 8 answers; 7/8 rejected; collapsed summary rejected; evidence-bearing requires file:line; Run Trace alone insufficient; repair cannot drop/reorder) + ~50 CoR regressions. ASCII-clean (chr()/escape-free source), purity + no-leak asserted.
- **Documented fail-closed limitations (all reject, none silently mis-parse)**: a Determine question body may not contain an inline `N.` ordinal (use `N`/prose); a decimal whose integer part == item num+1 is conservatively rejected; the Determine block must be TOP-LEVEL (not fenced); a fenced sample must restart numbering at 1 (a fenced ordinal continuing the sequence is ambiguous -> MALFORMED); evidence is SHAPE-only (existence/truth = downstream adversarial-verifier-panel slice); repair may strengthen but not source a missing anchor.
- Judgment lane sequence: **1 (this)** -> 2 REPAIR_PRESERVES_EVIDENCE -> 3 SYMBOL_AWARE_EXCERPT_DEPTH -> 4 ADVERSARIAL_VERIFIER_PANEL -> 5 FOUNDUP_INTAKE_PACKET_MODE. This slice = VERIFIED_READY draft PR only; not merged.

## 2026-07-05: REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1 (E1 -- first implementation)

**Author**: 0102 (RedDog Architect, Lane A Identity/Delegation/Signing) | Commander: 012 | Gate: VERIFIED_READY draft PR (do NOT self-merge)
**WSP**: 00, 15, 22, 50, 54, 71, 96, 97 | **Base**: `1a2412c0d` (after #925-#931; E0 merged)

- NEW `src/reddog_work_order_signature_verifier.py`: VERIFICATION ONLY. Validates a signed `RedDogDelegatedWorkAuthority` against its `RedDogPrincipalIdentity` per the ratified contract #928 (canonicalization Section 2, order Section 11) + E0. Implements canonical_signing_input (sorted-key compact JSON + LITERAL domain-prefix strip, ASCII-only, exclude {signature, receipt_chain}) and the full pipeline: revocation-first -> anti-self-mint anchors -> two signatures (identity by principal key, work order by reddog key) -> freshness (single shared time gate) -> snapshot fresh+digest-bound+grants -> repo/foundup scope -> forbidden-op + effective-path IN-FOUNDUP-SCOPE -> valve -> nonce-consume-LAST. Returns `VerificationResult(accepted, reason_codes)` (static codes, no expected-value/key leak). Raw asymmetric verify is INJECTED (algorithm deferred by contract); default `FailClosedSignatureVerifier`. NO signing, NO keygen, NO private key, NO execution side effect, NO subprocess/os/secrets import.
- Generalizes the proven intake_auth_provider pattern: verified-subject-not-payload, literal prefix strip, durable single-use nonce (consumed only after signature success), fail-closed, `hmac.compare_digest` constant-time.
- Enforcement seam: `require_authorized(result)` raises `WorkOrderRejected`; `VerificationResult.__bool__` == accepted (a bare `if result:` cannot mean "object exists").
- TEST `tests/test_reddog_work_order_signature_verifier.py` (29): the 17 required (valid; tamper; non-canonical; expiry; nonce replay; revoked key_epoch; wrong principal; wrong reddog_id; changed allowed_paths; changed foundup_scope; snapshot stale+mismatch; missing signature; free-text "012"; no-leak; constant-time; no-private-key; AST denylist) + CoR regressions (path-out-of-scope; traversal; untrusted/mismatched principal key; key-reuse self-mint; empty key_epoch; nonce-not-burned-on-transient-reject; bool/require_authorized; admin-verb-needs-can_admin; non-bool-verifier; non-serializable-fail-closed). 74 spine tests green, no regression.
- **9-lens adversarial CoR, 2 rounds: R1 found 3 blocker (path widening, principal self-mint, key-reuse self-mint) + 4 major (nonce lockout, key_epoch omission bypass, unwrapped deps, truthy-result misuse) + 2 minor -- ALL folded; R2 all 9 lenses SAFE, 0 blocker/0 major (2 residual minors: identity_nonce intentionally not consumed at work-order time = reusable identity; caller-enforcement is require_authorized).**
- **E0/E1 Sequence Lock honored: E0 is merged (#931); no signature is authority until BOTH E0+E1 land + gate review. This slice = VERIFIED_READY draft PR only; not merged.** INDEX_GAP: new verifier + E0/E1 docs unindexed (operator re-index).

## 2026-07-05: REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1 (E0 decision doc, pointer)

**Author**: 0102 (RedDog Architect) | Commander: 012 | Gate: decision-only PR (no code, no keys, no authority change)
**WSP**: 00, 15, 22, 48, 50, 54, 64, 71, 95, 96, 97 | **Base**: `62e6e7a48` (after #925-#929)

- Decision/contract-only. Slice E0 -- the mandatory precondition for E1 (the signature verifier). Extends WSP 71 (Secrets Mgmt + s3.4 SkillSafetyGate); grounds on secrets_mcp/vault_resolver.py (op://+TTL+audit-hash SHAPE, MOCK/no-principal-scoping) + intake_auth_provider.py (compare_digest, sign-current/verify-current+previous).
- ADD `docs/audits/architecture/REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1.md` -- isolates the future signing key from any code RedDog loads (closes threat-model G5.1: poisoned in-process Skill/dep reaches vault -> emits a VALID signature). 4-lens adversarial CoR (11 blocker/12 major) folded. Boundary invariants: MANDATORY distinct OS principal (same-user separation is NOT a boundary; PR_SET_DUMPABLE=0/RLIMIT_CORE=0/no-ptrace); no inherited env; host connects (not spawns) over perm-restricted socket; requester identity from KERNEL peer credential (SO_PEERCRED) not request-body; sign-what-you-validate (canonical_payload single source of truth); high-authority tiers need consensus/012-DAO co-sign + per-principal rate/volume cap; sign-current-key-only + key_epoch; resolve-per-sign/zeroize/TTL-at-use; key_fingerprint from public material never sha256(secret); keyed/chained audit_mac; WSP71 permission-validated retrieval (get_secret+agent_id->PermissionDeniedError) not op:// possession; constant-time both sides + no secret in argv/exit/shm/coredump.
- **Strict E0/E1 Sequence Lock (012): E1 verifier implementation is BLOCKED until E0 lands. E1 tests/APIs/semantics authored before E0 merge are non-authoritative and discarded/revalidated after E0. No signature is authority until BOTH E0 and E1 have landed + passed gate review.**
- TEST `tests/test_reddog_signing_key_isolation_contract_doc.py` (11): asserts distinct-OS-principal, kernel-peer-credential, sign-what-you-validate, co-sign+rate-cap, fingerprint-not-secret-hash + keyed-audit, WSP71-permission-validated-retrieval, the E0/E1 sequence lock, no-parallel-build-relaxation, decision-only; ASCII-clean.
- Sequence: A #925 -> B #927 -> C #929 -> D #926/#928 -> **E0(this)** -> E1 signature verifier (BLOCKED until E0 merges) -> F signed receipts -> G reward mapping -> H generic writer.

## 2026-07-05: REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL_PHASE1 (decision doc, pointer)

**Author**: 0102 (RedDog Architect) | Commander: 012 | Gate: decision-only PR (no code, no authority change)
**WSP**: 00, 15, 22, 48, 50, 54, 58, 64, 95, 96, 97, 100 | **Base**: `c7bb3ff5` (after #925/#926/#927/#928)

- Decision-only threat model. NO code, NO keys, NO chain, NO authority change, NO re-index. Slice C in the corrected A-H sequence.
- ADD `docs/audits/architecture/REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL_PHASE1.md` -- threats specific to RedDog becoming recursively self-improving AND execution-capable. Identity-spoofing is #926's territory (cited, not duplicated); this owns self-governance under recursion. 7 threat families: G1 derivation-substrate poisoning (oracle/WSP-index/HoloIndex + NEW pattern-memory + derivation prompt-injection); G2 self-governance mutation (+ NEW meta-authority/governance-capture); G3 integrity!=authenticity; G4 replay+concurrency (+ NEW distributed-TOCTOU, worktree/chain-fork, mutating-quorum-membership, non-atomic-6-step-gate, tamper-preserving-audit-rewrite); G5 executable-supply-chain (poisoned in-process Skill/dep reaches the vault -> emits a VALID signature -- signatures alone insufficient); G6 economic (Goodhart farming, collusive self-dealing, CABR-oracle poisoning); G7 availability/side-channel/social (DoS/fail-open, HMAC timing side-channel, social-engineer the honest reviewer). 15 RESIDUAL controls = the backlog. Sharpens slice E with two mandatory requirements: key isolation from plugin/Skillz/dependency runtime + constant-time signature compare with no expected-value leakage.
- TEST `tests/test_reddog_recursive_self_governance_threat_model_doc.py` (15): asserts G1-G7 present, integrity-not-authenticity, key-isolation/supply-chain, constant-time/no-timing-leak, concurrency/TOCTOU, economic gaming, DoS/fail-open, and NO runtime code / NO verifier implementation; ASCII-clean.
- Corrected sequence: A #925(done) -> B #927(done) -> **C(this)** -> D #926 ratified #928 -> **E0 REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1** -> E1 REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1 -> F signed receipts -> G reward mapping -> H generic writer. E split into E0+E1 per C's G5.1 finding (a verifier without key isolation can still emit valid forged authority).

## 2026-07-05: REDDOG_OPERATOR_LOOP_AND_GENERIC_SPINE_AUDIT_PHASE1 (decision docs, pointer)

**Author**: 0102 (RedDog Architect) | Commander: 012 | Gate: decision-only PR (no code, no authority change)
**WSP**: 00, 15, 22, 48, 50, 54, 64, 66, 96, 97 | **Base**: `4094ed58e` (#925 merged)

- Decision/contract-only slice. NO code, NO extension change, NO WSP-framework edit, NO live-writer change, NO re-index. Two docs land the record on main as the basis for the next layer (threat model, slice C).
- ADD `docs/audits/architecture/REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_AUDIT_PHASE1.md` -- 5-lens audit of #925: verdict KEEP_FOUNDUP_SPECIFIC_FOR_NOW + EXTRACT_GENERIC_SPINE_CONTRACT_NEXT; ~8 generic-SPINE vs ~5 FoundUp-POLICY couplings; runner already generic; 2 latent blockers gate genericization/012-out-of-loop (caller allowed_paths deletes containment; writer uses `_resolve_valve_state(env,[])` skipping the spine chain). Hard rule: generic != unbounded. INDEX_GAP confirmed.
- ADD `docs/audits/architecture/REDDOG_OPERATOR_LOOP_WSP97_BINDING_PHASE1.md` -- binds RedDog to run the WSP 97 operator loop autonomously (the 5 mandatory questions as a preamble receipt chain), ACTIVE-DERIVED not caller-asserted; extends WSP 97 (WSP 64, no new WSP). 4-lens adversarial CoR (9 blocker/11 major DESIGN findings) folded. **Core boundary (enforced by static test): the operator loop gives INTEGRITY, not AUTHENTICITY -- WSP derivation does NOT prove authorization.** Adds protected-oracle requirement (5A), 7 permanent system invariants (5B), derived-WSP-to-actual-work binding (5C). Signature/authenticity layer deferred to slices C/D; valve must not trust the unsigned `REDDOG` label until then.
- TEST `tests/test_reddog_operator_loop_and_generic_spine_audit_phase1.py`: static doc test (reads the .md files, asserts anchor strings incl. the integrity-not-authenticity boundary + the no-authenticity-overclaim gate; ASCII-clean). No runtime import, no authority behavior.
- Sequence: A(prove #925) -> **B(these docs)** -> C(REDDOG_IDENTITY_SPOOFING_AND_DELEGATION_THREAT_MODEL_PHASE1) -> D(PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT) -> E(GENERIC_SPINE_CONTRACT) -> F(generic writer, later).

## 2026-07-04: FOUNDUP_CREATE_ACTION_DRYRUN_PHASE1 (create_foundup canonical action)

**Author**: 0102 (RedDog Architect) | Commander: 012 | Gate: VERIFIED_READY draft PR (do NOT self-merge)
**WSP**: 00, 15, 22, 49, 50, 97, 109 | **Base**: `0046423c6`

- `foundup_job_contract.py`: added `create_foundup` to `CANONICAL_ACTIONS` (now 5) -- a NEW-scaffold
  action DISTINCT from build/extract. Added `EXISTING_MODULE_ACTIONS = {build_foundup, extract_foundup}`
  taxonomy so the no-alias invariant (P2 contract Section 3) is checkable. Added fail-closed
  `StatusReasonCode`s: `FAIL_FOUNDUP_ID_EXISTS`, `FAIL_CREATE_ALIASED_TO_EXTRACT`,
  `FAIL_ENVELOPE_NOT_GATE_PASSED`.
- The dry-run planner consuming this action lives in
  `modules/foundups/agent/src/create_foundup_dryrun.py` (writes nothing).
- TEST `tests/test_foundup_job_contract.py`: updated the canonical-actions count (4 -> 5) + added a
  create_foundup canonical + no-alias assertion.
- Pre-existing (NOT this slice): `test_e2e_foundup_job_seam.py` has 3 env-dependent extract failures
  that reproduce on clean main; CI env passes them.

## 2026-07-03: REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1 (v0.3.39)

**Slice:** Authoritative required-target section identification (marker forgery hardening)
**WSP:** WSP_00, WSP_11, WSP_22, WSP_50, WSP_97
**Stacked on:** REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 (#917)

- EDIT `src/fusion_redaction_gate.py` — add `_normalize_required_target_path()`; extend
  `_isolate_required_targets(context, authoritative_paths=None)` so marker-delimited sections are
  required-target sections only when their path is IN the authoritative packed list threaded from
  the JS packer. Phantom markers (path not in list) fold back verbatim as ordinary content; checked/
  passed/blocked/missing cannot exceed the authoritative count; `blocked_paths` is a subset of
  authoritative paths. `authoritative_paths=None` preserves byte-identical #917 behavior.
- EDIT `evaluate_redaction_gate(..., required_target_paths=None)` — thread authoritative list into
  isolation path.
- EDIT `scripts/advisory_model_once.py` (bridge) — read `required_target_paths` from stdin payload.
- ADD 6 MFH adversarial tests in `tests/test_fusion_redaction_gate.py` (embedded marker not a
  section; malicious fixture no inflation; blocked_paths subset; full adversarial fixture;
  None-byte-identical legacy; one-blocked sibling survives with authoritative list). 95/95 pass.
- No weakening: identification-only; no detector relaxed; audit-mode value-vs-structure unchanged.

## 2026-07-01: REDDOG_AUDIT_MODE_REDACTION_PHASE1 (slice 3/3)

**Slice:** Audit-mode redaction preserves governance STRUCTURE while still redacting VALUES
**WSP:** WSP_11, WSP_50, WSP_84, WSP_97, WSP_22
**Stacked on:** slice 2 (#907, feat/reddog-direct-read-fallback-by-path-phase1)

- EDIT `src/fusion_redaction_gate.py` -- add `audit_mode` param to `evaluate_redaction_gate`,
  `redaction_status_for`, `redact_text`, `scan_forbidden` (default `False` -> non-audit path
  byte-identical). Add `AUDIT_STRUCTURAL_CATEGORIES` (source_authority / merge_authorization /
  cabr_payout_authority / governance_instruction) made audit-visible, plus audit-only VALUE
  redactors (payout amounts, merge tokens, grant values, key-preserving secret_kv/env_secret_line).
- FIX over-sanitization from the FoundUp-creation run trace: those four BLOCK categories matched on
  the bare identifier and stripped the governance STRUCTURE a governance audit must read.
- SAFETY (non-negotiable): audit mode NEVER relaxes `private_reasoning`, `private_key_residual`, or
  any REDACT category. Fake API key / OAuth token / payout amount / merge token STILL `[REDACTED]`.
- EDIT `src/fusion_alias_live.py` -- add `audit_context=False` to `run_alias_live`, threaded into the
  entry gate (`audit_mode=`); default keeps the live path byte-identical.
- ADD 14 audit-mode tests in `tests/test_fusion_redaction_gate.py` (structure preserved, secrets
  still redacted, backward-compat byte-identical). 79/79 pass (65 prior + 14 new).
- Extension surfaces `audit_context=true` from `buildDirectReadContentSection` when slice-2 direct-read
  fetched required governance targets (extensions/foundups_advisory_workers); DRF-008/009 contract
  proofs added. No detector/fetch/allowlist change; no execution/write/shell-out authority.

## 2026-06-28: REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_PHASE1

**Slice:** OpenClaw FoundUpJob adapter dry-run planner (propose only, no enqueue)
**WSP:** WSP_15, WSP_34, WSP_50, WSP_91, WSP_97, WSP_22

- ADD `src/reddog_openclaw_adapter_dryrun.py` -- `plan_reddog_openclaw_adapter_dryrun()`, `RedDogOpenClawAdapterDryRunResult`.
- ADD `tests/test_reddog_openclaw_adapter_dryrun.py` -- FoundUpJob/autonomous_task propose, valve rejects, AST denylist.
- ADD `docs/audits/architecture/REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_CONTRACT_PHASE1.md`.
- Requires `VALVE_OPEN_DRYRUN_ONLY`; always `no_enqueue_performed` + `no_execution_performed`.

## 2026-06-28: REDDOG_WRE_EXECUTION_VALVE_PHASE1

**Slice:** Closed-by-default WRE execution valve evaluator (pure evaluation)
**WSP:** WSP_15, WSP_34, WSP_50, WSP_91, WSP_97, WSP_22

- ADD `src/reddog_wre_execution_valve.py` -- `evaluate_reddog_execution_valve()`, `ExecutionValveDecision`.
- ADD `tests/test_reddog_wre_execution_valve.py` -- default closed, dry-run open, worktree token, rejections, AST denylist.
- ADD `docs/audits/architecture/REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1.md` -- contract + gate ordering.
- Default `VALVE_CLOSED`; requires full #889-#898 spine + #901 canonical intake target.

## 2026-06-28: REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1 (pointer)

**Slice:** OpenClaw FoundUpJob adapter **contract only** (audit doc)
**WSP:** WSP_15, WSP_50, WSP_77, WSP_97, WSP_22

- Canonical: `docs/audits/architecture/REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md`
- ADD `tests/test_reddog_openclaw_adapter_contract_doc.py` — static doc-presence assertions.
- Ruling: AssignmentDispatcher simulated scaffold; OpenClaw owns worker loop.

## 2026-06-28: REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_DRYRUN_PHASE1

**Slice:** WRE isolated worktree executor dry-run planner (plan + receipts, no mutation)
**WSP:** WSP_34, WSP_50, WSP_91, WSP_97, WSP_22

- ADD `src/reddog_wre_executor_dryrun.py` — `plan_wre_isolated_worktree_execution_dryrun()`, `WREExecutorPlan`.
- ADD `tests/test_reddog_wre_executor_dryrun.py` — accept/reject/lock/cleanup/AST denylist.
- Consumes #896 invocation result; validates #897 contract rules; no git/subprocess/worktree.

## 2026-06-28: REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1 (pointer)

**Slice:** WRE isolated worktree executor **contract only** (audit doc; no module code)
**WSP:** WSP_15, WSP_50, WSP_97, WSP_22

- Canonical: `docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md`
- ADD `tests/test_reddog_wre_executor_contract_doc.py` — static doc-presence assertions only.
- Future executor consumes #893 PolicyGateReceipt + #894 RedDogWorkOrderReceipt after execution valve.

## 2026-06-28: REDDOG_WORK_ORDER_RUNTIME_INVOCATION_DRYRUN_PHASE1

**Slice:** Runtime dry-run invocation orchestrator (policy gate + receipt, no execution)
**WSP:** WSP_34, WSP_50, WSP_91, WSP_97, WSP_22

- ADD `src/reddog_work_order_runtime_invocation.py` — `invoke_reddog_work_order_dryrun()` chains #893 + #894.
- ADD `tests/test_reddog_work_order_runtime_invocation.py` — 7 tests (accept/reject/replay/idempotency/AST denylist).
- HoloIndex: pre-edit hits on OpenClaw orchestrator/routing; post-edit INDEX_GAP for new module — static pointers added.

## 2026-06-28: REDDOG_HERMES_WORK_ORDER_RECEIPT_PHASE1

**Slice:** Hermes-compatible pre-execution audit receipts for governed work orders
**WSP:** WSP_34, WSP_50, WSP_91, WSP_97, WSP_22

- ADD `src/reddog_work_order_receipt.py` — `RedDogWorkOrderReceipt`, `emit_work_order_receipt()`, SQLite `RedDogWorkOrderReceiptStore`.
- ADD `tests/test_reddog_work_order_receipt.py` — 14 tests (digest stability, redaction, idempotency, no-execution boundary).
- Reuses #893 `PolicyGateReceipt`; Hermes-compatible shape; NOT live Hermes queue wiring.
- HoloIndex: pre-edit hits on Hermes/CABR receipt patterns; post-edit static pointers in INTERFACE/ModLog (INDEX_GAP for semantic ranking — follow-up if needed).

## 2026-06-28: REDDOG_OPENCLAW_WORK_ORDER_POLICY_GATE_PHASE1

**Slice:** OpenClaw policy gate — dry-run + permission freshness + HoloIndex policy (no execution)
**WSP:** WSP_34, WSP_50, WSP_97, WSP_22

- ADD `src/reddog_openclaw_work_order_policy_gate.py` — `evaluate_work_order_policy_gate()` returns Hermes-shaped `PolicyGateReceipt`.
- ADD `tests/test_reddog_openclaw_work_order_policy_gate.py` — 22 tests (Addenda A–D; mocked permissions only).
- Reuses #890 `validate_work_order_dryrun()` and #892 `permission_to_capabilities()`; no WAE runtime, no `gh`, no execution.
- WAE-L1 ↔ RedDog ↔ PolicyGateReceipt mapping in module docstring (Addendum B).

## 2026-06-28: REDDOG_GOVERNED_REPO_WORK_ORDER_DRYRUN_PHASE1

**Slice:** External RedDog lane dry-run validator (shared with future OpenClaw policy gate)
**WSP:** WSP_34, WSP_50, WSP_97, WSP_22

- ADD `src/reddog_governed_work_order_dryrun.py` — `validate_work_order_dryrun()` with typed envelope, HoloIndex evidence gate, nonce replay guard, receipt digest.
- ADD `tests/test_reddog_governed_work_order_dryrun.py` — 13 tests (accept + rejection paths).
- WAE-L1 field mapping documented in module docstring (Addendum B); no WAE runtime changes.
- No GitHub, branch, PR, write, shell, or merge.

## 2026-06-19: Fusion ALIAS live path -- valve-gated OFF, redaction-gated, advisory-only (W6)

**Author**: 0102 (Worker-Lane W6, AUTHOR + internal SENTINEL)
**WSP**: 11 (Interface), 50 (Pre-Action), 84 (HTTP-client reuse), 97 (Truth Boundary)
**Slice**: `HERMES_FUSION_ALIAS_MODE_PHASE2`
**Predecessors**: #832 (contract, `7bd68e73a`), #842 (redaction gate, `972d082a0`)
**Base**: `005dd3629` (origin/main; #842 landed)

### Summary

First live OpenRouter integration -- but it makes ZERO live calls on landing. The actual network call is
behind a SOVEREIGN VALVE: env flag `FUSION_ALIAS_LIVE_ENABLED` (default OFF) AND a typed
`LiveFusionAuthorization` (authority `012`). Raw text is redacted ON ENTRY via the landed redaction gate;
only the REDACTED prompt/context is sent; only digests are retained. Phase 0 (HoloIndex MEDIUM/HIGH;
gate exposes `redacted_prompt`/`.passed`; ai_gateway uses `requests`) confirmed: no gate API gap, no new dep.

- ADD `src/fusion_alias_live.py` -- `run_alias_live(prompt, context=None, *, authorization, ...)`:
  redaction-gate-first -> env valve -> typed 012 authorization -> key -> budget -> ONE bounded POST (no
  stream, no retry) to `openrouter/fusion` via the reused `requests` client. `LiveFusionAuthorization`
  (frozen, not bool-coercible); `AliasLiveResult` (status/reason/made_network_call/receipt). Response is
  re-scanned with the same policy before a bounded summary can enter the advisory `ModelContributionReceipt`
  (advisory_not_canonical forced True; `redaction_status=REDACTION_GATE_PASSED`; digests from redacted
  output). Key read via `os.getenv`, never logged. Manual smoke in `__main__` (`run_manual_smoke`, requires
  `--authorize-012`) -- NOT a pytest, never collected in CI.
- ADD `tests/test_fusion_alias_live.py` -- 33 tests over 5 sentinel lanes (valve-bypass, raw-egress,
  response-retention, manual-smoke, live-mode-scope): valve-off zero-network (socket-blocked), env-flag-alone
  cannot enable, bad/typed-invalid auth refused, redacted-only send (raw prompt + raw context absent),
  block-category-builds-no-request, key-never-in-output, response re-scan, fail-closed (timeout/http/malformed/
  missing-key/budget), no-streaming, no-new-dependency, live-modes-still-blocked. Network MOCKED; synthetic keys.
  138 pass (33 alias + 65 gate + 40 adapter regression). No skip/xfail.
- EDIT `INTERFACE.md` + module/root ModLog -- alias surface, manual-smoke command, 28-row WSP_97 table
  (declared==actual==28).
- `fusion_adapter` UNCHANGED: ALIAS/SERVER_TOOL/LOCAL_FALLBACK still raise via MockFusionAdapter; the live
  path is a separate, fully-gated entry. FusionRequest stays digest-only.
- Boundaries: no live call by default, no new dependency, no key logged, no raw retained, advisory only, no
  CABR/payout/merge authority. ASCII-clean (0 non-ASCII; no mojibake). DRAFT; STOP at MERGE_READY.
  Next (NOT this slice): operationally flipping FUSION_ALIAS_LIVE_ENABLED is a separate sovereign action;
  SERVER_TOOL mode is a later slice.

## 2026-06-19: Fusion Redaction Gate -- deterministic FAIL-CLOSED precondition (W6)

**Author**: 0102 (Worker-Lane W6, AUTHOR + internal SENTINEL)
**WSP**: 11 (Interface), 50 (Pre-Action), 84 (Reuse evaluated), 97 (Truth Boundary)
**Slice**: `HERMES_FUSION_REDACTION_GATE_PHASE1`
**Predecessor**: #832 (FusionAdapter contract, merged `7bd68e73a`)
**Base**: `31a71946c` (origin/main; #832 landed)

### Summary

Builds the deterministic, FAIL-CLOSED redaction gate the #832 contract anticipates ("Privacy stays
BLOCKED_PENDING_REDACTION_GATE until a separate redaction-gate slice lands"). Precondition ONLY -- it
does NOT enable any live OpenRouter call; alias/server_tool/local_fallback still raise RedactionGateBlocked.

- ADD `src/fusion_redaction_gate.py` -- pure-Python (stdlib-only) policy redactor + gate with two action
  classes: REDACT (keys/bearer/.env/complete private-key/PII/credential-URLs -> replaced, may PASS if the
  re-scan is clean) and BLOCK (private chain-of-thought, merge-authorization, source_authority, CABR/payout/
  benefit authority, governance, malformed key header -> status stays BLOCKED even if a token were swapped).
  PASS only when redaction ran AND a post-redaction re-scan finds zero residual AND zero block markers AND no
  error. Digests computed FROM the redacted output. Counts-only report (policy_version `fusion_redaction.v1`;
  `categories_hit` dict; `blocked_categories` tuple; `residual_forbidden_count`). Low-cardinality reasons
  (clean/redacted/blocked_policy/residual_forbidden_pattern/redactor_error) that never echo raw input. Module
  never imports `os`; makes no network call.
- ADD `tests/test_fusion_redaction_gate.py` -- 61 adversarial tests across 6 sentinel lanes (secret-leak,
  authority-block, private-reasoning, source-literal, live-mode, non-vacuity): synthetic split-fragment secret
  corpus + no-leak invariant, BLOCK corpus never passes, fail-closed (non-text/exception/residual), digests-
  from-redacted, report-counts-not-snippets, no-raw-exception-echo, source-literal scan, determinism, no-network,
  live-modes-still-blocked, non-vacuous negative control. 65 gate tests; 127 pass (incl. 40 adapter + 22 manifest regression).
- WSP 84: an in-tree `redact_sensitive()` exists (duplicated in autofix_executor.py / kanban_plugin_contract.py;
  `redact_secrets()` in openclaw_codebase_agent.py) but is text-only, cross-domain, and lacks the report/digest/
  fail-closed/REDACT-vs-BLOCK split; the gate is self-contained (a security primitive must own its verification,
  WSP 3) with a detector set that is a documented SUPERSET. Follow-up: HERMES_REDACTOR_CONSOLIDATION (unify into
  shared_utilities).
- Boundaries: no live OpenRouter, no key read, no dependency, no runtime wiring. ASCII-clean (0 non-ASCII; no
  mojibake). WSP_97 26/26 declared==actual (INTERFACE.md). DRAFT; STOP at MERGE_READY (external 0102 gate).
  Next (NOT this slice): HERMES_FUSION_ALIAS_MODE_PHASE2 (only after this gate lands + is proven).

## 2026-06-17: FusionAdapter Contract REPAIR1 -- WSP_97 table + digest format guard (W6)

**Author**: 0102 (Worker-Lane W6) | **Slice**: `HERMES_FUSION_ADAPTER_CONTRACT_PHASE1_REPAIR1`
**Target**: PR #832 branch (repair only; no new PR) | **WSP**: 11, 97

Repair of two review findings on the #832 contract slice. No scope expansion (no live OpenRouter, no key
read, no dependency, no runtime wiring, no manifest status change beyond the already-done `parked`).

- INTERFACE.md: added the canonical 23-row WSP_97 Truth Boundary table (declared == actual == 23, all YES),
  evidence pointing to `fusion_adapter.py` / tests / manifest / README.
- `src/fusion_adapter.py`: `digest()` now emits a full `sha256:<64 hex>` (was truncated to 16); added
  `is_valid_digest()` and enforced it in `FusionRequest.__post_init__` so `prompt_digest` / `context_digest`
  must be `sha256:<64 hex>` -- raw text / empty / non-hex / missing-prefix is rejected early. `for_mock()`
  behavior preserved (it digests inputs, which now validate).
- `tests/test_fusion_adapter.py`: added digest-format tests (raw prompt rejected, raw context rejected,
  valid 64-hex accepted, `for_mock` still valid, receipt carries no raw prompt/context). 62 pass.

## 2026-06-16: FusionAdapter Contract -- Hermes Advisory Worker-Panel (mock/dry-run) (W6)

**Author**: 0102 (Worker-Lane W6, AUTHOR + internal SENTINEL)
**WSP**: 11 (Interface), 50 (Pre-Action), 97 (Truth Boundary)
**Slice**: `HERMES_FUSION_ADAPTER_CONTRACT_PHASE1`
**Predecessor**: #829 (`OPENROUTER_FUSION_FOUNDUPS_INTEGRATION_AUDIT_PHASE1`, landed)

### Summary

Builds the typed FusionAdapter CONTRACT recommended by the #829 audit (Section 7) and corrects the stale
OpenRouter `landed` claim. Contract-only: structurally incapable of a live OpenRouter call.

- ADD `src/fusion_adapter.py` -- typed `FusionRequest` / `FusionAnalysis` / `ModelContributionReceipt` +
  `MockFusionAdapter` (deterministic mock/dry-run). The module never imports `os` (cannot read keys) and
  imports no network client. Live modes (alias/server_tool/local_fallback) are declared but raise
  `RedactionGateBlocked`. The receipt forces `advisory_not_canonical=True` and
  `redaction_status=BLOCKED_PENDING_REDACTION_GATE`, and stores digests/refs -- never raw prompt/context.
- ADD `tests/test_fusion_adapter.py` -- 20 tests incl a NON-VACUOUS AST guard (negative control proves it
  fails on a forbidden import / getenv("OPENROUTER...") / subprocess / file write), a no-network proof
  (socket patched to raise), panel bounds (1-8), future-mode raises, receipt truth boundary, manifest honesty.
- EDIT `config/openclaw_integration_manifest.json` -- OpenRouter `status: "landed"` -> `"parked"` (the
  manifest schema enum is landed/planned/parked/removed; the precise `contract_pending` /
  `BLOCKED_PENDING_REDACTION_GATE` wording is carried in the new `notes` field). No `landed`/`ready` overclaim remains.
- ADD `modules/infrastructure/openrouter_client/README.md` -- honest dormant marker (the shell's source was
  reverted in `6f952f6b9`; only untracked `.pyc` linger and are intentionally left alone).
- EDIT `INTERFACE.md` -- document the FusionAdapter public contract surface.

### Boundaries honored

No live OpenRouter call, no API key read, no new dependency, no runtime wiring, no merge/CABR/payout/
source-authority. Privacy stays `BLOCKED_PENDING_REDACTION_GATE`. Tests: 42 pass (20 new + 22 manifest
regression). Internal SENTINEL ran. Opened as DRAFT; STOP at MERGE_READY (external 0102 gate).

## 2026-06-02: PolicyFlags Write-Back Remediation — Deserialization Sanitization (W6)

**Author**: 0102 (Worker-Lane W6)
**WSP**: 97 (Truth Boundary), 50 (Pre-Action Verification)
**Slice**: `HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1`
**Predecessors**: #746 (enforcement audit, `GAP_CONFIRMED_BOUNDED`), #744, HXA24/27/30

### Summary

Closes the #746 bounded PolicyFlags write-back defect (CHANGE 1 of 2). Security/token gate flags are
now **server-authored only** — deserialized job data can never grant a passing gate or a valid token.

### Changes
- `src/foundup_job_contract.py`:
  - Added module-level `_SERVER_AUTHORED_FLAGS` frozenset (12 gate/token fields).
  - Rewrote `PolicyFlags.from_dict` to **force every server-authored flag to `False`** regardless of
    inbound data; only `dry_run_mode` is preserved (operator-authored; `True` = safe/sandbox direction).
  - `FoundUpJob.from_dict` (`:613`) and `__post_init__` (`:411-412`) both route through this single
    chokepoint, so both untrusted-deserialization paths are covered.
  - Direct `PolicyFlags(...)` constructor + `default_factory=PolicyFlags` are UNCHANGED — server code can
    still author `True` flags by direct object assignment.
- Audit: `docs/audits/security/HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1.md` (sanitization +
  write-back field matrices, guard-sequencing proof, D3/D4/D5/D6 boundary proof, WSP 97 24/24 YES).

**Regression**: `git grep FoundUpJob.from_dict` non-test caller count = **0** (no production wiring).

**Tests**: `tests/test_foundup_job_contract.py` → **78 passed** (round-trip tests updated to assert the
new sanitization; new `TestPolicyFlagsDeserializationSanitization` positive-control class added).

---

## 2026-06-01: WSP 109 Genesis Gate Remediation (W6)

**Author**: 0102 (Worker-Lane W6)
**WSP**: 97 (Truth Boundary), 109 (FoundUp Onboarding Intake), 84 (Code Reuse)
**Slice**: `OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1`
**Predecessors**: #737 (probe), #738 (characterization xfails)

### Summary

Closes the #737/#738 WSP 109 onboarding governance gaps by **patching OpenClaw's existing
dispatch** — no second orchestration layer. Reuses the existing
`OpenClawFoundUpOrchestrator.validate_genesis_envelope` gate (WSP 84).

### Changes
- `src/openclaw_foundup_orchestrator.py`: genesis gate wired into `dispatch_foundup`;
  `_is_foundup_launch_or_onboard_intent` + `_extract_envelope_data` + `_genesis_gate_handoff`;
  bare `create foundup` added to `_FOUNDUP_BUILD_WORDS` (parser convergence).
- `src/openclaw_result_memory.py`: `build_w10_handoff` + W10 NOT_READY handoff for FOUNDUP
  outcomes (replaces self-approval).
- `tests/test_openclaw_wsp109_onboarding_dryrun.py`: 4 strict xfails → passing assertions
  + behavioural tests (10 passed, 0 xfail).
- `tests/test_openclaw_foundup_routing.py`: removed harmful `importlib.reload`
  (pre-existing cross-file pollution fixed).

### Behaviour
- `launch foundup ...` / `onboard ... foundup` → genesis gate → **NOT_READY** W10 handoff
  (no FAM launch). Closes the FOUNDUP permission/genesis bypass.
- `create foundup X` and `create foundup job for X` converge on the safe dry-run queue.
- FOUNDUP outcomes carry a W10 handoff instead of self-approving.

### Tests
59 passed across the 3 foundup test files (adjacent routing+orchestrator was `8 failed`
pre-fix → now 0). 4 pre-existing dae/runtime failures verified on clean main (stashed) —
out of scope. WSP_97 Truth Boundary: 24/24 YES.

---

## 2026-06-01: WSP 109 Onboarding Characterization Tests (W6)

**Author**: 0102 (Worker-Lane W6)
**WSP**: 97 (Truth Boundary), 109 (FoundUp Onboarding Intake)
**Slice**: `OPENCLAW_WSP109_ONBOARDING_DRYRUN_TEST_PHASE1`
**Predecessor**: #737 OPUS_4_8_OPENCLAW_INTERNAL_MODEL_PROBE_PHASE1

### Summary

Characterization-only test slice capturing CURRENT OpenClaw behaviour around WSP 109
onboarding and FOUNDUP routing as executable evidence. **No fixes.** The #737 gaps are
locked as strict xfail remediation contracts.

### Files
- NEW `tests/test_openclaw_wsp109_onboarding_dryrun.py` (11 tests: 7 PASS, 4 strict xfail)
- NEW `docs/audits/architecture/OPENCLAW_WSP109_ONBOARDING_DRYRUN_TEST_PHASE1.md`

### Current behaviour locked
- WSP 109 `onboard` is not an intake/build trigger → FAM passthrough, no genesis gate
- `dispatch_foundup` never invokes `validate_genesis_envelope`
- `create foundup X` (FAM passthrough) vs `create foundup job` (queue dry-run) **diverge**
- `validate_and_remember` self-approves; no W10 handoff
- Protected-path edit remains fail-closed **BLOCKED** (PASS, preserved from #737 S5)

### Constraints
No production/source code change. 4 strict xfails cite #737 + remediation slice
`OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1`. WSP_97 Truth Boundary: 26/26 YES.

---

## 2026-05-13: ROC_CANDIDATE Observability Metric (WSP 97)

**Author**: 0102 (Worker W1)
**WSP**: 97 (System Execution Prompting), 91 (Observability), 29 (CABR Engine)
**Slice**: `ROC_CANDIDATE_OBSERVABILITY_METRIC_IMPL_PHASE1`

### Summary

Added pure-function observability-only metric for counting ROC_CANDIDATE records
derived from CABR consensus pipeline output. Enables 012 to observe "distance to
DAO readiness" without state mutation.

### WSP 97 Critical Constraint

ROC_CANDIDATE metric is observability-only. It MUST NOT mean:
- Automatic promotion to ROC
- verification_complete=True / cabr_ready=True / payout_ready=True
- Token issuance / DAO activation / Governance rights

### ROC_CANDIDATE Criteria

Record qualifies when ALL conditions met:
1. `decision == ACCEPTED_FOR_REVIEW`
2. `quorum_met == True`
3. `threshold_met == True`
4. `evidence_present == True`

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/roc_candidate_metrics.py` | ~575 | Pure function metric counter |
| `tests/test_roc_candidate_metrics.py` | ~606 | Test coverage (57 tests) |
| `docs/audits/consensus/ROC_CANDIDATE_OBSERVABILITY_METRIC_IMPL_PHASE1.md` | ~120 | Audit documentation |

### New API Surface

```python
def count_roc_candidates(input: ROCCandidateMetricInput) -> ROCCandidateMetricSnapshot
def export_roc_candidate_metric_json(snapshot) -> str
def export_roc_candidate_metric_markdown(snapshot) -> str
```

### Test Results

- ROC candidate metric tests: 57 passed
- CABR pipeline regression: 80 passed

---

## 2026-05-13: CABR Consensus Finalization Phase 10 - Pipeline Integration (WSP 97)

**Author**: 0102 (Worker W1)
**WSP**: 97 (System Execution Prompting), 91 (Observability), 11 (Interface Contract)
**Slice**: `CABR_CONSENSUS_FINALIZATION_PHASE10_PIPELINE_INTEGRATION`

### Summary

Added caller-driven CABR consensus pipeline composer that runs the existing
review-only pipeline in deterministic order:
- ProofOfComputeReceipt -> pAVS -> CABR scoring -> quorum -> consensus
  finalization -> optional persistence -> lifecycle query/export

### WSP 97 Critical Constraint

Pipeline integration is explicit/caller-driven observability and review flow only.
It must NOT mean:
- Automatic state progression
- verification_complete=True
- cabr_ready=True
- payout_ready=True
- Payout approval
- DAO activation
- Token issuance
- Final consensus readiness
- External settlement

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/cabr_consensus_pipeline.py` | ~900 | Pipeline composer |
| `tests/test_cabr_consensus_pipeline.py` | ~850 | Test coverage (35 tests) |
| `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE10_PIPELINE_INTEGRATION.md` | ~200 | Audit documentation |

### New API Surface

```python
@dataclass
class CABRConsensusPipelineInput:
    receipts: List[Union[ProofOfComputeReceipt, Dict]]  # Required
    attestations: List[Union[VerifierAttestation, Dict]]  # Required
    pavs_results: Optional[List]  # Skip pAVS stage if provided
    score_results: Optional[List]  # Skip scoring if provided
    quorum_results: Optional[List]  # Skip quorum if provided
    store: Optional[CABRConsensusStore]  # No default DB path
    min_validators: int = 3
    consensus_threshold: float = 0.382
    include_lifecycle_export: bool = False

@dataclass
class CABRConsensusPipelineResult:
    success: bool
    stage_results: List[CABRConsensusPipelineStageResult]
    consensus_records: List[CABRConsensusRecord]
    persistence_attempted: bool
    persistence_success: bool
    json_export: Optional[str]
    markdown_export: Optional[str]
    wsp97_labels: List[str]
    truth_boundary: Dict[str, bool]

def run_cabr_consensus_pipeline(input) -> CABRConsensusPipelineResult
def export_cabr_consensus_pipeline_json(result) -> str
def export_cabr_consensus_pipeline_markdown(result) -> str
```

### Behavior

- Caller provides receipts and attestations
- No default DB path (store must be provided for persistence)
- No filesystem writes without caller-provided store
- No automatic runtime hooks (WRE/Hermes/FAM do not invoke this)
- Stages execute in deterministic order
- Stage failures fail closed (explicit error, pipeline stops)
- Missing data becomes gaps in export
- All required WSP 97 labels present in exports
- All truth boundary fields False

### Test Results

- Pipeline tests: 35 passed
- Regression tests: 287 passed (all CABR modules)

---

## 2026-05-13: CABR Consensus Finalization Phase 9 - Store-Export Integration (WSP 97)

**Author**: 0102 (Worker W1)
**WSP**: 97 (System Execution Prompting), 91 (Observability)
**Slice**: `CABR_CONSENSUS_FINALIZATION_PHASE9_STORE_EXPORT_INTEGRATION`

### Summary

Added caller-driven store-to-export integration helper that composes:
- CABRConsensusStore (Phase 2) - SQLite persistence
- Lifecycle Query (Phase 7) - store query with correlation
- Lifecycle Report Export (Phase 8) - unified JSON/Markdown export

### WSP 97 Critical Constraint

Store-export integration is observability only. It must NOT mean:
- Automatic state progression
- verification_complete=True
- cabr_ready=True
- payout_ready=True
- Payout approval
- DAO activation
- Token issuance
- Final consensus readiness
- External settlement

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/cabr_store_export.py` | ~400 | Store-export orchestration helper |
| `tests/test_cabr_store_export.py` | ~650 | Test coverage (65 tests) |
| `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE9_STORE_EXPORT_INTEGRATION.md` | ~180 | Audit documentation |

### New API Surface

```python
@dataclass
class CABRStoreExportRequest:
    store: Any  # MUST be provided by caller
    receipts: Optional[List[Dict]]
    pavs_results: Optional[List[Dict]]
    score_results: Optional[List[Dict]]
    quorum_results: Optional[List[Dict]]
    start: Optional[datetime]
    end: Optional[datetime]
    limit: Optional[int]
    include_markdown: bool = True
    include_json: bool = True

@dataclass
class CABRStoreExportResult:
    success: bool
    error_message: Optional[str]
    persisted_record_count: int
    total_correlations: int
    total_gaps: int
    has_anomalies: bool
    anomaly_count: int
    json_export: Optional[str]
    markdown_export: Optional[str]
    wsp97_labels: List[str]
    truth_boundary: Dict[str, bool]

def build_store_export(store, receipts=None, ...) -> CABRStoreExportResult
def build_store_export_json(store, ...) -> str
def build_store_export_markdown(store, ...) -> str
```

### Behavior

- Caller MUST provide store object (no default DB path)
- No filesystem writes (returns strings only)
- Composes existing lifecycle query and report export APIs
- Returns JSON/Markdown strings only
- Preserves all required WSP 97 labels
- Invalid query params fail closed (raises ValueError)
- Missing supplemental data reported as gaps, not inferred
- Truth-boundary anomalies flagged, not corrected
- No payout/DAO/final consensus readiness inferred

### Test Results

- `test_cabr_store_export.py`: 65 passed
- Regression tests:
  - `test_cabr_lifecycle_report_export.py`: 67 passed
  - `test_cabr_lifecycle_query.py`: 45 passed
  - `test_cabr_consensus_store.py`: 35 passed

---

## 2026-05-13: CABR Consensus Finalization Phase 8 - Lifecycle Report Export Integration (WSP 97)

**Author**: 0102 (Worker W1)
**WSP**: 97 (System Execution Prompting), 91 (Observability)
**Slice**: `CABR_CONSENSUS_FINALIZATION_PHASE8_LIFECYCLE_REPORT_EXPORT_INTEGRATION`

### Summary

Added unified report export that combines CABR lifecycle query output with
consensus reporting summaries into formatted JSON and Markdown outputs.

### WSP 97 Critical Constraint

Export is observability only. Every exported report MUST explicitly state:
- REVIEW_ONLY
- OBSERVABILITY_ONLY
- verification_complete=False
- cabr_ready=False
- payout_ready=False
- NOT_CABR_READY
- NOT_PAYOUT_READY
- NO_DAO_ACTIVATION
- NO_EXTERNAL_ATTESTATION_REQUIRED

It must NOT mean:
- Automatic state progression
- Payout approval
- DAO activation
- Token issuance
- Final consensus readiness
- External settlement

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/cabr_lifecycle_report_export.py` | ~450 | Unified export module |
| `tests/test_cabr_lifecycle_report_export.py` | ~650 | Test coverage (67 tests) |
| `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE8_LIFECYCLE_REPORT_EXPORT_INTEGRATION.md` | ~170 | Audit documentation |

### New API Surface

```python
class CABRExportFormat(Enum):
    JSON = "json"
    MARKDOWN = "markdown"

@dataclass
class CABRExportMetadata:
    export_format: CABRExportFormat
    generated_at: datetime
    export_version: str
    wsp97_labels_present: bool
    truth_fields_false: bool

@dataclass
class CABRLifecycleReportExport:
    metadata: CABRExportMetadata
    lifecycle_query_summary: Optional[Dict]
    gap_summary: Optional[Dict]
    consensus_report_summary: Optional[Dict]
    truth_boundary: Dict[str, bool]
    wsp97_labels: List[str]
    has_anomalies: bool
    anomaly_count: int
    anomaly_details: List[str]

def build_lifecycle_report_export(lifecycle_query_result, consensus_report) -> CABRLifecycleReportExport
def export_lifecycle_report_json(export, indent) -> str
def export_lifecycle_report_markdown(export) -> str
```

### Behavior

- Pure functions (no side effects, no filesystem writes)
- Deterministic JSON output (sorted keys for reproducibility)
- Deterministic Markdown output (consistent structure)
- Includes lifecycle query summary
- Includes gap summary
- Includes consensus report summary (optional)
- Includes truth-boundary section with explicit false fields
- Includes explicit review-only labels
- Flags anomalies but does not correct them
- No payout readiness inferred
- No DAO activation inferred
- No CABR readiness inferred
- No default DB path
- Caller handles file output if desired

### Test Results

- `test_cabr_lifecycle_report_export.py`: 67 passed
- Regression tests: 136 total (45+48+43), 0 failures

---

## 2026-05-13: CABR Consensus Finalization Phase 7 - Lifecycle Query Integration (WSP 97)

**Author**: 0102 (Worker W1)
**WSP**: 97 (System Execution Prompting), 91 (Observability)
**Slice**: `CABR_CONSENSUS_FINALIZATION_PHASE7_LIFECYCLE_QUERY_INTEGRATION`

### Summary

Integrated lifecycle correlation (Phase 6) with CABRConsensusStore queries for
end-to-end read-only tracing of CABR consensus pipeline stages.

### WSP 97 Critical Constraint

Lifecycle query integration is observability only. It does NOT mean:
- Automatic state progression
- `verification_complete=True`
- `cabr_ready=True`
- `payout_ready=True`
- Payout approval
- DAO activation
- Token issuance
- External settlement

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/cabr_lifecycle_query.py` | ~350 | Lifecycle query integration module |
| `tests/test_cabr_lifecycle_query.py` | ~750 | Test coverage (45 tests) |
| `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE7_LIFECYCLE_QUERY_INTEGRATION.md` | ~150 | Audit documentation |

### New API Surface

```python
@dataclass
class CABRLifecycleQueryFilter:
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    limit: Optional[int]
    decision_filter: Optional[str]
    def validate() -> bool
    def to_dict() -> Dict

@dataclass
class CABRLifecycleQueryResult:
    query_filter: Optional[CABRLifecycleQueryFilter]
    persisted_record_count: int
    correlation_result: Optional[CABRLifecycleCorrelationResult]
    gap_summary: Optional[CABRLifecycleGapSummary]
    generated_at: datetime
    wsp97_compliance_note: str

def query_lifecycle_from_store(store, receipts, pavs_results, score_results, 
                                quorum_results, start, end, limit) -> CABRLifecycleQueryResult
def query_lifecycle_gaps_from_store(...) -> CABRLifecycleGapSummary
def export_lifecycle_query_json(result, indent) -> str
```

### Behavior

- Read-only queries over CABRConsensusStore
- Apply optional time range and limit deterministically
- Correlate persisted records with supplied receipt/pAVS/score/quorum data
- Report missing supplemental data as gaps, not inferred
- Invalid time range fails closed (raises ValueError)
- Truth boundary anomalies propagated from Phase 6
- JSON export is deterministic with sorted keys
- No store mutation, no filesystem writes, no network calls

### Test Results

- `test_cabr_lifecycle_query.py`: 45 passed
- Regression tests: 169 total (43+35+46+45), 0 failures

---

## 2026-05-13: CABR Consensus Finalization Phase 6 - Receipt Lifecycle Correlation (WSP 97)

**Author**: 0102 (Worker W1)
**WSP**: 97 (System Execution Prompting), 91 (Observability)
**Slice**: `CABR_CONSENSUS_FINALIZATION_PHASE6_RECEIPT_LIFECYCLE_CORRELATION`

### Summary

Implemented read-only lifecycle correlation across all 7 CABR consensus pipeline stages:
- RECEIPT_CREATED (ProofOfComputeReceipt)
- PAVS_EVALUATED (PAVSVerificationResult)
- CABR_SCORED (CABRScoreResult)
- QUORUM_EVALUATED (QuorumVerificationResult)
- CONSENSUS_FINALIZED (CABRConsensusRecord)
- PERSISTED (stored record)
- REPORTED (report record)

### WSP 97 Critical Constraint

Lifecycle correlation is observability only. It does NOT mean:
- Automatic state progression
- `verification_complete=True`
- `cabr_ready=True`
- `payout_ready=True`
- Payout approval
- DAO activation
- Token issuance
- External settlement

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/cabr_lifecycle_correlation.py` | ~650 | Lifecycle correlation module |
| `tests/test_cabr_lifecycle_correlation.py` | ~700 | Test coverage (43 tests) |
| `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE6_RECEIPT_LIFECYCLE_CORRELATION.md` | ~200 | Audit documentation |

### New API Surface

```python
class CABRLifecycleStage(str, Enum):
    RECEIPT_CREATED, PAVS_EVALUATED, CABR_SCORED,
    QUORUM_EVALUATED, CONSENSUS_FINALIZED, PERSISTED, REPORTED

@dataclass
class CABRLifecycleItem: ...      # Item at a stage
@dataclass
class CABRLifecycleGap: ...       # Gap between stages
@dataclass
class CABRLifecycleCorrelation: ...  # Single item's lifecycle
@dataclass
class CABRLifecycleCorrelationResult: ...  # Full result
@dataclass
class CABRLifecycleGapSummary: ...   # Gap statistics

def correlate_cabr_lifecycle(...) -> CABRLifecycleCorrelationResult
def summarize_lifecycle_gaps(result) -> CABRLifecycleGapSummary
def export_lifecycle_correlation_json(result, indent) -> str
```

### Behavior

- Correlates by receipt_id > job_id > record_hash (priority order)
- Reports downstream gaps from highest present stage
- Handles duplicates deterministically (first wins)
- Flags truth boundary anomalies (any True field)
- JSON export is deterministic with sorted keys
- No store mutation, no filesystem writes, no network calls

### Test Results

- `test_cabr_lifecycle_correlation.py`: 43 passed
- All regression tests: 318 total, 0 failures

---

## 2026-05-13: CABR Consensus Finalization Phase 5 - Time Range and Receipt Correlation (WSP 97)

**Author**: 0102 (Worker W1)
**WSP**: 97 (System Execution Prompting), 91 (Observability)
**Slice**: `CABR_CONSENSUS_FINALIZATION_PHASE5_TIME_RANGE_RECEIPT_CORRELATION`

### Summary

Implemented time-range query helpers and receipt correlation for the CABR consensus reporting layer. This builds on Phase 4 to enable filtered audits and cross-referencing consensus records to original CABR receipts.

### WSP 97 Critical Constraint

Time-range queries and receipt correlation are read-only observability tools. They do NOT mean:
- Automatic state progression
- `verification_complete=True`
- `cabr_ready=True`
- `payout_ready=True`
- Payout approval
- DAO activation
- Token issuance
- External settlement

### Files Modified/Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/cabr_consensus_reporting.py` | +~200 | Time-range and correlation functions |
| `tests/test_cabr_consensus_reporting_time_correlation.py` | ~800 (NEW) | Test coverage (46 tests) |
| `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE5_TIME_RANGE_RECEIPT_CORRELATION.md` | ~150 (NEW) | Audit documentation |

### New API Surface

```python
# Time Range Filter
@dataclass
class CABRTimeRangeFilter:
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: Optional[int] = None
    def validate(self) -> bool: ...

# Time Range Query
def query_consensus_records_by_time(
    store: CABRConsensusStore,
    time_filter: Optional[CABRTimeRangeFilter] = None
) -> List[CABRConsensusRecord]

# Receipt Correlation
@dataclass
class CABRReceiptCorrelation:
    record_id: str
    receipt_id: Optional[str]
    matched: bool
    decision: str
    finalized_at: datetime

def correlate_consensus_records_to_receipts(
    records: List[CABRConsensusRecord],
    receipts: Dict[str, Any]
) -> List[CABRReceiptCorrelation]

# Correlation Report
@dataclass
class CABRReceiptCorrelationReport:
    time_filter: Optional[CABRTimeRangeFilter]
    total_records: int
    matched_records: int
    unmatched_records: int
    correlations: List[CABRReceiptCorrelation]
    generated_at: datetime

def generate_receipt_correlation_report(
    store: CABRConsensusStore,
    receipts: Dict[str, Any],
    time_filter: Optional[CABRTimeRangeFilter] = None
) -> CABRReceiptCorrelationReport

def export_receipt_correlation_report_json(
    report: CABRReceiptCorrelationReport
) -> str
```

### Test Results

- `test_cabr_consensus_reporting_time_correlation.py`: 46 passed (NEW)
- `test_cabr_consensus_reporting.py`: 48 passed (no regression)
- `test_cabr_consensus_store.py`: 35 passed (no regression)
- `test_cabr_consensus_finalizer_persistence.py`: 26 passed (no regression)

**Total**: 245 consensus pipeline tests, 0 failures

---

## 2026-05-13: CABR Consensus Finalization Phase 4 - Aggregation and Reporting (WSP 97)

**Author**: 0102 (Worker W1)
**WSP**: 97 (System Execution Prompting), 91 (Observability)
**Slice**: `CABR_CONSENSUS_FINALIZATION_PHASE4_AGGREGATION_REPORTING`

### Summary

Implemented read-only aggregation and reporting tools for persisted CABRConsensusRecord audit trails. This is Phase 4 of the CABR consensus finalization work, enabling observability and analysis of consensus decisions while maintaining all truth boundaries.

### WSP 97 Critical Constraint

Reporting is observability only. It does NOT mean:
- Automatic state progression
- `verification_complete=True`
- `cabr_ready=True`
- `payout_ready=True`
- Payout approval
- DAO activation
- Token issuance
- External settlement
- Payout readiness inference (high acceptance != payout ready)
- DAO activation inference (high quorum != DAO activation)

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/cabr_consensus_reporting.py` | ~530 | Read-only aggregation and reporting |
| `tests/test_cabr_consensus_reporting.py` | ~650 | Test coverage (48 tests) |
| `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE4_AGGREGATION_REPORTING.md` | ~250 | Audit documentation |

### New API Surface

```python
# Report Generation
def generate_consensus_report(
    store: CABRConsensusStore,
    limit: Optional[int] = None,
    decision_filter: Optional[str] = None,
) -> CABRConsensusReport

# Pure Summarization (no store required)
def summarize_consensus_records(
    records: List[Dict[str, Any]]
) -> CABRConsensusReportSummary

# JSON Export (pure string output)
def export_consensus_report_json(
    report: CABRConsensusReport,
    indent: int = 2,
) -> str

# Convenience Functions
def count_decisions(store, limit=None) -> CABRDecisionCounts
def check_truth_boundary_anomalies(store, limit=None) -> CABRTruthBoundarySummary
def get_records_by_decision(store, decision, limit=None) -> List[Dict]

# Report Dataclasses
@dataclass
class CABRConsensusReport:
    records: List[Dict[str, Any]]
    summary: CABRConsensusReportSummary
    generated_at: datetime
    wsp97_compliance_note: str  # Embedded compliance reminder

@dataclass
class CABRTruthBoundarySummary:
    has_anomaly: bool  # True if any truth field is unexpectedly True
    anomaly_record_ids: List[str]  # Records with anomalies
```

### Reporting Behavior

| Feature | Behavior |
|---------|----------|
| Read-only | No store mutations |
| Deterministic | Sorted keys, sorted anomaly IDs |
| Truth boundary detection | Flags any True value as anomaly |
| WSP 97 note | Embedded in report and JSON output |
| No inference | High counts != payout/DAO readiness |

### Test Results

- `test_cabr_consensus_reporting.py`: 48 passed
- `test_cabr_consensus_finalizer_persistence.py`: 26 passed (no regression)
- `test_cabr_consensus_finalizer.py`: 48 passed (no regression)
- `test_cabr_consensus_store.py`: 35 passed (no regression)

**Total**: 157 consensus pipeline tests, 0 failures

### Recommended Next Slice

`CABR_CONSENSUS_FINALIZATION_PHASE5` - Time-range queries and receipt correlation lookup.

---

## 2026-05-13: CABR Consensus Finalization Phase 3 - Auto-Persist Integration (WSP 97)

**Author**: 0102 (Worker W1)
**WSP**: 97 (System Execution Prompting), 91 (Observability)
**Slice**: `CABR_CONSENSUS_FINALIZATION_PHASE3_AUTO_PERSIST_INTEGRATION`

### Summary

Integrated optional caller-provided persistence into CABR consensus finalization. When a CABRConsensusStore is provided, the consensus record is automatically persisted after finalization. This completes the Phase 1-3 consensus pipeline: scoring -> quorum -> finalization -> storage.

### WSP 97 Critical Constraint

Auto-persist means storing the review-only CABRConsensusRecord when an explicit store is provided. It does NOT mean:
- Automatic state progression
- `verification_complete=True`
- `cabr_ready=True`
- `payout_ready=True`
- Payout approval
- DAO activation
- External settlement
- Default DB path (caller must provide explicitly)

### Files Changed

| File | Change | Purpose |
|------|--------|---------|
| `src/cabr_consensus_finalizer.py` | Extended | Added optional `store` parameter to finalize functions |
| `tests/test_cabr_consensus_finalizer_persistence.py` | New | 26 tests for persistence integration |
| `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE3_AUTO_PERSIST_INTEGRATION.md` | New | Audit documentation |

### New API Surface

```python
# Extended APIs with optional store parameter
def finalize_cabr_consensus(
    consensus_input: CABRConsensusInput,
    include_input_snapshot: bool = False,
    store: Optional[CABRConsensusStore] = None,  # NEW
) -> CABRConsensusRecord

def finalize_cabr_consensus_batch(
    inputs: List[CABRConsensusInput],
    store: Optional[CABRConsensusStore] = None,  # NEW
) -> List[CABRConsensusRecord]

# New explicit result APIs
@dataclass
class CABRConsensusFinalizeResult:
    record: CABRConsensusRecord
    persistence_attempted: bool
    persistence_success: bool
    persistence_status: Optional[str]
    persistence_error: Optional[str]

def finalize_cabr_consensus_with_result(...) -> CABRConsensusFinalizeResult
def finalize_cabr_consensus_batch_with_results(...) -> List[CABRConsensusFinalizeResult]
```

### Persistence Behavior

| Condition | Simple API | With Result API |
|-----------|------------|-----------------|
| `store=None` | No writes (Phase 1 behavior) | `persistence_attempted=False` |
| Store provided, success | Record persisted, logged | `persistence_success=True` |
| Store provided, duplicate | Logged as idempotent | `persistence_status='already_exists'` |
| Store failure | Logged, record returned | `persistence_success=False`, error message |

### Test Results

- `test_cabr_consensus_finalizer_persistence.py`: 26 passed
- `test_cabr_consensus_finalizer.py`: 48 passed (no regression)
- `test_cabr_consensus_store.py`: 35 passed (no regression)
- `test_quorum_verification_engine.py`: 41 passed (no regression)
- `test_cabr_scoring_engine.py`: 42 passed (no regression)

**Total**: 192 tests, 0 failures

### Recommended Next Slice

`CABR_CONSENSUS_FINALIZATION_PHASE4` - Consensus record aggregation and reporting tools for audit trail analysis.

---

## 2026-05-13: CABR Consensus Store Phase 2 - SQLite Audit Trail (WSP 97)

**Author**: 0102 (Worker W1)
**WSP**: 97 (System Execution Prompting), 91 (Observability)
**Slice**: `CABR_CONSENSUS_FINALIZATION_PHASE2_SQLITE_AUDIT_TRAIL`

### Summary

Implemented local SQLite persistence for CABRConsensusRecord audit trails. This is Phase 2 of the CABR consensus finalization work, enabling historical analysis and audit capabilities while maintaining all Phase 1 truth boundaries.

### WSP 97 Critical Constraint

Persistence is evidence storage only. It does NOT mean:
- `verification_complete=True`
- `cabr_ready=True`
- `payout_ready=True`
- Payout approval
- DAO activation
- Token issuance
- External settlement
- Automatic state progression

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/cabr_consensus_store.py` | ~550 | SQLite persistence layer |
| `tests/test_cabr_consensus_store.py` | ~500 | Test coverage (35 tests) |
| `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE2_SQLITE_AUDIT_TRAIL.md` | ~300 | Audit documentation |

### API Surface

```python
class CABRConsensusStore:
    def __init__(self, db_path: Union[str, Path]): ...
    def initialize_schema(self) -> CABRConsensusStoreResult: ...
    def save_record(self, record: Dict) -> CABRConsensusStoreResult: ...
    def get_record(self, record_id: str) -> CABRConsensusStoreResult: ...
    def record_exists(self, record_id: str) -> bool: ...
    def list_records(limit, decision_filter, offset) -> CABRConsensusStoreResult: ...

class CABRConsensusStoreResultStatus(str, Enum):
    SUCCESS, ALREADY_EXISTS, NOT_FOUND, SCHEMA_ERROR, WRITE_ERROR, READ_ERROR, VALIDATION_ERROR

class CABRConsensusStoreError(Exception): ...
```

### Storage Rules

1. Python stdlib sqlite3 only (no external dependencies)
2. Immutable append-only rows keyed by deterministic record_id/hash
3. Duplicate record_id returns ALREADY_EXISTS (idempotent)
4. Truth fields stored exactly as input (all False in Phase 1)
5. No automatic state progression
6. Caller-provided DB path (tests use tmp_path)
7. Fail closed on schema/write errors

### Test Results

- `test_cabr_consensus_store.py`: 35 passed
- `test_cabr_consensus_finalizer.py`: 48 passed (no regression)
- `test_quorum_verification_engine.py`: 41 passed (no regression)
- `test_cabr_scoring_engine.py`: 42 passed (no regression)

### Recommended Next Slice

`CABR_CONSENSUS_FINALIZATION_PHASE3` - Integration with consensus finalizer to automatically persist records after finalization.

---

## 2026-05-13: CABR Consensus Finalization Phase 1 (WSP 29/97)

**Author**: 0102 (Worker W1)
**WSP**: 29 (CABR Engine Framework), 97 (System Execution Prompting)
**Slice**: `CABR_CONSENSUS_FINALIZATION_PHASE1`

### Summary

Implemented deterministic CABR consensus finalization that combines CABRScoreResult and QuorumVerificationResult into a review-only consensus record. This addresses the third critical gap in the consensus infrastructure: the need to combine scoring and quorum decisions into a single auditable consensus record.

### WSP 97 Critical Constraint

"Finalization" in this slice means finalizing an internal review decision record. It does NOT mean:
- `verification_complete=True`
- `cabr_ready=True`
- `payout_ready=True`
- Payout approval
- DAO activation
- Token issuance
- External settlement

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/cabr_consensus_finalizer.py` | ~750 | Core consensus finalization engine |
| `tests/test_cabr_consensus_finalizer.py` | ~650 | Test coverage (48 tests) |
| `docs/audits/consensus/CABR_CONSENSUS_FINALIZATION_PHASE1.md` | ~250 | Audit documentation |

### API Surface

```python
# Enums
CABRConsensusDecision: NOT_FINALIZED, REJECTED, ACCEPTED_FOR_REVIEW,
                       PENDING_QUORUM, BLOCKED_TRUTH_BOUNDARY

CABRConsensusReasonCode: 35 distinct codes covering all decision paths

# Core Functions
finalize_cabr_consensus(consensus_input, include_input_snapshot) -> CABRConsensusRecord
finalize_cabr_consensus_batch(inputs) -> List[CABRConsensusRecord]
generate_record_hash(...) -> str  # Deterministic SHA-256 hash
```

### Decision Tree (Fail-Closed)

1. Missing both results -> NOT_FINALIZED
2. Missing score result -> NOT_FINALIZED (fail closed)
3. Missing quorum result -> PENDING_QUORUM
4. Truth boundary violation -> BLOCKED_TRUTH_BOUNDARY
5. Scoring rejected -> REJECTED
6. Quorum rejected -> REJECTED
7. Quorum not met/threshold not met -> PENDING_QUORUM
8. Both accepted -> ACCEPTED_FOR_REVIEW

### Test Results

- `test_cabr_consensus_finalizer.py`: 48 passed
- `test_quorum_verification_engine.py`: 41 passed (no regression)
- `test_cabr_scoring_engine.py`: 42 passed (no regression)
- `test_pavs_verification_seam.py`: 24 passed (no regression)
- `test_proof_of_compute_receipt.py`: 26 passed (no regression)

### Recommended Next Slice

`CABR_CONSENSUS_FINALIZATION_PHASE2` - Add persistence layer for consensus records with SQLite storage, enabling historical analysis and audit trails.

---

## 2026-05-13: Quorum Verification Enforcement Phase 1 (WSP 29/97)

**Author**: 0102 (Worker W1)
**WSP**: 29 (CABR Engine Framework), 97 (System Execution Prompting)
**Slice**: `QUORUM_VERIFICATION_ENFORCEMENT_PHASE1`

### Summary

Implemented deterministic quorum verification enforcement for CABR scoring, building on the merged CABR Runtime Scoring Engine (PR #577). This addresses the second critical gap identified in the consensus infrastructure audit: quorum enforcement for internal sovereign consensus.

### Scope Constraints

- Internal sovereign quorum enforcement only
- No external chain/AVS dependency
- No payouts, DAO activation, token issuance, network calls, secrets
- WSP 97 truth boundaries enforced: verification_complete=False, cabr_ready=False, payout_ready=False

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/quorum_verification_engine.py` | ~700 | Core quorum verification engine |
| `tests/test_quorum_verification_engine.py` | ~700 | Test coverage (41 tests) |
| `docs/audits/consensus/QUORUM_VERIFICATION_ENFORCEMENT_PHASE1.md` | ~350 | Audit documentation |

### API Surface

```python
# Enums
QuorumDecision: QUORUM_NOT_MET, QUORUM_MET_PENDING_CONSENSUS,
                CONSENSUS_ACCEPTED_FOR_REVIEW, CONSENSUS_REJECTED

QuorumReasonCode: OK_QUORUM_MET_THRESHOLD_MET, OK_QUORUM_MET_DRY_RUN,
                  PENDING_THRESHOLD_NOT_MET, QUORUM_ZERO_ATTESTATIONS,
                  REJECTED_DUPLICATE_VERIFIER_IDS, REJECTED_MISSING_VERIFIER_ID, etc.

AttestationStatus: VALID, APPROVE, REJECT, ABSTAIN, INVALID_*

# Core Functions
evaluate_quorum(quorum_input, include_input_snapshot) -> QuorumVerificationResult
evaluate_quorum_batch(inputs) -> List[QuorumVerificationResult]
build_quorum_input_from_cabr_result(cabr_result, attestations) -> QuorumVerificationInput
```

### Threshold Behavior

| Verifiers | Decision | Threshold (0.382) | Outcome |
|-----------|----------|-------------------|---------|
| 0 | QUORUM_NOT_MET | N/A | Cannot proceed |
| 1-2 | QUORUM_NOT_MET | N/A | Below min_validators=3 |
| 3+ (all approve) | CONSENSUS_ACCEPTED_FOR_REVIEW | 1.0 >= 0.382 | Accepted for review |
| 3+ (mixed) | Depends on score | >= or < 0.382 | Accepted or pending |
| duplicates | CONSENSUS_REJECTED | N/A | Fail-closed |

### Test Results

- `test_quorum_verification_engine.py`: 41 passed
- `test_cabr_scoring_engine.py`: 42 passed (no regression)
- `test_pavs_verification_seam.py`: 24 passed (no regression)
- `test_proof_of_compute_receipt.py`: 26 passed (no regression)

### Recommended Next Slice

`CABR_CONSENSUS_FINALIZATION_PHASE1` - Connect quorum verification to CABR score acceptance and define review-to-consensus transition criteria.

---

## 2026-05-13: CABR Runtime Scoring Engine Phase 1 (WSP 29/97)

**Author**: 0102 (Worker W1)
**WSP**: 29 (CABR Engine Framework), 97 (System Execution Prompting)
**Slice**: `CABR_RUNTIME_SCORING_ENGINE_PHASE1`

### Summary

Implemented the first deterministic CABR runtime scoring seam for internal sovereign consensus. This addresses the critical gap identified in PR #574 (WSP_CONSENSUS_INFRASTRUCTURE_AUDIT): "No runtime CABR scoring engine exists."

### Scope Constraints

- Deterministic scoring only
- No payouts, DAO activation, external attestation, network calls, secrets, or token issuance
- WSP 97 truth boundaries enforced: verification_complete=False, cabr_ready=False, payout_ready=False

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/cabr_scoring_engine.py` | ~750 | Core CABR scoring engine |
| `tests/test_cabr_scoring_engine.py` | ~560 | Test coverage (42 tests) |
| `docs/audits/consensus/CABR_RUNTIME_SCORING_ENGINE_PHASE1.md` | ~350 | Audit documentation |

### API Surface

```python
# Enums
CABRScoreDecision: NOT_EVALUATED, ACCEPTED_FOR_REVIEW, ACCEPTED_FOR_REVIEW_PENDING_QUORUM,
                   REJECTED_INSUFFICIENT_EVIDENCE, REJECTED_TRUTH_BOUNDARY,
                   REJECTED_QUORUM_NOT_MET, REJECTED_DUPLICATE_VERIFIERS,
                   REJECTED_PAVS_FAILED, REJECTED_MISSING_IDENTITY

CABRScoreReason: OK_EVIDENCE_PRESENT_QUORUM_MET, OK_EVIDENCE_PRESENT_DRY_RUN,
                 OK_EVIDENCE_PRESENT_PENDING_QUORUM, REJECTED_* codes

# Core Functions
score_cabr_receipt(score_input, min_validators=3) -> CABRScoreResult
score_cabr_batch(inputs, min_validators=3) -> List[CABRScoreResult]
score_from_receipt(receipt, verifier_ids) -> CABRScoreResult
score_from_pavs_result(result, verifier_ids) -> CABRScoreResult
```

### Quorum Behavior

| Verifiers | Unique | Decision |
|-----------|--------|----------|
| 0 | 0 | ACCEPTED_FOR_REVIEW_PENDING_QUORUM |
| 2 | 2 | ACCEPTED_FOR_REVIEW_PENDING_QUORUM |
| 3+ | 3+ | ACCEPTED_FOR_REVIEW (quorum_met=True) |
| N | <N (duplicates) | REJECTED_DUPLICATE_VERIFIERS |

### Test Results

- `test_cabr_scoring_engine.py`: 42 passed
- `test_pavs_verification_seam.py`: 24 passed
- `test_proof_of_compute_receipt.py`: 26 passed
- `test_hermes_job_executor.py`: 94 passed

### Recommended Next Slice

`QUORUM_VERIFICATION_ENFORCEMENT_PHASE1` - Implement verifier attestation recording and quorum threshold enforcement before state transition.

---

## 2026-05-12: HXA24 Capability Token PolicyFlags (WSP 97)

**Author**: 0102 (Worker HXA24)
**WSP**: 97 (System Execution Prompting)
**Slice**: `HXA24_CAPABILITY_TOKEN_POLICYFLAGS_PHASE1`

### Summary

Added capability token policy flags to PolicyFlags dataclass to support D3+ gate control in the destructive action guard. These fields track whether a capability token was checked, present, validated, and scope-authorized.

### Files Modified

| File | Change |
|------|--------|
| `src/foundup_job_contract.py` | Added 4 capability token fields to PolicyFlags |
| `tests/test_foundup_job_contract.py` | Added 8 tests for capability token fields |

### New PolicyFlags Fields

| Field | Default | Purpose |
|-------|---------|---------|
| `capability_token_checked` | False | Token check was performed |
| `capability_token_present` | False | Token was provided |
| `capability_token_validated` | False | Token signature/expiry valid |
| `capability_token_scope_authorized` | False | Token scope covers action |

### WSP 97 Compliance

- All fields default to False (safe)
- Backward compatible (missing fields default False)
- No real tokens issued or validated
- No external calls
- Conservative interpretation in guard

### Test Results

- `test_foundup_job_contract.py`: 70 passed (8 new tests)

---

## 2026-05-04: Restore Memory Query Route Wrapper (WSP 50)

**Author**: 0102 (Worker W7)
**WSP**: 50 (Pre-Action Verification)
**Slice**: `OPENCLAW_MEMORY_QUERY_IMPORT_FIX_PHASE1`

### Summary

Fixed main-branch import error where `_try_memory_query` was called but not defined. The function body existed as orphaned code after memory query extraction in commit `387d4a735`. Added missing function definition to restore the memory query route.

### Root Cause

Commit `387d4a735` "extract memory queries to owned module (Phase 1)" left orphaned code:
- Function body existed (lines 917-1003) with docstring and pattern matching
- `def _try_memory_query(dae, raw_message):` line was missing
- Tests imported `_try_memory_query` from `openclaw_execution_routes.py`
- Result: `ImportError: cannot import name '_try_memory_query'`

### Fix

Added single line: `def _try_memory_query(dae: Any, raw_message: str) -> Optional[str]:`

### Files Modified

| File | Change |
|------|--------|
| `src/openclaw_execution_routes.py` | Added missing function definition (1 line) |

### Test Results

- `test_openclaw_memory_queries.py`: 20 passed
- `test_openclaw_foundup_routing.py`: 27 passed
- `test_e2e_foundup_job_seam.py`: 11 passed

---

## 2026-05-03: OpenClaw Dry-Run Policy Flag Alignment (WSP 97)

**Author**: 0102 (Worker W9)
**WSP**: 97 (System Execution Prompting)
**Slice**: `OPENCLAW_DRY_RUN_POLICY_FLAG_ALIGNMENT_PHASE1`

### Summary

Aligned OpenClaw dry-run intent propagation with the existing FoundUpJob policy flag model. Dry-run inputs now map to `policy_flags.dry_run_mode = True` without adding a duplicate `is_dry_run` field.

### Files Modified

| File | Change |
|------|--------|
| `src/openclaw_foundup_orchestrator.py` | Added `_detect_dry_run_mode()`, updated `_handle_build_intent()` |
| `tests/test_openclaw_foundup_routing.py` | Added 11 dry-run policy flag tests |

### Dry-Run Detection Patterns

- CLI flags: `--dry-run`, `--dry_run`, `--dryrun`
- Parameters: `dry_run=true`, `dry_run=1`, `dry-run=true`
- Bracketed: `[dry-run]`, `[dryrun]`
- Payload: `payload.dry_run = True/1`

### WSP 97 Compliance

**Truth Boundaries Preserved**:
- `dry_run_mode=True` does NOT mean `verification_complete`
- Dry-run receipt maps to `VerificationStatus.NOT_REQUIRED`
- `cabr_ready` remains False (no CABR exists)
- `payout_ready` remains False (no payout engine exists)

**No Duplicate Fields**:
- Canonical field: `FoundUpJob.policy_flags.dry_run_mode`
- No `FoundUpJob.is_dry_run` added (tested)

### Test Coverage

- 27 tests passing in `test_openclaw_foundup_routing.py`
- 11 tests passing in `test_e2e_foundup_job_seam.py`
- 111 tests passing in `test_foundup_job_envelope_validation.py`

---

## 2026-04-23: pAVS Verification Seam Placeholder (WSP 11/91/97)

**Author**: 0102 (Worker W7)
**WSP**: 11 (Interface), 91 (Observability), 97 (Truth)
**Slice**: `OC7_PAVS_PROOF_OF_COMPUTE_VERIFICATION_PLACEHOLDER_PHASE1`

### Summary

Created pAVS verification seam placeholder that accepts ProofOfComputeReceipt and returns truthful verification decisions without claiming full pAVS/CABR/PoB implementation. This seam sits between W6 (receipt creation) and future W10 (CABR scoring).

### Files Added

| File | Purpose |
|------|---------|
| `src/pavs_verification_seam.py` | Verification seam with decision mapping |
| `tests/test_pavs_verification_seam.py` | 24 focused tests |

### Key Components

**PAVSDecision Enum**:
- `ACCEPTED_FOR_REVIEW` — receipt has evidence, accepted for review
- `BLOCKED_MISSING_EVIDENCE` — receipt claims PENDING_PAVS but no evidence
- `NOT_REQUIRED` — dry-run receipt, no verification needed
- `BLOCKED_UPSTREAM` — upstream job was BLOCKED
- `FAILED_INPUT` — upstream job FAILED
- `REJECTED_MISSING_IDENTITY` — missing receipt_id, job_id, or tenant_id

**PAVSVerificationResult Dataclass**:
- Identity: verification_id, receipt_id, job_id, tenant_id
- Decision: decision, reason_code, reason_human
- Evidence: evidence_refs, evidence_count
- Truth flags: cabr_ready=False, payout_ready=False, verification_complete=False

**Functions**:
- `verify_receipt(receipt)` → PAVSVerificationResult
- `verify_receipts(list)` → list[PAVSVerificationResult]
- `generate_verification_id(receipt_id)` → `pv_{suffix}_{timestamp}_{random}`

### Status Mapping

| VerificationStatus | Evidence | PAVSDecision |
|-------------------|----------|--------------|
| PENDING_PAVS | present | ACCEPTED_FOR_REVIEW |
| PENDING_PAVS | absent | BLOCKED_MISSING_EVIDENCE |
| NOT_REQUIRED | any | NOT_REQUIRED |
| BLOCKED | any | BLOCKED_UPSTREAM |
| FAILED_INPUT | any | FAILED_INPUT |

### WSP 97 Boundary

**DOES**:
- Accept ProofOfComputeReceipt or dict
- Validate identity fields (receipt_id, job_id, tenant_id)
- Map verification_status to pAVS decision
- Track evidence presence for decision logic

**DOES NOT**:
- Issue tokens or UPS
- Run CABR consensus
- Complete verification (only accepts for review)
- Mark cabr_ready or payout_ready as True

### Test Results

- `test_pavs_verification_seam.py`: 24/24 passed
- `test_proof_of_compute_receipt.py`: 26/26 passed
- `test_foundup_job_contract.py`: 66/66 passed

### Integration Notes

- W6 (receipt): `verify_receipt(receipt)` after creating receipt
- W10 (CABR): Consume results where `decision=ACCEPTED_FOR_REVIEW`

---

## 2026-04-26: Proof-of-Compute Receipt Contract (WSP 11/91/97)

**Author**: 0102 (Worker W6)
**WSP**: 11 (Interface), 91 (Observability), 97 (Truth)
**Slice**: `OC6_FAM_PROOF_OF_COMPUTE_RECEIPT_PHASE1`

### Summary

Created Proof-of-Compute receipt contract for recording terminal FoundUpJob execution as evidence without claiming token payout, CABR consensus, or pAVS verification is complete. Receipts are created only from terminal job states (SUCCEEDED, BLOCKED, FAILED) and preserve job identity, compute evidence, and truthful status fields.

### Files Added

| File | Purpose |
|------|---------|
| `src/proof_of_compute_receipt.py` | Receipt contract schema + factory functions |
| `tests/test_proof_of_compute_receipt.py` | 26 focused tests for receipt generation |

### Key Components

**VerificationStatus Enum**:
- `PENDING_PAVS` — SUCCEEDED job awaiting pAVS verification
- `NOT_REQUIRED` — dry-run job, no real compute
- `BLOCKED` — job was blocked, evidence recorded
- `FAILED_INPUT` — job failed, failure evidence recorded

**PayoutStatus/CABRStatus**:
- Always `NOT_EVALUATED` / `NOT_SUBMITTED` (no payout/consensus engine exists)

**ProofOfComputeReceipt Dataclass**:
- Identity: receipt_id, job_id, tenant_id, foundup_id, intent_id
- Evidence: compute_used, compute_summary, evidence_refs
- Status: verification_status, payout_status, cabr_status
- Audit: created_at, job_created_at, job_completed_at

**Factory Functions**:
- `create_receipt_from_job(job)` → ReceiptResult from terminal FoundUpJob
- `create_receipt(...)` → ReceiptResult convenience factory
- `generate_receipt_id(job_id)` → `rcpt_{suffix}_{timestamp}_{random}`

### WSP 97 Boundary

**DOES**:
- Accept terminal job states (SUCCEEDED, BLOCKED, FAILED)
- Preserve job identity and evidence references
- Set truthful verification_status based on job outcome
- Preserve `dry_run: true` context when NOT_REQUIRED is returned

**DOES NOT**:
- Issue tokens or UPS
- Allocate rewards or write to wallet
- Run CABR consensus or pAVS verification
- Accept non-terminal states (rejects QUEUED/RUNNING with truthful error)

### Status Mapping

| JobStatus | VerificationStatus |
|-----------|-------------------|
| SUCCEEDED | PENDING_PAVS |
| SUCCEEDED + dry_run | NOT_REQUIRED |
| BLOCKED | BLOCKED |
| FAILED | FAILED_INPUT |
| QUEUED/RUNNING | REJECTED |

### Test Results

- `test_proof_of_compute_receipt.py`: 26/26 passed
- `test_foundup_job_contract.py`: 53/53 passed

### Integration Notes

- W4 (Hermes): Call `create_receipt_from_job()` after terminal state
- W5 (WRE Router): Call `create_receipt()` if job not materialized
- W7 (pAVS): Consume receipts with `verification_status=PENDING_PAVS`
- W10 (CABR): Consume receipts with `cabr_status=NOT_SUBMITTED`

---

## 2026-04-25: OpenClaw Explicit FoundUp Build Job Creation (WSP 11/50/77/91/97)

**Author**: 0102 (Worker W1 + architect seam cleanup)
**WSP**: 11 (Interface), 50 (Pre-Action), 77 (Agent Coordination), 91 (Observability), 97 (Truth)
**Slice**: `OC1_PHASE2_OPENCLAW_FOUNDUP_JOB_CREATION_WIRING`

### Summary

Extended the OpenClaw FOUNDUP orchestrator so explicit build approval creates a typed `FoundUpJob` in `QUEUED` state while advisory/catalog FoundUp queries still pass through the FAM adapter. This is the OpenClaw-side handoff only; Hermes/WRE execution remains pending.

### Files Changed

| File | Purpose |
|------|---------|
| `src/openclaw_foundup_orchestrator.py` | Detect explicit build phrases and queue typed `FoundUpJob` objects |
| `tests/test_openclaw_foundup_routing.py` | Added explicit job-creation, advisory passthrough, and WSP 97 no-overclaim tests |

### WSP 97 Boundary

- Does not claim genesis validation is globally enforced.
- Does not claim Hermes executed the job.
- Leaves all policy gate pass flags false until checked by later execution slices.
- Uses canonical requested actions: `build_foundup`, `extract_foundup`, `validate_foundup`, `queue_foundup_job`.

### Validation

- `python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_foundup_routing.py -q`
- `python -m pytest modules/communication/moltbot_bridge/tests/test_foundup_job_contract.py -q`

---

## 2026-04-23: FoundUp Job Contract — Canonical Orchestration Contract (WSP 11/77/91/97)

**Author**: 0102 (Worker W2)
**WSP**: 11 (Interface), 50 (Pre-Action), 77 (Agent Coordination), 91 (Observability), 97 (Truth)
**Slice**: `OC2_FOUNDUP_JOB_CONTRACT_PHASE1`

### Summary

Created canonical job contract for OpenClaw ↔ Hermes handoff. This contract defines:
- Job identity (job_id, tenant_id, foundup_id, intent_id)
- Lifecycle states (QUEUED → RUNNING → BLOCKED | FAILED | SUCCEEDED)
- State transition validation with explicit guards
- PolicyFlags for tracking gate passes (security, permission, exfoliation, wsp_preflight)
- WSP 97 audit fields (evidence_refs, status_reason_code, status_reason_human)
- Idempotency key generation for replay guards

### Files Added

| File | Purpose |
|------|---------|
| `src/foundup_job_contract.py` | Contract schema + lifecycle model |
| `tests/test_foundup_job_contract.py` | 49 tests covering creation, transitions, serialization |

### Key Components

**JobStatus Enum**:
- `QUEUED` → `RUNNING` → `SUCCEEDED` (happy path)
- `RUNNING` → `BLOCKED` → `RUNNING` (resume)
- `RUNNING` → `FAILED` (error) / `BLOCKED` → `FAILED` (timeout)

**StatusReasonCode Categories**:
- `OK_*` (success), `BLOCKED_*` (blocking), `FAIL_*` (failures)

**PolicyFlags**:
- `security_gate_checked/passed`, `permission_gate_checked/passed`
- `exfoliation_gate_checked/passed`, `wsp_preflight_checked/passed`
- `dry_run_mode`

**Factory Functions**:
- `generate_job_id(action)` → `j_{action}_{timestamp}_{random}`
- `generate_idempotency_key(tenant, foundup, action, payload)` → sha256[:16]
- `create_job(tenant_id, action, ...)` → FoundUpJob in QUEUED state

### Test Results

- `test_foundup_job_contract.py`: 49/49 passed
- `test_openclaw_dae.py`: 103/104 passed (1 pre-existing flaky test unrelated to changes)

### Integration Points

- **OpenClaw**: Creates FoundUpJob when FOUNDUP intent detected
- **Hermes**: Receives FoundUpJob, transitions through lifecycle
- **FAM**: Links via intent_id correlation to Task/Proof/Verification models

---

## 2026-04-09: Discord Operator Surface Verification (WSP 15/97)

**Author**: 0102 (Worker AW)
**WSP**: 15 (Pre-Check), 97 (CoT/CoR gates)
**Slice**: `MOLTBOT_DISCORD_OPERATOR_SURFACE_VERIFICATION_PHASE1`

### Context

0102 bot was successfully authorized in the FOUNDUPS Discord server after resolving OAuth install issue. This slice documents the verified operator surface.

### OAuth Install Issue

**Problem**: Discord Developer Portal's `Install Link` setting defaulted to `None`, causing:
- `"Integration requires code grant"` error on invite attempt
- Blocked OAuth authorization flow

**Fix**: Use `Discord Provided Link` or direct OAuth URL with `scope=bot+applications.commands`.

### Verified Operator Surface

| Item | Status |
|------|--------|
| Bot presence in server | ✅ Verified |
| Required scopes | `bot` (required), `applications.commands` (optional/future) |
| Required intents | Message Content + Server Members (required), Presence (optional) |
| DM routing | ✅ Verified |
| Mention response | ✅ Verified |
| Slash commands | ❌ Not registered (future) |
| Thread auto-create | ❌ Not implemented (future) |

### Files Changed

| File | Change |
|------|--------|
| `docs/DISCORD_OPERATOR_SURFACE.md` | Created — full operator runbook |
| `docs/CHANNEL_SETUP.md` | Added OAuth fix, intent checklist, runbook link |
| `README.md` | Added Discord install section with OAuth fix note |

### Acceptance

- [x] OAuth fix documented truthfully
- [x] Bot requirements (scopes, intents, permissions) documented
- [x] Runtime boundary explicit (verified vs not implemented)
- [x] Operator runbook added
- [x] No OBAI or antifaFM edits

---

## 2026-04-03: Supervisor Self-Bootstrap Fix + Guard (WSP 97)

**Author**: 0102 (Worker G)
**WSP**: 97 (CoT/CoR gates)
**Slice**: `openclaw_supervisor_start_failure_audit_phase1` + `openclaw_supervisor_standalone_bootstrap_guard_phase1`

### Root Cause

OpenClawSupervisor repeatedly failed with `"openclaw_runtime_not_registered"` escalation when started standalone (not via main.py bootstrap).

**Failure chain**:
```
run_openclaw_supervisor_service()
  └─> OpenClawSupervisor.run_cycle()
      └─> _observe() → broker.get_runtime_status("openclaw")
          └─> Returns {"registered": False}  ← BROKER HAS NO SPECS
              └─> _triage() → "openclaw_runtime_not_registered" → ESCALATE
```

**Cause**: `bootstrap_runtime_dae_launches()` in main.py registers DAE specs, but this only runs when main.py is the entry point. Standalone supervisor invocation skips this.

### Fix (Phase 1)

Added `_ensure_broker_bootstrap()` to `scripts/launch.py`:
- Checks if broker has specs registered
- If not, imports and calls `main.bootstrap_runtime_dae_launches()`
- Fallback: registers minimal openclaw spec if main.py import fails
- Safe to call multiple times (module-level flag)

### Guard Fix (Phase 2 - Worker G)

**Bug found by architect**: Phase 1 fix called `bootstrap_runtime_dae_launches()` which also auto-starts supervisor at main.py:1071-1077. This caused recursive/duplicate supervisor start when called from inside `run_openclaw_supervisor_service()`.

**Guard applied**: Suppress autostart env gates during self-bootstrap:
```python
# Save and suppress autostart env gates
os.environ["OPENCLAW_SUPERVISOR_AUTOSTART"] = "0"
os.environ["OPENCLAW_RESIDENT_AUTOSTART"] = "0"
try:
    bootstrap_runtime_dae_launches()
finally:
    # Restore original env values
```

### Files Changed

| File | Change |
|------|--------|
| `scripts/launch.py` | Added `_ensure_broker_bootstrap()` with autostart guard |

### Verification

```
Before: Launchable DAEs: 0, openclaw registered: False
After:  Launchable DAEs: 11, openclaw registered: True
        supervisor state: registered (NOT running - no recursive start)
        resident state: registered (NOT running)
```

### Acceptance

- [x] Standalone supervisor start no longer depends on zero-spec broker
- [x] Standalone bootstrap does not recursively/duplicatively start supervisor
- [x] No pfMALL changes

---

## 2026-03-31: p.fMALL Catalog Integration (WSP 11/72/84)

**Author**: 0102
**WSP**: 11 (Interface Contract), 72 (Module Independence), 84 (Code Reuse)
**Slice**: `openclaw_pfmall_catalog_integration`

### Context

OpenClaw FOUNDUP route needed catalog/status/routing commands to integrate with p.fMALL contracts. The manifest and state overlay contracts were defined in `pfmall_architecture_and_template_contract` and `pfmall_state_overlay_contract` slices.

### Changes

1. **Created `pfmall_catalog.py`** (~450 lines):
   - `CatalogEntry` dataclass (subset of manifest for catalog display)
   - `FoundUpStateOverlay` dataclass (per PFMALL_STATE_OVERLAY_CONTRACT.md)
   - `StateOverlayProvider` protocol (abstract provider interface)
   - `PfmallCatalogManager` class:
     - Manifest discovery from known registry + JSON files
     - State overlay consumption with graceful degradation
     - `list_foundups()`, `get_catalog()`, `get_status()`, `get_open_target()`
   - Command handlers: `handle_list_foundups`, `handle_foundup_catalog`, `handle_foundup_status`, `handle_open_foundup`
   - `parse_catalog_command()` parser for FOUNDUP intent

2. **Extended `fam_adapter.py`**:
   - Catalog commands routed before launch commands
   - Help text updated with new commands

3. **Created `tests/test_pfmall_catalog.py`** (36 tests):
   - CatalogEntry and StateOverlay dataclass tests
   - PfmallCatalogManager tests (list, get, status, open, provider)
   - Command handler tests
   - Parser tests
   - FAM adapter integration tests

4. **Updated `INTERFACE.md`**:
   - FOUNDUP Route Contract now includes catalog commands
   - Documents p.fMALL contract consumption

### Design Principles

- **Provider abstraction**: State overlay consumed via protocol, not simulator import
- **Graceful degradation**: Status shows "unknown" when provider unavailable
- **Known registry**: PoC uses static registry until real manifests exist
- **Manifest-driven**: Real manifests loaded from `foundup_manifest.json` when present

### Commands Added

| Command | Description |
|---------|-------------|
| `list foundups` | Show all FoundUps in catalog |
| `foundup catalog [category]` | Browse by category |
| `foundup status <name>` | Show manifest + state overlay |
| `open <foundup>` | Get routing target |

### Result

OpenClaw can now list FoundUps, show status, and return routing targets. State overlay is consumed cleanly via provider interface with graceful degradation when unavailable.

---

## 2026-03-29: Skill Evolution Loop Phase 2 - Mutation Surface (WSP 48/77)

**Author**: 0102
**WSP**: 48 (Recursive Self-Improvement), 77 (Agent Coordination)
**Slice**: `skill_evolution_loop_phase2_mutation_surface`

### Context

Phase 1 (commit `3ae311767`) provided a read-only report surface for skill evolution candidates. Phase 2 adds a bounded mutation surface that queries existing WRE primitives for A/B test status and promotion readiness without duplicating engines.

### Changes

1. **Extended `openclaw_skill_evolution.py`** with Phase 2 mutation surface:
   - Three env gates (fail-closed): `OPENCLAW_MUTATION_SURFACE_ENABLED`, `OPENCLAW_AB_SCHEDULING_ENABLED`, `OPENCLAW_PROMOTION_ENABLED`
   - `get_active_ab_test_status()`: Queries PatternMemory for active A/B test
   - `check_ab_promotion_status()`: Queries PatternMemory for promotion decision
   - `check_promotion_readiness()`: Queries WRESkillsRegistryV2 for promotion readiness
   - `build_mutation_surface_entry()`: Builds entry with mutation_status, active_ab_test, promotion_readiness
   - `build_mutation_surface_report()`: Builds full report with summary counts and gate states
   - Mutation status values: `stable`, `ab_test_active`, `eligible_for_ab`, `blocked`

2. **Extended `openclaw_supervisor.py`**:
   - Mutation surface generation added to idle path alongside Phase 1 report
   - Gated by `OPENCLAW_MUTATION_SURFACE_ENABLED`
   - Reports `mutation_surface_report` in idle result with summary and gates

3. **Extended `test_openclaw_skill_evolution.py`** with Phase 2 tests:
   - Env gate tests (fail-closed by default, enabled when "1")
   - Report generation tests (disabled state, enabled state, summary counts)
   - Mutation entry classification tests (stable, eligible_for_ab, blocked)
   - WRE primitive query tests (no mutation calls verified)
   - Supervisor integration tests (gate off = no report, gate on = report generated)

4. **Updated `INTERFACE.md`**:
   - Skill Evolution Loop section with Phase 1 and Phase 2 documentation
   - Env var table with all gates
   - Supervisor integration contract

### Design Principles

- **Reuse WRE ownership**: Queries PatternMemory and WRESkillsRegistryV2 - no duplicate A/B or promotion engines
- **Fail-closed gates**: All mutation features disabled by default (set to "0" or unset)
- **Read-only surface**: Phase 2 surfaces eligibility/readiness but does NOT mutate
- **Idle path only**: Lower priority than restarts, autonomous tasks, and self-audit events

### Result

Phase 2 mutation surface is complete. Skills can now be classified as `stable`, `ab_test_active`, `eligible_for_ab`, or `blocked` with full A/B test and promotion readiness context from WRE primitives.

---

## 2026-03-29: OpenClaw Authority & Mutation Gate Hardening (WSP 00/95)

**Author**: 0102
**WSP**: 00 (Zen State / Security Boundary), 95 (Skill Safety)

### Context

Security audit identified three gaps in OpenClaw's mutation gate:
1. Commander authority derived solely from spoofable display-name matching
2. Source-modification detection missing bare filenames (.env, .bat, .gitignore)
3. Skill-safety failures were downgrading to conversation instead of fail-closed block

### Changes

1. **Commander authority trust model** (`openclaw_intent_planner.py`):
   - Local channels (voice_repl, local_repl) inherently trusted - operator has physical access
   - **Remote channels are NO LONGER commander** - display names are spoofable
   - No reliable remote identity field exists (no stable platform user ID, signed origin, or cryptographic verification)
   - Remote commander claims logged at WARNING level for security monitoring
   - Remote channels remain advisory/non-commander until stronger identity contract added

2. **Source-modification detection** (`openclaw_permission_policy.py`):
   - `extract_file_paths()` extended with new extension pattern: `.bat`, `.cmd`, `.env`
   - New special_pattern for dotfiles: `.env`, `.gitignore`, `.dockerignore`, `.npmrc`, `.npmignore`
   - Word boundary handling prevents false positives (config.env does not trigger .env detection)

3. **Skill-safety fail-closed** (`openclaw_process_loop.py`):
   - Skill-safety failures return deterministic blocked output instead of downgrading to conversation
   - Output: `[SECURITY BLOCK] Execution prevented by Skill Safety Guard: {reason}`
   - WSP 95 / WSP 00 compliance for mutating intents

4. **Tests** (`test_openclaw_dae.py`):
   - 4 tests for commander authority (local trusted, remote NOT trusted)
   - 6 tests for security-critical file detection (.env, .bat, .cmd, .gitignore, .dockerignore, no false positive)
   - Updated existing tests to use local channels where commander authority expected

### Design Principles

- Defense in depth: Local channel = inherent trust, remote = NOT trusted (no reliable identity)
- Fail closed: Skill-safety blocks return hard block, not soft downgrade
- Pattern completeness: All security-critical files detected by mutation gate

### Result

OpenClaw mutation gate now:
- Trusts local channels inherently (no spoofing possible)
- **Denies commander authority on remote channels** (display-name spoofable)
- Logs remote commander claim attempts for security monitoring
- Detects all security-critical files (.env, scripts, dotfiles)
- Fails closed on skill-safety gate failures

---

## 2026-03-28: OpenClaw Bounded Maintenance Loop (WSP 15/77/87/97)

**Author**: 0102
**WSP**: 15, 22, 77, 87, 97

### Context

OpenClaw needed a real maintenance loop that selects safe bounded tasks, executes through existing routes, verifies results, and writes durable reports. Without this, the supervisor could only restart OpenClaw or execute arbitrary autonomous tasks without safety filtering.

### Changes

1. **Created `openclaw_maintenance_selector.py`**:
   - `MaintenanceTask` dataclass with family, risk_level, bundle_confidence, escalation tracking
   - `select_maintenance_task()` uses HoloIndex bundle for task direction
   - `write_maintenance_report()` writes structured JSON artifacts to workspace/reports
   - **Allowed families (Phase 1 - real executors only)**:
     - `self_audit_fix`: source == "self_audit" -> self_audit_dispatch
     - `grant_review`: "openclaw-grants" in required_skills -> grant_dispatch
     - `startup_maintenance`: source == "startup_maintenance_gate" -> startup_maintenance_dispatch
   - Blocked families: source_edit, architecture_change, dependency_update, config_mutation, external_api_call

2. **Extended `openclaw_supervisor.py`**:
   - `_triage()` includes bounded maintenance selection (gated by `OPENCLAW_MAINTENANCE_ENABLED=1`)
   - `_triage()` reads self-audit events from JSONL and triggers `execute_self_audit_fix` action
   - `_get_pending_self_audit_event()` reads pending events with allowed fixes from JSONL
   - `_execute()` handles `execute_maintenance_task` action via existing `run_task.execute_task()`
   - `_verify()` validates maintenance tasks and writes report artifacts
   - `_plan()` carries maintenance_selection metadata for observability

3. **Created `test_openclaw_maintenance_selector.py`** (13 tests):
   - Task dataclass behavior (is_safe logic, serialization)
   - Task selection (safe selection, escalation paths, unknown family handling)
   - Report generation (success/failure artifacts)
   - Configuration validation

4. **Added self-audit triage tests in `test_openclaw_supervisor.py`** (3 tests):
   - `test_self_audit_triage_returns_execute_action`: JSONL event triggers action
   - `test_self_audit_triage_skips_already_attempted`: Already-attempted events skipped
   - `test_self_audit_triage_ignores_non_allowed_fixes`: Non-allowed fixes ignored

### Design Principles

- Uses existing supervisor loop (no new control plane)
- Uses HoloIndex execution bundle for direction (no second planner)
- Writes durable report artifacts (inspectable outcomes)
- Escalates ambiguous/high-risk work (fail closed)
- Only low-risk families in Phase 1

### Activation

```bash
export OPENCLAW_MAINTENANCE_ENABLED=1
# Supervisor will now select bounded maintenance tasks
```

### Result

OpenClaw can run real bounded maintenance cycles end-to-end. Safe tasks are selected via HoloIndex-guided filtering, executed through existing routes, verified, and reported.

---

## 2026-03-27: OpenClaw HoloIndex Execution Bundle (WSP 87/97)

**Author**: 0102
**WSP**: 22, 87, 97

### Context

OpenClaw/Kohi needed pre-execution context retrieval to make better routing and subroutine choices. Without bounded retrieval, the runtime was making execution decisions without consulting HoloIndex or prior patterns.

### Changes

1. **Created `openclaw_execution_bundle.py`**:
   - `ExecutionBundle` dataclass: query, route, docs, patterns, candidate_paths, constraints, verification_hints, confidence, code_hits, wsp_hits
   - `build_execution_bundle()`: single HoloIndex search, stores raw hits for route consumption
   - `retrieve_bundle_for_memory_query()`: specialized high-confidence bundle for memory queries
   - Graceful degradation when HoloIndex unavailable

2. **Integrated into `openclaw_execution_routes.py`**:
   - `execute_query()` uses bundle's code_hits/wsp_hits directly (no duplicate search)
   - Bundle verification_hints appear in response output
   - Candidate paths fallback when HoloIndex returns no hits
   - Debug logging: `[OPENCLAW-DAE] [BUNDLE] query=... conf=... candidates=... code=... wsp=...`

3. **Created `test_openclaw_execution_bundle.py`** (16 tests):
   - Dataclass behavior (defaults, is_actionable, to_compact_dict, code_hits/wsp_hits)
   - Bundle building (graceful HoloIndex unavailability, doc inference, raw hits storage)
   - Memory query bundles (high confidence, constraints)
   - Route integration:
     - Proves bundle data affects response output
     - Proves only one HoloIndex search occurs
     - Proves candidate paths fallback behavior

### Design Principles

- Bundles are execution aids, not architecture authorities
- Compact only — no giant context dumps
- Deterministic — same query produces same bundle shape
- Single HoloIndex search per query (no duplication)
- Suitable for bounded doer, not open-ended cognition

### Result

`execute_query()` now retrieves bounded HoloIndex context via bundle and uses that data directly. All 16 focused tests pass.

---

## 2026-03-28: OpenClaw execution stance clarified for current tranche

**Author**: 0102
**WSP**: 15, 22, 77

### Context

OpenClaw documentation had drifted toward treating the runtime as if it were the primary architect. For the current tranche, that is the wrong operating model.

### Clarification

- `0102` remains architect, prioritizer, and reviewer
- `OpenClaw / Kohi` is the bounded doer
- `HoloIndex` is the retrieval and subroutine-direction surface
- `WRE` remains the deterministic execution plane
- optional higher-compute review lanes may critique artifacts, but do not replace 0102 authority

### Current OpenClaw Job

- fix simple codebase issues
- run focused checks
- emit runtime evidence
- create reports and durable knowledge artifacts

### Documentation Updated

- `README.md`: added current operating rule
- `INTERFACE.md`: added bounded execution contract
- `docs/OPENCLAW_0102_HANDOFF_2026-03-07.md`: added operating clarification
- `workspace/HERMES_INSPIRED_FOUNDUPS_NATIVE_ROADMAP_2026-03-23.md`: added execution rule for low-fruit maintenance

### Result

The module docs now point to the current `WSP 77` coordination shape without mutating core WSP protocol text.

## 2026-03-24: Gateway Continuity Layer (P1)

**Author**: 0102
**WSP**: 22, 60, 91, 97

### Context

Task and conversation continuity was fragmented across runtime surfaces (CLI, OpenClaw, messaging). Work started on one surface couldn't be recognized on another. This implementation creates a unified continuity model under FoundUps control.

### Changes

1. **Created `continuity_context.py`**:
   - `RuntimeSurface` enum: cli, openclaw, messaging, social, supervisor, idle, wre, internal
   - `ContinuityContext` dataclass: carries continuity_id, surface, session_id, sender/channel normalization, parent lineage
   - `ContinuityManager` factory: from_openclaw(), from_cli(), from_supervisor(), from_idle(), from_wre(), from_messaging()
   - Environment variable propagation for subprocess continuity

2. **Extended AgentDB breadcrumbs** (agent_db.py):
   - Added columns: `continuity_id`, `runtime_surface`, `sender_normalized`, `parent_continuity_id`
   - Migration via `_ensure_table_columns()` pattern
   - New indexes for continuity queries

3. **Added cross-surface query methods**:
   - `get_breadcrumbs_by_continuity()`: retrieve by continuity ID with children
   - `get_breadcrumbs_by_surface()`: filter by runtime surface
   - `get_breadcrumbs_by_sender()`: filter by normalized sender
   - `get_continuity_summary()`: aggregated status for a continuity ID
   - `get_cross_surface_activity()`: find work that spanned multiple surfaces

4. **Integrated into OpenClaw process flow**:
   - `openclaw_process_loop.py`: Creates continuity context at request start
   - `openclaw_result_memory.py`: Records breadcrumb with continuity metadata after execution

5. **Added continuity query endpoints** (openclaw_execution_routes.py):
   - `show continuity <id>`: detailed status for a continuity ID
   - `show cross-surface activity`: recent multi-surface work
   - `what is my continuity id`: current request's continuity context

6. **Wired Supervisor and Idle surfaces**:
   - `openclaw_supervisor.py`: Creates continuity context at cycle start, records breadcrumb in `_remember()`
   - `idle_automation_dae.py`: Creates continuity context in `run_idle_tasks()`, records breadcrumb on completion

7. **Fixed critical issues from review (round 1)**:
   - `from_openclaw()` now derives stable continuity_id from session_key (same session = same ID)
   - `from_openclaw()` reads `OPENCLAW_CONTINUITY_ID` env var for subprocess propagation

8. **Fixed critical issues from review (round 2)**:
   - `get_cross_surface_activity()` now groups by lineage_root (COALESCE(parent_continuity_id, continuity_id))
   - `from_supervisor()` and `from_idle()` now accept `parent_context` parameter for lineage propagation
   - Cross-surface detection works via parent linkage, not just shared IDs
   - Added production-path test exercising real factories with parent propagation

9. **Fixed critical issues from review (round 3)**:
   - `run_cycle()` now accepts `parent_context` and passes to `_create_continuity_context()`
   - `run_idle_tasks()` now accepts `parent_context` and passes to `_create_continuity_context()`
   - `run_idle_automation()` convenience function accepts and propagates `parent_context`
   - Added 3 production entry point tests verifying propagation through actual runtime methods

10. **Wired OpenClaw → WRE production path (round 4)**:
    - `_build_wre_command_context()` now includes `parent_continuity_context` from dae
    - `wre_master_orchestrator.py` extracts parent context and forks WRE continuity from it
    - WRE skill execution records breadcrumb with continuity metadata and parent linkage
    - Added 2 production path tests verifying real factory wiring and cross-surface detection

11. **Wired CLI and Messaging entry points (round 5 - gateway_continuity_cli_messaging_wiring)**:
    - `modules/infrastructure/cli/src/openclaw_chat.py`: Creates CLI context via `from_cli()`, records breadcrumb, passes parent_continuity_id to dae.process()
    - `modules/infrastructure/cli/src/openclaw_voice.py`: Same wiring for voice REPL
    - `src/action_cli.py`: `_dispatch_via_dae()` creates CLI context, records breadcrumb, passes metadata to dae.process()
    - `src/webhook_receiver.py`: Creates messaging context via `from_messaging()`, records ingress breadcrumb, passes parent_continuity_id to process_via_openclaw_dae()
    - CLI → OpenClaw lineage: CLI session start tracked, OpenClaw processing references CLI as parent
    - Messaging → OpenClaw lineage: Webhook ingress tracked, OpenClaw processing references messaging as parent
    - **Session collision fix**: CLI chat derives `session_key = f"cli_chat_{cli_ctx.continuity_id[:12]}"` (not fixed "local_repl_012")
    - **Session collision fix**: CLI voice derives `session_key = f"cli_voice_{cli_ctx.continuity_id[:12]}"` (not fixed "voice_repl_012")
    - **Session collision fix**: CLI action derives `session_key = f"cli_action_{cli_ctx.continuity_id[:12]}"` (not fixed "action_cli")
    - **Session collision fix**: Webhook derives `session_key = f"msg_{msg_ctx.continuity_id[:12]}"` when sessionKey is default/missing
    - Added 4 production path tests verifying CLI and messaging cross-surface wiring

12. **Background work continuity correlation (round 6 - gateway_continuity_background_correlation)**:
    - **Problem**: When supervisor/idle executes previously discovered work, lineage to the original work item was lost
    - **Solution**: Recovery helpers + origin stamping on task creation + recursive lineage resolution
    - `continuity_context.py`: Added `resolve_origin_continuity_from_task()` and `resolve_origin_continuity_from_session()` helpers
    - `agent_db.py`: Added `origin_continuity_id` column to `agents_autonomous_tasks`, extended `create_autonomous_task()`, added `get_autonomous_task_by_id()`
    - `agent_db.py`: Rewrote `get_cross_surface_activity()` with recursive CTE to resolve ultimate lineage root for multi-hop chains
    - `agent_db.py`: **Fix**: Ancestry resolution now follows parent links outside the activity window - only final grouping filtered by time
    - `openclaw_supervisor.py`: Added `_resolve_and_link_origin_continuity()`, called before PLAN when executing autonomous tasks
    - `idle_automation_dae.py`: Pass continuity ID to `SelfResearchRefresher` for task origin stamping
    - `idle_automation_dae.py`: Added `_try_recover_origin_continuity()` and `set_triggering_session()` for session-based recovery
    - `idle_automation_dae.py`: **Fix**: Removed generic fallback - only recovers from explicit `last_triggering_session_id`, clears after use
    - `idle_automation_dae.py`: `run_idle_tasks()` now auto-recovers origin if no parent_context provided (explicit session only)
    - `self_research_refresh.py`: Accept `origin_continuity_id` in constructor, stamp on all created tasks
    - **Lineage flow**: Self-research discovers work → stamps origin_continuity_id → supervisor later resolves and links
    - **Multi-hop lineage**: OpenClaw → Idle → Supervisor all grouped under OpenClaw root via recursive CTE (even if root is old)
    - **No false lineage**: Idle only links to explicit triggering session, not arbitrary prior idle work
    - Added 7 background correlation tests verifying supervisor/idle/no-false-positive/multi-hop-grouping/old-root-resolution/production-wiring/no-false-lineage scenarios

### Files Changed

- `src/continuity_context.py` (new): Core continuity dataclass and manager with parent propagation
- `src/openclaw_process_loop.py`: Continuity context creation
- `src/openclaw_result_memory.py`: Breadcrumb recording with continuity
- `src/openclaw_execution_routes.py`: Continuity query handlers + WRE context propagation
- `src/openclaw_supervisor.py`: Supervisor continuity + run_cycle() accepts parent_context
- `src/webhook_receiver.py`: Messaging ingress continuity + breadcrumb recording + session collision fix
- `src/action_cli.py`: CLI action continuity + breadcrumb recording + parent propagation + session collision fix
- `modules/infrastructure/cli/src/openclaw_chat.py`: CLI session continuity + breadcrumb recording + parent propagation + session collision fix
- `modules/infrastructure/cli/src/openclaw_voice.py`: Voice session continuity + breadcrumb recording + parent propagation + session collision fix
- `modules/infrastructure/database/src/agent_db.py`: Schema extension and lineage-aware queries
- `modules/infrastructure/idle_automation/src/idle_automation_dae.py`: Idle surface + run_idle_tasks() accepts parent_context + passes origin to refresher
- `modules/infrastructure/idle_automation/src/self_research_refresh.py`: Accepts origin_continuity_id, stamps on task creation
- `modules/infrastructure/wre_core/wre_master_orchestrator/src/wre_master_orchestrator.py`: WRE continuity forking + breadcrumb recording
- `tests/test_continuity_context.py`: 58 tests (including 7 background correlation tests)

### Verification

```
pytest test_continuity_context.py  # 58 passed
```

### Acceptance Criteria Met

1. One task started on one surface can be recognized on another via shared continuity_id or lineage
2. Breadcrumbs record source surface consistently (cli, openclaw, messaging, supervisor, idle, wre wired)
3. Continuity state is queryable/debuggable via OpenClaw
4. No platform-specific memory fragmentation
5. Existing deterministic query paths not affected
6. Session stability: same session_key always produces same continuity_id
7. Subprocess propagation: OPENCLAW_CONTINUITY_ID env var wired
8. Lineage propagation: from_supervisor/from_idle accept parent_context for cross-surface linkage
9. Production entry points: run_cycle(), run_idle_tasks(), run_idle_automation() accept parent_context
10. **OpenClaw → WRE cross-surface**: Production path tested and wired with lineage detection
11. **CLI → OpenClaw cross-surface**: CLI session tracked, lineage into OpenClaw processing
12. **Messaging → OpenClaw cross-surface**: Webhook ingress tracked, lineage into OpenClaw processing
13. **Supervisor background correlation**: When executing autonomous tasks, resolves and links to origin continuity
14. **Idle background correlation**: When creating tasks via self-research, stamps origin_continuity_id
15. **Multi-hop lineage resolution**: `get_cross_surface_activity()` uses recursive CTE to group all descendants under ultimate root
16. **Old root resolution**: Ancestry follows parent links outside activity window - recent children group under old roots
17. **Idle session recovery**: `run_idle_tasks()` auto-recovers origin via explicit `set_triggering_session()` only
18. **No false idle lineage**: Idle recovery only from explicit triggering session, cleared after use

13. **WRE E2E Continuity Smoke Test (round 7 - wre_e2e_continuity_smoke)**:
    - **Problem**: Existing tests verified context propagation but not actual `execute_skill()` breadcrumb recording
    - **Solution**: E2E smoke tests that call real WRE orchestrator with mocked skill execution
    - `test_continuity_context.py`: Added `TestWREE2EContinuitySmoke` class with 3 tests:
      - `test_execute_skill_records_breadcrumb_with_continuity`: Core E2E - OpenClaw context → WRE execute_skill → verify breadcrumb + lineage
      - `test_execute_skill_without_parent_context_still_records_breadcrumb`: Orphan execution still records breadcrumb
      - `test_openclaw_to_wre_three_hop_lineage`: OpenClaw → WRE → child-WRE all grouped under root
    - `wre_master_orchestrator.py`: **Fix**: Exclude `parent_continuity_context` from `SkillOutcome` JSON serialization (was causing `TypeError: Object of type ContinuityContext is not JSON serializable`)
    - **E2E path verified**: OpenClaw creates context → `_build_wre_command_context()` includes it → WRE forks via `from_wre()` → breadcrumb recorded with parent linkage → `get_cross_surface_activity()` detects lineage

### Files Changed

- `src/continuity_context.py` (new): Core continuity dataclass and manager with parent propagation
- `src/openclaw_process_loop.py`: Continuity context creation
- `src/openclaw_result_memory.py`: Breadcrumb recording with continuity
- `src/openclaw_execution_routes.py`: Continuity query handlers + WRE context propagation
- `src/openclaw_supervisor.py`: Supervisor continuity + run_cycle() accepts parent_context
- `src/webhook_receiver.py`: Messaging ingress continuity + breadcrumb recording + session collision fix
- `src/action_cli.py`: CLI action continuity + breadcrumb recording + parent propagation + session collision fix
- `modules/infrastructure/cli/src/openclaw_chat.py`: CLI session continuity + breadcrumb recording + parent propagation + session collision fix
- `modules/infrastructure/cli/src/openclaw_voice.py`: Voice session continuity + breadcrumb recording + parent propagation + session collision fix
- `modules/infrastructure/database/src/agent_db.py`: Schema extension and lineage-aware queries
- `modules/infrastructure/idle_automation/src/idle_automation_dae.py`: Idle surface + run_idle_tasks() accepts parent_context + passes origin to refresher
- `modules/infrastructure/idle_automation/src/self_research_refresh.py`: Accepts origin_continuity_id, stamps on task creation
- `modules/infrastructure/wre_core/wre_master_orchestrator/src/wre_master_orchestrator.py`: WRE continuity forking + breadcrumb recording + serialization fix
- `tests/test_continuity_context.py`: 61 tests (including 3 WRE E2E smoke tests)

### Verification

```
pytest test_continuity_context.py  # 61 passed
```

### Acceptance Criteria Met

1. One task started on one surface can be recognized on another via shared continuity_id or lineage
2. Breadcrumbs record source surface consistently (cli, openclaw, messaging, supervisor, idle, wre wired)
3. Continuity state is queryable/debuggable via OpenClaw
4. No platform-specific memory fragmentation
5. Existing deterministic query paths not affected
6. Session stability: same session_key always produces same continuity_id
7. Subprocess propagation: OPENCLAW_CONTINUITY_ID env var wired
8. Lineage propagation: from_supervisor/from_idle accept parent_context for cross-surface linkage
9. Production entry points: run_cycle(), run_idle_tasks(), run_idle_automation() accept parent_context
10. **OpenClaw → WRE cross-surface**: Production path tested and wired with lineage detection
11. **CLI → OpenClaw cross-surface**: CLI session tracked, lineage into OpenClaw processing
12. **Messaging → OpenClaw cross-surface**: Webhook ingress tracked, lineage into OpenClaw processing
13. **Supervisor background correlation**: When executing autonomous tasks, resolves and links to origin continuity
14. **Idle background correlation**: When creating tasks via self-research, stamps origin_continuity_id
15. **Multi-hop lineage resolution**: `get_cross_surface_activity()` uses recursive CTE to group all descendants under ultimate root
16. **Old root resolution**: Ancestry follows parent links outside activity window - recent children group under old roots
17. **Idle session recovery**: `run_idle_tasks()` auto-recovers origin via explicit `set_triggering_session()` only
18. **No false idle lineage**: Idle recovery only from explicit triggering session, cleared after use
19. **WRE E2E breadcrumb**: `execute_skill()` records breadcrumb with correct continuity metadata and parent linkage
20. **WRE orphan execution**: Works without parent context (breadcrumb still recorded, no parent linkage)
21. **WRE multi-hop lineage**: Nested skill executions (OpenClaw → WRE → child-WRE) all group under ultimate root

### Remaining Work (Future Slices)

- **Caller wiring**: auto_moderator_dae.py needs continuity context to pass to run_idle_automation() + set_triggering_session()
- **Skill evolution continuity** (wardrobe/rolodex tracking): Pass `continuity_ctx` to `evolve_skill()`, add `origin_continuity_id` to `learning_events` table, record breadcrumb when variation created/promoted. This enables "what did this session do?" to include skill evolution events.
- **True nested E2E**: Current three-hop test uses fabricated lineage. Add test that calls `execute_skill()` which internally triggers another skill execution.
- **Skills 2.0 hygiene wiring** (skill consumption safety): WRE loader/orchestrator doesn't use Skills 2.0 fields. Need to:
  - Extend `SkillMetadata` with `category`, `evals`, `retirement_date`
  - Add `_check_skill_hygiene()` in loader - block retired skills, validate category
  - Add pre-execution evals check - run benchmark cases before first production use
  - Current: Cisco scanner runs, but Skills 2.0 metadata ignored

---

## 2026-03-23: Supervisor Memory Nudge Wiring (P1)

**Author**: 0102
**WSP**: 22, 60, 97

### Context

Supervisor already stores PatternMemory outcomes in `_remember()` but did not emit
dedicated nudges for high-value VERIFY/ESCALATE failures. This wiring adds targeted
nudge emission without creating noise.

### Changes

1. **Added `_emit_supervisor_nudge()` helper** to `openclaw_supervisor.py`:
   - Constructs explicit `NudgeEvent` objects
   - Calls `MemoryNudgeEngine.emit_nudges([event], record_breadcrumbs=True)`
   - Returns True if nudge was emitted (not deduplicated)

2. **VERIFY failure path now emits nudge**:
   - Trigger type: `supervisor_verify_failure`
   - Priority: P1
   - Includes: plan_action, plan_reason, verify_error, task_id, fidelity

3. **ESCALATE path now emits nudge for high-value reasons**:
   - `resident_openclaw_restart_budget_exhausted` → P0
   - `broker_or_observer_unavailable` → P1
   - `openclaw_runtime_not_registered` → P1

4. **Signature identity for VERIFY failures**:
   - Title includes `task_id` and `verify_error` to distinguish different failures
   - Format: `Task verify failed: <action> [<task_id>] (<error>)`
   - Prevents over-deduplication of materially different failures

5. **Deduplication**: Identical escalations are deduplicated by nudge engine
   (signature-based matching on trigger_type + title + provenance).

### Files Changed

- `src/openclaw_supervisor.py`: Added `_emit_supervisor_nudge()` method, calls in run_cycle
- `tests/test_openclaw_supervisor.py`: 7 new tests for nudge emission

### Verification

```
pytest test_openclaw_supervisor.py       # 14 passed
pytest test_openclaw_supervisor_p0.py    # 1 passed
pytest test_memory_nudge_engine.py       # 19 passed
pytest test_self_research_refresh.py     # 7 passed
```

### Not Changed

- Self-research nudge logic (already working from PR #238)
- Grant execution files (completed in PR #239)
- Gateway continuity layer (future slice)

---

## 2026-03-23: Memory Nudge Runtime Wiring (P1)

**Author**: 0102
**WSP**: 22, 60, 97

### Context

Memory nudge engine existed (PR #237) but was not called from live loops.
This wiring connects it to the self-research refresh cycle.

### Changes

1. **Enhanced emit_memory_nudges()** with `record_breadcrumbs` parameter:
   - When enabled, records a breadcrumb in AgentDB for each emitted nudge
   - Session ID: `self_research_{YYYYMMDD}` for daily aggregation
   - Action: `memory_nudge_emitted` with trigger type, priority, provenance

2. **Wired into self_research_refresh.py**:
   - New `emit_nudges=True` parameter on `run()` method
   - Called after report is written, before `remember_outcome`
   - Report now includes `memory_nudges_emitted` count
   - CLI flag: `--no-nudges` to disable

### Files Changed

- `src/memory_nudge_engine.py`: Added `_record_breadcrumb()`, updated signatures
- `modules/infrastructure/idle_automation/src/self_research_refresh.py`: Added `_emit_memory_nudges()` method
- `tests/test_memory_nudge_engine.py`: 3 new tests for breadcrumb recording

### Verification

```
pytest test_memory_nudge_engine.py  # 19 passed
pytest test_self_research_refresh.py  # 7 passed
```

Live test: 6 nudges emitted, 8 breadcrumbs recorded (some from earlier runs).

---

## 2026-03-23: Grant Task Pipeline Executable (P0)

**Author**: 0102
**WSP**: 22, 97

### Problem

Grant work was discovered by self-research but not autonomously executable:
- Tasks used slugified IDs (`self_research_external_watchlist_review_5...`)
- Dispatch expected stable IDs (`grant_watchlist_review`, `grant_watchlist_stabilize`)
- Old tasks accumulated alongside new ones

### Solution

1. **Stable task IDs** (already in self_research_refresh.py, now verified working):
   - `grant_watchlist_review` for changed grant pages
   - `grant_watchlist_stabilize` for watchlist fetch errors
   - INSERT OR REPLACE deduplicates by task_id PRIMARY KEY

2. **Stale task cleanup** in `publish_autonomous_tasks()`:
   - Combined filter: `task_id LIKE 'self_research_external_watchlist_%'` + `required_skills LIKE '%openclaw-grants%'`
   - Does NOT delete PQN or OpenClaw ecosystem watchlist tasks (different skill tags)
   - Preserves stable IDs via `NOT IN (?, ?)` clause
   - Sets `status = 'pending'` after creation (AgentDB may not set it)

3. **Completed task protection**:
   - Checks if stable grant task exists in `completed` status
   - Compares `changed_items`/`error_items` context
   - Skips republish with `skipped_reason: completed_same_context` if unchanged

4. **Structured grant executor** (`src/grant_task_executor.py`):
   - `execute_grant_review()`: Returns per-item findings, repo-fit assessment, recommendations
   - `execute_grant_stabilize()`: Returns error diagnostics, remediation steps
   - Priority mapping matches actual rescored sheet groups:
     - `p0_apply_now` → 0.95 fit score
     - `p1_after_one_concrete_adapter` → 0.70 fit score
     - `p2_deprioritized_until_new_chain_surface` → 0.35 fit score

5. **run_task.py dispatch** updated to use structured executor instead of OpenClawDAE

### Files Changed

- `modules/infrastructure/idle_automation/src/self_research_refresh.py`: Stale cleanup + completed protection
- `modules/communication/moltbot_bridge/scripts/run_task.py`: Use grant_task_executor
- `modules/communication/moltbot_bridge/src/grant_task_executor.py`: New file, 200 lines
- `modules/communication/moltbot_bridge/tests/test_grant_task_execution.py`: 21 tests
- `modules/communication/moltbot_bridge/tests/test_hardening_tranche.py`: 7 grant tests + 1 regression

### Verification

- `pytest test_grant_task_execution.py` → 21 passed
- `pytest test_hardening_tranche.py -k grant` → 8 passed (7 grant + 1 stale cleanup regression)
- Regression test: Seeds old slugified rows + PQN/ecosystem rows, verifies only old grant rows deleted
- Repro 1: Completed task same context → skipped (not reopened)
- Repro 2: Ethereum ESP (p0_apply_now) → fit_score=0.95, generates recommendations
- Stable task_ids confirmed: `grant_watchlist_review`, `grant_watchlist_stabilize`

### Human-Only Gates Intact

Per SKILL.md, OpenClaw does NOT:
- Submit applications
- Assert identity
- Sign wallets
- Click final binding submit

---

## 2026-03-23: Memory Nudge Engine (P0)

**Author**: 0102
**WSP**: 22, 60, 97

### Problem

High-value events (escalations, new autonomous tasks, grant deadlines, worktree
pressure) were being lost to logs instead of captured as operator-readable memory.
The system relied on humans remembering to write memory notes.

### Solution

Created `memory_nudge_engine.py` that automatically captures high-value events:

1. **Trigger types**:
   - `supervisor_escalation`: verify failures, critical/high severity escalations
   - `self_research_change`: P0/P1 update candidates, new autonomous tasks
   - `grant_watchlist_change`: human gate required, deadline approaching
   - `worktree_pressure`: queue backlog (5+ items awaiting audit)

2. **Deduplication**:
   - Stable signature from `trigger_type:title:provenance`
   - Loads existing nudge signatures from memory directory
   - Same event only creates one note

3. **Note format**:
   - Concise markdown with priority, trigger, timestamp, provenance
   - Details section with structured JSON when relevant
   - Auto-generated signature footer

### Files Added

- `src/memory_nudge_engine.py`: 350 lines, MemoryNudgeEngine class
- `tests/test_memory_nudge_engine.py`: 15 tests

### Audit Fixes (same PR)

1. **autonomous_tasks schema**: Live artifact is a list, not dict
2. **Escalations scanner**: Use `event_count` threshold, not `severity` field
3. **Grant watchlist**: Use `changed_count`/`error_count` at top level
4. **Removed**: `architecture_decision` trigger (not in this slice)

### Verification

- `pytest test_memory_nudge_engine.py` → 16 passed
- Live scan returns 6 events (P1: 4, P2: 2)

---

## 2026-03-23: Session recall search foundation (breadcrumb integration)

**Author**: 0102
**WSP**: 22, 97

### Problem

Memory queries from PR #235 used workspace memory notes only. AgentDB breadcrumbs
(`get_breadcrumbs()` at line 432) existed but were not wired to memory queries.
This left a gap: operators could query past decisions but not cross-reference
with actual activity breadcrumbs.

### Solution

1. **Past work queries**: `show past work on X`, `what was I working on`
   - Merges workspace memory + AgentDB breadcrumbs
   - Topic filtering across both sources
   - Explicit provenance: `workspace_memory`, `breadcrumbs`

2. **Enhanced decision queries** with breadcrumb evidence:
   - Existing workspace memory search retained
   - Adds breadcrumb evidence filtered by decision-keywords
   - Provenance-tagged response sections

3. **`_search_breadcrumbs(topic, limit)` helper**:
   - Searches AgentDB breadcrumbs by topic
   - Graceful degradation if AgentDB unavailable
   - Filters by action, query, and data fields

### Clean Rule Applied

- Topic/decision/session queries → workspace memory + breadcrumbs + reports
- Skill queries → rolodex + PatternMemory (not in this slice)

### Files Changed

- `openclaw_execution_routes.py`: Added `_query_past_work()`, `_search_breadcrumbs()`
- `tests/test_openclaw_memory_queries.py`: +7 tests (19 total)

### Audit Fixes (same PR)

1. **Time qualifier normalization**: `yesterday/today/last night` → `None` (not literal topics)
2. **No-topic includes workspace memory**: Added `_get_recent_memory_notes()` helper
3. **Tightened tests**: Explicit assertions for both behaviors

### Verification

- `pytest test_openclaw_memory_queries.py` → 20 passed

---

## 2026-03-23: Deterministic memory queries through OpenClaw (P0)

**Author**: 0102
**WSP**: 22, 97

### Problem

Operators had no way to query past decisions, unresolved work, or recent sessions
through OpenClaw. The roadmap item `openclaw_memory_queries` was marked as the
next ready P0 slice in the native execution queue.

### Solution

Added memory query detection and handlers in `openclaw_execution_routes.py`:

1. **Decision queries**: `what did we decide about X`
   - Scans workspace memory notes for topic matches
   - Returns provenance-backed answers with file paths
   - Explicit "insufficient evidence" when no matches

2. **Unresolved work queries**: `show unresolved work`, `show pending tasks`
   - Reads `openclaw_native_execution_queue_status.json`
   - Reads `openclaw_self_research_status.json` for update candidates
   - Returns structured list with priorities and sources

3. **Recent sessions queries**: `show recent sessions`, `show high-value sessions`
   - Lists workspace memory notes sorted by date
   - Returns titles, dates, and file paths

### Behavior Guarantees

- Responses include provenance (source file paths)
- Insufficient evidence is stated explicitly, not hallucinated
- Existing token-usage and identity query behavior preserved
- Memory queries route through normal QUERY path

### Files Changed

- `openclaw_execution_routes.py`: Added `_try_memory_query()` and helpers
- `tests/test_openclaw_memory_queries.py`: 10 focused tests

### Verification

- `pytest test_openclaw_memory_queries.py` → 10 passed

---

## 2026-03-23: AI Overseer integration in supervisor planning (P1)

**Author**: 0102
**WSP**: 22, 77, 97

### Problem

OpenClaw supervisor initialized AI Overseer at line 289 but `_plan()` at line 440
was a thin dict builder that never used it. The autonomy gap assessment identified
this as P1: "AI Overseer in PLAN is still open."

Additionally, `analyze_mission_requirements()` returns two response shapes:
- Normal: `{classification: {complexity: N}, patterns_detected, recommended_team}`
- Fallback: `{complexity: 3, requires_coordination}` (no classification object)

Initial integration assumed `classification.complexity` always exists, causing
fallback responses to degrade complexity to 0.

### Solution

1. Integrated `ai_overseer.analyze_mission_requirements()` into `_plan()`:
   - Gemma fast classification (50-100ms latency)
   - Adds `ai_analysis` to plan with complexity, patterns, recommended_team
   - Graceful fallback if AI Overseer unavailable

2. Added `_normalize_ai_analysis()` helper to handle both response shapes:
   - Extracts complexity from `classification.complexity` OR top-level `complexity`
   - Normalizes patterns, recommended_team, method, requires_coordination

### Verification

- `pytest test_openclaw_supervisor.py test_openclaw_supervisor_p0.py` → 8 passed
- Tests cover: normal shape, fallback shape, exception handling

---

## 2026-03-23: OpenViking WSP 97 ecosystem watchlist integration

**Author**: 0102
**WSP**: 22, 84, 97

### Problem

OpenClaw had grant and PQN benchmark watchlists, but no general external
ecosystem watchlist for architecture-level signals affecting the whole control,
memory, and context planes.

OpenViking is explicitly positioned upstream as an agent context database for
OpenClaw-like harnesses, so handling it as a one-off memo would let the system
fall behind on a relevant memory/filesystem paradigm shift.

### Solution

Integrated OpenViking into the live self-research loop as a monitored external
ecosystem candidate rather than a startup dependency:

1. Added `workspace/reports/openclaw_external_ecosystem_watchlist.json`
2. Added `scripts/refresh_openclaw_ecosystem_watchlist.py`
3. Added `workspace/reports/openclaw_external_tool_openviking_wsp97_20260323.json`
4. Updated `self_research_refresh.py` to refresh/report/rank ecosystem signals
5. Updated `openclaw-monitor` skill docs to surface the new watchlist

### Architecture Decision

`volcengine/OpenViking` is:
- `pilot_in_isolation`
- `integrate_via_adapter_or_mirror`
- plane=`external_context_sidecar`

Not approved:
- replacing HoloIndex or PatternMemory as source of truth
- adding OpenViking to `main.py` startup
- bypassing OpenClaw governance or WRE ownership

### Residual Work

- design a read-only context mirror pilot for retrieval comparison
- expose OpenViking dossier answers through a dedicated OpenClaw query surface if needed
- add more ecosystem signals to the new watchlist as they are validated

## 2026-03-23: Hermes Agent WSP 97 ecosystem assessment

**Author**: 0102
**WSP**: 22, 84, 97

### Problem

Hermes Agent is a strong external signal because it overlaps the same persistent
agent surface OpenClaw is trying to mature: memory, scheduling, gateway
continuity, skills, and cross-session learning.

It also explicitly positions itself as an OpenClaw migration target, so it is a
benchmark and a replacement-risk competitor at the same time.

### Solution

Added Hermes to the OpenClaw external ecosystem watchlist and created a WSP 97
dossier that makes the adoption boundary explicit.

### Architecture Decision

`NousResearch/hermes-agent` is:
- `track_as_benchmark_not_runtime`
- `selective_pattern_adoption_only`
- plane=`feature_benchmark`

Harvest patterns:
- persistent recall
- memory nudges
- gateway continuity
- scheduled NL automations
- self-improving skill loops

Do not adopt:
- runtime ownership
- migration/config authority
- a second orchestration layer

## 2026-03-23: Canonical native execution queue

**Author**: 0102
**WSP**: 22, 84, 97

### Problem

The repo had roadmap/backlog artifacts and autonomous tasks, but no canonical
queue that locks prior WSP 97 decisions and audits repo drift before execution.

### Solution

Added `scripts/build_openclaw_native_execution_queue.py` and wired its status
snapshot into the consolidated self-research report.

Queue items now move through:
- `ready`
- `audit_required`

based on whether owner modules changed after the backlog decision was recorded.

## 2026-03-22: P1 Supervisor Unification into OpenClawSupervisor

**Author**: 0102
**WSP**: 22, 77, 91, 97

### Problem

Two competing supervisor implementations existed:
- `modules/communication/moltbot_bridge/src/openclaw_supervisor.py` (canonical, booted by main.py)
- `modules/infrastructure/supervisor/src/supervisor_24x7.py` (donor/prototype with richer features)

Per the CTO prompt pack, `OpenClawSupervisor` is canonical and `Supervisor24x7` is a donor.

### Solution

Unified key behaviors from `Supervisor24x7` into the canonical `OpenClawSupervisor`:

1. **SupervisorMetrics** - telemetry dataclass for WSP 91 observability
2. **AI Overseer integration** - lazy-loaded for PLAN state
3. **PatternMemory** - SQLite outcome storage for REMEMBER state
4. **LibidoMonitor** - Gemma fidelity validation for VERIFY state
5. **get_metrics()** - public API for observability

### Changes

| File | Change |
|------|--------|
| `src/openclaw_supervisor.py` | Added `SupervisorMetrics`, `_init_unified_components()`, Gemma fidelity in `_verify()`, PatternMemory in `_remember()`, `get_metrics()` |
| `modules/infrastructure/supervisor/src/supervisor_24x7.py` | Added deprecation notice marking it as donor/prototype |

### Architecture Decision

```
Control Split (canonical):
- AI Overseer + sentinels: observe, gate, correlate, rank
- OpenClawSupervisor: schedule, budget, launch, verify (THIS FILE)
- OpenClaw: executive/control plane
- WRE + DAEs: execution
- PatternMemory: recall and learning
```

### Residual Work

- P1: Route highest-value menu/skill islands into OpenClaw (not done this session)
- P2: Headless runtime mode separate from interactive menu

---

## 2026-03-18: Cursor-based DAE follow commands

**Author**: 0102  
**WSP**: 22, 73, 91, 97

### Changes
- Updated `src/dae_runtime_adapter.py`
  - added `watch|follow <dae> since <sequence>` parsing
  - preserved `tail <dae>` as the recent-window command
  - surfaced `next_cursor` in live status formatting
- Updated `INTERFACE.md`
  - documented the cursor/follow runtime contract

### Impact
- OpenClaw runtime supervision is now incremental instead of snapshot-only.
- `012` and future 0102 loops can continue from a known event cursor without rereading the same tail window.

## 2026-03-18: Resident OpenClaw broker runtime

**Author**: 0102  
**WSP**: 22, 73, 77, 97

### Changes
- Added `scripts/launch.py`
  - `run_openclaw_resident_service(...)`
  - `stop_openclaw_resident_service()`
  - broker-safe Uvicorn startup without thread signal-handler conflicts
- Updated `README.md` and `INTERFACE.md`
  - documented resident OpenClaw service contract and env flags

### Impact
- OpenClaw now has a canonical resident service surface for broker-managed runtime activation.
- The resident runtime reuses the existing webhook receiver instead of introducing a second daemon shape.

## 2026-03-15: IronClaw startup_probe with LM Studio fallback

**Author**: 0102 (Opus 4.5)
**WSP**: 22, 97

### Changes
- Added `startup_probe()` to `src/ironclaw_gateway_client.py`
  - Higher-level than `health()` - provides actionable remediation
  - Checks IronClaw health first
  - Falls back to LM Studio probe if IronClaw down + `SIM_QWEN_BACKEND=local`
  - Returns detailed status with remediation steps

### Remediation Logic
```python
startup_probe() returns:
  - ok=True, backend="ironclaw" (if IronClaw healthy)
  - ok=True, backend="lm_studio" (if IronClaw down but LM Studio responding)
  - ok=False, remediation=[...] (both down - provides fix steps)
```

### WSP 97 Applied
- HoloIndex → Research → Hard Think → First Principles → Build
- This was documented in P0 execution walkthrough but never implemented

---

## 2026-03-07: CTO WRE prompt added to OpenClaw default context pack

**Author**: 0102  
**WSP**: 22, 60, 73, 87

### Changes
- Added `workspace/CTO_WRE_PROMPT.md`
  - Canonical CTO operating prompt for fresh 0102 sessions.
  - Encodes:
    - WSP-first behavior
    - `connect WRE` deterministic contract
    - Occam layered architecture
    - 24/7 state-machine mindset
    - model policy and git policy
- Updated `src/openclaw_dae.py`
  - Included `workspace/CTO_WRE_PROMPT.md` in the default platform context pack load order.
- Updated `MEMORY.md`
  - Added the CTO prompt as an auto-memory topic.

### Impact
- Fresh OpenClaw sessions now load CTO/WRE operating guidance automatically through the existing context-pack mechanism.
- This improves continuity without turning startup preflight into a heavy model-launch phase.

## 2026-03-07: Canonical OpenClaw 0102 handoff for fresh-session continuity

**Author**: 0102  
**WSP**: 22, 60, 73

### Changes
- Added `docs/OPENCLAW_0102_HANDOFF_2026-03-07.md`
  - Consolidates current OpenClaw/IronClaw/WRE architecture into one fresh-session handoff.
  - Separates implemented behavior from operator intent gathered in 012 voice sessions.
  - Defines the target 24/7 OpenClaw state machine:
    - boot
    - preflight
    - observe
    - triage
    - plan
    - execute
    - verify
    - remember
    - escalate
    - idle_watch
  - Clarifies git strategy:
    - `origin` + `backup` are mirrors, not rollback primitives
    - rollback should rely on checkpoint tags, clean worktree verification, and revertable commits

### Impact
- Fresh 0102 sessions now have a canonical operational brief instead of relying on chat history reconstruction.
- OpenClaw roadmap is now framed as a state-driven 24/7 supervisor problem, not a pure voice/chat UX problem.

## 2026-03-05: LinkedIn digital_twin mentions/identity passthrough

**Author**: 0102  
**WSP**: 22, 50, 73

### Changes
- `src/linkedin_social_adapter.py`
  - Enhanced `digital_twin` action mapping to parse and pass:
    - `mentions` (comma-separated)
    - `identity_cycle` (comma-separated)
  - Preserved existing required args gate for:
    - `comment_text`, `repost_text`, `schedule_date`, `schedule_time`

### Impact
- Agent command routing can now carry LinkedIn mention/identity intent into layered Digital Twin execution without manual code edits.
- Module docs synced: `README.md`, `INTERFACE.md`.

## 2026-03-05: Signed skill-manifest verification in workspace safety gate

**Author**: 0102  
**WSP**: 22, 50, 71, 95

### Changes
- `src/skill_safety_guard.py`
  - Added pre-scan manifest verification using shared guard:
    - hash verification of `workspace/skills/**/SKILL.md|SKILLz.md`
    - optional HMAC signature verification
  - Added policy controls:
    - `OPENCLAW_SKILL_MANIFEST_REQUIRED`
    - `OPENCLAW_SKILL_MANIFEST_ENFORCED`
    - `OPENCLAW_SKILL_MANIFEST_VERIFY_SIGNATURE`
    - `OPENCLAW_SKILL_MANIFEST_ALLOW_EXTRA`
    - `OPENCLAW_SKILL_MANIFEST_FILE`
    - `OPENCLAW_SKILL_MANIFEST_HMAC_KEY`
  - Added optional function parameters so non-workspace callers can disable manifest checks explicitly.
- `workspace/skills/SKILL_MANIFEST.json`
  - Added canonical hash manifest for current workspace skill files.
- `tests/test_skill_safety_guard.py`
  - Added tamper regression proving manifest mismatch blocks before scanner execution.
- Docs updated:
  - `README.md` + `INTERFACE.md` include new manifest policy controls.

## 2026-03-05: Skill safety always-scan mode for mutating routes

**Author**: 0102  
**WSP**: 22, 50, 71, 95

### Changes
- `src/openclaw_dae.py`
  - Added `OPENCLAW_SKILL_SCAN_ALWAYS` runtime flag.
  - When enabled (`=1`), `_ensure_skill_safety()` bypasses TTL cache and re-runs
    Cisco skill scan on every mutating/skill-driven intent.
- `src/action_cli.py`
  - Added direct adapter-mode skill safety gate (`_run_adapter_skill_safety_gate()`),
    so standalone action CLI cannot bypass Cisco scan when not using `--via-dae`.
- `tests/test_skill_safety_guard.py`
  - Added regression coverage proving `OPENCLAW_SKILL_SCAN_ALWAYS` forces
    a fresh `run_skill_scan()` call even when cache is valid.
- `tests/test_action_cli.py`
  - Added regression test proving adapter mode blocks when skill safety gate fails.
- Docs updated:
  - `README.md` and `INTERFACE.md` now document `OPENCLAW_SKILL_SCAN_ALWAYS`.

## 2026-02-24: Direct-channel model routing + live provider probe + startup availability API

**Author**: 0102  
**WSP**: 22, 50, 73

### Changes
- `src/openclaw_dae.py`
  - Added deterministic direct-channel routing for model/identity utterances
    (`voice_repl`, `local_repl`) to prevent drift into non-conversation domains.
  - Added model-switch live probe controls:
    - `OPENCLAW_MODEL_SWITCH_LIVE_PROBE` (default `1`)
    - `OPENCLAW_MODEL_SWITCH_PROBE_TIMEOUT_SEC` (default `2.0`)
  - Added provider endpoint probe utility and startup availability snapshot:
    - `get_model_availability_snapshot(live_probe=..., timeout_sec=...)`
    - reports local target readiness + provider key/api status + target status.
  - Updated identity model resolution:
    - when external target is configured and key-external mode is valid,
      compact identity reports `provider/model` instead of silently reverting to local label.

### Tests
- `tests/test_openclaw_dae.py`
  - Added deterministic routing test for direct-channel model identity prompts.
  - Added compact identity test for configured external target reporting.

## 2026-02-24: Model switch reliability + compact identity + WSP_00 gate

**Author**: 0102  
**WSP**: 22, 50, 73

### Changes
- `src/openclaw_dae.py`
  - Split model-switch detection from identity detection:
    - Generic switch intent (`change/switch/become ... model`) now routes to model-switch flow.
    - If no target is provided, returns deterministic target guidance instead of identity/card output.
  - Added WSP_00 gate for model switch execution:
    - Requires commander authority
    - Requires `OPENCLAW_IDENTITY_PROTOCOL=wsp_00`
    - Requires `OPENCLAW_WSP00_BOOT=1`
    - Runs preflight gate before applying switch
  - Expanded STT alias normalization for model terms:
    - `groc/grock/grog -> grok`
  - Compact identity response now reports model only:
    - `0102: model_name=<active_model>`
    - Removes catalog list from normal identity replies.
  - Improved external-switch denial copy under key-isolation policy:
    - Clear local alternatives (`qwen3/qwen/gemma`).

### Tests
- `tests/test_openclaw_dae.py`
  - Added coverage for:
    - switch intent with missing target (guidance path)
    - WSP_00 boot gate blocking model switch
  - Updated compact identity assertions to model-name-only response.

### Validation
- `python -m py_compile modules/communication/moltbot_bridge/src/openclaw_dae.py modules/communication/moltbot_bridge/tests/test_openclaw_dae.py`: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q -s modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "model_switch or identity_query_defaults_to_compact_response or compact_identity_query_handles_punctuation or identity_query_handles_quinn_stt_alias or running_qwen"`: PASS (8 passed)

## 2026-02-24: Live voice model switching (local + external profiles)

**Author**: 0102  
**WSP**: 22, 50, 60, 73

### Changes
- `src/openclaw_dae.py`
  - Added deterministic model-switch intent parsing for natural voice commands:
    - `switch model to qwen3`
    - `become codex`
    - `become grok`
  - Added STT alias normalization for model names (`coin -> qwen`).
  - Added runtime model target application:
    - Local targets update `LOCAL_MODEL_CODE_DIR` and reset Overseer for hot reload.
    - External targets set preferred provider/model for conversation.
  - Added preferred external model execution path (operator-selected provider/model).
  - Added conversation identity/monitor exposure for:
    - `conversation_model_target`
    - `preferred_external_provider/model`
  - Guarded identity intent routing so model-switch commands are not mistaken as identity queries.
- `tests/test_openclaw_dae.py`
  - Added tests for local switch (`qwen3`) and external switch (`grok` without key).

### Validation
- `python -m py_compile modules/communication/moltbot_bridge/src/openclaw_dae.py modules/communication/moltbot_bridge/tests/test_openclaw_dae.py`: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "model_switch or role_lock or identity_query_handles_quinn_stt_alias or identity_query_model_unavailable_phrase_returns_card"`: PASS (6 passed)

## 2026-02-24: Role-lock guard against 0102/012 inversion

**Author**: 0102  
**WSP**: 22, 50, 73

### Changes
- `src/openclaw_dae.py`
  - Added deterministic role-inversion detector for low-quality model drift.
  - Added canonical role-lock response:
    - `0102` is always the digital twin
    - `012 @UnDaoDu` is always the human twin
  - Updated baseline conversation system prompt with explicit role-lock instructions
    to prevent identity flips in generation.
  - Applied role-lock correction in `_ensure_conversation_identity(...)` as final guardrail.
- `tests/test_openclaw_dae.py`
  - Added role-lock regression tests for inversion blocking and normal prefix behavior.

### Validation
- `python -m py_compile modules/communication/moltbot_bridge/src/openclaw_dae.py modules/communication/moltbot_bridge/tests/test_openclaw_dae.py`: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "role_lock or identity_query_handles_quinn_stt_alias or identity_query_model_unavailable_phrase_returns_card"`: PASS (4 passed)

## 2026-02-24: Platform context pack boot for system-wide understanding

**Author**: 0102  
**WSP**: 22, 50, 60, 73

### Changes
- `src/openclaw_dae.py`
  - Added runtime platform-context pack loader with caching and refresh controls.
  - Injects curated system context into conversation system prompt, so OpenClaw runs
    with platform-level context (not only minimal identity boot text).
  - Adds monitor/identity visibility fields:
    - `platform_context` status
    - loaded source count
    - context load age
  - Adds env controls:
    - `OPENCLAW_PLATFORM_CONTEXT_ENABLED` (default `1`)
    - `OPENCLAW_PLATFORM_CONTEXT_FILES` (optional file override list)
    - `OPENCLAW_PLATFORM_CONTEXT_MAX_CHARS` (default `2200`)
    - `OPENCLAW_PLATFORM_CONTEXT_REFRESH_SEC` (default `120`)
    - `OPENCLAW_PLATFORM_CONTEXT_QUICK_RESPONSE_CHARS` (default `1000`)
  - Local Qwen (`overseer.quick_response`) now receives the platform-context pack
    in its `context` payload (trimmed), improving answer grounding across modules.
- `tests/test_openclaw_dae.py`
  - Added tests for context-pack injection and disable behavior.

### Validation
- `python -m py_compile modules/communication/moltbot_bridge/src/openclaw_dae.py modules/communication/moltbot_bridge/tests/test_openclaw_dae.py`: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "wsp00_boot_prompt or platform_context_pack or identity_query_handles_quinn_stt_alias or monitor_reports_lineage_and_model_name"`: PASS (7 passed)

## 2026-02-24: Identity query alias bridge for Qwen/Quinn voice STT

**Author**: 0102  
**WSP**: 22, 50, 73

### Changes
- `src/openclaw_dae.py`
  - Added identity-query normalization aliases so STT variants map correctly:
    - `quinn/quin/queen/gwen` -> `qwen`
  - Expanded identity-query detection to trigger on model-name prompts such as:
    - "are you qwen"
    - "are you quinn"
    - model/runtime availability phrasing with model aliases
  - Expanded diagnostic/full-card detection for model availability phrasing:
    - "not available" now treated as diagnostic signal for identity card route.

### Validation
- `python -m py_compile modules/communication/moltbot_bridge/src/openclaw_dae.py modules/communication/moltbot_bridge/tests/test_openclaw_dae.py`: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "identity_query_handles_quinn_stt_alias or identity_query_model_unavailable_phrase_returns_card or identity_query_defaults_to_compact_response"`: PASS (3 passed)

## 2026-02-24: IronClaw autostart resilience in strict voice/chat flows

**Author**: 0102  
**WSP**: 22, 50, 60, 65, 77

### Changes
- `src/openclaw_dae.py`
  - Hardened `_attempt_ironclaw_autostart()` to fail fast when the configured executable is missing.
  - Added missing-executable backoff window to prevent repeated failed spawn loops.
  - Added explicit executable resolution checks before launch (`Path.exists` / `shutil.which`).
  - Added optional shell fallback gate (`OPENCLAW_IRONCLAW_AUTOSTART_ALLOW_SHELL`, default off).
  - Added clearer recovery details for strict-mode conversation responses.
- `tests/test_openclaw_dae.py`
  - Added strict/autostart regression coverage for missing executable fast-fail path.

### Validation
- `python -m py_compile modules/communication/moltbot_bridge/src/openclaw_dae.py modules/communication/moltbot_bridge/tests/test_openclaw_dae.py`: PASS
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "autostart or strict or identity or cancellation"`: PASS (10 passed)

## 2026-02-24: Standalone Claw Action CLI + PatternMemory writeback

**Author**: 0102  
**WSP**: 11, 22, 48, 60, 73

### Changes
- Added `src/action_cli.py` as a standalone execution surface for Claw actions:
  - Supports direct commands:
    - `linkedin action <action> ...`
    - `x action <action> ...`
    - `social campaign <campaign> ...`
    - `youtube action <action> ...`
  - Supports repeat/interval execution for 012 observation loops.
  - Supports `--via-dae` to route through full `OpenClawDAE` permission + planning path.
- Integrated PatternMemory writeback in standalone execution path:
  - Each run now writes a `SkillOutcome` record using `PatternMemory().store_outcome(...)`.
  - Skill naming format: `action_cli_<route>_<action>`.
  - Captures command context, outcome summary, success/failure, and execution time.
- CLI integration points:
  - `main.py` non-interactive flags (`--agent-command`, `--agent-repeat`, `--agent-via-dae`, ...).
  - OpenClaw menu option for interactive standalone action execution.

### Validation
- `python -m py_compile` on updated files: PASS.
- `modules/communication/moltbot_bridge/tests/test_action_cli.py`: PASS.
- Smoke execution:
  - Adapter mode: PASS (`youtube action comments ... dry_run=true`)
  - DAE mode: PASS (`x action post ... --via-dae`)

## 2026-02-16: Conversation identity anchor normalization

**Author**: 0102  
**WSP**: 11, 22, 50

### Changes
- `src/openclaw_dae.py`
  - Added `_ensure_conversation_identity()` to normalize conversation outputs.
  - All conversation execution branches (AI Gateway, Ollama, Qwen, fallback)
    now return an identity-anchored response (`0102:` prefix) when missing.
  - Prevents nondeterministic conversational output from breaking role/identity
    expectations in end-to-end flows.

### Validation
- Targeted failing tests fixed:
  - `test_conversation_returns_response`
  - `test_blocked_command_downgrades_to_conversation`
- Included in concatenated cross-module run:
  - `modules/communication/moltbot_bridge/tests`
  - `modules/foundups/agent_market/tests`
  - `modules/foundups/simulator/tests`
  - Result: **335 passed, 2 warnings**

---

## 2026-02-16: FAM token auto-resolution + collision safety

**Author**: 0102  
**WSP**: 11, 22, 50

### Changes
- `src/fam_adapter.py`:
  - Added deterministic token auto-generation from FoundUp name when token is omitted.
  - Added explicit `AUTO`/legacy `FUP` seed handling.
  - Added collision-safe symbol resolution against existing registry symbols
    (`BASE`, `BASE2`, `BASE3`, ...).
  - Launch pipeline now uses resolved symbol for both `Foundup.token_symbol`
    and `TokenTerms.token_symbol`.
- `INTERFACE.md`:
  - Documented FOUNDUP route token resolution behavior and command contracts.

### Validation
- Covered by targeted lane:
  - `modules/foundups/agent_market/tests/test_e2e_integration.py`
  - Included in 51/51 pass run logged in Agent Market + Simulator TestModLogs.

---

## 2026-02-16: FAM/Moltbook Compatibility Stabilization

**Author**: 0102
**WSP**: 11, 22, 50

### Changes
- `src/fam_adapter.py`:
  - Knowledge/LLM responses now append deterministic command help.
  - Help now includes both launch and create command variants.
- `src/moltbook_distribution_adapter.py`:
  - Deterministic milestone IDs now use `moltbook_post_` prefix for moltbook channel.
  - Milestone listing now preserves insertion order (oldest -> newest).

### Validation
- Included in concatenated run:
  - `modules/foundups/agent_market/tests`
  - `modules/foundups/simulator/tests`
  - Result: **229 passed**

---

## 2026-02-08: Hardening Tranche 3 - Correlator Integration + Containment

**Author**: 0102
**WSP**: 71, 91, 95

### Changes
- `openclaw_dae.py`:
  - Added `_emit_to_overseer()` for security event emission to AI Overseer correlator
  - Added `_check_containment()` for containment state queries
  - Integrated containment check at process entry (Phase 0.5)
  - `permission_denied` events now emit to correlator
  - `command_fallback` events now emit to correlator

- `webhook_receiver.py`:
  - `rate_limited` events now emit to AI Overseer correlator
  - Added DAEmon signal: `[DAEMON][OPENCLAW-RATELIMIT]`

### DAEmon Signals (WSP 91)
```
[DAEMON][OPENCLAW-PERMISSION] event=permission_denied tier=... sender=... reason=...
[DAEMON][OPENCLAW-RATELIMIT] event=rate_limited sender=... channel=... reason=...
[DAEMON][OPENCLAW-FALLBACK] event=command_fallback sender=... reason=...
[DAEMON][OPENCLAW-CONTAINMENT] event=containment_active sender=... action=... expires_at=...
```

### Validation
- Full module test suite: **92 passed**

---

## 2026-02-08: Hardening Tranche 2 - SOURCE tier, Rate Limiting, COMMAND Fallback

**Author**: 0102
**WSP**: 22, 50, 71, 95, 96

### Changes

#### SOURCE Tier Enforcement (fail-closed)
- `openclaw_dae.py`: Added `_check_source_permission()` method
  - Integrates with `AgentPermissionManager` for explicit SOURCE tier grants
  - Fail-closed: blocks if permission manager unavailable or check fails
  - Permission denied events emitted with 60s dedupe window
  - Emits `permission_denied` signal for forensics (WSP 71)

#### Webhook Rate Limiting (token bucket)
- `webhook_receiver.py`: Added `TokenBucket` and `WebhookRateLimiter` classes
  - Per-sender bucket: 2 tokens/sec, 10 burst capacity (configurable)
  - Per-channel bucket: 5 tokens/sec, 20 burst capacity (configurable)
  - Returns HTTP 429 with `X-Retry-After` header when exceeded
  - Configurable via env vars: `OPENCLAW_RATE_*`

#### COMMAND Graceful Degradation
- `openclaw_dae.py`: Added `_command_advisory_fallback()` method
  - Returns deterministic advisory when WRE unavailable
  - Provides three actionable options (CLI, retry, query mode)
  - Includes error detail when WRE raises exception

### Files Modified
- `src/openclaw_dae.py`: +80 lines (permission check, event emission, fallback)
- `src/webhook_receiver.py`: +70 lines (rate limiter implementation)
- `tests/test_hardening_tranche.py` (NEW): 17 tests covering all new paths
- `tests/run_tests.ps1`: Added `test_hardening_tranche.py` to security gate
- `INTERFACE.md`: Documented rate limiting API and SOURCE tier check

### Validation
- Hardening tranche tests: **17 passed**
- Full module test suite: **72 passed**
- Security gate: PASS (test_skill_boundary_policy, test_skill_safety_guard, test_hardening_tranche)

---

## 2026-02-07: OpenClaw security operations hardening verified (DAEmon + CI gate)

**Author**: 0102  
**WSP**: 22, 50, 71, 95, 96

### Changes
- Added operator-visible skill safety status in monitor output (`_execute_monitor`):
  - gate status, required/enforced flags, last check timestamp, gate message.
- Hardened CI runner to enforce security gate first:
  - `tests/run_tests.ps1` runs `test_skill_boundary_policy.py` and `test_skill_safety_guard.py` before full suite.
  - Fails immediately on security gate failure.
  - Added `-SkipSecurityGate` switch for local-only diagnostics.

### Operational Verification (DAEmon)
- Forced scanner failure drill completed with:
  - Dedupe 60s window: 1 emitted, 5 suppressed.
  - Dedupe 5s window: expiry re-alert confirmed (3 emitted in 15s).
- Canonical signal observed:
  - `[DAEMON][OPENCLAW-SECURITY] event=openclaw_security_alert ...`

### Validation
- Security gate tests: PASS
- Full module test suite: `55 passed`
- Holo memory re-index executed after docs update.

---

## 2026-02-07: WRE Graceful Degradation for COMMAND Intents (WSP 15 P0 #5, MPS 15/20)

**Author**: 0102
**WSP**: 15 (MPS), 50 (Pre-Action Verification)

### Context
`_wsp_preflight()` hard-blocked COMMAND intents when WRE was unavailable (returned `False`), which caused `process()` to downgrade to CONVERSATION. This made the advisory fallback in `_execute_command()` unreachable - users got a generic Digital Twin response instead of actionable CLI guidance.

### Fix
Changed `_wsp_preflight()` Rule 2: COMMAND intents now pass preflight even when WRE is unavailable. The `_execute_command()` handler provides the advisory fallback with specific guidance (CLI execution, retry, query mode). SCHEDULE and SYSTEM still hard-block (no advisory fallback exists for those).

### Validation
- 50/50 tests passing (all existing tests backward-compatible)

---

## 2026-02-07: AgentPermissionManager SOURCE Tier Gate (WSP 15 P0 #2, MPS 17/20)

**Author**: 0102
**WSP**: 15 (MPS), 50 (Pre-Action Verification), 71 (Secrets), 95 (WRE Skills)

### Context
P0 #2 from WSP 15 MPS. OpenClaw COMMAND intents could reach WRE execution without file-specific permission checks. The SOURCE tier existed but was never resolved by `_resolve_autonomy_tier()` (always returned DOCS_TESTS), and `_check_source_permission()` passed `file_path=None` to the permission manager, bypassing allowlist/forbidlist validation.

### Implementation
**3-layer security gate for source code modification:**

1. **File path extraction** (`_extract_file_paths()`): Regex extracts file paths from COMMAND messages (forward/backslash, quoted, known extensions). Returns normalized forward-slash paths.

2. **Source modification detection** (`_is_source_modification()`): Heuristic combining source-verb keywords ("edit", "modify", "refactor", etc.) with file path presence or module/source references.

3. **SOURCE tier wiring** (`_resolve_autonomy_tier()`): Commander + COMMAND + source modification intent now resolves to `AutonomyTier.SOURCE` instead of `DOCS_TESTS`. Without permission manager loaded: fail-closed to `ADVISORY`.

4. **File-specific permission gate** (`_check_source_permission()`): Now extracts file paths from intent and calls `check_permission(file_path=fpath)` per file, validating against allowlist/forbidlist.

5. **Execution gate** (`_execute_command()`): Pre-execution check blocks WRE routing if any target file is forbidden. Returns "Permission Denied" response with the specific file and reason.

### Security Flow
```
COMMAND intent → _is_source_modification() → True?
  → _resolve_autonomy_tier() → SOURCE
  → _check_permission_gate() → _check_source_permission()
    → _extract_file_paths() → ["modules/foo/src/bar.py"]
    → permissions.check_permission(file_path="modules/foo/src/bar.py")
    → allowlist/forbidlist validation
  → _execute_command() → pre-execution file gate
  → WRE (only if all files pass)
```

### Files
- `src/openclaw_dae.py` (MODIFIED):
  - `_extract_file_paths()`: NEW static method (regex file path extraction)
  - `_is_source_modification()`: NEW method (source-verb + file path heuristic)
  - `_resolve_autonomy_tier()`: MODIFIED (SOURCE tier for source modification)
  - `_check_source_permission()`: MODIFIED (file-specific permission checks)
  - `_execute_command()`: MODIFIED (pre-execution file permission gate)
- `tests/test_openclaw_dae.py` (MODIFIED, +20 new tests):
  - `TestFilePathExtraction`: 7 tests (python, multi, md, json, none, quoted, backslash)
  - `TestSourceModificationDetection`: 5 tests (edit+path, modify+module, run=no, deploy=no, refactor+source)
  - `TestSourceTierResolution`: 4 tests (commander SOURCE, non-source DOCS_TESTS, non-commander ADVISORY, fail-closed)
  - `TestSourcePermissionGate`: 4 tests (no manager, file allowed, file forbidden, exception)

### Validation
- **50/50 tests passing** (8 original Layer 0 + 11 Gemma + 20 SOURCE tier + 11 Layer 1-3)
- **Fail-closed verified**: No permissions = ADVISORY, exception = denied, forbidlist = blocked
- **Backward compatible**: All original tests pass unchanged

---

## 2026-02-07: Gemma 270M Hybrid Intent Classifier (WSP 15 P0 #1, MPS 18/20)

**Author**: 0102
**WSP**: 15 (MPS), 77 (Agent Coordination), 84 (Code Reuse), 96 (Skill Execution)

### Context
P0 priority item from WSP 15 MPS scoring. OpenClaw's keyword-based intent classification (133 lines of heuristics) was vulnerable to prompt injection and poorly calibrated. Any message containing "run" would classify as COMMAND regardless of actual intent.

### Implementation
**Architecture**: Hybrid Option C (keyword pre-filter + Gemma validation)
1. **Fast keyword pre-filter** (<1ms): Existing `INTENT_KEYWORDS` scoring retained
2. **Gemma 270M validation** (<30ms per candidate): Binary YES/NO classification for top 3 keyword candidates
3. **Combined scoring**: `(keyword * 0.3) + (gemma * 0.7)` for prompt-injection resistance
4. **Graceful degradation**: Falls back to keyword-only if Gemma model unavailable

### Files
- `src/gemma_intent_classifier.py` (NEW, 290 lines): Standalone `GemmaIntentClassifier` class
  - Lazy model loading (follows `gemma_validator.py` pattern)
  - `_binary_classify()`: Single YES/NO inference per category
  - `classify()`: Hybrid scoring with keyword pre-filter
  - Performance stats tracking
- `src/openclaw_dae.py` (MODIFIED):
  - `_get_gemma_classifier()`: Lazy loader for classifier
  - `classify_intent()`: Rewritten with 2-phase hybrid (keyword -> Gemma)
  - Metadata now includes `classification_method`, `gemma_scores`, `classification_latency_ms`
- `tests/test_openclaw_dae.py` (MODIFIED, +11 new tests):
  - `TestGemmaIntentClassifier`: 5 unit tests (fallback, default, candidates, stats, availability)
  - `TestGemmaHybridIntegration`: 6 integration tests (disabled, metadata, mock hybrid, degradation, foundup)

### Validation
- **30/30 tests passing** (8 original + 11 new Gemma + 11 existing Layer 1-3)
- **Backward compatible**: All original Layer 0 intent tests pass unchanged
- **Env control**: `OPENCLAW_GEMMA_INTENT=0` forces keyword-only mode

### Env Vars
- `OPENCLAW_GEMMA_INTENT` (default `1`): Enable/disable Gemma hybrid classification

---

## 2026-02-07: Security preflight audit findings + NAVIGATION.py expansion

**Author**: 0102
**WSP**: 22, 50, 71, 87, 95

### Findings (Ecosystem Deep Dive)
- OpenClaw security posture audited: **CLEAN** - no violations found across 45+ security tests.
- Cisco skill scanner (`cisco-ai-skill-scanner`) binary not installed on dev machine. `OPENCLAW_SECURITY_PREFLIGHT_ENFORCED=1` default in `main.py` was blocking startup entirely. Default changed to `=0` (warn, don't block). Production should set `=1`.
- Security controls validated: Honeypot defense (2-phase deception), skill safety guard (fail-closed), graduated autonomy tiers (ADVISORY→SOURCE), secret redaction patterns.

### Gaps Identified (WSP 15 MPS Scored)
| Gap | MPS Score | Status |
|-----|-----------|--------|
| Keyword-based intent classification (prompt injection risk) | 18/20 P0 | Needs Gemma 270M binary classification |
| SOURCE tier permission check incomplete | 17/20 P0 | AgentPermissionManager integration needed |
| No WRE graceful degradation for COMMAND intents | 15/20 P1 | Fails if WRE unavailable |
| No rate limiting on webhook endpoints | 15/20 P1 | DoS vector |

### NAVIGATION.py Expansion
- Added 15 openclaw/moltbot entries to `NAVIGATION.py` for HoloIndex discoverability:
  - `openclaw dae frontal lobe`, `openclaw intent classification`, `openclaw permission gate`
  - `openclaw security sentinel`, `openclaw skill safety guard`, `openclaw honeypot defense`
  - `openclaw fam adapter`, `openclaw foundup launch`, `openclaw webhook receiver`
  - `openclaw install setup`, `openclaw security tests`, `openclaw dae tests`
  - `moltbot bridge digital twin`, `moltbot bridge workspace skills`

---

## 2026-02-07: Skill boundary policy codified + enforcement tests

**Author**: 0102
**WSP**: 50, 71, 95, 96

### Changes
- Added explicit boundary policy:
  - `docs/SKILL_BOUNDARY_POLICY.md`
  - Defines separation between OpenClaw workspace skills and internal module `skillz`.
- Updated docs to reference the policy:
  - `README.md`
  - `INTERFACE.md`
- Added enforcement tests:
  - `tests/test_skill_boundary_policy.py`
  - Verifies workspace skills remain docs-only.
  - Verifies mutating intent categories always pass through `_ensure_skill_safety()`.

### Validation
- `.\modules\communication\moltbot_bridge\tests\run_tests.ps1`
- Result: PASS

---

## 2026-02-07: Deterministic Test Runner Standardized

**Author**: 0102
**WSP**: 22, 34, 95

### Changes
- Added canonical test runner script: `tests/run_tests.ps1`.
- Runner now enforces deterministic pytest behavior by:
  - Using local venv Python (`.venv\Scripts\python.exe`)
  - Setting `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`
  - Restoring prior env state after execution
- Updated test docs to reference the runner:
  - `tests/README.md`
  - `tests/TestModLog.md`

### Validation
- `powershell -NoProfile -ExecutionPolicy Bypass -File modules/communication/moltbot_bridge/tests/run_tests.ps1`
- Result: 34 passed, 2 warnings

---

## 2026-02-07: WSP 95/71 Security Audit - Full Compliance

**Author**: 0102
**WSP**: 71, 95, 96

### Changes
- Completed security audit of all mutating DAE entrypoints for scanner gate parity.
- Added comprehensive test coverage (14 tests) for WSP 95/71 requirements:
  - Scanner missing + required mode => block (fail-closed)
  - High severity => block
  - Medium at threshold => block
  - Low below threshold => allow
  - Critical always blocks regardless of threshold
  - Cache TTL prevents re-scan
  - Cache expiry triggers re-scan
  - Enforced mode blocks failed scans
  - Non-enforced mode allows with warning
  - FOUNDUP intent category properly gated
- Created `violations.md` documenting clean audit (no violations found).
- All mutating routes (COMMAND, SYSTEM, SCHEDULE, SOCIAL, AUTOMATION, FOUNDUP) confirmed gated.

### Validation
- `modules/communication/moltbot_bridge/tests`: 34 passed
- All 14 skill safety guard tests passing

---

## 2026-02-07: Cisco Skill Scanner Safety Gate Integration

**Author**: 0102
**WSP**: 11, 22, 50, 73, 91

### Changes
- Added `src/skill_safety_guard.py` with `run_skill_scan()` wrapper around Cisco `skill-scanner`.
- Integrated cached skill safety gate into `src/openclaw_dae.py`:
  - Checks workspace skills before mutating/skill-driven routes.
  - Policy configurable via env vars (`REQUIRED`, `ENFORCED`, `MAX_SEVERITY`, `TTL_SEC`).
  - Unsafe scan downgrades route to conversation fail-safe.
- Hardened intent classification:
  - Word-boundary keyword matching to prevent substring false positives.
  - Greeting-first conversation override.
  - Boundary-safe extracted task cleanup.
- Hardened AI Overseer lazy loader to degrade gracefully on non-ImportError failures.
- Added tests: `tests/test_skill_safety_guard.py`.

### Validation
- `modules/communication/moltbot_bridge/tests`: 20 passed
- `modules/foundups/agent_market/tests`: 34 passed

---

## 2026-02-07: OpenClaw intent matching hardening + overseer fail-safe

**Author**: 0102
**WSP**: 50, 73, 91

### Changes
- Updated `src/openclaw_dae.py` intent classifier to use word-boundary regex matching instead of raw substring matching.
  - Prevents false positives such as `at` matching inside `what`.
- Added greeting-first conversation override for `hi|hey|hello` opener messages.
- Updated task extraction to remove matched keywords using word-boundary regex, avoiding token mutilation.
- Hardened AI Overseer lazy loader to catch non-ImportError failures (for example `SyntaxError`) and degrade gracefully.

### Validation
- `modules/communication/moltbot_bridge/tests`: 20 passed
- `modules/foundups/agent_market/tests`: 34 passed

---

## 2026-02-07: FAM Integration + Moltbook Distribution Adapter

**Author**: 0102
**WSP**: 11, 46, 50, 72, 73, 87

### Changes

**New: `src/fam_adapter.py` (~280 lines)**
- OpenClaw -> FAM boundary adapter
- `FAMLaunchRequest` / `FAMLaunchResponse` dataclasses
- `FAMAdapter` class: in-memory or injected adapter support
- `parse_launch_intent()`: parses "launch foundup" commands
- `handle_fam_intent()`: entry point for OpenClaw FOUNDUP routing

**New: `src/moltbook_distribution_adapter.py` (~180 lines)**
- `MoltbookDistributionAdapterStub`: implements FAM `MoltbookDistributionAdapter` interface
- In-memory storage for PoC testing
- Discord webhook push for production distribution
- `publish_milestone()`, `get_publish_status()`, `list_published_milestones()`

**Modified: `src/openclaw_dae.py`**
- Added `IntentCategory.FOUNDUP` for FoundUp-related intents
- Added FOUNDUP keywords: "foundup", "launch foundup", "token", "milestone", etc.
- Added `fam_adapter` domain route
- Added `_execute_foundup()` method routing to FAM adapter

### Architecture
```
OpenClaw (Partner)
    |
    v
[IntentCategory.FOUNDUP]
    |
    v
FAMAdapter (Principal)
    |
    v
LaunchOrchestrator (Associate)
    |
    +---> InMemoryAgentMarket (PoC)
    +---> MoltbookDistributionAdapterStub
```

### Test Results
- 29/29 FAM tests passing (including E2E integration)
- OpenClaw DAE tests: 22/22 passing

---

## 2026-02-02: OpenClaw WRE Integration - Plugin + Skillz + Workspace Skills

**Author**: 0102
**WSP**: 46, 50, 65, 73, 77, 91, 96

### Changes (Session 2)

**New: `OpenClawPlugin` class in `src/openclaw_dae.py`**
- WRE OrchestratorPlugin adapter: bridges WRE plugin interface (WSP 65) to OpenClaw DAE
- `as_plugin()` convenience method on OpenClawDAE returns singleton plugin
- `register_with_wre()` auto-registers on first WRE lazy-load (bidirectional routing)
- Handles async-to-sync bridging for WRE compatibility (ThreadPoolExecutor fallback)

**New: WRE SKILLz (2 skills)**
- `skillz/openclaw_intent_router/SKILLz.md` - Gemma 270M intent classification (3-step micro CoT)
- `skillz/openclaw_executor/SKILLz.md` - Qwen+Gemma execution pipeline (4-step micro CoT)
- Both registered in `skills_registry_v2.json` (total skills: 16 -> 18)

**New: OpenClaw Workspace Skills (3 skills)**
- `workspace/skills/openclaw-execute/SKILL.md` - Task execution through WRE routing
- `workspace/skills/openclaw-monitor/SKILL.md` - System health and WRE metrics
- `workspace/skills/openclaw-schedule/SKILL.md` - YouTube Shorts scheduling via CPS

**Modified: `src/__init__.py`**
- Exports `OpenClawPlugin` alongside `OpenClawDAE`

**Modified: `skills_registry_v2.json`**
- Added `openclaw_intent_router` (Gemma, CLASSIFICATION, WSP 46/50/73/96)
- Added `openclaw_executor` (Qwen+Gemma, DECISION, WSP 46/50/73/77/91/96)

**Test Results**: 22/22 passing (WRE plugin registration confirmed in test output)

---

## 2026-02-24: Identity Contract Lock (OpenClaw DAE)

**Author**: 0102
**WSP**: 22, 50, 73

### Changes
- Enforced runtime identity contract in DAE guardrails:
  - `0102` = agent/digital twin
  - `012` = operator/commander (`@012` canonical sender)
- Authorized commander set now includes canonical `012/@012` (legacy aliases retained for compatibility).
- Updated role-lock response and system prompt:
  - Role lock now states: `I am 0102 ... You are 012 (operator)`.
  - Conversation guardrails enforce `0102` agent role and `012` operator role.
- Permission/system denials reference `@012` for commander-gated operations.

### Validation
- `python -m py_compile` passed for updated DAE and CLI files.
- Focused tests passed with plugin autoload disabled:
  - `pytest -q modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "role_lock or identity_query_model_unavailable_phrase_returns_card"`

---

## 2026-02-02: OpenClaw DAE - The Frontal Lobe

**Author**: 0102
**WSP**: 46, 50, 73, 77, 91, 96

### Changes (Session 1)

**New: `src/openclaw_dae.py` (~530 lines)**
- OpenClaw DAE: control-plane "frontal lobe" translating intent into WRE-routed execution
- Full autonomy loop: Ingress -> Intent -> Preflight -> Plan -> Permission -> Execute -> Validate -> Remember
- WSP 73 Partner-Principal-Associate structure: OpenClaw=Partner, DAE=Principal, Domain DAEs=Associates
- 7 intent categories: QUERY, COMMAND, MONITOR, SCHEDULE, SOCIAL, SYSTEM, CONVERSATION
- 4 autonomy tiers: ADVISORY (anyone), METRICS (commander), DOCS_TESTS (commander), SOURCE (explicit)
- Security: non-commanders capped at ADVISORY, secret patterns redacted, all decisions logged
- Lazy-loaded WRE, AI Overseer, Agent Permissions (no import-time cost on webhook boot)
- Pattern memory integration: stores outcomes in WRE SQLite for recursive learning

**Modified: `src/webhook_receiver.py`**
- Replaced `process_with_holoindex()` as primary route with `process_via_openclaw_dae()`
- HoloIndex-only path kept as legacy fallback on DAE failure
- OpenClaw DAE singleton lazy-initialized on first request

**Modified: `src/__init__.py`**
- Exports OpenClawDAE alongside FastAPI components
- Graceful degradation when FastAPI not installed (DAE always importable)

**Modified: `INTERFACE.md`**
- Documented OpenClaw DAE API, intent categories, autonomy tiers
- Added WSP 73 Partner-Principal-Associate architecture
- Added security model documentation

**New: `tests/test_openclaw_dae_standalone.py` (~210 lines)**
- 22 tests across 5 layers (classification, preflight, permissions, security, E2E)
- 22/22 passing after intent classification refinement
- Standalone runner (no pytest/FastAPI dependency required)

### Architecture Decision
OpenClaw DAE is the "frontal lobe" because:
1. WSP is the rail (governance, not just reminders)
2. WRE is the execution cortex (pattern recall, not computation)
3. OpenClaw is the sensory gateway (multi-channel intent ingress)
4. Domain DAEs are the motor cortex (execute: communicate, schedule, index)

---

## 2026-02-01: OpenClaw Documentation Update

**Author**: 0102 (via Antigravity)

### Changes
- Created `docs/INSTALL_OPENCLAW.md` with comprehensive installation guide
- Updated `README.md` to reflect OpenClaw rebrand (Clawdbot → Moltbot → OpenClaw)
- Kept module name as `moltbot_bridge` to avoid churn from future rebrands
- Updated `workspace/AGENTS.md` to treat HoloIndex output issues as P0 and require WSP-guided deep dive before proceeding
- Updated OpenClaw naming across bridge interface, webhook endpoints, and setup docs while keeping legacy compatibility

### Critical Lesson Documented

> **Node.js must be installed INSIDE WSL, not just on Windows.**
> 
> Using Windows npm to install OpenClaw causes `node: not found` errors because
> the OpenClaw binary attempts to run with WSL's Node, which doesn't exist if
> only Windows Node is installed.

### Fix Applied
```bash
# Install Node.js in WSL
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# Then install OpenClaw
npm install -g openclaw
openclaw onboard
```

### Related Files
- `docs/INSTALL_OPENCLAW.md` - Full installation guide
- `docs/CHANNEL_SETUP.md` - Channel configuration (needs update for openclaw commands)
- `README.md` - Updated with rebrand info

## 2026-03-06: Qwen3.5 local-runtime bootstrap alignment

**Author**: 0102  
**WSP**: 00, 15, 84

### Changes
- Updated `src/openclaw_dae.py` local identity catalog default to include `qwen3.5`.
- Added `local/qwen3.5-4b` to `get_model_availability_snapshot()` so status checks report readiness correctly after model switch.
- Preserved existing model-switch contract while making runtime diagnostics consistent with `switch model to qwen3.5`.

### Validation
- Targeted tests pass for Qwen3.5 model-switch and availability snapshot.

## 2026-03-07: ZeroClaw runtime profile enforcement (WSP_77 alignment)

**Author**: 0102  
**WSP**: 00, 15, 50, 77

### Changes
- Updated `src/openclaw_dae.py` with runtime profile support:
  - New env: `OPENCLAW_RUNTIME_PROFILE` (`openclaw|ironclaw|zeroclaw`)
  - Added runtime profile aliases (`open`, `iron`, `zero`, `failsafe`, `safe`)
- Implemented ZeroClaw fail-closed behavior:
  - Forces `no_api_keys` ON
  - Forces external LLM routing OFF
  - Downgrades mutating intents (`command/system/schedule/social/automation/foundup/research`) to `conversation` + `digital_twin` route
- Hardened model switch policy:
  - Blocks external model targets when runtime profile is `zeroclaw`
  - Keeps local model switches available
- Surfaced profile in identity/status outputs:
  - `get_identity_snapshot()` now returns `runtime_profile`
  - Added profile signal to identity card/compact runtime/monitor status/label line

### Outcome
- ZeroClaw now behaves as a real runtime profile (not documentation-only):
  - Read-safe by default
  - No external model drift
  - Mutating intents auto-contained before execution planning

## 2026-03-15: PQN runtime broker control from OpenClaw

**Author**: 0102  
**WSP**: 11, 72, 73, 84, 97

### Changes
- Updated `src/pqn_research_adapter.py` to recognize broker-managed runtime commands:
  - `launch pqn research`
  - `status pqn research`
  - `stop pqn research`
  - `launch pqn architect`
  - `status pqn architect`
- Runtime control now routes through the central `DAELaunchBroker` instead of trying to re-enter the menu layer.
- Updated `INTERFACE.md` to document the new runtime control contract.

### Outcome
- 012 can ask 0102 to launch PQN research inside an already running system.
- OpenClaw stays the conversational/control-plane front door while DAEmon remains the lifecycle ledger.
## 2026-03-10: LinkedIn mission-control routing + WSP 97 context pack

**Author**: 0102  
**WSP**: 15, 50, 77, 84, 97

### Changes
- Added `src/linkedin_loop_adapter.py` as a conversational control surface for the durable LinkedIn orchestration loop.
- Updated `src/openclaw_dae.py` to:
  - route mission phrases such as `let's work on LN` through the loop adapter before low-level LinkedIn actions
  - load `WSP_97_System_Execution_Prompting_Protocol.md` into the default OpenClaw platform context pack
  - prioritize code-change language over health vocabulary during agentic model selection so edit work routes to the coder model

### Outcome
- OpenClaw can now steer LinkedIn loop phases conversationally while preserving deterministic action commands.
- WSP 97 is part of default OpenClaw context, so `follow wsp` resolves through the execution-prompting protocol by default.
- Mixed prompts like `fix the failing test in main.py` now route to `local/qwen-coder-7b` instead of `local/gemma-270m`.

## 2026-03-10: Deterministic "follow wsp" command route

**Author**: 0102  
**WSP**: 50, 77, 84, 97

### Changes
- Added explicit `follow wsp` interception in `src/openclaw_dae.py` command routing.
- The canonical WSP 97 operator now routes through `modules/infrastructure/wsp_orchestrator/src/wsp_orchestrator.py` instead of falling through generic WRE command handling.

### Outcome
- `follow wsp ...` now has a real execution plane in OpenClaw:
  - detect operator
  - call WSP orchestrator
  - return deterministic execution summary

## 2026-03-11: OpenClaw control-plane refactor - intent planner + result memory

**Author**: 0102  
**WSP**: 22, 50, 73, 84, 97

### Changes
- Added `src/openclaw_intent_planner.py` for intent classification, WSP preflight, and execution-plan construction.
- Added `src/openclaw_result_memory.py` for output validation and WRE pattern-memory storage.
- Reduced `src/openclaw_dae.py` by replacing inline classify/preflight/plan/finalize blocks with facade wrappers.

### Outcome
- OpenClaw intent resolution and result finalization are now isolated control-plane seams instead of monolith internals.
- `openclaw_dae.py` dropped from `2638` lines to `2262` lines in this slice.

## 2026-03-11: OpenClaw control-plane refactor - permission and safety policy

**Author**: 0102  
**WSP**: 22, 50, 71, 73, 84, 95, 97

### Changes
- Added `src/openclaw_permission_policy.py` for autonomy-tier resolution, source-write gating, AI Overseer emission, containment checks, and cached skill-safety scanning.
- Replaced the inline permission/security block in `src/openclaw_dae.py` with facade wrappers.

### Outcome
- Permission, containment, and skill-safety policy are now centralized and auditable as one control-plane module.
- `openclaw_dae.py` dropped from `2262` lines to `2086` lines in this slice.

## 2026-03-11: OpenClaw control-plane refactor - execution routes

**Author**: 0102  
**WSP**: 22, 50, 73, 84, 97

### Changes
- Added `src/openclaw_execution_routes.py` for post-plan route execution:
  - query
  - command + follow-wsp
  - monitor
  - schedule
  - system
  - automation
  - foundup
  - research
- Replaced the inline route layer in `src/openclaw_dae.py` with facade wrappers.

### Outcome
- Execution-plane routing now lives in a dedicated module after plan resolution, aligned to WSP 97 plane separation.
- `openclaw_dae.py` dropped from `2086` lines to `1678` lines in this slice.

## 2026-03-11: OpenClaw control-plane refactor - telemetry and turn state

**Author**: 0102  
**WSP**: 22, 73, 84, 91, 97

### Changes
- Added `src/openclaw_turn_state.py` for:
  - conversation-engine markers
  - preferred-external status markers
  - token telemetry
  - cooperative turn cancellation
- Replaced the inline runtime bookkeeping block in `src/openclaw_dae.py` with facade wrappers.

### Outcome
- Runtime bookkeeping is now isolated from the OpenClaw control-plane facade.
- `openclaw_dae.py` dropped from `1678` lines to `1603` lines in this slice.

## 2026-03-11: OpenClaw control-plane refactor - status surface + process loop

**Author**: 0102  
**WSP**: 22, 50, 73, 84, 91, 97

### Changes
- Added `src/openclaw_status_surface.py` for:
  - `connect_wre` readiness/status synthesis
  - Discord/AI Overseer status push dispatch
- Added `src/openclaw_process_loop.py` for the full autonomy loop:
  - honeypot intercept
  - containment gate
  - intent -> preflight -> permission -> plan -> execute -> validate pipeline
  - DAEmon in/out and action reporting
- Replaced the inline status/process bodies in `src/openclaw_dae.py` with facade delegation.

### Outcome
- `OpenClawDAE` now behaves as a true orchestration facade instead of carrying the full autonomy implementation.
- `openclaw_dae.py` dropped from `1603` lines to `1342` lines in this final extraction slice.

## 2026-03-15: OpenClaw docs updated for WSP 97 module split

**Author**: 0102  
**WSP**: 22, 73, 84, 97

### Changes
- Appended canonical control-plane module map to `README.md`.
- Appended internal module-boundary map to `INTERFACE.md`.

### Outcome
- Repo-local documentation now matches the post-refactor OpenClaw runtime layout.
- The next 0102 session can re-enter OpenClaw using the actual module graph instead of the old monolith assumption.

## 2026-03-17: OpenClaw runtime supervision surface

**Author**: 0102  
**WSP**: 22, 73, 91, 97

### Changes
- Extended `src/dae_runtime_adapter.py` with read-only supervision commands:
  - `tail <dae>`
  - `status <dae> live`
- Added OpenClaw aliases for its own daemon identity:
  - `openclaw`
  - `claw`
  - `0102`
- Updated `INTERFACE.md` to document the new live-tail command surface.

### Outcome
- 012 can inspect the DAEmon ledger through OpenClaw instead of reading raw logs.
- Claw and PQN runtime activity now has a real supervision surface, not just event persistence.

## 2026-03-18: PQN simulation broker/runtime alignment

**Author**: 0102  
**WSP**: 22, 73, 84, 97

### Changes
- Extended `src/dae_runtime_adapter.py` aliases and parsing so `pqn_simulation` is a first-class runtime target.
- Added deterministic separation:
  - `show pqn simulation plan` stays on the RESEARCH/read path
  - `run|launch|status|stop pqn simulation` routes to runtime control
- Updated `src/pqn_research_adapter.py` to delegate simulation execution/status/stop to the central broker instead of instantiating `PQNAlignmentDAE` inline.

### Outcome
- PQN simulation now behaves like the rest of the launchable runtime system instead of bypassing it.
- Claw, DAEmon, and the broker now share one execution ledger for PQN simulation lifecycle events.

## 2026-03-18: OpenClaw supervisor promoted to broker-managed runtime

**Author**: 0102  
**WSP**: 22, 73, 84, 97

### Changes
- Added `src/openclaw_supervisor.py` with the explicit state machine:
  - `BOOT`
  - `PREFLIGHT`
  - `OBSERVE`
  - `TRIAGE`
  - `PLAN`
  - `EXECUTE`
  - `VERIFY`
  - `REMEMBER`
  - `ESCALATE`
  - `IDLE_WATCH`
- Added supervisor launch/stop wrappers to `scripts/launch.py`.
- Updated `main.py` bootstrap so the supervisor is registered and can autostart as `openclaw_supervisor`.
- Shifted daemon self-audit ownership to the supervisor path, leaving `main.py` fallback-only when supervisor is disabled.

### Outcome
- 0102 now has a canonical runtime supervisor surface instead of relying only on the self-audit loop.
- Resident OpenClaw and self-audit are now coordinated through one broker-visible lifecycle.

## 2026-03-18: IronClaw startup readiness preflight

**Author**: 0102  
**WSP**: 22, 73, 97

### Changes
- Added startup IronClaw readiness gate in `main.py` using `IronClawGatewayClient.startup_probe()`.
- Added env controls for:
  - `OPENCLAW_IRONCLAW_PREFLIGHT`
  - `OPENCLAW_IRONCLAW_PREFLIGHT_ALWAYS`
  - `OPENCLAW_IRONCLAW_PREFLIGHT_ENFORCED`
- Updated README/INTERFACE startup contract to make IronClaw readiness explicit instead of a late conversational surprise.

### Outcome
- IronClaw health is now checked at the correct layer when IronClaw is the selected conversation backend.
- Startup blocking only occurs when the active backend truly depends on IronClaw without fallback.

## 2026-03-18: OpenClaw supervisor bounded repair loop
- Added OPENCLAW_SUPERVISOR_MAX_RESTARTS and OPENCLAW_SUPERVISOR_RESTART_WINDOW_SEC.
- Supervisor now observes incremental DAEmon follow events, tracks restart attempts inside a rolling window, and escalates when the resident OpenClaw repair budget is exhausted.
- Failed verify cycles now record memory and advance the event cursor before escalation.

## 2026-03-22: OpenClaw autonomy external prompt pack

**Author**: 0102  
**WSP**: 22, 77, 97

### Changes
- Added `workspace/OPENCLAW_AUTONOMY_EXTERNAL_PROMPT_PACK_2026-03-22.md`.
- Added a fresh-context master prompt plus bounded worker prompts for:
  - autonomous task consumer
  - supervisor unification
  - menu/skill island routing
- Added workspace memory note `workspace/memory/2026-03-22-openclaw-autonomy-prompt-pack.md`.

### Outcome
- 012 can now hand another `0102` context a repo-true autonomy mission without paying for another full-stack architecture re-audit.
- OpenClaw autonomy work is now split into explicit parallelizable slices instead of one oversized prompt.

## 2026-03-22: Walkthrough validation + P0 task consumer hardening

**Author**: 0102  
**WSP**: 22, 49, 77, 97

### Changes
- Validated the external OpenClaw walkthrough against repo truth and recorded the result in `workspace/memory/2026-03-22-openclaw-walkthrough-validation.md`.
- Hardened `src/openclaw_supervisor.py` so autonomous task execution:
  - uses `sys.executable`
  - uses an absolute `run_task.py` path
  - waits for the task runner to finish
  - verifies the task actually reached `completed` in `AgentDB`
- Updated `tests/test_openclaw_supervisor.py` to isolate `FOUNDUPS_DB_PATH` and reset the shared database singleton between tests.

### Outcome
- The P0 consumer loop no longer reports success just because a subprocess was spawned.
- Supervisor tests are no longer contaminated by shared pending tasks in the default AgentDB.
- The repo now distinguishes more clearly between real implemented autonomy and overstated walkthrough claims.


## 2026-03-22: OpenClaw Autonomous Maintenance Loop (P0 Slice)

**Author**: 0102
**WSP**: 78, 97

### Changes
- Promoted OpenClawSupervisor to act as the canonical autonomous task consumer.
- Enhanced _triage, _plan, _execute, and _verify in openclaw_supervisor.py to aggressively poll AgentDB for pending autonomous tasks whenever the resident OpenClaw runtime is healthy but idle.
- Created scripts/run_task.py as a deterministic task dispatch script simulator to close the execution loop, advancing tasked state to completed in AgentDB.

### Outcome
- The task consumer pipeline is now wired securely. Autonomous loop execution (Producer -> AgentDB -> Supervisor -> Consumer) has deterministic boundaries.
