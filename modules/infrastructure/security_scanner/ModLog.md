## 2026-10-10 — Security audit: fail closed on missing scan coverage

- Repaired scanner exit/schema validation, including authentication/configuration
  errors, empty finding exits, malformed records, and Semgrep partial coverage.
- Enabled Trivy vulnerability/secret/misconfiguration scans; normalized finding
  categories and locations without persisting secret matches or source snippets.
- Preserved categories/locations through WRE policy routing, including secret
  gates when policy loading fails. CLI exits distinguish complete/gated/incomplete
  coverage (0/1/2). Aggregate and SEC9 status preserve partial/error outcomes.
- Expanded SEC4 proposals to website/application/test source and pnpm, uv, Poetry,
  Pipenv, and Bun lockfiles. Dry-run calls remain non-executing.
- Validation: 131 focused scanner/WRE/trigger/controller/E2E tests passed, no skips;
  29 policy tests passed separately. Existing pytest asyncio-option and UTC
  deprecation warnings remain. No real scanner services, schedulers, or models ran.
- WSP 5/11/22/50/77/97. Source-bound lexical Holo retrieval used current audit
  baseline; semantic freshness remains UNKNOWN/index gap explicit.

# Security Scanner ModLog

## V0.1.0 - SEC1 CLI Proof (2026-04-17)

**Phase**: SEC1 — SECURITY_SCANNER_CLI_PROOF_PHASE1

**Objective**: Prove autonomous CLI-based security scanning without MCP/LLM dependencies.

### Created

- `src/security_scanner.py` - Main scanner class
  - `SecurityScanner` with subprocess-based scan execution
  - `ToolAvailability` dataclass for CLI tool detection
  - `ScanResult` dataclass for scan outcomes
  - `check_tool_availability()` with caching
  - `scan_snyk()`, `scan_trivy()`, `scan_semgrep()` methods
  - `scan_all_available()` for multi-tool scanning
  - `generate_capability_report()` for truthful availability

- `src/schemas.py` - Normalized output schemas
  - `SeverityLevel` enum with per-scanner mappers
  - `VulnerabilityFinding` dataclass
  - `VulnerabilityReport` dataclass with summary calculation
  - `normalize_snyk_output()`, `normalize_trivy_output()`, `normalize_semgrep_output()`

- `tests/test_security_scanner.py` - Mocked tests (no CLI tools required)
  - `TestToolAvailability` - detection and caching
  - `TestSnykScanner`, `TestTrivyScanner`, `TestSemgrepScanner` - scan execution
  - `TestSchemas` - normalization and serialization
  - `TestCapabilityReport` - truthful reporting
  - `TestExecutionBoundary` - verifies subprocess.run, no LLM imports

### Execution Boundary (CRITICAL)

```
CLI subprocess executes scans
Qwen/Gemma analyze results AFTER this module returns
MCP plugins are OPERATOR tools, NOT autonomous runtime
```

### WSP References

- WSP 49: Module structure
- WSP 77: Agent coordination
- WSP 97: Execution discipline

### Roadmap

- SEC2: Policy layer (severity thresholds, escalation rules)
- SEC3: WRE skills (wrap scanner as executable skills)
- SEC4: Triggers (HoloDAE cadence integration)
- SEC5: Memory (PatternMemory outcome storage)
- SEC6: MCP eval (evaluate Codex plugin integration)
