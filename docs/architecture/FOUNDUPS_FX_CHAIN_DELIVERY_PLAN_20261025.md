# FoundUps FX and blockchain delivery — 2026-10-25

Status: active layered delivery; no testnet or production readiness claim.

## Member serving allocation — 2026-10-26, before authoring

WSP15 C2/I4/D4/Impact4=14/P1; WSP00/6/11/22/50/62/71/77/84/97.
Parent candidate11ca7d54dd10007a2862a7da6b875a16965b4225, PR2225; use
agent/foundups-member-serving-20261026 in the same clean owned worktree.
Need: ASGI/TestClient acceptance does not prove a real server can deliver the
draft route. Reuse the existing Uvicorn CLI rather than add a custom launcher.
The umbrella already declares uvicorn[standard]>=0.24.0; do not migrate that
environment or import its optional dotenv/WebSocket/reloader machinery.

Allocate one optional requirements-server.txt (<=16 lines) including the existing
HTTP requirements plus exact minimal uvicorn0.54.0/h11 0.16.0/click8.5.0 pins.
Current official PyPI metadata reports no advisories for these three releases;
verify the actual complete installed inventory before qualifying it. Resolve only
official binary wheels in a new external environment; retain pip26.2.2 acquisition,
installation report, wheel digests and metadata inspection, not credential values.
Preserve the previous patched profile and every historical receipt unchanged.

Run the real factory through the ordinary CLI over loopback only: one worker,
asyncio/h11, no WebSockets, proxy-header trust, reload, access log or server header;
explicit concurrency16/backlog32/keepalive5/graceful10/header-buffer16384 bounds.
These library settings are not abuse protection, hard RSS/OS/network confinement
or cloud ingress limits. Do not invent a server wrapper or duplicate HTTP/auth code.
Cloud Run's separate deployment command must bind0.0.0.0 and its supplied PORT;
the local proof must never expose a workstation listener to the local network.

Test-first: reuse the original RSA/policy/header helpers in the existing417-line
test owner. Add <=160 lines/three real-process HTTP cases, keeping every existing
definition/oracle and all814 IDs. Freeze acceptance before the profile/CI change;
retain the expected missing-server RED in the old profile, then new-profile GREEN.
Use credential-free child configuration, ephemeral synthetic keys without output,
bounded startup/HTTP waits and process cleanup. Exercise actual health, rejection,
signed201 draft, unrelated404, no-store and absent server/access-log evidence.
No fixture or server monkeypatch replaces the actual TCP request path. Peer review
requires chunked oversize rejection and missing/bad policy startup failure. Use
port0 and the child startup log to identify its actual port/PID without a reserve-
close race. Terminate/wait/kill/wait cleanup proves reaping, not graceful shutdown.
Peer cleanup finding allocates finally-based launcher reaping and a separately
verified Windows child-liveness outcome, even after taskkill failure. WSP62 keeps
this cohesive RSA/process fixture in the existing owner rather than duplicating it.

Existing nomination workflow: add only the new profile's two trigger filters and
select it for installation; preserve jobs/permissions/tests/report retention.
Budget: README+35, INTERFACE+12, ROADMAP+12, module ModLog+18, tests README+12,
TestModLog+32 (retain fixture/cleanup corrections), this plan+70/root ModLog+16.
No new test owner, runtime member,
manifest/pin/ledger/registry change, application logic or grant. Existing manifest
check and independent exact-candidate review precede publication; hosted gates
must bind the final head. Stop/reallocate any actual unbudgeted delta.

Execution plane: local package acquisition and loopback server qualification.
No cloud build/deployment, IAM change, provider identity/session, persistent data,
repository claim, mint or reward is authorized by this proof. Container closure
must separately retain the real imported static directory (not a placeholder),
exclude credentials/shared ignored sources and qualify its Linux image. Existing
Firebase functions remain untouched. Then administer policy/cost/ingress and prove
a real session before browser wiring and atomic repository-control admission.

Retrieval: Holo again returns HEAD_MISMATCH/UNKNOWN/gaptrue; no reindex. NAV and
current HTTP/factory/package imports, module/test memory, requirements and workflow
are the primary evidence. Old deployment prose and umbrella extras are noise.
No memory/README exists; requirements now exist (the old debt note is stale).
Deterministic wire/inventory checks and a separate reviewer supply evidence that
Qwen/Gemma inference cannot establish. Uvicorn settings and Cloud Run container
contract were read from their official current documentation before allocation.
Local outcome: repaired real-process profile817PASS, all814 prior IDs retained;
28 installed official wheels match registry metadata with zero listed advisories.
Manifest check passes unchanged; independent fault-path and hosted gates remain.

## Member host bootstrap allocation — 2026-10-26, before authoring

WSP15 C3/I4/D4/Impact4=15/P1; WSP00/3/6/11/22/49/50/62/71/77/84/97/109.
Parent mainfe721d3778969f950dde3b291cf24724d018ee7d; reuse the clean owned
repository-observation worktree on agent/foundups-member-host-20261026.
Need: the published draft route has no configured production host. Exact source
search finds its only policy assignments in tests; Hosting has no API rewrite.
Read-only Firebase inventory binds projectgen-lang-client-0061781628, its existing
foundupscom site and six ACTIVE Node20 functions inus-central1. Their matching
entrypoint is ignored in the shared checkout and absent from clean main, with no
Clerk reference. Preserve those sources/services and all shared checkout state.
Installed gcloud has no active account; Docker's current daemon connection fails.
These observations do not prove billing/IAM, deployed source equivalence or a
Cloud Run inventory. Evidence: external foundups-member-host-discovery-20261026.

Simplest layer: supply the actual intended isolated ASGI host factory before its
container/cloud/browser qualification. Reuse existing ClerkIntakePolicy, verifier,
body/wire limits, mapper and proposal handler; do not clone them in Node or expose
the development catalog/static application. Bind policy to request.app.state so
separate server instances do not read the development app's global policy.

Add one <=150-line intake_host.py in the existing flat PFMall owner. Its no-argument
create_app factory reads only PFMALL_CLERK_POLICY_FILE from trusted server config;
require an absolute regular-file path, bounded16KiB UTF-8 JSON, unique/exact fields
issuer/authorized_parties/public_key_pem, and the existing canonical public-RSA
policy validation. Missing/invalid configuration fails startup with one generic
error and no configuration/token/key values. No dotenv, default/test issuer,
provider/JWKS call, membership/revocation claim, private key, storage or grants.
Expose only POST /pfmall/proposals and minimal no-store GET /healthz; disable
OpenAPI/docs and unrelated catalog/static/FoundUp routes. Reuse all draft semantics.

Execution plane: local app construction and ordinary credential-free ASGI tests,
not WRE/resident, cloud deployment, IAM expansion or a live provider session.
Test-first: preserve the exact786-case seven-owner baseline in the already qualified
patched optional profile. Extend the existing323-line real-RSA/HTTP test owner by
<=140 lines/<=30 cases, total<=470; retain all91 old cases/oracles and shared RSA
fixtures. Freeze desired bootstrap/config/instance-isolation acceptance before
production edits; retain actual RED, then full GREEN/old-ID parity and independent
boundary review. Do not mirror all existing token/body tests or add a framework.
WSP62 exception retains this cohesive fixture/HTTP owner rather than duplicate it.

Budget: new host file above; existing HTTP route changes one policy-owner line;
workflow adds the new source path to its two existing trigger lists only. Existing
README+16/INTERFACE+26/ROADMAP+14/ModLog+18, tests README+14/TestModLog+22,
this plan+65/root ModLog+16. No new test file, dependency, registry or permission.
Run existing manifest check: if any runtime member/hash/cap would change, stop and
allocate that real delta before mutation. Do not predict scanner exceptions;
require actual source-bound classification and fresh hosted gates for publication.
Historical receipts and protected Mall/TestNet/codec work remain untouched.

