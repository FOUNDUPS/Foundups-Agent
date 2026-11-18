"""Hostile tests for positive query-runtime distribution projection."""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    digest_bytes,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_distribution_graph import (
    DistributionGraphError,
    DistributionGraphLimits,
    derive_distribution_projection,
)


TARGET = {
    "implementation_name": "cpython", "implementation_version": "3.12.10",
    "os_name": "nt", "platform_machine": "AMD64",
    "platform_python_implementation": "CPython",
    "platform_release": "11", "platform_system": "Windows",
    "platform_version": "10.0", "python_full_version": "3.12.10",
    "python_version": "3.12", "sys_platform": "win32",
}


def _record_hash(payload: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(payload).digest())
    return encoded.rstrip(b"=").decode("ascii")


def _distribution(
    name: str, version: str, files: dict[str, bytes], requires: tuple[str, ...] = (),
    provides: tuple[str, ...] = (), requires_python: str = "",
) -> tuple[dict[str, bytes], str]:
    stem = name.replace("-", "_") + f"-{version}.dist-info"
    metadata = (
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
        + "".join(f"Requires-Dist: {row}\n" for row in requires)
        + "".join(f"Provides-Extra: {row}\n" for row in provides)
        + (f"Requires-Python: {requires_python}\n" if requires_python else "")
        + "\n"
    ).encode("utf-8")
    wheel = (
        b"Wheel-Version: 1.0\nRoot-Is-Purelib: false\n"
        b"Tag: cp312-cp312-win_amd64\n"
    )
    payloads = {
        **files, f"{stem}/METADATA": metadata, f"{stem}/WHEEL": wheel,
    }
    record_path = f"{stem}/RECORD"
    lines = [
        f"{path},sha256={_record_hash(payload)},{len(payload)}\n"
        for path, payload in sorted(payloads.items(), key=lambda row: row[0].casefold())
    ]
    payloads[record_path] = ("".join(lines) + f"{record_path},,\n").encode("utf-8")
    return payloads, stem


def _fixture() -> tuple[list[dict[str, object]], dict[str, bytes], tuple[str, str]]:
    demo, demo_stem = _distribution(
        "demo", "1.0", {"demo/__init__.py": b"import dep\n"},
        ("dep>=2; python_version == '3.12'",),
    )
    dep, dep_stem = _distribution(
        "dep", "2.1", {
            "dep/__init__.py": b"VALUE=1\n",
            "dep/native.cp312-win_amd64.pyd": b"MZ-native",
        },
    )
    payloads = {**demo, **dep}
    rows = [
        {
            "path": path, "size": len(payload), "sha256": digest_bytes(payload),
            "role": "dependency_payload",
        }
        for path, payload in sorted(payloads.items(), key=lambda row: row[0].casefold())
    ]
    return rows, payloads, (demo_stem, dep_stem)


def _derive(**overrides):
    rows, payloads, _stems = _fixture()
    kwargs = {
        "inventory_rows": rows, "read_bytes": payloads.__getitem__,
        "root_requirements": [{"name": "demo", "version": "1.0", "extras": []}],
        "module_origins": ["demo/__init__.py", "dep/native.cp312-win_amd64.pyd"],
        "marker_environment": TARGET,
    }
    kwargs.update(overrides)
    return derive_distribution_projection(**kwargs)


def _rebind_member(
    rows: list[dict[str, object]], payloads: dict[str, bytes],
    record_path: str, member_path: str,
) -> None:
    member = payloads[member_path]
    lines = payloads[record_path].splitlines(keepends=True)
    replacement = (
        f"{member_path},sha256={_record_hash(member)},{len(member)}\n".encode()
    )
    payloads[record_path] = b"".join(
        replacement if line.startswith((member_path + ",").encode()) else line
        for line in lines
    )
    for path in (member_path, record_path):
        row = next(item for item in rows if item["path"] == path)
        row.update(size=len(payloads[path]), sha256=digest_bytes(payloads[path]))


def _append_record_lines(
    rows: list[dict[str, object]], payloads: dict[str, bytes],
    record_path: str, lines: list[str],
) -> None:
    payloads[record_path] += "".join(lines).encode("utf-8")
    row = next(item for item in rows if item["path"] == record_path)
    row.update(size=len(payloads[record_path]), sha256=digest_bytes(payloads[record_path]))


