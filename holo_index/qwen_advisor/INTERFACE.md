# HoloDAE Modular Interface (Post-Refactoring)

## [ALERT] MAJOR ARCHITECTURAL CHANGE (2025-09-28)

**The HoloDAE interface has been completely refactored** from monolithic to modular architecture following correct **Qwen->0102 orchestration** principles per WSP 80.

## Public API (Modular Architecture)

### Import boundary

Importing this package or its `llm_engine` leaf does not load the coordinator,
services, UI or native inference library. The existing 20 names in `__all__`
remain discoverable through `dir()` and resolve from their original modules on
first access. Resolved objects are cached; `from` and star imports retain their
public identities. Missing attributes raise `AttributeError`, and provider
import failures propagate without caching a failed result.

Explicitly requesting an export still loads its original module and its
dependencies. Constructing or initializing an engine remains a separate effect;
this import boundary does not establish model readiness or inference quality.

### Main Coordinator (New Primary Interface)

#### HoloDAECoordinator
```python
from holo_index.qwen_advisor import HoloDAECoordinator

class HoloDAECoordinator:
    """Clean integration layer for modular HoloDAE architecture"""

    def __init__(self):
        """Initialize with all modular components"""

    def handle_holoindex_request(self, query: str, search_results: dict) -> str:
        """
        Handle HoloIndex search request with Qwen->0102 orchestration

        Args:
            query: Search query
            search_results: HoloIndex search results

        Returns:
            Analysis report with MPS-based arbitration decisions
        """

    def start_monitoring(self) -> bool:
        """Start quiet monitoring with actionable event reporting"""

    def stop_monitoring(self) -> bool:
        """Stop monitoring"""

    def get_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive status of all components"""

    def show_menu(self) -> str:
        """Show main menu and get user choice"""
```

### Orchestration Layer

#### QwenOrchestrator
```python
from holo_index.qwen_advisor.orchestration import QwenOrchestrator

class QwenOrchestrator:
    """Qwen's primary orchestration logic (WSP 80)"""

    def orchestrate_holoindex_request(self, query: str, search_results: dict) -> str:
        """
        Primary orchestration - finds issues, applies MPS scoring

        Returns:
            Orchestrated analysis with chain-of-thought reasoning
        """

    def get_chain_of_thought_summary(self) -> Dict[str, Any]:
        """Get Qwen's reasoning summary for 0102 review"""
```

### Arbitration Layer

#### MPSArbitrator
```python
from holo_index.qwen_advisor.arbitration import MPSArbitrator, ArbitrationDecision

class MPSArbitrator:
    """0102's MPS-based arbitration system (WSP 15)"""

    def arbitrate_qwen_findings(self, qwen_report: str) -> List[ArbitrationDecision]:
        """
        Review Qwen's findings and make MPS-based decisions

        Args:
            qwen_report: Qwen's orchestrated analysis report

        Returns:
            List of arbitration decisions with MPS scoring
        """

    def execute_arbitration_decisions(self, decisions: List[ArbitrationDecision]) -> Dict[str, Any]:
        """Execute the arbitration decisions autonomously"""

    def get_arbitration_summary(self) -> Dict[str, Any]:
        """Get summary of recent arbitration activity"""
```

### Core Services

#### FileSystemWatcher
```python
from holo_index.qwen_advisor.services import FileSystemWatcher

class FileSystemWatcher:
    """Real-time file system monitoring service"""

    def __init__(self, watch_paths: List[str] = None):
        """Initialize with paths to monitor"""

    def scan_for_changes(self) -> List[str]:
        """Scan for file changes since last check"""

    def get_watched_files_count(self) -> int:
        """Get total number of files being watched"""

    def get_status_summary(self) -> str:
        """Get monitoring status summary"""
```

#### ContextAnalyzer
```python
from holo_index.qwen_advisor.services import ContextAnalyzer

class ContextAnalyzer:
    """Analyze what 0102 is currently working on"""

    def analyze_work_context(self, changed_files: List[str],
                           session_actions: List[str]) -> WorkContext:
        """
        Analyze work context from files and actions

        Returns:
            WorkContext with task patterns and module focus
        """

    def get_related_modules(self, changed_files: List[str]) -> Set[str]:
        """Get modules related to changed files"""

    def detect_vibecoding_patterns(self, changed_files: List[str]) -> List[str]:
        """Detect potential vibecoding patterns"""
```

### Data Models

#### WorkContext
```python
from holo_index.qwen_advisor.models import WorkContext

@dataclass
class WorkContext:
    """Tracks 0102's current work state"""
    active_files: Set[str] = field(default_factory=set)
    primary_module: Optional[str] = None
    task_pattern: str = "unknown"
    last_activity: datetime = field(default_factory=datetime.now)
    session_actions: List[str] = field(default_factory=list)

    def add_file(self, file_path: str):
        """Add file to active work context"""

    def get_recent_files(self, limit: int = 5) -> List[str]:
        """Get recently active files"""

    def get_summary(self) -> str:
        """Get human-readable context summary"""
```

