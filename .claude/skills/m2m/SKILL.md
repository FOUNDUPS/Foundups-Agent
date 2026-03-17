---
name: m2m
description: M2M compression scan, compile, promote, batch, and benchmark for 0102 documentation optimization
version: 1.0.0
author: 0102
agents: [0102]
domain: documentation_optimization
intent_type: COMPRESSION
promotion_state: production
user_invocable: true
category: workflow
evals: []
---
# /m2m - M2M Compression Skill

Self-service M2M (machine-to-machine) documentation compression for 0102.

## Commands

Parse the argument after `/m2m` to determine the subcommand:

### `/m2m` or `/m2m scan`
Run M2M compression scan on the full repo. Show candidates with action levels.

```python
from pathlib import Path
from modules.ai_intelligence.ai_overseer.src.m2m_compression_sentinel import M2MCompressionSentinel

sentinel = M2MCompressionSentinel(Path('.'))
result = sentinel.check(force=True)

# Report summary
print(f"Files scanned: {result['files_scanned']}")
print(f"Candidates: {result['candidates_found']}")
print(f"Auto-apply: {result['auto_apply_count']}")
print(f"Stage-promote: {result['stage_promote_count']}")
print(f"Stage-review: {result['stage_review_count']}")
print(f"Savings: {result['total_estimated_savings_percent']:.1f}%")

# Show staged status
staged = sentinel.list_staged()
print(f"Currently staged: {staged['total_staged']}")
```

### `/m2m compile <path>`
Compile a specific file to M2M format and save to `.m2m/staged/`.

```python
sentinel = M2MCompressionSentinel(Path('.'))
result = sentinel.compile_to_staged("<path>", use_qwen=False)
# Report: success, reduction_percent, m2m_lines, staged_path
```

If no path given, compile all unstaged auto_apply candidates.

### `/m2m promote <staged_path>`
Promote a staged M2M file to live documentation. Creates backup automatically.

```python
sentinel = M2MCompressionSentinel(Path('.'))
result = sentinel.promote_staged("<staged_path>")
# Report: success, target_path, backup_path
```

### `/m2m rollback <target_path>`
Rollback a promoted file to its original from backup.

```python
sentinel = M2MCompressionSentinel(Path('.'))
result = sentinel.rollback("<target_path>")
# Report: success, backup_used
```

### `/m2m batch <n>`
Stage the next N unstaged auto_apply files (smallest first). Default: 10.

```python
sentinel = M2MCompressionSentinel(Path('.'))

# Get all auto_apply candidates
candidates_paths = sentinel._collect_candidate_files()
analyses = []
for fp in candidates_paths:
    a = sentinel._analyze_file(fp)
    if a and a.prose_density > 0.3 and a.action == 'auto_apply':
        analyses.append(a)

# Sort smallest first, filter already staged
analyses.sort(key=lambda a: a.line_count)
staged = sentinel.list_staged()
staged_names = {f['original_name'].strip() for f in staged['files']}
unstaged = [a for a in analyses if a.filename not in staged_names]

# Compile batch
batch = unstaged[:N]
for a in batch:
    result = sentinel.compile_to_staged(a.path, use_qwen=False)
    # Report each: path, reduction, lines
```

### `/m2m benchmark`
Run performance benchmarks on the M2M compression pipeline.

Execute the benchmark test suite:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest modules/ai_intelligence/ai_overseer/tests/test_m2m_compression_sentinel.py::TestBenchmarks -v -s
```

### `/m2m eval`
Evaluate M2M quality by comparing staged files against originals using HoloIndex embedding model.

```python
sentinel = M2MCompressionSentinel(Path('.'))
result = sentinel.evaluate_staged()
# Report: pairs_evaluated, avg_cosine_similarity, verdict, per-file details
# Verdict: excellent (0.6+), acceptable (0.4-0.6), needs_improvement (<0.4)
```

### `/m2m status`
Show current staged files and their status.

```python
sentinel = M2MCompressionSentinel(Path('.'))
staged = sentinel.list_staged()
# Show: total, by_module breakdown, file details
```

## Execution

When invoked, run the appropriate Python code inline using the Bash tool. Report results in a compact table format. All operations are local and reversible.
