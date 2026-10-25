"""Produce the first Little Shrew episode locally with no account or paid API.

Run by file path with --output-dir pointing to a NEW directory. Local authoring
only: never fabricates WRE authority or independent media-review acceptance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]


def _local_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def produce_preview(output_dir, *, preset="draft"):
    if preset not in ("draft", "final"):
        raise ValueError("preset must be draft or final")
    # Avoid the legacy Shorts package initializer and its optional cloud SDKs.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from modules.foundups.kids_episodes.src.little_shrew import build_pilot, SERIES_ROOT
    animation = _local_module("shrew_animation", Path(__file__).with_name("little_shrew_animation.py"))
    renderer = _local_module("shrew_editor", Path(__file__).with_name("kids_episode.py"))
    plan = build_pilot(request_id="little-shrew-local-pilot", supported_durations=(5,))
    episode = plan["episodes"][0]
    def verify_sources():
        for ref in plan["bible"]["reference_assets"]:
            if hashlib.sha256((ROOT / ref["path"]).read_bytes()).hexdigest() != ref["sha256"]:
                raise RuntimeError("Series references changed during local authoring")
    verify_sources()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    scene = animation.ShrewScene(SERIES_ROOT / "character.svg")
    clips = []
    for index, shot in enumerate(episode["shots"]):
        path = output / f"{shot['beat_id']}.mp4"
        animation.render_shot(scene, index, path)
        clips.append({"path": path.name, "start": 0, "duration": 5})
    cues = animation.compose_audio(output / "original-score.wav")
    spec = {"schema_version": 1, "duration_seconds": 15, "preset": preset,
            "orientation": "landscape", "clips": clips, "captions": cues,
            "music": {"path": "original-score.wav", "rights_evidence":
                      "Original code-composed instrumental and synthesized foley; no samples or lyrics."},
            **{key: episode[key] for key in ("title", "learning_objective", "activity")},
            "language": plan["language"], "age_band": plan["age_band"]}
    (output / "episode.json").write_text(json.dumps(spec, indent=2) + "\n")
    result = renderer.render_episode(spec, output / "little-shrew-episode-01.mp4", base_dir=output)
    verify_sources()
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in output.iterdir() if p.is_file()}
    record = {"schema": "kids.local_preview.v1", "created_at": datetime.now(timezone.utc).isoformat(),
              "status": "rendered_unreviewed", "execution_plane": "local_media_authoring",
              "method": "deterministic_2d_shared_svg_rig", "paid_calls": 0,
              "project_id": plan["project_id"], "episode_id": episode["episode_id"],
              "plan_digest": plan["plan_digest"],
              "editorial_revision": "012 revision 2: two parents, three equal-sized children; early tremor wakes rightmost child only; faster root approach; others stay asleep",
              "plan_relationship": "Local editorial override of first three beats; original nine-beat plan retained as source, not claimed to describe this revision exactly", "source_refs": plan["bible"]["reference_assets"],
              "source_code": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (Path(__file__), Path(animation.__file__), Path(renderer.__file__))},
              "assets_sha256": hashes, "result": result,
              "limits": ["First episode only; not a whole-story review",
                         "960x540 authored frames; final export is upscaled",
                         "No WRE activation, provider access, autonomous promotion or publication"]}
    (output / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preset", choices=("draft", "final"), default="draft")
    args = parser.parse_args()
    print(json.dumps(produce_preview(args.output_dir, preset=args.preset), indent=2))
