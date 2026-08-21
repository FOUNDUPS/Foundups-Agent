# RedDog Upstream Worker Live Proof

**Date:** 2026-08-21 (JST)
**Scope:** Read-only GotJunk audit canaries; no repository artifact was written
**Authority:** 012 requested verification of actual current Hermes/OpenClaw scaffolding
**WSP:** WSP_00, WSP_15, WSP_50, WSP_97

## Runtime identity

- Hermes Agent: API runtime `0.20.4`, official release tag `v2026.8.18`.
- OpenClaw: CLI and loopback Gateway `2026.7.1-2`; service audit clean and
  plugin-version drift empty.
- Hermes `reddogartifact`: only `delegation` enabled, exposing only
  `delegate_task`; skills empty; maximum concurrent children and spawn depth
  both one.
- OpenClaw `reddog-artifact`: sandbox mode `all`, workspace access `none`, one
  read-only sandbox mount, tools allow `[]`, tools deny `["*"]`, elevation off.

## Hermes live canary

The current RedDog lifecycle submitted a real authenticated `/v1/runs` request
using the configured OpenRouter Qwen route and bounded GotJunk manifest context.
The accepted run produced one matching child start/complete identity, child
status `completed`, zero child file reads/writes, only paired `delegate_task`
telemetry, one terminal completion, and one in-memory artifact. Content is
intentionally omitted. RedDog returned `MODEL_OK` and recorded Hermes dispatch.

Two prior diagnostic attempts were useful negative evidence: one completed
child exposed layered upstream tool telemetry and was rejected by the initial
overly strict oracle; another child ended `interrupted` and was rejected by the
corrected fail-closed oracle. No failed canary artifact was accepted.

## OpenClaw live canary

The current RedDog CLI adapter completed its four-command preflight and one real
Gateway agent turn against bounded GotJunk context. The accepted run produced
one in-memory artifact at `audit/gotjunk_openclaw_canary.md`, result `MODEL_OK`,
and five observed worker processes. The temporary message file was removed and
no repository artifact was materialized.

The proof found and repaired four prerequisites without reducing policy:

1. canonical `qwen/qwen3-coder` must be derived with its signed provider as
   `openrouter/qwen/qwen3-coder` for OpenClaw;
2. the dedicated agent required its own OpenRouter auth profile and model;
3. Docker Desktop was installed but not running or visible to the service PATH;
4. the npm install omits the sandbox setup script, so the official documented
   minimal `openclaw-sandbox:bookworm-slim` image was built verbatim.

Sandboxing was never disabled. Earlier calls failed closed on unknown model,
missing Docker, missing sandbox image, or empty artifact output.

## Evidence boundary

These are actual upstream runtime/model canaries, not fixture simulations. They
prove both installed scaffolds can perform bounded FoundUp audit work under
their confinement policies. They are not signed production work orders: the
diagnostic invoked the provider lifecycle beneath model-capability admission.
Production still requires the existing signed selection/runtime binding,
AgentDB/WRE authority, isolated materializer, exact-SHA commit stage, and
independent verifier before repository effects.