def test_positive_projection_binds_transitive_distribution_and_payloads() -> None:
    result = _derive()

    assert [row["name"] for row in result.distributions] == ["demo", "dep"]
    assert result.distributions[0]["direct"] is True
    assert result.distributions[1]["required_by"] == ["demo"]
    assert {row["path"] for row in result.files} == {
        row["path"] for row in _fixture()[0]
    }
    assert [row["path"] for row in result.files if row["role"] == "python_extension"] == [
        "dep/native.cp312-win_amd64.pyd"
    ]
    assert result.module_owners == [
        {"path": "demo/__init__.py", "distribution": "demo"},
        {"path": "dep/native.cp312-win_amd64.pyd", "distribution": "dep"},
    ]


def test_declared_marker_environment_controls_requires_dist() -> None:
    target = dict(TARGET, python_version="3.11", python_full_version="3.11.9")
    with pytest.raises(DistributionGraphError, match="QUERY_DISTRIBUTION_MARKER_ENVIRONMENT_INVALID"):
        _derive(marker_environment=target)


def test_missing_or_ambiguous_module_owner_fails_closed() -> None:
    rows, payloads, _stems = _fixture()
    payloads["missing/module.py"] = b"unowned"
    rows.append({
        "path": "missing/module.py", "size": 7,
        "sha256": digest_bytes(b"unowned"), "role": "dependency_payload",
    })
    rows.sort(key=lambda row: str(row["path"]).casefold())
    with pytest.raises(DistributionGraphError, match="QUERY_DISTRIBUTION_MODULE_OWNER_MISSING"):
        _derive(
            inventory_rows=rows, read_bytes=payloads.__getitem__,
            module_origins=["missing/module.py"],
        )

    rows, payloads, _stems = _fixture()
    duplicate, _stem = _distribution(
        "other", "1.0", {"demo/__init__.py": b"import dep\n"}
    )
    payloads.update(duplicate)
    rows.extend({
        "path": path, "size": len(payload), "sha256": digest_bytes(payload),
        "role": "dependency_payload",
    } for path, payload in duplicate.items() if path not in {row["path"] for row in rows})
    rows.sort(key=lambda row: str(row["path"]).casefold())
    with pytest.raises(DistributionGraphError, match="QUERY_DISTRIBUTION_MODULE_OWNER_AMBIGUOUS"):
        _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)


@pytest.mark.parametrize(
    ("mutation", "code"),
    (
        (lambda rows, payloads: rows[0].update(sha256="sha256:" + "0" * 64), "QUERY_DISTRIBUTION_PAYLOAD_DIGEST_MISMATCH"),
        (lambda rows, payloads: rows[0].update(size=999), "QUERY_DISTRIBUTION_PAYLOAD_SIZE_MISMATCH"),
        (lambda rows, payloads: payloads.update({"demo-1.0.dist-info/METADATA": b"changed"}), "QUERY_DISTRIBUTION_PAYLOAD_SIZE_MISMATCH"),
    ),
)
def test_bound_metadata_and_payload_mutation_rejects(mutation, code: str) -> None:
    rows, payloads, _stems = _fixture()
    mutation(rows, payloads)
    with pytest.raises(DistributionGraphError, match=code):
        _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)


def test_selected_record_rejects_duplicate_traversal_and_missing_hash() -> None:
    rows, payloads, stems = _fixture()
    record = f"{stems[0]}/RECORD"
    payloads[record] += b"demo/__init__.py,,\n"
    rows = deepcopy(rows)
    target = next(row for row in rows if row["path"] == record)
    target.update(size=len(payloads[record]), sha256=digest_bytes(payloads[record]))
    with pytest.raises(DistributionGraphError, match="QUERY_DISTRIBUTION_RECORD_DUPLICATE_PATH"):
        _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)

    rows, payloads, stems = _fixture()
    record = f"{stems[0]}/RECORD"
    payloads[record] += b"../../Scripts/demo.exe,,\n"
    target = next(row for row in rows if row["path"] == record)
    target.update(size=len(payloads[record]), sha256=digest_bytes(payloads[record]))
    with pytest.raises(DistributionGraphError, match="QUERY_DISTRIBUTION_RECORD_DIGEST_INVALID"):
        _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)


