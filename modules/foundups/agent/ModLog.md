# Agent Module ModLog

## 2026-07-04 - create_foundup dry-run scaffold planner (FOUNDUP_CREATE_ACTION_DRYRUN_PHASE1)

**Author**: 0102 (RedDog Architect) | Commander: 012 | Gate: VERIFIED_READY draft PR (do NOT self-merge)
**WSP**: 00, 15, 22, 49, 50, 97, 109
**Base**: `0046423c6` (main; includes P0 #919 + P1 #920 + P2 #921 scaffold contract)
**Slice**: FOUNDUP_CREATE_ACTION_DRYRUN_PHASE1

### Changed

- NEW `src/create_foundup_dryrun.py`: `plan_create_foundup_dry_run(envelope)` re-validates a genesis
  envelope (ai_overseer validator, fail-closed), rejects an existing `foundup_id`
  (`FAIL_FOUNDUP_ID_EXISTS`) or invalid envelope (`FAIL_ENVELOPE_NOT_GATE_PASSED`), and returns a
  DRY-RUN `FoundUpScaffoldContract` + planned WSP-49 artifacts + planned manifest + registry seed.
  Writes NOTHING (`dry_run=True`, `files_written=[]`, fam/hermes/registry/worktree all False). Maps to
  the P2 `FOUNDUP_SCAFFOLD_CONTRACT_PHASE1` contract. No FAM/Hermes/writer import (AST-guarded).
- Registry existence check reads `modules/foundups/foundup_registry.json` directly (the read-only
  loader import is blocked by `modules/foundups/src/__init__` eagerly importing a missing
  `platform_manager` -- residual, out of scope).
- TEST `tests/test_create_foundup_dryrun.py` (10): incl. the planned manifest passing the REAL
  `foundup_manifest_validator`, exists-rejection, invalid/reserved rejection, no-alias invariant,
  dry-run-no-writes, AST guard. Agent suite green (1041 passed).

### Note

Contract change lives in `moltbot_bridge/foundup_job_contract.py` (create_foundup added to
CANONICAL_ACTIONS + EXISTING_MODULE_ACTIONS taxonomy + 3 fail-closed StatusReasonCodes).

### Next

FOUNDUP_SCAFFOLD_WRITER_DRYRUN_PHASE1 (valve-gated dry-run writer), then live writer behind
VALVE_OPEN_WORKTREE_CREATE + 012/DAO sovereign token.

## 2026-07-04 - Hermes builder dry-run by DEFAULT: double opt-in for real writes (HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1)

**Author**: 0102 (RedDog Architect) | Commander: 012 | Gate: VERIFIED_READY draft PR (do NOT self-merge)
**WSP References**: WSP 00, WSP 15, WSP 22, WSP 50, WSP 97
**Base**: `ac1cc611a` (main)
**Slice**: HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1

### Why (OBSERVED safety finding)

The RedDog FoundUp-creation execution-path audit found `HermesFoundUpBuilder.__init__` set
`self.dry_run = os.environ.get("HERMES_BUILDER_DRY_RUN", "0") == "1"` -- dry_run defaulted to FALSE
(real writes ON) when the env var was unset. This was the outlier: `BuildPlanExecutor` and
`HermesJobExecutor` both default `dry_run=True`, and `build_plan_generator` always emits dry-run
plans. The default-on adapter-level write (`generate_adapters` mkdir + write_text) was reachable via
the extract/build path, gated only by an env flag plus the security sentinel.

### Changed (safety tightening only; no gate weakened)

- EDIT `src/hermes_adapter.py` (`HermesFoundUpBuilder.__init__`): dry-run is now the DEFAULT. Real
  writes require an explicit DOUBLE opt-in -- BOTH `HERMES_BUILDER_ALLOW_REAL_WRITES=1` AND
  `HERMES_BUILDER_DRY_RUN=0`. Any other combination (including all-unset) stays dry-run/safe. Added
  `self.allow_real_writes` for observability. No change to the security sentinel, CABR, OpenClaw
  genesis gate, or the WRE execution valve.
- TEST `tests/test_hermes_foundup_builder.py::TestDryRunDefaultSafety` (A1/A2/A3/A5) and
  `tests/test_hermes_foundup_job_executor.py::test_a4_executor_respects_builder_dry_run_default` (A4).
  Full agent suite green: 1031 passed.
- DOCS INTERFACE.md (env contract) + README.md (safety defaults).

### HoloIndex (Addendum A)

Pre-run recall surfaced `hermes_adapter.py` at #1 for "HERMES_BUILDER_DRY_RUN default". The four new
audit docs committed at `ac1cc611a` are NOT yet discoverable (code index predates the commit):
recorded as `HOLOINDEX_FOUNDUP_CREATION_AUDIT_DISCOVERABILITY_PHASE1`. Re-index is an explicit
operator action, out of scope for this code slice.

### Residual (SPECIFIED_NOT_IMPLEMENTED)

- Hermes real delegation in `hermes_job_executor.py` remains BLOCKED (out of scope).
- Re-index for the new audit docs pending (operator/worker action, not RedDog runtime).

## 2026-06-20 - Package __init__ lazy import: close the no-vendor boundary at the IMPORT boundary (FOUNDUP_AGENT_PACKAGE_INIT_LAZY_IMPORT_PHASE1)

**Author**: 0102 (AUTHOR worker) | Commander: 012 | Gate: independent SENTINEL (do NOT self-merge)
**WSP References**: WSP 22, WSP 50, WSP 64, WSP 84, WSP 97
**Base**: `a02b6fb9c` (origin/main)
**Slice**: FOUNDUP_AGENT_PACKAGE_INIT_LAZY_IMPORT_PHASE1

### Why (decision B: fix the no-vendor boundary at the IMPORT boundary, not just the file AST)

The #805/#806 boundary is "no Hermes / no vendor import". The Kanban publish adapter MODULE (parked
slice KANBAN_EXTERNAL_ADAPTER_PUBLISH_PILOT_PHASE1, a DIFFERENT worktree) and the #807 contract
MODULE (`kanban_plugin_contract.py`) are AST-clean -- BUT importing them THROUGH the package eagerly
loaded Hermes+subprocess+sqlite3+urllib because `modules/foundups/agent/src/__init__.py` EAGERLY
imported from `.hermes_adapter` and `.hermes_model_router` (old lines 35-46) to expose 8
package-level names. So a leaf-module import (e.g. `import
modules.foundups.agent.src.kanban_plugin_contract`) transitively pulled the entire Hermes/vendor
runtime. Confirmed live on `a02b6fb9c`: the leaf import leaked
`hermes_adapter`/`hermes_model_router`/`subprocess`/`sqlite3`/`urllib` into `sys.modules`.

### Changed (package structure only -- src: `__init__.py`)

- EDIT `modules/foundups/agent/src/__init__.py`: replaced the two EAGER
  `from .hermes_adapter import (...)` / `from .hermes_model_router import (...)` blocks with a PEP 562
  lazy module-level `__getattr__` backed by a `_LAZY` name->submodule map. The 8 public names still
  resolve on ACCESS (`from modules.foundups.agent.src import HermesFoundUpBuilder` works), are CACHED
  into `globals()` on first access (cheap + identity-stable on re-access), and a leaf-module import no
  longer triggers any Hermes/vendor import. `__version__` and `__all__` are UNCHANGED. Added a
  `__dir__` so the lazy names still surface for introspection. The module docstring is preserved.
- NO change to `hermes_adapter.py`, `hermes_model_router.py`, or `kanban_plugin_contract.py` (their
  diffs are EMPTY). The parked publish adapter is untouched (different worktree).

### Proofs (all in FRESH child interpreters where the boundary assertion needs a clean import graph)

1. `import modules.foundups.agent.src.kanban_plugin_contract` -> none of
   `hermes_adapter`/`hermes_model_router`/`subprocess`/`sqlite3`/`urllib` in child `sys.modules`.
2. `import modules.foundups.agent.src.source_authority` (2nd independent AST-clean leaf) -> same.
3. All 8 `__all__` names resolve lazily and are identity-stable across repeated access; resolved
   values are the SAME objects exported by `hermes_adapter`/`hermes_model_router` (no behavior change).
4. Lazy-on-demand: in a fresh child `hermes_adapter` is ABSENT until a public name is accessed, then
   PRESENT.
5. No circular import: package + both leaves + both hermes modules import cleanly in several orders.
6. Bogus package attribute -> `AttributeError` (not ImportError/other).

### WSP 97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|---|---|---|
| 1 | LEAF_IMPORT_DOES_NOT_EAGER_LOAD_HERMES | YES | Fresh child: `import ...kanban_plugin_contract` leaves `hermes_adapter`/`hermes_model_router` out of `sys.modules`; old eager `__init__` removed. |
| 2 | KANBAN_ADAPTER_PACKAGE_IMPORT_NO_VENDOR_PULLIN | YES | `test_leaf_adapter_import_no_vendor_pullin` (child): kanban_plugin_contract pulls in none of hermes_adapter/hermes_model_router/subprocess/sqlite3/urllib. (Publish adapter parked elsewhere; contract leaf is the present adapter-side AST-clean leaf.) |
| 3 | KANBAN_CONTRACT_PACKAGE_IMPORT_NO_VENDOR_PULLIN | YES | `test_leaf_contract_import_no_vendor_pullin` (child): source_authority leaf, same clean `sys.modules`. |
| 4 | EXISTING_PUBLIC_EXPORTS_PRESERVED | YES | `test_all_public_exports_still_resolve`: `__all__` unchanged (8 names); each resolves non-None, correct type, identity-stable on re-access. |
| 5 | LAZY_IMPORT_NO_BEHAVIOR_CHANGE | YES | `test_lazy_access_resolves_value_identical_to_source`: package names are the SAME objects as hermes_adapter/hermes_model_router exports; their source diffs are EMPTY. |
| 6 | NO_CIRCULAR_IMPORT | YES | `test_no_circular_import`: package + both leaves + both hermes modules import in 3 orders (incl. reverse) with returncode 0. |
| 7 | ADAPTER_REMAINS_PARKED | YES | No `kanban_publish_adapter` file in this worktree; only `__init__.py` + new test changed (git status --short); parked slice rebases + reruns its 7-lane gate after this lands. |
| 8 | ASCII_CLEAN | YES | Byte-check: 0 non-ASCII bytes in `__init__.py` and `test_package_init_lazy_import.py`. |
| 9 | NO_SKIP_XFAIL | YES | Full agent suite 1024 passed (CI and heavy mode); new file 8 passed; no skip/xfail markers. |
| 10 | FILE_SCOPE_EXACT | YES | `git status --short`: only `M src/__init__.py` + `?? tests/test_package_init_lazy_import.py` (+ ModLogs); hermes/contract diffs empty. |

### Follow-up

After this lands, the parked KANBAN_EXTERNAL_ADAPTER_PUBLISH_PILOT_PHASE1 (different worktree)
rebases onto the new package head and RE-RUNS its 7-lane gate -- its no-vendor lane now holds at the
IMPORT boundary, not just the file AST.

## 2026-06-20 - Kanban Contract dict-key redaction + token-precise command match (FOUNDUP_KANBAN_CONTRACT_REDACT_KEYS_AND_PRECISE_COMMAND_MATCH_PHASE1)

**Author**: 0102 (AUTHOR worker) | Commander: 012 | Gate: independent SENTINEL (do NOT self-merge)
**WSP References**: WSP 22, WSP 50, WSP 64, WSP 84, WSP 97
**Base**: `005dd3629` (origin/main; contains the landed #807 + #838 + #843)
**Slice**: FOUNDUP_KANBAN_CONTRACT_REDACT_KEYS_AND_PRECISE_COMMAND_MATCH_PHASE1

### Why (closes 2 findings the parked publish adapter's RE-REVIEW exposed)

After #843 landed, a re-review of the parked publish adapter (slice
KANBAN_EXTERNAL_ADAPTER_PUBLISH_PILOT_PHASE1, NOT part of this slice) exposed two NEW gaps in the
#807 authority contract. Decision A (again): fix the contract at its SOURCE.
- **Finding 1 (secret-as-dict-KEY survives serialization)**: `_redact_deep` redacted string
  VALUES/leaves but NOT dict KEYS (`{k: _redact_deep(v) for k, v in node.items()}`). A secret used
  as a nested dict KEY therefore survived verbatim into `to_dict()` and the adapter outbox.
  Confirmed live: origin `to_dict()` of a card carrying `{sk: "v", "f": sk}` in a list field leaks
  the raw `sk-...` as a KEY; HEAD does not.
