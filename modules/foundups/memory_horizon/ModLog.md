# Memory Horizon - ModLog

## 2026-09-20 - RSI autonomous-build restaurant-order package

- Confirmed AmIBot/`detect_ai` as the first autonomous-production fixture and reused its bounded production-line pattern.
- Opened issue #1825 for Memory Horizon as our second controlled RSI FoundUp experiment.
- Added a principal-readable launch package plus machine-readable package metadata.
- Added ten WSP 99 `0102_m2m_v1` kitchen tickets: preflight; game shell; measurement engine; procedural content; export/analytics; integration UI; product acceptance; independent research/privacy verification; WSP 102/104 public-surface integration; RSI outcome capture.
- G1 game/measurement/content/analytics writers use disjoint write roots.
- Package validation found all required WSP 99 fields present, all dependencies resolvable, all WSP 15 arithmetic correct, and no exact G1 write-path collision.
- Package remains `PLANNING_NOT_DISPATCHED` / `dispatchable=false`; authored JSON is not a signed WRE work order and grants no OpenClaw/Hermes/OpenRouter authority.

## 2026-09-20 - Low-fi survival game + cognitive sweep architecture

- Added `docs/GAME_DESIGN_SWEEPS.md`.
- Adopted a mechanically inspired low-fi survival/dungeon wrapper: character selection, exploration, randomized events, inventory/status and consequential choices; no copying of Fear & Hunger content/IP.
- Defined Sweeps 0-8 so game and measurement complexity increase one controlled layer at a time.
- Locked Phase 1 to Sweep 0 + Sweep 1: playable survival shell plus adaptive episodic-retention probes.
- Mapped TestMyBrain/NIH/SCAT6 constructs into later, separately scored game mechanics instead of copying their UX.
- Preserved construct separation: episodic retention, working memory, attention/reaction speed and executive switching do not collapse into one black-box score.
- Added natural probe presentations through dialogue, inventory and route choices in addition to explicit quiz cards.

## 2026-09-20 - WSP 97 memory terminology audit

- Retrieved canonical WSP 97, WSP 60, FoundUp Memex, Brain, Breadcrumb, Moshpit, Contact Memory, HoloIndex, AgentDB/workspace-memory and Memory Nudge Engine definitions before further architecture claims.
- Added `docs/FOUNDUPS_MEMORY_TERMINOLOGY_AUDIT.md` as the Memory Horizon terminology gate.
- Corrected the Companion mapping: Brain is a durable-consolidation component **inside** FoundUp Memex; Memex is not a synonym for Brain.
- Corrected HoloIndex and Memory Nudge Engine analogies: neither is automatically the proposed human-memory retriever/cue engine.
- Marked exact term `Memic` as `UNRESOLVED_TERM_MEMIC`: no canonical current repo, issue, branch, or retrieved historical definition found. No silent normalization to Memex.
- Future 012-supplied system terms require exact retrieval and truth labeling before use.

## 2026-09-20 - Assistive Memory Companion extension

- Added the deferred **Memory Horizon Companion** architecture: a "memory seeing dog" that turns lived events into private episodic breadcrumbs and provides evidence-ranked just-in-time cues when recall fails.
- Mapped the concept onto existing WSP 60 / RedDog memory roles: episodic Breadcrumbs, Brain/Memex consolidation, retrieval, working context and the attention/nudge boundary.
- Added MemPal, SenseCam, iRemember and ambient-wearable comparators to the research record.
- Opened issue #1823 for the deferred Companion research/architecture track.
- Preserved #1821 as the primary bounded POC; no wearable runtime or clinical claim is activated.

## 2026-09-20 - WSP 109 intake

- Created `memory_horizon` as a FoundUp registration candidate.
- Defined the adaptive episodic-memory game concept and retention-curve outcome.
- Added explicit non-diagnostic medical boundary.
- Added POC/MVP roadmap, event/probe/scoring contract, research references and validation gates.
- Proposed future host `memory.foundups.com`; no DNS or public activation.
- Opened issue #1821 for the bounded POC.
