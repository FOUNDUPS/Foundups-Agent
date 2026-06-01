# HERMES_NOUS_AGENT_DELEGATE_BINDING_AUDIT_PHASE1

**Slice:** HERMES_NOUS_AGENT_DELEGATE_BINDING_AUDIT_PHASE1
**Worker-Lane:** W6
**Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** READ-ONLY audit. No live delegation, no runtime launch, no code/config/env/vendor change.

---

## 1. Mission and Scope

Clarify and verify the intended Hermes execution path: FoundUps `HermesJobExecutor` is meant
to bind WRE `FoundUpJob` execution to the vendored Nous Hermes Agent `delegate_task`, not
remain only a local dry-run naming layer. This audit verifies the **current adapter boundary**
and defines the **smallest safe future binding** before any Phase-2 live delegation.

Central question: is the vendored `delegate_task` interface still compatible with FoundUps
`HermesDelegationRequest`, and what exact gates are required before Phase-2 live delegation?

Scope: exactly one file (this audit). All evidence gathered by reading source + `find_spec`
(structural only). **No** live `delegate_task` call, Hermes/Ollama runtime launch, WSL install,
dependency install, or vendor mutation.

---

## 2. Predecessor Citations

| Ref | Relationship |
|-----|--------------|
| HXA14 | Controlled live-Hermes harness (`test_hxa14_controlled_live_hermes_harness.py`) |
| HXA16 | Real delegate adapter boundary proof (`_execute_real_delegate_adapter`, semantics §5) |
| HXA23 | Destructive-action guard integration (gate before any execution) |
| HXA26–HXA30 | Capability token validation sequence (server-authored tokens gate) |
| PR #740 | WSP 109 genesis gate remediation (W10 handoff pattern reused for READY/NOT_READY) |
| PR #744 | HXA26/HXA27 redundancy audit (**MERGED** 2026-06-01) — token primitives already in main |
| `EXTERNAL_SWARM_OPENCLAW_HERMES_CURRENT_STATE_RECONCILIATION_PHASE1.md` | Records real delegate invocation as **BLOCKED**, HXA16 required (L227) |

