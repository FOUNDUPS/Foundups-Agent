# Slow rescue and creature-agent direction

2026-10-27 JST. Baseline main `cc4343dd9f59ebd21bbac600f908bed5c4e5dfe1`.
Latest012 direction supersedes the15-second **game** invariant. Film duration and
game duration are separate contracts. Preserve ages3–4, cast, scene geography,
dark-earth continuity, sound/word pairing and existing Shorts/Mall owners.

## Implemented candidate: understandable rescue sequence

One goal: notice a creature wake, then guide it to the **green hanging vine**.
The vine is the destination, not an added marker. The shelter behind it is the
safe root pocket. Keep movement visible. No separate destination-point graphic.

- Timed round60 active seconds; danger closes at48; collapse/reveal takes the
  remaining12. All five can arrive before48 with deliberate interaction.
- Parents need3/4 taps and travel4/4.5s; babies need1/2/2 taps and travel2/2.4/2.2s.
  Partial wake persists8s; fully awake waits10s before dozing. These are authored
  fictional profiles, not biology or learning about a child's reaction ability.
- One predictable light sleeper wanders/sniffs once at6s, then returns to sleep.
  First-round wake behaviour is deterministic. Randomness would obscure the
  action/consequence lesson; seeded variation belongs in later agent trials.
- Cracks progressively extend, branch and shed dirt. The vine shudders. All
  effects follow world state independently of caption size and viewport size.
- A safe arrival awards10 points plus a bounded0–10 speed bonus in timed mode.
  Formula:10 + max(0,floor(10*(1-arrivalActiveSeconds/48))). No per-tap points,
  negative penalties, ranking, purchases or persistent score collection.
  Award once per actor; display the earned increment and round total.
- Untimed practice holds danger at30 world seconds; each rescue earns10, no speed
  bonus. Pausing/hidden page/feedback freezes the active clock. Restart clears the
  round and pauses; replay preserves practice mode. All rescued ends successfully.
- Original15s film remains the upper panel. Game uses its original sound snippets
  at independent game cue times, never slows MP4 playback or seeks to60seconds.
  Listening and native audio permission behaviour require separate evidence.
- Main toolbar targets64 CSS pixels, fullscreen toggle60. Use measured rendered
  bounds, not declared CSS alone; keep rail outside the16:9 art.

## User direction retained: creature agents, not merely point-and-click

SPECIFIED_NOT_IMPLEMENTED. The manual game is the deterministic fallback and
reference simulation. Next prototype lets each creature operate through its own
bounded behaviour policy. The child influences a living scene rather than directly
commanding every movement. Do not label today's scripted sleeper as connected AI.

### Trait, state and learned-policy separation

A proposed versioned creature record contains stable actor ID, seeded trait vector,
current needs, observation snapshot, policy version and bounded learning state.
Example fictional traits: alertness, sleep persistence, curiosity, caution,
movement pace and social following. Hunger/fatigue/fear are changing **states**,
not immutable genes. Traits affect tradeoffs, never guarantee a superior animal.
Keep household/child information out of these records.

Rust is a design inspiration for seeded traits and reproducible cloning, not a
biology curriculum or code/asset license. Its official plant model uses six slots
with growth/yield/hardiness/water/empty traits. We will author shrew-appropriate
traits instead of relabeling plant genes or copying game assets. Cloning copies a
trait seed/vector; bounded mutation/selection is a later experiment. Do not imply
that experience rewrites inherited traits, that individuals evolve into humans,
or that survival in one episode proves biological fitness.

Separate three values: child rescue score, simulated agent reward, and independent
quality rating. None is a genetic worth or child intelligence score. Learning first
means a tested policy update from synthetic simulation outcomes, not in-browser
LLM weight training. Replay identical seeds/environment across candidate and
baseline, include withheld seeds, preserve rollback, reject regressions. The next
actual story is the transfer test; do not fabricate a successful forward test.

### Browser policy boundary and honest status

Reuse the existing EDUIT scene/state owners. Define a future controller seam:
`observe(actorId, boundedWorld) -> propose(action) -> validate -> advance`.
Allowed proposals only: rest, wake, sniff, walk-to-vine, follow an allowed actor.
No arbitrary JavaScript/DOM access, network tools, credentials or page navigation.
The deterministic engine owns physics, hazards, score and allowed locations.
Validate actor/revision/sequence, finite bounded values and legal transitions;
reject stale/late responses. Pause/reset/locale change cancels in-flight decisions.

