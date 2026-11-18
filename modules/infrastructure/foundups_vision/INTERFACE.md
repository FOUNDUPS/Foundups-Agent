# FoundUps Vision - Interface Specification

**WSP 11 Compliance:** In Progress
**Version:** 0.1.0

---

## Public API

### UITarsBridge

Main bridge to UI-TARS Desktop for vision-based automation.

### Explicit coordinate profiles — 2026-11-01

`execute_action(..., context={"coordinate_profile": "legacy_1000"})` remains the
default tagged1000-grid contract. Coordinates are bounded, not guessed from
whether a number exceeds1000. Unknown/multiple/malformed or executable actions
fail closed before any input action.

The opt-in `ui_tars_1_5_qwen25vl` profile requires the verified API model identifier
`ui-tars-1.5-7b`. Its plain `click(start_box='(x,y)')` coordinates are absolute pixels
over the explicitly submitted factor28 image grid, following ByteDance's
[model guide](https://github.com/bytedance/UI-TARS/blob/main/README_coordinates.md).
The bridge pre-resizes its image to that grid, then maps through observed CSS
geometry. The new profile is a top-level-only pilot: the viewport query must
prove `topLevel: true`, finite positive width/height, and screenshot scales
consistent within one physical rounding pixel per axis. Unknown/nested contexts
fail before inference or input; it never guesses or queries legacy frame offsets.
Existing legacy iframe/fallback behavior remains unchanged. Result metadata includes `coordinate_profile`,
`model_image_size`, `coordinate_grid_size`, `original_screenshot_size`,
`coordinates`, `observed_viewport` and `viewport_css`. The submitted image size and coordinate grid
are separate for the legacy normalized profile; diagnostics label both explicitly.
Do not apply the profile to another model merely because its filename says7B.

`verify`/`find` return a proposed location without clicking. A model response or
parse success is not a button/playback test: independently check the fresh frame,
execute authorized input through the approved controller, then observe the full
result. Unknown model provenance or geometry blocks actuation. The static
Storytime probe is development evidence, not autonomous gameplay or WRE admission.
Results now expose `proposal_only` and `action_executed`. Click/type/scroll only
report success when the existing browser actuator returns `{ok: true}` exactly;
sentinel denial, missing element or missing acknowledgement report failure/error
and emit `action_failed`. This confirms dispatch only, not the application's
eventual outcome; observe playback/navigation/state independently afterward.

```python
class UITarsBridge:
    """Bridge to UI-TARS Desktop for vision-based browser automation."""
    
    def __init__(
        self,
        ui_tars_path: str = "E:/HoloIndex/models/ui-tars-1.5",
        browser_port: int = 9222
    ) -> None:
        """Initialize UI-TARS bridge.
        
        Args:
            ui_tars_path: Path to UI-TARS Desktop installation
            browser_port: Chrome debugging port
        """
    
    async def execute_action(
        self,
        action: str,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 10
    ) -> ActionResult:
        """Execute a vision-based action.
        
        Args:
            action: Action type ('click', 'type', 'scroll', 'verify')
            description: Human-readable description of target element
            context: Additional context (video_id, comment_id, etc.)
            timeout: Max seconds to wait for action
            
        Returns:
            ActionResult with success status and details
            
        Raises:
            UITarsConnectionError: If UI-TARS is not running
            ElementNotFoundError: If element cannot be located
            ActionTimeoutError: If action exceeds timeout
        """
    
    async def capture_screenshot(self) -> Screenshot:
        """Capture current browser state.
        
        Returns:
            Screenshot object with image data and metadata
        """
    
    def close(self) -> None:
        """Close UI-TARS connection."""
```

### VisionExecutor

High-level executor for multi-step vision workflows.

```python
class VisionExecutor:
    """Executes multi-step vision workflows with verification."""
    
    def __init__(
        self,
        bridge: UITarsBridge,
        max_retries: int = 3
    ) -> None:
        """Initialize executor.
        
        Args:
            bridge: UITarsBridge instance
            max_retries: Max retry attempts per action
        """
    
    async def execute_workflow(
        self,
        steps: List[ActionStep],
        verify_each: bool = True
    ) -> WorkflowResult:
        """Execute a series of vision actions.
        
        Args:
            steps: List of ActionStep objects
            verify_each: Whether to verify after each step
            
        Returns:
            WorkflowResult with all step outcomes
        """
```

---

## Data Types

### ActionResult

```python
@dataclass
class ActionResult:
    success: bool
    action: str
    description: str
    duration_ms: int
    screenshot_before: Optional[str]  # Path
    screenshot_after: Optional[str]   # Path
    error: Optional[str]
    confidence: float  # 0.0 - 1.0
```

### ActionStep

```python
@dataclass
class ActionStep:
    action: str           # 'click', 'type', 'scroll', 'verify'
    description: str      # "blue Like button"
    text: Optional[str]   # For 'type' action
    wait_after: float     # Seconds to wait after action
```

### WorkflowResult

```python
@dataclass
class WorkflowResult:
    success: bool
    steps_completed: int
    steps_total: int
    step_results: List[ActionResult]
    total_duration_ms: int
```

---

## Configuration

### ui_tars_config.json

```json
{
    "ui_tars_path": "E:/HoloIndex/models/ui-tars-1.5",
    "model_name": "UI-TARS-1.5-7B.Q4_K_M.gguf",
    "browser_port": 9222,
    "screenshot_dir": "memory/screenshots",
    "max_retries": 3,
    "action_timeout": 10,
    "verify_timeout": 5
}
```

---

## Events (Telemetry)

Events emitted for AI Overseer monitoring:

| Event | Payload |
|-------|---------|
| `vision_action_start` | `{action, description, context}` |
| `vision_action_complete` | `{action, success, duration_ms, confidence}` |
| `vision_action_failed` | `{action, error, retry_count}` |
| `vision_screenshot` | `{path, hash, url}` |
| `vision_workflow_complete` | `{steps_completed, total_duration_ms}` |
| `vision_action_log` | `{action, target, text_mode, duration_ms, result, log_path}` |
| `livechat_notify` | `{message: "Comments all liked.", stream_id, timestamp}` |

Logging constraints:
- Every UI-TARS action must emit a DAE log entry (action, target, result, screenshot path) for troubleshooting.
- Typing must use 012 speed (character-by-character, no paste). Emit `text_mode="slow_type"` in telemetry.
- LiveChat flows should emit a notification event after engagement: `Comments all liked.`

---

## Error Handling

### Exception Hierarchy

```python
class FoundUpsVisionError(Exception):
    """Base exception for foundups_vision."""
    pass

class UITarsConnectionError(FoundUpsVisionError):
    """UI-TARS Desktop not running or unreachable."""
    pass

class ElementNotFoundError(FoundUpsVisionError):
    """Vision model could not locate element."""
    pass

class ActionTimeoutError(FoundUpsVisionError):
    """Action exceeded timeout."""
    pass
```

---

## Usage Examples

### Basic Click Action

```python
from modules.infrastructure.foundups_vision.src.ui_tars_bridge import UITarsBridge

bridge = UITarsBridge()

result = await bridge.execute_action(
    action="click",
    description="thumbs up Like button below the comment",
    context={"comment_id": "xyz123"}
)

if result.success:
    print(f"Liked with {result.confidence:.0%} confidence")
```

### Multi-Step Workflow

```python
from modules.infrastructure.foundups_vision.src.vision_executor import VisionExecutor, ActionStep

executor = VisionExecutor(bridge)

steps = [
    ActionStep(action="scroll", description="scroll to comment section", wait_after=1.0),
    ActionStep(action="click", description="Like button on first comment", wait_after=0.5),
    ActionStep(action="click", description="Reply button on first comment", wait_after=0.5),
    ActionStep(action="type", description="reply text box", text="Great comment! 👍", wait_after=0.5),
    ActionStep(action="click", description="blue Reply submit button", wait_after=1.0),
]

result = await executor.execute_workflow(steps, verify_each=True)
print(f"Completed {result.steps_completed}/{result.steps_total} steps")
```

---

**Interface Version:** 0.1.0
**WSP 11 Compliance:** Structure Complete, Implementation Pending