### Configuration

```python
@dataclass
class QwenAdvisorConfig:
    """Advisor configuration"""
    model_path: Path = Path("E:/LM_studio/models/local/qwen-coder-7b")
    max_tokens: int = 512
    temperature: float = 0.2
    cache_enabled: bool = True
    telemetry_path: Optional[Path] = None

    @classmethod
    def from_env(cls) -> 'QwenAdvisorConfig':
        """Load config from environment variables"""
```

## Usage Examples (Modular Architecture)

### Main Coordinator Usage
```python
from holo_index.qwen_advisor import HoloDAECoordinator

# Initialize the modular coordinator
coordinator = HoloDAECoordinator()

# Handle HoloIndex search request (main entry point)
report = coordinator.handle_holoindex_request(
    query="create authentication module",
    search_results={'code': [...], 'wsps': [...]}
)
print(f"Qwen->0102 Analysis: {report}")

# Start quiet monitoring with actionable events
coordinator.start_monitoring()

# Get comprehensive status
status = coordinator.get_status_summary()
print(f"Qwen Status: {status['qwen_status']}")
print(f"0102 Arbitration: {status['arbitration_status']}")
```

### Qwen Orchestration (Direct Access)
```python
from holo_index.qwen_advisor.orchestration import QwenOrchestrator

orchestrator = QwenOrchestrator()

# Direct orchestration (typically done via coordinator)
analysis = orchestrator.orchestrate_holoindex_request(
    query="fix authentication bug",
    search_results={'code': [...], 'wsps': [...]}
)

# Get Qwen's reasoning for 0102 review
reasoning = orchestrator.get_chain_of_thought_summary()
print(f"Qwen's Chain-of-Thought: {reasoning['recent_activity']}")
```

### 0102 Arbitration (Direct Access)
```python
from holo_index.qwen_advisor.arbitration import MPSArbitrator

arbitrator = MPSArbitrator()

# Review Qwen's findings and make MPS-based decisions
decisions = arbitrator.arbitrate_qwen_findings(qwen_report)

for decision in decisions:
    print(f"0102 Decision: {decision.recommended_action.value}")
    print(f"MPS Score: {decision.mps_analysis.total_score}")
    print(f"Reasoning: {decision.reasoning}")

# Execute decisions autonomously
results = arbitrator.execute_arbitration_decisions(decisions)
print(f"Execution Results: {results}")
```

### Core Services (Direct Access)
```python
from holo_index.qwen_advisor.services import FileSystemWatcher, ContextAnalyzer

# File monitoring
watcher = FileSystemWatcher(["holo_index/", "modules/"])
changes = watcher.scan_for_changes()
print(f"Files changed: {len(changes)}")

# Work context analysis
analyzer = ContextAnalyzer()
context = analyzer.analyze_work_context(changes, [])
print(f"Work Pattern: {context.task_pattern}")
print(f"Primary Module: {context.primary_module}")
```

### Data Models
```python
from holo_index.qwen_advisor.models import WorkContext

# Create and manipulate work context
context = WorkContext()
context.add_file("modules/auth/service.py")
context.add_action("Implementing JWT authentication")

print(f"Active Files: {len(context.active_files)}")
print(f"Context Summary: {context.get_summary()}")
```

## Error Handling

All methods may raise:
- `ImportError`: Missing dependencies (llama-cpp-python)
- `FileNotFoundError`: Model file not found
- `RuntimeError`: Model initialization failure
- `ValueError`: Invalid parameters

## Performance Considerations

- **Model Loading**: ~2 seconds first time, cached afterward
- **Inference**: ~500ms per query
- **Memory**: ~2GB for model in memory
- **Cache**: 15-minute TTL for guidance results
- **Concurrency**: Single-threaded LLM inference

## Integration Points

### With HoloIndex CLI
```python
# Automatically integrated when --llm-advisor flag used
python holo_index.py --search "query" --llm-advisor
```

### With Pattern Memory
```python
# Patterns stored for learning
E:/HoloIndex/pattern_coach/
+-- pattern_memory.json
+-- coaching_log.json
+-- effectiveness.json
```

### With Telemetry
```python
# Events recorded for analysis
E:/HoloIndex/qwen_advisor/
+-- telemetry.json
```

## WSP Compliance

- **WSP 11**: Complete interface documentation
- **WSP 35**: HoloIndex Qwen Advisor implementation
- **WSP 84**: Code memory and pattern learning
- **WSP 50**: Pre-action verification in guidance
