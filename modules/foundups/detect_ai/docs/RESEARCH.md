# Can You Detect AI? - Research and Decision Record

Checked: 2026-09-15. Sources below support the stated limited claims, not product readiness.

## Existing Game

[Human or Not](https://humanornot.so/) currently describes a two-minute conversation with either a human or AI, followed by a guess, and exposes a leaderboard. This establishes that the core consumer mechanic already exists. Current feature depth, audited model rankings, token systems and agent-judge support were not independently established.

[Jannai et al., Human or Not? A Gamified Approach to the Turing Test (2023)](https://arxiv.org/abs/2305.20010) reports an earlier large-scale study using short human-or-model chats. It supports the feasibility of recruiting participants for this format, not guaranteed adoption of a new FoundUp. The current website and historical study must not be assumed identical in ownership, implementation or dataset.

## Controlled Test

[Jones and Bergen, Large Language Models Pass the Turing Test (2025)](https://arxiv.org/abs/2503.23674) tested ELIZA, GPT-4o, LLaMa-3.1-405B and GPT-4.5. Its abstract reports that persona-prompted GPT-4.5 was selected as human 73% of the time in its three-party protocol. That is not a general leaderboard or an estimate directly comparable to this proposed two-party game. Grok was not among the four listed systems.

Searches for Grok plus Turing-test/leaderboard/human-detection terms did not establish a reliable source for the earlier claim that Grok leads this specific game or test. Leave that claim UNVERIFIED; do not substitute an unrelated reasoning or preference benchmark.

## Platform Decision

[Discord Activities overview](https://docs.discord.com/developers/activities/overview) states that Activities are web apps hosted in an iframe using the Embedded App SDK. Therefore a browser-first app can later share its application logic/backend with a Discord surface. This is an architectural option, not an integration already implemented or an automatic exemption from Discord review/policies.

Decision: browser-first for public accessibility and experimental control; Discord for pilot coordination first, optional embedded distribution later. Ordinary bot-tagged chats are unsuitable for hiding assignment type.

## Product Hypotheses to Test

Players may value calibrated skill progression; builders may value small-model performance-per-cost comparisons; communities may sustain recurring evaluation cohorts. Token incentives may improve useful participation, but may instead attract farming and contaminate data. Test contribution quality before economics activation. No willingness-to-pay or reward-budget evidence was collected.

## Repository Authority

[WSP 109](../../../../WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md) defines intake-only scope and the eight required artifacts. [WSP 97](../../../../WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md) requires retrieval, comparison and bounded execution. [FoundUps domain index](../../docs/FOUNDUPS_DOMAIN_CANONICAL_INDEX.md) distinguishes planning from current implementation and identifies existing shared orchestration/ledger owners. The product does not replace those owners.
