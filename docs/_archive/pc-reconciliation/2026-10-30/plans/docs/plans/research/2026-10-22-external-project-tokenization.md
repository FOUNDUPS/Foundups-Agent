# Preserved historical record: 2026-10-22-external-project-tokenization.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `docs/plans/research/2026-10-22-external-project-tokenization.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `2ede2a723ae5a7d14478ea304562de6a39b4a505351b4e7a0b5eaf3630ce9c32`
- Preserved record SHA-256: `2ede2a723ae5a7d14478ea304562de6a39b4a505351b4e7a0b5eaf3630ce9c32`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [FOUNDUPS_FX_CHAIN_DELIVERY_PLAN_20261025.md](../../../../../../../architecture/FOUNDUPS_FX_CHAIN_DELIVERY_PLAN_20261025.md), [intake_host.py](../../../../../../../../modules/foundups/pfmall/intake_host.py)

Disposition: Archive external-project/DAO2 research. Carry issuer authority, repository ownership, endorsement separation, replay, transfer and recovery requirements to current owners. External protocol claims are dated research; no live issuer or ownership proof is established.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content

---
title: External project tokenization and DAO2 evidence
date: 2026-10-22
status: research_and_proposed_gates
scope: external_project_intake_and_optional_solana_devnet_adapter
role: reviewer
origin: internal_handoff
tags: [foundups, tokenization, Solana, DAO2, WSP109, WSP106, testnet]
---

# External project tokenization and DAO2 evidence

**Decision:** Autonomous creation of a project token on Solana is technically possible after project authority, token terms, network and spending authority have been admitted. Submitting a public GitHub URL supplies none of those permissions by itself. Extend the existing chain-agnostic intake and FAM adapter boundaries; keep the established Algorand settlement pilot. A separately authorized Solana Devnet experiment can test the same admission and receipt contract without making Solana the platform's default chain.

**DAO2 remains unverified in this checkout.** The principal reports an existing FoundUps token, but the allowed repository searches found no canonical DAO2 network, mint, issuer or deployment record. No ticker search was substituted for that identity. Existing DAO2 should first be admitted as an existing asset, if its identity and intended role are verified; creating a new token with the same symbol would create another asset.

This is a research artifact. No keys, wallets, transactions, deployment, funds, Git mutations or PR operations were performed. No chain account or live RPC state was queried. Public documentation establishes protocol capabilities; it does not establish DAO2's properties or this repository's deployment status.

## 1. Local evidence and limits

| Surface | Exact repository evidence | Interpretation |
|---|---|---|
| DAO2 and Adobe | Scoped `rg` searches for `DAO2`, `DAO²`, `DAO₂` and `Adobe` returned no paths. A broader allowed-text inventory search also returned no paths. Exclusions are recorded below. | DAO2 is a principal-reported asset with unresolved identity. Adobe is an unspecified example; no Adobe repository, license, maintainer or token is selected here. Absence from this search is not proof of global nonexistence. |
| Existing chain direction | `NAVIGATION.py:511` onward routes to WSP 26's Bitcoin reserve / Algorand token-contract / off-chain agent design. [The existing orchestration plan](../../architecture/FOUNDUPS_BLOCKCHAIN_TESTNET_ORCHESTRATION_PLAN.md) and [chain evidence report](2026-10-21-blockchain-architecture.md) identify the Algorand pilot and mock-only execution seams. | This question does not require replacing that architecture or implementing multiple settlement chains together. |
| FAM factory | `modules/foundups/agent_market/src/token_factory.py:44` defines chain types; `:50` labels Solana `Future`; `:77` defines `ChainBackend`; `:118` implements the mock; `:215` registers it. | There is a useful adapter seam, but no implemented Solana backend in this file. |
| Factory gaps | The same file's `:233` selection can fall back from an explicit unsupported/disconnected chain; `:212` and `:292` retain deployment mappings in process memory; `:342` synthesizes a treasury string. | A future explicit Devnet selection must fail closed, persist deployment identity and use actual chain accounts. A successful mock result cannot satisfy a Solana admission gate. |
| Trade | `modules/foundups/trade/README.md:22` requires adapter-driven, chain-agnostic design; `:37-42` declares no-money/dry-run, no real execution and no payouts; `:162-166` lists Solana venues as Planned. `src/scoring_integration.py:168-169` creates synthetic addresses. | Market fixtures and desired launchpad adapters are not token creation, liquidity or trading integrations. |
| API vision | WSP 106 `:74` sketches FoundUp registration; `:189` uses the example `algo:ASA_12345`; `:569` signs method/path/timestamp/body hash; `:729` names `modules/infrastructure/api_gateway/` as a first implementation. `Test-Path` for that module returned `False`. | The gateway examples are a specification, not an existing autonomous token deployment service. Timestamp signatures alone do not define durable business-operation replay protection. |
| Intake policy | WSP 109 `:71` excludes token/wallet creation; `:334` sets `TOKEN_DEFERRED`; `:535` excludes catalog mutation; `:679-681` permits explicit forks while excluding inherited token/governance state without downstream authorization. | Intake produces a proposal. Token admission must be a separate downstream slice, and forks need their own identity and authority. |
| Actual public proposal handling | `modules/ai_intelligence/ai_overseer/src/foundup_genesis/launch_request.py:70` allows proposal fields including `reference_urls`; `:284` requires a trusted intake context; `:293` builds an envelope; `:325` forces `external_repo_requested=False`. | A URL is reference material, not repo-control proof, source authority, entitlement or mint authority. Preserve this boundary. |
| Existing authentication donor | Sibling `intake_transport.py:12-19` separates headers/cookies from body authority and returns drafts without effects; `:565` calls the existing verifier once. `intake_auth_provider.py:177` defines atomic nonce consumption; `:224` supplies SQLite durability; `:620-660` verifies and consumes a single-use invite. | Reuse the authenticated-subject and durable replay patterns. Authentication to submit an idea still does not prove repository or treasury ownership. |