Base: `origin/main` @ `1cfced349` (after #744).

---

## 3. Current-State Truth Statement

`HermesJobExecutor` is a **dry-run adapter / naming layer**, not a live delegation path:
- `HERMES_DELEGATE_ENABLED=0` (default) → simulation only, no `delegate_task` call (`hermes_job_executor.py` L15, L93).
- `HERMES_DELEGATE_ENABLED=1` → still **`BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED`** (L299, L16).
- HXA16 `_execute_real_delegate_adapter` (L701-769) *proves the boundary* and documents interface requirements but explicitly **does NOT call live `delegate_task` and does NOT instantiate the Hermes runtime** (L712-713).
- The reconciliation doc (L227) and the workspace fork plan (L339) both record "Real delegate_task calls — Hermes delegation remains blocked."

This audit confirms the binding is **not** live and **cannot** currently go live as wired (see §7, §9).

---

## 4. Vendored Hermes Agent Inventory

| Item | Finding |
|------|---------|
| `vendor/hermes-agent/tools/delegate_tool.py` | EXISTS (1103 lines); defines `delegate_task` (L623) |
| `vendor/hermes-agent/tools/__init__.py` | EXISTS |
| `vendor/hermes-agent/__init__.py` | **MISSING** |
| `vendor/__init__.py` | **MISSING** |
| `vendor/hermes_agent` (underscore dir) | **DOES NOT EXIST** (dir is `hermes-agent`, hyphen) |
| `hermes_agent` pip-installed | **NO** (`importlib.util.find_spec('hermes_agent')` → False) |
| Naming note | Fork plan (`FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md` L14-19) describes the *hermes-workspace* repo as "NOT vendored"; the vendored item here is the *hermes-agent* code — distinct artifacts; the agent is vendored, the workspace is external. |

---

## 5. `delegate_task` Signature and Runtime Requirements

```python
# vendor/hermes-agent/tools/delegate_tool.py:623
def delegate_task(
    goal: Optional[str] = None,
    context: Optional[str] = None,
    toolsets: Optional[List[str]] = None,
    tasks: Optional[List[Dict[str, Any]]] = None,
    max_iterations: Optional[int] = None,
    acp_command: Optional[str] = None,
    acp_args: Optional[List[str]] = None,
    parent_agent=None,
) -> str:
```

Required runtime objects (mandatory or behaviour-defining):
- **`parent_agent` is REQUIRED** — `if parent_agent is None: return tool_error("delegate_task requires a parent agent context.")` (L642-643). It must expose `_delegate_depth`, `_credential_pool`, workspace hints.
- It **spawns live child agents** (`_build_child_agent`, `_run_single_child`) and resolves provider credentials via `_resolve_delegation_credentials(cfg, parent_agent)` (L666) from `config.yaml` (`_load_config`).
- The executor's own HXA16 interface doc (L742-749) enumerates: `parent_agent` ("AIAgent instance with full agent context"), `toolsets`, `model_config`, `credentials` (API keys), `terminal_sessions`, `child_agent_spawning`.
- **No `dry_run` parameter exists on `delegate_task`** — once called, it executes live; dry-run is enforced *only* by not calling it.

---

## 6. FoundUps `HermesDelegationRequest` Mapping Matrix

`HermesDelegationRequest` (`hermes_job_executor.py` L319-380):

| `HermesDelegationRequest` field | `delegate_task` param | Mapping |
|---------------------------------|-----------------------|---------|
| `goal: str` | `goal` | **COMPATIBLE** |
| `context: str` | `context` | **COMPATIBLE** |
| `toolsets: List[str]` | `toolsets` | **COMPATIBLE** (default empty for dry_run) |
| `max_iterations: int=50` | `max_iterations` | **COMPATIBLE** |
| *(none)* | `parent_agent` (**required**) | **MISSING** — no field provides the live parent agent |
| *(none)* | `tasks` / `acp_command` / `acp_args` | unused (single-goal mode); not blocking |
| `dry_run: bool=True` | *(no param)* | **DRIFT** — no `dry_run` on `delegate_task`; not enforceable server-side |
| `policy_snapshot`, `job_id`, `foundup_id`, `tenant_id`, `workspace_binding` | *(no param)* | adapter-side metadata; **not passed** to `delegate_task` |

**Core params map cleanly (INTERFACE_COMPATIBLE).** The blocking gaps are the missing
`parent_agent` runtime and the absence of a `dry_run`/policy channel into `delegate_task`.

---

## 7. Import / Path Compatibility Assessment

**Result: IMPORT_PATH_DRIFT (verified, no execution).**
- The lazy import is `from vendor.hermes_agent.tools.delegate_tool import delegate_task`
  (`hermes_job_executor.py` L623) — uses **`vendor.hermes_agent`** (underscore).
- The filesystem path is **`vendor/hermes-agent/`** (hyphen). A hyphen is not a valid Python
  identifier, so `hermes-agent` can never import as `hermes_agent`.
- `vendor/__init__.py` and `vendor/hermes-agent/__init__.py` are **missing**.
- `importlib.util.find_spec('vendor.hermes_agent.tools.delegate_tool')` **fails to resolve**;
  `find_spec('hermes_agent')` → None.
- Inconsistency within the file: the import uses underscore (L623) while the HXA16 evidence
  path uses the hyphen `Path("vendor/hermes-agent/tools/delegate_tool.py")` (L739).

→ Even with `HERMES_DELEGATE_ENABLED=1`, `_lazy_import_delegate_task` (L610) would hit
`ImportError` and return False (L631). The import is non-functional as written.

---

## 8. Safety Gate Readiness Matrix

| Gate | Present today? | For Phase-2 live delegation |
|------|----------------|------------------------------|
| Feature flag `HERMES_DELEGATE_ENABLED` | YES (default 0) | Necessary, **not sufficient** |
| `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` | YES (L299) | Intended guard — **retain** until impl slice |
| Capability token validation (HXA26-30) | YES in main (#744) | Must be **server-authored** tokens, not local |
| Destructive-action guard (HXA23) | YES (pre-execution) | Must pass; D4/D5/D6 remain blocked |
| WSP 97 truth fields false unless real call + evidence | YES (`real_execution_performed` etc. never True in adapter) | Must remain false until a real `delegate_task` returns evidence |
| Workspace binding / path constraints | Partial (`WorkspaceBinding`, `vendor/`,`.hermes/` allow-roots) | Must be **server-built**, not client-asserted |
| `dry_run` enforced inside `delegate_task` | **NO** (no param) | **SAFETY_GATE_MISSING** — needs a server-side no-op/dry mode |
| W10 READY/NOT_READY handoff | Pattern exists (#740) | Required for the binding's readiness verdict |

---

## 9. Binding Readiness Classification

**Primary: `RUNTIME_DEPENDENCY_MISSING`** — `delegate_task` requires a live `parent_agent`
(AIAgent + credential pool + provider config + child-spawning), which the WRE FoundUpJob path
does not and should not construct in a dry-run adapter.

Contributing classifications:
- **`IMPORT_PATH_DRIFT`** — `vendor.hermes_agent` import cannot resolve against `vendor/hermes-agent` (§7). Concrete, fixable defect.
- **`INTERFACE_DRIFT`** — `HermesDelegationRequest` has no `parent_agent`; `delegate_task` has no `dry_run`/policy channel (§6).
- **`SAFETY_GATE_MISSING`** — no `dry_run` inside `delegate_task`; live once called (§8).
- **`BLOCKED_BY_POLICY`** — `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` is the correct current guard.

The **core parameter interface is `INTERFACE_COMPATIBLE`** (goal/context/toolsets/max_iterations).
Overall the binding is **NOT `READY_FOR_CONTROLLED_PHASE2_TEST`**.

---

## 10. Required Phase-2 Gates (before any live delegation)

1. `HERMES_DELEGATE_ENABLED=1` is **necessary but not sufficient**.
2. Resolve **IMPORT_PATH_DRIFT** first (coherent importable package or `spec_from_file_location` against the hyphen path).
3. Provide a **`parent_agent`** runtime safely (RUNTIME_DEPENDENCY_MISSING) — or a server-side delegation endpoint — without exposing real credentials client-side.
4. **Capability tokens must be server-authored** (not locally minted); validation via HXA26-30.
5. **Destructive-action guard must pass**; **D4/D5/D6 remain blocked**.
6. **Workspace binding / path constraints server-built**, not client-asserted.
7. A server-side **`dry_run`/no-op mode** for `delegate_task` (close SAFETY_GATE_MISSING) before any real spawn.
8. **No** `.env`, secret, wallet, token, DNS, payout, DAO, or public-route mutation.
9. **All WSP 97 truth fields remain false** unless a real `delegate_task` call occurs *and* evidence exists.
10. A **W10 READY/NOT_READY handoff** must gate the readiness state.

---

## 11. Explicit Out-of-Scope Items

- Any code/config/env/vendor change (this is read-only).
- Live `delegate_task` invocation, Hermes/Ollama runtime launch, WSL install, dependency install.
- Fixing the import drift (deferred to the next slice).
- Constructing or installing the Hermes Agent runtime.
- Worktree removal / branch deletion / secret values in the audit.

---

## 12. Recommended Next Slice

**`HERMES_AGENT_RUNTIME_INSTALL_AND_PATH_AUDIT_PHASE1`** — the smallest safe next step:
audit/resolve the **import-path coherence** (`vendor.hermes_agent` ↔ `vendor/hermes-agent`)
and determine **whether the vendored code is sufficient or a runtime install (parent agent +
provider config) is required**, *without* a live delegate call. The
`BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` guard and `HERMES_DELEGATE_ENABLED=0` default
**must remain** until that audit and the §10 gates are satisfied. A controlled dry-run
(`HERMES_NOUS_AGENT_CONTROLLED_DELEGATE_DRYRUN_PHASE2`) is premature until the import path and
runtime dependency are resolved.

---

## 13. Internal Review Verdict

**READY.** The `delegate_task` callable, signature, and runtime requirements are verified by
direct read; the import path drift is verified structurally via `find_spec` (no execution);
the `HermesDelegationRequest` ↔ `delegate_task` mapping is complete; and binding readiness is
classified `RUNTIME_DEPENDENCY_MISSING` (with IMPORT_PATH_DRIFT, INTERFACE_DRIFT,
SAFETY_GATE_MISSING, BLOCKED_BY_POLICY contributing). The current
`BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` path should remain until a separate implementation
slice. No live delegation, runtime launch, or mutation occurred.

---

## 14. WSP_97 Truth Boundary Checklist

Declared count: **26 / 26 YES** (rows below = 26).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_AUDIT_ONLY | YES | Only this audit doc written |
| 2 | NO_LIVE_DELEGATE_CALL | YES | No `delegate_task` invoked; `find_spec` only |
| 3 | NO_HERMES_RUNTIME_LAUNCH | YES | No AIAgent instantiated |
| 4 | NO_OLLAMA_LAUNCH | YES | No model runtime started |
| 5 | NO_WSL_INSTALL | YES | No WSL action |
| 6 | NO_CODE_CHANGE | YES | No `.py` modified |
| 7 | NO_TEST_CHANGE | YES | No test files modified |
| 8 | NO_CONFIG_CHANGE | YES | No config.yaml/settings changed |
| 9 | NO_ENV_MUTATION | YES | No env var set; `.env` not read |
| 10 | NO_DEPENDENCY_INSTALL | YES | No pip/package install |
| 11 | NO_VENDOR_UPDATE | YES | `vendor/` read-only |
| 12 | NO_WORKTREE_REMOVE | YES | No worktree touched |
| 13 | NO_BRANCH_DELETE | YES | No branch deleted |
| 14 | NO_SECRET_VALUES_IN_AUDIT | YES | No keys/tokens/secrets quoted |
| 15 | NO_REGISTRY_MUTATION | YES | No registry written |
| 16 | NO_MANIFEST_MUTATION | YES | No manifest written |
| 17 | NO_PUBLIC_SURFACE_MUTATION | YES | No routes/INTERFACE changed |
| 18 | NO_DNS_CHANGE | YES | No DNS action |
| 19 | NO_TOKEN_ASSIGNMENT | YES | No token assigned/minted |
| 20 | NO_CABR_READY | YES | No CABR touched |
| 21 | NO_PAYOUT_READY | YES | No payout touched |
| 22 | NO_DAO_ACTIVATION | YES | No DAO activation |
| 23 | DELEGATE_TASK_PATH_VERIFIED | YES | `delegate_tool.py:623` signature read directly (§5) |
| 24 | IMPORT_DRIFT_VERIFIED_VIA_FINDSPEC | YES | §7 `find_spec` non-resolution; missing `__init__.py` |
| 25 | MAPPING_MATRIX_COMPLETE | YES | §6 all `HermesDelegationRequest` fields mapped |
| 26 | BLOCKED_GUARD_RECOMMENDED_RETAINED | YES | §3, §10, §12 keep `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED` |

**WSP 97 Truth Boundary Checklist: 26/26 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary discipline.
Read-only audit of the FoundUps `HermesJobExecutor` → vendored Nous Hermes Agent `delegate_task`
binding. Binding is RUNTIME_DEPENDENCY_MISSING with a concrete IMPORT_PATH_DRIFT; the
BLOCKED_REAL_DELEGATION guard must remain until the §10 gates are met. No live delegation occurred.*
