# INTERFACE (WSP 11)

## Module: X/Twitter DAE Communication Node
**Domain**: platform_integration  
**Classification**: Autonomous Social Communication  
**WSP Compliance**: WSP 26-29 (DAE Protocols)

## Public API

### Verified API publication leaf

`src/verified_x_publisher.py::publish_verified_x(...)` is an internal transport
for the public `UnifiedXInterface.post_verified_x(...)` owner in
`social_media_orchestrator`. It accepts an injected synchronous Tweepy-compatible
client, explicit expected provider user ID and durable database path. Call the
UnifiedX owner for input validation and dry-run; do not call the leaf directly.

It verifies `get_me`, claims before `create_tweet`, persists the returned numeric
ID and verifies author/content through `get_tweet`. Unknown write outcomes cannot
retry creation; known IDs retry readback only. Live success requires a persisted
`verified`/`already_verified` receipt. Request awaits are bounded to 30 seconds;
the caller must additionally bound client socket I/O. Provider exception text is
not returned. Package imports do not instantiate the legacy browser/DAE path.
See `social_media_orchestrator/docs/ANTIFAFM_CAMPAIGN.md` for host operation.

### Core Classes
- `XTwitterDAENode`: Main DAE communication node with full autonomous capabilities
- `DAEAuthenticator`: WSP-27 entangled authentication protocol implementation
- `CABREngine`: WSP-29 collaborative autonomous behavior recursive engine
- `DAEIdentity`: WSP-26 tokenized identity framework

### Primary Methods

#### Authentication
```python
async def authenticate_twitter(bearer_token: str, api_key: str = None, 
                              api_secret: str = None, access_token: str = None,
                              access_token_secret: str = None) -> bool
```

#### Autonomous Communication
```python
async def post_autonomous_content(content: str, engagement_context: Dict[str, Any] = None) -> str
async def monitor_mentions(max_results: int = 10) -> List[Dict[str, Any]]
async def engage_autonomously(target_post_id: str, engagement_type: str = "like") -> bool
```

#### DAE Management
```python
def get_dae_status() -> Dict[str, Any]
def create_x_twitter_dae_node(config: Optional[Dict[str, Any]] = None) -> XTwitterDAENode
```

## Parameters

### XTwitterDAENode.__init__()
- `config: Optional[Dict[str, Any]]` - Configuration dictionary for DAE node
- `logger: Optional[logging.Logger]` - Custom logger instance

### authenticate_twitter()
- `bearer_token: str` - Twitter Bearer Token for API v2 (required)
- `api_key: str` - Twitter API Key (optional, for v1.1)
- `api_secret: str` - Twitter API Secret (optional, for v1.1)
- `access_token: str` - Twitter Access Token (optional, for posting)
- `access_token_secret: str` - Twitter Access Token Secret (optional, for posting)

### post_autonomous_content()
- `content: str` - Content to post autonomously with DAE signature
- `engagement_context: Dict[str, Any]` - Additional context for CABR scoring

## Returns

### authenticate_twitter()
- `bool` - True if authentication successful, False otherwise

### post_autonomous_content()
- `str` - Post ID if successful, raises exception on failure

### monitor_mentions()
- `List[Dict[str, Any]]` - List of mentions with DAE verification status

### get_dae_status()
- `Dict[str, Any]` - Comprehensive DAE status including WSP compliance metrics

## Errors

### Common Exceptions
- `ValueError` - Invalid parameters or unauthenticated operations
- `ImportError` - Missing dependencies (tweepy, cryptography)
- `Exception` - API failures, network errors, or authentication issues

### Error Handling
- All methods include comprehensive error logging
- WRE integration provides enhanced error tracking
- Simulation mode available when dependencies unavailable

## Examples

### Basic DAE Node Setup
```python
from modules.platform_integration.x_twitter.src.x_twitter_dae import create_x_twitter_dae_node

# Create DAE node
dae_node = create_x_twitter_dae_node()

# Authenticate with Twitter
success = await dae_node.authenticate_twitter(
    bearer_token="your_bearer_token",
    access_token="your_access_token",
    access_token_secret="your_access_token_secret"
)
```

### Autonomous Content Posting
```python
# Post autonomous content with DAE signature
post_id = await dae_node.post_autonomous_content(
    "[BOT] Autonomous communication from FoundUps DAE network! #AutonomousDAE",
    {"test_mode": False, "dae_verified": True}
)
```

### DAE Status Monitoring
```python
# Get comprehensive DAE status
status = dae_node.get_dae_status()
print(f"Smart DAO Ready: {status['operational_metrics']['smart_dao_ready']}")
print(f"CABR Score: {status['cabr_score']}")
```

### Standalone Execution
```python
# Run DAE node in interactive standalone mode
dae = XTwitterDAENode()
await dae.run_standalone()
```