WSP 97's execution and verification boundaries apply throughout: a plan, declared role, source link, mock address, command result or structural validation cannot establish project endorsement or a completed on-chain effect. WSP 106 describes a downstream API ambition; WSP 109 deliberately narrows the intake contract. Their different scopes should not be collapsed into an automatic mint-on-intake behavior.

## 2. What must be verified for existing DAO2

| Field | Current evidence | Required admission evidence |
|---|---|---|
| Claimed name/symbol | Principal says DAO2 / FoundUps token | Preserve as a claim; obtain canonical public project reference linking the intended asset identity. |
| Chain and network | UNKNOWN | Chain namespace, actual network/cluster and network identity; no inference from ticker. |
| Mint/asset identifier and token program | UNKNOWN | Canonical mint address plus owning token program if Solana, or that chain's native asset identifier. Independently read current public state. |
| Decimals, supply and extensions | UNKNOWN | Current parsed mint state at a recorded slot/block and commitment; enumerate extensions and their authorities. |
| Mint, freeze and metadata authorities | UNKNOWN | Record each separately, including revoked/absent authorities, multisig/program controls and proof of any authority FoundUps proposes to exercise. |
| Treasury and spend authority | UNKNOWN | Actual token account/owner, sufficient balance and a scoped authorization; a reported holding is not authorization to spend it. |
| Project endorsement | UNKNOWN | A verified FoundUps authority links the exact network + asset and defines its permitted role. |
| Liquidity, pools, routes or redemption | UNKNOWN | Independently verified pool identities, reserves/routes and explicit policy, if that later scope is requested. No bridge or redeemability is inferred. |

