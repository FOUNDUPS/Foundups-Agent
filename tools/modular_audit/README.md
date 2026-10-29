# Foundups Modular Audit System

`modular_audit.py` checks module structure and compares an owned candidate with
an exact Git baseline. Run it from a clean, isolated checkout. The baseline must
be a clean checkout of the candidate's merge base with `origin/main`, sharing
the same Git common directory.

```powershell
python -B tools/modular_audit/modular_audit.py --mode 2 --baseline C:/path/to/baseline --wsp-62-size-check
```

Mode 2 reports candidate-attributed errors separately from inherited warnings
and advisories. A successful exit means no blocking error was reported; it
does not mean the repository has no structural debt. Baseline differences are
also identified in the final summary.

## Secret-hint scope

`scan_for_secrets(Path("modules"))` requires the repository's Git-tracked module
inventory. It inspects current working-tree contents of selected Python,
JavaScript, TypeScript, JSON, YAML and configuration files, including tracked
test fixtures. It never falls back to walking local untracked files when Git
inventory is unavailable.

Credential-assignment patterns require a complete identifier and a quoted
literal. Ordinary calls and attribute references are not stored-secret evidence.
The existing private-key markers and credential-bearing database URI patterns
remain. These are heuristic hints, not proof that a value is a live credential.

Environment-named files (`.env`, `.env.*`, `*.env`) are reported without opening
them. Unreadable, invalid UTF-8, oversized (over 2 MiB), redirected or special
source files produce an explicit scan error. Path components are checked for
symlinks and Windows reparse points before reading. This is a bounded working
tree inspection, not a race-resistant filesystem security boundary; concurrent
checkout changes require a new inspection.

The source inspector returns typed location records containing only category,
relative path and optional line number. The audit adapter formats those records;
source text and matched values never cross that reporting boundary. Potential literals and unread environment files
are warnings; incomplete source inspection is an error. No test directory is
blanket-exempted.

The hosted security gate in `.github/scripts/security_gate.py` remains the
authoritative tracked-tree and introduced-history check. This heuristic neither
replaces that gate nor changes its rules, scope or reviewed-finding records.

## Remaining audit work

Mode 1's structural entrypoint now requires the exact Git root. It uses stage-0
tracked paths, never untracked directories, to identify blocks and document
presence. Git output is limited to 4 MiB/100,000 records/30 seconds per read.
Redirected, missing and special files are explicit incomplete inspection errors.
Environment-named components are excluded before file metadata/content reads.
Monitoring is a canonical WSP 3 domain; the documented `modules/wre_core` exception
remains. No files are moved or repaired by this audit.
Module evidence follows HoloIndex's existing rule: tracked files under direct
`src/` or `tests/`, or a direct `README.md`/`INTERFACE.md`. Other containers remain
explicit ownership warnings instead of acquiring fabricated module requirements.
This distinguishes legacy scripts, intake/archive folders and telemetry data.

`perform_security_scan(repo_root, domain_path="repository")` runs each applicable
external scanner once with explicit process cwd; it never changes the caller's
working directory. `run_pip_audit(root)` and `run_npm_audit(root)` require a root;
`run_bandit(root, tracked_paths)` also requires the admitted inventory.

- pip-audit covers the current interpreter's **installed environment**, when the
  root requirements file is tracked. It does not resolve every module requirements
  file. Known vulnerabilities without a severity are reported as unrated errors.
- Bandit receives explicit tracked module Python targets, including tests, through
  an owned temporary INI. It does not recurse or load an implicit `.bandit` file.
  Inputs are limited to 2 MiB/file, 128 MiB total and 4 MiB of target names;
  unsupported paths and missing coverage are errors. The INI is removed afterward.
- npm audits the tracked root package/lock pair (8 MiB limit per manifest), includes
  development/optional/peer dependencies, and disables workspace selection. It does
  not audit every nested frontend lock. Node invokes the installed npm JS entrypoint
  directly, including the adjacent Node/npm layout on Windows; unsupported layouts
  report incomplete inspection. No install, update or `audit fix` command is used.

Each external process has a 120-second deadline and 2 MiB stdout limit using the
existing WRE process boundary. Exit 1 vulnerability JSON is retained; empty failed,
malformed, duplicate-key and incomplete responses are errors. Findings contain
fixed tool names/counts, never provider descriptions, source excerpts or stderr.
Critical/high/unrated results are errors, medium results warnings, low/info results
advisories. These limits are not process-tree/RSS isolation or a filesystem race
guarantee. Auditors may contact advisory registries and use their own caches.

Mode 2 and the optional WSP 62 size-check discovery retain their existing baseline
and filesystem helpers; they are not covered by the new Mode 1 inventory claim.
The separate WSPComplianceChecker's tracked read-only repair landed in #2265.
Whole-repository security clearance, live auditor execution and deployment are
not established by the offline acceptance suite.
Use the focused test selection in [tests/README.md](tests/README.md); avoid
global test collection or live Mode 1 execution as an unreviewed test side effect.
