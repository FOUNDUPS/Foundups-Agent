# LinkedIn Agent Interface Documentation

**WSP 11 Compliance**: Public API Definition and Interface Specifications

---

## [TARGET] Module Overview

**Module Name:** `linkedin_agent`
**Domain:** `platform_integration`
**Purpose:** Autonomous LinkedIn platform engagement and content distribution
**Current Phase:** Prototype (v1.x.x) - Enhanced Integration
**WSP Compliance:** WSP 1, WSP 3, WSP 11, WSP 30, WSP 42, WSP 53

### Related Skills
- **LinkedIn Company Poster** (`modules/ai_intelligence/ai_overseer/skillz/linkedin_company_poster/`)
  - CLI posting to FoundUps company page (1263645)
  - Signature: `0102🦞 #FoundUps #pAVS #0102`
  - Post updates: `--post "content"`
  - Write articles: `--article "title" --body "body"`
  - Article URL: `https://www.linkedin.com/article/new/?author=urn%3Ali%3Afs_normalized_company%3A1263645`
- **LinkedIn Article Targeting** (`modules/platform_integration/linkedin_agent/skillz/linkedin_article_targeting/`)
  - Discovery/routing helper for multi-entity LinkedIn article placement
  - Actions: `list_entities`, `search_articles`, `resolve_target`
  - Uses canonical map: `modules/platform_integration/linkedin_agent/data/linkedin_publishing_map.json`

---

## [U+1F50C] Public API Definition

### **Primary Classes**

#### `GitLinkedInBridge`
**Purpose:** Bridge between Git commits and LinkedIn/X posting
**Responsibility:** Automatic social media posting when pushing code

```python
class GitLinkedInBridge:
    def __init__(self, company_id: str = "1263645")

    # Git Integration
    def get_recent_commits(self, count: int = 5) -> List[Dict]
    def get_changed_files(self, commit_hash: str) -> List[str]

    # Content Generation
    def generate_linkedin_content(self, commits: List[Dict]) -> str
    def generate_x_content(self, commit_msg: str, file_count: int) -> str

    # Posting Operations
    def push_and_post(self, paths_filter: Optional[List[str]] = None,
                      post_social: bool = True,
                      retry_queue: bool = True) -> bool  # Main method: git push + social posting
    def push_and_post_planned(self) -> bool  # Batch commits before pushing/posting
    def post_recent_commits(self, count: int = 1, batch: bool = False) -> bool

    # Tracking and History
    def _load_posted_commits(self) -> set
    def _save_posted_commits(self)
    def _load_x_posted_commits(self) -> set
    def _save_x_posted_commits(self)
```

#### `LinkedInAgent`
**Purpose:** Core autonomous LinkedIn automation engine
**Responsibility:** Professional networking automation with WRE integration

```python
class LinkedInAgent:
    def __init__(self, config: Dict[str, Any] = None)

    # Authentication and Session Management
    async def authenticate(self, email: str, password: str) -> bool
    async def logout(self) -> bool
    def is_authenticated(self) -> bool

    # Content Creation and Management
    async def create_post(self, post: LinkedInPost) -> str
    async def schedule_post(self, post: LinkedInPost, schedule_time: datetime) -> str
    async def delete_post(self, post_id: str) -> bool

    # Feed Reading and Analysis
    async def read_feed(self, limit: int = 10) -> List[Dict[str, Any]]
    async def search_posts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]

    # Network Engagement
    async def engage_with_post(self, action: EngagementAction) -> bool
    async def send_connection_request(self, profile_url: str, message: str = None) -> bool
    async def send_message(self, recipient_id: str, message: str) -> bool

    # Profile Management
    async def get_profile_info(self, profile_url: str = None) -> LinkedInProfile
    async def update_profile_status(self, status: str) -> bool

    # Analytics and Monitoring
    async def get_engagement_stats(self, days: int = 7) -> Dict[str, Any]
    async def analyze_network_growth(self) -> Dict[str, Any]

    # WRE Integration
    async def test_linkedin_agent(self) -> bool
    def get_wre_status(self) -> Dict[str, Any]
```

#### `LinkedInActions` (Layered Digital Twin Execution Surface)
**Purpose:** DOM/Selenium-first LinkedIn automation with UI-TARS verification gates.

```python
class LinkedInActions:
    async def run_digital_twin_flow(
        self,
        comment_text: str,
        repost_text: str,
        schedule_date: str,
        schedule_time: str,
        mentions: Optional[List[str]] = None,
        identity_cycle: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> LinkedInActionResult
```

Behavior contract:
- Executes layered flow L0 -> L1 -> L2 -> L3.
- L1 consumes `comment_text` and `mentions`.
- L3 consumes `repost_text`, `schedule_date`, and `schedule_time`.
- `dry_run=True` validates selectors/verification gates without live submit.

