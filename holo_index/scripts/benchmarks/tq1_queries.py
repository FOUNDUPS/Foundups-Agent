# -*- coding: utf-8 -*-
"""TQ1 benchmark query set — 30 representative HoloIndex queries.

Covers the breadth of HoloIndex domains called out in the TQ1 brief:
WSP protocols, SKILLz, pfMALL, ai_overseer, preflight_resolution,
HoloIndex internals, FoundUps docs, module paths, symbols.

This list is the *only* query set used for TQ1 benchmarks so results are
comparable across backends. Do not edit without re-running all baselines.
"""
from __future__ import annotations

TQ1_QUERIES: list[str] = [
    # WSP protocols
    "WSP 97 truth distinction protocol",
    "WSP 50 pre-action verification",
    "WSP 22 ModLog update requirements",
    "WSP 87 size limits for modules",
    "WSP 49 module structure conventions",
    # SKILLz
    "skill registry loader orchestration",
    "SKILLz compliance frontmatter requirements",
    "orphan capability scanner",
    # pfMALL / FoundUps
    "pfMALL data isolation model",
    "FoundUp agent market CABR engine",
    "FAM DAEmon heartbeat and breadcrumbs",
    # ai_overseer
    "ai_overseer M2M compression sentinel",
    "ai overseer role detection",
    # preflight / startup
    "preflight resolution ironclaw preflight",
    "HOLO_SKIP_MODEL offline bootstrap",
    # HoloIndex internals
    "HoloIndex retrieval_mode lexical fallback",
    "ChromaDB persistent client vector collections",
    "sentence transformer model load timeout",
    "HOLO_USE_TURBOQUANT environment switch",
    "embedding_backend search metadata",
    # FoundUps / antifaFM / broadcaster
    "antifaFM broadcaster 24/7 headless launch",
    "YouTube stream resolver livestream detection",
    # Module paths / symbols
    "modules/ai_intelligence/agent_permissions",
    "AgentPermissionManager.request_permission",
    "modules/platform_integration/youtube_auth",
    "autonomous_refactoring.py WSP 77",
    # Cross-domain phrasing
    "how does 0102 recall patterns from 0201",
    "token budget for DAE pattern memory",
    "zen coding principle code is remembered",
    "pytest HOLO_SKIP_MODEL lexical-only tests",
]

assert len(TQ1_QUERIES) == 30, f"Expected 30 queries, got {len(TQ1_QUERIES)}"
