# scripts/worktree_cleanup_phase1_dryrun.ps1
# W6 WORKTREE_REGISTRY_CLEANUP_EXECUTION_PHASE1 - DRY RUN ONLY
# Generated from live derivation (origin/main merge-truth + PR state).
# This script PRINTS what it WOULD do. It EXECUTES NOTHING destructive.
# WSP_97 Truth Boundary: NO mutations. Untracked file.
#
# Augmentation: per-path DIRTINESS SAFETY. Each REMOVE candidate is checked
# with `git status --porcelain`. DIRTY entries (uncommitted/untracked changes)
# are surfaced as SKIPPED_DIRTY and would NOT be removed; they are deferred
# for 012's explicit decision. --force is reserved ONLY for clearing a stale
# LOCK on a CLEAN entry, never to override a dirty working tree.

$ErrorActionPreference = 'Stop'

$Primary = 'O:/Foundups-Agent'

# --- Approved removal allowlist (71; derived live: ahead==0 OR MERGED PR) ---
$Remove = @(
    'O:/Foundups-Agent/.claude/worktrees/agent-a08fcd743e4adc5d0',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a090866179e4d7ef4',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a1553af9dddea24d1',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a1567043c8622c914',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a18622aee4ada241e',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a187a218cffdc35f4',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a22625e0cbdf94a57',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a277bff9efbeb3cdb',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a31ff5c53593ab71c',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a44b89910d9d668d9',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a5309dac6894ea142',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a5b33a499cdd31186',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a5d1278fb48536509',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a6dbec63c3170bc4d',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a6f78d5d0fbb4a0fc',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a725246dcea862ac2',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a7da1ac2a33652c8c',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a7eb1c4ac8465b49f',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a83511d4973ff7bf8',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a85784da8f30040c5',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a8bff204edaf248f8',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a8c9d1069933e25b2',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a94563978ac51a9b3',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-a9c75b4959be1e175',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-aa441040aaa233f77',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-aa594f2c6d5003a48',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-aaa208acb63acf50c',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-ab4e6f6b43d5648ac',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-ab7fd78b358b1cff2',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-ab95ecf806a69b22e',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-abac7f71a80903943',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-abecbc487af14d03b',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-ac02620e9da5701c8',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-ad3775f0d97c7ac60',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-ad62f4ddac9c26a9b',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-ad998a8e0c488774a',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/agent-adaaf184fa322062d',  # stale-locked
    'O:/Foundups-Agent/.claude/worktrees/APCA-W9D',
    'O:/Foundups-Agent/.claude/worktrees/destructive-action-guard-path-canonicalization',
    'O:/Foundups-Agent/.claude/worktrees/FCISRA-W9',
    'O:/Foundups-Agent/.claude/worktrees/FCRSA-W9A',
    'O:/Foundups-Agent/.claude/worktrees/foundup-canonical-registry-population',
    'O:/Foundups-Agent/.claude/worktrees/foundup-canonical-registry-schema',
    'O:/Foundups-Agent/.claude/worktrees/FPSSA-W9E',
    'O:/Foundups-Agent/.claude/worktrees/FWLBA-W9',
    'O:/Foundups-Agent/.claude/worktrees/holoindex-docs-reindex-observation',
    'O:/Foundups-Agent/.claude/worktrees/holoindex-index-docs-consistency-audit',
    'O:/Foundups-Agent/.claude/worktrees/holoindex-trade-alias-observation',
    'O:/Foundups-Agent/.claude/worktrees/M2JRA-W9B',
    'O:/Foundups-Agent/.claude/worktrees/MCPFSR-W9',
    'O:/Foundups-Agent/.claude/worktrees/MCPRLS-W9',
    'O:/Foundups-Agent/.claude/worktrees/MCPS2S-W9',
    'O:/Foundups-Agent/.claude/worktrees/PQNDA-W9C',
    'O:/Foundups-Agent/.claude/worktrees/redteam-ci-observation',
    'O:/Foundups-Agent/.claude/worktrees/redteam-family-a',
    'O:/Foundups-Agent/.claude/worktrees/redteam-family-c',
    'O:/Foundups-Agent/.claude/worktrees/redteam-harness-skeleton',
    'O:/Foundups-Agent/.claude/worktrees/redteam-provenance-check',
    'O:/Foundups-Agent/.claude/worktrees/redteam-regression-spec',
    'O:/Foundups-Agent/.claude/worktrees/trade-due-diligence-synthetic-regime-pack',
    'O:/Foundups-Agent/.claude/worktrees/vote-concat-audit',
    'O:/Foundups-Agent/.claude/worktrees/w1-guard-edge-case-tests',
    'O:/Foundups-Agent/.claude/worktrees/w1-holoindex-hxa-fix',
    'O:/Foundups-Agent/.claude/worktrees/w1-python-dotenv-remediation',
    'O:/Foundups-Agent/.claude/worktrees/w8-holoindex-status-audit',
    'O:/Foundups-Agent/.claude/worktrees/w9-agent-security-wsp-annex',
    'O:/Foundups-Agent/.claude/worktrees/w9-destructive-guard-edge-audit',
    'O:/Foundups-Agent/.claude/worktrees/work-ledger-search-integration',
    'O:/Foundups-Agent/.claude/worktrees/work-ledger-targeted-reindex-cli',
    'O:/tmp/w_tq3_routing',
    'O:/tmp/youtube_proxy_v0194'
)

