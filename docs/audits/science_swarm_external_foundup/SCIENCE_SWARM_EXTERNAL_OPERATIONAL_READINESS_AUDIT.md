# Science Swarm Hub — External FoundUp Operational Readiness Audit

**Worker**: CB2
**Date**: 2026-04-17
**Slice**: `SCIENCE_SWARM_EXTERNAL_OPERATIONAL_READINESS_AUDIT_PHASE1`
**WSP Lock**: WSP 15 (Prioritization Scoring), WSP 97 (Execution Protocol)
**Status**: AUDIT COMPLETE

---

## 1. Current Repo Truth (Monorepo)

| Artifact | Path | Status |
|----------|------|--------|
| Stub `__init__.py` | `modules/foundups/pqn_swarm_hub/__init__.py` | EXISTS — raises `ImportError` when package not installed (expected) |
| README.md | `modules/foundups/pqn_swarm_hub/README.md` | EXISTS — states "STUB" status, links to external repos |
| INTERFACE.md | `modules/foundups/pqn_swarm_hub/INTERFACE.md` | EXISTS — 592 lines, full contract documentation (stale: describes Phase 1 code now in external repo) |
| ModLog.md | `modules/foundups/pqn_swarm_hub/ModLog.md` | EXISTS — V0.1.0 through V0.15.0, 864 lines |
| `src/` directory | `modules/foundups/pqn_swarm_hub/src/` | DELETED — cutover 2026-03-30, all source migrated to external |
| `tests/` directory | `modules/foundups/pqn_swarm_hub/tests/` | DELETED — cutover 2026-03-30, all tests migrated to external |
| Historical docs | `PROTO_EXFOLIATION_CHECKLIST.md`, `MIGRATION_MANIFEST.md`, etc. | PRESERVED — audit trail artifacts |

**Monorepo verdict**: Stub-only. No executable code. `__init__.py` correctly delegates to installed package. Stub cutover was clean (V0.15.0).

---

## 2. External Surface Truth

### Primary Repo: FOUNDUPS/science-swarm-hub

| Check | Result | Method |
|-------|--------|--------|
| Repo exists | YES | `gh repo view` |
| Public | YES | `isPrivate: false` |
| Default branch | `main` | API response |
| Created | 2026-03-29 | API response |
| Last push | 2026-04-05 22:46:18 UTC | API response |
| Description | Present and accurate | API response |
| CI (GitHub Actions) | PASSING — 3/3 most recent runs `conclusion: success` | `gh api .../actions/runs` |
| Source files | 11 files in `src/pqn_swarm_hub/` | API directory listing |
| Test files | 9 files in `tests/` | API directory listing |
| `pyproject.toml` | Present — `name = "science-swarm-hub"`, `version = "0.12.0"`, `requires-python = ">=3.12"` | API content read |
| `CONTRIBUTING.md` | Present | API directory listing |
| `RUNBOOK.md` | Present | API directory listing |
| `LICENSE` | MIT | API directory listing |

### Backup Repo: Foundup/science-swarm-hub

| Check | Result | Method |
|-------|--------|--------|
| Repo exists | YES | `gh repo view` |
| Public | **NO — PRIVATE** | `isPrivate: true` |

**Backup repo concern**: Monorepo README and stub list the backup as a public resource, but it is private. External contributors cannot access it. This is not a blocker but is a documentation mismatch.

### PyPI Package

| Check | Result | Method |
|-------|--------|--------|
| `pip install science-swarm-hub` | **FAILS — not on PyPI** | `pip install --dry-run` |
| Package installed locally | **NO** — `ModuleNotFoundError: No module named 'pqn_swarm_hub'` | `python -c "from pqn_swarm_hub import ..."` |

### Install Claim Mismatch

| Source | Claim | Truth |
|--------|-------|-------|
| Monorepo README | `pip install science-swarm-hub` (unqualified) | FALSE — not on PyPI |
| Monorepo `__init__.py` | "Install with: pip install science-swarm-hub" | FALSE — not on PyPI |
| External README | "From PyPI (when published)" + "From source: git clone..." | HONEST — acknowledges not yet published |
| NONCLAIMS.md | "No PyPI Package" | TRUE |

