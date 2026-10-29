# FoundUps FX venue reuse and project claims — 2026-10-25

Status: research and architectural recommendation; no deployed FX, asset,
liquidity, custody, testnet-availability or settlement-readiness claim.

Allocation: [FX chain delivery plan](FOUNDUPS_FX_CHAIN_DELIVERY_PLAN_20261025.md),
WSP 15 allocation recorded before this document. This research owns one new
document only. It does not activate a provider, signer, repository verifier,
exchange service or resident worker.

## 1. Decision and evidence boundary

Build **FoundUps Exchange (FX)** as the project/asset discovery and trading
interface over bounded, chain-native venue adapters. Reuse an existing protocol
before considering a new AMM or order-book implementation. FX can have its own
presentation and project-admission policy without a new blockchain or FX token.

Keep the first reward-settlement pilot aligned with the existing Algorand design.
Evaluate Tinyman V2 integration first for that rail; retain Pact as an integration
alternative. If acquisition of Solana-native projects drives the first FX trading
experiment, evaluate Raydium CP-Swap through a separate Solana adapter and asset
domain. That choice must be explicit; it cannot silently migrate or duplicate
Algorand UPS/F_i supply.

Primary web sources below were checked on **2026-10-25**. Repository URLs point
to then-current **main/master branches**, not immutable reviewed release or
deployment pins. GitHub labels, README audit references and documented program
addresses do not establish a reviewed version or a currently available venue.
No deployed venue, pool, liquidity, contract bytecode, public-testnet availability,
account permission, quote, price, API quota or successful transaction was checked.
These are candidates for a later pinned integration review, not deployment
approvals. No external API request, chain/provider operation or installation was
performed; browsing public documentation was the external research surface.

