import sys
import os
from pathlib import Path

# Add repo root to path
repo_root = Path("o:/Foundups-Agent")
sys.path.insert(0, str(repo_root))

from modules.ai_intelligence.ai_overseer.src.openclaw_security_sentinel import OpenClawSecuritySentinel

def verify_sentinel():
    print("Initializing Sentinel...")
    sentinel = OpenClawSecuritySentinel(repo_root=repo_root)
    
    print("Running Security Check (Force Refesh)...")
    # Force check to bypass cache
    status = sentinel.check(force=True)
    
    print("--- Security Status ---")
    print(f"Passed: {status.get('passed')}")
    print(f"Message: {status.get('message')}")
    print(f"Exit Code: {status.get('exit_code')}")
    print(f"Open Ports: {status.get('open_ports')}")
    print(f"Risky Bindings: {status.get('risky_bindings')}")
    print("-----------------------")
    
    if status.get('open_ports') is None:
        print("FAIL: Port scan did not return a list")
        sys.exit(1)
        
    print("SUCCESS: Port scan logic executed")

if __name__ == "__main__":
    verify_sentinel()