# --- Stale-locked subset (lock cleared via `git worktree unlock`; --force ONLY for lock) ---
$StaleLocked = @(
    'O:/Foundups-Agent/.claude/worktrees/agent-a08fcd743e4adc5d0',
    'O:/Foundups-Agent/.claude/worktrees/agent-a090866179e4d7ef4',
    'O:/Foundups-Agent/.claude/worktrees/agent-a1553af9dddea24d1',
    'O:/Foundups-Agent/.claude/worktrees/agent-a1567043c8622c914',
    'O:/Foundups-Agent/.claude/worktrees/agent-a18622aee4ada241e',
    'O:/Foundups-Agent/.claude/worktrees/agent-a187a218cffdc35f4',
    'O:/Foundups-Agent/.claude/worktrees/agent-a22625e0cbdf94a57',
    'O:/Foundups-Agent/.claude/worktrees/agent-a277bff9efbeb3cdb',
    'O:/Foundups-Agent/.claude/worktrees/agent-a31ff5c53593ab71c',
    'O:/Foundups-Agent/.claude/worktrees/agent-a44b89910d9d668d9',
    'O:/Foundups-Agent/.claude/worktrees/agent-a5309dac6894ea142',
    'O:/Foundups-Agent/.claude/worktrees/agent-a5b33a499cdd31186',
    'O:/Foundups-Agent/.claude/worktrees/agent-a5d1278fb48536509',
    'O:/Foundups-Agent/.claude/worktrees/agent-a6dbec63c3170bc4d',
    'O:/Foundups-Agent/.claude/worktrees/agent-a6f78d5d0fbb4a0fc',
    'O:/Foundups-Agent/.claude/worktrees/agent-a725246dcea862ac2',
    'O:/Foundups-Agent/.claude/worktrees/agent-a7da1ac2a33652c8c',
    'O:/Foundups-Agent/.claude/worktrees/agent-a7eb1c4ac8465b49f',
    'O:/Foundups-Agent/.claude/worktrees/agent-a83511d4973ff7bf8',
    'O:/Foundups-Agent/.claude/worktrees/agent-a85784da8f30040c5',
    'O:/Foundups-Agent/.claude/worktrees/agent-a8bff204edaf248f8',
    'O:/Foundups-Agent/.claude/worktrees/agent-a8c9d1069933e25b2',
    'O:/Foundups-Agent/.claude/worktrees/agent-a94563978ac51a9b3',
    'O:/Foundups-Agent/.claude/worktrees/agent-a9c75b4959be1e175',
    'O:/Foundups-Agent/.claude/worktrees/agent-aa441040aaa233f77',
    'O:/Foundups-Agent/.claude/worktrees/agent-aa594f2c6d5003a48',
    'O:/Foundups-Agent/.claude/worktrees/agent-aaa208acb63acf50c',
    'O:/Foundups-Agent/.claude/worktrees/agent-ab4e6f6b43d5648ac',
    'O:/Foundups-Agent/.claude/worktrees/agent-ab7fd78b358b1cff2',
    'O:/Foundups-Agent/.claude/worktrees/agent-ab95ecf806a69b22e',
    'O:/Foundups-Agent/.claude/worktrees/agent-abac7f71a80903943',
    'O:/Foundups-Agent/.claude/worktrees/agent-abecbc487af14d03b',
    'O:/Foundups-Agent/.claude/worktrees/agent-ac02620e9da5701c8',
    'O:/Foundups-Agent/.claude/worktrees/agent-ad3775f0d97c7ac60',
    'O:/Foundups-Agent/.claude/worktrees/agent-ad62f4ddac9c26a9b',
    'O:/Foundups-Agent/.claude/worktrees/agent-ad998a8e0c488774a',
    'O:/Foundups-Agent/.claude/worktrees/agent-adaaf184fa322062d'
)

