# Preserved historical record: 2026-10-22-blockchain-readiness-recheck.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `docs/plans/research/2026-10-22-blockchain-readiness-recheck.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `ae325f9b6181d64a286d389855835a56c4e7d789ec6e8dfb332a9c8c88a67b79`
- Preserved record SHA-256: `ae325f9b6181d64a286d389855835a56c4e7d789ec6e8dfb332a9c8c88a67b79`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [FOUNDUPS_FX_CHAIN_DELIVERY_PLAN_20261025.md](../../../../../../../architecture/FOUNDUPS_FX_CHAIN_DELIVERY_PLAN_20261025.md), [SKILLz.md](../../../../../../../../modules/platform_integration/social_media_orchestrator/skillz/foundup_pitch_package/SKILLz.md), [README.md](../../../../../../../../modules/foundups/agent_market/README.md)

Disposition: Archive the October readiness recheck, including its bounded validation scope and model-selection discussion. Current canonical FX delivery and v0.1.3 pitch skill supersede the older sequencing. No model provider, hosted video path or chain deployment is qualified by this record.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content

# FoundUps blockchain readiness recheck — 2026-10-22

Subsequent local implementation: P0A backend-selection/fallback checks are now
fixed and module-tested; see the
[implementation receipt](2026-10-22-token-factory-fail-closed-receipt.json).
The observations below remain the pre-fix audit snapshot. Other authorization,
accounting, recovery and settlement gates remain open; no chain readiness is
promoted by this patch.

**Decision: local prototype; real testnet settlement and production security are
not complete.** This is a source/test/probe assessment at repository HEAD
`0c81418fe94a7786cfd55f01e138ddc5d510583d`, including the current working overlay.
At the time of this pre-fix audit, no blockchain runtime repairs, contracts,
wallets, assets or releases had been made. Its completed work was research/planning
and a local creative instruction skill; the subsequent P0A patch is recorded
above. Test success below is not security clearance.

The [orchestration plan](../../architecture/FOUNDUPS_BLOCKCHAIN_TESTNET_ORCHESTRATION_PLAN.md)
remains the delivery source. This recheck confirms blockers and narrows the next
engineering slice; it does not replace the existing architecture.

## 1. Current chain and accounting evidence

| Boundary | Fresh observation | Source |
|---|---|---|
| Real backend selection | Explicit Algorand/Solana/EVM/unknown hints, disconnected EVM and missing configured default can return mock success | token_factory.py:233 (historical reference: `../../../modules/foundups/agent_market/src/token_factory.py:233`) |
| Token deployment identity | Mock identity omits full terms; changing supply 100 to 200 reuses the asset and overwrites balance; restart forgets deployments | token_factory.py:138 (historical reference: `../../../modules/foundups/agent_market/src/token_factory.py:138`), deployment cache:212 (historical reference: `../../../modules/foundups/agent_market/src/token_factory.py:212`) |
| Verifier authority | Persistent path lacks verifier-role/independence checks; in-memory role checks permit self-verification and mismatched task binding | task_pipeline.py:239 (historical reference: `../../../modules/foundups/agent_market/src/task_pipeline.py:239`), in_memory.py:429 (historical reference: `../../../modules/foundups/agent_market/src/in_memory.py:429`) |
| Treasury authority | A funded unprivileged actor can initiate persistent payout with compute enforcement enabled or disabled; compute credit is not treasury authorization | task_pipeline.py:295 (historical reference: `../../../modules/foundups/agent_market/src/task_pipeline.py:295`) |
| Payment truth | Persistent task becomes PAID while payout is INITIATED with null transaction/reference, including after restart; in-memory COMPLETED uses a synthetic reference | task_pipeline.py:327 (historical reference: `../../../modules/foundups/agent_market/src/task_pipeline.py:327`), in_memory.py:468 (historical reference: `../../../modules/foundups/agent_market/src/in_memory.py:468`) |
| Atomicity/replay | Failure after payout creation but before task update leaves VERIFIED; retry creates a second durable payout row | task_pipeline.py:331 (historical reference: `../../../modules/foundups/agent_market/src/task_pipeline.py:331`), SQLite commits:358 (historical reference: `../../../modules/foundups/agent_market/src/persistence/sqlite_adapter.py:358`) |
| Merkle claims | Changing beneficiary, amount and epoch still verifies; identical rewards have the same root across tenants/epochs | epoch_ledger.py:96 (historical reference: `../../../modules/foundups/simulator/economics/epoch_ledger.py:96`) |
| Epoch closure | Duplicate epoch creates two entries and overwrites its root while chain verification still passes | epoch_ledger.py:148 (historical reference: `../../../modules/foundups/simulator/economics/epoch_ledger.py:148`) |
| Aggregate cap | Mint 21M then stake 100 UPS produces 21,000,097 aggregate F_i against a 21M cap | token_economics.py:826 (historical reference: `../../../modules/foundups/simulator/economics/token_economics.py:826`) |
| Epoch allowance | Two calls route 20 plus 19.6 UPS despite an initial 20-unit allowance; per-call conservation holds, durable epoch allowance is missing | cabr_flow_router.py:48 (historical reference: `../../../modules/foundups/simulator/economics/cabr_flow_router.py:48`) |
| Source-receipt replay | Two completion calls award 10 plus 10 F_i; API has no task/receipt/epoch identity. This is a missing composition boundary, not proof of a duplicate real task payment | token_economics.py:1040 (historical reference: `../../../modules/foundups/simulator/economics/token_economics.py:1040`) |
| BTC anchoring | Public publishers and real confirmation remain TODO; content-conflicting replay, publish-before-persist and failed/no-tx confirmation gaps reproduce in offline probes | btc_anchor_connector.py:313 (historical reference: `../../../modules/foundups/simulator/economics/btc_anchor_connector.py:313`), confirmation:372 (historical reference: `../../../modules/foundups/simulator/economics/btc_anchor_connector.py:372`) |

