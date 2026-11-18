# Foundups®Agent Extension F0 Safety Audit

**Date:** 2026-06-24
**Slice:** FOUNDUPS_AGENT_EXTENSION_BRANDING_AND_F0_SAFETY_PHASE1
**Calibration:** DOCS_PLUS_MANIFEST

## Purpose

Rename the user-facing extension surface from "FoundUps Fusion Worker" to
"Foundups®Agent" while preserving the current authority boundary.

Foundups®Agent is the product surface. RedDog is the 0102 digital-twin architect
inside it. Fusion is one internal reasoning mode, not the product identity.

## Current Capability Matrix

| Capability | Current Status | Boundary |
|---|---|---|
| Bounded repo context | YES | Extension gathers limited WSP/HoloIndex/editor/git/Skillz context |
| HoloIndex recall | YES | Retrieval evidence only; weak recall must be reported |
| OpenRouter egress | YES | Redaction gate runs before network |
| WSP_00/WSP_97/WSP_15 advisory review | YES | Model output is advisory only |
| Review packet copy | YES | Redacted packet for 0102 review |
| Model-controlled repo edits | NO | No write tool exposed to model |
| Model-controlled shell execution | NO | No shell authority exposed to model |
| Merge/deploy/repo creation | NO | Sovereign/WRE-governed only |
| Skillz/OpenClaw/Hermes execution | NO | Recommendation only |
| CABR/pAVS authority | NO | No benefit, payout, or source-authority claim |

## F0 Threat Model

F0 is the foundation Foundups-Agent repo. Foundups®Agent must never mutate F0
automatically.

Threats considered:

- malicious work focus prompt injection
- malicious repository content in bounded context
- accidental inclusion of secrets or gitignored files
- model-generated malware or worm instructions
- extension-host command execution expansion
- OpenRouter data egress before redaction
- automatic repo mutation, merge, deploy, or package install behavior
- false WSP/CABR/source-authority claims

## Safeguards

- 012 supplies work focus only; 0102 assembles WSP task prompt.
- Redaction gate runs before any OpenRouter call.
- The extension provides no model-controlled file write, shell, browser, merge, or
  deploy tool.
- Skillz/OpenClaw/Hermes/WRE surfaces are advisory handoff candidates only.
- `.env` and gitignored secret ingestion remain out of scope.
- WSP_97 truth labels are required for substantive claims.
- Any future execution path must go through governed WRE/OpenClaw/Hermes handoff.

## Future Any-Repo Path

FoundUps Agent Intake Mode should assess external repositories without mutating them:

1. WSP readiness audit
2. FoundUp intake packet
3. Skillz map
4. integration risk report
5. governed WRE handoff recommendation

No automatic onboarding, package install, repo mutation, publication, CABR claim, or
FoundUp registration is permitted in this phase.

## WSP_97 Truth Table

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|---|---|---|
| 1 | FOUNDUPS_AGENT_IS_PRODUCT_SURFACE | OBSERVED | package.json displayName and docs use Foundups®Agent. |
| 2 | REDDOG_IS_ARCHITECT_INSIDE_AGENT | OBSERVED | README, INTERFACE, ROADMAP state RedDog is the 0102 architect inside Foundups®Agent. |
| 3 | FUSION_IS_INTERNAL_MODE | OBSERVED | README, INTERFACE, ROADMAP state Fusion is an internal reasoning mode. |
| 4 | PACKAGE_ID_STABLE | OBSERVED | package.json name remains foundups-fusion-worker. |
| 5 | F0_NO_AUTO_MUTATION | SPECIFIED_NOT_IMPLEMENTED | Docs define boundary; no new execution path added. |
| 6 | MODEL_NO_SHELL_AUTHORITY | OBSERVED | Extension contract exposes no model-controlled shell tool. |
| 7 | GOVERNED_HANDOFF_ONLY | SPECIFIED_NOT_IMPLEMENTED | Handoff execution remains roadmap only. |
| 8 | ANY_REPO_INTAKE_ADVISORY_ONLY | SPECIFIED_NOT_IMPLEMENTED | Intake mode is roadmap only; no runtime wiring added. |
