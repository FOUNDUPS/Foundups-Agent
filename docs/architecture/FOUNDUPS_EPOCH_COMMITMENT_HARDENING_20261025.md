# FoundUps epoch commitment integrity — 2026-10-25

Status: allocated before implementation; local source plane, no chain effects.
Parent source: `80cccc3f7c94cc867a1ccfd469e53daa9efd5190` (PR2188 still in CI).
This is an independently reviewed next layer, not a whole-blockchain completion.

## WSP97 retrieval and decision receipt

WSP00 awakening and bootstrap remain active from the parent delivery session.
Refreshed WSP97, WSP15, WSP50, WSP62/87 limits and module memory before authoring.
Canonical Holo query for epoch/Merkle/proof/finalization tests again returns
`HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `ok=false`, `freshness=UNKNOWN`,
`index_gap_detected=true`; no reindex or authority-worktree mutation. Preserve
that maintenance boundary and use explicit degraded direct-source retrieval.

Noise: generated training JSON repeats historical descriptions. Source-only
search removes it. Ordering: current contracts and live consumers before dated
ModLogs. Missing: simulator requirements.txt and memory directory. Staleness:
historical WSP26 Section15 claims do not match the current protocol. Duplication:
there is already one epoch ledger, proof type and settlement-commitment test
owner; extend them. Read README, INTERFACE, ROADMAP, ModLog, tests/README and
tests/TestModLog; inspect NAVIGATION, economics exports, Mesa callsites,
participation sentinel and BTC connector/tests.

Micro: proof verification trusts supplied leaf metadata, epoch leaves omit
FoundUp/epoch, duplicate recording appends before tree completion and overwrites
tree state, caller dictionaries remain aliased, and anchor identity uses new
wall time. Macro: Mesa records UPS pool-distribution evidence through F0, while
work F_i issuance is separate. Keep existing numeric units and pending labels;
do not redefine this as a funded balance or payout ledger.

Dialectic: a new ledger or AMM duplicates existing owners. Aggregate supply-cap
repair is a strong competing P0, but first needs reconciliation of staked/mined
liabilities and release-policy owners. The selected integrity repair has a
bounded invariant and existing consumers; it requires no new financial policy,
provider, schema, SDK, custody, signer or production worker.

WSP15 allocation: C3/I5/D5/Impact5 =18/P0. Need: cryptographic evidence must bind
the claimed recipient, amount and checkpoint before it feeds later chain work.
Affordability: existing ledger/proof owner, existing test owner and module memory,
standard-library implementation. Deferral: unsafe before external commitment
publication. Qwen/Gemma can assist retrieval/classification; implementation and
independent review need exact source contracts and adversarial execution, so
existing 0102 workers handle this local slice without a model/runtime download.

## Bounded contract and authoring budget

- Version leaves/nodes/empty roots and bind FoundUp, epoch, participant and a
  deterministic simulator amount. Verification requires externally trusted root,
  FoundUp, epoch and participant expectations; no internal-root fallback.
- Accept exact built-in int/float only; reject bool, negative and nonfinite
  values. Preserve large integers, normalize integral floats and signed zero;
  compact sorted JSON with allow_nan=False. This is a versioned Python simulator
  encoding, not a chain integer-unit or general cross-language JSON standard.
- Validate complete payload/build privately before state publication. Exact
  epoch retries return the original immutable result; conflicts reject without
  mutation. Old exact retries remain valid after newer epochs. New epochs must
  increase, with gaps allowed. Serialize concurrent publication in this ledger.
- Detach/freeze recorded mappings and tree/entry snapshots. Returned ordinary
  dictionaries/proofs cannot mutate internal state. Repeated pre-settlement
  preparation derives from the finalized context and is byte-stable.
- Preserve pre_settlement / D_pending. The existing BTC connector's content-blind
  replay record and version migration remain a separately named blocker before
  non-mock activation. No new settlement/payment claim.

Product budget: economics/epoch_ledger.py, existing exports only if required,
and one cohesive pure helper only if existing owner size/no-growth requires it.
Do not expand inherited class-size debt or add a parallel ledger. Stop for
reallocation if persistence, accounting policy or connector changes are needed.
Test budget: extend tests/test_epoch_ledger_settlement_commitment.py after the
existing test log/README retrieval; retain its original two oracles. Existing
BTC connector, Layer-D runtime, Sentinel consumers and simulator suite are
regression owners. No new test file.

## WSP6 validation gates

1. Run the two original commitment cases and relevant connector/runtime cases
   on the unchanged parent. Author adversarial cases first; save desired RED
   results before editing production. Keep scratch and daemon storage external.
2. Exercise claim/context/root/path/version tampering, invalid inputs, exact and
   conflicting retries, old retries, monotonic gaps, aliasing/immutability,
   odd trees, build failure, concurrent finalization and stable commitments.
   Save exact collected/passed IDs and failures, not only totals.
3. Run affected source consumers, then connected simulator scope if impact or
   failures require it. Keep HTTP/network/model exclusions explicit and justify
   runner isolation; do not patch auth/economics/assertions.
4. Independent source review and held-out tests before publication; preserve
   any found defect and repair evidence. Check canonical test registry, backend
   manifest reachability and WSP97 structural receipt. Regenerate source closure
   only if this source is in its actual import graph.
5. Dedicated PR after PR2188 main convergence and rebase/readback. Fresh exact
   head CI/security, scoped diff, mergeability and main readback are required.

Durable cross-epoch work-receipt consumption, aggregate issuance caps, CABR epoch
allowance, authenticated issuer/treasury transport, network/asset-bound durable
transaction intent, signing, confirmations, repository claims and venue trading
remain subsequent delivery gates. This layer does not satisfy them.

## Independent review checkpoint (before correction)

The first candidate passes104 focused/adjacent cases and30 independent held-out
cases. Independent review reproduces one latent checker defect: replacing a
private chain-list entry while leaving the epoch index intact can make
verify_chain certify the indexed entry instead of the listed entry. The public
tuple/frozen-entry properties expose no such write, and no persisted import path
exists; this is an integrity-checker limitation, not a demonstrated public
mutation or authorization bypass.

Within the existing18/P0 budget, extend the same test owner with a private-state
corruption regression before correcting list/index consistency. Preserve the
failed candidate evidence and rerun affected checks against a new freeze. The
104/30 results remain bound to the first candidate; they do not qualify the fix.

## Derived source closure and known metadata allocation (before binding)

The ledger is an actual member of the existing RedDog AST import closure.
Canonical regeneration confirms1 changed source hash, no added/removed members
and the same1,470-member bound. WSP15 C2/I5/D5/Impact4=16/P0: update the existing
manifest and its two digest pins plus existing module/test logs, then stage the
coherent binding before the eight unchanged generator cases and three Node
compatibility entrypoints. All byte and member limits remain fixed. This is
source maintenance; the installed runtime and its descriptor are untouched.

Known metadata review: the preceding hosted scanner observed38 source-digest
findings in this manifest. This hash-only update changes their whole-file
fingerprints. WSP15 C1/I4/D5/Impact4=14/P1 permits re-reviewing those38 exact
contexts, their referenced source blobs and prior approvals with an independent
reviewer before adding only their new bindings to the existing ledger. Record
them in one epoch-specific evidence file. No unknown finding, path exemption,
scanner rule or scan scope is approved. A fresh hosted full tree/history scan
remains required; this review is not another scanner execution.

Repaired source qualification:106 focused/adjacent cases,41 independent held-out
cases, and parent whole-simulator410 cases pass. The latter explicitly deselects
only the same3 SSE HTTP cases as the parent baseline, records every test ID,
uses external daemon storage with existing external paths preserved, bypasses
only unrelated Holo/Qwen help enrichment, and observes zero Python network
attempts and stable168 source hashes. Counts overlap and are not added.
The canonical test registry is current:1,769 files/273 quarantined.
