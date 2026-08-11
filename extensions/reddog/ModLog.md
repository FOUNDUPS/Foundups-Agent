# RedDog ModLog

## 2026-08-11 - Read-only architect stage compatibility pin (0.4.75)

- Regenerated and pinned the backend manifest after replacing the invalid
  read-only bootstrap stage literal with canonical `AUDIT_NO_EFFECT`.
- Reconciled platform line endings and digest-bound intent test contracts; no
  editor execution authority or model-routing behavior changed.

## 2026-08-11 - Bounded iterative repository grounding pin (0.4.74)

- Regenerated and pinned the backend dependency manifest after adding
  deterministic two-round Holo refinement and immutable exact-HEAD evidence.
- No editor authority or new orchestration path was added; this build aligns
  the thin client with the changed backend trust boundary.

## 2026-08-10 - Orchestration prompt transparency and WSP execution contract (0.4.73)

- Added a collapsible local prompt trace that is content-free before the
  authoritative redaction gate and shows only the exact gate-redacted task
  prompt afterward. System text, context, history, provider IDs, blocked prompt
  bodies, unsuccessful prompt bodies, and raw work-focus excerpts are excluded.
  Successful disclosure requires a matching bridge-provided SHA-256 and an
  unchanged local Copy-MD sanitization pass; otherwise the body remains hidden.
  Pre-gate correlation uses a process-local keyed value so low-entropy operator
  prompts cannot be fingerprinted offline. Dynamic Markdown fencing keeps
  admitted text inert in Copy MD.
- Hardened RedDog prompting to require WSP_00 workstream/execution-plane
  classification, WSP_97 retrieval and CoR refutation, runtime-truth
  precedence, reuse-first design, explicit defect classes, HoloIndex quality
  evaluation, and the WSP_15 economy questions.
- Kept prompt text non-authoritative: audit and bounded effects remain governed
  by the existing progressive stage, signed work orders, and independent
  verification. Query-time reindexing remains forbidden. (WSP 00/15/22/50/97)
- Promoted generic repository-health questions into the existing deep-dive
  grounding path so missing target discovery or direct-read evidence blocks
  Fusion instead of producing an expensive ungrounded architecture answer.
- Renamed the heuristic model-routing value to `reasoning_tier`; it no longer
  masquerades as a WSP_15 allocation. Worker prompts must carry WSP_00,
  WSP_97, WSP_15, execution-plane, closed non-authoritative authority, and
  closed fail-policy fields. Failure conditions use canonical `REJECT_ON`
  reason codes; each prompt binds the selected author profile, and self-grants,
  role promotion, evidence invention, WSP bypasses, and natural-language policy
  inversions reject.
- Extracted the prompt-artifact validator and trace lifecycle from
  `extension.js`, preserving the existing API while restoring WSP_62 no-growth
  compliance without increasing an exemption.
- Extracted the governed target-read path policy and reused it in worker-prompt
  validation so repository metadata, environments, dependencies, packaged
  artifacts, secret-like paths, and private-key containers cannot pass the
  prompt contract while remaining unreadable at execution time. The shared
  JavaScript policy now preserves the existing authoritative Python bundle
  gate's stricter segment rules, including secret-shaped source filenames.
- Bound prompt-trace metadata to the route that actually ran. Local/no-model,
  grounding-failure fallback, and queued-recovery paths no longer inherit a
  speculative Fusion role or context label. Completed no-model routes now state
  that no prompt exists instead of implying a redaction gate is pending.
- Made compatibility-degraded no-model routing precede grounding rejection.
  A locally resolved compatibility receipt can no longer be relabeled as a
  model/network attempt when degraded context would also fail grounding. Its
  pre-route status messages likewise state that no bridge, model, or network
  call occurs.
- Hardened governed Git-context caching so control files, refs, pack metadata,
  and tree identity invalidate cached storage validation. Nested ref hardlink
  replacement after cache fill is rejected; current working-file content stays
  the only source content admitted to model context.
- Extracted governed Git projection and prompt-route construction into cohesive
  modules. `extension.js` is below its frozen WSP_62 ceiling; both new modules
  stay below 400 lines and every function stays below 30 lines.
- Fixed the worker-prompt path grammar so a leading `t` is not consumed as
  whitespace. Compound secret containers such as `secrets_store`,
  `credential_cache`, `token_data`, and `prod-secrets` now reject consistently
  without denying ordinary `auth/token_manager.py` or `token_efficiency` code.
- Replaced four CodeQL-reported regex decisions with linear token, suffix, and
  comment-marker checks. Adversarial long-spacing, long execution-plane, and
  alternate HTML comment terminator inputs remain bounded and fail closed.
  Repository-attention detection scans every need token so benign prefix text
  cannot bypass the deep-dive evidence gate.

## 2026-08-09 - Progressive audit and bounded-execution stages (0.4.72)

- Added an explicit `audit` / `boundedExecution` setting as a maximum effect
  stage. Audit remains conversational and may admit only signed strict
  read-only tasks with no changed paths or effect authority; the setting
  itself grants no authority.
- Bound the extension planning path to both the selected ceiling and the
  existing runtime-consumption gate. The resident editor backend clamps every
  requested ceiling to audit until a root-owned activation source exists.
  Production remains unavailable, and redaction, signature, replay, scope,
  and secret controls are not switchable.
- Added Run Trace truth for the configured stage, audit availability, action
  ceiling, and no-authority invariant. (WSP 00/15/22/50/62/97)
- Explicit repository audits can now submit the existing authenticated
  resident session while mutation planning is disabled. This path bypasses
  Wardrobe effect selection, carries the audit ceiling, and cannot enter the
  work-order, valve, worktree, shell, commit, or PR stages.
- Hardened the backend contract so signer and verifier recompute the complete
  canonical WSP_15 allocation, reject glob effect paths, and preserve a signed
  audit task through restart re-verification without granting effect authority.
- Added exact-chain assurance for the backend audit path: FoundUp/slice risk
  identity cannot be omitted, effect admission requires the independently
  verified authority digest, and the authenticated model-runtime receipt
  survives AgentDB restart reconstruction for the real read-only 0102 worker.

## 2026-08-09 - Single-input authority boundary hardening (0.4.71)

- Moved plain operator-only classification into the diagnostic ingress parser,
  removing the whole-message action fallback that could promote diagnostic
  fields such as `fix: false` or terse command-failure text.
- Added bounded recognition for timestamped, JSON, and logfmt diagnostics so
  common log formats begin inert evidence instead of entering operator scope.
- Required an accepted receipt-bearing Wardrobe selection, with no execution
  or enqueue side effects, before the resident AgentDB/OpenClaw session can be
  submitted. The receipt digest is recomputed against the exact selector input
  and admitted through the existing immutable process-local owner-proof
  pattern. Rejected, copied, injected, or malformed selections fail closed.
- Routed both the Python bootstrap and selector through the approved workspace
  `.venv`, isolated `-I -S -B` startup, and manifest-materialized source. A
  private per-runner capability binds canonical output to the Wardrobe proof;
  WRE invocation, live enqueue, and action-bearing resident submission each
  reject direct calls without it.
- Added the common `Please analyze and fix ...` imperative without weakening
  assessment-only questions or evidence isolation.
- Removed ambiguous intent inference from unmarked mixed text. One-field
  request-plus-log pastes require `DAEmon output:` or `## Run Trace`; otherwise
  diagnostic-shaped content remains evidence-only.

## 2026-08-09 - Single conversation input and governed action routing (0.4.70)

- Removed the duplicate diagnostic-evidence textarea. The single conversation
  input sends on Enter and supports multiline input with Shift+Enter.
- Added bounded inference of an intent/evidence boundary for a leading
  assessment or action followed by diagnostic-shaped lines. Bare log dumps
  remain local, and action text inside evidence remains inert.
- Distinguished assessment diagnostics from explicit operator action.
  Assessment output remains non-actionable; an explicit action no longer
  requires 012 to repeat the same request as a separate promotion phrase.
- Made explicit governed actions automatically request the existing
  authenticated resident AgentDB/OpenClaw architect cycle after grounding,
  validation, and Fusion quorum pass. No signer, queue, worker, worktree,
  verifier, PR, merge, or Hermes authority was duplicated in the extension.
- Added Run Trace truth for diagnostic and generic governed action requests.
- Hardened action admission after independent review: only imperative operator
  directives request work, diagnostic-shaped first lines cannot become intent,
  bounded requested paths remain in the evidence projection, all supported
  action verbs use the same resident-routing decision, and an explicit legacy
  resident-session opt-out survives the canonical setting migration.

## 2026-08-09 - Governed DAEmon architect diagnosis (0.4.69)

- Split DAEmon routing by operator intent: an unaccompanied raw log dump stays
  local, while an explicit analysis, diagnosis, or repair request reaches the
  existing HoloIndex and Fusion architect path.
- Added a bounded digest-bound evidence projection that omits secret-bearing
  lines and labels retained signals as inert untrusted data. Raw diagnostic
  text is not forwarded to the model or action-planning paths.
- Added separate work-focus and diagnostic-evidence ingress fields. Legacy
  combined pastes require an explicit evidence boundary, preventing JSON,
  logfmt, cookies, signed URLs, or payload prose from self-promoting to Fusion.
- Added Run Trace projection telemetry and a mandatory explicit-work-promotion
  rejection at runtime consumption. No queue, signer, database, orchestrator,
  repository, PR, or merge authority was added.
- Bound typed diagnostic evidence into blocked-request recovery, gave explicit
  typed diagnostic intent precedence over local Run Trace summarization, and
  allowed a recovered advisory to complete only when validation and Fusion
  quorum pass while runtime action remains denied.
- Extracted DAEmon and Run Trace policy into a focused module so the legacy
  thin-client integration file remains below its WSP 62 no-growth ceiling.
- Made every separately typed diagnostic payload use the bounded projection,
  independent of operator phrasing. Determine and prompt-deliverable controls
  now derive only from the work-focus field, never from diagnostic data.
- Advanced blocked-request recovery to schema v2 so the JavaScript client and
  Python authority runtime both require and digest-bind diagnostic evidence.
  Internally rehashed v1 packets are rejected and retired.
- Extended evidence omission to compound snake_case, kebab-case, and camelCase
  credential assignments before any model request.
- Omitted all authorization-header schemes and complete multiline private-key
  blocks, including log-prefixed body lines, before evidence sampling.
- Extracted diagnostic secret filtering into a focused module and replaced
  polynomial assignment and private-key regexes with bounded scanning after
  CodeQL identified uncontrolled-input performance risks.

## 2026-08-09 - Defensive Fusion critic failover (0.4.68)

- Reframed the targeted critic retry as an independent defensive evidence
  review so provider safety handling does not confuse defensive assurance with
  an offensive request.
- Extended the existing bounded retry to one distinct critic failover when the
  first retry is unavailable, abstains, or returns no qualifying challenge.
  Quorum and synthesis remain fail closed; no model agreement is converted into
  fabricated dissent.
- Added retry-attempt and abstaining-critic telemetry to Copy MD and Run Trace.

## 2026-08-09 - Stale HoloIndex authority recovery admission (0.4.67)

- Extended the existing Holo incident contract to admit an independently
  inspected clean authority checkout at an older HEAD. Preserved its actual
  HEAD and root digest instead of erasing the evidence on selection failure.
- Reused the post-merge coordinator and exact-SHA OpenClaw maintenance task;
  no second queue, lifecycle, signer, database, or query-time reindex path was
  created.
- Bound each incident through a separate immutable AgentDB association instead
  of altering the canonical SHA task/request/completion. Recovery therefore
  accepts maintenance that predated the incident while rejecting a missing or
  attacker-modified association.
- Allowed immutable blocked-request staging while maintenance is pending, but
  kept claim and retry current-authority-only and generation-bound.
- Added deterministic queued-recovery dialogue so RedDog reports internal
  repair status without spending a model call or asking 012 for repository
  paths. The dialogue consumes the actual extension-stage `incident_task_id`
  field and rejects legacy or substituted task fields. Preserved tri-state
  target-recall truth.

## 2026-08-07 - HoloIndex blocked-request recovery binding (0.4.66)

- Bound the pinned backend's integrity-checked Holo incident receipt to the
  existing AgentDB maintenance task and atomic completion event, then required
  an independently queried owner result for that exact generation.
- Kept the request in SecretStorage and consumed it before the advisory model
  retry. Reused the AgentDB coordination-event primary key as the cross-process
  one-use admission CAS. Waiting uses bounded asynchronous backoff; invalid
  and terminal packets are retired without adding another table or lifecycle.
- Removed raw staged request/query material from review output, continued a
  durably admitted READY retry across a racing panel disposal, surfaced
  terminal rejection, and skipped the resident-session wrapper entirely.
- Bound the original request and incident to an immutable digest-only AgentDB
  stage event. Recovery IDs no longer contain caller-restampable timestamps;
  rehashed mutations and restamped packets lack the exact stage commitment.
  READY model bridges detach from webview disposal while remaining bounded.
- Re-ran grounding, redaction, Fusion, and output validation while forcing
  start-operations, wardrobe, WRE, OpenClaw enqueue, and resident execution
  off. Added no maintenance, signer, repository, merge, HoloIndex mutation, or
  PatternMemory authority.
- Required a current backend-manifest preflight against the exact immutable
  recovery bridge root before stage or claim invocation, while keeping empty
  startup polling free of that scan.

## 2026-08-07 - Grounding-failure architect dialogue (0.4.65)

- Replaced terminal local `DEFER` behavior after typed-grounding failure with
  one principal-only, redaction-gated architect diagnosis.
- Sent only a bounded failure receipt and untrusted work focus; admitted no
  repository evidence, conversation history, critic panel, or direct-read body.
- Added an explicit conversation-only runtime gate that prevents validation,
  wardrobe selection, work orders, resident execution, enqueue, or repository
  effects regardless of model output.
- Preserved fail-closed redaction, backend compatibility, timeout, malformed
  response, and bridge-error behavior.

## 2026-08-06 - Principal Memex live resident source (0.4.64)

- Added SecretStorage commands for one pre-issued principal-signed disclosure;
  RedDog does not mint or sign the packet.
- Deleted the packet before one-shot bridge use and kept it out of the resident
  intent, durable audit tasks, status output, logs, and receipts.
- Deferred the opaque Principal-context capability until the durable cycle's
  final model checkpoint, then bound the actual cycle/current generation and
  rechecked expiry immediately before provider invocation.
- Preserved the signed accepted-decision subset and order with no work,
  repository, signer, merge, FoundUp-projection, or HoloIndex authority.
- Serialized SecretStorage consumption so concurrent calls cannot resurrect a
  spent disclosure. Memex-informed determinations persist no model-authored
  free text or proposal and cannot emit a queue candidate.
- Restored a packet only after explicit `consumed=false`; indeterminate or
  failed bridge outcomes retire it to avoid resurrecting consumed evidence.

## 2026-08-06 - Explicit signer request authority (0.4.63)

- Pinned the backend dependency closure containing the signer-owned policy
  gate and its secret-access grant contract.
- Preserved the thin-client boundary: no signing key, signer, work, repository,
  merge, or HoloIndex authority was added to the extension.

## 2026-08-06 - Principal Memex resident-admission backend (0.4.62)

- Pinned the backend dependency closure after authenticated, one-use Principal
  Memex context admission reached the resident architect model boundary.
- Added no extension history source, worker dispatch, repository, signer,
  merge, FoundUp, or HoloIndex authority.

## 2026-08-06 - Conversation scope-kind backend boundary (0.4.61)

- Pinned the backend manifest that introduces immutable `foundup`, `principal`,
  and `comparison` conversation scope kinds. Principal and comparison scopes do
  not receive work or repository authority.
- Bumped the VSIX version because the accepted backend integrity digest changed.

## 2026-08-06 - Conversation session authority source (0.4.60)

- Added VS Code SecretStorage commands for a pre-issued principal-signed
  conversation credential; no production credential minting was introduced.
- Replaced environment-label authorization in the resident editor bridge with
  verified session subject plus signed current-generation principal authority.
- Passed the credential through one-shot stdin, not environment variables;
  no HMAC or private signing material enters the resident process.
- Bound repository, audience, transport, TTL, FoundUp scope, signed principal
  record, generation lease, intent and grounding digests into admission.
- Kept conversation identity distinct from principal-signed work authority and
  added no worker, repository, merge, signer, or HoloIndex effect.
- Pinned the regenerated backend dependency graph after the shared typed
  authority-profile gate reached every runtime effect boundary.

## 2026-08-06 - Conversation proposal backend compatibility (0.4.59)

- Regenerated and pinned the exact backend dependency graph after authenticated
  conversation-to-work proposal promotion became runtime-reachable.
- Added no editor session issuer, worker dispatch, repository/merge authority,
  or HoloIndex mutation.

## 2026-08-06 - Linked-worktree HoloIndex runtime-root resolution (0.4.58)

- Preserved the authority checkout as the source of indexed repository bytes.
- Resolved Python dependencies from the same repository's primary worktree so
  clean linked worktrees do not require duplicate virtual environments.
- Kept queries generation-bound and read-only; no query-time refresh or
  re-index authority was added.
- Regenerated the backend manifest to bind the changed authority/query runtime.

## 2026-08-06 - Conversation history policy enforcement (0.4.57)

- Separated the sanitized last-packet continuation summary from raw provider
  conversation history.
- Added a zero-admission policy until authenticated FoundUp-scoped conversation
  state exists; prior raw turns cannot reach Fusion or persist back into editor
  state.
- Added truthful Run Trace/Copy MD telemetry for requested inclusion, stored and
  admitted counts, admitted turn IDs, rejection reason, setting-sensitive prompt
  policy key, and discarded provider history.
- Preserved the existing no-authority boundary and deferred persistent scope and
  work promotion to later slices (WSP 00, 15, 22, 50, 62, 97).

## 2026-08-05 - Current-generation trust binding manifest pin (0.4.56)

- Pinned the regenerated backend manifest containing the signer
  current-generation use-time evidence and explicit external-issuer blocker.
- Raised only the manifest serialization cap from 256 to 320 KiB after the
  bounded 1,194-file dependency closure crossed the old limit. Pretty JSON is
  retained for reviewable diffs; the 1,250-file and 32 MiB runtime caps remain.
- Preserved the thin-client boundary: no extension authority or runtime
  invocation behavior changed. Peer-handshake and six other live-canary trust
  anchors remain fail-closed (WSP 00, 15, 22, 50, 62, 97).

## 2026-08-04 - HoloIndex vector-segment convergence manifest pin (0.4.54)

- Pinned the regenerated backend manifest containing the bounded HoloIndex
  vector-segment cold-start convergence proof.
- Preserved the thin-client boundary: no extension behavior, authority, or
  runtime invocation path changed (WSP 00, 15, 22, 50, 97).

## 2026-08-03 - Fusion critic retry route failover (0.4.54)

- Changed the existing one-shot adversarial critic retry to prefer a configured
  critic that returned usable initial content over a blocked or abstaining
  route, preserving configured model order as the deterministic tie-breaker.
- Kept the retry count at one and preserved the substantive challenge, evidence,
  output-validation, and runtime-consumption gates. No queue, OpenClaw, Hermes,
  worktree, repository, PR, or merge authority was added (WSP 00, 15, 22, 50, 97).

## 2026-08-03 - Upstream Hermes artifact runtime (0.4.53)

- Pinned the backend manifest containing the actual authenticated loopback
  Hermes `/v1/runs` artifact provider and its fail-closed tool/skill
  confinement. The extension remains a thin client and gains no direct model,
  secret, shell, repository, or Hermes invocation path.

## 2026-08-02 - Upstream OpenClaw artifact runtime (0.4.52)

- Bound production artifact generation to the actual upstream OpenClaw
  Gateway CLI and a dedicated, fail-closed confined agent.
- Required signed AgentDB/WRE/model authority before any provider process and
  propagated observable provider effects through the durable receipt chain.
- Kept Hermes production dispatch blocked until its upstream runtime can prove
  authenticated split-runtime identity and confinement.
- Regenerated the canonical backend manifest and advanced the installed-client
  build identity so stale VSIX installs cannot silently reject current main.

