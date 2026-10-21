"""Bounded, dependency-free PE32+ metadata parser for inert runtime audit."""

from __future__ import annotations

import struct
from dataclasses import dataclass


AMD64_MACHINE = 0x8664
PE32_PLUS_MAGIC = 0x20B
IMAGE_FILE_DLL = 0x2000


class PEFormatError(RuntimeError):
    """One PE image is malformed or outside the admitted parser subset."""


def _fail(code: str) -> None:
    raise PEFormatError(code)


@dataclass(frozen=True)
class PELimits:
    max_image_bytes: int = 512 * 1024 * 1024
    max_sections: int = 96
    max_import_libraries: int = 2_048
    max_import_thunk_entries: int = 500_000
    max_exports: int = 500_000
    max_name_bytes: int = 4_096
    max_decoded_name_bytes: int = 64 * 1024 * 1024

    def validate(self) -> None:
        values = tuple(vars(self).values())
        if any(type(value) is not int or value <= 0 for value in values):
            _fail("PE_LIMIT_INVALID")


@dataclass(frozen=True)
class PEImport:
    library: str
    names: tuple[str, ...]
    ordinals: tuple[int, ...]
    delayed: bool


@dataclass(frozen=True)
class PEImage:
    machine: int
    optional_magic: int
    characteristics: int
    import_descriptor_count: int
    import_thunk_entry_count: int
    export_table_entry_count: int
    decoded_name_byte_count: int
    imports: tuple[PEImport, ...]
    export_names: tuple[str, ...]
    export_ordinals: tuple[int, ...]
    forwarded_export_names: tuple[str, ...]
    forwarded_export_ordinals: tuple[int, ...]

    @property
    def is_dll(self) -> bool:
        return bool(self.characteristics & IMAGE_FILE_DLL)


@dataclass(frozen=True)
class _Section:
    virtual_address: int
    virtual_span: int
    raw_offset: int
    raw_size: int


@dataclass(frozen=True)
class _Layout:
    data: bytes
    size_of_headers: int
    sections: tuple[_Section, ...]
    directories: tuple[tuple[int, int], ...]
    limits: PELimits

    def offset(self, rva: int, size: int = 1) -> int:
        if type(rva) is not int or type(size) is not int or rva < 0 or size < 0:
            _fail("PE_RVA_INVALID")
        end = rva + size
        if end < rva:
            _fail("PE_RVA_INVALID")
        if end <= self.size_of_headers:
            return rva
        matches = [
            section for section in self.sections
            if section.virtual_address <= rva
            and end <= section.virtual_address + section.raw_size
        ]
        if len(matches) != 1:
            _fail("PE_RVA_UNMAPPED")
        section = matches[0]
        offset = section.raw_offset + rva - section.virtual_address
        _require_span(self.data, offset, size, "PE_RVA_UNMAPPED")
        return offset

    def require_virtual_span(self, rva: int, size: int) -> None:
        if type(rva) is not int or type(size) is not int or rva < 0 or size <= 0:
            _fail("PE_RVA_INVALID")
        end = rva + size
        if end < rva:
            _fail("PE_RVA_INVALID")
        if end <= self.size_of_headers:
            return
        matches = [
            section for section in self.sections
            if section.virtual_address <= rva
            and end <= section.virtual_address + section.virtual_span
        ]
        if len(matches) != 1:
            _fail("PE_RVA_UNMAPPED")

    def raw_span(self, rva: int, maximum: int) -> tuple[int, int]:
        if type(rva) is not int or type(maximum) is not int or rva < 0 or maximum <= 0:
            _fail("PE_RVA_INVALID")
        if rva < self.size_of_headers:
            available = min(maximum, self.size_of_headers - rva)
            return rva, available
        matches = [
            section for section in self.sections
            if section.virtual_address <= rva
            < section.virtual_address + section.raw_size
        ]
        if len(matches) != 1:
            _fail("PE_RVA_UNMAPPED")
        section = matches[0]
        available = min(
            maximum, section.virtual_address + section.raw_size - rva
        )
        offset = section.raw_offset + rva - section.virtual_address
        _require_span(self.data, offset, available, "PE_RVA_UNMAPPED")
        return offset, available


