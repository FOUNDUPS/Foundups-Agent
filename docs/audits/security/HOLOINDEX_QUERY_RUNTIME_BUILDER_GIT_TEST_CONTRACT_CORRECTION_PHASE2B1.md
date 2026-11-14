# Assumption Audit Addendum: Builder Git Test Contract Phase 2B.1

**Date:** 2026-08-29
**Base commit:** `dff50350eb198093fd33ad628af5a468496cc939`
**Owner:** 0102 architect
**Decision:** CORRECT THE TEST; PRESERVE THE PRODUCTION BOUNDARY

The canonical RedDog WSP 15 allocator scores the complete eight-effect/
nine-read-target transaction 20/P0. WSP 97 requires preserving the verified
layered authority contract rather than making production code fit a false,
currently skipped assertion.

## Problem

The opt-in O:/E: live-Git test changed a tracked worktree file after commit and
expected `prove_pinned_git_authority()` to reject it as repository-state drift.
That expectation contradicted the reviewed Phase 2B contract: Git authority
binds repository topology, exact HEAD, ordinary index flags, and committed HEAD
blobs without invoking worktree porcelain or claiming global cleanliness.

## Verification

- Governed Holo evidence was CURRENT at the exact base commit with no index gap
  or reindex.
- Direct production-code inspection confirmed the Git proof reads committed
  objects with `ls-tree` and `cat-file`; it never reads bound worktree bytes.
- A live Git reproduction changed `bound.py` only in the worktree. HEAD, the
  HEAD tree, and `ls-files -v` observations remained identical; porcelain alone
  reported the modification.
- Source authority already owns the required rejection: it compares bound live
  bytes with both the backend manifest and committed HEAD blobs.

## Failure Modes and Disposition

| Failure mode | Impact | Disposition |
|---|---:|---|
| Leave the false expectation skipped until an O:/E: Git image appears | HIGH | Correct now; otherwise provisioning converts a skip into a false failure. |
| Add porcelain to make the old test pass | CRITICAL | Rejected; repository configuration and attributes can launch an unpinned filter process. |
| Move worktree-byte ownership into Git authority | HIGH | Rejected duplication; source authority already binds and rejects those bytes. |
| Rewrite the historical Phase 2B receipt | HIGH | Rejected; preserve immutable history and publish this correction addendum. |

## Scope and Nonclaims

This micro-transaction changes one test expectation and attached documentation.
It changes no production code or public interface and performs no runtime,
route, owner, Holo maintenance, activation, signing, write-denial, A-grade, or
retrieval-RSI operation. The live gate remains an expected skip until an
independently provisioned pinned Git image exists on O:/E:.