## 2026-08-02 - Canonical WSL agent runtime availability binding (0.4.51)

- Pinned the generated backend manifest containing the opt-in OpenClaw/Hermes
  WSL availability adapter.
- Kept the adapter disabled by default and explicitly non-authoritative.
- Resolved `wsl.exe` through the Windows system API and constrained child output
  to normalized product-version lines.

## 2026-08-02 - Governed runtime compatibility evidence supplier (0.4.50)

- Bound the new WRE-side OpenClaw/Hermes/Qwen/backend evidence supplier into
  the canonical backend manifest.
- Startup remains cached-evidence-only and nonblocking. The extension does not
  fetch releases, install updates, load models, or mutate runtime routes.
- The supplier reuses the existing OpenClaw watchlist runner and canonical
  runtime-artifact safety layer.
- Hardened the truth boundary after independent review: recomputed source
  self-hashes can produce only integrity-checked `OBSERVED_MATCH` or
  `OBSERVED_DRIFT`; overall state remains `NOT_READY` until signed source
  authentication exists.

## 2026-08-02 - Runtime compatibility advisory manifest binding (0.4.49)

- Added the dependency-launcher runtime compatibility advisory and its two
  implementation modules to the canonical RedDog backend manifest.
- Updated the exact manifest digest pin and extension build identity.
- The advisory remains read-only and nonblocking; no update or dispatch
  authority was added to the extension.

## 2026-08-02 - HoloIndex incident to WRE repair runtime (0.4.48)

- Added a bounded extension/Python incident bridge for exhausted semantic-owner
  startup, poisoning, and backend-unavailable failures.
- Reused the exact-HEAD post-merge AgentDB/OpenClaw coordinator for durable
  dedupe, retry, cooldown, authority-worktree validation, and freshness proof.
- Added process-local owner provenance, an independent Python owner requery,
  canonical receipt/evidence validation, and bounded failure serialization.
- Added fail-closed telemetry for deferred repair and coding-candidate
  escalation. No direct HoloIndex mutation or model invocation was added.
- Added focused Python and JavaScript security regressions.

# ModLog - RedDog Extension

## 2026-08-02 - HoloIndex persisted vector-segment proof (0.4.47)

- Regenerated and pinned the backend compatibility manifest after the
  HoloIndex maintenance gate began proving persisted vector segments in a
  fresh process.
- Retained the query-only editor boundary: RedDog does not re-index or repair
  HoloIndex during the reasoning request.

## 2026-08-02 - Registry-driven FoundUp work grounding (0.4.46)

- Added a pure canonical-registry resolver for named FoundUp work. Aliases come
  from registry identity, display name, token symbol, and module path; no
  production branch names a specific FoundUp.
- Bound current registry, manifest, module documentation, test history, and the
  provider-neutral Operations Skillz into required direct-read evidence.
- Bound repository HEAD, registry schema/entity/evidence digests, clean
  authority-critical files, and manifest-declared safe mutation surfaces into
  the receipt and downstream runtime handoffs.
- Enforced the checked-in JSON schema through a generic pure validator, deeply
  froze receipts, disclosed workspace-current dirty evidence, and required
  current-checkout revalidation at work-order, WRE, OpenClaw, resident, and
  wardrobe boundaries.
- Removed optional registry audit-history documents from the mandatory read
  budget, widened generic conversational target grammar, and kept generic
  FoundUp registry/onboarding discussions outside identity resolution.
- Unknown, ambiguous, malformed, escaped, dirty-authority, tampered, or
  incompletely recalled FoundUp evidence now blocks Fusion. Direct-read paths
  never derive mutation scope, and the receipt explicitly grants no authority.
- Refreshed and re-pinned the backend compatibility manifest after the
  production Skillz and wardrobe runtime changed, preventing a stale VSIX from
  silently pairing with incompatible backend files.

## 2026-08-01 - Authority-worktree semantic owner repair (0.4.45)

- Bound one-shot HoloIndex owner dependencies to the validated calling
  workspace while retaining repository code and generation proof in the clean
  authority checkout.
- Regenerated and pinned the backend compatibility manifest. No query-time
  re-index, model fallback, or editor execution authority was added.

## 2026-07-30 - HoloIndex owner runtime compatibility release (0.4.44)

- Regenerated the backend runtime manifest after binding nonsealed HoloIndex
  maintenance and owner startup to the validated canonical workspace
  virtualenv.
- Regenerated and re-pinned the manifest for the signed model-runtime
  artifact-generation boundary; the 1,106-file dependency closure remains
  below the explicit 1,150-file fail-closed limit.
- Pinned authenticated terminal health failure handling so backend
  unavailability fails quickly instead of consuming the startup deadline.
- No editor-side execution authority or query-time indexing was added.

## 2026-07-30 - Canonical thin-client release (0.4.43)

- Published current `main` as the canonical RedDog thin client after the
  0.4.42 Codex-intercept draft was quarantined.
- Preserved RedDog as the architect and retained signed
  OpenClaw/WRE/Hermes receipts as the worker-action boundary.
- Included the current generated backend compatibility constants so the VSIX
  verifies the merged runtime before opening operational paths.

## 2026-07-29 - Imperative semantic grounding normalization (0.4.37)

- Added `enhance` to substantive semantic-work detection and removed imperative
  scaffolding such as `continue`, `needed`, and `enhance` from evidence-match
  tokens.
- Preserved the named subject as the grounding obligation, so requests such as
  `continue do the work needed to fix enhance holoindex` can use retrieved
  HoloIndex evidence instead of demanding that evidence repeat command filler.
- Required evidence to cover every substantive target token; connective words
  can no longer substitute for a missing coordinated subject.
- Kept ambiguous pronoun-only follow-ups fail-closed; sanitized continuation
  remains advisory and cannot supply missing target authority.

## 2026-07-29 - HoloIndex health timeout calibration (0.4.36)

- Raised the asynchronous health-worker deadline from 15 to 30 seconds after
  live exact-SHA owner queries measured 14.5-18.5 seconds.
- Preserved worker-thread isolation, timeout failure, no model fallback, and
  the authenticated generation-bound owner proof.

## 2026-07-29 - Receipt-bound health and model freshness routing (0.4.35)

- Added a local HoloIndex health route backed by the existing authenticated,
  generation-bound semantic owner proof in a bounded worker thread.
- Added an explicit provider-catalog freshness route that reports configured
  model availability, chronology completeness, and provider-latest status
  without model inference or production binding changes.
- Restricted both routes to exact single-purpose grammars, blocked compound
  requests, and scrubbed credentials from public-catalog subprocess egress.
- Reused model-intelligence provider receipts and kept benchmark/promotion
  gates authoritative for production model selection.

## 2026-07-29 - Generation-bound owner fallback preservation (0.4.34)

- Preserved accepted, receipt-bound HoloIndex owner evidence when legacy
  bundle assembly falls back to non-JSON output.
- Required an immutable process-local owner proof in addition to deterministic
  receipt validation, closing attacker-recomputed receipt acceptance.
- Captured the bridge process and filesystem primitives inside the owner module;
  caller-supplied or later monkeypatched dependencies cannot mint that proof.
- Added a typed owner-only bundle that discards untrusted fallback text while
  retaining semantic hits, generation binding, and retry telemetry.
- Replaced rejected-owner fallback text with a typed empty bundle and added
  regressions for the exact `0.4.33` broad-audit failure.
- Consolidated every rejected-owner scorecard projection onto the same bounded
  sanitizer so forged error, retry, generation, and receipt fields are dropped.

## 2026-07-29 - Provider-neutral RedDog Operations Skillz (0.4.33)

- Bound the manifest-authenticated `reddog_operations` Skillz receipt and
  content to `start operations` before model binding, grounding, or resident
  submission; submit/resume revalidate the persisted receipt at use time.
- Kept actual provider/model assignment exclusively in signed model-selection
  and runtime-binding receipts.
- Reused the canonical production binding validator for both resident roles;
  host-pinned artifacts with empty signed evidence lineage or invalid role,
  policy, and authority bindings now fail closed before Start Operations.
- Clarified Brain, Breadcrumb, and Memex evidence classes: only authenticated
  snapshot/assignment-bound inputs are consumed, and absence is reported rather
  than inferred.
- Regenerated the backend compatibility manifest. Version 0.4.32 -> 0.4.33.

## 2026-07-29 - HoloIndex cold owner startup alignment (0.4.32)

- Aligned the manifest-sealed query-owner supervisor with the existing bounded
  cold semantic warmup contract while preserving ordinary health limits.
- Regenerated the backend compatibility manifest. Version 0.4.31 -> 0.4.32.

## 2026-07-29 - REDDOG_START_OPERATIONS_HOLO_REPAIR_RESUME_PHASE1 (0.4.31)

- Added a durable, exact-HEAD Holo repair task for failed/stale start-operations
  grounding. OpenClaw claims the task and reuses the canonical maintenance
  handshake; the extension never re-indexes directly.
- Added process-private owner handoff consumption, one bounded grounding retry,
  strict repair telemetry validation, and fail-closed task/context checks.
- The canonical operations profile now exercises one explicit semantic
  readiness target, so failed/stale owner evidence reaches the repair path in
  production. Expired OpenClaw assignments recover by exact timestamp CAS.
- Holo maintenance and owner startup execute only manifest-authenticated
  runtime copies with provider credentials and Python import overrides removed.
- Regenerated the sealed backend runtime manifest. Version 0.4.30 -> 0.4.31.

## 2026-07-29 - START_OPERATIONS_CONTROL_ADAPTER_PHASE1 (0.4.30)

- Added exact local controls for start, status, cancellation, and resume of
  the canonical durable resident architect cycle.
- Bound a checked-in read-only operations profile, clean repo HEAD, strict
  budgets, authenticated FoundUp scope, and distinct host-pinned
  audit/architect model-binding receipt IDs before submission.
- Added fresh request correlation, cumulative output/frame caps, a dedicated
  child-process environment allowlist, and workspace-persisted intent IDs.
- Launches only a real interpreter and dependency directory inside a
  non-redirected workspace `.venv`; `-I -S -B` plus an explicit bootstrap
  excludes `.pth`, `sitecustomize`, `PYTHONPATH`, `PYTHONHOME`, and user-site
  startup injection.
- Executes control code from a copy-time reverified backend-manifest source tree
  so untracked checkout modules cannot shadow standard, dependency, or runtime
  imports.
- Rejects runtime-materialization roots inside or above the audited repository.
- Loads standard library, sealed source, then dependencies and reauthenticates
  copied source bytes at every import and entry-script execution.
- Reserves manifest-derived module/package names to prevent deletion fallback
  into identically named dependency packages.
- Enforces the frame cap before parsing or dispatching an over-limit progress
  frame.
- Labeled all no-effect fields as implementation-boundary attestations rather
  than independent forensic evidence.
- Bypassed extension advisory Fusion while preserving the resident cycle's
  redaction-gated model calls. No source, shell, HoloIndex mutation, Hermes,
  worktree, PR, or merge authority was added.
- Regenerated and pinned the 1,072-file backend dependency manifest.

## 2026-07-28 - REDDOG_FOUNDUP_MEMEX_AUTHORITY_DISPATCH_BINDING_PHASE1 (0.4.29)

- Pinned optional signed Memex supply lineage through worker materialization,
  dispatch, AgentDB execution, read-only assignment, and independent review.
- Added canonical signed-authority digest revalidation at verifier admission;
  post-signing substitution and malformed or legacy bindings fail closed.
- Regenerated and pinned the 1,062-file backend dependency manifest.
- Preserved read-only editor authority. Version 0.4.28 -> 0.4.29.

## 2026-07-28 - REDDOG_SIGNED_WORKER_ADMISSION_AND_LEASE_SECURITY_REPAIR_PHASE1 (0.4.28)

- Required an opaque process-local verification seal before a serialized
  signed-worker envelope can reach AgentDB execution admission.
- Bound active-lease validation, task transition, assurance completion, and
  durable result-ledger append in one database transaction.
- Made invalid-assignment quarantine transactional and prevented forged local
  quarantine markers from releasing or reconciling verifier capacity.
- Regenerated and pinned the 1,060-file backend dependency manifest.
- Preserved read-only editor authority; this release adds no editor-side shell,
  repository, publication, or merge capability. Version 0.4.27 -> 0.4.28.

## 2026-07-28 - REDDOG_SIGNED_QUEUE_LINEAGE_AND_STARTUP_VERIFIER_BINDING_PHASE1 (0.4.27)

- Bound the canonical queue-consumer receipt digest and operational snapshot
  through delegated authority, signature verification, AgentDB envelopes, and
  use-time worker dispatch.
- Preserved the configured Ed25519 verifier and confined authority paths as an
  immutable process-local startup context instead of rebuilding trust from
  mutable environment variables.
- Regenerated and pinned the 1,055-file backend dependency manifest after
  held-publication activation, protected assignment, bounded execution-lease
  renewal, and atomic assurance/task/result quarantine/finalization. Raised
  only the explicit runtime-file count cap from 1,024 to 1,100; per-file,
  total-byte, digest, path, and schema checks remain unchanged.
- Added no editor-side shell, worker, repository, publication, or merge
  authority. Version 0.4.26 -> 0.4.27.

## 2026-07-27 - REDDOG_RESIDENT_QUEUE_EXACT_SHA_COMMIT_STAGE_PHASE1 (0.4.26)

- Added the backend exact-SHA commit stage between bounded authoring and
  independently assigned verification.
- Pinned exact base, parent, head, tree, work-order, branch, worktree, and path
  evidence; rejected pre-staged, extra, changed, or unbound work.
- Revalidated the canonical commit receipt before verifier admission.
- Regenerated and pinned the 1,002-file backend dependency manifest.
- Version 0.4.25 -> 0.4.26.

## 2026-07-27 - WRE_CHECKOUT_LOCAL_SKILL_RESOLUTION_PHASE1 (0.4.25)

- Pinned the regenerated 1,001-file backend manifest after WRE Skillz
  resolution became checkout-local and bound the authoritative registry.
- Preserved the backend API and runtime graph versions; this release adds no
  editor-side execution authority.
- Version 0.4.24 -> 0.4.25.

## 2026-07-27 - REDDOG_HOLOINDEX_OWNER_COLD_START_RETRY_PHASE1 (0.4.24)

- Added one bounded restart for explicit transient failures from the
  process-private HoloIndex semantic owner.
- Kept configured owners, stale state, authority mismatches, malformed
  evidence, and exhausted retries fail-closed without runtime re-indexing.
- Added owner attempt, retry, and reason telemetry to Run Trace.
- Version 0.4.23 -> 0.4.24.

## 2026-07-27 - REDDOG_BACKEND_MANIFEST_POSTMERGE_REFRESH_PHASE1 (0.4.23)

- Regenerated the backend dependency closure after exact-SHA HoloIndex
  post-merge maintenance landed.
- Pinned all 1,000 runtime files and the new canonical manifest digest without
  weakening fail-closed compatibility validation.
- Added generator sentinels for the maintenance lock, query admission,
  OpenClaw supervisor, task runner, AgentDB, and post-merge coordinator.
- Version 0.4.22 -> 0.4.23.

## 2026-07-25 - REDDOG_HOLOINDEX_SEMANTIC_EVIDENCE_RECEIPT_BINDING_PHASE1 (0.4.22)

- Bound the exact semantic evidence serialization and item count into the canonical HoloIndex query receipt.
- Made the extension verify and consume only receipt-bound semantic evidence; altered or malformed transport evidence now fails closed.
- Preserved the read-only authority-worktree, generation, owner-lifecycle, and no-runtime-reindex boundaries.
- Version 0.4.21 -> 0.4.22.

## 2026-07-25 - REDDOG_HOLOINDEX_PARENT_PROCESS_WATCHDOG_PHASE1 (0.4.21)

- Replaced the v0.4.19/v0.4.20 blocking stdin reader after live proof showed it starved semantic health while the service remained listening.
- Bound auto-owned child lifetime to the exact supervisor PID/process handle and restored child stdin to `DEVNULL`.
- Preserved the 30-second semantic probe, 300-second total startup deadline, token secrecy, generation proof, and query-time no-reindex boundary.
- Version 0.4.20 -> 0.4.21.

## 2026-07-25 - REDDOG_HOLOINDEX_OWNER_PROBE_BUDGET_PHASE1 (0.4.20)

- Raised only the auto-owner's authenticated health-probe response window from one to 30 seconds after a live semantic canary required 11.22 seconds.
- Preserved the 300-second total startup deadline, exact semantic/generation proof, fail-closed cleanup, process-private token, and query-time no-reindex boundary.
- Version 0.4.19 -> 0.4.20.

## 2026-07-25 - REDDOG_HOLOINDEX_OWNER_LIFECYCLE_HARDENING_PHASE1 (0.4.19)

- Added a pre-spawn exclusive loopback port check so a stale or foreign listener fails immediately instead of consuming the five-minute cold-start budget.
- Added a supervisor-owned stdin liveness pipe; the private HoloIndex owner exits when the parent process dies and closes the pipe.
- Preserved process-private bearer handoff, loopback-only binding, read-only query authority, and no runtime re-index behavior.
- Corrected the authority-path truth boundary: selection metadata is digest-only, while existing semantic-hit paths are unchanged.
- Version 0.4.18 -> 0.4.19.

## 2026-07-25 - REDDOG_HOLOINDEX_AUTHORITY_WORKTREE_QUERY_BINDING_PHASE1 (0.4.18)

- Added read-only selection of a configured or deterministic sibling HoloIndex authority worktree only when it is linked to the same Git common directory, clean, and at the workspace's exact HEAD.
- Bound repository-root digest, workspace-overlay state, authority HEAD, generation, and no-authority-mutation proof into the owner response, canonical query receipt, bundle metadata, and Run Trace.
- Re-proved workspace and authority state after semantic retrieval; configured-owner root mismatch and any selection change fail closed before evidence acceptance.
- Preserved the dirty workspace as the direct-read overlay. No query-time worktree creation, checkout, reset, repository mutation, or HoloIndex re-index was added.
- Version 0.4.17 -> 0.4.18.

## 2026-07-25 - REDDOG_EXTENSION_RECEIPT_BOUND_MODEL_RUNTIME_BINDING_PHASE1 (0.4.17)

- Added a read-only Python/JavaScript runtime-binding query that rehydrates the existing model binding receipt from its confined outside-repo root.
- Required nonzero verifier policy, benchmark/promotion/signed-promotion lineage, exact principal/panel role topology, and an external authority receipt.
- Labeled missing configuration `evaluation_config`; partial, malformed, tampered, wrong-surface, or topology-invalid configuration blocks before OpenRouter.
- Added model source, runtime-binding status/ID, selection/catalog lineage, task family, and role bindings to Run Trace.
- No selector, benchmark, HoloIndex, worker, action-authority, shell, or runtime-artifact mutation was added.
- Version 0.4.16 -> 0.4.17.

## 2026-07-25 - REDDOG_FUSION_SEMANTIC_RETRY_AND_QUORUM_EVIDENCE_PHASE1 (0.4.16)

- Added one bounded, receipted semantic retry for empty/`None` lead output.
- Added one bounded targeted adversarial critic retry before failing a no-challenge quorum.
- Prevented `No material challenge:` responses from satisfying the challenge gate.
- Surfaced lead and critic semantic-retry evidence in Copy MD without prompt, response, or reasoning content.
- Kept synthesis fail-closed behind required evidence, a substantive lead, and a material challenge.
- Version 0.4.15 -> 0.4.16.

## 2026-07-25 - REDDOG_CONVERSATIONAL_DRAFT_ROUTING_PHASE1 (0.4.15)

- Added an anchored conversational reply/message-drafting policy with explicit worker-prompt exclusion.
- Forced the route to regular effort, no repository context, and one redaction-gated model even when manual Fusion/context settings are selected.
- Treated pasted message content as untrusted data and kept all drafting output outside validation, wardrobe, queue, worker, and runtime-consumption authority.
- Preserved local fast-path model routing through a shared local-mode resolver.
- Version 0.4.14 -> 0.4.15.