@dataclass
class _ImportBudget:
    libraries: int
    symbols: int
    thunk_cache: dict[int, tuple[int, ...]]

    @classmethod
    def create(cls, limits: PELimits) -> "_ImportBudget":
        return cls(
            limits.max_import_libraries, limits.max_import_thunk_entries, {}
        )


@dataclass
class _NameBudget:
    remaining: int
    decoded: int
    cache: dict[int, str]

    @classmethod
    def create(cls, limits: PELimits) -> "_NameBudget":
        return cls(limits.max_decoded_name_bytes, 0, {})


def parse_pe_image(payload: bytes, limits: PELimits = PELimits()) -> PEImage:
    """Parse the declared import/export surface without loading the image."""

    limits.validate()
    if type(payload) is not bytes or not 64 <= len(payload) <= limits.max_image_bytes:
        _fail("PE_IMAGE_SIZE_INVALID")
    pe_offset = _headers(payload)
    machine, count, optional_size, characteristics = _coff(payload, pe_offset, limits)
    optional = pe_offset + 24
    magic, size_headers, directories = _optional(
        payload, optional, optional_size
    )
    sections = _sections(
        payload, optional + optional_size, count, size_headers
    )
    layout = _Layout(payload, size_headers, sections, directories, limits)
    budget = _ImportBudget.create(limits)
    name_budget = _NameBudget.create(limits)
    imports = _imports(layout, 1, False, budget, name_budget) + _imports(
        layout, 13, True, budget, name_budget
    )
    exports = _exports(layout, name_budget)
    names, ordinals, forwarded_names, forwarded_ordinals, export_count = exports
    return PEImage(
        machine, magic, characteristics,
        limits.max_import_libraries - budget.libraries,
        limits.max_import_thunk_entries - budget.symbols,
        export_count, name_budget.decoded,
        tuple(sorted(imports, key=lambda row: (row.delayed, row.library))),
        names, ordinals, forwarded_names, forwarded_ordinals,
    )


def _headers(data: bytes) -> int:
    if data[:2] != b"MZ":
        _fail("PE_DOS_SIGNATURE_INVALID")
    pe_offset = _u32(data, 0x3C, "PE_HEADER_INVALID")
    _require_span(data, pe_offset, 24, "PE_HEADER_INVALID")
    if data[pe_offset:pe_offset + 4] != b"PE\0\0":
        _fail("PE_SIGNATURE_INVALID")
    return pe_offset


def _coff(data: bytes, offset: int, limits: PELimits) -> tuple[int, int, int, int]:
    machine, count = struct.unpack_from("<HH", data, offset + 4)
    optional_size, characteristics = struct.unpack_from("<HH", data, offset + 20)
    if count == 0 or count > limits.max_sections or optional_size < 112:
        _fail("PE_COFF_HEADER_INVALID")
    _require_span(data, offset + 24, optional_size, "PE_OPTIONAL_HEADER_INVALID")
    return machine, count, optional_size, characteristics


def _optional(
    data: bytes, offset: int, size: int,
) -> tuple[int, int, tuple[tuple[int, int], ...]]:
    magic = _u16(data, offset, "PE_OPTIONAL_HEADER_INVALID")
    if magic != PE32_PLUS_MAGIC:
        _fail("PE_OPTIONAL_MAGIC_UNSUPPORTED")
    size_headers = _u32(data, offset + 60, "PE_OPTIONAL_HEADER_INVALID")
    count = _u32(data, offset + 108, "PE_OPTIONAL_HEADER_INVALID")
    available = (size - 112) // 8
    if count > available or count > 32 or size_headers == 0 or size_headers > len(data):
        _fail("PE_OPTIONAL_HEADER_INVALID")
    directories = tuple(
        struct.unpack_from("<II", data, offset + 112 + index * 8)
        for index in range(count)
    )
    return magic, size_headers, directories


