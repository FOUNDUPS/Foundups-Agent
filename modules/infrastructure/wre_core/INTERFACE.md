# wre_core Interface Specification

**WSP 11 Compliance:** Phase 3 Complete ✅
**Last Updated:** 2026-03-25
**Version:** 0.7.2

## Overview

`wre_core` is the wardrobe for native skills. It discovers `modules/*/skills/**/SKILL.md`, validates metadata, executes skills via local Qwen inference, validates output with Gemma, and records pattern fidelity for recursive evolution. `.claude/skills/` remains the prototype space; WRE promotes validated skills into production.

**Phase 3 Status**: HoloDAE integration + autonomous skill execution COMPLETE

## 2026-02-19 API Alignment Delta

- Discovery implementations MUST support both `SKILLz.md` (preferred) and `SKILL.md` (legacy fallback).
- Discovery path inference MUST treat both `.../skills/...` and `.../skillz/...` as production wardrobes.
- `PatternMemory(db_path=...)` MUST create isolated storage (no shared singleton reuse).
- `WREMasterOrchestrator` compatibility API:
  - `register_plugin(plugin_instance)` and `register_plugin("name", plugin_instance)` are both supported.
  - `get_plugin(plugin_name)` returns registered plugin or `None`.
  - `validate_module_path(path)` validates module existence under repo root.
- Runtime storage override:
  - `WRE_PATTERN_MEMORY_DB=<path>` binds orchestrator runtime storage to explicit DB path.

## Public API

### Data Structures

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class WRESkill:
    """Immutable skill descriptor (trainable weight)."""
    skill_id: str              # e.g. youtube_moderation.v1
    path: Path                 # Path to SKILL.md
    agents: List[str]          # ['qwen', 'gemma', 'ui_tars']
    wsp_chain: List[str]       # ['WSP 50', 'WSP 64', 'WSP 77']
    domains: List[str]         # ['streaming', 'compliance']
    version: str               # 1.0.0
    pattern_fidelity: float    # Last recorded score (0.0-1.0)
```

```python
@dataclass
class SkillSession:
    """Runtime binding of a skill to an execution request."""
    skill: WRESkill
    context: Dict[str, str]        # Task metadata (module, intent, run_id)
    tokens_budget: int             # Target 50-200 per WSP 75
    feedback_hook: Optional[str]   # Path to metrics sink
```

### Core Services

```python
class WRESkillsRegistry:
    def discover(self, roots: Optional[List[Path]] = None) -> List[WRESkill]:
        """Scan for SKILL.md files, parse YAML frontmatter, validate WSP citations."""

    def refresh(self) -> None:
        """Hot reload registry when files change (Occam: glob + hash, no DB)."""

    def get(self, skill_id: str) -> Optional[WRESkill]:
        """Return skill by id/version."""
```

```python
class WRESkillLoader:
    def __init__(self, registry: WRESkillsRegistry) -> None:
        self.registry = registry

    def mount(self, skill_id: str, task: Dict[str, str]) -> SkillSession:
        """Create SkillSession for Qwen/Gemma. Raises WREInvalidSkill on failure."""

    def record_feedback(self, session: SkillSession, fidelity: float, notes: str) -> None:
        """Persist pattern fidelity to recursive_improvement/metrics."""
```

```python
class WRESkillPromoter:
    def promote(self, prototype_path: Path, target_module: Path) -> WRESkill:
        """
        Copy `.claude/skills/.../SKILL.md` into module wardrobe, stamp CHANGELOG,
        register with registry. Uses WSP 50 approval before activation.
        """
```

### Phase 1: Libido Monitor & Pattern Memory (NEW - v0.3.0)

```python
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

class LibidoSignal(Enum):
    """Pattern activation frequency control signals"""
    CONTINUE = "continue"      # Frequency OK, proceed with execution
    THROTTLE = "throttle"      # Hit max frequency, skip execution
    ESCALATE = "escalate"      # Below min frequency, force execution