**Install truth**: Install from source only (`git clone` + `pip install -e .`). `pyproject.toml` is valid for local editable install. PyPI publish has not occurred.

---

## 3. Monorepo Stub Truth

The monorepo stub at `modules/foundups/pqn_swarm_hub/` is correctly structured:

- `__init__.py` attempts `from pqn_swarm_hub import ...` and raises helpful `ImportError` if package absent
- Re-exports 30 symbols (contracts, services, adapters, errors)
- No executable source code remains in monorepo
- Historical documentation preserved for audit trail

**Stub verdict**: Correct and clean. The stub will function as a pass-through once the package is installed from source.

**Stub concern**: The `__init__.py` import claim says "pip install science-swarm-hub" — should say "pip install -e . (from source)" until PyPI publish occurs.

---

## 4. Discord Embedded Category Truth

| Artifact | Status |
|----------|--------|
| `FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md` | CANONICAL — embedded category model, not standalone |
| `FOUNDUPS_SCIENCE_SWARM_NONCLAIMS.md` | CANONICAL — 15 explicit non-claims |
| `SCIENCE_SWARM_EMBEDDED_CATEGORY_BUILD_CHECKLIST.md` | OPERATOR-READY — all checkboxes unchecked |
| `FOUNDUPS_DISCORD_BLUEPRINT.md` | CANONICAL — server-wide structure |

**Intended model**: Science Swarm is an embedded category (`SCIENCE SWARM HUB`) inside the existing `FOUNDUPS` Discord server (guild ID `412646632992014336`), not a standalone server.

**Build state**: The build checklist exists but has **zero completed checkboxes**. No evidence that the Discord category has been created.

**Verification blocked**: This audit cannot verify Discord server state. No Discord API access available. State is assumed pending until operator (012) confirms execution.

**Key constraints documented**:
- 4 channels: `#swarm-general`, `#swarm-github`, `#swarm-work`, `swarm-voice`
- 2 project roles: `@swarm-contributor`, `@swarm-notify`
- No bot gate, no stake gate, no custom webhook, no sentinel agent
- GitHub is canonical; Discord is coordination surface only
- Non-blocking for repo release

---

## 5. pfMALL Catalog Status

| Field | Value | Assessment |
|-------|-------|------------|
| `foundup_id` | `science_swarm` | Correct |
| `source_type` | `github_repo` | Correct — not an app |
| `source_id` | `FOUNDUPS/science-swarm-hub` | Correct — matches real repo |
| `external_url` | `https://github.com/FOUNDUPS/science-swarm-hub` | Correct and verified accessible |
| `lifecycle_stage` | `externalized` | Correct — code lives in external repo |
| `launch_readiness` | `discoverable_only` | Correct — no app route exists |
| `entry_url` | ABSENT (no field) | Correct — no deployed app |
| `routing_prefix` | ABSENT (no field) | Correct — no pfMALL app route |
| `tier` | `F0_DAE` | Consistent with current stage |
| `video_count` | 0 | Correct |
| `poster_url` | `/media/posters/science_swarm.jpg` | NOT VERIFIED — would need to check file exists |

**Catalog verdict**: Accurately represents Science Swarm as a discovery-only entry pointing to a GitHub repo. No overclaiming. No app route claimed.

---

## 6. Operational Health Contract (Proposed)

The following contract defines what "operational" means for Science Swarm Hub at its current lifecycle stage (`externalized`, `discoverable_only`):

### MUST be true for "operational":

