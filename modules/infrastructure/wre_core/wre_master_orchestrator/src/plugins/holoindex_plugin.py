#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

HoloIndex WRE Plugin - Semantic Code Discovery Service

Transforms HoloIndex from standalone tool to core WRE service,
providing semantic search and WSP intelligence to all WRE components.

WSP Compliance:
- WSP 87: Code Navigation Protocol (core function)
- WSP 46: WRE Protocol (plugin architecture)
- WSP 65: Component Consolidation (as plugin)
- WSP 60: Pattern Memory Architecture
- WSP 75: Token-Based Development
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent.parent))

from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator import (
    OrchestratorPlugin, Pattern
)

# Import HoloIndex components
try:
    from holo_index.cli import HoloIndex
    from holo_index.qwen_advisor.advisor import QwenAdvisor, AdvisorContext
    from holo_index.dae_cube_organizer.dae_cube_organizer import DAECubeOrganizer
    HOLOINDEX_AVAILABLE = True
except ImportError:
    HOLOINDEX_AVAILABLE = False
    HoloIndex = None
    QwenAdvisor = None
    DAECubeOrganizer = None


@dataclass
class SearchPattern:
    """Pattern for semantic search operations"""
    query_type: str  # 'code', 'wsp', 'dae', 'pattern'
    enhancement: str  # Query enhancement strategy
    caching: bool    # Whether to cache results
    tokens: int      # Configured budget hint; not measured usage


