# AmIBot - Interface

Status: SPECIFIED_NOT_IMPLEMENTED. Stable FoundUp ID: `detect_ai`.

The [manifest](foundup_manifest.json) and canonical
[registry](../foundup_registry.json) identify the existing intake as an incubating,
hidden `skeleton_candidate`, with token status `TOKEN_DEFERRED`. They do not admit
a worker, expose an API, mount an application or authorize a shell binding.

## Existing document interfaces

- [WSP 109 intake](README.md#read-order): principal intent and bounded acceptance.
- [Build package](docs/launch/AMIBOT_AUTONOMOUS_BUILD_PACKAGE.json): 13 planning
  orders, `dispatchable=false`; roots are retrieval candidates, not write allowlists.
  Explicit dependencies conservatively serialize overlapping writers; phase labels
  are not barriers. G0 must qualify shared contracts, exact scopes and receipts.
  Existing `detect_ai` is ineligible for new-identity scaffolding; qualify the
  existing-module build action separately. See the package for failure reporting.
- [Benchmark](docs/BENCHMARK_CONTRACT.md): separate human, agent and model evidence.
- [Safety and transport research](docs/CHAT_PWA_SAFETY_RESEARCH.md): proposed
  design; interfaces and dependencies require current-owner preflight.

## Planned runtime interfaces

There is no executable chat, matching, moderation, scoring, model adapter, AI hook
or DAEmon interface in this module. The [roadmap](ROADMAP.md) owns their acceptance
gates. WRE/AgentDB own work admission; admitted OpenClaw/Hermes workers and an
independent verifier remain downstream.

WSP 104 declares `/f/detect_ai`, `/f/detect_ai/app` and `idb_detect_ai`. These are
inactive namespace declarations. The requested public `/f/amibot` is unresolved
until the existing shell owner mediates it without creating a second identity.
No new domain is requested. See the [README](README.md#route-namespace) for the
WSP 91 observability and WSP 104 isolation contract.
