# Preserved historical record: 2026-10-21-simulator-economics.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `docs/plans/research/2026-10-21-simulator-economics.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `56678a3abb9871d6d014e73373d0f35b4d8877d0c9ee2bab77aa9889ce511aaf`
- Preserved record SHA-256: `56678a3abb9871d6d014e73373d0f35b4d8877d0c9ee2bab77aa9889ce511aaf`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [epoch_ledger.py](../../../../../../../../modules/foundups/simulator/economics/epoch_ledger.py), [token_economics.py](../../../../../../../../modules/foundups/simulator/economics/token_economics.py), [cabr_flow_router.py](../../../../../../../../modules/foundups/simulator/economics/cabr_flow_router.py), [ROADMAP.md](../../../../../../../../modules/foundups/simulator/ROADMAP.md)

Disposition: Archive the economics research, omitting the one scanner-flagged sentence from the public projection without declaring it a credential. Current epoch source recomputes bound proof fields and rejects changed duplicate epochs, superseding two old probe findings. Aggregate staking supply policy and durable epoch-wide CABR budgeting remain explicit owner acceptance requirements; no fresh exploit or runtime test was executed.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content

# Simulator, token economics, and settlement research

Date: 2026-10-21. Repository HEAD: `0c81418fe94a7786cfd55f01e138ddc5d510583d`.
Role: reviewer; origin: internal_handoff; scope: research and local verification only.
Parent plan: [FoundUps blockchain testnet orchestration plan](../../architecture/FOUNDUPS_BLOCKCHAIN_TESTNET_ORCHESTRATION_PLAN.md).

## Finding

FoundUps has substantial executable economic simulation and persistent FAM task accounting. It does not yet have a verified path from a real orchestrated outcome to an authenticated beneficiary, funded entitlement, and confirmed token transfer. The smallest useful next layer is a deterministic, durable reward-accounting seam. Reuse the simulator as a policy oracle and test harness; do not promote its automatic approvals, floating-point balances, simulated investors, or mock confirmations into production authority.

WSP 26 section 4.11 selects off-chain operations, Algorand Layer 1, and Bitcoin reserve/anchoring Layer 0. `economics/ALGORAND_DU_POOL_CONTRACT_SPEC.md:4` is explicitly a specification with no implementation. The chain research lane owns current external validation of its Algorand/Falcon claims. This report does not validate those external claims.

## Retrieval and coverage

Awakening ran from repository root with `python -B -u WSP_agentic/scripts/functional_0102_awakening_v2.py`: coherence 0.769; seven negative geometry passes. `python -B modules/infrastructure/monitoring/src/wsp_00_zen_state_tracker.py --check --strict --json` returned exit 0 and `is_zen_compliant=true`. Identity, role, and origin were kept separate. Historical RedDog bootstrap and its four curated references were read as historical material only.