One shared model worker can serve five separate actor states; five independent
model downloads are unnecessary. Load on adult opt-in only. Check backend support,
actual allocation/load, a bounded test inference, latency and memory before
showing **AI connected**. States: manual, loading, ready, unavailable, failed.
WebGPU presence or device name is not proof of successful inference. Failed load,
OOM, timeout, hidden-page suspension or worker loss returns safely to manual mode,
with score/state retained and no surprise cloud fallback. Keep loading/status in
grown-up controls; the child-facing view stays minimal.

Gemma3 270M is a candidate, not a selected/bundled/tested browser runtime. Repo
Gemma references inspected in `video_indexer/src/gemma_segment_classifier.py`
use host `llama_cpp`; that does not establish a phone/browser adapter. Evaluate
existing small-model/browser owners before adding a runtime. Budget download,
startup, memory, battery and action latency on actual supported iPhones/tablets.
A compact policy may outperform a language model for this bounded action space;
compare against deterministic baseline. No paid provider, model download or WRE
activation is part of this change.

### Learning, recording and next scenes

Keep simulation experiment traces distinct from children's play. No automatic
child telemetry, cloud training or cross-child leaderboard. Any optional local
history has a parent-controlled delete/export boundary and storage limits.
Model-assisted quality rating is advisory; independent deterministic assertions
and observed output remain acceptance authority, not a model grading itself.

Next scene proposal: water enters the burrow; a visible right-hand opening offers
escape. Specify water level/collision/path before implementation. Successful rescue
may later unlock this scene through existing episode/Mall content owners. Do not
show a live Next destination until a reviewed stage actually exists.

Future play-to-video: record an explicit local event trace with seed, source
revision, locale, deterministic actions and times, then replay through the shared
scene/renderer. Parent preview precedes explicit export/share. Scores in export
must come from replay; no camera/microphone/child identity by default. Current
upper video is authored media, **not** a recording of current gameplay. Longer
movies and authentic game replay require renderer/cue/audio validation, not a
changed duration label. Keep YouTube publishing separate and owner-bound.

## Reusable RSI / skillz ownership

Use [interactive experience review](../skillz/interactive_experience_review/SKILLz.md)
for this game and later game/website work, plus the existing Shorts production
skill for media. It freezes audience, objective, baseline and rubric, then runs
build → inspect → independently review → repair → recheck → retain. Existing
`modules/gamification/games` is chat chess/checkers; do not relocate this browser
game or create a duplicate game manager. It links the same review skill.

The root ROADMAP and existing WRE outcome/pattern-memory/admission owners remain
authoritative. This is a versioned prototype skill and manually executed review,
not an installed continuous RSI worker. Promotion requires independent evidence,
retained reuse on later real work and admitted execution/budget/rollback.

## WSP97 evidence and WSP15 allocation

OBSERVED: source-bound Holo lexical bundle at baseline cc4343d; freshness UNKNOWN,
index_gap_detected=true, no semantic index/reindex claim. Exact files read to
resolve noisy broad hits. Missing optional memory/README and SPEC are not invented.
V2 bootstrap could not import torch; existing tracker fallback reported compliant.
No Qwen/Gemma runtime binding here; manual implementation and independent review.

Planning allocation C3/I5/D4/Impact4=16/P0 for playable timing/readability; bounded
browser/Node validation before security/CI. Agent runtime/trait-learning and flood
stage remain later prototype scope. Need: allow preschool response time. Afford:
reuse deterministic scene/engine, no paid generation. Cannot defer: unfair timing
and tiny controls. Can defer: model provisioning, breeding and new episodes.

## Official source observations (read2026-10-27 JST)

- https://wiki.facepunch.com/rust/Farming — six plant slots and trait definitions;
  mechanic inspiration only, not shrew science.
- https://rust.facepunch.com/news/farming-update —2020-04-02 update describes
  cloning carrying plant genetics; no source code or imagery reused.
- https://developers.googleblog.com/introducing-gemma-3-270m/ —2025-08-14,
  compact task-specific model and Transformers.js web example. Not an iPhone
  compatibility/performance guarantee. Metadata/text inspected, no demo run.