def _sections(
    data: bytes, offset: int, count: int, size_headers: int,
) -> tuple[_Section, ...]:
    end = offset + count * 40
    _require_span(data, offset, count * 40, "PE_SECTION_TABLE_INVALID")
    if end > size_headers:
        _fail("PE_SECTION_TABLE_INVALID")
    rows: list[_Section] = []
    for index in range(count):
        current = offset + index * 40
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, current + 8
        )
        if raw_size:
            _require_span(data, raw_offset, raw_size, "PE_SECTION_RAW_RANGE_INVALID")
            if raw_offset < size_headers:
                _fail("PE_SECTION_RAW_RANGE_INVALID")
        span = max(virtual_size, raw_size)
        if span == 0 or virtual_address + span > 0x1_0000_0000:
            _fail("PE_SECTION_VIRTUAL_RANGE_INVALID")
        rows.append(_Section(virtual_address, span, raw_offset, raw_size))
    _reject_overlap(
        [(row.raw_offset, row.raw_offset + row.raw_size) for row in rows if row.raw_size],
        "PE_SECTION_RAW_OVERLAP",
    )
    _reject_overlap(
        [(row.virtual_address, row.virtual_address + row.virtual_span) for row in rows],
        "PE_SECTION_VIRTUAL_OVERLAP",
    )
    return tuple(rows)


def _imports(
    layout: _Layout, directory_index: int, delayed: bool,
    budget: _ImportBudget, name_budget: _NameBudget,
) -> tuple[PEImport, ...]:
    if directory_index >= len(layout.directories):
        return ()
    rva, size = layout.directories[directory_index]
    if rva == 0 and size == 0:
        return ()
    width = 32 if delayed else 20
    if rva == 0 or size < width or rva + size > 0x1_0000_0000:
        _fail("PE_IMPORT_DIRECTORY_INVALID")
    rows: dict[str, tuple[set[str], set[int]]] = {}
    terminated = False
    for index in range(layout.limits.max_import_libraries + 1):
        descriptor_rva = rva + index * width
        if descriptor_rva + width > rva + size:
            break
        cursor = layout.offset(descriptor_rva, width)
        fields = struct.unpack_from("<8I" if delayed else "<5I", layout.data, cursor)
        if all(value == 0 for value in fields):
            terminated = True
            break
        if budget.libraries <= 0:
            _fail("PE_IMPORT_LIBRARY_LIMIT_EXCEEDED")
        if delayed and fields[0] != 1:
            _fail("PE_DELAY_IMPORT_ATTRIBUTES_INVALID")
        name_rva = fields[1] if delayed else fields[3]
        if name_rva == 0:
            _fail("PE_IMPORT_NAME_RVA_INVALID")
        lookup_rva, iat_rva = (
            (fields[4], fields[3]) if delayed else (fields[0] or fields[4], fields[4])
        )
        _validate_import_tables(layout, fields, delayed, lookup_rva, iat_rva, budget)
        library = _dll_name(layout, name_rva, name_budget)
        names, ordinals = _names_from_thunks(
            layout, _thunk_values(layout, lookup_rva, budget), name_budget
        )
        slot = rows.setdefault(library, (set(), set()))
        slot[0].update(names)
        slot[1].update(ordinals)
        budget.libraries -= 1
    if not terminated:
        _fail("PE_IMPORT_DIRECTORY_UNTERMINATED")
    return tuple(
        PEImport(name, tuple(sorted(values[0])), tuple(sorted(values[1])), delayed)
        for name, values in rows.items()
    )


def _validate_import_tables(
    layout: _Layout, fields: tuple[int, ...], delayed: bool,
    lookup_rva: int, iat_rva: int, budget: _ImportBudget,
) -> None:
    if lookup_rva == 0 or iat_rva == 0:
        _fail("PE_IMPORT_THUNK_INVALID")
    lookup = _thunk_values(layout, lookup_rva, budget)
    iat = _thunk_values(layout, iat_rva, budget)
    if len(lookup) != len(iat):
        _fail("PE_IMPORT_TABLE_LENGTH_MISMATCH")
    if not delayed:
        return
    if fields[2] == 0:
        _fail("PE_DELAY_IMPORT_HMOD_INVALID")
    layout.require_virtual_span(fields[2], 8)
    for optional_rva in fields[5:7]:
        if optional_rva and len(_thunk_values(layout, optional_rva, budget)) != len(lookup):
            _fail("PE_IMPORT_TABLE_LENGTH_MISMATCH")


