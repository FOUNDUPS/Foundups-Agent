# RedDog Hermes Native Delegation Assumption Audit

**Date:** 2026-08-21 (JST)
**Owner:** 0102
**Authority:** 012 explicitly directed RedDog to use the actual, current Hermes and OpenClaw scaffolding and to verify the claim online.
**WSP basis:** WSP_00, WSP_15, WSP_50, WSP_97

## Problem

The current `hermes_api` provider submits a real upstream Hermes API run, but its
confinement contract disables every Hermes toolset and rejects every subagent
event. That proves upstream text generation; it does not prove use of Hermes'
native delegation scaffold. The older `HermesJobExecutor` names and prepares a
delegation boundary, but its accepted repository proofs are dry-run/fixture
paths rather than a current upstream child-agent execution.

## Assumptions

1. The official Hermes API server remains the runtime authority for constructing
   its parent `AIAgent`, child agent, provider, terminal, and event stream.
2. Hermes Agent v0.20.4 (release tag `v2026.8.18`) exposes the documented
   `delegation` toolset and the `delegate_task` tool through the API-server
   platform policy.
3. A parent with exactly the `delegation` toolset can create one isolated leaf
   child; Hermes removes delegation from the leaf, preventing recursive fanout.
4. RedDog can retain sole artifact-write authority by accepting only returned
   artifact content and by giving Hermes no filesystem, shell, web, MCP, or
   approval-capable toolset.
5. The existing resident-runtime API-key file boundary is the intended
   credential handoff. Secret values must never enter the repository, logs,
   receipts, command output, or test fixtures.
6. OpenClaw remains a distinct confined execution provider. Native Hermes
   delegation must not be represented as an OpenClaw execution or vice versa.
7. The dedicated OpenClaw `reddog-artifact` agent needs its own provider auth
   profile and model allowlist. A model name accepted by Hermes is not evidence
   that OpenClaw can route the same signed model.

## Failure Modes

- A profile enables any toolset besides `delegation`, or exposes any tool other
  than `delegate_task`.
- A run performs zero child spawns, multiple child spawns, a nested child,
  approval waits, another tool, or any child file write.
- A run reports completion but its full SSE history does not prove one stable
  leaf identity from `subagent.start` through `subagent.complete`, followed by
  `run.completed`, with only `delegate_task` tool-progress telemetry.
- Hermes/OpenClaw version output drifts from the release-pinned preflight.
- A credential is copied with permissive filesystem access or printed during
  provisioning.
- A canonical signed model such as `qwen/qwen3-coder` is passed directly to
  OpenClaw without its required provider prefix, or is absent from the
  dedicated agent's configured model set.
- A diagnostic canary is mistaken for a signed production work-order run.
- Documentation continues to describe the Hermes route as text-only after the
  contract changes.

## Alternatives Considered

1. **Keep all Hermes tools disabled.** Rejected: truthful upstream inference,
   but it does not satisfy the requested native Hermes delegation behavior.
2. **Call/import `delegate_task` directly from RedDog.** Rejected: bypasses the
   official API-server construction and lifecycle and couples RedDog to Hermes
   internals.
3. **Revive `HermesJobExecutor` as the production route.** Rejected for this
   layer: the existing executor is valuable legacy policy scaffolding, but its
   proven execution path is not the current upstream API lifecycle.
4. **Enable broad Hermes tools.** Rejected: unnecessary capability and an
   unacceptable write/network/approval surface.
5. **Use one native leaf delegate through the official API server.** Selected:
   it is the smallest layer that proves real Hermes scaffolding while preserving
   RedDog's artifact authority.

## Decision

**PROCEED**, subject to fail-closed implementation and validation.

The dedicated `reddogartifact` Hermes profile will expose exactly the upstream
`delegation` toolset and `delegate_task`; skills remain empty. RedDog will require
one completed leaf child lifecycle, reject all other effects, and record
native-delegation proof in its result digest. Credential provisioning will copy
only the API-server key into the resident runtime with owner-only permissions
and will disclose metadata only. A live FoundUp audit canary will be reported as
an upstream-runtime proof, not as a signed production mutation.

The same already-authorized OpenRouter credential may be installed through the
official OpenClaw auth CLI into the `reddog-artifact` agent's private auth store;
stdin is the only transfer surface and no value may be logged. That agent will
configure `openrouter/qwen/qwen3-coder` explicitly. RedDog will derive this
OpenClaw runtime ID only from the signed `(provider, canonical_model_id)` pair;
it will not trust an unsigned string or silently fall back to another model.

## Evidence Correction

The first live v0.20.4 canary disproved the initial assumption that one child
produces exactly one `tool.started`/`tool.completed` pair. The upstream API
emits layered `delegate_task` progress pairs—including an internal error-marked
layer—around one stable child lifecycle. The same run emitted one matching
`subagent.start`/`subagent.complete` identity, `status=completed`, and zero
files written. The acceptance oracle therefore keys uniqueness to the stable
child identity and treats paired, delegate-only tool events as telemetry. It
still rejects a second child, another tool name, incomplete pairing, a failed
child, any child read/write effect, or a non-completed terminal event.
