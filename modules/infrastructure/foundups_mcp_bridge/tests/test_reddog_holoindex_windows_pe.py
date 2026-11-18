"""Hostile contract tests for the bounded Windows PE metadata parser."""

from __future__ import annotations

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_windows_pe import (
    AMD64_MACHINE,
    PEFormatError,
    PELimits,
    parse_pe_image,
)
from modules.infrastructure.foundups_mcp_bridge.tests.reddog_holoindex_runtime_composition_test_support import (
    synthetic_pe,
)


def _minimal_pe(*, machine: int = AMD64_MACHINE, delay_attributes: int = 1) -> bytes:
    import struct

    data = bytearray(synthetic_pe(
        machine=machine, exports=("PyInit_demo", "PyLong_FromLong")
    ))
    optional = 0x98
    struct.pack_into("<II", data, optional + 112 + 13 * 8, 0x1400, 0x40)
    struct.pack_into(
        "<8I", data, 0x600, delay_attributes, 0x1440, 0x1458,
        0x1460, 0x1460, 0, 0, 0
    )
    data[0x640:0x651] = b"VCRUNTIME140.dll\0"
    struct.pack_into("<QQ", data, 0x660, 0x1480, 0)
    struct.pack_into("<H", data, 0x680, 0)
    data[0x682:0x689] = b"memcpy\0"
    return bytes(data)


def test_parses_amd64_normal_delay_imports_and_exports() -> None:
    image = parse_pe_image(_minimal_pe())

    assert image.machine == AMD64_MACHINE
    assert image.is_dll is True
    assert [(row.library, row.delayed) for row in image.imports] == [
        ("kernel32.dll", False), ("vcruntime140.dll", True)
    ]
    assert image.imports[0].names == ("GetProcAddress",)
    assert image.export_names == ("PyInit_demo", "PyLong_FromLong")
    assert image.export_ordinals == (1, 2)
    assert image.export_table_entry_count == 2
    assert image.decoded_name_byte_count > 0


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: b"NO" + value[2:], "PE_DOS_SIGNATURE_INVALID"),
        (lambda value: value[:0x80] + b"NOPE" + value[0x84:], "PE_SIGNATURE_INVALID"),
        (lambda value: value[:100], "PE_HEADER_INVALID"),
    ],
)
def test_malformed_or_truncated_images_fail(mutation, code: str) -> None:
    with pytest.raises(PEFormatError, match=code):
        parse_pe_image(mutation(_minimal_pe()))


@pytest.mark.parametrize("attributes", [0, 2])
def test_nonmodern_delay_attributes_fail_closed(attributes: int) -> None:
    with pytest.raises(PEFormatError, match="PE_DELAY_IMPORT_ATTRIBUTES_INVALID"):
        parse_pe_image(_minimal_pe(delay_attributes=attributes))


@pytest.mark.parametrize(
    ("offset", "code"),
    [
        (0x40C, "PE_IMPORT_NAME_RVA_INVALID"),
        (0x410, "PE_IMPORT_THUNK_INVALID"),
        (0x608, "PE_DELAY_IMPORT_HMOD_INVALID"),
        (0x60C, "PE_IMPORT_THUNK_INVALID"),
    ],
)
def test_required_import_structure_rejects_null_rvas(offset: int, code: str) -> None:
    import struct

    data = bytearray(_minimal_pe())
    struct.pack_into("<I", data, offset, 0)
    with pytest.raises(PEFormatError, match=code):
        parse_pe_image(bytes(data))


def test_delay_lookup_and_iat_lengths_must_match() -> None:
    import struct

    data = bytearray(_minimal_pe())
    struct.pack_into("<I", data, 0x60C, 0x1488)
    with pytest.raises(PEFormatError, match="PE_IMPORT_TABLE_LENGTH_MISMATCH"):
        parse_pe_image(bytes(data))


def test_present_optional_delay_table_length_must_match() -> None:
    import struct

    data = bytearray(_minimal_pe())
    struct.pack_into("<I", data, 0x614, 0x1490)
    with pytest.raises(PEFormatError, match="PE_IMPORT_TABLE_LENGTH_MISMATCH"):
        parse_pe_image(bytes(data))


@pytest.mark.parametrize("offset", [0x21C, 0x220, 0x224])
def test_nonempty_exports_reject_null_table_rvas(offset: int) -> None:
    import struct

    data = bytearray(_minimal_pe())
    struct.pack_into("<I", data, offset, 0)
    with pytest.raises(PEFormatError, match="PE_EXPORT_LIMIT_EXCEEDED"):
        parse_pe_image(bytes(data))


def test_forwarded_exports_are_explicitly_classified() -> None:
    import struct

    data = bytearray(_minimal_pe())
    struct.pack_into("<I", data, 0x240, 0x10E0)
    data[0x2E0:0x2F2] = b"other.PyInit_demo\0"

    image = parse_pe_image(bytes(data))

    assert image.forwarded_export_names == ("PyInit_demo",)
    assert image.forwarded_export_ordinals == (1,)