## 2026-07-25 - REDDOG_TYPED_SEMANTIC_PATH_SUPPRESSION_RECONCILIATION_PHASE1 (0.4.14)

- Preserved semantic audit/evaluation obligations containing slash-delimited product or subsystem names such as `OpenClaw/WRE/Hermes`.
- Kept slash-shaped prose out of repo-file targets and low-confidence telemetry unchanged.
- Limited semantic-line suppression to actual bound repo targets, preserving the existing no-duplicate behavior for path-backed audits.
- Version 0.4.13 -> 0.4.14.

## 2026-07-25 - REDDOG_WORK_STATE_AUTHORITATIVE_GROUNDING_GATE_PHASE1 (0.4.13)

- Added a local authoritative work-state route for direct current/next-work questions.
- Validated external snapshot revision/age, governed queue/claim/freshness lineage, selected-slice consistency, and canonical WSP_15 allocation before reporting work.
- Returned a digest-bound read-only receipt and failed closed to `NOT_READY` without HoloIndex, model, queue/claim mutation, worker dispatch, shell, or execution.
- Corrected all local fast paths to skip repository/HoloIndex context assembly before producing their local response.
- Recorded `HOLOINDEX_REDDOG_WORK_STATE_QUERY_DISCOVERABILITY_GAP_PHASE1`: query-only checks rejected the dirty feature worktree and reported root/head/collection staleness from a clean merged worktree; no runtime re-index was performed.
- Version 0.4.12 -> 0.4.13.

## 2026-07-25 - REDDOG_EXTENSION_BACKEND_COMPATIBILITY_PREFLIGHT_PHASE1 (0.4.12)

- Added an extension-pinned repository backend manifest, generated 989-file executable/runtime dependency closure, per-file content digests, and a pure compatibility preflight for the editor thin client.
- Corrected package-initializer relative-import resolution, bound `holo_index.py` as an executable root, and fail-closed undeclared file-based dynamic loaders.
- Added exact-case Git tracking and package-relative dynamic-import resolution so manifests regenerate identically on case-sensitive and case-insensitive hosts.
- Moved activation, ingress, model, and action-boundary closure checks to an extension-owned worker thread; synchronous repair/judgment bridges recheck before launch.
- Blocked before grounding, HoloIndex, model, permission, and work-order paths when the selected workspace is stale, incomplete, altered, malformed, junction-backed, symlinked, or API-incompatible; rechecked before model and action-planning boundaries.
- Split compatibility logic into WSP_62-compliant modules and rejected every unsafe intermediate path component, including in-root Windows junctions.
- Added allowlisted content-free compatibility telemetry and a visible blocked install state without automatic repair or runtime re-index.
- Version 0.4.11 -> 0.4.12.

## 2026-07-20 - REDDOG_RESIDENT_CYCLE_CAS_ATTESTATION_AND_INTENT_BINDING_PHASE1 (0.4.11)

- Routed editor resident sessions through `RedDogResidentArchitectClient` instead of invoking the backend cycle directly.
- Required host-authenticated principal and FoundUp scope, and bound both into the complete resident intent identity.
- Added canonical genesis-state validation, revision-CAS transitions, terminal cancellation, monotonic retry history, and integrity-aware worker/model checkpoints.
- Kept the nine no-effect fields explicitly process-local self-attestations; transition receipts remain internal-integrity telemetry, not signed authority.
- Version 0.4.10 -> 0.4.11.

## 2026-07-20 - REDDOG_REPO_AUDIT_GROUNDING_FALLBACK_PHASE1 (0.4.10 unchanged)

- Added entity-to-path repository/module audit grounding without replacing the generation-bound semantic owner, focused deep-dive selection, progress, usage, or signed Fusion panel behavior already present in 0.4.10.
- Structured Holo candidates must yield readable implementation source plus independent test/contract evidence; incomplete evidence activates bounded deterministic discovery and final protected packing, then fails locally if source/test non-vacuity does not survive context assembly.
- Preserved the primary Fusion `review_packet` across schema repair, records repair separately, and treats empty/`None` critics as abstentions under defensive cybersecurity wording.
- No provider/model call, HoloIndex re-index, repository mutation, live enqueue, Hermes dispatch, PR, or merge authority was added.

## 2026-07-20 - REDDOG_FUSION_PROGRESS_AND_OPENROUTER_USAGE_RECEIPTS_PHASE1 (0.4.10)

- Added digest-bound, hash-chained Fusion progress events and per-call OpenRouter usage/routing receipts.
- Added chunk-safe stderr progress decoding and UI role/model/status details without exposing prompts, outputs, private reasoning, or secrets.
- Added Run Trace totals for calls, failures, retries, duration, tokens, OpenRouter cost credits, generation IDs, and selected routes; incomplete provider cost remains explicitly unknown.
- Kept the unkeyed progress receipt observational: process-local run binding rejects cross-run receipts, while runtime authority remains governed by the existing signed gates.
- Kept non-streaming model calls, redaction, quorum, model selection, and execution authority unchanged.
- Version 0.4.9 -> 0.4.10.

## 2026-07-19 - REDDOG_REPO_DEEP_DIVE_FOCUS_BOUND_TARGET_SELECTION_PHASE1 (0.4.9)

- Reserved the repository deep-dive core for token-matched paths under an explicit named focus when readable implementation, test, and document evidence all exist.
- Retained at most two off-anchor generation-bound semantic dependencies only when their evidence text explicitly names the focus; unrelated semantic hits cannot consume the 12-file budget.
- Added fail-closed focus-pool integrity checks and Run Trace provenance for anchor source, match mode, strategy, candidate count, cross-cutting targets, and fallback reason.
- Marked character- or count-truncated tracked-file manifests incomplete so filtering cannot turn partial repository enumeration into a completeness claim.
- Preserved broad discovery when the focus corpus is incomplete; the existing focus-coverage gate still blocks unsupported deep dives before Fusion.
- Added regressions for semantic decoys, bounded cross-cutting dependencies, explicit-focus parsing, substring collisions, broad fallback, gate tampering, and scorecard telemetry.
- Version 0.4.8 -> 0.4.9. No shell, repository mutation, HoloIndex re-index, OpenClaw/Hermes execution, PR, or merge authority was added.

## 2026-07-19 - REDDOG_DEEP_DIVE_OWNER_FAILURE_DIRECT_READ_CONTINUITY_PHASE1 (0.4.8)

- Preserved locally governed repository direct reads when the generation-bound semantic owner is unavailable; semantic hits remain withheld and explicit semantic obligations still fail closed.
- Removed generic `repository` wording from external-research target detection and added exact 0.4.7 host-trace regression coverage.
- Hardened deterministic manifest ranking so named subsystem concepts such as `p.fMALL` outrank WSP and instruction words.
- Required implementation, test, and document coverage tied to the primary focus anchor before a deep dive may reach Fusion.
- Marked fetched repository bodies as untrusted evidence, corrected direct-read telemetry, and classified missing/timeout/malformed owner failures without exposing raw diagnostics.
- Added manifest-cap telemetry and fail-closed deep-dive rejection so repository scale cannot silently hide later targets.
- Corrected the already-exceeded temporary WSP_62 ceiling from 7900 to 8350 lines for this focused integration-boundary change; the existing Q3 decomposition owner and expiry remain unchanged.
- Version 0.4.7 -> 0.4.8. No shell, repository mutation, HoloIndex re-index, OpenClaw/Hermes execution, PR, or merge authority was added.

## 2026-07-19 - REDDOG_REPO_DEEP_DIVE_DISCOVERY_PHASE1 (0.4.7)

- OBSERVED: RedDog 0.4.2 accepted a requested repository deep dive with zero repository targets, zero direct reads, and no source context; the active editor also biased the module hint to `extensions/reddog`.
- Added bounded tracked-file manifest discovery and deterministic target ranking seeded by generation-bound HoloIndex evidence. Discovered targets reuse the existing governed direct-read, redaction, protected-packing, and recall-proof stack.
- Broad repository deep dives now fail closed before Fusion unless manifest generation, nonzero targets, complete recall, nonzero direct-read bytes, and source-context inclusion all pass.
- Version 0.4.6 -> 0.4.7. No repository mutation, shell execution, HoloIndex re-index, OpenClaw enqueue, Hermes execution, PR, or merge authority was added.

## 2026-07-19 - REDDOG_TRANSPORT_NEUTRAL_GROUNDING_SERVICE_PHASE1 (0.4.6)

- Kept blockquote and fenced reference blocks separate when adjacent.
- Removed quoted/fenced content before external-research target extraction, so supplied URLs remain data rather than actionable retrieval instructions.
- Added editor/backend target-class parity coverage and transport-neutral Hermes grounding support in the backend runtime.
- Version 0.4.5 -> 0.4.6. No new shell, repository mutation, indexing, execution, PR, or merge authority.
- Full RedDog extension contract suite passed after the extractor and version changes.

## 2026-07-19 - REDDOG_GROUNDED_TARGET_ASSIGNMENT_CONTINUITY_PHASE1 (0.4.5)

- Added immutable `reddog_grounded_target_receipt.v1` generation at the editor thin-client boundary.
- Bound work focus, typed target universe, direct-read recall, semantic coverage, and current HoloIndex generation proof into resident intent v2.
- Revalidated the receipt through the durable AgentDB cycle, OpenClaw assignment/task publication, and the read-only 0102 worker before index or model calls.
- Preserved internal semantic targets for all audit lanes while keeping explicit external-research targets confined to the governed research adapter.
- Version 0.4.4 -> 0.4.5. WSP_15: Complexity 4 + Importance 5 + Deferability 5 + Impact 5 = 19 (P0).

## 2026-07-19 - REDDOG_HOLOINDEX_GENERATION_BOUND_QUERY_RUNTIME_PHASE1 (0.4.4)

- Replaced unbound semantic evidence from the extension's direct `holo_index.py --bundle-json` subprocess with an authenticated query through the existing localhost HoloIndex owner service.
- Added a bounded Python bridge that reuses owner bootstrap/handoff/client code and emits the canonical generation-bound query receipt without exposing the owner token or invoking any indexer.
- Semantic hits now reach grounding only when owner result and receipt agree on CURRENT freshness, semantic retrieval, clean repository HEAD, generation ID, freshness-receipt digest, no index gap, and no runtime re-index.
- Preserved governed direct-read bodies for explicit repository targets while preventing those bodies from masking stale semantic-generation telemetry.
- Extracted generation-bound acceptance, bundle merge, and metadata projection to `holoindex_generation_bound_query.js`, keeping `extension.js` within its temporary WSP_62 ceiling.
- Added Run Trace fields for owner acceptance, freshness, generation, repository HEAD, query receipt, source, error class, and query-only proof.
- Fixed the existing owner supervisor's stale-readiness loop: authenticated terminal freshness failures now stop startup immediately instead of being retried until the five-minute startup timeout; transport/auth/malformed failures remain opaque and retry-bounded.
- Version 0.4.3 -> 0.4.4. WSP_15: Complexity 3 + Importance 5 + Deferability 5 + Impact 5 = 18 (P0).

## 2026-07-19 - REDDOG_BROAD_SEMANTIC_GROUNDING_NONVACUITY_PHASE1 (0.4.3)

- Replaced the hardcoded semantic-domain noun gate with a generic, bounded action-and-subject derivation rule, so short repository audits such as `Audit <FoundUp>` create a semantic target without embedding FoundUp-specific names or paths in the extension.
- Kept explicit repo paths, external sources, and explicit semantic headers authoritative; generic fallback does not add duplicate `Determine` or prose targets when those stronger channels are present.
- Added a fail-closed `grounding_target_universe_empty` decision for substantive audit, implementation, verification, and research requests that still produce no actionable target. Fusion is not called after this rejection.
- Broad audit targets now use one bounded generic query expansion and require two distinct evidence references spanning implementation/authority plus verification/authority categories. Matching filenames without descriptive content no longer count as evidence.
- Added HoloIndex test, symbol, and knowledge buckets to semantic evidence projection and surfaced original/effective query plus expansion strategy in Run Trace telemetry.
- Preserved local identity and operational-diagnostic fast paths, per-target content-bearing HoloIndex evidence, query-only runtime behavior, and the existing no-runtime-reindex boundary.
- Version 0.4.2 -> 0.4.3. WSP_15: Complexity 2 + Importance 5 + Deferability 5 + Impact 5 = 17 (P0).

## 2026-07-18 - REDDOG_EXPLICIT_EMPTY_FUSION_PANEL_FAIL_CLOSED_PHASE1 (0.4.2 unchanged)

- Made an explicitly supplied Fusion panel list authoritative at both extension ingress and the Python bridge: `[]` and invalid-only lists remain empty instead of silently restoring `DEFAULT_PANEL_MODELS`; omitted/non-list inputs retain compatibility defaults.
- Both manual FoundUps Fusion and the OpenRouter Fusion alias now receive the exact filtered panel through stdin, reject an empty explicit panel before any model/provider call, and receipt the exact selection and truncation state. The extension forwards at most seven entries while Python owns the six-model runtime cap, preserving one overflow sentinel instead of hiding truncation behind the former four-model extension slice.
- Reserved bridge-owned review-packet fields so caller-controlled `bridge_meta` cannot spoof the selected mode, lead, panel, truncation, budgets, excerpts, quorum, or retry truth; non-core extension telemetry still propagates.
- Extracted focused rejection/success packet builders, reduced `_openrouter_fusion_alias` to 45 lines, and moved manual empty-panel rejection into a compliant public wrapper while preserving the inherited 201-line Fusion core body. Split the new panel matrix into a 239-line focused test file; `_run_foundups_fusion_core` and the 179-line `main` are covered by a temporary exact-function WSP_62 exemption with owned, dated extraction criteria rather than being silently grandfathered.
- Added temporary exact-scope WSP_62 exemptions for `extension.js` (7,900-line ceiling) and the two inherited Python bridge functions (201-line ceiling), both owned by RedDog Maintainers, expiring 2026-09-30, and bound to staged decomposition/removal criteria in `ROADMAP.md`.
- HoloIndex was queried first; offline lexical fallback returned the stale legacy extension path rather than canonical `extensions/reddog`, so implementation used direct canonical reads and performed no re-index.
- Preserved extension version `0.4.2`; package schema now caps both panel settings at the seven-entry forwarding bound, and this remains bridge security hardening with no model promotion, catalog refresh, paid call, Hermes dispatch, or execution authority.
- WSP_15: Complexity 1 + Importance 5 + Deferability 5 + Impact 5 = 16 (P0).

## 2026-07-18 - REDDOG_KIMI_K3_ALL_ROLE_RUNTIME_BUDGET_HARDENING_PHASE1 (0.4.2 unchanged)

- Preserved Kimi K3 as the default long-horizon critic while applying its 4096-token floor, mandatory `max` reasoning, and no-temperature contract to every exact `moonshotai/kimi-k3` direct completion call, including explicit single use and receipt-backed principal/synthesis selection.
- Added truthful direct `requested_max_tokens` / `effective_max_tokens` receipts and retained manual Fusion requested, per-role, and per-panel effective budget receipts; non-K3 budgets remain unchanged.
- This compatibility hardening does not promote K3 to champion, change RedDog defaults, open an OpenClaw execution valve, or dispatch Hermes. Signed promotion and live runtime binding remain separate evidence-gated responsibilities.
- Preserved extension version `0.4.2`; this is a bridge correctness amendment, not a product-surface release.
- WSP_15: Complexity 2 + Importance 4 + Deferability 4 + Impact 3 = 13 (P1).

## 2026-07-18 - REDDOG_HOLO_SEMANTIC_FIRST_PHASE1 (semantic retrieval recovery, 0.4.2)

- Proved the local HoloIndex embedding stack healthy (`sentence_transformers`, cached `all-MiniLM-L6-v2`) and measured a real semantic bundle at 15.6 seconds with five code and five WSP hits.
- Removed RedDog's unconditional `HOLO_SKIP_MODEL=1` production policy. The default read-only bundle clears inherited model-skip state, preserves an operator-set `HOLO_OFFLINE` network boundary, and requires the returned receipt to report `retrieval_mode=semantic`.
- Added explicit `REDDOG_HOLO_RETRIEVAL_MODE=lexical` opt-down for deterministic tests or emergency compute conservation; lexical results are labelled as lexical and never promoted to semantic evidence.
- Fixed the emergency fallback's block-scope defect: the fallback previously referenced `env` outside the `try` block where it was declared, so a primary bundle exception could collapse into `HoloIndex unavailable` instead of running lexical recovery.
- Added requested/actual retrieval mode, embedding backend, and routing state to RedDog HoloIndex metadata, scorecards, and bundle summaries.
- Version 0.4.1 -> 0.4.2 (package.json + EXTENSION_VERSION + README + interface + roadmap + contract tests).
- WSP_15: Complexity 3 + Importance 4 + Deferability 4 + Impact 4 = 15 (P1).

## 2026-07-18 - REDDOG_FUSION_KIMI_K3_PHASE1 (OpenRouter critic integration, 0.4.1)

- Added the verified OpenRouter slug `moonshotai/kimi-k3` to the default manual Fusion panel while retaining Kimi K2.7 Code for implementation comparison and capacity fallback.
- Kimi K3 requests use its published mandatory `max` reasoning contract, omit the unsupported temperature field, and use a receipt-recorded 4096-token critic budget validated by the live compatibility smoke.
- Review packets continue to bind the exact requested panel model IDs; no mutable `kimi-latest` alias is used.
- Version 0.4.0 -> 0.4.1 (package.json + EXTENSION_VERSION + README + interface + contract tests).
- WSP_15: Complexity 3 + Importance 4 + Deferability 4 + Impact 4 = 15 (P1).

## 2026-07-16 - REDDOG_PRODUCT_IDENTITY_AND_THIN_CLIENT_0_4_0 (product identity migration, 0.4.0)

- Renamed the extension folder and product identity from the legacy Foundups Fusion Worker / Foundups(R)Agent surface to RedDog.
- Added canonical `reddog.open` command and `reddog.*` settings while retaining `foundupsFusion.*` aliases for one migration release.
- Added duplicate/stale install telemetry so Copy MD can reject old VSIX or dual-extension host states.
- Added a typed `reddog_intent.v1` resident-session payload. The extension submits intent and receives receipts; it does not submit executable authority, shell authority, repo-write authority, or merge authority.
- Version 0.3.68 -> 0.4.0 (package.json + EXTENSION_VERSION + docs + contract-test assertions).

## 2026-07-16 - REDDOG_EXTENSION_TO_RESIDENT_ARCHITECT_SESSION_RUNTIME_PHASE1 (resident backend session bridge, 0.3.68)

- Added `scripts/reddog_resident_architect_session_once.py`, a JSON-in/JSON-out bridge that delegates to the resident read-only audit/research/backend-architect E2E runtime.
- Added `foundupsFusion.enableResidentArchitectSession` (default false). When enabled and local runtime-consumption gates pass, the extension calls the resident backend and attaches snapshot/swarm/task/report/architect-decision telemetry to the review packet and Copy MD.
- Boundary remains read-only: no shell, repo mutation, HoloIndex re-index, Hermes dispatch, worktree operation, PR creation, PatternMemory promotion, or live FoundUps enqueue.
- Version 0.3.67 -> 0.3.68 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-14 - REDDOG_EXTENSION_TO_OPENCLAW_LIVE_ENQUEUE_RUNTIME_BINDING_PHASE1 (guarded live-enqueue binding, 0.3.67)

- Added a guarded extension runtime binding for `live_enqueue` wardrobe-selection receipts after grounding, fusion quorum, output validation, and runtime-consumption gates pass.
- Added the `scripts/reddog_extension_live_enqueue_invoke_once.py` one-shot bridge, which delegates to the existing explicit live-enqueue invoke guard but keeps the concrete writer disabled in this slice.
- Copy MD now reports the OpenClaw live-enqueue runtime binding result with no worktree, shell, Hermes dispatch, file edit, PR, merge, or reward settlement authority.
- HoloIndex query-only preflight surfaced the existing live-enqueue seam and contract, but the new one-shot script is not indexed yet; no runtime reindex performed.
- Version 0.3.66 -> 0.3.67 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-13 - REDDOG_SEMANTIC_GROUNDING_PER_TARGET_PROOF_PHASE1 (semantic coverage proof, 0.3.66)

