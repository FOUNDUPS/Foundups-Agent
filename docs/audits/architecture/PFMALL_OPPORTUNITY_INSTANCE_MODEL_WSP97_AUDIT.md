# PFMALL_OPPORTUNITY_INSTANCE_MODEL_WSP97_AUDIT

**Date**: 2026-08-25  
**Scope**: Documentation-only architecture correction  
**Execution plane**: WRE not applicable; no runtime or autonomous execution change

## WSP 97 retrieval basis

Reviewed before mutation:

- `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`
- `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md`
- `modules/ai_intelligence/digital_twin/INTERFACE.md`
- `extensions/reddog/README.md`
- `extensions/reddog/INTERFACE.md`
- `modules/foundups/docs/FOUNDUPS_MASTER_ARCHITECTURE.md`
- `modules/foundups/docs/FOUNDUP_TEMPLATE.md`
- `modules/foundups/docs/PFMALL_LAUNCH_CATALOG_TAXONOMY.md`
- `modules/foundups/docs/PFMALL_ROUTING_DISCOVERY_MODEL.md`
- `modules/foundups/docs/FOUNDUPS_DOMAIN_CANONICAL_INDEX.md`
- `modules/foundups/pfmall/README.md`

## Findings

1. RedDog is already canonically defined as the operator-facing 0102 Digital Twin/product/conversation surface.
2. PFMall is already canonically a thin presentation client/surface for RedDog; authenticated resident transport remains specified, not implemented.
3. OpenClaw/WRE/Hermes are execution substrate and must not be reclassified as catalog FoundUps.
4. The five-layer FoundUps funnel remains valid and should not be changed.
5. Current p.fMALL taxonomy catalogs FoundUps themselves; no reviewed canonical document defines a reusable public projection for concrete opportunity instances beneath a FoundUp.
6. Therefore the smallest additive change is a planning model for opportunity instances that references existing RedDog authority contracts rather than redefining them.

## Dialectic sweep

### Competing move A: Keep Progressive Execution Agent as its own FoundUp
Rejected. It duplicates shared RedDog/0102/OpenClaw/WRE execution responsibilities and would incorrectly expose infrastructure as a marketplace product.

### Competing move B: Rewrite RedDog/pfMALL architecture
Rejected. The active Red Dog Digital Twin contract already defines the relationship. Rewriting it would create redundant or conflicting authority.

### Competing move C: Add opportunity instances directly to runtime catalog/schema now
Rejected. No typed contract, privacy boundary, or implementation slice has been validated yet.

### Chosen move
Add a planning-reference opportunity-instance model only, index it in the FoundUps canonical navigation document, and defer runtime/schema work to separate research-first PRs.

## Truth boundaries

- No runtime behavior changed.
- No RedDog authority changed.
- No FoundUp registered.
- No catalog or registry mutated.
- No opportunity schema implemented.
- No token/economic behavior changed.

## Correction of prior work

PR #1548 was closed unmerged because it misclassified shared execution capability as a standalone FoundUp.

PR #1549 was closed unmerged because it mixed the missing opportunity-instance concept with redundant RedDog/pfMALL architecture descriptions.

The replacement change is intentionally smaller and evidence-bound.
