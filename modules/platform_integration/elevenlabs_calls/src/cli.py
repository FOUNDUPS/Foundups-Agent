"""JSON-first local operator CLI. Calls are previews unless --execute is passed."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

from .client import ElevenLabsClient, ProviderError
from .config import agent_config
from .journal import CallJournal
from .request import CallRequest, read_object
from .service import MessageCaller
from .speech import is_call_trigger, listen_once


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="Report configuration presence without revealing credentials")
    setup = sub.add_parser("provision", help="Preview or create a dedicated ElevenLabs agent")
    setup.add_argument("--voice-id", required=True)
    call = sub.add_parser("call", help="Preview or submit one prepared Japanese message")
    call.add_argument("--request", required=True)
    call.add_argument("--contacts", required=True)
    call.add_argument("--listen", action="store_true", help="Require the spoken make-this-call trigger")
    call.add_argument("--language", choices=["en", "ja"], default="en")
    call.add_argument("--stt", choices=["whisper", "cohere"], default="whisper")
    status = sub.add_parser("status", help="Refresh one call's provider status, without redialing")
    status.add_argument("--request-id", required=True)
    for p in [doctor, setup, call, status]:
        p.add_argument("--json", action="store_true", help="Output is always JSON")
    for p in [setup, call]:
        mode = p.add_mutually_exclusive_group()
        mode.add_argument("--execute", action="store_true", help="Perform the requested external action")
        mode.add_argument("--dry-run", action="store_true", help="Preview only (default)")
    for p in [call, status]:
        p.add_argument("--journal", default=os.getenv(
            "FOUNDUPS_CALL_JOURNAL", str(Path.home() / ".local/share/foundups/phone_calls.sqlite3")))
    return root


def _client() -> ElevenLabsClient:
    return ElevenLabsClient(os.getenv("ELEVENLABS_API_KEY", ""))


def _run(args) -> dict:
    if args.command == "doctor":
        names = ["ELEVENLABS_API_KEY", "ELEVENLABS_AGENT_ID", "ELEVENLABS_PHONE_NUMBER_ID"]
        presence = {k: bool(os.getenv(k)) for k in names}
        return {"configuration_present": all(presence.values()), "environment": presence,
                "live_connection": "not_checked", "delivery": "not_tested"}
    if args.command == "provision":
        config = agent_config(args.voice_id)
        if not args.execute:
            return {"status": "preview", "agent_config": config}
        result = _client().create_agent(config)
        if not isinstance(result.get("agent_id"), str) or not result["agent_id"]:
            raise ProviderError("Agent creation response has no ID; inspect ElevenLabs before repeating")
        return {"status": "agent_created", "agent_id": result["agent_id"]}
    if args.command == "status":
        client = _client()
        journal = CallJournal(args.journal)
        # Status needs only the conversation ID already in the local journal.
        return MessageCaller(client, journal, "status-only", "status-only").status(args.request_id)
    request = CallRequest.resolve(read_object(args.request), read_object(args.contacts))
    if not args.execute:
        return {"status": "preview", "request": request.preview(), "delivery": "not_attempted"}
    client = _client()
    agent_id, phone_id = os.getenv("ELEVENLABS_AGENT_ID", ""), os.getenv("ELEVENLABS_PHONE_NUMBER_ID", "")
    if not agent_id or not phone_id:
        raise ValueError("ELEVENLABS_AGENT_ID and ELEVENLABS_PHONE_NUMBER_ID are required")
    if args.listen:
        print(json.dumps(request.preview(), ensure_ascii=False), file=sys.stderr)
        print('Say "make this call" or 「この電話をかけて」. Any other phrase cancels.', file=sys.stderr)
        if not is_call_trigger(listen_once(args.language, args.stt)):
            return {"status": "cancelled", "delivery": "not_attempted"}
    return MessageCaller(client, CallJournal(args.journal), agent_id, phone_id).submit(request)


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        data = _run(args)
        ok = data.get("status") not in {"rejected", "failed", "submission_unknown"}
        result = {"success": ok, "status": data.get("status", "checked"), "data": data, "error": None}
    except (ValueError, OSError, sqlite3.Error, ProviderError) as exc:
        result = {"success": False, "status": "error", "data": None, "error": str(exc)}
        ok = False
    except KeyboardInterrupt:
        result = {"success": False, "status": "interrupted", "data": None,
                  "error": "Interrupted; inspect journal/provider before any retry"}
        ok = False
    print(json.dumps(result, ensure_ascii=False))
    return 0 if ok else 1
