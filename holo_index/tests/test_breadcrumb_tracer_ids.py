#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression coverage for adaptive-learning runtime identifiers."""

from holo_index.adaptive_learning.breadcrumb_tracer import _new_runtime_id


def test_new_runtime_id_is_collision_resistant() -> None:
    seen = {_new_runtime_id("coord") for _ in range(50)}
    assert len(seen) == 50
    assert all(identifier.startswith("coord_") for identifier in seen)
