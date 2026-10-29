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

Mode 1 still discovers module structure through the filesystem and invokes
external dependency/code scanners per module. The separate
`WSPComplianceChecker` still needs its Git-scoped, read-only memory repair.
Do not describe either path as a fully bounded read-only repository audit yet.
Use the focused test selection in [tests/README.md](tests/README.md); avoid
global test collection and live Mode 1 execution during this repair.
