#!/usr/bin/env python3
"""
Comprehensive Training Corpus Collector - ALL System Data for Gemma/Qwen

Collects training data from ALL sources in the system:
1. 012.txt - 0102 operational decisions (28K lines)
2. ModLog files - Module change history across all modules
3. WSP violations - WSP_MODULE_VIOLATIONS.md + git history
4. Chat logs - LiveChat memory conversations
5. Daemon logs - All DAE operations
6. Git history - Commit messages, file renames, fixes

Purpose: Train Gemma to understand the ENTIRE system like 0102 does
Architecture: Gemma assists Qwen -> Together they become DAE for Rubik's Cube

WSP Compliance: WSP 90 (UTF-8), WSP 49 (Module Structure), WSP 22 (ModLog)
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import subprocess

from modules.infrastructure.wre_core.scripts.extract_brain_artifacts import (
    DEFAULT_BRAIN_DIR,
    build_training_examples,
)
from modules.infrastructure.shared_utilities.corpus_resolver import resolve_corpus_path

logger = logging.getLogger(__name__)


class ComprehensiveTrainingCorpus:
    """
    Collects ALL system data for Gemma/Qwen training.

    Data Sources (in priority order):
    1. 012.txt - 0102 operational decisions (PRIMARY)
    2. ModLog.md files - Module change history
    3. WSP_MODULE_VIOLATIONS.md - Violation patterns
    4. Chat logs - LiveChat conversation memory
    5. Git history - Commits, renames, fixes
    6. Daemon logs - DAE operational data

    Output: JSON corpus ready for ChromaDB or Colab
    """

    def __init__(
        self,
        root_dir: str = "O:/Foundups-Agent",
        brain_dir: Optional[str] = None,
    ):
        self.root = Path(root_dir)
        self.brain_dir = Path(brain_dir) if brain_dir else DEFAULT_BRAIN_DIR
        self.corpus = {
            "012_operations": [],
            "modlogs": [],
            "wsp_violations": [],
            "chat_logs": [],
            "git_history": [],
            "daemon_logs": [],
            "brain_artifact_dpo_pairs": [],
            "brain_artifact_sft": [],
        }
        self.stats = {
            "total_patterns": 0,
            "sources_processed": 0,
            "errors": []
        }

    def collect_all(self) -> Dict:
        """
        Collect training data from ALL sources.

        Returns comprehensive corpus ready for training.
        """
        logger.info("[CORPUS] Starting comprehensive data collection...")

        # Priority 1: 012.txt (0102 operational decisions)
        self._collect_012_txt()

        # Priority 2: ModLog files (module change history)
        self._collect_modlogs()

        # Priority 3: WSP violations (violation -> fix patterns)
        self._collect_wsp_violations()

        # Priority 4: Chat logs (conversation memory)
        self._collect_chat_logs()

        # Priority 5: Git history (commits, renames, fixes)
        self._collect_git_history()

        # Priority 6: Daemon logs (DAE operations)
        self._collect_daemon_logs()

        # Priority 7: Brain artifacts (cross-session reasoning traces)
        self._collect_brain_artifacts()

        self.stats["total_patterns"] = sum(len(v) for v in self.corpus.values())

        logger.info(f"[CORPUS] Collection complete: {self.stats['total_patterns']} patterns")
        logger.info(f"[CORPUS] Sources: 012={len(self.corpus['012_operations'])}, "
                   f"ModLogs={len(self.corpus['modlogs'])}, "
                   f"Violations={len(self.corpus['wsp_violations'])}, "
                   f"Chats={len(self.corpus['chat_logs'])}, "
                   f"Git={len(self.corpus['git_history'])}, "
                   f"Daemons={len(self.corpus['daemon_logs'])}, "
                   f"BrainDPO={len(self.corpus['brain_artifact_dpo_pairs'])}, "
                   f"BrainSFT={len(self.corpus['brain_artifact_sft'])}")

        return self.corpus

    def collect_brain_artifacts_only(self) -> Dict:
        """Collect only brain-artifact training rows for incremental export."""
        self.corpus["brain_artifact_dpo_pairs"] = []
        self.corpus["brain_artifact_sft"] = []
        self._collect_brain_artifacts()
        return {
            "brain_artifact_dpo_pairs": self.corpus["brain_artifact_dpo_pairs"],
            "brain_artifact_sft": self.corpus["brain_artifact_sft"],
        }

    def _collect_012_txt(self):
        """
        Collect 012.txt - 0102 operational decisions.

        This is the PRIMARY training data - real decisions from 0102.
        Contains: Qwen decisions, module executions, error patterns, priority scoring.
        """
        logger.info("[CORPUS] Collecting 012.txt operations data...")

        txt_file = resolve_corpus_path(self.root)
        if txt_file is None or not txt_file.exists():
            logger.warning("[CORPUS] 012.txt not found - skipping")
            return

        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Extract decision patterns (lines with Qwen markers)
            current_context = []
            for i, line in enumerate(lines):
                # Qwen decision markers
                if any(marker in line for marker in [
                    "[BOT][AI] [QWEN-SCORE]",
                    "[BOT][AI] [QWEN-DECISION]",
                    "[QWEN-INIT]",
                    "[QWEN-ROUTING]"
                ]):
                    # Extract context (10 lines before + 20 after)
                    context_start = max(0, i - 10)
                    context_end = min(len(lines), i + 20)
                    context = ''.join(lines[context_start:context_end])

                    # Parse decision details
                    decision_type = self._extract_decision_type(line)
                    module = self._extract_module_reference(context)

                    self.corpus["012_operations"].append({
                        "id": f"012_{i}",
                        "source": "012.txt",
                        "line": i,
                        "decision_type": decision_type,
                        "context": context.strip(),
                        "module": module,
                        "timestamp": self._extract_timestamp(line),
                        "type": "operational_decision"
                    })

            logger.info(f"[CORPUS] Collected {len(self.corpus['012_operations'])} patterns from 012.txt")
            self.stats["sources_processed"] += 1

        except Exception as e:
            logger.error(f"[CORPUS] Error collecting 012.txt: {e}")
            self.stats["errors"].append(f"012.txt: {e}")

    def _collect_modlogs(self):
        """
        Collect ALL ModLog.md files - Module change history.

        ModLogs contain WHY changes were made, what was learned.
        This teaches Gemma the evolution of the system.
        """
        logger.info("[CORPUS] Collecting ModLog files...")

        # Find all ModLog.md files
        modlog_files = list(self.root.rglob("ModLog.md"))
        modlog_files.extend(list(self.root.rglob("TESTModLog.md")))

        for modlog_file in modlog_files:
            try:
                with open(modlog_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract module path
                module_path = str(modlog_file.parent.relative_to(self.root))

                # Split into entries (## headers or date markers)
                entries = self._split_modlog_entries(content)

                for i, entry in enumerate(entries):
                    self.corpus["modlogs"].append({
                        "id": f"modlog_{module_path}_{i}",
                        "source": str(modlog_file.relative_to(self.root)),
                        "module": module_path,
                        "content": entry.strip(),
                        "type": "change_history"
                    })

            except Exception as e:
                logger.error(f"[CORPUS] Error reading {modlog_file}: {e}")
                self.stats["errors"].append(f"ModLog {modlog_file}: {e}")

        logger.info(f"[CORPUS] Collected {len(self.corpus['modlogs'])} ModLog entries from {len(modlog_files)} files")
        self.stats["sources_processed"] += 1

    def _collect_wsp_violations(self):
        """
        Collect WSP_MODULE_VIOLATIONS.md - Violation -> Fix patterns.

        This teaches Gemma what NOT to do and how to fix violations.
        """
        logger.info("[CORPUS] Collecting WSP violations...")

        violations_file = self.root / "WSP_knowledge" / "src" / "WSP_MODULE_VIOLATIONS.md"

        if not violations_file.exists():
            logger.warning("[CORPUS] WSP_MODULE_VIOLATIONS.md not found - skipping")
            return

        try:
            with open(violations_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse violation entries (typically grouped by module or type)
            violations = self._parse_violation_entries(content)

            for i, violation in enumerate(violations):
                self.corpus["wsp_violations"].append({
                    "id": f"violation_{i}",
                    "source": "WSP_MODULE_VIOLATIONS.md",
                    "violation": violation["description"],
                    "fix": violation.get("fix", ""),
                    "wsp": violation.get("wsp", ""),
                    "type": "violation_pattern"
                })

            logger.info(f"[CORPUS] Collected {len(self.corpus['wsp_violations'])} violation patterns")
            self.stats["sources_processed"] += 1

        except Exception as e:
            logger.error(f"[CORPUS] Error collecting violations: {e}")
            self.stats["errors"].append(f"WSP_VIOLATIONS: {e}")

    def _collect_chat_logs(self):
        """
        Collect LiveChat conversation memory.

        Located in: modules/communication/livechat/memory/conversation/
        Contains real user interactions and moderation decisions.
        """
        logger.info("[CORPUS] Collecting chat logs...")

        chat_memory_dir = self.root / "modules" / "communication" / "livechat" / "memory" / "conversation"

        if not chat_memory_dir.exists():
            logger.warning("[CORPUS] Chat memory directory not found - skipping")
            return

        # Find all session directories
        session_dirs = [d for d in chat_memory_dir.iterdir() if d.is_dir()]

        for session_dir in session_dirs:
            # Read conversation files
            for log_file in session_dir.glob("*.json"):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    self.corpus["chat_logs"].append({
                        "id": f"chat_{session_dir.name}_{log_file.stem}",
                        "source": str(log_file.relative_to(self.root)),
                        "session": session_dir.name,
                        "data": data,
                        "type": "chat_interaction"
                    })

                except Exception as e:
                    logger.error(f"[CORPUS] Error reading {log_file}: {e}")

        logger.info(f"[CORPUS] Collected {len(self.corpus['chat_logs'])} chat log entries")
        self.stats["sources_processed"] += 1

    def _collect_git_history(self):
        """
        Collect git history - Commits, renames, fixes.

        Git log contains WHY decisions were made, what was fixed.
        File renames show WSP 57 violations that were corrected.
        """
        logger.info("[CORPUS] Collecting git history...")

        try:
            # Get recent commits (last 500)
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%H|%an|%ae|%at|%s', '-n', '500'],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30
            )

            if result.returncode != 0:
                logger.warning("[CORPUS] Git log failed - skipping git history")
                return

            commits = (result.stdout or "").strip().split('\n')

            for commit in commits:
                if not commit:
                    continue

                parts = commit.split('|')
                if len(parts) >= 5:
                    self.corpus["git_history"].append({
                        "id": f"commit_{parts[0][:8]}",
                        "source": "git_log",
                        "commit_hash": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "timestamp": parts[3],
                        "message": parts[4],
                        "type": "git_commit"
                    })

            # Get file renames (WSP 57 violations that were fixed)
            rename_result = subprocess.run(
                ['git', 'log', '--pretty=', '--name-status', '--diff-filter=R', '-n', '200'],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30
            )

            if rename_result.returncode == 0:
                renames = (rename_result.stdout or "").strip().split('\n')
                for rename in renames:
                    if rename.startswith('R'):
                        parts = rename.split('\t')
                        if len(parts) >= 3:
                            self.corpus["git_history"].append({
                                "id": f"rename_{len(self.corpus['git_history'])}",
                                "source": "git_renames",
                                "old_name": parts[1],
                                "new_name": parts[2],
                                "type": "file_rename"
                            })

            logger.info(f"[CORPUS] Collected {len(self.corpus['git_history'])} git history entries")
            self.stats["sources_processed"] += 1

        except Exception as e:
            logger.error(f"[CORPUS] Error collecting git history: {e}")
            self.stats["errors"].append(f"Git history: {e}")

    def _collect_daemon_logs(self):
        """
        Collect daemon logs - DAE operational data.

        Searches for log files across all modules.
        Contains runtime decisions, errors, patterns.
        """
        logger.info("[CORPUS] Collecting daemon logs...")

        # Find all .log files (exclude DumpStack.log in root)
        log_files = []
        for pattern in ["**/*.log", "**/*_log.txt"]:
            log_files.extend(self.root.glob(pattern))

        # Filter out root violations
        log_files = [f for f in log_files if "DumpStack" not in f.name and f.parent != self.root]

        for log_file in log_files[:50]:  # Limit to 50 most recent
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read last 100 lines (most recent)
                    lines = f.readlines()[-100:]
                    content = ''.join(lines)

                self.corpus["daemon_logs"].append({
                    "id": f"daemon_{log_file.stem}",
                    "source": str(log_file.relative_to(self.root)),
                    "content": content.strip(),
                    "type": "daemon_operation"
                })

            except Exception as e:
                logger.error(f"[CORPUS] Error reading {log_file}: {e}")

        logger.info(f"[CORPUS] Collected {len(self.corpus['daemon_logs'])} daemon log entries")
        self.stats["sources_processed"] += 1

    def _collect_brain_artifacts(self):
        """
        Collect cross-session reasoning traces from the Antigravity brain.

        Outputs:
        - DPO pairs from implementation plan revision chains
        - SFT rows from final walkthroughs
        """
        logger.info("[CORPUS] Collecting brain artifact training data...")

        try:
            training_data = build_training_examples(self.brain_dir)
            self.corpus["brain_artifact_dpo_pairs"].extend(training_data.get("dpo_pairs", []))
            self.corpus["brain_artifact_sft"].extend(training_data.get("sft_examples", []))
            logger.info(
                "[CORPUS] Collected %s DPO pairs and %s SFT walkthroughs from brain artifacts",
                len(self.corpus["brain_artifact_dpo_pairs"]),
                len(self.corpus["brain_artifact_sft"]),
            )
            self.stats["sources_processed"] += 1
        except Exception as e:
            logger.error(f"[CORPUS] Error collecting brain artifacts: {e}")
            self.stats["errors"].append(f"Brain artifacts: {e}")

    # Helper methods

    def _extract_decision_type(self, line: str) -> str:
        """Extract decision type from Qwen marker line."""
        if "QWEN-SCORE" in line:
            return "priority_scoring"
        elif "QWEN-DECISION" in line:
            return "execution_decision"
        elif "QWEN-ROUTING" in line:
            return "routing_decision"
        elif "QWEN-INIT" in line:
            return "initialization"
        return "unknown"

    def _extract_module_reference(self, context: str) -> Optional[str]:
        """Extract module reference from context."""
        # Look for module paths
        import re
        patterns = [
            r'modules/([^/]+/[^/\s\)]+)',
            r'holo_index/([^/\s\)]+)',
            r'WSP_\d+',
        ]
        for pattern in patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(0)
        return None

    def _extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from log line."""
        import re
        # Look for common timestamp formats
        patterns = [
            r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',
            r'\[\d{2}:\d{2}:\d{2}\]'
        ]
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(0)
        return None

    def _split_modlog_entries(self, content: str) -> List[str]:
        """Split ModLog content into individual entries."""
        import re
        # Split on ## headers or date patterns
        entries = re.split(r'\n##\s+', content)
        return [e for e in entries if e.strip()]

    def _parse_violation_entries(self, content: str) -> List[Dict]:
        """Parse violation entries from WSP_MODULE_VIOLATIONS.md."""
        violations = []
        # Simple parsing - split on headers or bullet points
        lines = content.split('\n')
        current_violation = None

        for line in lines:
            line = line.strip()
            if line.startswith('###') or line.startswith('##'):
                # New violation category
                current_violation = {"description": line.replace('#', '').strip()}
                violations.append(current_violation)
            elif line.startswith('-') or line.startswith('*'):
                # Violation detail
                if current_violation:
                    if 'details' not in current_violation:
                        current_violation['details'] = []
                    current_violation['details'].append(line[1:].strip())

        return violations

    def export_to_json(self, output_file: str):
        """
        Export corpus to JSON file.

        This JSON can be uploaded to Colab for training.
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        export_data = {
            "corpus": self.corpus,
            "stats": self.stats,
            "metadata": {
                "collected_at": datetime.now().isoformat(),
                "root_dir": str(self.root),
                "version": "1.0"
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"[CORPUS] Exported to {output_path}")
        logger.info(f"[CORPUS] File size: {output_path.stat().st_size / 1024:.1f} KB")

        return output_path

    def export_brain_training_jsonl(self, output_dir: str) -> Dict[str, Path]:
        """
        Export brain-artifact training rows in JSONL formats compatible with
        the existing DPO/SFT pipeline shapes.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        dpo_path = output_path / "brain_artifact_dpo_pairs.jsonl"
        sft_path = output_path / "brain_artifact_sft.jsonl"

        with open(dpo_path, "w", encoding="utf-8") as dpo_file:
            for row in self.corpus["brain_artifact_dpo_pairs"]:
                json.dump(row, dpo_file, ensure_ascii=False)
                dpo_file.write("\n")

        with open(sft_path, "w", encoding="utf-8") as sft_file:
            for row in self.corpus["brain_artifact_sft"]:
                json.dump(row, sft_file, ensure_ascii=False)
                sft_file.write("\n")

        logger.info("[CORPUS] Exported brain artifact DPO rows to %s", dpo_path)
        logger.info("[CORPUS] Exported brain artifact SFT rows to %s", sft_path)
        return {
            "dpo_pairs": dpo_path,
            "sft_examples": sft_path,
        }

    def get_summary(self) -> Dict:
        """Get summary statistics of collected corpus."""
        return {
            "total_patterns": self.stats["total_patterns"],
            "sources_processed": self.stats["sources_processed"],
            "breakdown": {
                "012_operations": len(self.corpus["012_operations"]),
                "modlogs": len(self.corpus["modlogs"]),
                "wsp_violations": len(self.corpus["wsp_violations"]),
                "chat_logs": len(self.corpus["chat_logs"]),
                "git_history": len(self.corpus["git_history"]),
                "daemon_logs": len(self.corpus["daemon_logs"]),
                "brain_artifact_dpo_pairs": len(self.corpus["brain_artifact_dpo_pairs"]),
                "brain_artifact_sft": len(self.corpus["brain_artifact_sft"]),
            },
            "errors": len(self.stats["errors"])
        }


if __name__ == "__main__":
    # Test collection
    logging.basicConfig(level=logging.INFO)

    collector = ComprehensiveTrainingCorpus()
    corpus = collector.collect_all()

    # Export to JSON
    output_file = "O:/Foundups-Agent/holo_index/training/corpus_export.json"
    collector.export_to_json(output_file)

    # Print summary
    summary = collector.get_summary()
    print("\n[CORPUS SUMMARY]")
    print(f"Total patterns: {summary['total_patterns']}")
    print(f"Sources processed: {summary['sources_processed']}")
    print("\nBreakdown:")
    for source, count in summary['breakdown'].items():
        print(f"  {source}: {count}")

    if summary['errors'] > 0:
        print(f"\nErrors: {summary['errors']}")