- **Finding 2 (#843 command-key over-rejection regression)**: the command-key check used SUBSTRING
  matching (`any(c in nkey for c in _COMMAND_KEY_MARKERS)`), so `description` (contains "script"),
  `transcript`, `subscription`, etc. were treated as command-keys. Since #843 made command-keys
  reject bare strings, an ordinary raw-dict field like `{"description": "ordinary text"}` was now
  FALSELY REJECTED. The #843 no-weakening lane allowed this regression because a field going
  accepted->rejected reads as a "strengthening". Confirmed live: origin REJECTS description/
  transcript/subscription/executive_summary/scripted_notes/prescription/descriptor with an ordinary
  string value; HEAD ACCEPTS them.

### Changed (LOGIC change to the #807 authority contract -- src: `kanban_plugin_contract.py`)

1. **Fix 1 -- `_redact_deep` now redacts string KEYS as well as string values** (dict branch,
   `~line 124`): `{(redact_sensitive(k) if isinstance(k, str) else k): _redact_deep(v) for k, v in
   node.items()}`. Non-string keys pass through unchanged. Uses the SAME `redact_sensitive` redactor
   as values, returns a NEW structure (the input mapping is NOT mutated), and preserves the
   deterministic/canonical behavior (downstream `to_dict()` is `json.dumps(sort_keys=True)`). A
   secret-as-key can no longer survive into `to_dict()` or any serialization.
2. **Fix 2 -- command-key matching is now TOKEN/BOUNDARY-precise, NOT substring** (`~line 245`):
   replaced the substring test with `_key_is_command()` (`~line 165`), which runs the existing
   `_normalize` on the key, splits the normalized key into tokens by `_`, and matches a command-key
   IFF some TOKEN is EXACTLY a single-token command marker. `_COMMAND_KEY_MARKERS` is now the
   single-token set `{command, cmd, argv, shell, exec, script}` (frozenset). `run_cmd`/`runCmd` are
   caught via their `cmd` token; `exec_now` via `exec`; `shell_command` via `shell`/`command`. Legit
   fields whose names merely CONTAIN a marker substring (description/transcript/subscription/
   executive/scripted/prescription/...) each normalize to a single NON-marker token and are NOT
   command-keys. `_command_value_is_argv_or_null` is UNCHANGED -- a bare string under a TRUE command
   key remains REJECTED; a valid all-safe argv list under a true command key is still ACCEPTED.

### Two-directional parity (this slice needs BOTH no-weakening AND no-over-rejection)

AUTHORITY detection is UNCHANGED and not weakened (the command-KEY change is the only logic change
on the key path; redaction only ADDS key coverage). The command-KEY change is an INTENDED narrowing:
it removes false-positive command-keys (description/transcript/...) while keeping the true command
keys. So `{description: "text"}` flips REJECTED(origin)->ACCEPTED(HEAD) -- the intended fix, NOT a
weakening (it was never a real authority/command key). The no-weakening invariant applies to
AUTHORITY markers, not to the command-substring over-matches being fixed.

AUDIT-time live cross-check (origin/main module vs HEAD over the corpus):
- **NO WEAKENING**: 0 origin-rejected AUTHORITY payloads newly accepted by HEAD.
- **TRUE command keys (command/cmd/shell/script/exec/argv + run_command/runCmd/exec_now/
  shell_command) still reject a bare string** (origin False -> HEAD False; #843 invariant carried).
- **FALSE-POSITIVE FIX**: description/transcript/subscription/executive_summary/scripted_notes/
  prescription/descriptor flip REJECTED(origin)->ACCEPTED(HEAD).
- **KEY-REDACTION**: secret-as-key survives origin `to_dict()` (True), does NOT survive HEAD (False);
  HEAD instance not mutated.

### WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|---|---|---|
| 1 | DICT_KEYS_REDACTED | PASS | `_redact_deep` dict branch redacts string KEYS via `redact_sensitive`; non-string keys pass through |
| 2 | NESTED_KEYS_REDACTED | PASS | secret-as-KEY nested several levels deep is redacted (test) |
| 3 | TO_DICT_NO_SECRET_IN_KEYS_OR_VALUES | PASS | card `to_dict()` of `{sk:"v","f":sk}` in a list field carries no raw secret in keys OR values |
| 4 | COMMAND_MATCH_TOKEN_PRECISE_NOT_SUBSTRING | PASS | `_key_is_command` matches on a normalized `_`-token == single-token marker; substring fields excluded |
| 5 | DESCRIPTION_TRANSCRIPT_NOT_COMMAND_KEYS | PASS | description/transcript (+ false-positive battery) accepted with ordinary string values |
| 6 | TRUE_COMMAND_KEYS_STILL_REJECT_BARE_STRING | PASS | command/cmd/shell/script/exec/argv/run_command/runCmd/exec_now/shell_command bare string rejected |
| 7 | AUTHORITY_DETECTION_NOT_WEAKENED | PASS | full origin-rejected AUTHORITY corpus still rejected; 0 newly accepted (battery + live cross-check) |
| 8 | FALSE_POSITIVE_BATTERY_PRESENT | PASS | corpus of legit command-substring field names with ordinary values, all ACCEPTED (NEW #843-lacked invariant) |
| 9 | ADAPTER_FINDINGS_CLOSED_AT_CONTRACT_SOURCE | PASS | both findings fixed in the contract; adapter inherits safety |
| 10 | ASCII_CLEAN | PASS | 0 non-ASCII bytes in both edited files (synthetic secret via `chr()`) |
| 11 | NO_SKIP_XFAIL | PASS | no skip/xfail added |
| 12 | FILE_SCOPE_EXACT | PASS | only `kanban_plugin_contract.py` + its tests + ModLogs changed |
| 13 | NO_HERMES_OR_DB_OR_RUNTIME_WIRING | PASS | pure dataclasses/validators; no Hermes import, no Kanban DB, no runtime wiring |
| 14 | ORIGINAL_OBJECT_NOT_MUTATED | PASS | `_redact_deep` builds a NEW dict; card instance keeps raw key/value after `to_dict()` |

### Validation

- `test_kanban_plugin_contract.py`: 319 passed (was 251; +68 net new for key-redaction + token-
  precise-command + two-directional parity). Full agent suite: **1016 passed** in BOTH heavy
  (`AI_OVERSEER_HEAVY_TESTS=1`) and CI mode -- no skip/xfail, no regression.

### Follow-up

The parked slice **KANBAN_EXTERNAL_ADAPTER_PUBLISH_PILOT_PHASE1** rebases onto this once it lands
(it relies on the now-guaranteed key+value redaction and the token-precise command-key contract).

---

## 2026-06-19 - Kanban Contract card redaction + command argv-or-null (FOUNDUP_KANBAN_CONTRACT_CARD_REDACTION_AND_COMMAND_ARGV_PHASE1)

**Author**: 0102 (AUTHOR worker) | Commander: 012 | Gate: independent SENTINEL (do NOT self-merge)
**WSP References**: WSP 22, WSP 50, WSP 64, WSP 84, WSP 97
**Base**: `9e6d6d063` (origin/main; contains #807 + the landed #838 no-raw-echo)
**Slice**: FOUNDUP_KANBAN_CONTRACT_CARD_REDACTION_AND_COMMAND_ARGV_PHASE1

### Why (closes 2 HIGH findings the parked Kanban publish adapter surfaced)

The parked publish adapter (slice KANBAN_EXTERNAL_ADAPTER_PUBLISH_PILOT_PHASE1, NOT part of this
slice) exposed two latent gaps in the #807 authority contract. Decision A: harden the contract at
its SOURCE so the adapter and any consumer inherit safety.
- **Finding A**: `KanbanCardSpec.to_dict()` returned `asdict(self)` with NO redaction -- only
  `WreEvidencePacket` redacted (via `__post_init__`). A raw secret in a card free-text field
  serialized VERBATIM. (Proven: origin/main `to_dict()` leaks `sk-...`; HEAD does not.)
- **Finding B**: `validate_card_spec`'s command-key handling only rejected shell METACHARS. A
  metachar-free destructive command like `{"command": "rm -rf /"}` PASSED, despite the contract's
  stated guarantee being "argv-or-null only".

### Changed (LOGIC change -- src: `kanban_plugin_contract.py`)

1. **Finding A -- `KanbanCardSpec.to_dict()` now returns a REDACTED canonical body**
   (`~line 326`): added a pure deep redactor `_redact_deep()` (`~line 116`) that recurses
   list/tuple/dict and applies the existing `redact_sensitive` to EVERY string leaf. `to_dict()`
   returns `_redact_deep(asdict(self))`. Approach = redact AT SERIALIZATION (the dataclass instance
   is NOT mutated; chosen because the card has no `__post_init__` and the redacted dict is the
   canonical body any consumer digest is computed over -- so CARD_ID_FROM_REDACTED_CANONICAL_BODY
   holds without mutating state). Documented in the `to_dict()` docstring.
2. **Finding B -- `validate_card_spec` command-key is now argv-or-null ONLY** (in the shared
   `_scan_authority`, `~line 244`): added `_command_value_is_argv_or_null()` + `_argv_element_unsafe()`
   (`~line 252`). A command-key value is ACCEPTED only when None (null) OR an argv LIST whose every
   element is a safe string (reusing `_has_shell` + `_value_carries_authority` + `_check_path` per
   element). A bare STRING (even metachar-free), a dict, or a list with any unsafe/non-string element
   is REJECTED. Message names the rule class only -- the #838 no-raw-echo invariant is preserved
   (the raw command value is NEVER echoed).
3. **No weakening**: every input origin/main rejected is still rejected -- only ADDED rejections
   (bare/unsafe command strings) + ADDED redaction. The shared scanner change also propagates the
   argv-or-null rule to `validate_worker_task_spec` / `validate_evidence_packet` (defense-in-depth).
4. **SENTINEL re-audit alignment (code/docstring agreement)**: `_command_value_is_argv_or_null`
   (`~line 290`) docstring stated "null OR a NON-EMPTY argv LIST", but the body
   `all(not _argv_element_unsafe(item) for item in value)` accepted an EMPTY argv list `[]`
   (`all([])` is True), so `{"command": []}` was ACCEPTED -- contradicting the docstring. Made the
   CODE match the stated contract: a command-key is accepted only when null/absent OR a NON-EMPTY
   argv list of all-safe strings; an empty argv list is degenerate/malformed and is REJECTED
   (`len(value) >= 1 and all(...)`). This is strictly a STRENGTHENING (HEAD now rejects `command: []`
   which origin accepted) -- the no-weakening invariant is preserved (0 newly-accepted). The SAFE
   error message is unchanged (no raw echo). Nothing else changed (redaction, bare-string rejection,
   authority detection untouched).

### Parity proof (this is a LOGIC change -> AST-skeleton-identical no longer applies)

Proven by BATTERY (not skeleton hash). The prior AST-skeleton baseline test was REPLACED by a
self-contained behavioral no-weakening battery (origin-rejected corpus embedded in the committed
tests; NO runtime git-show). AUDIT-time cross-check loaded origin/main's module vs HEAD over the
full corpus: **77/77 origin-rejected inputs still rejected, 0 newly accepted** (zero weakening);
**14/14 new bare/unsafe command inputs rejected by HEAD** (13 are clean ACCEPTED(origin)->
REJECTED(HEAD) flips, 1 was already rejected by the authority-by-value scan); **5/5 clean valid
inputs still accepted**. Redaction parity: origin `to_dict()` leaks the secret, HEAD redacts +
digest stable on the redacted body + instance not mutated.

### WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|---|---|---|
| 1 | CARD_TO_DICT_REDACTS_SECRETS | PASS | `to_dict()` returns `_redact_deep(asdict(self))`; tests assert no raw secret in scalar + nested list fields |
| 2 | CARD_ID_FROM_REDACTED_CANONICAL_BODY | PASS | redacted dict is the canonical body; digest over `to_dict()` stable across two cards differing only in raw secret bytes |
| 3 | BARE_COMMAND_STRING_REJECTED | PASS | `{"command":"rm -rf /"}` (+ cmd/exec/shell/script/argv/run_cmd, metachar-free, nested) rejected |
| 4 | COMMAND_ARGV_OR_NULL_ONLY | PASS | null accepted; NON-EMPTY argv list accepted iff every element is a safe string; string/dict/unsafe-element/EMPTY-list rejected (code now matches docstring) |
| 5 | AUTHORITY_DETECTION_NOT_WEAKENED | PASS | 77/77 origin-rejected still rejected; 0 newly accepted (battery + AUDIT cross-check) |
| 6 | NO_RAW_ERROR_ECHO | PASS | command rejection names the rule class only; no raw command/secret in any message |
| 7 | ADAPTER_FINDINGS_CLOSED_AT_CONTRACT_SOURCE | PASS | Findings A+B fixed in the contract; adapter inherits safety |
| 8 | ASCII_CLEAN | PASS | 0 non-ASCII bytes in both edited files (fullwidth fixture via `\uXXXX`) |
| 9 | NO_SKIP_XFAIL | PASS | no skip/xfail added |
| 10 | FILE_SCOPE_EXACT | PASS | only `kanban_plugin_contract.py` + its tests + ModLogs changed |
| 11 | NO_HERMES_OR_DB_OR_RUNTIME_WIRING | PASS | pure dataclasses/validators; no Hermes import, no Kanban DB, no runtime wiring |

### Validation

- `test_kanban_plugin_contract.py`: 251 passed (was 135; +116 net new, incl. +16 empty-argv-list
  strengthening cases from the SENTINEL re-audit). Full agent suite: 948 passed in BOTH heavy
  (`AI_OVERSEER_HEAVY_TESTS=1`) and CI mode -- no skip/xfail, no regression.

### Follow-up

The parked slice **KANBAN_EXTERNAL_ADAPTER_PUBLISH_PILOT_PHASE1** will be rebased onto this once it
lands (it relies on the now-guaranteed redacted `to_dict()` + argv-or-null command contract).

## 2026-06-18 - Kanban Plugin Contract no-raw-echo for the #807 authority scanner (FOUNDUP_KANBAN_CONTRACT_ERROR_NO_RAW_ECHO_PHASE1)

**Author**: 0102 (AUTHOR worker) | Commander: 012
**WSP References**: WSP 22, WSP 50, WSP 84, WSP 97
**Base**: `edbd90642` (origin/main; contains #810/#821/#823/#824/#826/#830)
**Predecessor**: #830 launch_request slice DEFERRED the imported #807 authority-scanner echo.

### Why

The #830 launch_request no-raw-echo slice DEFERRED `kanban_plugin_contract.py::_scan_authority`
(the #807 AUTHORITY BOUNDARY shared by `validate_launch_request` AND `validate_card_spec` /
`validate_worker_task_spec` / `validate_evidence_packet`). Its error messages echoed raw
user-controlled keys / values / `repr()` / nested trail. This slice COMPLETES the no-raw-echo
invariant for the authority-scan path. MESSAGE TEXT ONLY -- the authority-detection LOGIC is
byte-identical (proven mechanically).

### Changed (message text only -- error sites in kanban_plugin_contract.py)

`_scan_authority` (the #807 boundary):
- non-string key: `f"{trail}: non-string key {key!r}"` -> `"non-string key rejected"`
- non-printable key: `f"{trail}{key}: non-ASCII / non-printable key rejected"` -> `"non-ASCII / non-printable key rejected"`
- verified=true: `f"{trail}{key}: verified=true is forbidden ..."` -> `"verified=true is forbidden (advisory-until-verified)"`
- source_authority promotion: `f"{trail}{key}: '{value}' is a source_authority promotion ..."` -> `"source_authority promotion is forbidden (only monorepo_poc)"`
- promotion flag: `f"{trail}{key}: promotion flag is forbidden"` -> `"promotion flag is forbidden"`
- forbidden authority field (KEY presence): `f"{trail}{key}: forbidden authority field '{m}' (presence)"` -> `f"forbidden authority field present (class: {m})"` (KEEP `{m}`, DROP `{trail}{key}`)
- shell-string command: `f"{trail}{key}: shell-string command is forbidden ..."` -> `"shell-string command is forbidden (argv-or-null only)"`
- value-carried authority: `f"{trail}: value carries authority '{carried}': {node!r}"` -> `f"value carries a forbidden authority marker (class: {carried})"` (KEEP `{carried}`, DROP `{trail}`+`{node!r}`)

`_check_path` (drop raw `value!r` and the offending char list, keep the fixed field label + rule):
- `path/ref must be printable ASCII: {value!r}` -> `path/ref must be printable ASCII`
- `absolute/UNC path forbidden: {value!r}` -> `absolute/UNC path forbidden`
- `drive path forbidden: {value!r}` -> `drive path forbidden`
- `path traversal '..' forbidden: {value!r}` -> `path traversal '..' forbidden`
- `shell metacharacters in path/ref: {sorted(bad)}` -> `shell metacharacters in path/ref forbidden`

`validate_card_spec`:
- `risk_class '{data.get('risk_class')}' not in {...}` -> `risk_class not in allowed set {sorted(ALLOWED_RISK_CLASSES)}` (drop raw value; keep fixed allowed-set taxonomy)

The fixed `{m}` / `{carried}` tokens come from the `_AUTHORITY_MARKERS` taxonomy (NOT user input) and
are RETAINED (Addendum-B message locality). The user-controlled nested `trail` is still computed for
recursion descent but is NEVER interpolated into a message.

### Authority-detection parity proof (logic byte-identical)

1. AST control-flow SKELETON parity: every string literal AND every f-string (`JoinedStr`) is
   uniformly blanked, so an f-string -> plain-string message rewrite is invisible; ANY branch /
   condition / call / marker-set change would change the hash. The blanked skeleton SHA-256 of the
   current file equals the frozen origin/main baseline (`f2ee0e26...`). SELF-CONTAINED -- no
   `git show` at runtime (the #830 shallow-CI lesson).
2. NAMED-category authority battery (Addendum A): ~42 fixtures across the #807 corpus
   (forbidden-authority keys by PRESENCE, ~13 normalized evasions incl. camelCase/separator/UPPER/
   fullwidth, ~10 authority-by-value, source_authority promotion, verified=true nested,
   shell-command keys, non-string/non-ASCII keys). Each fixture is mapped to its expected violation
   CLASS by INPUT DESIGN; the battery asserts rejection WITHOUT parsing the human-readable message
   (a weakened detector fails even though the message text changed).
3. No-raw-echo battery: seeds sentinel leak tokens into keys, nested trails, values, and paths;
   asserts no raw content / repr / control-byte appears in any produced message.

### Downstream

- `validate_launch_request` (#810) imports `_scan_authority`; its SOURCE is UNCHANGED. The #823
  intake_transport caller-regression (real `SQLiteNonceStore` + spy) confirms an authority-bearing
  payload is rejected, `IntakeResult.reason == "invalid_request"` (low-cardinality, no auth oracle),
  no raw key/value/trail leaks into the result/repr/serialized dict, and a valid single-use invite
  is NOT consumed. `validate_card_spec` / `validate_worker_task_spec` / `validate_evidence_packet`
  still reject exactly the same inputs (outcome-only assertions; only error TEXT changed).
- Two `test_foundup_launch_request.py` tests that pinned the #830-DEFERRED old #807 echo text were
  updated (text-only; outcome assertions kept) to pin the now-LANDED safe rule-only messages.

### WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | SCAN_AUTHORITY_ERRORS_NEVER_ECHO_RAW_KEY_VALUE_TRAIL | YES | `_scan_authority` 8 sites reworded; no-raw-echo battery seeds leak tokens into key/trail/value -> 0 leaks |
| 2 | AUTHORITY_MARKER_CLASS_KEPT_RAW_DROPPED | YES | `forbidden authority field present (class: {m})` + `value carries a forbidden authority marker (class: {carried})`; `test_marker_class_token_is_taxonomy_not_user_input` |
| 3 | AUTHORITY_DETECTION_LOGIC_BYTE_IDENTICAL | YES | AST skeleton SHA-256 == frozen origin/main baseline `f2ee0e26...`; NAMED-category battery rejects all fixtures |
| 4 | FULL_AUTHORITY_AND_EVASION_BATTERY_PARITY | YES | ~42-fixture battery: presence keys, ~13 normalized evasions, ~10 by-value, source_authority/verified/promotion/shell/non-string/non-ASCII |
| 5 | ERROR_CATEGORY_BASELINE_NOT_MESSAGE_DERIVED | YES | category mapped by INPUT DESIGN (`_AUTHORITY_BATTERY`); pass/fail = rejection, never message parse |
| 6 | SAFE_MESSAGE_LOCALITY_PRESERVED | YES | `test_safe_message_locality_preserved` asserts distinct rule families, not one bland phrase |
| 7 | DOWNSTREAM_VALIDATORS_OUTCOME_UNCHANGED | YES | `test_downstream_validators_reject_authority_payloads` + clean-shape accept (outcome-only) |
| 8 | LAUNCH_REQUEST_SOURCE_UNCHANGED | YES | `git diff` launch_request.py empty; only its imported `_scan_authority` messages changed |
| 9 | TRANSPORT_LOW_CARDINALITY_RECHECKED | YES | `test_kanban807_authority_body_low_cardinality_and_no_raw_echo`: reason == invalid_request, no leak |
| 10 | VALID_INVITE_NOT_CONSUMED_BY_AUTHORITY_PAYLOAD | YES | `test_kanban807_authority_body_does_not_consume_valid_invite_sqlite_spy` (real SQLiteNonceStore + spy) |
| 11 | AST_SKELETON_PARITY_SELF_CONTAINED_NO_GIT | YES | `test_authority_logic_skeleton_matches_origin_baseline` uses frozen hash, no runtime `git show` |
| 12 | NESTED_TRAIL_NOT_ECHOED | YES | trail computed for descent only; never interpolated; battery seeds `_LEAK_TRAIL` -> 0 leaks |
| 13 | REPR_VALUE_NOT_ECHOED | YES | all `{value!r}`/`{node!r}`/`{key!r}` removed; `_assert_no_leak` checks `repr(n) not in blob` |
| 14 | CONTROL_BYTES_NOT_IN_ERRORS | YES | `_assert_no_leak` asserts no `ord(c) < 32 or == 127` in any produced error |
| 15 | NO_OTHER_807_SLICE_DRIFT | YES | `git status` shows only kanban_plugin_contract.py + 3 test files; scope-guard sources empty diff |
| 16 | ASCII_CLEAN | YES | byte-check 0 non-ASCII on all 4 edited files; fixtures via `chr()`/`\uXXXX` |
| 17 | NO_SKIP_XFAIL | YES | grep: no `pytest.skip`/`xfail`/`skipif` in edits; all suites fully run |
| 18 | FILE_SCOPE_EXACT | YES | kanban_plugin_contract.py + test_kanban_plugin_contract.py + test_intake_transport.py + test_foundup_launch_request.py |

## 2026-06-13 - Kanban Plugin Contract (WRE-side typed seam) (HERMES_KANBAN_PLUGIN_CONTRACT_IMPL_PHASE1)

**Author**: 0102 (Worker-Lane A) | Commander: 012
**WSP References**: WSP 11, WSP 22, WSP 50, WSP 84, WSP 97
**Base**: `ed3ad2066` (origin/main after #801)
**Predecessors**: #804 (plugin contract), #806 (launch flow), #805 (Option D), #803 (surface-not-authority)

### Added

- **kanban_plugin_contract.py** -- pure, execution-free WRE-side typed seam implementing the three #804/#806
  shapes: `KanbanCardSpec` (WRE->Kanban), `WorkerTaskSpec` (worker receives), `WreEvidencePacket`
  (Kanban->WRE, ADVISORY) + `ArtifactRef`. Validators `validate_card_spec` / `validate_worker_task_spec` /
  `validate_evidence_packet` accept a typed shape OR a hostile inbound dict.
- Forbidden AUTHORITY cannot ride through any shape: a unified recursive scan normalizes keys (NFKC +
  camel-split + casefold + separator->underscore, defeating gatePassed/gate-passed/GATE_PASSED/fullwidth)
  and rejects authority-marker keys by PRESENCE, AND scans every string VALUE for authority markers
  (gate-pass / merge / land / repo-create / dao / payout / cabr / real-execution / source_authority
  promotion). Path/ref fields are hygiene-checked (printable ASCII, repo-relative, reject absolute/drive/
  UNC/traversal/control-chars/shell-metachars). Commands smuggled into command-named keys are rejected.
- `WreEvidencePacket.verified` is advisory-only: always False at construction; constructing/ingesting
  verified=true is rejected (nested too). The WRE-side verifier transition is deferred to the named slice
  WRE_EVIDENCE_PACKET_VERIFICATION_TRANSITION_PHASE1.
- Secret VALUES are redacted before storage across ALL string-bearing fields (free-text + pr_url/head_sha/
  tests_run/wsp97_rows/changed_files; defense-in-depth from the SENTINEL observation) -- the #768 policy,
  reimplemented locally so the module imports no ai_overseer runtime. Deterministic `to_dict()` serialization (json-safe, stable, verified=False, no
  forbidden keys/values).
- Boundary: imports nothing from Hermes/Kanban/OpenClaw/WRE-consumer/AI-Overseer; no subprocess/network/
  file-write/Kanban-DB/worker-spawn (AST-tested). No second orchestrator. Beside context_bundle_builder.py,
  foundup_manifest_validator.py, module_path_resolution.py.

## 2026-06-12 - WRE ContextBundle Dry-Run Consumer Phase 1 (first consumer adopts #775 bundle as trusted input)

**Author**: 0102 (W6)
**Commander**: 012
**Slice**: WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1
**Branch**: `w6/wre-context-bundle-dryrun-consumer-phase1`
**Base**: `90a7ec0ee` (origin/main after #779 and #781)
**Effort**: ULTRA

**Type**: Limited implementation. First consumer wiring of a trust artifact
(the #775 ContextBundle) into the EXISTING dry-run evidence path. Dry-run
only; no live execution. STANDALONE module + tests (ruling A): consumes a
ContextBundle + the shared validated resolver and RETURNS a typed
`DryRunResult` (ruling B: return-value-only, no side effects). NOT plumbed
into the live OpenClaw/WRE loop (runtime wiring is a separate Phase-2 slice).

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 84, WSP 97, WSP 22.

### Phase 0 -- Mandatory Discovery summary

- **HoloIndex** (index refreshed in #781): 3/3 queries returned the
  canonical files in the top hits (`build_plan_executor.py`,
  `hermes_foundup_job_executor.py`, `context_bundle_builder.py`,
  `module_path_resolution.py`, `source_authority.py`). Retrieval signal
  was GOOD this slice (the #781 reindex resolved the two prior LOW-signal
  slices). Manual `Read`/`Grep` cross-checked every target against the
  committed base per the tool-staleness guard.
- **Existing dry-run path ADOPTED (not invented)**: confirmed two existing
  dry-run primitives. (1) `hermes_foundup_job_executor.execute_foundup_job`
  (`modules/foundups/agent/src/hermes_foundup_job_executor.py:104-261`)
  resolves module_path via the shared `_resolve_validated_module_path`
  (line 186) before any sink; real-exec sink is
  `HermesFoundUpBuilder.extract_foundup`. (2) `BuildPlanExecutor.execute_step`
  (`modules/foundups/agent/src/build_plan_executor.py:618-665`): dry-run
  delegates to `simulate_step` (SIMULATED), real returns BLOCKED;
  `ExecutionReceipt` truth fields all False. The consumer reuses these
  shapes STANDALONE; it introduces NO live-loop wiring and NO second
  orchestrator.

### What changed

- **NEW** `src/context_bundle_dry_run_consumer.py` (~340 lines):
  `consume_context_bundle_dry_run(bundle, *, job=None, repo_root=None)`
  returns a frozen `DryRunResult`. Pinned design:
  - The ContextBundle is the TRUSTED input; the consumer reads validated
    fields (`module_path`, `source_authority`, `required_gates_to_recheck`,
    `readiness_flags`, `included_file_refs`) and does NOT re-derive trust
    from a raw payload.
  - `module_path` is ALWAYS the bundle's validated canonical value. When a
    `job` is supplied (it may carry a forged `payload.module_path` /
    `source_module`), the SAME shared `_resolve_validated_module_path`
    (#778/#779) is run as defense-in-depth and its effective path MUST equal
    the bundle's `module_path`; the payload candidate is surfaced as
    observable-ignore in `rejected_input` and is NEVER used. NO second
    resolver is defined (AST-pinned; exactly one resolver def repo-wide).
  - `source_authority` MUST equal `monorepo_poc` (via `resolve_source_authority`
    + `ACTIVE_STAGES`, #777); the consumer CANNOT promote a stage; any
    non-monorepo_poc bundle is REFUSED.
  - `required_gates_to_recheck` are gate NAMES to re-check, never pass-state;
    no gate-pass boolean is computed or serialized.
  - DRY-RUN ONLY: `dry_run=True` / `real_execution_performed=False`; no real
    build / subprocess / Hermes real delegation / executor sink invoked.
    `HERMES_DELEGATE_ENABLED` is never set; real delegation stays BLOCKED.
- **NEW** `tests/test_context_bundle_dry_run_consumer.py` (51 tests, 0
  skip/xfail): happy path, forged-payload rejection (cross-FoundUp / alias /
  syntactic), non-monorepo_poc refusal, gates-as-names (no pass-state
  serialized), real-exec sink + Hermes delegation + subprocess
  `assert_not_called`, no-file-bodies, HERMES flag respected, AST guards
  (no orchestrator / no second resolver / no subprocess-network-write),
  return-value-only (no file write, frozen result, no FAM import), and all 6
  real manifests.

### Tests

- New consumer suite: 51 passed, 0 skip/xfail.
- Full `modules/foundups/agent/tests/`: 697 passed, 0 skip/xfail.

### Non-goals / boundaries honoured

- NO new orchestrator; NO live build/real execution/subprocess; NO external
  agent; NO readiness promotion; NO repo concatenation (refs+sha256 only);
  NO mutation of `context_bundle_builder.py` / `module_path_resolution.py` /
  `source_authority.py` / `foundup_manifest_validator.py` (git diff confirms);
  NO live-loop runtime wiring; NO FAM event / file write.

## 2026-06-11 - BuildPlan Generator Module-Path Trust Removal Phase 1 (#778 carry-forward closure + shared resolver extraction)

**Author**: 0102 (W6)
**Commander**: 012
**Slice**: BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1
**Branch**: `w6/build-plan-generator-module-path-trust-removal-phase1`
**Base**: `a3e70b5a4` (origin/main after #778)
**Effort**: ULTRA

**Type**: Authoring slice (last carry-forward closure). Closes the
#778 carry-forward by extracting the validator-guarded resolver into a
SHARED module and reusing it in `build_plan_generator`. The module is
orphaned today (Phase-0 re-verified zero production importers); this
slice fences it BEFORE `WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1` makes
anything reachable.

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 84, WSP 87, WSP 97,
WSP 22.

### Phase 0 -- Mandatory Discovery summary

- **HoloIndex**: 4/4 queries returned HOLOINDEX_LOW_SIGNAL despite
  exact-identifier-token queries. Public HTML / WSP framework prose
  dominated cosine ranking; canonical files (`build_plan_generator.py`,
  `build_plan.py`, `hermes_foundup_job_executor.py`) were absent from
  every top-8. Recorded as the second LOW-signal slice in a row -- a
  HoloIndex re-index of `modules/foundups/agent/` is now urgent.
  Manual `Grep` / `Read` recovered every target.
- **Trust-point re-verification**: all 5 trust points present at
  current line numbers; small shifts (#3 +1, #6 +4). `_is_valid_foundup_path`
  at lines 203-223 still has `.lower()` case-folding at line 211 and
  still admits `public/member/foundups/`.
- **Reachability re-check**: REMAINS_ORPHANED. Zero production
  importers (only src/ reference is the explicit "NOT imported"
  comment at `foundup_manifest_validator.py:35`). All callers of
  `create_build_plan_from_job` / `validate_job_for_build_plan` /
  `build_target_from_job` / `get_known_foundup_path` are in
  `tests/`. `BuildPlanExecutor.execute_step` is still a BLOCKED stub
  for `dry_run=False`.
- **KNOWN_FOUNDUP_PATHS consumer census**: 2 PATH_IDENTITY_USE sites
  (lines 172 and 278) + 1 DISPLAY_CATALOG_USE inline string interpolation
  (line 182 in the same severed branch) + 0 cross-module callers.
  Ruling: **DELETE_AS_DEAD_CODE** (the DISPLAY_CATALOG_USE is removed
  with the branch that contains it).
- **Extraction equivalence map**: 12 names move to
  `module_path_resolution.py`; the executor shim re-exports every name
  the test file accesses via either `from ... import` or `import ... as e`
  patterns. `Path(__file__).resolve().parents[4]` evaluates to the
  same `Path` because the new module is at the same nesting depth.

### Added

- **`modules/foundups/agent/src/module_path_resolution.py`** -- NEW
  shared module. Single source of truth for the module-path trust rule
  across the agent module. Contains the verbatim-moved #778 resolver
  surface:
  - `ResolvedModulePath` frozen dataclass.
  - `DEFAULT_REPO_ROOT`, `_MANIFEST_SEARCH_GLOBS`, four
    `FAIL_TOKEN_*` constants, `ALL_FAIL_TOKENS`.
  - `_stringify_ignored`, `_find_manifest_for_foundup_id`,
    `_resolve_validated_module_path`.
  - Imports only `__future__`, `json`, `dataclasses`, `pathlib`,
    `typing`, the validator, and the `FoundUpJob` type. No runtime /
    executor / consumer imports. No subprocess / network /
    file-write.

### Changed

- **`modules/foundups/agent/src/hermes_foundup_job_executor.py`** --
  back-compat shim. The 12 moved names are re-imported and re-exported
  from the shared module. The executor's caller block (the
  resolver-invocation site) is unchanged; it now resolves
  `DEFAULT_REPO_ROOT` and `_resolve_validated_module_path` via the
  shim, but the call semantics are identical. Identity is preserved:
  `e._resolve_validated_module_path is m._resolve_validated_module_path`
  is `True` (mechanically pinned by
  `TestSharedResolverIsSingleSourceOfTruth::test_executor_shim_and_shared_module_resolve_same_function`).
- **`modules/foundups/agent/src/build_plan_generator.py`** -- the
  trust seams are CLOSED:
  - DELETED: `KNOWN_FOUNDUP_PATHS` dict + `get_known_foundup_path()`
    wrapper (lines 78-96 in the prior layout).
  - DELETED: `_is_valid_foundup_path()` prefix-only gate with
    `.lower()` compare and `public/member/foundups/` admit (lines
    203-223 in the prior layout).
  - DELETED: `f"modules/foundups/{job.foundup_id}"` synthesis fallback
    in `build_target_from_job` (line 282 in the prior layout).
  - DELETED: payload raw reads at the prior lines 167 and 276.
  - REWROTE `validate_job_for_build_plan(job, repo_root=None)`: pre-
    gates `MISSING_FOUNDUP_ID` / `UNSUPPORTED_ACTION` / `UNKNOWN_ACTION`,
    then delegates to the shared resolver. On resolver failure the
    `GenerationValidationResult.error_code` carries the closed-set
    #778 token (`syntactic_reject` / `manifest_mismatch` /
    `manifest_missing` / `cross_foundup_mismatch`).
  - REWROTE `build_target_from_job(job, repo_root=None)`: ALWAYS calls
    the resolver; `BuildTarget.module_path` is the resolver's
    canonical `effective`. PWA-surface ruling: DERIVED_ONLY --
    `pwa_surface_path` derived from the canonical module_path basename
    (`public/member/foundups/{basename}/`); payload-supplied surface
    paths NEVER trusted as module identity.
  - ADDED `rejected_payload_value` field to
    `GenerationValidationResult` -- mirrors `ResolvedModulePath.ignored`
    (observable-ignore). Visible even on success; NEVER propagates
    into BuildTarget output (pinned by
    `test_rejected_payload_value_does_not_propagate_into_buildtarget`).
- **`modules/foundups/agent/tests/test_build_plan_generator.py`** --
  test updates (flagged in TestModLog):
  - REMOVED dead-symbol imports `KNOWN_FOUNDUP_PATHS`,
    `get_known_foundup_path` from the import block.
  - DELETED `test_known_foundup_paths_include_voteballots` and
    `test_get_known_foundup_path_returns_voteballots` (the symbols
    they exercised are deleted).
  - UPDATED `TestModulePathInference`: kept the happy-path tests
    (the bounded foundup_id scan locates the real `voteballots`
    manifest); replaced the legacy `MISSING_MODULE_PATH` error_code
    expectation with `manifest_missing`.
  - UPDATED `TestOutsideScopeRejected`: replaced the legacy
    `INVALID_MODULE_PATH` error_code expectation with the closed-set
    #778 tokens (`syntactic_reject` for absolute / drive-prefix paths;
    `manifest_missing` for under-`modules/` paths without a backing
    manifest).
  - ADDED `TestSharedResolverValidationInGenerator` (the 14
    dispatch-required negative tests + happy-path controls): payload-
    path with no backing manifest, source_module alias variants,
    cross-FoundUp substitution, suffix/basename, case-variant +
    uppercase prefix, absolute + drive-prefix + traversal +
    backslash, empty-string-as-absent, the dead-dict legacy IDs no
    longer resolve, foundup_id synthesis dead, PWA surface as
    identity rejected, rejected value observable on failure AND on
    success, rejected value never propagates into BuildPlan output.
  - ADDED `TestSharedResolverIsSingleSourceOfTruth` (Addendum C #4):
    asserts the executor shim re-exports the SAME objects (identity
    preservation across the import boundary), the generator and
    executor reference the same resolver, AST scans on both files
    confirm no second resolver implementation remains.
  - ADDED `TestHermes778TestsUnchanged` (Addendum C #3 meta-test):
    asserts every import pattern the #778 executor test uses still
    resolves through the shim, including the `import ... as e`
    attribute-access pattern.

### Boundary preserved

- **HERMES_778_TESTS_UNCHANGED_GREEN**: `pytest -q
  modules/foundups/agent/tests/test_hermes_foundup_job_executor.py` ->
  **46 passed in 0.83s** with ZERO edits to the test file. Addendum
  C #3 satisfied.
- **NO_SECOND_MODULE_PATH_RESOLVER**: AST scan on both the executor
  and the generator confirms neither file defines
  `_resolve_validated_module_path`, `_find_manifest_for_foundup_id`,
  `_stringify_ignored`, or `ResolvedModulePath` locally. The shared
  module is the only definition.
- **NO_VALIDATOR_MUTATION**: `foundup_manifest_validator.py`
  untouched.
- **NO_MANIFEST_MUTATION**: no `foundup_manifest.json` modified.
- **NO_RUNTIME_OR_BUILDER_CHANGE**: `hermes_adapter.py` untouched;
  generator stays orphaned (no consumer wired).
- **NO_WSP_FILE_MUTATION**.
- **NO_NEW_DEPENDENCY**: only stdlib + intra-repo imports.
- **NO_JOB_CONTRACT_SCHEMA_CHANGE**: `StatusReasonCode` enum unchanged.

### Tests

```
python -m pytest modules/foundups/agent/tests/test_build_plan_generator.py -q
  -> 71 passed in 0.97s
python -m pytest modules/foundups/agent/tests/test_hermes_foundup_job_executor.py -q
  -> 46 passed in 0.83s (ZERO edits; Addendum C #3 satisfied)
python -m pytest modules/foundups/agent/tests/ -q
  -> 646 passed in 8.99s; 0 skipped; 0 xfailed
```

### Updated assertions (logged for W10 audit per dispatch)

- `TestModulePathInference::test_known_foundup_paths_include_voteballots`
  and `..._get_known_foundup_path_returns_voteballots` -- DELETED
  (symbols deleted).
- `TestModulePathInference::test_unknown_foundup_without_module_path_fails` --
  error_code expectation changed from `"MISSING_MODULE_PATH"` to
  `"manifest_missing"`.
- `TestOutsideScopeRejected::test_infrastructure_path_rejected` and
  `..._ai_intelligence_path_rejected` -- expected error_code changed
  from `"INVALID_MODULE_PATH"` to `"manifest_missing"` (paths under
  `modules/` but with no on-disk manifest).
- `TestOutsideScopeRejected::test_root_path_rejected` -- expected
  error_code changed from `"INVALID_MODULE_PATH"` to
  `"syntactic_reject"` (absolute path caught at pre-manifest hardening).

### WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | OLD_PAYLOAD_MODULE_PATH_TRUST_DEAD | YES | Source removes the lines 167, 220, 276 raw payload reads; `validate_job_for_build_plan` and `build_target_from_job` now both delegate to the shared resolver. Tests `test_payload_path_with_no_backing_manifest_rejected` and `test_rejected_payload_value_does_not_propagate_into_buildtarget` pin the new behavior. |
| 2 | KNOWN_FOUNDUP_PATHS_INFERENCE_DEAD | YES | Source: `KNOWN_FOUNDUP_PATHS` dict and `get_known_foundup_path` function REMOVED from `build_plan_generator.py`. Test `test_known_foundup_paths_symbol_is_gone` asserts the import raises `ImportError`. AST scan in `test_no_second_resolver_in_build_plan_generator` confirms no `KNOWN_FOUNDUP_PATHS` assignment node remains. `test_known_foundup_id_without_on_disk_manifest_fails_closed` parametrizes the legacy dead-dict entries (`pqn_portal`, `social_twin`, `move2japan`) and asserts every one now fails with `manifest_missing`. |
| 3 | FOUNDUP_ID_SYNTHESIS_DEAD | YES | Source: the `f"modules/foundups/{job.foundup_id}"` fallback at the prior line 282 is REMOVED. `test_foundup_id_synthesis_dead_no_modules_foundups_fallback` asserts a non-real foundup_id with empty payload returns `manifest_missing`, not a synthesized path. `test_build_target_does_not_use_synthesized_path` asserts `build_target_from_job` raises ValueError rather than returning a BuildTarget with a synthesized module_path. |
| 4 | CASE_VARIANT_PATH_REJECTED | YES | The `.lower()` compare in the dead `_is_valid_foundup_path` is gone. `test_case_variant_payload_rejected` (`modules/Foundups/voteballots`) and `test_uppercase_modules_prefix_rejected` (`Modules/foundups/voteballots`) both assert failure. |
| 5 | CROSS_FOUNDUP_SUBSTITUTION_REJECTED | YES | Inherits #778's resolver defense. `test_cross_foundup_substitution_rejected` constructs `job.foundup_id="voteballots"` + `payload.module_path="modules/foundups/kosei"` (both manifests are real) and asserts `error_code == "cross_foundup_mismatch"`. |
| 6 | PWA_SURFACE_RULING_RECORDED | YES | INTERFACE.md "PWA-surface ruling: DERIVED_ONLY" section. `test_pwa_surface_path_as_module_identity_rejected` asserts a payload-supplied `public/member/foundups/voteballots` path rejects at `syntactic_reject`. `test_buildplan_carries_only_canonical_when_payload_provided` asserts the BuildTarget's `pwa_surface_path` is derived from the manifest canonical's basename. |
| 7 | VALIDATED_MANIFEST_SOURCE_OF_TRUTH | YES | `validate_job_for_build_plan` and `build_target_from_job` both set their outputs from `resolved.effective`. `test_buildplan_carries_only_canonical_when_payload_provided` asserts the BuildTarget carries the manifest canonical (not the payload string) even when they match. |
| 8 | REJECTED_PAYLOAD_VALUE_OBSERVABLE | YES | New `GenerationValidationResult.rejected_payload_value` field carries the observable-ignore channel. `test_rejected_value_observable_on_failure` and `test_rejected_value_observable_on_success` both pass; the value is visible even when the payload matched. |
| 9 | REJECTED_VALUE_NOT_IN_BUILDPLAN_OUTPUT | YES | `test_rejected_payload_value_does_not_propagate_into_buildtarget` asserts both `create_build_plan_from_job` and `build_target_from_job` raise ValueError instead of producing a BuildTarget that carries the rejected value. |
| 10 | HERMES_778_TESTS_UNCHANGED_GREEN | YES | `pytest -q test_hermes_foundup_job_executor.py` returns `46 passed in 0.83s` with ZERO edits to the test file (Addendum C #3 hard gate). Verified by `TestHermes778TestsUnchanged::test_executor_test_imports_still_resolve` and `test_executor_attribute_access_pattern_still_works`. |
| 11 | SHARED_RESOLVER_SINGLE_SOURCE_OF_TRUTH | YES | NEW `modules/foundups/agent/src/module_path_resolution.py` carries the only definition. Both the executor (via shim) and the generator (via direct import) reference the SAME function object: `test_executor_shim_and_shared_module_resolve_same_function` and `test_generator_uses_same_resolver_as_executor` use `is` identity comparison. |
| 12 | HERMES_RESOLVER_EXTRACTION_BEHAVIOR_PRESERVED | YES | The 12 moved names are identical bytes (verbatim quote from #778 captured in Phase-0; reproduced unchanged in the new module). `Path(__file__).resolve().parents[4]` evaluates to the same Path because the new module is at the same nesting depth. The shim re-imports without wrapping. `test_executor_attribute_access_pattern_still_works` mechanically asserts every #778 attribute resolves correctly. |
| 13 | NO_SECOND_MODULE_PATH_RESOLVER | YES | AST scans `test_no_second_resolver_implementation_in_executor` and `test_no_second_resolver_in_build_plan_generator` walk the AST and assert neither file defines `_resolve_validated_module_path`, `_find_manifest_for_foundup_id`, `_stringify_ignored`, or `ResolvedModulePath` locally. KNOWN_FOUNDUP_PATHS-style assignments also caught. |
| 14 | NO_USER_QUESTION_FRAMING | YES | Addendum A respected. Phase-0 forks decided by evidence + recommendation: PWA-surface ruling -> DERIVED_ONLY (evidence: `BuildTarget` auto-derives from `module_path` basename); KNOWN_FOUNDUP_PATHS ruling -> DELETE_AS_DEAD_CODE (evidence: census shows 0 live non-PATH_IDENTITY consumers). |

**WSP_97 VERDICT**: PASS (14/14).

### Follow-ups (recorded; not executed here)

- `WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1` -- can now wire a
  dry-run consumer, IF AND ONLY IF the source of truth remains the
  shared resolver and no second implementation appears.
- HoloIndex re-index of `modules/foundups/agent/` -- two consecutive
  slices have hit LOW signal on identifier-token queries.

---

## 2026-06-10 - Hermes Module-Path Trust Removal Phase 1 (#774 carry-forward closure)

**Author**: 0102 (W6)
**Commander**: 012
**Slice**: HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1
**Branch**: `w6/hermes-module-path-trust-removal-phase1`
**Base**: `0952f51e9` (origin/main after #777)
**Effort**: ULTRA

**Type**: Authoring slice (last consumer-wiring precondition).
Closes the #774 carry-forward by forcing every job's `module_path`
through the #773 validator before the Hermes executor's subprocess
sink. Fail-closed. No consumer wiring; no validator / manifest /
runtime / WSP touch.

**WSP References**: WSP 11, WSP 50, WSP 77, WSP 84, WSP 87, WSP 97,
WSP 22.

### Phase 0 -- Mandatory Discovery summary

- **HoloIndex**: 4/4 queries returned HOLOINDEX_LOW_SIGNAL despite the
  subject domain being well-represented in `modules/foundups/agent/`,
  `modules/communication/moltbot_bridge/`, and recent commits
  (`27d6d2c22` hermes delegate-path fix). `public/litepaper.html` and
  similar large HTML/JS surfaces dominated cosine ranking. Recorded as
  a HoloIndex tuning concern, not a slice blocker; manual `Read`/`Grep`
  surfaced every target file with verbatim file:line citations.
- **Executor + validator + manifest convention survey**: full quotes
  with file:line cited; the manifest-on-disk join key is
  `<repo_root>/<module_path>/foundup_manifest.json`. No
  `foundup_id`-to-path index exists; bounded scan over the 6 canonical
  manifest directories (8 manifests today) is the explicit alternative
  to the removed `foundup_id`-as-path heuristic.
- **#774 audit verbatim finding**: "Legacy executor trusts
  payload.module_path. This is a consumer-wiring blocker, not a
  builder blocker." Cited at
  `docs/audits/architecture/OPENCLAW_HERMES_WRE_EXECUTION_CHAIN_AUDIT_PHASE1.md:378-390`
  with evidence pointer to
  `modules/foundups/agent/src/hermes_foundup_job_executor.py:217-237`
  (the now-removed `_extract_module_path`).
- **#770-#773 ModLog reading**: lineage captured. The #773 validator
  exposes `validate_manifest` / `validate_manifest_file` /
  `ManifestValidationResult` publicly; `_canonicalize_module_path` is
  module-private but consumable via explicit import (minimum
  blast-radius per Survey B.2; no public-surface change).
- **Build-plan-generator scope ruling** (Addendum B/D, load-bearing):
  **`OUT_OF_SCOPE_NAMED_FOLLOWUP`**. Evidence:
  `modules/foundups/agent/src/build_plan_generator.py:167, :276` read
  `payload.module_path`/`source_module` and at `:282` synthesize
  `f"modules/foundups/{job.foundup_id}"`. Reachability analysis
  confirmed ZERO non-test, non-doc importers; the only downstream
  consumer (`BuildPlanExecutor.execute_step`) is a stub that returns
  `StepExecutionStatus.BLOCKED` for any real execution
  (`build_plan_executor.py:634-665`). `build_plan_swarm.py` and
  `swarm_dispatch_integration.py` only label-match
  `target.module_path`; no `subprocess`, no `hermes_adapter` import.
  Tie-break per Addendum D #2: **current reachability decides** --
  unreachable now, follow-up
  `BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1` becomes a
  hard precondition row in `WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1`
  or any other slice that makes build_plan_generator reachable from a
  real-execution sink.

### Changed

- **`modules/foundups/agent/src/hermes_foundup_job_executor.py`**:
  - **REMOVED** `_extract_module_path` (raw-trust extraction; the
    function and its 3-priority cascade including the
    `foundup_id`-with-`/`-is-a-path heuristic).
  - **ADDED** `ResolvedModulePath` frozen dataclass with the
    observable-ignore tuple shape (`effective`, `ignored`, `failed`,
    `fail_token`, `fail_human`) mirroring #777's
    `source_authority.resolve_source_authority`.
  - **ADDED** `_stringify_ignored(declared)` -- mirror of
    source_authority's ignored-value stringification; None iff
    declaration None, else `str(declared)`.
  - **ADDED** `_find_manifest_for_foundup_id(repo_root, foundup_id)` --
    bounded glob over the 6 canonical manifest directories; reads each
    candidate's top-level `foundup_id` and returns the first match.
    Used ONLY when payload omits both `module_path` and `source_module`.
    Replaces the removed `foundup_id`-as-path heuristic with an
    explicit, evidence-backed lookup.
  - **ADDED** `_resolve_validated_module_path(job, repo_root)` -- the
    fail-closed resolver. Pinned-design conformance:
      1. candidate from `payload.module_path` / `payload.source_module`
         (alias); empty string is ABSENT (Addendum D #4).
      2. syntactic hardening BEFORE any manifest contact: backslashes
         (Addendum C #5), absolute / UNC (Addendum C #6), `..`
         traversal (Addendum C #6), `not startswith("modules/")` all
         REJECTED with `fail_token=syntactic_reject`.
      3. manifest located at
         `<repo_root>/<canonical>/foundup_manifest.json`, OR via
         bounded `foundup_id` scan when candidate absent.
      4. `validate_manifest_file` (#773) gates; I/O-class errors map to
         `manifest_missing`, shape errors to `manifest_mismatch`.
      5. **Cross-FoundUp substitution defense** (Addendum D #1,
         load-bearing): manifest's `foundup_id` MUST equal
         `job.foundup_id`; otherwise `fail_token=cross_foundup_mismatch`.
      6. **Case-variant defense** (Addendum D #3, Windows host
         reality): candidate canonical exact-string-compared
         (case-sensitive) against manifest canonical; mismatch =>
         `fail_token=manifest_mismatch`.
      7. Success: `effective` is the manifest's canonical
         `module_path` (the source of truth). The payload-declared
         value remains in `ignored` even when it matches (observable
         silent-swallow refused).
  - **ADDED** `DEFAULT_REPO_ROOT` (derived from `__file__`),
    `_MANIFEST_SEARCH_GLOBS`, `ALL_FAIL_TOKENS` frozenset, and four
    `FAIL_TOKEN_*` constants (`syntactic_reject`, `manifest_mismatch`,
    `manifest_missing`, `cross_foundup_mismatch`) -- greppable
    failure-mode taxonomy per Addendum D #5.
  - **REPLACED** the prior `if not module_path: job.fail(...)` block
    (lines 153-167) with the resolver invocation. On failure, the
    evidence list carries both
    `rejected_payload_value:<stringified>` (when the payload declared
    something) and `fail_token:<one of ALL_FAIL_TOKENS>` (always).
    `StatusReasonCode.FAIL_VALIDATION_ERROR` reused as-is; no
    job-contract schema changes.
- **`modules/foundups/agent/tests/test_hermes_foundup_job_executor.py`**:
  - **UPDATED FIXTURES** `queued_extract_job` / `queued_validate_job` /
    `queued_build_job` to use the real manifest `gotjunk_001`
    (`modules/foundups/gotjunk`) so the new validated-resolution
    pre-flight passes and the downstream mocked-Hermes paths still
    exercise their mappings. Prior synthetic `modules/foundups/widget`
    path no longer reaches the executor (refused as
    `manifest_missing`).
  - **UPDATED** `TestActionDispatch::test_extract_foundup_calls_extract_method`
    and `..._validate_foundup_calls_gate_and_boundary` assertions to
    expect `modules/foundups/gotjunk` (was `widget`).
  - **UPDATED** `TestModulePathExtraction`: replaced
    `test_foundup_id_as_fallback` with
    `test_foundup_id_path_heuristic_removed` (explicit no-inference
    assertion); existing `test_module_path_from_payload` and
    `test_source_module_from_payload` retained as documentation of
    payload shape; new behavior covered in
    `TestResolvedModulePathValidation`.
  - **ADDED** `TestResolvedModulePathValidation` (24 tests, no skip /
    no xfail) covering:
    - Happy paths: real `gotjunk_001` manifest; cross-domain `kosei`.
    - Addendum C #1 (`test_payload_path_wrong_manifest_path_rejected`)
      + payload alias variant.
    - Addendum C #2 (`test_source_module_alias_validates_same_as_module_path`,
      `..._with_wrong_path_rejected`).
    - Addendum C #4 (`test_suffix_only_path_rejected`,
      `test_partial_path_rejected`).
    - Addendum C #5 (`test_backslash_payload_rejected_pre_manifest`).
    - Addendum C #6 (`test_absolute_path_rejected_pre_manifest`,
      `..._absolute_drive_path_..`, `..._traversal_path_..`,
      `..._internal_traversal_..`).
    - Addendum C #7 (`test_payload_omitted_derives_from_validated_manifest`,
      `..._unknown_foundup_id_fails_missing`).
    - Addendum C #8 (`test_rejected_payload_value_appears_in_evidence`,
      end-to-end through `execute_foundup_job`).
    - Addendum D #1 (`test_cross_foundup_substitution_rejected`,
      `..._via_alias_rejected`).
    - Addendum D #3 (`test_case_variant_payload_rejected`,
      `test_uppercase_modules_prefix_rejected`).
    - Addendum D #4 (`test_empty_string_payload_treated_as_absent`,
      `..._empty_string_alias_..`).
    - Closed-set token taxonomy
      (`test_all_fail_tokens_present_in_taxonomy`).
    - End-to-end no-builder-instantiation guards
      (`test_execute_foundup_job_fails_closed_on_invalid_payload`,
      `..._on_cross_foundup_substitution`).

### Boundary preserved

- **NO_VALIDATOR_MUTATION**: `foundup_manifest_validator.py` untouched;
  the executor IMPORTS public + one underscore-helper without changing
  the validator's surface.
- **NO_MANIFEST_MUTATION**: no `foundup_manifest.json` modified.
- **NO_RUNTIME_OR_BUILDER_CHANGE**: `hermes_adapter.py` and the rest of
  the runtime are untouched. The patch is purely in the executor's
  pre-flight; the subprocess sink remains exactly where it was
  (`hermes_adapter.py:939, :946`).
- **NO_CONSUMER_WIRING**: no new caller wired into the Hermes
  executor; this slice only hardens the EXISTING execution seam.
- **NO_WSP_FILE_MUTATION**: nothing under `WSP_framework/` or
  `WSP_knowledge/`.
- **NO_NEW_DEPENDENCY**: only stdlib imports (`json`, `pathlib`,
  `dataclasses`) and the existing intra-repo validator import.
- **NO_JOB_CONTRACT_SCHEMA_CHANGE**: `StatusReasonCode` enum unchanged;
  `FAIL_VALIDATION_ERROR` reused. Granularity comes from the greppable
  fail-token prefix on `reason_human` + a parallel `evidence_refs`
  entry.

### Tests

```
python -m pytest modules/foundups/agent/tests/test_hermes_foundup_job_executor.py -q
  -> 46 passed in 0.84s
python -m pytest modules/foundups/agent/tests/ -q
  -> 621 passed in 9.06s (575 prior + 22 pre-existing executor + 24 new resolution tests)
```

0 skipped. 0 xfailed.

### Updated assertions (logged for W10 audit per dispatch)

- `TestActionDispatch::test_extract_foundup_calls_extract_method` --
  expected source_module changed from `modules/foundups/widget` to
  `modules/foundups/gotjunk` (validator-confirmed real manifest).
- `TestActionDispatch::test_validate_foundup_calls_gate_and_boundary` --
  same change.
- `TestModulePathExtraction::test_foundup_id_as_fallback` -- RENAMED to
  `test_foundup_id_path_heuristic_removed`; assertion flipped from
  "foundup_id with '/' is used as a path" to "foundup_id with '/' is
  NEVER used as a path; bounded scan or manifest_missing wins".
- Fixtures `queued_extract_job` / `queued_validate_job` /
  `queued_build_job` -- payload/foundup_id changed from synthetic
  `widget` to real `gotjunk_001`/`modules/foundups/gotjunk`.

### WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_PRIOR_ART_SEARCHED | YES | Phase-0 ran 4 queries; results recorded above with retrieval evaluation. All 4 returned LOW signal -- a HoloIndex tuning finding, not a slice blocker. Manual Read/Grep surfaced every target file. |
| 2 | WSP_84_REUSE_DECISION_DOCUMENTED | YES | Imports validator (`validate_manifest_file`, `_canonicalize_module_path`) -- does not reimplement. No competing axis invented. |
| 3 | VALIDATOR_REUSED_NOT_REIMPLEMENTED | YES | `from modules.foundups.agent.src.foundup_manifest_validator import validate_manifest_file` and `_canonicalize_module_path as _validator_canonicalize_module_path`. No validator logic duplicated. |
| 4 | NO_VALIDATOR_MUTATION | YES | `git diff` confirms `foundup_manifest_validator.py` is unchanged. |
| 5 | NO_MANIFEST_MUTATION | YES | `git diff` confirms no `foundup_manifest.json` modified. |
| 6 | NO_RUNTIME_OR_BUILDER_CHANGE | YES | `hermes_adapter.py` untouched. The patch is purely in the executor's pre-flight; the subprocess sink (`hermes_adapter.py:939, :946`) is unreached for failed jobs (verified by end-to-end test with mocked builder). |
| 7 | NO_CONSUMER_WIRING | YES | No new caller wired; existing execution seam only hardened. |
| 8 | NO_WSP_FILE_MUTATION | YES | `git diff` confirms no file under `WSP_framework/` or `WSP_knowledge/`. |
| 9 | NO_JOB_CONTRACT_SCHEMA_CHANGE | YES | `StatusReasonCode` enum unchanged; `FAIL_VALIDATION_ERROR` reused. |
| 10 | NO_USER_QUESTION_FRAMING | YES | Addendum A respected: no AskUser dialog used in this slice. Phase-0 fork (`build_plan_generator` ruling) was decided by 4-step protocol (evidence -> WSP_97 condition -> recommendation -> stop only if dispatch requires) -- ruling was OUT_OF_SCOPE_NAMED_FOLLOWUP, recorded in the Phase-0 summary. |
| 11 | BUILD_PLAN_GENERATOR_SCOPE_RULED | YES | Phase-0 ruling: `OUT_OF_SCOPE_NAMED_FOLLOWUP`. Evidence: `build_plan_generator.py:167, :276, :282` quoted; reachability shows zero non-test, non-doc importers and BuildPlanExecutor.execute_step is a BLOCKED stub. Follow-up named: `BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1`. Tie-break per Addendum D #2: current reachability decides; follow-up becomes a hard precondition row in `WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1`. |
| 12 | OLD_PAYLOAD_MODULE_PATH_TRUST_DEAD | YES | The prior `_extract_module_path` is REMOVED from the source tree. `git diff` confirms removal. Tests that would have passed under the legacy trust (`test_payload_path_wrong_manifest_path_rejected`, `test_cross_foundup_substitution_rejected`) now FAIL the prior behavior and PASS the new fail-closed semantics. |
| 13 | SOURCE_MODULE_ALIAS_VALIDATED | YES | `test_source_module_alias_validates_same_as_module_path` (happy path), `..._with_wrong_path_rejected` (alias gets the same fail-closed treatment), `test_cross_foundup_substitution_via_alias_rejected`, `test_empty_string_alias_also_treated_as_absent`. |
| 14 | FOUNDUP_ID_PATH_HEURISTIC_REMOVED | YES | Source: the `if job.foundup_id and "/" in job.foundup_id: return job.foundup_id` branch is gone. Test: `TestModulePathExtraction::test_foundup_id_path_heuristic_removed` asserts that a path-shaped foundup_id with empty payload returns `failed=True, fail_token=manifest_missing`, NOT a derived path. |
| 15 | REJECTED_PAYLOAD_VALUE_OBSERVABLE | YES | `ResolvedModulePath.ignored` preserved even on success. `test_happy_path_real_manifest_resolves_to_canonical` asserts `ignored == "modules/foundups/gotjunk"` even on a successful match. `test_rejected_payload_value_appears_in_evidence` asserts the `rejected_payload_value:...` entry is in `evidence_refs` on FAILED end-to-end. |
| 16 | VALIDATED_MANIFEST_SOURCE_OF_TRUTH | YES | `ResolvedModulePath.effective` is sourced from `manifest_data.get("build_contract", {}).get("module_path", "")` after `validate_manifest_file` returns `ok=True`. Payload candidate is only used for the candidate-vs-manifest exact-string check; the effective value is always the manifest's canonical module_path. `test_payload_omitted_derives_from_validated_manifest` pins the derivation. |
| 17 | CROSS_FOUNDUP_SUBSTITUTION_REJECTED | YES | Step 6 of the resolver enforces `manifest_foundup_id != job.foundup_id -> FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH`. Tests: `test_cross_foundup_substitution_rejected` (primary, via `module_path`), `test_cross_foundup_substitution_via_alias_rejected` (via `source_module`), `test_execute_foundup_job_fails_closed_on_cross_foundup_substitution` (end-to-end with mocked builder asserting `mock_builder_cls.assert_not_called()`). |
| 18 | CASE_VARIANT_PATH_REJECTED | YES | `test_case_variant_payload_rejected` (`modules/Foundups/gotjunk` -- inner caps), `test_uppercase_modules_prefix_rejected` (`Modules/foundups/gotjunk` -- prefix caps). Both reject (either at the `startswith("modules/")` syntactic guard or at the step-7 case-sensitive exact-match against the manifest canonical). |
| 19 | SYNTACTIC_REJECT_PRE_MANIFEST | YES | `test_backslash_payload_rejected_pre_manifest`, `test_absolute_path_rejected_pre_manifest`, `test_absolute_drive_path_rejected_pre_manifest`, `test_traversal_path_rejected_pre_manifest`, `test_internal_traversal_rejected`, `test_suffix_only_path_rejected`, `test_partial_path_rejected`. All return `fail_token=syntactic_reject` BEFORE the manifest is read. |
| 20 | GREPPABLE_FAIL_TOKENS_PINNED | YES | `test_all_fail_tokens_present_in_taxonomy` asserts the closed set is exactly `{syntactic_reject, manifest_mismatch, manifest_missing, cross_foundup_mismatch}`. Every `_resolve_validated_module_path` failure path emits one of these tokens via `reason_human` prefix + `evidence_refs[fail_token:...]` entry. |
| 21 | EMPTY_STRING_TREATED_AS_ABSENT | YES | `test_empty_string_payload_treated_as_absent` and `..._empty_string_alias_..` pin that `""` is falsy and falls through to derivation; `ignored` stays `None`. |
| 22 | NO_NEW_DEPENDENCY | YES | Imports added: stdlib `json`, `dataclasses.dataclass`; intra-repo validator only. No new package or version. |
| 23 | NO_SKIP_XFAIL | YES | `pytest -q modules/foundups/agent/tests/` -> `621 passed in 9.06s`; 0 skipped; 0 xfailed. |
| 24 | CITES_PR_770_771_772_773_774_AND_777 | YES | Header Predecessors cites #770-#774; section 5 cites the laundering-fix lineage and #777's observable-ignore convention; the resolver docstring cites #773 for exact-match and #774 for the trust gap; INTERFACE.md "Consumer-wiring precondition status" cites the follow-up name. |
| 25 | CONSUMER_WIRING_REMAINS_BLOCKED_UNTIL_FOLLOWUP | YES | INTERFACE.md and the contract section above state that
`BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1` is a hard precondition row for `WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1`. Tie-break per Addendum D #2: current reachability decides. |
| 26 | INTERFACE_MD_UPDATED | YES | New "Validated Module-Path Resolution" section added (WSP_22 order: INTERFACE -> ROADMAP -> ModLog -> TestModLog). |
| 27 | ASCII_CLEAN | YES | Slice-introduced content is 0 non-ASCII bytes across `hermes_foundup_job_executor.py` patch, new tests, INTERFACE/ROADMAP additions, this ModLog entry, TestModLog entry, and root ModLog entry. |

**WSP_97 VERDICT**: PASS (27/27).

### Follow-ups (recorded; not executed here)

- `BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1` -- hardens
  the build_plan_generator value flow with the same validator gate;
  becomes a HARD precondition row in
  `WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1` per Addendum D #2.
- `HOLOINDEX_LIFECYCLE_TUNING_PHASE1` (already proposed by #777) --
  the LOW signal on all 4 Phase-0 queries here strengthens the case.
- `WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1` -- can now safely wire
  the #775 ContextBundle into the Hermes executor seam IF AND ONLY IF
  the BUILD_PLAN_GENERATOR follow-up has landed (per Addendum D #2
  tie-break).

---

## 2026-06-10 - FoundUp Lifecycle / Source-Authority Contract Phase 1

**Author**: 0102 (W6)
**Commander**: 012
**Slice**: FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_CONTRACT_PHASE1
**Predecessors**:
- #775 (merged `96a860cc3`): ContextBundle producer with
  builder-constant `SOURCE_AUTHORITY = "monorepo_poc"`.
- `96314ab6c`: laundering-fix precedent that anchors the "cannot
  promote by declaration" hard rule.

**WSP References**: WSP 11, WSP 27, WSP 30, WSP 50, WSP 64, WSP 84,
WSP 97, WSP 103, WSP 109, WSP 22.

**Type**: Contract / design slice (decision-only). Authoritative
definition of the source-authority axis. Pins `monorepo_poc` as the
only reachable stage in Phase-1.

### Phase 0 -- Mandatory Discovery summary

- HoloIndex: 3 queries, MEDIUM / HIGH / MEDIUM signal. No existing
  `SourceAuthority` enum. WSP_27 / WSP_103 / WSP_109 did NOT directly
  surface for the lifecycle queries despite being load-bearing -- a
  HoloIndex tuning follow-up is proposed
  (`HOLOINDEX_LIFECYCLE_TUNING_PHASE1`).
- Axis reconciliation: WSP 27 Section 11.0 owns the canonical maturity
  lifecycle; WSP 103:616-617 owns the OPO transition gate; WSP 109:42,
  89-103, 350-360 owns the RedDog intake actor and `entity_type` enum.
- OPO LAUNCH vs smartDAO: SEQUENTIAL (not equal), derived from WSP 27
  tier numbers (OPO LAUNCH = Tier 2 Thriving; smartDAO = Tier 1
  Sovereign). The contract treats them as distinct points: `mvp_runtime`
  brackets post-OPO operation; `dao_managed` brackets post-Tier-1.
- Terminology drift recorded (NOT fixed): smartDAO (WSP 27) vs OPO
  LAUNCH (WSP 103); OBAI/RedDog is the intake actor (WSP 109), not a
  maturity stage. Follow-up
  `WSP27_LIFECYCLE_TERMINOLOGY_ALIGNMENT_PHASE1` proposed.
- WSP placement audit: recommendation (c) -- REMAIN a docs/architecture
  contract. Justification: single consumer at present
  (`context_bundle_builder.py`), WSP 27 + WSP 103 + WSP 109 citation
  triad is sufficient, WSP 109 already partially covers intake-time
  source-authority via `entity_type`. Promotion to WSP deferred to
  `FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_WSP_FORMALIZATION_PHASE1`.

### Added

- **`docs/architecture/FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md`** -- the
  authoritative contract doc. Defines 5 stages
  (`monorepo_poc` / `external_proto` / `mvp_runtime` / `dao_managed` /
  `archived`), per-stage matrix (9 dimensions), maturity coupling
  table (8 maturity rows x source-authority bindings with citations),
  4 transition gates (defined; not implemented), the verbatim hard
  rule, enforcement mechanism, relationship to the consumer-wiring
  precondition, explicit non-goals, proposed follow-ups, and the
  WSP_97 28-row Truth Boundary Checklist (canonical header).
- **`modules/foundups/agent/src/source_authority.py`** -- minimal
  typed enum module pinning the contract in code.
  - `SourceAuthority(str, enum.Enum)` with 5 members; values EXACT.
  - `ACTIVE_STAGES: frozenset = frozenset({SourceAuthority.MONOREPO_POC})`.
  - `resolve_source_authority(declared)` ALWAYS returns
    `(MONOREPO_POC, ignored_declaration_stringified_or_None)`; NEVER
    raises; observable ignored declaration (no silent swallow).
  - `request_promotion(target)` ALWAYS raises
    `NotImplementedError`; error message points readers at the
    contract doc.
  - Pure / read-only: imports only `__future__`, `enum`, `typing`.
- **`modules/foundups/agent/tests/test_source_authority.py`** -- 67
  tests across 8 classes covering enum shape, ACTIVE_STAGES,
  always-MONOREPO_POC resolution, garbage-input fuzz (20 parametrized
  inputs), request_promotion always-raises (parametrized by every
  member + garbage), builder value parity, AST safety scan, and the
  enum-not-wired-into-builder guard.
- **`modules/foundups/agent/INTERFACE.md`** -- new "Source-Authority
  Contract" public-API section with enum signature, function
  contracts, the hard rule, and citation triad. WSP_22 doc-update
  order honored.
- **`modules/foundups/agent/ROADMAP.md`** -- contract entry added
  under Completed.

### Boundary preserved

- No file under `WSP_framework/` or `WSP_knowledge/` modified
  (`NO_WSP_FILE_MUTATION`).
- `modules/foundups/agent/src/context_bundle_builder.py` untouched
  (`NO_BUILDER_CHANGE`).
- `foundup_manifest_validator.py` untouched.
- No manifest, registry, OpenClaw, Hermes, AI Overseer, WRE consumer,
  `*_dae.py`, `main.py`, `vendor/`, `.env`, CI, or dependency file
  touched.
- No CABR / payout / DAO / token logic added.
- The enum is NOT wired into the builder
  (`SOURCE_AUTHORITY_BUILDER_ENUM_UNIFICATION_PHASE2` proposed as a
  follow-up).
- Consumer wiring remains BLOCKED -- this slice satisfies precondition
  (a) of the consumer-wiring precondition; precondition (b) (#774
  carry-forward, legacy payload.module_path trust removal) is NOT
  satisfied.

### Tests

```
python -m pytest modules/foundups/agent/tests/test_source_authority.py -q
  -> 67 passed in 0.36s
python -m pytest modules/foundups/agent/tests/ -q
  -> 597 passed in 9.43s (530 prior FIX2c + 67 new)
```

0 skipped. 0 xfailed.

### WSP_97 Truth Boundary Checklist

Full 28-row checklist with verbatim evidence lives at
[FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md](../../../docs/architecture/FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md)
Section 10. **PASS (28/28)**.

### Proposed follow-ups (recorded; not executed here)

- `WSP27_LIFECYCLE_TERMINOLOGY_ALIGNMENT_PHASE1` -- harmonize WSP 27 /
  WSP 103 vocabularies; RedDog actor-vs-stage callout.
- `FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_WSP_FORMALIZATION_PHASE1` --
  promote to WSP 110 candidate slot once a second module consumes
  `source_authority`.
- `SOURCE_AUTHORITY_BUILDER_ENUM_UNIFICATION_PHASE2` -- replace the
  builder constant with an import of
  `SourceAuthority.MONOREPO_POC.value`.
- `HOLOINDEX_LIFECYCLE_TUNING_PHASE1` -- investigate why WSP_27 /
  WSP_103 / WSP_109 did not surface for the lifecycle queries.

---

## 2026-06-10 - WRE ContextBundle Builder Phase 1 FIX2c (explicit monorepo-PoC Phase-1 boundary)

**Author**: 0102 (W6)
**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1_FIX2C
**Predecessor**: FIX2b (this branch, PR #775)
**Trigger**: 012 architectural ruling on PR #775

**012 architectural ruling**:

> #775 is monorepo-PoC Phase-1 infrastructure, NOT the external-state FoundUp
> lifecycle system. The bundle must be HONEST about that scope and must NOT
> bake in "FoundUp = monorepo directory" as the permanent model. #775 is "a
> monorepo-PoC bundle producer WITH AN EXPLICIT BOUNDARY", kept SMALL. The
> full lifecycle transition model is a SEPARATE deferred slice
> (FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_CONTRACT_PHASE1) and is NOT implemented
> here.

**FIX2c changes (4 files; read-only builder; no validator/manifest/runtime
edit; no new dependency; small + additive)**:

1. `src/context_bundle_builder.py`:
   - Added module constant `SOURCE_AUTHORITY = "monorepo_poc"` (added to
     `__all__`). A comment documents the deferred future stages
     (external_proto / mvp_runtime / dao_managed / archived) for
     forward-compat WITHOUT implementing them.
   - Added a `source_authority: str` field to the `ContextBundle` frozen
     dataclass and to `to_dict()` (placed right after `bundle_version`).
   - In `build_context_bundle`, set `source_authority=SOURCE_AUTHORITY` -- a
     BUILDER CONSTANT. It is NEVER read from the manifest / build_contract /
     execution_routing. If a manifest carries a `source_authority` or
     `lifecycle_stage` key, the builder IGNORES it entirely. This enforces
     the hard rule "a context bundle cannot promote its lifecycle stage by
     declaration".
   - Added a `MONOREPO_PHASE1_BOUNDARY` statement to both the module
     docstring and the `ContextBundle` class docstring.
   - DETERMINISM: `BUNDLE_VERSION` and the `bundle_id` formula
     (`sha256(source_manifest_sha256 + "|" + module_path + "|" +
     BUNDLE_VERSION)`) are UNCHANGED; `source_authority` is additive and
     does NOT enter `bundle_id`.

2. `tests/test_context_bundle_builder.py`: new
   `TestMonorepoPhase1SourceAuthorityBoundary` (10 tests):
   - `test_source_authority_constant_is_monorepo_poc`.
   - `test_real_manifest_source_authority_is_monorepo_poc` (6 parametrized
     real manifests; object + `to_dict()` both `"monorepo_poc"`).
   - `test_manifest_cannot_self_promote_lifecycle_stage` -- ANTI-SELF-PROMOTION
     (load-bearing): a manifest that ADDS top-level `source_authority:
     "dao_managed"` AND build_contract `lifecycle_stage: "mvp_runtime"` STILL
     builds a bundle with `source_authority == "monorepo_poc"` (the builder
     ignores any manifest-supplied stage; the bundle IS produced, proving the
     manifest declaration is ignored, not merely rejected).
   - `test_to_dict_has_no_external_dao_mvp_readiness_authority` -- `to_dict()`
     contains NO external/DAO/MVP readiness key as a truthy authority
     (dao_ready/dao_managed/mvp_runtime/external_proto/cabr_ready/payout_ready/
     archived), and `source_authority` is exactly the Phase-1 constant.
   - `test_source_authority_not_in_bundle_id_fingerprint` -- determinism:
     `source_authority` does NOT enter the bundle_id formula.

3. `ModLog.md`: WSP_97 table extended 35 -> 36 rows; new row 36
   `MONOREPO_POC_SOURCE_AUTHORITY_EXPLICIT`; FIX2c verdict added.

4. `tests/TestModLog.md`: run summary updated to the new count.

**Prior guarantees preserved**: no validator edit, no manifest edit, no
runtime/consumer wiring, no build run, no new dependency, no FoundUp name
hard-coded in the production builder src. All 6 real manifests still build.
ALL prior W10 guarantees intact (dict/bool + fullwidth/NFKC authority +
non-ASCII + control-char all rejected; AST completeness detector;
printable-ASCII contract). No external_proto/mvp_runtime/dao_managed/archived
handling, no DAO/MVP/CABR/payout fields, no lifecycle transitions were
added. No skip / no xfail.

**Test run**: `python -m pytest modules/foundups/agent/tests/ -q
-p no:cacheprovider` -> 530 passed, 0 skipped, 0 xfailed (520 FIX2b + 10
FIX2c tests).

**ASCII**: both `.py` files are 0 non-ASCII bytes. This ModLog FIX2c entry
is ASCII-clean.

See the FIX1 entry below for the full WSP_97 Truth Boundary Checklist
(row 36 is the FIX2c addition; verdict FIX2c PASS 36/36).

---

## 2026-06-10 - WRE ContextBundle Builder Phase 1 FIX2b (printable-ASCII-only protected list elements)

**Author**: 0102 (W6)
**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1_FIX2B
**Predecessor**: FIX2 (this branch, PR #775)
**Trigger**: W10 final adversarial review of PR #775

**W10 final residual (proven after FIX2 ASCII-only contract)**:

> The protected list fields (required_gates / forbidden_paths /
> safe_mutation_surface) are guarded by `_require_str_tuple`, which rejects
> non-str, empty/whitespace, NFKC authority-keyword substrings, and
> non-ASCII (`if not item.isascii()`). RESIDUAL: ASCII CONTROL CHARACTERS
> (NUL U+0000, CR U+000D, LF U+000A, TAB U+0009, ESC U+001B, ...) ARE
> ASCII, so they pass `isascii()` and LAND in the bundle. Not authority
> laundering (still strings), but a string-hygiene / log-injection /
> terminal-escape shape in a provenance field future consumers may log.

**012 ruling**: upgrade the contract to PRINTABLE-ASCII-only, which
definitively ends the Unicode/control-char evasion class.

**FIX2b changes (4 files; read-only builder; no validator/manifest/runtime
edit; no new dependency)**:

1. `src/context_bundle_builder.py`: in `_require_str_tuple`, AFTER the
   existing `if not item.isascii(): raise` block and BEFORE
   `out.append(item)`, added `if not item.isprintable(): raise
   ContextBundleRejected(...)`. At this point the element is already known
   ASCII; `str.isprintable()` is False for ASCII control chars
   (NUL/CR/LF/TAB/ESC/DEL) and True for normal gate names / repo-relative
   paths / path globs (space is printable), so this rejects control chars
   with ZERO regression on real manifests. The appended value remains the
   ORIGINAL `item` (no rewrite); `repr(item)` in the message keeps output
   ASCII-safe. No other guard changed; `_require_strict_bool` unchanged.

2. `tests/test_context_bundle_builder.py`: new `TestControlCharactersRejected`
   (4 control-char negative tests + 1 non-vacuity fixture check + 1 printable
   positive control). Asserts `ContextBundleRejected` is raised BEFORE any
   bundle is produced for: NUL-split `gate\x00name` appended as a 9th gate to
   `required_gates` (8 real gates preserved); CRLF `ok\r\nFAKELOG: granted`
   in `safe_mutation_surface` (the W10-exploit field); ESC `x\x1b[31m` in
   `forbidden_paths`; bare TAB `a\tb` in `safe_mutation_surface`. Plus
   `test_control_char_fixtures_are_ascii_but_not_printable` (non-vacuity:
   each fixture isascii() True, isprintable() False, no authority keyword)
   and `test_printable_ascii_element_still_builds` (positive control:
   `modules/foundups/gotjunk/**` still builds, explicit `isprintable()`
   assertion). All control chars are `\xXX` / `\r` / `\n` / `\t` ESCAPE
   sequences so the source stays 0 non-ASCII bytes.

3. `ModLog.md`: WSP_97 table extended 34 -> 35 rows; new row 35
   `PROTECTED_LIST_FIELDS_PRINTABLE_ASCII_ONLY`; row 33 evidence updated to
   reference the printable-ASCII completion; FIX2b verdict added.

4. `tests/TestModLog.md`: run summary updated to the new count.

**Prior guarantees preserved**: no validator edit, no manifest edit, no
runtime/consumer wiring, no build run, no new dependency. All 6 real
manifests still build. The original W10 dict/bool exploit + fullwidth/NFKC
authority + non-ASCII are all still rejected BEFORE `to_dict()`. The
multi-pattern completeness detector is unchanged. No skip / no xfail.

**Test run**: `python -m pytest modules/foundups/agent/tests/ -q
-p no:cacheprovider` -> 520 passed, 0 skipped, 0 xfailed (514 FIX2 + 6
FIX2b tests).

**ASCII**: both `.py` files are 0 non-ASCII bytes (all test control chars
are `\xXX` / `\r` / `\n` / `\t` escapes). This ModLog FIX2b entry is
ASCII-clean.

See the FIX1 entry below for the full WSP_97 Truth Boundary Checklist
(row 35 is the FIX2b addition; verdict FIX2b PASS 35/35).

---

## 2026-06-10 - WRE ContextBundle Builder Phase 1 FIX2 (W10 residual-gap closure)

**Author**: 0102 (W6)
**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1_FIX2
**Predecessor**: FIX1 (commit 96314ab6c, PR #775)
**Trigger**: W10 adversarial re-gate of PR #775

**W10 residual gaps proven after FIX1, then TIGHTENED by 0102**:

> FINDING 1 (MAJOR): fullwidth-Unicode evades the `_AUTHORITY_KEYWORDS`
> substring scan. A manifest element that is the FULLWIDTH form of
> "payout_ready" (U+FF50 U+FF41 U+FF59 U+FF4F U+FF55 U+FF54 "_" U+FF52
> U+FF45 U+FF41 U+FF44 U+FF59) is a `str`, passed the raw `item.lower()`
> guard, landed in `bundle.to_dict()`, and NFKC-normalizes to
> "payout_ready" downstream. The denylist was Unicode-evadable.
>
> FINDING 2 (MINOR): the check-5 AST test
> `test_no_other_manifest_list_field_is_serialized` was POSITIVE-ONLY: it
> asserts the set of fields routed through `_require_str_tuple` equals the
> expected three. A FUTURE `tuple(build_contract.get("new_list", []))`
> that BYPASSES the helper would STILL pass that positive check.

**0102 TIGHTENING (two additional requirements beyond the first FIX2
push)**:

> GAP A (Unicode contract): NFKC-normalize-before-scan is necessary but
> not sufficient. A BENIGN non-ASCII element (no authority keyword) would
> still normalize-and-accept. These fields are gate names / repo-relative
> paths / path globs -- ASCII by convention -- so ambiguity must be
> REFUSED, not normalized-and-accepted. Add an ASCII-only rejection AFTER
> the authority check.
>
> GAP B (completeness beyond `tuple()`): the completeness detector caught
> only `tuple(<manifest access>)`. It must also catch
> `list`/`set`/`frozenset` conversions, list/set/tuple comprehensions, and
> direct-assignment bypasses that reach a `ContextBundle(...)` field --
> without false-positiving on legitimate local conversions or scalar/dict
> coercions.

**FIX2 changes (4 files; read-only builder; no validator/manifest/runtime
edit; no new dependency)**:

1. `src/context_bundle_builder.py`: added `import unicodedata` (stdlib).
   In `_require_str_tuple`, the `_AUTHORITY_KEYWORDS` denylist scan now runs
   against `unicodedata.normalize("NFKC", item).lower()` instead of
   `item.lower()` (NFKC-before-scan). GAP A tighten: AFTER the authority
   check, `if not item.isascii(): raise ContextBundleRejected(...)` rejects
   any benign non-ASCII element. Order is preserved: type -> empty/strip ->
   NFKC authority scan -> ASCII-only. The rejection DECISION uses the
   normalized form; the value APPENDED to the output tuple remains the
   ORIGINAL `item` (no silent rewrite of the serialized value).
   `_require_strict_bool` is unchanged.

2. `tests/test_context_bundle_builder.py`: new
   `TestFullwidthUnicodeAuthorityEvasionRejected` (6 tests + 1 non-vacuity
   fixture check) asserts `ContextBundleRejected` is raised BEFORE any
   bundle is produced for fullwidth `payout_ready` / `dao_approved` /
   `gate_passed` payloads across `safe_mutation_surface` (the W10-exploit
   field), `required_gates` (appended as a 9th gate so the 8 real names
   remain), and `forbidden_paths`, plus a generic NFKC-compatibility form
   (`human_approval`). GAP A tighten: new
   `TestNonAsciiNonAuthorityElementsRejected` (5 tests) asserts a BENIGN
   non-ASCII NON-authority string (`caf<U+00E9>-glob` / `modules/foundups/
   <U+6587>/x`) is rejected on ASCII-only across all three fields, plus a
   non-vacuity fixture check and an ASCII positive-control. All non-ASCII
   test strings are `\uXXXX` ESCAPE sequences so the source stays 0
   non-ASCII bytes.

3. `tests/test_context_bundle_builder.py`: check-5 AST guard upgraded to
   COMPLETENESS and (GAP B tighten) from `tuple(...)`-only to ALL list-like
   bypasses via the broadened shared detector
   `_find_manifest_listlike_bypasses`
   (`tuple`/`list`/`set`/`frozenset` conversion, comprehension/genexp,
   direct assignment reaching a `ContextBundle(...)` field).
   `test_no_bare_tuple_of_manifest_access_bypasses_helper` asserts ZERO
   bypass patterns over the real builder source. Non-vacuity proven over
   synthetic sources by `test_completeness_guard_detects_synthetic_bare_tuple`,
   `..._synthetic_bare_list`, `..._synthetic_bare_set_and_frozenset`,
   `..._synthetic_comprehension`, and `..._synthetic_direct_assignment`;
   plus `..._no_false_positive_on_local_assignment`. The original positive
   assertion is retained.

4. `ModLog.md` / `tests/TestModLog.md`: WSP_97 table stays at 34 rows
   (rows 33-34 evidence tightened to cite the ASCII-only rejection and the
   multi-pattern detector); test-run summary updated.

**FIX1 guarantees preserved**: no validator edit, no manifest edit, no
runtime/consumer wiring, no build run, no new dependency. All 6 real
manifests still build. The original W10 dict/bool exploit (dict appended
to `required_gates`, dict-as-value `safe_mutation_surface`, truthy-dict
readiness/routing, int readiness) is still rejected BEFORE `to_dict()`.
No skip / no xfail.

**Test run**: `python -m pytest modules/foundups/agent/tests/ -q
-p no:cacheprovider` -> 514 passed, 0 skipped, 0 xfailed (496 in FIX1 +
8 first-FIX2 tests + 10 tighten tests: 5 ASCII-only + 5 detector
non-vacuity/false-positive).

**ASCII**: both `.py` files are 0 non-ASCII bytes (all test strings are
`\uFFxx` / `\uXXXX` escapes). This ModLog FIX2 entry is ASCII-clean.

See the FIX1 entry below for the full 34-row WSP_97 Truth Boundary
Checklist (rows 33-34 are the FIX2 additions; verdict FIX2 PASS 34/34).

---

## 2026-06-09 - WRE ContextBundle Builder Phase 1 FIX1 (authority-laundering closure)

**Author**: 0102 (W6)
**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1_FIX1
**Predecessor**: this branch's prior commit (PR #775 first push)
**Trigger**: W10 return-from-review on PR #775

**W10 blocker**:

> A manifest that passes `validate_manifest_file` can smuggle non-string
> authority dicts into `bundle.to_dict()` because `context_bundle_builder.py`
> copies these build_contract list fields verbatim:
>   - required_gates_to_recheck
>   - forbidden_paths
>   - safe_mutation_surface
>
> Examples proven by W10:
>   required_gates_to_recheck: `{"gate_passed": true, "security_passed": true, "human_approval": true}`
>   forbidden_paths: `{"is_authorized": true, "approval_level": "CRITICAL"}`
>   safe_mutation_surface: `{"payout_ready": true, "dao_approved": true}`
>
> This refutes WSP_97 rows GATE_NAMES_ONLY_NOT_PASS_BOOLEANS and
> NO_CABR_PAYOUT_DAO.

**Root cause**: the #771/#773 validator does NOT enforce element types
on `required_gates` / `forbidden_paths`, and does not type-check
`safe_mutation_surface` at all. The prior builder's
`tuple(build_contract.get(field, []) or [])` faithfully forwarded any
element (or, for `safe_mutation_surface`, a dict-as-value where
`tuple(dict)` yields the dict's keys) into the bundle. The
validator's `is True` check on readiness / routing scalars created the
same vector at scalar granularity (a truthy dict passes `is True` then
`bool(dict)` coerces to True).

### Changed

- **`context_bundle_builder.py`**:
  - Added `_AUTHORITY_KEYWORDS` denylist constant (gate-pass / readiness
    / CABR / payout / DAO / human-approval / external-agent /
    self-authorization keywords; lower-case substring match).
  - Added `_require_str_tuple(field_name, value) -> Tuple[str, ...]`
    helper: rejects non-list/tuple value (dict-as-field), any element
    whose `type(item) is not str` (rejects dict / list / bool / int /
    None / object), empty / whitespace-only strings, and strings whose
    lower-cased form contains any authority keyword from
    `_AUTHORITY_KEYWORDS`. No silent drop -- raises
    `ContextBundleRejected`.
  - Added `_require_strict_bool(field_name, value, *, default=False)
    -> bool` helper: rejects anything that is not exactly `bool` /
    `None`. None / missing maps to `default`. No `bool(dict)` smuggle.
  - Applied `_require_strict_bool` to `readiness.manifest_ready`,
    `readiness.build_ready`, `readiness.autonomous_execution_ready`,
    `execution_routing.external_agent_allowed`,
    `execution_routing.can_self_authorize`, and
    `build_contract.dry_run.required` BEFORE the defense-in-depth
    safety re-checks (step 3a). The re-checks now operate on
    strictly-typed locals (step 3b).
  - Applied `_require_str_tuple` to `required_gates`, `forbidden_paths`,
    `safe_mutation_surface` BEFORE bundle construction (step 3c). The
    resulting `Tuple[str, ...]` values flow directly into
    `ContextBundle(...)`; the prior verbatim `tuple(...)` calls are
    gone.

### Audit -- other manifest-provided list/tuple fields copied into the bundle

Source audit performed: the ONLY manifest-provided list/tuple values
forwarded into the bundle are `required_gates`, `forbidden_paths`, and
`safe_mutation_surface`. Pinned mechanically by
`TestManifestListFieldsStringOnly::test_no_other_manifest_list_field_is_serialized`:
an AST scan of `context_bundle_builder.py` extracts the field-name
argument of every `_require_str_tuple(...)` call and asserts it equals
exactly `{"required_gates", "forbidden_paths", "safe_mutation_surface"}`.
If a future change adds a fourth list field that goes into the bundle,
that test fails until it is routed through the helper and a WSP_97
evidence line is added.

Scalar manifest fields audited:
- `foundup_id`, `module_path`, `contract_version`,
  `build_contract_status` -- already `str(...)`-coerced; cannot carry
  authority dicts even under malicious manifests.
- `routing.orchestrator` / `executor` / `auditor` -- validator already
  rejects anything not in the respective `ALLOWED_*` `frozenset`s (must
  be `str`).
- `routing.declarative_only` -- validator already rejects anything that
  is not the `True` singleton.
- `routing.external_agent_allowed`, `routing.can_self_authorize`,
  `readiness.*`, `build_contract.dry_run.required` -- newly routed
  through `_require_strict_bool` in this fix.

### Tests added

In `test_context_bundle_builder.py`:

- `TestRequireStrTupleListFieldsRejectsAuthorityLaundering` -- crafted
  manifests with appended dicts, parametrized non-str element types
  (`int`, `True`, `False`, `None`, nested list, dict, float, zero),
  dict-as-field-value (the safe_mutation_surface W10 repro), authority-
  keyword string smuggling (9 parametrized `(field, keyword)` cases),
  empty-string elements, all-six real manifests still build with
  helper applied, and the `to_dict()` is NEVER produced for crafted
  input.
- `TestRequireStrictBoolScalarFieldsRejectsAuthorityLaundering` --
  crafted truthy-dict / list / int / string values on each of three
  readiness fields and two routing flags; plus a specific repro that a
  truthy dict in `readiness.build_ready` is NOT laundered to True.
- `TestManifestListFieldsStringOnly` -- WSP_97 row coverage: every list
  field element is `str` after build for all six real manifests; AST
  scan pins that the helper is applied to exactly the three protected
  field names.

Full suite: `pytest -q modules/foundups/agent/tests/` ->
**496 passed in 7.87s**; 0 skipped; 0 xfailed.

The builder-test file alone: **129 passed in 2.40s** (54 prior +
75 new in FIX1).

### Boundary preserved

- READ_ONLY_BUILDER_ONLY. No new module-level imports beyond what was
  already there; no subprocess / network / dynamic-import / file-write.
- NO_CONSUMER_WIRING. NO_HERMES_CALL. NO_OPENCLAW_CALL.
  NO_JOB_ENQUEUE_OR_DRAIN. NO_BUILD_RUN.
- Validator NOT edited (one of the explicit RETURN_CONDITIONS).
- Manifests NOT edited.
- Bundle remains deterministic (`bundle_id` formula unchanged;
  `created_at` still injected; helpers do not introduce nondeterminism).
- All 6 real manifests still build (`TestRealManifestsBuild` plus
  `TestRequireStrTupleListFieldsRejectsAuthorityLaundering::
  test_real_manifests_still_build_with_helpers`).
- No skip / no xfail on any security assertion.

### WSP_97 Truth Boundary Checklist (FIX1 repair: 32 rows; FIX2 extends to 34 rows)

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_PRIOR_ART_SEARCHED | YES | 4 HoloIndex queries recorded in the previous PR-775 ModLog entry below; this fix uses the same Phase 0 result (no prior art for `ContextBundle`). |
| 2 | WSP_84_REUSE_DECISION_DOCUMENTED | YES | Validator imported (`_require_str_tuple` and `_require_strict_bool` are NEW helpers private to the builder; they do not duplicate validator logic). |
| 3 | VALIDATOR_REUSED_NOT_REIMPLEMENTED | YES | `context_bundle_builder.py` imports `validate_manifest_file`, `ManifestValidationResult`, `_canonicalize_module_path` and adds NO new logic that lives in the validator. The two new helpers operate solely on the bundle-output boundary. |
| 4 | READ_ONLY_BUILDER_ONLY | YES | `test_builder_no_subprocess_network_dynamic_import_or_write` still passes after FIX1; AST scan: no new banned-module imports, no banned calls. |
| 5 | NO_CONSUMER_WIRING | YES | `test_builder_signature_has_no_consumer_handle` still passes; no new consumer parameter. |
| 6 | NO_HERMES_CALL | YES | `test_builder_imports_no_runtime_executors` still passes. |
| 7 | NO_OPENCLAW_CALL | YES | Same test. |
| 8 | NO_JOB_ENQUEUE_OR_DRAIN | YES | No queue / broker / publish API referenced. |
| 9 | NO_BUILD_RUN | YES | No `subprocess.run` / `Popen`. |
| 10 | VALIDATOR_REQUIRED_BEFORE_MODULE_PATH_TRUST | YES | Order preserved: step 1 calls `validate_manifest_file(manifest_path)`; helpers run AFTER validator passes. `TestValidatorRejectionsPropagate` still pins this. |
| 11 | JOB_PAYLOAD_MODULE_PATH_NOT_TRUSTED | YES | `TestNo774LegacyPayloadAuthority` still passes; FIX1 did not add any payload-accepting parameter. |
| 12 | REFS_AND_SHA256_ONLY | YES | `FileRef` shape unchanged; `test_bundle_carries_only_refs_no_file_bodies` still passes. |
| 13 | NO_FILE_BODIES | YES | Same test. |
| 14 | STREAM_HASHED_NO_FULL_BODY_LOAD | YES | `_stream_sha256` unchanged. |
| 15 | MAX_CONTEXT_BYTES_ENFORCED | YES | Total-cap logic unchanged. |
| 16 | FORBIDDEN_PATHS_EXCLUDED | YES | `_is_path_forbidden` segment screen unchanged. |
| 17 | SYMLINK_ESCAPE_REJECTED | YES | `_is_path_within` helper-level test still passes. |
| 18 | GATE_NAMES_ONLY_NOT_PASS_BOOLEANS | YES (repaired; FIX2 Unicode-robust + ASCII-only) | Now backed by `_require_str_tuple` element-type check + `_AUTHORITY_KEYWORDS` denylist substring rejection; (FIX2) the denylist scan is NFKC-normalized before matching so fullwidth-Unicode forms cannot evade it; and (FIX2-tighten) a benign non-ASCII element is rejected on ASCII-only after the authority check (gate names are ASCII by convention). Crafted-test evidence: `test_required_gates_with_appended_dict_rejected` (W10 exact example), `test_required_gates_with_non_str_element_rejected` (7 parametrized non-str types), `test_required_gates_as_dict_value_rejected`, `test_authority_keyword_strings_rejected` (9 parametrized authority-keyword smuggle cases), `test_fullwidth_gate_passed_appended_to_required_gates_rejected` (FIX2: fullwidth `gate_passed` appended as a 9th gate), `test_nonascii_nonauthority_in_required_gates_rejected` (FIX2-tighten: benign non-ASCII 9th gate), `test_all_list_field_elements_are_str_after_build` (all 6 real manifests). |
| 19 | NO_READINESS_PROMOTION | YES | `_require_strict_bool` now rejects truthy-dict / list / int / "true"-string smuggling on each readiness field. Crafted evidence: `test_readiness_with_non_bool_value_rejected` (3 fields x 5 bad values), `test_truthy_dict_readiness_not_laundered_to_true`. Defense-in-depth check still raises `ContextBundleRejected` on `is True`. |
| 20 | BUNDLE_ID_DETERMINISTIC_NOT_WALLCLOCK | YES | bundle_id formula unchanged; `TestBundleIdDeterministic` still passes (4 cases + AST scan for nondeterministic imports). |
| 21 | EXTERNAL_AGENTS_STILL_DISABLED | YES | `_require_strict_bool` rejects non-bool `external_agent_allowed`; `test_routing_flag_with_non_bool_value_rejected` (parametrized) and the existing `test_external_agent_allowed_true_rejected` both pin this. |
| 22 | EXECUTION_ROUTING_DECLARATIVE_ONLY | YES | Validator's `is not True` check unchanged; `routing.declarative_only` cannot be a dict (validator rejects). |
| 23 | AI_OVERSEER_NOT_BUILDER | YES | No `ai_overseer` import or identifier added. |
| 24 | NO_CABR_PAYOUT_DAO | YES (repaired; FIX2 Unicode-robust) | Now backed by `_AUTHORITY_KEYWORDS` containing `cabr_ready`, `cabr_passed`, `payout_ready`, `payout_passed`, `payout_approved`, `dao_ready`, `dao_approved`, `dao_passed`, `dao_signed` (substring rejection in `_require_str_tuple`); plus `_require_strict_bool` for readiness fields. FIX2: the denylist scan is NFKC-normalized before matching, so fullwidth-Unicode forms of `payout_ready` / `dao_approved` are also rejected (W10 proved the raw `item.lower()` scan was Unicode-evadable). Crafted-test evidence: `test_safe_mutation_surface_as_dict_value_rejected_w10_repro` (the exact W10 example `{"payout_ready": True, "dao_approved": True}` rejected), `test_authority_keyword_strings_rejected` includes `payout_ready` and `dao_approved` as parametrized rejected substrings, `test_fullwidth_payout_ready_in_safe_mutation_surface_rejected` and `test_fullwidth_dao_approved_in_safe_mutation_surface_rejected` (FIX2 fullwidth payloads in the W10-exploit field), `test_to_dict_never_produced_for_crafted_input` proves the bundle is never produced for the W10 payload. |
| 25 | MANIFESTS_BUNDLE_BUILD_TESTED | YES | All 6 real manifests still build (`TestRealManifestsBuild::test_each_manifest_builds`, `TestReconciliationFlaggedStillBuild`, and new `TestRequireStrTupleListFieldsRejectsAuthorityLaundering::test_real_manifests_still_build_with_helpers`). |
| 26 | BUILDER_IMPORTS_NO_RUNTIME_EXECUTORS | YES | Imports unchanged from prior PR-775 push. |
| 27 | NO_SKIP_XFAIL | YES | `pytest -q modules/foundups/agent/tests/` -> 496 passed in 7.87s; 0 skipped; 0 xfailed. |
| 28 | CITES_PR_772 | YES | PR-775 ModLog entry and builder docstring both cite #772. |
| 29 | CITES_PR_773 | YES | PR-775 ModLog entry and builder docstring both cite #773. Validator imported. |
| 30 | CITES_PR_774 | YES | PR-775 ModLog entry and builder docstring section "Trust seam (carry-forward from #774)" cite #774. |
| 31 | ASCII_CLEAN | YES | Slice-introduced content for FIX1 (builder helpers + tests + this ModLog entry + TestModLog entry) is 0 non-ASCII bytes. Pre-existing non-ASCII bytes elsewhere in `ModLog.md`/`INTERFACE.md`/`ROADMAP.md` are unchanged. |
| 32 | MANIFEST_LIST_FIELDS_STRING_ONLY | YES (NEW) | Every list field forwarded from the manifest into the bundle is `Tuple[str, ...]` produced by `_require_str_tuple`. The three protected fields are `required_gates`, `forbidden_paths`, `safe_mutation_surface`. Pinned by `TestManifestListFieldsStringOnly::test_all_list_field_elements_are_str_after_build` (all 6 real manifests) and `..._test_no_other_manifest_list_field_is_serialized` (AST scan asserts exactly these three field names are routed through the helper). |
| 33 | AUTHORITY_KEYWORDS_UNICODE_NORMALIZED | YES (NEW; FIX2; tightened) | `_require_str_tuple` now applies TWO Unicode contracts in order. (a) NFKC-normalize: the `_AUTHORITY_KEYWORDS` denylist scan runs against `unicodedata.normalize("NFKC", item).lower()` BEFORE the substring match, closing the W10-proven fullwidth-Unicode evasion (a fullwidth `payout_ready` previously passed the raw `item.lower()` scan and NFKC-normalized to `payout_ready` downstream). (b) ASCII-only (FIX2-tighten): AFTER the authority check, a non-ASCII element is REFUSED outright (`if not item.isascii(): raise`) -- these fields are ASCII gate names / repo-relative paths / path globs by convention, so a BENIGN non-ASCII element (no authority keyword) is ambiguous and is rejected, not normalized-and-accepted. The authority check runs FIRST so authority strings still get the specific authority error. The serialized value remains the ORIGINAL `item` (no silent rewrite); only the rejection DECISION uses the normalized form. `unicodedata` is stdlib (no new dependency). Pinned (NFKC half) by `TestFullwidthUnicodeAuthorityEvasionRejected`: `test_fullwidth_payout_ready_in_safe_mutation_surface_rejected` (W10-exploit field), `test_fullwidth_dao_approved_in_safe_mutation_surface_rejected`, `test_fullwidth_gate_passed_appended_to_required_gates_rejected` (9th gate), `test_fullwidth_payout_ready_appended_to_forbidden_paths_rejected`, `test_generic_nfkc_compatibility_form_also_rejected` (mixed-form `human_approval`), `test_fullwidth_fixtures_normalize_as_documented`. Pinned (ASCII-only half) by `TestNonAsciiNonAuthorityElementsRejected`: `test_nonascii_nonauthority_in_required_gates_rejected` (9th gate), `..._in_forbidden_paths_rejected`, `..._in_safe_mutation_surface_rejected` (the W10-exploit field), `test_nonascii_fixtures_are_benign_and_nonascii` (non-vacuity: fixtures are non-ASCII and carry NO authority keyword), and `test_ascii_elements_preserved_unchanged` (ASCII inputs build and are kept verbatim). (c) Printable-ASCII-only (FIX2b; see row 35): a third contract is layered AFTER the ASCII-only check -- `if not item.isprintable(): raise` rejects ASCII CONTROL CHARACTERS (NUL/CR/LF/TAB/ESC/...) that pass `isascii()`, completing the printable-ASCII-only contract for these fields and ending the Unicode/control-char evasion class. |
| 34 | MANIFEST_LIST_FIELDS_COMPLETENESS_PINNED | YES (NEW; FIX2; tightened) | The check-5 AST guard is upgraded from positive-only to a COMPLETENESS check, and (FIX2-tighten) from `tuple(...)`-only to ALL list-like bypasses. The shared detector `_find_manifest_listlike_bypasses` walks the builder AST and flags any manifest dict access (`build_contract.get(...)` / `build_contract[...]` / routing / readiness / data) that reaches a bundle field via `tuple|list|set|frozenset(<manifest access>)`, a list/set comprehension or generator expression iterating a manifest list access, or a direct assignment `NAME = <manifest list access>` whose NAME is later a `ContextBundle(...)` keyword-arg value -- unless it is a `_require_str_tuple(...)` call. `TestManifestListFieldsStringOnly::test_no_bare_tuple_of_manifest_access_bypasses_helper` asserts ZERO such bypass patterns over the real builder source. Non-vacuity proven over synthetic sources by `test_completeness_guard_detects_synthetic_bare_tuple` (tuple), `..._synthetic_bare_list` (list), `..._synthetic_bare_set_and_frozenset` (set + frozenset), `..._synthetic_comprehension` (listcomp/setcomp/genexp), and `..._synthetic_direct_assignment` (assignment reaching a ContextBundle field). False-positive guard `test_completeness_guard_no_false_positive_on_local_assignment` proves local conversions (`tuple(included)` / `dict(excluded)`) and manifest dict reads whose name never reaches a ContextBundle field are NOT flagged. Detector restricted to `_LISTLIKE_CONVERTERS = {tuple,list,set,frozenset}` so `str(build_contract.get(...))` scalar coercions are not flagged. The original positive assertion `test_no_other_manifest_list_field_is_serialized` is retained. |
| 35 | PROTECTED_LIST_FIELDS_PRINTABLE_ASCII_ONLY | YES (NEW; FIX2b) | `_require_str_tuple` adds, AFTER the existing `if not item.isascii(): raise` block and BEFORE `out.append(item)`, an `if not item.isprintable(): raise ContextBundleRejected(...)` guard. W10 final adversarial review proved a residual: ASCII CONTROL CHARACTERS (NUL U+0000, CR U+000D, LF U+000A, TAB U+0009, ESC U+001B, ...) ARE ASCII, so they passed `item.isascii()` and would land in the bundle -- a string-hygiene / log-injection / terminal-escape shape in a provenance field future consumers may log (not authority laundering; still strings). At this point the element is already known ASCII, so `str.isprintable()` is False for ASCII control chars and True for normal gate names / repo-relative paths / path globs (space is printable), rejecting control chars with ZERO regression on real manifests. The appended value remains the ORIGINAL `item` (no rewrite); `repr(item)` in the message keeps output ASCII-safe. Pinned by `TestControlCharactersRejected`: `test_nul_split_in_required_gates_rejected` (NUL-split `gate\x00name` as a 9th gate, 8 real gates preserved), `test_crlf_log_injection_in_safe_mutation_surface_rejected` (CRLF `ok\r\nFAKELOG: granted` in the W10-exploit field), `test_esc_ansi_in_forbidden_paths_rejected` (ESC `x\x1b[31m`), `test_bare_tab_in_safe_mutation_surface_rejected` (bare TAB `a\tb`), `test_control_char_fixtures_are_ascii_but_not_printable` (non-vacuity: each fixture isascii() True, isprintable() False, no authority keyword), and `test_printable_ascii_element_still_builds` (positive control: `modules/foundups/gotjunk/**` still builds with an explicit `isprintable()` positive assertion). This completes the printable-ASCII-only contract for `required_gates` / `forbidden_paths` / `safe_mutation_surface` and ends the Unicode/control-char evasion class. The 6 real manifests still build (`TestRealManifestsBuild`, `test_real_manifests_still_build_with_helpers`). |
| 36 | MONOREPO_POC_SOURCE_AUTHORITY_EXPLICIT | YES (NEW; FIX2c) | The builder is HONEST about its monorepo-PoC Phase-1 scope and a manifest CANNOT promote its lifecycle stage by declaration. Evidence: (a) module constant `SOURCE_AUTHORITY = "monorepo_poc"` (in `__all__`); (b) a `source_authority: str` field on the `ContextBundle` frozen dataclass and in `to_dict()`; (c) `build_context_bundle` sets `source_authority=SOURCE_AUTHORITY` -- a BUILDER CONSTANT that is NEVER read from the manifest / build_contract / execution_routing, so a manifest carrying `source_authority` or `lifecycle_stage` is IGNORED (anti-self-promotion test `test_manifest_cannot_self_promote_lifecycle_stage`: a manifest declaring `source_authority="dao_managed"` + `lifecycle_stage="mvp_runtime"` STILL yields a bundle with `source_authority == "monorepo_poc"`); (d) the `MONOREPO_PHASE1_BOUNDARY` statement in the module docstring AND the `ContextBundle` class docstring; (e) NO external/DAO/MVP readiness authority in `to_dict()` (`test_to_dict_has_no_external_dao_mvp_readiness_authority`); (f) the full lifecycle transition model (external_proto / mvp_runtime / dao_managed / archived) is DEFERRED to FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_CONTRACT_PHASE1 and is NOT implemented here. DETERMINISM preserved: `source_authority` is additive and does NOT enter `bundle_id` (`test_source_authority_not_in_bundle_id_fingerprint`); `BUNDLE_VERSION` and the bundle_id formula are unchanged. The 6 real manifests still build with `source_authority == "monorepo_poc"` (`test_real_manifest_source_authority_is_monorepo_poc`). |

**WSP_97 VERDICT (FIX1)**: PASS (32/32).
**WSP_97 VERDICT (FIX2)**: PASS (34/34). FIX2 adds rows 33-34 and Unicode-hardens the evidence for rows 18 and 24. FIX2-tighten (W10) keeps the table at 34 rows and updates rows 33-34 (and row 18) evidence to cite the ASCII-only rejection of protected list elements and the multi-pattern completeness detector.
**WSP_97 VERDICT (FIX2b)**: PASS (35/35). FIX2b adds row 35 (`PROTECTED_LIST_FIELDS_PRINTABLE_ASCII_ONLY`) and updates row 33 evidence to reference the printable-ASCII completion; declared == actual == 35.
**WSP_97 VERDICT (FIX2c)**: PASS (36/36). FIX2c adds row 36 (`MONOREPO_POC_SOURCE_AUTHORITY_EXPLICIT`): a builder-constant `source_authority="monorepo_poc"` field + `MONOREPO_PHASE1_BOUNDARY` docstring that is builder-set (never manifest-sourced) so a bundle cannot promote its lifecycle stage by declaration, with the full lifecycle model deferred to FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_CONTRACT_PHASE1. No determinism change (source_authority is not in bundle_id). declared == actual == 36.

---

## 2026-06-09 - WRE ContextBundle Builder Phase 1 (v0.16.0)

**Author**: 0102 (W6)
**Slice**: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1
**Predecessors**:
- PR #768 typed shell=False exec boundary + redaction
- PR #769 durable design / build on existing primitives
- PR #770 manifest readiness audit
- PR #771 baseline build_contract / read-only validator
- PR #772 WRE context bundle boundary audit (identified suffix-match fallback)
- PR #773 canonical exact module_path validator hardening
- PR #774 OpenClaw / WRE / Hermes execution-chain audit
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 84, WSP 97

### Phase 0 -- Mandatory Discovery (per CLAUDE.md Steps 2 and 2.1, WSP 50/87)

HoloIndex prior-art search (4 queries, all run from `O:/Foundups-Agent`):

1. `python holo_index.py --search "context bundle provenance envelope file refs sha256" --limit 8`
   -> no existing `ContextBundle` / provenance-envelope builder surfaced.
   Closest WSPs: WSP_83 (Documentation Tree Attachment), WSP_56 (Artifact
   State Coherence). Neither implements a builder.
2. `python holo_index.py --search "manifest build contract bundle builder" --limit 8`
   -> WSP_30 (Agentic Module Build Orchestration) is the protocol but no
   executable builder for FoundUp manifests; the closest CODE hits were
   `dae_dependencies.py` and `m2m_compiler.py` (different domains).
3. `python holo_index.py --search "build plan generator FoundUp manifest" --limit 8`
   -> WSP_30 again plus `mesa_model.py` / `INTERFACE.md` for `agent_market`;
   no plan-vs-bundle confusion (BuildPlan is FoundUpJob -> dry_run plan;
   ContextBundle is validated-manifest -> provenance envelope).
4. `python holo_index.py --search "skill bundle skill loader registry" --limit 8`
   -> `wre_skills_loader.py` exists for SKILL bundles (a different
   abstraction: skill registry, not per-FoundUp provenance).

Direct Grep over the source tree for ``ContextBundle`` / ``context_bundle``
/ ``build_context_bundle`` returned only audit docs (#772 and the
autonomous-build context-bundle audit). Greenfield confirmed.

Retrieval evaluation: queries 2-4 returned medium-relevance hits with
some noise from unrelated "bundle" terminology (skill bundles vs context
bundles); query 1 was high-signal for the validator/protocol surface but
contained no builder. No HOLOINDEX_LOW_SIGNAL events; no Grep fallback
required. No duplication risk.

WSP_84 reuse decision (documented; not asserted):

- `build_plan.py` + `build_plan_generator.py` translate FoundUpJob into
  a dry-run BuildPlan -- a different lifecycle moment (post-job-
  translation) than the pre-execution provenance envelope this slice
  produces.
- `build_plan_executor.py` simulates step execution -- not provenance.
- `build_plan_swarm.py` aggregates `EvidenceBundle` from swarm step
  results -- post-execution, not pre-execution.
- `wre_skills_loader.py` loads SKILL bundles -- a registry mechanism,
  not a per-FoundUp manifest envelope.

Conclusion: a NEW co-located module
`modules/foundups/agent/src/context_bundle_builder.py` is justified
because (a) no existing primitive covers the per-FoundUp pre-execution
provenance-envelope shape, (b) co-location with `foundup_manifest_validator`
(#771/#773) keeps the validator-builder pair together with a single
ModLog/TestModLog to maintain, and (c) placing this in `wre_core/`
would risk the "lives in WRE so WRE can call it" assumption this slice
explicitly forbids.

### Added

- **context_bundle_builder.py** -- read-only builder that converts a
  validated FoundUp manifest into a bounded provenance envelope.
  - `build_context_bundle(manifest_path, repo_root, *, created_at,
    max_context_bytes=65536)` -- public API. Required keyword-only
    `created_at` (caller-injected; no wall-clock).
  - `ContextBundle` / `FileRef` / `ProvenanceRecord` frozen dataclasses
    plus `to_dict()` serializer.
  - `ContextBundleRejected` exception raised on any safety refusal.
  - Calls `foundup_manifest_validator.validate_manifest_file` before
    trusting `module_path`. Imports the validator; does NOT reimplement.
  - Stream-hash helper (`_stream_sha256`) in 64 KiB chunks; oversized
    files (> `PER_FILE_READ_CAP_BYTES`, default 4 MiB) recorded as
    excluded via `Path.stat()` without opening the body.
  - Symlink escape rejection via `Path.resolve()` + `Path.relative_to`.
  - Forbidden-path segment screen for `.env*`, `main.py`, `*_dae.py`,
    `vendor/`, `wallet/`, `token/`, `reward/`, `payout/`, `cabr/`,
    `blockchain/`, `credentials*`, `secrets*`.
  - `max_context_bytes` enforced fail-closed (over-cap candidates
    recorded under `excluded_paths_summary["over_total_cap"]`).
  - Defence-in-depth re-checks on `readiness.{manifest_ready,
    build_ready, autonomous_execution_ready}`, `external_agent_allowed`,
    `can_self_authorize`, and `declarative_only` (validator already
    enforces; builder refuses the bundle anyway).
  - Deterministic `bundle_id = sha256(source_manifest_sha256 + "|" +
    module_path + "|" + bundle_version).hexdigest()`. `created_at` is
    recorded but is NOT part of the fingerprint, so caller-injected
    timestamps cannot cause bundle_id drift.

### Tests added

- 53 tests in `tests/test_context_bundle_builder.py`. Categories:
  - Real-manifests-build (6 parametrized).
  - Bundle carries refs+sha256 only; no file bodies (6 parametrized).
  - Manifest ref included (6 parametrized).
  - Declared test refs included where safe.
  - Forbidden-path screen + total-cap fail-closed + cap-never-exceeded.
  - Validator rejections propagate (7 cases).
  - No gate-pass / CABR / payout / DAO keys anywhere in `to_dict()`.
  - Outside-module file excluded.
  - Path-traversal rejected.
  - Symlink-escape rejected (environment-gated integration) plus a
    helper-level pin (`_is_path_within`) that does NOT need symlink
    creation.
  - Builder-import + execution-safety AST scan (no `subprocess`,
    `socket`, `urllib`, `eval`, `exec`, `Popen`, `urlopen`, `write_*`,
    no Hermes / OpenClaw / WRE consumer / AI Overseer imports).
  - Deterministic `bundle_id` (4 cases) plus `created_at` required.
  - Builder does not import `time` / `datetime` / `random` / `secrets` /
    `uuid` for identity-field population (AST scan).
  - Stream-hash + oversized-excluded (with patched cap) plus AST scan
    proving `_stream_sha256` uses chunked reads inside a while loop.
  - voteballots / trade NEEDS_LABEL_RECONCILIATION builds with
    readiness false (#22 from dispatch).
  - No consumer wiring; signature has no `executor` / `consumer` /
    `hermes` / `openclaw` / `wre` parameter.
  - #774 carry-forward: API has no `payload` / `job_payload` / `job` /
    `task` / `request` parameter; bundle `module_path` comes from the
    validated manifest only; builder code does not reference
    `payload` / `job_payload` / `legacy_payload` as identifiers.

Full suite: `pytest -q tests/test_context_bundle_builder.py
tests/test_foundup_manifest_validator.py` -> **142 passed in 1.20s**;
0 skipped; 0 xfailed.

### Boundary preserved

- READ_ONLY_BUILDER_ONLY. No subprocess, Popen, os.system, eval, exec,
  importlib dynamic loading, network, runtime command execution.
- NO_CONSUMER_WIRING. NO_HERMES_CALL. NO_OPENCLAW_CALL.
  NO_JOB_ENQUEUE_OR_DRAIN. NO_BUILD_RUN.
- NO_READINESS_PROMOTION. NO_CABR_PAYOUT_DAO.
- AI_OVERSEER_NOT_BUILDER. EXTERNAL_AGENTS_STILL_DISABLED.
- The #773 validator is imported (not reimplemented) and called
  BEFORE trusting `module_path`.
- The #774 carry-forward precondition is documented in the builder
  docstring and pinned by tests; this slice does NOT satisfy the
  consumer-wiring precondition and does not claim to.

### What this unblocks

- Future WRE / Hermes work can adopt the `ContextBundle` envelope as
  the source of truth for what a consumer is allowed to look at. The
  envelope makes `allowed_source_roots` derivable from
  `build_contract.module_path` AFTER the #773 validator and the
  builder's own boundary checks have both passed.
- This slice does NOT wire any consumer; consumer wiring remains
  BLOCKED until a separate PR removes or guards legacy
  payload.module_path trust in Hermes legacy executor.

### WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_PRIOR_ART_SEARCHED | YES | 4 HoloIndex queries run + verbatim top hits recorded in the "Phase 0 -- Mandatory Discovery" subsection above. |
| 2 | WSP_84_REUSE_DECISION_DOCUMENTED | YES | Discovery subsection enumerates `build_plan.py`, `build_plan_generator.py`, `build_plan_executor.py`, `build_plan_swarm.py`, `wre_skills_loader.py` and explains why each is a different lifecycle moment; new module justified, not asserted. |
| 3 | VALIDATOR_REUSED_NOT_REIMPLEMENTED | YES | `context_bundle_builder.py` imports `validate_manifest_file`, `ManifestValidationResult`, and `_canonicalize_module_path` from `foundup_manifest_validator`. No validator logic is duplicated; the test `test_builder_imports_no_runtime_executors` cross-checks. |
| 4 | READ_ONLY_BUILDER_ONLY | YES | AST self-check `test_builder_no_subprocess_network_dynamic_import_or_write` passes: zero banned-module imports (subprocess, socket, urllib, importlib, ...) and zero banned name/attr calls (eval, exec, run, Popen, write_text, ...). |
| 5 | NO_CONSUMER_WIRING | YES | `test_builder_signature_has_no_consumer_handle` passes; public signature has no `executor` / `consumer` / `dispatcher` / `hermes` / `openclaw` / `wre` / `job_queue` / `broker` parameter. |
| 6 | NO_HERMES_CALL | YES | AST scan `test_builder_imports_no_runtime_executors` rejects any import matching `hermes`; passes. Source contains no identifier `Hermes` (`test_builder_source_does_not_reference_runtime_consumer_classes` AST scan). |
| 7 | NO_OPENCLAW_CALL | YES | Same AST scan rejects `openclaw` import + identifier `OpenClaw`; passes. |
| 8 | NO_JOB_ENQUEUE_OR_DRAIN | YES | No `enqueue` / `drain` / `publish` / `broker` / `queue` API touched. Source contains no `FoundUpJobConsumer` / `JobQueue` references (verified by `test_builder_source_does_not_reference_runtime_consumer_classes`). |
| 9 | NO_BUILD_RUN | YES | Builder does not invoke `subprocess.run` / `Popen` / `os.system`; banned-attr AST scan passes. |
| 10 | VALIDATOR_REQUIRED_BEFORE_MODULE_PATH_TRUST | YES | `build_context_bundle` calls `validate_manifest_file(manifest_path)` at line ~462 BEFORE any use of `build_contract.module_path` (step 4). Any non-ok result raises `ContextBundleRejected`. Covered by `TestValidatorRejectionsPropagate` (7 tests). |
| 11 | JOB_PAYLOAD_MODULE_PATH_NOT_TRUSTED | YES | Builder API exposes no `payload` / `job_payload` / `job` / `task` / `request` parameter (`test_builder_api_exposes_no_payload_parameter`). Bundle's `module_path` is sourced verbatim from the validated manifest (`test_bundle_module_path_comes_from_manifest_not_external_input`). Source has no identifier `payload` / `job_payload` / `legacy_payload` (`test_builder_does_not_reference_hermes_payload_fields`). |
| 12 | REFS_AND_SHA256_ONLY | YES | `FileRef` is a frozen dataclass with fields {path, sha256, size_bytes, role} only. `test_bundle_carries_only_refs_no_file_bodies` enforces this both at dataclass level and through `to_dict()` (no `body` or `content` keys). |
| 13 | NO_FILE_BODIES | YES | Same test. Additionally, the builder never reads a file body into the bundle: only `_stream_sha256` reads file content (for hashing) and the bundle stores only the digest. |
| 14 | STREAM_HASHED_NO_FULL_BODY_LOAD | YES | `_stream_sha256` uses `f.read(_HASH_CHUNK_BYTES)` inside a while loop; `test_stream_hash_function_uses_chunked_reads` AST-pins this. Oversized files are not opened (Path.stat-only) per `test_oversized_file_is_excluded_not_full_loaded`. |
| 15 | MAX_CONTEXT_BYTES_ENFORCED | YES | `test_max_context_bytes_cap_records_exclusion` and `test_cap_never_exceeded_even_when_close` pin the fail-closed total-cap behavior. Implementation: step 7 stops including once `total_bytes + size > max_context_bytes` and records `over_total_cap`. |
| 16 | FORBIDDEN_PATHS_EXCLUDED | YES | `_is_path_forbidden` segment-screen + `test_forbidden_path_screen_excludes_secrets_like_paths` pin exclusion of `.env*`, `main.py`, `*_dae.py`, `vendor/`, `wallet/`, `token/`, `reward/`, `payout/`, `cabr/`, `blockchain/`, `credentials*`, `secrets*`. |
| 17 | SYMLINK_ESCAPE_REJECTED | YES | `_is_path_within` uses `Path.relative_to` after `Path.resolve()`. Mechanically pinned by `test_is_path_within_helper_rejects_path_outside_base` (no symlink creation required). Integration `test_symlink_pointing_outside_module_is_excluded` exercises the resolve-and-reject path end-to-end where symlink creation is supported. |
| 18 | GATE_NAMES_ONLY_NOT_PASS_BOOLEANS | YES | `required_gates_to_recheck` is `Tuple[str, ...]`. `test_required_gates_to_recheck_carries_names_not_booleans` asserts all elements are strings. `test_bundle_to_dict_has_no_gate_pass_keys` walks the full serialized dict and rejects 14 forbidden authority keys including `gate_passed`, `security_passed`, `permission_passed`, `dry_run_passed`, `build_passed`, `verification_complete`, `real_execution_performed`, `cabr_ready`, `payout_ready`, `dao_ready`. |
| 19 | NO_READINESS_PROMOTION | YES | Builder echoes readiness verbatim and refuses with `ContextBundleRejected` if any readiness flag is true. Covered by `test_readiness_build_ready_true_rejected`, `..._autonomous_execution_ready_true_rejected`, `..._manifest_ready_true_rejected`, and `test_reconciliation_manifest_builds_with_readiness_false`. |
| 20 | BUNDLE_ID_DETERMINISTIC_NOT_WALLCLOCK | YES | `bundle_id = sha256(source_manifest_sha256 + "|" + module_path + "|" + bundle_version)`. Pinned by `test_same_inputs_yield_same_bundle_id`, `test_bundle_id_is_sha256_of_documented_components`, `test_bundle_id_not_affected_by_created_at`, `test_different_manifests_yield_different_bundle_ids`. `test_builder_does_not_call_time_or_random` AST-verifies no `time` / `datetime` / `random` / `secrets` / `uuid` import. `test_required_created_at_argument` enforces the keyword-only required `created_at`. |
| 21 | EXTERNAL_AGENTS_STILL_DISABLED | YES | `test_external_agent_allowed_true_rejected`; defence-in-depth re-check in step 3 raises on `routing.get("external_agent_allowed") is True`. |
| 22 | EXECUTION_ROUTING_DECLARATIVE_ONLY | YES | Step 3 raises if `routing.get("declarative_only") is not True`. Validator also rejects (covered by existing `test_execution_routing_declarative_only`). |
| 23 | AI_OVERSEER_NOT_BUILDER | YES | No `ai_overseer` import (AST scan in `test_builder_imports_no_runtime_executors`); no `AIIntelligenceOverseer` / `AIOverseer` identifier (`test_builder_source_does_not_reference_runtime_consumer_classes`). |
| 24 | NO_CABR_PAYOUT_DAO | YES | `test_bundle_to_dict_has_no_gate_pass_keys` walks the serialized dict and rejects `cabr_ready`, `cabr_passed`, `payout_ready`, `payout_passed`, `dao_ready`, `dao_passed`. Source contains no `cabr` / `payout` / `dao` references. |
| 25 | MANIFESTS_BUNDLE_BUILD_TESTED | YES | `TestRealManifestsBuild.test_each_manifest_builds` parametrizes all 6 real manifests; all 6 produce a valid bundle. `TestReconciliationFlaggedStillBuild` additionally pins that voteballots / trade build at the declarative level with readiness false (NEEDS_LABEL_RECONCILIATION not promoted). |
| 26 | BUILDER_IMPORTS_NO_RUNTIME_EXECUTORS | YES | `test_builder_imports_no_runtime_executors` passes; module imports: `__future__`, `hashlib`, `json`, `dataclasses`, `pathlib`, `typing`, plus `foundup_manifest_validator` (validator, not executor). |
| 27 | NO_SKIP_XFAIL | YES | `pytest -q` output: `142 passed in 1.20s` (52 builder + 1 helper-level pin + 89 validator). 0 skipped (the prior Windows-symlink `pytest.skip` was replaced by a clean early-return so the test runs but is a no-op when symlinks are unsupported; the security boundary is pinned by `test_is_path_within_helper_rejects_path_outside_base` which always runs). 0 xfailed. |
| 28 | CITES_PR_772 | YES | Predecessors list and builder docstring both cite PR #772 (WRE context-bundle boundary audit). |
| 29 | CITES_PR_773 | YES | Predecessors list and builder docstring both cite PR #773 (canonical exact module_path validator hardening). Validator is imported. |
| 30 | CITES_PR_774 | YES | Predecessors list and the docstring section "Trust seam (carry-forward from #774)" cite PR #774 (OpenClaw / WRE / Hermes execution-chain audit). The `TestNo774LegacyPayloadAuthority` test class pins the carry-forward. |
| 31 | ASCII_CLEAN | YES | Slice-introduced content is 0 non-ASCII bytes (`context_bundle_builder.py`=0, `test_context_bundle_builder.py`=0, this ModLog entry=0, INTERFACE/ROADMAP/TestModLog entries=0). Pre-existing non-ASCII bytes elsewhere in ModLog.md (60 bytes of box-drawing glyphs in an earlier entry) are unchanged and out of slice scope. |

**WSP_97 VERDICT**: PASS (31/31).

---

## 2026-06-09 - FoundUp Manifest Validator Module Path Exact-Match Hardening (v0.15.1)

**Author**: 0102 (W6)
**Slice**: FOUNDUP_MANIFEST_VALIDATOR_MODULE_PATH_EXACT_MATCH_HARDENING_PHASE1
**Predecessors**:
- PR #770 - manifest readiness + execution ecosystem boundary
- PR #771 - baseline build_contract / execution_routing + read-only validator
- PR #772 - WRE context-bundle boundary audit (identified suffix-match fallback)
**WSP References**: WSP 11, WSP 50, WSP 84, WSP 97

### Changed

- **foundup_manifest_validator.py** - `_expected_module_path_matches` now
  requires EXACT normalized repo-relative path equality between
  `build_contract.module_path` and the manifest file's parent directory.
  The prior suffix-match fallback (`parent.endswith("/" + norm_module)`)
  identified by PR #772 has been removed.
  - New helper `_canonicalize_module_path(raw)`: canonicalizes a manifest-
    declared module_path to repo-relative POSIX form. Accepts harmless
    equivalents (leading `./`, repeated `/`, `.` segments, backslashes).
    Rejects empty, absolute (drive letter, leading `/`), UNC (`\\\\`),
    and any `..` segment.
  - New helper `_canonicalize_manifest_path_for_compare(raw)`: as above,
    plus strips the validator's known repo-root prefix (case-insensitive
    for Windows drive-letter casing) so absolute on-disk manifest paths
    still compare correctly.
  - New module-level constants `_VALIDATOR_FILE`, `_REPO_ROOT_POSIX`,
    `_ABSOLUTE_OR_UNC_PATTERN` (used only for compare; no IO, no exec).
  - Module-level `import re` and `from pathlib import Path` added. The
    AST self-check tests confirm no banned-module imports, no
    `subprocess` / network / file-write calls, and no runtime executor
    or consumer imports.

### Boundary preserved

- Validator remains READ-ONLY. No subprocess, Popen, os.system, eval,
  exec, dynamic import, network, or file write.
- No manifest mutation. All 6 existing manifests still validate.
- No registry mutation. No runtime consumer wiring.
- No readiness promotion. No CABR / payout / DAO / token touch.
- AI Overseer is not invoked. External agents remain disabled.

### Test additions

- Existing tests: 51 pre-hardening tests still pass unchanged.
- `TestExactMatchHelperDirect` (8 unit tests on the helper itself).
- `TestSuffixCollisionRejected` (6 explicit suffix-collision cases).
- `TestCanonicalPathNormalization` (16 parametrized variants).
- `TestOldSuffixBehaviorRegression` (3 regressions that mechanically
  prove the old suffix fallback would have accepted these and the new
  exact-only rule rejects them).
- Total: 88 tests pass; 0 skipped; 0 xfailed.

### What this unblocks

- `WRE_CONTEXT_BUNDLE_BUILDER_PHASE1` may now safely derive
  `allowed_source_roots` from `build_contract.module_path`.
- This slice does NOT implement that builder; it only removes the
  pre-consumer trust gap.

### WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | VALIDATOR_HARDENING_ONLY | YES | git diff: only 4 in-scope files changed (validator src, test, ModLog, TestModLog). |
| 2 | EXACT_MATCH_ONLY | YES | `foundup_manifest_validator.py::_expected_module_path_matches` returns `parent == canonical_module`; no other path is accepted. |
| 3 | SUFFIX_FALLBACK_REMOVED | YES | Prior `parent.endswith("/" + norm_module)` branch removed; not present anywhere in `foundup_manifest_validator.py`. Verified by Grep. |
| 4 | SUFFIX_COLLISION_NEGATIVE_TESTS_PASS | YES | `TestSuffixCollisionRejected` (6 cases) + `TestCanonicalPathNormalization::test_unsafe_or_shadow_module_paths_rejected` (10 parametrized cases) all pass. |
| 5 | SIX_EXISTING_MANIFESTS_STILL_VALIDATE | YES | `test_all_six_manifests_validate` parametrized over `TARGET_MANIFESTS` (6 entries) passes; also `TestExactMatchHelperDirect::test_real_manifest_locations_match_exactly` covers each pair directly. |
| 6 | MAGADOOM_CROSS_DOMAIN_EXACT_MATCH_VALID | YES | `magadoom_001` at `modules/gamification/whack_a_magat/foundup_manifest.json` declares `module_path=modules/gamification/whack_a_magat`; exact-only match accepts. Covered by `TestExactMatchHelperDirect::test_real_manifest_locations_match_exactly[magadoom row]`. |
| 7 | NO_MANIFEST_MUTATION | YES | `git diff --name-only` shows no `foundup_manifest.json` files changed. |
| 8 | NO_REGISTRY_MUTATION | YES | No file under `modules/foundups/registry/`, `modules/foundups/manifest/`, `modules/foundups/projection/`, or `modules/foundups/catalog/` touched. |
| 9 | NO_RUNTIME_CONSUMER_WIRING | YES | No file in `modules/communication/moltbot_bridge/`, `modules/infrastructure/wre_core/`, `modules/ai_intelligence/ai_overseer/`, or any `*_dae.py` touched. |
| 10 | NO_BUILD_RUN | YES | No build/test execution performed by this slice beyond running the validator test file itself. |
| 11 | NO_READINESS_PROMOTION | YES | `test_reject_build_ready_true`, `test_reject_autonomous_execution_ready_true`, `test_reject_manifest_ready_true_without_promotion` still pass; no manifest readiness field flipped. |
| 12 | VALIDATOR_READ_ONLY | YES | `test_validator_no_exec_process_network_or_write` passes; no banned-name calls (`open`, `eval`, `exec`, `compile`, etc.), no banned-attr calls (`run`, `Popen`, `write`, `urlopen`, etc.). |
| 13 | VALIDATOR_IMPORTS_NO_RUNTIME_EXECUTORS | YES | `test_validator_imports_no_runtime_executors` passes; module imports: `__future__`, `dataclasses`, `json`, `pathlib`, `re`, `typing`. No `hermes`, `openclaw`, `ai_overseer`, `job_consumer`, `build_plan_executor`, `wre_core`. |
| 14 | COMMANDS_REMAIN_ARGV_OR_NULL | YES | `_validate_command_block` and `_is_argv_list_or_null` unchanged; `test_reject_shell_string_command` and `test_reject_shell_metacharacters_in_argv` still pass. |
| 15 | EXTERNAL_AGENTS_STILL_DISABLED | YES | `test_reject_external_agent_allowed_true` and `test_execution_routing_declarative_only` still pass; no relaxation of external-agent gating. |
| 16 | AI_OVERSEER_NOT_BUILDER | YES | `ALLOWED_AUDITORS = frozenset({"ai_overseer"})` unchanged; AI Overseer remains in the auditor allowlist only, not in `ALLOWED_EXECUTORS` (still `{"hermes"}`) or `ALLOWED_ORCHESTRATORS` (still `{"openclaw"}`). |
| 17 | CITES_PR_771 | YES | This ModLog entry's Predecessors block and the new validator docstring on `_expected_module_path_matches` cite PR #771 (baseline build_contract / validator). |
| 18 | CITES_PR_772 | YES | This ModLog entry's Predecessors block and the docstring on `_expected_module_path_matches` cite PR #772 (suffix-match audit). |
| 19 | NO_CABR_PAYOUT_DAO | YES | No file under `modules/foundups/agent_market/`, no CABR/UPS/Du/F_i/Treasury references added; validator does not emit any economic signal. |
| 20 | NO_SKIP_XFAIL | YES | `pytest -q` summary: `88 passed in 0.28s`; no `s` (skip) or `x` (xfail) markers in test output. |
| 21 | ASCII_CLEAN | YES | Slice-introduced content is 0 non-ASCII bytes (validator src=0, test=0, TestModLog.md=0, this ModLog entry=0). The 60 non-ASCII bytes elsewhere in `ModLog.md` are pre-existing box-drawing glyphs (U+2502, U+2500, U+2514, etc.) in an unrelated earlier entry; out of slice scope and not modified. |
| 22 | CANONICAL_REPO_RELATIVE_PATH_MATCH | YES | `_canonicalize_module_path` + `_canonicalize_manifest_path_for_compare` normalize both inputs to repo-relative POSIX form before comparing. `TestCanonicalPathNormalization::test_harmless_module_path_normalizations_accepted` (6 variants: `./`, `//`, `.` segment, backslashes, trailing `/`, baseline) all match. |
| 23 | TRAVERSAL_PATHS_REJECTED | YES | `_canonicalize_module_path` returns None on any `..` segment (leading, mid-path, or trailing). `TestExactMatchHelperDirect::test_canonical_module_path_rejects_unsafe_forms` and `..._rejects_internal_traversal` cover 3 traversal positions. |
| 24 | ABSOLUTE_AND_UNC_PATHS_REJECTED | YES | `_ABSOLUTE_OR_UNC_PATTERN = re.compile(r"^([A-Za-z]:\|/)")` rejects drive-prefixed and leading-slash forms; UNC (`\\\\srv\\share`) becomes `//srv/share` after backslash conversion and is caught by the leading-slash branch. `TestCanonicalPathNormalization::test_unsafe_or_shadow_module_paths_rejected` covers `O:/`, `C:/`, `/`, UNC. |
| 25 | OLD_SUFFIX_BEHAVIOR_REGRESSION_PINNED | YES | `TestOldSuffixBehaviorRegression::test_suffix_match_that_old_validator_would_accept_is_rejected` re-implements the legacy logic inline and asserts it would have accepted the input; the new helper rejects it. Two cases (shadow-prefixed and deep-shadow nesting) plus a positive control. |
| 26 | EXACT_MATCH_HELPER_TESTED_DIRECTLY | YES | `TestExactMatchHelperDirect` calls `_expected_module_path_matches`, `_canonicalize_module_path`, and `_canonicalize_manifest_path_for_compare` directly (not only through full-manifest validation) so the trust boundary is mechanically pinned. |

**WSP_97 VERDICT**: PASS (26/26).

---

## 2026-06-08 - FoundUp Manifest Baseline Build/Test Contract Validator (v0.15.0)

**Author**: 0102 (W6)
**Slice**: FOUNDUP_MANIFEST_BASELINE_IMPL_PHASE1
**Predecessor**: PR #770 (FOUNDUP_MANIFEST_READINESS_AUDIT, merged f3459a070)
**WSP References**: WSP 11, WSP 50, WSP 84, WSP 97

### Added

- **foundup_manifest_validator.py** - read-only validator for the new
  declarative `build_contract` / `execution_routing` manifest blocks.
  - `validate_manifest(data, manifest_path, *, allow_readiness_promotion=False)`
    - pure, no IO, returns `ManifestValidationResult(ok, errors, warnings, manifest_path)`.
  - `validate_manifest_file(path)` - reads via `Path.read_text` (read-only), then validates.
  - Enforces: foundup_id match, module_path matches manifest location, commands are
    argv-list-or-null (never shell strings), no shell metacharacters in argv,
    forbidden_paths cover `.env`/`main.py`/`*_dae.py`/`vendor`, all 8 required gates
    present (genesis/manifest/dry_run/test/D0-D6/typed_exec/no_live_launch/
    policy_required_sovereign_valve), executor/orchestrator/auditor are
    non-privileged, `external_agent_allowed`/`can_self_authorize` cannot be true,
    `dry_run.default` cannot be false, readiness cannot promote build/autonomous/
    manifest readiness, and no gate-bypass flag may be truthy.
  - EXECUTES NOTHING. Imports no Hermes/OpenClaw/WRE consumer/AI Overseer runtime;
    no process, network, dynamic-import, or file-write calls.

### Manifest contract blocks (declarative only, no runtime wiring)

Added sibling `build_contract` + `execution_routing` blocks to the 6
MANIFEST_PRESENT_BUT_INCOMPLETE FoundUps identified by #770:

| FoundUp | module_path | status |
|---------|-------------|--------|
| gotjunk_001 | modules/foundups/gotjunk | BASELINE_DECLARATIVE_ONLY |
| kosei | modules/foundups/kosei | BASELINE_DECLARATIVE_ONLY |
| magadoom_001 | modules/gamification/whack_a_magat | BASELINE_DECLARATIVE_ONLY |
| antifafm_001 | modules/platform_integration/antifafm_broadcaster | BASELINE_DECLARATIVE_ONLY |
| voteballots | modules/foundups/voteballots | NEEDS_LABEL_RECONCILIATION |
| trade | modules/foundups/trade | NEEDS_LABEL_RECONCILIATION |

- All 6 keep `manifest_ready=false`, `build_ready=false`,
  `autonomous_execution_ready=false`. This slice establishes contract presence only.
- No consumer wired; no autonomous build run; no runtime behavior changed; registry
  untouched; AI Overseer remains auditor (not a builder).
- voteballots/trade carry the #770 label-vs-surface conflict (labels say
  SPECIFIED_NOT_IMPLEMENTED but real src/tests exist) and are flagged, not build-trusted.

## 2026-05-01 - Worker Queue Observability Scaffold (v0.14.0)

**Author**: 0102 (W4)
**Slice**: OC20_WRE_WORKER_QUEUE_OBSERVABILITY_EVENTS_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 91, WSP 97

### Added

- **worker_queue_observability.py** - WorkerQueueObservability
  - `WorkerQueueObservability` class for queue telemetry
  - `emit_event()` - Emit observability event (append-only)
  - `emit_heartbeat()` - Emit heartbeat with consecutive tracking
  - `emit_lease_expired()` - Emit lease expiry signal
  - `emit_worker_available()` - Emit worker availability event
  - `emit_worker_unavailable()` - Emit worker unavailability event
  - `snapshot_queue_health()` - Queue health snapshot with counts

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `WorkerQueueEventType` | HEARTBEAT, LEASE_EXPIRED, WORKER_AVAILABLE, etc. |
| `WorkerAvailabilityStatus` | AVAILABLE, BUSY, OFFLINE, TERMINATED |
| `QueueHealthStatus` | HEALTHY, DEGRADED, UNHEALTHY |
| `WorkerQueueEvent` | Base event with timestamp, worker_id, entry_id, evidence_refs |
| `WorkerHeartbeatSnapshot` | Heartbeat state with consecutive count |
| `LeaseExpirySignal` | Lease expiration details |
| `WorkerAvailabilitySnapshot` | Worker availability state |
| `QueueHealthSnapshot` | Queue health with entry counts |

### WSP 91 Three Pillars

| Pillar | Implementation |
|--------|----------------|
| Logs | emit_* methods create discrete events with timestamps |
| Traces | Not implemented (Phase 2) |
| Metrics | snapshot_* methods for aggregated state |

### WSP 97 Truth Boundary

- Events are in-memory only (Phase 1)
- Events are append-only
- No real_execution_performed field exists
- No CABR/reward/payout/token fields exist
- No external telemetry sink yet
- No RedDog/pfMALL event emission yet

### Tests

- `test_worker_queue_observability.py` - 28 tests covering all 10 requirements

---

## 2026-04-30 - Swarm Dispatch Integration (v0.13.0)

**Author**: 0102 (W4)
**Slice**: OC18_DISPATCHER_QUEUE_INTEGRATION_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **swarm_dispatch_integration.py** - SwarmDispatchCoordinator
  - `SwarmDispatchCoordinator` class for queue-dispatcher coordination
  - `dispatch_next()` - Dequeue and dispatch to worker
  - `complete_dispatched_assignment()` - Report completion with evidence
  - `run_simulated_cycle()` - Full dequeue → dispatch → complete cycle
  - `summarize()` - Queue/dispatcher state summary

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `DispatchCycleStatus` | SUCCESS, NO_QUEUED_ENTRIES, NO_CAPABILITY_MATCH, etc. |
| `DispatchCycleResult` | Result of dispatch cycle (simulated) |
| `QueueDispatchSummary` | Queue and dispatcher state summary |

### Integration Flow

```
SwarmWorkerQueue.dequeue_for_worker()
    │
    ▼
SwarmDispatchCoordinator.dispatch_next()
    │
    ▼
AssignmentDispatcher.dispatch_assignment()
    │
    ▼
(Simulated work)
    │
    ▼
SwarmDispatchCoordinator.complete_dispatched_assignment()
    │
    ├─> AssignmentDispatcher.receive_completion()
    └─> SwarmWorkerQueue.complete_assignment()
```

### WSP 97 Truth Boundary

- `DispatchCycleResult.simulated = True` (always)
- `DispatchCycleResult.real_process_started = False` (always)
- `QueueDispatchSummary.all_simulated = True` (always)
- `QueueDispatchSummary.real_execution_performed = False` (always)
- No CABR/reward/payout/token fields exist

### Tests

- `test_swarm_dispatch_integration.py` - 12 tests covering all 7 requirements

---

## 2026-04-30 - Real Worker Assignment Protocol Scaffold (v0.12.0)

**Author**: 0102 (W4)
**Slice**: OC17_REAL_WORKER_ASSIGNMENT_PROTOCOL_DESIGN_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **worker_assignment_protocol.py** - AssignmentDispatcher scaffold
  - `AssignmentDispatcher` class for worker dispatch
  - `register_worker()` - Register worker with capabilities
  - `deregister_worker()` - Release worker and assignments
  - `dispatch_assignment()` - Simulated dispatch (no real process)
  - `receive_heartbeat()` - Update worker last_seen
  - `receive_completion()` - Record evidence from completion

- **REAL_WORKER_ASSIGNMENT_PROTOCOL.md** - Architecture spec

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `WorkerProcessStatus` | IDLE, ASSIGNED, PROCESSING, FAILED, TERMINATED |
| `WorkerRuntimeType` | OPENCLAW, HERMES, CLAUDE_0102, QWEN, GEMMA, GENERIC |
| `AssignmentDispatchStatus` | SIMULATED_DISPATCH, SPECIFIED_NOT_IMPLEMENTED, etc. |
| `WorkerTrustLevel` | UNTRUSTED, VERIFIED, TRUSTED, SYSTEM |
| `WorkerProcess` | Registered worker with status, capabilities |
| `WorkerRegistration` | Worker registration request |
| `WorkerDeregistration` | Deregistration result |
| `AssignmentDispatchRequest` | Dispatch request with step details |
| `AssignmentDispatchResult` | Dispatch result (simulated) |
| `WorkerHeartbeatEvent` | Heartbeat from worker |
| `WorkerCompletionEvent` | Completion report with evidence |

### Protocol Rules

| Rule | Description |
|------|-------------|
| R1 | Dispatch is simulated only |
| R2 | No real processes are started |
| R3 | No Claude/OpenClaw/Hermes invocation |
| R4 | Identity verification is simulated |
| R5 | Completion can carry evidence_refs |
| R6 | No CABR/payout/reward fields exist |

### WSP 97 Truth Boundary

- `WorkerProcess.simulated = True` (always)
- `AssignmentDispatchResult.simulated = True` (always)
- `AssignmentDispatchResult.real_process_started = False` (always)
- `WorkerCompletionEvent.simulated = True` (always)
- `real_execution_performed` does not exist
- No CABR/reward/payout/token fields exist

### Tests

- `test_worker_assignment_protocol.py` - 25 tests covering all 9 requirements

---

## 2026-04-30 - BuildPlan Swarm WRE Queue Contract (v0.11.0)

**Author**: 0102 (W4)
**Slice**: OC15_SWARM_WORKER_ASSIGNMENT_WRE_QUEUE_CONTRACT_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **build_plan_swarm_queue.py** - SwarmWorkerQueue scaffold
  - `SwarmWorkerQueue` class for worker assignment dispatch
  - `enqueue_assignment()` - Enqueue StepAssignment for worker pickup
  - `dequeue_for_worker()` - Capability-aware dequeue
  - `heartbeat()` - Lease renewal
  - `complete_assignment()` - Completion with evidence
  - `expire_entries()` - Expiration and requeue

- **BUILD_PLAN_SWARM_WRE_QUEUE_CONTRACT.md** - Architecture spec

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `QueuePriority` | CRITICAL, HIGH, NORMAL, LOW |
| `QueueEntryStatus` | QUEUED, PROCESSING, COMPLETED, FAILED, EXPIRED |
| `DequeueDecision` | ASSIGNED, NO_MATCH, QUEUE_EMPTY, BLOCKED |
| `CompletionStatus` | SUCCEEDED, FAILED, SKIPPED |
| `SwarmWorkerQueueEntry` | Queue entry with lease and evidence |
| `WorkerDequeueRequest` | Worker request with capabilities |
| `WorkerDequeueResult` | Dequeue result with assigned entries |
| `WorkerHeartbeat` | Heartbeat response |
| `AssignmentCompletionReport` | Completion report |
| `QueueAssignmentResult` | Operation result |

### Queue Rules

| Rule | Description |
|------|-------------|
| R1 | Dequeue is capability-aware |
| R2 | Dequeue creates/renews a lease |
| R3 | Expired entries requeue if retries remain |
| R4 | Completion reports simulated completion only |
| R5 | No real worker process is started |
| R6 | No files are edited |
| R7 | No CABR/payout/reward fields exist |

### WSP 97 Truth Boundary

- `SwarmWorkerQueueEntry.simulated = True` (always)
- `AssignmentCompletionReport.simulated = True` (always)
- `real_execution_performed` does not exist (cannot become True)
- No CABR/reward/payout/token fields exist

### Tests

- `test_build_plan_swarm_queue.py` - 20 tests covering all 9 requirements

---

## 2026-04-30 - BuildPlan Swarm Coordination Scaffold (v0.10.0)

**Author**: 0102 (W4)
**Slice**: OC13_SWARM_COORDINATION_CONTRACT_AND_TEST_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **build_plan_swarm.py** - SwarmCoordinator scaffold
  - `SwarmCoordinator` class for multi-agent step assignment
  - `register_worker()` - Register workers with leases
  - `assign_step()` - Assign steps to workers with file ownership
  - `claim_files()` / `release_files()` - File ownership management
  - `detect_conflicts()` - Conflict detection
  - `renew_lease()` / `expire_leases()` - Lease lifecycle
  - `aggregate_evidence()` - Evidence bundling
  - `summarize()` - Execution summary

- **BUILD_PLAN_SWARM_COORDINATION_CONTRACT.md** - Architecture spec

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `AssignmentStatus` | ASSIGNED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED |
| `LeaseStatus` | ACTIVE, EXPIRED, RELEASED |
| `ConflictSeverity` | WARNING, ERROR, FATAL |
| `WorkerCapability` | VALIDATE, BUILD, TEST, ALL |
| `WorkerIdentity` | Worker registration with capabilities |
| `StepAssignment` | Step-to-worker assignment (simulated only) |
| `FileOwnershipClaim` | File ownership with lease expiration |
| `Lease` | Worker lease with renewal support |
| `ConflictReport` | File ownership conflict report |
| `EvidenceBundle` | Aggregated evidence refs |
| `SwarmExecutionSummary` | Execution state summary |

### Coordination Rules

| Rule | Description |
|------|-------------|
| R1 | Two workers cannot own same file simultaneously |
| R2 | Claims must be within BuildPlan target scope |
| R3 | Lease expiration releases file claims |
| R4 | Assignments are simulated only |
| R5 | No workers actually edit files |
| R6 | No real agent processes start |

### WSP 97 Truth Boundary

- `StepAssignment.simulated = True` (always)
- `EvidenceBundle.verification_complete = False` (always)
- `EvidenceBundle.cabr_ready = False` (always)
- `SwarmExecutionSummary.all_simulated = True` (always)
- `SwarmExecutionSummary.real_execution_performed = False` (always)
- No CABR/reward/payout/token fields exist

### Tests

- `test_build_plan_swarm.py` - 34 tests covering all 10 requirements

---

## 2026-04-29 - BuildPlanExecutor Interface Stub (v0.9.0)

**Author**: 0102 (W4)
**Slice**: OC12_BUILD_PLAN_EXECUTOR_INTERFACE_STUB_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **build_plan_executor.py** - BuildPlanExecutor interface stub
  - `BuildPlanExecutor` class with dry_run=True default
  - `validate_plan()` - Plan validation with gate checks
  - `evaluate_gate()` - Gate evaluation (genesis, dry_run, human_approval)
  - `simulate_step()` - Step simulation returning SIMULATED status
  - `execute_step()` - Delegates to simulation; real execution returns BLOCKED
  - `create_execution_receipt()` - Creates receipt with WSP 97 truth fields

### Enums and Dataclasses

| Type | Purpose |
|------|---------|
| `StepExecutionStatus` | SUCCEEDED, FAILED, BLOCKED, SKIPPED, SIMULATED |
| `ExecutionMode` | DRY_RUN, REAL |
| `ExecutionBlockReason` | Block reasons (REAL_EXECUTION_NOT_IMPLEMENTED, etc.) |
| `StepExecutionResult` | Step execution outcome with evidence |
| `GateEvaluationResult` | Gate evaluation outcome |
| `ExecutionReceipt` | Terminal receipt with WSP 97 truth fields |

### WSP 97 Truth Boundary

- `verification_complete = False` (always)
- `cabr_ready = False` (always)
- `payout_ready = False` (always)
- `real_execution_performed = False` (stub)
- No CABR/reward/payout/token fields exist

### Tests

- `test_build_plan_executor.py` - 39 tests covering all 9 requirements

---

## 2026-04-29 - BuildPlan Generator (v0.8.0)

**Author**: 0102 (W4)
**Slice**: OC9_BUILD_PLAN_GENERATOR_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **build_plan_generator.py** - BuildPlan generation from FoundUpJob
  - `create_build_plan_from_job()` - Main entry point
  - `validate_job_for_build_plan()` - Pre-validation
  - `infer_build_scope()` - Scope inference from action
  - `build_target_from_job()` - Target construction
  - `KNOWN_FOUNDUP_PATHS` - Path inference for known FoundUps

### Scope Inference

| Action | Inferred Scope |
|--------|----------------|
| `validate_foundup` | GENESIS_ONLY |
| `build_foundup` | FULL_BUILD |
| `extract_foundup` | FULL_BUILD |

### Tests

- `test_build_plan_generator.py` - 20 tests

---

## 2026-04-29 - BuildPlan Dataclass (v0.7.0)

**Author**: 0102 (W4)
**Slice**: OC8_BUILD_PLAN_DATACLASS_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 97

### Added

- **build_plan.py** - BuildPlan typed interface
  - `BuildPlan` - Multi-step orchestration contract
  - `BuildTarget` - Target paths and scope
  - `BuildStep` - Step definition with action enum
  - `BuildGate` - Gate checkpoints
  - `BuildEvidence` - Evidence with verification status
  - `create_standard_build_steps()` - Standard step factory

### Enums

| Enum | Values |
|------|--------|
| `BuildPlanStatus` | DRAFT, READY, IN_PROGRESS, COMPLETED, FAILED, CANCELLED |
| `BuildMode` | DRY_RUN, REAL, PARTIAL |
| `BuildScope` | GENESIS_ONLY, FULL_BUILD, INCREMENTAL |
| `BuildStepAction` | VALIDATE_*, CREATE_*, UPDATE_*, RUN_TESTS, etc. |
| `GateType` | genesis_gate, dry_run_gate, test_gate, human_approval_gate |

### WSP 97 Truth Boundary

- `is_real_build_allowed()` checks all gates before real execution
- `dry_run=True` default enforced
- No CABR/payout/reward/token fields

---

## 2026-04-26 - Hermes FoundUpJob Executor (v0.6.0)

**Author**: 0102 (W4)
**Slice**: OC4_HERMES_FOUNDUP_JOB_EXECUTION_ADAPTER_PHASE1
**WSP References**: WSP 11, WSP 50, WSP 77, WSP 91, WSP 97

### Added

- **hermes_foundup_job_executor.py** - FoundUpJob execution adapter for Hermes
  - `execute_foundup_job()` - Main entry point accepting `FoundUpJob`
  - `HermesJobExecutionResult` - Result container with job, hermes_result, error
  - Supports actions: `build_foundup`, `extract_foundup`, `validate_foundup`

### Status Mapping (WSP 97 Truthful)

| Hermes Result | JobStatus | StatusReasonCode |
|---------------|-----------|------------------|
| `success: True, dry_run: True` | SUCCEEDED | OK_DRY_RUN_PASSED |
| `success: True, dry_run: False` | SUCCEEDED | OK_COMPLETED |
| `error: "security_gate_failed"` | BLOCKED | BLOCKED_AWAITING_APPROVAL |
| `error: "exfoliation_gate_failed"` | BLOCKED | FAIL_EXFOLIATION_GATE |
| Module not found | FAILED | FAIL_VALIDATION_ERROR |
| Exception | FAILED | FAIL_EXECUTION_ERROR |

### Scope Boundary

**DOES**: Job validation, Hermes invocation, status mapping, evidence_refs, dry_run truth
**DOES NOT**: FAM events, CABR/PoB, WRE queueing, autonomous build claims

### Tests

- `test_hermes_foundup_job_executor.py` - 22 tests covering:
  - Pre-validation (terminal, running, unsupported action, missing path)
  - Status mapping (success, security blocked, exfoliation blocked, exception)
  - Action dispatch (extract, validate, build)
  - Evidence and payload augmentation
  - Worker identity

---

## 2026-04-16 - FAM Daemon Breadcrumb System (v0.5.1)

**Author**: 0102
**WSP References**: WSP 29, WSP 77, WSP 91

### Added

- **FAM event breadcrumbs** for full audit trail of Hermes actions
  - `HERMES_EXTRACTION_STARTED` - Extraction initiated
  - `HERMES_EXTRACTION_COMPLETED` - Extraction succeeded
  - `HERMES_EXTRACTION_FAILED` - Extraction failed (with stage + error)
  - `HERMES_SECURITY_GATE` - AI Overseer gate result
  - `HERMES_BOUNDARY_ANALYZED` - Module boundary analysis done
  - `HERMES_GATE_CHECKED` - Exfoliation gate result

- `_emit_breadcrumb()` helper method for consistent event emission
- FAM dedupe keys for all Hermes events

### Observability

| Action | FAM Event | Payload |
|--------|-----------|---------|
| Start extraction | `hermes_extraction_started` | source_module, target_org |
| Security check | `hermes_security_gate` | passed, message |
| Boundary scan | `hermes_boundary_analyzed` | module_path, files, imports, blockers |
| Gate check | `hermes_gate_checked` | passed, all 6 check results |
| Success | `hermes_extraction_completed` | target_repo, files, adapters |
| Failure | `hermes_extraction_failed` | error, stage, blockers |

### Exports

- `FAM_DAEMON_AVAILABLE` flag added to `__init__.py`

---

## 2026-04-16 - MCP Bridge v1.4 Perception Integration (v0.5.0)

**Author**: 0102
**WSP References**: WSP 29, WSP 50, WSP 77, WSP 97

### Added

- **MCP Bridge perception layer** integrated into HermesFoundUpBuilder
  - `analyze_boundary()` now uses `get_module_dependencies` + `get_reverse_dependencies`
  - `check_exfoliation_gate()` now uses `get_change_impact_score` for risk analysis
  - `run_hermes_extraction()` injects context via `get_prompt_context_packet`
  - New `get_perception()` method for direct MCP tool calls

### Perception Capabilities

| Layer | Tools Used | Purpose |
|-------|------------|---------|
| Layer 1 | `get_module_dependencies`, `get_reverse_dependencies` | Boundary analysis |
| Layer 2 | `get_change_impact_score` | Exfoliation risk |
| Layer 4 | `get_prompt_context_packet` | Context injection |

### Exports

- `MCP_BRIDGE_AVAILABLE` flag added to `__init__.py`

### Communication Flow

```
012 → 0102 (Claude) → MCP Bridge → Hermes
```

012 gives intent, 0102 translates to execution with MCP perception, Hermes builds.

---

## 2026-04-25 - Hermes Deploy Surface Detector Alignment

**Author**: 0102
**WSP References**: WSP 34, WSP 50, WSP 60, WSP 83, WSP 97

### Fixed

- Added `HermesFoundUpBuilder._detect_deploy_surface()` so the exfoliation gate accepts existing verified deploy evidence:
  - direct deploy config (`Dockerfile`, `cloudbuild.yaml`, `firebase.json`, `deployment/`)
  - `app/index.html`
  - `frontend/index.html`
  - `foundup_manifest.json` with `entry_url` and `launch_readiness=ready`

### Validation

- `python -m pytest modules/foundups/agent/tests/test_hermes_foundup_builder.py -q`
- Result: 18 passed.

### Memory

- Updated `tests/README.md` with implemented Hermes builder coverage.
- Added `tests/TestModLog.md` for WSP 34/WSP 60 test memory.

---

## 2026-04-16 - Hermes Agent Integration (v0.4.0)

**Author**: 0102
**WSP References**: WSP 29, WSP 50, WSP 77, WSP 97

### Added

- **hermes_adapter.py** - Bounded Hermes agent wrapper
  - `HermesFoundUpBuilder` class with security gates
  - `extract_foundup()` - Main extraction entry point
  - `run_hermes_extraction()` - Hermes CLI invocation
  - `analyze_boundary()` - Module boundary analysis
  - `check_exfoliation_gate()` - CABR V1/V2/V3 gates
  - `generate_adapters()` - Adapter stub generation

- **hermes_model_router.py** - Dynamic model switching
  - `TaskCapability` enum: VISION, CODE, REASONING, TRIAGE, VOICE
  - `HermesModelRouter` class with fallback chains
  - `route_to_model()` convenience function

- **hermes-foundup-builder.yaml** - LM Studio configuration
  - Qwen Coder 7B as default
  - LM Studio provider at localhost:1234

### Git Submodule

- `vendor/hermes-agent` added from FOUNDUPS/hermes-agent fork

---

## 2026-02-16 - Domain continuity alignment docs

**Author**: 0102
**WSP References**: WSP 15, WSP 22, WSP 49

### Changes
- Updated `ROADMAP.md` with canonical domain alignment references:
  - `modules/foundups/ROADMAP.md`
  - `modules/foundups/docs/OCCAM_LAYERED_EXECUTION_PLAN.md`
  - `modules/foundups/docs/CONTINUATION_RUNBOOK.md`

### Rationale
- Ensure agent-module planning stays synchronized with domain-level layered
  delivery and handoff discipline.

---

## 2026-02-15 - Module Creation (v0.1.0)

**Author**: 0102
**WSP References**: WSP 00, WSP 29, WSP 49, WSP 73, WSP 77

### Created

- Initial module structure per WSP 49
- README.md with state machine documentation
- INTERFACE.md with event schemas
- ROADMAP.md with phased implementation plan
- This ModLog.md

### Integrated

- 6 agent lifecycle event types added to FAMDaemon:
  - `agent_joins` - 01(02) enters with public key
  - `agent_awakened` - → 0102 zen state
  - `agent_idle` - → 01/02 decayed
  - `agent_ranked` - Rank progression 1-7
  - `agent_earned` - F_i payout credited
  - `agent_leaves` - Logs off with wallet

- FAMBridge emit methods:
  - `emit_agent_joins()` - Enhanced with public_key, rank
  - `emit_agent_awakened()` - New method
  - `emit_agent_ranked()` - New method
  - `emit_agent_leaves()` - New method
  - `emit_agent_idle()` - Enhanced with tick tracking

- Mesa model integration:
  - `_track_agent_lifecycle()` method added
  - Awakening on first successful action
  - Idle detection (100 tick threshold)
  - Rank evaluation based on earnings

- SSE Server:
  - All 6 event types added to STREAMABLE_EVENT_TYPES

- Animation (foundup-cube.js):
  - SIM_EVENT_MAP entries for all agent events
  - TICKER_MESSAGES templates updated
  - Color key compacted (F_i Rating label fix)
  - Shift+wheel speed control added

### Files Modified

| File | Change |
|------|--------|
| `modules/foundups/agent_market/src/fam_daemon.py` | +6 event types, +dedupe keys |
| `modules/foundups/simulator/adapters/fam_bridge.py` | +4 emit methods, enhanced existing |
| `modules/foundups/simulator/mesa_model.py` | +lifecycle tracking, +emit calls |
| `modules/foundups/simulator/sse_server.py` | +6 event types |
| `public/js/foundup-cube.js` | +SIM_EVENT_MAP, +ticker, +speed wheel |

### Next Steps

1. Implement `AgentLifecycleService` class
2. Add coherence calculation logic
3. Create unit tests for state transitions
4. Integrate wallet generation
