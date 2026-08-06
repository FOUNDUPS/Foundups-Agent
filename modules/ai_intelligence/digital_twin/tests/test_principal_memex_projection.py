"""Read-only 012 Principal Memex projection contract tests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

import pytest

from holo_index.query_receipt import digest_json
from modules.ai_intelligence.digital_twin.src.principal_memex_projection import (
    build_principal_memex_item,
    project_principal_memex_readonly,
    rehydrate_principal_memex_projection,
)
from modules.ai_intelligence.digital_twin.src.principal_memex_contract import (
    PROJECTION_READY,
    PrincipalMemexProjection,
    PrincipalMemexProjectionResult,
    _create_principal_memex_projection,
)


NOW = "2026-08-06T12:00:00+00:00"
RECEIPT = "sha256:" + "1" * 64


def _item(**overrides: object):
    values = {
        "principal_id": "012",
        "category": "architectural_principle",
        "statement": "Audit before implementation.",
        "source_kind": "principal_statement",
        "source_receipt_id": RECEIPT,
        "source_revision": "conversation:42",
        "created_at": NOW,
        "sensitivity": "private",
    }
    values.update(overrides)
    return build_principal_memex_item(**values)


def _private_factory_values(projection, items, *, created_at: str = NOW):
    values = {
        key: value
        for key, value in projection.to_dict().items()
        if key not in {"projection_id", "items"}
    }
    values["created_at"] = created_at
    values["item_ids"] = tuple(item.item_id for item in items)
    values["source_receipt_ids"] = tuple(
        sorted({item.source_receipt_id for item in items})
    )
    values["manifest_digest"] = digest_json(
        [
            {"item_id": item.item_id, "content_digest": item.content_digest}
            for item in items
        ]
    )
    return values


def _construct_with_private_factory(projection, items, *, created_at: str = NOW):
    values = _private_factory_values(projection, items, created_at=created_at)
    return _create_principal_memex_projection(
        **values,
        projection_id=digest_json(values),
        items=items,
    )


def test_valid_projection_is_structural_readonly_and_round_trips() -> None:
    result = project_principal_memex_readonly(
        principal_id="012", items=[_item()], created_at=NOW
    )

    assert result.accepted is True
    projection = result.projection
    assert projection is not None
    assert projection.source_class == "principal_memex"
    assert projection.verification == "STRUCTURAL_ONLY"
    assert projection.runtime_admissible is False
    assert projection.no_persistence_performed is True
    assert projection.no_model_context_admission_performed is True
    assert projection.no_foundup_projection_performed is True
    assert projection.no_holoindex_write_performed is True
    assert projection.no_work_authority_granted is True
    assert rehydrate_principal_memex_projection(projection.to_dict()).accepted is True


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("category", "foundup_work", "principal_memex_category_invalid"),
        ("source_kind", "model_claim", "principal_memex_source_kind_invalid"),
        ("retention_state", "approved", "principal_memex_retention_invalid"),
        ("sensitivity", "worker", "principal_memex_sensitivity_invalid"),
        ("created_at", "now", "principal_memex_created_at_invalid"),
        ("source_receipt_id", "sha256:claim", "principal_memex_source_receipt_id_invalid"),
    ],
)
def test_item_policy_rejects_invalid_values(field: str, value: str, reason: str) -> None:
    item = _item()
    forged = replace(item, **{field: value})
    result = project_principal_memex_readonly(
        principal_id="012", items=[forged], created_at=NOW
    )
    assert result.accepted is False
    assert reason in result.rejection_reasons


def test_cross_principal_and_duplicate_items_fail_closed() -> None:
    item = _item()
    cross = _item(principal_id="999")
    cross_result = project_principal_memex_readonly(
        principal_id="012", items=[item, cross], created_at=NOW
    )
    duplicate_result = project_principal_memex_readonly(
        principal_id="012", items=[item, item], created_at=NOW
    )
    assert "principal_memex_cross_principal_item" in cross_result.rejection_reasons
    assert "principal_memex_duplicate_item" in duplicate_result.rejection_reasons


def test_tampered_item_and_projection_digests_fail_closed() -> None:
    item = _item()
    tampered_item = replace(item, statement="Skip the audit.")
    item_result = project_principal_memex_readonly(
        principal_id="012", items=[tampered_item], created_at=NOW
    )
    valid = project_principal_memex_readonly(
        principal_id="012", items=[item], created_at=NOW
    ).projection
    assert valid is not None
    tampered_projection = valid.to_dict()
    tampered_projection["manifest_digest"] = "sha256:" + "2" * 64
    projection_result = rehydrate_principal_memex_projection(tampered_projection)
    assert "principal_memex_item_digest_mismatch" in item_result.rejection_reasons
    assert projection_result.rejection_reasons == (
        "principal_memex_projection_digest_or_boundary_mismatch",
    )


def test_serialized_acceptance_claim_and_unknown_fields_are_not_trusted() -> None:
    projection = project_principal_memex_readonly(
        principal_id="012", items=[_item()], created_at=NOW
    ).projection
    assert projection is not None
    forged = projection.to_dict()
    forged["accepted"] = True
    result = rehydrate_principal_memex_projection(forged)
    assert result.accepted is False
    assert result.rejection_reasons == (
        "principal_memex_projection_schema_fields_invalid",
    )


@pytest.mark.parametrize(
    "statement",
    [
        "api_key=not-allowed",
        "password=not-allowed",
        "private_key=material",
        "Bearer abc.def.ghi",
        "sk-forbiddenvalue",
    ],
)
def test_secret_shaped_material_is_rejected(statement: str) -> None:
    with pytest.raises(ValueError, match="principal_memex_secret_material_forbidden"):
        _item(statement=statement)


@pytest.mark.parametrize("field", ["principal_id", "source_revision"])
def test_secret_shaped_provenance_is_rejected(field: str) -> None:
    with pytest.raises(ValueError, match="principal_memex_secret_material_forbidden"):
        _item(**{field: "api_key=not-allowed"})


def test_no_foundup_or_authority_fields_exist_in_contract() -> None:
    projection = project_principal_memex_readonly(
        principal_id="012", items=[_item()], created_at=NOW
    ).projection
    assert projection is not None
    serialized = projection.to_dict()
    forbidden = {
        "foundup_id",
        "repository_id",
        "work_order_id",
        "allowed_paths",
        "worker_id",
        "merge_authority",
    }
    assert forbidden.isdisjoint(serialized)
    assert forbidden.isdisjoint(serialized["items"][0])


def test_naive_time_integer_boolean_and_oversized_projection_fail_closed() -> None:
    item = _item()
    naive = replace(item, created_at="2026-08-06T12:00:00")
    naive_result = project_principal_memex_readonly(
        principal_id="012", items=[naive], created_at=NOW
    )
    assert "principal_memex_created_at_invalid" in naive_result.rejection_reasons

    projection = project_principal_memex_readonly(
        principal_id="012", items=[item], created_at=NOW
    ).projection
    assert projection is not None
    forged = projection.to_dict()
    forged["no_work_authority_granted"] = 1
    assert rehydrate_principal_memex_projection(forged).rejection_reasons == (
        "principal_memex_projection_type_invalid",
    )

    oversized = project_principal_memex_readonly(
        principal_id="012", items=[item] * 129, created_at=NOW
    )
    assert "principal_memex_item_limit_exceeded" in oversized.rejection_reasons


@pytest.mark.parametrize("field", ["principal_id", "statement", "created_at"])
def test_item_builder_rejects_non_string_values(field: str) -> None:
    with pytest.raises(ValueError, match="principal_memex_item_type_invalid"):
        _item(**{field: None})


def test_serialized_projection_requires_exact_json_container_types() -> None:
    projection = project_principal_memex_readonly(
        principal_id="012", items=[_item()], created_at=NOW
    ).projection
    assert projection is not None

    tuple_ids = projection.to_dict()
    tuple_ids["item_ids"] = tuple(tuple_ids["item_ids"])
    assert rehydrate_principal_memex_projection(tuple_ids).rejection_reasons == (
        "principal_memex_projection_type_invalid",
    )

    numeric_source = projection.to_dict()
    numeric_source["source_receipt_ids"] = [1]
    assert rehydrate_principal_memex_projection(numeric_source).rejection_reasons == (
        "principal_memex_projection_type_invalid",
    )


@pytest.mark.parametrize("items", [None, "not-an-item-list", []])
def test_projection_rejects_malformed_item_containers(items: object) -> None:
    result = project_principal_memex_readonly(
        principal_id="012", items=items, created_at=NOW
    )
    assert result.accepted is False
    assert result.rejection_reasons == ("principal_memex_items_missing",)


def test_projection_rejects_hostile_and_oversized_containers_before_traversal() -> None:
    class HostileSequence(Sequence):
        def __getitem__(self, _index: int):
            raise AssertionError("hostile sequence traversed")

        def __len__(self) -> int:
            raise AssertionError("hostile sequence measured")

    hostile = project_principal_memex_readonly(
        principal_id="012", items=HostileSequence(), created_at=NOW
    )
    assert hostile.rejection_reasons == ("principal_memex_items_missing",)

    projection = project_principal_memex_readonly(
        principal_id="012", items=[_item()], created_at=NOW
    ).projection
    assert projection is not None
    oversized = projection.to_dict()
    oversized["items"] = [oversized["items"][0]] * 129
    oversized["item_ids"] = [projection.item_ids[0]] * 129
    assert rehydrate_principal_memex_projection(oversized).rejection_reasons == (
        "principal_memex_projection_type_invalid",
    )

    oversized_projection_mapping = {f"extra_{index}": index for index in range(50_000)}
    oversized_projection_mapping.update(projection.to_dict())
    assert rehydrate_principal_memex_projection(
        oversized_projection_mapping
    ).rejection_reasons == ("principal_memex_projection_schema_fields_invalid",)

    oversized_item_mapping = {f"extra_{index}": index for index in range(50_000)}
    oversized_item_mapping.update(_item().to_dict())
    bounded = project_principal_memex_readonly(
        principal_id="012", items=[oversized_item_mapping], created_at=NOW
    )
    assert bounded.rejection_reasons == (
        "principal_memex_item_schema_fields_invalid",
    )


def test_supersession_relationships_are_projection_coherent() -> None:
    old = _item(statement="Use one implementation pass.", retention_state="superseded")
    current = _item(
        statement="Audit before implementation.",
        source_revision="conversation:43",
        supersedes_item_id=old.item_id,
    )
    assert project_principal_memex_readonly(
        principal_id="012", items=[old, current], created_at=NOW
    ).accepted is True

    orphan = project_principal_memex_readonly(
        principal_id="012", items=[old], created_at=NOW
    )
    assert "principal_memex_supersession_target_count_invalid" in orphan.rejection_reasons

    missing_target = _item(supersedes_item_id="sha256:" + "9" * 64)
    missing = project_principal_memex_readonly(
        principal_id="012", items=[missing_target], created_at=NOW
    )
    assert "principal_memex_supersession_target_missing" in missing.rejection_reasons

    first = _item(statement="Implement before auditing.", retention_state="superseded")
    second = _item(
        statement="Audit and then implement.",
        source_revision="conversation:44",
        retention_state="superseded",
        supersedes_item_id=first.item_id,
    )
    third = _item(
        statement="Audit, refute-test, then implement.",
        source_revision="conversation:45",
        supersedes_item_id=second.item_id,
    )
    assert project_principal_memex_readonly(
        principal_id="012", items=[first, second, third], created_at=NOW
    ).accepted is True


def test_typed_projection_objects_enforce_boundary_invariants() -> None:
    projection = project_principal_memex_readonly(
        principal_id="012", items=[_item()], created_at=NOW
    ).projection
    assert projection is not None
    with pytest.raises(ValueError, match="principal_memex_projection_boundary_invalid"):
        replace(projection, runtime_admissible=True)
    with pytest.raises(ValueError, match="principal_memex_projection_result_invalid"):
        PrincipalMemexProjectionResult(True, PROJECTION_READY, None, ())

    forged_values = projection.to_dict()
    forged_values["items"] = tuple(projection.items)
    forged_values["item_ids"] = tuple(projection.item_ids)
    forged_values["source_receipt_ids"] = tuple(projection.source_receipt_ids)
    with pytest.raises(ValueError, match="principal_memex_projection_boundary_invalid"):
        PrincipalMemexProjection(**forged_values)

    class StatefulBool:
        def __bool__(self) -> bool:
            return False

    with pytest.raises(ValueError, match="principal_memex_projection_boundary_invalid"):
        replace(projection, runtime_admissible=StatefulBool())
    with pytest.raises(ValueError, match="principal_memex_projection_result_invalid"):
        PrincipalMemexProjectionResult(1, PROJECTION_READY, projection, ())


def test_private_factory_rejects_policy_invalid_projection_shapes() -> None:
    projection = project_principal_memex_readonly(
        principal_id="012", items=[_item()], created_at=NOW
    ).projection
    assert projection is not None

    orphan = _item(retention_state="superseded")
    with pytest.raises(ValueError, match="principal_memex_projection_boundary_invalid"):
        _construct_with_private_factory(projection, (orphan,))

    second_item = _item(statement="Keep scopes isolated.", source_revision="conversation:46")
    ordered = project_principal_memex_readonly(
        principal_id="012", items=[_item(), second_item], created_at=NOW
    ).projection
    assert ordered is not None
    reversed_items = tuple(reversed(ordered.items))
    with pytest.raises(ValueError, match="principal_memex_projection_boundary_invalid"):
        _construct_with_private_factory(ordered, reversed_items)


def test_private_factory_rejects_duplicates_and_invalid_timestamp() -> None:
    item = _item()
    projection = project_principal_memex_readonly(
        principal_id="012", items=[item], created_at=NOW
    ).projection
    assert projection is not None

    with pytest.raises(ValueError, match="principal_memex_projection_boundary_invalid"):
        _construct_with_private_factory(projection, (item, item))
    with pytest.raises(ValueError, match="principal_memex_projection_boundary_invalid"):
        _construct_with_private_factory(
            projection, (item,), created_at="not-a-time"
        )


def test_private_factory_bounds_identifier_tuples_before_traversal() -> None:
    item = _item()
    projection = project_principal_memex_readonly(
        principal_id="012", items=[item], created_at=NOW
    ).projection
    assert projection is not None
    values = _private_factory_values(projection, (item,))
    values["item_ids"] = tuple("sha256:" + "a" * 64 for _ in range(50_000))
    with pytest.raises(ValueError, match="principal_memex_projection_boundary_invalid"):
        _create_principal_memex_projection(
            **values,
            projection_id="sha256:" + "b" * 64,
            items=(item,),
        )

    values = _private_factory_values(projection, (item,))
    values["source_receipt_ids"] = tuple(
        "sha256:" + "c" * 64 for _ in range(50_000)
    )
    with pytest.raises(ValueError, match="principal_memex_projection_boundary_invalid"):
        _create_principal_memex_projection(
            **values,
            projection_id="sha256:" + "d" * 64,
            items=(item,),
        )
