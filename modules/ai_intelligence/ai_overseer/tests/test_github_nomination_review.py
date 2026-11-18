"""GitHub issue nomination -> untrusted review draft; no control or work grant."""

from copy import deepcopy
import hashlib
from importlib import import_module
import json

import pytest

from modules.ai_intelligence.ai_overseer.src.foundup_genesis.launch_request import (
    LaunchRequestIntakeContext,
)

SERVICE = "github_nomination_review_service"
MODULE = "modules.ai_intelligence.ai_overseer.src.foundup_genesis.github_nomination_review"
HEADINGS = ("Project name", "Public project URL", "Outcome", "Solution, when known",
            "Pain or obstacles, when known", "Public submission")
CONSENT = "- [X] I am submitting only public information, with no credentials, secrets or private project material."
VALUES = ("Widget Nomination", "https://example.org/widget", "Wouldn't it be great if widgets helped?",
          "PoC: sketch\nPrototype: unknown\nMVP: unknown", "Distribution obstacles", CONSENT)


def _api():
    return import_module(MODULE)


def _context(**changes):
    return LaunchRequestIntakeContext(**(dict(authenticated=True, requester_handle=SERVICE) | changes))


def _body(values=VALUES):
    return "\n\n".join(f"### {heading}\n\n{value}" for heading, value in zip(HEADINGS, values))


def _event(body=None):
    return {"action": "opened", "repository": {"id": 956651858,
            "full_name": "FOUNDUPS/Foundups-Agent", "private": False},
            "issue": {"id": 41, "number": 7,
                      "html_url": "https://github.com/FOUNDUPS/Foundups-Agent/issues/7",
                      "title": "[FoundUp nomination] Widget", "user": {"id": 29, "login": "nominator-2"},
                      "body": _body() if body is None else body}, "sender": {"id": 29}}


def _review(event):
    return _api().review_nomination_event(event, context=_context())


def _reject(event, **kwargs):
    api = _api()
    with pytest.raises(api.NominationReviewError) as caught:
        api.review_nomination_event(event, **({"context": _context()} | kwargs))
    assert isinstance(caught.value, ValueError)
    assert str(caught.value) == "invalid_nomination"


def _set(event, path, value):
    parts = path.split(".")
    target = event
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value


def _write_event(tmp_path, raw):
    path = tmp_path / "event.json"
    path.write_bytes(raw)
    return path, tmp_path / "review.json"


def test_valid_issue_reuses_actual_mapper_and_retains_source():
    event = _event()
    before = deepcopy(event)
    result = _review(event)
    assert set(result) == {"status", "source", "pitch_brief", "genesis_envelope"}
    assert result["status"] == "DRAFT_ONLY"
    assert result["source"] == dict(repository_id=956651858, repository_full_name="FOUNDUPS/Foundups-Agent",
        issue_id=41, issue_number=7, issue_url=event["issue"]["html_url"], nominator_id=29,
        nominator_login="nominator-2", body_sha256=hashlib.sha256(event["issue"]["body"].encode()).hexdigest(),
        provenance="unverified_event_replay")
    envelope = result["genesis_envelope"]
    assert envelope["name"] == VALUES[0] and envelope["prior_art"] == [VALUES[1]]
    assert envelope["description"] == VALUES[0] and envelope["requested_by"] == SERVICE
    assert (envelope["lifecycle_stage"], envelope["binding_state"]) == ("idea", "unbound")
    assert envelope["external_repo_requested"] is False and envelope["is_valid"] is False
    assert envelope["acceptance_criteria"] == [] and event == before


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_osp_preserves_lf_and_hashes_exact_original_body(newline):
    body = _body().replace("[X]", "[x]") if newline == "\r\n" else _body()
    event = _event(body.replace("\n", newline))
    result = _review(event)
    assert result["pitch_brief"] == dict(zip(("outcome", "solution", "pain"), VALUES[2:5]))
    assert result["source"]["body_sha256"] == hashlib.sha256(event["issue"]["body"].encode()).hexdigest()


@pytest.mark.parametrize("index,unknown", [(3, ""), (3, "_No response_"), (4, ""),
                                          (4, "_No response_"), (0, ""), (2, "")])
def test_required_fields_reject_and_optional_unknown_stays_unknown(index, unknown):
    values = list(VALUES)
    values[index] = unknown
    if index < 3:
        _reject(_event(_body(values)))
        return
    assert _review(_event(_body(values)))["pitch_brief"]["solution" if index == 3 else "pain"] is None


