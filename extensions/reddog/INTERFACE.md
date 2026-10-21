# RedDog Interface

## Model routing and evaluation fallback

The extension consumes receipt-bound AI Gateway runtime bindings when
configured. It does not let Nemotron, Hermes, OpenClaw, LM Studio availability,
or extension keyword heuristics mint model-selection authority. The shared
verified topology resolver preserves exact role/provider/model bindings and
fails closed when the consumer does not expose the required provider. Each
`callFusion` provider egress obtains a fresh query receipt and performs an
epoch-second `topology_valid_until` check before spawning the provider bridge;
the worker captured when the webview opened is never sufficient call authority.

Without a ready runtime binding, the explicit evaluation fallback is:

- principal: `z-ai/glm-5.2`
- critics: `deepseek/deepseek-v4-pro`, `qwen/qwen3.8-max`,
  `moonshotai/kimi-k3`

This roster is usable only when the operator explicitly sets
`reddog.allowEvaluationFallback=true`; its default is false. The opt-in applies
only to an unconfigured runtime. A configured binding that is rejected,
expired, replayed, or provider-incompatible always blocks.
An admitted evaluation roster remains no-effect: only a fresh
`receipt_bound_runtime` egress can open bounded action planning. Evaluation
output cannot enqueue OpenClaw work, dispatch, or enter production promotion.

The local Nemotron proposer is shadow-only. It returns ordered model IDs;
AI Gateway supplies providers/roles and admits only evaluation-eligible held-out
benchmark candidates. No production routing or extension mutation follows from
that proposal.

## Governed resident Holo grounding

The VSIX one-shot and canonical resident/OpenClaw read-only worker share the
same generation-bound owner-query contract. The Python worker adapter retains
its 60-second total wall and reserves three seconds for cleanup; the canonical
CLI and asynchronous VSIX cold path are separately bounded at 300 seconds to
cover the existing 270-second readiness canary. It exposes only allowed scoped
hit metadata after exact CURRENT repository, authority, generation, replica,
and receipt verification; Fusion receives no route or owner credential.

Each success and health response now carries the owner-computed
`retrieval_runtime_ranker_digest` for the exact twelve-module source closure that
controls backend routing, ranking, Tier0 injection/dedup, path projection, and
response ordering. Query clients and evaluation receipts require that value to
equal the candidate's clean-authority digest. The same receipt now carries the
child-computed `runtime_environment_digest`, binding executable content,
ABI/platform, verified RedDog source bytes, distribution build records,
replica/model artifacts, and actual allowlisted settings. Installed dependency
payload bytes are not exact-closure verified, so the assurance flag is false
and A-grade admission rejects.

The A-grade facade always reruns the public corpus and enforces non-downgradable
floors, but it has no non-test/VSIX caller and no deployed independent signing
authority. Retrieval-quality RSI is unavailable and no promotion follows.

Automatic exact-main maintenance, route activation, and AgentDB completion
passed again through the real OpenClaw supervisor at exact main
`66526ae5cdd0467ce264c1db4122ab82eadb7733` on 2026-08-27. Three fresh-process
queries completed in about 34 seconds each and a pre-warmed query in 10.3
seconds; all were CURRENT/no-gap/no-reindex, and full immutable revalidation of
33 artifacts remained unchanged. Earlier post-restart diagnostics failed closed
at 60/180 seconds; the latest base-bound governed query passed on attempt one
inside the 300-second CLI wall. That proves base usability, not exact-current-
main readiness or scale.
Persistent authenticated owner activation is P0 scalability debt, and no
outbound Hermes dispatch is enabled by this interface.

## Test and promotion interface

`package.json` exposes `test`, `test:contract`, and `test:release` without local
dependencies. `tests/reddog_test_plan.js` is the single authenticated membership
source for the bounded developer tiers and the four promotion groups.
The exact release invocation is `npm run test:release`.
`tests/run_reddog_test_tier.js` accepts only `fast` or `contract`, resolves exact
regular files inside the test root, runs members sequentially with bounded
output/time, and propagates the first failure.

`tests/verify_extension_contract.js` remains the backward-compatible canonical
promotion entry. Its parent process authenticates all 18 shards and requires
the seven deferred `test_*` members (five governed-Git plus two bridge/package
tails) to exactly equal the unique flattened release plan. Four children then
run the shared-VM core, governed-Git hardening, Git
environment/ref formats, and bridge-environment/WSP_62 groups concurrently.
Concurrency is capped at four; each child is capped at 400 seconds and 2 MiB
per output stream under the unchanged 420-second release ceiling. Results print
in plan order and any exit, signal, timeout, or output overflow fails promotion.
The canonical owner never reads an environment group selector. It launches the
unadvertised `reddog_release_worker.js` with an exact group argv and a fresh
128-bit nonce mirrored in an owner-overridden child environment. The supervisor
starts one overall deadline from command entry, records child/release timeout
state before termination, then attempts graceful and forced process-tree stops.
If close cannot be confirmed, it destroys/unrefs child handles and emits a
bounded failing receipt after fixed grace; a later zero exit cannot erase it.
The first aligned promotion receipt was PASS in 295.928 seconds with `core` as
the slowest group at 295.219 seconds. A repeat passed in 266.709 seconds;
headroom is derived from the slower receipt.
A hostile ambient-selector repair run passed all four groups in 279.723 seconds.
Windows tree termination resolves `SystemRoot`/`SYSTEMROOT` to an absolute
`System32\\taskkill.exe`, uses fixed PID arguments with `shell: false`, and
waits for explicit process evidence. Synchronous/asynchronous launch failure,
nonzero exit, or the 750-millisecond taskkill timeout returns failure to the
controller for both graceful and forced attempts. Error handling remains
idempotent after settlement; POSIX process-group signaling is unchanged.
The loop-3 hostile-selector promotion passed in 274.537 seconds wall time;
the owner receipt was 273.762 seconds with all four timeout fields false.

`sanitizedGitEnv(source)` delegates to the fixed `buildGovernedGit(source)`
profile. It returns a new object and never aliases or mutates `source`. The
profile admits only case-normalized Windows process-launch/root/shell keys,
required temp keys, and locale controls, then overwrites the exact governed Git
variables. It does not copy PATH/Path/PATHEXT or wildcard-copy ambient `GIT_*`,
credential, Python, Node, dynamic-loader, SSH-agent, home/profile,
virtual-environment, or arbitrary caller fields.

`governed_git_executable.js` is the single executable authority. It resolves
lexical PATH/PATHEXT order before child execution, binds the canonical regular
file's portable/native identity, size, and SHA-256, rejects link/reparse
substitution, and permits ordinary installed hardlinks. Windows additionally
requires Valid Authenticode from an independently bound fixed-SystemRoot
PowerShell verifier; non-Windows records `not_applicable`. All readiness,
configuration, projection, content, and repository-state commands invoke the
same receipt-bound absolute executable with the closed environment and require
successful binding revalidation before releasing output. The direct proof does
not extend to Git DLLs or helper-program closure.
Local configuration and ownership probes have an exact five-second child bound;
this remains fail-closed while allowing the documented four-worker release
closure to contend for CPU and disk without a false authority rejection.

Readiness and projection receipts use `reddog_governed_git_readiness.v2` and
`reddog_git_projection_receipt.v2`. Start Operations carries a
`reddog_governed_git_repo_state.v2` receipt from the JavaScript authority into
Python; the Python snapshot consumer validates its root, HEAD, dirty paths,
worktree digest, readiness, digest-only executable receipt, and content digest
rather than launching ambient Git. Body hashing is necessary but insufficient:
the consumer also enforces exact object keys, types, bounds, digest formats,
complete equal portable/native identities, link counts, and platform signature
shape. Unknown or raw-path fields fail closed.

`buildBridgePythonEnv(baseEnv, profile)` delegates to the closed environment
profiles in `start_operations_environment.js`. Common isolated-profile state is limited
to allowlisted Windows/POSIX process-discovery, temp/home, locale, certificate,
and virtual-environment keys plus `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`, and
`PYTHONNOUSERSITE=1`. Named profiles admit only their observed configuration:
`advisory_provider`, `authoritative_work_state`, `model_runtime_binding`,
`holo_query`, `holoindex_owner`, and `resident_architect`; `default` adds none.
Unknown or caller-constructed profiles fail to `default`. OpenRouter, Holo
owner, and resident authority credentials never cross into another profile.
`REDDOG_HOLOINDEX_QUERY_ROUTE_FILE` and the exclusive legacy
`REDDOG_HOLOINDEX_QUERY_REPLICA_ROOT` are admitted by the closed
`holoindex_owner` and `resident_architect` profiles, allowing their Python
boundaries to prove the same explicit active replica without exposing it to
unrelated bridge children. The separate Start Operations control environment
also admits these exact non-empty strings for its promotion-time owner check;
non-string, empty, secret, and arbitrary values are dropped. Python rejects
both route candidates together, requires a digest-bound terminal journal for
`CURRENT`, and exact-matches route-file authority and replica bindings to the
active descriptor without consumer-side recovery or publication.
Those two profiles and the bounded Start Operations control boundary admit
`REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT` so an
explicit clean committed-head authority checkout survives the JavaScript to
Python boundary. The value remains only a candidate: Python independently
proves its topology, clean state, and exact workspace HEAD before use.
The resident worker does not treat profile propagation as proof. Its default
generation-bound adapter invokes the same one-shot owner bridge in a bounded
child process, validates exact CURRENT authority/replica/receipt coherence, and
projects only allowed-path hits into a new scoped worker receipt. Raw owner
evidence, private route state, and credentials do not enter Fusion. The path
grounds canonical resident/OpenClaw audits but performs no live Hermes dispatch.
`buildHoloQueryEnv(envLike, retrievalMode)` composes `holo_query`, which admits
only `HOLOINDEX_SSD_PATH`, legacy `HOLO_SSD_PATH`, and explicit `HOLO_OFFLINE`,
then forces `HOLOINDEX_QUERY_READONLY=1`. Lexical mode additionally synthesizes
`HOLO_SKIP_MODEL=1`; semantic and unknown modes remove an ambient skip request.
The local Holo helper removes the common `PYTHONNOUSERSITE` hardening flag to
preserve the current configured/system interpreter's per-user NumPy visibility;
it still excludes `PYTHONPATH`, `PYTHONHOME`, `PYTHONSTARTUP`, and credentials.
This residual package-provenance risk remains until a sealed/configured Holo
interpreter closure can support universal user-site isolation. The function
returns a fresh object and never aliases or mutates `envLike`.