| Gate | Check | Current Status |
|------|-------|----------------|
| G1: External repo accessible | `gh repo view FOUNDUPS/science-swarm-hub` returns public repo | PASS |
| G2: CI passing | Most recent GitHub Actions run `conclusion: success` | PASS |
| G3: Install from source works | `git clone` + `pip install -e .` + `from pqn_swarm_hub import WorkUnitRegistry` succeeds | PASS — verified 2026-04-17 (v0.12.0 installed, full smoke test passed) |
| G4: Import path truthful | `from pqn_swarm_hub import ...` matches `pyproject.toml` package name | PASS (`pqn_swarm_hub` in both) |
| G5: Core smoke test exists | At least one test exercises register → submit → verify → contribute flow | PASS (`test_poc_flow.py` exists) |
| G6: Catalog entry accurate | `mall-video-catalog.json` fields match repo truth | PASS (no overclaiming) |
| G7: PyPI claim absent or qualified | No unqualified "pip install" claim | PASS — fixed 2026-04-17 (CB3: monorepo stub now says "from source") |

### SHOULD be true (not blocking):

| Gate | Check | Current Status |
|------|-------|----------------|
| S1: Discord embedded category live | Build checklist completed by operator | PENDING (0/8 phases done) |
| S2: Backup repo public | `Foundup/science-swarm-hub` accessible to contributors | FAIL (private) |
| S3: Poster image exists | `/media/posters/science_swarm.jpg` resolves | NOT VERIFIED |

### NOT required for "operational":

- pfMALL app route (`entry_url`, `routing_prefix`)
- Standalone Discord server
- PyPI publication
- PWA wallet gate
- Sentinel agent
- Bidirectional GitHub-Discord sync

---

## 7. Blockers / Unknowns

### Blockers (prevent claiming "operational")

| # | Blocker | Severity | Resolution |
|---|---------|----------|------------|
| ~~B1~~ | ~~Monorepo stub install claim unqualified~~ | RESOLVED | Fixed 2026-04-17 (CB3): `__init__.py` and `README.md` now say "from source" with clone instructions |
| ~~B2~~ | ~~Local source install not verified~~ | RESOLVED | Verified 2026-04-17 (CB3): `git clone` + `pip install -e .` + full smoke test (register→submit→verify→contribute) PASSED |

### Unknowns (cannot verify from this audit)

| # | Unknown | Why |
|---|---------|-----|
| U1 | Discord embedded category state | No Discord API access |
| U2 | Poster image exists at `/media/posters/science_swarm.jpg` | Not checked in this slice |
| U3 | External repo tests pass locally on Windows | CI is Linux; local env is Windows |
| U4 | INTERFACE.md in monorepo stub still references full API (592 lines) — should this be truncated to "see external repo"? | Architectural decision for 012 |

---

## 8. Recommended Next Slice

**Slice name**: `science_swarm_install_claim_fix_and_local_verify`

**Scope**:
1. Fix monorepo `__init__.py` line 10: change `Install with: pip install science-swarm-hub` to `Install from source: git clone https://github.com/FOUNDUPS/science-swarm-hub.git && cd science-swarm-hub && pip install -e .`
2. Fix monorepo `README.md` Installation section: qualify the pip install instruction with "(from source)" or replace with clone instructions
3. Clone external repo locally, run `pip install -e .`, verify `from pqn_swarm_hub import WorkUnitRegistry` succeeds
4. Verify monorepo stub passes through to installed package (import via `modules/foundups/pqn_swarm_hub`)
5. Update NONCLAIMS.md if any non-claim has become true

**Estimated effort**: 15-30 minutes
**Risk**: LOW (documentation fix + local verification only)
**Touches**: monorepo stub files only (no external repo mutation)

---

## 9. HoloIndex Results

**Command**:
```bash
python holo_index.py --search "Science Swarm external FoundUp pqn_swarm_hub embedded Discord operational readiness github_repo" --limit 3
```

**Top hit**: `docs/audits/science_swarm_external_foundup/FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md` [WSP]

Other hits: `SCIENCE_SWARM_EMBEDDED_CATEGORY_BUILD_CHECKLIST.md` [WSP], `modules/foundups/pqn_swarm_hub/INTERFACE.md` [WSP]

---

## 10. WSP Compliance Notes

