"""Small HTTPS client. No POST retries, redirects or raw provider error logging."""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ProviderError(RuntimeError):
    """Provider operation failed; POST outcome may still be uncertain."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ElevenLabsClient:
    def __init__(self, api_key: str, opener=None):
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY is missing")
        self._key = api_key
        self._opener = opener or build_opener(_NoRedirect())

    def request(self, method: str, path: str, payload=None) -> dict:
        if not re.fullmatch(r"/convai/[A-Za-z0-9_/-]+", path):
            raise ValueError("Invalid provider path")
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        request = Request("https://api.elevenlabs.io/v1" + path, data=body,
                          headers={"xi-api-key": self._key, "Content-Type": "application/json"},
                          method=method)
        try:
            with self._opener.open(request, timeout=30) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProviderError("Provider response exceeded size limit")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ProviderError("Provider response is not an object")
            return result
        except HTTPError as exc:
            raise ProviderError(f"Provider HTTP {exc.code}; inspect its console before retrying a call") from None
        except (URLError, OSError, ValueError) as exc:
            raise ProviderError("Provider transport or JSON failure; call outcome may be unknown") from None

    def agent(self, agent_id: str) -> dict:
        return self.request("GET", "/convai/agents/" + _identifier(agent_id))

    def create_agent(self, config: dict) -> dict:
        return self.request("POST", "/convai/agents/create", config)

    def call(self, payload: dict) -> dict:
        return self.request("POST", "/convai/twilio/outbound-call", payload)

    def conversation(self, conversation_id: str) -> dict:
        return self.request("GET", "/convai/conversations/" + _identifier(conversation_id))


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("Invalid provider identifier")
    return value