- Replaced aggregate semantic grounding (`code_hits + wsp_hits > 0`) with per-target `SemanticTargetCoverage` records.
- Each semantic target now requires independent content-bearing HoloIndex evidence refs; unrelated global hits, backend errors, and ref-less hits fail closed.
- Run Trace and wardrobe grounding receipts now carry semantic required/grounded/missing counts plus a coverage digest.
- Version 0.3.65 -> 0.3.66 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-13 - REDDOG_DAEMON_PROMPT_AUTHORING_OVERRIDE_PHASE1 (prompt requests override log fast path, 0.3.65)

- Fixed prompt-authoring requests that include DAEmon/log output so they no longer route to the instant local diagnostic fast path.
- Requests for worker/slice/M2M prompts now stay on the governed prompt-authoring path and retain bounded prompt-authoring context.
- Operational diagnostic payload suppression still applies to pure log assessment requests.
- Version 0.3.64 -> 0.3.65 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-13 - REDDOG_OPERATIONAL_OUTPUT_TARGET_DERIVATION_GUARD_PHASE1 (browser/DAEmon log target guard, 0.3.64)

- Added an operational-output shape detector for browser/DAEmon diagnostics with URLs, timing values, screenshot filenames, ratios, and status/error tokens.
- Suppresses operational diagnostic payloads from repo-file and external-research target extraction unless an explicit required-target block is present.
- Tightened slashless extension detection so timing values such as `11.7s` and `100.0` cannot become repo-file targets.
- Version 0.3.63 -> 0.3.64 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-13 - REDDOG_DAEMON_OUTPUT_LOCAL_ASSESSMENT_PHASE1 (local DAEmon/log diagnostics, 0.3.63)

- Added a local DAEmon/log output assessment fast path for pasted operational diagnostics.
- Treats pasted output as data, redacts secret-shaped values, and skips HoloIndex, OpenRouter, Fusion, repair, repo/shell work, enqueue, and worktree action.
- Runtime consumption remains blocked with `local_daemon_output_assessment_not_actionable`; logs cannot become instructions or authority.
- Version 0.3.62 -> 0.3.63 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-13 - REDDOG_RUN_TRACE_LOCAL_ASSESSMENT_PHASE1 (local pasted-trace diagnostics, 0.3.62)

- Added a local Run Trace assessment fast path for pasted `## Run Trace` diagnostics so RedDog can explain blocked/slow traces without sending raw trace text through HoloIndex/Fusion/OpenRouter.
- The assessor parses telemetry fields such as `extension_version`, `mode`, `redaction gate status`, `made_network_call`, target recall counts, output validation, and runtime gate reasons, then returns a WSP_97-labeled diagnostic response.
- Runtime consumption remains blocked with `local_run_trace_assessment_not_actionable`; no downstream action planning, repo reads, shell, HoloIndex mutation, or model call is performed.
- Version 0.3.61 -> 0.3.62 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-13 - REDDOG_SIMPLE_IDENTITY_FAST_PATH_PHASE1 (local identity/status answer, 0.3.61)

- Added a narrow local fast path for short identity/status questions such as `are you RedDog?` so they do not escalate through HIGH-tier Fusion routing merely because the prompt contains `RedDog`.
- The fast path answers locally, sets `made_network_call=false`, uses context `none`, skips HoloIndex/OpenRouter/Fusion/repair/judgment verifier, and blocks downstream runtime consumption as non-actionable.
- Added contract coverage proving substantive RedDog audit prompts still classify HIGH and stay on the governed path.
- Version 0.3.60 -> 0.3.61 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-13 - REDDOG_PROMPT_AUTHORING_DELIVERABLE_CONTRACT_PHASE1 (worker prompt artifact gate, 0.3.60)

- Added prompt-authoring detection so requests to create/evaluate/provide worker prompts receive bounded RedDog prompt/judgment context even when no explicit repo paths are named.
- `constructWspTaskPrompt()` now requires a `## Worker Prompt` section with one fenced executable prompt for prompt-authoring asks; missing definitions must be represented as `DEFINITION_GAP` inside the prompt artifact.
- `validateRedDogOutput()` now fails prompt-authoring outputs that omit the executable worker prompt, causing the existing repair path and runtime-consumption gate to fail closed instead of treating advisory prose as complete.
- Version 0.3.59 -> 0.3.60 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_DETERMINE_BLOCK_TARGET_DERIVATION_GUARD_PHASE1 (Determine question target false-positive guard, 0.3.59)

- Fixed the 0.3.58 host block where `Determine:` numbered questions were parsed as markdown/path bullets and conceptual slash phrases such as `ledger/runtime` became false `repo_file_targets`.
- `deriveWorkFocusTargets()` now treats a `Determine:` block as answer/output requirements, not repository read intent, while preserving explicit `Read first:` / required-target capture.
- Added WFTD-021 regression coverage for collection, typed target extraction, target recall, and typed grounding preflight: the multi-lane orchestration-brain prompt now requires exactly the three real repo files and passes grounding when all three are recalled.
- Version 0.3.58 -> 0.3.59 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_EXTENSION_OPERATOR_LOOP_RUNTIME_CONSUMPTION_PHASE1 (validated recommendation gate, 0.3.58)

- Added `buildRuntimeConsumptionGate()` so wardrobe selection, permission probing, WRE dry-run preview, and explicit WRE invocation are only planned after model result OK, output validation pass, Determine verifier pass when applied, and Fusion quorum pass.
- Runtime action planning now stops on redaction, grounding, schema validation, judgment-verifier, or Fusion quorum failure.
- Run Trace now emits `runtime_consumption_gate_passed` and gate rejection reasons.
- Version 0.3.57 -> 0.3.58 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_FUSION_PANEL_QUORUM_PHASE1 (fail-closed Fusion synthesis quorum, 0.3.57)

- Added deterministic Fusion panel quorum checks in `scripts/advisory_model_once.py`: required evidence must be present in packed evidence context, lead output cannot be empty/`None`, at least one critic must challenge framing and priority, and synthesis failure fails closed.
- Removed the previous synthesis fallback that could convert missing synthesis into a usable answer.
- Added bridge hardening tests for missing evidence, missing lead, missing critic challenge, synthesis failure, and successful quorum.
- Version 0.3.56 -> 0.3.57 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_GROUNDING_TO_WARDROBE_SELECTION_RECEIPT_PHASE1 (grounded action-plane selection, 0.3.56)

- Threaded typed grounding preflight into the RedDog operator wardrobe-selection payload and receipt.
- Failed grounding now blocks action-plane selection before Python bridge invocation, preventing wardrobe/live-authority planning from ungrounded inputs.
- Direct Python bridge calls also fail closed on failed grounding with `no_action_plane_selected` / `grounding_blocked`.
- Version 0.3.55 -> 0.3.56 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_TYPED_GROUNDING_PREFLIGHT_PHASE1 (fail-closed grounding coverage gate, 0.3.55)

- Added `buildTypedGroundingPreflight()` to block Fusion before any model call when typed grounding coverage is incomplete.
- Repo-file targets require successful direct-read recall; semantic targets require HoloIndex coverage; external research targets fail closed until approved research retrieval exists; quoted blocks are treated as context-only.
- Added local `grounding_preflight_blocked` result with `made_network_call=false` plus Run Trace grounding preflight telemetry.
- Version 0.3.54 -> 0.3.55 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_TYPED_TARGET_EXTRACTION_PHASE1 (typed grounding input channels, 0.3.54)

- Added `extractTypedTargets()` to split preprocessing into `repo_file_targets`, `semantic_targets`, `external_research_targets`, and `quoted_reference_blocks`.
- Direct-read recall/packing now consumes only `repo_file_targets`; URLs, conceptual research phrases, and quoted/reference blocks are not sent to the governed file reader.
- Run Trace scorecard now reports typed target counts without emitting raw external research snippets.
- Version 0.3.53 -> 0.3.54 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_EXTENSION_GITHUB_PERMISSION_PROBE_RUNTIME_BRIDGE_PHASE1 (read-only permission snapshot, 0.3.53)

- Added `runGithubPermissionProbeBridge()` and `scripts/reddog_github_permission_probe_once.py` to emit a fresh read-only GitHub `repo_permission_snapshot` from the live extension path.
- Threaded the snapshot into the governed work-order candidate so `permission_binding.probe_performed=true` and `permission_truth_label=OBSERVED` only when the probe yields a fresh trusted permission level.
- Added Copy MD/review packet section `## RedDog GitHub Permission Probe`; no token scopes or raw secrets are emitted.
- Boundary unchanged: no signing, worktree create, task execution, OpenClaw enqueue, Hermes dispatch, PR, merge, reward settlement, or HoloIndex mutation.
- Version 0.3.52 -> 0.3.53 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_EXTENSION_OPERATOR_WARDROBE_SELECTION_RUNTIME_BRIDGE_PHASE1 (wardrobe receipt bridge, 0.3.52)

- Added `runOperatorWardrobeSelectionBridge()` and `scripts/reddog_operator_wardrobe_selection_once.py` to emit a deterministic WSP_97/WSP_95 operator wardrobe-selection receipt from the live extension path.
- Copy MD / review packet now include `## RedDog Operator Wardrobe Selection` with selected wardrobe, execution plane, authority boundary, mode/effort, WRE requirement, index-gap posture, and no-execution/no-enqueue flags.
- The WRE runtime wire now receives this locally generated selection receipt as an input, but still skips invocation by default until signed authority, permission, explicit invoke, and valve metadata are present.
- Version 0.3.51 -> 0.3.52 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_RUNTIME_WIRE_PHASE1 (guarded invoke seam, 0.3.51)

- Added `invokeWreOperationalSpineExplicitValveBridge()` and `scripts/reddog_extension_wre_spine_invoke_once.py` as the extension-side runtime seam to the landed Python explicit-valve guard.
- Default RedDog runs remain fail-closed: the runtime wire emits `EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_SKIPPED` unless a ready governed work-order candidate, explicit WRE invocation request, sovereign wardrobe selection receipt, valve environment, permission snapshot, and signed-authority verifier result are all supplied.
- The bridge passes authority metadata through stdin, never argv, and Copy MD surfaces the invoke decision without raw token/signature material.
- Version 0.3.50 -> 0.3.51 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_EXTENSION_WORK_ORDER_PERMISSION_AND_SIGNATURE_BINDING_PHASE1 (authority binding, 0.3.50)

- `buildRedDogGovernedWorkOrderCandidate()` now binds supplied repo permission snapshots and signed-authority verifier results into `permission_binding` and `signed_authority_binding` metadata.
- Readiness is fail-closed: a caller-supplied boolean is not authority; `ready_for_wre_invocation=true` requires a fresh trusted permission snapshot, matching accepted signed-authority result, derived path scope, and explicit worktree valve request.
- The extension does not run the GitHub permission probe, verify signatures, sign payloads, invoke Python/WRE, create worktrees, enqueue OpenClaw, dispatch Hermes, create PRs, merge, or settle rewards in this slice.
- Version 0.3.49 -> 0.3.50 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-12 - REDDOG_EXTENSION_GOVERNED_WORK_ORDER_RUNTIME_EMISSION_PHASE1 (governed work-order candidate, 0.3.49)

- `buildWreOperationalSpineDryRunPreview()` now embeds a full `RedDogGovernedWorkOrder` candidate under `governed_work_order_runtime_emission`.
- The candidate binds extension version, work-focus digest, WSP prompt digest, HoloIndex evidence posture, derived path scope, rollback plan, nonce, expiry, and safe advisory source digests without storing raw work focus.
- Fail-closed boundary: the candidate uses `repo_permission_snapshot.source=extension_runtime_candidate`, `permission_level=needs_verification`, `signed_authority_verified=false`, and `explicit_valve_requested=false`, so it is not WRE-invocation-ready until later authority gates land.
- HoloIndex query-only preflight found the existing RedDog work-order spine and contracts, but not the new extension runtime-emission surface itself; recorded follow-up `HOLOINDEX_REDDOG_EXTENSION_GOVERNED_WORK_ORDER_EMISSION_INDEX_GAP_PHASE1`.
- Version 0.3.48 -> 0.3.49 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-11 - REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_PHASE1 (refreshed contract pointer)

- Refresh stale #905 contract on current main after signed authority (#950) and signed receipt chain (#951).
- Contract remains docs/static-test only: no extension runtime call, no OpenClaw enqueue, no AgentDB write, no Hermes/WRE dispatch.
- Future live enqueue requires `VALVE_OPEN_LIVE_ENQUEUE`, accepted signed work authority, and signed receipt-chain verification.

## 2026-07-12 - HOLOINDEX_READONLY_QUERY_GUARD_PHASE1 (RedDog HoloIndex query posture, 0.3.48)

- RedDog HoloIndex calls now pass `HOLOINDEX_QUERY_READONLY=1` for bundle-json and offline fallback paths.
- HoloIndex CLI now defaults plain query/search mode to read-only and gates search-time auto-refresh behind explicit `--allow-auto-refresh`.
- HoloIndex collection reset refuses to run when `HOLOINDEX_QUERY_READONLY=1`, so a RedDog query process cannot mutate the semantic store even if a write path is accidentally reached.
- Version 0.3.47 -> 0.3.48 (package.json + EXTENSION_VERSION + README + contract-test assertions).

## 2026-07-11 - REDDOG_JUDGMENT_GENERATION_WIRING_PHASE1 (Determine verifier wiring, 0.3.47)

- Wire the landed Determine contract plus adversarial verifier panel into the live RedDog extension path.
- `constructWspTaskPrompt()` now instructs RedDog to emit the canonical `## Determine Answers` fenced JSON block when the 012 work focus contains a Determine numbered list.
- Add `runJudgmentVerifier()` -> `scripts/reddog_judgment_verifier_once.py`, which verifies final Determine answers against already-fetched governed direct-read hits and the HoloIndex scorecard.
- Boundary: local/advisory only. No HoloIndex re-index, WRE enqueue, shell, repo mutation, OpenClaw/Hermes dispatch, or network call is performed by the verifier bridge.
- Copy MD / Run Trace now surface `judgment_verifier_*` telemetry plus an advisory INDEX_GAP event when direct-read evidence masks stale semantic retrieval.
- Version 0.3.46 -> 0.3.47 (package.json + EXTENSION_VERSION + README + contract-test assertions).
## 2026-07-09 - REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_DRYRUN_WIRE_PHASE1 (extension dry-run preview, 0.3.46)

- Added `buildWreOperationalSpineDryRunPreview()` and `buildWreOperationalSpineDryRunPreviewSection()`.
  Substantive non-blocked RedDog packets now emit `review_packet.wre_operational_spine_dryrun_preview`
  and a Copy MD `## WRE Operational Spine Dry-Run Preview` section after the governed handoff section.
- Boundary: preview metadata only. The extension does NOT call
  `modules/communication/moltbot_bridge/src/reddog_wre_operational_spine.py`, does NOT create a worktree,
  does NOT execute tasks, does NOT edit files, does NOT create PRs, does NOT enqueue OpenClaw, does NOT
  dispatch Hermes, and does NOT push or merge. Blocked-local packets skip the preview.
- Safety: raw work focus is not stored in the preview; it records a full SHA256 `command_digest`, bounded
  sanitized `command_redacted_summary`, digest evidence refs, `required_future_valve: VALVE_OPEN_WORKTREE_CREATE`,
  and `required_human_gate: 012_sovereign`.
- Version 0.3.45 -> 0.3.46 (package.json + EXTENSION_VERSION + README + contract-test version assertions)
  so this dry-run preview build is distinguishable from the prior prose-tokenization 0.3.45 build.
- Next gate: `REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_EXPLICIT_VALVE_INVOKE_PHASE1` only after explicit
  `012_sovereign` + `VALVE_OPEN_WORKTREE_CREATE` and leak/non-mutation tests.

## 2026-07-07 - REDDOG_WORK_FOCUS_READ_CAPTURE_PROSE_TOKENIZATION_PHASE1 (P0 hotfix, 0.3.44 -> 0.3.45)

- Problem (OBSERVED, real 0.3.44 run on a free-form prose prompt): a `Read first:` prompt naming three
  files in ONE flowing sentence produced `target_recall_ok: false`. The read-capture branch tokenized the
  NON-bullet prose line with the COMMA-splitter (`extractTargetTokensFromLine`), so
  `holo_index/adaptive_learning/breadcrumb_tracer.py. Determine current lane-state sources` was captured
  WHOLE as `not_a_file` (breadcrumb_tracer.py MISSED) and `and the breadcrumb/handoff layer` (an
  embedded-slash English fragment) was captured whole as a garbage target. Result:
  `required_targets_total=4, recalled=2, target_recall_ok=false`. Derivation ENGAGED (0->4 derived,
  2 fetched) but prose tokenization was imprecise.
- Root cause (VERIFIED by reading): `deriveWorkFocusTargets`'s `read_first` capture used the comma-splitter
  on NON-bullet prose lines. The comma-splitter treats each comma-chunk as one token, so a chunk with a
  path+trailing-prose or an embedded slash becomes a bad target. The bounded path-token regex
  (`extractInlinePathTokens`, already used for source-6 inline prose) isolates clean path substrings.
- Fix (extension.js only; NO Python change):
  - Fix A (essential): the NON-bullet read-capture branch now tokenizes with `extractInlinePathTokens`
    (via new `extractProsePathTokens`) instead of `extractTargetTokensFromLine`. CLEAN BULLETS
    (`stripListMarker(...).isList`) keep the comma/`or`-splitter to preserve the `a / b / c` alternatives
    shape. Recovers `breadcrumb_tracer.py` cleanly.
  - Fix B (recall semantics + tiered strictness): FLOWING-PROSE-derived tokens (read-first prose +
    source-6 inline + source-7 backtick) are LOW-confidence -- a required target ONLY if it normalizes to a
    FILE SHAPE (a lowercase file extension). A prose token with a slash but NO extension
    (`breadcrumb/handoff`) is NOT required: dropped from `required_targets_total` / `required_targets_missing`
    (so it cannot flip `target_recall_ok`) and reported in the NEW `work_focus_targets_dropped_low_confidence`
    telemetry array. The explicit "Required direct-read targets" header, M2M `READ:`, M2M `CTX.FILES`, and
    CLEAN BULLETS keep the broader slash-OR-extension tier (a named directory path is still accepted). Only
    flowing prose is stricter -- the explicit/M2M/bullet tiers were NOT tightened.
  - Fix C (punctuation trim): `normalizeTargetPath` trailing set adds `}` to the existing
    `.` `,` `;` `:` `)` `]`, so `.../breadcrumb_tracer.py. Determine` -> `.../breadcrumb_tracer.py`.
- Reuse / ReDoS: `extractProsePathTokens` REUSES the existing bounded/anchored ReDoS-safe
  `extractInlinePathTokens` (no new backtracking regex introduced); `stripListMarker` (the ReDoS fix) is
  untouched. No `js/polynomial-redos`-style regex added. The governed fetch gate
  (`--bundle-must-include` -> `bundle_json.py` deny/traversal/budget) is unchanged; derived paths still flow
  through it. No Python / bundle_json.py / HoloIndex ranking / redaction change; no live-writer /
  orchestration-brain / budget-prioritization change (budget-prioritization is Phase 2, separate).
- Telemetry: NEW `work_focus_targets_dropped_low_confidence` (array of dropped raw tokens) threaded through
  `evaluateTargetRecall` -> `holoIndexMetaFromBundle` -> `extractHoloIndexScorecard` ->
  `formatHoloIndexScorecardLines` (Run Trace). Labeled OBSERVED (WSP_97). All existing fields preserved.
