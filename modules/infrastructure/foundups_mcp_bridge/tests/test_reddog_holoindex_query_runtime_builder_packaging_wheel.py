from __future__ import annotations

import base64
import csv
from dataclasses import fields, replace
import hashlib
import io
import os
from pathlib import Path
import stat
import struct
import tempfile
import zipfile

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_wheel import (
    BuilderPackagingWheelError,
    BuilderPackagingWheelLimits,
    _prove_packaging_wheel_bytes_for_test,
    admit_pinned_builder_packaging_wheel,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_runtime_builder_packaging_wheel as wheel_module,
)


_FILENAME = "packaging-26.0-py3-none-any.whl"
_DIST_INFO = "packaging-26.0.dist-info"
_EOCD = struct.Struct("<4s4H2LH")
_CENTRAL = struct.Struct("<4s6H3L5H2L")
_LOCAL = struct.Struct("<4s5H3L2H")


def _record_hash(payload: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest())
    return "sha256=" + digest.decode("ascii").rstrip("=")


def _record(files: list[tuple[str, bytes]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for name, payload in files:
        writer.writerow((name, _record_hash(payload), len(payload)))
    writer.writerow((f"{_DIST_INFO}/RECORD", "", ""))
    return output.getvalue().encode("utf-8")


def _members(*, metadata: bytes | None = None, wheel: bytes | None = None):
    files = [
        ("packaging/__init__.py", b'__version__ = "26.0"\n'),
        ("packaging/version.py", b"class Version: pass\n"),
        (f"{_DIST_INFO}/METADATA", metadata or b"Name: packaging\nVersion: 26.0\n"),
        (f"{_DIST_INFO}/WHEEL", wheel or (
            b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        )),
    ]
    return [*files, (f"{_DIST_INFO}/RECORD", _record(files))]


def _wheel_bytes(
    members: list[tuple[str, bytes]] | None = None,
    *,
    extra: bytes = b"",
    comment: bytes = b"",
) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.comment = comment
        for name, payload in members or _members():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.extra = extra
            archive.writestr(info, payload)
    return output.getvalue()


def _admit(payload: bytes, **kwargs):
    return _prove_packaging_wheel_bytes_for_test(
        wheel_bytes=payload,
        expected_filename=_FILENAME,
        expected_size=len(payload),
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        **kwargs,
    )


def _replace_member(
    members: list[tuple[str, bytes]], target: str, replacement: bytes,
) -> list[tuple[str, bytes]]:
    return [(name, replacement if name == target else payload) for name, payload in members]


def _central_offset(payload: bytes) -> int:
    return int(_EOCD.unpack_from(payload, len(payload) - _EOCD.size)[6])


def _physical_fixture(monkeypatch):
    Path("O:/tmp").mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix="reddog-wheel-", dir="O:/tmp")
    root = Path(temporary.name)
    path = root / _FILENAME
    payload = _wheel_bytes()
    path.write_bytes(payload)
    monkeypatch.setattr(wheel_module, "PACKAGING_26_WHEEL_SIZE", len(payload))
    monkeypatch.setattr(
        wheel_module, "PACKAGING_26_WHEEL_SHA256", hashlib.sha256(payload).hexdigest(),
    )
    return temporary, root, path


def test_strict_wheel_byte_proof_binds_distribution_without_public_authority() -> None:
    result = _admit(_wheel_bytes())
    assert result.distribution_name == "packaging"
    assert result.distribution_version == "26.0"
    assert result.wheel_tag == "py3-none-any"
    assert result.member_count == 5
    assert not hasattr(result, "reviewed_pin_match")
    assert not hasattr(result, "source_lease_held_during_admission")


@pytest.mark.parametrize("mutation", ["truncated", "trailer", "comment", "extra"])
def test_archive_envelope_rejects_noncanonical_zip_dialects(mutation: str) -> None:
    payload = _wheel_bytes(extra=b"\x01\x00\x00\x00" if mutation == "extra" else b"",
                           comment=b"x" if mutation == "comment" else b"")
    if mutation == "truncated":
        payload = payload[:-1]
    elif mutation == "trailer":
        payload += b"x"
    with pytest.raises(BuilderPackagingWheelError):
        _admit(payload)


@pytest.mark.parametrize("flag", [0x0001, 0x0008, 0x0800])
def test_archive_rejects_encryption_descriptors_and_utf8_flag(flag: int) -> None:
    payload = bytearray(_wheel_bytes())
    central = _central_offset(payload)
    struct.pack_into("<H", payload, 6, flag)
    struct.pack_into("<H", payload, central + 8, flag)
    with pytest.raises(BuilderPackagingWheelError, match="FLAGS"):
        _admit(bytes(payload))


def test_archive_rejects_local_and_central_name_disagreement() -> None:
    payload = bytearray(_wheel_bytes())
    name_length = _LOCAL.unpack_from(payload, 0)[9]
    assert name_length > 1
    payload[_LOCAL.size] = ord("P")
    with pytest.raises(BuilderPackagingWheelError, match="HEADER_MISMATCH"):
        _admit(bytes(payload))


def test_archive_rejects_gaps_between_local_members() -> None:
    payload = bytearray(_wheel_bytes())
    central = _central_offset(payload)
    payload[central:central] = b"x"
    struct.pack_into("<L", payload, len(payload) - _EOCD.size + 16, central + 1)
    with pytest.raises(BuilderPackagingWheelError):
        _admit(bytes(payload))


@pytest.mark.parametrize(
    "name",
    [
        "../version.py",
        "Packaging/version.py",
        "packaging/CON.py",
        "packaging/a:evil.py",
        "packaging/a\\evil.py",
        "packaging/a<evil.py",
        "packaging/a>evil.py",
        'packaging/a"evil.py',
        "packaging/a|evil.py",
        "packaging/a?evil.py",
        "packaging/a*evil.py",
        "packaging/a\x01evil.py",
        "packaging/a\x7fevil.py",
        "packaging/trailing./evil.py",
        "packaging/sitecustomize.py",
        "packaging/hook.pth",
    ],
)
def test_archive_rejects_unsafe_or_non_distribution_member_paths(name: str) -> None:
    members = _members()
    members[1] = (name, members[1][1])
    record_target = f"{_DIST_INFO}/RECORD"
    files = [(path, data) for path, data in members if path != record_target]
    members[-1] = (record_target, _record(files))
    with pytest.raises(BuilderPackagingWheelError):
        _admit(_wheel_bytes(members))


def test_archive_rejects_casefold_member_aliases() -> None:
    members = _members()
    members.insert(1, ("PACKAGING/__init__.py", b"alias"))
    record_target = f"{_DIST_INFO}/RECORD"
    files = [(name, data) for name, data in members if name != record_target]
    members[-1] = (record_target, _record(files))
    with pytest.raises(BuilderPackagingWheelError, match="PATH_COLLISION"):
        _admit(_wheel_bytes(members))


def test_archive_rejects_file_prefix_collision() -> None:
    members = _members()
    members.insert(2, ("packaging/version.py/child", b"x"))
    record_target = f"{_DIST_INFO}/RECORD"
    files = [(name, data) for name, data in members if name != record_target]
    members[-1] = (record_target, _record(files))
    with pytest.raises(BuilderPackagingWheelError, match="PATH_COLLISION"):
        _admit(_wheel_bytes(members))


@pytest.mark.parametrize(
    ("target", "replacement", "error"),
    [
        (f"{_DIST_INFO}/METADATA", b"Name: packaging\nName: evil\nVersion: 26.0\n", "METADATA"),
        (f"{_DIST_INFO}/WHEEL", b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: cp312-win_amd64\n", "WHEEL"),
    ],
)
def test_distribution_identity_requires_exact_metadata_and_wheel(
    target: str, replacement: bytes, error: str,
) -> None:
    members = _replace_member(_members(), target, replacement)
    record_target = f"{_DIST_INFO}/RECORD"
    files = [(name, data) for name, data in members if name != record_target]
    members[-1] = (record_target, _record(files))
    with pytest.raises(BuilderPackagingWheelError, match=error):
        _admit(_wheel_bytes(members))


def test_record_must_bind_every_exact_archive_member() -> None:
    members = _members()
    record_target = f"{_DIST_INFO}/RECORD"
    missing = [(name, data) for name, data in members if name not in {record_target, "packaging/version.py"}]
    members[-1] = (record_target, _record(missing))
    with pytest.raises(BuilderPackagingWheelError, match="RECORD_OWNERSHIP"):
        _admit(_wheel_bytes(members))


def test_record_member_hash_must_be_canonical_and_correct() -> None:
    members = _members()
    record_target = f"{_DIST_INFO}/RECORD"
    rows = _record([(name, data) for name, data in members if name != record_target])
    members[-1] = (record_target, rows.replace(b"sha256=", b"sha256=A", 1))
    with pytest.raises(BuilderPackagingWheelError, match="RECORD"):
        _admit(_wheel_bytes(members))


def test_declared_expansion_and_ratio_limits_are_fail_closed() -> None:
    limits = BuilderPackagingWheelLimits(max_compression_ratio=1)
    with pytest.raises(BuilderPackagingWheelError, match="COMPRESSION_RATIO"):
        _admit(_wheel_bytes(), limits=limits)


@pytest.mark.parametrize("field", ["filename", "size", "digest"])
def test_reviewed_pin_is_checked_before_archive_admission(field: str) -> None:
    payload = _wheel_bytes()
    values = {
        "expected_filename": "wrong.whl" if field == "filename" else _FILENAME,
        "expected_size": len(payload) + (1 if field == "size" else 0),
        "expected_sha256": "0" * 64 if field == "digest" else hashlib.sha256(payload).hexdigest(),
    }
    with pytest.raises(BuilderPackagingWheelError, match="PIN_MISMATCH"):
        _prove_packaging_wheel_bytes_for_test(wheel_bytes=payload, **values)


def test_limits_reject_bool_zero_and_unbounded_values() -> None:
    payload = _wheel_bytes()
    baseline = BuilderPackagingWheelLimits()
    invalid = [replace(baseline, **{field.name: True}) for field in fields(baseline)]
    invalid.extend((
        replace(baseline, max_members=0),
        replace(baseline, max_archive_bytes=1024 * 1024),
    ))
    for limits in invalid:
        with pytest.raises(BuilderPackagingWheelError, match="LIMIT"):
            _admit(payload, limits=limits)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("max_members", 4, "MEMBER_COUNT"),
        ("max_name_bytes", 12, "PATH"),
        ("max_depth", 1, "PATH"),
        ("max_member_bytes", 12, "MEMBER_SIZE"),
        ("max_expanded_bytes", 100, "EXPANDED_SIZE"),
    ],
)
def test_every_archive_resource_ceiling_is_exercised(
    field: str, value: int, error: str,
) -> None:
    limits = replace(BuilderPackagingWheelLimits(), **{field: value})
    with pytest.raises(BuilderPackagingWheelError, match=error):
        _admit(_wheel_bytes(), limits=limits)


