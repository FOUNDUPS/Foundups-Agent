"""Evidence-grounded metadata proposal; legacy skill name retained.

No model invocation: consumes an existing video-matched analyzer artifact.
"""
import json
from dataclasses import dataclass, field
from typing import Dict, List

from ...src.content_generator import validated_video_evidence
from ...src.content_generator import generate_clickbait_title_from_index


@dataclass
class SkillContext:
    original_title: str
    original_description: str = ""
    video_duration: int = 50
    content_hints: List[str] = field(default_factory=list)
    emotional_priority: str = "outrage"  # Compatibility only; never evidence.
    video_id: str = ""
    index_json: dict = field(default_factory=dict)
    preserve_metadata: bool = False


@dataclass
class SkillResult:
    enhanced_title: str
    enhanced_description: str
    original_title: str
    original_description: str
    hook_type: str
    confidence: float
    patterns_executed: Dict[str, bool] = field(default_factory=dict)


class FFCPLNTitleEnhanceSkill:
    def __init__(self):
        self.name = "ffcpln_title_enhance"
        self.version = "0.6.0"
        self.intent_type = "GENERATION"
        self.primary_agent = "qwen"

    def execute(self, context: SkillContext) -> SkillResult:
        evidence = validated_video_evidence(context.index_json, context.video_id)
        title, description = context.original_title, context.original_description
        eligible = evidence is not None and not context.preserve_metadata
        if eligible:
            title = generate_clickbait_title_from_index(
                original_title=title, index_json=context.index_json, video_id=context.video_id,
            )
            # Reuse the same deterministic composition/preservation policy.
            context_text = f"Video context ({evidence['modality']}):\n" + evidence["text"][:1000]
            from ...src.index_weave import inject_context_into_description
            description = inject_context_into_description(
                base_description=context.original_description, context_block=context_text)
            provenance = {k: v for k, v in evidence.items() if k != "text"}
            marker = "\n\nM2M_CONTEXT\n" + json.dumps(provenance, ensure_ascii=False, separators=(",", ":"))
            if marker not in description:
                description += marker
            if len(title) > 100 or len(description) > 5000:
                title, description = context.original_title, context.original_description
                eligible = False
        return SkillResult(
            title, description, context.original_title, context.original_description,
            "evidence_summary" if eligible else "preserved", 0.0,
            {"evidence_validated": evidence is not None,
             "metadata_changed": eligible, "performance_measured": False},
        )

    def _analyze_content(self, context: SkillContext) -> str:
        """Duration, channel and inherited title cannot establish music."""
        if validated_video_evidence(context.index_json, context.video_id) is None:
            return "unknown"
        return "analyzed"  # No fabricated music classification.


def enhance_title_with_skill(original_title: str, emotional_priority: str = "outrage") -> str:
    # Legacy calls supply no clip evidence, so preserve instead of inventing.
    return original_title


def enhance_description_with_skill(original_desc: str) -> str:
    return original_desc
