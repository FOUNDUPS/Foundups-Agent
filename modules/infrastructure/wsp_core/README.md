# WSP core infrastructure

The maintained audit entrypoint is `WSPComplianceChecker` in
`src/wsp_compliance_checker.py`. It returns structural hints from Git-tracked
working-tree files. FMAS remains the owner of exact-base WSP 62 enforcement and
exemption decisions; a clean hint list is not a security or coverage certificate.

```python
import asyncio
from pathlib import Path
from modules.infrastructure.wsp_core.src.wsp_compliance_checker import WSPComplianceChecker

findings = asyncio.run(WSPComplianceChecker(Path.cwd()).scan())
```

Run from the repository root or pass that root explicitly. The scanner verifies
the Git top-level path, reads the tracked index once per scan, and never falls back
to a directory walk. Git failures, merge conflicts, missing source, redirected
paths, unsupported tracked links/submodules and exhausted limits produce explicit
`SCAN_INCOMPLETE` rows. Environment-named paths are excluded without opening them.

The checker imports no inspected source, creates no pattern database and writes
no files or Git state. Git stdout is capped at 4 MiB/100,000 records and each Git
operation has a 30-second timeout. Python content is capped at 2 MiB per file and
128 MiB total; metadata checks reject symlinks, reparse points and special files.
These are working-tree checks, not an immutable snapshot or a race-proof boundary
against concurrent filesystem replacement. Scans should use an owned checkout.

Findings cover module-name duplication, current Python size review thresholds,
direct component counts, domain placement, tracked ModLog/test documentation and
dependency manifests, and tracked root Python files. Domain-level `src`/`tests`
are placement findings, not phantom module names. `monitoring` and WSP 3 section
5.1's `modules/wre_core` exception are recognized. No finding is marked
auto-fixable: substantive documentation and dependency choices require review.

Callers may pass a frozen in-memory false-positive selection; see
[INTERFACE.md](INTERFACE.md). No stored learning history is deleted. Explicit
suppression affects module-name/documentation hints or root-file hints, not
source inspection failures, file sizes or domain architecture.

`semantic_state_engine.py` separately implements WSP 44 triplet validation and
optional transition logging. `neural_operating_system.py` is a legacy WSP 00
adapter with optional integrations; it is not imported by this scanner. Its
mathematical labels do not establish physical quantum behavior. Earlier docs
advertised `WSPValidator` and `WSPEnforcer`, which this package does not implement.

See [tests/README.md](tests/README.md) for bounded regression evidence and
[ModLog.md](ModLog.md) for changes. Remaining work includes canonical domain
constant sharing with FMAS and separate ownership of structural migrations.
