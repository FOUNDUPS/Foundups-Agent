"""Declared native-name graph and CPython-link evidence for runtime ABI audit."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
)
from .reddog_holoindex_runtime_abi_contract import (
    BASE_ROLE,
    RuntimeAbiContractError,
    RuntimeAbiLimits,
)
from .reddog_holoindex_windows_pe import PEImage, PEImport


def _fail(code: str) -> None:
    raise RuntimeAbiContractError(code)


@dataclass(frozen=True)
class NativeNode:
    role: str
    path: str
    inventory_row: Mapping[str, Any]
    image: PEImage
    distribution: str
    wheel_tag: str

    @property
    def key(self) -> str:
        return f"{self.role}:{self.path}"

    @property
    def basename(self) -> str:
        return PurePosixPath(self.path).name.casefold()


def derive_declared_abi_rows(
    nodes: list[NativeNode], limits: RuntimeAbiLimits,
) -> list[Mapping[str, Any]]:
    """Verify the abstract name graph and return canonical per-image evidence."""

    graph, internal, external = _declared_graph(nodes, limits)
    targets = _python_targets(nodes)
    _verify_python_abi(nodes, graph, targets)
    return [
        _native_evidence_row(
            node, graph, internal[node.key], external[node.key], targets
        )
        for node in nodes
    ]


def _declared_graph(
    nodes: list[NativeNode], limits: RuntimeAbiLimits,
) -> tuple[dict[str, tuple[str, ...]], dict[str, list[str]], dict[str, list[str]]]:
    by_basename: dict[str, list[NativeNode]] = {}
    for node in nodes:
        by_basename.setdefault(node.basename, []).append(node)
    graph: dict[str, tuple[str, ...]] = {}
    internal: dict[str, list[str]] = {}
    external: dict[str, list[str]] = {}
    for node in nodes:
        edges, inside, outside = _node_edges(node, by_basename)
        graph[node.key] = tuple(sorted(edges))
        internal[node.key] = sorted(inside)
        external[node.key] = sorted(outside)
    if sum(len(edges) for edges in graph.values()) > limits.max_total_graph_edges:
        _fail("RUNTIME_ABI_GRAPH_EDGE_LIMIT_EXCEEDED")
    return graph, internal, external


def _node_edges(
    node: NativeNode, by_basename: Mapping[str, list[NativeNode]],
) -> tuple[set[str], set[str], set[str]]:
    edges: set[str] = set()
    inside: set[str] = set()
    outside: set[str] = set()
    for library in {row.library for row in node.image.imports}:
        candidate = _declared_target(node, by_basename.get(library, []))
        if candidate is None:
            outside.add(library)
        else:
            inside.add(library)
            edges.add(candidate.key)
    return edges, inside, outside


def _declared_target(
    importer: NativeNode, candidates: list[NativeNode],
) -> NativeNode | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    parent = PurePosixPath(importer.path).parent
    local = [
        node for node in candidates
        if node.role == importer.role and PurePosixPath(node.path).parent == parent
    ]
    return local[0] if len(local) == 1 else None


def _python_targets(nodes: list[NativeNode]) -> Mapping[str, NativeNode]:
    targets: dict[str, NativeNode] = {}
    for name in ("python3.dll", "python312.dll"):
        matches = [
            node for node in nodes
            if node.role == BASE_ROLE and node.path.casefold() == name
        ]
        if name == "python312.dll" and len(matches) != 1:
            _fail("RUNTIME_ABI_PYTHON_DLL_INVALID")
        if matches:
            targets[name] = matches[0]
    return targets


def _verify_python_abi(
    nodes: list[NativeNode], graph: Mapping[str, tuple[str, ...]],
    targets: Mapping[str, NativeNode],
) -> None:
    target_keys = {name: node.key for name, node in targets.items()}
    for node in nodes:
        _verify_direct_python_imports(node, graph, targets)
        _verify_extension(node, graph, target_keys)
    python_exe = next(
        (node for node in nodes if node.role == BASE_ROLE and node.path.casefold() == "python.exe"),
        None,
    )
    if python_exe is None or "python312.dll" not in _reachable_targets(
        python_exe.key, graph, target_keys
    ):
        _fail("RUNTIME_ABI_INTERPRETER_LINK_INVALID")


def _verify_direct_python_imports(
    node: NativeNode, graph: Mapping[str, tuple[str, ...]],
    targets: Mapping[str, NativeNode],
) -> None:
    for imported in node.image.imports:
        if not re.fullmatch(r"python(?:3|[0-9]{2,3})\.dll", imported.library):
            continue
        target = targets.get(imported.library)
        if target is None or target.key not in graph[node.key]:
            _fail("RUNTIME_ABI_PYTHON_DLL_MISMATCH")
        _require_exports(imported, target.image)


def _verify_extension(
    node: NativeNode, graph: Mapping[str, tuple[str, ...]],
    target_keys: Mapping[str, str],
) -> None:
    suffix = PurePosixPath(node.path).name.casefold()
    tagged = re.search(r"\.cp(\d+)-win_amd64\.pyd$", suffix)
    if tagged and tagged.group(1) != "312":
        _fail("RUNTIME_ABI_EXTENSION_TAG_INCOMPATIBLE")
    if not suffix.endswith(".pyd"):
        return
    init_name = _extension_init_name(node.path)
    if (
        init_name not in node.image.export_names
        or init_name in node.image.forwarded_export_names
    ):
        _fail("RUNTIME_ABI_EXTENSION_INIT_MISSING")
    reached = _reachable_targets(node.key, graph, target_keys)
    if not reached or (suffix.endswith(".abi3.pyd") and "python3.dll" not in reached):
        _fail("RUNTIME_ABI_EXTENSION_PYTHON_LINK_MISSING")


def _extension_init_name(path: str) -> str:
    stem = PurePosixPath(path).name.split(".", 1)[0]
    try:
        return "PyInit_" + stem.encode("ascii").decode("ascii")
    except UnicodeEncodeError:
        encoded = stem.encode("punycode").decode("ascii").replace("-", "_")
        return "PyInitU_" + encoded


def _require_exports(imported: PEImport, target: PEImage) -> None:
    available_names = set(target.export_names) - set(target.forwarded_export_names)
    available_ordinals = set(target.export_ordinals) - set(
        target.forwarded_export_ordinals
    )
    if not set(imported.names) <= available_names:
        _fail("RUNTIME_ABI_PYTHON_EXPORT_MISSING")
    if not set(imported.ordinals) <= available_ordinals:
        _fail("RUNTIME_ABI_PYTHON_EXPORT_ORDINAL_MISSING")


def _reachable_targets(
    start: str, graph: Mapping[str, tuple[str, ...]], targets: Mapping[str, str],
) -> set[str]:
    reverse = {key: name for name, key in targets.items()}
    seen: set[str] = set()
    pending = list(graph.get(start, ()))
    reached: set[str] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        if current in reverse:
            reached.add(reverse[current])
        pending.extend(graph.get(current, ()))
    return reached


def _native_evidence_row(
    node: NativeNode, graph: Mapping[str, tuple[str, ...]],
    internal: list[str], external: list[str], targets: Mapping[str, NativeNode],
) -> Mapping[str, Any]:
    normal = [_import_summary(row) for row in node.image.imports if not row.delayed]
    delayed = [_import_summary(row) for row in node.image.imports if row.delayed]
    target_keys = {name: value.key for name, value in targets.items()}
    reached = _reachable_targets(node.key, graph, target_keys)
    direct_python = sorted(library for library in internal if library in target_keys)
    return {
        "component_role": node.role, "path": node.path,
        "sha256": str(node.inventory_row["sha256"]),
        "size": int(node.inventory_row["size"]), "machine": node.image.machine,
        "optional_magic": node.image.optional_magic,
        "image_kind": "dll" if node.image.is_dll else "executable",
        "normal_imports": normal, "delay_imports": delayed,
        "internal_imports": internal, "external_imports": external,
        **_export_evidence(node.image),
        "direct_python_link_libraries": direct_python,
        "reachable_python_libraries": sorted(reached),
        "python_abi_reachable": bool(reached),
        "distribution": node.distribution,
        "compatible_wheel_tag": node.wheel_tag,
    }


def _export_evidence(image: PEImage) -> Mapping[str, Any]:
    return {
        "export_names_digest": digest_bytes(canonical_json_bytes(list(image.export_names))),
        "export_name_count": len(image.export_names),
        "export_ordinals_digest": digest_bytes(canonical_json_bytes(list(image.export_ordinals))),
        "export_ordinal_count": len(image.export_ordinals),
        "forwarded_export_names_digest": digest_bytes(
            canonical_json_bytes(list(image.forwarded_export_names))
        ),
        "forwarded_export_name_count": len(image.forwarded_export_names),
        "forwarded_export_ordinals_digest": digest_bytes(
            canonical_json_bytes(list(image.forwarded_export_ordinals))
        ),
        "forwarded_export_ordinal_count": len(image.forwarded_export_ordinals),
    }


def _import_summary(row: PEImport) -> Mapping[str, Any]:
    return {
        "library": row.library,
        "names_digest": digest_bytes(canonical_json_bytes(list(row.names))),
        "name_count": len(row.names),
        "ordinals_digest": digest_bytes(canonical_json_bytes(list(row.ordinals))),
        "ordinal_count": len(row.ordinals),
    }


__all__ = ["NativeNode", "derive_declared_abi_rows"]
