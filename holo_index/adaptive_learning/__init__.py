#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io

"""
# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

HoloIndex Phase 3: Adaptive Learning Package
===========================================

[MLE-STAR REMOVED - DEEMED VIBECODING - 2025-09-23]
MLE-STAR was removed from the codebase as it was pure documentation without
functional implementation (0.0% validation score, no working code).

Now implements direct adaptive learning through:
- Intelligent query enhancement using pattern analysis
- Search optimization through ensemble ranking
- Response improvement via context-aware processing

WSP Compliance: WSP 48 (Recursive Improvement), WSP 54 (Agent Coordination)
"""

from .adaptive_query_processor import AdaptiveQueryProcessor, AdaptiveQueryResult
from .vector_search_optimizer import VectorSearchOptimizer, OptimizedSearchResults
from .llm_response_optimizer import LLMResponseOptimizer, OptimizedResponse
from .memory_architecture_evolution import MemoryArchitectureEvolution, MemoryOptimizationResult
from .adaptive_learning_orchestrator import AdaptiveLearningOrchestrator
from .breadcrumb_tracer import get_tracer, BreadcrumbTracer, create_contract, signal_ready

__all__ = [
    'AdaptiveQueryProcessor',
    'AdaptiveQueryResult',
    'VectorSearchOptimizer',
    'OptimizedSearchResults',
    'LLMResponseOptimizer',
    'OptimizedResponse',
    'MemoryArchitectureEvolution',
    'MemoryOptimizationResult',
    'AdaptiveLearningOrchestrator',
    'BreadcrumbTracer',
    'get_tracer',
    'create_contract',
    'signal_ready'
]

__version__ = "3.0.0"
__status__ = "experimental_cli_disabled"
