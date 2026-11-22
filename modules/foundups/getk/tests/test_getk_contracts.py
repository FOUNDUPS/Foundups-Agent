#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GetK PoC contract tests -- pure, no network, no external imports."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.foundups.getk.src.getk_contracts import (
    ALLOWED_TOKEN_USES,
    FORBIDDEN_TOKEN_USES,
    CostEstimatePacket,
    DeferredAuctionLookupProvider,
    GetKListingPacket,
    MediaRef,
    StakeholderBidGate,
    TokenUtilityError,
    TokenUtilityRules,
    VehicleCapturePacket,
)

CONTRACTS_SRC = (
    Path(__file__).resolve().parents[1] / "src" / "getk_contracts.py"
)


# --- Stakeholder gate: public browse for all; bid requires a stakeholder ----

def test_public_browse_allowed_for_non_stakeholder():
    gate = StakeholderBidGate()
    assert gate.allows("browse", is_stakeholder=False) is True
    assert gate.allows("view", is_stakeholder=False) is True


def test_bid_blocked_for_non_stakeholder():
    gate = StakeholderBidGate()
    assert gate.allows("bid", is_stakeholder=False) is False
    assert gate.allows("offer", is_stakeholder=False) is False


def test_bid_allowed_for_stakeholder():
    gate = StakeholderBidGate()
    assert gate.allows("bid", is_stakeholder=True) is True


def test_unknown_action_denied_fail_closed():
    gate = StakeholderBidGate()
    assert gate.allows("delete_everything", is_stakeholder=True) is False


# --- Token utility rules: not bid, not ownership, not payment -----------------

@pytest.mark.parametrize("use", ["vehicle_bid", "vehicle_ownership", "payment_for_vehicle"])
def test_token_rejects_bid_ownership_payment(use):
    rules = TokenUtilityRules()
    with pytest.raises(TokenUtilityError):
        rules.validate_use(use)


def test_token_allows_internal_fee_offset_only():
    rules = TokenUtilityRules()
    assert rules.validate_use("offset_internal_service_fee") is True
    with pytest.raises(TokenUtilityError):
        rules.validate_use("buy_groceries")


def test_token_use_sets_are_disjoint():
    assert ALLOWED_TOKEN_USES.isdisjoint(FORBIDDEN_TOKEN_USES)


# --- Cost estimate: estimate only, never authoritative ------------------------

def test_cost_estimate_is_not_authoritative():
    est = CostEstimatePacket(item_id="k1", estimated_low=1000.0, estimated_high=2000.0)
    assert est.is_authoritative is False
    assert "Estimate only" in est.disclaimer


def test_cost_estimate_cannot_be_promoted_authoritative():
    with pytest.raises(ValueError):
        CostEstimatePacket(
            item_id="k1", estimated_low=1000.0, estimated_high=2000.0,
            is_authoritative=True,
        )


def test_cost_estimate_range_validated():
    with pytest.raises(ValueError):
        CostEstimatePacket(item_id="k1", estimated_low=2000.0, estimated_high=1000.0)


# --- Auction lookup: mocked / deferred (no network) ---------------------------

def test_auction_lookup_is_deferred_and_raises():
    provider = DeferredAuctionLookupProvider()
    assert provider.deferred is True
    with pytest.raises(NotImplementedError):
        provider.lookup("kei truck 1990")


# --- Capture packet: refs not bodies; auction + regulatory deferred -----------

def test_capture_packet_uses_media_refs_not_bodies():
    cap = VehicleCapturePacket(
        item_id="k1",
        media_refs=[MediaRef(ref="s3://bucket/k1/front.jpg", sha256="0" * 64)],
        declared_fields={"year": "1991", "odometer_km": "84000"},
    )
    assert cap.category == "kei_truck"
    assert cap.auction_lookup == "deferred"
    assert cap.regulatory_status == "deferred"
    assert cap.media_refs[0].ref.startswith("s3://")
    # No media body field exists on the ref (pointer-only).
    assert not hasattr(cap.media_refs[0], "body")


def test_capture_rejects_non_deferred_auction_or_regulatory():
    with pytest.raises(ValueError):
        VehicleCapturePacket(item_id="k1", auction_lookup="live_result")
    with pytest.raises(ValueError):
        VehicleCapturePacket(item_id="k1", regulatory_status="legal_in_TX")


def test_listing_from_capture_public_browse_stakeholder_gated():
    cap = VehicleCapturePacket(item_id="k1")
    listing = GetKListingPacket.from_capture("L1", cap, title="1991 Kei Truck")
    assert listing.visibility == "public_browse"
    assert listing.stakeholder_required_for_bid is True
    assert listing.item_id == "k1"


# --- AST: the contracts module is pure (no network / subprocess / file IO) ----

def test_contracts_module_is_pure_no_network_no_io():
    tree = ast.parse(CONTRACTS_SRC.read_text(encoding="utf-8"))

    banned_modules = {
        "subprocess", "socket", "ssl", "urllib", "requests", "httpx", "http",
        "ftplib", "ctypes", "importlib", "multiprocessing", "os", "sys",
        "shutil", "pathlib", "pickle", "marshal",
    }
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imported.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    bad = imported & banned_modules
    assert not bad, f"contracts module imports banned modules: {bad}"

    banned_calls = {"open", "eval", "exec", "compile", "__import__", "input"}
    banned_attrs = {
        "system", "popen", "Popen", "run", "call", "urlopen", "connect",
        "request", "get", "post", "write", "write_text", "write_bytes",
    }
    name_bad, attr_bad = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in banned_calls:
                name_bad.append(f.id)
            elif isinstance(f, ast.Attribute) and f.attr in banned_attrs:
                attr_bad.append(f.attr)
    assert not name_bad, f"banned builtin calls: {name_bad}"
    assert not attr_bad, f"banned attr calls: {attr_bad}"
