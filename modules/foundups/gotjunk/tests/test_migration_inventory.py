"""Pure offline migration-inventory acceptance; no Firebase or browser runtime."""

from modules.foundups.gotjunk.src.migration_inventory import plan_inventory


def row(item="item-1", *, owner="alice", digest="a" * 64,
        status="listed", system="gotjunk_firestore", foundup="gotjunk_001"):
    return {"source_system": system, "foundup_id": foundup,
            "source_item_id": item, "owner_uid": owner,
            "content_sha256": digest, "status": status}


def test_dryrun_is_order_independent_and_idempotent():
    a, b = row(), row("item-2", digest="b" * 64, status="draft")
    one = plan_inventory([a, b, a])
    two = plan_inventory([b, a, a])
    assert one == two
    assert one["unique_candidates"] == 2
    assert one["duplicate_rows"] == 1
    assert one["writes"] == 0
    assert one["dry_run"] is True and one["cutover_authorized"] is False
    assert one["source_digests_verified"] is False


def test_conflicting_owner_digest_or_state_blocks_entire_item():
    summary = plan_inventory([row(), row(owner="mallory"), row(digest="c" * 64)])
    assert summary["unique_candidates"] == 0
    assert summary["blocked_rows"] == 3
    assert summary["blocked_reasons"]["owner_digest_or_state_conflict"] == 3


def test_private_fields_and_cross_tenant_are_blocked():
    with_location = {**row(), "latitude": 35.6}
    with_media = {**row(), "blobStorageUrl": "private"}
    summary = plan_inventory([
        with_location, with_media, row(system="other_marketplace"),
        row(foundup="getk_001"), row(owner="", item="item-9"),
        row(digest="bad", item="item-10"),
        row(status="unrecognized", item="item-11"),
    ])
    assert summary["unique_candidates"] == 0
    assert summary["blocked_rows"] == 7


def test_report_has_no_source_ids_uids_or_media_urls():
    summary = plan_inventory([row("private-id", owner="private-owner")])
    rendered = str(summary)
    for secret in ("private-id", "private-owner", "latitude", "blobStorageUrl"):
        assert secret not in rendered


def test_empty_inventory_requires_no_data_or_cloud_service():
    result = plan_inventory([])
    assert result["input_rows"] == 0
    assert result["writes"] == 0
    assert result["cutover_authorized"] is False
