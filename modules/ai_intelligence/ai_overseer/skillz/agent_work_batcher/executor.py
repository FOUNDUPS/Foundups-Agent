#!/usr/bin/env python3
"""
Agent Work Batcher - Batch 0102 work for LinkedIn FoundUps posting

Collects work items from ModLogs, git commits, and skill updates.
Batches related work and posts to LinkedIn company page.

Usage:
    python executor.py --scan           # Show pending work items
    python executor.py --generate       # Generate post (dry run)
    python executor.py --post           # Post to LinkedIn
    python executor.py --daily          # Daily summary
"""

import argparse
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Fix Windows console Unicode encoding
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Agent gating - who can execute this skill
ALLOWED_AGENTS = ["qwen", "claude", "openclaw"]


@dataclass
class WorkItem:
    """A single work item from agent activity."""
    source: str  # modlog, git, skillz, roadmap
    category: str  # skills, docs, testing, etc.
    description: str
    timestamp: datetime
    files_affected: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'WorkItem':
        d['timestamp'] = datetime.fromisoformat(d['timestamp'])
        return cls(**d)


@dataclass
class WorkBatch:
    """A batch of work items ready for posting."""
    items: List[WorkItem]
    created_at: datetime
    categories: List[str]
    posted: bool = False
    linkedin_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'items': [i.to_dict() for i in self.items],
            'created_at': self.created_at.isoformat(),
            'categories': self.categories,
            'posted': self.posted,
            'linkedin_url': self.linkedin_url,
        }