def _thunk_values(
    layout: _Layout, rva: int, budget: _ImportBudget,
) -> tuple[int, ...]:
    if rva == 0:
        _fail("PE_IMPORT_THUNK_INVALID")
    if rva in budget.thunk_cache:
        return budget.thunk_cache[rva]
    values: list[int] = []
    while True:
        if budget.symbols <= 0:
            _fail("PE_IMPORT_SYMBOL_LIMIT_EXCEEDED")
        budget.symbols -= 1
        value = _u64(
            layout.data, layout.offset(rva + len(values) * 8, 8),
            "PE_IMPORT_THUNK_INVALID",
        )
        if value == 0:
            result = tuple(values)
            budget.thunk_cache[rva] = result
            return result
        values.append(value)


def _names_from_thunks(
    layout: _Layout, values: tuple[int, ...], name_budget: _NameBudget,
) -> tuple[set[str], set[int]]:
    names: set[str] = set()
    ordinals: set[int] = set()
    for value in values:
        if value & (1 << 63):
            if value & 0x7FFF_FFFF_FFFF_0000:
                _fail("PE_IMPORT_ORDINAL_INVALID")
            ordinals.add(value & 0xFFFF)
        else:
            layout.offset(value, 2)
            names.add(_ascii_z(
                layout, value + 2, layout.limits.max_name_bytes, name_budget,
            ))
    return names, ordinals


def _exports(
    layout: _Layout, name_budget: _NameBudget,
) -> tuple[tuple[str, ...], tuple[int, ...], tuple[str, ...], tuple[int, ...], int]:
    if not layout.directories:
        return (), (), (), (), 0
    rva, size = layout.directories[0]
    if rva == 0 and size == 0:
        return (), (), (), (), 0
    if rva == 0 or size < 40 or rva + size > 0x1_0000_0000:
        _fail("PE_EXPORT_DIRECTORY_INVALID")
    offset = layout.offset(rva, 40)
    base, functions, names = struct.unpack_from("<III", layout.data, offset + 16)
    eat_rva, names_rva, ordinals_rva = struct.unpack_from("<III", layout.data, offset + 28)
    _validate_export_tables(
        layout, functions, names, eat_rva, names_rva, ordinals_rva
    )
    exported_ordinals, forwarded_ordinals = _export_addresses(
        layout, base, functions, eat_rva, rva, size, name_budget
    )
    name_table = layout.offset(names_rva, names * 4) if names else 0
    ordinal_table = layout.offset(ordinals_rva, names * 2) if names else 0
    exported_names: set[str] = set()
    forwarded_names: set[str] = set()
    for index in range(names):
        symbol_rva = _u32(layout.data, name_table + index * 4, "PE_EXPORT_TABLE_INVALID")
        ordinal_index = _u16(layout.data, ordinal_table + index * 2, "PE_EXPORT_TABLE_INVALID")
        if ordinal_index >= functions or base + ordinal_index not in exported_ordinals:
            _fail("PE_EXPORT_ORDINAL_INVALID")
        name = _ascii_z(
            layout, symbol_rva, layout.limits.max_name_bytes, name_budget,
        )
        exported_names.add(name)
        if base + ordinal_index in forwarded_ordinals:
            forwarded_names.add(name)
    return (
        tuple(sorted(exported_names)), exported_ordinals,
        tuple(sorted(forwarded_names)), forwarded_ordinals, functions,
    )


