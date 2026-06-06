# AI Overseer Auto-Fix Shell-Exec Governance Audit (Phase 1)

- Lane: W9 (read-only security/governance audit)
- Status: DECISION-ONLY (no code/test/config change in this slice)
- Verdict: BLOCK_AUTOFIX_PENDING_GATE (shell-exec MECHANISM is GAP_CONFIRMED_BOUNDED; the one live command is credential-adjacent + interactive, which forces the block)
- Date: 2026-06-07
- WSP refs: WSP_00 (zen state), WSP_50 / WSP_87 (HoloIndex pre-action), WSP_15 (priority), WSP_96 (MCP/autonomous governance), WSP_97 (Truth Boundary), WSP_22 (ModLog)
- Discovered during: ollama-launch governance audit (#764)

---

## 1. Scope and Boundaries

This audit is a READ-ONLY review of the AI Overseer autonomous auto-fix surface that
calls `subprocess.run(..., shell=True)` (and `subprocess.Popen(..., shell=True)`) in
response to daemon-log pattern matches. The question is NOT "should this be autonomous"
- 012 has confirmed the system is meant to self-heal autonomously and that a human
approval gate is explicitly NOT a desired control. The question is whether the
autonomous shell-exec surface is BOUNDED, provenance-pinned, injection-free, and
test-guarded such that autonomy is safe.

Hard boundaries honored in this slice:
- No source/test/config changes.
- The AI Overseer was NOT run; no auto-fix was triggered; no configured `fix_command`
  was executed.
- Only read-only operations (file reads, rg, git) were used.
- No secrets read or displayed; no runtime launch; no WSP mutation.

Out of scope (Phase 1): implementing the remediation (allowlist, arg-vector exec,
dedup). Those are recommended below for a separate W6 slice gated by W10.

---

## 2. HoloIndex Pre-Work (WSP 50 / WSP 87)

HoloIndex / semantic search was run for the auto-fix shell-exec surface. Signal was
low: the top hits were training-corpus exports and prior-audit prose rather than the
live exec path, so ground-truth was established by direct source tracing with rg/git
and file reads (recorded throughout sections 4-10). This is consistent with prior
slices where HoloIndex surfaced documentation noise and the exec truth had to be
proven from source. The retrieval evaluation: HIGH noise (training exports),
acceptable ordering, no missing live artifact once direct grep was used, low staleness
risk (source read at HEAD), known duplication (multiple `_apply_auto_fix` copies, see
section 4).

---

## 3. Methodology

1. Enumerate every shell-exec site in the AI Overseer module (rg for subprocess /
   os.system / eval / exec / shell=True).
2. Map each `_apply_auto_fix` implementation and determine which one is bound to the
   running daemon (import/inheritance wiring).
3. Trace `fix_command` / `fix_commands` provenance: where the executed string comes
   from at runtime.
4. Trace the trigger and any gating (enable flag, retry cap, disable-on-failure).
5. Analyze interpolation/injection: any runtime data spliced into an executed string.
6. Check test coverage for shell-exec safety invariants.
7. Run an adversarial critic subworker tasked to REFUTE the working verdict by
   constructing a reachable exploit.
8. Independently verify the critic's decisive claims from source.

---

## 4. Source Inventory (shell-exec and `_apply_auto_fix` sites)

Four `_apply_auto_fix` implementations exist in the repo:

| # | File:line | shell-exec? | Interpolation branch? | Live? |
|---|-----------|-------------|-----------------------|-------|
| 1 | ai_overseer.py:2623 | YES (run subprocess.run shell=True :2659-2665) | NO | LIVE |
| 2 | auto_fix_engine.py:82 | YES (subprocess.run shell=True :118-124) | NO | not wired to live daemon |
| 3 | daemon_monitor_mixin.py:307 | YES (subprocess.run shell=True :329-335) | YES ($1 at :321-327; rotation at :443-464) | DEAD (test-only) |
| 4 | ai_overseer.py.backup:1001 | YES (shell=True :1009) | NO | DEAD (.backup file) |

Additional shell-exec in the dead mixin:
- daemon_monitor_mixin.py:803-813 `check_rotation_stalls`: `cmd = f"... --browser {browser} ..."` then `subprocess.Popen(cmd, shell=True)`. Direct f-string interpolation of breadcrumb-sourced `browser`; `operation` hardcoded to "comments" (:801).

Non-shell exec checked and cleared (list-form argv, shell=False, no interpolation):
- ai_overseer.py:1842, 1910 (`git status --porcelain` list form).
- ai_overseer.py:2228, 2243 (holo_index.py via list-form argv; query/limit are separate
  argv elements, not a shell string).
- preflight_resolution.py: zero subprocess / os.system / eval / exec.

---

## 5. Execution Path Map (LIVE daemon)

The running daemon binds the LIVE `_apply_auto_fix`:

```
youtube_dae_heartbeat.py:122-128
  from ...ai_overseer import AIIntelligenceOverseer
  self.ai_overseer = AIIntelligenceOverseer(repo_root)
-> monitor_daemon (ai_overseer.py:2318)
-> if bug["auto_fixable"] and auto_fix:  (ai_overseer.py:2454-2460)
-> self._apply_auto_fix(bug, skill)      (ai_overseer.py:2623)
-> branch run_reauthorization_script     (ai_overseer.py:2649)
-> fix_command = bug["config"].get("fix_command")   (ai_overseer.py:2650)
-> subprocess.run(fix_command, shell=True, timeout=30)  (ai_overseer.py:2659-2665)
```

Decisive wiring fact (independently verified):
- `class AIIntelligenceOverseer:` at ai_overseer.py:190 has NO base class. It does NOT
  inherit `DaemonMonitorMixin`.
- `DaemonMonitorMixin` (daemon_monitor_mixin.py:29) is referenced ONLY by
  tests/test_missing_library_detection.py:15,17 (a test subclass). No production code
  inherits it.

Therefore the `$1` substitution branch and BOTH rotation shell sites live exclusively
in code the live daemon never executes.

The LIVE `_apply_auto_fix` (ai_overseer.py:2623) has exactly four branches:
- run_reauthorization_script (:2649): shell=True on a static config string. NO `$1`.
- rotate_api_credentials (:2702): Python function call. No shell.
- reconnect_service (:2764): placeholder. No exec.
- add_unicode_conversion_before_youtube_send (:2801): git-diff patch via PatchExecutor.
  No shell. (Interpolates a module path sourced from repo JSON config, applied as a
  file patch, not a shell command.)

---

## 6. fix_command Provenance

`bug["config"]` is populated by loading a repo-committed skillz JSON
(`json.load(open(skill_path))`), where `skill_path` is a hardcoded repo path
(`modules/communication/livechat/skillz/youtube_daemon_monitor.json`). It is NOT loaded
from network, env var, user input, LLM output, or a writable runtime cache on the live
path.

The only `fix_command` value present in ANY config file repo-wide:
- youtube_daemon_monitor.json:51 -> `python modules/platform_integration/youtube_auth/scripts/reauthorize_set1.py` (static, no placeholder).

The rotation `fix_commands` dict (youtube_daemon_monitor.json:150-155) holds four static
`python -m ...rotation_supervisor --browser <X> --operation <Y> --timeout 300` strings.
These are consumed only by the DEAD mixin's `trigger_next_rotation`; the live class has
no `trigger_next_rotation` branch.

Conclusion: every command the live daemon can shell-execute today is a single static,
repo-committed, version-controlled string. Provenance = repo source control.

### 6.1 The live command is credential-adjacent, interactive, and destructive

The single live command (`reauthorize_set1.py`) was inspected from source. It is NOT a
harmless no-op; it meets all three of the escalation triggers for credential-adjacent
auto-fix:

- Modifies credential state: `os.remove(token_path)` at reauthorize_set1.py:39 deletes
  the existing OAuth token unconditionally before any new auth is obtained.
- Opens a browser + interactive login: reauthorize_set1.py:50-58 prints
  `[BROWSER] Browser will open for authorization...` and calls
  `get_authenticated_service(1)`, which triggers the interactive Google OAuth consent
  flow ("Sign in with the Google account and authorize the app"). On success it writes a
  new token (reauthorize_set1.py:58-73).

This makes autonomous execution actively harmful, not merely ungoverned. The live daemon
runs headless 24/7. On an `oauth_revoked` log match (youtube_daemon_monitor.json:49-51,
qwen_action auto_fix, P0) the daemon autonomously runs this script. Sequence:
1. The script deletes the working token (os.remove :39).
2. It blocks waiting for an interactive browser login that no human is present to
   complete.
3. The 30s subprocess timeout (ai_overseer.py:2659-2665) kills the process AFTER the
   token has already been removed.

Net effect: a transient/spurious `oauth_revoked` log line can cause the auto-fix to
DESTROY a possibly-valid token and leave YouTube auth unauthenticated, with no human in
the loop to recover it. This is a self-inflicted availability/credential outage vector,
not a fix. It is the decisive reason the overall verdict escalates from
GAP_CONFIRMED_BOUNDED to BLOCK_AUTOFIX_PENDING_GATE.

---

## 7. Trigger and Gating Analysis

Trigger (ai_overseer.py:2454-2460): `if bug["auto_fixable"] and auto_fix:` ->
`_apply_auto_fix`. Two conditions:
- `bug["auto_fixable"]`: set from the skill/pattern classification in the repo-committed
  skillz JSON (`qwen_action: auto_fix`, `auto_fix_threshold.max_complexity <= 2`).
- `auto_fix`: a call parameter to `monitor_daemon` (tests pass `auto_fix=True`).

Existing autonomous bounds (NOT human gates):
- 3-attempt retry cap and disable-after-3-failures (ai_overseer.py ~:2435, :2462-2467).
- Per-fix metrics/outcome logging (append_performance_metric / append_outcome_metric).
- `subprocess` timeout (30s reauth; 360s rotation in the dead path).

Governance note (per 012): for ORDINARY self-heal actions there is intentionally NO
012/W10 human approval gate on the live path, and one should NOT be added. The system is
designed to self-heal autonomously; W10 and 012 hand-running these audits are the
temporary MANUAL scaffolding the architecture exists to retire. The correct control for
an ordinary autonomous shell surface is a CODE-ENFORCED static boundary (allowlist +
arg-vector exec + provenance pin), which preserves full autonomy. "Missing human gate"
is therefore NOT logged as a gap for ordinary actions.

Carve-out (per 012 point 6): CREDENTIAL-ADJACENT actions are different. An action that
opens a browser / requires interactive login / mutates credential state cannot be safely
auto-run by a headless daemon - it either hangs (no human to complete login) or destroys
credential state (see section 6.1). For this class a gate IS warranted, OR the action
must be replaced by a proven-noninteractive equivalent (silent token refresh). This is
not re-introducing a blanket human-in-the-loop; it is recognizing that an interactive
flow is fundamentally incompatible with autonomous headless execution. The live
`run_reauthorization_script` action falls in this carve-out.

---

## 8. Allowlist / Sandbox / Logging Posture

- Allowlist: NONE. The live code executes whatever string `bug["config"].get("fix_command")`
  returns. Today that is one static repo value, but nothing in code constrains it to an
  allowlisted set; a future skill JSON could ship any command and it would run.
- Sandbox: NONE. The command runs as the daemon user with `shell=True` (and `cwd=repo_root`
  on the rotation path). No container, no restricted PATH, no dropped privileges.
- shell=True: used on all four exec sites. Unnecessary for the static argv-style commands
  in use and is the single largest latent injection multiplier.
- Logging: PRESENT. The command string is logged before execution (`[AUTO-FIX] Running
  OAuth reauth: {fix_command}`) and the outcome (returncode, truncated stdout/stderr) is
  recorded to metrics. This is an audit trail but not a control.

---

## 9. Interpolation / Injection Analysis

Two runtime-interpolation primitives exist; both are in DEAD (non-inherited) code:

(a) `$1` substitution - daemon_monitor_mixin.py:321-327:
```
if "$1" in fix_command and "matches" in bug:
    library_name = matches[0] ...
    fix_command = fix_command.replace("$1", library_name.strip())
subprocess.run(fix_command, shell=True, ...)
```
`matches[0]` is a regex capture off the daemon log. This is a genuine command-injection
primitive IF a skill ships a `$1` fix_command with `fix_action: install_missing_library`.
It is DOUBLE-bounded today:
- Config-unreachable: `install_missing_library` appears in ZERO *.json repo-wide (only as
  a code literal at :315); no live skill ships a `$1` fix_command.
- Inheritance-unreachable: the branch lives in `DaemonMonitorMixin`, which the live
  `AIIntelligenceOverseer` does not inherit. A malicious JSON would fall through the live
  4-branch `_apply_auto_fix` to a no-op default.

(b) `browser` f-string - daemon_monitor_mixin.py:803:
```
cmd = f"python -m ...rotation_supervisor --browser {browser} --operation comments ..."
subprocess.Popen(cmd, shell=True, ...)
```
`browser` comes from breadcrumb metadata (default "edge"). Direct interpolation into a
shell string. DEAD (mixin not inherited); `operation` hardcoded.

Live rotation path (mixin trigger_next_rotation :443-454, also dead): `cmd_key =
f"{browser}_{operation}"` is used only as a DICT KEY (`.get`) against four static values
plus a static fallback. The executed string is never assembled from runtime data; even an
attacker-influenced key returns one of five static strings or None. Bounded by
construction.

Live path conclusion: NO runtime data is interpolated into any string the live daemon
shell-executes. The only live exec is the static reauth command.

---

## 10. Test Coverage

Tests exercise the `auto_fix=True` flag and bug classification
(test_ai_overseer_monitoring.py, test_daemon_monitoring_witness_loop.py,
test_ai_overseer_unicode_fix.py, test_monitor_flow.py) and the mixin detection/`$1`
path (test_missing_library_detection.py). NONE assert a shell-exec safety invariant:
- No allowlist test (no assertion that a non-allowlisted command is rejected).
- No injection test (no assertion that `$1`/`;`/`&&`/backtick tokens are neutralized).
- No shell=False / arg-vector assertion.

Consequence: a future one-line change that wires the dead mixin into the live class
(`class AIIntelligenceOverseer(DaemonMonitorMixin):`) would re-enable both injection
primitives and pass CI silently. The absence of a negative/safety test is the main
reason the BOUNDED state is fragile rather than guaranteed.

---

## 11. Adversarial Critic Findings

A dedicated adversarial critic subworker was tasked to REFUTE the working verdict by
constructing a reachable exploit (config-poisoned command, command injection via the
`$1`/regex path, breadcrumb-driven injection on the rotation path, non-repo config
source, hidden agent launch, secret exfiltration).

Result: EXPLOIT_CONSTRUCTED = NO. The critic UPHELD all four working claims and added the
decisive wiring fact (live class does not inherit the mixin), making the `$1` primitive
doubly unreachable. The critic independently surfaced the second interpolation site
(check_rotation_stalls :803), also dead. Its recommended verdict matched:
GAP_CONFIRMED_BOUNDED.

Critic residual-risk (adopted here): the dangerous primitives are fully written and gated
off only by an inheritance accident; the breadcrumb `browser` provenance could not be
bound to a closed allowlist, and zero negative tests mean a re-wiring regression would be
silent.

Verification of critic claims (done first-hand, not taken on trust):
- `class AIIntelligenceOverseer:` at ai_overseer.py:190 - confirmed no base class.
- `DaemonMonitorMixin` referenced only by test_missing_library_detection.py:15,17 -
  confirmed via repo-wide grep.
- check_rotation_stalls f-string + Popen(shell=True) at daemon_monitor_mixin.py:803-813 -
  confirmed by file read.

---

## 12. Exploitability Verdict

VERDICT: BLOCK_AUTOFIX_PENDING_GATE
(shell-exec MECHANISM sub-verdict: GAP_CONFIRMED_BOUNDED)

Two layers, two findings:

Layer A - the shell-exec mechanism: GAP_CONFIRMED_BOUNDED.
- There IS a real, autonomous shell-exec surface on the live path
  (run_reauthorization_script, shell=True). Not NO_EXEC_SURFACE.
- Not SAFE_BOUNDED: real gaps exist - no code-enforced allowlist, unnecessary shell=True,
  latent injection primitives present in the codebase, 3x duplication plus a .backup,
  zero shell-safety tests.
- Not GAP_CONFIRMED_EXPLOITABLE from injection: no injection exploit is reachable today.
  The single live command is a static repo-committed string; both interpolation
  primitives are config-unreachable AND inheritance-unreachable.

Layer B - the live command it runs: forces BLOCK_AUTOFIX_PENDING_GATE.
- The one live fix_command (reauthorize_set1.py) is credential-adjacent, interactive
  (opens a browser / requires Google login), and destructive (os.remove of the OAuth
  token at :39 before re-auth). See section 6.1.
- Auto-running it from a headless 24/7 daemon on a regex log match is not a fix: it
  deletes a possibly-valid token and then hangs on a login no human can complete, and the
  30s timeout kills it after the token is already gone -> self-inflicted YouTube-auth
  outage.
- Per 012's explicit rule (browser/login/credential-state => BLOCK_AUTOFIX_PENDING_GATE),
  this credential-adjacent auto-fix must be blocked/gated until it is either gated or
  replaced by a proven-noninteractive token refresh.

Overall: BLOCK_AUTOFIX_PENDING_GATE. The block is narrow and principled - it does NOT
contradict the autonomous design intent (section 7). Ordinary self-heal stays
gate-free; only the credential-adjacent, interactive action class is blocked, because an
interactive browser-login flow is incompatible with headless autonomy. The Layer-A
hardening (allowlist + arg-vector exec + dedup + tests) remains required regardless.

---

## 13. Remediation (autonomous-safe; NOT a human gate)

All recommendations preserve full autonomy. None introduces a 012/W10 approval gate.
Proposed as a separate W6 slice, W10-gated:

1. Drop shell=True everywhere. Convert all four `_apply_auto_fix` exec sites (and the
   mixin Popen) to list-form argv with shell=False (`subprocess.run(shlex.split(cmd),
   shell=False, ...)`), eliminating the shell metacharacter surface while staying fully
   autonomous.
2. Code-enforced static allowlist. Validate any `fix_command` against a repo-owned
   allowlist manifest (permitted binary + argument shape) before exec; reject and log
   anything else. This is an autonomous, code-level boundary - no human in the loop.
3. Remove / neutralize the latent injection primitives. Delete the dead mixin
   interpolation branches (`$1` at :321-327, browser f-string at :803), or if retained,
   `shlex.quote` every interpolated token and route through the allowlist.
4. Provenance pin. Assert at load time that skill config comes from a repo-committed
   path; reject config sourced from writable runtime/network locations.
5. Deduplicate. Collapse the three live `_apply_auto_fix` copies into one governed
   implementation; delete ai_overseer.py.backup. Single audited exec path removes drift
   and the inheritance-accident fragility.
6. Add negative safety tests. Assert (a) allowlist rejects a non-allowlisted command,
   (b) an injection token in a regex capture is neutralized, (c) exec is shell=False.
   This makes a future mixin re-wiring fail CI loudly instead of silently.

Priority (WSP_15): P1. Not P0 because no live exploit; above routine because the
primitives are written and one inheritance edit would activate them.

---

## 13B. Addendum: Autonomous WRE Authority Boundary (012 clarification)

Governing principle (012): do NOT treat "require 012 approval" as the default
remediation. 012/W10 manual gating is temporary scaffolding and review discipline, not
the target runtime architecture. Target = autonomous by default inside a bounded,
code-enforced policy; fail-closed on violation; no free-form shell text; no
model-generated commands; no unpinned config-sourced command authority; durable evidence
and replay; 012 escalation ONLY when policy cannot decide.

Corollary applied to the verdict: the "GATE" in BLOCK_AUTOFIX_PENDING_GATE means a
CODE-ENFORCED policy gate (fail-closed block of the credential-adjacent class) plus a
noninteractive replacement - NOT a 012 human approval gate. Interim safe state =
autonomously DISABLE the credential-adjacent auto-fix (fail-closed), not route it to a
human.

### Action taxonomy applied to this surface

| Class | Present here? | Evidence / note |
|-------|---------------|-----------------|
| 1. Human approval gate | NOT on auto-fix path | input("Approve? y/n") exists elsewhere (ai_overseer.py:1456, mission_execution_mixin.py:64) - runtime-crutch pattern, not on this path |
| 2. Code-enforced autonomous gate | EXISTS in module, NOT used by auto-fix | vulnerability_scan_policy.py (EscalationDestination, requires_012); preflight_resolution.py:181-207; auto-fix bypasses all of it |
| 3. Static allowlist | ABSENT | ai_overseer.py:2650 runs any bug["config"]["fix_command"]; no allowlist/schema |
| 4. Dynamic/model-selected command | NO | command is config-sourced static string, not model-generated (good) |
| 5. Credential-adjacent operation | YES, UNCLASSIFIED | reauthorize_set1.py (OAuth) run through the same generic shell path as any other fix |
| 6. Destructive operation | YES, UNCLASSIFIED | reauthorize_set1.py:39 os.remove(token) - destructive, no risk class |
| 7. External-agent launch | NO (on live path) | dead mixin rotation Popen is non-live |
| 8. Sandbox-only operation | NO | runs as daemon user, shell=True, cwd=repo_root; no sandbox |

### Required questions (answered from source)

1. Does the auto-fix path rely on 012/W10 manual approval for safety? NO. The live path
   has no approval gate; safety today rests only on the command happening to be one
   static string.
2. Temporary scaffolding or production behavior? N/A (no approval exists). W10 is purely
   merge/review infra; it has zero runtime presence in the daemon.
3. Code-enforced allowlist independent of 012? NO (defect). ai_overseer.py:2650 executes
   whatever the config returns.
4. Commands typed or free shell strings? HYBRID: fix_action is a typed branch selector,
   but the command body is a FREE shell string (fix_command). Defect: free-string body.
5. Arguments structured and validated? NO. One opaque string to shell=True; no argv, no
   validation.
6. shell=True in the autonomous path? YES - ai_overseer.py:2659-2665 (live). Also
   auto_fix_engine.py:118 and daemon_monitor_mixin.py:329/457/807 (non-live).
7. Provenance pinned to repo-owned reviewed config? PARTIAL/UNENFORCED. Repo JSON by
   convention; nothing in code verifies the source. Defect.
8. Can config changes expand execution authority without tests failing? YES (defect). A
   PR / stale worktree / skill edit adding a fix_command runs with no test catching it;
   no test asserts "config cannot introduce arbitrary shell."
9. Are credential/OAuth/secret/git-write/pkg-install/external-launch separated into
   higher-risk classes? NO (defect). All fix_actions share one uniform shell-exec path;
   reauth (credential/OAuth/destructive) is not risk-classified.
10. Any "requires_012"-style labels where autonomous code policy should exist? YES, but
    SPLIT: a real code policy exists in vulnerability_scan_policy.py / preflight_resolution.py
    (requires_012, GATE_012), AND a stub auto-grant exists in mcp_integration.py:334-346
    ("simulate approval ... granted"). The auto-fix path uses NEITHER - worst of both:
    no human gate AND no code policy.
11. Where does W10 remain merge/review-only, not runtime authority? Everywhere - the
    daemon never consults W10 at runtime. Correct; no change needed there.
12. What must be refactored for autonomous WRE to run safely without asking 012? See
    remediation below; route fix execution through the existing
    vulnerability_scan_policy-style classifier rather than inventing a human gate.

### Reframed remediation (autonomous-first, fail-closed)

Do NOT add a 012 approval gate as the primary fix. Preferred (W6 slice, W10-gated):
1. Centralize auto-fix execution into ONE module; delete the duplicates and
   ai_overseer.py.backup (removes drift + the inheritance-accident fragility).
2. Convert fix_command strings into typed FixAction IDs (enum), not free JSON shell text.
3. Static allowlist mapping FixAction -> argv vector; reject anything not in the map
   (fail-closed).
4. Remove shell=True everywhere; execute argv with shell=False.
5. Structured, validated arguments (no string splicing; shlex.quote any interpolated
   token that survives).
6. Pin provenance: assert config came from a repo-committed, reviewed path; reject
   writable/runtime/network sources.
7. Risk-classify FixActions and route through the EXISTING policy classifier
   (vulnerability_scan_policy.py model: CRITICAL/SECRET => GATE_012; ordinary =>
   autonomous). Credential-adjacent / destructive / external-agent-launch classes
   fail-closed (auto-DISABLED) until a code policy for them exists.
8. Replace the interactive reauth with a proven-noninteractive token refresh; never
   os.remove a valid token before a new one is obtained.
9. Emit a durable evidence packet per execution (FixAction, argv, provenance, outcome)
   for WRE / WSP_97 / W10 post-hoc review and replay.
10. Add tests that FAIL if config can introduce arbitrary shell, if shell=True reappears,
    or if a credential/destructive class executes without a code policy.

## 14. WSP_97 Truth Boundary Checklist

Declared items: 17 - Rows: 17 - All YES

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY (no source/test/config change) | YES | Only doc added under docs/audits/security/; no code/test/config edited |
| 2 | NO_AUTOFIX_TRIGGER (overseer not run, no fix executed) | YES | No invocation of AIIntelligenceOverseer or _apply_auto_fix; analysis via reads/grep only |
| 3 | NO_COMMAND_EXECUTION_VIA_OVERSEER | YES | No configured fix_command run; no shell command except read-only rg/git/file reads |
| 4 | NO_SECRETS_READ_OR_DISPLAYED | YES | No .env/credential reads; provenance traced via config schema only |
| 5 | HOLOINDEX_PREWORK_DONE (WSP 50/87) | YES | Section 2; HoloIndex run, low signal, ground-truth via direct source trace |
| 6 | LIVE_EXEC_PATH_PROVEN_FROM_SOURCE | YES | Section 5; youtube_dae_heartbeat.py:122-128 -> ai_overseer.py:2454-2660 |
| 7 | PROVENANCE_TRACED (config source identified) | YES | Section 6; fix_command = repo-committed youtube_daemon_monitor.json:51 (static) |
| 8 | INTERPOLATION_PRIMITIVES_ENUMERATED | YES | Section 9; $1 at mixin:321-327 and browser f-string at mixin:803, both dead |
| 9 | LIVE_CLASS_DOES_NOT_INHERIT_MIXIN (verified) | YES | ai_overseer.py:190 no base class; mixin referenced only by test_missing_library_detection.py:15,17 |
| 10 | TEST_COVERAGE_ASSESSED | YES | Section 10; classification tests only, no shell-safety/allowlist/injection test |
| 11 | ADVERSARIAL_CRITIC_RUN_AND_VERIFIED | YES | Section 11; critic EXPLOIT_CONSTRUCTED=NO, all 4 claims UPHELD; claims re-verified first-hand |
| 12 | LIVE_COMMAND_INSPECTED_FROM_SOURCE | YES | Section 6.1; reauthorize_set1.py:39 os.remove(token) + :50-58 interactive browser OAuth, read first-hand |
| 13 | CREDENTIAL_ADJACENT_CLASS_IDENTIFIED | YES | Section 6.1 / 13B; reauth meets browser+login+credential-state triggers -> BLOCK class |
| 14 | NO_HUMAN_GATE_AS_RUNTIME_CRUTCH | YES | Section 13B; remediation is code-enforced autonomous policy, not a 012 approval gate; "no 012 gate" not logged as defect for ordinary actions |
| 15 | CODE_ENFORCED_AUTONOMOUS_BOUNDARY_REQUIRED | YES | Section 13B Q3/Q7/Q9; absence of allowlist/provenance-pin/risk-class IS the logged defect |
| 16 | NO_FREEFORM_SHELL_AUTHORITY | YES | Section 13B Q4/Q6; free-string fix_command + shell=True flagged; remediation = typed FixAction -> argv allowlist |
| 17 | 012_ESCALATION_ONLY_FOR_OUT_OF_POLICY_CASES | YES | Section 13B; route via vulnerability_scan_policy model (GATE_012 for CRITICAL/SECRET only); ASCII byte-check: zero bytes > 127 before commit |

---

## ModLog (WSP 22)

- 2026-06-07: W9 read-only security/governance audit of the AI Overseer autonomous
  auto-fix shell-exec surface. Verdict BLOCK_AUTOFIX_PENDING_GATE (shell-exec mechanism
  sub-verdict GAP_CONFIRMED_BOUNDED). The mechanism is bounded: the live surface executes
  one static repo-committed command via shell=True, and the two runtime-interpolation
  injection primitives are config-unreachable AND inheritance-unreachable (live
  AIIntelligenceOverseer does not inherit DaemonMonitorMixin). The block is forced by the
  one live command (reauthorize_set1.py): it is credential-adjacent, interactive (browser
  OAuth login) and destructive (os.remove of the OAuth token), so a headless daemon
  auto-running it on a regex log match can destroy a valid token and hang -> self-inflicted
  YouTube-auth outage. Gaps: no code-enforced allowlist, free-string fix_command +
  unnecessary shell=True, latent injection primitives in dead code, 3x duplication plus a
  .backup, no risk-classification of credential/destructive actions, zero shell-safety
  tests. Per 012's autonomy-boundary addendum, the "gate" is a CODE-ENFORCED policy gate
  (fail-closed disable of the credential-adjacent class) + a noninteractive token-refresh
  replacement, NOT a 012 human approval gate; ordinary self-heal stays gate-free.
  Remediation should route fix execution through the existing
  vulnerability_scan_policy-style classifier (GATE_012 only for out-of-policy CRITICAL/
  SECRET). Phase 1 decision-only; remediation deferred to a W10-gated W6 slice.
