#!/usr/bin/env python3
"""
Training Command Executor
Extracted from main.py per WSP 62 Large File Refactoring Protocol

Purpose: Execute training commands headlessly for 0102
Domain: ai_intelligence
Module: training_system
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from holo_index.qwen_advisor.pattern_memory import PatternMemory


def execute_training_command(command: str, targets: Optional[str], json_output: bool) -> None:
    """Execute training commands headlessly for 0102."""
    # Import UTF-8 hygiene functions from canonical module (WSP 62)
    from modules.ai_intelligence.utf8_hygiene.scripts.scanner import (
        run_utf8_hygiene_scan,
        summarize_utf8_findings,
    )

    response: Dict[str, Any] = {"command": command, "status": "error"}
    memory: Optional[PatternMemory] = None
    warning: Optional[str] = None

    try:
        memory = PatternMemory()
    except Exception as exc:
        warning = f"PatternMemory unavailable: {exc}"

    try:
        if command == "utf8_scan":
            target_list = None
            if targets:
                target_list = [item.strip() for item in targets.split(",") if item.strip()]
            findings = run_utf8_hygiene_scan(memory, target_list, interactive=False)
            response.update({"status": "ok", "count": len(findings), "findings": findings})
        elif command == "utf8_summary":
            target_list = None
            if targets:
                target_list = [item.strip() for item in targets.split(",") if item.strip()]
            summary = summarize_utf8_findings(memory, target_list)
            response.update(summary)
        elif command == "utf8_fix":
            from holo_index.qwen_advisor.orchestration.utf8_remediation_coordinator import (
                UTF8RemediationCoordinator,
            )

            coordinator = UTF8RemediationCoordinator(Path("."))
            scope_list = (
                [item.strip() for item in targets.split(",") if item.strip()]
                if targets
                else [None]
            )

            fix_results: List[Dict[str, Any]] = []
            total_files_fixed = 0
            total_violations_fixed = 0
            success = True

            for scope in scope_list:
                result = coordinator.remediate_utf8_violations(
                    scope=scope, auto_approve=True
                )
                fix_results.append({"scope": scope or ".", **result})
                total_files_fixed += result.get("files_fixed", 0)
                total_violations_fixed += result.get("violations_fixed", 0)
                if not result.get("success", True):
                    success = False

            response.update(
                {
                    "status": "ok",
                    "success": success,
                    "total_files_fixed": total_files_fixed,
                    "total_violations_fixed": total_violations_fixed,
                    "results": fix_results,
                }
            )
        elif command == "batch":
            from modules.infrastructure.idle_automation.src.idle_automation_dae import IdleAutomationDAE

            dae = IdleAutomationDAE()
            result = asyncio.run(dae._execute_pattern_training())
            response.update({"status": "ok", "result": result})
        else:
            response["message"] = f"Unknown training command '{command}'"
    except Exception as exc:
        response["error"] = str(exc)

    if warning:
        response["warning"] = warning

    if json_output:
        print(json.dumps(response, indent=2, default=str))
    else:
        status = response.get("status")
        if status == "ok":
            if command == "utf8_scan":
                print(f"[INFO] UTF-8 hygiene scan complete. Findings: {response.get('count', 0)}")
            elif command == "utf8_summary":
                print("[INFO] UTF-8 hygiene summary")
                print(f"  Total findings: {response.get('total_findings', 0)}")
                print(f"  Files affected: {response.get('files', 0)}")
                unique_chars = response.get("unique_characters")
                if unique_chars:
                    print(f"  Unique characters: {unique_chars}")
                for entry in response.get("top", []):
                    print(f"  {entry['path']}: {entry['count']} issues")
                    for sample in entry.get("samples", []):
                        print(f"    - {sample}")
            elif command == "utf8_fix":
                print("[INFO] UTF-8 remediation complete.")
                print(f"  Success: {response.get('success')}")
                print(f"  Files fixed: {response.get('total_files_fixed', 0)}")
                print(f"  Violations fixed: {response.get('total_violations_fixed', 0)}")
                for entry in response.get("results", []):
                    scope = entry.get("scope", ".")
                    fixed_count = entry.get("violations_fixed", entry.get("files_fixed", 0))
                    print(f"  - {scope}: {fixed_count} violations fixed")
                    if not entry.get("success", True):
                        print(f"    [WARN] {entry.get('message', 'Remediation issue encountered')}")
            elif command == "batch":
                result = response.get("result", {})
                print("[INFO] Batch training complete.")
                print(f"  Success: {result.get('success')}")
                print(f"  Patterns Stored: {result.get('patterns_stored')}")
                print(f"  Lines Processed: {result.get('lines_processed')}")
        else:
            print(f"[ERROR] Training command failed: {response.get('message', response.get('error'))}")
        if warning:
            print(f"[WARN] {warning}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        cmd = sys.argv[1]
        tgts = sys.argv[2] if len(sys.argv) >= 3 else None
        json_out = "--json" in sys.argv
        execute_training_command(cmd, tgts, json_out)
    else:
        print("Usage: python training_commands.py <command> [targets] [--json]")
        print("Commands: utf8_scan, utf8_summary, utf8_fix, batch")
