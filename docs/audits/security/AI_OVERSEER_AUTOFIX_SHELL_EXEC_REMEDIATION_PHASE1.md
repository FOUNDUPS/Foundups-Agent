# AI_OVERSEER_AUTOFIX_SHELL_EXEC_REMEDIATION_PHASE1

**Slice:** AI_OVERSEER_AUTOFIX_SHELL_EXEC_REMEDIATION_PHASE1
**Worker-Lane:** W6
**Author:** 0102 (WSP_00 zen state, FOLLOW-WSP, WSP_97 Truth Boundary + CoT/CoR)
**Type:** SECURITY CODE REMEDIATION.

---

## 1. Mission and Scope

Eliminate the AI Overseer auto-fix arbitrary-shell-exec surface by replacing freeform shell
(`subprocess.run(fix_command, shell=True)`) with a typed, statically-allowlisted, `shell=False`
executor. Security property: **"config selects, never injects."** Skill-config JSON may only
SELECT which allowlisted `FixAction` runs (with validated discrete params); it can never supply
a command string that reaches a shell. Autonomy is preserved (no 012 runtime-approval crutch);
the boundary is code-enforced. Dead/stale duplicates are deleted so they cannot become re-entry
points.

Scope: the ai_overseer module only - new executor + 2 live callers migrated + dead-file deletion
+ live-config migration + tests + ModLog/TestModLog + this audit. No new dependency (stdlib
only). No behavior regression to legitimate autonomous auto-fix.

---

## 2. Predecessor #767 + Re-Verified Live/Dead Classification

#767 (AI_OVERSEER_AUTOFIX_SHELL_EXEC_GOVERNANCE_AUDIT, merged 0b55b5cdd) classified the surface.
Per the dispatch, all line numbers were RE-VERIFIED on current main (0b55b5cdd) - not trusted
blindly. Re-verification found one correction to the reachability claim:

| Surface | shell exec | Reachability (re-verified) |
|---------|-----------|----------------------------|
| `ai_overseer.py:2659` `_apply_auto_fix` (OAuth reauth) | `subprocess.run(fix_command, shell=True)` | **CONFIRMED LIVE** - `AIIntelligenceOverseer._apply_auto_fix` is called at `ai_overseer.py:2460`; instance built in `youtube_dae_heartbeat.py:128` |
| `daemon_monitor_mixin.py:329` `_apply_auto_fix` (reauth/install) | `shell=True` | LATENT - `DaemonMonitorMixin` is imported only by a test; `AIIntelligenceOverseer` (L190) does NOT inherit it |
| `daemon_monitor_mixin.py:457` `_apply_auto_fix` (rotation) | `shell=True` | LATENT (same mixin) |
| `daemon_monitor_mixin.py:807` `check_rotation_stalls` | `subprocess.Popen(cmd, shell=True)` | LATENT - `youtube_dae_heartbeat.py:187` calls `self.ai_overseer.check_rotation_stalls(...)`, but `AIIntelligenceOverseer` does not expose that method (AttributeError, loop-guarded) |
| `auto_fix_engine.py` | `shell=True` (L120) | DEAD - 0 production imports |
| `ai_overseer.py.backup` | `shell=True` | DEAD - `.backup`, not importable |

**Truth-boundary note:** the dispatch/Addendum treat the `daemon_monitor_mixin` paths as live;
re-verification shows they are latent/orphaned on current main (the mixin is not inherited by the
live overseer, and `check_rotation_stalls` is currently unreachable from the heartbeat). All of
them are nonetheless migrated/neutralized as required (latent shell=True re-entry points). The
inheritance gap is a separate functional bug and is NOT changed here (out of security scope).

---

## 3. FOLLOW-WSP Evidence

- **(1) Occam:** smallest correct boundary - one executor module; reuse stdlib subprocess/enum/
  dataclasses; preserve the safe Python-native fix branches (`rotate_api_credentials`,
  `reconnect_service`, `add_unicode_...`) untouched; only the shell branches are centralized.
- **(2) HoloIndex FIRST** (WSP 50/87): queries `subprocess argv allowlist shell False command
  executor` (0 hits) and `FixAction typed action allowlist auto fix` (action_router /
  decision_policy - not subprocess executors). **No existing argv-allowlist executor pattern to
  reuse** -> built a minimal one. Recorded `HOLOINDEX_LOW_SIGNAL`.
