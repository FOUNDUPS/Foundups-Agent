# FoundUps Domain - Interface Documentation

## Interface Status

| Interface | File | Status |
|-----------|------|--------|
| `FoundUpSpawner` | `src/foundup_spawner.py` | **IMPLEMENTED** |
| `CABRLoop` | `src/foundup_spawner.py` | **IMPLEMENTED** |
| `FoundUpsLiveChatModule` | `src/main.py` | **IMPLEMENTED** |
| `PlatformManager` | - | PLANNED |
| `RuntimeEngine` | - | PLANNED |
| `FoundUpsPlatform` | - | PLANNED |

For canonical planning references, see [FOUNDUPS_DOMAIN_CANONICAL_INDEX.md](docs/FOUNDUPS_DOMAIN_CANONICAL_INDEX.md).

---

## Implemented Interfaces

### FoundUpSpawner (IMPLEMENTED)

**Module**: `src/foundup_spawner.py`
**Purpose**: Creates new FoundUp instances following WSP-defined protocols

#### **FoundUpSpawner Class**
```python
class FoundUpSpawner:
    """Spawns new FoundUp instances based on WSP-defined protocols."""
    
    def __init__(self, foundups_root: Optional[str] = None) -> None:
        """
        Initialize spawner with FoundUps root directory.
        
        Args:
            foundups_root: Optional path to FoundUps root directory
        """
    
    def spawn_foundup(self, name: str, founder: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Spawn a new FoundUp instance.
        
        Args:
            name: FoundUp name (should start with @)
            founder: Founder identifier
            config: Optional additional configuration
            
        Returns:
            Dict containing spawn result and instance info
            {
                "status": "success" | "error",
                "message": str,
                "path": str,
                "founder": str,
                "created_at": str (ISO format)
            }
        """
```

#### **CLI Interface**
```bash
# Command line interface for spawning FoundUps
python -m modules.foundups.src.foundup_spawner --name "@innovate" --founder "alice" --config '{"description": "Innovation FoundUp"}'
```

---

## Planned Interfaces (NOT YET IMPLEMENTED)

> **Note**: The interfaces below are design specifications for future implementation.
> They do not exist in current code. See Interface Status table above for implementation state.

### PlatformManager (PLANNED)

**Module**: `platform_manager.py` (not yet created)
**Purpose**: Manages multiple FoundUp instances across the platform

#### **PlatformManager Class**
```python
class PlatformManager:
    """Manages multiple FoundUp instances across the platform."""
    
    def __init__(self) -> None:
        """Initialize platform manager."""
    
    def list_foundups(self) -> List[Dict[str, Any]]:
        """
        List all FoundUp instances on the platform.
        
        Returns:
            List of FoundUp instance information
        """
    
    def get_foundup_status(self, name: str) -> Dict[str, Any]:
        """
        Get status of specific FoundUp instance.
        
        Args:
            name: FoundUp name (with @ prefix)
            
        Returns:
            Dict containing instance status and metrics
        """
    
    def start_foundup(self, name: str) -> Dict[str, Any]:
        """
        Start a FoundUp instance.
        
        Args:
            name: FoundUp name (with @ prefix)
            
        Returns:
            Dict containing start result
        """
    
    def stop_foundup(self, name: str) -> Dict[str, Any]:
        """
        Stop a FoundUp instance.
        
        Args:
            name: FoundUp name (with @ prefix)
            
        Returns:
            Dict containing stop result
        """
```

### RuntimeEngine (PLANNED)

**Module**: `runtime_engine.py` (not yet created)
**Purpose**: Execution environment for FoundUp instances

#### **RuntimeEngine Class**
```python
class RuntimeEngine:
    """Execution environment for FoundUp instances."""
    
    def __init__(self) -> None:
        """Initialize runtime engine."""
    
    def execute_cabr_cycle(self, foundup_name: str) -> Dict[str, Any]:
        """
        Execute CABR cycle for specific FoundUp.
        
        Args:
            foundup_name: FoundUp name (with @ prefix)
            
        Returns:
            Dict containing CABR cycle results
        """
    
    def get_platform_health(self) -> Dict[str, Any]:
        """
        Get overall platform health metrics.
        
        Returns:
            Dict containing platform health information
        """
    
    def optimize_performance(self) -> Dict[str, Any]:
        """
        Optimize platform performance.
        
        Returns:
            Dict containing optimization results
        """
```

### FoundUpsLiveChat (PLANNED - differs from current FoundUpsLiveChatModule)

**Module**: `foundups_livechat_module.py` (current: `src/main.py:FoundUpsLiveChatModule`)
**Purpose**: Platform-level livechat integration

> Note: Actual implementation is `FoundUpsLiveChatModule` in `src/main.py`. Interface below is planned expansion.

#### **FoundUpsLiveChat Class**
```python
class FoundUpsLiveChat:
    """Platform-level livechat integration for FoundUps."""
    
    def __init__(self) -> None:
        """Initialize FoundUps livechat module."""
    
    def start_platform_chat(self) -> Dict[str, Any]:
        """
        Start platform-wide livechat session.
        
        Returns:
            Dict containing chat session information
        """
    
    def send_platform_message(self, message: str, sender: str) -> Dict[str, Any]:
        """
        Send message to platform chat.
        
        Args:
            message: Message content
            sender: Sender identifier
            
        Returns:
            Dict containing message delivery status
        """
    
    def get_chat_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get platform chat history.
        
        Args:
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of chat messages
        """
```

### FoundUpsPlatform (PLANNED)

**Module**: `main.py` (not yet implemented as described)
**Purpose**: Main entry point for FoundUps platform