class GemmaLibidoMonitor:
    """
    Pattern frequency sensor - monitors skill activation frequency.

    IBM Typewriter Analogy: Paper feed sensor that monitors typing frequency.
    Gemma (270M) provides <10ms binary classification: CONTINUE, THROTTLE, or ESCALATE.

    Per WSP 96 v1.3: Micro Chain-of-Thought paradigm.
    """

    def __init__(
        self,
        history_size: int = 100,
        default_min_frequency: int = 1,
        default_max_frequency: int = 5,
        default_cooldown_seconds: int = 600
    ) -> None:
        """Initialize libido monitor with frequency thresholds."""

    def should_execute(
        self,
        skill_name: str,
        execution_id: str,
        force: bool = False
    ) -> LibidoSignal:
        """
        Check if skill should execute based on pattern frequency.

        Returns:
            LibidoSignal.CONTINUE - Proceed with execution
            LibidoSignal.THROTTLE - Skip execution (too frequent)
            LibidoSignal.ESCALATE - Force execution (below minimum)
        """

    def record_execution(
        self,
        skill_name: str,
        agent: str,
        execution_id: str,
        fidelity_score: Optional[float] = None
    ) -> None:
        """Record skill execution in pattern history."""

    def validate_step_fidelity(
        self,
        step_output: Dict,
        expected_patterns: List[str]
    ) -> float:
        """
        Gemma validates if Qwen followed skill instructions for a single step.

        Per WSP 96 v1.3: Micro Chain-of-Thought paradigm.
        Each step in skill execution is validated before proceeding.

        Args:
            step_output: Qwen's output for this step (dict with keys)
            expected_patterns: List of required output keys/patterns

        Returns:
            Fidelity score (0.0-1.0)
        """

    def get_skill_statistics(self, skill_name: str) -> Dict:
        """Get execution statistics for a skill."""

    def set_thresholds(
        self,
        skill_name: str,
        min_frequency: int,
        max_frequency: int,
        cooldown_seconds: int
    ) -> None:
        """Set custom thresholds for a skill."""

    def export_history(self, output_path: Path) -> None:
        """Export pattern history to JSON for analysis."""

@dataclass
class SkillOutcome:
    """
    Record of skill execution outcome for recursive learning.

    Per WSP 96: Skills are trainable weights that evolve.
    """
    execution_id: str
    skill_name: str
    agent: str                  # qwen, gemma, grok, ui-tars
    timestamp: str              # ISO format
    input_context: str          # JSON string
    output_result: str          # JSON string
    success: bool
    pattern_fidelity: float     # 0.0-1.0 from Gemma validation
    outcome_quality: float      # 0.0-1.0 correctness score
    execution_time_ms: int
    step_count: int             # Number of steps in micro chain-of-thought
    failed_at_step: Optional[int] = None
    notes: Optional[str] = None

