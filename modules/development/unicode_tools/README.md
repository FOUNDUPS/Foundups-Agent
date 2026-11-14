# Legacy Unicode rewrite utilities

This folder preserves three legacy rewrite utilities. Their Qwen/Gemma names
and printed success statements do not establish model inference or validated
cross-platform safety: the inspected implementations use deterministic
replacement and character-range heuristics.

`src/auto_cleaner.py` wraps output streams on Windows at import. Its main entry
reads the current directory's `012.txt`, writes a backup and applies lossy
replacements, including removal of some characters. It is not the maintained
bounded source audit or a safe way to inspect an operator conversation.

`src/emoji_fixer.py` reads and rewrites the MCP manager source at module import,
without a main guard. Importing it is an editing action. `src/unicode_campaign.py`
walks the current directory, selects files using its replacement patterns,
creates `.unicode_backup` files and rewrites selected source. Its directory
exclusions do not establish tracked-only or concurrent-worktree isolation.
The final analysis prints heuristic summaries and repeats the file selection;
its categorical preservation/compliance claims are not independent acceptance.

For maintained UTF-8 hygiene, inspect the existing
`modules/ai_intelligence/utf8_hygiene` owner and its tests before choosing a
scoped operation. This folder has no tracked dedicated test suite or dependency
manifest at this revision. No legacy utility was imported or executed, and no
conversation or application source was rewritten for this documentation review.
