# -*- coding: utf-8 -*-
"""
Module linking and query command handlers.

Extracted from holo_index/cli.py (lines 2158-2319).
Handles: --link-modules, --query-modules, --wsp, --list-modules
"""

import os
from pathlib import Path


def handle_link_modules(args, safe_print):
    """Handle --link-modules. Returns True if handled."""
    if not args.link_modules:
        return False

    safe_print("[QWEN] Module Documentation Linker - Autonomous Intelligence")
    safe_print("=" * 65)
    safe_print("Using Qwen advisor to discover and link module documentation...")
    print()  # Empty line for spacing

    coordinator = None
    try:
        from holo_index.qwen_advisor.module_doc_linker import QwenModuleDocLinker
        from holo_index.qwen_advisor.holodae_coordinator import HoloDAECoordinator

        # Initialize Qwen coordinator
        if not args.verbose:
            os.environ.setdefault("HOLO_SILENT", "1")
        coordinator = HoloDAECoordinator()

        # Initialize module doc linker
        repo_root = Path(__file__).resolve().parents[3]
        linker = QwenModuleDocLinker(repo_root, coordinator)

        if args.module:
            # Link specific module
            safe_print(f"[LINK] Linking module: {args.module}")
            success = linker.link_single_module(
                args.module,
                interactive=args.interactive,
                force=args.force
            )

            if success:
                safe_print("\n[SUCCESS] Module documentation linked successfully")
            else:
                safe_print("\n[FAIL] Module linking failed - see errors above")

        else:
            # Link all modules
            safe_print("[LINK] Linking all modules...")
            results = linker.link_all_modules(
                interactive=args.interactive,
                force=args.force
            )

            # Display summary
            success_count = sum(1 for v in results.values() if v)
            fail_count = len(results) - success_count

            safe_print(f"\n[SUMMARY] Linking complete:")
            safe_print(f"  - Success: {success_count}/{len(results)} modules")
            if fail_count > 0:
                safe_print(f"  - Failed: {fail_count} modules")
                safe_print("\n[FAILED] Failed modules:")
                for module_name, success in results.items():
                    if not success:
                        safe_print(f"    - {module_name}")

        safe_print("\n" + "=" * 65)
        safe_print("[TIP] Each module now has MODULE_DOC_REGISTRY.json with intelligent document relationships")

    except Exception as e:
        safe_print(f"[ERROR] Module linking failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if coordinator:
            coordinator.stop_monitoring()

    return True


def handle_module_queries(args, safe_print):
    """Handle --query-modules, --wsp, --list-modules. Returns True if handled."""
    if not (args.query_modules or args.wsp or args.list_modules):
        return False

    try:
        from modules.infrastructure.database.src.agent_db import AgentDB
        db = AgentDB()

        if args.wsp:
            # Query modules implementing a specific WSP
            safe_print(f"[QUERY] Modules implementing {args.wsp}")
            safe_print("=" * 65)

            modules = db.get_modules_implementing_wsp(args.wsp)

            if modules:
                safe_print(f"\n[FOUND] {len(modules)} module(s) implementing {args.wsp}:")
                for module in modules:
                    safe_print(f"  - {module['module_domain']}/{module['module_name']}")
                    safe_print(f"    Path: {module['module_path']}")
                    safe_print(f"    Last linked: {module['linked_timestamp']}")
                    safe_print("")
            else:
                safe_print(f"\n[NOT FOUND] No modules found implementing {args.wsp}")

        elif args.list_modules:
            # List all registered modules
            safe_print("[QUERY] All registered modules")
            safe_print("=" * 65)

            modules = db.get_all_modules()

            if modules:
                safe_print(f"\n[FOUND] {len(modules)} registered module(s):")

                # Group by domain
                by_domain = {}
                for module in modules:
                    domain = module['module_domain']
                    if domain not in by_domain:
                        by_domain[domain] = []
                    by_domain[domain].append(module)

                for domain in sorted(by_domain.keys()):
                    safe_print(f"\n[{domain.upper()}]")
                    for module in by_domain[domain]:
                        safe_print(f"  - {module['module_name']}")

                        # Get document count
                        docs = db.get_module_documents(module['module_id'])
                        wsps = db.get_module_wsp_implementations(module['module_id'])

                        safe_print(f"    Documents: {len(docs)}, WSP implementations: {len(wsps)}")
                        safe_print(f"    Last linked: {module['linked_timestamp']}")
            else:
                safe_print("\n[EMPTY] No modules registered yet")
                safe_print("[TIP] Run: python holo_index.py --link-modules")

        elif args.module:
            # Query specific module documentation
            safe_print(f"[QUERY] Module documentation: {args.module}")
            safe_print("=" * 65)

            module = db.get_module(module_name=args.module)

            if module:
                safe_print(f"\n[MODULE] {module['module_domain']}/{module['module_name']}")
                safe_print(f"Path: {module['module_path']}")
                safe_print(f"Last linked: {module['linked_timestamp']}")

                # Get documents
                docs = db.get_module_documents(module['module_id'])
                safe_print(f"\n[DOCUMENTS] {len(docs)} document(s):")
                for doc in docs:
                    safe_print(f"  - [{doc['doc_type']}] {doc['title']}")
                    safe_print(f"    {doc['file_path']}")

                # Get WSP implementations
                wsps = db.get_module_wsp_implementations(module['module_id'])
                if wsps:
                    safe_print(f"\n[WSP IMPLEMENTATIONS] {len(wsps)} protocol(s):")
                    safe_print(f"  {', '.join(wsps)}")
            else:
                safe_print(f"\n[NOT FOUND] Module '{args.module}' not registered")
                safe_print("[TIP] Run: python holo_index.py --link-modules --module {args.module}")

        safe_print("\n" + "=" * 65)

    except Exception as e:
        safe_print(f"[ERROR] Query failed: {e}")
        import traceback
        traceback.print_exc()

    return True
