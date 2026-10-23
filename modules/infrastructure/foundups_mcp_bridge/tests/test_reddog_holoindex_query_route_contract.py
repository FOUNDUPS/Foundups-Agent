from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_route_contract import (
    JOURNAL_SCHEMA_VERSION,
    ROUTE_MAX_BYTES,
    ROUTE_SCHEMA_VERSION,
    QueryRouteContractError,
    QueryRouteJournal,
    QueryRouteRecord,
    empty_route_record,
    encode_route_journal,
    parse_route_journal_bytes,
    parse_route_record_bytes,
    prove_route_record,
    route_record_from_mapping,
    route_record_mapping,
)


def _digest(character: str) -> str:
    return "sha256:" + character * 64


def _current_mapping(
    authority: Path, replica: Path, previous: str, *, revision: int = 1,
) -> dict[str, object]:
    return {
        "schema_version": ROUTE_SCHEMA_VERSION,
        "status": "CURRENT",
        "revision": revision,
        "activation_id": _digest("a"),
        "previous_route_digest": previous,
        "activated_at": "2026-08-23T00:00:00Z",
        "authority_repo_root": str(authority),
        "replica_root": str(replica),
        "canonical": {
            "repo_head_sha": "b" * 40,
            "repo_root_digest": _digest("c"),
            "generation_id": _digest("d"),
            "receipt_digest": _digest("e"),
        },
        "replica": {
            "query_replica_descriptor_digest": _digest("f"),
            "query_replica_generation_id": _digest("d"),
            "query_replica_id": _digest("1"),
            "query_replica_path_identity_digest": _digest("2"),
        },
    }


def _current(tmp_path: Path, previous: str | None = None) -> QueryRouteRecord:
    empty = prove_route_record(empty_route_record())
    mapping = _current_mapping(
        tmp_path / "authority", tmp_path / "replica", previous or empty.digest
    )
    return route_record_from_mapping(mapping)


def test_empty_and_current_records_round_trip_canonically(tmp_path: Path) -> None:
    for record in (empty_route_record(), _current(tmp_path)):
        proof = prove_route_record(record)
        parsed = parse_route_record_bytes(proof.encoded)
        assert parsed == proof
        assert proof.encoded.endswith(b"\n")
        assert type(parsed.record.canonical) is MappingProxyType
        with pytest.raises(TypeError):
            parsed.record.canonical["generation_id"] = _digest("9")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "route.v0"),
        ("status", "current"),
        ("revision", True),
        ("activation_id", "sha256:no"),
        ("previous_route_digest", ""),
        ("activated_at", "2026-08-23"),
        ("authority_repo_root", "relative"),
        ("replica_root", "relative"),
    ],
)
def test_current_record_rejects_hostile_top_level_values(
    tmp_path: Path, field: str, value: object,
) -> None:
    empty = prove_route_record(empty_route_record())
    mapping = _current_mapping(tmp_path / "authority", tmp_path / "replica", empty.digest)
    mapping[field] = value
    with pytest.raises(QueryRouteContractError):
        route_record_from_mapping(mapping)


def test_record_rejects_shape_generation_and_mutable_bindings(tmp_path: Path) -> None:
    empty = prove_route_record(empty_route_record())
    mapping = _current_mapping(tmp_path / "authority", tmp_path / "replica", empty.digest)
    mapping["extra"] = "value"
    with pytest.raises(QueryRouteContractError, match="QUERY_ROUTE_SHAPE_INVALID"):
        route_record_from_mapping(mapping)
    mapping.pop("extra")
    mapping["replica"]["query_replica_generation_id"] = _digest("9")
    with pytest.raises(QueryRouteContractError, match="QUERY_ROUTE_GENERATION_MISMATCH"):
        route_record_from_mapping(mapping)
    direct = QueryRouteRecord(
        ROUTE_SCHEMA_VERSION, "EMPTY", 0, "", "", "", "", "",
        {"repo_head_sha": "", "repo_root_digest": "", "generation_id": "", "receipt_digest": ""},
        {key: "" for key in _current_mapping(tmp_path, tmp_path, empty.digest)["replica"]},
    )
    with pytest.raises(QueryRouteContractError, match="QUERY_ROUTE_BINDING_SHAPE_INVALID"):
        prove_route_record(direct)