class AgentWorkBatcher:
    """
    Batch agent work for LinkedIn posting.

    Gated by ALLOWED_AGENTS - only specified agents can execute.
    Wardrobe (discovery) is open to all via HoloIndex.
    """

    # Emoji with ASCII fallbacks for Windows cp932
    CATEGORY_EMOJI = {
        'skills': '[SKILL]',
        'docs': '[DOC]',
        'testing': '[TEST]',
        'refactor': '[REFAC]',
        'feature': '[FEAT]',
        'bugfix': '[FIX]',
        'perf': '[PERF]',
        'security': '[SEC]',
        'infra': '[INFRA]',
        'other': '[OTHER]',
    }

    # Rich emoji for LinkedIn posts (not console)
    CATEGORY_EMOJI_RICH = {
        'skills': '🛠️',
        'docs': '📝',
        'testing': '🧪',
        'refactor': '♻️',
        'feature': '✨',
        'bugfix': '🐛',
        'perf': '⚡',
        'security': '🔒',
        'infra': '🏗️',
        'other': '📦',
    }

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or REPO_ROOT
        self.state_dir = Path(__file__).parent / "state"
        self.state_dir.mkdir(exist_ok=True)
        self.pending_file = self.state_dir / "pending_items.jsonl"
        self.posted_file = self.state_dir / "posted_batches.jsonl"
        self.last_scan_file = self.state_dir / "last_scan.json"

    def check_agent_gate(self, agent: str) -> bool:
        """Check if agent is allowed to execute this skill."""
        if agent.lower() not in [a.lower() for a in ALLOWED_AGENTS]:
            logger.warning(f"[GATE] Agent '{agent}' not allowed. Allowed: {ALLOWED_AGENTS}")
            return False
        return True

    def get_last_scan_time(self) -> datetime:
        """Get timestamp of last scan."""
        if self.last_scan_file.exists():
            data = json.loads(self.last_scan_file.read_text())
            return datetime.fromisoformat(data['timestamp'])
        return datetime.now() - timedelta(days=1)

    def update_last_scan_time(self):
        """Update last scan timestamp."""
        self.last_scan_file.write_text(json.dumps({
            'timestamp': datetime.now().isoformat()
        }))

    def scan_modlogs(self, since: datetime = None) -> List[WorkItem]:
        """Scan ModLog.md files for recent entries."""
        items = []
        since = since or self.get_last_scan_time()

        # Find all ModLog.md files
        modlogs = list(self.repo_root.glob("**/ModLog.md"))
        logger.info(f"[SCAN] Found {len(modlogs)} ModLog files")

        date_pattern = re.compile(r'###\s*(\d{4}-\d{2}-\d{2})')
        entry_pattern = re.compile(r'^[-*]\s+(.+)$', re.MULTILINE)

        for modlog in modlogs:
            try:
                content = modlog.read_text(encoding='utf-8')

                # Find date headers and entries
                for match in date_pattern.finditer(content):
                    date_str = match.group(1)
                    entry_date = datetime.strptime(date_str, '%Y-%m-%d')

                    if entry_date.date() >= since.date():
                        # Get section after this date header
                        start = match.end()
                        next_header = date_pattern.search(content, start)
                        end = next_header.start() if next_header else len(content)
                        section = content[start:end]

                        # Extract bullet points
                        for entry in entry_pattern.finditer(section):
                            desc = entry.group(1).strip()
                            if desc and len(desc) > 10:
                                category = self._categorize(desc)
                                items.append(WorkItem(
                                    source='modlog',
                                    category=category,
                                    description=desc,
                                    timestamp=entry_date,
                                    files_affected=[str(modlog.relative_to(self.repo_root))],
                                ))
            except Exception as e:
                logger.warning(f"[SCAN] Error reading {modlog}: {e}")

        return items

    def scan_git_commits(self, since: datetime = None) -> List[WorkItem]:
        """Scan git commits for recent changes."""
        items = []
        since = since or self.get_last_scan_time()
        since_str = since.strftime('%Y-%m-%d')

        try:
            result = subprocess.run(
                ['git', 'log', f'--since={since_str}', '--oneline', '--no-merges'],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        # Parse: "abc1234 feat(scope): message"
                        parts = line.split(' ', 1)
                        if len(parts) == 2:
                            commit_hash, message = parts
                            category = self._categorize_commit(message)
                            items.append(WorkItem(
                                source='git',
                                category=category,
                                description=message,
                                timestamp=datetime.now(),  # Simplified
                                metadata={'commit': commit_hash},
                            ))
        except Exception as e:
            logger.warning(f"[SCAN] Git scan failed: {e}")

        return items

    def scan_skillz_updates(self, since: datetime = None) -> List[WorkItem]:
        """Scan for new/updated SKILLz.md files."""
        items = []
        since = since or self.get_last_scan_time()

        skillz_files = list(self.repo_root.glob("**/SKILLz.md"))
        logger.info(f"[SCAN] Found {len(skillz_files)} SKILLz.md files")

        for skillz in skillz_files:
            try:
                # Check modification time
                mtime = datetime.fromtimestamp(skillz.stat().st_mtime)
                if mtime >= since:
                    # Read skill name from frontmatter
                    content = skillz.read_text(encoding='utf-8')
                    name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
                    name = name_match.group(1) if name_match else skillz.parent.name

                    items.append(WorkItem(
                        source='skillz',
                        category='skills',
                        description=f"Skill updated: {name}",
                        timestamp=mtime,
                        files_affected=[str(skillz.relative_to(self.repo_root))],
                    ))
            except Exception as e:
                logger.warning(f"[SCAN] Error scanning {skillz}: {e}")

        return items

    def _categorize(self, text: str) -> str:
        """Categorize work item by text content."""
        text_lower = text.lower()

        if any(k in text_lower for k in ['skill', 'skillz', 'wardrobe']):
            return 'skills'
        if any(k in text_lower for k in ['test', 'coverage', 'passing']):
            return 'testing'
        if any(k in text_lower for k in ['readme', 'interface', 'modlog', 'doc']):
            return 'docs'
        if any(k in text_lower for k in ['refactor', 'cleanup', 'wsp']):
            return 'refactor'
        if any(k in text_lower for k in ['feat', 'add', 'new', 'implement']):
            return 'feature'
        if any(k in text_lower for k in ['fix', 'bug', 'error']):
            return 'bugfix'
        if any(k in text_lower for k in ['perf', 'optim', 'fast']):
            return 'perf'
        if any(k in text_lower for k in ['secur', 'auth', 'cred']):
            return 'security'
        if any(k in text_lower for k in ['infra', 'deploy', 'ci']):
            return 'infra'

        return 'other'

    def _categorize_commit(self, message: str) -> str:
        """Categorize git commit by conventional commit prefix."""
        prefixes = {
            'feat': 'feature',
            'fix': 'bugfix',
            'docs': 'docs',
            'test': 'testing',
            'refactor': 'refactor',
            'perf': 'perf',
            'chore': 'infra',
            'ci': 'infra',
        }

        for prefix, category in prefixes.items():
            if message.lower().startswith(prefix):
                return category

        return self._categorize(message)

    def scan_all(self, since: datetime = None) -> List[WorkItem]:
        """Scan all sources for work items."""
        since = since or self.get_last_scan_time()
        logger.info(f"[SCAN] Scanning work since {since.isoformat()}")

        items = []
        items.extend(self.scan_modlogs(since))
        items.extend(self.scan_git_commits(since))
        items.extend(self.scan_skillz_updates(since))

        # Deduplicate by description
        seen = set()
        unique_items = []
        for item in items:
            key = item.description[:50]
            if key not in seen:
                seen.add(key)
                unique_items.append(item)

        logger.info(f"[SCAN] Found {len(unique_items)} unique work items")
        return unique_items

    def generate_post(self, items: List[WorkItem], summary: str = None) -> str:
        """Generate LinkedIn post content from work items."""
        if not items:
            return ""

        # Group by category
        by_category: Dict[str, List[WorkItem]] = {}
        for item in items:
            if item.category not in by_category:
                by_category[item.category] = []
            by_category[item.category].append(item)

        # Build post
        lines = ["0102 Agent Update", ""]  # Signature adds lobster emoji

        if summary:
            lines.append(f"**{summary}**")
            lines.append("")

        for category, cat_items in by_category.items():
            emoji = self.CATEGORY_EMOJI_RICH.get(category, '📦')
            cat_name = category.replace('_', ' ').title()
            lines.append(f"{emoji} **{cat_name}**")

            for item in cat_items[:5]:  # Limit per category
                desc = item.description
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                lines.append(f"• {desc}")

            if len(cat_items) > 5:
                lines.append(f"  _(+{len(cat_items) - 5} more)_")

            lines.append("")

        # Stats
        total_files = set()
        for item in items:
            total_files.update(item.files_affected)

        if total_files:
            lines.append("📊 **Stats**")
            lines.append(f"• Work items: {len(items)}")
            lines.append(f"• Files touched: {len(total_files)}")
            lines.append(f"• Categories: {len(by_category)}")
            lines.append("")

        # Signature
        lines.append("---")
        lines.append("0102🦞 #FoundUps #pAVS #0102 #AgentUpdate")

        return '\n'.join(lines)

    def post_to_linkedin(self, content: str) -> tuple[bool, str]:
        """Post content to LinkedIn using linkedin_company_poster."""
        try:
            from modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster.executor import (
                post_update
            )

            # Remove signature (poster adds its own)
            content_clean = content.replace("0102🦞 #FoundUps #pAVS #0102 #AgentUpdate", "").strip()

            success, message = post_update(content_clean)
            return success, message

        except ImportError as e:
            logger.error(f"[POST] linkedin_company_poster not available: {e}")
            return False, f"Import error: {e}"
        except Exception as e:
            logger.error(f"[POST] Failed: {e}")
            return False, str(e)

    def save_pending(self, items: List[WorkItem]):
        """Save pending items to state file."""
        with open(self.pending_file, 'a', encoding='utf-8') as f:
            for item in items:
                f.write(json.dumps(item.to_dict()) + '\n')

    def load_pending(self) -> List[WorkItem]:
        """Load pending items from state file."""
        items = []
        if self.pending_file.exists():
            for line in self.pending_file.read_text().strip().split('\n'):
                if line:
                    items.append(WorkItem.from_dict(json.loads(line)))
        return items

    def clear_pending(self):
        """Clear pending items after posting."""
        if self.pending_file.exists():
            self.pending_file.unlink()

    def save_batch(self, batch: WorkBatch):
        """Save posted batch to history."""
        with open(self.posted_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(batch.to_dict()) + '\n')


def main():
    parser = argparse.ArgumentParser(
        description="Agent Work Batcher - Batch 0102 work for LinkedIn",
        epilog="""
Examples:
  python executor.py --scan                    # Show pending work
  python executor.py --generate                # Generate post (dry run)
  python executor.py --post                    # Post to LinkedIn
  python executor.py --post --summary "Skills 2.0 update"
"""
    )
    parser.add_argument("--scan", action="store_true", help="Scan for new work items")
    parser.add_argument("--generate", action="store_true", help="Generate post (dry run)")
    parser.add_argument("--post", action="store_true", help="Post to LinkedIn")
    parser.add_argument("--summary", type=str, help="Custom summary for post")
    parser.add_argument("--daily", action="store_true", help="Daily summary (last 24h)")
    parser.add_argument("--clear", action="store_true", help="Clear pending items")
    parser.add_argument("--agent", type=str, default="claude", help="Executing agent (for gate check)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    batcher = AgentWorkBatcher()

    # Agent gate check
    if not batcher.check_agent_gate(args.agent):
        logger.error(f"[GATE] Execution denied for agent: {args.agent}")
        sys.exit(1)

    if args.clear:
        batcher.clear_pending()
        print("[OK] Pending items cleared")
        sys.exit(0)

    # Determine time range
    since = None
    if args.daily:
        since = datetime.now() - timedelta(days=1)

    if args.scan or args.generate or args.post:
        # Scan for items
        items = batcher.scan_all(since)

        if args.json:
            print(json.dumps([i.to_dict() for i in items], indent=2))
            sys.exit(0)

        if args.scan:
            print(f"\n[SCAN] Found {len(items)} work items:\n")
            for item in items:
                emoji = batcher.CATEGORY_EMOJI.get(item.category, '📦')
                print(f"  {emoji} [{item.source}] {item.description[:60]}")

            # Show category breakdown
            categories = {}
            for item in items:
                categories[item.category] = categories.get(item.category, 0) + 1

            print(f"\n[CATEGORIES]")
            for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
                emoji = batcher.CATEGORY_EMOJI.get(cat, '📦')
                print(f"  {emoji} {cat}: {count}")

        if args.generate or args.post:
            content = batcher.generate_post(items, args.summary)

            if args.generate:
                print("\n[PREVIEW] LinkedIn Post:\n")
                print("=" * 50)
                print(content)
                print("=" * 50)
                print(f"\nCharacters: {len(content)}")

            if args.post:
                if not items:
                    print("[SKIP] No work items to post")
                    sys.exit(0)

                print("\n[POST] Posting to LinkedIn...")
                success, message = batcher.post_to_linkedin(content)

                if success:
                    print(f"[OK] {message}")
                    batcher.update_last_scan_time()
                    batcher.clear_pending()
                else:
                    print(f"[FAIL] {message}")
                    sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
