"""Tests for LinkedIn publishing discovery and routing helpers."""

from modules.platform_integration.linkedin_agent.src.content import (
    list_publishing_entities,
    resolve_article_target,
    search_published_articles,
)


def test_list_publishing_entities_includes_foundups_and_personal():
    entities = list_publishing_entities()
    keys = {entity["key"] for entity in entities}

    assert "foundups" in keys
    assert "personal_undaodu" in keys


def test_search_published_articles_finds_foundups_ide_history():
    matches = search_published_articles("solo founders coding idea with ai", limit=5)

    assert matches
    assert matches[0]["entity_key"] == "foundups"
    assert "Solo Founders Coding their Idea with AI" in matches[0]["title"]


def test_search_published_articles_finds_resp_quantum_history():
    matches = search_published_articles("retrocausal entanglement signal phenomena", limit=3)

    assert matches
    assert matches[0]["entity_key"] == "resp"


def test_resolve_article_target_prefers_explicit_entity_override():
    result = resolve_article_target(
        title="Children learning AI with a teaching tablet",
        preferred_entity="eduit",
    )

    assert result["confidence"] == "explicit"
    assert result["recommended_entity"]["key"] == "eduit"


def test_resolve_article_target_uses_historical_overlap():
    result = resolve_article_target(
        title="Building a multi-agent IDE for solo founders coding with AI",
        brief="A Foundups article about software like LEGO and post-startup tooling.",
    )

    assert result["recommended_entity"]["key"] == "foundups"
    assert result["confidence"] in {"high", "medium_high", "medium"}


def test_resolve_article_target_marks_personal_profile_limitations():
    result = resolve_article_target(
        title="Toward synthetic self-presence and the 0102 digital twin",
        brief="Roger's Box, reflexive autonomous systems, and pArtifact evolution.",
    )

    assert result["recommended_entity"]["key"] == "personal_undaodu"
    assert any("Personal profile article creation" in item for item in result["limitations"])
