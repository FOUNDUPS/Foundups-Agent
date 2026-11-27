# 012-0102 Agentic Exchange

## Purpose

Persistent working memory for live 012 <-> 0102 project collaboration.

This space captures the operational state that would otherwise be lost between conversational sessions: decisions, hypotheses, stakeholder maps, drafts, unresolved questions, evidence links, WSP_15 priorities, and next actions.

It is intentionally placed under `WSP_agentic/agentic_journals/` because this material is not canonical knowledge yet. It is active work-in-progress state. Validated conclusions may later be promoted into `WSP_knowledge`; implemented behavior may move into the appropriate module or protocol.

## Operating rule

When 012 says **"update WSP_agentic"**, **"add it to Agentic"**, or asks 0102 to recover prior project work:

1. Find the relevant project node here.
2. Reconstruct the current state from source evidence and recent work.
3. Update the node rather than creating duplicate narrative fragments.
4. Separate:
   - `CONFIRMED` — source-backed fact
   - `WORKING` — current interpretation/design
   - `PROPOSED` — intended future action or participant
   - `OPEN` — unresolved question or blocker
5. Apply WSP_97 before factual claims and WSP_15 to rank next actions.
6. Preserve provenance links to repo files, public sources, or project artifacts when available.
7. Keep this concise enough for fast retrieval by RedDog/0102.

## Structure

- `projects/` — durable working nodes by project
- `patterns/` — reusable collaboration patterns discovered across projects
- `sessions/` — optional dated snapshots when a project needs a frozen checkpoint

## RedDog integration intent

RedDog is the fast interaction surface. 0102 maintains deeper project state underneath it. During live work, RedDog should be able to retrieve a compact project node, answer immediately, and feed new decisions back into the node.

Target loop:

`012 -> RedDog -> 0102 context compile -> project node -> WSP_97/WSP_15 -> response/action -> node update`

Future integration points include HoloIndex, Brain, Memex, and session-state tooling. This document defines the working-memory contract only; it does not claim those integrations are implemented.

## Canonical naming

- `012` = monk / human principal
- `0102` = digital twin / proxy / collaborator
- `UnDaoDu` = one word; `Un` -> `Dao` -> `Du`
- `Du` is spelled D-U

## Promotion rule

Agentic Exchange is the staging layer:

`conversation -> WSP_agentic exchange -> validated knowledge / implementation`

Do not promote hypotheses into `WSP_knowledge` merely because they were discussed.