@pytest.mark.parametrize("path", ("sitecustomize.py", "usercustomize.py", "evil.pth", "edit.egg-link"))
def test_selected_startup_and_editable_surfaces_reject(path: str) -> None:
    rows, payloads, stems = _fixture()
    payloads[path] = b"ambient"
    rows.append({
        "path": path, "size": len(payloads[path]), "sha256": digest_bytes(payloads[path]),
        "role": "dependency_payload",
    })
    rows.sort(key=lambda row: str(row["path"]).casefold())
    record = f"{stems[0]}/RECORD"
    payloads[record] += f"{path},sha256={_record_hash(payloads[path])},{len(payloads[path])}\n".encode()
    target = next(row for row in rows if row["path"] == record)
    target.update(size=len(payloads[record]), sha256=digest_bytes(payloads[record]))
    with pytest.raises(DistributionGraphError, match="QUERY_DISTRIBUTION_STARTUP_SURFACE_FORBIDDEN"):
        _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)


def test_undeclared_executable_inside_selected_distribution_rejects() -> None:
    rows, payloads, stems = _fixture()
    path = "demo/tool.exe"
    payloads[path] = b"MZ-tool"
    rows.append({
        "path": path, "size": len(payloads[path]), "sha256": digest_bytes(payloads[path]),
        "role": "dependency_payload",
    })
    rows.sort(key=lambda row: str(row["path"]).casefold())
    record = f"{stems[0]}/RECORD"
    payloads[record] += f"{path},sha256={_record_hash(payloads[path])},{len(payloads[path])}\n".encode()
    target = next(row for row in rows if row["path"] == record)
    target.update(size=len(payloads[record]), sha256=digest_bytes(payloads[record]))

    with pytest.raises(DistributionGraphError, match="QUERY_DISTRIBUTION_SUBPROCESS_UNDECLARED"):
        _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)
    result = _derive(
        inventory_rows=rows, read_bytes=payloads.__getitem__,
        declared_subprocess_paths=[path],
    )
    assert next(row for row in result.files if row["path"] == path)["role"] == "declared_subprocess"


def test_root_version_unknown_extra_and_requires_python_reject() -> None:
    with pytest.raises(DistributionGraphError, match="ROOT_VERSION_MISMATCH"):
        _derive(root_requirements=[{"name": "demo", "version": "2.0", "extras": []}])
    with pytest.raises(DistributionGraphError, match="EXTRA_UNPROVIDED"):
        _derive(root_requirements=[{"name": "demo", "version": "1.0", "extras": ["gpu"]}])

    demo, _stem = _distribution(
        "demo", "1.0", {"demo/__init__.py": b"pass\n"},
        requires_python=">=3.13",
    )
    rows = [{
        "path": path, "size": len(payload), "sha256": digest_bytes(payload),
        "role": "dependency_payload",
    } for path, payload in sorted(demo.items(), key=lambda row: row[0].casefold())]
    with pytest.raises(DistributionGraphError, match="REQUIRES_PYTHON_UNSATISFIED"):
        derive_distribution_projection(
            inventory_rows=rows, read_bytes=demo.__getitem__,
            root_requirements=[{"name": "demo", "version": "1.0", "extras": []}],
            module_origins=["demo/__init__.py"], marker_environment=TARGET,
        )


def test_extra_not_equal_is_evaluated_only_for_active_extra() -> None:
    demo, _stem = _distribution(
        "demo", "1.0", {"demo/__init__.py": b"pass\n"},
        ("dep; extra != 'gpu'",), provides=("gpu",),
    )
    dep, _dep_stem = _distribution("dep", "1.0", {"dep/__init__.py": b"pass\n"})
    payloads = {**demo, **dep}
    rows = [{
        "path": path, "size": len(payload), "sha256": digest_bytes(payload),
        "role": "dependency_payload",
    } for path, payload in sorted(payloads.items(), key=lambda row: row[0].casefold())]
    result = derive_distribution_projection(
        inventory_rows=rows, read_bytes=payloads.__getitem__,
        root_requirements=[{"name": "demo", "version": "1.0", "extras": ["gpu"]}],
        module_origins=["demo/__init__.py"], marker_environment=TARGET,
    )
    assert [row["name"] for row in result.distributions] == ["demo"]


def test_import_grounding_and_subprocess_declarations_are_mandatory() -> None:
    with pytest.raises(DistributionGraphError, match="PATH_SET_INVALID"):
        _derive(module_origins=[])
    with pytest.raises(DistributionGraphError, match="SUBPROCESS_DECLARATION_UNUSED"):
        _derive(declared_subprocess_paths=["ghost.exe"])