Macro path remains bootstrap -> qualified serving/container -> administered public
policy and cloud IAM/cost bounds -> deployed host/real session -> same-origin UI
and abuse/revocation qualification -> fresh repository challenge/atomic receipt.
This layer does not substitute for any of those outcomes or close the whole goal.
Cloud Run's official FastAPI guide and Uvicorn's factory/resource documentation
support the selected ASGI path; no CLI/IAM/API-enable/deploy command was executed.
Sources: [Cloud Run](https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-fastapi-service), [Uvicorn](https://uvicorn.dev/settings/).

Retrieval evaluation: task-bound Holo atfe returns UNKNOWN/HEAD_MISMATCH/gaptrue
againsta519f0ad; no reindex/repair/CURRENT claim. Current source/interface and
provider resource metadata outrank historical publication-pending prose. Optional
requirements are present; memory/README absent. Deduplicate into existing RSA,
mapper and HTTP owners. Qwen/Gemma inference cannot prove app isolation or cloud
identity; deterministic source/tests plus attributed independent review can.

## Observation manifest finding allocation — before ledger mutation

WSP15 C1/I4/D5/Impact4=14/P1; WSP6/15/22/50/71/97. Candidate1d2d6a07,
hosted CI40229328761/job121277457907 reports39 manifest tree findings plus
one history row repeating the client hash:40 rows/39 unique bindings. Root
verified38 unchanged parent lines and one new reproducible client source hash;
all1471 normalized source hashes match. Hosted client167PASS; GitGuardian passes.
Need: independently classify each observed line/rule/whole-file binding before
publication. Reuse .github/security/reviewed-findings.json with its exact2378-row
ordered prefix. Append only the39 agreed bindings after separate source review.
No detector, fingerprint algorithm, scan scope, manifest/source/test oracle or
external incident change. Preserve initial failed scan; fresh tree/history scans
remain required. This metadata repair grants no provider/runtime/token authority.
Budget amendment: this existing plan+18 additional lines (83 total for this work),
root ModLog+2/module ModLog+2 within original limits, ledger+39 rows; no new file.
Root proposal is external/source-bound; verifier must derive the exact same set.

## Observation HTTP allocation — 2026-10-26, before authoring

Review amendment: add32nd case for duplicate encoding; retain all existing budgets.
Local result: original135PASS; frozen RED146PASS/20FAIL; initial GREEN166PASS.
Duplicate-header RED166PASS/1FAIL; final167PASS preserves original exact IDs.
32 new HTTP cases; no live provider/control/issuance or runtime claim. Hosted
gates, independent review and current-main convergence remain required.

WSP15 C3/I3/D2/Impact3=11/P2; WSP00/6/11/15/22/50/62/71/84/97.
Parent main2c9c93ead0ee146da8b18078129e4b7059fd4cc8; clean owned
repository-observation worktree, agent/foundups-observation-transport-20261026.
Need: the existing Git-object reader parses an unbounded HTTP body and inherits
redirect/time defaults before validating object limits. Bound this prerequisite
before connecting repository-control evidence. It has no production consumer,
so it is deferrable; higher-priority GG dispositions await authenticated access.
Reuse the existing client/HTTP fixtures, with no new service or provider framework.

Execution plane: observation-only async GitHub reads. Keep the public signature,
13-field DTO, identity checks, legacy verbs and legacy Contents tuple unchanged.
Use a private request opt-in; permit only GET against the exact configured
https://api.github.com base, fixed same-origin relative endpoints, no redirects.
Request identity encoding, disable automatic decompression and reject compressed
responses. Require200 and application/json or application/*+json; decode UTF-8
only after a looping raw-body ceiling of2MiB, independent of Content-Length.
Reject a declared oversize early; count actual chunks when absent or misleading.

Operational budgets: per request total5s/connect2s/socket-connect2s/socket-read2s;
whole observation timeout30s, with caller cancellation propagated and response
cleanup retained. These are application/library deadlines, not a hard OS/RSS or
latency guarantee. At most13 logical GET calls; preserve zero application retries
and pinned aiohttp3.13.5's possible one reconnect retry per call. No hard TCP/DNS
attempt cap is claimed. Retain field-only errors, including JSON recursion errors.
No authenticated-provider admission, atomic name-reuse proof, repository claim,
work/issuer/signing/token grant or current-tip freshness follows from these bounds.

Verification: reuse both canonical unit owners in the existing qualified external
Python3.12.10/pytest9.0.3/pytest-asyncio1.3.0/aiohttp3.13.5/aioresponses0.7.8
environment, clean process/no credentials/no installs. Baseline original135 IDs
first; freeze desired new tests before product edits and retain actual RED.
Then focused GREEN, exact old-ID/outcome preservation, full two-owner shard and
independent source review. HTTP mocks prove application policy, not real wire
retry/decompression, provider identity, network denial or OS isolation.

Budget: existing client<=850 lines/+100, new functions<=35; existing request
function<=55 for the opt-in, with unchanged legacy body. Existing807-line test
owner<=1020/+210, <=32 new parameter cases and new methods<=35; retain all120
old client cases/oracles, allowing only the callback's private-option signature.
WSP62 advisory exceptions keep these cohesive existing owners and fixtures rather
than duplicate them. Module README+16/INTERFACE+32/ROADMAP+16/ModLog+20,
tests README+24/TestModLog+24/memory README+10, this plan+65/root ModLog+16.
Derived: client already belongs to1471-member runtime closure; regenerate only its
hash and two existing digest pins, same members/caps; reuse eight generator cases
and three Node owners. Actual scanner findings need source-bound review before
any individual ledger append; no predicted exceptions, detector/scope relaxation,
registry/workflow/dependency changes or source/runtime activation.

Retrieval evaluation: exact-task Holo owner query and this turn's query both show
HEAD_MISMATCH/UNKNOWN/index gap; no retry/reindex or CURRENT claim. NAV points to
legacy WSP automation, so direct definitions/callers and all module-memory docs
provide current evidence. README completion/security claims and historical test
file lists are noise; current source/interface/two-owner inventory take precedence.
ROADMAP is a stub; memory README exists. No duplicate bounded observation path or
non-test consumer was found. Deterministic transport/cleanup needs source and real
client-path tests; Qwen/Gemma inference adds no evidence to these policy decisions.

## Pitch skill publication allocation — 2026-10-26, before authoring

WSP15 C2/I3/D4/Impact3=12/P2; WSP00/6/15/22/50/62/84/97.
Parent main33f1442d76cca7fc084523355c6895964828258e; clean owned
repository-observation worktree, agent/foundup-pitch-package-20261026.
Need: the requested pitch/deck instruction already exists locally but is absent
from main. Publish that owner and its discovery wrappers, correcting two stale
references. This affordable local layer can proceed while higher-priority
Mall/TestNet/codec GitGuardian holds remain unresolved; it does not clear them.

Execution plane: local creative drafting by an instructed agent. Outcome is the
vision; Solution nests PoC/Prototype/MVP; Pain describes obstacles to Solution.
Preserve unknown stages, evidence/assumption separation, rendered-deck QA and
truthful pending-media status. No executor, WRE registry, resident RedDog trigger,
provider admission, paid generation, publication, claim, mint or reward grant.
The current AntifaFM campaign prototype has distinct operations and grants;
its former placeholder label and a missing local-only plan link must be corrected.

Reuse the existing module Skillz and canonical .claude discovery mechanism;
generate the byte-identical .agents mirror with the unchanged projection script.
Budget: two wrappers<=24 lines each, module SKILLz<=150; this plan+60,
module README+12/ModLog+16, root ModLog+16. Exactly seven paths; no other
configuration, tests, dependencies, registries, manifest members, caps or pins.
Stop and reallocate if generation changes an existing projection unexpectedly.
Observed generator effect: two existing text outputs changed CRLF to LF only.
Permit restoring those owned writes after exact normalized comparison; require
their pre-run byte hashes and retain the seven-path content scope.

Verification: fresh parent projection --check and unchanged existing18-case owner
in the qualified external Python3.12.10/pytest9.0.3 clean process, preserving exact
IDs/outcomes and any real-symlink capability skip. Then repeat after publication,
validate both wrappers with the bundled skill validator, resolve local links,
review the frozen seven-path candidate independently and require hosted gates.
No new tests or package installs; local structural checks do not prove artifact
generation, provider operation, runtime admission or OS/network isolation.
Qwen/Gemma inference would add no evidence to this deterministic projection;
attributed parallel source/test review supplies the useful challenge.

Retrieval evaluation: Holo owner query returned HEAD_MISMATCH/UNKNOWN with an
index gap; direct current source/docs replace it without reindexing or a CURRENT
claim. Current campaign interfaces outrank old placeholder prose. Deduplicate
wrappers into the module owner; module memory README and the legacy local plan
are absent on main. Existing projection tests are the reusable contract.

Publication checkpoint: projection check passes before/after; unchanged18-case
owner yields17PASS/1SKIP in each run (real Windows symlink creation unavailable).
Both wrappers pass bundled structural validation; generated bytes match canonical.
Existing projection source/tests/configuration remain unchanged. Independent
review and hosted current-head gates are required before merge.

Media capability research — 2026-10-26: Google's current
[video guidance](https://ai.google.dev/gemini-api/docs/video) recommends
`gemini-omni-1.1-flash`. Its Gemini API Veo3.1 previews were retired on2026-10-22;
see [deprecations](https://ai.google.dev/gemini-api/docs/deprecations).
Omni uses the [Interactions API](https://ai.google.dev/gemini-api/docs/omni);
an older Veo adapter is not automatically compatible. No credential/account/spend
verification or live generation occurred. Provider operation/retry qualification,
RedDog invocation and public Mall distribution remain separate delivery layers.

## GitHub nomination review allocation — 2026-10-26, before authoring

WSP15 C3/I4/D4/Impact4=15/P1; WSP00/3/6/11/22/49/50/62/84/97.
Parent main531bd0341ef502b53c8913c9163963b03354f62c; reuse the clean owned
repository-observation worktree on agent/foundups-project-admission-20261026.
Need: the public issue form has no nomination-to-draft consumer. The simpler whole
component is issue event -> bounded adapter -> existing mapper -> review artifact.
Network reads in the pure mapper/unrelated writer would not close this gap.

Execution plane: a single GitHub-hosted issue-review job, not a WRE worker or
RedDog resident command. Only trusted default-branch source runs for issue events;
no issue body/title interpolation into shell, credential checkout persistence,
project code checkout, URL fetch, model/provider, database, comment or label writes.
GitHub's event metadata attributes a nominator; it grants no project ownership,
commander, registry, issuer, asset, reward or venue authority. Local event replays
are unsigned development inputs, not provider authentication. Drafts retain
IDEA/UNBOUND, external_repo_requested=False and missing acceptance criteria.

One new <=300-line module under ai_overseer/src/foundup_genesis owns the pure
adapter and bounded CLI. Require the exact repository, positive issue/author IDs,
issue action, title prefix, matching canonical issue URL and exact ordered form
headings/consent. Bound event bytes<=256KiB, body<=16KiB and each field; reject
ambiguous/duplicate/unknown headings, invalid controls and credential-bearing URLs.
Preserve Outcome (vision), Solution (PoC/Prototype/MVP as supplied), and Pain
(obstacles) as redacted advisory text; unknown optional fields stay unknown.
Reuse LaunchRequest mapping/redaction, without changing its seven-field contract,
auth provider, validation or AST pin. Fixed output artifact, generic rejection,
no raw input in logs/errors; artifact is for review, never executable admission.

Test reuse: existing launch-request/transport owners cover mapper/auth semantics;
the new issue-event/CLI contract is materially distinct and warrants one <=300-line
test owner (<=24 methods/81 cases), plus its default allowlist and canonical test
registry entry. Read their existing inventories/fixtures before authoring. Baseline
the two existing owners first in the previously qualified external Python3.12.10 /
pytest9.0.3 environment; record exact IDs/results, normal package imports and actual
dependency versions. No shared install, package substitutions or skip-to-green.
Freeze desired new acceptance before production code and retain RED. Then focused
GREEN, unchanged adjacent intake owners, CLI replay and independent source review;
add a <=130-line workflow for issue review and exact PR/main contract execution.
Use hosted security/scope/current-head checks before merge and read back main.
Budget: new source/test/workflow above; existing module README+20, INTERFACE+30,
ROADMAP+20, ModLog+16, tests README+20/TestModLog+20, conftest one entry,
canonical test registry only one new unit entry, this plan+85/root ModLog+16.
No runtime manifest member/cap/source change, dependency, security exception,
public API/server, token, signing or chain submission. If static closure shows
otherwise, amend before that change. No new large receipt/testcase framework.
Qwen/Gemma inference adds no value to deterministic form parsing; attributed
parallel source/test review supplies the relevant architectural challenge.

Retrieval evaluation: HoloIndex returned HEAD_MISMATCH/UNKNOWN with an index gap;
direct main source/callsites replace semantic retrieval, not a CURRENT claim.
Historical ProductionReady claims and older prototype trajectories are noise;
current interface/source/tests outrank them. Parent module owns Tier0 documents;
its memory README is absent. Deduplicated actual callers show no nomination
consumer, Firebase handler or authenticated project-control principal bridge.
Open Mall/TestNet/codec parents keep their unique work and security holds.

Pre-authoring architect refinement: use issues.opened only, with exact repository
ID956651858 and distinct positive issue/user IDs; sender ID must match the initial
issue author. The pure adapter requires an explicit nomination-only trusted service
context supplied by the host bootstrap, never constructed from parsed event/body.
The existing session/invite provider remains sole authority for HTTP intake;
this separate workflow host may assert its own fixed review-service context for
draft creation only. Keep requested_by=github_nomination_review_service; nominator
identity is separate advisory source metadata. Local CLI replay is explicitly
unverified; Actions run provenance is external, not authenticated by a JSON field.
No application API/network calls; checkout/setup/artifact use hosted transport.

Baseline: unchanged owners pass387; frozen V1 RED80 missing-module failures/387pass.
Replace the malformed-only CLI cap case with valid JSON at cap/cap+1 (+1 net case).
Baseline uses normal
package imports and unchanged source hashes in the qualified external environment.
The distinct issue adapter avoids growing the existing1,012/1,427-line tests.
Preserve multiline OSP in a redacted advisory sidecar;
map only the safe name/reference to genesis rather than guessing how vision maps
to problem_statement. No mapper control-character normalization or policy change.
Replay metadata stays unverified; the Actions run supplies external provenance.
Local result:682 cases/five owners pass, plus an actual synthetic CLI replay;
resident1471/c1f97e86 unchanged. Current hosted/security/main gates remain required.

## Repository file observation allocation — 2026-10-26, before authoring

WSP15 C3/I4/D4/Impact4=15/P1; WSP00/6/11/22/50/62/84/97.
Parent main5da187622d0076f6d53de79bf8e1bd1b93aa9bb5; isolated owned worktree.
Need: project admission needs a committed regular-file reader, while the legacy
Contents route can dereference symlinks and discards identity/mode/commit fields.
Affordability: extend the existing GitHub client and test owner; no new service,
dependency declaration, claim store or execution plane. Identity-only metadata
does not establish file provenance; a full claim/issuer flow exceeds this layer.

Add frozen13-field GitHubFileObservation (including private visibility) and
get_file_observation(path, *, commit_sha=None).
Keep the seven-field GitHubRepository and legacy content tuple unchanged. Read
stable numeric repository/owner IDs and actual default branch; observe its commit,
then resolve an optional exact commit through nonrecursive Git trees and a blob.
Admit <=8 path components/1024 UTF-8 bytes, <=4096 entries per tree and <=16384
decoded bytes. Require exact object IDs, unique selected entries, truncated=False,
regular modes100644/100755, strict bounded wrapped base64, length and Git blob hash.
Compare identity/name/branch/visibility again before returning; <=13 GET requests.
Errors must identify fields without echoing response bodies or file contents.

This is provider-response consistency, not atomic repository provenance. Matching
identity brackets cannot exclude name reuse between calls, nor prove the initially
observed tip is still current. Existing transport is not upgraded to an admitted,
time/body-bounded provider. No caller may treat this DTO as a claim, permission,
trusted fact, signer, token, reward, venue or agent-work grant. Later admission
requires its own authenticated identity-bound observation and fresh challenge.

Verification: inventory/reuse the existing26 client cases, baseline them first in
a new external venv (pytest9.0.3, pytest-asyncio1.3.0, aiohttp3.13.5,
aioresponses0.7.8; binary wheels only, record actual closure). No shared install.
Permit only observed baseline repairs: PATCH dispatch for existing close_issue,
unsupported-method oracle moves to TRACE; network fixture uses aiohttp.ClientError.
Preserve failures and exact IDs. Freeze new acceptance in the same test file before
product changes; run desired RED, focused GREEN, adjacent compatible unit shards,
independent source review and current hosted/security/scope gates. Local mock runs
are development evidence, not OS isolation or full-repository promotion evidence.

Budget: existing client<=850 lines/new functions<=35; existing tests<=850/new
methods<=35. Existing interface<=100, README+20, ModLog+20, tests README+30,
TestModLog+25, this plan+65 and root ModLog+16. Add one focused CI workflow<=100
lines and one portable receipt<=24KiB; optional module memory README<=35. No other
source, registry membership, runtime manifest, dependency or security-ledger change.
Holo owner query remains HEAD_MISMATCH; direct source/callsites/test inventory
replace stale retrieval, without a CURRENT-index claim. Legacy doc assertions are
historical; no production-ready or comprehensive coverage claim follows.

Metadata dependency amendment before repair: WSP15 C2/I4/D4/Impact3=13/P1.
The existing runtime manifest includes this client; leaving its old hash would
break the source compatibility contract. Regenerate scripts/reddog_backend_manifest.json
and update only the digest literals in extensions/reddog/backend_compatibility_constants.js
and scripts/tests/test_generate_reddog_backend_manifest.py. No generator, member,
cap or semantic assertion changes. Reuse all eight generator cases after staging
source+manifest, plus the existing Node compatibility, preflight and blocked-recovery
owners. Read their inventory first; scripts/tests/README.md is absent.
Add at most10 lines each to scripts/tests/TestModLog.md and extension ModLog and
tests/TestModLog; report the exact one-member hash delta and unchanged member list.
This explicit dependency repair supersedes the earlier no-manifest-change budget;
it grants no installed runtime or provider activation.

Local result:135 module cases pass (120 client/15 permission-probe); eight existing
generator cases and three Node owners pass. Runtime1471 members unchanged; only
the client's source hash changes, canonical digest c1f97e86. Frozen RED and prior
runner/long-ID errors remain in the [receipt](receipts/FOUNDUPS_GITHUB_FILE_OBSERVATION_20261026.json); hosted/main gates remain.

Hosted-profile/security metadata amendment, before correction: WSP15
C2/I4/D4/Impact4=14/P1. Preserve run40208878967:134PASS/1FAIL because empty
GITHUB_TOKEN differs from absent in the legacy presence check. Unset GITHUB_TOKEN
and GH_TOKEN for the mock test process and set an explicit workspace root;
no product or assertion change. Retain fresh exact IDs/artifacts at the new head.
Internal scanner run40208878992 reports41 tree and3 history rows, only in the
source-hash manifest and new local receipt. Before adding any reviewed binding,
derive exact fingerprints, prove unchanged parent review coverage and public
hash/metadata origins, and obtain independent review. Append only individually
verified bindings to .github/security/reviewed-findings.json; preserve its ordered
prefix and scanner/rule/history semantics. Unknown findings still block.
Extend this plan's allocation to+85, root ModLog+16 and test README+30; no new
receipt, test case, runtime member, cap, secret, signer or provider activation.
Independent reconstruction accepted exactly40 bindings (39 manifest/one receipt);
append preserves all2260 prior entries/order/keys. Fresh hosted scan still required.

## Unsigned integration checkpoint allocation — before authoring

WSP15 C2/I4/D4/Impact3=13/P1; WSP22/50/84/97. Source: main0909b941.
Publish the latest merged intake/nomination facts, exact open delivery heads and
the bounded stored-intent/unsigned-codec experiment in this existing owner.
Need: the checkpoint below predates these deliveries; local experiment evidence
would otherwise be lost in temporary files or mistaken for production admission.
Budget: this plan at most100 added lines, root ModLog at most18, and one new
compact receipt at most24KiB. No product, test, dependency, runtime member/cap,
security exception, provider, signer, asset, settlement or deployment change.
Validate exact source/result IDs, retained failed run, hashes, scope and independent
review; do not rerun unchanged component suites for documentation. Current CI and
main readback remain publication gates. Local scripts/payloads are not bundled;
the receipt must disclose that reproducibility limit and every unproved stage.
Deterministic source/evidence reconciliation needs no Qwen/Gemma model execution.

## Unsigned integration checkpoint — 2026-10-25

This checkpoint supersedes older status prose below while retaining its chronology.
Observed main `0909b9419f410e7da371dfbd6bf9738a229bf7a7` includes nomination
PR2207 and reference-preservation PR2208. The entire merged intake tree equals
its reviewed tree. Nomination creates a public proposal; intake keeps untrusted
references in a detached draft list. Neither grants repository control or issuance.

| Preserved PR | Reviewed current head | Publication state at this checkpoint |
|---|---|---|
| [Mall2196](https://github.com/FOUNDUPS/Foundups-Agent/pull/2196) | afc0e776 | 21 successful checks; GitGuardian remains failed |
| [TestNet2202](https://github.com/FOUNDUPS/Foundups-Agent/pull/2202) | 12996b82 | 21 successful checks; GitGuardian remains failed |
| [Unsigned codec2206](https://github.com/FOUNDUPS/Foundups-Agent/pull/2206) | adf9633b | 22 successful checks; GitGuardian remains failed |

All three have zero pending checks at observation. The remaining incidents were
source-classified as public commit identifiers or a synthetic public address;
authenticated disposition is still required. No bypass, history rewrite or claim
of merge/publication follows from that classification. Mall root/About/FX links
have preview evidence; this does not establish production-root activation.

The bounded local experiment connects the actual stored FAM TestNet intent to
the unchanged unsigned Algorand codec in a separate SDK process. Its twenty
frozen checks cover stored identity, retry/reopen, absent authority, tampering,
strict requests/results and selected effect/resource controls. Two format calls
match independent golden wire/transaction identity and whole-request binding.
The preexisting accounting tables and reopened full snapshot stay unchanged;
no database transaction spans formatter I/O. The nine total child launches
include five denied effect controls and bounded overflow/timeout controls.

Run001 remains rejected: its internal functional-pass label accompanied an
unexpected host effect and outer exit1. A separate dependency diagnostic reproduced
SQLAlchemy's local hostname lookup; it cannot retroactively identify the original
caller. The revised host explicitly permits one pinned `platform._node` hostname
metadata read, records no hostname, and still denies every other socket/DNS call.
Run002 exits0, completes all twenty checks and records no unexpected host events.
The raw results, source pins and independent-review disposition are bound in the
[compact checkpoint receipt](receipts/FOUNDUPS_BLOCKCHAIN_CHECKPOINT_20261025.json).
Independent review accepts this local known-code result. Raw before-snapshots and
child format stdout packets were not separately retained; temporal/golden equality
rests on pinned executed assertions plus inspected post-state corroboration.

These twenty checks are not added to historical28/173/459 component counts;
those unchanged suites were not rerun. The external scripts/profiles/payloads
are not bundled, so hashes alone do not provide public reproduction. Selected
byte pins and audit hooks do not prove full native/OS, concurrent-writer or
SQLite ATTACH isolation. No deliberate source/profile/executable drift attack
was newly executed. No durable artifact, production worker, signing or chain
submission was introduced. Host dependency declarations remain unratified.

Next: close the security publication gates, then allocate one consumer/artifact
layer using revalidated intent and current host grants. Bind independently admitted
fee/round facts and immutable request/wire identity; verify retry, reopen and
conflict behavior before integrating a signer. Real pilot facts, funding, issuer
authority, confirmations and reconciliation remain separate prerequisites.
Repository-control challenges/admission, ratified reward units/funding, the full
venture inventory, autonomous pitch/video/deck runtime and a funded trading venue
remain open. Nineteen mixed catalog records/five cards do not verify115 FoundUps;
the existing paper DEX/simulator does not establish live markets.

## Intake reference preservation allocation — 2026-10-25

WSP15 C2/I4/D3/Impact4=13/P1; WSP22/50/84/97. Source: main e801a412.
Existing authenticated LaunchRequest validates reference_urls but drops them
while constructing its existing genesis envelope. Preserve their order/values
in a detached prior_art list: one constructor keyword, <=4 production lines.
References remain untrusted draft metadata; no fetch, source identity, repository
control, claim, admission, registry, execution, token or publication authority.

Reuse the two existing launch-request/transport test owners and their fixtures.
Add <=90 lines for dict/dataclass/transport forms, empty defaults and list detachment;
retain all validation/auth/provider/nonce oracles. First run desired behavior
against unchanged production source and retain the actual RED. The existing
whole-source AST pin intentionally changes: preserve the old pin/failure, and
rebaseline only after independent review of the single added constructor keyword.
Do not weaken the AST assertion, denial behavior or existing behavioral cases.

The mapper is already resident: retain1,471 members and all byte/count caps.
Root owns manifest regeneration, exact canonical digest pins and existing generator
test log; qualify generator/parity and unchanged Node membership boundaries.
Budget <=16 existing paths:7 module source/test/docs owners, this plan/root log,
manifest/constants/generator-test/TestModLog, and at most3 existing exact security
metadata owners if actual hosted findings require separately reviewed rebindings.
No speculative exception, new runtime member, dependency, framework or service.
Qwen/Gemma inference is unnecessary for this fixed mapping; attributed source/test
review and direct bounded offline checks provide the relevant evidence.
The four-owner selection now passes601 cases, including all9 new behaviors,
after independent review approved the exact AST pin update. Original validation,
auth and nonce oracles remain intact; desired RED and setup failures are retained.
Published nomination main a44e7864 is reconciled without changing the tested module
inputs. The existing mapper changes the sole resident source digest; membership
stays1,471 and all caps remain fixed. Canonical f427e16b and both existing pins
are updated. Seven generator cases pass initially; the old staged-manifest check
fails until the actual bindings are staged, then its unchanged rerun passes.
The three existing Node entrypoints pass. Current hosted/security publication
gates remain required; neither source delivery nor a draft admits execution.
Actual current-head security job121124347560 reports40 tree findings and zero
unreviewed history findings. All39 manifest source-digest entries reconstruct;
the additional preexisting hostile-input fixture line108 moves to150 unchanged.
Parent rederives every current/prior file/rule/line fingerprint and source hash.
Use only decoded Git blob identity; discard the review's initial raw-response
test fingerprint. Preserve2,220 prior bindings and append only40 (2,260 total)
within the three preallocated security metadata owners. Mapper authorship is
disclosed; independent metadata-diff review passes. Fresh hosted scans remain gates.
Five unchanged security regression cases pass; no scanner, scope, rules, source,
or oracle change is made. The initial hosted failure remains historical evidence.

## Project nomination inbox allocation — 2026-10-25

WSP15 C2/I4/D4/Impact3=13/P1; WSP22/50/84/97/109. Source: main e801a412.
Smallest usable layer: a deliberate person-submitted GitHub issue form, with
GitHub sign-in, durable issue permalink and open/closed conversation status.
Nomination is raw input, distinct from repository control, FoundUp admission,
issuer authority, asset creation and market listing. Issue closure grants none.

Budget: one new <=90-line `.github/ISSUE_TEMPLATE/foundup-project-nomination.yml`,
this existing plan and root ModLog. No new runtime, store, registry, test framework,
label, assignment or custom auth service. Existing launch intake returns only a
draft and drops reference URLs during mapping; address that separate bug later.
WSP109 prepares intake, so this inbox does not claim to execute its full gate.
Qwen/Gemma inference adds no value to this small fixed schema; attributed parallel
source readers and YAML/schema validation suffice. No model/provider calls.

The form captures public project reference, name and Outcome/vision first, then
Solution (including PoC/Prototype/MVP) and Pain/obstacles when known. Anyone may
nominate; public-only acknowledgment and honest proposal wording are required.
No public-key challenge or rights inference. No issue is submitted by this work.
Validate YAML/unique IDs/required fields and independently review the actual form.
Merge and read back default-main template availability before linking an active
Mall/FX shortcut; its existing `public/f/index.html` overlaps pending Mall2196.
This prevents premature UI activation and avoids duplicating intake services.
The55-line form now passes YAML/schema/required-field/order checks and independent
source review. Publication and default-branch availability remain unproved.

## Current-state consolidation allocation (before authoring)

WSP15 C2/I4/D4/Impact4 = **14/P1**. On main
`5be89ae4bb34133d775cd09f273d7781adfebc9f`, reconcile delivered layers,
open PRs, the completed source review and 012's Mall/FX/intake/pitch requirements
in these existing architecture owners. Historical observations below remain dated
evidence. Need: the older delivery state precedes subsequent merged work.
Affordability: documentation only, no new execution plane. Deferral obscures the
remaining prerequisites; copying the three older untracked plans would duplicate
owners and promote stale status. Qwen/Gemma model execution is unnecessary for
source-bound status reconciliation; parallel readers provide attributed evidence.

Budget: this plan at most220 added lines, venue/claim research at most30,
root ModLog at most18, and one compact coverage index at most100KiB/210 records.
No product, test, WSP policy, registry, dependency, runtime manifest, scanner,
ledger, provider, signer, chain or deployment changes. Preserve1471 resident
members and fixed limits. Validate source/link identities, counts, exact scope
and independent review; no runtime test rerun is implied by this docs-only slice.

## Current checkpoint — 2026-10-25 (supersedes status prose, preserves history)

Pre-authoring WSP15 C2/I4/D4/Impact4=14/P1; existing two architecture owners plus root ModLog, max4
files/zero runtime. Observed main `5be89ae4bb34133d775cd09f273d7781adfebc9f`; research source
`182e15bdd7f0be887d3c78c0d55cc2755b69d8f3` has the same tree
`f9abf184dacc65f28ee23458bba713c860df0ec9`. This is a dated readback, not continuing remote
freshness. Earlier allocation, execution-base and receipt terminal states remain historical.

| 012 outcome | Delivered or evidence available | Still required / honest boundary |
|---|---|---|
| Read all WSP/vision and map the architecture | Three readers completed190 allocated paths; gap reader completed18 additional physical versions | All119 canonical WSP-prefixed files and3 framework support documents covered. Bounded vision scope and display exceptions below; no all-repository claim. |
| List the FoundUps, recalling about115 | Current separate audit:19 mixed registry records,5 public project projections,14 media lanes | Different populations; do not add them or claim115 verified ventures/assets. Reuse canonical registry/public projector; publish source/date/classification. |
| Testnet system where accepted work earns tokens/pool allocations | Main has fail-closed mock backend selection and trusted-host scoped verification/initiation; epoch, mock BTC integrity and selected numeric repairs | No real issuance, funded rewards, settlement, live reserve or trade. Unit/rights/funding/authority policy and independent effect/replay/conservation gates remain. |
| Root Play FoundUps Mall, About explanatory page, visible FX | Mall PR2196 local/preview route/auth/cache/browser evidence; `/f/` five-card directory is live | Last verified production root is the old About/gateway. Mall homepage is not merged/deployed to production. Preserve admission search/hash, member/callback, tenant `/f/{id}/app`, Move2Japan exception and scoped SW. |
| Clean Netflix-like browsing/listening | Requested vertical panel rows plus horizontal browsing, tap elevator pitch, scrolling/listening queue, pinch density with accessible zoom | Presentation backlog; not proof existing cards contain audio/video or that media automation exists. Preserve source attribution and actual artifact state. |
| Useful RedDog discovery and participation | Requested1–7 chili/like-hate preferences and organization; hold bottom RedDog push-to-talk; anyone may nominate/join/support/vote | Bounded catalog filtering/sorting only: “show Japanese FoundUps”, “dealing with clones”, “closest to me”. Explicit microphone/locality consent; preferences/votes do not establish CABR, entitlement or authority. |
| Bring any external project into FoundUps | Existing authenticated genesis/intake plus registry/projection owners; fresh claim contract researched | Nomination→repository-control/representative claim→admission→optional issuer grant→confirmed asset→separately funded market. No-code projects possible. No new parallel registry or automatic mint from a URL/key file. |
| Vision-first pitch/deck from RedDog conversation | Source-bound local Move2Japan package:13 sources,5 slides, desktop/mobile rendered QA | Outcome “Wouldn’t it be great if…”→Solution/how/what with nested PoC/Prototype/MVP→Pain/obstacles. Current package has no audio/video; original prototype skill is untracked/absent main, no resident executor/publication. |
| FX token discovery and later exchange | FX metadata/search/readiness view; existing chain-native venue/license comparison; pinned public DAO/Playapp source research | No token deployed or tradable just because it has a ticker/card. Prefer reviewed venue integration over new AMM; exact asset/network/rights/liquidity approvals still required. |

Main delivery facts: epoch PR2192 merged at `7d3d7f64390762040bc2ca737ff0964d94d887c1`; mock BTC
PR2198 at `6fe7eba424c17f7813043dfb104cd845617cab38`; legacy public-repository research PR2200 at
`919beb0ff106fbbe5e94138759e68b3f93477f7c`; numeric PR2201 at main5be above. Numeric final226
focused,28 independent and736 simulator cases pass, with overlapping inventories and named SSE
exclusions. These are bounded local source checks, not aggregate conservation or settlement proof.
Existing exact-ID receipts remain the owners of test detail.

Open exact-head PRs: Mall2196 `3767e36e5b33a54a3f3f6205dec7075a08861461` (39 files); TestNet2202
`8723a28bd7c5c4dd04e63f8202224e9e1177176b` (17 files). Retained snapshots each show37 SUCCESS plus1
GitGuardian FAILURE; strict scopes39/39 and17/17 PASS. Mall latest custom security job121079425887
passes20 regressions, tree0unreviewed/172reviewed and history0unreviewed/3reviewed; this separate
scanner does not resolve GitGuardian. GG38958604/Mall and38962564/TestNet remain
unlocated/unclassified. Known scanner metadata/frontend-ID classification does not resolve those
unknown GG gates; no bypass or ready-to-merge claim.

TestNet intent is a separate local `PREPARED` disposable `TEST_TRANSPORT_PROBE`, not UPS/F_i/reward
conversion, funded reservation or paid settlement. Its affected173, independent16 and all-FAM459
case counts overlap. It has no resident/HTTP/daemon/TokenFactory consumer. Payout remains INITIATED
without tx reference/paid_at, task VERIFIED. Durable records and trusted injected policy are not an
authenticated production host or node observation.

Source binding remains **1,471 runtime members**,1,472 rejected; byte caps328KiB manifest/2MiB
source/32MiB total unchanged. Observed main manifest332,650 LF bytes/335,665 CRLF-equivalent
leaves207 bytes under335,872 cap. Dependency/native experiments are external and do not join this
runtime or change Holo’s packaging-only admission. Do not add imports/exports just to force an
intent facade into reachability.

External dependency chronology: v1/v2 acquisition literal-metadata failures retained; v3 exact15
wheels acquired; pip bootstrap failed on2 unlocated unexpected sockets. A separate
exact1498-payload+7-baseline materialization passed; pytest setup then failed before JUnit/case
results on1 unlocated socket and1 denied `\\.\nul` write. **SDK/native qualification PENDING; actual
direct seven-function attempt FAILED.** One actual isolated-flags function passed; six were not
reached. The new bounded observer located this attempt’s
`packaging.default_environment→platform.machine→uname→_node→socket.gethostname` denial; `_node`
catches PermissionError as OSError, so setup continued until the unchanged post-function guard check
stopped it. Controller0 attempts/all1505 bytes stable. Earlier installer/framework socket callers
stay UNLOCATED. Frozen assertion/guard bytes remain unchanged; no
pip/pytest/runtime/signing/transaction qualification or live effect is inferred.

Subsequent fixed-target direct-v2 qualification passes all seven unchanged functions.
It uses the reviewed CPython3.12.10/WindowsAMD64/no-extras dependency edges and explicit
public tag constructors, avoiding the hostname helper with no guard/vendor/oracle change.
All four intentional denials pass; zero unexpected/controller attempts. Parent rehashes
256 loaded origins,1505 candidate files,4207 base files and209 source files unchanged.
Controller receipt SHA256: `6de7b3757fd05414eb92ff5d4014d7d44c2c7e92a9cf1bfe7f09957595e9a0e8`;
child result: `b7d23c93adfa2c6f16e3b349b903ba3065e7bc5d9bf34eb1b2f007cf8ff0e6fa`.
These are direct assertion checks, not pytest/pip installation, OS/native isolation,
transaction or production-runtime qualification. Prior failures remain as recorded above.

Policy gates before economic issuance/trading: WSP26 nontransferable/bound UPS/Fi versus external
realization/DEX proposals; human UPS versus older agent-UPS examples; fixed21M/adoption release
versus older1000/creator80 drafts; global60/16/4/16/4 versus differently scoped task/activity splits
and passive-Du/event Dao/Un refinements. Ratify an asset-rights/recipient/unit/policy-version table,
liability scope, denominator, rounding/residuals and finite funded release/reservation authority.
WSP27 also says PoC has no tokens while its tier6 example releases5%/1.05M at PoC;
resolve that stage conflict before using maturity labels as issuance triggers.
CABR routes a bounded budget and PoB gates it; neither creates mint rights, treasury capacity or
entitlement. An unspecified aggregate guarantee is not itself a confirmed runtime cap violation.
Preserve disabled economic activation without inventing a new supply or conversion policy.

Coverage: allocation119 tracked WSP-prefixed files plus71 curated vision/Mall/economics/support
paths.119 is not119 active unique numbered protocols. Recursive framework total122 Markdown
equals119 prefix files+3 support docs, not3 missing protocols. Group0:43 canonical/21 curated paths;
group1:38 canonical/25 curated. Group1 read all lines but redacted one secret-like example literal;
WSP31 used NUL-only display cleanup. Group2:38 canonical/25 curated paths, fully read. The190-path
corpus totals58,376 lines/2,564,730 host bytes. All27 tracked Markdown basenames containing vision
were covered across the corpus and six gap additions. Gap separately read both roots’ support docs,
six extra literal vision filenames and bounded original continuity files; do not add its
physical-version count to unique corpus totals. Ten directory-only computer-vision docs and
arbitrary semantic/vendor/nested vision remain unclaimed.

Retrieval: no generation-current Holo proof; retained owner query failed
`HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH` (`ok=false`, `freshness=UNKNOWN`, gap=true). Direct
path/hash reads and module-owner evidence are the fallback, no reindex. Historic operational labels,
mock outputs, aliases/mirrors and dated provider claims are the principal
noise/staleness/duplication; missing real effect evidence stays explicit. Original O untracked
plans/skill are continuity inputs, not canonical main.

Next order: (1) publish this source-bound checkpoint while the existing exact unknown GG gates
remain unresolved; (2) read back and merge Mall/TestNet only after their current gates pass, then
qualify and deploy the exact merged Mall public tree; (3) qualify the fixed-target offline SDK
dependencies, preserving all prior failures; (4) allocate a pure unsigned Algorand probe codec, then
durable exact-artifact/attempt/reissue state before any signer; (5) independently allocate project
nomination/control through the existing intake/GitHub owners after its runtime-footprint review.
Codec inputs still need trusted host
network/genesis/asset/decimals/authority/holdings/freeze/balance/fee/round facts; node snapshot
authenticity is separate, UTC expiry is not automatic on-chain round expiry. Do not
sign/fund/broadcast. Mall presentation improvements can be separately layered after its own
publication, while real rewards/venue trading wait for ratified policy and funded
conservation/replay/reconciliation gates.

References: existing `FOUNDUPS_EPOCH_COMMITMENT_HARDENING_20261025.md`,
`FOUNDUPS_BTC_ANCHOR_INTEGRITY_20261025.md`, `FOUNDUPS_NUMERIC_ADMISSION_20261025.md` and their
exact-ID receipts. Pending Mall/TestNet owners are in their PRs, not assumed main links. The
[coverage index](receipts/FOUNDUPS_WSP_VISION_COVERAGE_20261025.json) records all208 physical read
contexts/205 relative paths and reader report identities; dated PR snapshots remain external
publication evidence; no historical receipt is relabeled as a later run or main verification.

## Generated-manifest security re-review allocation (before binding)

Frozen candidate `80cccc3f7` security job121027671790 reports38 unreviewed
tracked-tree findings, all in the regenerated source manifest:36 generic hash
matches and two Discord-rule hash matches. Introduced history reports zero
unreviewed findings; the hosted security regression suite passes20 cases.
These observations require classification, not a scanner exemption by path.

WSP15 C1/I4/D5/Impact4=14/P1. Need: preserve exact source-binding review on a
changed generated artifact. Budget: verify38 exact line contexts, referenced
normalized Git source hashes and existing main approvals independently, then
append only their new whole-file/rule/line bindings to the existing ledger and
review evidence. Can it wait: it blocks current publication. Competing blanket
hash/path exclusions would weaken detection and are rejected. No scanner,
fingerprint algorithm, source manifest, test oracle or unknown finding changes.
Fresh hosted tree/history scans remain required after the exact review.

## CI integration dependency allocation (before repair)

At candidate `9b9784770`, the hosted security gate passes. The bounded worker
step fails the two existing generated backend manifest parity/index tests.
The changed FAM import closure must be reflected in the existing source
manifest before main convergence; this is part of the original source change.

WSP15: complexity 2, importance 5, deferability 5, impact 4 = 16/P0. Need:
source hashes and runtime membership must remain exact. Affordability: use the
canonical AST-only generator, its existing eight tests and Node compatibility
controls. Deferral would leave CI blocked. The competing move, excluding FAM
from closure or weakening parity, would conceal a real dependency and is rejected.

Execution plane: local generated-source maintenance, not installed activation.
Budget: existing source manifest, shared digest/member constants, existing digest
and exact-boundary test fixtures only as measured, and relevant module/test logs.
No generator algorithm, runtime authority, installed descriptor, release, byte
limit or global scan rule changes. Inspect the generated delta before retaining
it. Keep exact member/+1 rejection if one required dependency grows the closure.
Stage the repaired source artifacts before the staged-index test; then run the
existing generator check, focused Python and Node controls, independent review
and new hosted gates. Do not reuse earlier CI success for a new head.

Reconciliation: parallel main advanced to `03035b4f5` through PR2189. Merge its
brand-grounding contracts and CI without alteration. Preserve both additive doc
sections and the exact reviewed-finding union (1,853 main + this lane's five =
1,858 unique bindings). Recompute the shared manifest digest for the combined
source; the delta against new main remains one member/four source hashes.

Fresh combined-source qualification: eight generator cases pass in 80.48 s
(two inherited inactive asyncio config warnings), and all three existing Node
compatibility/preflight/recovery entrypoints exit0. JUnit evidence:
`foundups-fx-merged-manifest-9a4a69dab5874b698a6c92df77b8910e/results.xml`
in host temp. Independent review verifies all 1,470 staged normalized source
blobs, both digest pins, fixed byte caps, exact member/+1 control and the complete
ledger union; no mismatches or unmerged paths. The earlier 80.23 s run and CLI
generator check bind the pre-merge repair only. New-head hosted gates remain.

Authority: operator requested completion, dedicated PRs and main delivery after
verification. This lane owns FoundUps chain/FX work; unrelated concurrent changes
remain in the original checkout. Base: `8b2fccf64251097b647b7fc5a45dad75706a9192`.

## Start-of-work evidence

- WSP 00 awakening ran; tracker returned `is_zen_compliant=true`.
- Read WSP 97, WSP 15, WSP 50, WSP CORE memory contract, master index,
  session briefings and historical continuity shelf. The old slice ledger is
  historical where newer Git/PR facts contradict it; it is not current PR state.
- Canonical Holo owner query for exchange, repository ownership, verifier,
  treasury and payout tests failed `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`:
  `ok=false`, `freshness=UNKNOWN`, `index_gap_detected=true`. No reindex.
- Explicit degraded retrieval: verified source reads, exact module docs and
  scoped callsites. Noise: older design plans and simulations are not real chain
  integrations. Order: current contracts/source/tests before historical claims.
  Missing: FAM memory README and requirements file on this base. Tier-0 FAM
  README/INTERFACE exist; roadmap, ModLog and test docs were retrieved.
- Fresh main contains atomic pending initiation and verification/replay repairs
  (including PRs 1893/1894). Preserve these rather than reimplementing old gaps.
  Entitlement and settlement are explicitly outside those repairs.
- Execution plane: local source changes and read-only parallel research. No
  resident WRE admission, signer, wallet, provider call or live mint is activated.
  Delegates review exact existing surfaces; no Qwen/Gemma model download needed.

## WSP 15 allocation before implementation

Scores are complexity / importance / deferability / impact; sums use WSP 15.
This record precedes porting P0A or authoring P0B/FX in this worktree. Historical
P0A tests from October 22 are evidence, not fresh validation on this base.

| Work item | Scores | Sum | Priority | Allocation and reason |
|---|---|---:|---|---|
| Trusted verifier/treasury authorization | 4/5/5/5 | 19 | P0 | Security prerequisite for project work rewards. Reuse existing transaction owners and inject server-owned grants; no self-declared profile authority. Research before authoring. |
| Port and publish token factory rejection | 2/5/5/5 | 17 | P0 | Existing reviewed patch; prerequisite to honest adapter selection. One source file, existing orchestrator tests; preserve latest main docs and persistence. |
| FX discovery and project admission | 3/4/4/4 | 15 | P1 | Reuse existing mall/catalog/DEX surfaces. First expose honest discovery; admission/claim is distinct from mint/trading. Inspect current tests before authoring. |
| New AMM/orderbook implementation | 5/3/1/3 | 12 | P2 | Defer custom contracts. Compare maintained existing chain-native venues and pinned licenses first. |
| Autonomous pitch/video/deck providers | 4/3/2/4 | 13 | P1 | Prior creative plan/skill exists; funding/credentials/model availability are separate delivery dependencies. Keep in queue after admission identity. |

Need: absent authority permits paid work to become accepted/rewarded without a
trusted verifier or treasury issuer. Affordability: extend the existing module
and tests without new services, schema, models or signing infrastructure. Can it
wait: real testnet rewards cannot proceed safely without it; cosmetic exchange
work can proceed independently after source/contract review.

Highest-priority P0B first requires revalidation against fresh main and its
existing transaction tests. The smaller, already-reviewed P0A port runs while
that read-only investigation completes; no duplicate persistence repair.

## Layer acceptance and budget

1. **Token selection:** keep default/explicit identified mock; reject unknown,
   unavailable, disconnected or identity-changing backends; reject wrong-chain
   results before caching. Reuse the seven existing orchestrator tests and add
   edge cases in the same file. Run those and the current connected FAM suite.
   Budget: one production file, existing test file, module memory and receipt.
2. **Authority:** deny absent grants, require the exact privileged operation,
   scope and independent verifier before mutations/debits. Read-only profile
   labels and paid compute do not grant authority. Preserve atomic retry and
   truthful pending state. Fix acceptance before product edits. Budget: one
   small internal authorization owner and existing boundary hooks; do not grow
   the oversized SQLite adapter beyond its recorded ceiling. Stop to reassess
   if it requires a new role store, migrations or new orchestration plane.
3. **FX discovery:** make one clear FoundUps Exchange entry/tab backed by the
   existing project identities; distinguish nomination, repository-control claim,
   admitted issuer, token deployment and tradable/liquid market. No placeholder
   price or mock token presented as live. Reuse current browser VM tests.
4. **Repository claim:** a public key committed on the repository's current
   default branch is one control signal, not a complete claim. Bind a fresh
   challenge to repository identity, immutable commit, claimant/key, nonce and
   expiry; require proof of the corresponding private key and recheck control.
   Fork/replay/redirect/private-network cases must reject. Never execute imported
   repository instructions. Define/reuse the intake owner before adding code.
5. **Settlement:** policy, exact network/asset/treasury, bounded signer,
   accounting/proof/replay, confirmation and reconciliation precede one admitted
   testnet contribution/transfer. Discovery and repository control never bypass
   these gates. Venue listing needs separate liquidity/venue approval.

Each implementation layer receives independent review, exact fresh test IDs,
updated module memory and a bounded PR. Merge only after current required checks
and review pass; never force-push main or commit parallel work. The original
checkout is neither reset nor switched. Completion is demonstrated by outcomes,
not aggregate test counts or a planning checkbox.

## Initial P0A/P0B/FX1 delivery snapshot (historical)

- P0A: ported to this base; 49 focused cases pass and are included in final
  connected closure. Default/mock simulation remains identified.
- P0B host context: implemented and independently reviewed. Final connected
  closure690 passes (366 FAM+324 simulator), three unchanged SSE HTTP exclusions;
  independent permission/verification closure115 passes. Counts overlap.
- FX1: implemented, source-reviewed and browser-checked. Worker300 passes and
  independent300 passes use the same existing test owners. Root FX link, ticker,
  readiness and empty-state behavior verified locally; not yet hosted.
- [Venue/claim research](FOUNDUPS_FX_VENUE_AND_PROJECT_CLAIM_RESEARCH_20261025.md)
  evaluates existing protocols and separates repository control from issuer,
  mint, liquidity and market authority.
- Claim, live token, settlement and venue: not complete.

The [delivery receipt](receipts/FOUNDUPS_FX_CHAIN_DELIVERY_20261025.json) records
exact executed node IDs, exclusions, environment isolation and artifact hashes.
All runs have two inherited inactive asyncio config warnings. New source has
no network effect; the final connected runner bypasses unrelated Holo/Qwen help
enrichment and redirects default daemon storage outside the checkout. Independent
115-case and FX300-case runs need no enrichment patch. No test totals here are
security clearance or evidence of real-chain settlement.

Process correction: the worker read fresh simulator source/callsites before its
small compatibility edit, but refreshed the six simulator Markdown memory
artifacts only afterward. Post-edit review found no source contradiction; the
timing gap remains recorded. Future cross-module handoffs must enumerate Tier0
and Tier1 retrieval for every touched module, including compatibility hooks.

### FX1 authorized micro-slice (before authoring)

The current source has 19 typed registry records and five public projections;
these are different inventories, not 115 verified token listings. Existing
`public/f/index.html` already searches ID/name/summary; extend it with optional
declared ticker search. Reuse this public directory owner for FX, rather than
forking member video-search state or inventing token records.

Approved files: root `public/index.html` FX navigation anchor to `/f/`, existing
`public/f/index.html` FX directory framing/search, and the existing tests
`public/member/tests/test_route_contract_bridge.py` and
`modules/foundups/pfmall/tests/test_gateway_roc_shell.py`. Read module contracts
and test logs before authoring; capture actual DOM handlers in the existing VM
test. Update only relevant public/member and pfmall structured memory.

Acceptance: visible accessible FX link; existing gateway/admission routes stay
valid; ID/name/summary/ticker search works, including null symbols; readiness
filter still works; clear empty state and fetch failure; no execution of fetched
markup; declared ticker does not imply deployed asset, liquidity, price or trade.
No new router, registry, profile store, price feed, wallet or trading endpoint.
This independent P1 slice can run beside P0 authorization because it invokes no
privileged effects. WSP15 allocation: C3/I4/D4/Impact4=15/P1.

### P0B authorized micro-slice (before authoring)

Fresh-main research confirms atomic SQLite operations already exist but lack
domain authority. Add a small immutable `CallerAuthorization` with authenticated
host-supplied principal and exact `(foundup_id, role)` grants. Pass it explicitly
as a keyword-only context to task verification and payout initiation. Absence
denies. Validate content/types, principal equality, exact scope/role and verifier
independence from stored proof submitter/assignee. Do not infer grants from
profile, caller IDs, repository control, paid compute or administrator strings.

Approved production owners: new internal `agent_market/src/authorization.py`,
existing interfaces, in-memory implementation, task pipeline, SQLite adapter,
atomic verification owner, and simulator FAM bridge compatibility. Hooks belong
inside existing transactions, including direct adapter initiation and retry;
preserve atomicity and original costs. Simulator contexts originate from its
configured host identities and remain explicitly simulation-only.

Test budget: expand existing `test_permissions.py`; reuse current persistence
and verification helpers, mechanically pass explicit trusted fixture contexts
in existing lifecycle/CABR/distribution/deterministic/E2E controls and simulator
bridge fixtures. Do not auto-grant from the actor under test or wrap all methods
in an accepting fixture. Preserve previous assertion oracles and inventory all
new parameterized controls before running the changed product implementation.
Run baseline, desired negative acceptance, affected suites and independent
review; keep socket/DNS offline and DB/temp paths outside the checkout.

No schema, issuer store, new endpoint or orchestrator. The required trust
boundary is host injection; an authenticated transport/signed entitlement issuer
is still a separate integration. WSP15 C4/I5/D5/Impact5=19/P0; it cannot be deferred
before reward admission. If source/test compatibility exceeds these owners,
document the new dependency and re-evaluate before expanding.
