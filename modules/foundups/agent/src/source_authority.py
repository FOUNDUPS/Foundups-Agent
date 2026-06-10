#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUp Source-Authority Enum -- Phase 1 (monorepo_poc only reachable).

Code-pin for the FoundUp source-authority axis defined by the contract
document ``docs/architecture/FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md``.
This module is pure, read-only, and intentionally tiny. It does NOT:

  - implement transition handling for ``external_proto`` / ``mvp_runtime``
    / ``dao_managed`` / ``archived`` (those stages are DEFINED but
    UNREACHABLE in Phase-1);
  - import or wire any runtime executor or consumer
    (no Hermes, no OpenClaw, no WRE consumer, no AI Overseer);
  - read source_authority / lifecycle_stage from any manifest, build
    contract, execution routing, or external job payload;
  - call subprocess / Popen / os.system / eval / exec / dynamic import
    / network / file write APIs;
  - touch CABR / payout / DAO / token logic.

THE HARD RULE (verbatim, load-bearing):

    A context bundle / manifest must be lifecycle-aware but CANNOT
    promote its lifecycle stage by declaration; promotion requires
    evidence + WSP gate + CABR / DAO proof. A declared stage from any
    manifest / external input is NEVER trusted.

Phase-1 enforcement of the hard rule:

  - ``resolve_source_authority(declared)`` ALWAYS returns
    ``(SourceAuthority.MONOREPO_POC, ignored_declaration)`` and NEVER
    raises. Any non-None declared value (even ``"monorepo_poc"`` itself)
    is reported as the second tuple element so a caller can observe the
    ignored declaration. Silent swallow is explicitly refused.
  - ``request_promotion(target)`` ALWAYS raises ``NotImplementedError``
    in Phase-1 -- promotion is not a function call, it is a multi-WSP
    multi-evidence event.

Predecessor commits (load-bearing):

  - #775 (merged 96a860cc3): read-only ContextBundle producer with
    builder-constant SOURCE_AUTHORITY = "monorepo_poc". See
    ``modules/foundups/agent/src/context_bundle_builder.py:132``. The
    enum's MONOREPO_POC member value is value-parity tested against that
    constant (drift guard).
  - 96314ab6c: ``fix(wre): close authority laundering in ContextBundle
    output (W10 return)``. The prior builder forwarded build_contract
    list and scalar fields verbatim, allowing authority dicts to launder
    through ``bundle.to_dict()``. That precedent is why the source-
    authority hard rule is enforced in code, not by guideline.

WSP Compliance:
  WSP 11 -- Interface contract (typed enum + typed functions).
  WSP 27 Section 11 -- Canonical maturity lifecycle (axis 1).
  WSP 50 -- Pre-action validation.
  WSP 84 -- Code reuse (no duplicate axis invented).
  WSP 97 -- Truth boundaries (read-only, no overclaim, no execution).
  WSP 103 -- Federation / OPO transition (Pre-OPO vs Post-OPO).
  WSP 109 -- Intake / RedDog actor role.

NAVIGATION:
  -> Contract: docs/architecture/FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md
  -> Value-parity guard: modules/foundups/agent/src/context_bundle_builder.py:132
  -> Tested by: modules/foundups/agent/tests/test_source_authority.py
"""

from __future__ import annotations

import enum
from typing import NoReturn, Optional, Tuple, Union

__all__ = [
    "SourceAuthority",
    "ACTIVE_STAGES",
    "resolve_source_authority",
    "request_promotion",
]


class SourceAuthority(str, enum.Enum):
    """The five source-authority stages defined by the Phase-1 contract.

    EXACTLY five members. String values are EXACT and stable -- they are
    the wire format of any downstream consumer.

    Only ``MONOREPO_POC`` is REACHABLE in Phase-1. The other four are
    DEFINED (so callers can refer to them by name) but UNREACHABLE
    (``request_promotion`` always raises).
    """

    MONOREPO_POC = "monorepo_poc"
    EXTERNAL_PROTO = "external_proto"
    MVP_RUNTIME = "mvp_runtime"
    DAO_MANAGED = "dao_managed"
    ARCHIVED = "archived"


# The set of stages that are reachable in Phase-1. Exactly one entry.
# Downstream code may compare a SourceAuthority against this set to
# decide whether to proceed without crossing the Phase-1 boundary.
ACTIVE_STAGES: frozenset = frozenset({SourceAuthority.MONOREPO_POC})


def resolve_source_authority(
    declared: Optional[Union[str, SourceAuthority]] = None,
) -> Tuple[SourceAuthority, Optional[str]]:
    """Resolve the effective source-authority stage. ALWAYS returns MONOREPO_POC.

    The function NEVER trusts the caller-supplied ``declared`` value.
    Returns a tuple ``(effective, ignored)`` where:

      - ``effective`` is ALWAYS ``SourceAuthority.MONOREPO_POC`` in
        Phase-1.
      - ``ignored`` carries the caller's ``declared`` value, stringified,
        if and only if a non-None value was supplied. Even when the
        declared value happens to be ``"monorepo_poc"`` (or
        ``SourceAuthority.MONOREPO_POC``) it is still reported as
        ignored, because the contract is that the builder is the source
        of truth -- not the caller. A caller can observe the second
        element to detect a (potentially malicious) declaration attempt.
      - ``ignored`` is ``None`` if and only if the caller passed
        ``None`` (or did not pass the argument).

    The function NEVER raises. Garbage input (wrong type, unknown
    string, casing variants, control chars, ints, dicts) is treated the
    same as a known-but-non-monorepo-poc value: ignored, reported.

    This is the Phase-1 enforcement of the hard rule:

        A context bundle / manifest must be lifecycle-aware but CANNOT
        promote its lifecycle stage by declaration.
    """
    if declared is None:
        return (SourceAuthority.MONOREPO_POC, None)
    # Stringify whatever the caller supplied so the report is observable
    # regardless of input type. We do NOT validate or normalize -- the
    # caller's intent is irrelevant; the builder decides.
    if isinstance(declared, SourceAuthority):
        ignored = declared.value
    else:
        ignored = str(declared)
    return (SourceAuthority.MONOREPO_POC, ignored)


def request_promotion(
    target: Union[str, SourceAuthority],
) -> NoReturn:
    """Promotion request. ALWAYS raises NotImplementedError in Phase-1.

    Promotion to a non-active stage is NOT a function call. It is a
    multi-WSP, multi-evidence event that requires:

      - sovereign-valve decision (012 or DAO-vote, stage-dependent),
      - federation / OPO / SmartDAO gate proof per WSP 103 / WSP 27,
      - CABR readiness per WSP 29 (where applicable),
      - signed evidence envelope.

    None of those exist in Phase-1. This function is the explicit
    refusal that pins the boundary.
    """
    # Stringify the target solely for the error message; the value is
    # never used as authority.
    if isinstance(target, SourceAuthority):
        target_str = target.value
    else:
        target_str = str(target)
    raise NotImplementedError(
        "source-authority promotion is not implemented in Phase-1; "
        "target=" + repr(target_str)
        + "; promotion requires evidence + WSP gate + CABR/DAO proof "
        "(see docs/architecture/FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md "
        "section 4 for the four defined transitions)."
    )