def test_unrecorded_startup_surface_and_record_metadata_gap_reject() -> None:
    rows, payloads, stems = _fixture()
    direct = f"{stems[0]}/direct_url.json"
    payloads[direct] = b"{}"
    rows.append({
        "path": direct, "size": 2, "sha256": digest_bytes(b"{}"),
        "role": "dependency_payload",
    })
    rows.sort(key=lambda row: str(row["path"]).casefold())
    with pytest.raises(DistributionGraphError, match="RECORD_METADATA_INCOMPLETE"):
        _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)

    rows, payloads, stems = _fixture()
    record = f"{stems[0]}/RECORD"
    wheel = f"{stems[0]}/WHEEL"
    payloads[record] = b"".join(
        line for line in payloads[record].splitlines(keepends=True)
        if not line.startswith((wheel + ",").encode())
    )
    target = next(row for row in rows if row["path"] == record)
    target.update(size=len(payloads[record]), sha256=digest_bytes(payloads[record]))
    with pytest.raises(DistributionGraphError, match="RECORD_METADATA_INCOMPLETE"):
        _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)


def test_disguised_pe_and_selected_byte_limits_reject_before_acceptance() -> None:
    demo, _stem = _distribution(
        "demo", "1.0", {"demo/__init__.py": b"pass\n", "demo/payload.bin": b"MZhidden"},
    )
    rows = [{
        "path": path, "size": len(payload), "sha256": digest_bytes(payload),
        "role": "dependency_payload",
    } for path, payload in sorted(demo.items(), key=lambda row: row[0].casefold())]
    with pytest.raises(DistributionGraphError, match="EXECUTABLE_SUFFIX_MISMATCH"):
        derive_distribution_projection(
            inventory_rows=rows, read_bytes=demo.__getitem__,
            root_requirements=[{"name": "demo", "version": "1.0", "extras": []}],
            module_origins=["demo/__init__.py"], marker_environment=TARGET,
        )
    with pytest.raises(DistributionGraphError, match="PAYLOAD_LIMIT_EXCEEDED"):
        _derive(limits=DistributionGraphLimits(max_selected_file_bytes=4))
    with pytest.raises(DistributionGraphError, match="PAYLOAD_LIMIT_EXCEEDED"):
        _derive(limits=DistributionGraphLimits(max_total_selected_bytes=16))


def test_selected_path_claimed_by_unselected_distribution_rejects() -> None:
    demo, _demo_stem = _distribution(
        "demo", "1.0", {
            "demo/__init__.py": b"pass\n", "demo/shared.py": b"VALUE=1\n",
        },
    )
    other, _other_stem = _distribution(
        "other", "1.0", {"demo/shared.py": b"VALUE=1\n"},
    )
    payloads = {**demo, **other}
    rows = [{
        "path": path, "size": len(payload), "sha256": digest_bytes(payload),
        "role": "dependency_payload",
    } for path, payload in sorted(payloads.items(), key=lambda row: row[0].casefold())]
    with pytest.raises(DistributionGraphError, match="FILE_OWNER_AMBIGUOUS"):
        derive_distribution_projection(
            inventory_rows=rows, read_bytes=payloads.__getitem__,
            root_requirements=[{"name": "demo", "version": "1.0", "extras": []}],
            module_origins=["demo/__init__.py"], marker_environment=TARGET,
        )


def test_dist_info_identity_and_wheel_dialect_are_content_bound() -> None:
    rows, payloads, stems = _fixture()
    metadata = f"{stems[0]}/METADATA"
    record = f"{stems[0]}/RECORD"
    payloads[metadata] = payloads[metadata].replace(b"Name: demo", b"Name: evil")
    _rebind_member(rows, payloads, record, metadata)
    with pytest.raises(DistributionGraphError, match="DIST_INFO_IDENTITY_INVALID"):
        _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)

    rows, payloads, stems = _fixture()
    wheel = f"{stems[0]}/WHEEL"
    record = f"{stems[0]}/RECORD"
    payloads[wheel] = payloads[wheel].replace(b"Root-Is-Purelib: false\n", b"")
    _rebind_member(rows, payloads, record, wheel)
    with pytest.raises(DistributionGraphError, match="WHEEL_INVALID"):
        _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)


