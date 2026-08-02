"""Canonical artifact-provider mode vocabulary for the resident queue."""

RUNTIME_MODE_FOUNDUPS_FUSION = "foundups_fusion"
RUNTIME_MODE_OPENCLAW_GATEWAY = "openclaw_gateway"
RUNTIME_MODE_HERMES_API = "hermes_api"

ARTIFACT_GENERATOR_MODES = frozenset(
    {
        RUNTIME_MODE_FOUNDUPS_FUSION,
        RUNTIME_MODE_OPENCLAW_GATEWAY,
        RUNTIME_MODE_HERMES_API,
    }
)
PRODUCTION_ARTIFACT_GENERATOR_MODES = frozenset(
    {RUNTIME_MODE_FOUNDUPS_FUSION, RUNTIME_MODE_OPENCLAW_GATEWAY}
)


def normalize_artifact_generator_mode(value: object) -> str:
    """Normalize aliases while rejecting unrecognized provider names."""

    normalized = str(value or "").strip().lower()
    if normalized == "fusion":
        normalized = RUNTIME_MODE_FOUNDUPS_FUSION
    return normalized if normalized in ARTIFACT_GENERATOR_MODES else ""


def production_artifact_generator_mode(value: object) -> str:
    """Return only modes whose complete production trust boundary exists."""
    normalized = normalize_artifact_generator_mode(value)
    return normalized if normalized in PRODUCTION_ARTIFACT_GENERATOR_MODES else ""


__all__ = [
    "ARTIFACT_GENERATOR_MODES",
    "PRODUCTION_ARTIFACT_GENERATOR_MODES",
    "RUNTIME_MODE_FOUNDUPS_FUSION",
    "RUNTIME_MODE_HERMES_API",
    "RUNTIME_MODE_OPENCLAW_GATEWAY",
    "normalize_artifact_generator_mode",
    "production_artifact_generator_mode",
]
