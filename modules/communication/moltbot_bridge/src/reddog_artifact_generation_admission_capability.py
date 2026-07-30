"""One-shot authority and provider admissions for artifact generation."""

from .reddog_artifact_generation_authority_capability import (
    ArtifactGenerationAuthorityCapability,
    _issue_artifact_generation_authority as _authority_issue,
    consume_artifact_generation_authority,
)
from .reddog_artifact_generation_model_capability import (
    ArtifactGenerationModelCapability,
    _issue_artifact_generation_model as _model_issue,
    consume_artifact_generation_model,
    discard_artifact_generation_model,
)

_issue_artifact_generation_authority = _authority_issue
_issue_artifact_generation_model = _model_issue

__all__ = [
    "ArtifactGenerationAuthorityCapability",
    "ArtifactGenerationModelCapability",
    "consume_artifact_generation_authority",
    "consume_artifact_generation_model",
    "discard_artifact_generation_model",
]
