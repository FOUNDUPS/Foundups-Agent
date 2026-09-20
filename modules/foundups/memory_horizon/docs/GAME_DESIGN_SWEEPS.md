# Memory Horizon - Game Design Sweeps

Status: DESIGN_CONTRACT / SPECIFIED_NOT_IMPLEMENTED.

## Design thesis

Our Memory Horizon game should feel closer to a deliberately low-fi, unforgiving
survival-dungeon game than to a neuropsychology website.

The visual and interaction reference is the **structural feel** of games such as
*Fear & Hunger*: simple presentation, character selection, exploration, persistent
state, consequential choices, randomized encounters, inventory/status changes and
high information density.

We do **not** copy its characters, art, maps, dialogue, monsters, lore, names,
encounters or protected content. The reference is mechanical only.

The cognitive measurements remain underneath the game loop.

```text
PLAY
 -> experience an event
 -> continue exploring
 -> experience unrelated events
 -> hidden scheduler matures a prior event
 -> natural gameplay question / explicit probe
 -> response + latency + cue level recorded
 -> event retired from independent retention scoring
 -> continue
```

## Why "sweeps"

A sweep is one controlled increase in game complexity **and** one controlled
increase in what we attempt to measure.

Do not add five cognitive constructs at once. Each sweep must preserve the prior
measurement contracts so we know which new mechanic changed the data.

```text
Sweep 0  prove game loop
Sweep 1  episodic retention
Sweep 2  temporal/sequence memory
Sweep 3  associative/context memory
Sweep 4  working memory + interference
Sweep 5  attention / response inhibition / processing speed
Sweep 6  executive switching / route planning
Sweep 7  adaptive mixed-domain campaign
Sweep 8  longitudinal alternate-form research
```

## Sweep 0 - Survival shell

Goal: make it playable before making it smart.

- 4 simple character archetypes.
- 8-12 rooms/nodes.
- move / inspect / use / take / leave / choose.
- basic health/status/inventory.
- deterministic seed for reproducibility.
- event ledger records every meaningful encounter.
- intentionally low-fi UI: text, cards, icons, crude/pixel illustrations.
- no memory score visible during play.

Acceptance: a player can complete a 10-minute run and the event ledger exactly
reconstructs what happened.

## Sweep 1 - Episodic retention

Primary question:

**Can the player retrieve an experienced event after increasing elapsed time?**

Game examples:
- What did you hear outside?
- Which object did the injured traveler hand you?
- Which door did you choose?
- Who warned you about the lower passage?

Probe ladder:
1. free recall;
2. contextual/categorical cue;
3. recognition choices.

Candidate delays:
30 s -> 1 min -> 2 min -> 4 min -> 8 min -> later expansion.

Each independent scored event is retired after probing.

Output:
- delay x free-recall outcome;
- cue level required;
- recognition rescue;
- response latency;
- retention bracket/curve with raw observation count.

This is the core Memory Horizon POC.

## Sweep 2 - Temporal and sequence memory

Research inspiration: NIH Toolbox Picture Sequence Memory Test measures episodic
memory by asking participants to reconstruct the order of pictured activities.

Game implementation:
- player experiences a short sequence: bell -> corridor -> merchant -> locked door;
- later game state asks which came first / reconstruct the sequence;
- route chronology can matter to solving a later problem.

Measurements:
- item recall;
- order accuracy;
- temporal adjacency errors;
- delay from experience to reconstruction.

Do not simply reproduce NIH Toolbox test items or scoring.

## Sweep 3 - Associative/context memory

Research inspiration: TestMyBrain verbal/visual paired-associate tasks learn
word/picture pairs and test them after an intervening delay.

Game implementation:
- person <-> object;
- room <-> symbol;
- character <-> warning;
- faction <-> color/token;
- sound <-> threat.

Example:
"You saw this symbol earlier. Which room was it attached to?"

Measurements:
- free association;
- forced-choice association;
- interference errors;
- delay sensitivity.

## Sweep 4 - Working memory and interference

Research inspiration:
- TestMyBrain N-back: attention + working memory.
- NIH List Sorting: recall/resequence current stimuli.

Game implementation should remain contextual:
- remember the last two rune states while moving;
- carry a short verbal instruction through one or two intervening actions;
- update a small active set when one item changes;
- distinguish **working-memory load** from delayed episodic retention.

Important: these data must be labeled separately from the episodic-retention
curve. We do not let a working-memory failure become an episodic-memory failure.

## Sweep 5 - Attention, inhibition and processing speed

Research inspiration:
- TestMyBrain Simple Reaction Time;
- Choice Reaction Time;
- Gradual Onset Continuous Performance Test;
- Digit Symbol Matching.