WSP 00 was refreshed in the parent research session: seven detector passes,
coherence 0.777, separate strict tracker compliant. WSP 97 and WSP 15 were
refreshed. Role: research reviewer; origin: internal handoff. The parent canonical
HoloIndex query failed `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, with
`ok=false`, `freshness=UNKNOWN`, `index_gap_detected=true`. Scoped source reads
and primary documentation were the explicit fallback; no raw query or reindex.

## 2. Current repository capability versus design

The source observations in this section were rechecked in the managed
`foundups-fx-chain-delivery/Foundups-Agent` checkout before authoring. Its delivery
plan records base `8b2fccf64251097b647b7fc5a45dad75706a9192`; this research did
not independently inspect Git state or infer merge status.

| Surface | Observed capability | Boundary |
|---|---|---|
| [Simulator order book](../../modules/foundups/simulator/economics/fi_orderbook.py), lines 110–133 and 380–421 | Python order matching, float-valued prices/quantities, trade records and fee statistics | `_execute_trade` updates local orders/lists/statistics. It supplies no node transaction, escrow, signer, funded settlement or independently confirmed recipient effect. |
| [Simulator runtime](../../modules/foundups/simulator/mesa_model.py), order-book integration | Simulated order placement, account/event wiring and market display data | Useful for policy and adversarial scenarios; simulated volume, reserve fees and prices must not become live FX market data. |
| [Token factory](../../modules/foundups/agent_market/src/token_factory.py), lines 237–310 | The reviewed working overlay rejects unsupported, missing, disconnected or identity-changing backend selection and mismatched result chains; mock remains identified | **This is a working-overlay P0A patch, not landed-main evidence until its dedicated PR completes.** Enum names are not chain implementations. No concrete Algorand or Solana backend was established. |
| [Registry schema](../../modules/foundups/foundup_registry.schema.json) | External FoundUp representation and nullable local implementation path | Existing products need not relocate source into the monorepo. Registry membership does not establish a maintainer claim, issuer grant, market or liquidity. |
| [Source-authority contract](FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md) | Separates project lifecycle from execution source authority | Listing or claiming an external project does not grant authority to execute its code or change runtime source ownership. |
| [Reserve/token architecture](FOUNDUPS_BTC_RESERVE_TOKEN_ARCHITECTURE.md), lines 39–65 and primary-option section | Draft Algorand token / Bitcoin reserve direction | It remains a design document. Its post-quantum, custody and reserve assertions were not independently validated by this venue review. |

Token-factory source SHA-256 observed during this read:
`d2d969090820e9b42802b981d415164e9e564587f164d4fd1273b6fd340dd5b9`.
This identifies the observed source bytes; it is not a commit or deployed-artifact
attestation, and another active lane may subsequently edit the file.

October 22 working-checkout plans described the old mock-fallback behavior and
earlier payment/proof defects. Some of those planning files are absent from this
managed checkout, and fresh main has newer persistence/verification repairs.
Treat that earlier material as historical research. Do not port obsolete repairs
or claim that every old defect remains without revalidation against the owning
current source. This document adds no new test result or accounting clearance.

## 3. Venue and license shortlist

License scope is per component and version. Pin the contract, SDK, frontend,
dependencies, build artifact and effective license before adopting code. SDK
permission does not establish contract permission, trademark permission, hosted
API availability or liquidity. Preserve required notices and review the exact
distribution/deployment arrangement before a production fork.

| Candidate | Fit | Checked component/license and consequence |
|---|---|---|
| **Tinyman V2 / Algorand** | Existing AMM with official Python/JavaScript integration paths; best first integration candidate for the existing rail | [Python SDK](https://github.com/tinymanorg/tinyman-py-sdk) is MIT. [V2 contract license](https://raw.githubusercontent.com/tinymanorg/tinyman-amm-contracts-v2/main/LICENSE) specifies BSL 1.1, no additional use grant, change date **2026-01-01**, change license **GPL v2.0 or later**. Its text makes the change effective on the specified date and applies separately to each version. As of this research the observed date has passed; verify the effective terms for the pinned work instead of describing all Tinyman components as permissive or all versions as still production-restricted. |
| **Pact / Algorand** | Alternative Python integration for pools, liquidity and swaps | [SDK license](https://raw.githubusercontent.com/pactfi/pact-py-sdk/main/LICENSE) is MIT. [Official SDK documentation](https://pactfi.github.io/pact-py-sdk/latest/) describes transaction preparation, integer asset amounts and explicit `network="testnet"`; its default is MainNet. This review did not establish the license of every underlying contract or service, or current testnet availability. |
| **Raydium CP-Swap / Solana** | Constant-product AMM; no OpenBook market requirement; smaller conceptual first pool than a concentrated-liquidity or order-book deployment | [Contract repository](https://github.com/raydium-io/raydium-cp-swap) identifies Apache-2.0 and Token-2022 support. The [SDK V2 license](https://raw.githubusercontent.com/raydium-io/raydium-sdk-V2/master/LICENSE) is GPL-3.0. Do not describe the entire Raydium stack as Apache. Public contract source does not establish that every Raydium service/program is available for reuse. |
| **OpenBook V2 / Solana** | Central limit order book; suitable if executable limit-order semantics are essential | [Official repository](https://github.com/openbook-dex/openbook-v2) states MIT for most code, including client/CPI paths, and GPL-gated code needed to compile the exchange program. A derived exchange program has different obligations from a client integration. Requires a deliberate market-making and order/settlement lifecycle; the simulator matcher is not its implementation. |
| **Orca Whirlpools / Solana** | Concentrated-liquidity AMM with SDKs and documented deployments | [Current license](https://raw.githubusercontent.com/orca-so/whirlpools/main/LICENSE) says Apache availability ended **2025-02-26** and the Orca License applies from **2025-02-27**. It restricts commercial/competitor use and requires separate written consent outside its permitted uses. Current main is not an unrestricted Apache donor, despite the repository's open-source wording. Historical revisions require their own license/provenance review. |
| **Jupiter / Solana** | Hosted routing, quote and transaction-building option for an FX interface | [Current official documentation source](https://raw.githubusercontent.com/jup-ag/docs/main/swap/index.mdx) describes Swap V2: `/order` plus `/execute`, or `/build` for raw instructions and separate landing. It describes proprietary landing and multiple routing sources. This is integration documentation, not evidence of a fully reusable open-source exchange engine or permission to clone its whole service. Older V1/Ultra examples are migration material. |

Tinyman's [official SDK page](https://docs.tinyman.org/v2-integration/official-sdks)
also directs integrators to inspect individual SDK releases and licenses.
Pact's documentation distinguishes preparing transactions from signing/sending;
an SDK should sit below FoundUps authorization and signer boundaries.

No package, SDK, binary or contract was downloaded or installed for execution.
No venue endpoint was probed. Current maintenance, testnet deployments, exact
program/app IDs, supported asset extensions, audit-to-bytecode correspondence and
operational dependencies remain selection gates before implementation promotion.

## 4. Bounded architecture and strongest competing design

**Recommended first shape:** extend the existing Mall/public projection and
canonical project records with an FX presentation. Keep a chain-neutral asset
manifest and venue interface, then implement one chain-specific adapter. Reuse
the selected protocol's execution mechanism; retain FoundUps-owned admission,
authorization, accounting and receipts. The existing FAM persistence/transaction
owners remain the extension boundary; do not create a second FoundUp registry,
ledger, general scheduler or token issuer inside FX.

The first FX view can show a verified project and declared asset state before
trading. A later adapter may read an approved market, prepare a bounded swap and
hand it to a separately authorized signer. Pool creation and LP funding are
separate operations. Automatic workflows may continue under a standing grant
with exact project, operation, network, assets, venue, signer, fee/slippage ceiling,
budget, expiry and revocation policy; no repeated approval is needed for each
permitted mechanical step.

**Strongest competitor:** a Solana-only acquisition/FX pilot using CP-Swap or
hosted Jupiter routing. This can reduce integration work if the target community
already has Solana assets. The tradeoff is a separate Solana asset and signer
domain alongside the existing Algorand reward direction. It does not provide
interoperability, Bitcoin backing or a shared supply automatically. Choose this
deliberately when Solana-native acquisition is the first validated outcome.

**Other alternative:** fork an open AMM or order-book program and operate an
FX-owned protocol. This offers greater contract/fee control, but adds deployment,
upgrade authority, market-making, security, liquidity and maintenance work before
the simplest useful exchange action is demonstrated. It is not required for an
FX-branded interface or project directory.

The parent delivery plan supplies WSP 15 allocation: authority and truthful token
selection are P0; FX discovery/admission is P1; a new AMM/order-book implementation
is P2. Preserve that ordering. Discovery work can progress independently while
reward-settlement authorization and accounting are validated.

## 5. Asset identity and chain mismatch gates

- A ticker, repository or FoundUp ID is not an asset identity. Bind Algorand
  assets to exact network/genesis and ASA ID; bind Solana assets to exact network,
  mint and token-program identity. Record decimals, issuer/treasury authority,
  approved supply/release policy and immutable evidence separately.
- An Algorand ASA cannot directly enter a Solana pool. A second-chain mint is
  another asset unless a separately designed bridge/custody/issuance arrangement
  says otherwise. Do not duplicate a global issuance cap or promise conversion.
- Solana's Token Program and Token-2022 have different account derivation and
  instruction requirements. [Official token-program explanation](https://solana.com/docs/payments/how-payments-work).
  [Transfer fees](https://solana.com/docs/tokens/extensions/transfer-fees) alter
  received/withheld amounts; [transfer hooks](https://solana.com/docs/tokens/extensions/transfer-hook)
  introduce additional program logic/accounts. Verify the exact extensions against
  the chosen venue and route; a broad support label is insufficient.
- Algorand receiver opt-in, minimum balances, app/storage costs and native ALGO
  fees need separate budget lines. [Official asset operations](https://dev.algorand.co/concepts/assets/asset-operations/).
  A configured SDK network label alone is not a verified endpoint/genesis binding.
- Every quote/build result is untrusted proposed execution. Inspect exact assets,
  program/app identities, payer/recipient, transfers, approvals, fees, minimum
  output, expiry and any extra instructions before authorizing a signature.
- Test assets, test liquidity and simulator prices carry no implied MainNet value,
  reserve backing, redemption or conversion promise. Confirm actual pool state
  before exposing a Trade action; no pool/route or stale data needs an honest
  unavailable state.
- Persist intent and transaction identity, bound retry behavior, and reconcile
  confirmed effects independently. Unknown submission cannot trigger another
  economic operation merely because the request timed out. Market permission
  cannot bypass source-receipt consumption, aggregate caps or funded rewards.

## 6. Nomination, claim, admission, issuance and market

```text
nomination -> verified representative claim -> admitted FoundUp
          -> optional issuer authorization -> confirmed asset
          -> separately authorized market and funded liquidity
