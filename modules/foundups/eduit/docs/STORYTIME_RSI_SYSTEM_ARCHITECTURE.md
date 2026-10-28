# Storytime RSI system architecture — continuation node
Date: 2026-10-28. Status: architecture and integration map, **not** autonomous production activation.

## Mission, product and hierarchy
eSingularity is the broad educational-singularity paradigm; EDUIT is the open, decentralized, self-directed education mission within FoundUps. Storytime is one educational workload, not a new platform. Its initial audience is young learners (roughly third-grade entry), with age-appropriate review. Narrative content spans an evolutionary journey, with optional future GEOZE/tardigrade arcs. Treat evolutionary branching and dates as research claims requiring independent scientific verification; the fictional Little Shrew is not an identified direct human ancestor.

**Journey → epochs → episodes → blocks → tiles.** A tile is a versioned **video plus matching playable game**, learning objective and synchronized cues. A block groups tiles; an episode groups blocks; an epoch groups episodes. These content units are not FoundUps and do not create tenant identities. A five-tile production batch is an operator batch, not necessarily a narrative block or five-mission player set. The first Little Shrew tile is the calibration fixture; do not mass-produce until a second real tile proves transfer.

## Existing owners — reuse, do not clone
| Boundary | Canonical owner / file | Role and evidence limit |
|---|---|---|
| WSP governance and independent validation | `WSP_framework/src/WSP_41_WRE_Simulation_Protocol.md`, WSP 48, WSP 97 | WSP compliance and bounded validation; written protocols do not prove live autonomy |
| WRE outcome learning | `modules/infrastructure/wre_core/src/pattern_memory.py` | Existing SkillOutcome and learning-event storage; no EDUIT-specific second memory |
| WRE bounded candidate loop | `modules/infrastructure/wre_core/src/wre_auto_researcher.py` | Candidate/evaluate/retain design; Storytime judge and live commit remain unproved |
| WRE admission | `modules/infrastructure/wre_core/src/skill_runtime_admission.py` | Reuse existing runtime authority; no fabricated grant |
| Retrieval and continuity | `holo_index/` and `holo_index/docs/WRE_INTEGRATION_DESIGN.md` | Ground code/WSP ownership; verify freshness, don't equate retrieval with execution |
| Work tickets and verification | `modules/foundups/agent_market/src/task_pipeline.py` | Task/Proof/Verification and existing FAM ticket lineage |
| OpenClaw/Hermes coordination | Existing WRE allocation / `docs/operations/RSI_SWARM_DISPATCH.md` | Hub/leaf only when qualified; no new scheduler or parallel backlog |
| Story and media checks | `modules/foundups/kids_episodes/src/story_pipeline.py` | Existing story pipeline and independent review |
| Five-tile planning | `modules/foundups/kids_episodes/src/tile_batch.py` | Deterministic plan and record completeness only, not admitted execution |
| Production boundary | `modules/foundups/kids_episodes/src/work_order_adapter.py` | Fail closed on missing executor, workspace or authority |
| Model comparison | AI Gateway `model_champion_challenger_autoresearch.py` | Fixed test/rubric, identical budgets; GLM or others only when available and admitted |
| Browser game and shared film scene | `public/eduit/storytime/engine.mjs`, `scene.mjs` | Keep one paired revision and learning cues; don't replace the working prototype |
| Site and Shorts packaging | `modules/foundups/eduit/build_site.py`, `render_story_preview.py` | Local media and site output, not proof of release |
| Child-facing review | `modules/foundups/eduit/skillz/interactive_experience_review/SKILLz.md` | Age, controls, education and lifecycle evidence; independent output review still required |
| Mall integration | `public/member/INTERFACE.md`, `modules/foundups/eduit/docs/EPISODE_MALL_ARCHITECTURE.md` | Existing product-scoped shell; no duplicate Mall or per-tile FoundUp |

## Operational RSI path (proposed, not yet admitted end-to-end)
1. **Retrieve** README, INTERFACE, ROADMAP, ModLog, this map, `docs/TILE_PRODUCTION_RSI.md`, Kids Episodes interfaces, and current WRE/RSI admission contracts. Confirm main/PR/CI state; historical notes are not current runtime proof.
2. **Freeze** Little Shrew tile specification, film/game revision, learning objective, audience, approved scientific claims, acceptance rubric, fixed test seeds, budget and rollback baseline.
3. **Plan** five ordered tiles via the existing Kids Episodes planner, but authorize and build **only the next real tile**. Resolve canonical ticket IDs, both artifact digests, independent verifier and grant/lease through existing FAM/WRE owners.
4. **Execute** within admitted scope: author game/video, render and run existing tests, inspect actual visual/audio outputs and accessible controls. A source check is not a listening or device test.
5. **Critique and repair** against the *frozen* `eduit.tile_acceptance.v1` oracle. Limit iterations and spend; reject/revert on failure. Independent reviewer must be outside author authority.
6. **Retain** a candidate correction in existing WRE Pattern Memory with evidence, cause, accepted/rejected status and rollback. Never ingest child play records or claim self-training.
7. **Forward-test** on a genuinely different next tile and compare baseline vs candidate under identical conditions; only measured transfer earns an RSI-improvement claim. Hold subsequent four if the first transfer fails.
8. **Publish** only after existing human/owner, licensing, science, privacy and release gates. Keep local completion, PR merge, deployment and learning evidence as separate states.

## Known state and blockers (as of this documentation review)
- Local Little Shrew scene/game and media packaging exist. The five-tile planner/record checker exists. Manual correction-and-review cycles are documented.
- **Not proved:** admitted production executor, end-to-end authenticated author/verifier ticket flow, live autonomous five-tile run, persistent promotion consumed on next tile, independently measured transfer, production Mall mounting and public deployment.
- The RSI swarm handoff records missing owner/authority artifacts and authenticated caller/lease connections; it explicitly forbids a new orchestrator. See `docs/operations/RSI_SWARM_DISPATCH.md`.
- Do not claim current branch, tests or hosted CI from historical snapshots; inspect live evidence before each merge.

## New-session continuation contract
Start at `modules/foundups/eduit/README.md` → this architecture → `INTERFACE.md` → `ROADMAP.md` → `docs/TILE_PRODUCTION_RSI.md` → `ModLog.md`. Follow references to the existing WRE/FAM/Kids Episodes/Mall owners, reconcile their current state, then choose the smallest bounded gap. A documentation PR is a memory node, **not** proof of autonomous RSI. Record branch, PR, squash SHA, checks and remaining blockers in the existing ModLog when verified.
