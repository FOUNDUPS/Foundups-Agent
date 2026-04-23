#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test 012.txt Pattern Mining via MCP
Verifies that HoloIndex MCP can extract and verify code patterns from conversations
WSP Compliance: WSP 93 (CodeIndex Surgical Intelligence)

Note: Requires foundups_mcp_p1 package. Tests are skipped if not available.
"""

import asyncio
import json
from pathlib import Path
import sys

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Try to import MCP server - skip tests if not available
try:
    from foundups_mcp_p1.servers.holo_index.server import HoloIndexMCPServer
    MCP_AVAILABLE = True
except ImportError:
    HoloIndexMCPServer = None  # type: ignore
    MCP_AVAILABLE = False

pytestmark = pytest.mark.skipif(not MCP_AVAILABLE, reason="foundups_mcp_p1 not installed")


async def test_pattern_mining():
    """Test mining 012.txt for code patterns"""
    print("=" * 80)
    print("TEST: Mining 012.txt for Code Patterns via HoloIndex MCP")
    print("=" * 80)

    # Initialize MCP server
    server = HoloIndexMCPServer()

    # Test with first 8000 lines only (faster test)
    result = await server.mine_012_conversations_for_patterns(
        txt_file="O:/Foundups-Agent/012.txt",
        chunk_size=8000,
        verify_code=True
    )

    # Print results
    print(f"\n[RESULTS]")
    print(f"Total Lines: {result.get('total_lines', 0)}")
    print(f"Patterns Found: {result.get('patterns_found', 0)}")
    print(f"Verified Patterns: {result.get('verified_patterns', 0)}")
    print(f"Unverified Patterns: {result.get('unverified', 0)}")

    if 'summary' in result:
        print(f"\n[SUMMARY]")
        print(f"Verification Rate: {result['summary'].get('verification_rate', '0%')}")
        print(f"Chunks Processed: {result['summary'].get('chunks_processed', 0)}")

    # Show sample verified patterns
    verified = result.get('patterns', [])
    if verified:
        print(f"\n[SAMPLE VERIFIED PATTERNS] (showing first 5)")
        for i, pattern in enumerate(verified[:5], 1):
            print(f"\nPattern #{i}:")
            print(f"  Line Range: {pattern.get('conversation_line_range', 'unknown')}")
            print(f"  Code Reference: {pattern.get('code_reference', 'none')}")
            print(f"  Code Found: {pattern.get('code_found', 'none')}")
            if pattern.get('holo_search_query'):
                print(f"  HoloIndex Query: {pattern['holo_search_query']}")
            if pattern.get('actual_code'):
                code_snippet = pattern['actual_code'][:100].replace('\n', ' ')
                print(f"  Code Snippet: {code_snippet}...")

    # Save results to JSON
    output_file = Path("O:/Foundups-Agent/holo_index/reports/012_pattern_mining_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n[SAVED] Results saved to: {output_file}")

    # Evaluate success
    verification_rate = float(result.get('summary', {}).get('verification_rate', '0%').rstrip('%'))

    print(f"\n[EVALUATION]")
    if verification_rate >= 70:
        print(f"[OK] EXCELLENT: {verification_rate}% verification rate")
    elif verification_rate >= 50:
        print(f"[OK] GOOD: {verification_rate}% verification rate")
    elif verification_rate >= 30:
        print(f"[U+26A0]️ FAIR: {verification_rate}% verification rate - some patterns unverified")
    else:
        print(f"[FAIL] POOR: {verification_rate}% verification rate - most patterns unverified")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    return result


async def test_specific_priority_inversion():
    """Test extraction of specific priority inversion issue"""
    print("\n" + "=" * 80)
    print("TEST: Extracting Priority Inversion Pattern (Move2Japan vs UnDaoDu)")
    print("=" * 80)

    server = HoloIndexMCPServer()

    # Search for priority scoring code
    results = await server.semantic_code_search(
        query="qwen priority scoring channel selection",
        limit=5
    )

    print(f"\n[SEARCH RESULTS]")
    print(f"Total Results: {results.get('total_results', 0)}")

    if results['code_results']:
        print(f"\n[TOP CODE MATCH]")
        top_result = results['code_results'][0]
        print(f"File: {top_result.get('path', 'unknown')}")
        print(f"Function: {top_result.get('function', 'unknown')}")
        print(f"Relevance: {top_result.get('relevance', 0.0):.3f}")
        print(f"Snippet:\n{top_result.get('snippet', 'none')}")

        # Verify this is the priority inversion bug location
        expected_file = "modules/communication/livechat/src/qwen_youtube_integration.py"
        if expected_file in top_result.get('path', ''):
            print(f"\n[OK] CORRECT FILE FOUND: {expected_file}")
            print("Priority inversion bug location successfully identified via HoloIndex!")
        else:
            print(f"\n[U+26A0]️ Different file found: {top_result.get('path', 'unknown')}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_pattern_mining())
    asyncio.run(test_specific_priority_inversion())
