# -*- coding: utf-8 -*-
"""
Compliance and audit command handlers.

Extracted from holo_index/cli.py (lines 1437-1829).
Handles: --wsp88, --audit-docs, --check-module, --check-wsp-docs,
         --rollback-ascii, --fix-violations, --docs-file
"""

import os
from pathlib import Path


def handle_wsp88(args, safe_print):
    """Handle --wsp88 orphan analysis. Returns True if handled."""
    if not args.wsp88:
        return False

    print("[SEARCH] WSP 88 ORPHAN ANALYSIS - Intelligent Connection System")
    print("=" * 65)
    print("Analyzing HoloIndex for orphaned files and connection opportunities...")
    print("This follows first principles: Connect rather than delete, enhance rather than remove")
    print()

    try:
        from holo_index.monitoring.wsp88_orphan_analyzer import WSP88OrphanAnalyzer
        analyzer = WSP88OrphanAnalyzer()

        # Run comprehensive analysis
        results = analyzer.analyze_holoindex_orphans()
        report = analyzer.generate_holodae_report()

        print(report)

        # Show top connection suggestions
        suggestions = analyzer.get_connection_suggestions()
        if suggestions:
            print("\n[HOLODAE-RECOMMENDATIONS] Top Connection Opportunities:")
            print("-" * 60)
            for i, suggestion in enumerate(suggestions[:10], 1):
                print(f"{i:2d}. {suggestion}")

        print("\n[SUCCESS] WSP 88 Analysis Complete")
        print("Focus on CONNECTION opportunities - HoloDAE recommends keeping all utilities")
        print("=" * 65)

    except Exception as e:
        print(f"[ERROR] WSP 88 analysis failed: {e}")
        import traceback
        traceback.print_exc()

    return True