Game implementation:
- occasional rapidly appearing threat/door/signal requiring response;
- go/no-go moments;
- discriminate relevant from distractor signals;
- simple symbol/key matching as an in-world mechanic.

Measurements:
- reaction time;
- missed target;
- false alarm;
- response inhibition;
- processing-speed proxy.

This sweep must be device-aware because hardware/browser latency can influence
timing. Do not blend these metrics into the Memory Horizon retention score.

## Sweep 6 - Executive switching / route planning

Research inspiration: TestMyBrain Trail Making B measures processing speed and
task switching/cognitive flexibility.

Game implementation:
- alternate between two rule sets;
- route by number/symbol or person/location;
- switch rules after an event;
- remember that the rule changed rather than merely execute one repeated rule.

Measurements:
- switch cost;
- rule perseveration;
- route errors;
- completion time.

## Sweep 7 - Adaptive mixed-domain campaign

Only after individual constructs are stable.

The game director selects encounters based on evidence quality and player state,
not merely difficulty.

Examples:
- episodic delay is under-sampled -> schedule a new event that can mature;
- working-memory load has enough samples -> stop sampling it;
- reaction-time device data are unstable -> suppress speed claims;
- repeated form exposure too high -> select unused event family.

The director must preserve **measurement independence**:
an exciting game should not contaminate the construct it is attempting to sample.

## Sweep 8 - Longitudinal alternate forms

Research inspiration:
- TestMyBrain supports alternate/ultra-brief forms and high-frequency,
  longitudinal/measurement-burst studies.
- NIH Picture Sequence Memory Test provides multiple forms for repeated-measures
  designs to reduce practice effects.

Our equivalent is procedural content families:
- names;
- objects;
- sounds;
- room motifs;
- route structures;
- symbol systems;
- associative pairs;
- narrative events.

Every event carries `form_id` / `family_id` so repeated sessions can avoid
reusing material and quantify exposure.

## Probe presentation styles

Do not make every test look like a test.

### Explicit card
Useful for early POC validation:
"What did you hear at the entrance?"

### Character dialogue
"The guard asks what was following you outside."

### Environmental action
Four levers correspond to four earlier symbols.

### Inventory consequence
Player must choose the item previously requested by a character.

### Route decision
A clue encountered earlier determines the safe route.

All of these map to the same probe schema. Presentation style is metadata, not a
different score.

## Difficulty versus measurement

Game difficulty and cognitive-test difficulty are separate axes.

A player can die because of:
- poor strategic choice;
- combat/resource failure;
- randomized danger.

Those failures must not automatically become memory failures.

Likewise, cognitive probes should not make survival impossible merely to increase
test yield. The engine records whether a wrong memory answer affected the game.

## Source-derived construct map

| Construct | Research reference | Memory Horizon implementation |
|---|---|---|
| episodic event retention | NIH PSMT; TMB paired associates | delayed game-event probes |
| sequence/temporal order | NIH PSMT | reconstruct encounter order |
| associative memory | TMB verbal/visual paired associates | person-object/place-symbol links |
| working memory | TMB N-back; NIH working-memory tasks | active rune/instruction state |
| sustained attention/inhibition | TMB GradCPT / Choice RT | in-world go/no-go signals |
| processing speed | TMB Digit Symbol / reaction-time tasks | timed symbol/action events |
| task switching | TMB Trail Making B | alternating game rules |
| delayed recall/concentration | SCAT6 clinical reference | research comparison only; do not copy/replace clinical tool |

## Technical architecture

Keep two engines separate:

```text
GAME ENGINE
  world
  encounters
  inventory/status
  narrative
  choices
       |
       v
EVENT BUS
       |
       +--> Measurement Engine
       |      event eligibility
       |      delay scheduler
       |      probe generation
       |      contamination/retirement
       |      scoring
       |
       +--> Session Ledger
              raw events
              responses
              timing
              form exposure
              device/browser context
```

jsPsych is a candidate for the measurement/timeline layer because it already
supports browser experiments, trial timelines, randomization, sampling, looping
and trial data capture. The game should not be forced into jsPsych if a thin
TypeScript engine plus jsPsych measurement adapter is cleaner.

## First build boundary

Do not build all sweeps in Phase 1.

Phase 1 = Sweep 0 + Sweep 1:
- low-fi survival shell;
- 12+ unique scorable events;
- explicit + natural probe presentations;
- adaptive delayed episodic recall;
- contamination controls;
- transparent data export.

Sweeps 2-8 stay behind evidence gates and are added only after the prior sweep
produces interpretable data.

## Product principle

The player should say:

**"I played a strange little dungeon game."**

The researcher should be able to say:

**"Here is exactly what the player experienced, when each memory was queried,
which cue level was needed, how long the response took, and which observations
support the retention curve."**
