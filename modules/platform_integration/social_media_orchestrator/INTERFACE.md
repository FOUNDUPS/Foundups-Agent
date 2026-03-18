# INTERFACE (WSP 11)

## Module: Social Media Orchestrator
**Domain**: platform_integration  
**Classification**: Social Media Orchestration Service  
**WSP Compliance**: WSP 3, WSP 11, WSP 22, WSP 49, WSP 42

## Public API

### Core Classes
- `SocialMediaOrchestrator`: Main orchestration service for unified social media management
- `OAuthCoordinator`: Centralized OAuth management for all social platforms
- `ContentOrchestrator`: Content generation and cross-platform formatting
- `SchedulingEngine`: Advanced scheduling with platform-specific optimizations
- `TwitterAdapter`: Twitter/X platform-specific adapter
- `LinkedInAdapter`: LinkedIn platform-specific adapter
- `AutonomousActionScheduler`: Natural language understanding for 0102 commands
- `HumanSchedulingInterface`: Human (012) interface for scheduled posts
- `SimplePostingOrchestrator`: Sequential posting with anti-detection
- `RefactoredPostingOrchestrator`: Clean coordinator with QWEN pre-posting intelligence checks
- `DuplicatePreventionManager`: Duplicate detection with QWEN platform health monitoring

### Primary Methods

#### Orchestrator Management
```python
async def initialize(config: Optional[Dict[str, Any]] = None) -> bool
async def authenticate_platform(platform: str, credentials: Dict[str, Any]) -> bool
def get_status() -> Dict[str, Any]
```

### Broker-Managed Runtime Hooks

```python
from modules.platform_integration.social_media_orchestrator.scripts.launch import (
    run_social_media_dae,
    stop_social_media_dae,
)

run_social_media_dae()
stop_social_media_dae()  # -> {"status": "stopping"} | {"status": "not_running"}
```

Runtime contract:
- `main.py` registers `social_media` with `stop_callable=stop_social_media_dae`
- the cadence wait is interruptible, so stop requests do not wait for the full interval

#### Content Operations
```python
async def post_content(content: str, platforms: List[str], options: Optional[Dict] = None) -> Dict[str, Any]
async def schedule_content(content: str, platforms: List[str], schedule_time: datetime, options: Optional[Dict] = None) -> str
async def get_content_history(platform: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]
```

#### Cross-Platform Management
```python
async def sync_platforms() -> Dict[str, bool]
async def get_platform_status(platform: str) -> Dict[str, Any]
def list_supported_platforms() -> List[str]

# QWEN Intelligence Methods
async def qwen_pre_posting_check(stream_info: Dict, platforms: List[str]) -> Dict[str, Any]
async def get_platform_health() -> Dict[str, str]
```

### Adapter Interface

#### Platform Adapters
```python
# TwitterAdapter
async def post(content: str, options: Dict = None) -> str
async def authenticate(credentials: Dict[str, Any]) -> bool
def get_platform_limits() -> Dict[str, Any]

# LinkedInAdapter
async def post(content: str, options: Dict = None) -> str
async def authenticate(credentials: Dict[str, Any]) -> bool
def get_platform_limits() -> Dict[str, Any]

# LinkedIn Company Poster Skill (0102🦞)
# Location: modules/ai_intelligence/ai_overseer/skillz/linkedin_company_poster/
def post_update(content: str, signature: str = "0102🦞") -> Tuple[bool, str]
def write_article(title: str, body: str, signature: str = "0102🦞") -> Tuple[bool, str]
def open_article_editor() -> Tuple[bool, str]
```

### LinkedIn Company Poster CLI
```bash
# Post update to FoundUps company page
python -m modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster --post "Your content"

# Write article
python -m modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster --article "Title" --body "Body"

# Test article editor
python -m modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster --test-article
```

## Parameters

### SocialMediaOrchestrator.__init__()
- `config: Optional[Dict[str, Any]]` - Configuration including platform settings, logging level
- `logger: Optional[logging.Logger]` - Custom logger instance

### authenticate_platform()
- `platform: str` - Platform identifier ('twitter', 'linkedin')
- `credentials: Dict[str, Any]` - Platform-specific authentication data

### post_content()
- `content: str` - Content to post (required)
- `platforms: List[str]` - Target platforms ['twitter', 'linkedin'] (required)
- `options: Optional[Dict]` - Platform-specific options (hashtags, mentions, media)

### schedule_content()
- `content: str` - Content to schedule (required)
- `platforms: List[str]` - Target platforms (required) 
- `schedule_time: datetime` - When to post the content (required)
- `options: Optional[Dict]` - Additional scheduling and content options

## Returns

### initialize()
- `bool` - True if initialization successful, False otherwise

### authenticate_platform()
- `bool` - True if authentication successful for the platform

### post_content()
- `Dict[str, Any]` - Results per platform with post IDs and status
```python
{
    'twitter': {'success': True, 'post_id': 'tweet_123', 'error': None},
    'linkedin': {'success': False, 'post_id': None, 'error': 'Rate limit exceeded'}
}
```

### schedule_content()
- `str` - Schedule ID for tracking the scheduled content

