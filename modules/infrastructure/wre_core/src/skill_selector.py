#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tree-of-Thought Skill Selector (Sprint 3 - Gap B)

Implements multi-candidate skill selection with branch scoring.
Uses historical fidelity, success rate, trend, and context match.

Per WRE_COT_DEEP_ANALYSIS.md Gap B:
- Add SkillSelector with N candidate branches
- Score using historical fidelity from PatternMemory plus context match
- Execute best branch and log branch scores

WSP References: WSP 46, WSP 48, WSP 77
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .pattern_memory import PatternMemory

logger = logging.getLogger(__name__)


@dataclass
class SkillCandidate:
    """A candidate skill for ToT selection."""
    skill_name: str
    score: float
    fidelity: float
    success_rate: float
    trend_bonus: float
    context_match: float
    total_executions: int


@dataclass
class ToTSelection:
    """Result of Tree-of-Thought selection."""
    selected: SkillCandidate
    candidates: List[SkillCandidate]
    selection_reason: str
    confidence: float
    branch_count: int = 0


class SkillSelector:
    """
    Tree-of-Thought skill selector.

    Given multiple candidate skills that could handle an intent,
    selects the best one based on historical performance and context.

    Per WRE_COT_DEEP_ANALYSIS.md:
    - Explore multiple candidate strategies
    - Score by fidelity + history + context
    - Execute best path and log branch scores
    """

    def __init__(
        self,
        pattern_memory: Optional["PatternMemory"] = None,
        skills_loader=None
    ):
        """
        Initialize selector with memory and optional skills loader.

        Args:
            pattern_memory: PatternMemory instance for fidelity stats
            skills_loader: Optional WRESkillsLoader for skill discovery
        """
        self.memory = pattern_memory
        self.skills_loader = skills_loader
        self.min_executions_for_confidence = 5
        self.cold_start_score = 0.5  # Score for skills with no history

    def select_skill(
        self,
        candidates: List[str],
        context: Dict,
        max_branches: int = 5
    ) -> ToTSelection:
        """
        Select best skill from candidates using ToT scoring.

        Args:
            candidates: List of candidate skill names
            context: Execution context with keywords for matching
            max_branches: Maximum candidates to evaluate

        Returns:
            ToTSelection with selected skill and evaluation details
        """
        if not candidates:
            raise ValueError("No candidate skills provided")

        # Limit branches
        candidates = candidates[:max_branches]

        # Extract context keywords
        context_keywords = self._extract_keywords(context)

        # Score all candidates
        if self.memory:
            ranked = self.memory.rank_skills_for_context(candidates, context_keywords)
        else:
            # Fallback: equal scores for cold start
            ranked = [
                {
                    "skill_name": s,
                    "score": self.cold_start_score,
                    "components": {
                        "fidelity": 0.5,
                        "success_rate": 0.5,
                        "trend_bonus": 0.5,
                        "context_match": 0.0
                    },
                    "total_executions": 0
                }
                for s in candidates
            ]

        # Convert to SkillCandidate objects
        skill_candidates = []
        for r in ranked:
            components = r.get("components", {})
            skill_candidates.append(SkillCandidate(
                skill_name=r["skill_name"],
                score=r["score"],
                fidelity=components.get("fidelity", 0.5),
                success_rate=components.get("success_rate", 0.5),
                trend_bonus=components.get("trend_bonus", 0.5),
                context_match=components.get("context_match", 0.0),
                total_executions=r.get("total_executions", 0)
            ))

        # Select best
        selected = skill_candidates[0]

        # Calculate confidence
        confidence = self._calculate_confidence(selected, skill_candidates)

        # Determine selection reason
        reason = self._explain_selection(selected, skill_candidates)

        logger.info(
            f"[TOT-SELECT] Selected {selected.skill_name} "
            f"(score={selected.score:.3f}, confidence={confidence:.3f}) "
            f"from {len(candidates)} candidates"
        )

        return ToTSelection(
            selected=selected,
            candidates=skill_candidates,
            selection_reason=reason,
            confidence=confidence,
            branch_count=len(skill_candidates)
        )

    def _extract_keywords(self, context: Dict) -> List[str]:
        """Extract keywords from context for matching."""
        keywords = []

        # Common context fields that might contain keywords
        for key in ['intent', 'action', 'query', 'task', 'command', 'operation']:
            if key in context:
                value = str(context[key])
                # Split on common separators
                keywords.extend(value.replace('_', ' ').replace('-', ' ').split())

        # Also check for explicit keywords field
        if 'keywords' in context:
            kw_val = context['keywords']
            if isinstance(kw_val, list):
                keywords.extend(kw_val)
            elif isinstance(kw_val, str):
                keywords.extend(self._tokenize_text(kw_val))

        normalized = []
        for keyword in keywords:
            normalized.extend(self._tokenize_text(str(keyword)))

        return normalized

    @staticmethod
    def _tokenize_text(text: str) -> List[str]:
        """Tokenize natural language and snake/kebab case into search terms."""
        return [
            token
            for token in re.findall(r"[a-z0-9]+", text.lower().replace("_", " ").replace("-", " "))
            if len(token) > 2
        ]

    def _calculate_confidence(
        self,
        selected: SkillCandidate,
        all_candidates: List[SkillCandidate]
    ) -> float:
        """
        Calculate selection confidence.

        High confidence when:
        - Large score gap to second place
        - Selected skill has many executions
        - High fidelity history
        """
        if len(all_candidates) < 2:
            return 0.9 if selected.total_executions >= self.min_executions_for_confidence else 0.5

        # Score gap to second place
        second = all_candidates[1]
        score_gap = selected.score - second.score
        gap_confidence = min(1.0, score_gap / 0.2)  # 0.2 gap = full confidence

        # Execution count confidence
        exec_confidence = min(1.0, selected.total_executions / 20)

        # Fidelity confidence
        fidelity_confidence = selected.fidelity

        # Weighted combination
        confidence = (
            0.4 * gap_confidence +
            0.3 * exec_confidence +
            0.3 * fidelity_confidence
        )

        return round(confidence, 3)

    def _explain_selection(
        self,
        selected: SkillCandidate,
        all_candidates: List[SkillCandidate]
    ) -> str:
        """Generate human-readable selection explanation."""
        reasons = []

        if selected.fidelity >= 0.8:
            reasons.append(f"high fidelity ({selected.fidelity:.0%})")

        if selected.success_rate >= 0.8:
            reasons.append(f"high success rate ({selected.success_rate:.0%})")

        if selected.trend_bonus > 0.6:
            reasons.append("improving trend")

        if selected.context_match > 0.5:
            reasons.append("strong context match")

        if selected.total_executions >= 20:
            reasons.append(f"proven ({selected.total_executions} executions)")
        elif selected.total_executions < self.min_executions_for_confidence:
            reasons.append("cold start (limited history)")

        if len(all_candidates) > 1:
            gap = selected.score - all_candidates[1].score
            if gap > 0.1:
                reasons.append(f"clear winner (+{gap:.2f} margin)")

        return "; ".join(reasons) if reasons else "default selection"

    def find_candidates_for_intent(self, intent: str) -> List[str]:
        """
        Find candidate skills that could handle an intent.

        Uses skills_loader if available, otherwise returns empty list.
        """
        if not self.skills_loader:
            return []

        # Get healthy skills from loader (Skills 2.0 hygiene)
        all_skills = []
        if hasattr(self.skills_loader, 'list_healthy_skills'):
            # Prefer hygiene-filtered list (excludes retired/invalid category)
            all_skills = self.skills_loader.list_healthy_skills()
        elif hasattr(self.skills_loader, 'list_skills'):
            all_skills = self.skills_loader.list_skills()
        elif hasattr(self.skills_loader, 'skills_registry'):
            all_skills = list(self.skills_loader.skills_registry.keys())

        if not all_skills:
            return []

        registry = getattr(self.skills_loader, "registry", {}) or {}
        registry_skills = registry.get("skills", {}) if isinstance(registry, dict) else {}
        intent_tokens = self._tokenize_text(intent)
        if not intent_tokens:
            return []

        ranked_candidates = []
        for skill in all_skills:
            skill_info = registry_skills.get(skill, {}) if isinstance(registry_skills, dict) else {}
            searchable_parts = [
                skill,
                str(skill_info.get("description", "")),
                str(skill_info.get("domain", "")),
                str(skill_info.get("intent_type", "")),
                str(skill_info.get("location", "")),
            ]
            searchable_text = " ".join(part for part in searchable_parts if part).lower()
            searchable_tokens = set(self._tokenize_text(searchable_text))
            if not searchable_tokens:
                continue

            score = 0.0
            for token in intent_tokens:
                if token in searchable_tokens:
                    score += 1.0
                elif token in skill.lower():
                    score += 0.75
                elif token in searchable_text:
                    score += 0.5

            if score > 0:
                ranked_candidates.append((score, skill))

        ranked_candidates.sort(key=lambda item: (-item[0], item[1]))
        return [skill for _, skill in ranked_candidates[:10]]