R9 makes `registeredGitMetadataReceipt(root)` an authority receipt rather than
a whole-repository hygiene receipt. Its existing frozen public shape remains
`{ fingerprint, valid, worktree_config_state }`. The fingerprint covers the
canonical direct/linked topology, linked gitfile/common/back-reference,
authority HEAD/index/config.worktree, common config/shallow/info attributes and
exclude controls, top-level objects/refs directory identity, and the exact
current detached or `refs/heads/*` loose/packed resolution. Alternate stores,
grafts, unsafe relevant controls, and unsupported ref storage fail closed.

The common `info` and `objects/info` directories are required ordinary,
canonical in-common directories for both direct repositories and linked
worktrees. Missing, non-directory, symlink/junction/reparse escape, or identity
substitution during their pre/realpath/post capture rejects the receipt; RedDog
does not create either directory and still does not enumerate their entries.
Supported `refs/heads/*` names use a bounded internal parser faithful to Git's
ref-format exclusions: Unicode and `+` remain valid, while controls, space,
DEL, `~^:?*[\\`, `..`, `@{`, empty components, dot-prefixed/dot-suffixed
components, `.lock` suffixes, and leading/trailing slash fail closed. The
parser never invokes Git and never broadens authority beyond branch refs. The
receipt's OID check is intentionally structural: exactly 40 or 64 hexadecimal
characters for detached HEAD and the current loose or packed ref. It does not
reimplement Git's config grammar. Complete capped config bytes remain in the
receipt fingerprint, while Git's own `HEAD^{commit}` resolution proves object-
format and commit semantics before a bound named batch or projection is
released. Packed current-ref classification recognizes exact-current
whitespace tokens before accepting only the canonical one-space record;
malformed current records cannot degrade into the valid unborn state.

`noFollowPathEntry(path)` centralizes internal entry state as `absent`,
`present`, or `error` from `lstat`. Only `ENOENT` maps to absent. Optional and
forbidden controls, ordinary directories, `plainControlFile()`, direct
`commondir`, current loose refs, and execution-root `.git` therefore reject
dangling or unreadable present entries instead of treating them as missing.
`registeredGitMetadataState(root)` shares the root `.git` observation with the
first receipt so this correction does not add a fourth receipt or weaken the
absolute-final-proof order. For supported branch refs, required canonical
`refs/heads` plus each existing deeper parent is checked without directory
enumeration; only a genuinely missing deeper parent preserves unborn handling.

`gitOutputs()` still accepts at most 16 unique fixed operation names and keeps
its existing array/error shapes. Each immutable command list runs twice with
identical governed argv/environment; all bounded strings must match. A bound
batch that does not request `HEAD_SHA` prepends that fixed operation as its
semantic proof and removes the proof output before return. Only then is the
narrow final receipt taken as the last protected read. A command error, output
mismatch, or relevant receipt drift invalidates the whole batch. `HEAD_SHA`
verifies `HEAD^{commit}`, so format mismatch and missing/corrupt required
objects fail through Git even though unrelated object directories are not
traversed. Snapshot callers use the same semantic proof while preserving true
unborn handling, two enumerations, stable content captures, and a narrow final
receipt. `governedGitReadiness()` covers structural/config readiness, not later
command success, so READY may coexist with a fail-closed command result.

Projection admission never uses a follow-target existence check. For each
changed path, `projectionPathState()` uses the shared no-follow entry classifier
and validates every existing parent component as a stable canonical ordinary
directory, without enumeration. Exact `ENOENT` may represent a tracked
deletion; dangling final/parent links, junctions, non-directory parents, lookup
errors, or component substitution reject the complete snapshot. An absent
untracked record remains invalid. Present files continue through
`resolveSafeRepoFile()` and the canonical confined regular-file/single-link
identity checks.

Before `readOpenedBytes(handle, size, maxSize)` is called, the opened fd must be
an ordinary single-link file with the exact pre-open identity and a safe integer
size from zero through 2 MiB. The reader defensively repeats the explicit size
cap before allocating exactly that size and issuing only remaining-length
positional `readSync` requests. A zero or incomplete read, growth, truncation,
fd/path identity change, pre-open replacement, or invalid size returns no
projection. Zero bytes and exactly 2 MiB are valid; 2 MiB plus one is rejected.
These checks do not increase the per-file or aggregate caps.

Each present control is capped before and after open, allocated at exactly the
opened size, and read through explicit remaining-length fd requests. A zero or
incomplete read, growth, truncation, or candidate-path substitution rejects the
receipt at the retained fd/path identity checks. Index bytes are digested as a
Buffer and are not copied into a UTF-8 string. `packedRefOid()` deliberately
parses only an exact current-ref entry (including duplicate/current-OID
rejection); malformed unrelated packed lines are outside the narrow receipt's
global-hygiene claim. A `HEAD_SHA` authority resolution that makes Git parse
such malformed storage fails the complete named batch as a command failure.

This is point-sampled consistency, not continuous filesystem atomicity. A
fully restored ABA between samples is outside the receipt claim. Per-query
global loose-object/all-ref special-file hygiene is also not claimed; that
would require a separate maintenance audit. The FoundUp resolver's subsequent
registry/schema byte reads are not transactionally enclosed by the Git quartet
and remain an explicitly separate atomicity limitation.

Historical release narratives and superseded acceptance boundaries are maintained in
`ModLog.md`; this interface retains only current callable and authority contracts.

## Purpose

`reddog` is a local Cursor/VS Code thin-client extension for RedDog, the
lightweight interaction, exchange, and attention surface backed by the
principal-scoped 0102 FoundUps Digital Twin. It retains the redaction-gated
OpenRouter bridge through `scripts/advisory_model_once.py`.

### Continuous conversation adapter

`conversation_plane_policy.js` exposes deterministic `classify()` plus bounded
prompt, context, effort, and model selectors. Its decision carries independent
`interaction_intent`, `reasoning_depth`, and `effect_ceiling` fields. The
adapter can emit at most `PROPOSAL`; it cannot emit bounded execution authority.
`CHAT` always receives an empty repository context packet. Default fast/critic
chat uses the configured single-model path; an explicit/risk-derived panel may
use Fusion without changing the `NONE` effect ceiling.
Raw provider history and the opt-in last-work-packet summary are both withheld
from foreground chat, even if the UI continuation checkbox is selected.

This is a package-internal policy interface, not a network API. The Digital
Twin backend now defines a strict zero-authority turn/status/cancel envelope,
binds existing requests to verified current-generation session/AgentDB state,
stores their content-free replay fence, and can persist one trusted empty-ID
TURN scope after exact intent/grounding/FoundUp/E0 checks. The backend also
durably binds that original empty-ID request to the resolved ID/revision 0
through an explicit v2 journal record under the same signed-generation lease.
The backend's scope-schema-v4 E0 state signs the exact source/resolved request
commitment, and replay consumes its verified authority atomically.
The extension does not call these aggregates, and the first TURN is not yet
executed by a handler or immediate CAS. PFMall and phone clients therefore still
require an authenticated resident adapter with durable event ordering; the
browser `reddog:command` event is not that transport.

### VS Code workspace and package capabilities

`package.json` declares `untrustedWorkspaces.supported=false` and
`virtualWorkspaces.supported=false`. RedDog requires trusted local filesystem,
Git, Python subprocess, worker-thread, and materialized backend behavior; these
capability flags are a fail-closed compatibility boundary, not a permission
grant.

The distributable surface is pinned to 67 files: 63 runtime files derived from
the static relative-require closure plus the two dynamic workers and Python
bootstrap, and four public metadata/assets (`LICENSE`, `README.md`, `package.json`,
`icon.png`). The packaged license text must canonically match the repository
authority. `tests/**`, `docs/**`, internal governance journals, caches,
coverage, logs, environment files, credential-container suffixes, dependencies,
editor files, prior VSIX files, and `.vscodeignore` do not cross the package
boundary. The release group runs the deterministic installed-VSCE listing
twice; the default fast tier performs static validation only.
The listed regular-file closure is additionally capped at 1 MiB raw. Git
attributes materialize all 66 text entries as LF on every host and keep the PNG
binary. `reddog_package_surface_receipt.v2` emits file/byte/cap fields plus the
governing effective EOL-policy digest, sorted member-content digest, LF mode,
and text/binary counts. CR bytes or an effective attribute override fail before
receipt emission. The observed raw
total is not a final compressed-VSIX size claim; archive size is verified when
the release artifact is actually built.

`renderHtml()` receives `webview.cspSource` plus a fresh 128-bit nonce created
for each panel. Its deny-by-default CSP admits the packaged icon, inline
VS Code-theme CSS, and only the nonce-bearing inline script. The webview has no
network or arbitrary script source. Inline CSS remains an explicit bounded
compatibility exception pending the WSP_62 UI extraction.

`governed_git_executable.js` is the sole production Git process authority.
Its internal binding retains canonical absolute paths solely for invocation and
revalidation. `toPublicExecutableReceipt()` removes both Git and verifier paths
before any serialized boundary. Readiness v2 and projection-receipt v2 expose
only canonical-path digests, SHA-256,
size, start/final portable/native identities, and signature proof. Windows
readiness requires Valid Authenticode from an identity/hash-bound fixed-
SystemRoot PowerShell verifier; its public proof retains only verifier path/root
digests, fixed-relative-path and containment proof, hash/size, and complete
identities. Other platforms expose exactly `status: not_applicable`.
Configuration and content calls use the same internal absolute binding with
PATH/Path/PATHEXT removed and revalidate before output release. Start Operations
consumes the JS-minted repository-state v2 receipt; Python does not resolve or
execute Git. This proves the selected executable only, not Git DLL/helper
closure or independent authentication of the unhashed receipt origin.

It is the IDE-side thin-client surface for the resident RedDog backend and the OpenClaw/WRE/Hermes execution spine. The extension submits typed intent and displays receipts; it does not grant shell, repository write, merge, FoundUp registration, or CABR authority.

The VSIX is the IDE-side thin client. RedDog is the fast interaction/exchange
surface; 0102 is the resident FoundUps Digital Twin and deep architect layer.
Fusion is one internal reasoning mode, not the product identity.

For version-by-version provenance, generated closure pins, and migration history, see
`ModLog.md`. Current behavior is specified by the contracts below.