def _export_addresses(
    layout: _Layout, base: int, functions: int, eat_rva: int,
    export_rva: int, export_size: int, name_budget: _NameBudget,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    eat = layout.offset(eat_rva, functions * 4) if functions else 0
    addresses = tuple(
        _u32(layout.data, eat + index * 4, "PE_EXPORT_TABLE_INVALID")
        for index in range(functions)
    )
    for value in addresses:
        if value == 0:
            continue
        if export_rva <= value < export_rva + export_size:
            _forwarder_name(
                layout, value, export_rva + export_size, name_budget
            )
        else:
            layout.require_virtual_span(value, 1)
    exported = tuple(base + index for index, value in enumerate(addresses) if value)
    forwarded = tuple(
        base + index for index, value in enumerate(addresses)
        if value and export_rva <= value < export_rva + export_size
    )
    return exported, forwarded


def _validate_export_tables(
    layout: _Layout, functions: int, names: int,
    eat_rva: int, names_rva: int, ordinals_rva: int,
) -> None:
    if (
        functions > layout.limits.max_exports or names > functions
        or (functions and eat_rva == 0)
        or (names and (names_rva == 0 or ordinals_rva == 0))
    ):
        _fail("PE_EXPORT_LIMIT_EXCEEDED")


def _forwarder_name(
    layout: _Layout, rva: int, export_end: int, budget: _NameBudget,
) -> str:
    value = _ascii_z(
        layout, rva, min(layout.limits.max_name_bytes, export_end - rva - 1),
        budget,
    )
    if "." not in value or value.startswith(".") or value.endswith("."):
        _fail("PE_EXPORT_FORWARDER_INVALID")
    return value


def _dll_name(layout: _Layout, rva: int, budget: _NameBudget) -> str:
    value = _ascii_z(layout, rva, layout.limits.max_name_bytes, budget)
    if any(character in value for character in "/\\:"):
        _fail("PE_IMPORT_LIBRARY_NAME_INVALID")
    return value.casefold()


def _ascii_z(
    layout: _Layout, rva: int, maximum: int, budget: _NameBudget,
) -> str:
    if type(maximum) is not int or maximum <= 0:
        _fail("PE_STRING_INVALID")
    cached = budget.cache.get(rva)
    if cached is not None:
        if len(cached) > maximum:
            _fail("PE_STRING_INVALID")
        return cached
    offset, available = layout.raw_span(rva, maximum + 1)
    end = layout.data.find(b"\0", offset, offset + available)
    if end < 0 or end == offset:
        _fail("PE_STRING_INVALID")
    raw = layout.data[offset:end]
    if len(raw) > budget.remaining:
        _fail("PE_NAME_BYTE_LIMIT_EXCEEDED")
    if any(byte < 0x21 or byte > 0x7E for byte in raw):
        _fail("PE_STRING_INVALID")
    try:
        value = raw.decode("ascii")
    except UnicodeDecodeError:
        _fail("PE_STRING_INVALID")
    budget.remaining -= len(raw)
    budget.decoded += len(raw)
    budget.cache[rva] = value
    return value


def _reject_overlap(ranges: list[tuple[int, int]], code: str) -> None:
    ordered = sorted(ranges)
    if any(current[0] < previous[1] for previous, current in zip(ordered, ordered[1:])):
        _fail(code)


def _require_span(data: bytes, offset: int, size: int, code: str) -> None:
    if type(offset) is not int or type(size) is not int or offset < 0 or size < 0:
        _fail(code)
    if offset + size < offset or offset + size > len(data):
        _fail(code)


def _u16(data: bytes, offset: int, code: str) -> int:
    _require_span(data, offset, 2, code)
    return int(struct.unpack_from("<H", data, offset)[0])


def _u32(data: bytes, offset: int, code: str) -> int:
    _require_span(data, offset, 4, code)
    return int(struct.unpack_from("<I", data, offset)[0])


def _u64(data: bytes, offset: int, code: str) -> int:
    _require_span(data, offset, 8, code)
    return int(struct.unpack_from("<Q", data, offset)[0])


__all__ = [
    "AMD64_MACHINE", "PE32_PLUS_MAGIC", "PEFormatError", "PEImage",
    "PEImport", "PELimits", "parse_pe_image",
]