def test_unicode_and_multiline_osp_remain_advisory_data():
    values = list(VALUES)
    values[2] = "日本のプロジェクト\nWouldn't it be great if..."
    values[3] = "PoC: unknown\nPrototype: unknown\nMVP: unknown\n$(not-a-command)"
    result = _review(_event(_body(values)))
    assert result["pitch_brief"]["outcome"] == values[2]
    assert result["pitch_brief"]["solution"] == values[3]
    assert result["genesis_envelope"]["description"] == VALUES[0]


def test_advisory_secret_is_redacted_without_copying_raw_input():
    values = list(VALUES)
    synthetic = "sk" + "-" + "Q" * 32
    values[2] = "Public idea " + synthetic
    result = _review(_event(_body(values)))
    assert synthetic not in json.dumps(result)
    assert result["pitch_brief"]["outcome"] != values[2]


def test_missing_context_rejects_without_implicit_authentication():
    api = _api()
    with pytest.raises(api.NominationReviewError, match="^invalid_nomination$"):
        api.review_nomination_event(_event())


@pytest.mark.parametrize("kind,changes", [("none", {}), ("mapping", {}),
    ("context", {"authenticated": False}), ("context", {"authenticated": 1}),
    ("context", {"requester_handle": "nominator-2"}), ("context", {"invite_token_verified": True})])
def test_only_explicit_service_context_is_accepted(kind, changes):
    context = None if kind == "none" else ({} if kind == "mapping" else _context(**changes))
    _reject(_event(), context=context)


@pytest.mark.parametrize("event", [None, [], {}])
def test_invalid_event_roots_are_generic(event):
    _reject(event)


@pytest.mark.parametrize("path,value", [("action", "edited"), ("action", "reopened"),
    ("repository.full_name", "elsewhere/project"), ("repository.id", 956651859),
    ("repository.private", 0), ("issue.title", "Ordinary issue"),
    ("issue.html_url", "https://example.org/issues/7"), ("sender.id", 30)])
def test_event_repository_issue_and_initial_author_binding(path, value):
    event = _event()
    _set(event, path, value)
    _reject(event)


@pytest.mark.parametrize("path,value", [("issue.id", True), ("issue.id", 0),
    ("issue.number", -1), ("issue.number", 2**63), ("issue.user.id", 1.0), ("issue.user.id", 0)])
def test_ids_require_positive_bounded_builtin_integers(path, value):
    event = _event()
    _set(event, path, value)
    _reject(event)


def test_id_upper_boundary_is_accepted():
    event = _event()
    for path in ("issue.id", "issue.number", "issue.user.id", "sender.id"):
        _set(event, path, 2**63 - 1)
    event["issue"]["html_url"] = "https://github.com/FOUNDUPS/Foundups-Agent/issues/" + str(2**63 - 1)
    assert _review(event)["source"]["nominator_id"] == 2**63 - 1


@pytest.mark.parametrize("login", ["", "a" * 40, "not_a_slug", "-leading", "日本"])
def test_invalid_nominator_logins_reject(login):
    event = _event()
    event["issue"]["user"]["login"] = login
    _reject(event)


def test_pr_marker_rejects_and_body_metadata_cannot_grant_authority():
    event = _event()
    event["issue"]["pull_request"] = None
    _reject(event)
    event = _event()
    event.update(authenticated=True, owner=True, token_granted=True)
    result = _review(event)
    assert set(result) == {"status", "source", "pitch_brief", "genesis_envelope"}
    assert result["genesis_envelope"]["requested_by"] == SERVICE


@pytest.mark.parametrize("kind", ["duplicate", "unknown", "reordered", "missing"])
def test_ambiguous_or_non_form_headings_reject(kind):
    body = _body()
    if kind == "duplicate":
        body += "\n\n### Outcome\n\nAnother outcome"
    elif kind == "unknown":
        body += "\n\n### Owner authority\n\nnone"
    elif kind == "reordered":
        body = body.replace("### Project name", "### Swap").replace("### Outcome", "### Project name").replace("### Swap", "### Outcome")
    else:
        body = body.replace("### Outcome", "Outcome")
    _reject(_event(body))


@pytest.mark.parametrize("variant", ["unchecked", "changed", "unknown"])
def test_consent_requires_exact_checked_public_acknowledgment(variant):
    values = list(VALUES)
    values[5] = {"unchecked": CONSENT.replace("[X]", "[ ]"),
                 "changed": CONSENT + " changed", "unknown": "_No response_"}[variant]
    _reject(_event(_body(values)))