The extension-pinned backend manifest is validated before target extraction, HoloIndex lookup, model execution, permission probing, or work-order creation.
Compatibility failure is local and fail-closed; it does not trigger repair,
re-indexing, provider access, or work dispatch.

## RedDog and the Recursive 0102 DAE Ecosystem

012 does not orchestrate every worker. 012 talks to RedDog, which exchanges
bounded intent and context with the deeper 0102 layer. Autonomous WRE/DAE
agents perform bounded system work under OpenClaw supervision and WRE authority;
Hermes receives bounded leaf jobs.

### Architecture Stack

```text
012 work focus
  -> RedDog fast interaction / exchange surface
  -> 0102 digital twin / architect layer
  -> recursive 0102 DAE ecosystem
```

### Layer Roles

| Layer | Role |
| --- | --- |
| RedDog | Lightweight low-latency interaction, exchange, and attention surface; 012's first contact point. |
| 0102 | Principal-scoped Digital Twin, architect, and deep cognition/orchestration layer. |
| Hermes | Bounded delegated leaf-worker/scaffolding runtime. Not conversation, policy, repository, or promotion authority. |
| OpenClaw | Channel gateway and policy/control supervisor for admitted work. |
| HoloIndex | Memory and retrieval. |
| Skillz/Rolodex | Capability catalog. |
| Autonomous WRE/DAE agents | Code, docs, tests, ops, promotion, FoundUps launch. |
| Sentinels | Critique, truth, drift, regression review. Review only, no execution. |
| WRE | Work decomposition, repo/process authority, verification, dispatch, and recursive learning. |
| CABR/pAVS | Benefit validation, routing, reputation. |
| 012 | Work focus, testing, sovereign authorization, override. |

### Autonomy Boundary

Autonomous WRE/DAE agents are NOT 012 work. 012 provides work focus, testing, sovereign approval, and override. 0102 DAEs communicate recursively and perform bounded autonomous work.

## Authority Boundary

| Capability | Status | Boundary |
|---|---|---|
| Advisory model review | YES | OpenRouter request after Fusion redaction gate passes |
| Bounded repo context | YES | Extension auto-gathers WSP/HoloIndex/editor/git/Skillz context by reasoning tier and sends it through redaction gate |
| HoloIndex recall | YES | One governed owner adapter supplies current generation-bound semantic evidence or a bounded lexical/direct-read bundle. The extension does not invoke raw `holo_index.py --bundle-json`/`--offline`; lexical mode remains diagnostic-only and semantic authority fails closed. |
| Repository audit fallback | YES, READ-ONLY | Generation-bound semantic recall remains authoritative; structured Holo candidates must also survive secure direct read. Missing source or independent test/contract evidence triggers bounded deterministic discovery, never shell/model paths, writes, or execution authority. |
| WSP_00/WSP_97/WSP_15 prompting | YES | System prompt requires role lock, truth labels, proposed fixes, and MPS priority |
| Repo edits | NO | No write tool exposed to model |
| Shell execution by model | NO | Extension host runs only bounded local context/bridge commands; model cannot execute Skillz/OpenClaw/Hermes |
| WRE operational spine dry-run preview | YES | Copy MD/review packet metadata only; no Python spine call, worktree create, task execution, OpenClaw enqueue, Hermes dispatch, PR, push, merge, or repo mutation |
| Merge/PR authority | NO | Advisory output only |
| CABR/payout/source authority | NO | Blocked by Fusion redaction gate and prompt contract |
| pfMALL integration | SPECIFIED_NOT_IMPLEMENTED | Roadmap only |
| FoundUps onboarding automation | SPECIFIED_NOT_IMPLEMENTED | Roadmap only; WSP_109 packet production is not implemented here |

For a detected repository/module audit, the structured bundle returns `repo_audit_grounding.v1` with canonical entity/aliases, evidence references, deterministic candidates, selected path/digest/category records, exclusions, agreement, and coverage truth. Selected content reaches the model only through governed direct-read hits and protected target packing. Missing receipt, incomplete coverage, or post-pack source/test non-vacuity failure returns `codebase_audit_evidence_incomplete` before network access.

Schema repair preserves the primary result and exact primary Fusion `review_packet`; repair provenance is a sibling `schema_repair_telemetry` object. A repair cannot mint or overwrite quorum evidence. Cybersecurity critic prompts are defensive-only, and empty/`None` panel outputs are abstentions.

## F0 Safety Boundary

F0 is the foundation Foundups-Agent repo. RedDog must never mutate F0 directly from the extension thin client.

The extension may gather bounded context and produce advisory review packets. It must not execute model-generated code, install packages, create persistence, write files, mutate repositories, publish artifacts, or call Skillz/OpenClaw/Hermes/WRE execution surfaces directly. Any future execution path must be a governed handoff where WRE retains repo/process authority and 012 remains sovereign for test, land, publish, and override decisions.

External repositories are assessed through advisory WSP intake before they can become FoundUps candidates. The extension can recommend a FoundUps intake packet and integration risk report; it cannot automatically enroll or mutate an external repo.

## Governed Repo Work Order Contract

RedDog is the interaction interface to the 0102 architect layer - **not an authority owner**. A governed RedDog-mediated operation may receive **bounded delegated capability for one work order after fresh verification**; the surface itself does not "have authority."

| Artifact | Location |
|---|---|
| Authority contract + schema | `docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md` |
| Slice queue | `extensions/reddog/ROADMAP.md` |

**Dry-run validator (no mutation):** `modules/communication/moltbot_bridge/src/reddog_governed_work_order_dryrun.py` - validates envelope + HoloIndex evidence packet; returns `WOULD_ACCEPT` / `WOULD_REJECT` / `WOULD_ACCEPT_WITH_RETRIEVAL_GAP`. Extension v0.3.27 does not invoke it yet.

**Permission probe (read-only):** `modules/platform_integration/github_integration/src/reddog_github_permission_probe.py` -- `probe_repo_permission()` produces fresh `repo_permission_snapshot` evidence. Extension v0.3.53 invokes it through `scripts/reddog_github_permission_probe_once.py` for read-only permission evidence only.

**OpenClaw policy gate (no execution):** `modules/communication/moltbot_bridge/src/reddog_openclaw_work_order_policy_gate.py` - `evaluate_work_order_policy_gate()` composes dry-run + permission freshness + HoloIndex policy; returns `PolicyGateReceipt`. Extension does not invoke it yet.

**Work-order receipt (Hermes-compatible audit):** `modules/communication/moltbot_bridge/src/reddog_work_order_receipt.py` - `emit_work_order_receipt()` persists/emits pre-execution audit records from `PolicyGateReceipt`. Extension does not invoke it yet.

**Runtime invocation dry-run:** `modules/communication/moltbot_bridge/src/reddog_work_order_runtime_invocation.py` - `invoke_reddog_work_order_dryrun()` chains policy gate + receipt; returns audit result. Extension does not invoke it yet.

**WRE isolated worktree executor (contract only):** `docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md` - defines future executor cage; **no implementation**.

**WRE executor dry-run planner:** `modules/communication/moltbot_bridge/src/reddog_wre_executor_dryrun.py` - `plan_wre_isolated_worktree_execution_dryrun()`; plan + phase receipts; **no git/worktree mutation**.

**OpenClaw handoff adapter (contract only):** `docs/audits/architecture/REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md` - RedDog -> FoundUpsJob mapping; OpenClaw owns worker loop; **AssignmentDispatcher not canonical**.

**WRE execution valve:** `modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py` -- `evaluate_reddog_execution_valve()`; default `VALVE_CLOSED`; pure evaluation only. Contract: `docs/audits/architecture/REDDOG_WRE_EXECUTION_VALVE_CONTRACT_PHASE1.md`.

**OpenClaw adapter dry-run:** `modules/communication/moltbot_bridge/src/reddog_openclaw_adapter_dryrun.py` -- `plan_reddog_openclaw_adapter_dryrun()`; proposes FoundUpsJob / `autonomous_task` intake only; **no enqueue**. Contract: `docs/audits/architecture/REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_CONTRACT_PHASE1.md`.

**OpenClaw live enqueue contract:** `docs/audits/architecture/REDDOG_OPENCLAW_LIVE_ENQUEUE_CONTRACT_PHASE1.md` -- future conversion from proposed FoundUpsJob / `autonomous_task` intake to live queue item. Requires future `VALVE_OPEN_LIVE_ENQUEUE`, accepted signed work authority, and signed receipt-chain verification. Contract only; no live enqueue in this slice.

**WRE operational spine dry-run preview (extension v0.3.46):** `buildWreOperationalSpineDryRunPreview()` emits `review_packet.wre_operational_spine_dryrun_preview` and Copy MD section `## WRE Operational Spine Dry-Run Preview`. It references `modules/communication/moltbot_bridge/src/reddog_wre_operational_spine.py::run_reddog_wre_worktree_create_spine` as a future call target only. The extension does **not** invoke Python for this preview and records `python_invocation_performed=false`, `wre_spine_invoked=false`, `worktree_create_performed=false`, `task_execution_performed=false`, `openclaw_enqueue_performed=false`, `hermes_dispatch_performed=false`, `pr_created=false`, and `merge_performed=false`. Future live use requires `VALVE_OPEN_WORKTREE_CREATE` and `012_sovereign`.

**Governed work-order candidate emission (extension v0.3.49):** `buildRedDogGovernedWorkOrderCandidate()` emits a full `RedDogGovernedWorkOrder` candidate inside the WRE dry-run preview and Copy MD section `## RedDog Governed Work Order Candidate`. It binds extension version, work-focus digest, WSP prompt digest, HoloIndex evidence posture, derived path scope, nonce, expiry, rollback plan, and safe advisory source digests. The candidate is explicitly not invocation-ready unless a later slice supplies a fresh permission snapshot, signed work authority, and explicit worktree valve request. No Python invocation, worktree create, task execution, OpenClaw enqueue, Hermes dispatch, PR, push, merge, or reward settlement is performed by this emission slice.

**Permission/signature binding (extension v0.3.50):** `buildRedDogGovernedWorkOrderCandidate()` now emits `permission_binding` and `signed_authority_binding` metadata. A candidate is `ready_for_wre_invocation=true` only when a supplied permission snapshot is fresh/trusted, a supplied signed-authority verifier result is accepted for the same `work_order_id`, path scope exists, and `explicitValveRequested=true`. The extension does not perform the GitHub probe, signature verification, signing, Python/WRE invocation, worktree create, OpenClaw enqueue, Hermes dispatch, PR, push, merge, or reward settlement in this slice.

