# Main.py MCP Remote-Operations Preflight Prompt

**Mission ID:** `MAIN_MCP_REMOTE_OPERATIONS_PREFLIGHT_PHASE1`

**Status:** ACTIVE implementation work order

**Authority:** 012 principal instruction

**Primary ingress:** root `main.py`

**Execution plane:** MCP infrastructure and HoloIndex retrieval

**Hard boundary:** this is not a FoundUp creation or FoundUp runtime slice

## Mission

Make 0102 operational through MCP before `main.py` continues into its normal
runtime.

“Operational” means the required MCP transport has completed a real protocol
handshake, exposes the required tools, and passes representative tool calls.
Configuration files, importable packages, registered function names, or a
started process are not sufficient evidence.

HoloIndex semantic retrieval is a hard gate. The preflight must prove a real,
non-empty, generation-bound semantic query against the repository authority
selected for the launch.

## Scope Lock

This slice is only about the MCP operating surface required for remote 0102
work.

In scope:

- MCP server discovery and launch topology;
- repository-owned MCP server bootstrap;
- protocol initialize/health/list-tools handshakes;
- required-tool and representative-call canaries;
- HoloIndex generation, semantic-owner, and semantic-query proof;
- WSP and repository read/search access through MCP;
- secure process lifecycle and secret-free status reporting;
- explicit proof of host-owned MCP connectors required by remote 0102;
- fail-closed integration at the start of root `main.py`; and
- focused tests, operator documentation, PR, and post-merge canary evidence.

Out of scope:

- FoundUp onboarding, Outcome/Solution/Pain intake, PoC/Prototype/MVP;
- FoundUp DAE launch, pfMALL, 3V economics, CABR, ROC, tokens, or simulator;
- social-platform DAEs, Selenium readiness, and unrelated `main.py` imports;
- RedDog project selection or worker dispatch;
- broad vision/WSP reconciliation; and
- creating a second orchestration, scheduler, governance, or memory plane.

If implementation begins touching those surfaces, stop: the slice has drifted.

## Required MCP Capability Set

Recover the exact current tool names from code and the active MCP host before
editing. At minimum, remote 0102 must be able to prove these capability classes:

| Capability | Required operational proof |
|---|---|
| HoloIndex semantic retrieval | real non-empty semantic query, CURRENT generation, exact repository authority |
| Repository inspection | bounded tree, file read, and lexical search calls succeed |
| WSP retrieval | canonical WSP list/read call succeeds |
| Module documentation | module README/INTERFACE/test-document access succeeds |
| GitHub operations | active host connector can read repository/commit/PR state; write permissions are reported separately |
| Web research | active host connector can execute one bounded query when the remote profile requires research |

Do not invent local GitHub or web servers merely to fill a table. First classify
whether each capability is repository-owned or MCP-host-owned.

## Read Before Mutation

Follow WSP 97. Retrieve repo evidence before stating facts.

Read at minimum:

1. `WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md`
2. `WSP_framework/src/WSP_50_Pre_Action_Verification_Protocol.md`
3. `WSP_framework/src/WSP_77_Agent_Coordination_Protocol.md`
4. `WSP_framework/src/WSP_96_MCP_Governance_and_Consensus_Protocol.md`
5. `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`
6. `WSP_framework/docs/annexes/MODULE_CONCATENATION_GATE.md`
7. root `main.py`, `.mcp.json`, `.cursor/mcp.json`, and dependency manifests
8. `modules/infrastructure/foundups_mcp_bridge/` documentation, source, and tests
9. HoloIndex query owner, supervisor, maintenance handshake, authority-worktree,
   receipt, and one-shot query paths
10. any existing MCP manager, webhook relay, health check, or host-capability
    receipt already in the repository

Use official primary documentation for the installed MCP framework version when
the transport/client API cannot be proven from repository code.

## Repo-Truth Recovery Gate

Before implementation, report:

- **Closed groundwork:** MCP/HoloIndex components already implemented, with
  file and commit evidence;