def test_nonforwarded_export_target_must_map_to_virtual_image() -> None:
    import struct

    data = bytearray(_minimal_pe())
    struct.pack_into("<I", data, 0x240, 0x9000)

    with pytest.raises(PEFormatError, match="PE_RVA_UNMAPPED"):
        parse_pe_image(bytes(data))


def test_forwarder_string_must_terminate_inside_export_directory() -> None:
    import struct

    data = bytearray(_minimal_pe())
    struct.pack_into("<I", data, 0x240, 0x10FF)
    data[0x2FF:0x303] = b"x.y\0"

    with pytest.raises(PEFormatError, match="PE_STRING_INVALID"):
        parse_pe_image(bytes(data))


def test_name_string_cannot_cross_raw_section_boundary() -> None:
    import struct

    data = bytearray(_minimal_pe())
    struct.pack_into("<H", data, 0x86, 2)
    struct.pack_into("<I", data, 0x198, 0x500)
    second = 0x188 + 40
    data[second:second + 8] = b".next\0\0\0"
    struct.pack_into("<IIII", data, second + 8, 0x100, 0x2000, 0x100, 0x700)
    struct.pack_into("<I", data, 0x40C, 0x14FF)
    data[0x6FF:0x703] = b"AB\0\0"

    with pytest.raises(PEFormatError, match="PE_STRING_INVALID"):
        parse_pe_image(bytes(data))


def test_repeated_thunk_table_is_scanned_once_under_global_budget() -> None:
    import struct

    data = bytearray(_minimal_pe())
    struct.pack_into("<IIIII", data, 0x414, 0x1260, 0, 0, 0x1240, 0x1260)

    image = parse_pe_image(
        bytes(data), PELimits(max_import_libraries=3, max_import_thunk_entries=4)
    )

    assert image.imports[0].names == ("GetProcAddress",)


def test_repeated_name_rvas_are_decoded_once_under_global_budget() -> None:
    import struct

    baseline = parse_pe_image(_minimal_pe())
    data = bytearray(_minimal_pe())
    struct.pack_into("<IIIII", data, 0x414, 0x1260, 0, 0, 0x1240, 0x1260)

    image = parse_pe_image(
        bytes(data), PELimits(
            max_import_libraries=3,
            max_decoded_name_bytes=baseline.decoded_name_byte_count,
        )
    )

    assert image.decoded_name_byte_count == baseline.decoded_name_byte_count


def test_decoded_name_bytes_are_bounded() -> None:
    baseline = parse_pe_image(_minimal_pe())

    with pytest.raises(PEFormatError, match="PE_NAME_BYTE_LIMIT_EXCEEDED"):
        parse_pe_image(
            _minimal_pe(), PELimits(
                max_decoded_name_bytes=baseline.decoded_name_byte_count - 1
            )
        )


def test_global_thunk_work_budget_includes_termination() -> None:
    with pytest.raises(PEFormatError, match="PE_IMPORT_SYMBOL_LIMIT_EXCEEDED"):
        parse_pe_image(_minimal_pe(), PELimits(max_import_thunk_entries=1))


def test_data_directory_rva_overflow_fails_closed() -> None:
    import struct

    data = bytearray(_minimal_pe())
    struct.pack_into("<II", data, 0x98 + 120, 0xFFFF_FFF0, 0x80)
    with pytest.raises(PEFormatError, match="PE_IMPORT_DIRECTORY_INVALID"):
        parse_pe_image(bytes(data))


def test_overlapping_raw_sections_fail_closed() -> None:
    data = bytearray(_minimal_pe())
    import struct

    struct.pack_into("<H", data, 0x86, 2)
    second = 0x188 + 40
    data[second:second + 8] = b".evil\0\0\0"
    struct.pack_into("<IIII", data, second + 8, 0x100, 0x2000, 0x100, 0x280)

    with pytest.raises(PEFormatError, match="PE_SECTION_RAW_OVERLAP"):
        parse_pe_image(bytes(data))


def test_ordinal_imports_are_bounded_and_parsed() -> None:
    data = bytearray(_minimal_pe())
    import struct

    struct.pack_into("<QQ", data, 0x460, (1 << 63) | 17, 0)

    image = parse_pe_image(bytes(data))

    assert image.imports[0].names == ()
    assert image.imports[0].ordinals == (17,)


def test_bool_and_oversize_limits_reject() -> None:
    with pytest.raises(PEFormatError, match="PE_LIMIT_INVALID"):
        parse_pe_image(_minimal_pe(), PELimits(max_sections=True))
    with pytest.raises(PEFormatError, match="PE_IMAGE_SIZE_INVALID"):
        parse_pe_image(_minimal_pe(), PELimits(max_image_bytes=512))