> Note: `src/main.py` exists but contains `FoundUpsLiveChatModule`, not `FoundUpsPlatform`.

#### **FoundUpsPlatform Class**
```python
class FoundUpsPlatform:
    """Main FoundUps platform entry point."""
    
    def __init__(self) -> None:
        """Initialize FoundUps platform."""
    
    def start_platform(self) -> Dict[str, Any]:
        """
        Start the FoundUps platform.
        
        Returns:
            Dict containing platform startup status
        """
    
    def stop_platform(self) -> Dict[str, Any]:
        """
        Stop the FoundUps platform.
        
        Returns:
            Dict containing platform shutdown status
        """
    
    def get_platform_status(self) -> Dict[str, Any]:
        """
        Get current platform status.
        
        Returns:
            Dict containing platform status information
        """
```

## Integration Interfaces (PLANNED)

> Note: These integrations are design specifications. The referenced modules exist but the integration layer class does not.

### WRE-Built Module Integration (PLANNED)
```python
# Integration with WRE-built platform modules
from modules.platform_integration.remote_builder import RemoteBuilder
from modules.platform_integration.linkedin_agent import LinkedInAgent
from modules.platform_integration.youtube_proxy import YouTubeProxy
from modules.platform_integration.x_twitter import XTwitterDAENode

class FoundUpsPlatformIntegration:
    """Integration layer for WRE-built platform modules."""
    
    def __init__(self):
        self.remote_builder = RemoteBuilder()
        self.linkedin_agent = LinkedInAgent()
        self.youtube_proxy = YouTubeProxy()
        self.social = XTwitterDAENode()
    
    def create_foundup_with_platforms(self, name: str, platforms: List[str]) -> Dict[str, Any]:
        """
        Create FoundUp with specific platform integrations.
        
        Args:
            name: FoundUp name
            platforms: List of platform names to integrate
            
        Returns:
            Dict containing creation result
        """
```

## Web Interface APIs (PLANNED - NOT IMPLEMENTED)

> Note: These REST API endpoints are design specifications for future foundups.com/foundups.org deployment. Not currently implemented.

### FoundUps.com/FoundUps.org REST API (PLANNED)

#### **FoundUp Management Endpoints**
```http
# Create new FoundUp
POST /api/foundups
Content-Type: application/json

{
    "name": "@innovate",
    "founder": "alice",
    "config": {
        "description": "Innovation-focused FoundUp",
        "platforms": ["linkedin", "youtube", "x_twitter"]
    }
}

# List all FoundUps
GET /api/foundups

# Get specific FoundUp
GET /api/foundups/{name}

# Update FoundUp
PUT /api/foundups/{name}

# Delete FoundUp
DELETE /api/foundups/{name}
```

#### **Platform Integration Endpoints**
```http
# Get platform status
GET /api/platforms/status

# Start platform service
POST /api/platforms/{platform}/start

# Stop platform service
POST /api/platforms/{platform}/stop

# Get platform metrics
GET /api/platforms/{platform}/metrics
```

#### **LiveChat Endpoints**
```http
# Start chat session
POST /api/chat/session

# Send message
POST /api/chat/message
Content-Type: application/json

{
    "message": "Hello FoundUps!",
    "sender": "user123"
}

# Get chat history
GET /api/chat/history?limit=100
```

## [CLIPBOARD] Error Handling

### **Standard Error Response Format**
```python
{
    "status": "error",
    "error_code": "FOUNDUP_ALREADY_EXISTS",
    "message": "FoundUp @innovate already exists",
    "details": {
        "foundup_name": "@innovate",
        "existing_path": "/modules/foundups/@innovate"
    },
    "timestamp": "2025-01-27T10:30:00Z"
}
```

### **Common Error Codes**
- `FOUNDUP_ALREADY_EXISTS`: FoundUp instance already exists
- `INVALID_FOUNDUP_NAME`: FoundUp name doesn't follow @name convention
- `PLATFORM_NOT_AVAILABLE`: Requested platform module not available
- `CABR_CYCLE_FAILED`: CABR cycle execution failed
- `PLATFORM_STARTUP_FAILED`: Platform startup failed

## [LOCK] Security Considerations

### **Authentication**
- All web API endpoints require authentication
- FoundUp creation requires founder verification
- Platform management requires admin privileges

### **Authorization**
- Founders can only manage their own FoundUps
- Platform-wide operations require admin access
- LiveChat access controlled by user permissions

### **Data Protection**
- All FoundUp data encrypted at rest
- Communication channels use TLS encryption
- User data handled per GDPR/CCPA requirements

## [DATA] Performance Requirements

### **Response Times**
- FoundUp creation: < 5 seconds
- Platform status queries: < 1 second
- LiveChat message delivery: < 500ms
- CABR cycle execution: < 30 seconds

### **Scalability**
- Support 1000+ concurrent FoundUp instances
- Handle 100+ simultaneous LiveChat users
- Process 1000+ platform API requests per minute
- Maintain performance under 10x load increase

## AionUI External Surface

`AionUI` is an external orchestration surface, not a replacement for
`FoundUpSpawner`.

Canonical relationship:
- `FoundUp Seed` = declarative build intent
- `FoundUpSpawner` = low-level repo/workspace bootstrap primitive
- `AionUI` = external visual command deck supervising the seed-driven build

Reference:
- `modules/foundups/docs/AIONUI_FOUNDUP_FACTORY_WSP97_ARCHITECTURE_2026-03-16.md`

---

**Note**: All interfaces follow WSP 11 standards and are designed for seamless integration with the WRE-built platform modules across all enterprise domains.
