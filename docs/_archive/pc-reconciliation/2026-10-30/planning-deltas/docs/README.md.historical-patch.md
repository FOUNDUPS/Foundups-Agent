# Preserved planning delta: README.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `docs/README.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `f0d7a2d93c0b4ce7e05993285dd7e1df3657e5596c4714784be774d33218b42c`
- Preserved record SHA-256: `90b554232d7ca01b4480afaa9473e4a0c1b76c6c6376444f790699149865f80c`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [FOUNDUPS_DOMAIN_CANONICAL_INDEX.md](../../../../../../modules/foundups/docs/FOUNDUPS_DOMAIN_CANONICAL_INDEX.md), [doc_dae.py](../../../../../../modules/infrastructure/doc_dae/src/doc_dae.py)

Disposition: Keep the current documentation index. Preserve the six-line navigation/count/date change as a historical patch, and expose the three recovered plans through this archive. Regenerate the owned doc index only after accepted publication; do not restore the old document count or last-updated date.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical patch (not for application)

```diff
--- HEAD/docs/README.md
+++ PC/docs/README.md
@@ -4,7 +4,7 @@
 
 **Status:** ACTIVE
 
-**Last Updated:** 2026-08-28
+**Last Updated:** 2026-10-22
 
 **WSP Compliance:** WSP 22 (ModLog), WSP 50 (Pre-Action Verification), WSP 87 (Code Navigation)
 
@@ -14,7 +14,7 @@
 
 | Category | Count | Description |
 |----------|-------|-------------|
-| [Architecture](#architecture-documents) | 8 | System architecture and design patterns |
+| [Architecture](#architecture-documents) | 11 | System architecture and design patterns |
 | [Daemon & Event Systems](#daemon--event-systems) | 3 | Daemon orchestration and event-driven flows |
 | [Vision & Automation](#vision--automation-systems) | 3 | Browser automation and vision AI systems |
 | [0102 Session Briefings](#0102-session-briefings) | 1 | Session-start onboarding digests for 0102 |
@@ -30,6 +30,9 @@
 
 | Document | Status | Purpose | WSP References |
 |----------|--------|---------|----------------|
+| [Autonomous FoundUp pitch/deck and project claim](architecture/FOUNDUPS_AUTONOMOUS_PITCH_DECK_AND_PROJECT_CLAIM_PLAN.md) | Local instruction skill + proposed integration | RedDog-to-brief generation, matching pitch/deck/media, GitHub verification sash and connection to public discovery/tokenization | WSP 27, WSP 50, WSP 95, WSP 97, WSP 109 |
+| [FoundUps discovery and external-project onboarding](architecture/FOUNDUPS_DISCOVERY_AND_EXTERNAL_PROJECT_ONBOARDING_PLAN.md) | Proposed | Landing audit, discovery-first root/About split, external-project claims, authorized token creation, and market admission | WSP 50, WSP 97, WSP 104, WSP 106, WSP 109 |
+| [FoundUps blockchain testnet orchestration plan](architecture/FOUNDUPS_BLOCKCHAIN_TESTNET_ORCHESTRATION_PLAN.md) | Proposed | Inventory, contribution accounting, pool decisions, simulator gates, and staged Algorand testnet settlement | WSP 26, WSP 29, WSP 50, WSP 77, WSP 97, WSP 101 |
 | [ARCHITECTURE.md](ARCHITECTURE.md) | ✅ Active | Core system architecture overview | WSP 1, WSP 3, WSP 49 |
 | [THREE_STATE_ARCHITECTURE_COMPLETE.md](THREE_STATE_ARCHITECTURE_COMPLETE.md) | ✅ Complete | WSP_knowledge/framework/agentic three-state design | WSP 1, WSP 32, WSP 57 |
 | [KNOWLEDGE_ARCHITECTURE_FIRST_PRINCIPLES.md](KNOWLEDGE_ARCHITECTURE_FIRST_PRINCIPLES.md) | ✅ Active | Knowledge management and memory systems | WSP 60, WSP 48 |
```