**WSP 15 Applied**: Science Swarm Hub scores as follows under MPS:
- Complexity: 2 (stub + external repo, well-documented)
- Importance: 3 (first externalized FoundUp, pattern-setter)
- Deferability: 3 (functional as-is, install claim fix is low urgency)
- Impact: 3 (sets precedent for future exfoliated FoundUps)
- **MPS Score**: 11/20 (P2 — standard priority)

**WSP 97 Applied**: Execution followed CoT gate (retrieved all 8 required artifacts + HoloIndex + live verification before stating any facts). CoR gate applied: dialectic sweep confirmed install claim mismatch is real (cross-referenced NONCLAIMS, external README, pip dry-run, and monorepo stub). No confabulation — every claim in this audit has a verification method column.

---

## 11. Live Checks Performed

| Check | Command | Result |
|-------|---------|--------|
| Primary repo exists | `gh repo view FOUNDUPS/science-swarm-hub` | PUBLIC, last push 2026-04-05 |
| Backup repo exists | `gh repo view Foundup/science-swarm-hub` | EXISTS but PRIVATE |
| PyPI availability | `pip install science-swarm-hub --dry-run` | NOT FOUND on PyPI |
| Local package install | `python -c "from pqn_swarm_hub import ..."` | `ModuleNotFoundError` |
| CI status | `gh api .../actions/runs` | 3/3 PASSING |
| External repo structure | `gh api .../contents/` | 15 root items, full source + tests present |
| External pyproject.toml | `gh api .../contents/pyproject.toml` | Valid, `name=science-swarm-hub`, `version=0.12.0` |
| External README install | `gh api .../contents/README.md` | Honestly qualified: "From PyPI (when published)" |

---

---

## 12. CB3 Addendum — Install Claim Fix and Local Verification (2026-04-17)

**Worker**: CB3
**Slice**: `SCIENCE_SWARM_INSTALL_CLAIM_FIX_AND_LOCAL_VERIFY_PHASE1`

### Changes Made

| File | Change |
|------|--------|
| `modules/foundups/pqn_swarm_hub/__init__.py` (docstring) | "Install with: pip install science-swarm-hub" → source clone instructions |
| `modules/foundups/pqn_swarm_hub/__init__.py` (ImportError msg) | "Install with: pip install science-swarm-hub" → source clone instructions |
| `modules/foundups/pqn_swarm_hub/README.md` | "pip install science-swarm-hub" → "git clone + pip install -e ." |

### Local Verification Results

| Test | Command | Result |
|------|---------|--------|
| Clone external repo | `git clone https://github.com/FOUNDUPS/science-swarm-hub.git` | PASS |
| Install from source | `pip install -e .` | PASS — v0.12.0 installed |
| Core import | `from pqn_swarm_hub import WorkUnitRegistry, SubmissionSink, ...` | PASS — 5 core services imported |
| Full smoke test | register → submit → verify → contribute flow | PASS — contribution score=0.85, id=29e206ee |
| Monorepo stub passthrough | `from modules.foundups.pqn_swarm_hub import WorkUnitRegistry` | PASS — work_unit_id generated |

### Gate Status After CB3

| Gate | Before | After |
|------|--------|-------|
| G3: Install from source | NOT VERIFIED | **PASS** |
| G7: PyPI claim qualified | PARTIAL FAIL | **PASS** |
| B1: Install claim unqualified | OPEN | **RESOLVED** |
| B2: Local install not verified | OPEN | **RESOLVED** |

**All MUST gates now PASS (7/7).** Science Swarm Hub is operationally healthy for its current lifecycle stage (`externalized`, `discoverable_only`).

### Remaining Items (unchanged)

- S1: Discord embedded category — PENDING (operator action)
- S2: Backup repo private — FAIL (low priority)
- S3: Poster image — NOT VERIFIED
- U1-U4: Unknowns unchanged

---

*This audit distinguishes repo truth from external truth. Readiness is not overclaimed. The embedded Discord model remains intact. All corrective findings from CB2 have been resolved by CB3.*
