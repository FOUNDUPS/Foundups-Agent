"""Test-only repository-analysis caches and deterministic receipt support."""

from __future__ import annotations

import copy
import functools
from pathlib import Path
from typing import Callable, Iterable

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    dependency_tools,
    impact_scoring,
    test_mapping,
)


EXPECTED_REPOSITORY_ANALYSIS_CACHE_RECEIPT = {
    "mapping": {"keys": 7, "requests": 125, "scans": 7},
    "module": {"keys": 57, "requests": 2434, "scans": 57},
    "reverse": {"keys": 12, "requests": 303, "scans": 12},
}


class ImpactCallCache:
    """Reuse exact read-only impact signatures within one immutable repo view."""

    def __init__(self, bridge) -> None:
        self.bridge = bridge
        self.results = {}
        self.call_counts = {}

    def __call__(self, *, target_type: str, target: str):
        key = (target_type, target)
        if key not in self.results:
            self.results[key] = self.bridge.call_tool(
                "get_change_impact_score", target_type=target_type, target=target,
            )
            self.call_counts[key] = self.call_counts.get(key, 0) + 1
        return copy.deepcopy(self.results[key])

    def replay(self, key: tuple[str, str]):
        return self(target_type=key[0], target=key[1])


class ReverseDependencySnapshotCache:
    """Test-only snapshots for one immutable, resolved repository root."""

    def __init__(self, repo_root: Path, scan: Callable) -> None:
        self.repo_root = repo_root.resolve()
        self.scan = scan
        self.results = {}
        self.requests = {}
        self.scans = {}

    def __call__(self, repo_root, module_name, search_scope="modules"):
        resolved = Path(repo_root).resolve()
        if resolved != self.repo_root:
            return self.scan(repo_root, module_name, search_scope)
        key = (str(resolved), module_name, search_scope)
        self.requests[key] = self.requests.get(key, 0) + 1
        if key not in self.results:
            self.results[key] = self.scan(repo_root, module_name, search_scope)
            self.scans[key] = self.scans.get(key, 0) + 1
        return copy.deepcopy(self.results[key])

    def replay(self, key: tuple):
        return self(Path(key[0]), key[1], key[2])


class ModuleDependencySnapshotCache(ReverseDependencySnapshotCache):
    def __call__(
        self, repo_root, module_name, include_external=True, max_depth=1,
    ):
        resolved = Path(repo_root).resolve()
        if resolved != self.repo_root:
            return self.scan(repo_root, module_name, include_external, max_depth)
        key = (str(resolved), module_name, include_external, max_depth)
        self.requests[key] = self.requests.get(key, 0) + 1
        if key not in self.results:
            self.results[key] = self.scan(
                repo_root, module_name, include_external, max_depth,
            )
            self.scans[key] = self.scans.get(key, 0) + 1
        return copy.deepcopy(self.results[key])

    def replay(self, key: tuple):
        return self(Path(key[0]), key[1], key[2], key[3])


class TestMappingSnapshotCache(ReverseDependencySnapshotCache):
    __test__ = False

    def __call__(self, repo_root, modules):
        resolved = Path(repo_root).resolve()
        if resolved != self.repo_root:
            return self.scan(repo_root, modules)
        key = (str(resolved), *tuple(modules))
        self.requests[key] = self.requests.get(key, 0) + 1
        if key not in self.results:
            self.results[key] = self.scan(repo_root, modules)
            self.scans[key] = self.scans.get(key, 0) + 1
        return copy.deepcopy(self.results[key])

    def replay(self, key: tuple):
        return self(Path(key[0]), list(key[1:]))


def repository_analysis_cache_receipt(caches: Iterable) -> dict:
    """Return the bounded, order-independent scan receipt for three caches."""

    receipt = {}
    for name, cache in zip(("reverse", "module", "mapping"), caches):
        receipt[name] = {
            "keys": len(cache.results),
            "requests": sum(cache.requests.values()),
            "scans": sum(cache.scans.values()),
        }
    return receipt


def _exercise_requests(call: Callable[[int], dict], keys: int, requests: int) -> bool:
    """Populate an exact workload while proving every returned value is isolated."""

    base, remainder = divmod(requests, keys)
    isolated = True
    for index in range(keys):
        calls = base + (1 if index < remainder else 0)
        first = call(index)
        first["test_only_mutation"] = True
        second = call(index)
        isolated = isolated and "test_only_mutation" not in second
        for _ in range(calls - 2):
            isolated = isolated and "test_only_mutation" not in call(index)
    return isolated


