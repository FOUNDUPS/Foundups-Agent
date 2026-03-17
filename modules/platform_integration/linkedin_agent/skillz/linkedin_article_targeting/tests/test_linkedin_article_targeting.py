"""Tests for the LinkedIn article targeting skill."""

from modules.platform_integration.linkedin_agent.skillz.linkedin_article_targeting import execute


def test_execute_list_entities_returns_known_accounts():
    result = execute({"action": "list_entities", "params": {"query": "foundups"}})

    assert result["success"] is True
    assert result["count"] >= 1
    assert result["entities"][0]["key"] == "foundups"


def test_execute_search_articles_returns_matches():
    result = execute(
        {
            "action": "search_articles",
            "params": {"query": "rubik cube of agenticness", "limit": "5"},
        }
    )

    assert result["success"] is True
    assert result["matches"]
    assert result["matches"][0]["entity_key"] == "esingularity"


def test_execute_resolve_target_returns_routing_result():
    result = execute(
        {
            "action": "resolve_target",
            "params": {
                "title": "Roadmap to social beneficial capitalism in an AI economy",
                "brief": "OBAI and transforming capitalism through beneficial design.",
            },
        }
    )

    assert result["success"] is True
    assert result["result"]["recommended_entity"]["key"] == "social_beneficial_capitalism"
