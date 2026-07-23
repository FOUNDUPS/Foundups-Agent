#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Natural-language schedule evaluator for OpenClaw routines.

Supports deterministic parsing of schedule phrases like:
- "run self research daily"
- "run nightly queue audit"
- "run grant watchlist refresh every morning"

Schedules persist across runs and execute through existing native paths.
WSP-Compliant: WSP 27 (DAE Architecture), WSP 60 (Memory Architecture)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules.infrastructure.idle_automation.src.schedule_claim_state import (
    ScheduleClaim,
    ScheduleClaimOps,
    ScheduleClaimStore,
    ScheduleWindow,
    build_execution_id,
)

logger = logging.getLogger(__name__)

# Supported routines - these must map to existing safe native paths
SUPPORTED_ROUTINES = {
    "self_research": {
        "description": "Run self-research refresh (index, compliance, watchlists)",
        "aliases": ["self research", "self-research", "research"],
    },
    "queue_audit": {
        "description": "Rebuild and audit native execution queue",
        "aliases": ["queue audit", "queue refresh", "execution queue", "queue"],
    },
    "grant_watchlist": {
        "description": "Refresh external grant watchlist",
        "aliases": ["grant watchlist", "grant refresh", "grants", "watchlist"],
    },
}

# Cadence definitions with preferred execution windows (hour ranges, UTC)
CADENCE_WINDOWS = {
    "daily": {"start_hour": 0, "end_hour": 24, "description": "Once per calendar day"},
    "nightly": {"start_hour": 0, "end_hour": 6, "description": "Between midnight and 6am"},
    "morning": {"start_hour": 6, "end_hour": 12, "description": "Between 6am and noon"},
    "evening": {"start_hour": 18, "end_hour": 24, "description": "Between 6pm and midnight"},
}


def utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(UTC)


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return utc_now().isoformat()


@dataclass
class ScheduleSpec:
    """A parsed schedule specification."""

    id: str
    phrase: str
    routine: str
    cadence: str
    enabled: bool = True
    last_run: Optional[str] = None
    last_result: Optional[str] = None
    created_on: Optional[str] = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduleSpec":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            phrase=data["phrase"],
            routine=data["routine"],
            cadence=data["cadence"],
            enabled=data.get("enabled", True),
            last_run=data.get("last_run"),
            last_result=data.get("last_result"),
            created_on=data.get("created_on"),
        )


class ScheduleParser:
    """Deterministic parser for natural-language schedule phrases."""

    # Pattern components
    _ROUTINE_PATTERN = None  # Built dynamically
    _CADENCE_PATTERN = r"(?:every\s+)?(daily|nightly|morning|evening)"

    @classmethod
    def _build_routine_pattern(cls) -> str:
        """Build regex pattern from supported routines and aliases."""
        all_aliases = []
        for routine, info in SUPPORTED_ROUTINES.items():
            all_aliases.extend(info["aliases"])
        # Sort by length (longest first) for greedy matching
        all_aliases.sort(key=len, reverse=True)
        escaped = [re.escape(alias) for alias in all_aliases]
        return r"(" + "|".join(escaped) + r")"

    @classmethod
    def parse(cls, phrase: str) -> Optional[Tuple[str, str]]:
        """
        Parse a schedule phrase into (routine, cadence) tuple.

        Returns None if the phrase doesn't match supported patterns.

        Supported patterns:
        - "run {routine} {cadence}" -> (routine, cadence)
        - "run {cadence} {routine}" -> (routine, cadence)
        - "{routine} {cadence}" -> (routine, cadence)
        """
        if cls._ROUTINE_PATTERN is None:
            cls._ROUTINE_PATTERN = cls._build_routine_pattern()

        normalized = phrase.lower().strip()
        # Strip leading "run" if present
        if normalized.startswith("run "):
            normalized = normalized[4:].strip()

        routine_match = re.search(cls._ROUTINE_PATTERN, normalized, re.IGNORECASE)
        cadence_match = re.search(cls._CADENCE_PATTERN, normalized, re.IGNORECASE)

        if not routine_match or not cadence_match:
            return None

        matched_alias = routine_match.group(1).lower()
        cadence = cadence_match.group(1).lower()

        # Resolve alias to canonical routine name
        routine = None
        for routine_name, info in SUPPORTED_ROUTINES.items():
            if matched_alias in [a.lower() for a in info["aliases"]]:
                routine = routine_name
                break

        if routine is None or cadence not in CADENCE_WINDOWS:
            return None

        return (routine, cadence)

    @classmethod
    def generate_id(cls, phrase: str) -> str:
        """
        Generate stable ID from parsed (routine, cadence) tuple.

        This ensures semantic deduplication - different phrasings of the same
        logical schedule produce the same ID:
        - "run self research daily" -> same ID
        - "self research daily" -> same ID
        - "schedule self research daily" -> same ID
        """
        parsed = cls.parse(phrase)
        if parsed is None:
            # Fallback to phrase-based ID for unparseable input
            normalized = phrase.lower().strip()
            hash_input = normalized.encode("utf-8")
            return hashlib.sha256(hash_input).hexdigest()[:12]

        routine, cadence = parsed
        # Canonical form: "routine:cadence"
        canonical = f"{routine}:{cadence}"
        hash_input = canonical.encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()[:12]


