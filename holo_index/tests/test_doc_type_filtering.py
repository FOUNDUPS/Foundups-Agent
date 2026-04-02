#!/usr/bin/env python3
"""
Test doc-type filtering in HoloIndex search.
"""

import sys
import os
from unittest.mock import patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from holo_index.core.holo_index import HoloIndex
except ImportError:
    pytest.skip("HoloIndex dependencies unavailable", allow_module_level=True)


def _make_holo_stub():
    holo = HoloIndex.__new__(HoloIndex)
    holo._log_agent_action = lambda *args, **kwargs: None
    holo._enhance_code_results_with_previews = lambda results: results
    holo.search_cache = None
    holo.model = None
    holo.project_root = None
    holo.code_collection = object()
    holo.wsp_collection = object()
    holo.test_collection = object()
    holo.symbol_collection = None
    holo.skill_collection = None
    return holo


def test_wsp_doc_type_filter_calls_wsp_search():
    calls = []

    holo = _make_holo_stub()

    def stub_search(holo_inst, collection, query, limit, kind, doc_type_filter="all"):
        calls.append((kind, doc_type_filter))
        return []

    with patch("holo_index.core.search_engine._search_collection", stub_search):
        holo.search("wsp 60 memory", limit=3, doc_type_filter="wsp_protocol")

    assert ("wsp", "wsp_protocol") in calls
    assert not any(call[0] == "code" for call in calls)


def test_code_doc_type_filter_skips_wsp_search():
    calls = []

    holo = _make_holo_stub()

    def stub_search(holo_inst, collection, query, limit, kind, doc_type_filter="all"):
        calls.append((kind, doc_type_filter))
        return []

    with patch("holo_index.core.search_engine._search_collection", stub_search):
        holo.search("find module", limit=3, doc_type_filter="code")

    assert ("code", "all") in calls
    assert not any(call[0] == "wsp" for call in calls)
