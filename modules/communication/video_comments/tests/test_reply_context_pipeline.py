"""Focused regression tests for grounded YouTube comment replies."""

from modules.communication.video_comments.src.intelligent_reply_generator import (
    IntelligentReplyGenerator,
)
from modules.communication.video_comments.skillz.tars_like_heart_reply.src import (
    comment_processor as processor_module,
)
from modules.communication.video_comments.skillz.tars_like_heart_reply.src.comment_processor import (
    CommentProcessor,
)


class _FakeQwen:
    def __init__(self):
        self.call = None

    def generate_response(self, **kwargs):
        self.call = kwargs
        return "That lyric lands because the video connects solidarity with action."


def _bare_generator():
    generator = object.__new__(IntelligentReplyGenerator)
    generator.lm_studio_available = False
    generator.lm_studio_model_id = None
    generator.qwen_engine = _FakeQwen()
    generator.grok_connector = None
    generator.banter_engine = None
    generator._last_llm_source = None
    generator._current_content_analysis = None
    generator._load_personalization_context = lambda **_: "Prior topic: mutual aid"
    generator._load_voice_memory_context = (
        lambda comment_text, video_title=None: "Verified channel position: build cooperatively"
    )
    return generator


def test_local_qwen_receives_comment_video_guidance_and_memory():
    generator = _bare_generator()

    reply = generator._generate_contextual_reply(
        comment_text="This verse nails why organizing matters",
        author_name="Aki",
        custom_prompt="Treat #FFCPLN as shared music context.",
        tier=2,
        video_title="FFCPLN Song 97 - Mutual Aid",
    )

    prompt = generator.qwen_engine.call["prompt"]
    assert reply.startswith("That lyric lands")
    assert "This verse nails why organizing matters" in prompt
    assert "Treat #FFCPLN as shared music context" in prompt
    assert "FFCPLN Song 97 - Mutual Aid" in prompt
    assert "Prior topic: mutual aid" in prompt
    assert "Verified channel position: build cooperatively" in prompt
    assert generator.qwen_engine.call["stop"] == ["###"]
    assert generator.get_last_llm_source() == "qwen"


def test_voice_memory_query_includes_video_title():
    captured = {}

    class _VoiceMemory:
        def query(self, text, k):
            captured.update(text=text, k=k)
            return [{"score": 0.9, "text": "grounded fact", "source_type": "video"}]

    generator = object.__new__(IntelligentReplyGenerator)
    generator._voice_memory_enabled = True
    generator._get_voice_memory = lambda: _VoiceMemory()

    context = generator._load_voice_memory_context(
        "What did you mean by this?",
        video_title="A specific video",
    )

    assert captured == {
        "text": "A specific video\nWhat did you mean by this?",
        "k": 3,
    }
    assert "grounded fact" in context


def test_ffcpln_pattern_does_not_classify_supporter_as_troll():
    pattern = IntelligentReplyGenerator.SEMANTIC_PATTERN_PROMPTS["ffcpln"]

    assert pattern["keywords"] == ["ffcpln", "ffc pln", "#ffcpln"]
    assert "Do NOT assume the commenter is a troll" in pattern["variation_prompt"]
    assert "actual point first" in pattern["variation_prompt"]


def test_generate_reply_for_comment_forwards_video_title():
    captured = {}
    generator = object.__new__(IntelligentReplyGenerator)
    generator.generate_reply = lambda **kwargs: captured.update(kwargs) or "reply"

    reply = generator.generate_reply_for_comment(
        {
            "text": "comment",
            "author_name": "Kai",
            "channel_id": "commenter-channel",
            "video_title": "Exact Studio row title",
        },
        target_channel_id="receiving-channel",
    )

    assert reply == "reply"
    assert captured["video_title"] == "Exact Studio row title"
    assert captured["target_channel_id"] == "receiving-channel"


def test_comment_processor_forwards_row_context_and_personality(monkeypatch):
    captured = {}

    class _Generator:
        def generate_reply(self, **kwargs):
            captured.update(kwargs)
            return "contextual"

    monkeypatch.setattr(processor_module, "get_reply_generator", lambda: _Generator())
    processor = object.__new__(CommentProcessor)
    processor.video_title = "DAE-wide fallback title"
    processor.target_channel_id = "receiving-channel"

    result = processor._generate_intelligent_reply(
        {
            "text": "row comment",
            "author_name": "Mina",
            "channel_id": "commenter-channel",
            "video_title": "Per-row title",
        }
    )

    assert result == "contextual"
    assert captured["video_title"] == "Per-row title"
    assert captured["target_channel_id"] == "receiving-channel"


def test_dom_extraction_retains_per_row_video_context():
    expected = {
        "text": "comment",
        "author_name": "Mina",
        "author_handle": "@mina",
        "channel_id": "channel",
        "is_mod": False,
        "is_subscriber": True,
        "published_time": "2 hours ago",
        "video_title": "Per-row title",
        "video_id": "abc123",
        "video_url": "https://studio.youtube.com/video/abc123/comments/inbox",
    }

    class _Driver:
        def execute_script(self, script, index):
            assert "ytcp-video-thumbnail-with-info" in script
            assert index == 2
            return expected

    processor = object.__new__(CommentProcessor)
    processor.driver = _Driver()

    assert processor.extract_comment_data(3) == expected


def test_context_gate_rejects_generic_and_stale_sources():
    assert CommentProcessor.is_contextual_reply_source("skill_1:qwen")
    assert CommentProcessor.is_contextual_reply_source("lm_studio")
    assert not CommentProcessor.is_contextual_reply_source("skill_1:template_regular")
    assert not CommentProcessor.is_contextual_reply_source("skill_2:personalized_stats")
    assert not CommentProcessor.is_contextual_reply_source("unknown")
