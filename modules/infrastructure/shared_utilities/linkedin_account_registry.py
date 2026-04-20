"""
LinkedIn Account Registry - Single source of truth for LinkedIn company accounts.

Purpose:
- Centralize LinkedIn company IDs and account metadata.
- Load from LINKEDIN_ACCOUNTS_JSON env var for flexibility.
- Provide fuzzy matching and URL generation for company pages.

WSP References:
- WSP 3: Functional Distribution (shared utilities for cross-domain config)
- WSP 60: Module Memory Architecture (env-based configuration)

Usage:
    from modules.infrastructure.shared_utilities.linkedin_account_registry import (
        get_accounts,
        get_company_id,
        get_article_url,
        get_admin_url,
        get_default_company,
    )

    # Get all accounts
    accounts = get_accounts()

    # Get specific company ID (with fuzzy matching)
    company_id = get_company_id("undaodu")  # Returns "68706058"
    company_id = get_company_id("monk")     # Alias -> "undaodu" -> "68706058"

    # Get URLs
    article_url = get_article_url("foundups")
    admin_url = get_admin_url("move2japan")

Env vars:
    LINKEDIN_ACCOUNTS_JSON={"foundups":"1263645","undaodu":"68706058",...}
    LINKEDIN_DEFAULT_COMPANY=foundups
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Company Name Constants - Use these instead of hardcoded strings
# ============================================================================
class LinkedInCompany:
    """
    LinkedIn company name constants for type-safe usage.

    Usage:
        from linkedin_account_registry import LinkedInCompany, get_company_id
        company_id = get_company_id(LinkedInCompany.FOUNDUPS)
    """
    FOUNDUPS = "foundups"
    UNDAODU = "undaodu"
    MOVE2JAPAN = "move2japan"
    AUTONOMOUSWALL = "autonomouswall"
    ESINGULARITY = "esingularity"
    LNREPUBLICANVOTERS = "lnrepublicanvoters"
    AIHARMONIC = "aiharmonic"
    FOUNDUPS100X100 = "foundups100x100"
    BITCLOUTFORK = "bitcloutfork"
    DECENTRALIZEDCRYPTO = "decentralizedcrypto"
    EDUIT = "eduit"


# Default fallback if env not set (minimal - use LINKEDIN_ACCOUNTS_JSON env var)
# Format: LINKEDIN_ACCOUNTS_JSON='{"foundups":"1263645","undaodu":"156137799","move2japan":"104834798"}'
_DEFAULT_ACCOUNTS: Dict[str, str] = {}

# Aliases for fuzzy matching (lowercase -> canonical name)
ACCOUNT_ALIASES: Dict[str, str] = {
    # Personal/brand aliases
    "foundups\u00ae": "foundups",
    "foundups (registered)": "foundups",
    "fu": "foundups",
    # UnDaoDu aliases
    "monk": "undaodu",
    "012": "undaodu",
    "michael": "undaodu",
    "mjt": "undaodu",
    "undao": "undaodu",
    # Move2Japan aliases
    "m2j": "move2japan",
    "japan": "move2japan",
    # AutonomousWall
    "autonomous wall": "autonomouswall",
    "aw": "autonomouswall",
    "wall": "autonomouswall",
    # LN Republican
    "ln republican": "lnrepublicanvoters",
    "republican": "lnrepublicanvoters",
    "rvat": "lnrepublicanvoters",
    # AI Harmonic / HapticSign
    "ai harmonic": "aiharmonic",
    "haptic": "aiharmonic",
    "hapticsign": "aiharmonic",
    # 100x100
    "100x100": "foundups100x100",
    "100": "foundups100x100",
    # BitCloutFork
    "bitclout": "bitcloutfork",
    "bcf": "bitcloutfork",
    # Decentralized Crypto Fund
    "crypto fund": "decentralizedcrypto",
    "dcf": "decentralizedcrypto",
    "crypto": "decentralizedcrypto",
    # eSingularity
    "singularity": "esingularity",
    "esingularity": "esingularity",
}


def _load_accounts_from_env() -> Dict[str, str]:
    """
    Load LinkedIn accounts from LINKEDIN_ACCOUNTS_JSON env var.

    Format: JSON object mapping name -> company_id
    Example: {"foundups":"1263645","undaodu":"68706058","move2japan":"104834798"}

    Returns:
        Dict mapping account name (lowercase) to company ID
    """
    accounts_json = os.getenv("LINKEDIN_ACCOUNTS_JSON", "")
    if accounts_json:
        try:
            raw = json.loads(accounts_json)
            # Normalize keys to lowercase
            return {k.lower().strip(): str(v).strip() for k, v in raw.items()}
        except json.JSONDecodeError as e:
            logger.warning(f"[LINKEDIN] Invalid LINKEDIN_ACCOUNTS_JSON: {e}, using defaults")
    return dict(_DEFAULT_ACCOUNTS)


def get_accounts() -> Dict[str, str]:
    """
    Get all LinkedIn accounts.

    Returns:
        Dict mapping account name -> company ID
    """
    return _load_accounts_from_env()


def get_default_company() -> str:
    """
    Get the default company ID from LINKEDIN_DEFAULT_COMPANY env var.

    Returns:
        Company ID string (defaults to FOUNDUPS "1263645")
    """
    default_name = os.getenv("LINKEDIN_DEFAULT_COMPANY", "foundups").lower().strip()
    accounts = get_accounts()

    # Check if default is in accounts
    if default_name in accounts:
        return accounts[default_name]

    # Check aliases
    canonical = ACCOUNT_ALIASES.get(default_name)
    if canonical and canonical in accounts:
        return accounts[canonical]

    # No fallback - env var must be set
    logger.error("[LINKEDIN] LINKEDIN_ACCOUNTS_JSON env var not set or missing accounts")
    return ""


def _resolve_account_name(name: str) -> Optional[str]:
    """
    Resolve account name using exact match, alias, or fuzzy match.

    Args:
        name: Account name or alias

    Returns:
        Canonical account name or None if not found
    """
    if not name:
        return None

    name_lower = name.lower().strip()
    accounts = get_accounts()

    # 1. Exact match
    if name_lower in accounts:
        return name_lower

    # 2. Check aliases
    if name_lower in ACCOUNT_ALIASES:
        canonical = ACCOUNT_ALIASES[name_lower]
        if canonical in accounts:
            return canonical

    # 3. Fuzzy/partial match
    for key in accounts:
        if name_lower in key or key in name_lower:
            return key

    return None


def get_company_id(name: str) -> str:
    """
    Get company ID for an account name (with fuzzy matching).

    Args:
        name: Account name, alias, or partial match

    Returns:
        Company ID string (falls back to default if not found)

    Examples:
        get_company_id("foundups")  # "1263645"
        get_company_id("monk")      # "68706058" (alias for undaodu)
        get_company_id("m2j")       # "104834798" (alias for move2japan)
    """
    accounts = get_accounts()
    resolved = _resolve_account_name(name)

    if resolved and resolved in accounts:
        return accounts[resolved]

    logger.warning(f"[LINKEDIN] Unknown account '{name}', using default")
    return get_default_company()


def get_article_url(name: str = None) -> str:
    """
    Get LinkedIn article editor URL for an account.

    Args:
        name: Account name (optional, uses default if not provided)

    Returns:
        Direct article editor URL with company ID embedded

    Example:
        get_article_url("foundups")
        # "https://www.linkedin.com/article/new/?author=urn%3Ali%3Afs_normalized_company%3A1263645"
    """
    if name:
        company_id = get_company_id(name)
    else:
        company_id = get_default_company()

    return f"https://www.linkedin.com/article/new/?author=urn%3Ali%3Afs_normalized_company%3A{company_id}"


def get_admin_url(name: str = None) -> str:
    """
    Get LinkedIn company admin posts URL.

    Args:
        name: Account name (optional, uses default if not provided)

    Returns:
        Company admin page URL

    Example:
        get_admin_url("foundups")
        # "https://www.linkedin.com/company/1263645/admin/page-posts/published/"
    """
    if name:
        company_id = get_company_id(name)
    else:
        company_id = get_default_company()

    return f"https://www.linkedin.com/company/{company_id}/admin/page-posts/published/"


def get_company_page_url(name: str = None) -> str:
    """
    Get public LinkedIn company page URL.

    Args:
        name: Account name (optional, uses default if not provided)

    Returns:
        Public company page URL
    """
    if name:
        company_id = get_company_id(name)
    else:
        company_id = get_default_company()

    return f"https://www.linkedin.com/company/{company_id}/"


def list_all_accounts() -> Dict[str, Dict[str, str]]:
    """
    List all accounts with their URLs (for debugging/display).

    Returns:
        Dict mapping account name -> {company_id, article_url, admin_url}
    """
    accounts = get_accounts()
    result = {}
    for name, company_id in accounts.items():
        result[name] = {
            "company_id": company_id,
            "article_url": get_article_url(name),
            "admin_url": get_admin_url(name),
            "page_url": get_company_page_url(name),
        }
    return result


# Module-level exports for convenience
__all__ = [
    "LinkedInCompany",
    "get_accounts",
    "get_company_id",
    "get_article_url",
    "get_admin_url",
    "get_company_page_url",
    "get_default_company",
    "list_all_accounts",
    "ACCOUNT_ALIASES",
]