### get_status()
- `Dict[str, Any]` - Comprehensive orchestrator status
```python
{
    'platforms': {'twitter': 'authenticated', 'linkedin': 'error'},
    'active_schedules': 5,
    'total_posts': 142,
    'last_activity': '2025-01-10T15:30:00Z',
    'platform_health': {'linkedin': 'HEALTHY', 'x_twitter': 'WARMING'}
}
```

### qwen_pre_posting_check()
- `Dict[str, Any]` - QWEN intelligence decision about posting
```python
{
    'qwen_active': True,
    'should_post': True,
    'warnings': [],
    'recommendations': ['linkedin', 'x_twitter'],
    'delays': {'linkedin': 0, 'x_twitter': 15},
    'reasons': ['All platforms healthy']
}
```

## Errors

### OrchestrationError
- Base exception for orchestrator-related failures
- Includes platform context and error details

### AuthenticationError
- Raised when platform authentication fails
- Contains platform-specific error information

### ContentError
- Raised for content-related issues (too long, invalid format)
- Includes validation details and suggestions

### SchedulingError
- Raised for scheduling conflicts or failures
- Contains timing and platform availability information

## Examples

### Basic Setup and Authentication
```python
from modules.platform_integration.social_media_orchestrator import SocialMediaOrchestrator

# Initialize orchestrator
orchestrator = SocialMediaOrchestrator({
    'logging_level': 'INFO',
    'enable_scheduling': True
})

await orchestrator.initialize()

# Authenticate Twitter
twitter_creds = {
    'bearer_token': 'your_bearer_token',
    'access_token': 'your_access_token',
    'access_token_secret': 'your_access_token_secret'
}
await orchestrator.authenticate_platform('twitter', twitter_creds)

# Authenticate LinkedIn
linkedin_creds = {
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret',
    'access_token': 'your_access_token'
}
await orchestrator.authenticate_platform('linkedin', linkedin_creds)
```

### Cross-Platform Posting
```python
# Post to both platforms simultaneously
result = await orchestrator.post_content(
    content="[ROCKET] Exciting update from FoundUps development team!",
    platforms=['twitter', 'linkedin'],
    options={
        'twitter': {'hashtags': ['#FoundUps', '#Development']},
        'linkedin': {'visibility': 'PUBLIC'}
    }
)

print(f"Twitter: {result['twitter']['success']}")
print(f"LinkedIn: {result['linkedin']['success']}")
```

### Content Scheduling
```python
from datetime import datetime, timedelta

# Schedule content for tomorrow
schedule_time = datetime.now() + timedelta(days=1)
schedule_id = await orchestrator.schedule_content(
    content="Weekly development update! [U+1F4BB] #WeeklyUpdate",
    platforms=['twitter', 'linkedin'],
    schedule_time=schedule_time
)

print(f"Scheduled with ID: {schedule_id}")
```

### Status Monitoring
```python
# Get comprehensive status
status = orchestrator.get_status()
print(f"Platforms: {status['platforms']}")
print(f"Active schedules: {status['active_schedules']}")

# Get platform-specific status
twitter_status = await orchestrator.get_platform_status('twitter')
print(f"Twitter rate limit: {twitter_status['rate_limit']}")
```

### Hello World Tests
```python
# Test Twitter hello world (test mode)
await orchestrator.test_platform_hello_world('twitter')

# Test LinkedIn hello world (test mode)
await orchestrator.test_platform_hello_world('linkedin')
```

### Natural Language Scheduling (0102 Mode)
```python
from modules.platform_integration.social_media_orchestrator.src.autonomous_action_scheduler import AutonomousActionScheduler

# Initialize 0102 scheduler
scheduler = AutonomousActionScheduler()

# Understand natural language commands
action = scheduler.understand_command(
    "Post 'Going live soon!' to LinkedIn in 30 minutes",
    context={'stream_title': 'AI Development'}
)

# Execute pending actions
results = await scheduler.execute_pending_actions()
```

### Human Scheduling Interface (012 Mode)
```python
from modules.platform_integration.social_media_orchestrator.src.human_scheduling_interface import HumanSchedulingInterface

# Initialize human scheduler
human_scheduler = HumanSchedulingInterface()

# Schedule a post
post_id = human_scheduler.schedule_post(
    content="Stream starting soon!",
    platforms=[Platform.LINKEDIN, Platform.X_TWITTER],
    scheduled_time=datetime.now() + timedelta(hours=2)
)

# Execute scheduled posts
results = await human_scheduler.execute_scheduled_posts()
```

### QWEN Platform Intelligence
```python
from modules.platform_integration.social_media_orchestrator.src.core.duplicate_prevention_manager import DuplicatePreventionManager

# Initialize with QWEN intelligence
duplicate_mgr = DuplicatePreventionManager(qwen_enabled=True)

# Get QWEN pre-posting decision
stream_info = {
    'title': 'Live Stream',
    'url': 'https://youtube.com/watch?v=123',
    'channel_name': 'FoundUps'
}
qwen_decision = duplicate_mgr.qwen_pre_posting_check(stream_info, ['linkedin', 'x_twitter'])

if qwen_decision['should_post']:
    print(f"QWEN recommends posting to: {qwen_decision['recommendations']}")
else:
    print(f"QWEN blocked posting: {qwen_decision['warnings']}")

# Check platform health
health = duplicate_mgr.get_platform_health()
print(f"LinkedIn: {health['linkedin']}, X/Twitter: {health['x_twitter']}")
```