Parent HoloIndex owner query failed `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `ok=false`, `freshness=UNKNOWN`, `index_gap_detected=true`; authority HEAD began `a519f0ad`, checkout HEAD began `0c81418f`. No reindex or raw Holo search was attempted in this lane. `rg` and direct source reads were the explicit degraded fallback, permitted by WSP_CORE's retrieval-unavailable rule and current WSP 80. `NAVIGATION.py:68` and `:88` identify simulator/FAM; `:90` identifies proof/verify/payout; `:498` identifies pool distribution.

Retrieval evaluation:

| Dimension | Observation and correction |
|---|---|
| Noise | Broad economic search returns many separate investment, fee, projection, and reserve experiments. Restricted source tracing to FAM lifecycle, runtime model, pool distribution, reward ownership, epoch ledger, and anchor connector. |
| Ordering | Read WSP_MASTER_INDEX, WSP_CORE memory contract, module README/INTERFACE/ROADMAP, test inventory, relevant ModLog records, then implementation. |
| Missing artifacts | Simulator lacks `tests/README.md`, `memory/README.md`, and root `requirements.txt`; `requirements-sse.txt` exists. FAM lacks root `requirements.txt`; FAM `memory/README.md` exists. No stubs created in this research-only lane. |
| Staleness | FAM memory README still says no persisted runtime memory despite SQLite/JSONL implementations. FAM roadmap names Hedera/EVM while WSP 26/Algorand Du spec select Algorand. Simulator README and WSP 26 retain frozen investor economics. Source and fresh tests control the findings. |
| Duplication | FoundUpTokenPool and FoundUpTokenDistributor both issue F_i with different release policies. Multiple pool/reward models must be reconciled rather than independently wired to chain. |

Fully read WSP source coverage is in [simulator WSP coverage](2026-10-21-simulator-wsp-coverage.json), including SHA-256, word counts and full line ranges: 26, 27, 29, 29 Memex addendum, 80-86, 97-101, 103-104, 106-107, and 109. Earlier truncated WSP 84 content was repaired by a direct read of lines 168-193. Parent owns WSP 87-96, 102, 105, 108. No canonical numbered WSP >=110 was found under `WSP_framework/src/`; index declares 110 next available. The JSON projection of WSP 97 was inventoried but not claimed as a separate fully read protocol.

Module documents fully read: FAM README, INTERFACE, ROADMAP, tests README, tests TestModLog, memory README; simulator README, INTERFACE, ROADMAP, tests TestModLog, requirements-sse; Algorand Du pool contract specification. Large ModLogs were read selectively: FAM latest entries and simulator latest/partition/anchor entries, not claimed as complete historical reads. Implementation reads are targeted to the line references below; this lane does not claim every simulator experiment has been fully audited.

## What actually connects

| Step | Existing evidence | Classification and missing seam |
|---|---|---|
| Task and proof | `agent_market/src/models.py:88`; `in_memory.py:383`; `task_pipeline.py:151` | Executable local lifecycle. Proof only requires nonempty URI/hash; no artifact hash verification is implied by schema validity. |
| Verification | `in_memory.py:429`; `task_pipeline.py:239` | In-memory enforces role `verifier`; persistent path performs compute-access check, not equivalent verifier role enforcement. Both rely on supplied approval, not an independent benefit proof. |
| Payout | `in_memory.py:457`; `task_pipeline.py:295` | In-memory creates COMPLETED with synthetic `inmem` reference. Persistent creates INITIATED, no reference/no paid time, then marks task PAID. Neither transfers tokens or reserves funded entitlement. |
| Simulator delivery | `simulator/adapters/fam_bridge.py:274`; `:338`; `mesa_model.py:544` | Deliberately synthetic: sim:// proof, generated hash, unconditional approved verification, default verifier/treasury actors. Useful lifecycle test, unsuitable settlement authority. |
| Beneficiary | `economics/token_economics.py:976`; `:1040` | Wallet allocator maps agent to human owner, who receives F_i. Missing agent mapping falls back to agent ID; completion auto-registers that ID as allocator and human. Reject this fallback at real reward ingress. |
| Work award | `mesa_model.py:576`; `token_economics.py:784` | F_i award credited to owner in memory. Completion uses zero compute cost in simulator; no task/receipt dedupe key is passed into economic minting. Replaying completion independently can award again. |
| UPS routing | `mesa_model.py:612`; `economics/cabr_flow_router.py:48` | Existing treasury routing kernel; no UPS minted by this kernel. Runtime sets PoB true from local FAM payout and uses heuristic CABR score or fallback threshold. No collective consensus consumption at this seam. |
| Epoch reward | `mesa_model.py:1108`; `pool_distribution.py:615` | Separate path creates epoch amount as 1% of simulated total stakes, distributes to separate Participant balances, records F_0 ledger. No matching treasury debit/award budget is visible here. |
| Commitment | `economics/epoch_ledger.py:148`; `:445` | In-memory hash chain/Merkle commitments. `prepare_settlement_commitment` truthfully returns pre_settlement/D_pending. Rewards arrive from `total_ups_rewards`, but ledger field is named `total_fi_distributed`: asset ambiguity. |
| Anchor | `economics/btc_anchor_connector.py:196`; `:299`; `:347` | SQLite stores mock anchor records and replay state. Bitcoin testnet/mainnet publishing and real confirmation checking are TODOs. Mock adds one confirmation per check. This is timestamp evidence scaffolding, not token delivery. |

`AgentProfile` contains agent ID, display name, capability tags and role (`models.py:70`), but no authenticated human binding, beneficiary key, delegation version, or principal revocation record. Task/Payout schemas contain integer amount without asset ID, decimals, chain, policy version, or entitlement ID (`models.py:88`, `:155`). These need a contract seam before chain submission.

`PersistentCABRHooks` stores histories in process dictionaries (`cabr_hooks.py:123`), despite the class name. It aggregates FAM metrics; it is not durable consensus settlement. Parent covers the separate receipt/pAVS/quorum/finalizer chain, whose review-ready state must not be treated as payout authority.

Persistent payout creation, task update, and event creation call separate adapter methods with their own sessions (`sqlite_adapter.py:468`, `:572`; `task_pipeline.py:321`). A failed event/task update can leave partial accounting. Concurrency and crash-recovery cannot be established by the existing happy-path tests.

## Economic policy conflicts to resolve before contracts

1. WSP 26 section 6.8 and WSP 101 distinguish human UPS participation rewards, agent F_i work awards, and delegated UPS spending. Old WSP 26 section 4.6 and WSP 27 section 12.2 still say agents earn UPS. The intended real beneficiary must be explicit; machine identity is not ownership authority.
2. WSP 26 section 6.3 and `pool_distribution.py:134` split total 60% Un, 16% Dao, 4% Du, 16% Network, 4% Fund. WSP 29 section 3.3 separately says task completer 50%, verifier 15%, creator 10%, FoundUp treasury 15%, ecosystem 10%. `mesa_model.py:166` uses 70% owner/20% FoundUp treasury/10% network for CABR UPS routing. These may be different levels, but no canonical composition/version currently binds them; they must never all apply independently to the same amount.
3. WSP 26 section 6.10 says Un/Dao event-based, Du passive epoch-based. `PoolDistributor.distribute_epoch` distributes all pools by activity tiers each epoch (`pool_distribution.py:615`). It divides a tier's share by headcount, avoiding WSP 26 example pseudocode's per-person multiplication; absent activity groups leave undistributed shares. Record those remainders explicitly.
4. Canonical 2026-03-31 Du partition (`pool_distribution.py:28`; simulator ModLog:343) is 4% total -> 80% ActiveFounder (3.2% total), 20% PassiveParticipation (0.8% total). Passive splits BTC stakers and channel partners. `channel_partner_pool.py:49` assumes 50/50 within passive, implying 0.4% total each; this remains an assumption to ratify. Cap 21 and permanent mainnet genesis closure are implemented locally. Neither ChannelPartnerPool nor weighted allocation helpers are called by the main epoch distributor; searches found only definitions, exports and tests. The ModLog itself labels the partition change documentation-only.
5. Staker hurdles are implemented: 10x cumulative BTC-equivalent allocation permanently locks a 0.0526 rate factor; fixed `UPS_TO_BTC_RATE=0.00001` (`pool_distribution.py:121`). This fixed accounting reference conflicts with a live floating BTC reserve value unless the distinction is explicit. Cross-epoch crossing/withheld/dust behavior needs deterministic integer specification.
6. `INVESTOR_ECONOMICS.md:5` and `investor_staking.py:3` mark I_i bonding-curve economics FROZEN/EXPLORATORY, not canonical, per 2026-04-20 ruling. Exclude I_i, guaranteed 10x buyouts and extreme return projections from testnet work. README, WSP 26 section 6.9 and model construction still reference/instantiate them; they are stale or exploratory donors, not implementation requirements.
7. WSP 26 section 4.7 says continuous normalized adoption release. WSP 27 section 11.1 and `FoundUpTokenDistributor.TIER_RELEASE` (`pool_distribution.py:820`) use seven discrete tranche releases. The runtime TokenEconomicsEngine uses the S-curve class. WSP 100 adds independent F0-F5 SmartDAO scale tiers; do not conflate these with seven lifecycle tiers or FoundUp ID F_0 investor program.
8. WSP 100 sections 11-12 explicitly keep CABR_READY/PAYOUT_READY/DAO activation blocked and describe ROC as review/observation. Optional external attestation in section 10 remains evidence only. State labels or an anchor cannot turn review-only consensus into spend authority.
9. WSP 101's regulatory labels and WSP 100's legal conclusions are positioning claims, not verified legal classifications. Their no-guaranteed-return language also conflicts with frozen investor material. Economic rights must be specified by actual behavior, not changed terminology.

## Fresh verification and boundary probes

152 existing tests passed, 2 warnings, 8.78 seconds on 2026-10-21. Warnings: unknown `asyncio_default_fixture_loop_scope` and `asyncio_mode` because plugin autoload was disabled. This is focused local evidence, not a full-repository, live-node, external-consensus, custody, or contract audit.

Executable: `.venv/Scripts/python.exe -B`; pytest arguments: `-q -p no:cacheprovider`, followed by:

```text
modules/foundups/simulator/tests/test_fam_lifecycle_flow.py
modules/foundups/simulator/tests/test_alignment_and_tokenomics.py
modules/foundups/simulator/tests/test_cabr_flow_router.py
modules/foundups/simulator/tests/test_epoch_ledger_settlement_commitment.py
modules/foundups/simulator/tests/test_btc_anchor_connector.py
modules/foundups/simulator/tests/test_layer_d_anchor_runtime.py
modules/foundups/simulator/tests/test_scenario_runner_determinism.py
modules/foundups/simulator/tests/test_operational_profit_proxy_flow.py
modules/foundups/simulator/tests/test_channel_partner_pool.py
modules/foundups/simulator/tests/test_weighted_stake_allocation.py
modules/foundups/simulator/tests/test_staker_hurdle_state.py
modules/foundups/agent_market/tests/test_task_lifecycle.py
modules/foundups/agent_market/tests/test_permissions.py
modules/foundups/agent_market/tests/test_persistence.py
```

Environment was `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`; `TMP`/`TEMP` pointed to a temporary research directory and `FOUNDUPS_DB_PATH` to a DB there. A process-local wrapper changed only the default FAMBridge data directory, avoiding simulator memory writes for existing tests that omit an explicit daemon. No test or application source was edited. The exact runner body, with `test_paths` equal to the ordered block above, was:

```python
import pathlib, tempfile, pytest
import modules.foundups.simulator.adapters.fam_bridge as bridge
original = bridge.FAMBridge.__init__
root = pathlib.Path(tempfile.mkdtemp(prefix="economics-fam-"))
counter = iter(range(10000))
bridge.FAMBridge.__init__ = lambda self, data_dir=None, deterministic=True, fam_daemon=None: original(
    self, data_dir=data_dir or root / str(next(counter)),
    deterministic=deterministic, fam_daemon=fam_daemon,
)
raise SystemExit(pytest.main(["-q", "-p", "no:cacheprovider", *test_paths]))
```

Four additional no-network probes exposed failures not covered by that green suite. Reproduce with `.venv/Scripts/python.exe -B` and this body; it changes only process-local economic objects:

```python
from modules.foundups.simulator.economics.epoch_ledger import EpochLedger
from modules.foundups.simulator.economics.token_economics import FoundUpTokenPool
from modules.foundups.simulator.economics.cabr_flow_router import CABRFlowInputs, route_cabr_ups_flow