**WRE operational-spine runtime wire (extension v0.3.51):** `invokeWreOperationalSpineExplicitValveBridge()` and `scripts/reddog_extension_wre_spine_invoke_once.py` provide the extension-side seam into `reddog_extension_wre_operational_spine_invoke.py`. Default RedDog runs emit a skipped invoke result and do not call Python. The bridge invokes Python only when explicit invoke metadata, a ready governed work-order candidate, a sovereign wardrobe-selection receipt, a valve environment, a permission snapshot, and an accepted signed-authority result are all supplied. The bridge passes authority metadata through stdin, not argv, and still stops at the WRE worktree-create spine boundary: no task execution, file edits, OpenClaw enqueue, Hermes dispatch, PR, merge, or reward settlement.

**Operator wardrobe-selection runtime bridge (extension v0.3.52):** `runOperatorWardrobeSelectionBridge()` and `scripts/reddog_operator_wardrobe_selection_once.py` call the deterministic operator-loop wardrobe-selection dry-run and emit a no-execution/no-enqueue `RedDogOperatorLoopWardrobeSelectionReceipt` into review packets and Copy MD section `## RedDog Operator Wardrobe Selection`. The receipt is supplied to `invokeWreOperationalSpineExplicitValveBridge()` as `selection_receipt`. The extension still does not sign, probe permissions, run tasks, create worktrees, enqueue OpenClaw, dispatch Hermes, push PRs, merge, settle rewards, or mutate HoloIndex.

**GitHub permission-probe runtime bridge (extension v0.3.53):** `runGithubPermissionProbeBridge()` and `scripts/reddog_github_permission_probe_once.py` call the existing read-only `probe_repo_permission()` surface and emit a fresh `repo_permission_snapshot` into review packets and Copy MD section `## RedDog GitHub Permission Probe`. The snapshot is supplied to `buildWreOperationalSpineDryRunPreview()` so the governed work-order candidate can mark `permission_binding` as OBSERVED when the probe returns a trusted fresh permission. The extension still does not sign, run tasks, create worktrees, enqueue OpenClaw, dispatch Hermes, push PRs, merge, settle rewards, or mutate HoloIndex.

**Judgment generation verifier wiring (extension v0.3.47):** when a work focus contains a top-level `Determine:` numbered list, `constructWspTaskPrompt()` instructs RedDog to emit a canonical `## Determine Answers` fenced JSON block. After any schema repair, `runJudgmentVerifier()` invokes `scripts/reddog_judgment_verifier_once.py`, which reuses `reddog_adversarial_verifier_panel.verify_answer_set()` against already-fetched direct-read hit bodies and the HoloIndex scorecard. The verifier is deterministic/local only: no HoloIndex re-index, WRE enqueue, shell, repo mutation, OpenClaw/Hermes dispatch, or network call. Run Trace / Copy MD expose `judgment_verifier_applied`, `judgment_verifier_verified`, verified/refuted/NEEDS_VERIFICATION counts, support-note counts, and advisory `index_gap_event` metadata.

**Specified flow (not implemented in extension v0.3.27):**

```text
authenticated principal -> GitHub permission snapshot -> RedDogGovernedWorkOrder
  -> OpenClaw policy gate -> Hermes lifecycle/receipts
  -> WRE isolated worktree (branch, tests, PR draft)
  -> Sentinel/reviewer opinions (review only)
  -> merge gate (012/operator sovereign valve on F0)
```

**WSP Applicability Preflight (specified):** before any future work-order emission, identify applicable WSPs (WSP_34, WSP_50, WSP_54, WSP_95, WSP_97, WSP_109) and Skillz candidates from HoloIndex; attach evidence refs; block if recall is weak.

**F0 autonomous merge:** SPECIFIED_NOT_IMPLEMENTED - not planned behavior until dryrun, permission probe, OpenClaw envelope gate, WRE executor, and review receipts land.

## Webview Contract

The UI copies the VS Code terminal/chat layout:

1. Header: build/model metadata only.
2. Output scrollback: status, 012 work focus, 0102 output, validation errors, and errors.
3. Working Tail / RedDog action strip (above controls).
4. Control row: **0102 Role**, routing/context pills, tests, Copy MD.
5. Bottom composer: fixed **012 work focus** input.

The output pane owns scrolling. Content must not pass behind the composer.

Keyboard:

- `Enter`: send work focus.
- `Shift+Enter`: newline.
- `Ctrl+Shift+C`: copy redacted review packet.

Copy:

- `Copy MD`: copies a markdown packet with `Run Trace` (extension_version, role, tier, effort, mode, models, context, redaction, validation), `Work Trail` (allowlisted normalized events, cap 50), and 0102 output.
- Run Trace build-version field (REDDOG_RUN_TRACE_BUILD_VERSION_FIELD_PHASE1, v0.3.37): the `## Run Trace` block emits `- extension_version: <EXTENSION_VERSION>` near the top (after the header, before role/tier). It reads the real installed-build `EXTENSION_VERSION` constant, NOT any prompt/packet/model value, so build staleness is machine-checkable from telemetry and never masked by model output. 012/tooling gates build staleness on this field, not on model text.
- Redaction-block runs include `## Redaction Gate Report` (`BLOCKED_LOCALLY`, WSP_97 truth labels, no raw snippets) before any model output.
- Validation-failure runs include `OUTPUT_VALIDATION_FAILED` with local static footer (no extra network call).
- Substantive tasks include `## Governed Handoff Recommendation` (`advisory_only`; bounded digest evidence refs only). Non-blocked substantive packets also include `## WRE Operational Spine Dry-Run Preview` (metadata only; no invocation).
- Status/progress scrollback lines are summarized in Run Trace / Work Trail; raw status lines are not duplicated verbatim unless needed for trace fields.

## 0102 Roles

| 0102 Role | Intended Use |
|---|---|
| RedDog Architect | Default architecture review and FoundUps intake/orchestration reasoning |
| WSP Gate Critic | Gate reports, return-to-author findings, WSP_97 critique |
| Repair Planner | Smallest valid implementation and test-slice planning |
| Smoke Test | Bounded API/bridge checks without broad architecture review |

## Model Modes

| Mode | Traceability | Notes |
|---|---|---|
| FoundUps manual lead + panel | Higher | Stores lead, panel, and synthesis excerpts in review packet |
| OpenRouter Fusion alias | Lower | Black-box Fusion synthesis; individual critic transcripts are not exposed |
| Regular OpenRouter | Single-model | Fast direct lead review |

## HoloIndex Truth Boundary

The model cannot access the filesystem. It receives only the bounded context packet.

Extension v0.4.10 adds bounded Fusion progress and OpenRouter usage/routing receipts. Extension v0.4.9 makes a complete named-subsystem evidence corpus authoritative for the core of a focused repository deep dive. At most two off-anchor generation-bound semantic dependencies may enter when their evidence text names the focus; unrelated hits are excluded. Focus strategy, cross-cutting paths, and manifest completeness are explicit in the Run Trace.

If HoloIndex recall reports zero WSP hits, missing Tier-0 docs, stale/offline fallback, or unavailable output, the answer must treat protocol claims as `NEEDS_VERIFICATION` and propose retrieval/index repair before strong claims.

Run Trace HoloIndex scorecard fields (v0.3.22+):

| Field | Meaning | WSP_97 |
| --- | --- | --- |
| `holoindex_status` | Bundle transport result (e.g. `bundle_json_ok`) | OBSERVED |
| `code_hits_count` | Count of code hits returned | OBSERVED |
| `target_recall_ok` | Requested target file/symbol appeared in hits (never `unknown` when a required list exists) | OBSERVED |
| `index_gap_detected` | Target-specific miss (true whenever `required_targets_missing` is non-empty, even when `code_hits_count > 0`) | OBSERVED |
| `required_targets_total` | Count of paths parsed from an explicit "Required direct-read targets" prompt list (0 = none present) | OBSERVED |
| `required_targets_recalled` | Required targets whose content-bearing path appeared in the bundle (self-file `extension.js` excluded) | OBSERVED |
| `required_targets_missing` | Required target paths absent from content (drives `index_gap_detected`) | OBSERVED |
| `work_focus_targets_derived` | At least one required target was DERIVED from free-form work-focus prose / M2M / Read-first shapes, not only the explicit header (v0.3.44+) | OBSERVED |
| `work_focus_target_derivation_sources` | Which read-intent shapes contributed targets: subset of `{required_block, read_first, m2m_read, ctx_files, markdown_bullet, inline_path, backtick_path, symbol}` (v0.3.44+) | OBSERVED |
| `work_focus_targets_dropped_low_confidence` | Flowing-prose tokens dropped from the required list because they had a slash but NO file extension (e.g. `breadcrumb/handoff`); EXCLUDED from `required_targets_total` / `_missing` so they cannot flip `target_recall_ok` (v0.3.45+; `[]` when none) | OBSERVED |
| `direct_read_fallback_used` | The governed owner bundle contains accepted non-empty direct-read paths and bytes | OBSERVED |
| `direct_read_paths` | Repo-relative target paths actually fetched by the Python bundle layer | OBSERVED |
| `direct_read_rejected` | `{path, reason}` for denied/traversal/absolute/secret/symlink-escape hits (never read) | OBSERVED |
| `direct_read_bytes` | Total bytes injected across all fetched targets (bounded by total budget) | OBSERVED |
| `direct_read_truncated` | `{path, bytes}` for targets clipped by the per-file byte cap | OBSERVED |
| `direct_read_fetch_attempted` | The governed owner bundle supplied direct-read evidence, or bounded missing-target enrichment was requested (v0.3.33+) | OBSERVED |
| `direct_read_fetch_error` | Classified fetch failure (`timeout`, `max_buffer`, `process_error`, `unknown`, or none) | OBSERVED |
| `audit_context_requested` | Extension requested audit-mode redaction for governance direct-read context (v0.3.34+) | OBSERVED |
| `audit_context_applied` | Bridge passed `audit_mode=True` into `evaluate_redaction_gate()` (v0.3.34+) | OBSERVED |
| `required_targets_in_model_context` | Required targets in the authoritative packed set whose OWN fenced section survived the 42K cut (v0.3.35+; v0.3.39+ uses structured `included_paths`, NOT marker reparse of merged text) | OBSERVED |
| `required_targets_context_total` | Count of path-form required targets eligible for the model-context proof (v0.3.35+) | OBSERVED |
| `required_targets_context_chars` | Total chars of required-target excerpts surviving in the final context (v0.3.35+) | OBSERVED |
| `required_targets_context_missing` | Required target paths never packed OR whose authoritative section did NOT survive the 42K cut (v0.3.35+; v0.3.39+ unforgeable -- phantom body markers cannot flip to present) | OBSERVED |
| `required_targets_context_truncated` | `{path, chars}` for required-target excerpts bounded by the per-target budget (v0.3.35+) | OBSERVED |
| `required_targets_redaction_checked` | Required-target sections evaluated INDEPENDENTLY by the audit-mode per-target redaction gate (v0.3.38+; 0 on non-audit / no-marker path) | OBSERVED |
| `required_targets_redaction_passed` | Required targets that passed per-target redaction and survived into the reassembled model context (v0.3.38+) | OBSERVED |
| `required_targets_redaction_blocked` | Required targets OMITTED because a section triggered a non-audit-structural hard block (body replaced with a notice; secrets never reach the model) (v0.3.38+) | OBSERVED |
| `required_targets_redaction_blocked_paths` | Repo-relative paths of the omitted required targets (v0.3.38+; `[]` when none blocked) | OBSERVED |
| `required_targets_redaction_blocked_reasons` | BLOCK category names that caused each omission (counts-only; e.g. `private_reasoning`) (v0.3.38+) | OBSERVED |
| `target_content_paths` | Relative paths whose snippets were included | OBSERVED |
| `target_content_chars` | Character count of included target snippets | OBSERVED |
| `target_content_omitted_reason` | Why snippets omitted when `target_content_included=false` | OBSERVED |
| `target_content_truncated` | Any target snippet truncated by per-file budget | OBSERVED |
| `target_content_sanitized` | Block-triggering literals replaced before egress | OBSERVED |
| `target_content_sanitized_categories` | Fusion BLOCK categories sanitized (metadata only) | OBSERVED |

