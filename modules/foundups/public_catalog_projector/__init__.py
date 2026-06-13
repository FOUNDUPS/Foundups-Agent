"""Scope-free Public FoundUp Catalog projector + validator (Phase 1).

Derives a scope-free public catalog (``public/f/public_catalog.json``) from the
canonical registry and validates, FAIL-CLOSED, that it contains ONLY
public-allowlisted fields. The validator is the leak guard that lets the public
``/f/`` surface (a later slice) read a PROJECTION instead of the member runtime
catalog ``public/member/mall-video-catalog.json``.

Spec context: ``docs/audits/architecture/PLAYFOUNDUPS_MALL_PUBLIC_DISCOVERY_AUDIT_PHASE1.md``
Mirrors: ``modules/foundups/portfolio_validator`` + ``public/f/portfolio_data.json``.

WSP_97 boundaries:
  - PUBLIC_CATALOG_PROJECTOR_PHASE1_ONLY
  - DERIVED_FROM_REGISTRY_ONLY (registry is the single source)
  - NO_RUNTIME_CATALOG_READ (projection path never reads mall-video-catalog.json)
  - NO_FRONTEND_CHANGE / NO_UNGATING / NO_AUTH_CHANGE
"""

from .src.projector import (
    PUBLIC_ALLOWLIST,
    KNOWN_MEMBER_SCOPED_FIELDS,
    SourceError,
    ValidationReport,
    Violation,
    find_repo_root,
    generate_projection,
    load_registry,
    validate_projection,
    write_projection,
)

__all__ = [
    "PUBLIC_ALLOWLIST",
    "KNOWN_MEMBER_SCOPED_FIELDS",
    "SourceError",
    "ValidationReport",
    "Violation",
    "find_repo_root",
    "generate_projection",
    "load_registry",
    "validate_projection",
    "write_projection",
]
