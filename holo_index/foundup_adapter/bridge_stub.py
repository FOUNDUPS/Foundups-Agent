"""
Shell bridge interceptor Python adapter stub.
"""
import json

class BridgeStub:
    def __init__(self):
        self.last_request = None

    def sendMessage(self, payload_str):
        self.last_request = json.loads(payload_str)
        
        # Parse the request
        route = self.last_request.get("route")
        payload = self.last_request.get("payload", {})
        action = payload.get("action")
        
        # Simulate response
        if route == "openclaw_search" and action == "semantic_search":
            query = payload.get("query", "")
            return json.dumps({
                "results": [
                    {
                        "content": f"[Bridge Backend] Simulated backend response for: {query}",
                        "path": "backend_stub/result.md",
                        "relevance": 0.99
                    }
                ],
                "quantum_coherence": 0.95,
                "stub": True,
                "source": "python_bridge_stub"
            })
            
        return json.dumps({"error": "Unknown route or action"})
