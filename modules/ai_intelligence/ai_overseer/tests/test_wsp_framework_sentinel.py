#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for AI Overseer WSP framework sentinel."""

from __future__ import annotations

import os
import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIIntelligenceOverseer
from modules.ai_intelligence.ai_overseer.src.wsp_framework_sentinel import WSPFrameworkSentinel


class TestWSPFrameworkSentinel(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(self.temp_dir)
        self.framework_src = self.repo_root / "WSP_framework" / "src"
        self.knowledge_src = self.repo_root / "WSP_knowledge" / "src"
        self.framework_src.mkdir(parents=True, exist_ok=True)
        self.knowledge_src.mkdir(parents=True, exist_ok=True)

        (self.framework_src / "WSP_15_Module_Prioritization_Scoring_System.md").write_text(
            "WSP 15 framework version\n",
            encoding="utf-8",
        )
        (self.framework_src / "WSP_96_MCP_Governance_and_Consensus_Protocol.md").write_text(
            "WSP 96 framework version\n",
            encoding="utf-8",
        )
        (self.knowledge_src / "WSP_15_Module_Prioritization_Scoring_System.md").write_text(
            "WSP 15 framework version\n",
            encoding="utf-8",
        )
        (self.knowledge_src / "WSP_96_MCP_Governance_and_Consensus_Protocol.md").write_text(
            "WSP 96 old backup version\n",
            encoding="utf-8",
        )
        (self.knowledge_src / "WSP_97_System_Execution_Prompting_Protocol.md").write_text(
            "WSP 97 knowledge only\n",
            encoding="utf-8",
        )

        (self.framework_src / "WSP_MASTER_INDEX.md").write_text(
            "\n".join(
                [
                    "| WSP | Title |",
                    "|-----|-------|",
                    "| WSP 15 | MPS |",
                    "| WSP 96 | MCP Governance |",
                    "| WSP 97 | System Prompting |",
                    "- **Next Available Number**: WSP 98",
                ]
            ),
            encoding="utf-8",
        )

        self.sentinel = WSPFrameworkSentinel(self.repo_root)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _index_allocation_case(self, added, declaration, *, omit=(), index_only=()):
        for number in added:
            (self.framework_src / f"WSP_{number:02d}_Allocation.md").write_text(
                f"WSP {number} fixture\n", encoding="utf-8")
        ids = set(self.sentinel._hash_wsp_files(self.framework_src))
        numbers = {int(name.split("_")[1]) for name in ids}
        rows = sorted((numbers | set(index_only)) - set(omit) - {0})
        text = ["| WSP | Title |", "|-----|-------|"]
        text.extend(f"| WSP {number} | Fixture |" for number in rows)
        text.append(declaration)
        (self.framework_src / "WSP_MASTER_INDEX.md").write_text(
            "\n".join(text) + "\n", encoding="utf-8")
        return ids

    def test_master_index_accepts_current_next_110(self) -> None:
        ids = self._index_allocation_case(
            (0, 109), "- **Next Available Number**: WSP 110")
        self.assertEqual(self.sentinel._check_master_index(ids), [])

    def test_master_index_accepts_new_allocation_110_then_next_111(self) -> None:
        ids = self._index_allocation_case(
            (109, 110), "- **Next Available Number**: WSP 111")
        self.assertEqual(self.sentinel._check_master_index(ids), [])

    def test_master_index_rejects_reused_or_skipped_next_number(self) -> None:
        for number in (99, 109, 111):
            with self.subTest(next_number=number):
                ids = self._index_allocation_case(
                    (109,), f"- **Next Available Number**: WSP {number}")
                issues = self.sentinel._check_master_index(ids)
                self.assertTrue(any("next available" in issue.lower() for issue in issues))

    def test_master_index_rejects_missing_or_malformed_next_declaration(self) -> None:
        for suffix in ("", "one hundred ten", "110.5", "110 trailing", "0", "-110", "+110"):
            with self.subTest(declaration=suffix):
                declaration = "- **Next Available Number**: WSP " + suffix if suffix else ""
                ids = self._index_allocation_case((109,), declaration)
                issues = self.sentinel._check_master_index(ids)
                self.assertTrue(any("next available" in issue.lower() for issue in issues))

    def test_master_index_rejects_duplicate_next_declarations(self) -> None:
        for second in (110, 111):
            with self.subTest(second_number=second):
                declaration = ("- **Next Available Number**: WSP 110\n"
                               f"- **Next Available Number**: WSP {second}")
                ids = self._index_allocation_case((109,), declaration)
                issues = self.sentinel._check_master_index(ids)
                self.assertTrue(any("next available" in issue.lower() for issue in issues))

    def test_master_index_still_requires_rows_for_actual_protocol_files(self) -> None:
        ids = self._index_allocation_case(
            (109,), "- **Next Available Number**: WSP 110", omit=(109,))
        issues = self.sentinel._check_master_index(ids)
        self.assertTrue(any("missing rows" in issue and "WSP 109" in issue for issue in issues))

    def test_master_index_cannot_reuse_an_index_only_allocated_number(self) -> None:
        ids = self._index_allocation_case(
            (109,), "- **Next Available Number**: WSP 110", index_only=(110,))
        issues = self.sentinel._check_master_index(ids)
        self.assertTrue(any("next available" in issue.lower() for issue in issues))

    def test_master_index_accepts_next_after_index_only_allocated_number(self) -> None:
        ids = self._index_allocation_case(
            (109,), "- **Next Available Number**: WSP 111", index_only=(110,))
        self.assertEqual(self.sentinel._check_master_index(ids), [])

    def test_detects_drift_and_framework_knowledge_diff(self) -> None:
        status = self.sentinel.check(force=True)
        self.assertTrue(status["available"])
        self.assertEqual(status["framework_count"], 2)
        self.assertEqual(status["knowledge_count"], 3)
        self.assertEqual(status["common_count"], 2)
        self.assertEqual(status["drift_count"], 1)
        self.assertIn("WSP_96_MCP_Governance_and_Consensus_Protocol", status["drift_files"])
        self.assertEqual(status["framework_only"], [])
        self.assertIn("WSP_97_System_Execution_Prompting_Protocol", status["knowledge_only"])
        self.assertEqual(status["index_issues"], [])
        self.assertEqual(status["severity"], "warning")
        self.assertIn("report_path", status)

    def test_uses_cache_within_ttl(self) -> None:
        with unittest.mock.patch.dict(os.environ, {"WSP_FRAMEWORK_AUDIT_TTL_SEC": "3600"}, clear=False):
            first = self.sentinel.check(force=True)
            second = self.sentinel.check(force=False)
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(first["drift_count"], second["drift_count"])

    def test_backup_only_knowledge_files_are_non_blocking_by_default(self) -> None:
        (self.knowledge_src / "WSP_96_MCP_Governance_and_Consensus_Protocol.md").write_text(
            "WSP 96 framework version\n",
            encoding="utf-8",
        )

        status = self.sentinel.check(force=True)
        self.assertEqual(status["drift_count"], 0)
        self.assertEqual(status["framework_only"], [])
        self.assertIn("WSP_97_System_Execution_Prompting_Protocol", status["knowledge_only"])
        self.assertEqual(status["severity"], "ok")

    def test_backup_only_can_be_promoted_to_warning_via_env(self) -> None:
        (self.knowledge_src / "WSP_96_MCP_Governance_and_Consensus_Protocol.md").write_text(
            "WSP 96 framework version\n",
            encoding="utf-8",
        )

        with unittest.mock.patch.dict(
            os.environ,
            {"WSP_FRAMEWORK_ALLOW_KNOWLEDGE_ONLY": "0"},
            clear=False,
        ):
            status = self.sentinel.check(force=True)
        self.assertEqual(status["drift_count"], 0)
        self.assertEqual(status["severity"], "warning")


class TestAIOverseerWSPAuditApi(unittest.TestCase):
    def test_monitor_wsp_framework_updates_last_status(self) -> None:
        overseer = object.__new__(AIIntelligenceOverseer)
        expected = {
            "available": True,
            "severity": "warning",
            "drift_count": 2,
            "framework_only": ["WSP_95_WRE_SKILLz_Wardrobe_Protocol"],
            "knowledge_only": ["WSP_95_MCP_Governance_and_Consensus_Protocol"],
            "index_issues": [],
        }
        sentinel = MagicMock()
        sentinel.check.return_value = expected

        overseer.wsp_framework_sentinel = sentinel
        overseer.wsp_framework_last_status = None

        with unittest.mock.patch.dict(os.environ, {"WSP_FRAMEWORK_ALERT_TO_STDOUT": "0"}, clear=False):
            result = AIIntelligenceOverseer.monitor_wsp_framework(
                overseer,
                force=True,
                emit_alert=True,
            )

        sentinel.check.assert_called_once_with(force=True)
        self.assertEqual(result, expected)
        self.assertEqual(overseer.wsp_framework_last_status, expected)

    def test_monitor_wsp_framework_handles_unavailable_sentinel(self) -> None:
        overseer = object.__new__(AIIntelligenceOverseer)
        overseer.wsp_framework_sentinel = None
        overseer.wsp_framework_last_status = None

        result = AIIntelligenceOverseer.monitor_wsp_framework(overseer, force=False)
        self.assertFalse(result["available"])
        self.assertEqual(result["severity"], "critical")

    def test_telemetry_event_routes_wsp_framework_audit_request(self) -> None:
        overseer = object.__new__(AIIntelligenceOverseer)
        overseer.monitor_wsp_framework = MagicMock(
            return_value={"severity": "warning", "drift_count": 3}
        )

        async def _run() -> None:
            await AIIntelligenceOverseer._handle_telemetry_event(
                overseer,
                {"event": "wsp_framework_audit_request", "force": True},
            )

        asyncio.run(_run())
        overseer.monitor_wsp_framework.assert_called_once_with(force=True, emit_alert=True)


if __name__ == "__main__":
    unittest.main()