Run Trace Unicode normalization fields (v0.3.24+) and bridge UTF-8 invariant (v0.3.25+):

| Field | Meaning | WSP_97 |
|---|---|---|
| `unicode_normalization_applied` | Bridge payload required surrogate replacement before gate | OBSERVED |
| `unicode_replacements_count` | Count of isolated surrogate replacements (counts only) | OBSERVED |
| `unicode_normalization_sources` | Pipe-separated: `prompt`, `context`, `repair_prompt` | OBSERVED |
| `unicode_normalization_form` | `NFC` when normalization ran; `none` when skipped | OBSERVED |

Bridge child env (v0.4.101+): every route uses a closed profile and forces
`PYTHONIOENCODING=utf-8` plus `PYTHONUTF8=1`. Common isolated profiles also set
`PYTHONNOUSERSITE=1`; local `holo_query` deliberately removes it because the
current configured/system interpreter requires per-user NumPy. That route still
denies `PYTHONPATH`, `PYTHONHOME`, `PYTHONSTARTUP`, and credentials. Universal
user-site isolation requires a sealed/configured Holo interpreter closure.
Python
bridge reads stdin via `sys.stdin.buffer` UTF-8 decode so valid Unicode (e.g.
U+2014 em dash) is not mis-decoded on Windows before the redaction gate.

`evaluateTargetRecall(taskText, bundleOutput)` and `inferRecallTargetPaths(taskText)` implement target-specific recall from bundle `task_retrieval.code_hits`. Path-aware detector (REDDOG_TARGET_RECALL_PATH_AWARE_PHASE1, slice 1/3): when the prompt carries an explicit "Required direct-read targets" list, `parseRequiredTargetPaths(taskText)` parses it into repo-relative paths/globs and `evaluateTargetRecall` compares each required path against content-bearing bundle locations, using `isSelfFileLocation()` so retrieving `extension.js` (RedDog itself) can never satisfy a required target. This closes the `content_included(any file) != required_targets_recalled` false negative: `index_gap_detected` is honestly `true` when required targets are absent. Prompts without a required list keep prior inferred-target behavior. This slice is detector-only: it does NOT read required files (slice 2) or change redaction (slice 3).

Free-form work-focus target derivation (REDDOG_WORK_FOCUS_TARGET_DERIVATION_PHASE1, v0.3.44): 012 frequently names repo targets in free-form prose, WSP_99 M2M packets, or "Read first" sections rather than under the exact `Required direct-read targets:` header, which left the whole direct-read stack dormant (`required_targets_total: 0`, `direct_read_fetch_attempted: false`) even though real paths were named. `collectRequiredTargets(taskText)` now MERGES the explicit-header list (from `parseRequiredTargetPaths`, byte-identical for the header-only shape and kept FIRST) with `deriveWorkFocusTargets(taskText)`, de-duplicated case-insensitively in first-seen order. `deriveWorkFocusTargets` recognizes these read-intent shapes: (2) `Read first:` / `READ BEFORE EDITING` blocks, (3) WSP_99 M2M `READ:` arrays, (4) M2M `CTX.FILES` / `CTX: FILES:` arrays, (5) markdown bullet lists of repo paths, (6) inline repo paths in prose, (7) backticked repo paths, and (8) existing `symbol:` targets (preserved verbatim; symbols are not path-fetchable, left for recall). `evaluateTargetRecall` and `buildBoundedRepoContext` both consume the MERGED list, so a derived path makes `required_targets_total > 0`, drives the SAME governed direct-read fetch, and is packed/proven exactly like a header target. HoloIndex semantic miss never suppresses direct-read for a named path. Two false-positive guards: (A) inline/prose extraction uses a bounded, anchored, ReDoS-safe path-TOKEN regex (`WORK_FOCUS_PATH_TOKEN_RE`; a slash-less token requires a LOWERCASE file extension, so acronyms/M2M keys like `CTX.FILES` are not captured, and surrounding prose words are never swept in); (B) command/validation fences (```powershell / ```bash carrying `git diff --check`, `node --check`, `python holo_index.py ...`, `rg ...`) and scope-out / `Do NOT touch` / `OUT OF SCOPE` sections are EXCLUDED, and ambiguous read-intent prefers precision (no derivation) so an over-derived wrong path cannot inflate `required_targets_missing`. Denied paths (`.env`, traversal, secret-like) are still EMITTED honestly by the deriver and REJECTED by the unchanged Python direct-read gate (`bundle_json.py`) -- the gate remains the enforcement boundary; derivation never weakens the denylist / traversal protection / byte budgets / redaction. New telemetry: `work_focus_targets_derived` + `work_focus_target_derivation_sources`. Exported helpers: `deriveWorkFocusTargets`, `collectRequiredTargets`, `extractInlinePathTokens`, `extractM2mArrayTargets`. HoloIndex anchor terms: `RedDog work focus target derivation`, `deriveWorkFocusTargets read first M2M CTX.FILES`, `collectRequiredTargets merged required list`, `free-form direct-read target promotion`. Follow-up if not indexed: `HOLOINDEX_REDDOG_WORK_FOCUS_TARGET_DERIVATION_INDEX_GAP_PHASE1` (SPECIFIED_NOT_IMPLEMENTED -- no ranking/reindex code changed here).

Flowing-prose read-capture tokenization + tiered strictness (REDDOG_WORK_FOCUS_READ_CAPTURE_PROSE_TOKENIZATION_PHASE1, v0.3.45): a real 0.3.44 run on a FLOWING-PROSE `Read first:` prompt (three files named in one sentence, with a period+prose after `breadcrumb_tracer.py` and the phrase `and the breadcrumb/handoff layer`) reported `target_recall_ok: false` because the read-capture branch tokenized the prose line with the COMMA-splitter (`extractTargetTokensFromLine`): the splitter glued trailing prose onto the path (`breadcrumb_tracer.py. Determine ...` -> `not_a_file`) and captured an embedded-slash English fragment whole (`and the breadcrumb/handoff layer` -> garbage target), so `required_targets_total=4 / recalled=2`. The three fixes: (A) the NON-bullet read-capture branch now tokenizes with the bounded path-TOKEN regex (`extractInlinePathTokens` via `extractProsePathTokens`) instead of the comma-splitter, isolating clean path substrings from surrounding prose; CLEAN BULLETS (`stripListMarker(...).isList`) keep the comma/`or`-splitter so the intentional `a / b / c` alternatives shape is preserved. (B) Tiered confidence: FLOWING-PROSE-derived tokens (read-first prose + source-6 inline + source-7 backtick) are LOW-confidence and become required targets ONLY when they normalize to a FILE SHAPE (a lowercase file extension); a prose token with a slash but no extension is NOT required -- it is dropped and reported in `work_focus_targets_dropped_low_confidence`, and EXCLUDED from `required_targets_total` / `required_targets_missing` so it cannot flip `target_recall_ok`. The explicit "Required direct-read targets" header, M2M `READ:`, M2M `CTX.FILES`, and CLEAN BULLETS keep the broader slash-OR-extension tier (an intentionally-named directory path is still accepted); only flowing prose is stricter. (C) `normalizeTargetPath` trailing-punctuation trim adds `}` to the existing set (`.` `,` `;` `:` `)` `]`), so `.../breadcrumb_tracer.py.` -> `.../breadcrumb_tracer.py`. `extractProsePathTokens(line)` returns `{ accepted, dropped }` and REUSES `extractInlinePathTokens` (same bounded ReDoS-safe regex + self-file guard); no new backtracking regex was introduced. The governed direct-read gate (`bundle_json.py`) is unchanged; derived paths still flow through it. New telemetry: `work_focus_targets_dropped_low_confidence`. New exported helper: `extractProsePathTokens`.

Target content egress (v0.3.22+): `buildTargetRecallContentSection(root, taskText, maxChars)` reads workspace-confined snippets for inferred recall targets after HoloIndex path ranking. Snippets pass through `sanitizeTargetSnippetForRedaction()` before inclusion (ADDENDUM F); placeholders use neutral `[SANITIZED_BLOCK:NN]` tokens so category names do not re-trigger the Fusion gate. Legacy target-content telemetry reflects the bounded context string assembled by `buildBoundedRepoContext` before the 42000-char slice; the v0.3.35 `required_targets_in_model_context` proof fields are the exception -- they are computed AFTER the final slice from the surviving markers. `buildWsp97ProtocolExcerpt(root, maxChars)` adds a bounded WSP_97 protocol excerpt when the task mentions WSP_97 or truth labels.

