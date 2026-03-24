#!/usr/bin/env python3
"""
WRE Skills Discovery - Filesystem Scanner for Phase 2
Scans filesystem to discover all SKILL.md files (not just registry-based)

WSP Compliance: WSP 96 (WRE Skills), WSP 50 (Pre-Action Verification)
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import time
from threading import Thread, Event

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredSkill:
    """Filesystem-discovered skill (may not be in registry yet)"""
    skill_path: Path
    skill_name: str
    agents: List[str]
    intent_type: str
    version: str
    promotion_state: str  # Inferred from location
    wsp_chain: List[str]
    metadata: Dict[str, Any]
    # Skills 2.0 hygiene fields
    category: str = "workflow"  # workflow | capability-uplift
    retirement_date: str = ""  # ISO date string or empty
    has_evals: bool = False  # True if evals field is present and non-empty


class WRESkillsDiscovery:
    """
    Filesystem-based skills discovery for WRE Phase 2

    Scans:
    - modules/*/skills/**/SKILLz.md (production skills - preferred)
    - modules/*/skills/**/SKILL.md (production skills - legacy)
    - .claude/skills/**/SKILLz.md (prototype skills)
    - holo_index/skills/**/SKILLz.md (holo skills)

    Does NOT require skills_registry.json - discovers from filesystem
    
    Note: SKILLz.md is the new naming convention (WSP 95 enhancement).
    SKILL.md is supported for backward compatibility.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize skills discovery

        Args:
            repo_root: Repository root path (defaults to 5 levels up from this file)
        """
        if repo_root is None:
            # From wre_skills_discovery.py -> skills -> wre_core -> infrastructure -> modules -> repo_root
            self.repo_root = Path(__file__).parent.parent.parent.parent.parent
        else:
            self.repo_root = Path(repo_root)

        logger.info(f"[WRE-DISCOVERY] Initialized with repo_root: {self.repo_root}")

    def discover_all_skills(self) -> List[DiscoveredSkill]:
        """
        Scan filesystem for all SKILLz.md files (and legacy SKILL.md)

        Returns:
            List of discovered skills (both registered and unregistered)
        """
        discovered_skills = []

        # Scan patterns - SKILLz.md first (preferred), then SKILL.md (legacy)
        # Both skills/ and skillz/ directory names are scanned (some modules use skillz/)
        scan_patterns = [
            # SKILLz.md - new naming convention
            "modules/*/*/skills/**/SKILLz.md",    # Production skills (domain/module/skills/)
            "modules/*/*/skillz/**/SKILLz.md",    # Production skills (domain/module/skillz/)
            ".claude/skills/**/SKILLz.md",         # Prototype skills
            "holo_index/skills/**/SKILLz.md",      # HoloIndex skills
            # SKILL.md - legacy (backward compatibility)
            "modules/*/*/skills/**/SKILL.md",    # Legacy production skills
            "modules/*/*/skillz/**/SKILL.md",    # Legacy production skills (skillz/)
            ".claude/skills/**/SKILL.md",         # Legacy prototype skills
            "holo_index/skills/**/SKILL.md",      # Legacy HoloIndex skills
        ]

        for pattern in scan_patterns:
            skill_paths = list(self.repo_root.glob(pattern))
            logger.info(f"[WRE-DISCOVERY] Pattern '{pattern}' found {len(skill_paths)} skills")

            for skill_path in skill_paths:
                try:
                    skill = self._parse_skill_file(skill_path)
                    if skill:
                        discovered_skills.append(skill)
                except Exception as e:
                    logger.error(f"[WRE-DISCOVERY] Failed to parse {skill_path}: {e}")

        logger.info(f"[WRE-DISCOVERY] Total discovered: {len(discovered_skills)} skills")
        return discovered_skills

    def discover_by_agent(self, agent_type: str) -> List[DiscoveredSkill]:
        """
        Discover skills for specific agent

        Args:
            agent_type: Agent filter (qwen, gemma, grok, ui-tars)

        Returns:
            Filtered list of skills
        """
        all_skills = self.discover_all_skills()

        filtered = [
            skill for skill in all_skills
            if agent_type in skill.agents or agent_type == skill.agents[0]
        ]

        logger.info(f"[WRE-DISCOVERY] Found {len(filtered)} skills for agent={agent_type}")
        return filtered

    def discover_by_module(self, module_path: str) -> List[DiscoveredSkill]:
        """
        Discover skills for specific module

        Args:
            module_path: Module path (e.g., "modules/communication/livechat")

        Returns:
            Skills belonging to that module
        """
        all_skills = self.discover_all_skills()

        filtered = [
            skill for skill in all_skills
            if str(skill.skill_path).startswith(str(self.repo_root / module_path))
        ]

        logger.info(f"[WRE-DISCOVERY] Found {len(filtered)} skills for module={module_path}")
        return filtered

    def discover_production_ready(self, min_fidelity: float = 0.90) -> List[DiscoveredSkill]:
        """
        Discover skills ready for production promotion

        Args:
            min_fidelity: Minimum pattern fidelity threshold

        Returns:
            Production-ready skills
        """
        all_skills = self.discover_all_skills()

        # Production skills are in modules/*/skills/
        # AND have passed fidelity threshold
        filtered = [
            skill for skill in all_skills
            if skill.promotion_state == "production"
            and skill.metadata.get("pattern_fidelity", 0.0) >= min_fidelity
        ]

        logger.info(f"[WRE-DISCOVERY] Found {len(filtered)} production-ready skills (fidelity>={min_fidelity})")
        return filtered

    def discover_healthy_skills(self) -> List[DiscoveredSkill]:
        """
        Discover all healthy skills (Skills 2.0 hygiene filter).

        Excludes:
        - Retired skills (retirement_date in the past)
        - Skills with invalid/missing category

        Returns:
            List of healthy skills
        """
        all_skills = self.discover_all_skills()
        healthy_skills = []

        for skill in all_skills:
            # Check retirement
            if skill.retirement_date and self._is_retired(skill.retirement_date):
                logger.debug(f"[WRE-DISCOVERY] Excluding retired skill: {skill.skill_name}")
                continue

            # Check category validity
            if skill.category not in {"workflow", "capability-uplift"}:
                logger.debug(
                    f"[WRE-DISCOVERY] Excluding skill with invalid category: "
                    f"{skill.skill_name} (category={skill.category})"
                )
                continue

            healthy_skills.append(skill)

        excluded = len(all_skills) - len(healthy_skills)
        if excluded > 0:
            logger.info(f"[WRE-DISCOVERY] Hygiene filter excluded {excluded}/{len(all_skills)} skills")

        return healthy_skills

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
            logger.warning(f"[WRE-DISCOVERY] Invalid retirement_date format: {retirement_date}")
            return False

    def _parse_skill_file(self, skill_path: Path) -> Optional[DiscoveredSkill]:
        """
        Parse SKILL.md file to extract metadata

        Args:
            skill_path: Path to SKILL.md

        Returns:
            DiscoveredSkill object or None if parsing fails
        """
        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract YAML frontmatter if present
            metadata = self._extract_frontmatter(content)

            # Parse markdown headers if no frontmatter
            if not metadata:
                metadata = self._parse_markdown_headers(content)

            # Infer promotion state from path
            promotion_state = self._infer_promotion_state(skill_path)

            # Extract skill name from directory
            skill_name = skill_path.parent.name

            # Validate required fields
            if not metadata.get("agents"):
                logger.warning(f"[WRE-DISCOVERY] No agents specified in {skill_path}")
                return None

            # Extract Skills 2.0 hygiene fields
            category = metadata.get("category", "")
            retirement_date = metadata.get("retirement_date")
            evals = metadata.get("evals") or []
            has_evals = bool(evals) and len(evals) > 0

            return DiscoveredSkill(
                skill_path=skill_path,
                skill_name=skill_name,
                agents=self._parse_agents(metadata.get("agents", "")),
                intent_type=metadata.get("intent", "GENERAL"),
                version=metadata.get("version", "1.0.0"),
                promotion_state=promotion_state,
                wsp_chain=self._parse_wsp_chain(content),
                metadata=metadata,
                category=category,  # Keep empty for hygiene filter to detect
                retirement_date=str(retirement_date) if retirement_date and retirement_date != "null" else "",
                has_evals=has_evals,
            )

        except Exception as e:
            logger.error(f"[WRE-DISCOVERY] Error parsing {skill_path}: {e}")
            return None

    def _extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """
        Extract YAML frontmatter from SKILL.md

        Format:
        ---
        agents: qwen, gemma
        intent: DECISION
        version: 1.0.0
        ---

        Args:
            content: Full SKILL.md content

        Returns:
            Metadata dict or empty dict
        """
        if not content.startswith('---\n'):
            return {}

        # Find closing ---
        end_idx = content.find('\n---\n', 4)
        if end_idx == -1:
            return {}

        try:
            frontmatter = content[4:end_idx]
            return yaml.safe_load(frontmatter) or {}
        except yaml.YAMLError as e:
            logger.warning(f"[WRE-DISCOVERY] YAML parse error: {e}")
            return {}

    def _parse_markdown_headers(self, content: str) -> Dict[str, Any]:
        """
        Parse markdown headers for metadata (fallback if no YAML frontmatter)

        Looks for:
        **Agents**: Qwen 1.5B, Gemma 270M
        **Intent**: DECISION
        **Version**: 1.0.0

        Args:
            content: SKILL.md content

        Returns:
            Extracted metadata
        """
        metadata = {}

        for line in content.split('\n')[:50]:  # Only check first 50 lines
            line = line.strip()

            # Match **Key**: Value patterns
            if line.startswith('**') and '**:' in line:
                key_end = line.find('**:', 2)
                key = line[2:key_end].lower().replace(' ', '_')
                value = line[key_end + 3:].strip()

                metadata[key] = value

        return metadata

    def _infer_promotion_state(self, skill_path: Path) -> str:
        """
        Infer promotion state from filesystem path

        Rules:
        - .claude/skills/*_prototype/ -> prototype
        - .claude/skills/*_staged/ -> staged
        - modules/*/skills/ -> production

        Args:
            skill_path: Path to SKILL.md

        Returns:
            Promotion state (prototype, staged, production)
        """
        path_str = str(skill_path).replace("\\", "/").lower()

        if '_staged' in path_str:
            return "staged"
        if '_prototype' in path_str or '.claude/skills' in path_str:
            return "prototype"
        if 'modules/' in path_str and ('/skills/' in path_str or '/skillz/' in path_str):
            return "production"
        return "unknown"

    def _parse_agents(self, agents_input) -> List[str]:
        """
        Parse agents string or list into list

        Args:
            agents_input: "Qwen 1.5B, Gemma 270M" or ["qwen", "gemma"] or list

        Returns:
            List of agent names ["qwen", "gemma"]
        """
        if not agents_input:
            return []

        # Handle list input (from YAML)
        if isinstance(agents_input, list):
            agents = [str(a).strip().lower() for a in agents_input]
        # Handle string input
        elif isinstance(agents_input, str):
            agents = [a.strip().lower() for a in agents_input.split(',')]
        else:
            return []

        # Extract agent name (remove model size)
        result = []
        for agent in agents:
            if 'qwen' in agent:
                result.append('qwen')
            elif 'gemma' in agent:
                result.append('gemma')
            elif 'grok' in agent:
                result.append('grok')
            elif 'ui-tars' in agent or 'tars' in agent:
                result.append('ui-tars')

        return result or ['qwen']  # Default to qwen if parsing fails

    def _parse_wsp_chain(self, content: str) -> List[str]:
        """
        Extract WSP references from skill content

        Args:
            content: Full SKILL.md content

        Returns:
            List of WSP references (e.g., ["WSP 96", "WSP 77"])
        """
        wsp_refs = []

        # Look for "WSP XX" patterns
        import re
        matches = re.findall(r'WSP\s+\d+', content, re.IGNORECASE)

        # Deduplicate and normalize
        seen = set()
        for match in matches:
            normalized = match.upper().replace('  ', ' ')
            if normalized not in seen:
                wsp_refs.append(normalized)
                seen.add(normalized)

        return wsp_refs

    def export_discovered_to_registry(
        self,
        output_path: Path,
        discovered_skills: List[DiscoveredSkill]
    ) -> None:
        """
        Export discovered skills to registry JSON format

        Args:
            output_path: Where to write registry JSON
            discovered_skills: Skills to export
        """
        registry = {
            "version": "2.0",
            "description": "Auto-generated from filesystem discovery (Phase 2)",
            "last_updated": None,  # Will be filled by calling code
            "skills": {}
        }

        for skill in discovered_skills:
            try:
                location = str(skill.skill_path.parent.relative_to(self.repo_root))
            except ValueError:
                # Keep export robust for unit tests that use synthetic relative paths.
                location = str(skill.skill_path.parent).replace("\\", "/")

            registry["skills"][skill.skill_name] = {
                "skill_name": skill.skill_name,
                "promotion_state": skill.promotion_state,
                "location": location,
                "primary_agent": skill.agents[0] if skill.agents else "qwen",
                "fallback_agent": skill.agents[1] if len(skill.agents) > 1 else None,
                "intent_type": skill.intent_type,
                "version": skill.version,
                "wsp_chain": skill.wsp_chain,
                "metadata": skill.metadata
            }

        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2)

        logger.info(f"[WRE-DISCOVERY] Exported {len(discovered_skills)} skills to {output_path}")

    def start_watcher(
        self,
        interval_seconds: int = 60,
        on_change_callback: Optional[Callable[[List[DiscoveredSkill]], None]] = None
    ) -> None:
        """
        Start filesystem watcher for hot reload (simple polling-based)

        Args:
            interval_seconds: How often to check for changes (default 60s)
            on_change_callback: Optional callback when skills change

        Usage:
            def on_skills_changed(skills):
                print(f"Skills updated: {len(skills)} found")

            discovery.start_watcher(interval_seconds=30, on_change_callback=on_skills_changed)
        """
        self._watcher_running = True
        self._watcher_thread = Thread(target=self._watcher_loop, args=(interval_seconds, on_change_callback), daemon=True)
        self._watcher_thread.start()
        logger.info(f"[WRE-DISCOVERY] Started filesystem watcher (interval={interval_seconds}s)")

    def stop_watcher(self) -> None:
        """Stop filesystem watcher"""
        self._watcher_running = False
        logger.info("[WRE-DISCOVERY] Stopped filesystem watcher")

    def _watcher_loop(self, interval_seconds: int, on_change_callback: Optional[Callable]) -> None:
        """Internal watcher loop (runs in background thread)"""
        last_count = 0

        while getattr(self, '_watcher_running', False):
            try:
                # Discover skills
                skills = self.discover_all_skills()
                current_count = len(skills)

                # Check if changed
                if current_count != last_count:
                    logger.info(f"[WRE-DISCOVERY] Skills changed: {last_count} -> {current_count}")
                    last_count = current_count

                    # Call callback if provided
                    if on_change_callback:
                        try:
                            on_change_callback(skills)
                        except Exception as e:
                            logger.error(f"[WRE-DISCOVERY] Callback error: {e}")

            except Exception as e:
                logger.error(f"[WRE-DISCOVERY] Watcher error: {e}")

            # Sleep
            time.sleep(interval_seconds)

    # =========================================================================
    # COMMAND ROLODEX INTEGRATION (Step 2: WRE reads orphan CLIs)
    # =========================================================================

    def load_command_rolodex(self, source: str = "sqlite") -> Dict[str, Any]:
        """
        Load command rolodex for CLI discovery.

        Args:
            source: "sqlite" (indexed) or "json" (portable)

        Returns:
            Dict with commands list and metadata
        """
        rolodex_base = self.repo_root / "holo_index" / "docs"

        if source == "sqlite":
            db_path = rolodex_base / "command_rolodex.db"
            if db_path.exists():
                return self._load_rolodex_sqlite(db_path)
            logger.warning("[WRE-DISCOVERY] SQLite rolodex not found, falling back to JSON")

        # Fallback to JSON
        json_path = rolodex_base / "command_rolodex.json"
        if json_path.exists():
            return self._load_rolodex_json(json_path)

        logger.error("[WRE-DISCOVERY] No command rolodex found. Run: python holo_index.py --index-cli")
        return {"commands": [], "total_cli_entrypoints": 0}

    def _load_rolodex_sqlite(self, db_path: Path) -> Dict[str, Any]:
        """Load rolodex from SQLite database."""
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get metadata
        metadata = {}
        cursor.execute("SELECT key, value FROM rolodex_metadata")
        for row in cursor.fetchall():
            metadata[row["key"]] = row["value"]

        # Get commands
        commands = []
        cursor.execute("SELECT * FROM cli_commands ORDER BY line_count DESC")
        for row in cursor.fetchall():
            commands.append(dict(row))

        conn.close()

        return {
            "commands": commands,
            "total_cli_entrypoints": int(metadata.get("total_commands", 0)),
            "wre_connected_count": int(metadata.get("wre_connected_count", 0)),
            "orphan_count": int(metadata.get("orphan_count", 0)),
            "indexed_at": metadata.get("indexed_at"),
        }

    def _load_rolodex_json(self, json_path: Path) -> Dict[str, Any]:
        """Load rolodex from JSON file."""
        import json
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def discover_orphan_clis(
        self,
        min_line_count: int = 100,
        has_json_flag: Optional[bool] = None,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Discover orphan CLIs that need SKILLz.md wrappers.

        Args:
            min_line_count: Minimum lines to be considered substantial
            has_json_flag: Filter by JSON support (True/False/None for all)
            category: Filter by category (e.g., "cadence:continuous")
            limit: Max results to return

        Returns:
            List of orphan CLI dicts sorted by line_count (most substantial first)
        """
        rolodex = self.load_command_rolodex()
        orphans = []

        for cmd in rolodex.get("commands", []):
            # Skip WRE-connected
            if cmd.get("wre_connected"):
                continue

            # Apply filters
            if cmd.get("line_count", 0) < min_line_count:
                continue
            if has_json_flag is not None and cmd.get("has_json_flag") != has_json_flag:
                continue
            if category and cmd.get("category") != category:
                continue

            orphans.append(cmd)

        # Sort by line_count descending
        orphans.sort(key=lambda x: x.get("line_count", 0), reverse=True)

        logger.info(f"[WRE-DISCOVERY] Found {len(orphans)} orphan CLIs (limit={limit})")
        return orphans[:limit]

    def suggest_skillz_md_for_orphan(self, orphan_cli: Dict[str, Any]) -> str:
        """
        Generate SKILLz.md template for an orphan CLI.

        This enables Gemma pattern-matching to suggest WRE connection.

        Args:
            orphan_cli: Dict from discover_orphan_clis()

        Returns:
            SKILLz.md template content
        """
        from datetime import datetime

        module_name = orphan_cli.get("module_name", "unknown")
        path = orphan_cli.get("path", "")
        trigger = orphan_cli.get("suggested_trigger", "manual")
        has_json = orphan_cli.get("has_json_flag", False)
        line_count = orphan_cli.get("line_count", 0)

        # Extract skill name from module path
        parts = module_name.split(".")
        skill_name = parts[-1] if parts else "unknown_skill"

        # Determine primary agent based on trigger type
        if "cadence:continuous" in trigger:
            primary_agent = "qwen"
            intent_type = "TELEMETRY"
        elif "event:" in trigger:
            primary_agent = "qwen"
            intent_type = "DECISION"
        else:
            primary_agent = "gemma"
            intent_type = "CLASSIFICATION"

        template = f'''---
name: {skill_name}
description: Auto-generated wrapper for {module_name}
version: 1.0_prototype
author: orphan_capability_scanner
created: {datetime.now().strftime("%Y-%m-%d")}
agents: [{primary_agent}]
primary_agent: {primary_agent}
intent_type: {intent_type}
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: auto_generated
evals: []
trigger:
  {trigger}
---
# {skill_name.replace("_", " ").title()}

## Purpose
WRE wrapper for `{path}` ({line_count} lines)

## CLI Interface
```bash
python {path.replace(chr(92), "/")} --help
{"python " + path.replace(chr(92), "/") + " --json" if has_json else "# TODO: Add --json support per WSP 103"}
```

## Instructions (For AI Agent)

### 1. VALIDATE_PRECONDITIONS
**Rule**: Before execution, verify required state
**Expected Pattern**: preconditions_validated=True

### 2. EXECUTE_CLI
**Rule**: Run the CLI command with appropriate flags
**Expected Pattern**: cli_executed=True

### 3. VALIDATE_OUTPUT
**Rule**: Check output for success/failure indicators
**Expected Pattern**: output_validated=True

## Benchmark Test Cases

### Test Set 1: Basic Execution
1. Input: `--help` → Expected: Usage information displayed
2. Input: `--status` → Expected: Status JSON (if supported)

## Success Criteria

- ✅ Pattern fidelity ≥ 85%
- ✅ CLI executes without error
- ✅ Output matches expected format
'''
        return template

    def get_orphan_reduction_progress(self) -> Dict[str, Any]:
        """
        Get metrics on orphan CLI reduction progress.

        Returns:
            Dict with progress metrics for observability
        """
        rolodex = self.load_command_rolodex()

        total = rolodex.get("total_cli_entrypoints", 0)
        connected = rolodex.get("wre_connected_count", 0)
        orphans = rolodex.get("orphan_count", 0)

        return {
            "total_clis": total,
            "wre_connected": connected,
            "orphans": orphans,
            "connection_rate": round(connected / total * 100, 2) if total > 0 else 0,
            "indexed_at": rolodex.get("indexed_at"),
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    discovery = WRESkillsDiscovery()

    # Example 1: Discover all skills
    print("\n[EXAMPLE 1] Discover all skills:")
    all_skills = discovery.discover_all_skills()
    print(f"  Found: {len(all_skills)} skills")
    for skill in all_skills[:5]:  # Show first 5
        print(f"    - {skill.skill_name} ({skill.agents[0]}, {skill.promotion_state})")

    # Example 2: Discover Qwen skills
    print("\n[EXAMPLE 2] Discover Qwen skills:")
    qwen_skills = discovery.discover_by_agent("qwen")
    print(f"  Found: {len(qwen_skills)} Qwen skills")

    # Example 3: Discover production-ready skills
    print("\n[EXAMPLE 3] Discover production-ready skills:")
    production_skills = discovery.discover_production_ready(min_fidelity=0.90)
    print(f"  Found: {len(production_skills)} production-ready skills")

    print("\n[OK] WRE Skills Discovery complete")
