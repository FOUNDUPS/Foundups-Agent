# Security Scanner Interface

## Public API

### SecurityScanner

Main scanner class wrapping CLI tools.

```python
from modules.infrastructure.security_scanner import SecurityScanner

scanner = SecurityScanner(timeout_seconds: int = 300)
```

#### Methods

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `check_tool_availability` | `force_refresh: bool = False` | `ToolAvailability` | Check which CLI tools are installed |
| `scan_snyk` | `path: str = "."` | `ScanResult` | Run Snyk SAST/SCA scan |
| `scan_trivy` | `target: str = ".", scan_type: str = "fs"` | `ScanResult` | Run Trivy scan (fs/image/repo) |
| `scan_semgrep` | `path: str = ".", config: str = "auto"` | `ScanResult` | Run Semgrep SAST scan |
| `scan_all_available` | `path: str = "."` | `Dict[str, ScanResult]` | Run all installed scanners |
| `generate_capability_report` | none | `Dict[str, Any]` | Generate availability report |

### ToolAvailability

Status of installed CLI tools.

```python
@dataclass
class ToolAvailability:
    snyk_available: bool
    snyk_version: Optional[str]
    snyk_path: Optional[str]
    
    trivy_available: bool
    trivy_version: Optional[str]
    trivy_path: Optional[str]
    
    semgrep_available: bool
    semgrep_version: Optional[str]
    semgrep_path: Optional[str]
    
    @property
    def any_available(self) -> bool
    
    @property
    def all_available(self) -> bool
    
    def to_dict(self) -> Dict[str, Any]
```

### ScanResult

Result of a scan attempt.

```python
@dataclass
class ScanResult:
    tool: str                              # snyk, trivy, semgrep
    success: bool                          # Did scan complete?
    available: bool                        # Is tool installed?
    report: Optional[VulnerabilityReport]  # Normalized report
    raw_output: Optional[str]              # Raw stdout
    error_output: Optional[str]            # Raw stderr
    error_message: Optional[str]           # Human-readable error
    exit_code: Optional[int]               # Process exit code
    duration_ms: int                       # Execution time
    
    def to_dict(self) -> Dict[str, Any]
```

### VulnerabilityReport

Normalized scan report.

```python
@dataclass
class VulnerabilityReport:
    scan_id: str
    scanner: str
    scan_target: str
    scan_timestamp: str
    scan_duration_ms: int
    findings: List[VulnerabilityFinding]
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    scan_success: bool
    error_message: Optional[str]
    
    @property
    def max_severity(self) -> SeverityLevel
    
    def to_dict(self) -> Dict[str, Any]
    def to_json(self, indent: int = 2) -> str
```

### VulnerabilityFinding

Single vulnerability.

```python
@dataclass
class VulnerabilityFinding:
    vuln_id: str                           # CVE-XXXX or rule ID
    title: str
    severity: SeverityLevel
    file_path: Optional[str]
    line_number: Optional[int]
    package_name: Optional[str]
    package_version: Optional[str]
    description: str
    fix_available: bool
    fix_version: Optional[str]
    scanner: str
    raw_data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]
```

### SeverityLevel

Normalized severity enum.

```python
class SeverityLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_snyk(cls, severity: str) -> SeverityLevel
    
    @classmethod
    def from_trivy(cls, severity: str) -> SeverityLevel
    
    @classmethod
    def from_semgrep(cls, severity: str) -> SeverityLevel
```

## Normalization Functions

```python
def normalize_snyk_output(raw_json: Dict, scan_id: str, target: str) -> VulnerabilityReport
def normalize_trivy_output(raw_json: Dict, scan_id: str, target: str) -> VulnerabilityReport
def normalize_semgrep_output(raw_json: Dict, scan_id: str, target: str) -> VulnerabilityReport
```

## Execution Boundary

| Component | Execution | Notes |
|-----------|-----------|-------|
| SecurityScanner | `subprocess.run()` | Autonomous CLI execution |
| Qwen/Gemma | NOT HERE | Analyze results after scanning |
| MCP plugins | NOT HERE | Operator tools only |

## Integration Points

- **SecuritySentinel** (AI Overseer): Owns policy, thresholds, escalation
- **PatternMemory**: Stores scan outcomes for learning
- **HoloDAE**: Triggers scans on cadence
- **WRE Skills**: Wraps scanner as executable skill