Governed direct-read-by-path (REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1, slice 2/3): when slice-1's detector reports `index_gap_detected=true` with a non-empty `required_targets_missing`, `holoIndexOutput` re-invokes the bundle with `buildMustIncludeArgs(missing)` -> `--bundle-must-include <path>` so the **Python bundle layer** (`holo_index/cli/commands/bundle_json.py::_direct_read_fetch`) reads the named repo files and returns their content in the bundle. The extension does NOT read those files via raw fs; it only names the paths. Fetched hits are spliced into `task_retrieval.code_hits` (so slice-1 recall re-evaluates and flips `target_recall_ok`) and rendered by `buildDirectReadContentSection(bundleOutput)` into a bounded section. Hard security allowlist (all in the Python layer): repo-relative only; realpath must stay inside repo root (rejects absolute, `..` traversal, symlink-escape); hard-deny basenames/globs (`.env*`, `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `*.p12`, `*.keystore`, `*secret*`/`*credential*`/`*token*`, `.git/` and credential dot-dirs); per-file byte cap (12KB) plus a total fetch budget (96KB) spread across MANY targets ranked by prompt order; every denial is recorded in `direct_read_rejected` and never aborts the bundle. Fetched content passes through the EXISTING redaction gate unchanged (slice 3 owns audit-mode redaction). No execution authority, no write path, no shell-out.

Exported helpers for contract tests: `isTargetReadPathDenied`, `resolveSafeRepoFile`, `readBoundedTargetSnippet`, `readBoundedTargetSnippets`, `buildTargetRecallContentSection`, `sanitizeTargetSnippetForRedaction`, `taskMentionsWsp97`, `buildWsp97ProtocolExcerpt`, `parseRequiredTargetPaths`, `deriveWorkFocusTargets`, `collectRequiredTargets`, `extractInlinePathTokens`, `extractM2mArrayTargets`, `isSelfFileLocation`, `requiredTargetMatchesLocation`, `formatHoloIndexScorecardLines`, `buildMustIncludeArgs`, `buildDirectReadContentSection`, `buildRequiredTargetProtectedSection`, `assembleFinalBoundedContext`, `computeRequiredTargetContextProof`, `requiredTargetSectionSurvived`, `neutralizeRequiredTargetMarker`.

Audit-context bridge wire (REDDOG_AUDIT_CONTEXT_BRIDGE_WIRE_PHASE1, v0.3.34): when `buildDirectReadContentSection()` sets `audit_context: true` (governance direct-read fetch), `buildBoundedRepoContext()` preserves the flag; `callFusion()` sends `audit_context: true` in the bridge stdin payload; `scripts/advisory_model_once.py` passes `audit_mode=True` into `evaluate_redaction_gate()` **only** when explicitly requested. Default path (no governance direct-read) remains byte-identical strict blocking. HoloIndex anchor terms: `audit_context bridge wire`, `advisory_model_once audit_mode`, `buildDirectReadContentSection audit_context`, `fusion_redaction_gate audit_mode`, `RedDog golden FoundUps creation audit`. Follow-up if not indexed: `HOLOINDEX_REDDOG_AUDIT_CONTEXT_BRIDGE_WIRE_INDEX_GAP_PHASE1`.

Required-target context packing (REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_PHASE1, v0.3.35): the FINAL bounded context is capped at `BOUNDED_CONTEXT_MAX_CHARS` (42000) by a single tail slice. Before this slice, `buildBoundedRepoContext()` split assembly into a fixed head (WSP contract + `BOUNDED_REPO_CONTEXT` preamble) and lower-priority sections (HoloIndex raw JSON blob, direct-read section, target-recall self-file snippet, Skillz, git diff). When a prompt carries an explicit "Required direct-read targets" list AND the governed fetch succeeded (`direct_read_fallback_used`), `buildRequiredTargetProtectedSection(requiredTargets, directReadSection)` renders each required target from the ALREADY-FETCHED direct-read hit content (no new fs read) with the STABLE marker `### Required direct-read target: <path>` (see `REQUIRED_TARGET_MARKER_PREFIX`), under a per-target minimum-first budget (min 1800 / max 6000 chars, protected total 30000). `assembleFinalBoundedContext(head, protected, lower)` packs the protected block FIRST so the lower-priority sections yield to the 42K cut, never the required-target excerpts; the self-file `extension.js` target-recall snippet is DEMOTED/OMITTED in explicit-target audit mode and can never precede the required-target markers. `computeRequiredTargetContextProof(finalText, requiredTargets, protectedMeta)` computes the `required_targets_in_model_context` / `required_targets_context_missing` / `required_targets_context_chars` / `required_targets_context_truncated` fields by scanning the FINAL post-cut context for the markers -- proof of model visibility, NOT fetch telemetry. Run Trace renders BOTH `required_targets_recalled` (fetched/available) and `required_targets_in_model_context` (model-visible); they are distinct layers. Prompts without a required list pack byte-identically and leave the proof fields `unknown`. Exported helpers: `buildRequiredTargetProtectedSection`, `assembleFinalBoundedContext`, `computeRequiredTargetContextProof`, `REQUIRED_TARGET_MARKER_PREFIX`, `BOUNDED_CONTEXT_MAX_CHARS`. HoloIndex anchor terms: `RedDog required target context packing`, `buildBoundedRepoContext 42000 slice`, `buildRequiredTargetProtectedSection`, `required_targets_in_model_context`, `assembleFinalBoundedContext protected required target`. Follow-up if not indexed: `HOLOINDEX_REDDOG_REQUIRED_TARGET_CONTEXT_PACKING_INDEX_GAP_PHASE1` (SPECIFIED_NOT_IMPLEMENTED -- no ranking/reindex code changed here).

Authoritative (unforgeable) required-target telemetry (REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1, v0.3.39; per-path dedup completion v0.3.40): before this slice the required-target telemetry was derived by REPARSING marker strings out of merged text, so file CONTENT could forge it -- `computeRequiredTargetContextProof` counted `text.indexOf(REQUIRED_TARGET_MARKER_PREFIX + target)` over the FINAL text (a phantom marker in a body flipped a never-fetched target from missing -> in_model_context), and Python `_isolate_required_targets` derived checked/passed/blocked + blocked_paths from marker-delimited SECTIONS (a body containing `### Required direct-read target: <path>` minted a PHANTOM section). This slice makes the telemetry AUTHORITATIVE. (1) The JS proof iterates the packer's STRUCTURED record `protectedInfo.included_paths` (the paths actually packed), NOT markers scanned from text; a requested target counts as in_model_context only when it is in the authoritative packed set AND its own fenced section survived the final cut (`requiredTargetSectionSurvived`). A phantom marker for a non-authoritative path is never counted; `required_targets_context_total` counts the requested path-form targets so a phantom cannot inflate the denominator. (2) Pack-time defense-in-depth: `neutralizeRequiredTargetMarker` inserts a zero-width WORD JOINER (U+2060) after the `### ` lead of any literal marker occurring INSIDE an excerpt body, so a target's content cannot mint a sibling marker (nor a phantom section for the Python splitter). (3) The JS packer threads its authoritative `included_paths` through the bridge payload (`required_target_paths`) -> `scripts/advisory_model_once.py` -> `evaluate_redaction_gate(..., required_target_paths=...)` -> `_isolate_required_targets(context, authoritative_paths)`; a marker-delimited section is treated as a required-target section only when its path is IN the authoritative list, so checked/passed/blocked/missing can never exceed the authoritative count and `required_targets_redaction_blocked_paths` is a subset of authoritative paths (phantom markers fold back as ordinary content, still redacted by the whole-context gate). (4) v0.3.40 per-path dedup completion -- the 0.3.39 JS neutralization protected only the packed EXCERPT bodies, but the LOWER sections (git diff, HoloIndex recall JSON, active editor) merged UN-neutralized into the same `gate_context` Python splits, so a MODIFIED required file whose OWN diff body contains its authoritative marker line rendered a SECOND marker section that normalized to an ALREADY-authoritative path -- checked/passed exceeded the authoritative count and a hard-block token in that diff body forged a `blocked_paths` entry for the clean protected section. The robust closure is Python per-path dedup in `_isolate_required_targets`: the FIRST marker for a normalized authoritative path (the real packed protected section, packed before any lower section) is authoritative; any LATER marker whose normalized path is already-consumed folds back as ordinary content, so each authoritative path is checked/passed/blocked AT MOST ONCE and the invariant HOLDS FOR REAL even with duplicate authoritative markers. Defense-in-depth: `neutralizeRequiredTargetMarker` now also wraps the git-diff / HoloIndex-recall / active-editor lower-section bodies before assembly. A JS threading contract assertion (MFH-J-006) pins the bridge payload line that sets `required_target_paths` from `bridgeMeta.required_targets_authoritative_paths` so a future edit cannot silently drop it (which would make Python receive None -> the forgeable fallback path at runtime). Identification only: no ACTION_BLOCK detector relaxed, `AUDIT_STRUCTURAL_CATEGORIES` untouched, the #917 one-blocked-sibling-survives content-safety fix preserved. Exported helpers: `requiredTargetSectionSurvived`, `neutralizeRequiredTargetMarker` (plus the existing packing helpers). HoloIndex anchor terms: `RedDog required target marker forgery hardening`, `authoritative required target telemetry`, `computeRequiredTargetContextProof included_paths`, `neutralizeRequiredTargetMarker`, `_isolate_required_targets authoritative_paths`. Follow-up if not indexed: `HOLOINDEX_REDDOG_MARKER_FORGERY_INDEX_GAP_PHASE1` (SPECIFIED_NOT_IMPLEMENTED -- no ranking/reindex code changed here).

