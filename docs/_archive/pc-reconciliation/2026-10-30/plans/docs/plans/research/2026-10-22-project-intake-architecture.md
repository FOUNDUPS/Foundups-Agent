# Preserved historical record: 2026-10-22-project-intake-architecture.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `docs/plans/research/2026-10-22-project-intake-architecture.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `aeac4fa1a78699cf32fe287a25c4ba3061a7c2ea9936c9510348bb008c92788d`
- Preserved record SHA-256: `aeac4fa1a78699cf32fe287a25c4ba3061a7c2ea9936c9510348bb008c92788d`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [intake_host.py](../../../../../../../../modules/foundups/pfmall/intake_host.py), [FOUNDUPS_FX_CHAIN_DELIVERY_PLAN_20261025.md](../../../../../../../architecture/FOUNDUPS_FX_CHAIN_DELIVERY_PLAN_20261025.md)

Disposition: Archive intake design and carry ownership challenges, rename/transfer/fork handling, untrusted input and publication gates to current owners. Current intake_host provides isolated draft intake with explicit policy and public-key verification; that is not a deployed universal project claimant or authorization for external mutations.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content

# External project intake into Play FoundUps Mall

Date: 2026-10-22. Role: reviewer. Origin: internal_handoff.
Scope: architecture research and read-only verification. No product source, registry, public deployment, Git/PR state, credentials or chain state was changed.

## Recommendation

Allow an existing external project to join FoundUps without rebuilding its product in this monorepo. Reuse the existing intake, registry, public projector and FAM adapter boundaries. Add a provider-neutral **nomination and claim variant** beside the current idea intake, with durable claim/admission evidence. Do not turn an arbitrary repository URL into an admitted FoundUp or token deployment authorization.

Anyone may nominate a project. A moderated, clearly **unclaimed discovery candidate** can exist before its maintainers join. Claim verification, admission, token authorization, code execution and market activation are separate transitions. A standing, human-authorized policy can automate subsequent actions within its explicit scope; repeated approval of every permitted run is unnecessary.

This is an alternative to blind token issuance for every discovered repository. The useful broad promise is **any project can apply**, including existing products, services, community projects and ideas without code. The platform need not assume that every project wants a token, that a repository is a venture, or that the nominator represents the project.

## Evidence and current capability

