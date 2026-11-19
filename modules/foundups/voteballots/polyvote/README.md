# Poly Vote

**Status:** DOCUMENTATION_ONLY / SPECIFIED_NOT_IMPLEMENTED.
**Classification:** separately documented module **within** the existing Vote/Ballots FoundUp (`voteballots`).
**Module name:** `polyvote`; not a new FoundUp identity, repository, token, tenant or authentication system.

## Outcome -> solution -> pain

**Outcome:** eligible verified officeholders can propose people for leadership/committee roles and express non-binding preferences, choosing deliberately what becomes public.

**Solution:** reuse shared sign-in and separately qualified current-office authorization; unlock scoped Poly Vote features privately; keep authorized participation distinct from per-record public disclosure. Public Vote profiles may show only deliberately published nominations/preferences. The module has its own [roadmap](ROADMAP.md), [interface](INTERFACE.md) and [change log](ModLog.md).

**Pain:** community popularity, identity checks, institutional authority and public endorsements are easily conflated. The system needs clear eligibility, privacy, correction and evidence boundaries, not an assumption that signing a message confers congressional authority.

## Relationship to adjacent components

Vote owns the public discovery experience and overall civic schema. Poly Vote owns the proposed verified-office nomination/ballot workflow. HPC is the community layer; Voice is civic action/public expression; [Poly Voice](../../polyvoice/README.md) is private meeting capture/commitments. None automatically gains another's privileges or private data.

The [integration index](../docs/VOTE_VOICE_INTEGRATION.md) links these owners. Detailed Poly Vote design stays here, rather than expanding the parent roadmap into every feature specification.

## Scope boundaries

The target includes chamber/leadership and committee nomination/preference workflows, private conversation around them, and an optional public committee-tile view of a representative's disclosed choices. Cabinet-related concepts require their own role/authority definition; they are not silently treated as congressional committees.

Community nominations and public polls remain a separate non-binding track. No in-app nomination puts anyone on an official ballot, fills a committee seat or substitutes for an official congressional proceeding. A promoted name is not evidence of that person's endorsement, participation or eligibility.

Existing public Vote card/media behavior remains a shared-Mall dependency. This documentation does not implement a ballot, authentication role, chat server, roster, route or player.