Persistent verification correctly rejects a mismatched task ID (positive control).
In-memory role checks also reject ordinary actors without the relevant role.
These narrower protections do not establish persistent authorization parity or
independent verification. The probes demonstrate local/pre-chain correctness and
authorization defects; no live-chain exploit was exercised.

Network/genesis binding, exact asset/treasury authorization, signer capability,
fee limits, revocation and independently observed receipt/effect are not supplied
by chain hints or string account fields. The first test adapter must implement
those boundaries. Keep signing credentials and private work outside browser,
public catalog, model prompts and chain payloads; use minimal public commitments.

## 2. Current validation scope

All execution was offline, with bytecode/cache disabled and temporary database
and bridge output outside the checkout. The chain/FAM lane blocked sockets/DNS
and observed zero network attempts. No provider, signer or credential operation
was invoked. Default Python lacked SQLAlchemy; the existing `.venv` succeeded
without an install.

| Lane | Result | Exact test-file scope |
|---|---|---|
| FAM | 50 passed | `agent_market/tests/test_task_lifecycle.py`, `test_permissions.py`, `test_persistent_compute_wiring.py`, `test_schemas.py`, `test_orchestrator.py`, `test_persistence.py`, `test_sqlite_adapter.py`, `test_migrations.py` |
| BTC/commitment/runtime | 16 + 2 + 2 passed | `simulator/tests/test_btc_anchor_connector.py`, `test_epoch_ledger_settlement_commitment.py`, `test_layer_d_anchor_runtime.py` |
| Economics selected cases | 9 passed in 0.76s | Exact node IDs below; partly overlap the commitment scope above |

Paths in this table start under `modules/foundups/`. Do not add these counts into
a distinct-coverage total. Two inactive asyncio-configuration warnings occurred
with plugin autoload disabled. This is not a full repository/contract/custody
audit or live-node integration test.

Representative FAM/BTC passing node IDs (current execution, not inferred from old
test counts):

```text
modules/foundups/agent_market/tests/test_task_lifecycle.py::test_task_lifecycle_open_to_paid
modules/foundups/agent_market/tests/test_permissions.py::test_only_verifier_can_verify
modules/foundups/agent_market/tests/test_permissions.py::test_only_treasury_can_trigger_payout
modules/foundups/agent_market/tests/test_persistent_compute_wiring.py::test_task_pipeline_enforces_and_debits_each_step
modules/foundups/simulator/tests/test_layer_d_anchor_runtime.py::test_layer_d_anchor_publishes_on_configured_cadence
modules/foundups/simulator/tests/test_layer_d_anchor_runtime.py::test_layer_d_anchor_disabled_records_epoch_without_publish
```

The two permission cases exercise the in-memory implementation. Passing them
does not establish persistent role enforcement. Exact economics node IDs, all
under `modules/foundups/simulator/tests/`:

```text
test_alignment_and_tokenomics.py::test_foundup_mint_respects_available_supply_cap
test_alignment_and_tokenomics.py::test_staking_roundtrip_fee_math
test_cabr_flow_router.py::test_valve_closed_routes_zero_flow
test_cabr_flow_router.py::test_pipe_size_controls_flow_rate
test_cabr_flow_router.py::test_release_budget_caps_flow
test_epoch_ledger_settlement_commitment.py::test_prepare_settlement_commitment_returns_none_when_epoch_missing
test_epoch_ledger_settlement_commitment.py::test_prepare_settlement_commitment_contains_expected_fields
test_fam_lifecycle_flow.py::test_bridge_supports_full_task_lifecycle
test_fam_lifecycle_flow.py::test_model_advances_claimed_task_to_paid_and_published
```