All-section + legacy-path unforgeable required-target telemetry (REDDOG_REQUIRED_TARGET_MARKER_FORGERY_HARDENING_PHASE1, all-section + legacy-path closure v0.3.41): v0.3.39/v0.3.40 made the telemetry inert on the AUTHORITATIVE path (packProtected=true), but two vectors remained forgeable. VECTOR A (incomplete lower-section neutralization): `neutralizeRequiredTargetMarker` covered the HoloIndex recall blob, active-editor content, and git status/stat/diff bodies, but four raw file-body lower sections still pushed UN-neutralized content that could carry a literal `### Required direct-read target: <path>` marker minted from file CONTENT -- the target-recall section (`buildTargetRecallContentSection`), the WSP_97 excerpt (`buildWsp97ProtocolExcerpt`), the Skillz/Wardrobe/Rolodex discovery section (`skillzWardrobeRolodexContext` -> `readBoundedRepoFile`), and the plain direct-read section (`buildDirectReadContentSection`, reachable only when packProtected=false). Fix: EVERY `lowerSections.push(...)` in `buildBoundedRepoContext` now routes its body through `neutralizeRequiredTargetMarker`, so no file-body section can emit the literal marker prefix into the Python isolation splitter. VECTOR B (legacy None path): when `audit_context=true` but `packProtected=false` (direct-read code_hits present so audit_context true, but `direct_read_fallback_used` false so the packer emits `authoritativePacked=[]`), `scripts/advisory_model_once.py` collapsed the empty list to `None`, and `_isolate_required_targets(None)` is the LEGACY path where `authoritative_set` is None -> EVERY marker section (including content-minted phantoms) is checked/counted and could mint content-controlled `blocked_paths`. Fix: under `audit_context_requested` the empty/absent list is NOT collapsed to None -- an EXPLICIT EMPTY tuple `()` is forwarded, so the gate builds an EMPTY `authoritative_set`: every marker's `norm_path not in authoritative_set` is true and every marker folds back as ordinary content (checked==0, passed==0, no forged `blocked_paths`), while any real secret/token in a folded body STILL fails the whole payload closed via the audit-mode whole-context gate. Non-audit legacy behavior stays byte-identical (absent/empty -> None); the direct `_isolate_required_targets(..., None)` legacy contract is unchanged. Completeness/forward-safety: contract assertion MFH-J-008 ENUMERATES every `lowerSections.push` site and asserts 100% route through `neutralizeRequiredTargetMarker` (a FUTURE new raw-body section pushed un-neutralized fails the runner); MFH-J-007b pins the four new file-body call sites. Python proofs: `test_mfh_vectorb_*` (empty-set folds every marker, zero counts, still fails closed on a token, differs from legacy None) and `test_vectorb_*` (the bridge forwards `()` under audit_mode, `None` on the non-audit path). Identification/counting only: no ACTION_BLOCK detector relaxed, `AUDIT_STRUCTURAL_CATEGORIES` untouched, the #917 content-safety fix and #914 budget preserved. HoloIndex anchor terms: `RedDog all-section required target neutralization`, `Vector B legacy None empty authoritative set`, `lowerSections push neutralizeRequiredTargetMarker enumeration`, `advisory_model_once required_target_paths empty tuple audit_mode`. Follow-up if not indexed: `HOLOINDEX_REDDOG_MARKER_FORGERY_INDEX_GAP_PHASE1` (SPECIFIED_NOT_IMPLEMENTED -- no ranking/reindex code changed here).

Per-target redaction isolation (REDDOG_REDACTION_PER_TARGET_ISOLATION_PHASE1, v0.3.38): the packing path assembles all required-target excerpts into ONE merged context that is redaction-gated as a single unit (`evaluate_redaction_gate` in `scripts/advisory_model_once.py`; `fusion_alias_live.py`). Before this slice, ONE required excerpt carrying a hard-block token (`private_reasoning` / `private_key_residual`) blocked the ENTIRE payload (`redacted_context=None`), dropping ALL required targets even in audit_mode. This slice makes the redaction layer (`modules/communication/moltbot_bridge/src/fusion_redaction_gate.py`) marker-aware: when `audit_mode` AND the context carries the stable `### Required direct-read target: <path>` marker (`REQUIRED_TARGET_MARKER_PREFIX`), `_isolate_required_targets(context)` splits the context into preamble + per-target sections, evaluates each section's block status INDEPENDENTLY (reusing the unchanged audit-mode policy), OMITS only the sections that hit a non-audit-structural block (marker + a redaction notice kept, body gone -> secrets never reach the model), preserves all other sections verbatim, reassembles, and runs the UNCHANGED whole-context audit-mode gate over the survivors. This changes ONLY the GRANULARITY of the block (per-target instead of whole-payload); it relaxes NO ACTION_BLOCK detector, adds nothing to `AUDIT_STRUCTURAL_CATEGORIES`, and does not change what audit-mode preserves vs redacts. Fail-closed: no markers or an ambiguous split -> the unchanged whole-context gate runs; a hard block outside a target section still blocks the whole payload. The in-context notice sanitizes the block-category name so it can never re-trigger a detector; the real name is kept only in counts-only telemetry. Telemetry fields (`required_targets_redaction_checked` / `_passed` / `_blocked` / `_blocked_paths` / `_blocked_reasons`) flow from the gate report through the bridge to the Run Trace scorecard. HoloIndex anchor terms: `RedDog per-target redaction isolation`, `fusion_redaction_gate marker-aware isolation`, `required_targets_redaction_blocked`, `_isolate_required_targets`, `REQUIRED_TARGET_MARKER_PREFIX audit_mode`. Follow-up if not indexed: `HOLOINDEX_REDDOG_REDACTION_PER_TARGET_ISOLATION_INDEX_GAP_PHASE1` (SPECIFIED_NOT_IMPLEMENTED -- no ranking/reindex code changed here).

## WSP_97 Truth Boundary

Every substantive answer should classify claims:

- `OBSERVED`: present in supplied context.
- `INFERRED`: derived from supplied context but not directly proven.
- `NEEDS_VERIFICATION`: requires local read, test, live run, or external decision.
- `SPECIFIED_NOT_IMPLEMENTED`: documented requirement, not current behavior.

## WSP_15 Output Requirement

Every substantive answer ends with:

```text
## WSP_15 Priority
| Action | Complexity | Importance | Deferability | Impact | MPS | Priority |
|---|---:|---:|---:|---:|---:|---|
| ... | ... | ... | ... | ... | ... | P0-P4 |

## Next Safest Step
...
```

## RedDog Fusion Orchestrator (v0.3.14)

Internal contract layer. Advisory-only. No new authority.

| Function | Purpose |
|---|---|
| `classifyTaskForRedDog(prompt, contextMode, workerType)` | WSP_15-style effort/risk classification |
| `resolveAutoContextMode(classification, selectedContextMode)` | Maps Auto context to `wsp_holo` (REGULAR) / WSP+Holo+Skillz (HIGH) / WSP+Holo+git+Skillz (ULTRA) |
| `resolveAutoEffort(classification, selectedEffort)` | Maps Auto -> regular/high/ultra |
| `resolveModelMode(classification, selectedMode, workerType)` | RedDog WSP work defaults to auditable manual panel |
| `validateRedDogOutput(markdown)` | Required schema section check |
| `buildRepairPrompt(originalPrompt, badOutput, missingSections)` | One bounded repair pass; sanitizes draft for gate |
| `buildRepairBoundedContext()` | Minimal WSP-only context for repair (no HoloIndex resend) |
| `mergeRepairedOutput(primaryContent, repairContent)` | Appends schema supplement to primary Fusion output |

Required substantive output sections:

- Decision
- Findings
- Evidence
- Proposed fixes
- Uncertainties
- WSP_97 Truth Labels
- WSP_15 Priority
- Next safest step

Auto effort rules:

- `ULTRA`: auth/security/secrets/live runtime/public surface/pfMALL/WRE/OpenClaw/Hermes/Kanban/CABR/merge authority/repo creation.
- `HIGH`: architecture, WSP protocol, HoloIndex gaps, extension routing, FoundUps intake, RedDog/pfMALL planning.
- `REGULAR`: simple smoke tests, simple code explanation, non-runtime UI polish.
- If uncertain, choose `HIGH`.

Model and context routing:

- RedDog WSP/security/architecture/runtime work auto-routes to `foundups_fusion` (manual principal + panel).
- Omitted or non-list `panel_models` inputs retain the compatibility defaults. An explicitly supplied list is authoritative: an empty or invalid-only list remains empty and both Fusion modes reject it before any provider call instead of restoring default critics.
- The extension filters and forwards at most seven panel entries. Python is the canonical six-model runtime cap; the seventh entry is a bounded overflow sentinel so `panel_models_truncated` remains truthful for over-cap configuration.
- Fusion review-packet model fields are bridge-owned. Extension-supplied `bridge_meta` may add non-core telemetry but cannot replace the selected mode, lead, critic panel, truncation state, budgets, excerpts, quorum, or retry truth.
- Principal/synthesis default: `z-ai/glm-5.2`.
- Adversarial critic default: `deepseek/deepseek-v4-pro`.
- Implementation critic default: `qwen/qwen3.8-max`.
- Long-horizon reasoning critic default: `moonshotai/kimi-k3` with mandatory `max` reasoning, no temperature parameter, and a receipt-recorded 4096-token floor for every direct completion call. Regular single and manual Fusion inputs accept only integer completion budgets from 1 through the endpoint-fixture maximum of 131072; missing values retain their existing 2048/1600 defaults and invalid values fail as `invalid_max_tokens` before provider dispatch. Valid larger budgets are preserved and receipts distinguish requested from effective values. An explicit direct selection or receipt-backed signed promotion may place K3 in single, principal, or synthesis roles; this bridge does not itself promote a champion, change defaults, open an OpenClaw execution valve, or dispatch Hermes.
- REGULAR smoke/simple prompts auto-route to `openrouter_single` with the GLM principal and `wsp_holo` HoloIndex grounding (no Fusion panel, Skillz, or git).
- Substantive audit/research/implementation prompts must produce a non-empty typed target universe. When no explicit path, external source, or semantic header exists, RedDog derives a generic semantic subject and requires content-bearing HoloIndex evidence for it; broad audits require two references across implementation/authority and verification/authority categories. Unparseable work fails before Fusion with `grounding_target_universe_empty`.
- Context is not a 012-facing selector; it is resolved from the reasoning tier. That heuristic is not a WSP_15 allocation.
- Skillz/Wardrobe/Rolodex/OpenClaw/Hermes discovery is context only. RedDog may recommend a governed handoff, but this extension cannot execute it.
- `openrouter_fusion_alias` remains implemented for future explicit use, but is not the RedDog default because critic traces are not exposed.
- Repair pass: at most one; uses the same redaction-gated bridge; must not invent evidence.

Review packet additions:

- `task_classification`
- `resolved_effort`
- `resolved_mode`
- `resolved_context`
- `principal_model`
- `panel_models`
- direct `requested_max_tokens` and provider-effective `effective_max_tokens`; manual Fusion `requested_max_tokens`, `role_max_tokens`, and `panel_max_tokens`
- `mode_selection_reasoning`
- `work_focus_digest` (`hash`, `excerpt`, `length` - redacted)
- `wsp_prompt_digest` (`hash`, `excerpt`, `length` - redacted)
- `prompt_construction`: `0102_generated_from_work_focus`
- `output_validation` (`validated`, `missing_sections`, `repair_attempted`, `repair_ok`, `repair_context_mode`, `repair_mode`, `fusion_panel_ok`)

