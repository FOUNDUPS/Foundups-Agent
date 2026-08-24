# Progressive Execution Agent - Solution Definition

## Core Solution
A dependency-aware progressive execution FoundUp that maintains a whole-project graph, evidence ledger, stakeholder map, constraints, and opportunities; identifies the highest-value unresolved gap; resolves the required capability through WRE/WSP 95; invokes a validated SKILLz; captures the resulting evidence; and compresses the updated state into one next action for the founder.

## Key Capabilities
1. Project graph and evidence-ledger state model.
2. Next-best-action arbitration using verified evidence, dependencies, deadlines, blockers, and opportunities.
3. Capability-to-SKILLz resolution through existing WRE rather than a parallel skill engine.
4. Progressive disclosure UI that shows the founder one immediate objective/task while the DAE reasons over the complete project.
5. Field evidence capture: voice, forms, documents, images, claims, objections, referrals, and provenance.
6. Explicit authority states separating agent inference, evidence-backed claims, external verification, and principal approval.
7. Audience-specific read-only projections that minimize disclosure rather than falsely claiming browser content cannot be copied.

## Differentiation
Traditional project-management tools expose plans, tasks, and dashboards and require the user to understand what should happen next. This FoundUp treats the DAE as the cognitive project operator: the project model remains nonlinear and globally visible to the DAE, while the human receives a deliberately compressed execution surface.

## Technical Approach
The FoundUp should consume existing Foundups-Agent architecture rather than duplicate it:

FoundUp Memex / project state -> dependency and evidence evaluation -> DAE identifies critical gap -> capability request -> WRE resolves WSP 95 SKILLz -> execution/evidence receipt -> ledger update -> graph reevaluation -> next action projection.

Project-specific facts belong in FoundUp state/configuration. Reusable procedures belong in SKILLz. WRE owns skill loading/execution. The FoundUp owns the project graph, evidence state, capability demand, and user-facing progressive execution experience.