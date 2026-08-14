"""Adversarial tests for canonical grant-authority service archives."""

from __future__ import annotations

import ast
import io
import json
import stat
import warnings
import zipfile
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_contract import (
    ARCHIVE_MAIN,
    ARCHIVE_MANIFEST,
    ARCHIVE_TIMESTAMP,
    build_grant_service_archive,
    canonical_archive_bytes,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_validation import (
    validate_grant_service_archive,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    canonical_json,
    digest,
    raw_digest,
)

SOURCE_SHA = "a" * 40
SERVICE = (
    b"import argparse\n"
    b"from helpers.runtime import status\n\n"
    b"def main(argv=None):\n"
    b"    parser = argparse.ArgumentParser()\n"
    b"    parser.parse_args(argv)\n"
    b"    return status()\n"
)
HELPER = b"def status():\n    return 2\n"


def test_valid_archive_is_canonical_and_dependency_closed() -> None:
    archive = _archive()
    manifest = validate_grant_service_archive(archive)

    assert manifest["entrypoint"] == "reddog_grant_authority_service:main"
    assert manifest["claimed_source_commit_sha"] == SOURCE_SHA
    assert manifest["file_count"] == 4


@pytest.mark.parametrize("raw", [b"", b"not-a-zip", b"PK\x03\x04attacker"])
def test_non_zip_archive_rejects(raw: bytes) -> None:
    with pytest.raises(RuntimeArtifactManifestError, match="archive_invalid"):
        validate_grant_service_archive(raw)


def test_missing_entrypoint_rejects() -> None:
    with pytest.raises(RuntimeArtifactManifestError, match="entrypoint_invalid"):
        build_grant_service_archive(
            {"reddog_grant_authority_service.py": SERVICE},
            source_commit_sha=SOURCE_SHA,
        )


def test_missing_transitive_dependency_rejects() -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": SERVICE,
        },
        source_commit_sha=SOURCE_SHA,
    )
    with pytest.raises(RuntimeArtifactManifestError, match="dependency_missing"):
        validate_grant_service_archive(archive)


def test_missing_package_initializer_rejects() -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": SERVICE,
            "helpers/runtime.py": HELPER,
        },
        source_commit_sha=SOURCE_SHA,
    )
    with pytest.raises(RuntimeArtifactManifestError, match="package_missing"):
        validate_grant_service_archive(archive)


def test_missing_relative_dependency_from_package_rejects() -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": (
                b"from helpers import status\n\ndef main():\n    return status()\n"
            ),
            "helpers/__init__.py": b"from .runtime import status\n",
        },
        source_commit_sha=SOURCE_SHA,
    )
    with pytest.raises(RuntimeArtifactManifestError, match="dependency_missing"):
        validate_grant_service_archive(archive)


def test_missing_absolute_from_member_rejects() -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": (
                b"from helpers import missing\n\ndef main():\n    return missing()\n"
            ),
            "helpers/__init__.py": b"# package\n",
        },
        source_commit_sha=SOURCE_SHA,
    )
    with pytest.raises(RuntimeArtifactManifestError, match="dependency_missing"):
        validate_grant_service_archive(archive)


def test_standard_library_module_shadowing_rejects() -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": (
                b"import json\n\ndef main():\n    return 2\n"
            ),
            "json.py": b"def loads(value):\n    return value\n",
        },
        source_commit_sha=SOURCE_SHA,
    )
    with pytest.raises(RuntimeArtifactManifestError, match="stdlib_shadowed"):
        validate_grant_service_archive(archive)


@pytest.mark.parametrize(
    "source",
    [
        b"import json.nonexistent\n\ndef main():\n    return 2\n",
        b"from json import nonexistent\n\ndef main():\n    return 2\n",
    ],
)
def test_unverifiable_standard_library_member_rejects(source: bytes) -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": source,
        },
        source_commit_sha=SOURCE_SHA,
    )
    with pytest.raises(RuntimeArtifactManifestError, match="stdlib_member_unverifiable"):
        validate_grant_service_archive(archive)


