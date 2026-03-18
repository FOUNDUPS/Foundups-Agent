#!/usr/bin/env python3
"""LinkedIn article targeting skill executor."""

from __future__ import annotations

from typing import Any, Dict

from modules.platform_integration.linkedin_agent.src.content import (
    list_publishing_entities,
    resolve_article_target,
    search_published_articles,
)

SUPPORTED_ACTIONS = {"list_entities", "search_articles", "resolve_target"}


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: str, default: int = 10) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def execute(task: Dict[str, Any]) -> Dict[str, Any]:
    action = str(task.get("action", "")).strip().lower()
    params = dict(task.get("params", {}))
    skill_name = "linkedin_article_targeting"

    if action not in SUPPORTED_ACTIONS:
        return {
            "success": False,
            "skill": skill_name,
            "action": action,
            "error": "unsupported_action",
            "supported": sorted(SUPPORTED_ACTIONS),
        }

    if action == "list_entities":
        entities = list_publishing_entities(
            include_zero_article=_truthy(params.get("include_zero_article", "true")),
            include_not_checked=_truthy(params.get("include_not_checked", "true")),
            query=params.get("query", ""),
        )
        return {
            "success": True,
            "skill": skill_name,
            "action": action,
            "entities": entities,
            "count": len(entities),
        }

    if action == "search_articles":
        query = params.get("query", "").strip()
        if not query:
            return {
                "success": False,
                "skill": skill_name,
                "action": action,
                "error": "missing_query",
            }
        matches = search_published_articles(query, limit=_safe_int(params.get("limit", "10")))
        return {
            "success": True,
            "skill": skill_name,
            "action": action,
            "query": query,
            "matches": matches,
            "count": len(matches),
        }

    title = params.get("title", "").strip()
    if not title:
        return {
            "success": False,
            "skill": skill_name,
            "action": action,
            "error": "missing_title",
        }

    result = resolve_article_target(
        title=title,
        brief=params.get("brief", ""),
        body=params.get("body", ""),
        preferred_entity=params.get("preferred_entity", ""),
    )
    return {
        "success": True,
        "skill": skill_name,
        "action": action,
        "result": result,
    }


def get_skill_info() -> Dict[str, Any]:
    return {
        "name": "linkedin_article_targeting",
        "version": "1.0.0",
        "domain": "social",
        "actions": sorted(SUPPORTED_ACTIONS),
        "intent_type": "DECISION",
    }