def test_direct_record_proof_copies_and_strictly_validates_proxy_bindings(
    tmp_path: Path,
) -> None:
    empty = prove_route_record(empty_route_record())
    mapping = _current_mapping(tmp_path / "authority", tmp_path / "replica", empty.digest)
    canonical_backing = dict(mapping["canonical"])
    replica_backing = dict(mapping["replica"])
    direct = QueryRouteRecord(
        ROUTE_SCHEMA_VERSION, "CURRENT", 1, mapping["activation_id"],
        empty.digest, mapping["activated_at"], mapping["authority_repo_root"],
        mapping["replica_root"], MappingProxyType(canonical_backing),
        MappingProxyType(replica_backing),
    )
    proof = prove_route_record(direct)
    canonical_backing["generation_id"] = _digest("9")
    replica_backing["extra"] = _digest("8")
    assert proof.record.canonical["generation_id"] == _digest("d")
    assert "extra" not in proof.record.replica
    assert parse_route_record_bytes(proof.encoded) == proof

    canonical_backing = dict(mapping["canonical"])
    canonical_backing["extra"] = _digest("8")
    hostile = QueryRouteRecord(
        ROUTE_SCHEMA_VERSION, "CURRENT", 1, mapping["activation_id"],
        empty.digest, mapping["activated_at"], mapping["authority_repo_root"],
        mapping["replica_root"], MappingProxyType(canonical_backing),
        MappingProxyType(dict(mapping["replica"])),
    )
    with pytest.raises(QueryRouteContractError, match="QUERY_ROUTE_BINDING_SHAPE_INVALID"):
        prove_route_record(hostile)


def test_direct_record_hostile_binding_type_has_stable_error(tmp_path: Path) -> None:
    empty = prove_route_record(empty_route_record())
    mapping = _current_mapping(tmp_path / "authority", tmp_path / "replica", empty.digest)
    canonical = dict(mapping["canonical"])
    canonical["repo_head_sha"] = 7
    direct = QueryRouteRecord(
        ROUTE_SCHEMA_VERSION, "CURRENT", 1, mapping["activation_id"],
        empty.digest, mapping["activated_at"], mapping["authority_repo_root"],
        mapping["replica_root"], MappingProxyType(canonical),
        MappingProxyType(dict(mapping["replica"])),
    )
    with pytest.raises(QueryRouteContractError, match="QUERY_ROUTE_TEXT_INVALID"):
        prove_route_record(direct)


def test_route_parser_rejects_duplicate_noncanonical_constant_and_oversize() -> None:
    with pytest.raises(QueryRouteContractError, match="DUPLICATE"):
        parse_route_record_bytes(b'{"schema_version":"a","schema_version":"b"}\n')
    proof = prove_route_record(empty_route_record())
    pretty = (json.dumps(route_record_mapping(proof.record), indent=2) + "\n").encode("ascii")
    with pytest.raises(QueryRouteContractError, match="NOT_CANONICAL"):
        parse_route_record_bytes(pretty)
    with pytest.raises(QueryRouteContractError):
        parse_route_record_bytes(b'{"revision":NaN}\n')
    with pytest.raises(QueryRouteContractError, match="JSON_INVALID"):
        parse_route_record_bytes(b"x" * (ROUTE_MAX_BYTES + 1))


def test_journal_round_trip_and_chain_binding(tmp_path: Path) -> None:
    previous = prove_route_record(empty_route_record())
    candidate = prove_route_record(_current(tmp_path, previous.digest))
    journal = QueryRouteJournal(
        JOURNAL_SCHEMA_VERSION, "PREPARED", candidate.record.activation_id,
        previous.digest, candidate.digest, previous.record, candidate.record,
    )
    encoded = encode_route_journal(journal)
    assert parse_route_journal_bytes(encoded) == journal
    broken = QueryRouteJournal(
        JOURNAL_SCHEMA_VERSION, "PREPARED", candidate.record.activation_id,
        previous.digest, candidate.digest, candidate.record, previous.record,
    )
    with pytest.raises(QueryRouteContractError, match="JOURNAL_BINDING_INVALID"):
        encode_route_journal(broken)


def test_journal_rejects_duplicate_and_noncanonical(tmp_path: Path) -> None:
    previous = prove_route_record(empty_route_record())
    candidate = prove_route_record(_current(tmp_path, previous.digest))
    journal = QueryRouteJournal(
        JOURNAL_SCHEMA_VERSION, "COMMITTED", candidate.record.activation_id,
        previous.digest, candidate.digest, previous.record, candidate.record,
    )
    mapping = json.loads(encode_route_journal(journal))
    pretty = (json.dumps(mapping, indent=2) + "\n").encode("ascii")
    with pytest.raises(QueryRouteContractError, match="NOT_CANONICAL"):
        parse_route_journal_bytes(pretty)
    with pytest.raises(QueryRouteContractError, match="DUPLICATE"):
        parse_route_journal_bytes(b'{"schema_version":"a","schema_version":"b"}\n')


def test_direct_journal_hostile_status_has_stable_error(tmp_path: Path) -> None:
    previous = prove_route_record(empty_route_record())
    candidate = prove_route_record(_current(tmp_path, previous.digest))
    journal = QueryRouteJournal(
        JOURNAL_SCHEMA_VERSION, [], candidate.record.activation_id,
        previous.digest, candidate.digest, previous.record, candidate.record,
    )
    with pytest.raises(QueryRouteContractError, match="QUERY_ROUTE_TEXT_INVALID"):
        encode_route_journal(journal)
