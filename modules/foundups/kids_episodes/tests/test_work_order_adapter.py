import copy
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.foundups.kids_episodes.src.work_order_adapter import (
    SKILL_NAME, prepare_episode_request, dispatch_episode_request,
)


def request():
    return prepare_episode_request("Count one, two, three!", request_id="count")


class WRE:
    def __init__(self, tmp_path, *, production=True, executor=True):
        skill = tmp_path / "SKILLz.md"
        skill.write_text("test fixture")
        if executor:
            (tmp_path / "executor.py").write_text("# test fixture, never executed")
        state = "production" if production else "prototype"
        info = dict(name=SKILL_NAME, version="0.1.0", intent_type="CONTENT_PRODUCTION", promotion_state=state)
        self.skills_loader = SimpleNamespace(
            registry={"skills": {SKILL_NAME: info}}, repo_root=tmp_path,
            get_skill_metadata=lambda name: info, resolve_skill_file=lambda name: skill,
        )
        self.calls = []
        self.response = {"success": True, "result": {"proposal": "pretend video"}}

    def execute_skill(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def dispatch(wre, tmp_path):
    return dispatch_episode_request(request(), wre=wre, workspace=tmp_path, execution_binding_digest="a"*64)


def test_canonical_request_preserves_story_and_explicit_corrections():
    raw = "  Slido counts!\n"
    a = prepare_episode_request(raw, request_id="one", confirmed_terms={"Slido": "Suno"})
    assert a["raw_story"] == raw
    assert a == prepare_episode_request(raw, request_id="one", confirmed_terms={"Slido": "Suno"})
    assert dispatch_episode_request(a)["status"] == "BLOCKED"
    a["raw_story"] += "changed"
    assert "canonical" in dispatch_episode_request(a)["reason"]


@pytest.mark.parametrize("kwargs", [{"max_attempts":True}, {"supported_durations":[float("nan")]},
    {"orientation":"other"}, {"confirmed_terms":{"absent":"Suno"}}, {"work_order_id":"../authority"}])
def test_invalid_request(kwargs):
    with pytest.raises(ValueError):
        prepare_episode_request("story", request_id="one", **kwargs)


@pytest.mark.parametrize("production,executor", [(False,True),(True,False)])
def test_existing_admission_and_missing_executor_fail_closed(tmp_path, production, executor):
    wre=WRE(tmp_path,production=production,executor=executor)
    assert dispatch(wre,tmp_path)["status"] == "BLOCKED"
    assert not wre.calls


def test_proposal_and_missing_owner_binding_never_success(tmp_path):
    wre=WRE(tmp_path)
    assert dispatch_episode_request(request(),wre=wre)["status"]=="BLOCKED"
    assert not wre.calls
    assert dispatch(wre,tmp_path)["status"]=="BLOCKED"
    assert wre.calls[0][1]["force"] is False


def valid_response(tmp_path):
    path=tmp_path/"episode.mp4"
    path.write_bytes(b"fixture output, not a real render")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    return {"success":True,"execution_id":"execution", "result":{
        "_executor_dispatch":True,"_effect_evidence":True,
        "effect_receipts":[{"receipt_id":"receipt","effect_type":"render"}],
        "_skill_binding":{"schema_version":"wre_skill_execution_binding.v1","execution_id":"execution",
                          "loaded_skill_sha256":"sha256:"+"a"*64,"scanner_admission_fingerprint":"b"*64},
        "outcome":{"status":"episodes_reviewed_assembly_pending","episodes":[{
            "video_path":str(path),"sha256":digest,"review":{"artifact_sha256":digest,"reviewer_id":"reviewer",
                "checks":dict.fromkeys(("education","safety","continuity","audio","captions","rights"),True)}}]}}}


def test_output_hash_and_review_evidence_required(tmp_path):
    wre=WRE(tmp_path)
    wre.response=valid_response(tmp_path)
    assert dispatch(wre,tmp_path)["success"] is True
    (tmp_path/"episode.mp4").write_bytes(b"modified")
    assert dispatch(wre,tmp_path)["status"]=="BLOCKED"


def test_output_outside_trusted_workspace_rejected(tmp_path):
    wre=WRE(tmp_path)
    other=tmp_path/"other";other.mkdir()
    wre.response=valid_response(tmp_path)
    assert dispatch(wre,other)["status"]=="BLOCKED"


@pytest.mark.parametrize("field", ["_executor_dispatch","_effect_evidence","_skill_binding","effect_receipts"])
def test_missing_effect_evidence_rejected(tmp_path,field):
    wre=WRE(tmp_path);wre.response=valid_response(tmp_path)
    del wre.response["result"][field]
    assert dispatch(wre,tmp_path)["status"]=="BLOCKED"


@pytest.mark.parametrize("status", ["assembled_unreviewed", "story_reviewed", "story_review_failed"])
def test_assembly_review_status_and_join_evidence(tmp_path,status):
    wre=WRE(tmp_path);wre.response=valid_response(tmp_path)
    outcome=wre.response["result"]["outcome"]
    episode=outcome["episodes"][0]
    outcome.update(status=status,story_video={"path":episode["video_path"],"sha256":episode["sha256"]},
        story_review=copy.deepcopy(episode["review"]))
    outcome["story_review"]["checks"]["joins"]=True
    result=dispatch(wre,tmp_path)
    assert result["success"] is (status != "story_review_failed")
    if status == "story_reviewed":
        outcome["story_review"]["checks"]["joins"]=False
        assert dispatch(wre,tmp_path)["status"]=="BLOCKED"


def test_real_repository_loader_api_and_prototype_gate():
    pytest.importorskip("yaml", reason="WRE loader requires PyYAML")
    from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader
    loader=WRESkillsLoader()
    assert loader.resolve_skill_file(SKILL_NAME).is_file()
    class Host:
        skills_loader=loader
        def execute_skill(self,*args,**kwargs):
            pytest.fail("Prototype must not execute")
    response=dispatch_episode_request(request(),wre=Host())
    assert response["status"]=="BLOCKED"
    assert "production" in response["reason"]
