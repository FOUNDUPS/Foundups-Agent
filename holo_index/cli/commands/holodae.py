# -*- coding: utf-8 -*-
"""
HoloDAE lifecycle and menu feature command handlers.

Extracted from holo_index/cli.py (lines 2124-2157, 2324-2513).
Handles: --start-holodae, --stop-holodae, --holodae-status,
         --pattern-coach, --module-analysis, --health-check,
         --performance-metrics, --system-check, --slow-mode,
         --pattern-memory, --mcp-hooks, --mcp-log, --thought-log,
         --monitor-work
"""

import os
from pathlib import Path


def handle_holodae_lifecycle(args, safe_print):
    """Handle --start-holodae, --stop-holodae, --holodae-status. Returns True if handled."""
    if args.start_holodae:
        safe_print("[HOLODAE] Starting Autonomous HoloDAE monitoring...")
        try:
            from holo_index.qwen_advisor import start_holodae
            start_holodae()
            safe_print("[HOLODAE] Monitoring started successfully")
        except ImportError as e:
            safe_print(f"[HOLODAE-ERROR] Failed to start: {e}")
        return True

    elif args.stop_holodae:
        safe_print("[HOLODAE] Stopping Autonomous HoloDAE monitoring...")
        try:
            from holo_index.qwen_advisor import stop_holodae
            stop_holodae()
            safe_print("[HOLODAE] Monitoring stopped")
        except ImportError as e:
            safe_print(f"[HOLODAE-ERROR] Failed to stop: {e}")
        return True

    elif args.holodae_status:
        print("[HOLODAE] Status Report:")
        try:
            from holo_index.qwen_advisor import get_holodae_status
            status = get_holodae_status()
            print(f"  Active: {'Yes' if status['active'] else 'No'}")
            print(f"  Uptime: {status['uptime_minutes']} minutes")
            print(f"  Files Watched: {status['files_watched']}")
            print(f"  Current Module: {status.get('current_module', 'None')}")
            print(f"  Task Pattern: {status['task_pattern']}")
            print(f"  Session Actions: {status['session_actions']}")
            print(f"  Last Activity: {status['last_activity']}")
        except ImportError as e:
            safe_print(f"[HOLODAE-ERROR] Failed to get status: {e}")
        return True

    return False


