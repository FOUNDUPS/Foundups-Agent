# OpenRouter Client - Interface Specification

## Public API

### Classes

#### `OpenRouterConfig`
Frozen dataclass for runtime configuration.

```python
@dataclass(frozen=True)
class OpenRouterConfig:
    api_key: str
    base_url: str
    default_model: str
    preset: str
    timeout_sec: float
    fallback_enabled: bool
    web_search: bool

    @classmethod
    def from_env(cls) -> "OpenRouterConfig": ...
```

#### `OpenRouterResponse`
Response wrapper with cost tracking.

```python
@dataclass
class OpenRouterResponse:
    ok: bool              # True if request succeeded
    content: str          # Response content
    model: str            # Model used
    cost: float           # Cost in USD
    prompt_tokens: int    # Input tokens
    completion_tokens: int # Output tokens
    error: Optional[str]  # Error message if ok=False
    raw: Optional[Dict]   # Raw API response
```

#### `OpenRouterClient`
Main client class.

```python
class OpenRouterClient:
    def __init__(self, config: Optional[OpenRouterConfig] = None): ...

    def is_configured(self) -> bool: ...
    def health(self) -> tuple[bool, str]: ...
    def list_models(self) -> List[str]: ...

    def chat_completion(
        self,
        user_message: str,
        system_prompt: str = "You are a helpful assistant.",
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        use_preset: bool = True,
        web_search: Optional[bool] = None,
    ) -> OpenRouterResponse: ...

    def startup_probe(self) -> Dict[str, Any]: ...
```

### Functions

```python
def get_openrouter_client() -> OpenRouterClient:
    """Get singleton client instance."""

def openrouter_chat(
    message: str,
    system_prompt: str = "You are a helpful assistant.",
    model: Optional[str] = None,
    **kwargs,
) -> OpenRouterResponse:
    """Quick chat completion."""

def openrouter_health() -> tuple[bool, str]:
    """Quick health check."""
```

### Constants

```python
MODEL_ALIASES: Dict[str, str]  # Model alias mappings
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | (required) | API key from openrouter.ai |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | API base URL |
| `OPENROUTER_DEFAULT_MODEL` | `anthropic/claude-sonnet-4` | Default model |
| `OPENROUTER_PRESET` | `foundups-agent` | Dashboard preset name |
| `OPENROUTER_TIMEOUT_SEC` | `60` | Request timeout |
| `OPENROUTER_FALLBACK_ENABLED` | `true` | Enable as fallback |
| `OPENROUTER_WEB_SEARCH` | `false` | Enable web search plugin |

## Error Handling

All errors return `OpenRouterResponse` with `ok=False` and `error` message:
- API key not configured
- Request timeout
- HTTP errors (4xx, 5xx)
- Connection errors
- Unexpected exceptions

## Thread Safety

- `OpenRouterClient` instances are thread-safe for read operations
- `requests.Session` is created lazily and reused
- Singleton via `get_openrouter_client()` is safe for concurrent access
