---
name: linkedin_article_targeting
description: LinkedIn publishing discovery and routing skill for searching historical articles, listing publishing entities, and resolving the best LinkedIn target for a new article brief or title.
version: 1.0.0
author: 0102
agents: [qwen]
dependencies: [linkedin_agent]
domain: social
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
owning_module: modules/platform_integration/linkedin_agent
executor: executor.py
category: workflow
evals: []
---
# LinkedIn Article Targeting Skill

Use this skill when 0102 needs to answer:

- Where should this article be published?
- Which LinkedIn entity has already published work on this topic?
- What articles already exist across the LinkedIn publishing ecosystem?

## Supported Actions

| Action | Description |
| --- | --- |
| `list_entities` | Return the known LinkedIn publishing entities and metadata |
| `search_articles` | Search published article titles across all known entities |
| `resolve_target` | Recommend the best publishing entity for a new article |

## Execution Contract

1. Load the canonical publishing map from `data/linkedin_publishing_map.json`.
2. Use `list_entities` for account discovery and manage/article URLs.
3. Use `search_articles` to find precedent in historical titles.
4. Use `resolve_target` for heuristic routing based on title, brief, body, and optional preferred entity.
5. Treat results as discovery/routing evidence, not a guarantee that live posting is already wired.