# --- Protected paths (MUST be excluded; KEEP) ---
$Protected = @(
    'O:/Foundups-Agent',
    'O:/Foundups-Agent/.claude/worktrees/agent-a3072b92195f6e5a7',
    'O:/Foundups-Agent/.claude/worktrees/agent-a38c0fe37c0231091',
    'O:/Foundups-Agent/.claude/worktrees/agent-a856dfecee631f9be',
    'O:/Foundups-Agent/.claude/worktrees/agent-abd459fbbbc75e72d',
    'O:/Foundups-Agent/.claude/worktrees/agent-ad2c339cf9b6ab9c3',
    'O:/Foundups-Agent/.claude/worktrees/trade-deterministic-clock-fix',
    'O:/Foundups-Agent/.claude/worktrees/w6-registry-build-integration',
    'O:/Foundups-Agent/.claude/worktrees/w9-roc-pipeline-integration-audit',
    'O:/Foundups-Agent/.worktrees/0102-clean-main',
    'O:/tmp/w6_autoagent_rescue'
)

# === CWD GUARD (fail-closed) ===
$cwd = $PWD.Path.Replace('\','/').TrimEnd('/')
$primaryNorm = $Primary.TrimEnd('/')
if ($cwd -ne $primaryNorm) {
    Write-Output "ABORT: cwd '$cwd' is not the primary checkout '$primaryNorm'."
    exit 1
}
# Ensure cwd is NOT inside any linked worktree tree
if ($cwd -like '*/.claude/worktrees/*' -or $cwd -like 'O:/tmp/*' -or $cwd -like '*/.worktrees/*') {
    Write-Output "ABORT: cwd '$cwd' appears to be inside a linked worktree tree."
    exit 1
}
Write-Output "CWD GUARD: PASS (cwd is primary checkout, not inside any linked worktree)"
Write-Output ""

$staleLockedSet = @{}
foreach ($s in $StaleLocked) { $staleLockedSet[$s] = $true }
$protectedSet = @{}
foreach ($p in $Protected) { $protectedSet[$p] = $true }

# === PROTECTED-COLLISION CHECK (fail-closed, exit 2) ===
$collisions = 0
foreach ($p in $Remove) {
    if ($protectedSet.ContainsKey($p)) {
        Write-Output "COLLISION: protected path appeared in remove list -> $p"
        $collisions++
    }
}
if ($collisions -gt 0) {
    Write-Output "ABORT: $collisions protected/remove collision(s). Refusing to proceed."
    exit 2
}

# === DIRTINESS SAFETY + WOULD-DO PRINT (no mutations) ===
$wouldRemove = 0
$wouldUnlock = 0
$skippedDirty = 0
$dirtyList = @()

foreach ($p in $Remove) {
    if (-not (Test-Path $p)) {
        Write-Output "MISSING (already gone): $p"
        continue
    }
    # git status --porcelain via primary git, -C into the worktree (read-only)
    $st = & git -C $p status --porcelain
    $stText = ($st | Out-String).Trim()
    if ($stText -ne '') {
        Write-Output "SKIPPED_DIRTY: $p"
        foreach ($ln in ($stText -split "`n")) { Write-Output ("    " + $ln.TrimEnd()) }
        $skippedDirty++
        $dirtyList += $p
        continue
    }
    if ($staleLockedSet.ContainsKey($p)) {
        Write-Output "WOULD: git worktree unlock $p ; git worktree remove $p   (--force ONLY if lock persists)"
        $wouldUnlock++
    } else {
        Write-Output "WOULD: git worktree remove $p"
    }
    $wouldRemove++
}

Write-Output ""
Write-Output ("SUMMARY: {0} would-remove (clean) | {1} would-unlock | {2} SKIPPED_DIRTY | {3} protected-excluded | {4} collisions" -f `
    $wouldRemove, $wouldUnlock, $skippedDirty, $Protected.Count, $collisions)
Write-Output ("ALLOWLIST total = {0} (clean {1} + dirty-skipped {2})" -f $Remove.Count, $wouldRemove, $skippedDirty)
if ($dirtyList.Count -gt 0) {
    Write-Output ""
    Write-Output "SKIPPED_DIRTY paths (deferred for 012 decision):"
    foreach ($d in $dirtyList) { Write-Output "  $d" }
}
