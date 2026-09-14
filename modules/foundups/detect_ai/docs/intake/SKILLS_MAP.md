# Can You Detect AI? - Skills Map

## Candidate SKILLz (Not Created - WSP 95 Governs)

Names below describe candidate capabilities, not installed skill IDs. Search the existing registry/wardrobe before creating anything.

| Candidate capability | Purpose | Priority |
|---|---|---|
| intake_duplicate_discovery | Reconcile semantic, registry, catalog and external-repo evidence | P1 |
| blinded_round_contract_review | Validate truth isolation, consent and round transitions | P1 |
| model_configuration_audit | Check approved models, permissions, versions, cost and runtime settings | P1 |
| detector_benchmark_evaluation | Compute scores, calibration, uncertainty and contamination checks | P1 |
| consented_red_dog_case_curation | Curate task-relevance and instruction-following examples | P2 |
| contribution_reward_verification | Verify bounded contribution evidence before existing reward authority | P2 |

P1/P2 are proposed task priorities, not a completed WSP 15 score.

## WRE Integration Points
- `modules/infrastructure/wre_core/`: existing orchestration owner; architect admission and worker dispatch remain downstream.
- `modules/communication/moltbot_bridge/`: existing intake/control-plane context, not a new game orchestrator.
- `modules/ai_intelligence/ai_gateway/`: inspect current inference adapters; repository searches verified OpenRouter catalog-discovery files, not game-ready inference.
- `scripts/openrouter_model_catalog_snapshot_once.py`: existing explicit catalog snapshot entry point; no discovery invocation ran here.
- `modules/ai_intelligence/ai_overseer/`: candidate independent evaluation/verification owner; no verifier is claimed active.
- `modules/foundups/agent_market/` and `modules/foundups/simulator/`: existing ledger/economics owners; audit interfaces and authority before reward integration.
- `extensions/reddog/`: front-interface evaluation target, not a place to hide game-specific matchmaking.

Runtime compatibility, permissions and exact callable interfaces require inspection during preflight. Keep product logic module-local; reuse proven shared services rather than copying speculative architecture.

## Future Slice
DETECT_AI_SKILLZ_WARDROBE_PHASE1

Discover first. WSP 109 creates this map only; WSP 95 governs any actual skill creation, promotion or rollback.
