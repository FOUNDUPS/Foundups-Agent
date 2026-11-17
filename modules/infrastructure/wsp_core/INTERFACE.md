# WSP core interface

## Read-only compliance hints

Import `WSPComplianceChecker`, `WSPViolation`, and `WSPViolationType` directly from
`modules.infrastructure.wsp_core.src.wsp_compliance_checker`.

`WSPComplianceChecker(project_root: Path | None = None, *,
known_false_positives: Iterable[tuple[str, str]] = ())` stores an explicit repository
root and an immutable suppression selection. The default is this package's
checkout root. Construction does not run Git or initialize/open a pattern database.

`await checker.scan() -> list[WSPViolation]` refreshes Git-tracked inventory on each
call. Only ordinary tracked Python source is opened; tracked module-document
presence uses metadata. Untracked local files cannot create findings or satisfy
required documentation. Tracked tests are included in Python size hints.

`WSPViolation` retains `violation_type`, `description`, `affected_files`,
`severity`, `wsp_protocol`, `detection_time`, `auto_fixable`, and optional
`fix_suggestion`. Paths are relative to the selected root. All new scan results
have `auto_fixable=False`; the scanner does not authorize writes, moves or PRs.

`WSPViolationType.SCAN_INCOMPLETE` adds an explicit WSP 50 failure record. An
unavailable/invalid tracked inventory returns one such row. Individual unsupported
or unreadable entries add incomplete rows alongside findings from inspected files.
Do not interpret incomplete results as a clean scan. Environment-named paths are
excluded without content reads; no environment-file security coverage is claimed.

Size hints use WSP 62's Python review range: 800–1000 lines low, above 1000 and
below 1500 medium, 1500 or more high. They do not apply FMAS exemption contracts or
establish candidate-attributed gate failures. Component hints count direct Python
children only. A tracked `tests/README.md` establishes documentation presence,
never executed coverage. Python-bearing modules require tracked requirements.txt.

Suppression entries are `("module", "block_name")` or
`("root_file", "filename.py")`. Module selections suppress duplicate-name and
module-document/dependency hints for that block name across domains. Root-file
selections suppress root-placement hints. They do not suppress source inspection,
size/component/domain findings. Invalid tuple shapes raise `ValueError`; callers
must supply the documented iterable of string tuples. Stored PatternMemory data
is neither read nor changed; callers own any prior authorized retrieval.

## Other existing owners

`src/wsp_domain_policy.py` exports immutable `CORE_DOMAINS`,
`ARCHITECTURAL_EXCEPTIONS`, and `RESERVED_BLOCK_NAMES`. The checker's previous
constant names remain aliases; FMAS's `ENTERPRISE_DOMAINS` aliases `CORE_DOMAINS`.
Callers cannot mutate the shared sets. Both WSP 3 Markdown mirrors are checked
against the policy by tests, not parsed at runtime.

`evidenced_module_roots(paths, exceptions=ARCHITECTURAL_EXCEPTIONS)` and
`unqualified_module_containers(paths, exceptions=ARCHITECTURAL_EXCEPTIONS)` return
sorted tuples of relative roots. Inputs are already-admitted repository-relative
file paths. The functions do no filesystem/process/database IO and do not prove
path validity, current generation or domain legitimacy. Unknown domains remain
separate findings; custom exception selections preserve the FMAS adapter API.
Unqualified-container architecture hints are not suppressed by module-document
false-positive selections. Suppression of real modules retains its prior scope.

`SemanticStateEngine` and its immutable `SemanticState` are defined in
`src/semantic_state_engine.py`; they retain their existing WSP 44 transition
contract and optional log behavior. The WSP 00 neural adapter remains separate.
Neither is covered by the compliance scanner's no-write guarantee.

`WSPValidator` / `WSPEnforcer` examples from the former interface were speculative
and are not executable APIs in this module. No replacement classes are introduced.
