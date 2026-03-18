# Container Isolation Interface

## Public API

### MountPolicy

```python
class MountPolicy:
    def __init__(
        self,
        config_path: Path = ~/.config/foundups/mount-policy.json,
        repo_root: Optional[Path] = None,
    ):
        """Initialize mount policy with optional custom config path."""

    def check_mount(self, path: str) -> MountDecision:
        """Check if path can be mounted into container."""

    def add_to_allowlist(self, path: str) -> None:
        """Add path to custom allowlist."""

    def add_to_blocklist(self, path: str) -> None:
        """Add path to custom blocklist."""

    def filter_allowed(self, paths: List[str]) -> List[str]:
        """Return only paths that are allowed to mount."""

    def save_config(self) -> None:
        """Save current policy to config file."""
```

### MountDecision

```python
class MountDecision(Enum):
    ALLOWED = "allowed"
    BLOCKED_SENSITIVE = "blocked_sensitive"
    BLOCKED_NOT_IN_ALLOWLIST = "blocked_not_in_allowlist"
    BLOCKED_PATTERN = "blocked_pattern"
```

### ContainerExecutor

```python
class ContainerExecutor:
    def __init__(
        self,
        repo_root: Optional[Path] = None,
        mount_policy: Optional[MountPolicy] = None,
        docker_available: Optional[bool] = None,
    ):
        """Initialize executor with optional mount policy."""

    @property
    def docker_available(self) -> bool:
        """Return whether Docker is available."""

    async def execute(
        self,
        command: List[str],
        config: Optional[ContainerConfig] = None,
    ) -> ContainerResult:
        """Execute command in ephemeral container."""

    async def execute_python(
        self,
        code: str,
        config: Optional[ContainerConfig] = None,
    ) -> ContainerResult:
        """Execute Python code in container."""

    async def execute_skill(
        self,
        skill_path: Path,
        input_data: Dict[str, Any],
        config: Optional[ContainerConfig] = None,
    ) -> ContainerResult:
        """Execute skill in isolated container."""
```

### ContainerConfig

```python
@dataclass
class ContainerConfig:
    image: str = "python:3.12-slim"
    timeout_sec: float = 60.0
    memory_limit: str = "512m"
    cpu_limit: str = "1.0"
    user: str = "nobody"
    network: str = "none"
    working_dir: str = "/workspace"
    env_vars: Dict[str, str] = field(default_factory=dict)
    mounts: List[str] = field(default_factory=list)
```

### ContainerResult

```python
@dataclass
class ContainerResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    container_id: Optional[str] = None
    error: Optional[str] = None
```

## Integration Points

| Component | Import Path | Usage |
|-----------|-------------|-------|
| Supervisor24x7 | EXECUTE state | Container-isolated skill execution |
| WREMasterOrchestrator | execute_skill() | Isolate skill code |
| CodeActExecutor | _execute_python() | Sandbox Python execution |
