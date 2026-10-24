# FoundUps FX and blockchain delivery — 2026-10-25

Status: active layered delivery; no testnet or production readiness claim.

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

## Current delivery state

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
