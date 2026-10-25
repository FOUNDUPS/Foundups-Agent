"""Turn the public GitHub nomination form into an advisory review artifact.

The trusted workflow host supplies a fixed nomination-service context, separately
from issue data. Session/invite verification remains the sole HTTP intake context
provider. This separate CLI bootstrap permits draft construction only; it does not
authenticate a GitHub user, an owner, a session or an execution entitlement.

The adapter never derives context from event fields or serializes it. Local replay
is allowed and always labelled unverified; JSON cannot attest hosted execution.
The actual Actions run supplies external provenance. No application network calls,
project checkout, registry, worker, ownership or token operations occur here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from modules.foundups.agent.src.kanban_plugin_contract import redact_sensitive
from .launch_request import LaunchRequest, LaunchRequestIntakeContext, to_genesis_envelope
from .validator import _contains_disallowed_display_char

_REPOSITORY = "FOUNDUPS/Foundups-Agent"
_REPOSITORY_ID = 956651858
_SERVICE = "github_nomination_review_service"
_HEADINGS = ("Project name", "Public project URL", "Outcome", "Solution, when known",
             "Pain or obstacles, when known", "Public submission")
_CAPS = (120, 2048, 4000, 6000, 4000)
_CONSENT = ("- [X] I am submitting only public information, with no credentials, "
            "secrets or private project material.")
_MAX_EVENT_BYTES = 256 * 1024


class NominationReviewError(ValueError):
    """Safe, low-cardinality rejection; never carries parsed input."""


def _reject() -> None:
    raise NominationReviewError("invalid_nomination")


def _mapping(value: object) -> dict:
    if type(value) is not dict:
        _reject()
    return value


def _positive_id(value: object) -> int:
    if type(value) is not int or not 0 < value < 2**63:
        _reject()
    return value


def _form_values(body: object) -> list[str]:
    if type(body) is not str or len(body.encode("utf-8")) > 16384:
        _reject()
    normalized = body.replace("\r\n", "\n")
    if _contains_disallowed_display_char(normalized.replace("\n", "")):
        _reject()
    pieces = re.split(r"(?m)^### ([^\n]+)\n", normalized.strip(" \n"))
    if pieces[0] or tuple(pieces[1::2]) != _HEADINGS:
        _reject()
    values = [part.strip(" \n") for part in pieces[2::2]]
    if len(values) != len(_HEADINGS):
        _reject()
    if any(len(value) > cap for value, cap in zip(values, _CAPS)):
        _reject()
    if any(value in ("", "_No response_") for value in values[:3]):
        _reject()
    if values[5] not in (_CONSENT, _CONSENT.replace("[X]", "[x]")):
        _reject()
    return values


def _project_reference(value: str) -> str:
    """Syntactic metadata only; this is not a public-host fetch allowlist."""
    parsed = urlsplit(value)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or any(char.isspace() for char in value)
            or redact_sensitive(value) != value):
        _reject()
    # Force validation of malformed port syntax without making a connection.
    parsed.port
    return value


def _event_source(event: object) -> tuple[dict, dict, dict]:
    data = _mapping(event)
    repository = _mapping(data.get("repository"))
    if (data.get("action") != "opened"
            or _positive_id(repository.get("id")) != _REPOSITORY_ID
            or repository.get("full_name") != _REPOSITORY
            or repository.get("private") is not False):
        _reject()
    issue = _mapping(data.get("issue"))
    author = _mapping(issue.get("user"))
    sender = _mapping(data.get("sender"))
    number = _positive_id(issue.get("number"))
    _positive_id(issue.get("id"))
    author_id = _positive_id(author.get("id"))
    login = author.get("login")
    if ("pull_request" in issue or _positive_id(sender.get("id")) != author_id
            or type(login) is not str
            or re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", login) is None
            or type(issue.get("title")) is not str
            or not issue["title"].startswith("[FoundUp nomination] ")
            or issue.get("html_url") != f"https://github.com/{_REPOSITORY}/issues/{number}"):
        _reject()
    return repository, issue, author


def review_nomination_event(
    event: object, *, context: LaunchRequestIntakeContext | None = None,
) -> dict:
    """Consume an opened-issue snapshot with an explicit draft-service context."""
    try:
        if (not isinstance(context, LaunchRequestIntakeContext)
                or context.authenticated is not True
                or context.invite_token_verified is not False
                or context.requester_handle != _SERVICE):
            _reject()
        repository, issue, author = _event_source(event)
        values = _form_values(issue.get("body"))
        reference = _project_reference(values[1])
        envelope = to_genesis_envelope(LaunchRequest(
            proposed_name=values[0], reference_urls=[reference]), context)
        brief = dict(zip(("outcome", "solution", "pain"), (
            redact_sensitive(value) if value not in ("", "_No response_") else None
            for value in values[2:5])))
        return {"status": "DRAFT_ONLY", "pitch_brief": brief,
                "genesis_envelope": envelope.to_dict(), "source": {
                    "repository_id": repository["id"], "repository_full_name": _REPOSITORY,
                    "issue_id": issue["id"], "issue_number": issue["number"],
                    "issue_url": issue["html_url"], "nominator_id": author["id"],
                    "nominator_login": author["login"],
                    "body_sha256": hashlib.sha256(issue["body"].encode("utf-8")).hexdigest(),
                    "provenance": "unverified_event_replay"}}
    except (KeyError, TypeError, ValueError, AttributeError):
        raise NominationReviewError("invalid_nomination") from None


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _reject()
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    _reject()


def _read_event(path: str) -> object:
    with Path(path).open("rb") as handle:
        raw = handle.read(_MAX_EVENT_BYTES + 1)
    if len(raw) > _MAX_EVENT_BYTES:
        _reject()
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                      parse_constant=_reject_json_constant)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an unverified nomination review draft.")
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args(argv)
    try:
        # Host-owned review service identity; never populated from event/body data.
        context = LaunchRequestIntakeContext(authenticated=True, requester_handle=_SERVICE)
        try:
            artifact = review_nomination_event(_read_event(args.event_path), context=context)
        except (ValueError, UnicodeError, RecursionError):
            artifact = {"status": "NEEDS_MANUAL_REVIEW", "reason": "invalid_nomination"}
        with Path(args.output_path).open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(artifact, handle, ensure_ascii=True, allow_nan=False, indent=2)
            handle.write("\n")
    except OSError:
        print("nomination_review_io_error", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
