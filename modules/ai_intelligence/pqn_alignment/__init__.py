"""
PQN Alignment Module - Phantom Quantum Node detection and analysis.

Public API for rESP research validation and council optimization.
"""

from .src.detector.api import run_detector
from .src.sweep.api import run_sweep, phase_sweep
from .src.council.api import council_run, council_run_with_llm
from .src.results_db import (
    init_db, 
    index_run, 
    index_council_run, 
    query_runs, 
    query_cross_analysis,
    analyze_cross_model_performance,
    correlate_campaign_council_results
)
from .src.io.api import promote
from .src.pqn_alignment_dae import PQNAlignmentDAE
from .src.theory_archive import get_theory_archive_context

__all__ = [
    "run_detector",
    "run_sweep",
    "phase_sweep",
    "council_run",
    "council_run_with_llm",  # S11 Local LLM Integration
    "init_db",
    "index_run",
    "index_council_run",
    "query_runs",
    "query_cross_analysis",
    "analyze_cross_model_performance",
    "correlate_campaign_council_results",
    "promote",
    "PQNAlignmentDAE",
    "get_theory_archive_context",
]
