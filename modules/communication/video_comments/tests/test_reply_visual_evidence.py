"""Separate exact delivery evidence from optional visual locator observations."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def reply_case(monkeypatch, tmp_path):
    path = Path(__file__).with_name('test_reply_quality_safety.py')
    spec = importlib.util.spec_from_file_location('_visual_quality_helpers', path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    owners = helper.owners.__wrapped__(monkeypatch, tmp_path)
    item, posted = helper.processor(owners)
    item._inspect_posted_reply = owners.PROCESSOR.CommentProcessor._inspect_posted_reply.__get__(item)
    item._snap_dir, item.session_id = tmp_path, 'private-fixture'
    item.driver = SimpleNamespace(get_screenshot_as_png=lambda: b'synthetic-private-image')
    observations = []
    async def locate(**kwargs):
        observations.append(kwargs)
        return SimpleNamespace(success=True, confidence=0.99,
                               metadata={'thought': 'The expected reply is missing from this view.'})
    item.use_vision = True
    item.ui_tars_bridge = SimpleNamespace(verify=locate)
    evidence = []
    item.reply_executor.last_attempt_id = 'attempt-fixture'
    item.reply_executor.history_store = SimpleNamespace(
        append_reply_evidence=lambda attempt, data: evidence.append((attempt, data)))
    return SimpleNamespace(item=item, posted=posted, observations=observations,
                           evidence=evidence, tmp_path=tmp_path)


def engage(case):
    return asyncio.run(case.item.engage_comment(1, do_like=False, do_heart=False))


def test_locator_confidence_is_never_quality_or_delivery_approval(reply_case):
    result = engage(reply_case)
    assert result['reply'] is True and result['delivery_verified'] is True
    observation = result['reply_visual_observation']
    assert observation == {
        'status': 'locator_returned', 'authoritative': False,
        'text_verified': False, 'model_image_binding': 'unbound_recapture',
    }
    assert len(reply_case.posted) == len(reply_case.observations) == 1
    stored = reply_case.evidence[0][1]
    assert stored['delivery_verified'] is True
    assert stored['visual_observation'] == observation
    assert 'post_inspection_passed' not in stored
    assert 'confidence' not in observation


@pytest.mark.parametrize('failure', ['screenshot', 'vision_exception', 'vision_negative', 'vision_missing'])
def test_optional_observation_failure_preserves_verified_delivery(reply_case, failure):
    def no_screenshot():
        raise OSError('synthetic private screenshot failure')
    async def no_vision(**_kwargs):
        raise RuntimeError('synthetic private vision failure')
    async def negative(**_kwargs):
        return SimpleNamespace(success=False, confidence=0.99)
    if failure == 'screenshot':
        reply_case.item.driver.get_screenshot_as_png = no_screenshot
    elif failure == 'vision_exception':
        reply_case.item.ui_tars_bridge.verify = no_vision
    elif failure == 'vision_negative':
        reply_case.item.ui_tars_bridge.verify = negative
    else:
        reply_case.item.ui_tars_bridge = None
    result = engage(reply_case)
    assert result['reply'] is True and result['delivery_verified'] is True
    assert result['reply_submission_status'] == 'verified'
    assert result['reply_visual_observation']['authoritative'] is False
    assert result['reply_visual_observation']['text_verified'] is False
    assert result['reply_visual_observation']['status'] in {'unavailable', 'screenshot_unavailable'}
    assert reply_case.item.stats['replies'] == 1
    assert len(reply_case.posted) == 1
    assert not result.get('halted_for_reply_quality')


def test_private_screenshot_is_not_misrepresented_as_model_image(reply_case):
    result = engage(reply_case)
    path = Path(result['reply_inspection_screenshot'])
    assert path.parent == reply_case.tmp_path and path.read_bytes() == b'synthetic-private-image'
    import hashlib
    assert result['reply_inspection_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result['reply_visual_observation']['model_image_binding'] == 'unbound_recapture'


def test_dom_only_delivery_remains_useful_without_visual_claim(reply_case):
    reply_case.item.use_vision = False
    result = engage(reply_case)
    assert result['reply'] is True and result['delivery_verified'] is True
    assert result['reply_visual_observation']['status'] == 'not_requested'
    assert result['reply_visual_observation']['authoritative'] is False
    assert reply_case.observations == []


def test_unknown_delivery_is_never_promoted_by_visual_inspection(reply_case):
    async def uncertain(*_args, **_kwargs):
        reply_case.posted.append(True)
        return False
    reply_case.item.reply_executor.execute_reply = uncertain
    reply_case.item.reply_executor.last_submission_status = 'unknown'
    result = engage(reply_case)
    assert result['reply'] is False and result.get('delivery_verified') is not True
    assert result['reply_submission_status'] == 'unknown'
    assert reply_case.observations == reply_case.evidence == []
    assert len(reply_case.posted) == 1


def test_optional_evidence_append_failure_does_not_erase_delivery(reply_case):
    def unavailable(*_args):
        raise OSError('synthetic private evidence write failure')
    reply_case.item.reply_executor.history_store.append_reply_evidence = unavailable
    result = engage(reply_case)
    assert result['reply'] is True and result['delivery_verified'] is True
    assert result['reply_evidence_status'] == 'append_unavailable'
    assert len(reply_case.posted) == 1
