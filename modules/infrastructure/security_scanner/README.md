# Security Scanner

Autonomous CLI-based vulnerability scanning via snyk, trivy, and semgrep.

## Execution Boundary (CRITICAL)

```
CLI subprocess executes scans (snyk, trivy, semgrep)
Qwen/Gemma analyze results AFTER this module returns
Codex/Claude MCP plugins are operator tools, NOT autonomous runtime dependencies
```

This module is the **autonomous 0102 scanning path**. No LLM, no MCP, no human in loop for scan execution.

## WSP References

- WSP 49: Module structure
- WSP 77: Agent coordination (SecuritySentinel integration)
- WSP 97: Execution discipline

## Installation

```bash
# Module has no Python dependencies beyond stdlib
# CLI tools must be installed separately:

# Snyk (npm)
npm install -g snyk
snyk auth  # One-time authentication

# Trivy (various methods)
brew install trivy        # macOS
choco install trivy       # Windows
apt-get install trivy     # Debian/Ubuntu

# Semgrep (pip)
pip install semgrep
```

## Usage

```python
from modules.infrastructure.security_scanner import SecurityScanner

scanner = SecurityScanner()

# Check what tools are available
availability = scanner.check_tool_availability()
print(f"Snyk: {availability.snyk_available}")
print(f"Trivy: {availability.trivy_available}")
print(f"Semgrep: {availability.semgrep_available}")

# Run individual scans
if availability.snyk_available:
    result = scanner.scan_snyk(".")
    if result.success:
        print(f"Found {result.report.total_findings} vulnerabilities")
        print(result.report.to_json())

# Run all available scanners
results = scanner.scan_all_available(".")
for tool, result in results.items():
    if result.success:
        print(f"{tool}: {result.report.total_findings} findings")

# Generate capability report (truthful availability)
report = scanner.generate_capability_report()
print(json.dumps(report, indent=2))
```

## Architecture

```
                    +-------------------+
                    |  SecurityScanner  |
                    |  (subprocess.run) |
                    +--------+----------+
                             |
         +-------------------+-------------------+
         |                   |                   |
    +----v----+        +-----v-----+       +-----v-----+
    |  snyk   |        |   trivy   |       |  semgrep  |
    |  CLI    |        |    CLI    |       |    CLI    |
    +----+----+        +-----+-----+       +-----+-----+
         |                   |                   |
         v                   v                   v
    +----------+        +----------+        +----------+
    | Raw JSON |        | Raw JSON |        | Raw JSON |
    +----+-----+        +-----+----+        +-----+----+
         |                   |                   |
         +-------------------+-------------------+
                             |
                    +--------v---------+
                    |  schemas.py      |
                    |  (normalize)     |
                    +--------+---------+
                             |
                    +--------v---------+
                    | VulnerabilityReport |
                    | (unified format)    |
                    +---------------------+
                             |
              +--------------+--------------+
              |                             |
     +--------v--------+           +--------v--------+
     | Qwen (analyze)  |           | PatternMemory   |
     | Gemma (validate)|           | (store/recall)  |
     +-----------------+           +-----------------+
```

## Normalized Output

All scanners produce `VulnerabilityReport` with:

```python
{
    "scan_id": "snyk-a1b2c3d4",
    "scanner": "snyk",
    "scan_target": ".",
    "scan_timestamp": "2026-04-17T12:00:00Z",
    "findings": [
        {
            "vuln_id": "CVE-2021-44228",
            "title": "Log4Shell",
            "severity": "critical",
            "package_name": "log4j",
            "package_version": "2.14.0",
            "fix_available": true,
            "fix_version": "2.17.0"
        }
    ],
    "summary": {
        "total": 1,
        "critical": 1,
        "high": 0,
        "medium": 0,
        "low": 0
    }
}
```

## Testing

All tests use mocked subprocess calls - no CLI tools required:

```bash
cd modules/infrastructure/security_scanner
pytest tests/ -v
```

## Roadmap

- **SEC1** (current): CLI proof - subprocess execution, mocked tests
- **SEC2**: Policy layer - severity thresholds, escalation rules
- **SEC3**: WRE skills - wrap scanner as executable skills
- **SEC4**: Triggers - HoloDAE cadence integration
- **SEC5**: Memory - PatternMemory outcome storage
- **SEC6**: MCP eval - evaluate Codex plugin integration for 012 workflows