def test_valid_package_relative_dependency_is_closed() -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": (
                b"from helpers import status\n\ndef main():\n    return status()\n"
            ),
            "helpers/__init__.py": b"from .runtime import status\n",
            "helpers/runtime.py": HELPER,
        },
        source_commit_sha=SOURCE_SHA,
    )

    assert validate_grant_service_archive(archive)["file_count"] == 4


def test_beyond_top_level_relative_import_rejects() -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": (
                b"from pkg.sub import call\n\ndef main():\n    return call()\n"
            ),
            "pkg/__init__.py": b"# package\n",
            "pkg/sub/__init__.py": b"from ...outside import call\n",
            "outside.py": b"def call():\n    return 2\n",
        },
        source_commit_sha=SOURCE_SHA,
    )
    with pytest.raises(RuntimeArtifactManifestError, match="dependency_missing"):
        validate_grant_service_archive(archive)


def test_non_python_payload_rejects_at_build_boundary() -> None:
    with pytest.raises(RuntimeArtifactManifestError, match="files_invalid"):
        build_grant_service_archive(
            {
                "__main__.py": ARCHIVE_MAIN,
                "reddog_grant_authority_service.py": SERVICE,
                "config.txt": b"attacker-controlled data",
            },
            source_commit_sha=SOURCE_SHA,
        )


@pytest.mark.parametrize(
    "source",
    [
        b"def main():\n    return __import__('attacker')\n",
        b"import sys\nsys.path.append('/attacker')\ndef main():\n    return 2\n",
        b"import importlib\ndef main():\n    return importlib.import_module('x')\n",
        b"import importlib as loader\ndef main():\n    return loader.import_module('x')\n",
        b"from importlib import import_module as load\ndef main():\n    return load('x')\n",
        b"import sys as runtime\nruntime.path.append('/attacker')\ndef main():\n    return 2\n",
        b"from sys import path\npath.append('/attacker')\ndef main():\n    return 2\n",
        b"import builtins\ndef main():\n    return builtins.exec('x')\n",
        b"def main():\n    return globals()['__builtins__']\n",
        b"import pkgutil\n__path__ = pkgutil.extend_path(__path__, __name__)\ndef main():\n    return 2\n",
        b"__path__.insert(0, '/attacker')\ndef main():\n    return 2\n",
        b"import sys\ndef main():\n    return getattr(sys, 'path')\n",
        b"import sys\ndef main():\n    setattr(sys.modules[__name__], 'main', None)\n    return 2\n",
        b"import sys\nruntime = sys\nruntime.path.append('/attacker')\ndef main():\n    return 2\n",
        b"import sys\nruntime = sys\nruntime.modules[__name__].main = None\ndef main():\n    return 2\n",
    ],
)
def test_dynamic_loading_and_path_mutation_reject(source: bytes) -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": source,
        },
        source_commit_sha=SOURCE_SHA,
    )
    with pytest.raises(RuntimeArtifactManifestError, match="dynamic_load_forbidden"):
        validate_grant_service_archive(archive)


@pytest.mark.parametrize(
    "source",
    [
        b"async def main():\n    return 2\n",
        b"def main(required):\n    return required\n",
        b"def decorate(fn):\n    return fn\n\n@decorate\ndef main():\n    return 2\n",
        b"def main():\n    return 2\n\nmain = None\n",
        b"def main() -> MissingType:\n    return 2\n",
        b"def main(argv=None):\n    yield 2\n",
        b"def main(argv=None):\n    yield from ()\n",
    ],
)
def test_non_callable_canonical_entrypoint_rejects(source: bytes) -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": source,
        },
        source_commit_sha=SOURCE_SHA,
    )
    with pytest.raises(RuntimeArtifactManifestError, match="entrypoint_invalid"):
        validate_grant_service_archive(archive)


