<#
.SYNOPSIS
    NON-DESTRUCTIVE dry-run for W6 Worktree Stranded-Work Removal Execution Phase 1.

.DESCRIPTION
    Hard-codes the 7-path allowlist (#758) and the protected/never-touch set.
    Asserts CWD is the primary checkout and that no allowlist path collides with
    a protected/a5d1278/SALVAGE/ARCHIVE path. Prints per-path fresh status/drift
    and the planned unlock/remove commands, then a SUMMARY.

    This script NEVER calls: git worktree remove / unlock / prune,
    Remove-Item, or Move-Item. It is read-only.

    Predecessors: #758 (allowlist), #741 (Windows reconciliation pattern).
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = 'O:/Foundups-Agent'

# ---- The 7-path allowlist (hard-coded EXACTLY; no globs/regex/branch-derived) ----
$Remove = @(
    [pscustomobject]@{ Path = 'O:/Foundups-Agent/.claude/worktrees/agent-a7eb1c4ac8465b49f'; ExpectHead = '0c01a268a'; ExpectDirty = 'dirty(5)'; Locked = $true },
    [pscustomobject]@{ Path = 'O:/Foundups-Agent/.claude/worktrees/agent-ab7fd78b358b1cff2'; ExpectHead = '0c01a268a'; ExpectDirty = 'dirty(2)'; Locked = $true },
    [pscustomobject]@{ Path = 'O:/Foundups-Agent/.claude/worktrees/agent-a38c0fe37c0231091'; ExpectHead = '50ac3dc11'; ExpectDirty = 'clean';    Locked = $true },
    [pscustomobject]@{ Path = 'O:/Foundups-Agent/.claude/worktrees/agent-ad998a8e0c488774a'; ExpectHead = 'facdd7362'; ExpectDirty = 'dirty(5)'; Locked = $true },
    [pscustomobject]@{ Path = 'O:/Foundups-Agent/.claude/worktrees/w1-holoindex-hxa-fix';     ExpectHead = '8f05f1f4b'; ExpectDirty = 'dirty(1)'; Locked = $false },
    [pscustomobject]@{ Path = 'O:/Foundups-Agent/.claude/worktrees/w6-hxa-policyflags';       ExpectHead = '47fc79d2d'; ExpectDirty = 'clean';    Locked = $false },
    [pscustomobject]@{ Path = 'O:/tmp/w_tq3_routing';                                          ExpectHead = 'b9f8a9a6f'; ExpectDirty = 'dirty(1)'; Locked = $false }
)

# ---- Protected / never-touch (fail-closed) ----
$Protected = @(
    'O:/Foundups-Agent/.worktrees/0102-clean-main',
    'O:/tmp/w6_autoagent_rescue',
    'O:/Foundups-Agent/.claude/worktrees/agent-a5d1278fb48536509',
    # 7 SALVAGE
    'O:/Foundups-Agent/.claude/worktrees/agent-a856dfecee631f9be',
    'O:/Foundups-Agent/.claude/worktrees/agent-abd459fbbbc75e72d',
    'O:/Foundups-Agent/.claude/worktrees/agent-ad2c339cf9b6ab9c3',
    'O:/Foundups-Agent/.claude/worktrees/agent-a3072b92195f6e5a7',
    'O:/Foundups-Agent/.claude/worktrees/w6-registry-build-integration',
    'O:/Foundups-Agent/.claude/worktrees/w9-roc-pipeline-integration-audit',
    'O:/Foundups-Agent/.claude/worktrees/trade-deterministic-clock-fix',
    # 2 ARCHIVE
    'O:/Foundups-Agent/.claude/worktrees/MCPFSR-W9',
    'O:/Foundups-Agent/.claude/worktrees/vote-concat-audit'
)

function Normalize([string]$p) {
    return ($p -replace '\\', '/').TrimEnd('/').ToLowerInvariant()
}

Write-Output '================================================================'
Write-Output ' W6 WORKTREE STRANDED-WORK REMOVAL - PHASE 1 DRY-RUN (READ-ONLY)'
Write-Output '================================================================'

# ---- CWD GUARD (fail-closed) ----
$cwd = (Get-Location).Path
$cwdN = Normalize $cwd
$repoN = Normalize $RepoRoot
if ($cwdN -ne $repoN) {
    Write-Output "CWD-GUARD: FAIL - cwd is '$cwd', expected '$RepoRoot'"
    exit 1
}
if ($cwdN -match '\.claude/worktrees' -or $cwdN -match '\.worktrees' -or $cwdN -match '^o:/tmp/') {
    Write-Output "CWD-GUARD: FAIL - cwd is inside a linked worktree: '$cwd'"
    exit 1
}
Write-Output "CWD-GUARD: PASS (cwd = $cwd)"

# ---- PROTECTED-COLLISION (fail-closed, exit 2) ----
$protN = $Protected | ForEach-Object { Normalize $_ }
$collisions = @()
foreach ($r in $Remove) {
    if ($protN -contains (Normalize $r.Path)) { $collisions += $r.Path }
}
if ($collisions.Count -gt 0) {
    Write-Output "PROTECTED-COLLISION: FAIL - allowlist intersects protected set:"
    $collisions | ForEach-Object { Write-Output "  COLLISION: $_" }
    exit 2
}
Write-Output "PROTECTED-COLLISION: PASS (0 collisions; 7 allowlist disjoint from $($Protected.Count) protected)"
Write-Output ''

# ---- Per-path fresh status / drift + planned commands ----
$wouldRemove = 0
$wouldUnlock = 0
$skippedDrift = @()

foreach ($r in $Remove) {
    $p = $r.Path
    Write-Output "---- $p ----"
    if (-not (Test-Path $p)) {
        Write-Output "  EXISTS: NO (already gone)"
        $skippedDrift += $p
        Write-Output ''
        continue
    }
    $head = (& git -C $p rev-parse --short HEAD).Trim()
    $statusLines = @(& git -C $p status --porcelain | Where-Object { $_ -ne '' })
    $dirtyCount = $statusLines.Count
    Write-Output "  Fresh HEAD : $head  (expected $($r.ExpectHead))"
    Write-Output "  Fresh dirty: $dirtyCount entr(ies)  (expected $($r.ExpectDirty))"
    Write-Output "  Locked     : $($r.Locked)"

    $headMatch = ($head -eq $r.ExpectHead)
    if (-not $headMatch) {
        Write-Output "  DRIFT: HEAD mismatch -> SKIPPED_DRIFT (no remove planned)"
        $skippedDrift += $p
        Write-Output ''
        continue
    }
    Write-Output "  DRIFT: none (HEAD matches #758)"

    if ($r.Locked) {
        Write-Output "  PLAN: git -C $RepoRoot worktree unlock $p"
        $wouldUnlock++
    }
    if ($r.ExpectDirty -eq 'clean' -and -not $r.Locked) {
        Write-Output "  PLAN: git -C $RepoRoot worktree remove $p   (clean+unlocked)"
    } elseif ($r.ExpectDirty -eq 'clean' -and $r.Locked) {
        Write-Output "  PLAN: git -C $RepoRoot worktree remove --force $p   (clean but locked-admin)"
    } else {
        Write-Output "  PLAN: git -C $RepoRoot worktree remove --force $p   (dirty cleared + backed up)"
    }
    $wouldRemove++
    Write-Output ''
}

Write-Output '================================ SUMMARY ========================'
Write-Output "  Would-remove     : $wouldRemove"
Write-Output "  Would-unlock     : $wouldUnlock"
Write-Output "  SKIPPED_DRIFT    : $($skippedDrift.Count)"
if ($skippedDrift.Count -gt 0) { $skippedDrift | ForEach-Object { Write-Output "      - $_" } }
Write-Output "  Protected-excluded: $($Protected.Count) (never in remove set)"
Write-Output "  Collisions       : 0"
Write-Output "  Final: prune planned AFTER removals (real script only)"
Write-Output '================================================================'
Write-Output 'DRY-RUN COMPLETE - no destructive action taken.'
