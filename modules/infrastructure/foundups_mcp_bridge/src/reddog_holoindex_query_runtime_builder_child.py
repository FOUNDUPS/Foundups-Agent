"""One-shot held-executable child for inert RedDog builder-process evidence."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
import math
from pathlib import Path
import subprocess
import sys
from typing import Callable

from holo_index.repository_state import repository_root_digest
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_root_path,
)

from .reddog_bounded_child_process import (
    BoundedChildResult,
    bounded_child_runner,
)
from .reddog_holoindex_process_image import (
    ProcessExecutableCapability,
    ProcessExecutableProof,
    hold_process_executable_for_launch,
    prove_process_executable_path,
)
from .reddog_holoindex_query_runtime_builder_child_contract import (
    BuilderProcessChildEvidence,
    _build_builder_process_child_evidence,
    child_process_output_bytes,
    parse_child_process_output,
)
from .reddog_holoindex_query_runtime_builder_process import (
    prove_builder_process_authority,
)
from .reddog_holoindex_query_runtime_builder_runtime_composition_contract import (
    BuilderRuntimeCompositionBinding,
    build_builder_runtime_composition_binding,
)
from .reddog_holoindex_runtime_composition_contract import (
    ISOLATION_FLAGS,
    RuntimeCompositionBinding,
)
from .reddog_holoindex_runtime_composition_descriptor import (
    verify_runtime_composition_generation,
)


_CHILD_FLAGS = (*ISOLATION_FLAGS, "-E", "-s", "-c")
_MAX_TIMEOUT_SECONDS = 120.0
_CHILD_BOOTSTRAP = (
    "import sys;"
    "b,d,r=sys.argv[1:4];"
    "z='python'+str(sys.version_info.major)+str(sys.version_info.minor)+'.zip';"
    "sys.path[:]=[b+'\\\\'+z,b+'\\\\DLLs',b+'\\\\Lib',b,d,r];"
    "from modules.infrastructure.foundups_mcp_bridge.src."
    "reddog_holoindex_query_runtime_builder_child import "
    "emit_builder_process_child_output;"
    "emit_builder_process_child_output(sys.argv[4:])"
)


class QueryRuntimeBuilderChildError(RuntimeError):
    """Stable fail-closed held-child execution error."""


def _fail(code: str) -> None:
    raise QueryRuntimeBuilderChildError(code)


@dataclass(frozen=True)
class BuilderProcessChildDependencies:
    composition_verifier: Callable[..., RuntimeCompositionBinding]
    executable_prover: Callable[[Path], ProcessExecutableProof]
    executable_holder: Callable[
        [ProcessExecutableProof], AbstractContextManager[ProcessExecutableCapability]
    ]
    child_runner: Callable[..., BoundedChildResult]


_SEALED_DEPENDENCIES = BuilderProcessChildDependencies(
    verify_runtime_composition_generation,
    prove_process_executable_path,
    hold_process_executable_for_launch,
    bounded_child_runner,
)


def _approved_directory(value: Path | str, repo_root: Path) -> Path:
    try:
        path = validate_runtime_root_path(value, repo_root=repo_root)
        if (
            not path.is_dir()
            or path.drive.rstrip(":").upper() not in {"O", "E"}
        ):
            _fail("QUERY_BUILDER_CHILD_RUNTIME_PATH_INVALID")
        return path
    except QueryRuntimeBuilderChildError:
        raise
    except (OSError, TypeError, ValueError):
        _fail("QUERY_BUILDER_CHILD_RUNTIME_PATH_INVALID")


def _timeout(value: object) -> float:
    if (
        type(value) not in {int, float}
        or not math.isfinite(float(value))
        or not 0 < float(value) <= _MAX_TIMEOUT_SECONDS
    ):
        _fail("QUERY_BUILDER_CHILD_TIMEOUT_INVALID")
    return float(value)


def _paths_overlap(left: Path, right: Path) -> bool:
    try:
        left.relative_to(right)
        return True
    except ValueError:
        try:
            right.relative_to(left)
            return True
        except ValueError:
            return False


def _validate_temp_root(
    temporary: Path,
    *,
    runtime: RuntimeCompositionBinding,
    canonical_store: Path,
    repo_root: Path,
) -> None:
    protected = (
        repo_root,
        canonical_store,
        runtime.generation_root.parent,
        runtime.generation_root,
        runtime.base_runtime.generation_root.parent,
        runtime.base_runtime.generation_root,
        runtime.dependency_runtime.generation_root.parent,
        runtime.dependency_runtime.generation_root,
    )
    if any(_paths_overlap(temporary, root) for root in protected):
        _fail("QUERY_BUILDER_CHILD_RUNTIME_PATH_INVALID")


def _runtime_truth(binding: object) -> RuntimeCompositionBinding:
    if type(binding) is not BuilderRuntimeCompositionBinding:
        _fail("QUERY_BUILDER_CHILD_RUNTIME_INVALID")
    try:
        rebuilt = build_builder_runtime_composition_binding(
            builder_dependency=binding.builder_dependency,
            runtime_composition=binding.runtime_composition,
        )
    except Exception:
        _fail("QUERY_BUILDER_CHILD_RUNTIME_INVALID")
    if rebuilt != binding:
        _fail("QUERY_BUILDER_CHILD_RUNTIME_INVALID")
    return binding.runtime_composition


def _verification_kwargs(
    runtime: RuntimeCompositionBinding, canonical_store: Path, repo_root: Path,
) -> dict[str, object]:
    return {
        "composition_store_root": runtime.generation_root.parent,
        "generation_root": runtime.generation_root,
        "base_runtime_store_root": runtime.base_runtime.generation_root.parent,
        "base_generation_root": runtime.base_runtime.generation_root,
        "dependency_runtime_store_root": (
            runtime.dependency_runtime.generation_root.parent
        ),
        "dependency_generation_root": runtime.dependency_runtime.generation_root,
        "canonical_store": canonical_store,
        "repo_roots": (repo_root,),
        "expected_generation_id": runtime.generation_id,
    }


def _child_arguments(
    runtime: RuntimeCompositionBinding,
    verification: dict[str, object],
    repo_root: Path,
) -> tuple[str, ...]:
    return (
        str(runtime.base_runtime.base_prefix_root),
        str(runtime.dependency_runtime.site_packages_root),
        str(repo_root),
        str(verification["composition_store_root"]),
        str(verification["generation_root"]),
        str(verification["base_runtime_store_root"]),
        str(verification["base_generation_root"]),
        str(verification["dependency_runtime_store_root"]),
        str(verification["dependency_generation_root"]),
        str(verification["canonical_store"]),
        str(repo_root),
    )


def _run_child(
    *, capability: ProcessExecutableCapability,
    runtime: RuntimeCompositionBinding, verification: dict[str, object],
    repo_root: Path, temp_root: Path, timeout: float,
    runner: Callable[..., BoundedChildResult],
) -> BoundedChildResult:
    command = (
        str(capability.launch_path), *_CHILD_FLAGS, _CHILD_BOOTSTRAP,
        *_child_arguments(runtime, verification, repo_root),
    )
    kwargs: dict[str, object] = {
        "cwd": str(repo_root),
        "env": {"TEMP": str(temp_root), "TMP": str(temp_root)},
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.DEVNULL,
        "shell": False,
        "timeout": timeout,
        "check": False,
        "close_fds": True,
    }
    if capability.pass_fds:
        kwargs["pass_fds"] = capability.pass_fds
    return runner(command, **kwargs)


def _validated_child_process(
    result: object, runtime: RuntimeCompositionBinding, repo_root: Path,
) -> dict[str, object]:
    if (
        type(result) is not BoundedChildResult
        or type(result.returncode) is not int
        or result.returncode != 0
        or result.output_oversized is not False
        or result.output_read_failed is not False
    ):
        _fail("QUERY_BUILDER_CHILD_EXECUTION_FAILED")
    try:
        process = parse_child_process_output(result.stdout)["process_authority"]
    except Exception:
        _fail("QUERY_BUILDER_CHILD_OUTPUT_INVALID")
    if (
        process["runtime_composition_generation_id"] != runtime.generation_id
        or process["runtime_composition_descriptor_digest"]
        != runtime.descriptor_digest
        or process["dependency_runtime_inventory_digest"]
        != runtime.dependency_runtime.inventory_digest
        or process["builder_source_root_digest"]
        != repository_root_digest(repo_root)
        or process["process_image_content_digest"]
        != runtime.interpreter_content_digest
        or process["process_image_size"] != runtime.interpreter_size
    ):
        _fail("QUERY_BUILDER_CHILD_PROCESS_IDENTITY_MISMATCH")
    return process


def _run_builder_process_once_for_test(
    *, builder_runtime: BuilderRuntimeCompositionBinding,
    repo_root: Path | str, canonical_store: Path | str,
    temp_root: Path | str, timeout_seconds: float,
    dependencies: BuilderProcessChildDependencies,
) -> BuilderProcessChildEvidence:
    runtime = _runtime_truth(builder_runtime)
    repo = Path(repo_root).resolve(strict=True)
    canonical = _approved_directory(canonical_store, repo)
    temporary = _approved_directory(temp_root, repo)
    _validate_temp_root(
        temporary,
        runtime=runtime,
        canonical_store=canonical,
        repo_root=repo,
    )
    timeout = _timeout(timeout_seconds)
    verification = _verification_kwargs(runtime, canonical, repo)
    before = dependencies.composition_verifier(**verification)
    if before != runtime:
        _fail("QUERY_BUILDER_CHILD_RUNTIME_INVALID")
    proof = dependencies.executable_prover(runtime.interpreter_path)
    try:
        with dependencies.executable_holder(proof) as capability:
            result = _run_child(
                capability=capability, runtime=runtime,
                verification=verification, repo_root=repo,
                temp_root=temporary, timeout=timeout,
                runner=dependencies.child_runner,
            )
    except subprocess.TimeoutExpired:
        _fail("QUERY_BUILDER_CHILD_TIMEOUT")
    except QueryRuntimeBuilderChildError:
        raise
    except Exception:
        _fail("QUERY_BUILDER_CHILD_EXECUTION_FAILED")
    process = _validated_child_process(result, runtime, repo)
    after = dependencies.composition_verifier(**verification)
    if after != before:
        _fail("QUERY_BUILDER_CHILD_COMPOSITION_MUTATED")
    return _build_builder_process_child_evidence(process)


def run_builder_process_once(
    *, builder_runtime: BuilderRuntimeCompositionBinding,
    repo_root: Path | str, canonical_store: Path | str,
    temp_root: Path | str, timeout_seconds: float = 120.0,
) -> BuilderProcessChildEvidence:
    """Launch one held interpreter and return observation evidence, not authority."""

    try:
        return _run_builder_process_once_for_test(
            builder_runtime=builder_runtime, repo_root=repo_root,
            canonical_store=canonical_store, temp_root=temp_root,
            timeout_seconds=timeout_seconds, dependencies=_SEALED_DEPENDENCIES,
        )
    except QueryRuntimeBuilderChildError:
        raise
    except Exception:
        _fail("QUERY_BUILDER_CHILD_UNAVAILABLE")


def emit_builder_process_child_output(argv: object) -> None:
    """Child-only entry: prove the live process and emit one canonical line."""

    if type(argv) is not list or len(argv) != 8 or any(
        type(value) is not str or not value for value in argv
    ):
        _fail("QUERY_BUILDER_CHILD_ARGUMENT_INVALID")
    paths = tuple(Path(value) for value in argv)
    verification = {
        "composition_store_root": paths[0],
        "generation_root": paths[1],
        "base_runtime_store_root": paths[2],
        "base_generation_root": paths[3],
        "dependency_runtime_store_root": paths[4],
        "dependency_generation_root": paths[5],
        "canonical_store": paths[6],
        "repo_roots": (paths[7],),
        "expected_generation_id": f"sha256:{paths[1].name}",
    }
    authority = prove_builder_process_authority(
        composition_verification_kwargs=verification,
        repo_root=paths[7],
    )
    sys.stdout.buffer.write(child_process_output_bytes(authority.public_binding))
    sys.stdout.buffer.flush()


__all__ = [
    "BuilderProcessChildDependencies", "QueryRuntimeBuilderChildError",
    "run_builder_process_once",
]