def test_annotation_without_runtime_value_is_not_an_export() -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": (
                b"from helpers import ghost\n\ndef main():\n    return ghost\n"
            ),
            "helpers.py": b"ghost: int\n",
        },
        source_commit_sha=SOURCE_SHA,
    )
    with pytest.raises(RuntimeArtifactManifestError, match="dependency_missing"):
        validate_grant_service_archive(archive)


def test_deleted_export_is_not_available_to_from_import() -> None:
    archive = build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": (
                b"from helpers import ghost\n\ndef main():\n    return ghost\n"
            ),
            "helpers.py": b"ghost = 1\ndel ghost\n",
        },
        source_commit_sha=SOURCE_SHA,
    )
    with pytest.raises(RuntimeArtifactManifestError, match="dependency_missing"):
        validate_grant_service_archive(archive)


def test_maximum_payload_archive_is_accepted() -> None:
    files = _maximum_payload_files()
    archive = build_grant_service_archive(files, source_commit_sha=SOURCE_SHA)

    assert validate_grant_service_archive(archive)["file_count"] == len(files)


def test_canonical_archive_over_payload_limit_rejects_at_use_time() -> None:
    archive = build_grant_service_archive(
        _maximum_payload_files(), source_commit_sha=SOURCE_SHA
    )
    entries = _entries(archive)
    entries["zz_overflow.py"] = b"#" + b"x" * (1024 * 1024 - 1)
    manifest = json.loads(entries[ARCHIVE_MANIFEST].decode("ascii"))
    manifest["files"].append(
        {
            "path": "zz_overflow.py",
            "byte_count": len(entries["zz_overflow.py"]),
            "content_digest": raw_digest(entries["zz_overflow.py"]),
        }
    )
    manifest["file_count"] = len(manifest["files"])
    manifest["archive_source_descriptor_digest"] = digest(
        {
            "claimed_source_commit_sha": manifest["claimed_source_commit_sha"],
            "files": manifest["files"],
        }
    )
    manifest["archive_manifest_id"] = ""
    body = dict(manifest)
    body.pop("archive_manifest_id")
    manifest["archive_manifest_id"] = digest(body)
    entries[ARCHIVE_MANIFEST] = canonical_json(manifest).encode("ascii")

    with pytest.raises(RuntimeArtifactManifestError, match="archive_invalid"):
        validate_grant_service_archive(canonical_archive_bytes(entries))


def test_control_character_archive_path_rejects_at_use_time() -> None:
    entries = _entries(_archive())
    body = entries.pop("helpers/runtime.py")
    bad_path = "helpers/evil\n.py"
    entries[bad_path] = body
    manifest = json.loads(entries[ARCHIVE_MANIFEST].decode("ascii"))
    for item in manifest["files"]:
        if item["path"] == "helpers/runtime.py":
            item["path"] = bad_path
    manifest["files"].sort(key=lambda item: item["path"])
    manifest["archive_source_descriptor_digest"] = digest(
        {
            "claimed_source_commit_sha": manifest["claimed_source_commit_sha"],
            "files": manifest["files"],
        }
    )
    manifest["archive_manifest_id"] = ""
    unsigned = dict(manifest)
    unsigned.pop("archive_manifest_id")
    manifest["archive_manifest_id"] = digest(unsigned)
    entries[ARCHIVE_MANIFEST] = canonical_json(manifest).encode("ascii")

    with pytest.raises(RuntimeArtifactManifestError, match="archive_invalid"):
        validate_grant_service_archive(canonical_archive_bytes(entries))


def test_trailing_bytes_reject() -> None:
    with pytest.raises(RuntimeArtifactManifestError, match="noncanonical"):
        validate_grant_service_archive(_archive() + b"attacker-tail")


def test_compressed_member_rejects() -> None:
    entries = _entries(_archive())
    altered = _zip(entries, compression=zipfile.ZIP_DEFLATED)
    with pytest.raises(RuntimeArtifactManifestError, match="archive_invalid"):
        validate_grant_service_archive(altered)


