"""No-network production state-machine contracts with fake injected effects."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("kids_story_pipeline", Path(__file__).parents[1] / "src/story_pipeline.py")
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


def draft():
    return {"title": "Three seeds", "age_band": "3-6", "language": "en",
            "bible": {"characters": "Pip, an original blue bird", "world": "A garden", "visual_style": "Soft clay shapes"},
            "episodes": [{"title": "Count seeds", "source_start": 0, "source_end": 12,
                "learning_objective": "Count three", "activity": "Count aloud", "start_state": "Pip has seeds", "end_state": "Seeds counted",
                "shots": [{"prompt": "Show one seed", "generation_seconds": 6, "edit_seconds": 5} for _ in range(3)],
                "captions": [{"start": 0, "end": 15, "text": "One, two, three seeds!"}]}]}


def plan():
    return m.compile_plan("Three seeds.", draft(), request_id="request-1")


def callbacks(root, *, failures=0):
    calls = []
    count = {"reviews": 0}
    def authorize(stage, context):
        calls.append(("admit", stage))
        return True
    def shot(shot, context):
        calls.append(("shot", shot["shot_id"]))
        p = Path(context["output_dir"]) / (shot["shot_id"] + ".mp4")
        p.write_bytes(b"fake source video")
        return {"path": str(p), "rights_evidence": "test original"}
    def audio(episode, context):
        p = Path(context["output_dir"]) / "music.wav"
        p.write_bytes(b"fake original audio")
        return {"music": {"path": str(p), "rights_evidence": "test original"}, "captions": episode["captions"]}
    def render(spec, output_path, *, base_dir):
        output_path.write_bytes(b"fake render")
        output_path.with_suffix(".srt").write_text("caption")
        return {"video_path": str(output_path), "captions_path": str(output_path.with_suffix(".srt"))}
    def review(result, episode, context):
        count["reviews"] += 1
        calls.append(("review", context["artifact_sha256"]))
        assert context["assets"] and context["final_render_captions"]
        return {"artifact_sha256": context["artifact_sha256"], "reviewer_id": "independent",
                "checks": {key: count["reviews"] > failures for key in m.CHECKS}, "feedback": "Clear counted sequence"}
    return dict(authorize=authorize, generate_shot=shot, produce_audio=audio, render_episode=render,
                review_episode=review, producer_id="author", reviewer_id="independent", execution_binding_digest="a"*64), calls


def test_stable_ids_preserve_raw_story_and_terms():
    a = plan()
    assert a == plan()
    assert a["raw_story"] == "Three seeds."
    assert a["episodes"][0]["shots"][0]["generation_seconds"] == 6
    assert len({s["shot_id"] for s in a["episodes"][0]["shots"]}) == 3
    p = draft(); p["episodes"][0]["source_end"] = 10
    corrected = m.compile_plan("E-D-U-I-T.", p, request_id="speech", confirmed_terms={"E-D-U-I-T": "EDUIT"})
    assert corrected["raw_story"] == "E-D-U-I-T."
    assert corrected["confirmed_terms"] == {"E-D-U-I-T": "EDUIT"}


@pytest.mark.parametrize("mutation", [
    lambda d: d["episodes"][0].update(source_start=1),
    lambda d: d["episodes"][0].update(source_end=11),
    lambda d: d["episodes"][0]["shots"][0].update(generation_seconds=5),
    lambda d: d["episodes"][0]["shots"][0].update(edit_seconds=4),
    lambda d: d["episodes"][0].update(captions=[{"start": 0, "end": 16, "text": "x"}]),
    lambda d: d["bible"].update(characters=""),
])
def test_reject_invalid_model_plan(mutation):
    data = draft(); mutation(data)
    with pytest.raises(ValueError):
        m.compile_plan("Three seeds.", data, request_id="r")


def test_linked_spans_and_continuity():
    data = draft()
    second = copy.deepcopy(data["episodes"][0])
    second.update(source_start=12, source_end=24, start_state="Seeds counted")
    data["episodes"].append(second)
    p = m.compile_plan("Three seeds.Three seeds.", data, request_id="r")
    assert p["episodes"][1]["previous_episode_id"] == p["episodes"][0]["episode_id"]
    second["start_state"] = "Unrelated place"
    with pytest.raises(ValueError, match="continuity"):
        m.compile_plan("Three seeds.Three seeds.", data, request_id="r")


def test_planning_denial_prevents_model_call():
    with pytest.raises(PermissionError):
        m.plan_story("Three seeds.", lambda _r: pytest.fail("planner invoked"), authorize=lambda *_: False, request_id="r")


def test_reviewed_resume_does_not_regenerate_but_rechecks(tmp_path):
    kw, calls = callbacks(tmp_path)
    result = m.run_story(plan(), tmp_path, **kw)
    assert result["status"] == "episodes_reviewed_assembly_pending"
    assert sum(c[0] == "shot" for c in calls) == 3
    m.run_story(plan(), tmp_path, **kw)
    assert sum(c[0] == "shot" for c in calls) == 3
    assert sum(c[0] == "review" for c in calls) == 2


def test_failure_retries_are_bounded(tmp_path):
    kw, calls = callbacks(tmp_path, failures=10)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        m.run_story(plan(), tmp_path, **kw)
    assert sum(c[0] == "shot" for c in calls) == 6
    with pytest.raises(RuntimeError, match="budget exhausted"):
        m.run_story(plan(), tmp_path, **kw)
    assert sum(c[0] == "shot" for c in calls) == 6


def test_retry_feedback_and_recovery(tmp_path):
    kw, calls = callbacks(tmp_path, failures=1)
    assert m.run_story(plan(), tmp_path, **kw)["status"] == "episodes_reviewed_assembly_pending"
    assert sum(c[0] == "shot" for c in calls) == 6


def test_interrupted_effect_is_not_automatically_replayed(tmp_path):
    kw, calls = callbacks(tmp_path)
    def fail(*_):
        raise RuntimeError("provider timeout, result unknown")
    kw["generate_shot"] = fail
    with pytest.raises(RuntimeError, match="provider timeout"):
        m.run_story(plan(), tmp_path, **kw)
    kw["generate_shot"] = lambda *_: pytest.fail("replayed uncertain effect")
    with pytest.raises(RuntimeError, match="reconciliation"):
        m.run_story(plan(), tmp_path, **kw)


def test_changed_artifact_or_runtime_blocks_resume(tmp_path):
    kw, _ = callbacks(tmp_path)
    result = m.run_story(plan(), tmp_path, **kw)
    other = dict(kw, execution_binding_digest="b"*64)
    with pytest.raises(ValueError, match="execution binding"):
        m.run_story(plan(), tmp_path, **other)
    Path(result["episodes"][0]["video_path"]).write_bytes(b"modified")
    with pytest.raises(ValueError, match="artifact changed"):
        m.run_story(plan(), tmp_path, **kw)


def test_review_missing_check_never_approves(tmp_path):
    kw, _ = callbacks(tmp_path)
    kw["review_episode"] = lambda result, ep, context: {"artifact_sha256": context["artifact_sha256"],
        "reviewer_id": "independent", "checks": {"education": True}, "feedback": "good"}
    with pytest.raises(ValueError, match="all quality checks"):
        m.run_story(plan(), tmp_path, **kw)


def test_self_review_rejected_before_effects(tmp_path):
    kw, calls = callbacks(tmp_path)
    kw["reviewer_id"] = "author"
    with pytest.raises(ValueError, match="sole reviewer"):
        m.run_story(plan(), tmp_path, **kw)
    assert not calls


def test_changed_plan_rejected(tmp_path):
    kw, calls = callbacks(tmp_path)
    p = plan(); p["episodes"][0]["shots"][0]["prompt"] = "different"
    with pytest.raises(ValueError, match="modified"):
        m.run_story(p, tmp_path, **kw)
    assert not calls


def test_assembly_preserves_order_and_is_not_final_review(tmp_path):
    kw, _ = callbacks(tmp_path)
    def assemble(paths, output):
        assert len(paths) == 1
        output.write_bytes(b"joined")
        return output
    result = m.run_story(plan(), tmp_path, assemble_story=assemble, **kw)
    assert result["status"] == "assembled_unreviewed"
    assert result["story_video"]["sha256"]


def test_full_story_review_requires_actual_join_check(tmp_path):
    kw, _ = callbacks(tmp_path)
    def assemble(paths, output):
        output.write_bytes(b"joined")
        return {"video_path": str(output), "status": "assembled_unreviewed"}
    def final_review(artifact, plan, context):
        return {"artifact_sha256": context["artifact_sha256"], "reviewer_id": "independent",
                "checks": {key: True for key in (*m.CHECKS, "joins")}, "feedback": "Joins and story checked"}
    result = m.run_story(plan(), tmp_path, assemble_story=assemble, review_story=final_review, **kw)
    assert result["status"] == "story_reviewed"
    def absent_join(artifact, plan, context):
        review = final_review(artifact, plan, context); del review["checks"]["joins"]
        return review
    with pytest.raises(ValueError, match="joins"):
        m.run_story(plan(), tmp_path, assemble_story=assemble, review_story=absent_join, **kw)


def test_invalid_correction_preflight_prevents_paid_planner():
    with pytest.raises(ValueError, match="Correction source"):
        m.plan_story("Three seeds.", lambda _r: pytest.fail("planner invoked"), authorize=lambda *_: True,
                     request_id="r", confirmed_terms={"not present": "EDUIT"})


def test_review_receives_original_source_and_audience(tmp_path):
    kw, _ = callbacks(tmp_path)
    original_review = kw["review_episode"]
    def review(result, episode, context):
        assert context["raw_story"] == context["source_excerpt"] == "Three seeds."
        assert context["age_band"] == "3-6" and context["language"] == "en"
        assert context["confirmed_terms"] == {}
        return original_review(result, episode, context)
    kw["review_episode"] = review
    m.run_story(plan(), tmp_path, **kw)


@pytest.mark.parametrize("target", ["video_path", "captions_path", "asset"])
def test_reviewer_cannot_mutate_approved_bytes(tmp_path, target):
    kw, _ = callbacks(tmp_path)
    original_review = kw["review_episode"]
    def review(result, episode, context):
        verdict = original_review(result, episode, context)
        path = context["assets"][0]["path"] if target == "asset" else result[target]
        Path(path).write_bytes(b"changed while reviewing")
        return verdict
    kw["review_episode"] = review
    with pytest.raises(ValueError, match="artifact changed"):
        m.run_story(plan(), tmp_path, **kw)


def test_final_reviewer_cannot_mutate_story(tmp_path):
    kw, _ = callbacks(tmp_path)
    def assemble(paths, output):
        output.write_bytes(b"joined"); return output
    def review(artifact, plan, context):
        Path(artifact["path"]).write_bytes(b"changed final")
        return {"artifact_sha256": context["artifact_sha256"], "reviewer_id": "independent",
                "checks": {key: True for key in (*m.CHECKS, "joins")}, "feedback": "old bytes"}
    with pytest.raises(ValueError, match="artifact changed"):
        m.run_story(plan(), tmp_path, assemble_story=assemble, review_story=review, **kw)


def test_predictable_checkpoint_temp_symlink_not_followed(tmp_path):
    kw, _ = callbacks(tmp_path)
    outside = tmp_path.parent / (tmp_path.name + "-outside.txt")
    outside.write_text("keep")
    link = (tmp_path / f"{plan()['project_id']}.checkpoint.json").with_suffix(".tmp")
    link.symlink_to(outside)
    m.run_story(plan(), tmp_path, **kw)
    assert outside.read_text() == "keep"
    assert link.is_symlink()


def test_checkpoint_symlink_rejected_before_read(tmp_path):
    kw, calls = callbacks(tmp_path)
    outside = tmp_path.parent / (tmp_path.name + "-outside.json")
    outside.write_text("private content")
    (tmp_path / f"{plan()['project_id']}.checkpoint.json").symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        m.run_story(plan(), tmp_path, **kw)
    assert not calls


def test_planner_duration_iterator_normalized_before_call():
    p = m.plan_story("Three seeds.", lambda _r: draft(), authorize=lambda *_: True, request_id="r",
                     supported_durations=(d for d in [4, 6, 8]))
    assert p["supported_durations"] == [4.0, 6.0, 8.0]


def test_later_episode_reviewer_cannot_mutate_previous_episode(tmp_path):
    kw, _ = callbacks(tmp_path)
    data = draft(); second = copy.deepcopy(data["episodes"][0])
    second.update(source_start=12, source_end=24, start_state="Seeds counted")
    data["episodes"].append(second)
    compiled = m.compile_plan("Three seeds.Three seeds.", data, request_id="two")
    original = kw["review_episode"]
    def review(result, episode, context):
        verdict = original(result, episode, context)
        if context["previous_episode"]:
            Path(context["previous_episode"]["video_path"]).write_bytes(b"changed previous")
        return verdict
    kw["review_episode"] = review
    with pytest.raises(ValueError, match="artifact changed"):
        m.run_story(compiled, tmp_path, **kw)


def test_assembler_cannot_mutate_accepted_inputs(tmp_path):
    kw, _ = callbacks(tmp_path)
    def assemble(paths, output):
        Path(paths[0]).write_bytes(b"changed source")
        output.write_bytes(b"joined")
        return output
    with pytest.raises(ValueError, match="artifact changed"):
        m.run_story(plan(), tmp_path, assemble_story=assemble, **kw)