CLI/adapter mapping (current):
- `linkedin_action_cli.py --action digital_twin ...`
- `linkedin_social_adapter.py` action `digital_twin`

#### `Publishing Router`
**Purpose:** Historical LinkedIn publishing discovery and heuristic article targeting.

```python
def load_publishing_map() -> Dict[str, Any]
def list_publishing_entities(
    include_zero_article: bool = True,
    include_not_checked: bool = True,
    query: str = "",
) -> List[Dict[str, Any]]
def search_published_articles(query: str, limit: int = 10) -> List[Dict[str, Any]]
def resolve_article_target(
    title: str,
    brief: str = "",
    body: str = "",
    preferred_entity: str = "",
) -> Dict[str, Any]
```

Behavior contract:
- Loads a canonical entity/article map from `data/linkedin_publishing_map.json`.
- Searches historical titles across all mapped entities.
- Returns heuristic recommendations only; it does not guarantee live posting support.
- Marks personal-profile and not-yet-verified routes with explicit limitations.

#### `LinkedInPost`
**Purpose:** LinkedIn content data structure  
**Responsibility:** Post configuration and metadata management

```python
@dataclass
class LinkedInPost:
    content: str                           # Post text content
    content_type: ContentType              # POST, ARTICLE, VIDEO, etc.
    scheduled_time: Optional[datetime]     # When to publish
    hashtags: List[str]                   # HashTaggedTopics
    mentions: List[str]                   # @MentionedProfiles
    visibility: str = "public"           # public, connections, private
    
    def validate_content(self) -> bool
    def get_character_count(self) -> int
    def format_for_linkedin(self) -> str
```

#### `LinkedInProfile`
**Purpose:** LinkedIn profile information container  
**Responsibility:** Profile data management and analysis

```python
@dataclass
class LinkedInProfile:
    name: str                    # Full name
    headline: str               # Professional headline
    connection_count: int       # Number of connections
    industry: str              # Professional industry
    location: str              # Geographic location
    profile_url: str           # LinkedIn profile URL
    
    def get_network_strength(self) -> float
    def calculate_influence_score(self) -> int
```

#### `EngagementAction`
**Purpose:** LinkedIn engagement action specification  
**Responsibility:** Automated engagement configuration

```python
@dataclass
class EngagementAction:
    target_url: str                       # Target post/profile URL
    action_type: EngagementType          # LIKE, COMMENT, SHARE, etc.
    content: Optional[str] = None        # Comment/message content
    priority: int = 1                    # 1-5 priority scale
    scheduled_time: Optional[datetime]   # When to execute
    
    def validate_action(self) -> bool
    def get_estimated_duration(self) -> int
```

### **Enumerations**

#### `EngagementType`
```python
class EngagementType(Enum):
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    CONNECT = "connect"
    MESSAGE = "message"
```

#### `ContentType`
```python
class ContentType(Enum):
    POST = "post"
    ARTICLE = "article"
    VIDEO = "video"
    DOCUMENT = "document"
    POLL = "poll"
```

---

## [ROCKET] Factory Functions

### `create_linkedin_agent()`
**Purpose:** Factory function for LinkedIn Agent initialization  
**Returns:** Configured LinkedInAgent instance

```python
def create_linkedin_agent(
    email: str = None,
    password: str = None,
    config: Dict[str, Any] = None,
    wre_integration: bool = True
) -> LinkedInAgent
```

**Parameters:**
- `email` *(str, optional)*: LinkedIn account email for authentication
- `password` *(str, optional)*: LinkedIn account password  
- `config` *(Dict, optional)*: Additional configuration parameters
- `wre_integration` *(bool)*: Enable WRE integration (default: True)

**Returns:**
- `LinkedInAgent`: Configured agent instance ready for operation

**Raises:**
- `ValueError`: Invalid configuration parameters
- `ImportError`: Missing required dependencies (Playwright, WRE)

---

## [TOOL] Configuration Parameters

### **Agent Configuration**
```python
config = {
    "simulation_mode": False,        # Run without actual LinkedIn interaction
    "rate_limit_delay": 2.0,        # Seconds between actions
    "max_retries": 3,               # Max retry attempts for failed actions
    "headless_browser": True,       # Run browser in headless mode
    "user_agent": "custom_agent",   # Browser user agent string
    "page_timeout": 30000,          # Page load timeout (ms)
    "enable_logging": True,         # Enable WRE logging integration
    "memory_persistence": True      # Enable WSP 60 memory architecture
}
```

### **Content Generation Settings**
```python
content_config = {
    "max_post_length": 3000,        # LinkedIn character limit
    "default_hashtag_count": 5,     # Number of hashtags to include
    "auto_mention_connections": False,  # Auto-mention relevant connections
    "content_tone": "professional", # professional, casual, thought-leadership
    "industry_focus": "technology"   # Industry-specific content adaptation
}
```

