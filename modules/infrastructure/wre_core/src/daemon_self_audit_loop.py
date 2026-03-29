#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Continuous 0102 daemon self-audit loop with policy-bound auto-fixes."""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import sqlite3
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SelfAuditEvent:
    timestamp: float
    source_file: str
    signature: str
    line: str
    recommended_fix: str
    auto_fix_attempted: bool
    auto_fix_result: str


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
    """Tails daemon logs, opens fix tasks, and executes safe fixes under policy."""

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

    # Noise signatures to ignore — these match ERROR_PATTERNS but are not actionable
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
        self.auto_fix_enabled = os.getenv("OPENCLAW_SELF_AUDIT_AUTO_FIX", "1") == "1"
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
        self.enable_telemetry = os.getenv("OPENCLAW_SELF_AUDIT_TELEMETRY", "1").strip() == "1"
        self.escalate_after = int(os.getenv("OPENCLAW_SELF_AUDIT_ESCALATE_AFTER", "3"))
        self.escalation_window_sec = int(
            os.getenv("OPENCLAW_SELF_AUDIT_ESCALATION_WINDOW_SEC", "900")
        )
        self.escalation_cooldown_sec = int(
            os.getenv("OPENCLAW_SELF_AUDIT_ESCALATION_COOLDOWN_SEC", "600")
        )
        self.escalation_cmd = os.getenv("OPENCLAW_SELF_AUDIT_ESCALATE_CMD", "").strip()
        self.escalation_allow_shell = (
            os.getenv("OPENCLAW_SELF_AUDIT_ESCALATE_ALLOW_SHELL_CMD", "0").strip() == "1"
        )

        self.task_log_path = (
            self.repo_root
            / "modules/infrastructure/wre_core/reports/daemon_self_audit_tasks.jsonl"
        )
        self.escalation_log_path = (
            self.repo_root
            / "modules/infrastructure/wre_core/reports/daemon_self_audit_escalations.jsonl"
        )
        self.state_path = (
            self.repo_root
            / "modules/infrastructure/wre_core/reports/daemon_self_audit_state.json"
        )
        self._offsets: Dict[str, int] = {}
        self._seen: Dict[str, float] = {}
        self._last_fix_at: Dict[str, float] = {}
        self._fix_stats: Dict[str, Dict[str, Any]] = {}
        self._signature_stats: Dict[str, Dict[str, Any]] = {}
        self._last_escalation_at: Dict[str, float] = {}
        self._pattern_memory: Any = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
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
        events = 0
        for log_file in self._resolve_log_files():
            lines = self._tail_new_lines(log_file)
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if not self._is_error_line(line):
                    continue
                signature = self._normalize_signature(line)
                if self._is_noise_signature(signature):
                    continue
                if self._is_duplicate(signature):
                    continue
                self._seen[signature] = time.time()
                event = self._open_fix_task(log_file, signature, line)
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
            files.extend(self.repo_root.glob(pattern))
        # stable ordering for deterministic state writes
        return sorted({p.resolve() for p in files if p.is_file()})

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
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(read_from)
                text = handle.read()
                self._offsets[key] = handle.tell()
        except Exception:
            return []
        return text.splitlines()

    def _is_error_line(self, line: str) -> bool:
        return any(p.search(line) for p in self.ERROR_PATTERNS)

    @staticmethod
    def _normalize_signature(line: str) -> str:
        stripped = re.sub(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[,.\d]*", "", line)
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
        elif "paerrorcode -9984" in signature or "incompatible host api specific stream info" in signature:
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

    def _open_fix_task(self, source_file: Path, signature: str, line: str) -> SelfAuditEvent:
        recommended = self._recommend_fix(signature)
        attempted = False
        result = "not_attempted"
        if self.auto_fix_enabled and recommended in self.allowed_fixes:
            self._increment_counter("self_audit_auto_fix_attempts")
            attempted, result = self._apply_policy_fix(recommended)
            if attempted and self._is_successful_fix_result(result):
                self._increment_counter("self_audit_auto_fix_success")
            elif attempted:
                self._increment_counter("self_audit_auto_fix_fail")
        self._record_fix_feedback(recommended, attempted, result)
        return SelfAuditEvent(
            timestamp=time.time(),
            source_file=str(source_file),
            signature=signature,
            line=line[:600],
            recommended_fix=recommended,
            auto_fix_attempted=attempted,
            auto_fix_result=result,
        )

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
            dispatch_attempted, dispatch_result = self._dispatch_escalation_command(
                self.escalation_cmd
            )
            if dispatch_attempted and dispatch_result.startswith("dispatched"):
                self._increment_counter("self_audit_escalation_dispatch_success")
            elif dispatch_attempted:
                self._increment_counter("self_audit_escalation_dispatch_fail")

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
            return self._dispatch_start_command(cmd)
        if fix_name == "diagnose_microphone_device":
            return self._diagnose_microphone_device()
        if fix_name == "verify_dae_event_store":
            return self._verify_dae_event_store()
        return False, "no_policy_handler"

    def _dispatch_start_command(self, cmd: str) -> Tuple[bool, str]:
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

    def _diagnose_microphone_device(self) -> Tuple[bool, str]:
        report_path = (
            self.repo_root / "modules/infrastructure/wre_core/reports/microphone_diagnostics.json"
        )
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
            payload.update({"status": "error", "error": str(exc)})
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return False, "microphone_diagnostics_failed"

        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True, "microphone_diagnostics_written"

    def _verify_dae_event_store(self) -> Tuple[bool, str]:
        db_candidates = [
            self.repo_root / "modules/infrastructure/dae_daemon/memory/dae_audit.db",
            self.repo_root / "modules/infrastructure/dae_daemon/data/dae_audit.db",
        ]
        db_path = next((p for p in db_candidates if p.exists()), None)
        if db_path is None:
            return False, "dae_event_store_not_found"

        report_path = (
            self.repo_root / "modules/infrastructure/wre_core/reports/dae_event_store_health.json"
        )
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
            report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            if integrity != "ok" or int(dupes) > 0:
                return False, "event_store_integrity_failed"
            return True, "event_store_verified"
        except Exception as exc:
            payload = {
                "timestamp": time.time(),
                "db_path": str(db_path),
                "error": str(exc),
            }
            report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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
        self.task_log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "timestamp": event.timestamp,
            "source_file": event.source_file,
            "signature": event.signature,
            "line": event.line,
            "recommended_fix": event.recommended_fix,
            "auto_fix_attempted": event.auto_fix_attempted,
            "auto_fix_result": event.auto_fix_result,
        }
        with self.task_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _persist_escalation(self, escalation: SelfAuditEscalation) -> None:
        self.escalation_log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "timestamp": escalation.timestamp,
            "signature": escalation.signature,
            "source_file": escalation.source_file,
            "event_count": escalation.event_count,
            "recommended_fix": escalation.recommended_fix,
            "last_fix_result": escalation.last_fix_result,
            "dispatch_attempted": escalation.dispatch_attempted,
            "dispatch_result": escalation.dispatch_result,
        }
        with self.escalation_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _load_state(self) -> None:
        if not self.state_path.exists():
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
        except Exception:
            self._offsets = {}
            self._seen = {}
            self._last_fix_at = {}
            self._fix_stats = {}
            self._signature_stats = {}
            self._last_escalation_at = {}

    def _save_state(self) -> None:
        payload = {
            "offsets": self._offsets,
            "seen": self._seen,
            "last_fix_at": self._last_fix_at,
            "fix_stats": self._fix_stats,
            "signature_stats": self._signature_stats,
            "last_escalation_at": self._last_escalation_at,
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