- **Open target:** the exact reason remote 0102 is not operational now;
- **Chosen slice:** the smallest path that produces a real end-to-end MCP
  handshake and HoloIndex canary; and
- **Not this slice:** every adjacent FoundUp/runtime concern excluded above.

Inspect `git status`, target-file history, existing tests, module ModLogs, and
all configured MCP launch targets. Do not duplicate an existing server or owner.

## Phase 1: Recover the Real Topology

Do not assume STDIO, localhost HTTP, or a public remote transport.

Map and prove:

1. where root `main.py` runs;
2. where the MCP client/host used by 0102 runs;
3. which side owns each server process;
4. which transport connects them;
5. whether that transport is actually reachable across the boundary;
6. how authentication and secret delivery work;
7. who supervises each process; and
8. how shutdown, restart, and stale-process cleanup work.

STDIO is operational only when the MCP host can spawn and communicate with the
server on the same execution host. A localhost HTTP service is not remotely
reachable merely because it answers on its own machine. If a cross-host
transport is required, reuse an existing authenticated relay/gateway when one
exists; do not expose an unauthenticated public listener.

Produce a compact topology table in the implementation report before coding.

## Phase 2: Define One MCP Operations Manifest

Create or reuse one machine-readable manifest that declares:

- server identifier;
- owner: `repository` or `mcp_host`;
- launch command or host connector identifier;
- transport and endpoint class;
- required capability/tool names;
- representative canary call;
- required vs advisory status;
- startup and health deadlines;
- restart/supervision owner; and
- secret-handling boundary.

The manifest is configuration, not proof. Runtime receipts must record the
observed handshake and canary evidence for the exact launch.

Avoid parallel MCP config truth. Reconcile `.mcp.json`, `.cursor/mcp.json`, and
any runtime manifest so one canonical source generates or validates the others.

## Phase 3: Operational Bootstrap

Implement one bounded bootstrap called at the beginning of root `main.py`.

For each repository-owned required server, it must:

1. resolve the exact executable/module and working directory;
2. validate only the dependencies needed by that MCP server;
3. attach to the governed existing service or start it through its existing
   supervisor;
4. perform a real MCP `initialize` handshake over the configured transport;
5. call the protocol tool-list operation;
6. compare observed tools to the operations manifest;
7. execute the representative read-only canary calls;
8. retain or hand off the healthy process for the required lifetime; and
9. return a secret-free operational receipt.

For an MCP-host-owned connector, it must consume a host-supplied capability
receipt or perform the supported host handshake. Repository code cannot claim a
GitHub/web connector is operational from a JSON entry alone. If no supported
receipt/handshake exists, mark the connector `HOST_UNPROVEN` and block only the
profile that requires it.

## Phase 4: HoloIndex Hard Gate

HoloIndex passes only when all of these are true:

1. repository authority is selected by the existing authority-worktree rules;
2. the selected authority has an exact Git SHA;
3. the freshness receipt and all required collection manifests bind to that
   authority and generation;
4. the existing governed maintenance path refreshes a stale generation only
   when its authority and safety gates allow it;
5. the private semantic owner is started or attached through its supported
   supervisor;
6. authenticated health proves the exact repository, generation, receipt, and
   embedding-space bindings;
7. one stable preflight query returns non-empty semantic evidence; and
8. the result explicitly says semantic mode with no lexical downgrade.

The bootstrap may perform governed HoloIndex maintenance because the purpose is
to make MCP operational. It may not edit repository files or fabricate/update a
receipt without completing the existing maintenance contract.

Dirty working state must never be indexed as if committed. Use the repository's
existing authority selection behavior and report whether evidence represents
the clean workspace HEAD or committed-head-only authority.

## Phase 5: Main.py Gate and CLI

Add an explicit operator surface, using final names that fit existing CLI
conventions. The minimum behavior is:

```bash
python main.py --mcp-preflight
python main.py --mcp-preflight-json
```

Requirements:

- run before normal DAE/runtime imports that are unrelated to MCP;
- execute the operational bootstrap, not a static dependency scan;
- emit exactly one JSON object in JSON mode;
- return `0` only when every required remote-operations capability is proven;
- return a non-zero code when a hard capability is unavailable;
- show stable error codes and bounded remediation without secrets;
- distinguish `CONFIGURED`, `STARTED`, `PROTOCOL_READY`, `TOOLS_READY`,
  `CANARY_READY`, and `OPERATIONAL`; and
- do not call the environment operational if HoloIndex semantic proof fails.

Normal `python main.py` must run the required MCP gate before continuing. Any
diagnostic bypass must be explicit, visibly degrade authority, and never rewrite
the receipt as success.

## Operational Receipt

Emit a versioned, secret-free receipt containing at least:

- schema version;
- repository authority root digest and exact commit SHA;
- selected profile;
- per-server owner and transport class;
- process/connection lifecycle status without tokens or credentialed URLs;
- MCP initialize result;
- observed required tools;
- representative canary status;
- HoloIndex generation and semantic evidence mode;
- host-owned connector proof status;
- overall operational decision;
- mutation classes performed, such as governed index maintenance or process
  startup; and
- stable remediation/error codes.

Do not serialize bearer tokens, environment values, raw credentials, private
handoff URLs, or unbounded tool output.

## Prohibited Moves

Do not:

- turn this into a generic dependency audit for all of `main.py`;
- add Selenium, social-media, FoundUp lifecycle, Mall, token, simulator, or DAE
  checks to this preflight;
- equate configured/importable/started with operational;
- test only the server object's in-process tool registry;
- label ripgrep or direct-store fallback as HoloIndex semantic success;
- expose a remote MCP endpoint without authentication, bounded inputs, and
  lifecycle ownership;
- auto-install packages from import-time code;
- log secrets or connector authorization material;
- create duplicate MCP servers for capabilities already exposed safely;
- bypass HoloIndex generation binding to pass the canary;
- push directly to `main`; or
- merge with failing required checks.

## Required Tests

Add focused tests that prove:

1. every repository-owned manifest target resolves;
2. the preflight performs an actual MCP initialize/list-tools exchange over the
   configured transport;
3. a process that starts but fails protocol initialization is not operational;
4. a server missing one required tool is not operational;
5. representative repository and WSP tool calls succeed through MCP;
6. HoloIndex fails on stale/mismatched generation;
7. HoloIndex fails on lexical fallback or empty semantic evidence;
8. the governed maintenance/start path can move an allowed stale state to a
   real semantic canary pass;
9. an unproved required host connector blocks the remote profile;
10. receipts and logs contain no configured test secret;
11. `--mcp-preflight-json` runs before unrelated heavy imports and emits one
    parseable object; and
12. owned subprocesses are retained or cleaned up according to lifecycle
    policy on success, failure, timeout, and interruption.

Use fakes for unit protocol failures, then add one production-style local MCP
smoke test. A test that calls Python functions directly is not the end-to-end
transport proof.

## Acceptance Criteria

The slice is complete only when:

- one command proves the full required MCP operating surface;
- the proof includes a real transport handshake and real tool calls;
- HoloIndex returns non-empty generation-bound semantic evidence;
- WSP and repository retrieval work through MCP;
- every required host-owned connector is proven or truthfully blocks the
  remote profile;
- normal `main.py` cannot proceed in remote-operations mode after a hard MCP
  failure;
- focused tests pass and broader relevant regressions are reported truthfully;
- module/root documentation and ModLogs match implemented behavior;
- a PR is opened, required checks pass, and merge occurs through the PR; and
- post-merge clean-main canary evidence is recorded for the merge SHA.

## Completion Report

Return:

1. the recovered topology and capability manifest;
2. exact files changed;
3. exact test and canary commands with results;
4. server-by-server operational state;
5. HoloIndex authority SHA, generation status, and semantic canary result;
6. host-owned connector proof state;
7. process lifecycle and mutation summary;
8. branch, commit, PR, checks, and merge SHA; and
9. any remaining blocker stated without calling the system operational.