- Tests: WFTD-015..WFTD-020 in `tests/verify_extension_contract.js` using the EXACT failed 0.3.44 flowing-
  prose prompt as a fixture (`WORK_FOCUS_PROSE_READ_FIRST_PROMPT` in `tests/fixtures.js`): asserts
  `required_targets_total=3 / recalled=3 / target_recall_ok=true / index_gap_detected=false`, the 3 real
  files present + breadcrumb_tracer.py clean (no trailing " Determine..."), `breadcrumb/handoff` in
  `work_focus_targets_dropped_low_confidence` and NOT in required, Fix C trailing-punctuation trim, the
  bulleted-Read-first Option-3 regression, and the explicit/M2M/bullet broader-tier proof. WFTD-001..014
  regression preserved.
- Version 0.3.44 -> 0.3.45 (package.json + EXTENSION_VERSION + README + contract-test version assertions).
- Gate: VERIFIED_READY draft PR only (do NOT self-merge; merge is harness/012-gated, VSIX build is a 012
  host step).

## 2026-07-07 - REDDOG_WORK_FOCUS_TARGET_DERIVATION_PHASE1 (free-form target derivation, 0.3.44)

- Problem (OBSERVED, real run at 0.3.41/0.3.43): a multi-lane-orchestration audit named
  `docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md`, `docs/0102_session_briefings/work_ledger.schema.json`,
  and `holo_index/adaptive_learning/breadcrumb_tracer.py` in prose bullets, but NOT under the exact
  `Required direct-read targets:` header. Result: `required_targets_total: 0`,
  `direct_read_fetch_attempted: false`, `direct_read_fallback_used: false` -- the whole direct-read stack
  stayed dormant even though real paths were named. RedDog was retrieval-blind to free-form targets.
- Fix (extension.js only; NO Python change): new `deriveWorkFocusTargets(taskText)` derives required
  direct-read targets from read-intent shapes -- `Read first:` / `READ BEFORE EDITING` blocks, WSP_99 M2M
  `READ:` arrays, M2M `CTX.FILES` / `CTX: FILES:` arrays, markdown bullet path lists, and inline/backticked
  repo paths in prose. New `collectRequiredTargets(taskText)` MERGES the explicit-header list (kept FIRST,
  byte-identical for the header-only shape) with derived targets, de-duped case-insensitively in first-seen
  order. `evaluateTargetRecall` and `buildBoundedRepoContext` consume the MERGED list, so a derived path
  makes `required_targets_total > 0`, fires the SAME governed direct-read fetch, and is packed/proven like
  a header target -- regardless of HoloIndex semantic recall.
- False-positive guards: (A) inline/prose extraction uses a bounded, anchored, ReDoS-safe path-TOKEN regex
  (`WORK_FOCUS_PATH_TOKEN_RE`; a slash-less token requires a LOWERCASE file extension so acronyms / M2M keys
  like `CTX.FILES` are not captured and surrounding prose words are never swept in) -- heeds the CodeQL
  js/polynomial-redos lesson at `normalizeTargetPath`; (B) command/validation fences
  (```powershell / ```bash with `git diff --check`, `node --check`, `python holo_index.py ...`, `rg ...`)
  and scope-out / `Do NOT touch` / `OUT OF SCOPE` sections are EXCLUDED; ambiguous read-intent prefers
  precision (no derivation).
- CI hardening (folded into this PR before promotion): CodeQL flagged 2 new HIGH `js/polynomial-redos`
  alerts on the bullet-list marker regex (marker + `\s+` + greedy capture, where the leading whitespace
  class overlapped the trailing capture) -- the same rule/family as pre-existing alert #174. Replaced ALL
  THREE instances (the pre-existing one in `parseRequiredTargetPaths` plus the two new derivation instances)
  with a single linear O(n) `stripListMarker(line)` helper (no backtracking; the only regex is a
  quantifier-free single-character `\s` test), mirroring the `normalizeTargetPath` linear-trim remediation.
  Behavior is byte-identical (`{ isList, itemText }` matches the old `listMatch ? listMatch[1] : stripped`
  idiom). `stripListMarker` exported; WFTD-014 adds parity + regex-absence + pathological-input timing
  guards. Version stays 0.3.44 (unreleased; fix folded in, no VSIX churn).
- Governance unchanged: denied paths (`.env`, traversal, secret-like) are EMITTED honestly by the deriver
  and REJECTED by the unchanged Python direct-read gate (`bundle_json.py`); denylist / traversal protection /
  byte budgets / redaction / audit_context / required-target packing are all untouched. No HoloIndex
  ranking/index change; no runtime reindex; no live-writer / orchestration-brain change.
- Telemetry: `work_focus_targets_derived` (bool) + `work_focus_target_derivation_sources` (array from
  `{required_block, read_first, m2m_read, ctx_files, markdown_bullet, inline_path, backtick_path, symbol}`),
  threaded through `evaluateTargetRecall` -> `holoIndexMetaFromBundle` -> `extractHoloIndexScorecard` ->
  `formatHoloIndexScorecardLines` (Run Trace). Both labeled OBSERVED (WSP_97).
- Tests: WFTD-001..WFTD-013 in `tests/verify_extension_contract.js` (+ fixtures in `tests/fixtures.js`),
  covering all 8 source shapes, both guards, the denied-path honesty case, the HoloIndex-miss-still-fetches
  case, the no-path backward-compat case, and a real end-to-end regression (`holoIndexOutput` on the
  multi-lane prompt: `required_targets_total >= 3`, `direct_read_fetch_attempted: true`, all three files
  fetched/rejected/honestly-missing).