def test_archive_payload_must_fit_a_valid_raw_byte_ceiling() -> None:
    payload = _wheel_bytes()
    limits = replace(
        BuilderPackagingWheelLimits(), max_archive_bytes=len(payload) - 1,
    )
    with pytest.raises(BuilderPackagingWheelError, match="ARCHIVE_SIZE"):
        _admit(payload, limits=limits)


@pytest.mark.parametrize(
    ("surface", "offset", "value", "error"),
    [
        ("eocd_h", 4, 1, "MULTIDISK"),
        ("central_h", 4, 0x0214, "VERSION"),
        ("central_h", 10, 0, "MEMBER_TYPE"),
        ("central_l", 38, 0, "MEMBER_TYPE"),
        ("local_h", 4, 10, "HEADER_MISMATCH"),
    ],
)
def test_zip_header_dialects_and_local_disagreement_reject(
    surface: str, offset: int, value: int, error: str,
) -> None:
    payload = bytearray(_wheel_bytes())
    base = len(payload) - _EOCD.size if surface.startswith("eocd") else 0
    if surface.startswith("central"):
        base = _central_offset(payload)
    fmt = "<L" if surface.endswith("l") else "<H"
    struct.pack_into(fmt, payload, base + offset, value)
    with pytest.raises(BuilderPackagingWheelError, match=error):
        _admit(bytes(payload))