def self_populated_repository_analysis_caches(repo_root: Path):
    """Build the frozen receipt from deterministic scans, independent of test order."""

    def reverse_scan(root, module_name, search_scope="modules"):
        return {"root": str(root), "module": module_name, "scope": search_scope}

    def module_scan(root, module_name, include_external=True, max_depth=1):
        return {
            "root": str(root), "module": module_name,
            "include_external": include_external, "max_depth": max_depth,
        }

    def mapping_scan(root, modules):
        return {"root": str(root), "modules": list(modules)}

    caches = (
        ReverseDependencySnapshotCache(repo_root, reverse_scan),
        ModuleDependencySnapshotCache(repo_root, module_scan),
        TestMappingSnapshotCache(repo_root, mapping_scan),
    )
    isolation = (
        _exercise_requests(
            lambda index: caches[0](repo_root, f"reverse_{index}"), 12, 303,
        )
        and _exercise_requests(
            lambda index: caches[1](repo_root, f"module_{index}"), 57, 2434,
        )
        and _exercise_requests(
            lambda index: caches[2](repo_root, [f"mapping_{index}"]), 7, 125,
        )
    )
    return caches, isolation


@pytest.fixture(scope="class")
def impact_call(bridge):
    """Bound duplicate full-repository scans without caching production state."""

    cache = ImpactCallCache(bridge)
    yield cache
    assert cache.call_counts
    assert set(cache.call_counts.values()) == {1}
    assert set(cache.call_counts) == set(cache.results)
    sample_key = next(iter(cache.results))
    first = cache.replay(sample_key)
    second = cache.replay(sample_key)
    first["test_only_mutation"] = True
    assert "test_only_mutation" not in second


def _repository_analysis_caches(repo_root: Path) -> tuple:
    """Bind the three immutable-root caches to their production scanners."""

    return (
        ReverseDependencySnapshotCache(
            repo_root, dependency_tools.get_reverse_dependencies,
        ),
        ModuleDependencySnapshotCache(
            repo_root, dependency_tools.get_module_dependencies,
        ),
        TestMappingSnapshotCache(repo_root, test_mapping.get_test_mapping),
    )


def _repository_analysis_wrappers(caches: tuple) -> tuple:
    """Build signature-preserving wrappers for the three cache instances."""

    reverse_cache, module_cache, mapping_cache = caches

    @functools.wraps(reverse_cache.scan)
    def cached_reverse_dependencies(
        repo_root, module_name, search_scope="modules",
    ):
        return reverse_cache(repo_root, module_name, search_scope)

    @functools.wraps(module_cache.scan)
    def cached_module_dependencies(
        repo_root, module_name, include_external=True, max_depth=1,
    ):
        return module_cache(repo_root, module_name, include_external, max_depth)

    @functools.wraps(mapping_cache.scan)
    def cached_test_mapping(repo_root, modules):
        return mapping_cache(repo_root, modules)

    return (
        cached_reverse_dependencies,
        cached_module_dependencies,
        cached_test_mapping,
    )


def _install_repository_analysis_patches(patcher, wrappers: tuple) -> None:
    """Install identical wrappers at every production consumer import site."""

    reverse, module, mapping = wrappers
    patcher.setattr(dependency_tools, "get_reverse_dependencies", reverse)
    patcher.setattr(impact_scoring, "get_reverse_dependencies", reverse)
    patcher.setattr(dependency_tools, "get_module_dependencies", module)
    patcher.setattr(impact_scoring, "get_module_dependencies", module)
    patcher.setattr(test_mapping, "get_test_mapping", mapping)
    patcher.setattr(impact_scoring, "get_test_mapping", mapping)


def _assert_repository_analysis_receipt(caches: tuple) -> None:
    """Prove one scan per used key, exact key sets, and replay isolation."""

    used = [cache for cache in caches if cache.scans]
    if not used:
        return
    assert all(set(cache.scans.values()) == {1} for cache in used)
    assert all(
        set(cache.scans) == set(cache.requests) == set(cache.results)
        for cache in used
    )
    for cache in used:
        sample_key = next(iter(cache.results))
        first = cache.replay(sample_key)
        second = cache.replay(sample_key)
        first["test_only_mutation"] = True
        assert "test_only_mutation" not in second
        assert cache.scans[sample_key] == 1


@pytest.fixture(scope="module", autouse=True)
def _bounded_repository_analysis_scans():
    """Reuse pure discovery snapshots; foreign/temp roots always scan directly."""

    caches = _repository_analysis_caches(Path(__file__).resolve().parents[4])
    patcher = pytest.MonkeyPatch()
    _install_repository_analysis_patches(
        patcher, _repository_analysis_wrappers(caches),
    )
    try:
        yield caches
        _assert_repository_analysis_receipt(caches)
    finally:
        patcher.undo()