- **(4) Real FixAction set derived from ACTUAL live config**
  (`modules/communication/livechat/skillz/youtube_daemon_monitor.json`):
  - `run_reauthorization_script` -> `python modules/platform_integration/youtube_auth/scripts/reauthorize_set1.py` (fixed script, no params) -> **FixAction.REAUTHORIZE**.
  - `trigger_next_rotation` -> `fix_commands` over browser in {chrome, edge} x operation in {comments, shorts} -> **FixAction.ROTATION_RECOVERY** (params enum-validated).
  - `rotate_api_credentials` -> Python-native (already safe; untouched).
  - `install_missing_library` -> **NOT present in any live config** -> latent -> NOT implemented; the executor REJECTS it (Addendum #3).

---

## 4. Design

New module `src/autofix_executor.py`:
- `class FixAction(enum.Enum)`: exactly `REAUTHORIZE`, `ROTATION_RECOVERY` (derived from live config).
- Static, code-defined `_ALLOWLIST: {FixAction -> argv builder}`. Builders return `list[str]`;
  params inserted as **discrete enum-validated argv elements**, never string-concatenated.
  - `_reauthorize_argv`: `[sys.executable, <repo>/.../reauthorize_set1.py]` (no config influence).
  - `_rotation_argv`: `[sys.executable, "-m", "modules.communication.livechat.src.rotation_supervisor", "--browser", <chrome|edge>, "--operation", <comments|shorts>, "--timeout", "300"]`.
- `assert_no_command_fields(config)`: REJECTS (not ignores) `fix_command` / `fix_commands`.
- `resolve_fix_action(str)`: exact-match map to the enum or REJECT.
- `execute_fix(...)`: the ONLY execution path - `subprocess.run(argv, shell=False, ...)` (`wait=True`)
  or `subprocess.Popen(argv, shell=False, ...)` (`wait=False`). Uses `sys.executable` (Addendum #5).
  Returns an `EvidencePacket`; on any rejection/error, `decision="REJECTED"`/`success=False` and
  NOTHING executes.
- `EvidencePacket`: action, decision, safe argv, cwd, timeout, returncode, pid, truncated
  stdout/stderr, timestamp, success, reason. No env/token/secret fields (Addendum #6).
- **Output redaction (W10 micro-repair):** captured `stdout`/`stderr` and any `execution_error`
  reason are passed through `redact_sensitive()` BEFORE storage (redaction applied before tail
  truncation, so no token straddles the boundary). It redacts access/refresh/id tokens,
  client_secret/client_id, OAuth `code`/`user_code`/`authorization_code`, OAuth URL query params
  (`code=`/`access_token=`/...), `*_TOKEN`/`*_SECRET`/`*_PASSWORD`/`*_API_KEY` env-style pairs,
  bearer tokens, and known token shapes (`ya29.`, `1//`, `AIza`, `sk-`, `gh[posru]_`).

---

## 5. Migration of the Callers (file:line before -> after)

All four shell paths now route through `execute_fix`; none builds a string command or uses shell.

| Caller | Before | After |
|--------|--------|-------|
| `ai_overseer.py` `_apply_auto_fix` reauth (was L2649-2699) | `subprocess.run(fix_command, shell=True, timeout=30)` | `execute_fix("run_reauthorization_script", bug.get("config",{}), wait=True, timeout=30)` |
| `daemon_monitor_mixin.py` `_apply_auto_fix` reauth/install (was L315-365) | `$1` string-substitution + `subprocess.run(fix_command, shell=True)` | `execute_fix(fix_action, bug.get("config",{}), wait=True, timeout=30)` (install_missing_library -> REJECTED) |
| `daemon_monitor_mixin.py` `_apply_auto_fix` rotation (was L443-494) | `subprocess.run(fix_command, shell=True, timeout=360)` | `execute_fix("trigger_next_rotation", config, {"browser","operation"}, wait=True, timeout=360, cwd=repo_root)` |
| `daemon_monitor_mixin.py` `check_rotation_stalls` (was L797-822) | `subprocess.Popen(cmd, shell=True)` | `execute_fix("trigger_next_rotation", {}, {"browser","operation"}, wait=False, cwd=repo_root)` |

Both modules import `execute_fix`. The migrated returns expose `decision` + the evidence packet,
and no longer return the raw command string.

**Live config migrated** (Addendum #2): `youtube_daemon_monitor.json` - removed `fix_command`
(reauth entry) and the `fix_commands` dict (rotation entry); `fix_action` retained. The executor
now REJECTS any config that re-introduces those command fields.

---

## 6. Dead/Stale Neutralization

- `src/auto_fix_engine.py` - **DELETED** (`git rm`). Re-verified 0 production imports
  (rg for `import auto_fix_engine` / `AutoFixEngine` excluding the file: none). It carried
  `shell=True` at L120 - a latent re-entry point now removed.
- `src/ai_overseer.py.backup` - **DELETED** (`git rm`). `.backup`, not importable.
- `REFACTOR_PLAN.md` updated with a note that `auto_fix_engine.py` was deleted (doc consistency).
- Test `TestDuplicatesGone` proves both files are gone AND that no production `.py` imports the
  deleted engine.

---

## 7. Config-Injection Boundary Proof + Adversarial Attempt (Refuted)

**Test battery** (`TestConfigInjectionRefuted`): 10 malicious payloads (`rm -rf /`, `;`, `&&`,
`$()`, backticks, pipe-to-nc, path traversal, `>/dev/tcp`, newline-injection) fed via
`fix_command`, `fix_commands`, and the `browser` param. Each -> `decision == "REJECTED"`, and
the negative control asserts `subprocess.run`/`Popen` are **never called**.

**Independent adversarial verification** (separate red-team pass): strongest attack =
argv/option injection via the rotation `browser` param (e.g. `"edge --foo; rm -rf / #"`).
**refuted: true.** Reasons (code-level): (a) `shell=False` + list argv makes metacharacters
inert - one literal token, never interpreted; (b) the enum gate `browser not in ("chrome","edge")`
rejects the payload before exec (`FixActionRejected`); (c) type-confusion (dict/list browser)
fails closed on the same check; (d) `fix_command`/`fix_commands` are rejected before action
resolution and are never read to build argv; (e) unmapped `fix_action` rejected; (f) the
REAUTHORIZE script path is hardcoded from `REPO_ROOT`, not config-influenceable. No
attacker-controlled string reaches a shell or selects the executed program.

**Residual concerns (NOT arbitrary-exec, recorded honestly):**
- The separate `add_unicode_conversion_before_youtube_send` branch builds a patch target path
  from config `fix_module` and applies it via `PatchExecutor` (a file-write primitive, not a
  shell). Out of this remediation's shell-exec scope; recommend confirming `PatchExecutor`
  path-confinement in a follow-up.
- An attacker controlling skill config can repeatedly TRIGGER allowlisted (safe) fixes
  (bounded by the `fix_attempts` throttle: 300s window, disable after 3). This is the intended
  trust model ("config selects among safe actions"), not an exec escape.

---

## 8. Test Matrix (each guard with a negative control)

File: `tests/test_autofix_executor_security.py` - **63 passed** (added to the conftest
default-run allowlist so it runs in CI, not skipped). The 14 added by the W10 micro-repair
prove evidence-packet VALUE-level redaction (below).

| Guard | Test(s) | Negative control |
|-------|---------|------------------|
| Config-injection refuted | `test_fix_command_payload_is_rejected_not_executed` (x10), `_fix_commands_dict_` (x10), `_malicious_browser_param_` | `test_negative_control_clean_config_is_allowed` (clean config DOES proceed) |
| Unmapped action rejected | `test_unmapped_action_rejected` | (clean-config control above) |
| install_missing_library rejected | `test_install_missing_library_rejected_latent` | n/a (asserts absent from enum) |
| Static argv allowlist | `test_reauthorize_argv_is_fixed`, `test_rotation_argv_uses_validated_enums`, `_rejects_unknown_browser/operation` | enum-reject parametrize |
| Zero shell=True | `test_no_shell_true_call_in_source` (AST, 3 files) | `test_negative_control_ast_scanner_detects_shell_true` (planted shell=True IS caught) |
| No Popen shell | `test_no_popen_shell_in_check_rotation_stalls` | n/a |
| Callsite guard | `test_callsites_use_execute_fix_and_no_config_command_read` | n/a |
| Autonomy preserved | `test_execute_fix_has_no_approval_parameter`, `_executes_without_prompt` (input never called) | n/a |
| Evidence packet | `test_evidence_packet_fields_present_and_safe`, `_spawn_evidence_has_pid` | safety: no secret fields |
| Evidence VALUE redaction (W10) | `TestEvidencePacketRedaction` (10 token/code/secret/OAuth-URL payloads + leaky stdout/stderr + error reason) | `test_negative_control_non_secret_output_survives` (ordinary output is NOT over-redacted) |
| Duplicates gone | `test_dead_files_deleted`, `test_no_production_import_of_auto_fix_engine` | n/a |
| Live config migrated | `test_youtube_daemon_monitor_has_no_command_fields` | n/a |

No skip/xfail in the new tests.

---

## 9. Autonomy-Preserved Proof (no 012 runtime gate)

The security boundary is code-enforced (typed allowlist + shell=False), NOT a human in the loop.
`execute_fix` has no approval/confirm/human/operator/interactive parameter
(`test_execute_fix_has_no_approval_parameter`), and an allowlisted fix runs end-to-end with
`builtins.input` never called (`test_allowlisted_action_executes_without_prompt`). OpenClaw/Hermes
keep auto-fixing safely without a 012-in-the-loop crutch.

---

## 10. Internal Review Verdict

**READY.** The arbitrary-shell-exec surface is eliminated: one typed, statically-allowlisted,
`shell=False` executor; all four shell/Popen paths migrated; the two dead duplicates deleted; the
live config migrated and command fields rejected at runtime. Zero `shell=True` remains on any
auto-fix source (AST-proven). Config-injection is refuted by a 49-test battery + an independent
adversarial pass. Autonomy is preserved (no human gate). `install_missing_library` is rejected as
latent. Line numbers were re-verified on 0b55b5cdd and a reachability correction to #767 is
recorded. Residual non-exec concerns are documented for follow-up.

---

## 11. WSP_97 Truth Boundary Checklist

Declared count: 22 / 22 YES (rows below = 22).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | CENTRALIZED_EXECUTOR_SINGLE_PATH | YES | `autofix_executor.execute_fix`; both callers route through it (Sec 5) |
| 2 | TYPED_FIXACTION_ENUM | YES | `class FixAction(enum.Enum)` - REAUTHORIZE, ROTATION_RECOVERY |
| 3 | STATIC_ARGV_ALLOWLIST_NO_CONCAT | YES | `_ALLOWLIST` argv builders; discrete tokens (Sec 4; argv tests) |
| 4 | ZERO_SHELL_TRUE | YES | AST test across 3 source files = 0; negative control catches planted shell=True |
| 5 | DEAD_DUPLICATES_DELETED | YES | `git rm` auto_fix_engine.py + ai_overseer.py.backup; import-scan test |
| 6 | AUTONOMY_PRESERVED_NO_012_GATE | YES | Sec 9; no approval param; input() never called |
| 7 | CONFIG_INJECTION_REFUTED | YES | 49-test battery + independent adversarial pass (refuted=true), Sec 7 |
| 8 | EVIDENCE_PACKET_EMITTED | YES | `EvidencePacket.to_dict`; evidence-packet tests |
| 9 | INSTALL_MISSING_LIBRARY_REJECTED | YES | not in enum; `test_install_missing_library_rejected_latent` |
| 10 | ROTATION_PARAMS_ENUM_VALIDATED | YES | browser{chrome,edge}, operation{comments,shorts}; reject tests |
| 11 | SYS_EXECUTABLE_USED | YES | argv[0]==sys.executable (no bare "python"); argv tests |
| 12 | EVIDENCE_PACKET_SAFE_NO_SECRETS | YES | key-level: `test_evidence_packet_fields_present_and_safe` |
| 22 | EVIDENCE_OUTPUT_VALUE_REDACTED (W10) | YES | `redact_sensitive` applied to stdout/stderr/error before store; `TestEvidencePacketRedaction` proves token/code/secret/OAuth-URL values are gone, with negative control |
| 13 | CONFIG_COMMAND_FIELDS_REJECTED | YES | `assert_no_command_fields`; reject (not ignore) |
| 14 | LIVE_CONFIG_MIGRATED | YES | youtube_daemon_monitor.json fix_command/fix_commands removed; test |
| 15 | POPEN_SHELL_REMOVED | YES | check_rotation_stalls -> execute_fix(wait=False); no `subprocess.Popen` in mixin src |
| 16 | AST_CALLSITE_GUARD | YES | `TestNoShellTrueAnywhere` + `TestCallsiteGuard` |
| 17 | NO_NEW_DEPENDENCY | YES | stdlib subprocess/sys/enum/dataclasses only |
| 18 | LINE_NUMBERS_REVERIFIED_ON_MAIN | YES | Sec 2 (re-verified on 0b55b5cdd; #767 reachability corrected) |
| 19 | NO_SKIP_XFAIL | YES | new test file has no skip/xfail; added to conftest run-allowlist |
| 20 | ASCII_CLEAN | YES | audit + executor + tests are ASCII |
| 21 | NO_BEHAVIOR_REGRESSION_SAFE_FIXES | YES | Python-native fix branches untouched; allowlisted reauth/rotation still apply |

**WSP 97 Truth Boundary Checklist: 22/22 YES.**

---

*Authored by 0102 (Worker-Lane W6). Typed, allowlisted, shell=False auto-fix executor replaces the
freeform shell surface; config selects, never injects; autonomy preserved; dead duplicates removed.
Config-injection refuted by test battery + independent adversarial verification.*
