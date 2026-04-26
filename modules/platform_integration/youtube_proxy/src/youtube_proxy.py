"""
YouTube Proxy: Cross-Domain Component Orchestrator
WSP Protocol: WSP 42 (Cross-Domain Integration), WSP 40 (Architectural Coherence)

Revolutionary YouTube integration that orchestrates components across multiple 
enterprise domains for complete autonomous functionality.
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===


import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Component imports across enterprise domains
try:
    from modules.infrastructure.oauth_management.src.oauth_manager import OAuthManager
    from modules.communication.livechat.src.livechat_processor import LiveChatProcessor  
    from modules.ai_intelligence.banter_engine.src.banter_engine import BanterEngine
    from modules.infrastructure.agent_management.src.agent_manager import AgentManager
    from modules.platform_integration.stream_resolver.src.stream_resolver import StreamResolver
except ImportError as e:
    print(f"[WARN] Import warning: {e} (will use mock components in standalone mode)")

class EngagementLevel(Enum):
    """Stream engagement level indicators"""
    LOW = "low"
    MODERATE = "moderate" 
    HIGH = "high"
    VIRAL = "viral"

@dataclass
class StreamInfo:
    """Stream information structure"""
    stream_id: str
    title: str
    status: str = "live"
    viewer_count: int = 0
    chat_enabled: bool = True
    url: str = ""

@dataclass
class YouTubeStream:
    """YouTube stream data structure for enhanced stream processing"""
    stream_id: str
    title: str
    description: str
    status: str
    viewer_count: int
    chat_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    start_time: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    engagement_level: Optional[EngagementLevel] = None

@dataclass  
class ProxyStatus:
    """Proxy operational status"""
    authenticated: bool = False
    stream_active: bool = False
    chat_monitoring: bool = False
    agents_active: int = 0
    last_activity: Optional[datetime] = None

class YouTubeProxy:
    """
    YouTube Proxy: Cross-Domain Component Orchestrator
    
    WSP-COMPLIANT ORCHESTRATION HUB that coordinates YouTube functionality 
    across enterprise domains without duplicating module logic.
    
    Orchestrates:
    - platform_integration/ (auth, stream discovery)
    - communication/ (chat processing)  
    - ai_intelligence/ (banter responses)
    - infrastructure/ (agent management)
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None, config: Optional[Dict[str, Any]] = None, credentials: Optional[Any] = None):
        """Initialize with dependency injection support"""
        self.logger = logger or self._create_default_logger()
        self.config = config or {}
        self.credentials = credentials
        self.service = None
        
        # Core state
        self.status = ProxyStatus()
        self.current_stream: Optional[StreamInfo] = None
        self.active_components: Dict[str, Any] = {}
        
        # Initialize components (with fallbacks for standalone mode)
        self._initialize_components()
        
        self.logger.info("[U+1F3AC] YouTube Proxy initialized successfully")
    
    def _create_default_logger(self) -> logging.Logger:
        """Create default logger for standalone operation"""
        logger = logging.getLogger("YouTubeProxy")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - YouTubeProxy - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _initialize_components(self):
        """Initialize cross-domain components with fallbacks"""
        try:
            # Platform Integration Components
            self.oauth_manager = OAuthManager(platform="youtube", logger=self.logger)
            self.stream_resolver = StreamResolver(logger=self.logger)
            
            # Communication Components  
            self.chat_processor = LiveChatProcessor(logger=self.logger)
            
            # AI Intelligence Components
            self.banter_engine = BanterEngine(logger=self.logger)
            
            # Infrastructure Components
            self.agent_manager = AgentManager(logger=self.logger)
            
            self.logger.info("[OK] All enterprise domain components initialized")
            
        except Exception as e:
            self.logger.warning(f"[U+26A0]️  Using mock components for standalone mode: {e}")
            self._initialize_mock_components()
    
    def _initialize_mock_components(self):
        """Initialize mock components for standalone testing"""
        class MockComponent:
            def __init__(self, name: str, logger: logging.Logger):
                self.name = name
                self.logger = logger
                
            async def initialize(self): 
                self.logger.info(f"[TOOL] Mock {self.name} initialized")
                return True
                
            async def start(self): 
                self.logger.info(f"[U+25B6]️  Mock {self.name} started")
                return True
                
            async def stop(self): 
                self.logger.info(f"⏹️  Mock {self.name} stopped")
                return True
        
        self.oauth_manager = MockComponent("OAuthManager", self.logger)
        self.stream_resolver = MockComponent("StreamResolver", self.logger)
        self.chat_processor = MockComponent("LiveChatProcessor", self.logger)
        self.banter_engine = MockComponent("BanterEngine", self.logger)
        self.agent_manager = MockComponent("AgentManager", self.logger)
        
        self.logger.info("[TOOL] Mock components initialized for standalone mode")

    def find_active_livestream(self, channel_id: str) -> Optional[Tuple[str, str]]:
        """
        Find active livestream for a channel.
        WSP 48: Self-healing authentication with automatic token refresh.
        
        Returns:
            Tuple of (video_id, chat_id) if found, None otherwise
        """
        try:
            # Import stream resolver functions
            from modules.platform_integration.stream_resolver.src.stream_resolver import (
                get_active_livestream_video_id_enhanced,
                get_authenticated_service_with_fallback
            )
            
            # WSP 48: Self-healing - Try to get authenticated service
            self.logger.info("[INFO] Attempting to find active livestream...")
            
            # First try with provided credentials
            if self.credentials:
                # Use existing credentials
                from googleapiclient.discovery import build
                self.service = build('youtube', 'v3', credentials=self.credentials)
            else:
                # WSP 48: Self-heal by getting new authentication
                self.logger.info("[INFO] No credentials provided, attempting self-healing auth...")
                auth_result = get_authenticated_service_with_fallback()
                
                if auth_result:
                    self.service, self.credentials, credential_set = auth_result
                    self.logger.info(f"[OK] Self-healed authentication with {credential_set}")
                else:
                    # Try to refresh tokens automatically
                    self.logger.warning("[WARN] Authentication failed, attempting token refresh...")
                    if self._auto_refresh_tokens():
                        # Retry authentication
                        auth_result = get_authenticated_service_with_fallback()
                        if auth_result:
                            self.service, self.credentials, credential_set = auth_result
                            self.logger.info(f"[OK] Authentication successful after token refresh")
                        else:
                            self.logger.error("[ERROR] Authentication failed even after token refresh")
                            return None
                    else:
                        self.logger.error("[ERROR] Could not refresh tokens")
                        return None
            
            # Now use stream resolver to find livestream
            if self.service:
                result = get_active_livestream_video_id_enhanced(self.service, channel_id)
                if result:
                    video_id, chat_id = result
                    self.logger.info(f"[OK] Found active livestream: {video_id[:8]}...")
                    return result
                else:
                    self.logger.info("[INFO] No active livestream found")
                    return None
            else:
                self.logger.error("[ERROR] No YouTube service available")
                return None
                
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to find livestream: {e}")
            return None
    
    def _auto_refresh_tokens(self) -> bool:
        """
        WSP 48: Automatic token refresh for self-healing
        """
        try:
            import os
            import json
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            
            CREDENTIALS_DIR = "credentials"
            TOKEN_FILES = ["oauth_token.json", "oauth_token2.json", "oauth_token3.json", "oauth_token4.json"]
            SCOPES = [
                "https://www.googleapis.com/auth/youtube.force-ssl",
                "https://www.googleapis.com/auth/youtube.readonly"
            ]
            
            refreshed_any = False
            
            for token_file in TOKEN_FILES:
                token_path = os.path.join(CREDENTIALS_DIR, token_file)
                
                if os.path.exists(token_path):
                    try:
                        with open(token_path, 'r', encoding="utf-8") as f:
                            creds_data = json.load(f)
                        
                        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
                        
                        if creds and creds.refresh_token:
                            try:
                                creds.refresh(Request())
                                
                                # Save refreshed token
                                with open(token_path, 'w', encoding="utf-8") as f:
                                    f.write(creds.to_json())
                                
                                self.logger.info(f"[OK] Auto-refreshed token: {token_file}")
                                refreshed_any = True
                                break  # One successful refresh is enough
                                
                            except Exception as refresh_error:
                                if 'invalid_grant' in str(refresh_error):
                                    self.logger.warning(f"[WARN] Token {token_file} expired, needs reauth")
                                else:
                                    self.logger.error(f"[ERROR] Failed to refresh {token_file}: {refresh_error}")
                    except Exception as e:
                        self.logger.error(f"[ERROR] Could not load {token_file}: {e}")
            
            return refreshed_any
            
        except Exception as e:
            self.logger.error(f"[ERROR] Auto-refresh failed: {e}")
            return False

    async def connect_to_active_stream(self) -> Optional[StreamInfo]:
        """
        WSP-COMPLIANT ORCHESTRATION: Connect to active YouTube stream 
        by delegating to appropriate domain modules
        """
        try:
            self.logger.info("[SEARCH] Orchestrating stream connection across domains...")
            
            # 1. Authenticate via infrastructure domain
            if hasattr(self.oauth_manager, 'authenticate'):
                await self.oauth_manager.authenticate()
            
            # 2. Discover streams via platform_integration domain  
            if hasattr(self.stream_resolver, 'find_active_streams'):
                streams = await self.stream_resolver.find_active_streams()
                if streams:
                    self.current_stream = streams[0]
            
            # 3. Connect to chat via communication domain
            if self.current_stream and hasattr(self.chat_processor, 'connect'):
                await self.chat_processor.connect(self.current_stream.stream_id)
            
            # 4. Enable AI responses via ai_intelligence domain
            if hasattr(self.banter_engine, 'initialize_context'):
                await self.banter_engine.initialize_context(self.current_stream)
            
            self.status.stream_active = True
            self.status.chat_monitoring = True
            self.logger.info(f"[OK] Connected to stream: {self.current_stream.title if self.current_stream else 'Mock Stream'}")
            
            return self.current_stream
            
        except Exception as e:
            self.logger.error(f"[FAIL] Stream connection failed: {e}")
            return None

    async def run_standalone(self):
        """Run YouTube proxy in standalone mode for testing"""
        self.logger.info("[ROCKET] Starting YouTube Proxy in standalone mode...")
        
        try:
            # Initialize all components
            await self._initialize_all_components()
            
            # Start orchestration
            stream = await self.connect_to_active_stream()
            
            # Keep alive for interaction
            await self._interactive_mode()
            
        except KeyboardInterrupt:
            self.logger.info("[STOP] Shutting down YouTube Proxy...")
            await self._cleanup()
        except Exception as e:
            self.logger.error(f"[FAIL] Standalone execution failed: {e}")
            raise
    
    async def _initialize_all_components(self):
        """Initialize all cross-domain components"""
        components = [
            ('oauth_manager', self.oauth_manager),
            ('stream_resolver', self.stream_resolver),
            ('chat_processor', self.chat_processor),
            ('banter_engine', self.banter_engine),
            ('agent_manager', self.agent_manager)
        ]
        
        for name, component in components:
            try:
                if hasattr(component, 'initialize'):
                    await component.initialize()
                self.active_components[name] = component
                self.logger.info(f"[OK] {name} ready")
            except Exception as e:
                self.logger.warning(f"[U+26A0]️  {name} initialization failed: {e}")
    
    async def _interactive_mode(self):
        """Interactive mode for standalone testing"""
        print("\n[U+1F3AC] YouTube Proxy Interactive Mode")
        print("Available commands:")
        print("  1. status     - Show current status")
        print("  2. stream     - Show stream info")
        print("  3. components - List active components")
        print("  4. connect    - Connect to stream")
        print("  5. quit       - Exit")
        print("\nEnter command number (1-5) or command name:")
        print("Press Ctrl+C or type '5' or 'quit' to exit\n")
        
        while True:
            try:
                cmd = input("YouTubeProxy> ").strip().lower()
                
                # Handle numbered inputs
                if cmd == "1" or cmd == "status":
                    await self._show_status()
                elif cmd == "2" or cmd == "stream":
                    await self._show_stream_info()
                elif cmd == "3" or cmd == "components":
                    await self._show_components()
                elif cmd == "4" or cmd == "connect":
                    await self.connect_to_active_stream()
                elif cmd == "5" or cmd == "quit":
                    break
                elif cmd == "":
                    continue
                else:
                    print(f"[FAIL] Unknown command: {cmd}")
                    print("[IDEA] Use numbers 1-5 or command names (status, stream, components, connect, quit)")
                    
            except EOFError:
                break
    
    async def _show_status(self):
        """Show current proxy status"""
        print(f"\n[DATA] YouTube Proxy Status:")
        print(f"  Stream Active: {'[OK]' if self.status.stream_active else '[FAIL]'}")
        print(f"  Chat Monitoring: {'[OK]' if self.status.chat_monitoring else '[FAIL]'}")
        print(f"  Active Components: {len(self.active_components)}")
        print()
    
    async def _show_stream_info(self):
        """Show current stream information"""
        if self.current_stream:
            print(f"\n[U+1F3AC] Stream Information:")
            print(f"  ID: {self.current_stream.stream_id}")
            print(f"  Title: {self.current_stream.title}")
            print(f"  Status: {self.current_stream.status}")
            print(f"  Viewers: {self.current_stream.viewer_count}")
            print()
        else:
            print("No active stream")
    
    async def _show_components(self):
        """Show active components across domains"""
        print(f"\n[U+1F9E9] Active Components ({len(self.active_components)}):")
        for name, component in self.active_components.items():
            print(f"  • {name}: {type(component).__name__}")
        print()
    
    async def _cleanup(self):
        """Cleanup resources"""
        self.logger.info("[U+1F9F9] Cleaning up resources...")
        
        for name, component in self.active_components.items():
            try:
                if hasattr(component, 'stop'):
                    await component.stop()
                self.logger.info(f"[OK] {name} stopped")
            except Exception as e:
                self.logger.warning(f"[U+26A0]️  {name} cleanup failed: {e}")

def create_youtube_proxy(credentials: Optional[Any] = None, config: Optional[Dict[str, Any]] = None) -> YouTubeProxy:
    """
    Factory function to create YouTubeProxy instance.
    
    Args:
        credentials: YouTube API credentials (optional)
        config: Configuration for proxy and components
        
    Returns:
        YouTubeProxy: Configured proxy instance
    """
    return YouTubeProxy(config=config, credentials=credentials)

if __name__ == "__main__":
    """Standalone execution entry point"""
    async def main():
        proxy = YouTubeProxy()
        await proxy.run_standalone()
    
    asyncio.run(main()) 