"""Compatibility re-export of the HoloIndex-owned freshness authority."""

from holo_index.query_freshness_gate import (
    BASELINE_COLLECTIONS as BASELINE_COLLECTIONS,
    BASELINE_FRESHNESS_PATHS as BASELINE_FRESHNESS_PATHS,
    FreshnessSnapshot as FreshnessSnapshot,
    HoloQueryFreshnessGate as HoloQueryFreshnessGate,
    MAINTENANCE_ACTIVE_ERROR as MAINTENANCE_ACTIVE_ERROR,
    MAINTENANCE_ACTIVE_REASON as MAINTENANCE_ACTIVE_REASON,
    MAINTENANCE_UNPROVEN_ERROR as MAINTENANCE_UNPROVEN_ERROR,
    MAINTENANCE_UNPROVEN_REASON as MAINTENANCE_UNPROVEN_REASON,
    maintenance_reason_for_error as maintenance_reason_for_error,
    normalize_binding as normalize_binding,
    snapshot_error as snapshot_error,
)
from holo_index.query_freshness_gate import __all__ as __all__