The canonical HoloIndex owner query remains unavailable according to the parent evidence: `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `ok=false`, `freshness=UNKNOWN`, `index_gap_detected=true`, authority HEAD `a519f0ad...` versus workspace `0c81418f...`. This lane used scoped `rg`, NAVIGATION and direct reads; it did not reindex or make a new Git-state assertion.

WSP_00 V2 awakening completed with coherence 0.700 and seven negative detector passes. The separate strict tracker returned compliant. These are bootstrap observations, not identity or financial evidence. WSP 97's evidence/authority distinction and Occam's smallest-layer discipline govern the proposal below.

WSP 106 and WSP 109 were fully read in the previous research lane; their bytes were rechecked unchanged for this task. SHA-256: WSP 106 `c8380eb89088f63ed4a037121d4852816c266382298d7012663b45dc874b4a80`; WSP 109 `21cc5eb038f443e464fcf70f109054760932da81c72bf5b15af14edbd673c0ec`. The prior lane's [coverage manifest](2026-10-21-simulator-wsp-coverage.json) records that full read. New source assessment is scoped to the paths and seams cited here; this report does not claim a fresh full-repository read.

| Surface | Implemented evidence | Limit relevant to external admission |
|---|---|---|
| External project policy | [WSP 106:67](../../../../../../../../WSP_framework/src/WSP_106_FoundUp_API_Gateway_Protocol.md#1-onboarding-api-foundups) defines external project registration; token deployment, staking and DEX are separate domains at lines 156–241. | Its API examples and `ACTIVE` status are specifications. The claimed first implementation at line 729 names `modules/infrastructure/api_gateway/`, which was absent in this checkout's scoped file inventory. No running gateway was established. |
| Documentation intake | [WSP 109](../../../../../../../../WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md), lines 56–77, separates intake from repo creation, Hermes, runtime and tokens/wallets; lines 318–369 allow an external entity and deferred token. | Producing its documentation packet is not project admission or token consent. It describes adding an intake packet to the monorepo, not forcing every external product's implementation into it. |
| Existing idea front door | [launch_request.py](../../../../../../../../modules/ai_intelligence/ai_overseer/src/foundup_genesis/launch_request.py), lines 68–78 and 228–325, validates proposal data and maps to the existing genesis envelope. | The mapped result is always IDEA, UNBOUND and `external_repo_requested=False`. An existing external product should not be silently relabeled as an internal genesis/extraction request. |
| Transport and platform authentication | [intake_transport.py](../../../../../../../../modules/ai_intelligence/ai_overseer/src/foundup_genesis/intake_transport.py), lines 509–598, extracts transport credentials, validates data and returns a draft. [intake_auth_provider.py](../../../../../../../../modules/ai_intelligence/ai_overseer/src/foundup_genesis/intake_auth_provider.py), lines 177–250 and 670–746, supplies nonce stores and verified intake context. | This proves a platform session/invite, not repository control, project representation or token authority. Transport source lines 76–86 explicitly defer concrete surface binding and entitlement. Production must inject the durable nonce store; its per-call in-memory fallback is not a durable invite redemption service. |
| Structured idea parser | [intake_packet_builder.py](../../../../../../../../modules/ai_intelligence/ai_overseer/src/foundup_genesis/intake_packet_builder.py), lines 188–282, builds and validates a dry-run envelope. | No registry, FAM or Hermes write; not a GitHub importer, claim verifier or complete eight-document WSP 109 packet generator. Its fixed `requested_by="012"` is unsuitable as a public claimant identity. |
| Canonical catalog registry | [schema](../../../../../../../../modules/foundups/foundup_registry.schema.json), lines 25–38, 151–180 and 330–371, includes `external_foundup`, nullable `module_path`, and external repo reference. Current registry already has two external entries with no local implementation path. | No stable provider repository ID, claim proof, claim dispute, publishing consent or asset authorization record. `EXISTS` plus symbol is not independently confirmed chain evidence. A URL field can be null under the current external conditional. |
| Registry loader | [foundup_registry_loader.py](../../../../../../../../modules/foundups/src/foundup_registry_loader.py), lines 60–99, reads the catalog registry. | Minimal shape checks and membership are not admission/rights checks. Duplicate IDs overwrite in the in-memory index at line 89; reject duplicates before accepting intake projections. |
| FAM operational registry | [registry.py](../../../../../../../../modules/foundups/agent_market/src/registry.py), lines 28–126, persists FoundUps through SQLiteAdapter. | The create gate checks compute access using supplied `owner_id`, not verified external maintainership or token consent. Static catalog identity and operational SQLite state are distinct existing stores; a new service must declare one admission authority and derive the other view, not create bidirectional competing truth. |
| Public catalog | [projector.py](../../../../../../../../modules/foundups/public_catalog_projector/src/projector.py), lines 75–139, 262–342 and 477–517, derives an allowlisted catalog from the canonical registry. [public/f/index.html](../../../../../../../../public/f/index.html), lines 896–1000, already reads only `/f/public_catalog.json` and gates app participation through `/member/`. | Portfolio eligibility is the selection predicate, not claim verification, consent, visibility or content moderation. Allowlisted values still need semantic/publication validation. Candidate nominations must not be inserted into the admitted registry merely to obtain public cards. |
| Discovery precedent | [pfmall_discovery/INTERFACE.md](../../../../../../../../modules/ai_intelligence/pfmall_discovery/INTERFACE.md), lines 9–57 and 95–116, exposes YouTube candidates with `review_status="proposed"`. | Reuse the proposal/review pattern. Its video/channel schema is not a provider-neutral project or GitHub claim schema. |
| GitHub boundary | [github_api_client.py](../../../../../../../../modules/platform_integration/github_integration/src/github_api_client.py), lines 43–52 and 180–192, reads repository metadata. [reddog_github_permission_probe.py](../../../../../../../../modules/platform_integration/github_integration/src/reddog_github_permission_probe.py), lines 47–75, 104–131 and 155–210, provides a read-only permission snapshot with digest and freshness. | Current repository dataclass drops provider `id`, `node_id`, owner numeric ID and fork lineage. Permission is a control observation, not token authorization. Existing mixed read/write automation must not be invoked by a discovery fetch. |
| Repo provisioning | [interfaces.py](../../../../../../../../modules/foundups/agent_market/src/interfaces.py), lines 120–135, defines repository creation/metadata methods. | Creating a new repository is different from importing the identity and authority of an existing repository. It is not a claim-verification shortcut. |
| Source authority | [source_authority.py](../../../../../../../../modules/foundups/agent/src/source_authority.py) and [source contract](../../../../../../../architecture/FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md), lines 297–316, pin reachable execution authority to `monorepo_poc`; promotion is unimplemented. | Admitting or listing an external project must not falsely promote runtime source authority. External execution remains disabled until its own federation/authority adapter and acceptance gate are implemented. |
| Token factory | [token_factory.py](../../../../../../../../modules/foundups/agent_market/src/token_factory.py), lines 44–52, 204–257 and 259–354, supplies a backend interface and mock deployment bookkeeping. | Only mock is registered by default; unknown/unavailable chain hints fall back. No Algorand backend appears in this enum. No maintainer claim, durable deployment saga or asset receipt reconciliation is supplied here. A test deployment path must reject wrong/unavailable backends instead of treating fallback output as live assets. |

The source has progressed beyond the historical [public discovery audit](../../../../../../../audits/architecture/PLAYFOUNDUPS_MALL_PUBLIC_DISCOVERY_AUDIT_PHASE1.md): projector README lines 9–14 and 57 still say frontend wiring is deferred, while current frontend source already consumes the public projection. Prefer source evidence, then verify the deployed route separately. This lane did not establish live deployment parity. `/f/` source still has `noindex,nofollow` at line 9.

The frontend's `renderEntry` at lines 1235–1249 falls back from `token_symbol` to `foundup_id` and displays a `$` prefix. Do not reuse that rendering for unclaimed candidates: a discovery card must state unclaimed and token absent/deferred, without implying a project-endorsed asset.

## Inventory evidence and its limits

Read-only GitHub connector calls used `github_list_repositories(owner="FOUNDUPS", page_size=100, page_offset=0, include_search_index_status=false)`, then `page_offset=20`. This returned **20 connector-visible repositories: 16 public and 4 private**; the next page was empty. No private identity or metadata is reproduced here, and no repository content or PR was read.

That exhausts this connector-visible result, not necessarily the organization's full inventory. Access scope, provider projection and visibility can limit it. It is not evidence of 20 admitted ventures or 115 FoundUps. Infrastructure, tools, forks and empty repositories are not automatically ventures.

Separately, the checked-in catalog registry contains **16 entities**, including **5 `foundup`, 2 `external_foundup`**, and other platform/service/tool/skeleton types. Three rows meet the projector's portfolio eligibility filter. Those are file counts under current classifications, not active product, token, deployment or legal-entity counts. Neither repository count nor catalog count supports a claim that 115 projects are admitted today.

## Minimal module boundary and authority model

1. Extend `ai_overseer/src/foundup_genesis/` with an additive, provider-neutral external project nomination/claim contract and transport mapping. Reuse `LaunchRequest` validation helpers, redaction and verified platform intake context. Preserve the existing idea envelope invariants; nomination is metadata, not a request to build or execute. Do not broaden a client-authored field into source or token authority.
2. Keep provider metadata/control resolution in `platform_integration/github_integration`. Add a strictly read-only, metadata-scoped adapter which returns stable provider IDs and observed permissions. Its output is evidence for the domain decision. It cannot admit a FoundUp, deploy an asset or execute a repository.
3. Reuse FAM's existing persistence boundary for durable nomination, claim, authorization and admission evidence. These are workflow records, not a second FoundUp registry. Declare the admission transition's authoritative record and its single writer before wiring public writes. The existing canonical registry remains the source of admitted public catalog rows until that contract is deliberately migrated. Require transactional idempotency/outbox for projection/export; never hand-edit generated public JSON.
4. Extend `public_catalog_projector` for **admitted public** projects under explicit visibility/consent policy. If unclaimed discovery becomes public, give its moderated candidates a separate schema and projection with explicit state. A combined browse page may join two projections for display without merging their authorities. Private claim evidence, nomination identity, auth context and member catalog fields stay out of either public payload.
5. Reuse FAM `TokenFactoryAdapter` and the already proposed [testnet orchestration gates](../../architecture/FOUNDUPS_BLOCKCHAIN_TESTNET_ORCHESTRATION_PLAN.md) for authorized deployment/rewards. Do not add another token issuer, ledger, DEX or source-authority resolver to intake.

This needs one bounded intake capability and provider adapter, not a new generic crawler, identity system, repository provisioning platform or parallel registry service. Qwen/Gemma may help classify and summarize candidate metadata after retrieval. A model score cannot establish repository control, consent, public visibility, reward validity or settlement.

## Proposed canonical records and transitions

These records are design requirements, not implemented APIs or migrations.

| Record | Minimum binding | Transition it may authorize |
|---|---|---|
| Project nomination | Internal project/candidate ID; submitting principal or anonymous abuse-control ID; provider-neutral reference list; provenance timestamp/digest; moderation state | Review/hold/reject or publish explicitly unclaimed metadata. No asset or code actions. |
| Provider reference | Provider host + repository numeric ID/node ID; current owner ID/login and slug; aliases; observed visibility; fork parent/network root where available; retrieved-at and metadata digest | Identity resolution and duplicate/lineage comparison. Never project authority by itself. |
| Project claim | Candidate ID, claimant provider subject ID and platform principal; verified control mechanism, role, timestamp/expiry, evidence digest; declared organization delegation; dispute state | Establish a scoped representative claim after policy review. Ownership claims remain distinct from control observations. |
| Rights and publication attestation | Claimant/organization, project ID, attested scope for name/content/listing, external source/license provenance, publication choice, terms/policy version, accepted-at and revocation | Use approved metadata and represent the project's opt-in. A source license alone does not satisfy the project's token-authorization gate. |
| Admission decision | Project/candidate ID → one canonical `foundup_id`; claim/attestation versions; admission policy/version; deciding authority and evidence; integration mode | Create/attach one admitted FoundUp and derive catalog/operational views. `catalog_only` is possible before runtime federation. |
| Automation grant | Admitted FoundUp, authenticated authorizer and delegation, approved actions, repository IDs, network/asset class, treasury/beneficiary policy, budgets/rate limits, policy hash, expiry/revocation | Repeat permitted automatic workflows without renewed per-action permission. Missing/out-of-scope/expired grant fails closed. |
| Asset deployment intent/receipt | FoundUp + grant + immutable terms hash + chain/network + deployer/treasury + idempotency key; actual tx/asset ID, confirmations and reconciliation | Move requested → submitted → confirmed → reconciled, independently from listing/admission. No symbol-only success. |
| Market activation | Confirmed asset identity, explicit trading/liquidity grant, approved pair/venue, funded budget and market policy | Enable test DEX/liquidity only after asset and separate market gates. An admitted project may remain tokenless and market-disabled. |

Suggested state flow:

`submitted nomination → moderated unclaimed candidate → control-verified claim → project-authorized admission → optional authorized test asset → verified earned contribution → optional test market integration`.

Every transition needs immutable provenance and same-key/same-content replay semantics. Same-key/different-content is a conflict. Keep rejected/withdrawn/disputed states, revocation timing, audit and appeal/takedown paths. Admission is not a blanket grant to operate all project repositories.

### Identity, renames, transfers, forks and projects without code

Use an internal durable project ID independent of `foundup_id`, display name, token symbol and repository slug. Key a GitHub reference by provider host plus provider repository ID; retain `node_id` and observed aliases. GitHub's repository API returns these metadata and fork `parent`/`source` relationships. The current local adapter must retain them. [GitHub repository API](https://docs.github.com/en/rest/repos/repos)

On rename/transfer, resolve the current provider identity and compare IDs before updating the alias ledger. Do not identify a project by redirects alone: GitHub documents that redirects can disappear when the old repository name is reused. Recheck claim authority when control/owner changes. A reused slug with a different ID cannot inherit the old FoundUp, claim, asset or automation grant. [GitHub repository renaming](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository), [repository transfers](https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository)

Forks have distinct repository identities. Record parent/network lineage; do not deduplicate a fork into its upstream or inherit the upstream maintainer's claim, trademark, treasury, rewards or governance. A project can have multiple repositories; a repository can support several projects, so overlapping references require explicit review rather than automatic project merge. Duplicate nominations attach to the same reviewed candidate when identity matches; retain submitter provenance without granting duplicate FoundUp IDs or rewards.

A project with no repository uses website/document/community references and an appropriate organization/domain/manual verification route. Source code, permissive licensing and an internal build are not prerequisites for nomination. The claim route must say what it verified; it must not pretend domain control proves every right associated with the project.

### Claim proof and automatic workflows

Platform sign-in identifies a person in FoundUps. GitHub authentication plus repository role/app installation provides a separate observation of current repository control. For an organization-owned project, require the organization's authorized representative/delegation under the admission policy; a collaborator's write permission is not automatically sufficient to authorize a project token.

A GitHub App grant can be narrowed to repository IDs and permissions within its installation. That supports least-privilege automated read/work scopes; it does not itself express token, liquidity or brand consent. Keep the project authorization grant explicit and separate. [GitHub Apps API](https://docs.github.com/en/rest/apps/apps)

After one concrete authorization, an owner may permit automatic test asset deployment, approved contribution workflows and bounded test distributions. The runner records the grant/version used, checks revocation at the defined action boundary, and enforces network, asset, signer, fee and budget limits. Changing network, beneficiary policy, token terms, issuance cap or market scope requires a new grant. Do not ask again merely because another authorized run starts.

Importing the URL, installing an app, obtaining a source license, holding a token, making a fork or nominating a project must not silently produce this grant. Name the distinction in the product flow: submitter, verified controller, authorized project representative, contributor and beneficiary can be different principals.

## Untrusted input and publication gate

Discovery is metadata retrieval, not execution. Fetch GitHub metadata through a fixed provider API, with parsed/validated owner/repo identifiers or provider IDs. Do not pass arbitrary supplied URLs to an unrestricted server fetch. Enforce HTTPS/host allowlists, credentials prohibition, redirect and DNS/IP validation, private/loopback/link-local/metadata-address rejection, and bounded response size/time/depth. Revalidate every redirect destination; a URL validator for display is not an SSRF guard for a future fetcher.

README text, descriptions, issues, images and links are untrusted source material. Bound and sanitize display; preserve provenance; do not follow their embedded instructions, run shell commands, clone/install/build/test the project, trigger GitHub Actions, load remote active HTML or execute hooks for discovery or claim verification. If execution is later authorized, use the existing governed work-order and sandbox boundary with a pinned revision and scoped grant.

Public nomination does not publish private repository metadata or claim evidence. Default private sources to held/private review; require an authorized publication choice for each public field. Apply abuse/rate limits, malicious-link/content moderation, impersonation disputes and takedown handling before an unclaimed candidate is public. The public schema should deliberately exclude nomination emails, claimant identity proofs, signatures, installation details, member eligibility, treasury keys and raw auth evidence.

The current projector allowlist limits field names and drift; it is not proof that the underlying values are public, licensed, safe, consented or current. Add publication eligibility and URL/content validation at the candidate/admission boundary, with projector guards for the approved state. Reject duplicate identities instead of allowing dict-index overwrite. Distinguish `unclaimed`, `claimed`, `admitted`, `token deferred`, `test asset confirmed`, and `market enabled` in projections; no misleading token fallback on unclaimed cards.

## Ordered implementation slices and acceptance gates

| Order | Small slice | Acceptance evidence |
|---|---|---|
| 0 | Ratify authority/state contract and reconcile stale docs | Nomination, claim, admission, source authority and token consent are distinct. Existing idea intake invariants remain intact. Catalog/admission single writer and projection direction are explicit. |
| 1 | Add nomination dry-run beside existing intake | Existing project URL and project without code produce safe draft candidates; forged auth/source/token fields fail. No registry write, execution, repo creation, asset or public publication. |
| 2 | Add read-only provider identity adapter and duplicate resolution | Provider IDs survive rename/transfer; slug takeover does not inherit claim; fork lineage is distinct; ambiguous projects require review. SSRF, redirects, huge/malformed input and README instruction cases fail safely. |
| 3 | Persist moderated candidate and verified claim | Durable uniqueness/replay constraints, isolated publication state, current controller evidence, organization delegation, rights/consent and dispute/revocation paths. Private metadata cannot enter public projection. |
| 4 | Admit one external project without rebuilding it | Single admitted ID and canonical registry export; metadata-only mode supported; current `monorepo_poc` runtime source authority is not promoted. Project can remain tokenless. |
| 5 | Public browse candidate/admitted projections | Explicit labels, no implied endorsed token, no member/claim leaks, deterministic generation and drift guard. Deployed JSON MIME/body/route parity verified independently from local tests. |
| 6 | Bind standing authorization and one test deployment | One owner-approved grant, explicit chain/network, durable deployment intent/outbox and confirmation/reconciliation; unavailable backend fails closed; restart/retry cannot deploy twice. No real-value assertion or market activation. |
| 7 | Attach one project-authorized contribution to test rewards | Reuse the main plan's durable verified-work receipt, beneficiary binding, independent verification, integer conservation, no double entitlement and settled balance evidence. Nomination/star/fork alone earns nothing unless a separately approved reward category says so. |
| 8 | Optional bounded test DEX/liquidity | Separate market authorization, confirmed asset and pair identity, scoped funded budget, quote/slippage/fee policy and repeat-safe settlement. No automatic liquidity promise from project admission. |

Existing upstream tests are not sufficient acceptance for this proposed chain. In particular, a dry-run intake result or admitted registry row cannot bypass the main plan's accounting, execution-authority and settlement gates.

## Local validation and retrieval evaluation

Safe focused command, from repository root, with generated scratch files outside the checkout:

```powershell
$taskTmp = Join-Path $env:TEMP ('foundups-intake-research-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskTmp | Out-Null
$env:TMP=$taskTmp
$env:TEMP=$taskTmp
$env:FOUNDUPS_DB_PATH=Join-Path $taskTmp 'foundups.db'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
$env:AI_OVERSEER_HEAVY_TESTS='1'
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider --basetemp (Join-Path $taskTmp 'pytest') modules/foundups/public_catalog_projector/tests/test_projector.py modules/foundups/agent/tests/test_source_authority.py modules/ai_intelligence/ai_overseer/tests/test_intake_packet_builder.py modules/ai_intelligence/ai_overseer/tests/test_intake_transport.py modules/ai_intelligence/ai_overseer/tests/test_intake_auth_provider.py modules/platform_integration/github_integration/tests/test_reddog_github_permission_probe.py
```

Observed: **416 passed, 1 failed in 2.40s**, exit 1. Failure: `test_intake_packet_builder.py::test_openclaw_dispatch_simulation` at line 184 expects `NOT_READY` for no envelope, but current `dispatch_foundup(None, ...)` returns `FoundUp mutation denied: authenticated commander authority is required...`. Both calls hit the current authorization rejection; the first assertion merely checks absence of `NOT_READY`, so it does not demonstrate successful authorized dispatch. Update that fixture and assert the intended authorized branch before using it as integration evidence. No source/test fix was made in this research slice.

An initial same-four-surface run without the heavy-test opt-in yielded 7 passed, 1 failed, 124 skipped. `ai_overseer/tests/conftest.py` applies a basename allowlist to all collected items; mixing paths caused unrelated pure tests to be skipped. The second scoped command enables the opt-in for the explicitly named local tests, not the whole legacy suite. The GitHub permission tests use mock backends; no GitHub mutation or real signer test was performed.

| Retrieval dimension | Finding and correction |
|---|---|
| Noise | `candidate`, `token`, `claim` and `registry` hit voting, OAuth and unrelated runtime code. Narrowed searches to `foundup_genesis`, FAM, registry/projector and the existing GitHub integration. |
| Ordering | Policy and current contracts preceded capability claims. Current frontend source corrects historical audit/README claims. GitHub connector was preferred for metadata; official primary docs informed identity/redirect/installation design. |
| Missing artifacts | Projector has no ROADMAP, tests README/TestModLog or memory README in the reviewed inventory. GitHub ROADMAP and memory README are templates. None was invented for a research-only task. |
| Staleness | WSP `ACTIVE` and module `Production Ready` labels do not prove the proposed endpoint, external source authority or chain backend exists. Local source does not prove deployed route parity. |
| Duplication | Existing idea intake/auth/transport, FAM persistence, GitHub control probe, discovery review precedent and catalog projector cover much of the shape. Extend them; do not add a second FoundUp registry, issuer or ledger. |

The next useful implementation is a dry-run external nomination with an explicit claim/admission contract. It can prove outside-project onboarding semantics before any public card, code execution or test asset is created.