- Version 0.3.43 -> 0.3.44 (package.json + EXTENSION_VERSION + README + contract-test version assertions).
- Gate: VERIFIED_READY draft PR only (do NOT self-merge; merge is harness/012-gated, VSIX build is a 012
  host step). Judgment-lane retrieval-blindness fix (parallel to the judgment-lane slices #933-#935).

## 2026-07-05 - REDDOG_SYMBOL_AWARE_EXCERPT_DEPTH_PHASE1 (symbol line windows reach the model, 0.3.43)

- A required direct-read target may now be `path#symbol`. The Python bundle layer
  (holo_index/cli/commands/bundle_json.py) returns a bounded LINE WINDOW around the symbol's
  DEFINITION instead of the head-clip of the first 12KB, so a symbol defined deep in a large file
  (e.g. `build_foundup` / `extract_foundup`) actually reaches the model.
- Extension wiring: the full `path#symbol` token is forwarded to `--bundle-must-include` verbatim
  (a pathless `symbol:` prefix is still excluded, unchanged). `stripSymbolSuffix(target)` normalizes
  `path#symbol` -> the bare path for all recall/resolve comparisons (`requiredTargetMatchesLocation`,
  the resolver, the required-target context-proof denominator), because the fetched hit's location is
  the bare path. `extractTargetTokensFromLine` shape-checks the PATH portion so a `path#symbol` target
  parses. `stripSymbolSuffix` is bounded/anchored (ReDoS-safe).
- Extension contract test extended: stripSymbolSuffix behavior, recall-by-bare-path for a `path#symbol`
  target, forwarded `--bundle-must-include` token, end-to-end `parseRequiredTargetPaths`, and the
  unchanged `symbol:`-prefix exclusion.
- Gate: VERIFIED_READY draft PR only (do NOT self-merge). Judgment-lane slice 3 (after #933/#934).

## 2026-07-05 - REDDOG_REPAIR_PRESERVES_EVIDENCE_PHASE1 (repair preserves Determine evidence, 0.3.42)

- The schema-repair pass now PRESERVES a primary Determine answer block. A repair exists to ADD missing
  sections; it must not silently drop / reorder / weaken (OBSERVED -> vague NEEDS_VERIFICATION) / strip
  file:line evidence / fabricate anchors in the evidence-backed Determine answers.
- Wiring (repair path, callFusion review flow):
  - PRE-REPAIR: `runRepairGuard(context, 'protect', ...)` extracts the protected block and prepends it to
    the `repair_minimal` bounded context, so the repair model reproduces the answers UNCHANGED.
  - POST-MERGE: after `mergeRepairedOutput`, `runRepairGuard(context, 'guard', ...)` revalidates the merged
    output. On `keep_original` the merge is DISCARDED and the primary + its validation failure is kept
    (`repair_failure_reason: repair_dropped_determine_evidence`). Existing schema-completeness acceptance is
    unchanged for the non-keep-original branch.
  - Fail-closed: if the guard bridge is unavailable, a primary that carried a Determine block still keeps
    the original (`repair_evidence_reasons: ['guard_bridge_unavailable']`).
- REUSES the Python Determine contract's `assert_repair_preserves` (no preservation rules reimplemented in
  JS) via `scripts/reddog_repair_guard_once.py` (synchronous `cp.execFileSync`, same pattern as HoloIndex/git).
  New helpers `runRepairGuard` / `hasDetermineAnswersBlock` exported; telemetry `repair_evidence_protected` /
  `repair_evidence_preserved` / `repair_evidence_reasons` added to output_validation.
- Guard hardened via a 5-round 8-lens adversarial CoR (R5 all SAFE, 0 findings). Extension contract test
  extended: source wiring + ATX/SETEXT block presence + real end-to-end guard bridge (protect/faithful/strip/drop).
- Gate: VERIFIED_READY draft PR only (do NOT self-merge). Judgment-lane slice 2 (after #933 Determine contract).

## 2026-07-03 - REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1 (all-section + legacy-path closure, 0.3.41)

- Closes the LAST two residual required-target-telemetry forgery vectors so forgery_inert=true holds on
  ALL paths/sections, not only the authoritative (packProtected=true) path that 0.3.39/0.3.40 hardened.
- VECTOR A (incomplete lower-section neutralization): `neutralizeRequiredTargetMarker` was applied to the
  HoloIndex recall blob, active-editor content, and git status/stat/diff bodies, but THREE (really four)
  raw file-body lower sections still pushed UN-neutralized content that could contain a literal
  "### Required direct-read target: <path>" marker minted from file CONTENT:
    - target-recall section (`buildTargetRecallContentSection` -> `#### <rel>` fenced raw snippets),
      neutralized at push (extension.js ~2636).
    - WSP_97 excerpt (`buildWsp97ProtocolExcerpt` -> raw protocol body), neutralized at push (~2648).
    - Skillz/Wardrobe/Rolodex discovery (`skillzWardrobeRolodexContext` -> `readBoundedRepoFile` raw
      snippets), neutralized at push (~2661).
    - plain direct-read section (`buildDirectReadContentSection` -> raw fetched `hit.content`), reachable
      only when packProtected=false (the exact Vector B window); neutralized at push (~2617).
  Now EVERY `lowerSections.push(...)` routes its body through `neutralizeRequiredTargetMarker`. No
  file-body section can emit the literal marker prefix into the Python isolation splitter.
- VECTOR B (legacy None path): when `audit_context=true` but `packProtected=false` (direct-read code_hits
  present -> audit_context true, but `direct_read_fallback_used` false -> `authoritativePacked=[]`), the
  JS emitted an EMPTY authoritative list. `scripts/advisory_model_once.py` collapsed the empty list to
  `None`, and `fusion_redaction_gate._isolate_required_targets(None)` is the LEGACY path where
  `authoritative_set` is None -> EVERY marker section (including content-minted phantoms) is
  checked/counted and could mint content-controlled `blocked_paths`. Fix: under `audit_context_requested`
  the empty/absent list is NOT collapsed to None -- an EXPLICIT EMPTY tuple `()` is forwarded, so the gate
  builds an EMPTY `authoritative_set`: every marker's `norm_path not in authoritative_set` is true ->
  every marker folds back as ordinary content (checked==0, passed==0, no forged blocked_paths), while any
  real secret/token in a folded body STILL fails the whole payload closed via the audit-mode whole-context
  gate. Non-audit legacy behavior stays byte-identical (absent/empty -> None). The direct
  `_isolate_required_targets(..., None)` legacy contract is unchanged (no frg.py guard added), so
  `test_mfh_authoritative_none_is_byte_identical_legacy` still holds.
- Completeness / forward-safety: MFH-J-008 ENUMERATES every `lowerSections.push` site in the extension
  source and asserts 100% route through `neutralizeRequiredTargetMarker`; a FUTURE new raw-body section
  pushed without neutralization fails the contract runner rather than silently reopening the forgery.
  MFH-J-007b pins the four new file-body call sites explicitly. Python: `test_mfh_vectorb_*` (empty-set
  folds every marker, zero counts, still fails closed on a token; differs from legacy None) +
  `test_vectorb_*` (bridge forwards `()` under audit_mode, `None` on the non-audit legacy path).
- No weakening: identification/counting only. No ACTION_BLOCK detector relaxed, `AUDIT_STRUCTURAL_CATEGORIES`
  unchanged, #917 one-blocked-sibling-survives content-safety and #914 budget preserved. Authoritative path
  (dedup / neutralization / #917 / #914) still inert. Version bump 0.3.40 -> 0.3.41.

## 2026-07-03 - REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1 (per-path dedup completion, 0.3.40)

- Closes the residual duplicate-authoritative-marker bypass that survived the 0.3.39 authoritative fix.
  #918 made the JS `in_model_context` proof unforgeable, but the Python isolation telemetry
  (`required_targets_redaction_checked/passed/blocked/blocked_paths/reasons`) was still forgeable:
  `neutralizeRequiredTargetMarker` was applied ONLY to the protected required-target EXCERPT bodies, so
  the LOWER sections (git diff, HoloIndex recall JSON blob, active editor) merged UN-neutralized into the
  same `gate_context` that Python's `_isolate_required_targets` splits. In `wsp_holo_git*` modes a
  MODIFIED required file whose OWN body contains the literal line
  "### Required direct-read target: <its-own-authoritative-path>" rendered that marker un-neutralized in
  the git diff; Python split it as a SECOND section whose path normalized to the SAME authoritative path,
  PASSED the authoritative gate, and was counted AGAIN (no per-path dedup) -> checked/passed EXCEEDED the
  authoritative count (falsifying the docstring invariant). If that diff body also carried a hard-block
  token, the clean authoritative path was appended to blocked_paths with a forged reason while its REAL
  protected section was clean.
- Fix (robust single point = per-path dedup; identification only, no policy change):
  - PRIMARY (Python per-path dedup) in `_isolate_required_targets` (fusion_redaction_gate.py ~:499-543):
    a `consumed_paths` set tracks normalized authoritative paths already consumed. An authoritative path
    is checked/passed/blocked AT MOST ONCE (the FIRST marker section for that path -- the real packed
    protected section, packed BEFORE any lower section). Any SUBSEQUENT marker whose normalized path is
    already-consumed folds back as ORDINARY content (exactly like a non-authoritative phantom). This makes
    checked/passed/blocked/missing <= authoritative count HOLD FOR REAL, even with duplicate authoritative
    markers minted by lower sections; blocked_paths stays a subset of authoritative paths.
  - Defense-in-depth (JS lower-section neutralization) in extension.js: `neutralizeRequiredTargetMarker`
    now also wraps the git-diff (`### git status/--stat/git diff -- .` bodies ~:2643-2649), HoloIndex
    recall JSON blob (~:2583), and active-editor content (~:2639) before assembly, so a literal marker in
    those sections cannot reach the Python splitter as a real marker in the first place.
  - JS threading contract assertion (MFH-J-006 in verify_extension_contract.js): pins the bridge payload
    line that sets `required_target_paths` from `bridgeMeta.required_targets_authoritative_paths` so a
    future edit cannot silently drop it (which would make Python receive None -> the forgeable #917
    fallback at runtime while Python-direct tests still pass). MFH-J-007 pins the three lower-section
    neutralization call sites.
- No weakening: identification-only. No ACTION_BLOCK detector relaxed; AUDIT_STRUCTURAL_CATEGORIES
  untouched; the #917 one-blocked-sibling-survives content-safety fix and #914 budget math preserved.
- Tests: 3 new Python dedup regression tests in test_fusion_redaction_gate.py
  (duplicate-authoritative-marker-in-git-diff-not-recounted; duplicate-with-hard-block-token-does-not-
  forge-blocked-path; counts-never-exceed-authoritative-with-many-duplicates) -> 98/98 gate tests pass.
  Proven non-vacuous: the 3 dedup tests FAIL when the per-path dedup condition is disabled (checked=6
  instead of 2) and PASS with it. Contract test adds MFH-J-006 (threading) + MFH-J-007 (lower-section
  neutralization). Full JS contract suite exit 0 on 0.3.40; golden 6-file still in_model_context=6,
  redaction_blocked=0.
- Version: LIVE-surface bump 0.3.39 -> 0.3.40.
- Stacked on the 0.3.39 authoritative fix (same #918 slice) and REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 (#917).
- WSP: WSP_00, WSP_50, WSP_97, WSP_22.

## 2026-07-03 - REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1 (authoritative unforgeable required-target telemetry, 0.3.39)

- Root cause (marker-reparse forgery): the required-target telemetry was derived by REPARSING marker
  strings out of merged text, so file CONTENT could forge it. JS `computeRequiredTargetContextProof`
  (extension.js) counted marker substrings via `text.indexOf(REQUIRED_TARGET_MARKER_PREFIX + target)`
  over the FINAL text, so a phantom marker inside a target BODY flipped a never-fetched target from
  missing -> in_model_context. Python `_isolate_required_targets` (fusion_redaction_gate.py) split the
  context on the marker and derived checked/passed/blocked + blocked_paths from marker-delimited
  SECTIONS, so a body containing "### Required direct-read target: <path>" minted a PHANTOM section ->
  inflated checked/passed and forged blocked_paths. The marker is not exotic (RedDog's own
  docs/ModLog/INTERFACE/verify_extension_contract.js contain it), so this fired on realistic
  self-referential audits, not just attacks.
- Fix (structured-records; identification only, no policy change):
  - JS proof is now AUTHORITATIVE: `computeRequiredTargetContextProof` iterates the packer's STRUCTURED
    record (`protectedInfo.included_paths` -- the paths actually packed), NOT markers scanned out of
    text. A requested target counts as in_model_context only if it is in the authoritative packed set
    AND its OWN fenced section survived the final cut (`requiredTargetSectionSurvived`). A phantom marker
    for a path not in the authoritative set is never counted; a requested-but-never-packed path is
    reported missing (never flipped present by a stray marker).
  - JS pack-time defense-in-depth: `neutralizeRequiredTargetMarker` inserts a zero-width WORD JOINER
    (U+2060, written in source as the ASCII escape backslash-u-2060) after the "### " lead of any literal
    marker occurring INSIDE an excerpt BODY, so a target's content can never mint a sibling marker (nor
    a phantom section for the Python splitter). Visually inert to reader/model; breaks the byte sequence.
  - Python authoritative-list intersection: the JS packer threads its authoritative `included_paths`
    through the bridge payload (`required_target_paths`) -> `advisory_model_once.py` ->
    `evaluate_redaction_gate(..., required_target_paths=...)` -> `_isolate_required_targets(context,
    authoritative_paths)`. A marker-delimited section is treated as a required-target section only when
    its path is IN the authoritative list; phantom markers (path not in list) are folded back verbatim
    as ORDINARY content (still redacted by the whole-context gate, never counted as a section). So
    checked/passed/blocked/missing can never exceed the authoritative count and blocked_paths is a
    subset of authoritative paths. When no list is threaded (None) behavior is byte-identical to #917.
- No weakening: identification-only. No ACTION_BLOCK detector relaxed; AUDIT_STRUCTURAL_CATEGORIES
  untouched; audit-mode value-vs-structure behavior unchanged; the #917 content-safety fix (one blocked
  target omitted while siblings survive) is preserved. This slice only changes how telemetry / sections
  are IDENTIFIED, never what is blocked.
- Tests: 6 new Python tests in test_fusion_redaction_gate.py (embedded-marker-not-a-section;
  malicious-fixture-no-extra-sections; blocked_paths-subset-of-authoritative; the ADVERSARIAL
  full-fixture no-inflation/no-phantom; authoritative-None-byte-identical-legacy;
  authoritative-one-blocked-sibling-survives) -> 95/95 gate tests pass. Contract test adds
  MFH-J-001..005 (authoritative structured proof; the adversarial phantom-marker-in-final-text proof;
  body neutralization; packed-section marker-count == included_paths; post-cut survival honesty). Full
  JS contract suite exit 0 on 0.3.39.
- Version: LIVE-surface bump 0.3.38 -> 0.3.39.
- Stacked on REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 (#917).
- HoloIndex: the new hardening functions do not surface in semantic recall (index gap) ->
  HOLOINDEX_REDDOG_MARKER_FORGERY_INDEX_GAP_PHASE1 (SPECIFIED_NOT_IMPLEMENTED; static anchors here + in
  INTERFACE only; no ranking/reindex code changed). HoloIndex discoverability is NOT an acceptance gate.
- WSP: WSP_00, WSP_50, WSP_97, WSP_22.

## 2026-07-03 - REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1 (per-target redaction isolation for required-target evidence, 0.3.38)

- Root cause: the packing path (#914) assembles all required-target excerpts into ONE merged context,
  then the WHOLE context is redaction-gated once (advisory_model_once.py evaluate_redaction_gate;
  fusion_alias_live.py line ~199). The gate had NO per-target isolation: if ONE required excerpt
  contained a hard-block token (private_reasoning / private_key_residual), the ENTIRE merged payload
  blocked -> redacted_context=None -> ALL required targets dropped, even in audit_mode. The 6 golden
  files are clean (0 triggers), but this was a known sharp edge on the evidence-ingress path.
- Fix (granularity only, in the Python redaction layer fusion_redaction_gate.py): when audit_mode AND
  the context carries the stable marker `### Required direct-read target: <path>`, the gate now splits
  the context into preamble + per-target sections, evaluates each section's block status INDEPENDENTLY,
  OMITS only the sections that trigger a non-audit-structural block (marker + a redaction notice kept,
  body gone -> secrets never reach the model), preserves all other sections verbatim, reassembles, and
  runs the UNCHANGED whole-context audit-mode gate over the survivors. One blocked required target no
  longer drops the clean ones; the overall gate passes (redacted_context non-None).
- No weakening: this changes ONLY the GRANULARITY of the block (per-target instead of whole-payload),
  never WHAT is blocked. No ACTION_BLOCK detector relaxed; AUDIT_STRUCTURAL_CATEGORIES untouched;
  audit-mode value-vs-structure behavior unchanged; private_reasoning / private_key_residual still
  always block their section. The in-context notice sanitizes the block-category name (underscore ->
  dot) so it can never re-trigger a detector; the real category name lives only in counts-only
  telemetry. Fail-closed: no markers or an ambiguous split -> the unchanged whole-context gate runs; a
  block outside a target section still blocks the whole payload.
- Telemetry (5 new counts-only fields; surfaced in the Run Trace scorecard): required_targets_redaction_checked,
  required_targets_redaction_passed, required_targets_redaction_blocked, required_targets_redaction_blocked_paths[],
  required_targets_redaction_blocked_reasons[]. Emitted by the Python gate report -> advisory_model_once.py
  (top-level result + review_packet) -> extension.js holoScorecard -> formatHoloIndexScorecardLines. Default
  zero/empty on the non-audit / no-marker path (backward compatible).
- Tests: 10 new per-target isolation tests in test_fusion_redaction_gate.py (adversarial one-blocked-others-survive;
  secret target withheld; loose secret redacted-in-place; all-clean 6-file mirror; backward-compat no-markers;
  non-audit path unchanged; block-outside-section still blocks; notice-does-not-reintroduce-trigger;
  no-detector-relaxed; zero-network). 89/89 pass. Contract test adds RPTI-001..004 (scorecard mapping +
  render + defaults). Full JS contract suite exit 0 on 0.3.38.
- Version: LIVE-surface bump 0.3.37 -> 0.3.38.
- Stacked on REDDOG_RUN_TRACE_BUILD_VERSION_FIELD_PHASE1 (#916).
- WSP: WSP_00, WSP_50, WSP_97, WSP_22.

## 2026-07-03 - REDDOG_RUN_TRACE_BUILD_VERSION_FIELD_PHASE1 (emit extension_version in Run Trace scorecard, 0.3.37)

- Incident: a golden rerun was mistakenly run on a STALE 0.3.34 build, but the model OUTPUT header claimed
  "Build: 0.3.36" because it parroted a "Version expected:" line from the prompt. The Run Trace scorecard
  did NOT emit the actual installed build version as a telemetry field, so staleness could not be detected
  from the trace itself (only from the UI footer). The model text masked the real build.
- Fix: `buildRunTraceSection(...)` now emits `- extension_version: ` + `EXTENSION_VERSION` (the real
  installed-build constant) near the TOP of the `## Run Trace` block, immediately after the header and
  before the role/tier fields. It reads the constant, NOT any value from the prompt, packet, or model
  output, so build staleness is machine-checkable from telemetry and can never be masked by model text.
- Purely additive telemetry. No packing, redaction, fetch, or continuation logic changed. No new
  file-read. No execution authority.
- Tests (verify_extension_contract.js): (a) `buildRunTraceSection(...)` output contains
  `- extension_version: ` followed by the current EXTENSION_VERSION; (b) that value equals the
  package.json version (they must agree - the trace proves the build); (c) the source line reads the
  EXTENSION_VERSION constant, not prompt/packet/model text. Full JS contract suite exit 0 on 0.3.37.
- 012 note: the Run Trace now carries `extension_version` = the real installed build; use it (not model
  text) as the staleness gate.
- Version: LIVE-surface bump 0.3.36 -> 0.3.37.
- Stacked on REDDOG_CONTINUATION_DEFAULT_OFF_PHASE1 (#915).
- WSP: WSP_00, WSP_50, WSP_97, WSP_22.

## 2026-07-03 - REDDOG_CONTINUATION_DEFAULT_OFF_PHASE1 (default Use-last-packet checkbox OFF, opt-in continuation, 0.3.36)

- Change: the webview "Use last RedDog packet" checkbox now defaults UNCHECKED. Continuation is opt-IN
  instead of opt-out. The feature stays manually available (012 can check the box to append the prior
  WSP_97-safe summary). One-line HTML edit: removed the `checked` attribute from
  `<input id="useLastPacket" type="checkbox">`.
- No backend logic change. The #911 fail-closed backend (`const continuationEnabled = message.useLastPacket
  === true`) already treats missing/false as OFF, so an unchecked default yields
  `continuation_enabled=false` AND `continuation_appended=false` with no new code. The frontend still sends
  `useLastPacket: continuationOn` where `continuationOn = !!(useLastPacket && useLastPacket.checked)`.
- The "Continuation: disabled for this run." status line (from #911) now renders by default (unchecked run),
  which is the intended opt-in signal.
- No packing change (#914), no direct-read change, no redaction change, no new telemetry (continuation
  telemetry already exists from #911).
- Tests (verify_extension_contract.js): (a) the useLastPacket checkbox HTML default has NO `checked`
  attribute; (b) default submit (useLastPacket false/absent) yields continuation_enabled=false AND
  continuation_appended=false and Copy MD does NOT append the summary even when a prior packet exists;
  (c) manual check (useLastPacket=true) still appends when a summary is present (feature not removed). Full
  JS contract suite exit 0 on 0.3.36.
- Golden rerun note: default-off is now the shipped behavior; the golden rerun no longer needs a manual
  uncheck of the box.
- Version: LIVE-surface bump 0.3.35 -> 0.3.36.
- Stacked on REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_PHASE1 (#914).
- WSP: WSP_00, WSP_50, WSP_97, WSP_22.

## 2026-07-03 - REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_PHASE1 (protect required-target excerpts in final model context, 0.3.35)

- Problem (golden 6-file FoundUps-creation audit on 0.3.34): senses stack PASS
  (direct_read_fallback_used=true, target_recall_ok=true, 6/6 recalled) and audit egress PASS
  (audit_context requested+applied, redaction passed), but the model pass FAILED: the model claimed
  fetched files (foundup_job_contract.py, hermes_foundup_job_executor.py,
  reddog_governed_work_order_dryrun.py, reddog_wre_execution_valve.py) were "not in bounded context".
- Root cause = PACKING, not fetch/recall. `buildBoundedRepoContext()` joined all sections then applied a
  single `.slice(0, 42000)` tail cut. Section order put the HoloIndex raw JSON blob (18KB), the git diff
  (24KB), and the self-file `extension.js` target-recall snippet (24KB) ahead of / around the fetched
  direct-read required-target content, so the required-target excerpts were guillotined by the tail cut.
  direct_read_bytes=72000 but final bounded context = 42000 chars; the fetch/recall telemetry read 6/6
  while the model saw far fewer.
- Fix: when a prompt carries an explicit "Required direct-read targets" list AND the governed fetch
  succeeded (`direct_read_fallback_used`), pack a PROTECTED required-target block FIRST (right after the
  WSP contract head), each target rendered with a STABLE marker `### Required direct-read target: <path>`.
  Per-target minimum-first budget (min 1800 / max 6000 chars, protected total 30000) so a large early file
  cannot starve later required files. Lower-priority sections (HoloIndex JSON blob, git diff, Skillz,
  self-file snippet) yield to the 42K cut instead of the required-target excerpts; the self-file
  `extension.js` target-recall snippet is DEMOTED/OMITTED in explicit-target audit mode.
- ADDENDUM B (model-context proof): new telemetry `required_targets_in_model_context`,
  `required_targets_context_total`, `required_targets_context_chars`, `required_targets_context_missing`,
  `required_targets_context_truncated` are computed by scanning the FINAL post-cut context string for the
  stable markers -- NOT from fetch/bundle telemetry. Run Trace renders BOTH `required_targets_recalled`
  (fetched/available layer) and `required_targets_in_model_context` (actually model-visible layer); the two
  layers are never conflated.
- Backward compat: prompts WITHOUT a required-target list pack byte-identically (head+lower join+same 42K
  cut); model-context proof fields stay 'unknown'. No new file-read paths (protected block reuses the
  already-fetched, already-redaction-gated direct-read hit content). No execution authority, no redaction
  policy change, no change to the Python fetch/allowlist or the #913 audit_mode wire.
- Tests: RTP-001..RTP-005 + ADDENDUM B assertions in `verify_extension_contract.js`
  (`GOLDEN_6FILE_FOUNDUP_PROMPT` live packing proof: all 6 markers survive the 42K cut;
  in_model_context == total when recall satisfied; context_missing == []; legacy prompt preserves ordering
  and stays 'unknown'; large required file does not starve siblings; a marker cut post-slice counts as
  missing). Full JS contract suite exit 0. Python `test_reddog_extension_bundle_recall.py`: 15 pass, 2 pre-
  existing discoverability failures (extension.js not in top HoloIndex hits) that also fail on the base SHA
  -- index-staleness, not a regression of this slice.
- HoloIndex discoverability (ADDENDUM A, pre-edit): queries "RedDog required target context packing",
  "buildBoundedRepoContext 42000 slice", "buildDirectReadContentSection direct-read target content",
  "buildTargetRecallContentSection extension.js" did NOT surface `extension.js` or
  `verify_extension_contract.js` in top code hits (INDEX_GAP -- OBSERVED). Static anchors added to
  INTERFACE.md / ROADMAP.md. Follow-up indexing slice:
  `HOLOINDEX_REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_INDEX_GAP_PHASE1` (SPECIFIED_NOT_IMPLEMENTED -- no
  ranking/reindex code changed here). Discoverability is NOT the acceptance bar; acceptance is final-context
  marker proof + golden model answer quality.
- Version: LIVE-surface bump 0.3.34 -> 0.3.35.
- WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-07-02 - REDDOG_AUDIT_CONTEXT_BRIDGE_WIRE_PHASE1 (audit_context bridge wire, 0.3.34)

- Problem (golden rerun on 0.3.33): **senses stack PASS** (7/7 recall, direct_read_fallback_used=true,
  continuation off) but **model pass FAIL** - `redaction gate status: BLOCKED_LOCALLY`,
  `made_network_call: false`. Root cause: slice-3 `audit_mode` exists in `fusion_redaction_gate.py` and
  `buildDirectReadContentSection()` surfaces `audit_context: true`, but the live path
  `extension.js` -> `scripts/advisory_model_once.py` never passed the flag into
  `evaluate_redaction_gate()`.
- Fix: `buildBoundedRepoContext()` preserves `audit_context` from `holo.direct_read_section`;
  `callFusion()` payload carries `audit_context: true` when `promptConstruction.audit_context_requested`;
  `advisory_model_once.py` passes `audit_mode=audit_context_requested` into the entry gate only.
  Run Trace telemetry: `audit_context_requested`, `audit_context_applied`.
- Default path byte-identical: no direct-read governance context => `audit_context=false` => strict gate unchanged.
- Tests: ACB-001..005 in `verify_extension_contract.js`; 3 bridge tests in
  `scripts/tests/test_advisory_model_once_hardening.py`.
- HoloIndex discoverability (ADDENDUM A, pre-edit): queries for bridge wire / audit_mode did NOT surface
  `extension.js`, `advisory_model_once.py`, or `fusion_redaction_gate.py` in top code hits
  (INDEX_GAP - OBSERVED). Static anchors added to INTERFACE.md / ROADMAP.md. Follow-up indexing slice:
  `HOLOINDEX_REDDOG_AUDIT_CONTEXT_BRIDGE_WIRE_INDEX_GAP_PHASE1` (SPECIFIED_NOT_IMPLEMENTED - no ranking
  code changed in this slice).
- Version: mechanical LIVE-surface bump 0.3.33 -> 0.3.34.
- WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-07-02 - REDDOG_DIRECT_READ_FALLBACK_TRIGGER_DIAGNOSTIC_PHASE1 (enriched-fetch buffer + fetch-error telemetry, 0.3.33)

- Problem (golden rerun on landed 0.3.31): slice-1 detector WORKED (index_gap_detected=true,
  required_targets_total=8, recalled=0) but slice-2 enriched fetch NEVER surfaced in the scorecard
  (direct_read_fallback_used=false, 0 paths, 0 rejected). CONFIRMED ROOT CAUSE = maxBuffer overflow,
  swallowed silently. The caller passes maxChars=18000; the enriched `execFileSync` set
  `maxBuffer: Math.max(maxChars*8, 131072)` = 144000 bytes (~141KB). The enriched bundle for the 8
  FoundUps targets is ~184.5KB (proxy-measured 184529 bytes = semantic bundle + governed fetched
  content). 184.5KB > 141KB => the subprocess throws ENOBUFS+SIGTERM, and the EMPTY `catch (fetchErr)`
  swallowed it, keeping the pre-fetch bundle/meta and reporting fallback_used=false with no cause.
- Fix 1 (buffer + timeout): the enriched call now sizes `maxBuffer = Math.max(maxChars*16, 8*1024*1024)`
  (8MB floor, wide headroom over the ~185KB observed size and the ~96KB Python total fetch budget) and
  `timeout = 45000` (up from 30s; the enriched call re-runs HoloIndex + reads N target files under load).
- Fix 2 (fetch-error telemetry): the previously-empty catch now classifies the caught error via
  `classifyDirectReadFetchError` and surfaces it. Attempt telemetry is set BEFORE the enriched call so a
  failure can never again read as "never triggered". New meta/scorecard/Run-Trace fields:
  `direct_read_fetch_attempted` (bool), `direct_read_fetch_error` (timeout | max_buffer | process_error |
  unknown | null), `direct_read_fetch_arg_count` (fetchable target count), `direct_read_fetch_timeout_ms`.
- Secondary bug found + fixed: a maxBuffer overflow raises BOTH `code='ENOBUFS'` AND `signal='SIGTERM'`;
  the classifier now checks the definitive ENOBUFS/maxBuffer signal BEFORE the SIGTERM timeout branch so
  an overflow is not misclassified as a timeout (a real timeout is ETIMEDOUT+SIGTERM with no ENOBUFS).
- Trigger hardening: the `index_gap_detected === true` condition is coercion-hardened to also accept the
  string 'true', so no upstream serialization can silently defeat the strict-equality trigger.
- Honest-gap invariant preserved: the golden 8th target is a non-fetchable `symbol:`; the fallback resolves
  all 7 fetchable paths (recalled=7) and leaves exactly the symbol missing -- it never fabricates symbol
  resolution. arg_count (7) therefore equals the fetchable target count, not the total (8).
- Version: mechanical LIVE-surface bump 0.3.32 -> 0.3.33 (`package.json`, `EXTENSION_VERSION`, README header,
  every LIVE 0.3.32 assertion in `tests/verify_extension_contract.js` incl. target-snippet content checks).
  Historical annotations untouched.
- Tests: DRT-001..DRT-008 in `tests/verify_extension_contract.js` - classifier ordering (ENOBUFS+SIGTERM =>
  max_buffer); default + error telemetry through meta/scorecard/formatter; regression guard on the >=8MB
  buffer floor and the removed 144KB constant; END-TO-END trigger via `holoIndexOutput` on the golden prompt
  proving direct_read_fetch_attempted=true + direct_read_fallback_used=true + 7 fetchable paths under the
  raised buffer; a real 4KB-buffer overflow simulation classifying as max_buffer; continuation-independence
  (fetch fires identically with/without a trailing continuation block); golden 8-target contract (total 8,
  arg pairs 7). Full node suite PASS on 0.3.33. Python `test_reddog_extension_bundle_recall.py`: 15 pass;
  the 2 `*_top_hits_/_recall` lexical-ranking failures are PRE-EXISTING on the #911 base (reproduced with all
  changes stashed) and out of scope for this slice.
- Stacked on REDDOG_CONTINUATION_TOGGLE_HARDENING_PHASE1 (#911). No continuation change here; the direct-read
  trigger reads only the required-target list + bundle recall and is independent of the continuation toggle.
- Out of scope (unchanged): no new file-write authority; no Python fetch/allowlist change (that is #910); no
  redaction policy change; no continuation change (that is #911).

WSP: WSP_22, WSP_50, WSP_97.

## 2026-07-02 - REDDOG_CONTINUATION_TOGGLE_HARDENING_PHASE1 (deterministic Use-last-packet toggle + telemetry, 0.3.32)

- Problem (012-observed): 012 unchecked "Use last RedDog packet" but Copy MD still emitted the
  "Continuation from last RedDog packet" block. Two independent defects in landed 0.3.31 `extension.js`:
  1. Backend default too permissive: `const useLastPacket = message.useLastPacket !== false` defaulted
     ON unless the field was exactly `false` (missing/stale field => ON).
  2. Copy MD continuation append was gated only on `ctx.continuationSummary` EXISTING, not on the toggle;
     and the summary is always built + stored, so even a correct `false` would not strip Copy MD.
- Fix (fail-closed): continuation is included THIS run ONLY when `message.useLastPacket === true`.
  Single boolean `continuationEnabled` drives both append sites. `continuationAppended = continuationEnabled
  && !!state.lastContinuationSummary`. Missing/stale toggle => OFF (a stale packet no longer contaminates
  redaction or acceptance scoring).
- Both append sites now gated on the toggle: the model-prompt append (`appendContinuationSummaryToWspPrompt`)
  and the Copy MD append (`buildContinuationSummaryCopySection`, now requires `ctx.continuationEnabled`).
  Building/storing the summary for the NEXT run is unchanged; only INCLUDING it this run is gated.
- Telemetry (Run Trace + Copy MD "## Continuation Telemetry"): `continuation_enabled`, `continuation_appended`,
  `continuation_source_run_id` (`run_xxx` when appended, else `none`). New helpers:
  `normalizeContinuationTelemetry`, `formatContinuationTelemetryLines`, `buildContinuationTelemetrySection`.
- UI: when disabled, webview shows status line "Continuation: disabled for this run." (frontend on send +
  backend on assemble).
- Version: mechanical LIVE-surface bump 0.3.31 -> 0.3.32 (`package.json`, `EXTENSION_VERSION`, README header,
  every LIVE 0.3.31 assertion in `tests/verify_extension_contract.js` incl. target-snippet content checks).
  Historical `vX.Y.Z` annotations untouched.
- Tests: ADDENDUM H in `tests/verify_extension_contract.js` - enabled+stored => appended (prompt + Copy MD)
  with `continuation_appended=true`; disabled+stored => NOT appended with `continuation_enabled=false`;
  missing toggle => fail-closed NOT appended; telemetry fields present in Run Trace + Copy MD. Full suite PASS.
- Out of scope (unchanged): no model/routing/redaction policy change; no direct-read fallback change; no
  cross-session memory; no mid-run steering.

WSP: WSP_22, WSP_50, WSP_97.

## 2026-07-02 - Version bump to 0.3.31 (REDDOG_AUDIT_MODE_REDACTION_PHASE1, slice 3/3)

- Mechanical build-label bump 0.3.30 -> 0.3.31 across LIVE version surfaces.
- Surfaces: `package.json`, `extension.js` (`EXTENSION_VERSION`), `README.md` header,
  `tests/verify_extension_contract.js` LIVE-version assertions.

WSP: WSP_22.

## 2026-07-01 - REDDOG_AUDIT_MODE_REDACTION_PHASE1 (slice 3/3, structure-preserving redaction)

- Files: `modules/communication/moltbot_bridge/src/fusion_redaction_gate.py` (audit_mode + structural
  categories + audit value redactors), `.../src/fusion_alias_live.py` (`audit_context` param),
  `extensions/foundups_advisory_workers/extension.js` (`buildDirectReadContentSection` surfaces
  `audit_context=true` when slice-2 direct-read fetched required governance targets).
- Goal: fix the FoundUps-creation over-sanitization -- `source_authority`, `merge_authorization`,
  `cabr_payout_authority`, `governance_instruction` matched on the bare identifier and BLOCKED the whole
  fetched payload, hiding the enum members / field names / gate ordering a governance audit must read.
- Value-vs-structure line: audit_mode PRESERVES identifiers (enum members `SourceAuthority.MONOREPO_POC`,
  field names, `CANONICAL_ACTIONS` incl. `build_foundup`/`extract_foundup`, valve gate names, WSP refs)
  and STILL REDACTS every secret VALUE / payout AMOUNT / authorization TOKEN / private_reasoning free-text.
- SAFETY: audit_mode never relaxes `private_reasoning`, `private_key_residual`, or any REDACT category.
  Fake `sk-...` key / OAuth token / payout amount / merge token remain `[REDACTED]` in audit mode.
- Trigger: OFF by default (backward compatible; non-audit path byte-identical). ON only for audit-context
  retrieval (direct-read of required targets). No detector/fetch/allowlist change; no execution/write/shell.
- Tests: 14 audit-mode unit tests in `modules/communication/moltbot_bridge/tests/test_fusion_redaction_gate.py`
  (79/79 pass); DRF-008 (structure readable in audit mode) + DRF-009 (secret STILL redacted) in
  `tests/verify_extension_contract.js`. INTERFACE truth-boundary rows 27-32 added (32/32 YES).

## 2026-07-02 - Version bump to 0.3.30 (REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1, slice 2/3)

- Mechanical build-label bump 0.3.29 -> 0.3.30 across LIVE version surfaces.
- Surfaces: `package.json`, `extension.js` (`EXTENSION_VERSION`), `README.md` header,
  `tests/verify_extension_contract.js` LIVE-version assertions.

WSP: WSP_22.

## 2026-07-02 - Version bump to 0.3.29 (REDDOG_TARGET_RECALL_PATH_AWARE_PHASE1, slice 1/3)

- Mechanical build-label bump 0.3.28 -> 0.3.29 across LIVE version surfaces so an installed
  host does not stay stale on this senses-spine slice. No runtime logic change.
- Surfaces: `package.json`, `extension.js` (`EXTENSION_VERSION`), `README.md` header,
  `tests/verify_extension_contract.js` LIVE-version assertions.

WSP: WSP_22.

## 2026-07-01 - REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1 (slice 2/3, governed fetch)

- Files: `holo_index/cli/commands/bundle_json.py` (fetch + hard allowlist), `holo_index/_cli_main.py`
  (`--bundle-must-include`), `extensions/foundups_advisory_workers/extension.js` (request paths + telemetry).
- Goal: when slice-1's detector reports `index_gap_detected=true` and the prompt named required targets absent
  from the bundle, FETCH those exact files' content so RedDog reasons on real source instead of HOLDing blind.
- Architecture: the FETCH lives in the PYTHON bundle layer (`_direct_read_fetch`); the extension only REQUESTS
  must-include paths via `--bundle-must-include` (no raw fs in extension.js, no shell-out, no model/router change).
  Fetched hits are spliced into `task_retrieval.code_hits`; slice-1's `evaluateTargetRecall` re-runs so
  `target_recall_ok` / `required_targets_recalled` reflect the now-present content.
- HARD security allowlist (WSP_50): repo-relative only; realpath must stay inside repo root (rejects absolute,
  `..` traversal, symlink-escape); hard-deny `.env*`, `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `*.p12`,
  `*.keystore`, `*secret*`/`*credential*`/`*token*`, `.git/` and credential dot-dirs; per-file byte cap (12KB)
  plus total fetch budget (96KB) spread across MANY targets (ranked by prompt order) so no single file starves
  the rest; every rejection recorded and never aborts the bundle.
- Telemetry: `direct_read_fallback_used`, `direct_read_paths`, `direct_read_rejected` (`{path, reason}`),
  `direct_read_bytes`, `direct_read_truncated` (`{path, bytes}`) added to the Run Trace scorecard.
- Boundary: NO redaction-category change and NO audit-mode change (slice 3). Fetched content passes through the
  EXISTING redaction gate unchanged (governance content may still be over-sanitized until slice 3 - expected).
  NO execution authority, NO write capability, NO shell-out added.
- Acceptance (slice-2 bar): on the FoundUps-creation required-target list against a bundle lacking them, the
  targets (WSP_109, openclaw_foundup_orchestrator, hermes_foundup_job_executor, foundup_job_contract,
  reddog_governed_work_order_dryrun, reddog_wre_execution_valve, source_authority) are fetched + present,
  `direct_read_fallback_used=true`, `target_recall_ok=true`.
- Tests: `holo_index/tests/test_reddog_extension_bundle_recall.py` (deny-gate unit, real-target fetch,
  recall-flip via node, traversal/absolute/secret-fixture/symlink-escape rejection, per-file cap + total budget
  spread, CLI end-to-end) + `tests/verify_extension_contract.js` (DRF-001..007 incl. slice-boundary proof that
  the existing redaction gate STILL blocks governance content, unchanged).
- Stacked on slice 1 (#906). WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.


## 2026-07-01 - REDDOG_TARGET_RECALL_PATH_AWARE_PHASE1 (slice 1/3, detector only)

- File: `extensions/foundups_advisory_workers/extension.js`
- Problem: on the FoundUps-creation audit run, the run trace reported `index_gap_detected: false` even though
  none of the 20+ required direct-read targets were retrieved. The only retrieved file was `extension.js`
  (RedDog itself), and that "content included" falsely satisfied the recall check
  (`content_included(any file) != required_targets_recalled`).
- Fix (detector only): `parseRequiredTargetPaths()` parses an explicit "Required direct-read targets" prompt
  list into repo-relative paths/globs; `evaluateTargetRecall()` now compares that list against content-bearing
  bundle locations, with a self-file guard (`isSelfFileLocation()`) so retrieving `extension.js` never counts.
- New truthful scorecard/telemetry fields: `required_targets_total`, `required_targets_recalled`,
  `required_targets_missing`, honest `target_recall_ok` and `index_gap_detected`
  (never `unknown` when a required list exists).
- Backward compatible: prompts with no required-target list preserve prior inferred-target behavior.
- No file-read added (slice 2), no redaction-category change (slice 3). Advisory boundary preserved.
- Tests: `holo_index/tests/test_reddog_extension_bundle_recall.py` (4 new: 0/N gap, self-file guard, all-present,
  backward-compat) + `tests/verify_extension_contract.js` (TRP-001..007 scorecard vocabulary).

WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_PHASE1 (extension pointers)

- Module: `modules/communication/moltbot_bridge/src/reddog_openclaw_adapter_dryrun.py`
- `plan_reddog_openclaw_adapter_dryrun()` -- propose FoundUpsJob / autonomous_task intake; no enqueue.
- Contract: `docs/audits/architecture/REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_CONTRACT_PHASE1.md`

WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_WRE_EXECUTION_VALVE_PHASE1 (extension pointers)

- Module: `modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py`
- `evaluate_reddog_execution_valve()` -- closed-by-default; pure evaluation only.
- Contract: `docs/audits/architecture/REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1.md`

WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1 (LANDED #901)

- Canonical: `docs/audits/architecture/REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md`
- Ruling: OpenClaw Supervisor / FoundUpsJob intake is canonical; AssignmentDispatcher is simulated scaffold only.
- No runtime adapter in this slice.

WSP: WSP_00, WSP_15, WSP_50, WSP_77, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_REVIEW_PACKET_MEMORY_AND_FOLLOWUP_PHASE1 (LANDED #899)

- ADD `buildSanitizedContinuationSummary()` - WSP_97-safe packet memory from last run (success or BLOCKED_LOCALLY).
- ADD `appendContinuationSummaryToWspPrompt()` - follow-up path without pasting raw Copy MD.
- UI: "Use last RedDog packet" checkbox (default ON); in-memory `state.lastContinuationSummary` only.
- Copy MD optional safe Continuation Summary section; fusion redaction gate tested on continuation block.

WSP: WSP_00, WSP_50, WSP_97, WSP_22. Version 0.3.27 -> 0.3.28.

## 2026-06-28 - REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_DRYRUN_PHASE1 (extension pointers)

- Module: `modules/communication/moltbot_bridge/src/reddog_wre_executor_dryrun.py`
- `plan_wre_isolated_worktree_execution_dryrun()` - plan + phase receipts; no git/worktree mutation.

WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1 (audit doc)

- Canonical: `docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md`
- Defines executor cage: entry conditions, isolation, mutation bounds, rollback, output contract.
- No runtime implementation in this slice.

WSP: WSP_00, WSP_15, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_WORK_ORDER_RUNTIME_INVOCATION_DRYRUN_PHASE1 (extension pointers)

- Points to `modules/communication/moltbot_bridge/src/reddog_work_order_runtime_invocation.py`.
- Chains #893 policy gate + #894 receipt; proves handoff without repo mutation.

WSP: WSP_34, WSP_50, WSP_97.

## 2026-06-28 - REDDOG_HERMES_WORK_ORDER_RECEIPT_PHASE1 (extension pointers)

- Points to `modules/communication/moltbot_bridge/src/reddog_work_order_receipt.py`.
- Pre-execution audit trail from #893 `PolicyGateReceipt`; Hermes-compatible, not live queue.

WSP: WSP_34, WSP_50, WSP_91, WSP_97.

## 2026-06-28 - REDDOG_OPENCLAW_WORK_ORDER_POLICY_GATE_PHASE1 (extension pointers)

- Points to `modules/communication/moltbot_bridge/src/reddog_openclaw_work_order_policy_gate.py`.
- Policy gate composes #890 dry-run + #892 permission snapshot freshness; Hermes-shaped receipt; no execution.

WSP: WSP_34, WSP_50, WSP_97.

## 2026-06-28 - REDDOG_GITHUB_PERMISSION_PROBE_PHASE1 (extension pointers)

- Points to `modules/platform_integration/github_integration/src/reddog_github_permission_probe.py`.
- Read-only snapshot feeds `repo_permission_snapshot` for future work-order emission.

WSP: WSP_34, WSP_50, WSP_97.

## 2026-06-28 - #890 LANDED + post-dryrun queue revision

- **#890 merged** @ `bd68ab83a` - `validate_work_order_dryrun()` pure validation module.
- P0 sequence: GitHub permission probe -> OpenClaw policy gate -> Hermes receipts -> WRE executor.

WSP: WSP_15, WSP_22.

## 2026-06-28 - REDDOG_GOVERNED_REPO_WORK_ORDER_DRYRUN_PHASE1

- Added `reddog_governed_work_order_dryrun.py` - typed `RedDogGovernedWorkOrder` + `HoloIndexEvidencePacket` dry-run validator.
- Decisions: `WOULD_ACCEPT`, `WOULD_REJECT`, `WOULD_ACCEPT_WITH_RETRIEVAL_GAP`; receipt digest; in-memory nonce replay guard.
- Gates: required fields, expiry, nonce, forbidden ops/paths, main mutation block, HoloIndex evidence (Addendum A), WAE-L1 mapping docstring (Addendum B).
- Tests: 13 pytest cases (accept + all rejection paths).
- No GitHub, branch, PR, write, shell, or merge calls.

WSP: WSP_34, WSP_50, WSP_97, WSP_22.

## 2026-06-28 - REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1

- Added `docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md` - authority model, `RedDogGovernedWorkOrder` schema, HoloIndex discoverability + reindex gate.
- Updated ROADMAP queue: contract DONE; P0 dryrun + GitHub probe + OpenClaw gate + WRE executor.
- README/INTERFACE: governed work-order contract pointers; authenticated principal wording; F0 merge SPECIFIED_NOT_IMPLEMENTED.
- HoloIndex: baseline Phase 0 + targeted `--index-docs` post-edit (Addendum C).
- No extension runtime, bridge, or HoloIndex ranking code changes.

WSP: WSP_00, WSP_34, WSP_50, WSP_54, WSP_95, WSP_97, WSP_109, WSP_22.

## 2026-06-27 - #888 LANDED + external lane queue revision (v0.3.27)

- **#888 merged** to `main` @ `9c3a8f829`; 012 smoke PASS (schema repair minimal path, `output_validation: passed`).
- **Queue revised:** P0 next is `REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1` (docs/audit authority model).
- P1: sanitized-target provenance, Run Trace telemetry correction.
- P2: governed work-order dryrun (after contract).
- Stale `provider_reasoning_note` tracked under telemetry slice, not #888.

WSP: WSP_15, WSP_22.

## 2026-06-14 - REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1 addendum (v0.3.27)

- Run Trace always emits `repair_context_mode` / `repair_mode` when `repair_attempted`.
- Dedicated repair Work Trail mapping (`repair_single_started`, no `panel_started` after repair).
- `extractMarkdownSection` + section-aware `mergeRepairedOutput(..., missingSections)`.
- Repair prompt lists required `## Section` headers explicitly; repair `max_tokens: 2400`.
- Contract tests OSR-007..OSR-010 (smoke-missing tail sections).
- Version bump 0.3.26 -> 0.3.27.

WSP: WSP_97, WSP_22.

## 2026-06-14 - REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1 (v0.3.26)

- Repair pass uses `buildRepairBoundedContext()` (minimal WSP contract; no HoloIndex resend).
- Repair routes `openrouter_single` with sanitized draft via `sanitizeTargetSnippetForRedaction`.
- `mergeRepairedOutput()` appends schema supplement to primary Fusion output.
- Run Trace: `repair_context_mode`, `repair_mode` on validation state.
- Contract tests OSR-001..OSR-006.
- Version bump 0.3.25 -> 0.3.26.

WSP: WSP_97, WSP_22, WSP_84.

## 2026-06-14 - ADDENDUM B bridge UTF-8 stdin invariant (v0.3.25)

- **Problem:** Valid U+2014 em dash in HoloIndex context passed JS normalization but Windows Python text stdin mis-decoded UTF-8 to surrogate `\udc94`, causing `redactor_error` at digest.
- **`scripts/advisory_model_once.py`:** `_read_stdin_json()` reads `sys.stdin.buffer` as UTF-8 (`errors="replace"`).
- **`extension.js`:** `buildBridgePythonEnv()` sets `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1` on bridge child.
- Tests UNI-008..UNI-010; Python `test_main_em_dash_utf8_stdin_not_redactor_error`.
- Prior surrogate normalization (Addendum A / UNI-001..007) unchanged.
- Version bump 0.3.24 -> 0.3.25.

WSP: WSP_00, WSP_97, WSP_22, WSP_84.

## 2026-06-14 - REDDOG_CONTEXT_UNICODE_NORMALIZATION_PHASE1 (v0.3.24)

- Added `normalizeBridgeTextForUnicode()` to replace isolated UTF-16 surrogates with `[MALFORMED_SURROGATE]` and apply NFC before bridge/redaction gate.
- Wired normalization in `callFusion` for WSP task prompt, bounded context, and repair prompt (`repair_prompt` source label).
- Run Trace / review packet: `unicode_normalization_applied`, `unicode_replacements_count`, `unicode_normalization_sources`, `unicode_normalization_form`.
- Contract tests UNI-001..UNI-007; fixtures `MALFORMED_UNICODE_CONTEXT`, `BLOCKED_POLICY_CONTEXT`.
- `fusion_redaction_gate.py` unchanged; policy not weakened.
- Version bump 0.3.23 -> 0.3.24.

WSP: WSP_00, WSP_15, WSP_97, WSP_22, WSP_84.

## 2026-06-14 - REDDOG_ALWAYS_HOLOINDEX_GROUNDING_PHASE1 (v0.3.23)

- REGULAR auto context: `none` -> `wsp_holo` (HoloIndex bundle-json; no Skillz/git/Fusion panel).
- Updated `modeSelectionReasoning` for REGULAR: cites HoloIndex-grounded wsp_holo.
- Contract tests THG-001..006; fixtures `REGULAR_SMOKE_PROMPT`.
- Preserved #883 target content + TCI-001..TCI-010 + ADDENDUM F gate tests.
- Version bump 0.3.22 -> 0.3.23.

WSP: WSP_00, WSP_15, WSP_87, WSP_97, WSP_22.

## 2026-06-14 - ADDENDUM F redaction-safe target snippets (v0.3.22)

- Raw `extension.js` snippets tripped Fusion BLOCK categories (`governance_instruction`, `private_reasoning`, etc.) before OpenRouter.
- Added `sanitizeTargetSnippetForRedaction()` mirroring `fusion_redaction_gate.py` BLOCK detectors; neutral `[SANITIZED_BLOCK:NN]` placeholders (category names in metadata only).
- Run Trace: `target_content_sanitized`, `target_content_sanitized_categories`.
- Contract tests TCI-009/TCI-010: Python gate probe on EXT-ACC-001 bounded context (no OpenRouter).
- `fusion_redaction_gate.py` unchanged.

WSP: WSP_97, WSP_22, WSP_84.

## 2026-06-14 - REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1 (v0.3.22)

- Added workspace-confined target snippet readers: `readBoundedTargetSnippet`, `buildTargetRecallContentSection`, `buildWsp97ProtocolExcerpt`.
- Wired `buildBoundedRepoContext` to egress `### Target recall content` after HoloIndex bundle-json (before Skillz noise).
- WSP_97 tasks append bounded `### WSP protocol excerpt (bounded)` from `WSP_97_System_Execution_Prompting_Protocol.md`.
- Run Trace scorecard: `target_content_included`, `target_content_paths`, `target_content_chars`, `target_content_omitted_reason`, `target_content_truncated`.
- Path safety rejects absolute paths, `..`, `.git`, `node_modules`, `.env`, `.vsix`; realpath confinement.
- ADDENDUM E contract tests: inferRecallTargetPaths, snippet inclusion, buildBoundedRepoContext integration, path denial (no OpenRouter).
- Shared fixtures: `tests/fixtures.js`; TEST_REGISTRY TCI-001..008 in `tests/TestModLog.md`; `tests/README.md` for reuse policy.
- Version bump 0.3.21 -> 0.3.22 (install hygiene).

WSP: WSP_00, WSP_15, WSP_87, WSP_97, WSP_22, WSP_84.

## 2026-06-26 - REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1 (docs)
- Added `docs/REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md`: 15-prompt pack, 012 rubric, runbook, WSP_97 truth rows, baseline vs replacement pass.
- Added `docs/acceptance/README.md` artifact storage rules.
- HoloIndex Phase 0: INDEX_GAP for extension.js and advisory_model_once.py retrieval.
- No runtime behavior changes; external lane scoreboard only.

WSP: WSP_00, WSP_15, WSP_87, WSP_97, WSP_22.

## 2026-06-26 - Content inclusion prompt REQUEST_CHANGES resolved

- Architect addenda A-D merged into `.prompt_reddog_context_target_content_inclusion_phase1.md`
- ASCII clean dispatch; MOJIBAKE validation via `MOJIBAKE_MARKERS` export not embedded chars
- Workspace-confined read safety + final-context telemetry + test exports specified
- Status: **APPROVE_WORKER_DISPATCH** (architect) pending worker implementation

WSP: WSP_97, WSP_22.

## 2026-06-26 - REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION worker prompt (review)

- Worker prompt: `.prompt_reddog_context_target_content_inclusion_phase1.md`
- Queued from EXT-ACC-001 evidence: path hit, no source content in bounded context.
- Version bump 0.3.22 planned in slice (install hygiene).

WSP: WSP_97, WSP_22.

## 2026-06-26 - EXT-ACC-001 post-#882 probe r3 (telemetry gate still open)

- Same path-only signal as r2; repair redaction passed (r2 repair blocked).
- Run Trace still `v0.3.20` - force-install did not reflect in host; telemetry gate open.
- Queue content inclusion; hold dispatch until `target_recall_ok` appears in Run Trace.

WSP: WSP_97, WSP_22.

## 2026-06-26 - Install trap: header 0.3.21 vs stale host (docs)

- **OBSERVED:** Cursor header `Build: 0.3.21` while installed `extension.js` had `v0.3.20` provider note and no #882 telemetry.
- **Cause:** #882 landed without version bump beyond `0.3.21`; force VSIX install required.
- **Runbook:** Preflight requires Run Trace internals, not header alone.

WSP: WSP_97, WSP_22.

## 2026-06-26 - EXT-ACC-001 post-#882 probe r2 (needs_repair, stale telemetry)

- Main egress succeeded; RedDog correctly BLOCKed on missing source (path hit ~7.4%, no content body).
- **Queue** `REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1` - do **not** treat as final post-#882 proof (v0.3.20 note; no `target_recall_ok` / `code_hits_count`).
- **Pending:** Clean EXT-ACC-001 after force-install VSIX; then dispatch content-inclusion if criterion #2 still fails with telemetry active.

WSP: WSP_97, WSP_22.

## 2026-06-26 - EXT-ACC-001 post-#882 probe recorded (blocked)

- **Verdict:** `blocked` - `redactor_error` before OpenRouter; HoloIndex fix not assessable at model layer.
- **Distinction:** `redactor_error` (gate scan error, fail-closed)  `blocked_policy` (intentional policy block).
- **Next slice (P0):** `REDDOG_REDACTION_GATE_CONTEXT_ERROR_DIAGNOSTIC_PHASE1` - before `REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1`.
- **Pending:** EXT-ACC-003 post-#882 probe (confirms context bundle vs work focus if same error).
- **Note:** Trace showed `v0.3.20` provider note - reinstall post-#882 VSIX before reruns.

WSP: WSP_97, WSP_22.

## 2026-06-26 - Post-#882 acceptance criteria update (docs)

- Updated `REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md`: EXT-ACC-001 replacement pass requires five criteria (path hit, source content in bounded context, WSP_97 finding on source, `target_recall_ok`, output validation).
- Documented path-ranking vs content-inclusion distinction; post-#882 probe order (001 + 003 only before full 15-pack).
- Recorded conditional follow-on `REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1` - do not start until post-land probe proves path-only context.

WSP: WSP_97, WSP_22.

## 2026-06-26 - HOLOINDEX_REDDOG_EXTENSION_INDEX_GAP_PHASE1 (worker slice)

**Problem (OBSERVED):** EXT-ACC-001 showed `bundle_json_ok` + `code_hits=5` but `extension.js` not retrieved; `index_gap_detected` falsely reported `false`.

**Root causes (OBSERVED):**
- `bundle_json.py` path fallback `allowed_ext` excluded `.js`.
- RedDog NAVIGATION recall keys were appended to `DAE_ARCHITECTURE` instead of `NEED_TO`.
- `holoIndexMetaFromBundle()` inferred gap from structured memory / zero WSP hits, not target path recall.

**Fixes (IMPLEMENTED):**
- Added `.js` to lexical path fallback; filename token + NEED_TO exact/substring scoring boosts.
- Moved RedDog keys into `NEED_TO`; added `HOLOINDEX.md` manifest.
- Added `inferRecallTargetPaths()`, `evaluateTargetRecall()`, `target_recall_ok`, `code_hits_count` scorecard fields.
- Regression tests: `holo_index/tests/test_reddog_extension_bundle_recall.py`; contract tests updated.

**Architect review packet:** `docs/REDDOG_HOLOINDEX_INDEX_GAP_ARCHITECT_REVIEW_PHASE1.md`

WSP: WSP_50, WSP_84, WSP_87, WSP_97.

## 2026-06-25 - v0.3.21 Blocked RedDog Copy MD polish
- Adjacent duplicate Work Trail events collapse to one entry (detail-bearing event retained).
- Redaction-block-only runs use conservative Governed Handoff defaults: `handoff_needed: unknown`, `reason: blocked_context_needs_local_0102_review`, `wsp15_priority: P1`, `suggested_slice_name: none`.
- Target may remain `[INFERRED]` from work focus; no automatic WRE dispatch assertion on blocked-local packets.

WSP: WSP_22, WSP_97.

## 2026-06-24 - v0.3.20 Redaction Gate Report + WRE Handoff Readiness (Addendum F)
- Rebased onto #871 bridge hardening (`9e5416af4`); version bump 0.3.19 -> 0.3.20.
- Copy MD redaction blocks now include `## Redaction Gate Report` with WSP_97 truth labels (OBSERVED/UNKNOWN); no raw blocked content.
- Required fields: `BLOCKED_LOCALLY`, `made_network_call: false`, `blocked_stage: pre_openrouter_request`, `blocked_payload_part: unknown` when gate cannot identify part, `raw_snippets_included: false`, bounded digest, safe summary, `next_safe_context`.
- Substantive tasks append `## Governed Handoff Recommendation` (`advisory_only`, bounded evidence refs, WSP_15 priority inference).
- Copy MD Work Trail: allowlisted normalized events (cap 50), `sanitizeCopyMdText` for secret-adjacent phrases.
- Run Trace: dual effort (`reddog_effort` + provider reasoning report-only); HoloIndex recall scorecard when bundle context used.

WSP: WSP_22, WSP_97, WSP_15.

## 2026-06-24 - v0.3.19 RedDog UX + Review Packet Polish
- Moved Working Tail strip above controls row (output -> trail -> 0102 Role/controls -> 012 work focus).
- Renamed UI label `Worker` -> `0102 Role`; role options unchanged.
- Copy MD now prepends `Run Trace` (role, tier, effort, mode, models, context, redaction, validation).
- Redaction-block and repair-failure Copy MD include `BLOCKED_LOCALLY` / `OUTPUT_VALIDATION_FAILED` with explicit incomplete-advisory wording.
- Added mojibake detector (``, ``) with `mojibake_detected` flag in output_validation and Copy MD warning.
- Validation repair failure appends local static footer (Verification Gaps + Next safest step); no extra network call.

WSP: WSP_22, WSP_97.

## 2026-06-24 - v0.3.18 Foundups(R)Agent Branding
- Renamed user-facing extension surface from "FoundUps Fusion Worker" to "Foundups(R)Agent".
- Kept internal package id and command id stable (`foundups-fusion-worker`, `foundupsFusion.open`) to avoid breaking existing installs/settings.
- Clarified that RedDog is the 0102 digital-twin architect inside Foundups(R)Agent and Fusion is an internal reasoning mode.

## V0.3.17 REDDOG_WORKING_TRAIL_PHASE1_CODE 2026-06-23

- Implemented RedDog working trail strip (`#reddogWorkingTrail`) under work focus composer.
- ASCII pixel grammar: `~~~`, `.rd.`, `<rd>`, `>rd>`, `!rd!`.
- Structured progress: host posts `{ command: 'progress', stage, text }`; scrollback uses `{ command: 'status', text }` unchanged.
- `REDDOG_STAGE_ACTIONS` covers all 16 unique `advisory_model_once.py` bridge stages; regex fallback for webview-local events.
- Elapsed timer (1s), 10s no-event sitting fallback, idle pixel cycle while running, terminal hold 3000ms.
- Redaction-block UX: operator message, `made_network_call=false`, `retry_count=0`; no raw blocked content in scrollback.
- `advisory_model_once.py` unchanged (Phase 3 review-packet summary deferred).

WSP: WSP_22, WSP_97.

## 2026-06-23 - REDDOG_RECURSIVE_DAE_ECOSYSTEM_ARCHITECTURE_PHASE1

Audit and doc additions for correct FoundUps architecture capture:

- Added "RedDog and the Recursive 0102 DAE Ecosystem" section to README.md, INTERFACE.md, ROADMAP.md.
- Architecture stack: 012 -> RedDog digital twin / architect -> recursive 0102 DAE ecosystem.
- Layer roles table: RedDog, Hermes, OpenClaw, HoloIndex, Skillz/Rolodex, Autonomous WRE/DAE agents, Sentinels, WRE, CABR/pAVS, 012.
- Key correction documented: Autonomous WRE/DAE agents are NOT 012 work. 012 provides work focus, testing, sovereign approval, and override.
- Added WSP_97 truth table rows: REDDOG_IS_ARCHITECT_INTERFACE, AUTONOMOUS_DAE_WORK_NOT_012_WORK, HERMES_IS_SCAFFOLDING_NOT_POLICY, OPENCLAW_IS_POLICY_GATE, WRE_RETAINS_REPO_AUTHORITY, SENTINELS_REVIEW_NOT_EXECUTE, CABR_PAVS_VALIDATES_BENEFIT, EXTENSION_REMAINS_ADVISORY_ONLY.
- HoloIndex Phase 0 retrieval audit complete (4 queries, all PASS, INDEX_GAP noted for extension.js/advisory_model_once.py).

WSP: WSP_00, WSP_48, WSP_54, WSP_73, WSP_97.

## V0.3.17b REDDOG_WORKING_TRAIL_PHASE1_REPAIR 2026-06-23

- Repair pass on docs/REDDOG_WORKING_TRAIL_PHASE1.md.
- ASCII pixel grammar: replaced `.v.`, `xvx`, `!v!`, `IvI` Unicode glyphs with `.rd.`, `<rd>`, `!rd!`, `>rd>` throughout (tables, code blocks, prose, JS signatures, CSS). Zero non-ASCII confirmed by rg scan.
- Phase 2/3 split: clarified Phase 2 = extension.js only (~123 lines, no advisory_model_once.py); Phase 3 = bounded working_trail_summary / review event emission. Renamed "training events" to `working_trail_events` / `trail telemetry` in Phase 2 scope.
- Terminal state hold: corrected `setRunning(false)` contract -- terminal states (`>rd>`, `!rd!`) held >=3s via `setTimeout(3000)` before idle reset; immediate reset removed.
- Structured stage first: Section 2 now specifies stage-field primary match (advisory_model_once.py emits `_progress(stage, text)` confirmed); text regex is fallback only.
- Resolved Open Questions (Section 10): Q1=review-packet append, Q2=ASCII-safe Phase 2, Q3=continue elapsed; removed as open questions.
- WSP_97 expanded from 10 to 16 rows (items 11-16: MOJIBAKE_FREE, ASCII_PIXEL_FALLBACK, PHASE2_EXTENSION_ONLY, TRAINING_EVENTS_DEFERRED, TERMINAL_STATE_VISIBLE, STRUCTURED_STAGE_FIRST).

WSP: WSP_22, WSP_97.

## V0.3.17 - REDDOG_WORKING_TRAIL_PHASE1 (Design Contract) - 2026-06-23

- Authored design contract for RedDog working trail (docs/REDDOG_WORKING_TRAIL_PHASE1.md).
- Defines UI contract (`reddogWorkingTrail` strip), event-to-action mapping for all 16 bridge progress events, JSONL training schema, and WSP_97 truth boundary checklist.
- Phase 1: design only. Phase 2 implements extension.js trail strip + elapsed timer; advisory_model_once.py unchanged in Phase 2.
- WSP_97 N/10 (all 10 truth boundary items PASS per design).

WSP: WSP_22, WSP_97, WSP_15.

## 2026-06-22 - REDDOG_BRIDGE_HARDENING_PHASE1 (v0.3.16)

- Python resolver chain: configured -> .venv/venv -> system fallback; reports interpreter in bridge_meta.
- Subprocess stdout/stderr caps with kill-on-exceed and output_cap_exceeded reason.
- Webview dispose kills in-flight bridge child (orphan cleanup).
- Context/prompt char budget before bridge; truncation_applied + truncation_reason in review packet.
- advisory_model_once: panel_models cap 6; HTTP retry only on 429/502/503 (max 2); same redacted body; retry metadata in packet.
- Failure taxonomy: redaction_blocked, missing_key, timeout, retry_exhausted, http_error, malformed_response, subprocess_failed, output_cap_exceeded.
- Added scripts/tests/test_advisory_model_once_hardening.py for retry invariants.

WSP: WSP_97, WSP_87.

## 2026-06-22 - Addendum A Gate Precision (#870 pre-land)

- Verified exact scope: 8 extension-local files only; `scripts/advisory_model_once.py` unchanged.
- Strengthened contract tests: WSP_00/97/15 non-vacuity, raw-focus bypass guard, digest boundedness.
- Added WSP_97 truth rows: WORK_FOCUS_NOT_AUTHORITY, WSP_PROMPT_0102_GENERATED, RAW_FOCUS_NOT_SENT_AS_SOLE_AUTHORITY, DIGESTS_NOT_RAW_CONTEXT, ROUTING_UNCHANGED_FROM_0_3_14.
- Recorded Addendum B bridge hardening controls in ROADMAP (next slice; not in #870).

## 2026-06-22 - REDDOG_WORK_FOCUS_TO_WSP_PROMPT_PHASE1 (v0.3.15)

- Renamed 012-facing UI language from "prompt" to **work focus** (composer, scrollback labels, placeholders).
- Added `constructWspTaskPrompt()` and `redactedDigest()` - 0102 assembles WSP task prompt from work focus before bridge call.
- Bridge now receives WSP task prompt, not raw composer text alone; classification/context still derived from work focus.
- Review packet adds `work_focus_digest`, `wsp_prompt_digest`, `prompt_construction: 0102_generated_from_work_focus`.
- HoloIndex Phase 0 (pre-edit): Q1/Q2 INDEX_GAP for extension.js; Q3 MEDIUM_SIGNAL; Q4 adjacent redaction gate hits.
- Preserved v0.3.14 auto-router, architect trace schema, and advisory-only boundary unchanged.

WSP: WSP_00, WSP_87, WSP_97.

## 2026-06-22 - HoloIndex Phase 0 / WSP_87 (REDDOG_ARCHITECT_AUTO_ROUTER_PHASE1)

Pre-edit retrieval audit (bundle-json; all four queries PASS, no offline fallback required):

| Query | Status | WSP | Code | Edit target | Classification |
| --- | --- | --- | --- | --- | --- |
| Q1 RedDog extension | PASS | 8 | 6 | `extension.js` **missed**; module README/INTERFACE in bundle | **INDEX_GAP** |
| Q2 Bridge/redaction | PASS | 8 | 5 | `advisory_model_once.py` **missed** | **INDEX_GAP** |
| Q3 Skillz/handoff | PASS | 8 | 8 | `video_comments/skillz/qwen_studio_engage` in docs; extension discovery unwired in index | **MEDIUM_SIGNAL** |
| Q4 WSP protocols | PASS | 8 | 8 | WSP_00/15/87/97 not top-ranked; RedDog briefings adjacent | **MEDIUM_SIGNAL** |

**WSP_97 finding (retrieval weakness):** HoloIndex bundle-json correctly resolved extension module memory (tier0_complete, README/INTERFACE present) but semantic code search returned adjacent routers (`fusion_adapter.py`, `wsp_adaptive_router_integration.py`) instead of `extensions/foundups_advisory_workers/extension.js` or `scripts/advisory_model_once.py`. Direct-read confirmed edit targets post-retrieval.

**Follow-up slice recorded:** `HOLOINDEX_REDDOG_EXTENSION_INDEX_GAP_PHASE1` - index extension.js, advisory_model_once.py, and Skillz discovery paths for RedDog queries.

WSP: WSP_87, WSP_97.

## 2026-06-22 - REDDOG_AUTO_ROUTER_SKILLZ_CONTEXT_PHASE1 (v0.3.14)

- Changed RedDog defaults to GLM-5.2 principal, DeepSeek V4 Pro adversarial critic, and Kimi K2.7 Code implementation critic.
- Removed Mode/Effort/Context from the 012-facing prompt controls; routing and context now resolve automatically from WSP_15 task classification.
- Added bounded Skillz/Wardrobe/Rolodex/OpenClaw/Hermes discovery to HIGH/ULTRA context packets for governed handoff recommendations.
- Added visible `RedDog Routing` output and review-packet metadata for resolved effort, mode, context, principal, and panel.
- Wired Skillz/Wardrobe/Rolodex context into `buildBoundedRepoContext` for HIGH/ULTRA modes; ULTRA git diff now includes `wsp_holo_git_skillz`.
- Extended architect output schema: Architect Trace (structured CoR, not raw CoT), Verification gaps, mode-selection reasoning, Fusion panel structure validation.
- Added WSP_97 truth table to README/INTERFACE; recorded future slices in ROADMAP.
- Preserved advisory-only boundary: the extension can recommend handoffs but cannot execute Skillz, shell, OpenClaw, Hermes, repo, browser, merge, or deployment actions.
## 2026-06-22 - REDDOG_FUSION_ORCHESTRATOR_TRACKING_PHASE1 (git land)

- First tracked commit of `extensions/foundups_advisory_workers/` and `scripts/advisory_model_once.py`.
- VSIX remains a local build artifact only (`*.vsix` gitignored; package via `vsce package --no-dependencies`).
- No behavior change from v0.3.13 gate; discoverability/PR scope only.
- Explicit non-overlap: livechat #841 selective cancellation untouched.

WSP: WSP_22, WSP_49, WSP_97.

## 2026-06-22 - REDDOG_FUSION_ORCHESTRATOR_PHASE1 (v0.3.13)

- Added internal orchestrator contract in `extension.js`:
  - `classifyTaskForRedDog` WSP_15-style task classifier
  - `resolveAutoEffort` auto effort selection (ULTRA/HIGH/REGULAR)
  - `resolveModelMode` RedDog WSP default to auditable manual panel
  - `validateRedDogOutput` required schema section validator
  - `buildRepairPrompt` bounded one-pass repair helper
- Substantive RedDog answers now require WSP_97 Truth Labels in the output schema.
- On missing schema sections, run one repair pass through the existing redaction-gated bridge; attach validator/repair status to review packet.
- OpenRouter Fusion alias remains selectable but is not the RedDog WSP default.
- Extended contract tests in `tests/verify_extension_contract.js` (15 assertions including inject/revert classifier paths).

WSP: WSP_00, WSP_15, WSP_22, WSP_97, WSP_109.

## 2026-06-22 - RedDog Architect Webview Contract (v0.3.12)

- Reworked the Cursor webview into a VS Code terminal/chat-style surface:
  - compact header
  - scrollback output pane
  - fixed bottom composer
  - no separate status notices outside output
  - `Enter` sends and `Shift+Enter` inserts newline
- Added worker controls:
  - RedDog Architect
  - WSP Gate Critic
  - Repair Planner
  - Smoke Test
- Added effort controls:
  - Auto
  - Regular
  - High
  - Ultra
- Strengthened WSP operating prompt:
  - WSP_00 role/origin framing
  - WSP_97 truth labels
  - WSP_15 priority block at bottom
  - proposed fix required for every finding
  - HoloIndex retrieval weakness must become a remediation finding
- Changed HoloIndex context gathering to WSP_00 bundle-json first with `HOLO_SKIP_MODEL=1`, falling back to offline lexical only if bundle recall fails.
- Updated the bridge so prompt and bounded context are redaction-gated separately and the explicit RedDog system prompt reaches regular, Fusion alias, and manual panel modes.
- Added Tier-0/Tier-1 memory files for HoloIndex discoverability: `INTERFACE.md`, `ROADMAP.md`, `ModLog.md`, and `tests/TestModLog.md`.

WSP: WSP_00, WSP_15, WSP_22, WSP_87, WSP_97, WSP_109.