def test_crc_mismatch_rejects_after_exact_deflate_decode() -> None:
    payload = bytearray(_wheel_bytes())
    central = _central_offset(payload)
    wrong_crc = (struct.unpack_from("<L", payload, 14)[0] + 1) & 0xFFFFFFFF
    struct.pack_into("<L", payload, 14, wrong_crc)
    struct.pack_into("<L", payload, central + 16, wrong_crc)
    with pytest.raises(BuilderPackagingWheelError, match="CRC_MISMATCH"):
        _admit(bytes(payload))


def test_zip64_member_count_sentinels_reject() -> None:
    payload = bytearray(_wheel_bytes())
    eocd = len(payload) - _EOCD.size
    struct.pack_into("<H", payload, eocd + 8, 0xFFFF)
    struct.pack_into("<H", payload, eocd + 10, 0xFFFF)
    with pytest.raises(BuilderPackagingWheelError, match="MEMBER_COUNT"):
        _admit(bytes(payload))


@pytest.mark.parametrize("mode", [stat.S_IFLNK | 0o777, stat.S_IFREG | 0o755])
def test_symlink_and_executable_member_attributes_reject(mode: int) -> None:
    payload = bytearray(_wheel_bytes())
    struct.pack_into("<L", payload, _central_offset(payload) + 38, mode << 16)
    with pytest.raises(BuilderPackagingWheelError, match="MEMBER_TYPE"):
        _admit(bytes(payload))


