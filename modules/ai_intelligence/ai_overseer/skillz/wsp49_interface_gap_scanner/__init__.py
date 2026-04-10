"""WSP 49 INTERFACE gap discovery — queue + scaffold prompts only (no repo writes)."""

from .executor import discover_interface_gaps, rank_gaps, SCAN_DOMAIN_ORDER

__all__ = ["discover_interface_gaps", "rank_gaps", "SCAN_DOMAIN_ORDER"]
