"""
Log Follower for 0102 Multi-Agent Coordination
WSP 48 Recursive Learning - Allows agents to follow DBA entries in real-time

This utility allows 012 and other 0102_HOLO_ID agents to follow the unified
agent activity log in real-time, seeing HoloIndex searches, Qwen analysis,
breadcrumb activities, and 0102 decisions as they happen.
"""

import time
import os
from pathlib import Path
from typing import Set, Optional

class LogFollower:
    """Follows the unified agent log stream in real-time."""

    def __init__(self, agent_id: str = "LOG-FOLLOWER", log_file: str = "holo_index/logs/unified_agent_activity.log"):
        resolved = agent_id or os.getenv("HOLO_ID_0102") or os.getenv("0102_HOLO_ID") or os.getenv("HOLO_AGENT_ID")
        self.agent_id = resolved if resolved else "LOG-FOLLOWER"
        self.log_file = Path(log_file)
        self.last_position = 0
        self.following = False

    def follow_logs(self, follow: bool = True):
        """Follow the unified log stream in real-time."""
        if not self.log_file.exists():
            print(f"[LOG-FOLLOWER] Waiting for log file: {self.log_file}")
            return

        print(f"[LOG-FOLLOWER] Following unified agent activity stream...")
        print(f"[LOG-FOLLOWER] Agent ID: {self.agent_id}")

        self.following = follow
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # Start from end if following, or read all existing content
                if follow:
                    f.seek(0, 2)  # Seek to end
                    self.last_position = f.tell()
                else:
                    content = f.read()
                    if content:
                        print("[LOG-FOLLOWER] === EXISTING LOGS ===")
                        print(content)
                        print("[LOG-FOLLOWER] === END EXISTING LOGS ===")

                if follow:
                    print(f"[LOG-FOLLOWER] Following live activity (Ctrl+C to stop)...")
                    while self.following:
                        line = f.readline()
                        if line:
                            self._process_log_line(line.strip())
                        else:
                            time.sleep(0.1)  # Small delay to avoid busy waiting

        except KeyboardInterrupt:
            print(f"\n[LOG-FOLLOWER] Stopped following logs")
        except Exception as e:
            print(f"[LOG-FOLLOWER] Error following logs: {e}")

    def _process_log_line(self, line: str):
        """Process a log line and highlight important agent activities."""
        if not line.strip():
            return

        # Extract agent ID from log line format: [TIMESTAMP] [AGENT_ID] message
        try:
            parts = line.split('] [', 2)
            if len(parts) >= 3:
                timestamp = parts[0].replace('[', '')
                agent_id = parts[1]
                message = parts[2].replace(']', '', 1)

                # Highlight different types of agent activities
                if 'HOLO-SEARCH' in agent_id:
                    print(f"[SEARCH] {timestamp} | {agent_id} | {message}")
                elif 'BREADCRUMB' in agent_id:
                    print(f"[U+1F9F5] {timestamp} | {agent_id} | {message}")
                elif 'QWEN' in agent_id:
                    print(f"[AI] {timestamp} | {agent_id} | {message}")
                elif '0102' in agent_id:
                    print(f"[TARGET] {timestamp} | {agent_id} | {message}")
                else:
                    print(f"[NOTE] {timestamp} | {agent_id} | {message}")

        except:
            # Fallback for malformed lines
            print(f"[NOTE] {line}")

def follow_agent_logs(agent_id: str = "012-FOLLOWER"):
    """Convenience function to follow agent logs."""
    follower = LogFollower(agent_id)
    follower.follow_logs()

if __name__ == "__main__":
    # Allow custom agent ID via environment variable
    agent_id = os.getenv("HOLO_ID_0102") or os.getenv("0102_HOLO_ID") or os.getenv("HOLO_AGENT_ID") or "LOG-FOLLOWER"
    follow_agent_logs(agent_id)
