#!/usr/bin/env python3
"""
Training System Launch Script
Extracted from main.py per WSP 62 Large File Refactoring Protocol

Purpose: Qwen/Gemma Training System submenu
Domain: ai_intelligence
Module: training_system

Implements WRE pattern (WSP 46): Qwen coordinates, Gemma executes
"""

import asyncio
from typing import Optional, Dict, Any
from holo_index.qwen_advisor.pattern_memory import PatternMemory
import os

# WRE CoT preflight - recursive enforcement after watch period
try:
    from modules.infrastructure.wre_core.src.dae_preflight import preflight_guard
except ImportError:
    def preflight_guard(name, quiet=True):
        def decorator(func):
            return func
        return decorator


@preflight_guard("training_system_dae")
def run_training_system():
    """
    Qwen/Gemma Training System submenu.
    Implements WRE pattern (WSP 46): Qwen coordinates, Gemma executes.
    """
    # Import run_utf8_hygiene_scan from main module context
    import sys
    import os
    from pathlib import Path
    
    repo_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo_root))
    from main import run_utf8_hygiene_scan

    corpus_name = os.getenv("OPENCLAW_TRAINING_CORPUS", "012.txt")
    corpus_path = repo_root / corpus_name
    total_lines = None
    if corpus_path.exists():
        try:
            with open(corpus_path, "r", encoding="utf-8", errors="ignore") as f:
                total_lines = sum(1 for _ in f) or 1
        except Exception:
            pass

    def load_memory() -> tuple[Optional[Any], Optional[Dict[str, Any]]]:
        try:
            mem = PatternMemory()
            stats = mem.get_stats()
            return mem, stats
        except Exception as err:
            print(f"[WARN] Could not load stats: {err}")
            print("   Pattern memory may need initialization.")
            return None, None

    while True:
        memory, stats = load_memory()

        print("\n" + "=" * 60)
        print("[MENU] QWEN/GEMMA TRAINING SYSTEM")
        print("=" * 60)
        print("Implements WRE Pattern (WSP 46): Qwen coordinates, Gemma executes")
        lines_display = f"{total_lines:,}" if total_lines else "unknown"
        print(f"Training Data: {corpus_name} ({lines_display} lines of operational decisions)")
        print("=" * 60)

        if stats:
            print(f"\n[INFO] CURRENT STATUS:")
            print(f"   Patterns Stored: {stats['total_patterns']}")
            if total_lines:
                prog_pct = (stats['checkpoint_line'] / total_lines) * 100
                print(f"   {corpus_name} Progress: {stats['checkpoint_line']}/{total_lines} ({prog_pct:.1f}%)")
            else:
                print(f"   {corpus_name} Progress: {stats['checkpoint_line']} lines (corpus not found, total unknown)")
            print(f"   Verification Rate: {stats['verification_rate']:.1%}")
            print(f"   Sources: {stats['sources']}")

        print("\n" + "-" * 60)
        print("TRAINING OPTIONS:")
        print("-" * 60)
        print(f"1. Start Batch Training (Process {corpus_name})")
        print("2. UTF-8 Hygiene Scan (Gemma training data)")
        print("3. Gemma Policy Drill (coming soon)")
        print("4. Qwen Summary Drill (coming soon)")
        print("5. View Training Progress")
        print("6. Test Pattern Recall")
        print("7. Test Qwen/Gemma Routing (Adaptive AI)")
        print("8. View Training Metrics")
        print("9. Clear Pattern Memory (Reset)")
        print("0. Back to Main Menu")
        print("-" * 60)

        choice = input("\nSelect option (0-9): ").strip()

        if choice == "0":
            print("[INFO] Returning to main menu...")
            break

        elif choice == "1":
            print("\n[INFO] Starting Batch Training...")
            print("=" * 60)
            try:
                from modules.infrastructure.idle_automation.src.idle_automation_dae import IdleAutomationDAE

                dae = IdleAutomationDAE()
                result = asyncio.run(dae._execute_pattern_training())

                print("\n[RESULT]")
                print(f"  Success: {'YES' if result['success'] else 'NO'}")
                print(f"  Patterns Stored: {result['patterns_stored']}")
                print(f"  Lines Processed: {result['lines_processed']}")
                print(f"  Duration: {result['duration']:.1f}s")

                if result.get("progress"):
                    print(f"  Progress: {result['progress']}")
                if result.get("error"):
                    print(f"  Error: {result['error']}")
            except Exception as err:
                print(f"[ERROR] Batch training failed: {err}")

            input("\nPress Enter to continue...")

        elif choice == "2":
            run_utf8_hygiene_scan(memory)

        elif choice == "3":
            print("\n[INFO] Gemma policy drill coming soon. Add labelled examples to extend this menu item.")
            input("\nPress Enter to continue...")

        elif choice == "4":
            print("\n[INFO] Qwen summary drill coming soon. Log candidate transcripts to enable this feature.")
            input("\nPress Enter to continue...")

        elif choice == "5":
            print("\n[INFO] Training Progress")
            print("=" * 60)
            try:
                mem = memory or PatternMemory()
                prog_stats = mem.get_stats()

                processed = prog_stats["checkpoint_line"]
                progress_pct = (processed / total_lines) * 100 if total_lines else 0

                print(f"\n[INFO] Progress:")
                if total_lines:
                    remaining = total_lines - processed
                    print(f"   Total Lines: {total_lines:,}")
                    print(f"   Processed: {processed:,} ({progress_pct:.1f}%)")
                    print(f"   Remaining: {remaining:,}")
                    print(f"   Estimated Chunks: {remaining // 1000} @ 1000 lines/chunk")
                else:
                    print(f"   Processed: {processed:,} (corpus not found, total unknown)")

                print(f"\n[INFO] Pattern Storage:")
                print(f"   Total Patterns: {prog_stats['total_patterns']}")
                verified = int(prog_stats['total_patterns'] * prog_stats['verification_rate'])
                print(f"   Verified: {verified}")
                print(f"   Verification Rate: {prog_stats['verification_rate']:.1%}")

                if prog_stats.get("sources"):
                    print(f"\n[INFO] Sources:")
                    for source, count in prog_stats["sources"].items():
                        print(f"   {source}: {count} patterns")

                bar_width = 40
                filled = int(bar_width * progress_pct / 100)
                bar = "#" * filled + "-" * (bar_width - filled)
                print(f"\n[{bar}] {progress_pct:.1f}%")
            except Exception as err:
                print(f"[ERROR] Could not load progress: {err}")

            input("\nPress Enter to continue...")

        elif choice == "6":
            print("\n[INFO] Test Pattern Recall")
            print("=" * 60)
            print("Enter a query to test Gemma pattern recall:")
            print("Examples:")
            print("  - 'Which module handles YouTube authentication?'")
            print("  - 'How does priority scoring work?'")
            print("  - 'Where should test files be placed?'")
            print("=" * 60)

            query = input("\nQuery: ").strip()
            if not query:
                print("[WARN] No query entered.")
                input("\nPress Enter to continue...")
                continue

            try:
                mem = memory or PatternMemory()
                patterns = mem.recall_similar(query, n=5, min_similarity=0.3)
                if patterns:
                    print(f"\n[INFO] Found {len(patterns)} similar patterns:\n")
                    for idx, pattern in enumerate(patterns, 1):
                        print(f"Pattern {idx}:")
                        print(f"  ID: {pattern['id']}")
                        print(f"  Similarity: {pattern['similarity']:.2f}")
                        print(f"  Context: {pattern['context'][:100]}...")
                        print(f"  Module: {pattern['metadata'].get('module', 'unknown')}")
                        print()
                else:
                    print("\n[INFO] No patterns found above similarity threshold (0.3).")
            except Exception as err:
                print(f"[ERROR] Pattern recall failed: {err}")

            input("\nPress Enter to continue...")

        elif choice == "7":
            print("\n[INFO] Qwen/Gemma Routing Test")
            print("=" * 60)
            print("WRE Pattern: 012 -> 0102 -> Qwen (Coordinator) -> Gemma (Executor)")
            print("=" * 60)

            try:
                from holo_index.qwen_advisor.gemma_rag_inference import GemmaRAGInference
                from modules.infrastructure.shared_utilities.local_model_selection import (
                    resolve_code_model_path,
                    resolve_triage_model_path,
                )

                gemma_path = resolve_triage_model_path()
                qwen_path = resolve_code_model_path()

                if not gemma_path.exists() or not qwen_path.exists():
                    print("\n[ERROR] Models not found:")
                    if not gemma_path.exists():
                        print(f"   Missing: {gemma_path}")
                    if not qwen_path.exists():
                        print(f"   Missing: {qwen_path}")
                    print("\n   Configure LOCAL_MODEL_* env vars and ensure GGUF files are available.")
                    input("\nPress Enter to continue...")
                    continue

                print("\n[INFO] Initializing Gemma/Qwen routing engine...")
                engine = GemmaRAGInference(
                    gemma_model_path=gemma_path,
                    qwen_model_path=qwen_path,
                    confidence_threshold=0.7,
                )

                while True:
                    print("\n" + "-" * 60)
                    print("TEST QUERIES:")
                    print("-" * 60)
                    print("1. Which module handles YouTube authentication? (simple)")
                    print("2. How does priority scoring work? (medium)")
                    print("3. Why did Move2Japan get score 1.00? (complex)")
                    print("4. Where should test files be placed? (simple)")
                    print("5. Custom query")
                    print("6. View performance stats")
                    print("7. Back to training menu")
                    print("-" * 60)

                    query_choice = input("\nSelect option (1-7): ").strip()

                    if query_choice == "1":
                        query = "Which module handles YouTube authentication?"
                    elif query_choice == "2":
                        query = "How does priority scoring work?"
                    elif query_choice == "3":
                        query = "Why did Move2Japan get score 1.00?"
                    elif query_choice == "4":
                        query = "Where should test files be placed?"
                    elif query_choice == "5":
                        query = input("\nEnter your query: ").strip()
                        if not query:
                            print("[ERROR] No query entered")
                            continue
                    elif query_choice == "6":
                        stats_snapshot = engine.get_stats()
                        print("\n[INFO] ROUTING PERFORMANCE:")
                        print(f"   Total Queries: {stats_snapshot['total_queries']}")
                        print(f"   Gemma Handled: {stats_snapshot['gemma_handled']} ({stats_snapshot['gemma_percentage']:.1f}%)")
                        print(f"   Qwen Escalated: {stats_snapshot['qwen_escalated']} ({stats_snapshot['qwen_percentage']:.1f}%)")
                        print("\n[INFO] TARGET: 70% Gemma / 30% Qwen")
                        print(f"   ACTUAL: {stats_snapshot['gemma_percentage']:.1f}% Gemma / {stats_snapshot['qwen_percentage']:.1f}% Qwen")
                        if 50 <= stats_snapshot['gemma_percentage'] <= 90:
                            print("\n[INFO] Performance within target range.")
                        else:
                            print("\n[WARN] Performance needs tuning.")
                        input("\nPress Enter to continue...")
                        continue
                    elif query_choice == "7":
                        print("[INFO] Returning to training menu...")
                        break
                    else:
                        print(f"[ERROR] Invalid choice '{query_choice}'")
                        continue

                    print(f"\n[QUERY] {query}")
                    print("[INFO] Processing...")

                    result = engine.infer(query)

                    print("\n[RESULT]")
                    print(f"   Model Used: {result.model_used}")
                    print(f"   Latency: {result.latency_ms} ms")
                    print(f"   Confidence: {result.confidence:.2f}")
                    print(f"   Patterns Used: {result.patterns_used}")
                    if result.escalated:
                        print(f"   [INFO] Escalated: {result.escalation_reason}")
                    print("\n[RESPONSE]")
                    print(f"   {result.response}")

                    input("\nPress Enter to continue...")
            except Exception as err:
                print(f"\n[ERROR] Routing test failed: {err}")
                import traceback

                traceback.print_exc()

            input("\nPress Enter to continue...")

        elif choice == "8":
            print("\n[INFO] Training Metrics")
            print("=" * 60)
            try:
                mem = memory or PatternMemory()
                metrics = mem.get_stats()
                print(f"\n[INFO] Performance Metrics:")
                print(f"   Total Patterns: {metrics['total_patterns']}")
                print(f"   Verification Rate: {metrics['verification_rate']:.1%}")
                print("   Storage Location: holo_index/memory/chroma/")
                print(f"\n[INFO] Training Coverage:")
                if total_lines:
                    prog_pct = (metrics['checkpoint_line'] / total_lines) * 100
                    print(f"   Lines Processed: {metrics['checkpoint_line']:,} / {total_lines:,}")
                    print(f"   Progress: {prog_pct:.1f}%")
                else:
                    print(f"   Lines Processed: {metrics['checkpoint_line']:,} / unknown (corpus not found)")
                print(f"\n[INFO] Pattern Distribution:")
                if metrics.get("sources"):
                    for source, count in metrics["sources"].items():
                        pct = (count / metrics['total_patterns'] * 100) if metrics['total_patterns'] else 0
                        print(f"   {source}: {count} ({pct:.1f}%)")
                print("\n[INFO] Storage Stats:")
                print("   Database: ChromaDB (vector embeddings)")
                print("   Checkpoint File: checkpoint.txt")
                print("   Training Method: In-context learning (RAG)")
                print("   Cost: $0 (no fine-tuning)")
            except Exception as err:
                print(f"[ERROR] Could not load metrics: {err}")

            input("\nPress Enter to continue...")

        elif choice == "9":
            print("\n[INFO] Clear Pattern Memory")
            print("=" * 60)
            print("[WARN] WARNING: This will delete ALL stored patterns!")
            print("   - Pattern memory will be reset to empty")
            print("   - Checkpoint will be reset to 0")
            print("   - Training will need to restart from beginning")
            print("=" * 60)
            confirm = input("\nType 'CONFIRM' to proceed: ").strip()
            if confirm == "CONFIRM":
                try:
                    mem = memory or PatternMemory()
                    mem.clear_all(confirm=True)
                    mem.save_checkpoint(0)
                    print("\n[INFO] Pattern memory cleared successfully.")
                    print("   All patterns deleted.")
                    print("   Checkpoint reset to 0.")
                except Exception as err:
                    print(f"[ERROR] Clear failed: {err}")
            else:
                print("\n[INFO] Clear aborted - memory preserved.")
            input("\nPress Enter to continue...")

        else:
            print(f"[ERROR] Invalid choice '{choice}'. Please enter 0-9.")
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    run_training_system()