class ScheduleEvaluator:
    """Evaluate and manage scheduled OpenClaw routines."""

    def __init__(
        self,
        schedules_path: Optional[Path] = None,
        *,
        runtime_root: Optional[Path] = None,
        repo_root: Optional[Path] = None,
        claim_ops: Optional[ScheduleClaimOps] = None,
    ):
        """
        Initialize schedule evaluator.

        Args:
            schedules_path: Path to schedules.json. Defaults to module memory dir.
        """
        explicit_schedules_path = schedules_path is not None
        if not explicit_schedules_path:
            module_path = Path(__file__).parent.parent
            schedules_path = module_path / "memory" / "schedules.json"
        self.schedules_path = Path(schedules_path)
        self.schedules_path.parent.mkdir(parents=True, exist_ok=True)
        repository = repo_root or Path(__file__).resolve().parents[4]
        claim_root = runtime_root or _default_claim_root(
            self.schedules_path, explicit_schedules_path, Path(repository)
        )
        self.claim_store = ScheduleClaimStore(
            repo_root=repository,
            runtime_root=claim_root,
            ops=claim_ops,
        )
        self._schedules: Dict[str, ScheduleSpec] = {}
        self._load_schedules()

    def _load_schedules(self) -> None:
        """Load schedules from disk."""
        if not self.schedules_path.exists():
            self._schedules = {}
            return

        try:
            data = json.loads(self.schedules_path.read_text(encoding="utf-8"))
            self._schedules = {
                spec_id: ScheduleSpec.from_dict(spec_data)
                for spec_id, spec_data in data.get("schedules", {}).items()
            }
            logger.debug("[SCHEDULE] Loaded %d schedule(s)", len(self._schedules))
        except Exception as exc:
            logger.warning("[SCHEDULE] Failed to load schedules: %s", exc)
            self._schedules = {}

    def _save_schedules(self) -> None:
        """Save schedules to disk."""
        data = {
            "generated_on": utc_now_iso(),
            "schedule_count": len(self._schedules),
            "schedules": {
                spec_id: spec.to_dict() for spec_id, spec in self._schedules.items()
            },
        }
        try:
            self.schedules_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            logger.debug("[SCHEDULE] Saved %d schedule(s)", len(self._schedules))
        except Exception as exc:
            logger.error("[SCHEDULE] Failed to save schedules: %s", exc)

    def add_schedule(self, phrase: str) -> Optional[ScheduleSpec]:
        """
        Add a schedule from a natural-language phrase.

        Returns the created ScheduleSpec, or None if parsing failed.
        """
        parsed = ScheduleParser.parse(phrase)
        if parsed is None:
            logger.warning("[SCHEDULE] Could not parse phrase: %s", phrase)
            return None

        routine, cadence = parsed
        spec_id = ScheduleParser.generate_id(phrase)

        # Check for duplicate
        if spec_id in self._schedules:
            logger.info("[SCHEDULE] Schedule already exists: %s", spec_id)
            return self._schedules[spec_id]

        spec = ScheduleSpec(
            id=spec_id,
            phrase=phrase,
            routine=routine,
            cadence=cadence,
            enabled=True,
            created_on=utc_now_iso(),
        )
        self._schedules[spec_id] = spec
        self._save_schedules()
        logger.info("[SCHEDULE] Added schedule: %s (%s %s)", spec_id, routine, cadence)
        return spec

    def remove_schedule(self, spec_id: str) -> bool:
        """Remove a schedule by ID. Returns True if removed."""
        if spec_id not in self._schedules:
            return False
        del self._schedules[spec_id]
        self._save_schedules()
        logger.info("[SCHEDULE] Removed schedule: %s", spec_id)
        return True

    def list_schedules(self) -> List[ScheduleSpec]:
        """Return all schedules."""
        return list(self._schedules.values())

    def get_due_schedules(self, now: Optional[datetime] = None) -> List[ScheduleSpec]:
        """
        Return schedules that are due for execution.

        A schedule is due if:
        1. It is enabled
        2. Current hour is within the cadence window
        3. It hasn't run during the current cadence window
        """
        current = _utc_value(now or utc_now())
        return [
            spec
            for spec in self._schedules.values()
            if _schedule_is_due(spec, current)
        ]

    def claim_schedule(
        self,
        spec: ScheduleSpec,
        *,
        now: Optional[datetime] = None,
    ) -> Optional[ScheduleClaim]:
        """Durably claim one currently due schedule immediately before dispatch."""

        current = _utc_value(now or utc_now())
        known = self._schedules.get(spec.id)
        if (
            known is None
            or not known.enabled
            or known.routine != spec.routine
            or known.cadence != spec.cadence
            or known.routine not in SUPPORTED_ROUTINES
            or known.cadence not in CADENCE_WINDOWS
        ):
            return None
        window = _schedule_window(known, current)
        if window is None:
            return None
        return self.claim_store.claim_window(window, now=current)

    def finalize_claim(
        self,
        token: str,
        *,
        success: bool,
        outcome_code: str,
        now: Optional[datetime] = None,
    ) -> bool:
        """Finalize only the current exact durable claim token."""

        return self.claim_store.finalize(
            token,
            success=success,
            outcome_code=outcome_code,
            now=_utc_value(now or utc_now()),
        )

    def record_execution(
        self, spec_id: str, success: bool, result_summary: str
    ) -> bool:
        """
        Record that a scheduled routine was executed.

        Returns True if the spec was found and updated.
        """
        if spec_id not in self._schedules:
            return False

        spec = self._schedules[spec_id]
        spec.last_run = utc_now_iso()
        spec.last_result = f"{'success' if success else 'failed'}: {result_summary}"
        self._save_schedules()
        return True

    def get_schedule(self, spec_id: str) -> Optional[ScheduleSpec]:
        """Get a schedule by ID."""
        return self._schedules.get(spec_id)

    def set_enabled(self, spec_id: str, enabled: bool) -> bool:
        """Enable or disable a schedule. Returns True if updated."""
        if spec_id not in self._schedules:
            return False
        self._schedules[spec_id].enabled = enabled
        self._save_schedules()
        return True


