#!/usr/bin/env python3
"""
WRE Skills Loader
Progressive disclosure loader with dependency injection for native Qwen/Gemma execution
WSP Compliance: WSP 77 (Agent Coordination), WSP 50 (Pre-Action Verification)
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Lightweight skill metadata for progressive disclosure"""
    name: str
    description: str
    primary_agent: str
    intent_type: str
    promotion_state: str
    location: Path
    pattern_fidelity_threshold: float
    # Skills 2.0 hygiene fields
    category: str = "workflow"  # workflow | capability-uplift
    retirement_date: str = ""  # ISO date string or empty
    has_evals: bool = False  # True if evals field is present and non-empty


@dataclass
class SkillHygieneStatus:
    """Result of skill hygiene check."""
    skill_name: str
    is_healthy: bool
    is_retired: bool = False
    missing_category: bool = False
    missing_evals: bool = False  # Warning only for production skills
    retirement_date: str = ""
    category: str = ""
    issues: list = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


@dataclass
class SkillContext:
    """Dependency context injected into skill execution"""
    data_stores: Dict[str, Any]
    mcp_endpoints: Dict[str, Any]
    throttles: Dict[str, Any]
    required_context: Dict[str, Any]


class WRESkillsLoader:
    """
    WRE Skills Loader - Entry point for loading AI instructions into agent prompts

    Features:
    - Progressive disclosure (load metadata first, full content on-demand)
    - Dependency injection (data stores, MCP endpoints, throttles, context)
    - Agent filtering (only show relevant skills to each agent)
    - Caching (avoid repeated file reads)
    """

    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize skills loader

        Args:
            registry_path: Path to skills_registry.json
        """
        if registry_path is None:
            self.registry_path = Path(__file__).parent / "skills_registry_v2.json"
        else:
            self.registry_path = Path(registry_path)

        self.repo_root = Path(__file__).parent.parent.parent.parent
        self.registry = self._load_registry()
        self.skill_cache: Dict[str, str] = {}  # skill_name -> full_content

    def _load_registry(self) -> Dict[str, Any]:
        """Load skills registry JSON"""
        if not self.registry_path.exists():
            logger.warning(f"[WRE-LOADER] Registry not found: {self.registry_path}")
            return {"version": "1.0", "skills": {}}

        with open(self.registry_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_skills(
        self,
        agent_type: Optional[str] = None,
        promotion_state: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> List[str]:
        """
        Return registered skill names with optional lightweight filtering.

        This is a metadata-only operation intended for routing and candidate
        selection. It should not force-load any SKILLz.md content.
        """
        skills = self.registry.get("skills", {})
        if not isinstance(skills, dict):
            return []

        names: List[str] = []
        for skill_name, skill_info in skills.items():
            if not isinstance(skill_info, dict):
                continue

            if agent_type:
                agents = skill_info.get("agents") or []
                primary_agent = skill_info.get("primary_agent")
                fallback_agent = skill_info.get("fallback_agent")
                if (
                    agent_type not in agents
                    and agent_type != primary_agent
                    and agent_type != fallback_agent
                ):
                    continue

            if promotion_state and skill_info.get("promotion_state") != promotion_state:
                continue

            if domain and skill_info.get("domain") != domain:
                continue

            names.append(skill_name)

        return sorted(names)

    def has_skill(self, skill_name: str) -> bool:
        """Return True when the registry contains the named skill."""
        skills = self.registry.get("skills", {})
        return isinstance(skills, dict) and skill_name in skills

    def discover_skills(
        self,
        agent_type: Optional[str] = None,
        intent_type: Optional[str] = None,
        promotion_state: Optional[str] = None
    ) -> List[SkillMetadata]:
        """
        Discover available skills (progressive disclosure - metadata only)

        Args:
            agent_type: Filter by agent (gemma, qwen, grok, ui-tars)
            intent_type: Filter by intent (CLASSIFICATION, DECISION, GENERATION, TELEMETRY)
            promotion_state: Filter by state (prototype, staged, production)

        Returns:
            List of skill metadata (NOT full content)
        """
        discovered_skills = []

        for skill_name, skill_info in self.registry["skills"].items():
            # Apply filters
            if agent_type and skill_info.get("primary_agent") != agent_type:
                if skill_info.get("fallback_agent") != agent_type:
                    continue

            if intent_type and intent_type not in skill_info.get("intent_type", ""):
                continue

            if promotion_state and skill_info.get("promotion_state") != promotion_state:
                continue

            skill_path: Optional[Path] = None
            try:
                skill_path = self.resolve_skill_file(skill_name)
                metadata = self._extract_metadata(skill_path)

                # Extract Skills 2.0 hygiene fields
                category = metadata.get("category", "")
                retirement_date = metadata.get("retirement_date") or ""
                evals = metadata.get("evals") or []
                has_evals = bool(evals) and len(evals) > 0

                discovered_skills.append(SkillMetadata(
                    name=skill_name,
                    description=metadata.get("description", ""),
                    primary_agent=skill_info.get("primary_agent", ""),
                    intent_type=skill_info.get("intent_type", ""),
                    promotion_state=skill_info.get("promotion_state", "prototype"),
                    location=skill_path,
                    pattern_fidelity_threshold=metadata.get("pattern_fidelity_threshold", 0.90),
                    category=category,  # Keep empty for hygiene filter to detect
                    retirement_date=str(retirement_date) if retirement_date and retirement_date != "null" else "",
                    has_evals=has_evals,
                ))
            except Exception as e:
                logger.error(
                    "[WRE-LOADER] Failed to extract metadata from %s: %s",
                    skill_path or skill_name,
                    e,
                )

        logger.info(f"[WRE-LOADER] Discovered {len(discovered_skills)} skills (agent={agent_type}, intent={intent_type}, state={promotion_state})")
        return discovered_skills

    def discover_healthy_skills(
        self,
        agent_type: Optional[str] = None,
        intent_type: Optional[str] = None,
        promotion_state: Optional[str] = None
    ) -> List[SkillMetadata]:
        """
        Discover available skills filtered by hygiene status.

        Same as discover_skills() but excludes:
        - Retired skills (retirement_date in the past)
        - Skills with invalid/missing category

        Args:
            agent_type: Filter by agent (gemma, qwen, grok, ui-tars)
            intent_type: Filter by intent (CLASSIFICATION, DECISION, GENERATION, TELEMETRY)
            promotion_state: Filter by state (prototype, staged, production)

        Returns:
            List of healthy skill metadata (NOT full content)
        """
        all_skills = self.discover_skills(agent_type, intent_type, promotion_state)
        healthy_skills = []

        for skill in all_skills:
            # Check retirement
            if skill.retirement_date and self._is_retired(skill.retirement_date):
                logger.debug(f"[WRE-LOADER] Excluding retired skill: {skill.name}")
                continue

            # Check category validity
            if skill.category not in {"workflow", "capability-uplift"}:
                logger.debug(f"[WRE-LOADER] Excluding skill with invalid category: {skill.name} (category={skill.category})")
                continue

            healthy_skills.append(skill)

        excluded = len(all_skills) - len(healthy_skills)
        if excluded > 0:
            logger.info(f"[WRE-LOADER] Hygiene filter excluded {excluded}/{len(all_skills)} skills")

        return healthy_skills

    def load_skill(
        self,
        skill_name: str,
        agent_type: str,
        inject_context: bool = True,
        enforce_hygiene: bool = True
    ) -> str:
        """
        Load full skill content for agent execution (on-demand)

        Args:
            skill_name: Name of skill to load
            agent_type: Agent that will execute (gemma, qwen, grok, ui-tars)
            inject_context: Whether to inject dependency context
            enforce_hygiene: If True, block retired/unhealthy skills (default: True)

        Returns:
            Full SKILL.md content with agent-specific filtering and context injection

        Raises:
            ValueError: If skill not found or fails hygiene check
        """
        # Check cache first
        cache_key = f"{skill_name}_{agent_type}"
        if cache_key in self.skill_cache:
            logger.debug(f"[WRE-LOADER] Cache hit: {cache_key}")
            return self.skill_cache[cache_key]

        # Get skill info from registry
        skill_info = self.registry["skills"].get(skill_name)
        if not skill_info:
            raise ValueError(f"Skill not found in registry: {skill_name}")

        # Skills 2.0 hygiene gate
        if enforce_hygiene:
            hygiene = self.check_skill_hygiene(skill_name)
            if hygiene.is_retired:
                raise ValueError(
                    f"Skill '{skill_name}' is retired (retirement_date: {hygiene.retirement_date}). "
                    "Use enforce_hygiene=False to bypass."
                )
            if not hygiene.is_healthy:
                logger.warning(
                    f"[WRE-LOADER] Skill '{skill_name}' has hygiene issues: {hygiene.issues}"
                )

        skill_path = self.resolve_skill_file(skill_name)
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill file not found: {skill_path}")

        with open(skill_path, 'r', encoding='utf-8') as f:
            skill_content = f.read()

        # Filter for agent-specific sections
        filtered_content = self._filter_for_agent(skill_content, agent_type)

        # Inject dependency context if requested
        if inject_context:
            context = self._prepare_context(skill_info)
            filtered_content = self._inject_context(filtered_content, context)

        # Cache and return
        self.skill_cache[cache_key] = filtered_content
        logger.info(f"[WRE-LOADER] Loaded skill: {skill_name} for {agent_type} ({len(filtered_content)} chars)")
        return filtered_content

    def resolve_skill_file(self, skill_name: str) -> Path:
        """
        Resolve canonical skill file path (SKILLz.md preferred, SKILL.md fallback).

        Raises:
            ValueError: if skill is absent from registry
            FileNotFoundError: if neither SKILLz.md nor SKILL.md exists
        """
        skill_info = self.registry["skills"].get(skill_name)
        if not skill_info:
            raise ValueError(f"Skill not found in registry: {skill_name}")

        candidates = self._candidate_skill_files(skill_name, skill_info)
        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            f"Skill file not found for {skill_name}: "
            + ", ".join(str(candidate) for candidate in candidates[:6])
        )

    def _candidate_skill_files(
        self,
        skill_name: str,
        skill_info: Optional[Dict[str, Any]] = None,
    ) -> List[Path]:
        """
        Build candidate SKILL file paths for a registry entry.

        Some registry locations still point at legacy `skills/` directories while
        the real implementation now lives in `skillz/`. Prefer the configured
        location first, then scan common in-repo skill locations as a wiring
        fallback instead of silently degrading to synthetic prompt content.
        """
        candidates: List[Path] = []
        seen: set[str] = set()

        def _append(path: Path) -> None:
            path_str = str(path)
            if path_str not in seen:
                seen.add(path_str)
                candidates.append(path)

        if skill_info:
            configured = Path(str(skill_info["location"]))
            if not configured.is_absolute():
                configured = self.repo_root / configured
            _append(configured / "SKILLz.md")
            _append(configured / "SKILL.md")

            configured_str = str(configured)
            if "\\skills\\" in configured_str or "/skills/" in configured_str:
                alt_dir = Path(
                    configured_str.replace("\\skills\\", "\\skillz\\").replace("/skills/", "/skillz/")
                )
                _append(alt_dir / "SKILLz.md")
                _append(alt_dir / "SKILL.md")

        search_patterns = [
            f"modules/*/*/skillz/{skill_name}/SKILLz.md",
            f"modules/*/*/skillz/{skill_name}/SKILL.md",
            f"modules/*/*/skills/{skill_name}/SKILLz.md",
            f"modules/*/*/skills/{skill_name}/SKILL.md",
            f".claude/skills/{skill_name}/SKILLz.md",
            f".claude/skills/{skill_name}/SKILL.md",
            f"holo_index/skills/{skill_name}/SKILLz.md",
            f"holo_index/skills/{skill_name}/SKILL.md",
        ]
        for pattern in search_patterns:
            for match in self.repo_root.glob(pattern):
                _append(match)

        return candidates

    def inject_skill_into_prompt(
        self,
        base_prompt: str,
        skill_name: str,
        agent_type: str
    ) -> str:
        """
        Inject skill instructions into agent prompt (WRE entry point)

        Args:
            base_prompt: Agent's base system prompt
            skill_name: Skill to inject
            agent_type: Agent type

        Returns:
            Augmented prompt with skill instructions
        """
        skill_content = self.load_skill(skill_name, agent_type)

        # Inject skill into prompt (append to system instructions)
        augmented_prompt = f"{base_prompt}\n\n# SKILL: {skill_name}\n\n{skill_content}"

        logger.info(f"[WRE-LOADER] Injected skill '{skill_name}' into {agent_type} prompt")
        return augmented_prompt

    def _extract_metadata(self, skill_path: Path) -> Dict[str, Any]:
        """Extract YAML frontmatter from SKILL.md"""
        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract YAML frontmatter
        if content.startswith('---\n'):
            end_idx = content.find('\n---\n', 4)
            if end_idx != -1:
                frontmatter = content[4:end_idx]
                return yaml.safe_load(frontmatter)

        return {}

    def check_skill_hygiene(self, skill_name: str) -> SkillHygieneStatus:
        """
        Check skill hygiene status (Skills 2.0 compliance).

        Validates:
        - retirement_date: If set and past, skill is retired
        - category: Must be 'workflow' or 'capability-uplift'
        - evals: Should be present for production skills (warning)

        Args:
            skill_name: Name of skill to check

        Returns:
            SkillHygieneStatus with health assessment
        """
        issues = []

        try:
            skill_path = self.resolve_skill_file(skill_name)
            metadata = self._extract_metadata(skill_path)
        except (ValueError, FileNotFoundError) as e:
            return SkillHygieneStatus(
                skill_name=skill_name,
                is_healthy=False,
                issues=[f"Cannot load skill: {e}"],
            )

        # Check retirement_date
        retirement_date = metadata.get("retirement_date") or ""
        is_retired = self._is_retired(retirement_date)
        if is_retired:
            issues.append(f"Skill retired on {retirement_date}")

        # Check category
        category = metadata.get("category") or ""
        valid_categories = {"workflow", "capability-uplift"}
        missing_category = category not in valid_categories
        if missing_category:
            issues.append(f"Invalid or missing category: '{category}' (expected: workflow, capability-uplift)")

        # Check evals presence (warning for production skills)
        evals = metadata.get("evals") or []
        has_evals = bool(evals) and len(evals) > 0
        promotion_state = metadata.get("promotion_state", "unknown")
        missing_evals = promotion_state == "production" and not has_evals
        if missing_evals:
            issues.append("Production skill missing evals (recommended)")

        is_healthy = not is_retired and not missing_category

        return SkillHygieneStatus(
            skill_name=skill_name,
            is_healthy=is_healthy,
            is_retired=is_retired,
            missing_category=missing_category,
            missing_evals=missing_evals,
            retirement_date=str(retirement_date) if retirement_date else "",
            category=category,
            issues=issues,
        )

    def _is_retired(self, retirement_date: Any) -> bool:
        """
        Check if skill is retired based on retirement_date.

        Args:
            retirement_date: Date string (ISO format) or None/null

        Returns:
            True if skill is retired (date is in the past)
        """
        if not retirement_date or retirement_date == "null":
            return False

        try:
            # Parse ISO date string
            if isinstance(retirement_date, str):
                # Handle both date-only and datetime formats
                if "T" in retirement_date:
                    retire_dt = datetime.fromisoformat(retirement_date.replace("Z", "+00:00"))
                else:
                    retire_dt = datetime.strptime(retirement_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                return False

            now = datetime.now(timezone.utc)
            return retire_dt <= now
        except (ValueError, TypeError):
            logger.warning(f"[WRE-LOADER] Invalid retirement_date format: {retirement_date}")
            return False

    def list_healthy_skills(
        self,
        agent_type: Optional[str] = None,
        promotion_state: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> List[str]:
        """
        Return registered skill names filtered by hygiene status.

        Only returns skills that:
        - Are not retired
        - Have valid category

        Args:
            agent_type: Filter by agent
            promotion_state: Filter by state
            domain: Filter by domain

        Returns:
            List of healthy skill names
        """
        all_skills = self.list_skills(agent_type, promotion_state, domain)
        healthy = []

        for skill_name in all_skills:
            status = self.check_skill_hygiene(skill_name)
            if status.is_healthy:
                healthy.append(skill_name)
            else:
                logger.debug(
                    f"[WRE-LOADER] Skill '{skill_name}' excluded by hygiene: {status.issues}"
                )

        return healthy

    def _filter_for_agent(self, content: str, agent_type: str) -> str:
        """
        Filter skill content to show only agent-specific sections

        Args:
            content: Full SKILL.md content
            agent_type: Agent type to filter for

        Returns:
            Filtered content
        """
        # TODO: Implement agent-specific filtering
        # For now, return full content
        # Future: Parse markdown sections and filter based on agent annotations
        return content

    def _prepare_context(self, skill_info: Dict[str, Any]) -> SkillContext:
        """
        Prepare dependency context for skill execution

        Args:
            skill_info: Skill metadata from registry

        Returns:
            SkillContext with loaded dependencies
        """
        # TODO: Load actual dependencies
        # For now, return empty context structure
        return SkillContext(
            data_stores={},
            mcp_endpoints={},
            throttles={},
            required_context={}
        )

    def _inject_context(self, content: str, context: SkillContext) -> str:
        """
        Inject dependency context into skill content

        Args:
            content: Skill content
            context: Dependency context

        Returns:
            Content with injected context
        """
        # TODO: Implement context injection
        # For now, append context as comment
        context_str = f"\n\n<!-- WRE Context Injected -->\n"
        return content + context_str

    def get_skill_location(self, skill_name: str, promotion_state: str) -> Path:
        """
        Get filesystem path for skill at given promotion state

        Args:
            skill_name: Name of skill
            promotion_state: Promotion state (prototype, staged, production)

        Returns:
            Path to skill directory
        """
        skill_info = self.registry["skills"].get(skill_name)
        if not skill_info:
            raise ValueError(f"Skill not found: {skill_name}")

        if promotion_state == "prototype":
            return self.repo_root / f".claude/skills/{skill_name}_prototype/"
        elif promotion_state == "staged":
            return self.repo_root / f".claude/skills/{skill_name}_staged/"
        elif promotion_state == "production":
            return self.repo_root / skill_info["production_path_target"]
        else:
            raise ValueError(f"Invalid promotion state: {promotion_state}")

    def reload_registry(self) -> None:
        """Reload registry from disk (after promotions/rollbacks)"""
        self.registry = self._load_registry()
        self.skill_cache.clear()
        logger.info("[WRE-LOADER] Registry reloaded, cache cleared")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    loader = WRESkillsLoader()

    # Example 1: Discover skills for Gemma
    print("[EXAMPLE 1] Discover Gemma CLASSIFICATION skills:")
    gemma_skills = loader.discover_skills(agent_type="gemma", intent_type="CLASSIFICATION")
    for skill in gemma_skills:
        print(f"  - {skill.name}: {skill.description[:60]}...")

    # Example 2: Load specific skill
    print("\n[EXAMPLE 2] Load youtube_spam_detection skill:")
    try:
        # Note: This will fail if prototype SKILL.md doesn't exist yet
        skill_content = loader.load_skill("youtube_spam_detection", agent_type="gemma")
        print(f"  Loaded: {len(skill_content)} characters")
    except FileNotFoundError as e:
        print(f"  [EXPECTED] {e}")
        print("  (Skills will exist after Qwen generates baseline templates)")

    # Example 3: Inject skill into prompt
    print("\n[EXAMPLE 3] Inject skill into Gemma prompt:")
    base_prompt = "You are Gemma, a fast classification agent."
    try:
        augmented_prompt = loader.inject_skill_into_prompt(
            base_prompt,
            "youtube_spam_detection",
            agent_type="gemma"
        )
        print(f"  Base prompt: {len(base_prompt)} chars")
        print(f"  Augmented prompt: {len(augmented_prompt)} chars")
    except FileNotFoundError:
        print("  [EXPECTED] Skill file not found yet")

    print("\n[OK] WRE Skills Loader ready")
