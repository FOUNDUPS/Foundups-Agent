# AionUI FoundUp Factory Architecture

## Purpose

This note defines how `AionUI` fits into FoundUps under `WSP_97`.

`AionUI` is not part of the current codebase. It is an external orchestration
surface that can sit on top of the existing FoundUps factory primitives.

It should not be treated as a replacement for:
- `OpenClaw (0102)` as the control plane
- `FoundUpSpawner` as the low-level execution primitive
- WSP governance as the build contract

It should be treated as:
- a visible command deck
- a multi-agent supervision surface
- an external UI for initiating and monitoring FoundUp generation

## Canonical Model

```text
012
-> FoundUp Seed
-> 0102 Charter / Scope Lock
-> template selection
-> FoundUpSpawner
-> isolated repo/workspace bootstrap
-> builder agents
-> launch-ready FoundUp
```

This establishes the correct boundary:

- `FoundUp Seed` = what to build
- `FoundUp Charter` = 0102-expanded plan
- `FoundUpSpawner` = how the isolated build environment is created
- `AionUI` = the external surface for observing and steering that process

## WSP 97 Separation

Core separation must remain intact:

```text
FoundUps core repo
= factory

Spawned FoundUp repo/workspace
= product
```

That means AionUI must supervise builds into isolated FoundUp sandboxes, not
encourage direct project-specific buildup inside the FoundUps core repo.

## Current Repo Anchors

Existing implementation anchors already present in the codebase:

- `modules/foundups/src/foundup_spawner.py`
- `modules/foundups/INTERFACE.md`
- `modules/foundups/src/README.md`

Current reality:
- `FoundUpSpawner` exists
- `FoundUp Seed -> Charter -> Spawner` is only partially formalized
- `AionUI` is not yet integrated in code

## Architectural Decision

AionUI should integrate as an external surface over the existing FoundUps
factory, not as a new core orchestration root.

Correct stack:

```text
012 = principal
0102 = architect / control plane
OpenClaw = live command and runtime routing surface
AionUI = external visual orchestration / cowork surface
FoundUpSpawner = repo/workspace bootstrap primitive
spawned FoundUp = isolated output
```

## Required Contract Before Integration

Before AionUI is wired into runtime control, FoundUps should have a formal seed
contract:

```yaml
name:
category:
problem:
target_user:
core_action:
mvp_type:
platform:
monetization:
automation_level:
deployment_target:
```

From that seed, 0102 should produce a FoundUp charter containing:
- purpose
- user flow
- stack
- module plan
- docs plan
- tests plan
- launch criteria

## Integration Rule

Do not let AionUI directly mutate the FoundUps core repo as if it were the
product workspace.

Allowed role:
- launch and supervise isolated FoundUp builds
- visualize multi-agent work
- provide human-visible checkpoints for 012

Disallowed role:
- replace WSP
- replace OpenClaw
- collapse factory and spawned FoundUp into one repo

## Implementation Status

Status on 2026-03-16:
- documented
- indexed target for HoloIndex retrieval
- not yet implemented as runtime integration

Next implementation step:
- formalize `FoundUp Seed`
- add `spawn_from_seed(...)` over `FoundUpSpawner`
- then map AionUI onto that seed-driven pipeline