def handle_audit_docs(args, safe_print):
    """Handle --audit-docs documentation audit. Returns True if handled."""
    if not args.audit_docs:
        return False

    print("[SEARCH] WSP 83 DOCUMENTATION TREE AUDIT - Preventing Orphaned Documentation")
    print("=" * 70)

    try:
        import subprocess
        import shutil

        holoindex_root = Path(__file__).resolve().parents[2]
        orphaned_files = []
        valid_locations = {
            "README.md", "ModLog.md", "ROADMAP.md", "INTERFACE.md",
            "TESTModLog.md", "requirements.txt", "__init__.py"
        }

        # WSP 83 Orphan Detection Pattern
        def find_references(doc_path):
            """Check if document is referenced by other docs (per WSP 83)"""
            doc_name = Path(doc_path).name
            try:
                rg_path = shutil.which("rg")
                doc_rel = str(doc_path).replace("\\", "/")
                references = []

                if rg_path:
                    result = subprocess.run(
                        [
                            rg_path,
                            "-n",
                            "--fixed-strings",
                            "--glob",
                            "*.md",
                            "--glob",
                            "!**/.git/**",
                            doc_name,
                            str(holoindex_root)
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        cwd=holoindex_root
                    )
                    for line in result.stdout.split('\n'):
                        if not line.strip():
                            continue
                        parts = line.split(":", 2)
                        if not parts:
                            continue
                        path_part = parts[0].replace("\\", "/")
                        if path_part.endswith(doc_rel) or path_part == doc_rel:
                            continue
                        references.append(line)
                else:
                    for root, dirs, files in os.walk(holoindex_root):
                        dirs[:] = [d for d in dirs if d != ".git"]
                        for filename in files:
                            if not filename.endswith(".md"):
                                continue
                            file_path = Path(root) / filename
                            rel_path = file_path.relative_to(holoindex_root)
                            if str(rel_path).replace("\\", "/") == doc_rel:
                                continue
                            try:
                                content = file_path.read_text(encoding="utf-8", errors="ignore")
                            except OSError:
                                continue
                            if doc_name in content:
                                references.append(str(rel_path))
                                break

                return len(references) > 0
            except Exception:
                return False

        def serves_0102_purpose(doc_path):
            """Check if document serves 0102 operational needs (per WSP 83)"""
            doc_path = Path(doc_path)

            # Valid locations per WSP 49 and WSP 83
            if doc_path.name in valid_locations:
                return True

            # Check if it's a test file referenced in TESTModLog
            if 'tests' in str(doc_path):
                testmodlog = holoindex_root / "tests" / "TESTModLog.md"
                if testmodlog.exists():
                    with open(testmodlog, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if doc_path.name in content:
                            return True

            # Check if it's referenced in main ModLog
            modlog = holoindex_root / "ModLog.md"
            if modlog.exists():
                with open(modlog, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if doc_path.name in content:
                        return True

            return False

        # Audit all .py, .md, and .txt files in HoloIndex
        audit_paths = [
            holoindex_root / "tests",
            holoindex_root / "scripts",
            holoindex_root / "dae_cube_organizer",
            holoindex_root / "adaptive_learning",
            holoindex_root / "qwen_advisor",
            holoindex_root / "module_health",
            holoindex_root / "violation_tracker.py",
            holoindex_root / "ROADMAP.md",
            holoindex_root / "README.md",
            holoindex_root / "ModLog.md"
        ]

        for audit_path in audit_paths:
            if audit_path.exists():
                if audit_path.is_file():
                    files_to_check = [audit_path]
                else:
                    files_to_check = list(audit_path.rglob("*.py")) + list(audit_path.rglob("*.md")) + list(audit_path.rglob("*.txt"))

                for file_path in files_to_check:
                    rel_path = file_path.relative_to(holoindex_root)

                    # Skip __pycache__ and other system files
                    if '__pycache__' in str(rel_path) or rel_path.name.startswith('.'):
                        continue

                    # Check if file is attached to tree (has references or serves operational purpose)
                    has_references = find_references(str(rel_path))
                    serves_0102 = serves_0102_purpose(str(rel_path))

                    if not (has_references or serves_0102):
                        file_type = "Script" if file_path.suffix == '.py' else "Documentation" if file_path.suffix == '.md' else "Config"
                        orphaned_files.append((file_type, str(rel_path)))

        # Report findings per WSP 83
        if orphaned_files:
            print(f"[ALERT] FOUND {len(orphaned_files)} ORPHANED DOCUMENTS (WSP 83 VIOLATION)")
            print()
            print("[INFO] ORPHANED FILES (Not attached to system tree):")
            print("-" * 50)

            for file_type, file_path in orphaned_files:
                print(f"  • {file_type}: {file_path}")

            print()
            print("[FIX] WSP 83 REMEDIATION REQUIRED:")
            print("-" * 50)
            print("Per WSP 83 (Documentation Tree Attachment Protocol):")
            print("1. [CHECK] VERIFY operational purpose (does 0102 need this?)")
            safe_print("2. [LINK] CREATE reference chain (add to ModLog/TESTModLog)")
            safe_print("3. [LOCATION] ENSURE tree attachment (proper WSP 49 location)")
            safe_print("4. [DELETE] DELETE if unnecessary (prevents token waste)")
            safe_print("")
            safe_print("Reference Chain Requirements (WSP 83.4.2):")
            safe_print("  - Referenced in ModLog or TESTModLog")
            safe_print("  - Part of WSP 49 module structure")
            safe_print("  - Referenced by another operational document")

        else:
            safe_print("[SUCCESS] WSP 83 COMPLIANT")
            safe_print("   All documents properly attached to system tree")
            safe_print("   No orphaned documentation found")

        safe_print("")
        safe_print("[SUMMARY] AUDIT SUMMARY:")
        safe_print(f"   - Protocol: WSP 83 (Documentation Tree Attachment)")
        safe_print(f"   - Purpose: Prevent orphaned docs, ensure 0102 operational value")
        safe_print(f"   • Status: {'[VIOLATION]' if orphaned_files else '[COMPLIANT]'}")

        safe_print("=" * 70)

    except Exception as e:
        safe_print(f"[ERROR] WSP 83 Documentation audit failed: {e}")
        import traceback
        traceback.print_exc()

    return True


def handle_check_module(args, holo, safe_print):
    """Handle --check-module. Returns True if handled."""
    if not args.check_module:
        return False

    safe_print(f"[0102] MODULE EXISTENCE CHECK: '{args.check_module}'")
    safe_print("=" * 60)

    module_check = holo.check_module_exists(args.check_module)

    if module_check["exists"]:
        safe_print(f"[SUCCESS] MODULE EXISTS: {module_check['module_name']}")
        safe_print(f"[PATH] Path: {module_check['path']}")
        safe_print(f"[COMPLIANCE] WSP Compliance: {module_check['wsp_compliance']} ({module_check['compliance_score']})")

        if module_check["health_warnings"]:
            safe_print(f"[WARN] Health Issues:")
            for warning in module_check["health_warnings"]:
                safe_print(f"   • {warning}")

        safe_print(f"\n[TIP] RECOMMENDATION: {module_check['recommendation']}")
    else:
        safe_print(f"[ERROR] MODULE NOT FOUND: {module_check['module_name']}")
        if module_check.get("similar_modules"):
            safe_print(f"[SEARCH] Similar modules found:")
            for similar in module_check["similar_modules"]:
                safe_print(f"   • {similar}")
        safe_print(f"\n[TIP] RECOMMENDATION: {module_check['recommendation']}")

    safe_print("\n" + "=" * 60)
    safe_print("[PROTECT] WSP_84 COMPLIANCE: 0102 AGENTS MUST check module existence BEFORE ANY code generation - DO NOT VIBECODE")
    return True


def handle_check_wsp_docs(args, safe_print):
    """Handle --check-wsp-docs. Returns True if handled."""
    if not args.check_wsp_docs:
        return False

    safe_print(f"[WSP-GUARDIAN] WSP Documentation Guardian - Compliance Check")
    safe_print("=" * 60)

    try:
        from holo_index.qwen_advisor.orchestration.qwen_orchestrator import QwenOrchestrator

        orchestrator = QwenOrchestrator()

        mock_files = ["dummy_wsp_file.md"]
        mock_modules = ["dummy_module"]
        mock_snapshots = {}

        remediation_mode = args.fix_ascii
        if remediation_mode:
            safe_print("[WSP-GUARDIAN] ASCII auto-remediation ENABLED (--fix-ascii flag used)")
            safe_print("=" * 60)

        results = orchestrator._run_wsp_documentation_guardian(
            query="wsp documentation compliance check",
            files=mock_files,
            modules=mock_modules,
            module_snapshots=mock_snapshots,
            remediation_mode=remediation_mode
        )

        if results:
            safe_print("\n".join(results))
        else:
            safe_print("[WSP-GUARDIAN] All WSP documentation compliant and up-to-date")

        safe_print(f"\n[TIP] Use 'python -m holo_index.cli --search \"wsp\"' for real-time WSP guidance during development")

    except Exception as e:
        safe_print(f"[ERROR] Failed to run WSP Documentation Guardian: {e}")
        safe_print(f"[TIP] Ensure HoloIndex is properly configured")

    return True


def handle_rollback_ascii(args, safe_print):
    """Handle --rollback-ascii. Returns True if handled."""
    if not args.rollback_ascii:
        return False

    safe_print(f"[WSP-GUARDIAN] ASCII Rollback - {args.rollback_ascii}")
    safe_print("=" * 60)

    try:
        from holo_index.qwen_advisor.orchestration.qwen_orchestrator import QwenOrchestrator

        orchestrator = QwenOrchestrator()
        result = orchestrator.rollback_ascii_changes(args.rollback_ascii)
        safe_print(result)

    except Exception as e:
        safe_print(f"[ERROR] Failed to rollback ASCII changes: {e}")
        safe_print(f"[TIP] Ensure the file exists and has a backup in temp/wsp_backups/")

    return True


def handle_fix_violations(args, safe_print):
    """Handle --fix-violations. Returns True if handled."""
    if not args.fix_violations:
        return False

    safe_print("[WSP-COMPLIANCE] Auto-correcting root directory violations")
    safe_print("=" * 60)

    try:
        from holo_index.monitoring.root_violation_monitor import scan_and_correct_violations
        import asyncio

        corrections = asyncio.run(scan_and_correct_violations())

        safe_print("\n[RESULTS] Auto-correction completed:")
        safe_print(f"  [OK] Corrections applied: {corrections['corrections_applied']}")
        safe_print(f"  [FAIL] Failed corrections: {corrections['failed_corrections']}")
        safe_print(f"  [DATA] Total processed: {corrections['total_processed']}")

        if corrections['corrections_applied']:
            safe_print("\n[SUCCESS] Violations auto-corrected. Run search again to verify.")
        else:
            safe_print("\n[INFO] No auto-correctable violations found.")

    except Exception as e:
        safe_print(f"[ERROR] Failed to auto-correct violations: {e}")
        safe_print("[TIP] Manual correction may be required for some violations.")

    return True


def handle_docs_file(args, safe_print, throttler):
    """Handle --docs-file. Returns True if handled."""
    if not args.docs_file:
        return False

    throttler.add_section('header', f"[0102] DOCUMENTATION PROVISION: '{args.docs_file}'", priority=1, tags=['header', 'docs'])
    throttler.add_section('separator', "=" * 60, priority=5, tags=['separator'])

    coordinator = None
    try:
        from holo_index.qwen_advisor import HoloDAECoordinator
        if not args.verbose:
            os.environ.setdefault("HOLO_SILENT", "1")
        coordinator = HoloDAECoordinator()

        doc_info = coordinator.provide_docs_for_file(args.docs_file)

        if 'error' in doc_info:
            throttler.add_section('error', f"[ERROR] {doc_info['error']}", priority=1, tags=['error'])
            throttler.add_section('tip', "\n[TIP] Try using the full path or filename with extension", priority=3, tags=['tip'])
        else:
            throttler.add_section('module', f"[MODULE] {doc_info['module']}", priority=2, tags=['module'])
            throttler.add_section('docs_header', "\n[DOCUMENTATION]", priority=3, tags=['docs_header'])

            for doc_name, doc_data in doc_info['docs'].items():
                status = "[OK]" if doc_data['exists'] else "[FAIL]"
                throttler.add_section('doc_item', f"  {status} {doc_name}: {doc_data['path']}", priority=4, tags=['doc_item'])

            throttler.add_section('commands', "\n[COMMANDS]", priority=3, tags=['commands'])
            throttler.add_section('commands_text', "To read existing docs:", priority=4, tags=['commands_text'])
            for doc_name, doc_data in doc_info['docs'].items():
                if doc_data['exists']:
                    throttler.add_section('command', f"  cat \"{doc_data['path']}\"", priority=4, tags=['command'])

            missing_docs = [name for name, data in doc_info['docs'].items() if not data['exists']]
            if missing_docs:
                throttler.add_section('missing', "\n[MISSING]", priority=2, tags=['missing'])
                throttler.add_section('missing_list', f"  Missing docs: {', '.join(missing_docs)}", priority=3, tags=['missing_list'])
                throttler.add_section('compliance', "  Create these to improve WSP compliance", priority=3, tags=['compliance'])

    except Exception as e:
        throttler.add_section('error', f"[ERROR] Failed to get documentation: {e}", priority=1, tags=['error'])
        throttler.add_section('tip', "[TIP] Ensure HoloDAE coordinator is properly initialized", priority=3, tags=['tip'])
    finally:
        if coordinator:
            coordinator.stop_monitoring()

    throttler.add_section('separator', "\n" + "=" * 60, priority=5, tags=['separator'])
    throttler.add_section('principle', "[PRINCIPLE] HoloIndex provides docs directly - no grep needed (012's insight)", priority=4, tags=['principle'])

    output = throttler.render_prioritized_output(verbose=args.verbose if hasattr(args, 'verbose') else False)
    safe_print(output)
    return True
