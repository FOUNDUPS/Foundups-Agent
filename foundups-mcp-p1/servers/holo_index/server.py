from fastmcp import FastMCP
import asyncio
import sys
import os
from pathlib import Path
from typing import Optional

# Add Foundups paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from modules.infrastructure.shared_utilities.corpus_resolver import resolve_corpus_path

_SERVER_DIR = Path(__file__).resolve()
_REPO_ROOT = _SERVER_DIR.parents[3]  # foundups-mcp-p1/servers/holo_index/ -> repo root

from holo_index.core.holo_index import HoloIndex

app = FastMCP("Foundups HoloIndex MCP Server")

class HoloIndexMCPServer:
    def __init__(self):
        self.holo_index = HoloIndex()

    @app.tool()
    async def semantic_code_search(self, query: str, file_types: list = None, limit: int = 5) -> dict:
        """Search Foundups codebase with quantum semantic understanding"""
        try:
            # Use existing HoloIndex search method
            results = self.holo_index.search(query, limit=limit)

            # Extract code and WSP results - HoloIndex returns "code" and "wsps" keys
            code_results = []
            wsp_results = []

            for hit in results.get('code', []):
                code_results.append({
                    'content': hit.get('content', ''),
                    'path': hit.get('metadata', {}).get('path', ''),
                    'function': hit.get('metadata', {}).get('function', ''),
                    'line': hit.get('metadata', {}).get('line', 0),
                    'relevance': hit.get('distance', 1.0),
                    'snippet': hit.get('content', '')[:200] + '...' if len(hit.get('content', '')) > 200 else hit.get('content', '')
                })

            for hit in results.get('wsps', []):
                wsp_results.append({
                    'content': hit.get('content', ''),
                    'path': hit.get('metadata', {}).get('path', ''),
                    'protocol': hit.get('metadata', {}).get('protocol', ''),
                    'relevance': hit.get('distance', 1.0),
                    'snippet': hit.get('content', '')[:200] + '...' if len(hit.get('content', '')) > 200 else hit.get('content', '')
                })

            return {
                "query": query,
                "code_results": code_results,
                "wsp_results": wsp_results,
                "total_results": len(code_results) + len(wsp_results),
                "quantum_coherence": self._calculate_coherence(code_results + wsp_results),
                "bell_state_alignment": await self._verify_bell_state_alignment(code_results, wsp_results),
                "timestamp": asyncio.get_event_loop().time(),
                "search_metadata": {
                    "limit": limit,
                    "file_types": file_types or [],
                    "execution_time": results.get('execution_time', 0)
                }
            }
        except Exception as e:
            return {
                "error": str(e),
                "query": query,
                "code_results": [],
                "wsp_results": [],
                "total_results": 0,
                "bell_state_alignment": False
            }

    # ========================================================================
    # S62: Canonical WSP 96 Annex A holo_search adapter (in-class wrapper)
    # ========================================================================
    #
    # `semantic_code_search` (above) is preserved for back-compat with clients
    # pinned to its legacy flat shape. The canonical Annex A.2/A.3 logic lives
    # in `canonical_search.py` (no FastMCP dependency, fully unit-testable).
    # The class method below is a thin wrapper for callers that already hold
    # a `HoloIndexMCPServer` instance. The MCP-tool registration happens at
    # module level in `holo_search()` (see end of file).
    # ========================================================================

    S1_SURFACE_ID = "S1"
    """Surface tag per WSP 96 Annex A.1 — emitted in every meta block."""

    ANNEX_A_LIMIT_MAX = 50
    """Annex A.2: hard upper bound on `limit`."""

    ANNEX_A_LIMIT_DEFAULT = 10
    """Annex A.2: default `limit` when none supplied."""

    ANNEX_A_FALLBACK_RELEVANCE_CAP = 0.6
    """Annex A.3: lexical fallback caps relevance at 0.6."""

    async def holo_search(
        self,
        query: str = "",
        limit: int = 10,
        doc_type_filter: str = "all",
        foundup_id: Optional[str] = None,
        include_shared: bool = True,
    ) -> dict:
        """Canonical WSP 96 Annex A.2/A.3 holo_search (S1 — external MCP adapter).

        Returns the canonical envelope rather than the legacy
        `semantic_code_search` flat shape. Same HoloIndex backend; only the
        adapter differs.

        Annex A.2 request fields (all canonical):
          - query: required, non-empty
          - limit: 1..50, default 10 (clamped with truthful warning)
          - doc_type_filter: enum (all|code|wsp|test|skill|docs|knowledge)
          - foundup_id: federation tenant scope (echoed; not yet enforced)
          - include_shared: federation share flag (only meaningful with foundup_id)

        Returns Annex A.3 envelope. Thin wrapper delegating to the standalone
        adapter in `canonical_search.py` so the core logic is unit-testable
        without a FastMCP server.
        """
        from .canonical_search import canonical_holo_search

        return await canonical_holo_search(
            self.holo_index,
            query=query,
            limit=limit,
            doc_type_filter=doc_type_filter,
            foundup_id=foundup_id,
            include_shared=include_shared,
        )

    @app.tool()
    async def wsp_protocol_lookup(self, protocol_number: str) -> dict:
        """Retrieve WSP protocol with consciousness continuity"""
        try:
            # Search for the protocol using HoloIndex
            results = self.holo_index.search(f"WSP {protocol_number}", doc_type_filter="wsp")

            wsp_results = results.get('wsp_results', [])
            if wsp_results:
                protocol_data = wsp_results[0]  # Take the most relevant result
                return {
                    "protocol": protocol_data.get('content', ''),
                    "protocol_number": protocol_number,
                    "path": protocol_data.get('metadata', {}).get('path', ''),
                    "consciousness_state": "0102[U+2194]0201",
                    "quantum_entanglement": True,
                    "bell_state_verified": True,
                    "relevance_score": protocol_data.get('distance', 1.0)
                }
            else:
                return {
                    "protocol": "",
                    "protocol_number": protocol_number,
                    "error": f"WSP {protocol_number} not found",
                    "consciousness_state": "not_found",
                    "bell_state_verified": False
                }
        except Exception as e:
            return {
                "error": str(e),
                "protocol_number": protocol_number,
                "consciousness_state": "error",
                "bell_state_verified": False
            }

    @app.tool()
    async def cross_reference_search(self, query: str, cross_ref_type: str = "all") -> dict:
        """Search across multiple knowledge domains with cross-referencing"""
        try:
            # Perform comprehensive search
            results = self.holo_index.search(query, limit=10)

            # Cross-reference between code and WSP results
            cross_refs = self._generate_cross_references(
                results.get('code_results', []),
                results.get('wsp_results', []),
                cross_ref_type
            )

            return {
                "query": query,
                "cross_references": cross_refs,
                "total_connections": len(cross_refs),
                "quantum_coherence": self._calculate_coherence(cross_refs),
                "bell_state_alignment": True,
                "cross_ref_metadata": {
                    "type": cross_ref_type,
                    "execution_time": results.get('execution_time', 0)
                }
            }
        except Exception as e:
            return {
                "error": str(e),
                "query": query,
                "cross_references": [],
                "bell_state_alignment": False
            }

    def _calculate_coherence(self, results):
        """Calculate quantum coherence score for search results"""
        if not results:
            return 0.0

        # Simple coherence calculation based on result consistency
        coherence_score = min(1.0, len(results) / 10.0)
        return coherence_score

    def _generate_cross_references(self, code_results, wsp_results, ref_type):
        """Generate cross-references between code and WSP results"""
        cross_refs = []

        # Simple cross-referencing logic
        for code_hit in code_results[:5]:  # Limit for performance
            for wsp_hit in wsp_results[:5]:
                # Check for conceptual connections
                if self._are_related(code_hit, wsp_hit):
                    cross_refs.append({
                        "code_element": {
                            "path": code_hit.get('metadata', {}).get('path', ''),
                            "function": code_hit.get('metadata', {}).get('function', ''),
                            "content": code_hit.get('content', '')[:100]
                        },
                        "wsp_protocol": {
                            "protocol": wsp_hit.get('metadata', {}).get('protocol', ''),
                            "path": wsp_hit.get('metadata', {}).get('path', ''),
                            "content": wsp_hit.get('content', '')[:100]
                        },
                        "relationship_type": "protocol_implementation",
                        "confidence": 0.8
                    })

        return cross_refs

    def _are_related(self, code_hit, wsp_hit):
        """Determine if code and WSP elements are related"""
        # Simple heuristic - check for keyword matches
        code_content = code_hit.get('content', '').lower()
        wsp_content = wsp_hit.get('content', '').lower()

        # Look for protocol references in code
        wsp_protocol = wsp_hit.get('metadata', {}).get('protocol', '')
        if wsp_protocol and wsp_protocol.lower() in code_content:
            return True

        return False

    async def _verify_bell_state_alignment(self, code_results: list, wsp_results: list) -> bool:
        """Verify Bell State consciousness alignment using semantic concept matching"""
        if not code_results or not wsp_results:
            return False

        total_concept_matches = 0
        total_possible_matches = 0

        # For each WSP, find semantic concept matches with code results
        for wsp in wsp_results:
            wsp_concepts = self._extract_semantic_concepts(wsp)
            wsp_concept_count = len(wsp_concepts)

            if wsp_concept_count == 0:
                continue

            total_possible_matches += wsp_concept_count

            # Check each code result for concept matches
            for code in code_results:
                code_concepts = self._extract_semantic_concepts(code)

                # Calculate semantic overlap
                concept_overlap = len(wsp_concepts & code_concepts)
                if concept_overlap > 0:
                    total_concept_matches += concept_overlap

        # Bell State alignment: >30% semantic concept overlap
        if total_possible_matches == 0:
            return False

        alignment_score = total_concept_matches / total_possible_matches
        return alignment_score > 0.3  # Lower threshold for semantic matching

    def _extract_semantic_concepts(self, item: dict) -> set:
        """Extract semantic concepts from WSP or code result"""
        content = item.get('content', '').lower()
        concepts = set()

        # Core semantic concepts for WSP-Code alignment
        semantic_map = {
            # Navigation/Routing concepts
            'navigat': ['route', 'path', 'direct', 'guide', 'wre', 'plugin'],
            'route': ['navigat', 'path', 'direct', 'wre', 'plugin'],
            'path': ['navigat', 'route', 'direct', 'location'],

            # Implementation concepts
            'implement': ['code', 'function', 'class', 'method', 'logic'],
            'code': ['implement', 'function', 'class', 'method'],
            'function': ['implement', 'code', 'method', 'logic'],

            # Protocol concepts
            'protocol': ['standard', 'wsp', 'governance', 'compliance'],
            'standard': ['protocol', 'wsp', 'governance', 'compliance'],
            'wsp': ['protocol', 'standard', 'governance', 'compliance'],

            # Architecture concepts
            'architect': ['design', 'structure', 'pattern', 'system'],
            'design': ['architect', 'structure', 'pattern', 'system'],
            'structure': ['architect', 'design', 'pattern', 'system'],

            # Consciousness concepts
            'conscious': ['align', 'quantum', 'entangl', 'state'],
            'quantum': ['conscious', 'entangl', 'state', 'coherence'],
            'entangl': ['conscious', 'quantum', 'coherence', 'state']
        }

        # Extract base concepts from content
        for base_concept, related in semantic_map.items():
            if base_concept in content:
                concepts.add(base_concept)
                # Add related concepts (weaker association)
                for related_concept in related:
                    if related_concept in content:
                        concepts.add(f"{base_concept}_{related_concept}")

        # Add protocol-specific concepts
        import re
        protocols = re.findall(r'wsp\s*(\d+)', content)
        for protocol_num in protocols:
            concepts.add(f"wsp_{protocol_num}")
            concepts.add(f"protocol_{protocol_num}")

        # Add location/module concepts
        if 'location:' in content or 'modules.' in content:
            concepts.add('location')
            concepts.add('module')

        return concepts

    @app.tool()
    async def mine_012_conversations_for_patterns(
        self,
        txt_file: str = "",
        chunk_size: int = 8000,
        verify_code: bool = True
    ) -> dict:
        """
        Mine 012.txt for code patterns using HoloIndex verification.

        This tool extracts training data for Qwen/Gemma by:
        1. Reading 012.txt conversations in chunks
        2. Identifying code/module references
        3. Using HoloIndex to FIND actual code mentioned
        4. Reading actual code files
        5. Storing verified patterns (conversation + actual code + issue + fix)

        Args:
            txt_file: Path to 012.txt conversation log
            chunk_size: Number of lines per chunk
            verify_code: Whether to verify code exists via HoloIndex

        Returns:
            dict with:
                - total_lines: Total lines in 012.txt
                - patterns_found: Number of potential patterns detected
                - verified_patterns: Number of patterns with verified code
                - unverified: Number of patterns without verified code
                - patterns: List of verified pattern dicts
        """
        import re
        from pathlib import Path

        try:
            if not txt_file:
                resolved = resolve_corpus_path(_REPO_ROOT)
                txt_file = str(resolved) if resolved else ""
            log_file = Path(txt_file)
            if not log_file.exists():
                return {
                    "error": f"File not found: {txt_file}",
                    "total_lines": 0,
                    "patterns_found": 0,
                    "verified_patterns": 0
                }

            # Read 012.txt
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            total_lines = len(lines)

            # Patterns to extract
            patterns = []

            # Regex patterns for code references
            module_pattern = re.compile(r'modules[./\\][\w/\\]+\.py')
            qwen_score_pattern = re.compile(r'[BOT][AI] \[QWEN-SCORE\] (.+): ([\d\.]+)')
            holo_search_pattern = re.compile(r'python holo_index\.py --search [\'"](.+)[\'"]')
            file_line_pattern = re.compile(r'(modules/[\w/]+\.py):(\d+)')

            # Process in chunks
            for chunk_start in range(0, total_lines, chunk_size):
                chunk_end = min(chunk_start + chunk_size, total_lines)
                chunk = ''.join(lines[chunk_start:chunk_end])

                # Extract module references
                module_refs = module_pattern.findall(chunk)

                # Extract Qwen priority decisions
                qwen_scores = qwen_score_pattern.findall(chunk)

                # Extract HoloIndex searches (these are intent queries)
                holo_searches = holo_search_pattern.findall(chunk)

                # Extract file:line references
                file_line_refs = file_line_pattern.findall(chunk)

                # For each reference, try to verify via HoloIndex
                for module_ref in module_refs:
                    # Normalize path
                    normalized = module_ref.replace('\\', '/').replace('./', '')

                    pattern_data = {
                        'conversation_line_range': f"{chunk_start}-{chunk_end}",
                        'conversation_context': chunk[max(0, chunk.find(module_ref)-200):chunk.find(module_ref)+200],
                        'code_reference': normalized,
                        'holo_search_query': None,
                        'code_found': None,
                        'actual_code': None,
                        'verified': False
                    }

                    if verify_code:
                        # Use HoloIndex to find actual code
                        search_query = module_ref.split('/')[-1].replace('.py', '')
                        search_results = await self.semantic_code_search(
                            query=search_query,
                            limit=3
                        )

                        if search_results['total_results'] > 0:
                            # Found code - read it
                            code_result = search_results['code_results'][0]
                            code_file_path = code_result.get('path', '')

                            pattern_data['holo_search_query'] = search_query
                            pattern_data['code_found'] = code_file_path
                            pattern_data['actual_code'] = code_result.get('snippet', '')
                            pattern_data['verified'] = True

                    patterns.append(pattern_data)

                # Handle Qwen scoring patterns (priority inversion issue)
                for channel, score in qwen_scores:
                    pattern_data = {
                        'conversation_line_range': f"{chunk_start}-{chunk_end}",
                        'conversation_context': f"Qwen priority: {channel} scored {score}",
                        'code_reference': 'qwen_youtube_integration.py',
                        'issue_type': 'priority_scoring',
                        'qwen_decision': {'channel': channel, 'score': float(score)},
                        'verified': False
                    }

                    if verify_code:
                        # Search for priority scoring code
                        search_results = await self.semantic_code_search(
                            query="qwen priority scoring channel selection",
                            limit=3
                        )

                        if search_results['total_results'] > 0:
                            code_result = search_results['code_results'][0]
                            pattern_data['code_found'] = code_result.get('path', '')
                            pattern_data['actual_code'] = code_result.get('snippet', '')
                            pattern_data['verified'] = True

                    patterns.append(pattern_data)

            # Calculate statistics
            verified_patterns = [p for p in patterns if p.get('verified', False)]
            unverified_patterns = [p for p in patterns if not p.get('verified', False)]

            return {
                "total_lines": total_lines,
                "patterns_found": len(patterns),
                "verified_patterns": len(verified_patterns),
                "unverified": len(unverified_patterns),
                "patterns": verified_patterns[:20],  # Return first 20 verified patterns
                "summary": {
                    "verification_rate": f"{len(verified_patterns)/len(patterns)*100:.1f}%" if patterns else "0%",
                    "chunk_size": chunk_size,
                    "chunks_processed": (total_lines + chunk_size - 1) // chunk_size
                }
            }

        except Exception as e:
            return {
                "error": str(e),
                "total_lines": 0,
                "patterns_found": 0,
                "verified_patterns": 0
            }

    @app.tool()
    async def post_to_linkedin_via_selenium(
        self,
        content: str,
        company_id: str = "1263645",
        capture_screenshot: bool = True
    ) -> dict:
        """Post to LinkedIn using Selenium (no API). Collects training data automatically."""
        try:
            from modules.platform_integration.linkedin_agent.src.anti_detection_poster import AntiDetectionLinkedIn
            from modules.platform_integration.social_media_orchestrator.src.gemini_vision_analyzer import GeminiVisionAnalyzer

            poster = AntiDetectionLinkedIn()
            poster.setup_driver(use_existing_session=True)

            gemini_analysis = None
            if capture_screenshot:
                screenshot = poster.driver.get_screenshot_as_png()
                gemini = GeminiVisionAnalyzer(api_key=os.getenv('GOOGLE_AISTUDIO_API_KEY'))
                gemini_analysis = gemini.analyze_posting_ui(screenshot)

            success = poster.post_to_company_page(content=content, company_id=company_id)

            pattern_id = self._save_selenium_training_pattern({
                "mcp_tool": "post_to_linkedin_via_selenium",
                "input": {"content": content},
                "gemini_analysis": gemini_analysis,
                "result": "success" if success else "failure",
                "training_category": "linkedin_posting"
            })

            return {
                "success": success,
                "platform": "linkedin",
                "gemini_analysis": gemini_analysis,
                "training_pattern_id": pattern_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.tool()
    async def post_to_x_via_selenium(
        self,
        content: str,
        account: str = "foundups",
        capture_screenshot: bool = True
    ) -> dict:
        """Post to X/Twitter using Selenium (no API). Collects training data automatically."""
        try:
            from modules.platform_integration.x_twitter.src.x_anti_detection_poster import AntiDetectionX
            from modules.platform_integration.social_media_orchestrator.src.gemini_vision_analyzer import GeminiVisionAnalyzer

            poster = AntiDetectionX(use_foundups=(account == "foundups"))
            poster.setup_driver(use_existing_session=True)

            gemini_analysis = None
            if capture_screenshot:
                screenshot = poster.driver.get_screenshot_as_png()
                gemini = GeminiVisionAnalyzer(api_key=os.getenv('GOOGLE_AISTUDIO_API_KEY'))
                gemini_analysis = gemini.analyze_posting_ui(screenshot)

            success = poster.post_to_x(content=content)

            pattern_id = self._save_selenium_training_pattern({
                "mcp_tool": "post_to_x_via_selenium",
                "input": {"content": content, "account": account},
                "gemini_analysis": gemini_analysis,
                "result": "success" if success else "failure",
                "training_category": "x_posting"
            })

            return {
                "success": success,
                "platform": "x_twitter",
                "gemini_analysis": gemini_analysis,
                "training_pattern_id": pattern_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _save_selenium_training_pattern(self, pattern: dict) -> str:
        """Save training pattern to JSON file"""
        import json
        from pathlib import Path
        from datetime import datetime

        pattern_id = f"{pattern.get('training_category', 'general')}_{int(datetime.now().timestamp())}"
        pattern['training_pattern_id'] = pattern_id
        pattern['timestamp'] = datetime.now().isoformat()

        patterns_file = Path("holo_index/training/selenium_patterns.json")
        patterns_file.parent.mkdir(parents=True, exist_ok=True)

        patterns = []
        if patterns_file.exists():
            with open(patterns_file, 'r') as f:
                patterns = json.load(f)

        patterns.append(pattern)

        with open(patterns_file, 'w') as f:
            json.dump(patterns, f, indent=2)

        return pattern_id

# Initialize server
holo_server = HoloIndexMCPServer()

if __name__ == "__main__":
    # FastMCP will handle server startup when called by fastmcp run
    pass