def test_exact_duplicate_archive_member_rejects() -> None:
    members = _members()
    members.insert(1, members[0])
    record_target = f"{_DIST_INFO}/RECORD"
    members[-1] = (record_target, _record(members[:-1]))
    with pytest.warns(UserWarning, match="Duplicate name"):
        payload = _wheel_bytes(members)
    with pytest.raises(BuilderPackagingWheelError, match="PATH_COLLISION"):
        _admit(payload)


@pytest.mark.parametrize(
    ("record_mutation", "error"),
    [
        ("case_alias", "RECORD_OWNERSHIP"),
        ("self_hash", "RECORD"),
        ("leading_zero_size", "RECORD"),
        ("noncanonical_hash", "RECORD"),
        ("duplicate_row", "RECORD_OWNERSHIP"),
    ],
)
def test_record_alias_self_hash_size_hash_and_duplicate_rows_reject(
    record_mutation: str, error: str,
) -> None:
    members = _members()
    target = f"{_DIST_INFO}/RECORD"
    raw = dict(members)[target]
    mutated = _replace_member(members, target, _mutated_record(raw, record_mutation))
    with pytest.raises(BuilderPackagingWheelError, match=error):
        _admit(_wheel_bytes(mutated))


def _mutated_record(raw: bytes, mutation: str) -> bytes:
    replacements = {
        "case_alias": (b"packaging/version.py", b"Packaging/version.py"),
        "self_hash": (b",,\n", b",sha256=AAAA,1\n"),
        "leading_zero_size": (b",21\n", b",021\n"),
        "noncanonical_hash": (b"sha256=", b"sha256=A"),
    }
    if mutation == "duplicate_row":
        return raw + raw.splitlines(keepends=True)[0]
    before, after = replacements[mutation]
    return raw.replace(before, after, 1)