class PatternMemory:
    """
    SQLite storage for skill outcomes and recursive learning.

    Per WSP 60: Enable recall instead of computation.
    Per WSP 48: Store outcomes for self-improvement.

    Database Schema:
    - skill_outcomes: Execution records
    - skill_variations: A/B test variations
    - learning_events: Pattern improvement events

    Known producers (2026-02):
    - WRE master orchestrator execution pipeline
    - OpenClawDAE validation/remember phase
    - Standalone Claw action runner (`modules.communication.moltbot_bridge.src.action_cli`)
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize pattern memory database."""

    def store_outcome(self, outcome: SkillOutcome) -> None:
        """Store skill execution outcome."""

    def recall_successful_patterns(
        self,
        skill_name: str,
        min_fidelity: float = 0.90,
        limit: int = 10
    ) -> List[Dict]:
        """
        Recall successful execution patterns for a skill.

        Per WSP 60: Recall instead of compute (50-200 tokens vs 5000+)

        Returns:
            List of successful execution records sorted by fidelity DESC
        """

    def recall_failure_patterns(
        self,
        skill_name: str,
        max_fidelity: float = 0.70,
        limit: int = 10
    ) -> List[Dict]:
        """Recall failed execution patterns for learning."""

    def get_skill_metrics(self, skill_name: str, days: int = 7) -> Dict:
        """
        Get aggregated metrics for a skill over time period.

        Returns:
            Dict with avg_fidelity, success_rate, execution_count, etc.
        """

    def store_variation(
        self,
        variation_id: str,
        skill_name: str,
        variation_content: str,
        parent_version: Optional[str] = None,
        created_by: str = "qwen"
    ) -> None:
        """Store skill variation for A/B testing."""

    def record_learning_event(
        self,
        event_id: str,
        skill_name: str,
        event_type: str,
        description: str,
        before_fidelity: Optional[float] = None,
        after_fidelity: Optional[float] = None,
        variation_id: Optional[str] = None,
        continuity_id: Optional[str] = None,
        parent_continuity_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> None:
        """
        Record learning event for skill evolution tracking with continuity lineage.

        Event types: variation_created, variation_promoted, threshold_tuned, rollback

        Per WSP 91: Observability with continuity metadata
        Per WSP 97: Answers "what work led to this evolved skill?"

        Args:
            continuity_id: Links event to continuity work chain
            parent_continuity_id: Parent continuity for lineage tracking
            execution_id: Execution ID that triggered this evolution
        """

    def get_evolution_history(self, skill_name: str) -> List[Dict]:
        """Get evolution history for a skill (includes continuity metadata)."""

    def get_evolution_by_continuity(
        self,
        continuity_id: str,
        include_children: bool = False
    ) -> List[Dict]:
        """
        Get evolution events linked to a continuity chain.

        Per WSP 91: Answer "what work led to this evolved skill?"

        Args:
            continuity_id: Continuity ID to query
            include_children: If True, also return events where this is the parent

        Returns:
            List of learning events linked to this continuity chain
        """

    def get_evolution_by_execution(self, execution_id: str) -> List[Dict]:
        """
        Get evolution events triggered by a specific execution.

        Args:
            execution_id: Execution ID to query

        Returns:
            List of learning events triggered by this execution
        """

    def close(self) -> None:
        """Close database connection."""

class WREMasterOrchestrator:
    """
    Central hub integrating libido monitor, pattern memory, and skills loader.

    Per WSP 96 v1.3: Full WRE Skills Wardrobe execution pipeline.
    """

    def __init__(self) -> None:
        """Initialize orchestrator with all WRE components."""
        # Original components
        self.pattern_memory: PatternMemory
        self.wsp_validator: WSPValidator
        self.plugins: Dict[str, OrchestratorPlugin]

        # Phase 1 components (NEW in v0.3.0)
        self.libido_monitor: GemmaLibidoMonitor
        self.sqlite_memory: PatternMemory
        self.skills_loader: WRESkillsLoader

    def execute_skill(
        self,
        skill_name: str,
        agent: str,
        input_context: Dict,
        force: bool = False
    ) -> Dict:
        """
        Execute skill with libido monitoring and outcome storage.

        Pipeline:
        1. Check libido (should we execute now?)
        2. Load skill instructions
        3. Execute skill (Qwen/Gemma coordination)
        4. Calculate execution time
        5. Validate with Gemma (pattern fidelity)
        6. Record execution in libido monitor
        7. Store outcome in pattern memory

        Args:
            skill_name: Name of skill to execute
            agent: Agent to execute skill (qwen, gemma, grok, ui-tars)
            input_context: Input parameters for skill
            force: Force execution regardless of libido (0102 override)

        Returns:
            Dict with success, pattern_fidelity, execution_id, execution_time_ms
        """

    def validate_module_path(self, module_path: Path) -> bool:
        """Validate module path exists."""

    def register_plugin(self, name: str, plugin: OrchestratorPlugin) -> None:
        """Register orchestrator plugin."""

    def get_plugin(self, name: str) -> Optional[OrchestratorPlugin]:
        """Get registered plugin by name."""
```

### Phase 2: Filesystem Skills Discovery (NEW - v0.4.0)

```python
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

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

class WRESkillsDiscovery:
    """
    Filesystem-based skills discovery for WRE Phase 2

    Scans filesystem for SKILL.md files without requiring skills_registry.json.
    Enables dynamic skill discovery and automatic promotion state inference.

    Per WSP 96 v1.3: Skills are discovered from filesystem, not hardcoded registry.
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        """Initialize skills discovery with repository root."""

    def discover_all_skills(self) -> List[DiscoveredSkill]:
        """
        Scan filesystem for all SKILL.md files

        Scan Patterns:
        - modules/*/*/skills/**/SKILL.md (production skills)
        - .claude/skills/**/SKILL.md (prototype skills)
        - holo_index/skills/**/SKILL.md (holo skills)

        Returns:
            List of discovered skills (both registered and unregistered)
        """

    def discover_by_agent(self, agent_type: str) -> List[DiscoveredSkill]:
        """
        Discover skills for specific agent

        Args:
            agent_type: Agent filter (qwen, gemma, grok, ui-tars)

        Returns:
            Filtered list of skills
        """

    def discover_by_module(self, module_path: str) -> List[DiscoveredSkill]:
        """
        Discover skills for specific module

        Args:
            module_path: Module path (e.g., "modules/communication/livechat")

        Returns:
            Skills belonging to that module
        """

    def discover_production_ready(self, min_fidelity: float = 0.90) -> List[DiscoveredSkill]:
        """
        Discover skills ready for production promotion

        Args:
            min_fidelity: Minimum pattern fidelity threshold

        Returns:
            Production-ready skills
        """

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
```

### Skills 2.0 Hygiene API (NEW - v0.7.1)

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class SkillHygieneStatus:
    """Result of skill hygiene check per Skills 2.0 specification."""
    skill_name: str
    is_healthy: bool
    is_retired: bool = False
    retirement_date: Optional[str] = None
    missing_category: bool = False
    category: Optional[str] = None
    has_evals: bool = False
    issues: List[str] = field(default_factory=list)

# Extended SkillMetadata with Skills 2.0 fields
@dataclass
class SkillMetadata:
    """Skill descriptor with Skills 2.0 hygiene fields."""
    name: str
    description: str
    primary_agent: str
    intent_type: str
    promotion_state: str
    location: Path
    pattern_fidelity_threshold: float
    # Skills 2.0 hygiene fields
    category: str = "workflow"              # workflow | capability-uplift
    retirement_date: str = ""               # ISO date or empty
    has_evals: bool = False                 # Has eval test cases

# Extended DiscoveredSkill with Skills 2.0 fields
@dataclass
class DiscoveredSkill:
    """Filesystem-discovered skill with hygiene fields."""
    skill_path: Path
    skill_name: str
    agents: List[str]
    intent_type: str
    version: str
    promotion_state: str
    wsp_chain: List[str]
    metadata: Dict[str, Any]
    # Skills 2.0 hygiene fields
    category: str = "workflow"
    retirement_date: str = ""
    has_evals: bool = False
```

#### WRESkillsLoader Hygiene Methods

```python
class WRESkillsLoader:
    """Extended with Skills 2.0 hygiene enforcement."""

    def check_skill_hygiene(self, skill_name: str) -> SkillHygieneStatus:
        """
        Check skill hygiene per Skills 2.0 specification.

        Validates:
        - retirement_date: If set and past, skill is retired
        - category: Must be 'workflow' or 'capability-uplift'
        - evals: Presence of eval test cases

        Returns:
            SkillHygieneStatus with is_healthy=True if all checks pass
        """

    def _is_retired(self, retirement_date: Optional[str]) -> bool:
        """
        Check if retirement_date indicates skill is retired.

        Args:
            retirement_date: ISO date string, 'null', '', or None

        Returns:
            True if date is in the past, False otherwise
        """

    def list_healthy_skills(self) -> List[str]:
        """
        List skill names that pass hygiene checks.

        Excludes:
        - Retired skills (retirement_date in past)
        - Skills with invalid/missing category

        Returns:
            List of healthy skill names
        """

    def discover_healthy_skills(self) -> List[SkillMetadata]:
        """
        Discover and return only healthy skills.

        Returns:
            List of SkillMetadata for skills passing hygiene checks
        """

    def load_skill(
        self,
        skill_name: str,
        agent: str,
        enforce_hygiene: bool = True
    ) -> str:
        """
        Load skill content with hygiene enforcement.

        Args:
            skill_name: Name of skill to load
            agent: Agent requesting the skill
            enforce_hygiene: If True (default), raises ValueError for retired skills

        Returns:
            Skill content string

        Raises:
            ValueError: If enforce_hygiene=True and skill is retired
        """
```

#### WRESkillsDiscovery Hygiene Methods

```python
class WRESkillsDiscovery:
    """Extended with Skills 2.0 hygiene filtering."""

    def _is_retired(self, retirement_date: Optional[str]) -> bool:
        """Check if retirement_date indicates skill is retired."""

    def discover_healthy_skills(self) -> List[DiscoveredSkill]:
        """
        Discover skills that pass hygiene checks.

        Filters out:
        - Retired skills (retirement_date in past)
        - Skills with invalid category (not workflow/capability-uplift)

        Returns:
            List of healthy DiscoveredSkill instances
        """
```

#### Valid Categories

```python
VALID_SKILL_CATEGORIES = {"workflow", "capability-uplift"}
```

- **workflow**: Standard operational skills (permanent)
- **capability-uplift**: Gap-filling skills (deprecated once capability goes native)

### Phase 3: HoloDAE Integration (NEW - v0.6.0)

```python
from typing import Dict, Any, List

class HoloDAECoordinator:
    """
    HoloDAE monitoring coordinator with WRE Skills integration.

    Per WSP 96 v1.3 Phase 3: Autonomous skill execution based on health checks.
    """

    def check_git_health(self) -> Dict[str, Any]:
        """
        Check git repository health for autonomous skill triggering.

        Returns:
            Dict containing:
            - uncommitted_changes (int): Number of uncommitted files
            - files_changed (List[str]): List of changed files (first 10)
            - time_since_last_commit (int): Seconds since last commit
            - trigger_skill (Optional[str]): Skill to trigger (e.g., "qwen_gitpush")
            - healthy (bool): True if uncommitted_changes < 20

        Trigger Conditions:
            - Triggers qwen_gitpush if >5 files AND >1 hour since last commit
        """

    def check_daemon_health(self) -> Dict[str, Any]:
        """
        Check daemon health status for autonomous monitoring.

        Returns:
            Dict containing:
            - youtube_dae_running (bool): YouTube DAE status
            - mcp_daemon_running (bool): MCP daemon status
            - unhealthy_daemons (List[str]): List of unhealthy daemon names
            - trigger_skill (Optional[str]): Skill to trigger (e.g., "daemon_health_monitor")
            - healthy (bool): True if no unhealthy daemons
        """

    def check_wsp_compliance(self) -> Dict[str, Any]:
        """
        Check WSP protocol compliance for autonomous validation.

        Returns:
            Dict containing:
            - violations_found (int): Number of WSP violations
            - violation_details (List[Dict]): Details of each violation
            - trigger_skill (Optional[str]): Skill to trigger (e.g., "wsp_compliance_fixer")
            - healthy (bool): True if no violations
        """

    def _check_wre_triggers(self, result: 'MonitoringResult') -> List[Dict[str, Any]]:
        """
        Check monitoring result for WRE skill trigger conditions.

        Analyzes health checks and determines if any skills should be triggered.

        Args:
            result: Monitoring result from _monitoring_loop()

        Returns:
            List of trigger dicts, each containing:
            - skill_name (str): Name of skill to execute
            - agent (str): Agent to execute skill (qwen, gemma, etc.)
            - input_context (Dict): Input parameters for skill
            - trigger_reason (str): Why skill was triggered
            - priority (str): Execution priority (high, medium, low)
        """

    def _execute_wre_skills(self, triggers: List[Dict[str, Any]]) -> None:
        """
        Execute WRE skills based on monitoring triggers.

        Loads WRE Master Orchestrator and executes each triggered skill.
        Logs success/throttle/error for each execution.

        Args:
            triggers: List of skill triggers from _check_wre_triggers()
        """
```

### Error Model

```python
class WREInterfaceError(Exception): ...
class WREInvalidSkill(WREInterfaceError): ...
class WREValidationError(WREInterfaceError): ...
class WREPromotionError(WREInterfaceError): ...
```

## Usage

### Basic Skill Mount
```python
from modules.infrastructure.wre_core import WRESkillsRegistry, WRESkillLoader

registry = WRESkillsRegistry()
registry.refresh()

loader = WRESkillLoader(registry)

session = loader.mount(
    skill_id="youtube_moderation.v1",
    task={
        "module": "modules/communication/livechat",
        "intent": "stream_start_watchdog",
        "run_id": "2025-10-20T09:58:00Z"
    }
)

qwen.apply_skill(session)   # Executes workflow at 50-200 tokens
```

### Recording Pattern Fidelity
```python
loader.record_feedback(
    session,
    fidelity=0.92,
    notes="Gemma scoring PASS (intent coverage + escalation rule triggered)."
)
```

### Promoting from `.claude/skills`
```python
from modules.infrastructure.wre_core import WRESkillPromoter

promoter = WRESkillPromoter()
production_skill = promoter.promote(
    prototype_path=Path(".claude/skills/youtube_moderation_prototype/SKILL.md"),
    target_module=Path("modules/communication/livechat/skills/youtube_moderation")
)
```

## Configuration

```python
WRE_SKILLS_CONFIG = {
    "watch_paths": [
        "modules/**/skills/**/SKILL.md",
        ".claude/skills/**/SKILL.md"
    ],
    "metadata_required": ["skill_id", "version", "agents", "dependencies", "wsp_chain"],
    "pattern_threshold": 0.90,   # Minimum fidelity before promotion
    "metrics_dir": "modules/infrastructure/wre_core/recursive_improvement/metrics",
    "promotion_log": "modules/infrastructure/wre_core/skills/CHANGELOG.md"
}
```

### Environment Hooks
- `WRE_SKILLS_AUTO_REFRESH` (`true`/`false`) – enable watcher thread
- `WRE_SKILLS_MAX_TOKENS` (default `200`) – cap per execution
- `WRE_SKILLS_SANDBOX` (`true`/`false`) – dry-run promotion without copying files

## Dependencies

| Dependency | Purpose |
|------------|---------|
| `pyyaml` | Parse SKILL.md frontmatter |
| `watchdog` | Optional filesystem watcher for hot reload |
| `jsonschema` (future) | Validate advanced skill metadata |
| `modules.infrastructure.recursive_improvement` | Persist metrics |
| `modules.holo_index` | Re-index skills after promotion (WSP 50) |

## Testing

```bash
cd modules/infrastructure/wre_core
python -m pytest tests/test_skills_registry.py
python -m pytest tests/test_skill_loader.py
```

### Coverage Goals
- Registry discovery paths (≥ 95%)
- Metadata validation (≥ 90%)
- Promotion happy path + failure modes (≥ 90%)
- Feedback persistence (≥ 90%)

## Performance Expectations

| Operation | Target |
|-----------|--------|
| Registry refresh | < 300 ms for 200 skills |
| Skill mount | < 50 ms |
| Feedback write | < 20 ms |

## Error Handling

- **WREInvalidSkill** – Missing metadata, unsupported agent, or invalid WSP chain
- **WREValidationError** – Promotion blocked by WSP 50 / WSP 64 guard
- **WREPromotionError** – Filesystem issues during prototype → wardrobe copy

## Version History

### 0.7.1 (2026-03-25) - Skills 2.0 Hygiene Enforcement
- **IMPLEMENTED**: `SkillHygieneStatus` dataclass for hygiene check results
- **EXTENDED**: `SkillMetadata` with Skills 2.0 fields (category, retirement_date, has_evals)
- **EXTENDED**: `DiscoveredSkill` with Skills 2.0 fields
- **IMPLEMENTED**: `check_skill_hygiene()` - Full hygiene validation
- **IMPLEMENTED**: `_is_retired()` - ISO date retirement detection
- **IMPLEMENTED**: `list_healthy_skills()` - Filter healthy skills by name
- **IMPLEMENTED**: `discover_healthy_skills()` - Filter healthy SkillMetadata/DiscoveredSkill
- **UPDATED**: `load_skill()` with `enforce_hygiene` parameter (blocks retired skills)
- **ADDED**: `test_wre_skills_loader_hygiene.py` (18 tests - ALL PASSED)
- **ADDED**: `TestSkillsHygiene` class in discovery tests (7 tests - ALL PASSED)
- **DOCUMENTED**: Valid categories: workflow, capability-uplift

### 0.5.0 (2025-10-24) - Phase 2 Complete
- **IMPLEMENTED**: `_execute_skill_with_qwen()` - Local Qwen inference integration (wre_master_orchestrator.py:282-383)
- **INTEGRATED**: QwenInferenceEngine from holo_index/qwen_advisor/llm_engine.py
- **FIXED**: Gemma validation API to use correct signature (step_output + expected_patterns)
- **ADDED**: Graceful fallback if llama-cpp-python or model files unavailable
- **ADDED**: Filesystem watcher (start_watcher/stop_watcher) for hot reload
- **ADDED**: test_qwen_inference_wiring.py (4 integration tests - ALL PASSED)
- **UPDATED**: requirements.txt to document llama-cpp-python dependency
- **UPDATED**: ModLog.md with Phase 2 completion details
- **UPDATED**: INTERFACE.md (v0.4.0 → v0.5.0)

### 0.4.0 (2025-10-24) - Phase 2 Filesystem Discovery
- **IMPLEMENTED**: `WRESkillsDiscovery` - Filesystem scanner for SKILL.md files (416 lines)
- **IMPLEMENTED**: `discover_all_skills()` - Scans modules/*/*/skills/**/SKILL.md, .claude/skills/**/SKILL.md, holo_index/skills/**/SKILL.md
- **IMPLEMENTED**: `discover_by_agent()`, `discover_by_module()`, `discover_production_ready()` filtering
- **ADDED**: YAML frontmatter parsing (handles both string and list agents)
- **ADDED**: Markdown header fallback parsing
- **ADDED**: Promotion state inference from filesystem path
- **ADDED**: WSP chain extraction via regex
- **UPDATED**: ModLog.md with Phase 2 entry
- **UPDATED**: INTERFACE.md (v0.3.0 → v0.4.0)

### 0.3.0 (2025-10-24) - Phase 1 Complete
- **IMPLEMENTED**: `GemmaLibidoMonitor` - Pattern frequency sensor (<10ms binary classification)
- **IMPLEMENTED**: `PatternMemory` - SQLite recursive learning storage (skill_outcomes, skill_variations, learning_events)
- **IMPLEMENTED**: `WREMasterOrchestrator.execute_skill()` - Full execution pipeline with libido monitoring
- **ADDED**: Comprehensive test suites (test_libido_monitor.py, test_pattern_memory.py, test_wre_master_orchestrator.py)
- **ADDED**: requirements.txt for WSP 49 compliance
- **UPDATED**: ModLog.md entries for wre_core and git_push_dae
- **DOCUMENTED**: Micro chain-of-thought paradigm (WSP 96 v1.3)

### 0.2.0 (2025-10-20)
- Drafted skills-aware API (`WRESkillsRegistry`, `WRESkillLoader`, `WRESkillPromoter`)
- Added configuration schema and promotion workflow
- Documented feedback loop for pattern fidelity scoring

### 0.1.0 (2025-09-25)
- Initial placeholder interface for WSP 11 compliance

## Development Notes

### Phase 1 ✅ (Completed 2025-10-24)
- [x] Libido monitor, pattern memory, execute_skill() pipeline
- [x] Comprehensive test coverage (65+ tests)
- [x] WSP 5, WSP 22, WSP 49 compliance

### Phase 2 ✅ (Completed 2025-10-24)
- [x] Filesystem skills discovery implemented (wre_skills_discovery.py)
- [x] Filesystem watcher for hot reload (start_watcher/stop_watcher)
- [x] Wired execute_skill() to local Qwen inference (_execute_skill_with_qwen)
- [x] Graceful fallback if llama-cpp-python unavailable
- [x] Fixed Gemma validation API integration
- [x] Created test_wre_skills_discovery.py (20+ tests)
- [x] Created test_qwen_inference_wiring.py (4 integration tests - ALL PASSED)
- [x] Documentation updated (ModLog, INTERFACE, requirements.txt)

### Phase 3 (Roadmap)
- [ ] Convergence loop (autonomous skill promotion based on fidelity)
- [ ] Add Gemma/Grok/UI-TARS inference support (currently Qwen only)
- [ ] MCP server integration (if remote inference needed)
- [ ] Promotion CLI helpers
- [ ] Real-world skill execution validation

---

### Memory Preflight Guard (NEW - v0.7.0)

```python
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class ArtifactInfo:
    """Information about a single memory artifact."""
    path: str
    relative_path: str
    tier: int               # 0, 1, or 2
    required: bool          # True for Tier-0 mandatory artifacts
    exists: bool
    last_updated: Optional[str]
    why_retrieved: str

@dataclass
class MemoryBundle:
    """Structured memory bundle for orchestration."""
    module_path: str
    artifacts: List[ArtifactInfo]
    missing_required: List[str]
    missing_optional: List[str]
    duplication_rate_proxy: float
    ordering_confidence: Optional[float]
    staleness_risk: Optional[str]
    tier0_complete: bool
    preflight_passed: bool
    stubs_created: List[str]

class MemoryPreflightGuard:
    """
    Enforces WSP_CORE Memory System by requiring tiered retrieval
    and Tier-0 artifact presence before code-changing operations.

    Per WSP_CORE Section 3: Mandatory Start-of-Work Loop
    Per WSP_00 Section 3.4: Post-Awakening Operational Protocol

    Environment Variables:
        WRE_MEMORY_PREFLIGHT_ENABLED: Enable preflight (default: true)
        WRE_MEMORY_AUTOSTUB_TIER0: Auto-create stubs (default: false)
        WRE_MEMORY_ALLOW_DEGRADED: Allow with warnings (default: false)
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize Memory Preflight Guard."""

    def run_preflight(self, module_path: str) -> MemoryBundle:
        """
        Run memory preflight check for a module.

        Executes WSP_CORE Start-of-Work Loop:
        1. Tiered retrieval (Tier 0 -> 1 -> 2)
        2. Evaluate retrieval quality
        3. Auto-stub Tier-0 if enabled and missing
        4. Return structured Memory Bundle

        Args:
            module_path: Relative path to module

        Returns:
            MemoryBundle with retrieval results

        Raises:
            MemoryPreflightError: If Tier-0 missing and autostub disabled
        """

class MemoryPreflightError(Exception):
    """Raised when memory preflight check fails."""
    missing_files: List[str]
    module_path: str
    required_action: str

def check_memory_preflight(module_path: str) -> MemoryBundle:
    """Convenience function to run memory preflight check."""

def require_memory_preflight(func):
    """Decorator to enforce memory preflight before operations."""
```

**First Principles:** Keep the wardrobe simple. One registry, one loader, one promoter. Everything else (versioning, A/B tests, telemetry) builds on top after the entry point works.
