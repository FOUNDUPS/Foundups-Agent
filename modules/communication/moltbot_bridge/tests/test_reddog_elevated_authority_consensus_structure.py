"""Static boundaries for elevated RedDog consensus modules."""

from __future__ import annotations

import ast
from pathlib import Path


MODULES = tuple(
    sorted(
        list((Path(__file__).parents[1] / "src").glob(
            "reddog_elevated_authority_consensus_*.py"
        ))
        + list((Path(__file__).parents[1] / "src").glob(
            "reddog_elevated_consensus_*.py"
        ))
        + list((Path(__file__).parents[1] / "src").glob(
            "reddog_delegated_authority_signing_*.py"
        ))
        + list((Path(__file__).parents[1] / "src").glob(
            "reddog_ed25519_elevated_consensus_*.py"
        ))
    )
)
TEST_MODULES = tuple(
    sorted(Path(__file__).parent.glob("reddog_elevated_consensus_*.py"))
    + sorted(
        Path(__file__).parent.glob(
            "test_reddog_elevated_authority_consensus_*.py"
        )
    )
    + sorted(
        Path(__file__).parent.glob("test_reddog_elevated_consensus_*.py")
    )
)
LEGACY_RUNTIME_HOST_LIMITS = {
    "reddog_resident_queue_stage_handler_registry.py": (
        699, "build_reddog_resident_queue_stage_handler_registry", 409
    ),
    "reddog_main_resident_queue_runtime_dependency_bundle.py": (
        530, "load_reddog_main_resident_queue_runtime_dependency_bundle", 143
    ),
    "reddog_main_resident_queue_serial_loop_bootstrap.py": (
        1730, "run_reddog_main_resident_queue_serial_loop_bootstrap", 467
    ),
    "reddog_signer_delegated_authority_runtime.py": (
        716, "issue_delegated_authority_runtime", 285
    ),
}


def test_modules_have_no_shell_network_or_key_generation_imports() -> None:
    banned = {"subprocess", "socket", "requests", "urllib", "cryptography"}
    for path in MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        assert imports.isdisjoint(banned)


def test_consensus_modules_remain_bounded_lego_components() -> None:
    assert len(MODULES) == 13
    for path in MODULES:
        source = path.read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 200, path.name
        tree = ast.parse(source)
        functions = (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        for function in functions:
            assert function.end_lineno - function.lineno + 1 <= 50, (
                path.name,
                function.name,
            )


def test_consensus_test_modules_are_bounded_lego_components() -> None:
    assert len(TEST_MODULES) == 15
    for path in TEST_MODULES:
        source = path.read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 200, path.name
        tree = ast.parse(source)
        for function in (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ):
            assert function.end_lineno - function.lineno + 1 <= 50, (
                path.name,
                function.name,
            )


def test_test_only_downstream_consensus_never_enters_production_sources() -> None:
    needle = "reddog_elevated_consensus_downstream_test_support"
    source_root = Path(__file__).parents[1] / "src"
    offenders = [
        path.name
        for path in source_root.glob("*.py")
        if needle in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_production_runtime_does_not_compose_unsigned_elevated_sources() -> None:
    source_root = Path(__file__).parents[1] / "src"
    composition_hosts = (
        "reddog_signer_socket_service_runtime_wiring.py",
        "reddog_signer_socket_service_runtime_bootstrap.py",
        "reddog_signer_socket_system_service_entrypoint.py",
        "reddog_main_resident_queue_runtime_dependency_bundle.py",
    )
    forbidden = (
        "ElevatedConsensusExternalSignerClient(",
        "ElevatedConsensusSignerAuthority(",
    )
    for name in composition_hosts:
        path = source_root / name
        if path.exists():
            source = path.read_text(encoding="utf-8")
            assert all(item not in source for item in forbidden)


def test_modified_runtime_host_functions_do_not_add_wsp62_debt() -> None:
    source_root = Path(__file__).parents[1] / "src"
    expected = {
        "reddog_ed25519_signer_backend.py": "sign",
        "reddog_resident_queue_authority_runtime_handler.py": "__call__",
        "reddog_wre_queue_authority_runtime_invoke.py": (
            "invoke_reddog_wre_queue_authority_runtime"
        ),
    }
    for name, function_name in expected.items():
        tree = ast.parse((source_root / name).read_text(encoding="utf-8"))
        function = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        )
        assert function.end_lineno - function.lineno + 1 <= 60, name


def test_touched_legacy_runtime_hosts_do_not_exceed_base_debt() -> None:
    source_root = Path(__file__).parents[1] / "src"
    for name, (file_limit, function_name, function_limit) in (
        LEGACY_RUNTIME_HOST_LIMITS.items()
    ):
        source = (source_root / name).read_text(encoding="utf-8")
        assert len(source.splitlines()) <= file_limit, name
        tree = ast.parse(source)
        function = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        )
        assert function.end_lineno - function.lineno + 1 <= function_limit, name