def handle_holodae_features(args, safe_print, project_root):
    """Handle HoloDAE menu feature commands. Returns True if any handled."""
    if args.pattern_coach:
        safe_print("[PATTERN-COACH] Running behavioral vibecoding pattern analysis...")
        try:
            from holo_index.qwen_advisor.pattern_coach import PatternCoach
            coach = PatternCoach()
            safe_print("[PATTERN-COACH] Analysis complete - see coaching messages above")
        except Exception as e:
            safe_print(f"[ERROR] Pattern coach failed: {e}")
        return True

    if args.module_analysis:
        safe_print("[MODULE-ANALYSIS] Analyzing modules for duplicates and health issues...")
        try:
            from holo_index.module_health.size_audit import SizeAuditor

            auditor = SizeAuditor()
            repo_root = Path(__file__).resolve().parents[3]

            targets = [repo_root / "holo_index", repo_root / "modules"]
            issues_found = 0

            for target in targets:
                if target.exists():
                    safe_print(f"\n[AUDIT] Scanning {target.name}...")
                    results = auditor.audit_module(target)
                    for res in results:
                        safe_print(f"  [{res.risk_tier.value.upper()}] {res.path.name}: {res.line_count} lines")
                        safe_print(f"     Guidance: {res.guidance}")
                        issues_found += 1

            if issues_found == 0:
                safe_print("\n[SUCCESS] No size violations found.")
            else:
                safe_print(f"\n[SUMMARY] Found {issues_found} files needing attention.")

            safe_print("[MODULE-ANALYSIS] Complete")
        except Exception as e:
            safe_print(f"[ERROR] Module analysis failed: {e}")
        return True

    if args.health_check:
        safe_print("[HEALTH-CHECK] Running system architecture health analysis...")
        try:
            from holo_index.core import IntelligentSubroutineEngine
            from holo_index.reports.holo_system_check import run_system_check
            engine = IntelligentSubroutineEngine()
            results = engine.run_intelligent_analysis("health check", None)
            safe_print(results.get('summary', '[HEALTH-CHECK] Complete'))
            system_report = run_system_check(project_root)
            wsp_health = system_report.get("wsp_framework_health") or {}
            safe_print(
                "[HEALTH-CHECK][WSP] severity={severity} drift={drift} framework={framework} knowledge={knowledge}".format(
                    severity=wsp_health.get("severity", "unknown"),
                    drift=wsp_health.get("drift_count", 0),
                    framework=wsp_health.get("framework_count", 0),
                    knowledge=wsp_health.get("knowledge_count", 0),
                )
            )
        except Exception as e:
            safe_print(f"[ERROR] Health check failed: {e}")
        return True

    if args.performance_metrics:
        safe_print("[PERFORMANCE] HoloDAE Effectiveness & Performance Metrics")
        safe_print("=" * 65)
        try:
            from holo_index.qwen_advisor.telemetry import get_performance_summary
            summary = get_performance_summary()
            safe_print(summary)
        except Exception as e:
            safe_print(f"[ERROR] Performance metrics failed: {e}")
        return True

    if args.system_check:
        safe_print("[SYSTEM-CHECK] Verifying Holo CLI wiring...")
        try:
            from holo_index.reports.holo_system_check import run_system_check, write_system_check_report
            report = run_system_check(project_root)
            output_dir = Path(__file__).resolve().parents[2] / "reports"
            output_path = write_system_check_report(report, output_dir)
            summary = report.get("summary") or {}
            wsp_health = report.get("wsp_framework_health") or {}
            safe_print(
                "[SYSTEM-CHECK] Summary: ok {ok}, in_dev {in_dev}, missing {missing}, unwired {unwired}".format(
                    ok=summary.get("ok", 0),
                    in_dev=summary.get("in_dev", 0),
                    missing=summary.get("missing", 0),
                    unwired=summary.get("unwired", 0),
                )
            )
            safe_print(
                "[SYSTEM-CHECK][WSP] severity={severity} drift={drift} framework={framework} knowledge={knowledge}".format(
                    severity=wsp_health.get("severity", "unknown"),
                    drift=wsp_health.get("drift_count", 0),
                    framework=wsp_health.get("framework_count", 0),
                    knowledge=wsp_health.get("knowledge_count", 0),
                )
            )
            safe_print(f"[SYSTEM-CHECK] Report saved -> {output_path}")
        except Exception as e:
            safe_print(f"[ERROR] System check failed: {e}")
        return True

    if args.slow_mode:
        safe_print("[SLOW-MODE] Enabling recursive feedback with 2-3s delays...")
        safe_print("[SLOW-MODE] This mode is for training/observation - not production")
        os.environ['HOLODAE_SLOW_MODE'] = '1'
        safe_print("[SLOW-MODE] Enabled - all HoloDAE operations will use delays")
        return True

    if args.pattern_memory:
        safe_print("[PATTERN-MEMORY] Learned Intervention Patterns")
        safe_print("=" * 65)
        try:
            from modules.infrastructure.wre_core.wre_master_orchestrator import PatternMemory
            memory = PatternMemory.get()
            safe_print(str(memory))
        except Exception as e:
            safe_print(f"[ERROR] Pattern memory access failed: {e}")
        return True

    if args.mcp_hooks:
        safe_print("[MCP-HOOKS] Connector Health & Registration Status")
        safe_print("=" * 65)
        try:
            from modules.communication.livechat.src.mcp_youtube_integration import MCPYouTubeIntegration
            integration = MCPYouTubeIntegration()
            status = integration.connect_all()
            safe_print(f"MCP Status: {status}")
        except Exception as e:
            safe_print(f"[ERROR] MCP hooks inspection failed: {e}")
        return True

    if args.mcp_log:
        safe_print("[MCP-LOG] Recent MCP Tool Activity")
        safe_print("=" * 65)
        try:
            safe_print("[MCP-LOG] Feature in development - see Qwen Daemon logs")
        except Exception as e:
            safe_print(f"[ERROR] MCP log access failed: {e}")
        return True

    if args.thought_log:
        safe_print("[THOUGHT-LOG] Chain-of-Thought Breadcrumb Trail")
        safe_print("=" * 65)
        try:
            from holo_index.adaptive_learning.breadcrumb_tracer import BreadcrumbTracer
            tracer = BreadcrumbTracer()
            summary = tracer.summarize_session()

            safe_print(f"Session ID: {summary['session_id']}")
            safe_print(f"Timestamp: {summary['timestamp']}")
            safe_print(f"Total Actions: {summary['total_actions']}")

            if summary['searches']:
                safe_print("\n[SEARCHES]")
                for s in summary['searches']:
                    safe_print(f"  - {s['query']} ({s['results']} results)")

            if summary['actions']:
                safe_print("\n[ACTIONS]")
                for a in summary['actions']:
                    safe_print(f"  - {a['what']} -> {a['target']} ({a['result']})")

            if summary['learnings']:
                safe_print("\n[LEARNINGS]")
                for l in summary['learnings']:
                    safe_print(f"  - {l}")

            safe_print("\n[THOUGHT-LOG] Complete")
        except Exception as e:
            safe_print(f"[ERROR] Thought log access failed: {e}")
        return True

    if args.monitor_work:
        safe_print("[WORK-MONITOR] Starting work completion monitoring...")
        try:
            from modules.ai_intelligence.work_completion_publisher.src.monitoring_service import MonitoringService
            service = MonitoringService()
            import asyncio
            asyncio.run(service.start())
        except Exception as e:
            safe_print(f"[ERROR] Work monitoring failed: {e}")
        return True

    return False