def test_duplicate_wheel_tag_rejects() -> None:
    wheel = (
        b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\n"
        b"Tag: py3-none-any\nTag: py3-none-any\n"
    )
    members = _members(wheel=wheel)
    target = f"{_DIST_INFO}/RECORD"
    members[-1] = (target, _record(members[:-1]))
    with pytest.raises(BuilderPackagingWheelError, match="WHEEL"):
        _admit(_wheel_bytes(members))


@pytest.mark.skipif(os.name != "nt", reason="Windows held-descriptor contract")
def test_public_admission_reads_one_exact_file_through_retained_leases(monkeypatch) -> None:
    temporary, root, path = _physical_fixture(monkeypatch)
    try:
        first = admit_pinned_builder_packaging_wheel(
            wheel_path=path, wheel_store_root=root,
        )
        second = admit_pinned_builder_packaging_wheel(
            wheel_path=path, wheel_store_root=root,
        )
        assert first == second
        assert first.source_lease_held_during_admission is True
        binding = first.public_binding
        false_claims = (
            "official_provenance_authenticated", "signature_verified",
            "extraction_performed", "publication_performed",
            "import_authority_verified", "child_execution_authorized",
            "deterministic_effects_verified", "write_denial_verified",
            "activation_eligible", "a_grade_verified", "retrieval_rsi_verified",
            "builder_runtime_authenticated", "preimport_loader_authority_verified",
            "native_loader_closure_verified", "subprocess_closure_verified",
            "exact_runtime_closure_verified", "network_performed",
            "download_performed", "installation_performed",
        )
        assert all(binding[name] is False for name in false_claims)
        assert "path" not in repr(binding).casefold()
    finally:
        temporary.cleanup()


@pytest.mark.skipif(os.name != "nt", reason="Windows held-descriptor contract")
def test_retained_source_lease_denies_same_path_mutation(monkeypatch) -> None:
    temporary, root, path = _physical_fixture(monkeypatch)
    original = wheel_module._prove_packaging_wheel_payload_for_test
    attempted = False

    def attempt_mutation(**kwargs):
        nonlocal attempted
        attempted = True
        with pytest.raises(PermissionError):
            path.write_bytes(kwargs["wheel_bytes"])
        return original(**kwargs)

    try:
        monkeypatch.setattr(wheel_module, "_prove_packaging_wheel_payload_for_test", attempt_mutation)
        result = admit_pinned_builder_packaging_wheel(
            wheel_path=path, wheel_store_root=root,
        )
        assert attempted and result.reviewed_pin_match
    finally:
        temporary.cleanup()


@pytest.mark.skipif(os.name != "nt", reason="Windows held-descriptor contract")
def test_public_admission_rejects_hardlinked_source(monkeypatch) -> None:
    temporary, root, path = _physical_fixture(monkeypatch)
    alias = root / "alias.whl"
    try:
        os.link(path, alias)
        with pytest.raises(BuilderPackagingWheelError, match="SOURCE_INVALID"):
            admit_pinned_builder_packaging_wheel(
                wheel_path=path, wheel_store_root=root,
            )
    finally:
        temporary.cleanup()


@pytest.mark.skipif(os.name != "nt", reason="Windows held-descriptor contract")
def test_public_admission_rejects_alternate_data_stream(monkeypatch) -> None:
    temporary, root, path = _physical_fixture(monkeypatch)
    try:
        Path(str(path) + ":hidden").write_bytes(b"hidden")
        with pytest.raises(BuilderPackagingWheelError, match="ADMISSION_UNAVAILABLE"):
            admit_pinned_builder_packaging_wheel(
                wheel_path=path, wheel_store_root=root,
            )
    finally:
        temporary.cleanup()
