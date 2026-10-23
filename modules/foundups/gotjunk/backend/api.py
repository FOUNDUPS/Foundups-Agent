"""
GotJunk Backend API - Liberty Alert Integration
Thin FastAPI wrapper that imports existing Liberty Alert modules (WSP 3 compliant)
NO vibecoding - reuses modules/communication/liberty_alert/src/
"""

import sys
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import os
from modules.foundups.gotjunk.backend.security import BodyLimitMiddleware, require_writer
from datetime import datetime

# Optional PatternMemory for learned false positives (WSP 48/60)
try:
    from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory
    PATTERN_MEMORY_AVAILABLE = True
except Exception:
    PATTERN_MEMORY_AVAILABLE = False

# Add parent directory to path for module imports
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(repo_root))

# Import EXISTING Liberty Alert modules (NO vibecoding!)
try:
    from modules.communication.liberty_alert.src.mesh_network import MeshNetwork
    from modules.communication.liberty_alert.src.models import Alert, GeoPoint, ThreatType
    from modules.communication.liberty_alert.src.alert_broadcaster import AlertBroadcaster
except ImportError as e:
    print(f"Warning: Liberty Alert modules not fully available: {e}")
    print("Running in mock mode for development")

    # Mock classes for development (will be replaced by actual imports)
    class GeoPoint:
        def __init__(self, latitude: float, longitude: float, accuracy: float = 10.0):
            self.latitude = latitude
            self.longitude = longitude
            self.accuracy = accuracy

    class ThreatType:
        ICE_RAID = "ice_raid"
        CHECKPOINT = "checkpoint"
        IMMIGRATION = "immigration"

    class Alert:
        def __init__(self, id: str, location: GeoPoint, message: str, video_url: Optional[str] = None,
                     threat_type: str = ThreatType.ICE_RAID, verified: bool = False, timestamp: int = None):
            self.id = id
            self.location = location
            self.message = message
            self.video_url = video_url
            self.threat_type = threat_type
            self.verified = verified
            self.timestamp = timestamp or int(datetime.now().timestamp() * 1000)

        def dict(self):
            return {
                "id": self.id,
                "location": {"latitude": self.location.latitude, "longitude": self.location.longitude},
                "message": self.message,
                "video_url": self.video_url,
                "threat_type": self.threat_type,
                "verified": self.verified,
                "timestamp": self.timestamp
            }

    class AlertBroadcaster:
        def __init__(self):
            self.alerts = []

        def get_recent_alerts(self):
            return self.alerts

        async def broadcast(self, alert: Alert):
            self.alerts.insert(0, alert)
            return True

    class MeshNetwork:
        def __init__(self):
            pass

app = FastAPI(title="GotJunk Liberty Alert API")

# Initialize PatternMemory (best-effort, non-fatal)
pattern_memory: Optional[Any] = None
if PATTERN_MEMORY_AVAILABLE:
    try:
        pattern_memory = PatternMemory()
    except Exception:
        pattern_memory = None

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.environ.get("GOTJUNK_ALLOWED_ORIGINS", "").split(",") if origin.strip() and origin.strip() != "*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(BodyLimitMiddleware)

# Initialize Liberty Alert backend (reusing EXISTING modules)
try:
    mesh = MeshNetwork()
    broadcaster = AlertBroadcaster()
except Exception as e:
    print(f"Using mock broadcaster: {e}")
    broadcaster = AlertBroadcaster()

# Pydantic models for API
class AlertCreate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    message: str = Field(min_length=1, max_length=4000)
    video_url: Optional[str] = Field(default=None, max_length=2048)

class AlertResponse(BaseModel):
    id: str
    location: dict
    message: str
    video_url: Optional[str]
    timestamp: int


def _should_skip(task_key: str) -> Optional[Dict[str, Any]]:
    """
    Check PatternMemory for learned false positives (best-effort).
    """
    if not pattern_memory:
        return None
    try:
        return pattern_memory.get_false_positive_reason("gotjunk_task", task_key)
    except Exception:
        return None


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "gotjunk-liberty-alert"}

@app.get("/api/liberty/alerts", response_model=List[AlertResponse])
async def get_alerts():
    """
    Get recent Liberty Alerts
    Uses EXISTING AlertBroadcaster.get_recent_alerts() - NO vibecoding!
    """
    alerts = broadcaster.get_recent_alerts()
    return [a.dict() for a in alerts]

@app.post("/api/liberty/alert")
async def post_alert(alert_data: AlertCreate, writer: str = Depends(require_writer)):
    """
    Create new Liberty Alert
    Uses EXISTING Alert model and AlertBroadcaster - NO vibecoding!
    """
    skip = _should_skip("create_liberty_alert")
    if skip:
        return {
            "success": True,
            "skipped": True,
            "reason": skip.get("reason"),
            "actual_location": skip.get("actual_location")
        }

    # Use EXISTING GeoPoint and Alert models
    location = GeoPoint(alert_data.latitude, alert_data.longitude)
    alert = Alert(
        id=f"alert-{datetime.now().timestamp()}",
        location=location,
        message=alert_data.message,
        video_url=alert_data.video_url,
        threat_type=ThreatType.ICE_RAID,
        verified=False,
        timestamp=int(datetime.now().timestamp() * 1000)
    )

    # Use EXISTING AlertBroadcaster.broadcast()
    await broadcaster.broadcast(alert)

    return {"success": True, "alert_id": alert.id}

@app.post("/api/liberty/alert/video")
async def upload_alert_video(file: UploadFile = File(...), latitude: float = 0.0, longitude: float = 0.0, writer: str = Depends(require_writer)):
    """
    Upload video for Liberty Alert
    TODO: Implement video storage (Cloud Storage bucket)
    """
    skip = _should_skip("upload_liberty_alert_video")
    if skip:
        return {
            "success": True,
            "skipped": True,
            "reason": skip.get("reason"),
            "actual_location": skip.get("actual_location")
        }

    # TODO: Upload to Cloud Storage
    # video_url = await upload_to_cloud_storage(file)

    video_url = f"/videos/{file.filename}"  # Placeholder

    location = GeoPoint(latitude, longitude)
    alert = Alert(
        id=f"alert-{datetime.now().timestamp()}",
        location=location,
        message="ICE Alert (video)",
        video_url=video_url,
        threat_type=ThreatType.ICE_RAID,
        verified=False,
        timestamp=int(datetime.now().timestamp() * 1000)
    )

    await broadcaster.broadcast(alert)

    return {"success": True, "alert_id": alert.id, "video_url": video_url}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