def test_symlink_member_rejects() -> None:
    entries = _entries(_archive())
    altered = _zip(entries, symlink_path="helpers/runtime.py")
    with pytest.raises(RuntimeArtifactManifestError, match="archive_invalid"):
        validate_grant_service_archive(altered)


def test_duplicate_member_rejects() -> None:
    entries = _entries(_archive())
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w") as archive:
            for path, body in entries.items():
                _write(archive, path, body)
            _write(archive, "helpers/runtime.py", HELPER)
    with pytest.raises(RuntimeArtifactManifestError, match="archive_invalid"):
        validate_grant_service_archive(output.getvalue())


def test_manifest_member_digest_substitution_rejects() -> None:
    entries = _entries(_archive())
    manifest = json.loads(entries[ARCHIVE_MANIFEST].decode("ascii"))
    manifest["files"][-1]["content_digest"] = "sha256:" + "f" * 64
    entries[ARCHIVE_MANIFEST] = canonical_json(manifest).encode("ascii")
    with pytest.raises(RuntimeArtifactManifestError, match="manifest_invalid"):
        validate_grant_service_archive(_zip(entries))


def test_source_commit_must_be_hex() -> None:
    with pytest.raises(RuntimeArtifactManifestError, match="manifest_invalid"):
        build_grant_service_archive(
            {
                "__main__.py": ARCHIVE_MAIN,
                "reddog_grant_authority_service.py": SERVICE,
                "helpers/__init__.py": b"# package\n",
                "helpers/runtime.py": HELPER,
            },
            source_commit_sha="not-a-commit",
        )


def test_archive_modules_remain_bounded_and_effect_free() -> None:
    root = Path(__file__).parents[1] / "src"
    for name in (
        "reddog_grant_authority_service_archive_contract.py",
        "reddog_grant_authority_service_archive_validation.py",
        "reddog_grant_authority_service_entrypoint_validation.py",
        "reddog_grant_authority_service_import_closure.py",
        "reddog_grant_authority_service_import_member_validation.py",
    ):
        source = (root / name).read_text(encoding="ascii")
        lines = source.splitlines()
        assert len(lines) <= 200
        assert all(token not in source for token in ("subprocess", "os.system"))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 50


def _maximum_payload_files() -> dict[str, bytes]:
    service_prefix = b"def main():\n    return 2\n#"
    service = service_prefix + b"x" * (1024 * 1024 - len(service_prefix))
    files = {
        "__main__.py": ARCHIVE_MAIN,
        "reddog_grant_authority_service.py": service,
    }
    remaining = 8 * 1024 * 1024 - sum(map(len, files.values()))
    for index in range(7):
        body = b"#" + b"x" * (min(1024 * 1024, remaining) - 1)
        files[f"payload_{index}.py"] = body
        remaining -= len(body)
    if remaining:
        files["payload_tail.py"] = b"#" + b"x" * (remaining - 1)
    return files


def _archive() -> bytes:
    return build_grant_service_archive(
        {
            "__main__.py": ARCHIVE_MAIN,
            "reddog_grant_authority_service.py": SERVICE,
            "helpers/__init__.py": b"# package\n",
            "helpers/runtime.py": HELPER,
        },
        source_commit_sha=SOURCE_SHA,
    )


def _entries(raw: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
        return {item.filename: archive.read(item) for item in archive.infolist()}


def _zip(
    entries: dict[str, bytes], *, compression: int = zipfile.ZIP_STORED,
    symlink_path: str | None = None,
) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        for path, body in entries.items():
            _write(archive, path, body, compression, path == symlink_path)
    return output.getvalue()


def _write(
    archive: zipfile.ZipFile, path: str, body: bytes,
    compression: int = zipfile.ZIP_STORED, symlink: bool = False,
) -> None:
    info = zipfile.ZipInfo(path, ARCHIVE_TIMESTAMP)
    info.create_system = 3
    info.compress_type = compression
    mode = (stat.S_IFLNK | 0o777) if symlink else (stat.S_IFREG | 0o444)
    info.external_attr = mode << 16
    archive.writestr(info, body)
