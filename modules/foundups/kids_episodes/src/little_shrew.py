"""Local, source-grounded Little Shrew preset for the existing story controller.

Compiles data only. It neither admits execution nor calls a generation provider.
Reference hashes describe design inputs, not proof a provider used those inputs.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from .story_pipeline import compile_plan

SERIES_ROOT = Path(__file__).resolve().parents[1] / "series" / "little_shrew"


def build_pilot(*, request_id: str, supported_durations=(4, 6, 8)) -> dict:
    """Compile nine five-second beats into three linked 15-second episodes.

    The shortest admitted provider duration >= five is selected, then trimmed.
    Caller supplies actual provider capabilities; defaults are illustrative.
    Paths are repository-relative, never host-specific workspace identities.
    """
    durations = list(supported_durations)
    if not durations or len(durations) > 12 or any(
        isinstance(x, bool) or not isinstance(x, (int, float))
        or not math.isfinite(x) or not 0 < x <= 120 for x in durations
    ):
        raise ValueError("Invalid provider durations")
    candidates = [x for x in durations if x >= 5]
    if not candidates:
        raise ValueError("Little Shrew requires a provider shot of at least five seconds")
    generation_seconds = min(candidates)
    profile = json.loads((SERIES_ROOT / "pilot.json").read_text(encoding="utf-8"))
    beats = profile["beats"]
    if len(beats) != 9 or len(profile["segments"]) != 3:
        raise ValueError("Little Shrew requires nine beats and three segments")
    refs = [{"path": f"modules/foundups/kids_episodes/series/little_shrew/{name}",
             "sha256": hashlib.sha256((SERIES_ROOT / name).read_bytes()).hexdigest()}
            for name in ("pilot.json", "character.svg", "storyboard.svg")]
    # Adapted narrative is the immutable source for this preset. The Google Doc
    # URL and editorial decisions remain provenance, not executable instructions.
    paragraphs = ["\n".join(b["action"] for b in beats[i:i + 3]) + "\n"
                  for i in range(0, 9, 3)]
    raw_story = "".join(paragraphs)
    episodes = []
    offset = 0
    for index, segment in enumerate(profile["segments"]):
        group = beats[index * 3:index * 3 + 3]
        episode = dict(segment, source_start=offset, source_end=offset + len(paragraphs[index]))
        episode["shots"] = [{
            "prompt": f"{profile['bible']['visual_style']}\n{profile['bible']['characters']}\n"
                      f"Beat {beat['id']}: {beat['action']} Expression: {beat['expression']}. "
                      "No speech. Preserve the supplied shared character design. No frightening impact.",
            "generation_seconds": generation_seconds, "edit_seconds": 5,
            "beat_id": beat["id"], "expression": beat["expression"], "reference_assets": refs,
        } for beat in group]
        episode["captions"] = [{"start": i * 5, "end": (i + 1) * 5,
                                "text": beat["sound_caption"]} for i, beat in enumerate(group)]
        episode["music_brief"] = profile["music"]["brief"]
        episodes.append(episode)
        offset = episode["source_end"]
    bible = dict(profile["bible"], series_id=profile["series_id"], source=profile["source"],
                 reference_assets=refs, palette=profile["palette"], music=profile["music"])
    return compile_plan(raw_story, {"title": profile["title"], "age_band": profile["age_band"],
                        "language": profile["language"], "bible": bible, "episodes": episodes},
                        request_id=request_id, supported_durations=durations)
