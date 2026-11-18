# Preserved planning delta: ROADMAP.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `modules/foundups/agent_market/ROADMAP.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `8349cd4461ac21519d98862397c0e643e0895a23c8d08411856b629733f358ab`
- Preserved record SHA-256: `c9b011947ca1db3cade38447320b488050155d3f69c84cb0eef67bacffddf6a5`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [README.md](../../../../../../../../modules/foundups/agent_market/README.md), [authorization.py](../../../../../../../../modules/foundups/agent_market/src/authorization.py), [sqlite_adapter.py](../../../../../../../../modules/foundups/agent_market/src/persistence/sqlite_adapter.py), [FOUNDUPS_FX_CHAIN_DELIVERY_PLAN_20261025.md](../../../../../../../architecture/FOUNDUPS_FX_CHAIN_DELIVERY_PLAN_20261025.md)

Disposition: Archive the P0A roadmap patch. Keep current roadmap and authorization/payout ownership; do not restore old missing-authorization/non-atomic statements where current source has changed. Preserve signing, funding, issuer, confirmation and retry qualification as separate current delivery requirements.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical patch (not for application)

```diff
--- HEAD/modules/foundups/agent_market/ROADMAP.md
+++ PC/modules/foundups/agent_market/ROADMAP.md
@@ -57,9 +57,15 @@
 - `tests/test_repository_factory.py`
 
 ### Tranche 3: Chain Adapter (Planned)
+- [x] Local P0A: exact fail-closed backend selection for deployment/vesting;
+  preserve identified simulation and validate returned chain identity (2026-10-22).
 - One concrete token adapter (Hedera or EVM)
 - Chain-agnostic interface preservation
 - Test doubles for CI
+- Remaining pre-chain gates: shared verifier/treasury authorization, atomic
+  replay-safe payout intent, proof/supply/epoch accounting and independently
+  confirmed network-scoped settlement. See the current blockchain orchestration
+  plan; P0A does not promote chain readiness.
 
 ### Tranche 4: Role Refinement (Planned)
 - Role model for verifiers/governance actors
```