def test_unselected_startup_files_do_not_enter_positive_projection() -> None:
    rows, payloads, _stems = _fixture()
    other, _other_stem = _distribution(
        "other", "1.0", {
            "other/__init__.py": b"pass\n", "other/ambient.pyc": b"cache",
            "other/ambient.pth": b"import ambient\n",
        },
    )
    payloads.update(other)
    rows.extend({
        "path": path, "size": len(payload), "sha256": digest_bytes(payload),
        "role": "dependency_payload",
    } for path, payload in other.items())
    rows.sort(key=lambda row: str(row["path"]).casefold())

    result = _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)

    assert all(not row["path"].startswith("other/") for row in result.files)


def test_external_record_scheme_rows_are_explicit_exclusions() -> None:
    rows, payloads, stems = _fixture()
    record = f"{stems[0]}/RECORD"
    data = b"external"
    identity = f"sha256={_record_hash(data)},{len(data)}\n"
    _append_record_lines(rows, payloads, record, [
        f"../../Scripts/demo.exe,{identity}",
        f"../../Scripts/__pycache__/demo.pyc,,\n",
        f"../../share/demo/schema.json,{identity}",
        f"../../include/demo/header.h,{identity}",
    ])

    result = _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)

    assert [row["path"] for row in result.excluded_record_entries] == [
        "@prefix/include/demo/header.h",
        "@prefix/Scripts/__pycache__/demo.pyc",
        "@prefix/Scripts/demo.exe",
        "@prefix/share/demo/schema.json",
    ]
    assert all(
        row["reason"] == "external_distribution_payload_excluded"
        for row in result.excluded_record_entries
    )


@pytest.mark.parametrize(
    "path",
    (
        "..\\..\\Scripts\\demo.exe", "../../../outside/file.py",
        "../../Scripts/demo.exe:stream", "//server/share/demo.exe",
        "../../Scripts/con.exe", "../../Scripts/trailing. ",
        "../../Scripts/e\u0301.exe", "../../Scripts/control\x01.exe",
    ),
)
def test_external_record_aliases_and_escapes_reject(path: str) -> None:
    rows, payloads, stems = _fixture()
    record = f"{stems[0]}/RECORD"
    data = b"external"
    _append_record_lines(rows, payloads, record, [
        f"{path},sha256={_record_hash(data)},{len(data)}\n",
    ])
    with pytest.raises(DistributionGraphError, match="RECORD_(EXTERNAL_PATH_)?INVALID"):
        _derive(inventory_rows=rows, read_bytes=payloads.__getitem__)


def test_external_claim_cannot_ground_module_or_subprocess() -> None:
    rows, payloads, stems = _fixture()
    record = f"{stems[0]}/RECORD"
    data = b"external"
    _append_record_lines(rows, payloads, record, [
        f"../../Scripts/demo.exe,sha256={_record_hash(data)},{len(data)}\n",
    ])
    with pytest.raises(DistributionGraphError, match="MODULE_ORIGIN_UNBOUND"):
        _derive(
            inventory_rows=rows, read_bytes=payloads.__getitem__,
            module_origins=["@prefix/Scripts/demo.exe"],
        )
    with pytest.raises(DistributionGraphError, match="SUBPROCESS_DECLARATION_UNUSED"):
        _derive(
            inventory_rows=rows, read_bytes=payloads.__getitem__,
            declared_subprocess_paths=["@prefix/Scripts/demo.exe"],
        )


def test_requires_dist_name_is_pep503_normalized_after_parse() -> None:
    demo, _stem = _distribution(
        "demo", "1.0", {"demo/__init__.py": b"pass\n"},
        ("typing_extensions>=4.5.0",),
    )
    dependency, _dependency_stem = _distribution(
        "typing-extensions", "4.15.0", {"typing_extensions.py": b"pass\n"},
    )
    payloads = {**demo, **dependency}
    rows = [{
        "path": path, "size": len(payload), "sha256": digest_bytes(payload),
        "role": "dependency_payload",
    } for path, payload in sorted(payloads.items(), key=lambda row: row[0].casefold())]
    result = derive_distribution_projection(
        inventory_rows=rows, read_bytes=payloads.__getitem__,
        root_requirements=[{"name": "demo", "version": "1.0", "extras": []}],
        module_origins=["demo/__init__.py"], marker_environment=TARGET,
    )
    assert [row["name"] for row in result.distributions] == [
        "demo", "typing-extensions",
    ]
