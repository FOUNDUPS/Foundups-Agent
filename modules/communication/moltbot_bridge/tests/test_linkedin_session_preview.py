"""Fixed session-preview acceptance using the existing inert browser fixture."""
import pytest

from .test_linkedin_social_adapter import (
    linkedin_inert, _linkedin_direct, _linkedin_wrapper, _linkedin_no_effects,
)


@pytest.mark.parametrize("params,duration,maximum", [
    ({"dry_run": "true"}, 10, 5),
    ({"dry_run": True, "duration_minutes": "2", "max_engagements": "3", "agentic": "true"}, 2, 3),
    ({"dry_run": " YES ", "duration_minutes": 0, "max_engagements": -1}, 0, -1),
    ({"dry_run": "on", "duration_minutes": " 4 ", "max_engagements": " 6 "}, 4, 6),
])
def test_linkedin_dry_run_session_preview(linkedin_inert, params, duration, maximum):
    linkedin_inert.deny_import = True
    result = _linkedin_direct("engagement_session", params)
    assert result == {"success": True, "action": "engagement_session", "dry_run": True,
                      "duration_minutes": duration, "max_engagements": maximum}
    _linkedin_no_effects(linkedin_inert)


@pytest.mark.parametrize("field", ["browser_port", "duration_minutes", "max_engagements"])
@pytest.mark.parametrize("value,error", [("invalid", ValueError), (None, TypeError)])
def test_linkedin_dry_run_session_invalid_preview(linkedin_inert, field, value, error):
    linkedin_inert.deny_import = True
    with pytest.raises(error):
        _linkedin_direct("engagement_session", {"dry_run": "true", field: value})
    _linkedin_no_effects(linkedin_inert)


def test_linkedin_dry_run_session_validation_order(linkedin_inert):
    linkedin_inert.deny_import = True
    with pytest.raises(ValueError):
        _linkedin_direct("engagement_session", {
            "dry_run": "true", "browser_port": "invalid", "duration_minutes": None,
        })
    _linkedin_no_effects(linkedin_inert)


@pytest.mark.parametrize("outer,nested", [("omitted", "false"), (True, "false"),
                                         ("omitted", False), (True, False)])
def test_linkedin_dry_run_session_wrapper_preview(linkedin_inert, outer, nested):
    linkedin_inert.deny_import = True
    task = {"action": "engagement_session", "params": {"dry_run": nested}}
    if outer != "omitted":
        task["dry_run"] = outer
    result = _linkedin_wrapper(task)
    assert result["success"] is True
    assert result["skill"] == "linkedin_engagement"
    assert result["action"] == "engagement_session"
    assert result["params"] == {"dry_run": "true"}
    assert result["result"] == {
        "success": True, "action": "engagement_session", "dry_run": True,
        "duration_minutes": 10, "max_engagements": 5,
    }
    _linkedin_no_effects(linkedin_inert)


@pytest.mark.parametrize("params,duration,maximum", [
    ({}, 10, 5),
    ({"dry_run": "false", "duration_minutes": "2", "max_engagements": "3", "agentic": "true"}, 2, 3),
])
def test_linkedin_dry_run_session_live_compatibility(linkedin_inert, params, duration, maximum):
    observer = object()
    result = _linkedin_direct("engagement_session", params, observer)
    assert result == {"success": True, "action": "engagement_session", "result": {"success": True}}
    linkedin_inert.factory.assert_called_once_with(
        profile="linkedin_foundups", browser_port=9222, dom_action_observer=observer,
    )
    linkedin_inert.client.run_engagement_session.assert_awaited_once_with(
        duration_minutes=duration, max_engagements=maximum,
    )
    linkedin_inert.client.close.assert_called_once_with()
    linkedin_inert.agentic.assert_not_awaited()
    linkedin_inert.draft.assert_not_awaited()

    for name in ("like_post", "like_and_reply", "reply_to_post", "read_feed"):
        getattr(linkedin_inert.client, name).assert_not_awaited()


@pytest.mark.parametrize("stage", ["constructor", "action", "close", "action_and_close"])
def test_linkedin_dry_run_session_live_errors(linkedin_inert, stage):
    action_error = ValueError("synthetic session action")
    final_error = RuntimeError("synthetic " + stage)
    if stage == "constructor":
        linkedin_inert.factory.side_effect = final_error
    if stage in {"action", "action_and_close"}:
        linkedin_inert.client.run_engagement_session.side_effect = (
            final_error if stage == "action" else action_error
        )
    if stage in {"close", "action_and_close"}:
        linkedin_inert.client.close.side_effect = final_error
    with pytest.raises(RuntimeError) as caught:
        _linkedin_direct("engagement_session", {"dry_run": "false"})
    assert caught.value is final_error
    if stage == "constructor":
        linkedin_inert.client.close.assert_not_called()
        linkedin_inert.client.run_engagement_session.assert_not_awaited()
    else:
        linkedin_inert.client.close.assert_called_once_with()
        linkedin_inert.client.run_engagement_session.assert_awaited_once_with(
            duration_minutes=10, max_engagements=5,
        )
    if stage == "action_and_close":
        assert caught.value.__context__ is action_error
    linkedin_inert.agentic.assert_not_awaited()
    linkedin_inert.draft.assert_not_awaited()


@pytest.mark.parametrize("field", ["duration_minutes", "max_engagements"])
def test_linkedin_dry_run_session_live_invalid_closes(linkedin_inert, field):
    with pytest.raises(ValueError):
        _linkedin_direct("engagement_session", {"dry_run": "false", field: "invalid"})
    linkedin_inert.factory.assert_called_once_with(
        profile="linkedin_foundups", browser_port=9222, dom_action_observer=None,
    )
    linkedin_inert.client.run_engagement_session.assert_not_awaited()
    linkedin_inert.client.close.assert_called_once_with()
    linkedin_inert.agentic.assert_not_awaited()
    linkedin_inert.draft.assert_not_awaited()
