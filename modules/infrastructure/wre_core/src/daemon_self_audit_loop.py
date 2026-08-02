#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Continuous 0102 daemon self-audit loop with policy-bound auto-fixes."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shlex
import sqlite3
import subprocess
import threading
import time
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from modules.infrastructure.wre_core.src.improvement_job_contract import (
    ImprovementRiskLevel,
    ImprovementScope,
    ImprovementType,
    create_improvement_job,
)
from modules.infrastructure.wre_core.src.reddog_direction import RedDogDirector
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    redact_runtime_text,
    runtime_operation_lock,
    secure_append_runtime_text,
    secure_read_confined_bytes,
    secure_replace_runtime_text,
    validate_runtime_root_path,
)

logger = logging.getLogger(__name__)


def resolve_daemon_self_audit_runtime_root(
    repo_root: Path | str,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the single external runtime root used by self-audit producers and consumers."""

    root = Path(repo_root).resolve()
    env = os.environ if environ is None else environ
    explicit = str(env.get("OPENCLAW_SELF_AUDIT_RUNTIME_ROOT", "")).strip()
    resident_root = str(env.get("REDDOG_RESIDENT_RUNTIME_ROOT", "")).strip()
    if explicit:
        candidate = Path(explicit)
        if not candidate.is_absolute():
            candidate = root.parent / candidate
    elif resident_root:
        base = Path(resident_root)
        if not base.is_absolute():
            base = root.parent / base
        candidate = base / "daemon_self_audit"
    else:
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", root.name).strip("-_")
        candidate = (
            root.parent
            / ".reddog"
            / "resident"
            / (slug or "repository")
            / "daemon_self_audit"
        )
    return validate_runtime_root_path(candidate, repo_root=root)


@dataclass
class SelfAuditEvent:
    timestamp: float
    source_file: str
    signature: str
    line: str
    recommended_fix: str
    auto_fix_attempted: bool
    auto_fix_result: str
    improvement_job_id: str = ""
    improvement_direction: str = ""
    redaction_applied: bool = False
    redaction_replacements: int = 0
    line_truncated: bool = False


@dataclass
class SelfAuditEscalation:
    timestamp: float
    signature: str
    source_file: str
    event_count: int
    recommended_fix: str
    last_fix_result: str
    dispatch_attempted: bool
    dispatch_result: str


class DaemonSelfAuditLoop:
    """Tails daemon logs and proposes RedDog-directed dry-run improvement jobs."""

    ERROR_PATTERNS = [
        re.compile(r"\[ERROR\]", re.IGNORECASE),
        re.compile(r"traceback", re.IGNORECASE),
        re.compile(r"exception", re.IGNORECASE),
        re.compile(r"ironclaw runtime is unavailable", re.IGNORECASE),
        re.compile(r"health endpoint unavailable", re.IGNORECASE),
        re.compile(r"connectionerror", re.IGNORECASE),
        re.compile(r"paerrorcode\s*-9984", re.IGNORECASE),
        re.compile(r"unique constraint failed", re.IGNORECASE),
    ]

    # Noise signatures to ignore -- these match ERROR_PATTERNS but are not actionable
    NOISE_SIGNATURES = [
        "traceback (most recent call last):",  # generic traceback header
        "raise exception_class(message, screen, stacktrace)",  # Selenium generic raise
        "ntdll!rtlinitializeexceptionchain",  # Windows crash stack noise
        "from fastapi import fastapi",  # import line in stack trace
    ]

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.interval_sec = float(os.getenv("OPENCLAW_SELF_AUDIT_INTERVAL_SEC", "5"))
        self.max_read_bytes = int(os.getenv("OPENCLAW_SELF_AUDIT_MAX_READ_BYTES", "65536"))
        self.dedupe_window_sec = int(os.getenv("OPENCLAW_SELF_AUDIT_DEDUPE_WINDOW_SEC", "120"))
        self.improvement_proposals_enabled = (
            os.getenv("OPENCLAW_SELF_AUDIT_IMPROVEMENT_PROPOSALS", "1").strip() == "1"
        )
        self.legacy_process_dispatch_enabled = (
            os.getenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_PROCESS_DISPATCH", "0").strip()
            == "1"
        )
        self.auto_fix_enabled = (
            os.getenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "0").strip() == "1"
            and os.getenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_AUTO_FIX", "0").strip() == "1"
        )
        self.allowed_fixes = {
            part.strip().lower()
            for part in os.getenv(
                "OPENCLAW_SELF_AUDIT_ALLOWED_FIXES",
                "start_ironclaw_gateway,diagnose_microphone_device,verify_dae_event_store",
            ).split(",")
            if part.strip()
        }
        self.fix_cooldown_sec = int(os.getenv("OPENCLAW_SELF_AUDIT_FIX_COOLDOWN_SEC", "120"))
        self.allow_shell_start_cmd = os.getenv(
            "OPENCLAW_SELF_AUDIT_ALLOW_SHELL_START_CMD", "0"
        ).strip() == "1"
        self.ironclaw_start_retry_count = max(
            0, int(os.getenv("IRONCLAW_START_RETRY_COUNT", "3"))
        )
        self.ironclaw_start_retry_delay_sec = max(
            0.0, float(os.getenv("IRONCLAW_START_RETRY_DELAY_SEC", "5"))
        )
        self.enable_telemetry = os.getenv("OPENCLAW_SELF_AUDIT_TELEMETRY", "1").strip() == "1"
        self.escalate_after = int(os.getenv("OPENCLAW_SELF_AUDIT_ESCALATE_AFTER", "3"))
        self.escalation_window_sec = int(
            os.getenv("OPENCLAW_SELF_AUDIT_ESCALATION_WINDOW_SEC", "900")
        )
        self.escalation_cooldown_sec = int(
            os.getenv("OPENCLAW_SELF_AUDIT_ESCALATION_COOLDOWN_SEC", "600")
        )
        self.escalation_cmd = os.getenv("OPENCLAW_SELF_AUDIT_ESCALATE_CMD", "").strip()
        self.escalation_dispatch_enabled = (
            os.getenv("OPENCLAW_SELF_AUDIT_ALLOW_LEGACY_ESCALATION_DISPATCH", "0").strip()
            == "1"
        )
        self.escalation_allow_shell = (
            os.getenv("OPENCLAW_SELF_AUDIT_ESCALATE_ALLOW_SHELL_CMD", "0").strip() == "1"
        )

        self.runtime_root = self._resolve_runtime_root()
        self.task_log_path = self.runtime_root / "daemon_self_audit_tasks.jsonl"
        self.improvement_job_log_path = (
            self.runtime_root / "daemon_self_audit_improvement_jobs.jsonl"
        )
        self.escalation_log_path = self.runtime_root / "daemon_self_audit_escalations.jsonl"
        self.state_path = self.runtime_root / "daemon_self_audit_state.json"
        self._offsets: Dict[str, int] = {}
        self._seen: Dict[str, float] = {}
        self._last_fix_at: Dict[str, float] = {}
        self._fix_stats: Dict[str, Dict[str, Any]] = {}
        self._signature_stats: Dict[str, Dict[str, Any]] = {}
        self._last_escalation_at: Dict[str, float] = {}
        self._pattern_memory: Any = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._scan_lock = threading.Lock()
        self._state_loaded_mtime_ns = 0
        self._load_state()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="daemon-self-audit", daemon=True)
        self._thread.start()

    def stop(self, timeout_sec: float = 2.0) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_sec)
        self._save_state()

    def scan_once(self) -> int:
        """Run one scan cycle. Returns number of events opened."""
        with self._scan_lock:
            return self._scan_once_locked()

    def _scan_once_locked(self) -> int:
        with runtime_operation_lock(self.runtime_root / "daemon_self_audit.scan"):
            self._refresh_state_if_changed()
            return self._scan_once_with_lease()

    def _scan_once_with_lease(self) -> int:
        events = 0
        for log_file in self._resolve_log_files():
            lines = self._tail_new_lines(log_file)
            for line in lines:
                redacted = redact_runtime_text(line, max_chars=4096)
                safe_line = redacted.text.strip()
                if not safe_line:
                    continue
                if not self._is_error_line(safe_line):
                    continue
                signature = self._normalize_signature(safe_line)
                if self._is_noise_signature(signature):
                    continue
                if self._is_duplicate(signature):
                    continue
                self._seen[signature] = time.time()
                event = self._open_fix_task(
                    log_file,
                    signature,
                    safe_line,
                    redaction_replacements=redacted.replacements,
                    line_truncated=redacted.truncated,
                )
                self._persist_event(event)
                self._increment_counter("self_audit_events_total")
                self._record_signature_event(event)
                self._maybe_escalate(event)
                events += 1
        self._save_state()
        return events

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.scan_once()
            except Exception:
                # Keep loop alive under all conditions.
                pass
            self._stop.wait(max(self.interval_sec, 1.0))

    def _resolve_log_files(self) -> List[Path]:
        raw = os.getenv(
            "OPENCLAW_SELF_AUDIT_LOG_GLOBS",
            "holo_index/logs/**/*.log;logs/**/*.log;holo_index/logs/telemetry/**/*.jsonl",
        )
        globs = [part.strip() for part in re.split(r"[;,\n]+", raw) if part.strip()]
        files: List[Path] = []
        for pattern in globs:
            if not self._valid_log_glob(pattern):
                continue
            files.extend(self.repo_root.glob(pattern))
        # stable ordering for deterministic state writes
        resolved: set[Path] = set()
        for path in files:
            try:
                candidate = path.resolve()
                candidate.relative_to(self.repo_root)
            except (OSError, ValueError):
                continue
            if candidate.is_file():
                resolved.add(candidate)
        return sorted(resolved)

    @staticmethod
    def _valid_log_glob(pattern: str) -> bool:
        if not pattern or "\x00" in pattern:
            return False
        normalized = pattern.replace("\\", "/")
        if normalized.startswith(("/", "//?/", "//./")):
            return False
        if re.match(r"^[a-zA-Z]:", normalized):
            return False
        return ".." not in Path(normalized).parts

    def _tail_new_lines(self, path: Path) -> List[str]:
        key = str(path)
        try:
            size = path.stat().st_size
        except Exception:
            return []

        offset = int(self._offsets.get(key, 0))
        if offset > size:
            offset = 0
        read_from = max(0, size - self.max_read_bytes) if offset == 0 else offset
        try:
            raw, next_offset = secure_read_confined_bytes(
                path,
                allowed_root=self.repo_root,
                offset=read_from,
                max_bytes=self.max_read_bytes,
            )
            text = raw.decode("utf-8", errors="replace")
            self._offsets[key] = next_offset
        except (OSError, ValueError):
            return []
        return text.splitlines()

    def _is_error_line(self, line: str) -> bool:
        return any(p.search(line) for p in self.ERROR_PATTERNS)

    @staticmethod
    def _normalize_signature(line: str) -> str:
        safe = redact_runtime_text(line, max_chars=4096).text
        stripped = re.sub(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[,.\d]*", "", safe)
        stripped = re.sub(r"\b[0-9a-f]{8,}\b", "<hex>", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s+", " ", stripped).strip().lower()
        return stripped[:240]

    def _is_duplicate(self, signature: str) -> bool:
        now = time.time()
        last = float(self._seen.get(signature, 0))
        return (now - last) < max(self.dedupe_window_sec, 1)

    def _is_noise_signature(self, signature: str) -> bool:
        """Return True if signature matches a known noise pattern (not actionable)."""
        return any(noise in signature for noise in self.NOISE_SIGNATURES)

    def _recommend_fix(self, signature: str) -> str:
        candidates: List[str]
        if (
            "ironclaw runtime is unavailable" in signature
            or "health endpoint unavailable" in signature
            or "connectionerror" in signature
        ):
            candidates = ["start_ironclaw_gateway"]
        elif (
            "paerrorcode -9984" in signature
            or "incompatible host api specific stream info" in signature
        ):
            candidates = ["diagnose_microphone_device"]
        elif "unique constraint failed" in signature and "dae_events.sequence_id" in signature:
            candidates = ["verify_dae_event_store"]
        else:
            candidates = ["inspect_log_and_create_patch_task"]

        scored = sorted(
            ((self._fix_score(name), name) for name in candidates),
            reverse=True,
        )
        return scored[0][1]

    def _fix_score(self, fix_name: str) -> float:
        stats = self._fix_stats.get(fix_name, {})
        attempts = int(stats.get("attempts", 0))
        successes = int(stats.get("successes", 0))
        failures = int(stats.get("failures", 0))
        success_rate = (successes / attempts) if attempts else 0.5
        failure_rate = (failures / attempts) if attempts else 0.0
        allow_bonus = 0.2 if fix_name in self.allowed_fixes else 0.0
        return success_rate - (failure_rate * 0.5) + allow_bonus

    def _open_fix_task(
        self,
        source_file: Path,
        signature: str,
        line: str,
        *,
        redaction_replacements: int = 0,
        line_truncated: bool = False,
    ) -> SelfAuditEvent:
        safe_signature = self._normalize_signature(signature)
        safe_line_result = redact_runtime_text(line, max_chars=600)
        safe_line = safe_line_result.text
        recommended = self._recommend_fix(signature)
        attempted = False
        result = "not_attempted"
        improvement_job_id = ""
        improvement_direction = ""
        if self.improvement_proposals_enabled:
            improvement_job_id, improvement_direction = self._emit_improvement_proposal(
                source_file=source_file,
                signature=safe_signature,
                line=safe_line,
                recommended_fix=recommended,
            )
            if improvement_job_id:
                result = f"improvement_job_proposed:{improvement_job_id}"
        if self.auto_fix_enabled and recommended in self.allowed_fixes:
            self._increment_counter("self_audit_auto_fix_attempts")
            attempted, result = self._apply_policy_fix(recommended)
            if attempted and self._is_successful_fix_result(result):
                self._increment_counter("self_audit_auto_fix_success")
            elif attempted:
                self._increment_counter("self_audit_auto_fix_fail")
        safe_result = redact_runtime_text(result, max_chars=600).text
        self._record_fix_feedback(recommended, attempted, safe_result)
        return SelfAuditEvent(
            timestamp=time.time(),
            source_file=str(source_file),
            signature=safe_signature,
            line=safe_line,
            recommended_fix=recommended,
            auto_fix_attempted=attempted,
            auto_fix_result=safe_result,
            improvement_job_id=improvement_job_id,
            improvement_direction=improvement_direction,
            redaction_applied=(redaction_replacements + safe_line_result.replacements) > 0,
            redaction_replacements=(
                redaction_replacements + safe_line_result.replacements
            ),
            line_truncated=line_truncated or safe_line_result.truncated,
        )

    def _emit_improvement_proposal(
        self,
        *,
        source_file: Path,
        signature: str,
        line: str,
        recommended_fix: str,
    ) -> Tuple[str, str]:
        signature = self._normalize_signature(signature)
        line = redact_runtime_text(line, max_chars=600).text
        rel_source = self._relative_source_path(source_file)
        improvement_type = self._improvement_type_for_fix(recommended_fix)
        scope = ImprovementScope(
            module_path="modules/infrastructure/wre_core",
            file_paths=[rel_source],
            wsp_refs=["WSP 15", "WSP 48", "WSP 50", "WSP 97"],
        )
        finding_digest = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]
        job = create_improvement_job(
            finding_id=f"daemon_self_audit:{finding_digest}",
            improvement_type=improvement_type,
            scope=scope,
            risk_level=ImprovementRiskLevel.LOW,
            requested_by="daemon_self_audit_loop",
            payload={
                "source_file": rel_source,
                "signature": signature,
                "line": line[:600],
                "recommended_fix": recommended_fix,
                "legacy_auto_fix_attempted": False,
            },
        )
        directed = RedDogDirector(requested_by="daemon_self_audit_loop").direct([job])[0]
        row = {
            "timestamp": time.time(),
            "job": job.to_dict(),
            "direction": directed.to_dict(),
            "no_execution_performed": True,
            "no_subprocess_performed": True,
            "no_queue_mutation_performed": True,
            "no_pattern_memory_write_performed": True,
        }
        secure_append_runtime_text(
            self.improvement_job_log_path,
            json.dumps(row, ensure_ascii=True, default=str) + "\n",
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
            validate_existing=_validate_jsonl,
        )
        return job.job_id, directed.direction.value

    def _relative_source_path(self, source_file: Path) -> str:
        try:
            return str(source_file.resolve().relative_to(self.repo_root)).replace("\\", "/")
        except ValueError:
            return str(source_file.resolve()).replace("\\", "/")

    @staticmethod
    def _improvement_type_for_fix(recommended_fix: str) -> ImprovementType:
        if recommended_fix == "verify_dae_event_store":
            return ImprovementType.DRIFT_CORRECTION
        if recommended_fix == "diagnose_microphone_device":
            return ImprovementType.FMAS_SCAN
        return ImprovementType.MODULE_REPAIR

    def _record_signature_event(self, event: SelfAuditEvent) -> None:
        now = event.timestamp
        stats = self._signature_stats.setdefault(
            event.signature,
            {
                "count": 0,
                "first_seen": now,
                "last_seen": now,
                "recommended_fix": event.recommended_fix,
                "last_fix_result": event.auto_fix_result,
            },
        )

        first_seen = float(stats.get("first_seen", now))
        if (now - first_seen) > max(self.escalation_window_sec, 1):
            stats["count"] = 0
            stats["first_seen"] = now

        stats["count"] = int(stats.get("count", 0)) + 1
        stats["last_seen"] = now
        stats["recommended_fix"] = event.recommended_fix
        stats["last_fix_result"] = event.auto_fix_result

    def _maybe_escalate(self, event: SelfAuditEvent) -> None:
        stats = self._signature_stats.get(event.signature, {})
        count = int(stats.get("count", 0))
        if count < max(self.escalate_after, 1):
            return
        if event.auto_fix_attempted and self._is_successful_fix_result(event.auto_fix_result):
            return

        now = event.timestamp
        last_escalated = float(self._last_escalation_at.get(event.signature, 0))
        if (now - last_escalated) < max(self.escalation_cooldown_sec, 1):
            return
        self._last_escalation_at[event.signature] = now

        dispatch_attempted = False
        dispatch_result = "not_configured"
        if self.escalation_cmd:
            if self.escalation_dispatch_enabled:
                dispatch_attempted, dispatch_result = self._dispatch_escalation_command(
                    self.escalation_cmd
                )
                if dispatch_attempted and dispatch_result.startswith("dispatched"):
                    self._increment_counter("self_audit_escalation_dispatch_success")
                elif dispatch_attempted:
                    self._increment_counter("self_audit_escalation_dispatch_fail")
            else:
                dispatch_result = "legacy_escalation_dispatch_disabled"

        escalation = SelfAuditEscalation(
            timestamp=now,
            signature=event.signature,
            source_file=event.source_file,
            event_count=count,
            recommended_fix=str(stats.get("recommended_fix", event.recommended_fix)),
            last_fix_result=str(stats.get("last_fix_result", event.auto_fix_result)),
            dispatch_attempted=dispatch_attempted,
            dispatch_result=dispatch_result,
        )
        self._persist_escalation(escalation)
        self._increment_counter("self_audit_escalations_total")

    def _dispatch_escalation_command(self, cmd: str) -> Tuple[bool, str]:
        if not (
            self.legacy_process_dispatch_enabled
            and self.escalation_dispatch_enabled
        ):
            return False, "legacy_process_dispatch_disabled"
        try:
            if self.escalation_allow_shell:
                subprocess.Popen(
                    cmd,
                    cwd=str(self.repo_root),
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True, "dispatched(shell)"

            args = shlex.split(cmd, posix=os.name != "nt")
            if not args:
                return False, "invalid_escalation_command"
            subprocess.Popen(
                args,
                cwd=str(self.repo_root),
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True, "dispatched"
        except Exception as exc:
            return False, str(exc)

    @staticmethod
    def _is_successful_fix_result(result: str) -> bool:
        success_markers = (
            "start_command_dispatched",
            "microphone_diagnostics_written",
            "event_store_verified",
        )
        return any(marker in result for marker in success_markers)

    def _record_fix_feedback(self, fix_name: str, attempted: bool, result: str) -> None:
        stats = self._fix_stats.setdefault(
            fix_name,
            {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "last_result": "",
                "last_attempt_at": 0.0,
            },
        )
        if attempted:
            stats["attempts"] = int(stats.get("attempts", 0)) + 1
            if self._is_successful_fix_result(result):
                stats["successes"] = int(stats.get("successes", 0)) + 1
            else:
                stats["failures"] = int(stats.get("failures", 0)) + 1
            stats["last_attempt_at"] = time.time()
        stats["last_result"] = result

    def _apply_policy_fix(self, fix_name: str) -> Tuple[bool, str]:
        now = time.time()
        last = float(self._last_fix_at.get(fix_name, 0))
        if (now - last) < max(self.fix_cooldown_sec, 1):
            return False, "cooldown_active"
        self._last_fix_at[fix_name] = now

        if fix_name == "start_ironclaw_gateway":
            cmd = os.getenv("IRONCLAW_START_CMD", "").strip()
            if not cmd:
                return False, "IRONCLAW_START_CMD not set"
            return self._dispatch_start_command_with_retry(cmd)
        if fix_name == "diagnose_microphone_device":
            return self._diagnose_microphone_device()
        if fix_name == "verify_dae_event_store":
            return self._verify_dae_event_store()
        return False, "no_policy_handler"

    def _dispatch_start_command(self, cmd: str) -> Tuple[bool, str]:
        if not self.legacy_process_dispatch_enabled or not self.auto_fix_enabled:
            return False, "legacy_process_dispatch_disabled"
        try:
            if self.allow_shell_start_cmd:
                subprocess.Popen(
                    cmd,
                    cwd=str(self.repo_root),
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True, "start_command_dispatched(shell)"

            args = shlex.split(cmd, posix=os.name != "nt")
            if not args:
                return False, "invalid_start_command"
            subprocess.Popen(
                args,
                cwd=str(self.repo_root),
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True, "start_command_dispatched"
        except Exception as exc:
            return False, str(exc)

    def _dispatch_start_command_with_retry(self, cmd: str) -> Tuple[bool, str]:
        # Dispatch once; daemon start is fire-and-forget (Popen).
        dispatched, detail = self._dispatch_start_command(cmd)
        if not dispatched:
            return False, f"dispatch_failed:{detail}"

        # Dispatch succeeded -> fix was attempted. Health polling annotates
        # the result string but does not flip the "attempted" flag.
        if self.ironclaw_start_retry_count <= 0:
            return True, detail

        last_health_detail = "no_health_attempt"
        for attempt in range(1, self.ironclaw_start_retry_count + 1):
            time.sleep(self.ironclaw_start_retry_delay_sec)
            healthy, last_health_detail = self._verify_ironclaw_health()
            if healthy:
                return True, f"healthy_after_{attempt}_attempt(s):{detail}"
        # Dispatch ran but health never came up. "attempted=True"; the
        # result string omits the dispatch success marker so
        # _is_successful_fix_result classifies this as a failure.
        return True, (
            f"attempted_but_unhealthy_after_{self.ironclaw_start_retry_count}_attempt(s):"
            f"{last_health_detail}"
        )

    def _verify_ironclaw_health(self) -> Tuple[bool, str]:
        base = os.getenv("IRONCLAW_BASE_URL", "http://127.0.0.1:3000").strip().rstrip("/")
        if not base:
            return False, "no_base_url"
        timeout = max(1.0, float(os.getenv("IRONCLAW_TIMEOUT_SEC", "5")))
        url = f"{base}/health"
        try:
            from urllib.request import Request, urlopen

            req = Request(url, method="GET")
            with urlopen(req, timeout=timeout) as resp:
                status = int(getattr(resp, "status", 200))
                if 200 <= status < 300:
                    return True, f"health_ok:{status}"
                # 3xx/4xx/5xx: reachable but not reporting healthy.
                return False, f"health_bad_status:{status}"
        except Exception as exc:
            return False, f"health_error:{exc.__class__.__name__}"

    def _diagnose_microphone_device(self) -> Tuple[bool, str]:
        report_path = self.runtime_root / "microphone_diagnostics.json"
        payload: Dict[str, Any] = {"timestamp": time.time(), "status": "unknown"}
        try:
            import sounddevice as sd  # type: ignore

            devices = sd.query_devices()
            payload.update(
                {
                    "status": "ok",
                    "default_device": sd.default.device,
                    "device_count": len(devices),
                    "input_devices": [
                        {
                            "name": d.get("name"),
                            "index": idx,
                            "max_input_channels": d.get("max_input_channels", 0),
                            "default_samplerate": d.get("default_samplerate"),
                        }
                        for idx, d in enumerate(devices)
                        if int(d.get("max_input_channels", 0)) > 0
                    ],
                }
            )
        except Exception as exc:
            payload.update(
                {"status": "error", "error": redact_runtime_text(exc, max_chars=600).text}
            )
            secure_replace_runtime_text(
                report_path,
                json.dumps(payload, indent=2),
                repo_root=self.repo_root,
                allowed_root=self.runtime_root,
            )
            return False, "microphone_diagnostics_failed"

        secure_replace_runtime_text(
            report_path,
            json.dumps(payload, indent=2),
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
        )
        return True, "microphone_diagnostics_written"

    def _verify_dae_event_store(self) -> Tuple[bool, str]:
        db_candidates = [
            self.repo_root / "modules/infrastructure/dae_daemon/memory/dae_audit.db",
            self.repo_root / "modules/infrastructure/dae_daemon/data/dae_audit.db",
        ]
        db_path = next((p for p in db_candidates if p.exists()), None)
        if db_path is None:
            return False, "dae_event_store_not_found"

        report_path = self.runtime_root / "dae_event_store_health.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(str(db_path)) as conn:
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                total = conn.execute("SELECT COUNT(*) FROM dae_events").fetchone()[0]
                max_seq = conn.execute("SELECT MAX(sequence_id) FROM dae_events").fetchone()[0] or 0
                dupes = conn.execute(
                    """
                    SELECT COUNT(*) FROM (
                      SELECT sequence_id FROM dae_events
                      GROUP BY sequence_id HAVING COUNT(*) > 1
                    )
                    """
                ).fetchone()[0]

            payload = {
                "timestamp": time.time(),
                "db_path": str(db_path),
                "integrity_check": integrity,
                "total_events": total,
                "max_sequence_id": max_seq,
                "duplicate_sequence_rows": dupes,
            }
            secure_replace_runtime_text(
                report_path,
                json.dumps(payload, indent=2),
                repo_root=self.repo_root,
                allowed_root=self.runtime_root,
            )
            if integrity != "ok" or int(dupes) > 0:
                return False, "event_store_integrity_failed"
            return True, "event_store_verified"
        except Exception as exc:
            payload = {
                "timestamp": time.time(),
                "db_path": str(db_path),
                "error": redact_runtime_text(exc, max_chars=600).text,
            }
            secure_replace_runtime_text(
                report_path,
                json.dumps(payload, indent=2),
                repo_root=self.repo_root,
                allowed_root=self.runtime_root,
            )
            return False, "event_store_verify_exception"

    def _get_pattern_memory(self) -> Any:
        if not self.enable_telemetry:
            return None
        if self._pattern_memory is not None:
            return self._pattern_memory
        try:
            from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory

            self._pattern_memory = PatternMemory()
        except Exception as exc:
            logger.debug("[SELF-AUDIT] PatternMemory unavailable: %s", exc)
            self._pattern_memory = None
        return self._pattern_memory

    def _increment_counter(self, counter_name: str, delta: int = 1) -> None:
        memory = self._get_pattern_memory()
        if memory is None:
            return
        try:
            memory.increment_counter(counter_name, delta)
        except Exception as exc:
            logger.debug("[SELF-AUDIT] counter increment failed (%s): %s", counter_name, exc)

    def _persist_event(self, event: SelfAuditEvent) -> None:
        row = asdict(event)
        for field in ("signature", "line", "auto_fix_result", "improvement_direction"):
            row[field] = redact_runtime_text(row.get(field), max_chars=600).text
        secure_append_runtime_text(
            self.task_log_path,
            json.dumps(row, ensure_ascii=True) + "\n",
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
            validate_existing=_validate_jsonl,
        )

    def _persist_escalation(self, escalation: SelfAuditEscalation) -> None:
        row = {
            "timestamp": escalation.timestamp,
            "signature": redact_runtime_text(escalation.signature, max_chars=240).text,
            "source_file": escalation.source_file,
            "event_count": escalation.event_count,
            "recommended_fix": escalation.recommended_fix,
            "last_fix_result": redact_runtime_text(
                escalation.last_fix_result, max_chars=600
            ).text,
            "dispatch_attempted": escalation.dispatch_attempted,
            "dispatch_result": redact_runtime_text(
                escalation.dispatch_result, max_chars=600
            ).text,
        }
        secure_append_runtime_text(
            self.escalation_log_path,
            json.dumps(row, ensure_ascii=True) + "\n",
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
            validate_existing=_validate_jsonl,
        )

    def _load_state(self) -> None:
        if not self.state_path.exists():
            self._state_loaded_mtime_ns = 0
            return
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            self._offsets = dict(payload.get("offsets", {}))
            self._seen = {k: float(v) for k, v in (payload.get("seen", {}) or {}).items()}
            self._last_fix_at = {
                k: float(v) for k, v in (payload.get("last_fix_at", {}) or {}).items()
            }
            self._fix_stats = dict(payload.get("fix_stats", {}) or {})
            self._signature_stats = dict(payload.get("signature_stats", {}) or {})
            self._last_escalation_at = {
                k: float(v) for k, v in (payload.get("last_escalation_at", {}) or {}).items()
            }
            self._state_loaded_mtime_ns = self.state_path.stat().st_mtime_ns
        except Exception:
            self._offsets = {}
            self._seen = {}
            self._last_fix_at = {}
            self._fix_stats = {}
            self._signature_stats = {}
            self._last_escalation_at = {}

    def _refresh_state_if_changed(self) -> None:
        try:
            current_mtime = self.state_path.stat().st_mtime_ns
        except OSError:
            current_mtime = 0
        if current_mtime > self._state_loaded_mtime_ns:
            self._load_state()

    def _save_state(self) -> None:
        payload = {
            "offsets": self._offsets,
            "seen": self._seen,
            "last_fix_at": self._last_fix_at,
            "fix_stats": self._fix_stats,
            "signature_stats": self._signature_stats,
            "last_escalation_at": self._last_escalation_at,
        }
        secure_replace_runtime_text(
            self.state_path,
            json.dumps(payload, indent=2),
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
        )
        self._state_loaded_mtime_ns = self.state_path.stat().st_mtime_ns

    def _resolve_runtime_root(self) -> Path:
        return resolve_daemon_self_audit_runtime_root(self.repo_root)


def _validate_jsonl(existing: str) -> None:
    for line_number, raw in enumerate(existing.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"daemon_self_audit_jsonl_invalid:{line_number}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"daemon_self_audit_jsonl_not_object:{line_number}")
