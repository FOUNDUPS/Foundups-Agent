"""Explicit story entry retains local trust and WRE's production admission."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src.openclaw_execution_routes import execute_plan
from modules.foundups.kids_episodes.src import work_order_adapter


class DAE:
    wre = None

    async def _try_conversation_social_control(self, intent):
        return None

    def _execute_conversation(self, intent):
        return "ordinary conversation"


def invoke(message, channel="local_repl", authorized=True):
    intent = SimpleNamespace(raw_message=message, channel=channel, is_authorized_commander=authorized)
    return asyncio.run(execute_plan(DAE(), SimpleNamespace(intent=intent, route="conversation")))


@pytest.mark.parametrize("prefix", ["kids story:", "eduit story:", "KIDS STORY:"])
def test_explicit_request_reaches_truthful_blocked_adapter(prefix):
    response=json.loads(invoke(prefix+" Count and clap!"))
    assert response["status"]=="BLOCKED"
    assert response["request"]["raw_story"]==" Count and clap!"
    assert "WRE runtime" in response["reason"]


@pytest.mark.parametrize("channel,authorized", [("discord",True),("telegram",True),("local_repl",False),("local_repl",1)])
def test_spoofed_or_unauthorized_request_has_no_dispatch(monkeypatch,channel,authorized):
    def unexpected(*args,**kwargs):
        pytest.fail("Unauthorized request reached dispatch")
    monkeypatch.setattr(work_order_adapter,"dispatch_episode_request",unexpected)
    assert invoke("kids story: count",channel,authorized).startswith("BLOCKED")


def test_generic_story_remains_conversation():
    assert invoke("Please tell a story about kids") == "ordinary conversation"


def test_empty_story_is_blocked():
    assert invoke("kids story:  ").startswith("BLOCKED")