# Convenience function for quick selection
def select_best_skill(
    candidates: List[str],
    context: Dict,
    pattern_memory: Optional["PatternMemory"] = None
) -> Tuple[str, Dict]:
    """
    Quick function to select best skill from candidates.

    Args:
        candidates: List of candidate skill names
        context: Execution context
        pattern_memory: Optional PatternMemory for fidelity stats

    Returns:
        (selected_skill_name, selection_metadata)
    """
    if not candidates:
        return None, {"error": "No candidates"}

    selector = SkillSelector(pattern_memory=pattern_memory)

    try:
        selection = selector.select_skill(candidates, context)
        return selection.selected.skill_name, {
            "tot_score": selection.selected.score,
            "tot_confidence": selection.confidence,
            "tot_reason": selection.selection_reason,
            "tot_branch_count": selection.branch_count
        }
    except Exception as exc:
        logger.warning(f"[TOT-SELECT] Selection failed: {exc}")
        return candidates[0], {"tot_error": str(exc)}


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("[EXAMPLE] Tree-of-Thought Skill Selection")

    # Create selector (without memory for demo)
    selector = SkillSelector()

    # Mock candidates
    candidates = ["qwen_gitpush", "qwen_gitdiff", "qwen_commit_review"]
    context = {"intent": "push_changes", "action": "git"}

    # Select best
    selection = selector.select_skill(candidates, context)

    print(f"  Selected: {selection.selected.skill_name}")
    print(f"  Score: {selection.selected.score:.3f}")
    print(f"  Confidence: {selection.confidence:.3f}")
    print(f"  Reason: {selection.selection_reason}")
    print(f"  Branch count: {selection.branch_count}")

    print("\n  All candidates:")
    for c in selection.candidates:
        print(f"    - {c.skill_name}: score={c.score:.3f}")

    print("\n[OK] ToT selection complete")