def get_supported_phrases() -> List[str]:
    """Return example supported schedule phrases."""
    examples = []
    for routine, info in SUPPORTED_ROUTINES.items():
        primary_alias = info["aliases"][0]
        for cadence in CADENCE_WINDOWS:
            examples.append(f"run {primary_alias} {cadence}")
    return examples


def _default_claim_root(
    path: Path, explicit_path: bool, repo_root: Path
) -> Path:
    configured = os.getenv("IDLE_AUTOMATION_RUNTIME_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser()
    if explicit_path and not _is_within(path.parent, repo_root):
        return path.parent / "claim-runtime"
    return Path.home() / ".foundups-agent" / "idle_automation"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _utc_value(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _schedule_window(
    spec: ScheduleSpec, now: datetime
) -> Optional[ScheduleWindow]:
    bounds = CADENCE_WINDOWS.get(spec.cadence)
    if bounds is None:
        return None
    start = now.replace(
        hour=bounds["start_hour"], minute=0, second=0, microsecond=0
    )
    end_hour = bounds["end_hour"]
    end = (
        now.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        if end_hour < 24
        else now.replace(hour=0, minute=0, second=0, microsecond=0)
        + timedelta(days=1)
    )
    if not start <= now < end:
        return None
    start_text, end_text = start.isoformat(), end.isoformat()
    execution_id = build_execution_id(
        spec.id, spec.routine, spec.cadence, start_text, end_text
    )
    return ScheduleWindow(
        schedule_id=spec.id,
        routine=spec.routine,
        cadence=spec.cadence,
        window_start=start_text,
        window_end=end_text,
        execution_id=execution_id,
    )


def _schedule_is_due(spec: ScheduleSpec, now: datetime) -> bool:
    if not spec.enabled:
        return False
    bounds = CADENCE_WINDOWS.get(spec.cadence)
    if bounds is None:
        return False
    if not bounds["start_hour"] <= now.hour < bounds["end_hour"]:
        return False
    if not spec.last_run:
        return True
    try:
        last_run = _utc_value(
            datetime.fromisoformat(spec.last_run.replace("Z", "+00:00"))
        )
    except ValueError:
        return True
    start_hour = 0 if spec.cadence == "daily" else bounds["start_hour"]
    window_start = now.replace(
        hour=start_hour, minute=0, second=0, microsecond=0
    )
    return last_run < window_start