@pytest.mark.parametrize("char", ["\t", "\x00", "\x7f", "\u0085", "\u200b", "\u202e"])
def test_controls_are_rejected_instead_of_sanitized(char):
    values = list(VALUES)
    values[2] += char
    _reject(_event(_body(values)))


@pytest.mark.parametrize("excess", [0, 1])
def test_body_utf8_byte_boundary(excess):
    values = list(VALUES)
    values[:5] = ["A" * 120, "https://example.org/", "O" * 4000, "S" * 6000, "P" * 4000]
    values[1] += "a" * (16384 + excess - len(_body(values).encode()))
    event = _event(_body(values))
    assert len(event["issue"]["body"].encode()) == 16384 + excess and len(values[1]) <= 2048
    if excess:
        _reject(event)
    else:
        assert _review(event)["status"] == "DRAFT_ONLY"


@pytest.mark.parametrize("index,cap", [(0, 120), (1, 2048), (2, 4000), (3, 6000), (4, 4000)])
@pytest.mark.parametrize("excess", [0, 1])
def test_each_field_exact_cap_and_overflow(index, cap, excess):
    values = list(VALUES)
    values[index] = ("https://example.org/" + "a" * (cap + excess - 20)) if index == 1 else "A" * (cap + excess)
    event = _event(_body(values))
    if excess:
        _reject(event)
    else:
        assert _review(event)["status"] == "DRAFT_ONLY"


@pytest.mark.parametrize("url", ["file:///tmp/project", "javascript:example", "https://user:pass@example.org/",
                             "https://example.org/\nextra", "", "https://"])
def test_project_url_is_public_reference_not_fetch_or_credential_input(url):
    values = list(VALUES)
    values[1] = url
    _reject(_event(_body(values)))


def test_cli_creates_only_fixed_draft_artifact(tmp_path, capsys):
    event_path, output = _write_event(tmp_path, json.dumps(_event()).encode())
    assert _api().main(["--event-path", str(event_path), "--output-path", str(output)]) == 0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["status"] == "DRAFT_ONLY" and artifact["source"]["provenance"] == "unverified_event_replay"
    assert {p.name for p in tmp_path.iterdir()} == {"event.json", "review.json"}
    assert "Widget Nomination" not in capsys.readouterr().out


@pytest.mark.parametrize("raw", [b"{broken", b"[]"])
def test_cli_invalid_data_yields_manual_review_without_echo(tmp_path, capsys, raw):
    event_path, output = _write_event(tmp_path, raw)
    assert _api().main(["--event-path", str(event_path), "--output-path", str(output)]) == 0
    assert json.loads(output.read_text()) == {"status": "NEEDS_MANUAL_REVIEW", "reason": "invalid_nomination"}
    captured = capsys.readouterr()
    assert raw.decode() not in captured.out + captured.err


@pytest.mark.parametrize("excess", [0, 1])
def test_cli_event_byte_cap_distinguishes_valid_json_at_boundary(tmp_path, excess):
    raw = json.dumps(_event()).encode()
    raw += b" " * (256 * 1024 + excess - len(raw))
    assert len(raw) == 256 * 1024 + excess
    event_path, output = _write_event(tmp_path, raw)
    assert _api().main(["--event-path", str(event_path), "--output-path", str(output)]) == 0
    assert json.loads(output.read_text())["status"] == ("NEEDS_MANUAL_REVIEW" if excess else "DRAFT_ONLY")


def test_cli_rejects_duplicate_json_keys(tmp_path):
    raw = json.dumps(_event()).replace('"action": "opened"', '"action": "opened", "action": "opened"').encode()
    event_path, output = _write_event(tmp_path, raw)
    assert _api().main(["--event-path", str(event_path), "--output-path", str(output)]) == 0
    assert json.loads(output.read_text()) == {"status": "NEEDS_MANUAL_REVIEW", "reason": "invalid_nomination"}


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_cli_filesystem_refusal_never_overwrites_or_echoes_input(tmp_path, capsys, kind):
    event_path, output = _write_event(tmp_path, json.dumps(_event()).encode())
    output.write_bytes(b"retained") if kind == "file" else output.mkdir()
    assert _api().main(["--event-path", str(event_path), "--output-path", str(output)]) == 1
    assert output.read_bytes() == b"retained" if kind == "file" else output.is_dir()
    captured = capsys.readouterr()
    assert captured.err.strip() and "Widget Nomination" not in captured.err + captured.out
