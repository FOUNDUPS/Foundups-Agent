# Progressive Execution Agent - Manifest Draft

## Registry Fields (Draft)

| Field | Value |
|---|---|
| foundup_id | progressive_execution_agent |
| display_name | Progressive Execution Agent |
| entity_type | foundup |
| module_path | modules/foundups/progressive_execution_agent |
| stage | incubating |
| tier | F0_DAE |
| implementation_status | SPECIFIED |
| token_status | TOKEN_DEFERRED |
| poc_status | idea |
| next_slice | PROGRESSIVE_EXECUTION_AGENT_POC_PHASE1 |

## Notes
- Display name is provisional; the architecture should be committed before branding.
- Source should begin inside the Foundups-Agent monorepo because the FoundUp depends directly on WRE, WSP 95 SKILLz, WSP 97 execution discipline, FoundUp project state/Memex, and downstream registry/catalog conventions.
- Do not create an independent repository for the PoC. Reassess an external deployment sleeve only after the graph/evidence/capability contracts stabilize and there is a concrete distribution or technology boundary that benefits from separate lifecycle management.
- The FoundUp must not implement a second WRE or central SKILLz engine. Its core ownership is project-state modeling, dependency/evidence evaluation, capability demand, progressive disclosure, and FoundUp-specific user experience.
- The first PoC environment is the Fukui E-Singularity community-feasibility workflow, but E-Singularity facts must not become reusable skill constants.