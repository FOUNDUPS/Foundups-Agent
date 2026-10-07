# EDuIT — autonomous learning and discovery

Status: **SPECIFIED_NOT_IMPLEMENTED**. Documentation and declarative onboarding only.
No educational runtime, validated talent detector, deployed route, scholarship pipeline,
token issuance, or autonomous game-publishing worker is claimed.

**EDuIT** is the current styled brand; **EDUIT** is retained in historical quotations.
The original expansion is **Education Using Information Technology**.
Do not use `eDuit` as the brand. Machine identifiers remain `eduit`.
Its mission is accessible, personalized learning through play on ordinary devices.
**EDuIT Discovery** is the new working name for an internal capability that investigates
exceptional domain-specific potential and connects consenting learners with human-reviewed
opportunities. It is not a second FoundUp or a replacement name for EDUIT.

## Historical continuity

The 2007 mission described a web portal and play-learn experience. The 2009 book
named The Tool, The Content, and The Experience, included “No genius left behind,”
and proposed scholarships. The Malaysia prize draft explicitly described identifying
brilliant rural learners through their interactions. The 2023 EDUITs and Baby0 documents
added teaching-tablet, OBAI, adaptive language-learning, and DAE proposals. These are
historical designs, not evidence that the proposed outcomes were achieved.

Read [history](docs/HISTORY.md), [naming decision](docs/NAMING.md),
and the [source register](docs/SOURCE_REGISTER.md) before changing the vision.

## Build order

Begin with one browser-based, low-text game and deterministic adaptation using synthetic
sessions. Preserve learner choice, accessible controls, and offline continuation.
Then validate learning and measurement, build consented profiles, and only later qualify
discovery and reviewed referrals. See [requirements](docs/PRODUCT_REQUIREMENTS.md),
[architecture](docs/ARCHITECTURE.md), [interfaces](INTERFACE.md), and [roadmap](ROADMAP.md).

## Route Namespace

| Field | Declared value; not deployed |
| --- | --- |
| foundup_id | `eduit` |
| routing_prefix / landing | `/f/eduit` |
| app root | `/f/eduit/app` |
| discovery capability | `/f/eduit/app/discovery` |

Discovery is subordinate to the EDUIT tenant. Do not claim `/discovery` or shell-owned
root routes. Existing EDUIT media/social surfaces are not evidence of an educational app.

## App Mount

Planned mount: `/f/eduit/app`. No development or production app URL exists in this package.
Existing `esingularity_001` infrastructure/campaign routes remain unchanged.

## AI Capability Hooks

All hooks are specified, not implemented: `get_status`, `get_context`, `navigate`,
`launch_capability`, and shell handoff/return. [INTERFACE.md](INTERFACE.md) defines access,
inputs, outputs, failure states, and the boundary between learner and operator contexts.
The canonical contract is
[FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md](../docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md).

## DAEmon Outputs

No worker is attached. Future workers must expose health, last action, error state,
recommended next action, queue/work state, and tenant-scoped telemetry. A future
curriculum worker may propose a candidate; it may not approve its own release.
See [governance and RSI](docs/GOVERNANCE_AND_RSI.md).

## Data / Telemetry Namespace

`foundup_id=eduit`; `data_namespace=idb_eduit`.
Separate tenant, organization/cohort, guardian authority, and learner scopes.
Discovery is not a new tenant. Never publish identifiable learner records or derived
ability profiles to blockchain, public GitHub, shared agent memory, or unrelated FoundUps.

## Documentation map

- [Product requirements](docs/PRODUCT_REQUIREMENTS.md), [games](docs/GAME_DESIGN.md),
  [data contract](docs/DATA_CONTRACT.md), [validation](docs/VALIDATION.md).
- [Child safety/privacy](docs/CHILD_SAFETY_AND_PRIVACY.md),
  [governance/RSI](docs/GOVERNANCE_AND_RSI.md), [FoundUp integration](docs/FOUNDUP_INTEGRATION.md).
- [Contribution rules](CONTRIBUTING.md), [test plan](tests/README.md),
  [test inventory](tests/TestModLog.md), [memory boundary](memory/README.md),
  [change log](ModLog.md).

## WSP References

WSP 97 governs evidence-first execution and completion truth; WSP 91 governs DAEmon
observability; WSP 104 governs tenant routing/isolation. WSP 106 is the platform gateway,
not permission to invent an EDUIT backend. Follow the current FoundUp onboarding protocol,
root ROADMAP, and repository bootstrap/admission requirements before implementation.