Adversarial observations in section 1 are additional probes, not cases repaired
by this audit. They explain why the green existing suite does not prove safety.

## 3. Existing product work versus integration gaps

The authored skill 0.1.2 and plans align with WSP 27/30/109: OUTCOME is vision;
SOLUTION nests PoC/Prototype/MVP; PAIN includes obstacles to implementing that
solution and existing adoption evidence. Why/how/CTA remain supporting detail.
Local pitch/deck drafts were demonstrated; resident triggers and automatic media
jobs remain proposed. Final release should derive the companion deck from the
verified video's transcript/stills and the same brief revision.

Public project nomination, representative claims, community project-following,
directory voting and audience pepper persistence were not found as an integrated
owned public workflow in the bounded source review. Existing pieces are different:

- FAM supports internal agent joining and SQLite profiles; that is not public
  project admission or a representative claim.
- The Mall follow hook is specified; video saving is implemented in browser-local
  storage. Saving a video does not establish persistent project following.
- The existing 1-7 economic input is founder conviction, not audience peppers.
- Vote/Ballots has an internal civic research PoC, not the directory vote service.
- Current genesis intake conversion retains IDEA/UNBOUND/no-external-repo flags;
  external nomination needs an additive typed variant, not weakened invariants.

Reuse those contracts and the existing public projector; do not rebuild a
parallel marketplace or reinterpret economic/civic votes as directory preference.
These integrations are secondary to the chain correctness work in this session.

## 4. Video model decision

For the first new video adapter, evaluate **Gemini Omni Flash
(`gemini-omni-1.1-flash`)**. Google's current guide recommends it for general video
generation; the [Omni documentation](https://ai.google.dev/gemini-api/docs/omni)
documents text-to-video with audio through the Interactions API.

The existing generator uses `veo-3.0-generate-001` / its fast variant. Google's
[deprecation table](https://ai.google.dev/gemini-api/docs/deprecations) lists those
Gemini API versions as retired, and Veo 3.1 previews for shutdown on October 22,
2026. A separately configured Cloud GA Veo path has different availability/API
requirements. No account access, provider quota, price quote or successful live
render was verified. Do not silently rename models, fall back across providers,
or call the legacy publishing constructor to generate a draft.

## 5. Ordered engineering work

1. **P0A: fail-closed backend selection.** Preserve explicit, visibly identified
   simulation; reject unavailable/unregistered/disconnected real backends and
   unsupported hints. Reuse the token factory and its closest tests. Exit when
   every reproduced fallback case rejects and explicit simulation remains honest.
2. **P0B: common authorization and payment truth.** Enforce verifier/treasury
   roles, independent principal/task binding and tenant scope in both adapters.
   Separate initiated/submitted/confirmed/reconciled; PAID must not imply a
   confirmed transfer without an independently checked chain receipt.
3. **P0C: accounting/proof/replay repair.** Integer asset-aware accounting; one
   aggregate issuance cap; immutable epochs and durable epoch allowances; proof
   recomputation from all domain-bound claims; consumed source-receipt keys across
   epochs. Reserve funded entitlement and outbox atomically; crash/retry must
   preserve exactly one intent and eventual effect.
4. **Freeze one explicit test policy and adapter configuration.** Resolve the
   competing pool/release formulas and beneficiary rules before contract effects.
   Existing architecture favors an Algorand pilot; adding a Solana mint does not
   resolve accounting. Pin network, asset, treasury, signer scope, limits and
   confirmation/recovery semantics; keep MainNet credentials/stores separate.
5. **Prove one transfer, then expand.** One admitted FoundUp, independently
   accepted contribution, funded capped test allocation and authorized recipient.
   Local network first, then public testnet. Inject altered claims, revoked/wrong
   roles, duplicate source, concurrency, crashes and ambiguous submissions; prove
   one confirmed recipient effect and balanced reconciliation. A trusted test
   treasury transfer is not autonomous contract enforcement; that is a later
   reviewed milestone. BTC reserve/anchoring, DEX and mainnet remain separate.

P0A is the smallest next build slice. Policy work can proceed alongside P0
repairs; it must not be guessed by a model. No new WSP, scheduler, exchange or
frontend is needed to execute this sequence.

HoloIndex owner retrieval remains `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`,
`ok=false`, `freshness=UNKNOWN`, `index_gap_detected=true`; no reindex. Direct
module/security/test/source reads supplied the evidence. Earlier roadmap and
mock-success labels were treated as retrieval noise rather than readiness proof.