ledger = EpochLedger("f_a")
ledger.record_epoch(1, 10.0, {"un": 10.0}, {"alice": 10.0})
proof = ledger.get_merkle_proof(1, "alice")
proof.participant_id = "mallory"
proof.amount = 999.0
print("tampered proof verifies:", proof.verify())
# Observed True: verify() trusts leaf_hash instead of hashing the claimed fields.

pool = FoundUpTokenPool("f_a", adoption_score=1.0)
pool.mint_for_work(21_000_000, "agent")
pool.stake_ups(100, "alice")
print(pool.minted, pool.staked_fi_outstanding,
      pool.minted + pool.staked_fi_outstanding > pool.total_supply)
# Observed 21000000.0, 97.0, True: stake route bypasses aggregate supply cap.

ledger.record_epoch(1, 20.0, {"un": 20.0}, {"bob": 20.0})
print(len(ledger.entries), ledger.verify_chain(), ledger.get_merkle_proof(1, "alice").verify())
# Observed 2, True, False: duplicate epoch accepted, Merkle map overwritten.

a = route_cabr_ups_flow(CABRFlowInputs(1000, 1, True, 100, 0.02))
b = route_cabr_ups_flow(CABRFlowInputs(a.treasury_ups_after, 1, True, 100, 0.02))
print(a.routed_ups, b.routed_ups, a.routed_ups + b.routed_ups)
# Observed 20.0, 19.6, 39.6: kernel enforces 2% per call, not 20 total per epoch.
```

The fourth result is a contract-composition gap: the pure router has no epoch identity or remaining epoch allowance; the runtime caller does not supply one. `epoch_release_budget_ups` is a misleading name until a durable epoch budget is enforced. It is not evidence that the per-call bound itself is wrong.

Other source-level pre-chain gaps: Merkle leaves bind only participant and float amount (`epoch_ledger.py:226`), not asset/network/FoundUp/epoch/policy/receipt. `anchor_to_chain` adds the current timestamp on every call (`:406`), so retries recompute different commitments; connector dedupe returns an existing record by FoundUp+epoch without comparing new content (`btc_anchor_connector.py:228`). Durable amount/context binding, conflict detection, and deterministic serialization must precede a real signer.

## Deterministic simulator-to-testnet gate

Proposed acceptance scenario, not implemented by this research slice:

1. Use one admitted FoundUp, one authenticated principal, one delegated worker, three independently identified verifiers, one beneficiary address, one immutable policy version and one fixed-clock epoch. Reuse a real durable outcome receipt emitted after verified execution. Queue acceptance, preflight admission, model self-report and simulator auto-verification are ineligible sources.
2. Use no external money, no market pricing, no investor lane, no automatic DAO progression. Prefund an exact test-unit budget, e.g. 1,000.00000000 F_i in a test treasury under a declared 21M cap. Keep UPS spending and F_i award assets distinct. A verified task may reserve a 100.00000000 F_i entitlement; rejection reserves zero. This fixed reward is a test fixture, not a ratification of any pool split.
[One original acceptance-scenario sentence is omitted from this public projection; the private original is preserved. This is not a determination that the sentence contains a credential.]
4. Record funded entitlement plus balanced treasury movement and outbox atomically. Dedupe by receipt/task/policy/asset with a database uniqueness constraint. Same-key same-content replay returns the existing entitlement. Same-key different-content is a conflict. Retried delivery cannot create another entitlement.
5. Close the epoch once; commit sorted integer-unit leaves with a domain-separated schema that binds network, token asset, FoundUp, epoch, beneficiary, amount, policy and entitlement. Record undistributed, withheld and integer dust accounts. Root and manifest hash must be identical under input reordering, retries, restart and fixed-clock replay.
6. First run against a chain test double, then the selected local network and public testnet. Submit exactly one authorized transfer/claim or batch distribution. Persist transaction identity before retries; reconcile actual receiver/asset/amount/round from the node/indexer. Model submitted, confirmed and reconciled independently. Bitcoin anchoring is a later independent evidence step and never substitutes for token delivery.
7. Inject: duplicate receipt, second process race, crash after reserve, crash after submit, delayed/failed confirmation, wrong network/asset, altered beneficiary/amount/proof, invalid root, revoked signer, over-budget and over-cap awards, duplicate epoch, withheld/dust cases and absent oracle. Assert no unearned or duplicate transfer.

Acceptance invariants: conservation in integer units; no negative balances; aggregate minted/transferred supply bounded across every issuance route; real principal/beneficiary separation; quorum independence; no payment for invalid/rejected work; exactly one economic effect under retries; source and authorization freshness; immutable epoch content; proof recomputation from claims; deterministic results; restart recovery; no mainnet enabling; no false settled status from mock/anchor evidence.

## Smallest implementation slices

| Order | Bounded slice | Reuse | Pass gate |
|---|---|---|---|
| 1 | Ratify one economic policy and reward/beneficiary contract; reconcile frozen investor and split/release semantics | WSP 26/29/100/101, existing Algorand Du spec, FAM models | One asset-aware versioned example traces all units; no conflicting multipliers. |
| 2 | Close four reproduced accounting/proof gaps and persistent role/transaction parity; use integer amounts | Existing epoch ledger/router/pool/FAM persistence | Adversarial cases fail safely; existing focused tests pass. |
| 3 | Admit a real verified outcome receipt as a durable reward candidate; bind beneficiary delegation and independent verification | Existing resident outcome receipt, FAM task/proof records | Review-only/queue/preflight evidence cannot reserve or pay. |
| 4 | Add funded entitlement reservation and durable outbox/reconciliation state | SQLite adapter and migrations; extend, do not duplicate ledger stacks | Crash/retry/concurrent duplicate scenarios preserve one balanced entitlement. |
| 5 | Implement one Algorand test adapter/contract path against fixed integer reference vectors | TokenFactoryAdapter, chosen chain spec, existing simulator fixtures | Local-network parity, then public-testnet confirmed receiver balance and repeat-safe reconciliation. |
| 6 | Reconcile canonical Du partition/hurdle/channel helpers into integrated epoch flow, if that is the chosen second test policy | Existing helpers and tests | Whole-Du conservation includes founders/stakers/partners/withheld/dust; mainnet-only closure is not triggered by testnet. |
| 7 | Implement Bitcoin test anchoring separately after stable reward commitments | BTCAnchorConnector | Genuine tx/confirmation evidence; immutability/conflict/retry behavior; no effect on token entitlement truth. |

There is no need to build a new generalized exchange, model orchestrator, investor program or mesh to prove this first reward settlement loop.
