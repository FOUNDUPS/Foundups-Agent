# ModLog

## 2026-10-28 — Public LinkedIn identity and source refresh

Verified hornethunters as the Hornethunter.com company page using its public
page and owner-supplied launch post. Added discoverable identity documentation,
kept the post activity ID separate from the unresolved numeric company ID, and
removed tracking parameters from evidence links. Added the company footer link
and Organization.sameAs while retaining the personal profile. Source snapshot
now matches Sites version 16. Local 18-page structural checks and both isolated
build tests pass. No LinkedIn publication or private data import occurred.

## 2026-10-28 — Repair PR 2251 canonical test inventory

CI run 40646023390 stopped at the registry check before executing suites. The
source import added test_public_build.py but omitted its generated registry row.
Regenerated through the existing wre_core owner: one Hornet Hunter entry and
total 1775 -> 1776; all 273 quarantine entries remain unchanged. Added the
stage/regenerate/check preflight to the module test handoff. No classification,
security exception or website deployment policy changed. Bounded source reads
and deterministic validation were used; no HoloIndex/Qwen/Gemma runtime or
bootstrap compliance is claimed.

## 2026-10-28 — Sanitized website source handoff

012 requested continuity of the Hornet Hunter work inside Foundups-Agent without
exposing secrets. Imported the public generator, SEO module, CSS/JS and minimal
public video fields. Added a hash-pinned public asset manifest, restoration tool,
build validation and maintenance/privacy contracts. Excluded unpublished manual
content, private documentation, original media, administrative identifiers,
credentials and source Git history.

Placement follows the existing FoundUp-owned website pattern (WSP 3/49).
Read-before-change and bounded lexical retrieval are documented in README
(WSP 50); this log and public-only continuity record address WSP 22/60.
No WRE/HoloIndex runtime or semantic freshness acceptance is claimed (WSP 97).
No live site, forms, email or LinkedIn mutation is performed by this import.
