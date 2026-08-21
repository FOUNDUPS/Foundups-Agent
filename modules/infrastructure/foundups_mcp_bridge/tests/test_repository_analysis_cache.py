"""Standalone receipt checks for the repository-analysis test caches."""

import json

from .repository_analysis_cache_support import (
    EXPECTED_REPOSITORY_ANALYSIS_CACHE_RECEIPT,
    repository_analysis_cache_receipt,
    self_populated_repository_analysis_caches,
)


def test_repository_analysis_cache_receipt(tmp_path):
    """Freeze exact scan cardinality without depending on another test module."""

    caches, _ = self_populated_repository_analysis_caches(tmp_path)
    receipt = repository_analysis_cache_receipt(caches)

    assert receipt == EXPECTED_REPOSITORY_ANALYSIS_CACHE_RECEIPT
    assert all(item["keys"] == item["scans"] for item in receipt.values())
    assert all(item["keys"] > 0 for item in receipt.values())
    assert sum(item["requests"] for item in receipt.values()) > sum(
        item["scans"] for item in receipt.values()
    )
    print("REDDOG_CACHE_RECEIPT=" + json.dumps(receipt, sort_keys=True))


def test_repository_analysis_cache_receipt_values_are_mutation_isolated(tmp_path):
    """Every repeated cache request receives a deep-copy snapshot."""

    _, isolation = self_populated_repository_analysis_caches(tmp_path)
    assert isolation is True