If DAO2 is verified as a Solana token, first support read-only asset admission using its existing mint. If its mint authority is absent, new DAO2 issuance is unavailable through the normal mint instruction; authorized holders may still transfer their own spendable balances. If it is on another chain, use that chain's adapter. Do not remint, wrap, bridge, redenominate, substitute it for UPS, or promise conversion merely because a ticker exists. Solana's production guidance specifically treats mint-address allowlists as necessary because identical names and symbols can be spoofed. [Solana production readiness](https://solana.com/docs/tools/production-readiness).

Whether admitted DAO2 becomes a reward asset, community/governance asset, or a possible trading-pair asset is a separate economic decision. None of those roles follows from asset existence. Each would require an explicit treasury policy; a trading pair additionally requires suitable funded liquidity.

## 3. Current primary protocol facts

Verified against official documentation on **2026-10-22**. These are capabilities and requirements, not actions performed in this lane.

| Question | Verified fact and consequence |
|---|---|
| What creates a Solana token? | A mint account owned by the chosen Token program identifies the asset and records decimals, current supply and optional mint/freeze authorities. Creating/initializing that mint and issuing units are distinct instructions. A display symbol is not the identity. [Create a mint](https://solana.com/docs/tokens/basics/create-mint). |
| Who controls supply? | Current mint authority authorizes further issuance; freeze authority controls freezing token accounts. `SetAuthority` can rotate supported authorities, while setting an authority to `None` permanently removes that authority. Select and document each control rather than automatically revoking them all. [Set authority](https://solana.com/docs/tokens/basics/set-authority). |
| Where do name and symbol live? | The base mint is not its descriptive metadata. Metaplex metadata supports original Token and Token-2022 assets; Token-2022 also supports metadata extensions. Its metadata pointer, metadata update authority, URI and extra fields need their own policy and storage budget. Metadata cannot authenticate the upstream GitHub project. [Create a mint](https://solana.com/docs/tokens/basics/create-mint), [Token-2022 metadata](https://solana.com/docs/tokens/extensions/metadata). |
| Which test network? | Devnet is intended for application development with testing SOL; Testnet primarily serves validator/network testing. Devnet assets have no mainnet value and the network may reset. Public RPC endpoints are rate-limited. Production is a separate network and deployment. [Clusters](https://solana.com/docs/references/clusters). |
| What does creation cost? | Transactions incur base fees, currently 5,000 lamports per signature, plus any priority fee. Relevant mint, metadata and recipient token accounts also require rent-exempt funding based on their allocated sizes. There is no universal flat token-launch price. Estimate the exact transaction with `getFeeForMessage` and account sizes with `getMinimumBalanceForRentExemption`; failed execution can still consume transaction fees. Initial liquidity is separate capital. [Fee structure](https://solana.com/docs/core/fees/fee-structure), [fee RPC](https://solana.com/docs/rpc/http/getfeeformessage), [rent RPC](https://solana.com/docs/rpc/http/getminimumbalanceforrentexemption). |
| What proves completion? | `processed`, `confirmed` and `finalized` are different commitment levels. Record the selected level and observed slot. A submission signature or low-commitment observation is not final registry admission. This proposal uses `finalized` for admitted asset identity. [RPC commitment definitions](https://solana.com/docs/rpc). |
| What happens on timeout? | Recent-blockhash transactions expire. Persist the blockhash and `lastValidBlockHeight`; reconcile status/account state and establish expiry before replacing an uncertain operation. Matching fetch/simulation preflight commitments avoids common confirmation errors. A business action still needs its own durable deduplication. [Transaction confirmation and expiration](https://solana.com/developers/cookbook/transactions/confirmation). |
| Does creation make it tradable? | Raydium's CPMM flow requires both mint addresses, enough of both assets to seed liquidity, an initial price/deposit ratio and funding for creation. Search/indexing follows pool creation. This is an additional funded operation. [Create a CPMM pool](https://docs.raydium.io/user-flows/create-cpmm-pool). |
| Does Token-2022 work everywhere? | Raydium's current support varies by program and mint extensions; CPMM/CLMM enforce extension allowlists, while AMM v4 requires classic Token mints. Compatibility must be checked for the selected mint and venue, not inferred from the Token-2022 label. [Token-2022 support matrix](https://docs.raydium.io/reference/token-2022-support). |
| Is a pool automatically a useful route? | Discovery, pool state, quoting, fees, slippage and route assembly are separate integration concerns. An on-chain pool does not guarantee a particular wallet/aggregator listing, execution quality or demand. [Raydium aggregator integration](https://docs.raydium.io/integration-guides/aggregator). |

**Supply-cap implication for FAM:** `TokenTerms.max_supply` is not a native SPL mint maximum-supply field. With mint authority retained, supply can increase. A fixed-supply pilot can issue the explicitly authorized initial supply and revoke mint authority under its approved policy; continued issuance needs an enforceable authority/program policy. Rewarding orchestration can instead transfer from an already funded treasury. This is a proposed contract boundary inferred from the mint data model, not an implemented cap in this repository. [Mint fields](https://solana.com/docs/tokens/basics/create-mint).

## 4. Project identity, ownership and endorsement

A public GitHub repository is not automatically open source: reuse permissions come from its license, and without a license default copyright restrictions remain. Repository visibility and GitHub's ability to fork are insufficient to infer arbitrary reuse rights. Record the actual license at a pinned revision rather than assuming that a URL or an “open source” description settles it. [GitHub licensing documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

Proposed FoundUps admission policy distinguishes:

1. **Upstream-endorsed FoundUp:** independently verify the submitting principal controls the claimed repository/organization or has a documented delegation covering this token proposal. Record an explicit approval bound to the immutable repository ID, revision and token terms. A verified GitHub account alone proves neither project control nor financial authority.
2. **Legitimate independent fork:** record the submitting principal's controlled fork, upstream lineage, applicable license/attribution and differentiated intent. A fork can be admitted under its own identity where policy permits; it must not impersonate upstream endorsement or inherit upstream token/IP/governance rights. This follows WSP 109 `:679-681`.
3. **Reference-only submission:** an idea may cite an upstream repo without controlling it. Keep it at intake/reference status until a separately authorized identity and implementation boundary exists. Do not automatically publish an “official” token for the cited project.

An optional proof method is a short-lived challenge signed/acknowledged through a verified repository authority channel, cross-checked against provider permissions and the immutable repository ID. Exact proof mechanics require an implementation decision; an arbitrary file in a pull request, copied README, commit author name or reference URL alone is not proof. Consent must specify what the token represents; no source-code ownership, revenue share or redemption right is created by attaching repository metadata to a mint.

No exact Adobe project was identified in the permitted local evidence. Treat “an Adobe open-source project” as an unspecified example at reference-only status until an actual repository and intended relationship are provided.

## 5. Smallest autonomous path

Keep WSP 109 intake free of effects. Add one downstream admission path, with autonomy bounded by an already approved policy and spending delegation. This need not require a fresh manual approval for every operation inside that delegation; intake itself must never grant the delegation.

| State | Evidence required to advance | Effect boundary |
|---|---|---|
| `INTAKE_DRAFT` | Existing proposal schema, trusted authenticated subject/invite, duplicate discovery | Reuse current intake. Reference URL remains untrusted data. No asset or registry publication. |
| `PROJECT_AUTHORITY_VERIFIED` | Provider + immutable repo ID, canonical URL, pinned revision, license evidence, verified principal/delegation, upstream/fork relationship | Admit a specific project relationship. Recheck owner/permissions after repository transfer or material authority change. |
| `TOKEN_PROPOSAL` | FoundUp ID, terms version/hash, chain/network/program, name/symbol/decimals, integer initial supply and issuance cap policy, treasury/beneficiaries, mint/freeze/metadata controls, extension allowlist | Produce a reviewable token intent; this is distinct from asset existence. Duplicate symbols do not merge identities. |
| `AUTHORIZED_DEVNET` | Project-bound consent, server-issued nonce, expiry, policy/delegation ID, fee/rent cap, exact network and recipients, bounded sponsor budget | Authorize this test operation. Mainnet and liquidity remain separate scopes. Durable unique operation key is claimed atomically. |
| `SUBMITTED_UNKNOWN` | Persisted deployment record, chosen mint public identity, protected signer reference, transaction signature/expiry and intent hash before broadcast | Submit only through the selected adapter. Timeout remains unknown until reconciliation; do not create a replacement mint. |
| `FINALIZED_VERIFIED` | Independent read confirms exact mint owner/program, decimals, supply, authorities/extensions and intended treasury holdings at finality | Confirm the asset actually matches the authorized intent. Mismatch quarantines the record and blocks registry admission. |
| `ASSET_REGISTRY_ADMITTED` | Durable receipt binds FoundUp + terms hash + chain/network + mint/program + finality observation | Registry stores an actual asset identity, with Devnet clearly marked. Existing DAO2 follows a read-only variant rather than minting again. |

After that, **treasury funded**, **work accepted**, **allocation approved**, **reward settled**, **liquidity funded**, **pool created**, **route verified** and **project endorsed** remain separate facts. A token can exist with zero supply, supply can sit outside the reward treasury, and a funded reward treasury can exist without any DEX pool. Accepted orchestration earns an authorized claim only under the selected reward policy; settlement requires an independently verified transfer receipt.

Minimal implementation allocation, for a later authorized slice:

- Extend FAM's existing `ChainBackend`/`TokenFactoryAdapter` with an explicit network-aware result and fail-closed selection; use the proposed durable asset/deployment registry rather than another JSON catalog or a second token factory.
- Reuse intake's trusted-context and atomic nonce patterns. Add project-control verification and token-effect admission downstream; do not broaden the public proposal allowlist to accept self-asserted authority.
- Start with a local validator/mock contract test and one admitted project on Solana Devnet. Use a normal Token mint unless a specific approved Token-2022 feature is required; if extensions are selected, pin the exact set and relevant authority/venue compatibility.
- Confirm one token admission, then one capped treasury-to-beneficiary test transfer tied to one accepted work claim. Compare receipt/accounting semantics with the Algorand pilot. Do not add automatic DEX creation to this slice.

Ordinary Token/Token-2022 minting does not implement the simulator's verified-work rules, pool allocation, vesting, exit conversion or UPS decay. Those remain off-chain policy and separately scoped settlement/application logic until implemented and proven. Do not use transfer-fee or UI-scaling extensions as substitutes for the canonical economic model.

## 6. Identity, replay and recovery contract

Canonical asset identity should contain chain namespace, network/genesis identity, token program where applicable, and native mint/asset ID. Canonical project identity should contain provider and immutable repository ID, with URL as a mutable display locator. A Devnet reset invalidates the corresponding observations; it never promotes them to mainnet.

The proposed durable operation key binds `foundup_id`, project relationship, action type, terms version/hash, target network/program and logical issuance/allocation ID. It must be stable across transport retries. A nonce prevents request replay; a unique business key prevents duplicate operations under a fresh nonce. Concurrent workers must claim that key atomically, persist the selected mint identity and signed intent, and recover the same operation after restart. Changed terms require a new explicit version/admission, not silent reminting.

For creation, reuse the same persisted mint identity on recovery and check its current owner/state; never generate a fresh mint because an RPC response was lost. Where transaction limits permit, create, initialize and perform the authorized initial issuance atomically so initialization cannot be mistaken for completion. If issuance is separate, `MintTo` is a non-idempotent business effect and needs its own receipt/key. Retrying with a fresh blockhash is not proof the earlier issuance failed. Reconcile all known signatures, expiry and observed mint/treasury state before resubmission; keep ambiguous cases quarantined. An on-chain idempotency/escrow program is a later option if stronger multi-worker settlement guarantees are needed.

Record request/authority provenance, intent hash, approved integer amounts/decimals, network, program, mint, recipient token accounts and owners, fee cap, signature, expiry, observed slot/commitment, pre/post balances and terminal result. Keep secrets and serialized signed transactions out of public logs. Claims, mock receipts and submission acknowledgements must not be shown as funded/finalized payouts.

| Abuse or failure | Required boundary |
|---|---|
| Same ticker/logo, copied project metadata, fake DAO2 | Verify exact asset identity and project authority independently; display upstream/fork relationship and authority state. Never resolve a reward asset by symbol alone. |
| Intake spoofing or prompt injection in README/issues/metadata | Treat external text as data. Preserve trusted context, allowed fields and WSP 97 effect gates; external instructions cannot authorize minting or spending. |
| Repo redirects, transfer, renamed owner or compromised authority | Pin immutable ID and revision, revalidate ownership/delegation before effect, and quarantine conflicting evidence. Do not equate commit attribution with control. |
| Sponsored-fee spam and duplicate project submissions | Per-principal/project/network quotas, bounded fee/rent budget, atomic deduplication, duplicate/fork triage and revocable sponsor delegation. Public submission must not open an unlimited faucet. |
| Arbitrary metadata URLs, source code or program IDs | Allowlisted fetch/network behavior, bounded content, no execution of submitted repository code during authority verification, approved token/metadata programs and extension sets. |
| Authority/extension change after admission | Refresh relevant state before issuance/transfer or pool approval; block unexpected freezes, delegates, transfer fees/hooks or update authorities. A registry snapshot is not perpetual verification. |
| Timeout, RPC disagreement or restart | Persist before broadcast, reconcile signatures and expiry, require finality/read-back, and recover by stable operation identity. No blind remint or double reward. |

## 7. Decision matrix

| Option | Decision for current plan | What must precede effects |
|---|---|---|
| Continue Algorand LocalNet/TestNet reward pilot | Preserve existing plan | Its existing identity, canonical accounting, durable replay, funding and independent receipt gates. |
| Add Solana Devnet proof of the common admission/receipt contract | Feasible optional bounded adapter lane | One admitted project, explicit program/authority terms, capped test budget and fail-closed persistent adapter. No implementation is supplied by this report. |
| Register existing DAO2 without minting | First appropriate DAO2 step once public identity is supplied | Verify network + native asset ID, current authorities/metadata and intended FoundUps role. Current status remains UNKNOWN. |
| Reward contributors with existing DAO2 | Separate funded settlement proposal | Verified asset, authorized spendable treasury, beneficiary binding, integer-unit budget, accepted-work policy and replay-safe transfer evidence. |
| Mint a token for every submitted public repo | Unsupported admission policy | Submission must first pass relationship/authority/license/duplicate checks. A reference-only idea cannot authorize an upstream-branded asset. |
| Pair tokens with DAO2/SOL or launch a DEX market automatically | Defer from this pilot | Verified assets, venue/extension compatibility, separately authorized real funding and pricing, LP ownership, slippage and recovery policy. |
| Bridge DAO2/UPS or promise BTC conversion | Outside current scope | Independently specified reserve/custody, liabilities, conversion and bridge model. No such rights follow from minting. |

The next concrete specification is an **asset admission and deployment receipt contract**, shared by Algorand and optional Solana adapters. Its first review fixture should include one verified project, one intentional fork and one spoofed duplicate, then exercise duplicate requests, concurrent workers, changed token terms, restart after broadcast, unexpected authorities, network mismatch and finalized-state mismatch. These are proposed acceptance cases, not tests executed here.

## 8. Retrieval evaluation and coverage

WSP_00 V2 was executed from the repository root for this lane: 7/7 negative witness passes, coherence 0.772 and resonance 7.05 Hz. The separate tracker returned `is_zen_compliant=true`, last validation `2026-10-22T03:18:19.263139`. These script observations provide no token/project authorization.

The parent reports the canonical HoloIndex owner query remains rejected with `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `ok=false`, `freshness=UNKNOWN`, `index_gap_detected=true` (authority `a519f0ad...`, workspace `0c81418f...`). This lane used `rg`/direct reads and did not reindex or attempt to repair the shared authority. No Git commands were run for this lane.

| Dimension | Evaluation and correction |
|---|---|
| Noise | Generic “token” includes authentication credentials and trade fixtures. Searches were scoped to explicit names/module/docs, excluding `.env`, credential/secret surfaces, transcripts/conversations, vendor/runtime dependencies and generated/nested worktrees. The broader inventory search also excluded token-named JSON to avoid sensitive token stores; consequently its negative result is not an exhaustive asset-record proof. |
| Ordering | Canonical WSPs and NAVIGATION/module contracts preceded source assessment; implementation and official protocol documentation outrank examples and aspirational README claims. Existing chain findings were reused through the dated evidence report. |
| Missing artifacts | No permitted local DAO2/Adobe identity evidence was found. The WSP 106 API gateway module is absent. A Solana backend and real DEX adapter are not present in the reviewed factory/trade surfaces. Missing deployment evidence remains unknown, not inferred from synthetic addresses. |
| Staleness | Historical chain-agnostic/Hedera/EVM/Polygon references coexist with the stronger Algorand design direction. Solana/DEX capabilities were checked against current primary docs; Token-2022 compatibility is venue/program/extension specific and must be rechecked during implementation. |
| Duplication | Canonical WSP files, current module source and the prior research report were used; mirrors, worktrees and fixtures were not counted as independent implementations or assets. Reuse intake nonce/authentication and FAM factory boundaries rather than creating parallel registries/auth systems. |

Commands/evidence: scoped and broader `rg` name searches returned no matches; targeted Solana/code searches produced the file/line references above; `Test-Path modules/infrastructure/api_gateway` returned `False`. Source reads were bounded, with required WSPs read fully. No integration, token, DEX or chain tests were run because this lane changes only this research document; no network effect was authorized. Prior chain test observations remain documented in the separate dated report and are not represented as rerun today.

Full WSP reading identity for this lane:

| Canonical file | SHA-256 | Bytes | Lines | Words | Read mode |
|---|---|---:|---:|---:|---|
| `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md` | `5dcb531b5eac2cbd77bce102b5ccee650f230a0576124a7c97cfdbf4c357b263` | 33156 | 778 | 4343 | full bounded chunks |
| `WSP_framework/src/WSP_106_FoundUp_API_Gateway_Protocol.md` | `c8380eb89088f63ed4a037121d4852816c266382298d7012663b45dc874b4a80` | 18542 | 740 | 1748 | full bounded chunks |
| `WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md` | `21cc5eb038f443e464fcf70f109054760932da81c72bf5b15af14edbd673c0ec` | 25708 | 911 | 3531 | full bounded chunks |

Relevant code reads are targeted evidence, not a new claim of complete module coverage. FAM/legacy blockchain module-doc coverage and the wider WSP/vision audit belong to the 2026-10-21 research artifacts.