```

These are linked records with independent status, evidence and permitted effects.

| Record/state | Establishes | Does not establish |
|---|---|---|
| Nomination | Someone supplied project metadata/reference; moderated unclaimed preview is possible | Maintainer endorsement, code execution, issuer or token rights |
| Repository-control/representative claim | Fresh evidence for a particular claimant, source and scope; organization delegation checked where needed | Legal ownership or unlimited issuer/treasury authority |
| Admission | Explicit decision binding one candidate/claim to one canonical FoundUp identity and allowed capabilities | Required token creation, runtime source-authority promotion or exchange listing |
| Issuer grant | Explicit authorized network, asset terms, treasury, supply, costs and operation scope | Funded rewards or LP capital |
| Confirmed asset | Independently observed mint/ASA identity and actual configuration | Liquidity, price, trading admission or benefit validation |
| Market admission | Approved venue/pair, supported asset configuration, funding authority and current liquidity evidence | Ownership of upstream IP or permission to spend other participants' assets |

Anyone may nominate a public project. Projects with no code can use a project
site/document/community evidence route. Preserve separate candidate and admitted
projections with clear unclaimed labels; never insert a candidate into the
admitted registry merely to obtain a card. Private source/claim evidence remains
outside public payloads. Existing assets may be registered after appropriate
identity/issuer verification instead of automatically minting replacements.

Generation of a pitch, project following, ratings, a badge, token creation or
market activity does not independently earn contribution rewards. Rewards still
require project-authorized work, independently accepted evidence, beneficiary
binding, a funded capped entitlement, source-replay protection and confirmed
settlement through the existing owners.

## 7. Public key file and fresh repository-control proof

A public key in a repository is a useful declaration, but anyone can copy it into
a fork. A signature alone proves possession of its private key, not present
control of the canonical repository or authority to issue the project's token.
Use both a repository-authorized key binding and a fresh service challenge for
the key-file route allocated by the parent plan.

The claim contract should bind:

- authenticated claimant/provider subject and platform session;
- provider host, stable repository ID, current owner ID and fork lineage;
- exact default-branch reference, pinned commit, regular-file path and key digest;
- domain-separated purpose such as `foundups.fx.discovery_claim.v1`;
- unpredictable nonce, issue/expiry times, permitted scope and challenge ID.

Verify a fresh signature over the exact canonical challenge bytes. Establish the
key's authorized file binding at the pinned default-branch commit, then recheck
repository/owner/default-branch/tip identity immediately before admission. Persist
the signature/evidence digests and observation time; atomically consume the
challenge in the owning durable store. Same-request retries return the existing
receipt; conflicting content or claimants require resolution. Verification is
dated evidence, not a guarantee that repository control can never change.

A fresh bound challenge file added through the representative's normal GitHub
process is another control pattern; it need not grant FoundUps write access.
Keep that method's proof statement distinct from private-key possession. Neither
method is a wallet-transfer signature, issuer grant or treasury delegation.

Use [GitHub repository metadata](https://docs.github.com/en/rest/repos/repos)
to resolve IDs/owner/fork relationships, [refs](https://docs.github.com/en/rest/git/refs)
to pin the current branch, and [Git trees](https://docs.github.com/en/rest/git/trees)
to check file type/mode. The [Contents API](https://docs.github.com/en/rest/repos/contents)
can return a normal-file symlink target's contents; content retrieval alone cannot
prove a regular-file claim. Reject symlinks, submodules, PR/tag-only refs, wrong
forks, reused slugs, stale/expired/replayed challenges and identity/tip changes.
Bound response size and URLs; never execute a submitted repository or README.

A GitHub “Verified” commit badge is not fresh permission evidence. GitHub records
can persist after key revocation or contributor departure and across the fork
network. [Official signature-verification behavior](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification).
An optional GitHub App can provide ongoing scoped control evidence, using the
authenticated person's permissions and installation repository access; an app's
own installation access must not be confused with the claimant's authority.
[App installation endpoints](https://docs.github.com/en/rest/apps/installations),
[App authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app).

Record current claim status separately from historical verification. Recheck on
policy expiry, owner transfer, permissions/key changes or revocation. A rename
updates aliases only after stable-ID resolution; a fork receives a distinct
claim. Organization representation and token/brand/publication consent remain
explicit scoped attestations, not conclusions inferred from a source license.

## 8. Smallest acceptance sequence

1. Reconcile current authority/payment work and the P0A overlay through their
   dedicated reviews/PRs; do not infer landed state from this research document.
2. Agree one project/admission/asset/venue record contract and one issuance rail.
   Expose an honest read-only FX entry using existing identity/projection owners.
3. Prove one nomination and fresh bound claim with no token, code-execution or
   trading effect. Cover fork/rename/transfer, wrong file/ref, stale key, replay,
   concurrent claim and private-data leakage cases.
4. Pin one venue integration's component licenses, artifacts, network identity,
   dependencies and exact supported asset configuration. Establish its actual
   LocalNet/Devnet/TestNet availability before accepting it as a pilot dependency.
5. Prepare one approved test pair and separately funded bounded liquidity. Test
   quote/build inspection and transaction recovery before a public test swap.
6. Confirm one intended recipient/asset effect and balanced reconciliation.
   Connect verified-work rewards only after the existing authorization,
   accounting, proof and source-replay gates pass. Expand to another tenant or
   chain only after that scenario remains isolated and repeat-safe.

Retrieval evaluation: obsolete mock-fallback statements, generic open-source
labels, mutable branch docs and simulated exchange output were the principal
noise/staleness risks. Current local source and exact component LICENSE text take
precedence. Deployment availability and immutable artifact pins remain missing
evidence. The architecture deliberately reuses existing records/adapters and
avoids duplicating the registry, ledger, scheduler or exchange engine.

Validation of this authoring slice is limited to source/link review. No new tests,
chain/provider calls, credentials, installations, product code or Git operations
were performed. Only this new research document was authored.

## 9. Public legacy DAO and Playapp evidence — 2026-10-25

Pre-authoring allocation: **C2/I4/D3/Impact4 = 13/P1**. The parent authorized
at most 100 appended lines here and one root ModLog entry of at most 12 lines.
This slice persists completed public research only; no product, test, WSP,
registry, dependency, provider, signer or chain change is authorized.

Authoring base after an authorized fetch: main
`c7f0d93928581d67f0304cc6623876f0cabe1c54`, on the owned branch
`agent/foundups-legacy-fx-research-20261025`. This is a dated readback,
not continuing remote freshness. The earlier sections retain their original
source, overlay, qualification and validation limits; they are not relabeled.

The connected GitHub review used only the two requested public repositories.
Their default branches were resolved before reading immutable trees/files:

| Public repository | Default branch / commit SHA-1 | Tree SHA-1 |
|---|---|---|
| [foundups-dao](https://github.com/FOUNDUPS/foundups-dao/tree/303a56f7da09ea80c400034e713c967728b2ff3a) | main / `303a56f7da09ea80c400034e713c967728b2ff3a` | `c9eee933f8c3ec03313f9c869e563eb3909e1cc2` |
| [playapp-web-frontend](https://github.com/FOUNDUPS/playapp-web-frontend/tree/8ebdb6af24acdab0b0ad0c0d1328e1c4429b313d) | master / `8ebdb6af24acdab0b0ad0c0d1328e1c4429b313d` | `cb94b9fcf1de95e3184b65a393d8e22d6e294716` |

Both recursive trees were untruncated: 65 and 21 entries, including directories.
Each release query returned no releases. Neither observation proves global
absence across other branches, applications or deployments. Repository counts
are nomination/discovery inputs, never counts of admitted FoundUps or tokens.

**Actual DAO primitives.** [FucDao](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/contracts/FucDao.sol#L31-L79)
accepts an ERC20 deposit, creates a beneficiary timelock and mints FUC using a
time-dependent reward formula. Its owner can change interest, multiplier and
lock duration. [FucToken](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/contracts/FucToken.sol)
inherits ERC20Burnable; mint is owner-only, and its deploying FucDao owns it.
This is source code, not evidence of a deployed issuer or accepted-work rewards.

[PaymentSplitter](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/contracts/PaymentSplitter.sol#L72-L162)
holds the accepted ERC20 and releases it to payees by shares; payees may transfer
their shares. Its owner adds, removes or updates payees. FucDao's burn path burns
FUC; it does not return the accepted deposit or redeem BTC.
[TokenTimeLock](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/contracts/TokenTimeLock.sol#L29-L70)
holds minted FUC until its threshold; its owner FucDao calls release to the fixed
beneficiary. Contract-held funds and owner controls are part of this design.

Separate [UChildERC20](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/contracts/UChildERC20.sol#L1488-L1562)
source grants an initializer caller default admin, grants the configured child
chain manager a depositor mint role, and burns on user withdrawal. The
[proxy owner](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/contracts/UChildERC20Proxy.sol#L117-L143)
can replace implementation and call it. These privileged bridge/proxy primitives
are not proof that a bridge is deployed or connected to the FUC flow.

[Hardhat configuration](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/hardhat.config.js#L36-L73)
names local networks, Mumbai and Polygon (chain ID 137). The
[deployment script](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/deploy/10_deploy_fucdao.js#L18-L45)
attaches a configured accepted-token address and chooses payee shares 225/25/9750.
Those are configuration intentions, not current network/asset verification.
The complete tree has no committed deploy.json/deployments registry or
transaction/finality receipt; [test setup](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/scripts/mainDeploy.js#L15-L44)
uses ERC20Mock and a mocked clock. No AMM/router/order book or token-voting
governance implementation was established in this tree. DAO2's canonical chain,
asset ID, issuer relationship and role remain unverified; these sources name FUC.

**Playapp and licenses.** Playapp's [App.js](https://github.com/FOUNDUPS/playapp-web-frontend/blob/8ebdb6af24acdab0b0ad0c0d1328e1c4429b313d/src/App.js)
is the Create React App starter, and its [dependencies](https://github.com/FOUNDUPS/playapp-web-frontend/blob/8ebdb6af24acdab0b0ad0c0d1328e1c4429b313d/package.json)
contain no wallet/chain/DEX integration. Its reviewed tree has no LICENSE.
DAO licensing differs by layer: [root Unlicense](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/LICENSE),
[package ISC declaration](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/package.json#L77),
principal contracts' MIT headers, and [ABDK conditions](https://github.com/FOUNDUPS/foundups-dao/blob/303a56f7da09ea80c400034e713c967728b2ff3a/contracts/abdk-libraries-solidity/LICENSE.md)
including notice retention and advertising acknowledgement. Preserve component
notices and resolve the declarations before adopting a distribution.

**Reuse and policy.** Reuse requirements/test vectors for deposit allocation,
authority separation and timelock beneficiaries if an EVM experiment is selected.
Solidity is not a direct Algorand ASA transport implementation. These repositories
provide no existing DEX integration to adopt. Do not infer external-trading or
issuer permission from their public visibility or from a token's existence.
[WSP26](../../WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md):98,107,269
describes participant-bound UPS and FoundUp-bound converted tokens; transferable
FUC/payee shares cannot silently substitute for them. The reserve architecture
remains DRAFT; its proposed external exit does not resolve this policy conflict.
Keep discovery, project/asset admission and separately authorized transport apart.

Evidence: external report `foundups-public-dao-research-20261025/report.json`,
SHA-256 `951e3b3297d531f95391d22a9a50d97308e1776529cdaab93ae37dfd0fda423c`.
It retains immutable source/blob SHA-1 IDs; that Git object hash domain differs
from report SHA-256 and raw checkout hashes. Its older local 0c814/944 references
remain historical. This persistence pass reread the full current FX document and
relevant WSP26/reserve/source-authority constraints. The canonical owner query
again returned HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH, ok=false,
freshness=UNKNOWN and index_gap_detected=true (shared authority a519f0ad… versus
shared workspace 0c81418f…; managed authoring base c7f0d939…). No reindex or
CURRENT semantic claim. Direct reads corrected ordering/staleness; public-only
scope reduced noise, missing deployment/DAO2 evidence stayed unknown, and this
existing owner avoids duplication. Source/link/diff review only: no tests,
product execution, installation, credentials, signing or chain/provider calls.

## 10. Current checkpoint and external-project boundary — 2026-10-25

This section updates status only; sections1–9 retain their dated sources and validation limits. P0A is now in observed main5be89ae4bb34133d775cd09f273d7781adfebc9f; the original line53 working-overlay warning is historical. `token_factory.py` still has observed raw SHA256 `d2d969090820e9b42802b981d415164e9e564587f164d4fd1273b6fd340dd5b9`; only mock ships, no concrete Algorand/Solana issuer/transfer backend is established. Follow the [delivery checkpoint](FOUNDUPS_FX_CHAIN_DELIVERY_PLAN_20261025.md#current-checkpoint--2026-10-25-supersedes-status-prose-preserves-history) for later publication state.

The intended product combines Play Mall discovery and FX metadata; public nomination is open, but claim/admission/issuer/market powers are separate. Reuse `ai_overseer/src/foundup_genesis/{launch_request,intake_transport,intake_packet_builder}.py`, canonical registry/projector and existing FAM authorization/persistence owners. Current packet builder still forces `external_repo_requested=False` at line210; launch intake IDEA/UNBOUND is not a completed external-record admission/claim writer. Extend the owner in one offline-tested layer; do not infer existing external mint support.

Nominate any public repository using stable provider/repository/owner IDs and pinned refs; projects without code can nominate site/document/community evidence. Never fetch arbitrary internal URLs, run README/scripts or promote imported text to instructions. Preserve public/private moderation and fork/rename/transfer lineage. A license allows only its stated rights; it does not prove maintainer representation, brand/IP title or token/treasury authority.

Preferred file route: issue a fresh service challenge binding provider/repository/owner IDs, authenticated claimant, key, purpose/domain, nonce/challenge ID, scope and expiry. The representative commits that challenge file through the current default branch and supplies its key signature. Observe and pin the resulting commit/tree/blob separately, then recheck owner/branch/tip; do not require a file to sign its own containing commit. A fresh signature over an old declared key proves key possession, while a departed maintainer's key can remain in the repository. A copied public key or “Verified” badge alone is insufficient.

After bounded provider reads, challenge consumption and the immutable decision receipt must commit atomically in their existing durable owner, with exact retry/conflict/reopen behavior. A consume-only nonce primitive cannot by itself recover a lost response without a receipt. Reject symlink/submodule, copied-fork, stale/replayed and changed-identity proofs; retain historical verification separately from current control. Standing owner-authorized workflows may automate permitted steps under exact budgets/scopes/expiry/revocation; repeated approval is not required for those mechanical steps. No such writer is implemented by this research.

Admission need not mint. Existing assets need their own identity/issuer attestation; token creation needs an issuer grant, network/genesis/asset/decimals/supply/treasury rules; market admission needs reviewed venue/pair/configuration and separately funded liquidity. Declared ticker, community support/vote/rating, successful generation, task completion, mock anchor or local PREPARED intent does not prove contribution entitlement or settlement. The WSP26 bound/nontransferability and human/agent policy conflicts in the checkpoint remain decisions before issuance/trading, not permissions inferred from DEX availability.

Retain Algorand-first reward direction and the explicit competing Solana-native acquisition pilot; no silent duplicate UPS/F_i supply or assumed ASA↔SPL interoperability. Current branch-level venue sources are not immutable deployment/license/testnet-availability pins. Public legacy DAO Solidity/FUC/payee-share primitives are not an Algorand transport or approved FoundUps asset-rights policy. Reuse narrowly qualified components before a custom AMM/order book; no current liquidity/trade/quote/bridge/reserve proof.

Pitch evidence must preserve Outcome→Solution(how/what; PoC/Prototype/MVP nested)→Pain and distinguish intended vision from stage evidence. Local rendered decks are useful creative artifacts; absent media stays absent. The untracked prototype instruction is not a resident generator, provider queue or publication grant. A public projector only exposes moderated authorized fields; generation/publication receipts cannot issue rewards.

Video candidate, verified2026-10-25: evaluate Gemini Omni Flash (`gemini-omni-1.1-flash`) through the existing media owner. Google's [video guide](https://ai.google.dev/gemini-api/docs/video) reports Veo3.1 Preview shutdown2026-10-22 and directs new generation to Omni; its [Omni guide](https://ai.google.dev/gemini-api/docs/omni) uses the Interactions API and supports generated audio. This requires a real adapter migration, not replacing the model string in the old Veo3 wrapper. OpenAI's [deprecation record](https://developers.openai.com/api/docs/deprecations) reports direct Sora2/Videos API shutdown2026-09-24; that alone does not determine the separate Azure helper's availability. Account access, pinned SDK/endpoint, actual output, duration/audio, cost ceiling and durable operation/retry admission remain unqualified. No provider request, credential inspection or generation occurred in this research.