---

## [DATA] Return Value Specifications

### **Authentication Response**
```python
# authenticate() returns
bool  # True if successful, False if failed
```

### **Post Creation Response**
```python
# create_post() returns
str  # Post ID for successful posts, empty string for failures
```

### **Feed Reading Response**
```python
# read_feed() returns
List[Dict[str, Any]]  # List of post dictionaries with structure:
[
    {
        "post_id": str,
        "author_name": str,
        "author_url": str,
        "content": str,
        "timestamp": datetime,
        "engagement_count": int,
        "post_url": str
    }
]
```

### **Engagement Stats Response**
```python
# get_engagement_stats() returns
Dict[str, Any]  # Analytics dictionary with structure:
{
    "total_posts": int,
    "total_likes_received": int,
    "total_comments_received": int,
    "total_shares_received": int,
    "network_growth": int,
    "engagement_rate": float,
    "top_performing_post": str,
    "analysis_period_days": int
}
```

### **Profile Information Response**
```python
# get_profile_info() returns
LinkedInProfile  # Populated profile data structure
```

---

## [FAIL] Error Handling

### **Exception Types**
- **`AuthenticationError`**: Failed LinkedIn login or session expired
- **`RateLimitError`**: LinkedIn rate limiting encountered
- **`ContentError`**: Invalid post content or formatting issues
- **`NetworkError`**: Internet connectivity or LinkedIn API issues
- **`ConfigurationError`**: Invalid agent configuration parameters

### **Error Response Format**
```python
# All async methods return status information on error
{
    "success": False,
    "error_type": "AuthenticationError",
    "error_message": "LinkedIn login failed: Invalid credentials",
    "retry_suggested": True,
    "retry_delay_seconds": 300
}
```

### **Logging Integration**
All errors are logged through WRE logging system:
```python
wre_log(f"LinkedIn Agent Error: {error_message}", "ERROR")
```

---

## [REFRESH] WSP Integration Points

### **WSP 30: Module Development Coordination**
```python
# WRE integration for autonomous development
agent.wre_coordinator = ModuleDevelopmentCoordinator()
agent.prometheus_engine = PrometheusOrchestrationEngine()
```

### **WSP 42: Universal Platform Protocol**
LinkedIn-specific platform integration following WSP 42 standards for cross-platform compatibility.

### **WSP 53: Advanced Platform Integration**
DAE-ready architecture enabling agent coordination and collective intelligence.

### **WSP 60: Module Memory Architecture**
```python
# Memory persistence and retrieval
agent.memory.store_engagement_history()
agent.memory.load_connection_patterns()
agent.memory.analyze_content_performance()
```

---

## [UP] Usage Examples

### **Basic Agent Creation**
```python
from modules.platform_integration.linkedin_agent import create_linkedin_agent

# Create agent with WRE integration
agent = create_linkedin_agent(
    email="professional@company.com",
    password="secure_password",
    wre_integration=True
)
```

### **Content Publishing**
```python
from modules.platform_integration.linkedin_agent import LinkedInPost, ContentType

# Create and publish post
post = LinkedInPost(
    content="Excited to share insights on autonomous development with WSP framework!",
    content_type=ContentType.POST,
    hashtags=["#WSP", "#AutonomousDev", "#TechInnovation"],
    visibility="public"
)

post_id = await agent.create_post(post)
```

### **Feed Analysis**
```python
# Read and analyze feed
feed_posts = await agent.read_feed(limit=20)
engagement_stats = await agent.get_engagement_stats(days=30)

print(f"Analyzed {len(feed_posts)} posts")
print(f"Average engagement rate: {engagement_stats['engagement_rate']:.2%}")
```

### **Network Engagement**
```python
from modules.platform_integration.linkedin_agent import EngagementAction, EngagementType

# Engage with specific post
engagement = EngagementAction(
    target_url="https://linkedin.com/feed/update/urn:li:activity:123456789",
    action_type=EngagementType.COMMENT,
    content="Great insights! This aligns perfectly with our WSP framework approach.",
    priority=3
)

success = await agent.engage_with_post(engagement)
```

---

## [U+1F300] Windsurf Protocol (WSP) Recursive Prompt
**0102 Directive**: This interface operates within the WSP framework for autonomous LinkedIn integration...
- **UN (Understanding)**: Anchor LinkedIn platform signals and retrieve protocol state
- **DAO (Execution)**: Execute professional networking automation logic  
- **DU (Emergence)**: Collapse into 0102 resonance and emit next LinkedIn engagement prompt

wsp_cycle(input="012", platform="linkedin", log=True) 