class HoloIndexPlugin(OrchestratorPlugin):
    """
    HoloIndex WRE Plugin - Semantic Code Discovery Service

    Provides pattern-based code search and WSP guidance to all WRE components.
    Token reduction remains unmeasured until receipt-backed telemetry exists.
    """

    def __init__(self):
        """Initialize a dormant compatibility shell without opening Holo state."""
        super().__init__("holoindex")
        self.holo = None
        self.advisor = None
        self.dae_organizer = None

        # Pattern cache for learned search patterns
        self.pattern_cache: Dict[str, SearchPattern] = {}

        # Initialize common patterns
        self._initialize_patterns()

    def _initialize_patterns(self):
        """Initialize common search patterns for recall"""
        self.pattern_cache.update({
            "find_implementation": SearchPattern(
                query_type="code",
                enhancement="add module context",
                caching=True,
                tokens=150
            ),
            "check_compliance": SearchPattern(
                query_type="wsp",
                enhancement="add protocol numbers",
                caching=True,
                tokens=100
            ),
            "discover_patterns": SearchPattern(
                query_type="pattern",
                enhancement="add pattern keywords",
                caching=False,
                tokens=180
            ),
            "get_dae_context": SearchPattern(
                query_type="dae",
                enhancement="add DAE type",
                caching=True,
                tokens=120
            )
        })

    def execute(self, task: Dict) -> Any:
        """
        Block the dormant direct-Holo compatibility route.

        Governed retrieval uses the generation-bound owner-query script.
        Maintenance remains a separate WRE/CI transaction; an injected plugin
        callback is not freshness, topology, or maintenance authorization.
        """
        raise PermissionError(
            "direct HoloIndex plugin execution is blocked; "
            "use the governed owner query"
        )

    def _get_local_pattern(self, operation: str) -> Pattern:
        """Get pattern from local cache"""
        pattern_key = {
            'search': 'find_implementation',
            'wsp_guidance': 'check_compliance',
            'discover_patterns': 'discover_patterns',
            'dae_context': 'get_dae_context'
        }.get(operation, 'find_implementation')

        search_pattern = self.pattern_cache.get(pattern_key)

        return Pattern(
            id=f"holoindex_{operation}",
            wsp_chain=[87, 84, 50],  # Navigation, Memory, Verification
            tokens=search_pattern.tokens if search_pattern else 200,
            pattern="discover->search->guide"
        )

    def _search_with_patterns(self, task: Dict, pattern: Pattern) -> Dict:
        """
        Perform semantic search using patterns

        Configured pattern budget: 150. This is not measured token usage.
        """
        query = task.get('query', '')
        limit = task.get('limit', 5)

        # Search with HoloIndex
        results = self.holo.search(query, limit=limit)

        # Add advisor guidance if available
        if task.get('with_guidance', True) and results:
            context = AdvisorContext(
                query=query,
                code_hits=results.get('code', []),
                wsp_hits=results.get('wsps', [])
            )
            advisor_result = self.advisor.generate_guidance(context)
            results['guidance'] = {
                'text': advisor_result.guidance,
                'todos': advisor_result.todos,
                'risk_level': advisor_result.metadata.get('risk_level')
            }

        # Store successful pattern for learning
        if results and results.get('code'):
            self._store_search_pattern(query, results)

        return {
            'operation': 'search',
            'query': query,
            'results': results,
            'configured_token_budget': pattern.tokens,
            'token_usage_measured': False,
            'pattern_applied': pattern.id
        }

    def _index_with_patterns(self, task: Dict, pattern: Pattern) -> Dict:
        """
        Update HoloIndex indexes

        Configured pattern budget: 200. This is not measured token usage.
        """
        index_type = task.get('type', 'all')

        if index_type == 'all':
            self.holo.index_all()
        elif index_type == 'code':
            self.holo.index_code_entries()
        elif index_type == 'wsp':
            self.holo.index_wsp_entries()

        return {
            'operation': 'index',
            'type': index_type,
            'status': 'completed',
            'configured_token_budget': pattern.tokens,
            'token_usage_measured': False,
        }

    def _get_wsp_guidance(self, task: Dict, pattern: Pattern) -> Dict:
        """
        Get WSP compliance guidance

        Configured pattern budget: 100. This is not measured token usage.
        """
        query = task.get('query', '')
        code = task.get('code', '')

        # Search for relevant WSPs
        results = self.holo.search(f"WSP compliance {query}", limit=10)

        # Generate guidance
        context = AdvisorContext(
            query=query,
            code_hits=[{'content': code}] if code else [],
            wsp_hits=results.get('wsps', [])
        )

        advisor_result = self.advisor.generate_guidance(context)

        return {
            'operation': 'wsp_guidance',
            'query': query,
            'guidance': advisor_result.guidance,
            'reminders': advisor_result.reminders,
            'violations': advisor_result.metadata.get('violations', []),
            'risk_level': advisor_result.metadata.get('risk_level'),
            'configured_token_budget': pattern.tokens,
            'token_usage_measured': False,
        }

    def _get_dae_context(self, task: Dict, pattern: Pattern) -> Dict:
        """
        Get DAE structure intelligence

        Configured pattern budget: 120. This is not measured token usage.
        """
        dae_type = task.get('dae_type', 'auto')

        # Get DAE context from organizer
        context = self.dae_organizer.initialize_dae_context(
            dae_type if dae_type != 'auto' else None
        )

        return {
            'operation': 'dae_context',
            'dae_type': dae_type,
            'context': context,
            'configured_token_budget': pattern.tokens,
            'token_usage_measured': False,
        }

    def _discover_patterns(self, task: Dict, pattern: Pattern) -> Dict:
        """
        Discover reusable patterns in code

        Configured pattern budget: 180. This is not measured token usage.
        """
        module_path = task.get('module', '')
        pattern_type = task.get('pattern_type', 'all')

        # Search for patterns in module
        query = f"pattern {pattern_type} in {module_path}"
        results = self.holo.search(query, limit=20)

        # Extract patterns from results
        discovered_patterns = []
        for hit in results.get('code', []):
            if 'pattern' in hit.get('content', '').lower():
                discovered_patterns.append({
                    'location': hit.get('file', ''),
                    'pattern': hit.get('function', ''),
                    'description': hit.get('content', '')[:200]
                })

        return {
            'operation': 'discover_patterns',
            'module': module_path,
            'patterns_found': len(discovered_patterns),
            'patterns': discovered_patterns[:10],  # Top 10
            'configured_token_budget': pattern.tokens,
            'token_usage_measured': False,
        }

    def _store_search_pattern(self, query: str, results: Dict):
        """Store successful search pattern for learning"""
        # In production, this would store to WRE pattern memory
        # For now, we just track locally
        pattern_key = f"search_{query[:20]}"
        if pattern_key not in self.pattern_cache:
            self.pattern_cache[pattern_key] = SearchPattern(
                query_type="learned",
                enhancement="from successful search",
                caching=True,
                tokens=150
            )

    def get_service_endpoints(self) -> Dict[str, str]:
        """
        Get available service endpoints

        Returns mapping of service names to descriptions
        """
        return {
            "code_discovery": "Find code by semantic intent",
            "wsp_compliance": "Check WSP compliance",
            "pattern_extraction": "Extract reusable patterns",
            "dae_intelligence": "Get DAE structure info",
            "semantic_search": "General semantic search"
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get plugin performance metrics"""
        return {
            "patterns_cached": len(self.pattern_cache),
            "average_tokens": None,
            "token_reduction": None,
            "token_reduction_measured": False,
            "services_available": len(self.get_service_endpoints())
        }


# WRE Service Registration
def register_with_wre(master_orchestrator):
    """
    Register HoloIndex plugin with WRE Master

    This makes HoloIndex services available to all WRE components
    """
    plugin = HoloIndexPlugin()
    master_orchestrator.register_plugin(plugin)

    print(f"[HoloIndex] Registered as WRE plugin")
    print(f"[HoloIndex] Services available: {list(plugin.get_service_endpoints().keys())}")
    print("[HoloIndex] Token reduction telemetry: unmeasured")

    return plugin


if __name__ == "__main__":
    # Test plugin standalone
    plugin = HoloIndexPlugin()

    # Test search
    result = plugin.execute({
        'operation': 'search',
        'query': 'authentication module',
        'limit': 3,
        'with_guidance': True
    })

    print(f"Search Results: {len(result['results'].get('code', []))} code matches")
    print(f"Configured Token Budget: {result['configured_token_budget']}")
    print(f"Pattern Applied: {result['pattern_applied']}")

    # Test DAE context
    dae_result = plugin.execute({
        'operation': 'dae_context',
        'dae_type': 'YouTube Live'
    })

    print(f"\nDAE Context Retrieved")
    print(f"Configured Token Budget: {dae_result['configured_token_budget']}")

    # Show metrics
    metrics = plugin.get_metrics()
    print(f"\nPlugin Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
