#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Pattern Memory - ChromaDB Integration
Verifies pattern storage, retrieval, and checkpoint management
WSP Compliance: WSP 93 (CodeIndex), WSP 46 (WRE Pattern)

Note: UTF-8 enforcement removed from module level to fix pytest capture teardown error.
The sys.stdout/stderr wrapping at import time conflicts with pytest's capture mechanism.
"""

import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from holo_index.qwen_advisor.pattern_memory import PatternMemory
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_pattern_storage():
    """Test storing patterns in ChromaDB"""
    print("\n" + "="*80)
    print("TEST 1: Pattern Storage")
    print("="*80)

    memory = PatternMemory()

    # Test pattern 1: Module location decision
    pattern1 = {
        "id": "test_module_001",
        "context": "User asked: 'Which module handles YouTube authentication?' System searched codebase and found youtube_auth module at modules/platform_integration/youtube_auth/",
        "decision": {
            "action": "recommend_module",
            "module": "modules/platform_integration/youtube_auth/",
            "reasoning": "Handles OAuth, token management, and session persistence"
        },
        "outcome": {
            "success": True,
            "user_satisfied": True,
            "follow_up_questions": 0
        },
        "module": "modules/platform_integration/youtube_auth/src/youtube_auth.py",
        "actual_code": "class YouTubeAuth:\n    def __init__(self):\n        self.oauth_client = build_oauth_flow()",
        "timestamp": datetime.now().isoformat(),
        "verified": True,
        "source": "test_suite"
    }

    # Test pattern 2: Priority scoring decision
    pattern2 = {
        "id": "test_priority_001",
        "context": "Priority scoring: Move2Japan scored 1.00 (perfect match), UnDaoDu scored 5.38 (poor match). System chose Move2Japan based on lower score = better embedding match.",
        "decision": {
            "action": "prioritize_channel",
            "channel": "Move2Japan",
            "score": 1.00,
            "reasoning": "Lower embedding distance indicates better semantic match"
        },
        "outcome": {
            "success": True,
            "stream_connected": True,
            "latency_ms": 245
        },
        "module": "modules/communication/livechat/src/qwen_youtube_integration.py",
        "actual_code": "prioritized.sort(key=lambda x: x[2])  # Lower score = better match",
        "timestamp": datetime.now().isoformat(),
        "verified": True,
        "source": "012.txt"
    }

    # Test pattern 3: WSP violation detection
    pattern3 = {
        "id": "test_wsp_001",
        "context": "Test file created in root directory: test_execution_tracer.py. WSP 49 violation detected - test files must be in module/tests/ subdirectory.",
        "decision": {
            "action": "report_violation",
            "wsp_violated": "WSP 49",
            "file": "test_execution_tracer.py",
            "reasoning": "Test files in root violate module structure standardization"
        },
        "outcome": {
            "success": True,
            "file_moved": True,
            "new_location": "holo_index/tests/test_execution_tracer.py"
        },
        "module": "WSP_framework/src/WSP_49_Module_Directory_Structure_Standardization_Protocol.md",
        "timestamp": datetime.now().isoformat(),
        "verified": True,
        "source": "compliance_check"
    }

    # Store patterns
    patterns = [pattern1, pattern2, pattern3]
    stored_count = 0

    for pattern in patterns:
        if memory.store_pattern(pattern):
            stored_count += 1
            print(f"[OK] Stored pattern: {pattern['id']}")
        else:
            print(f"[FAIL] Failed to store: {pattern['id']}")

    print(f"\n[RESULT] Stored {stored_count}/{len(patterns)} patterns")

    return stored_count == len(patterns)


def test_pattern_recall():
    """Test retrieving similar patterns"""
    print("\n" + "="*80)
    print("TEST 2: Pattern Recall")
    print("="*80)

    memory = PatternMemory()

    # Test queries
    queries = [
        "Which module handles YouTube authentication?",
        "How does priority scoring work for channels?",
        "Where should test files be placed?",
        "What is the correct module structure?"
    ]

    all_success = True

    for query in queries:
        print(f"\n[QUERY] {query}")

        patterns = memory.recall_similar(query, n=3, min_similarity=0.3)

        if patterns:
            print(f"[FOUND] {len(patterns)} similar patterns")
            for i, pattern in enumerate(patterns, 1):
                print(f"\n  Pattern {i}:")
                print(f"    ID: {pattern['id']}")
                print(f"    Similarity: {pattern['similarity']:.2f}")
                print(f"    Context: {pattern['context'][:100]}...")
                print(f"    Module: {pattern['metadata'].get('module', 'unknown')}")
        else:
            print(f"[NOT FOUND] No patterns above similarity threshold")
            all_success = False

    return all_success


def test_checkpoint_management():
    """Test checkpoint save/load for resumable processing"""
    print("\n" + "="*80)
    print("TEST 3: Checkpoint Management")
    print("="*80)

    memory = PatternMemory()

    # Initial checkpoint should be 0
    initial = memory.get_checkpoint()
    print(f"Initial checkpoint: {initial}")

    # Save checkpoint
    test_line = 5000
    memory.save_checkpoint(test_line)
    print(f"Saved checkpoint: {test_line}")

    # Verify retrieval
    retrieved = memory.get_checkpoint()
    print(f"Retrieved checkpoint: {retrieved}")

    success = (retrieved == test_line)

    if success:
        print(f"[OK] Checkpoint management working correctly")
    else:
        print(f"[FAIL] Checkpoint mismatch: expected {test_line}, got {retrieved}")

    return success


def test_stats_reporting():
    """Test statistics reporting"""
    print("\n" + "="*80)
    print("TEST 4: Statistics Reporting")
    print("="*80)

    memory = PatternMemory()

    stats = memory.get_stats()

    print(f"\n[STATS]")
    print(f"  Total Patterns: {stats['total_patterns']}")
    print(f"  Checkpoint Line: {stats['checkpoint_line']}")
    print(f"  Verification Rate: {stats['verification_rate']:.1%}")
    print(f"  Verified Count: {stats.get('verified_count', 0)}")
    print(f"  Sources: {stats['sources']}")

    # Verify stats are reasonable
    success = (
        stats['total_patterns'] >= 0 and
        stats['checkpoint_line'] >= 0 and
        0.0 <= stats['verification_rate'] <= 1.0
    )

    if success:
        print(f"\n[OK] Statistics reporting working correctly")
    else:
        print(f"\n[FAIL] Statistics contain invalid values")

    return success


def test_prompt_formatting():
    """Test formatting patterns for LLM prompts"""
    print("\n" + "="*80)
    print("TEST 5: Prompt Formatting")
    print("="*80)

    memory = PatternMemory()

    # Recall patterns
    query = "module structure"
    patterns = memory.recall_similar(query, n=3)

    if not patterns:
        print(f"[U+26A0]️  No patterns found - skipping prompt formatting test")
        return True

    # Format for prompt
    formatted = memory.format_for_prompt(patterns, max_patterns=2)

    print(f"\n[FORMATTED PROMPT]")
    print(formatted)

    # Check formatting contains key elements
    success = (
        "Based on past operational decisions" in formatted and
        "Pattern" in formatted and
        "Context:" in formatted
    )

    if success:
        print(f"\n[OK] Prompt formatting working correctly")
    else:
        print(f"\n[FAIL] Prompt formatting incomplete")

    return success


def run_all_tests():
    """Run all pattern memory tests"""
    print("\n" + "="*80)
    print("PATTERN MEMORY TEST SUITE")
    print("="*80)

    tests = [
        ("Pattern Storage", test_pattern_storage),
        ("Pattern Recall", test_pattern_recall),
        ("Checkpoint Management", test_checkpoint_management),
        ("Statistics Reporting", test_stats_reporting),
        ("Prompt Formatting", test_prompt_formatting)
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"[TEST FAILED] {test_name}: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status} - {test_name}")

    print(f"\n[OVERALL] {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print(f"\n[CELEBRATE] ALL TESTS PASSED - Pattern memory ready for production")
    else:
        print(f"\n[U+26A0]️  SOME TESTS FAILED - Review errors above")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