## RedDog Follow-Up Memory (v0.3.28)

In-memory WSP_97-safe continuation from the last successful or `BLOCKED_LOCALLY` run:

- `buildSanitizedContinuationSummary()` - extracts Decision/Findings/WSP_97/WSP_15/Next step summaries; strips secrets and blocked-policy literals.
- `appendContinuationSummaryToWspPrompt()` - appends sanitized summary to the next WSP task prompt when **Use last RedDog packet** is enabled (default OFF as of v0.3.36 - continuation is opt-in; 012 checks the box to enable).
- `state.lastContinuationSummary` - per-tab in-memory only; no disk persistence in Phase 1.
- Copy MD may include a safe **Continuation Summary** section for the stored packet (not raw prior model output).

Does **not** paste raw Copy MD, bounded context, or blocked snippets into follow-up prompts.

## Bridge Hardening (v0.3.16)

| Control | Status |
| --- | --- |
| Python resolver chain | OBSERVED |
| Subprocess output caps | OBSERVED |
| Orphan cleanup on webview dispose | OBSERVED |
| Context/prompt char budget | OBSERVED |
| Panel models cap (max 6) | OBSERVED |
| HTTP retry 429/502/503 only, max 2 | OBSERVED |
| Failure taxonomy (low-cardinality reasons) | OBSERVED |
| Work-focus contract unchanged | OBSERVED |

Failure reasons include: `redaction_blocked`, `missing_key`, `timeout`, `retry_exhausted`, `http_error`, `malformed_response`, `subprocess_failed`, `output_cap_exceeded`.

## 012 Work Focus to 0102 WSP Task Prompt (v0.3.15)

Formal contract:

```text
012 work focus (non-authoritative)
  -> RedDog interaction surface
  -> 0102 constructWspTaskPrompt(workFocus, classification, contextQuality, workerType)
  -> redaction gate (prompt + bounded context separately)
  -> OpenRouter bridge
  -> 0102 advisory output
  -> RedDog presentation
```

012 speaks to RedDog directly. RedDog does not send raw work focus to the
provider as sole authority: the deeper 0102 layer assembles the WSP task prompt
for the bridge, and embeds work focus under an explicit non-authoritative label.

## WSP_97 Truth Table (v0.3.15)

| Claim | Status |
| --- | --- |
| Auto router REGULAR/HIGH/ULTRA | OBSERVED |
| 012 work focus -> 0102 WSP task prompt layer | OBSERVED |
| Review packet work_focus_digest + wsp_prompt_digest | OBSERVED |
| WORK_FOCUS_NOT_AUTHORITY | OBSERVED |
| WSP_PROMPT_0102_GENERATED | OBSERVED |
| RAW_FOCUS_NOT_SENT_AS_SOLE_AUTHORITY | OBSERVED |
| DIGESTS_NOT_RAW_CONTEXT | OBSERVED |
| ROUTING_UNCHANGED_FROM_0_3_14 | OBSERVED |
| Skillz/Rolodex non-vacuous for YouTube comment ops | OBSERVED |
| Advisory-only; no shell/repo/browser/OpenClaw/Hermes execution | OBSERVED |
| Redaction gate before OpenRouter | OBSERVED |
| Governed handoff contract (typed WRE dispatch) | SPECIFIED_NOT_IMPLEMENTED |
| GitHub permission probe (read-only snapshot) | OBSERVED (github_integration module) |
| OpenClaw work-order policy gate | OBSERVED (moltbot_bridge module); no execution |
| RedDog work-order receipt (Hermes-compatible audit) | OBSERVED (moltbot_bridge module); not live Hermes queue |
| RedDog runtime invocation dry-run | OBSERVED (moltbot_bridge module); no execution |
| WRE isolated worktree executor | SPECIFIED_NOT_IMPLEMENTED (contract doc only) |
| WRE executor dry-run planner | OBSERVED (moltbot_bridge module); no mutation |
| OpenClaw FoundUpsJob adapter | SPECIFIED_NOT_IMPLEMENTED (contract doc only) |
| AssignmentDispatcher as worker launcher | FORBIDDEN (simulated scaffold only) |
| Governed repo work order dry-run validator | OBSERVED (OpenClaw bridge module) |
| Governed repo work order (`RedDogGovernedWorkOrder`) | OBSERVED (candidate runtime emission from extension; authority binding still required) |
| WRE operational spine dry-run preview | OBSERVED (extension v0.3.46); metadata only, no invocation |
| Extension invokes `reddog_wre_operational_spine.py` | SPECIFIED_NOT_IMPLEMENTED |
| GitHub permission snapshot per work order | SPECIFIED_NOT_IMPLEMENTED |
| F0 autonomous merge | SPECIFIED_NOT_IMPLEMENTED |
| WSP Applicability Preflight | SPECIFIED_NOT_IMPLEMENTED |
| pfMALL surface binding | SPECIFIED_NOT_IMPLEMENTED |
| Review packet memory / persistence | SPECIFIED_NOT_IMPLEMENTED |
| Bridge hardening (edge-case redaction/repair) | SPECIFIED_NOT_IMPLEMENTED |
| REDDOG_IS_ARCHITECT_INTERFACE | OBSERVED |
| AUTONOMOUS_DAE_WORK_NOT_012_WORK | OBSERVED |
| HERMES_IS_SCAFFOLDING_NOT_POLICY | OBSERVED |
| OPENCLAW_IS_POLICY_GATE | OBSERVED |
| WRE_RETAINS_REPO_AUTHORITY | OBSERVED |
| SENTINELS_REVIEW_NOT_EXECUTE | OBSERVED |
| CABR_PAVS_VALIDATES_BENEFIT | OBSERVED |
| EXTENSION_REMAINS_ADVISORY_ONLY | OBSERVED |

## Redaction Gate Report (v0.3.20)

When redaction blocks before OpenRouter, Copy MD includes `## Redaction Gate Report`. Raw blocked content is never included.

| Field | Notes |
| --- | --- |
| decision | `BLOCKED_LOCALLY` |
| made_network_call | `false` |
| blocked_stage | `pre_openrouter_request` |
| blocked_payload_part | `work_focus` \| `system_prompt` \| `repo_context` \| `holoindex_context` \| `skillz_context` \| `unknown` |
| rule_classes | Detector class names or safe categories |
| rule_counts | Category -> count map |
| raw_snippets_included | Always `false` |
| redacted_payload_digest | `sha256:<64 hex>` when available |
| safe_summary | One sentence, no raw content |
| next_safe_context | `none` \| `wsp_only` \| `narrowed_diff` \| `local_0102_review` |

All fields carry WSP_97 truth labels (`OBSERVED` or `UNKNOWN`). If the gate cannot identify the payload part, report `unknown`; do not infer.

## Governed Handoff Recommendation (v0.3.20+)

Substantive Copy MD packets append `## Governed Handoff Recommendation`:

| Field | Notes |
| --- | --- |
| handoff_needed | `true` \| `false` \| `unknown` |
| target | `WRE` \| `OpenClaw` \| `Hermes` \| `Sentinel` \| `none` |
| authority_level | Always `advisory_only` |
| suggested_slice_name | Bounded slice identifier |
| WSP_15 priority | Inferred from tier |
| required_human_gate | `012_sovereign` \| `none` |
| reason | Conservative blocked-local reason when no model output (e.g. `blocked_context_needs_local_0102_review`) |
| evidence_refs | Bounded digest references only |

Redaction-block-only runs default to `handoff_needed: unknown`, `wsp15_priority: P1`, and `suggested_slice_name: none` unless concrete fix evidence exists.

Extension retains no repo/shell/merge authority.

## WRE Operational Spine Dry-Run Preview (v0.3.46)

Substantive non-blocked Copy MD packets append `## WRE Operational Spine Dry-Run Preview` after the governed handoff section. The preview is a typed candidate envelope for the WRE spine path and includes only digests, redacted summary text, target labels, and no-execution booleans. Blocked-local packets skip this preview so blocked payload content is not summarized.

| Field | Meaning |
| --- | --- |
| `slice_name` | `REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_DRYRUN_WIRE_PHASE1` |
| `target` | `reddog_wre_operational_spine` |
| `would_call` | Future spine function reference only; not invoked by extension |
| `command_digest` | SHA256 of the work focus; raw work focus is not stored |
| `command_redacted_summary` | Bounded sanitized summary |
| `dry_run_only` | Always `true` |
| `python_invocation_performed` / `wre_spine_invoked` | Always `false` in this slice |
| `worktree_create_performed` / `task_execution_performed` / `file_edit_performed` / `pr_created` / `merge_performed` | Always `false` in this slice |
| `openclaw_enqueue_performed` / `hermes_dispatch_performed` | Always `false` in this slice |
| `required_future_valve` | `VALVE_OPEN_WORKTREE_CREATE` |
| `required_human_gate` | `012_sovereign` |

## External Acceptance Baseline (v0.3.21+)

Foundups(R)Agent external-lane usefulness is measured by a **fixed 15-prompt acceptance pack** documented in `docs/REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md`.

| Layer | Scope |
| --- | --- |
| CI | Contract tests, syntax, bridge AST - **no live OpenRouter** |
| 012 manual | Full prompt pack, rubric scoring, Copy MD artifacts, sovereign verdict |
| Artifacts | Redacted records under `docs/acceptance/` - no secrets |

Baseline pass records honest scores on v0.3.21. Replacement pass reruns the same prompts after HoloIndex/dispatch improvements.

Lane B (internal WRE architect / Sakana loop) is **excluded** from this acceptance boundary.

## Public/RedDog Roadmap Boundary

The extension is the IDE-side model for a future RedDog operation surface:

```text
012 work focus
  -> 0102 WSP task prompt assembly
  -> RedDog Architect advisory review
  -> HoloIndex recall
  -> WSP_97 truth classification
  -> WSP_15 priority
  -> WSP_109 intake packet or WRE dispatch recommendation
  -> Skillz/Wardrobe/Rolodex match and WRE/OpenClaw/Hermes governed handoff recommendation
  -> WRE/OpenClaw/Hermes governed execution
  -> pfMALL-visible state after verification
```

This interface documents that direction only. It does not expose a public intake route.
