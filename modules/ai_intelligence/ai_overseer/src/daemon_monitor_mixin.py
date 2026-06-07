#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daemon monitoring + LLM delegation mixin for AI Overseer.

Moves the large daemon monitoring workflow out of ai_overseer.py so the
main orchestrator stays within WSP 87 size guidance.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.infrastructure.shared_utilities.local_model_selection import resolve_code_model_path
# Typed, allowlisted, shell=False auto-fix executor (security remediation; PR #767 follow-up)
from modules.ai_intelligence.ai_overseer.src.autofix_executor import execute_fix
from .types import AgentRole, AgentTeam

logger = logging.getLogger(__name__)


class DaemonMonitorMixin:
    """Provides daemon monitoring, LLM initialization, and auto-remediation helpers."""

    holo_available: bool = False
    holo_adapter = None
    orchestrator = None
    repo_root: Path
    metrics = None
    patch_executor = None
    fix_attempts: Dict[str, Any]

    def monitor_daemon(
        self,
        bash_id: str = None,
        skill_path: Path = None,
        bash_output: str = None,
        auto_fix: bool = True,
        report_complex: bool = True,
        chat_sender=None,
        announce_to_chat: bool = True,
    ) -> Dict[str, Any]:
        """Skill-driven daemon monitoring pipeline."""
        logger.info("[DAEMON-MONITOR] Starting ubiquitous monitor")

        skill = self._load_daemon_skill(skill_path)
        if not skill:
            return {"success": False, "error": f"Failed to load skill: {skill_path}"}

        logger.info("[DAEMON-MONITOR] Loaded skill for %s", skill.get("daemon_name", "unknown"))

        if bash_output is None and bash_id:
            bash_output = self._read_bash_output(bash_id, lines=100)

        if not bash_output:
            return {"success": False, "error": "No bash output provided"}

        detected_bugs = self._gemma_detect_errors(bash_output, skill)
        if not detected_bugs:
            logger.info("[DAEMON-MONITOR] No bugs detected in bash %s", bash_id)
            return {"success": True, "bugs_detected": 0, "bugs_fixed": 0, "reports_generated": 0}

        logger.info("[GEMMA-ASSOCIATE] Detected %s potential bugs", len(detected_bugs))
        classified_bugs = self._qwen_classify_bugs(detected_bugs, skill)

        results = {
            "success": True,
            "bugs_detected": len(classified_bugs),
            "bugs_fixed": 0,
            "reports_generated": 0,
            "fixes_applied": [],
            "reports": [],
        }

        for bug in classified_bugs:
            # Use ONLY pattern_name for tracking (matches change frequently, causing spam)
            pattern_key = bug['pattern_name']
            announce_this_bug = True

            if pattern_key in self.fix_attempts:
                attempt = self.fix_attempts[pattern_key]
                if attempt.get("disabled"):
                    continue
                time_since = time.time() - attempt["last_attempt"]
                if time_since < 300:
                    continue
                attempt["attempts"] += 1
                attempt["last_attempt"] = time.time()
                if attempt["attempts"] >= 3:
                    logger.warning("[LIMIT] Final attempt (%s) for %s", attempt["attempts"], bug["pattern_name"])
                announce_this_bug = False
            else:
                self.fix_attempts[pattern_key] = {
                    "attempts": 1,
                    "last_attempt": time.time(),
                    "first_seen": time.time(),
                    "disabled": False,
                    "last_fix_success": None,
                }

            fix_succeeded_this_time = False
            if bug["auto_fixable"] and auto_fix:
                fix_result = self._apply_auto_fix(bug, skill)
                if fix_result.get("success"):
                    results["bugs_fixed"] += 1
                    results["fixes_applied"].append(fix_result)
                    fix_succeeded_this_time = True
                    if announce_to_chat and announce_this_bug:
                        self._announce_fix(chat_sender, bug, "applying")
                        self._announce_fix(chat_sender, bug, "complete", fix_result=fix_result)
                else:
                    # Only announce first failure, then silence
                    if announce_to_chat and announce_this_bug and self.fix_attempts[pattern_key]["attempts"] == 1:
                        self._announce_fix(chat_sender, bug, "applying")
                        self._announce_fix(chat_sender, bug, "complete", fix_result=fix_result)
            elif bug["needs_0102"] and report_complex:
                report = self._generate_bug_report(bug, skill, bash_id)
                results["reports"].append(report)
                results["reports_generated"] += 1
                if announce_to_chat and announce_this_bug:
                    self._announce_fix(chat_sender, bug, "detection")

            # Per-pattern disable logic: disable after 3 failed attempts
            if pattern_key in self.fix_attempts:
                self.fix_attempts[pattern_key]["last_fix_success"] = fix_succeeded_this_time
                if self.fix_attempts[pattern_key]["attempts"] >= 3 and not fix_succeeded_this_time:
                    self.fix_attempts[pattern_key]["disabled"] = True
                    logger.warning("[SILENCED] Pattern %s disabled after 3 failures", bug["pattern_name"])

        self._store_monitoring_patterns(skill_path, results)
        return results

    def _load_daemon_skill(self, skill_path: Path) -> Optional[Dict[str, Any]]:
        try:
            if not skill_path:
                return None
            with open(skill_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            logger.error("[SKILL-LOAD] Failed to load %s: %s", skill_path, exc)
            return None

    def _read_bash_output(self, bash_id: str, lines: int = 100) -> Optional[str]:
        logger.warning("[BASH-READ] BashOutput integration not yet implemented")
        return None

    def _initialize_gemma(self) -> bool:
        if getattr(self, "_gemma_engine", None) is not None:
            return getattr(self, "_gemma_available", False)
        try:
            from holo_index.qwen_advisor.gemma_rag_inference import GemmaRAGInference
            self._gemma_engine = GemmaRAGInference()
            self._gemma_available = True
            logger.info("[GEMMA] Initialized Gemma 270M for pattern validation")
            return True
        except Exception as exc:
            logger.warning("[GEMMA] Gemma unavailable, using static patterns: %s", exc)
            self._gemma_available = False
            return False

    def _gemma_detect_errors(self, bash_output: str, skill: Dict[str, Any]) -> List[Dict[str, Any]]:
        detected: List[Dict[str, Any]] = []
        error_patterns = skill.get("error_patterns", {})
        for pattern_name, pattern_config in error_patterns.items():
            regex = pattern_config.get("regex", "")
            if not regex:
                continue
            matches = re.findall(regex, bash_output, re.IGNORECASE | re.MULTILINE)
            if not matches:
                continue
            if self._initialize_gemma():
                log_excerpt = bash_output[-500:]
                prompt = (
                    f"Error Pattern: {pattern_name}\n"
                    f"Description: {pattern_config.get('description', '')}\n"
                    f"Matches: {len(matches)}\n"
                    f"Log Context: {log_excerpt}\n\n"
                    "Deep Think: Is this a genuine bug requiring action?\n"
                    "First Principles: Does this indicate system malfunction?\n"
                    "Occam's Razor: What is the SIMPLEST explanation?\n\n"
                    "Answer: YES (genuine bug) or NO (false positive/noise)\n"
                    "Confidence: 0.0-1.0"
                )
                try:
                    result = self._gemma_engine.infer(prompt)  # type: ignore[attr-defined]
                    if result.response.upper().startswith("YES") and result.confidence > 0.7:
                        detected.append(
                            {
                                "pattern_name": pattern_name,
                                "matches": matches,
                                "config": pattern_config,
                                "gemma_confidence": result.confidence,
                                "ml_validated": True,
                            }
                        )
                    else:
                        logger.debug("[GEMMA] Rejected %s as false positive", pattern_name)
                except Exception as exc:
                    logger.warning("[GEMMA] ML validation failed, using static: %s", exc)
                    detected.append(
                        {
                            "pattern_name": pattern_name,
                            "matches": matches,
                            "config": pattern_config,
                            "ml_validated": False,
                        }
                    )
            else:
                detected.append(
                    {
                        "pattern_name": pattern_name,
                        "matches": matches,
                        "config": pattern_config,
                        "ml_validated": False,
                    }
                )
        return detected

    def _initialize_qwen(self) -> bool:
        if getattr(self, "_qwen_engine", None) is not None:
            return getattr(self, "_qwen_available", False)
        try:
            from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine
            model_path = resolve_code_model_path()
            self._qwen_engine = QwenInferenceEngine(
                model_path=model_path,
                max_tokens=512,
                temperature=0.2,
                context_length=2048,
            )
            if self._qwen_engine.initialize():
                self._qwen_available = True
                logger.info("[QWEN] Initialized Qwen 1.5B for strategic classification")
                return True
            self._qwen_available = False
            return False
        except Exception as exc:
            logger.warning("[QWEN] Qwen unavailable, using static config: %s", exc)
            self._qwen_available = False
            return False

    def _fallback_static_classification(self, bug: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        qwen_action = config.get("qwen_action", "ignore")
        wsp_15_mps = config.get("wsp_15_mps", {})
        complexity = wsp_15_mps.get("complexity", 3)
        return {
            "pattern_name": bug["pattern_name"],
            "complexity": complexity,
            "auto_fixable": qwen_action == "auto_fix",
            "needs_0102": qwen_action == "bug_report",
            "qwen_action": qwen_action,
            "matches": bug["matches"],
            "config": config,
            "ml_classified": False,
        }

    def _qwen_classify_bugs(self, detected_bugs: List[Dict[str, Any]], skill: Dict[str, Any]) -> List[Dict[str, Any]]:
        classified: List[Dict[str, Any]] = []
        for bug in detected_bugs:
            config = bug["config"]
            if self._initialize_qwen():
                prompt = json.dumps(
                    {
                        "pattern": bug["pattern_name"],
                        "description": config.get("description", ""),
                        "matches": len(bug["matches"]),
                        "daemon": skill.get("daemon_name", "unknown"),
                    }
                )
                try:
                    response = self._qwen_engine.generate_response(prompt)  # type: ignore[attr-defined]
                    qwen_analysis = json.loads(response)
                    classified.append(
                        {
                            "pattern_name": bug["pattern_name"],
                            "complexity": qwen_analysis["complexity"],
                            "auto_fixable": qwen_analysis["action"] == "auto_fix",
                            "needs_0102": qwen_analysis["action"] == "bug_report",
                            "qwen_action": qwen_analysis["action"],
                            "mps_score": qwen_analysis["total_mps"],
                            "priority": qwen_analysis["priority"],
                            "rationale": qwen_analysis["rationale"],
                            "matches": bug["matches"],
                            "config": config,
                            "ml_classified": True,
                        }
                    )
                    continue
                except Exception:
                    pass
            fallback = self._fallback_static_classification(bug, config)
            if fallback["qwen_action"] == "ignore":
                continue
            fallback["fix_action"] = config.get("fix_action")
            fallback["fix_module"] = config.get("fix_module")
            fallback["fix_function"] = config.get("fix_function")
            classified.append(fallback)
        return classified

    def _apply_auto_fix(self, bug: Dict[str, Any], skill: Dict[str, Any]) -> Dict[str, Any]:
        fix_action = bug.get("fix_action")
        pattern_name = bug["pattern_name"]
        skill_name = skill.get("daemon_name", "unknown_daemon")
        exec_id = f"fix_{pattern_name}_{int(time.time())}"
        start_time = time.time()

        try:
            if fix_action in ["run_reauthorization_script", "install_missing_library"]:
                # Typed, allowlisted, shell=False executor. Skill config can only SELECT
                # the action; no command string reaches a shell. install_missing_library is
                # NOT allowlisted (no live config uses it; latent) -> executor REJECTS it.
                packet = execute_fix(fix_action, bug.get("config", {}), wait=True, timeout=30)
                success = packet.success
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.metrics.append_performance_metric(
                    skill_name=skill_name,
                    execution_id=exec_id,
                    execution_time_ms=execution_time_ms,
                    agent="ai_overseer",
                    exception_occurred=not success,
                )
                self.metrics.append_outcome_metric(
                    skill_name=skill_name,
                    execution_id=exec_id,
                    decision=fix_action,
                    expected_decision=fix_action,
                    correct=success,
                    confidence=1.0 if success else 0.0,
                    reasoning=f"{fix_action} {packet.decision}: {packet.reason}",
                    agent="ai_overseer",
                )
                return {
                    "success": success,
                    "bug": pattern_name,
                    "fix_applied": fix_action,
                    "method": "autofix_executor",
                    "decision": packet.decision,
                    "evidence": packet.to_dict(),
                    "returncode": packet.returncode,
                    "execution_id": exec_id,
                }

            if fix_action == "rotate_api_credentials":
                try:
                    from modules.platform_integration.youtube_auth.src.youtube_auth import get_authenticated_service
                except ImportError as exc:
                    return {"success": False, "bug": pattern_name, "error": f"Cannot import youtube_auth: {exc}"}
                try:
                    get_authenticated_service()
                    success = True
                    error_msg = None
                except Exception as exc:
                    success = False
                    error_msg = str(exc)
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.metrics.append_performance_metric(
                    skill_name=skill_name,
                    execution_id=exec_id,
                    execution_time_ms=execution_time_ms,
                    agent="ai_overseer",
                    exception_occurred=not success,
                )
                self.metrics.append_outcome_metric(
                    skill_name=skill_name,
                    execution_id=exec_id,
                    decision=fix_action,
                    expected_decision=fix_action,
                    correct=success,
                    confidence=1.0 if success else 0.0,
                    reasoning=f"API rotation {'succeeded' if success else f'failed: {error_msg}'}",
                    agent="ai_overseer",
                )
                if success:
                    return {
                        "success": True,
                        "bug": pattern_name,
                        "fix_applied": fix_action,
                        "method": "api_rotation",
                        "message": "API credentials rotated to next available set",
                        "execution_id": exec_id,
                    }
                return {
                    "success": False,
                    "bug": pattern_name,
                    "error": error_msg,
                    "method": "api_rotation",
                    "execution_id": exec_id,
                }

            if fix_action == "reconnect_service":
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.metrics.append_performance_metric(
                    skill_name=skill_name,
                    execution_id=exec_id,
                    execution_time_ms=execution_time_ms,
                    agent="ai_overseer",
                    exception_occurred=False,
                )
                self.metrics.append_outcome_metric(
                    skill_name=skill_name,
                    execution_id=exec_id,
                    decision=fix_action,
                    expected_decision=fix_action,
                    correct=True,
                    confidence=0.5,
                    reasoning="Service reconnection placeholder (not yet implemented)",
                    agent="ai_overseer",
                )
                return {
                    "success": True,
                    "bug": pattern_name,
                    "fix_applied": fix_action,
                    "method": "service_reconnect",
                    "message": "Service reconnection attempted (placeholder)",
                    "execution_id": exec_id,
                }

            # 2026-03-07: RotationSupervisor stall recovery (WSP 77) - typed, shell=False.
            # browser/operation come from breadcrumb metadata and are enum-validated by the
            # executor (chrome|edge x comments|shorts); argv is a fixed vector, never a string.
            if fix_action == "trigger_next_rotation":
                browser = bug.get("metadata", {}).get("browser", "edge")
                operation = bug.get("metadata", {}).get("operation", "comments")
                packet = execute_fix(
                    fix_action,
                    bug.get("config", {}),
                    {"browser": browser, "operation": operation},
                    wait=True,
                    timeout=360,  # 6 min for full rotation
                    cwd=self.repo_root,
                )
                success = packet.success
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.metrics.append_performance_metric(
                    skill_name=skill_name,
                    execution_id=exec_id,
                    execution_time_ms=execution_time_ms,
                    agent="ai_overseer",
                    exception_occurred=not success,
                )
                self.metrics.append_outcome_metric(
                    skill_name=skill_name,
                    execution_id=exec_id,
                    decision=fix_action,
                    expected_decision=fix_action,
                    correct=success,
                    confidence=1.0 if success else 0.0,
                    reasoning=f"Rotation trigger {packet.decision}: {browser}_{operation}",
                    agent="ai_overseer",
                )
                return {
                    "success": success,
                    "bug": pattern_name,
                    "fix_applied": fix_action,
                    "method": "autofix_executor",
                    "decision": packet.decision,
                    "evidence": packet.to_dict(),
                    "returncode": packet.returncode,
                    "execution_id": exec_id,
                }

            if fix_action == "add_unicode_conversion_before_youtube_send":
                affected_module = bug.get(
                    "fix_module",
                    "modules.ai_intelligence.banter_engine.src.banter_engine",
                )
                affected_file = affected_module.replace(".", "/") + ".py"
                patch_content = f"""diff --git a/{affected_file} b/{affected_file}
index 0000000..1111111 100644
--- a/{affected_file}
+++ b/{affected_file}
@@ -1,3 +1,4 @@
+# -*- coding: utf-8 -*-
 \"\"\"
 Module implementation
 \"\"\"
"""
                patch_result = self.patch_executor.apply_patch(  # type: ignore[call-arg]
                    patch_content=patch_content,
                    patch_description=f"Add UTF-8 header to {affected_file}",
                )
                success = patch_result["success"]
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.metrics.append_performance_metric(
                    skill_name=skill_name,
                    execution_id=exec_id,
                    execution_time_ms=execution_time_ms,
                    agent="ai_overseer",
                    exception_occurred=not success,
                )
                if success:
                    verification = self._verify_unicode_patch(patch_result.get("files_modified", []))
                    self.metrics.append_outcome_metric(
                        skill_name=skill_name,
                        execution_id=f"{exec_id}_verify",
                        decision="verify_unicode_patch",
                        expected_decision="verify_unicode_patch",
                        correct=verification["verified"],
                        confidence=0.9 if verification["verified"] else 0.0,
                        reasoning=verification["reason"],
                        agent="ai_overseer",
                    )
                    if verification["verified"]:
                        return {
                            "success": True,
                            "bug": pattern_name,
                            "fix_applied": fix_action,
                            "method": "patch_executor",
                            "files_modified": patch_result["files_modified"],
                            "message": f"UTF-8 header patch applied to {affected_file}",
                            "execution_id": exec_id,
                            "needs_restart": True,
                            "verification": verification,
                        }
                    return {
                        "success": False,
                        "bug": pattern_name,
                        "fix_applied": fix_action,
                        "error": "Verification failed - manual review required",
                        "execution_id": exec_id,
                        "verification": verification,
                        "needs_restart": False,
                        "escalate": True,
                    }
                self.metrics.append_outcome_metric(
                    skill_name=skill_name,
                    execution_id=exec_id,
                    decision=fix_action,
                    expected_decision=fix_action,
                    correct=False,
                    confidence=0.0,
                    reasoning=patch_result.get("error", "Patch application failed"),
                    agent="ai_overseer",
                )
                return {
                    "success": False,
                    "bug": pattern_name,
                    "fix_applied": None,
                    "error": patch_result.get("error", "Patch application failed"),
                    "violations": patch_result.get("violations", []),
                    "execution_id": exec_id,
                }

            return {
                "success": False,
                "bug": pattern_name,
                "error": f"Unknown fix_action: {fix_action}",
                "available_fixes": [
                    "run_reauthorization_script",
                    "rotate_api_credentials",
                    "reconnect_service",
                    "add_unicode_conversion_before_youtube_send",
                ],
                "execution_id": exec_id,
            }

        except subprocess.TimeoutExpired:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.metrics.append_performance_metric(
                skill_name=skill_name,
                execution_id=exec_id,
                execution_time_ms=execution_time_ms,
                agent="ai_overseer",
                exception_occurred=True,
                exception_type="TimeoutExpired",
            )
            return {
                "success": False,
                "bug": pattern_name,
                "error": "Fix command timed out after 30s",
                "execution_id": exec_id,
            }
        except Exception as exc:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.metrics.append_performance_metric(
                skill_name=skill_name,
                execution_id=exec_id,
                execution_time_ms=execution_time_ms,
                agent="ai_overseer",
                exception_occurred=True,
                exception_type=type(exc).__name__,
            )
            return {
                "success": False,
                "bug": pattern_name,
                "error": str(exc),
                "traceback": traceback.format_exc()[:500],
                "execution_id": exec_id,
            }

    def _generate_bug_report(self, bug: Dict[str, Any], skill: Dict[str, Any], bash_id: str) -> Dict[str, Any]:
        return {
            "id": f"bug_{int(time.time())}",
            "daemon": skill.get("daemon_name", "unknown"),
            "bash_id": bash_id,
            "pattern": bug["pattern_name"],
            "complexity": bug["complexity"],
            "auto_fixable": bug["auto_fixable"],
            "needs_0102_review": bug["needs_0102"],
            "matches": bug["matches"],
            "recommended_fix": bug.get("fix_action", "Manual review required"),
            "priority": skill.get("report_priority", "P3"),
            "timestamp": time.time(),
        }

    def _store_monitoring_patterns(self, skill_path: Path, results: Dict[str, Any]) -> None:
        try:
            skill = self._load_daemon_skill(skill_path)
            if not skill:
                return
            if "learning_stats" not in skill:
                skill["learning_stats"] = {
                    "total_bugs_detected": 0,
                    "total_bugs_fixed": 0,
                    "total_reports_generated": 0,
                }
            skill["learning_stats"]["total_bugs_detected"] += results["bugs_detected"]
            skill["learning_stats"]["total_bugs_fixed"] += results["bugs_fixed"]
            skill["learning_stats"]["total_reports_generated"] += results["reports_generated"]
            skill["last_monitoring_run"] = time.time()
            with open(skill_path, "w", encoding="utf-8") as handle:
                json.dump(skill, handle, indent=2)
        except Exception as exc:
            logger.warning("[LEARNING] Failed to update skill stats: %s", exc)

    def _announce_fix(
        self,
        chat_sender,
        bug: Dict[str, Any],
        phase: str,
        verification: Optional[Dict[str, Any]] = None,
        fix_result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not chat_sender:
            return False
        try:
            from modules.ai_intelligence.banter_engine.src.banter_engine import BanterEngine
            banter = BanterEngine(emoji_enabled=True)
            if phase == "detection":
                error_type = bug["pattern_name"].replace("_", " ").title()
                priority = bug.get("config", {}).get("wsp_15_mps", {}).get("priority", "P1")
                emoji_map = {"P0": "[U+1F525]", "P1": "[U+1F50D]", "P2": "[U+1F6E0]"}
                emoji = emoji_map.get(priority, "[U+1F50D]")
                message = f"012 detected {error_type} [{priority}] {emoji}"
            elif phase == "applying":
                message = "012 applying fix, restarting MAGAdoom [U+1F527]"
            elif phase == "complete":
                if verification and verification.get("verified"):
                    message = bug["config"].get("announcement_template", "012 fix applied - system online [U+2705]")
                    # Handle variable substitution in announcement template
                    if "$1" in message and "matches" in bug:
                        matches = bug.get("matches", [])
                        if matches and len(matches) > 0:
                            library_name = matches[0] if isinstance(matches[0], str) else str(matches[0])
                            message = message.replace("$1", library_name.strip())
                elif fix_result and fix_result.get("success"):
                    message = "012 fix applied - verification pending [U+23F3]"
                else:
                    message = "012 fix failed - creating bug report [U+26A0]"
            else:
                return False
            rendered = banter._convert_unicode_tags_to_emoji(message)
            try:
                asyncio.create_task(
                    chat_sender.send_message(rendered, response_type="update")
                )
            except RuntimeError:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(
                            chat_sender.send_message(rendered, response_type="update")
                        )
                    )
                else:
                    loop.run_until_complete(
                        chat_sender.send_message(rendered, response_type="update")
                    )
            return True
        except Exception as exc:
            logger.error("[ANNOUNCE] Failed: %s", exc)
            return False

    def _verify_unicode_patch(self, files_modified: List[str]) -> Dict[str, Any]:
        if not files_modified:
            return {"verified": False, "reason": "No files reported as modified"}
        missing_files: List[str] = []
        missing_header: List[str] = []
        for rel_path in files_modified:
            file_path = (self.repo_root / rel_path).resolve()
            if not file_path.exists():
                missing_files.append(rel_path)
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    first_lines = [handle.readline() for _ in range(5)]
            except Exception as exc:
                missing_header.append(f"{rel_path} (read error: {exc})")
                continue
            if not any("# -*- coding: utf-8 -*-" in line for line in first_lines):
                missing_header.append(rel_path)
        if missing_files:
            return {"verified": False, "reason": f"Modified files missing: {', '.join(missing_files)}"}
        if missing_header:
            return {"verified": False, "reason": f"UTF-8 header missing in: {', '.join(missing_header)}"}
        return {"verified": True, "reason": "UTF-8 header confirmed in patched files"}

    def check_rotation_stalls(
        self,
        minutes: int = 5,
        auto_trigger: bool = True,
    ) -> Dict[str, Any]:
        """
        Check breadcrumb telemetry for rotation stalls and optionally trigger CLI rotation.

        This enables AI Overseer to autonomously detect when the rotation system stalls
        (heartbeat_stale, task_killed) and trigger the next rotation phase via CLI.

        Args:
            minutes: Look back window in minutes
            auto_trigger: Whether to automatically trigger rotation on stall detection

        Returns:
            Dict with stalls detected and actions taken
        """
        try:
            from modules.communication.livechat.src.breadcrumb_telemetry import get_breadcrumb_telemetry
            telemetry = get_breadcrumb_telemetry()
        except ImportError:
            return {"success": False, "error": "Breadcrumb telemetry not available"}

        # Query for stall-related breadcrumbs
        stall_patterns = ["stall_detected", "KILLED", "STALE", "rotation stalled"]
        stalls_found = []

        for pattern in stall_patterns:
            try:
                breadcrumbs = telemetry.get_recent_breadcrumbs(minutes=minutes, source_dae="rotation_supervisor")
                for bc in breadcrumbs:
                    message = bc.get("message", "")
                    if pattern.lower() in message.lower():
                        stalls_found.append({
                            "pattern": pattern,
                            "message": message,
                            "metadata": bc.get("metadata", {}),
                            "timestamp": bc.get("timestamp"),
                        })
            except Exception as e:
                logger.debug(f"[STALL-CHECK] Error querying breadcrumbs: {e}")

        if not stalls_found:
            return {"success": True, "stalls_detected": 0, "message": "No stalls detected"}

        logger.warning(f"[STALL-CHECK] Detected {len(stalls_found)} stall events in last {minutes} minutes")

        result = {
            "success": True,
            "stalls_detected": len(stalls_found),
            "stalls": stalls_found,
            "rotations_triggered": 0,
        }

        if auto_trigger and stalls_found:
            # Trigger rotation for the most recent stall via the typed, shell=False executor
            # (non-blocking spawn). browser is enum-validated; operation fixed to comments.
            latest_stall = stalls_found[-1]
            browser = latest_stall.get("metadata", {}).get("browser", "edge")
            operation = "comments"  # Default to comments rotation

            packet = execute_fix(
                "trigger_next_rotation",
                {},
                {"browser": browser, "operation": operation},
                wait=False,
                cwd=self.repo_root,
            )
            if packet.decision == "ALLOWED" and packet.success:
                result["rotations_triggered"] = 1
                result["rotation_pid"] = packet.pid
                result["rotation_evidence"] = packet.to_dict()
                logger.info(f"[STALL-CHECK] Rotation spawned (PID: {packet.pid})")
            else:
                result["rotation_error"] = packet.reason
                logger.error(
                    f"[STALL-CHECK] Rotation not spawned: {packet.decision}/{packet.reason}"
                )

        return result
