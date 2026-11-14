from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import scripts.refresh_openclaw_ecosystem_watchlist as watchlist_bridge

from modules.infrastructure.dependency_launcher.src.runtime_compatibility_evidence_supplier import (
    OFFICIAL_RELEASE_APIS,
    build_component_source_receipt,
    build_runtime_compatibility_supply,
    compose_runtime_compatibility_evidence,
    publish_runtime_compatibility_evidence,
)
from modules.infrastructure.dependency_launcher.src.runtime_compatibility_receipt import (
    INTEGRITY_ONLY,
    REQUIRED_COMPONENTS,
    build_runtime_compatibility_receipt,
    canonical_digest,
)
from scripts.refresh_openclaw_ecosystem_watchlist import (
    MAX_RELEASE_BYTES,
    fetch_official_release,
    publish_compatibility_evidence,
)


NOW = datetime(2026, 8, 2, 6, 30, tzinfo=timezone.utc)


def _source(component_id: str, *, role: str, kind: str, ref: str, now: datetime = NOW):
    return build_component_source_receipt(
        component_id=component_id,
        source_role=role,
        source_kind=kind,
        component_ref=ref,
        source_locator=f"receipt:{component_id}:{role.lower()}",
        source_payload_digest=canonical_digest({"component": component_id, "ref": ref}),
        observed_at_utc=now.isoformat(),
        expires_at_utc=(now + timedelta(days=1)).isoformat(),
    )


def _supply(*, now: datetime = NOW) -> dict[str, object]:
    observations = [
        _source(component_id, role="INSTALLED_OBSERVATION", kind="LOCAL_RUNTIME_OBSERVATION", ref=f"{component_id}-current", now=now)
        for component_id in REQUIRED_COMPONENTS
    ]
    expectations = [
        _source(component_id, role="EXPECTED_BINDING", kind="PROMOTED_RUNTIME_BINDING", ref=f"{component_id}-current", now=now)
        for component_id in ("qwen_general", "qwen_code", "inference_backend")
    ]
    return build_runtime_compatibility_supply(
        installed_observations=observations,
        promoted_expectations=expectations,
    )


def _release(component_id: str) -> dict[str, object]:
    repository = OFFICIAL_RELEASE_APIS[component_id].split("/repos/", 1)[1].split("/releases/", 1)[0]
    return {
        "tag_name": f"{component_id}-current",
        "html_url": f"https://github.com/{repository}/releases/tag/{component_id}-current",
        "published_at": (NOW - timedelta(hours=1)).isoformat(),
        "draft": False,
        "prerelease": False,
    }


def _releases() -> dict[str, dict[str, object]]:
    return {component_id: _release(component_id) for component_id in OFFICIAL_RELEASE_APIS}


def test_composer_emits_consumer_compatible_integrity_only_evidence() -> None:
    evidence = compose_runtime_compatibility_evidence(
        _supply(), upstream_releases=_releases(), now=NOW
    )
    receipt = build_runtime_compatibility_receipt(evidence, now=NOW)
    assert receipt.overall_state == "NOT_READY"
    assert receipt.reasons == ("evidence_authentication_not_verified",)
    assert {item.state for item in receipt.components} == {"OBSERVED_MATCH"}
    assert evidence["verification"] == INTEGRITY_ONLY
    assert len(evidence["source_receipt_ids"]) == 10
    assert evidence["evidence_receipt_id"] == canonical_digest(
        {key: value for key, value in evidence.items() if key != "evidence_receipt_id"}
    )


def test_upstream_drift_is_reported_without_update_action() -> None:
    releases = _releases()
    releases["openclaw"]["tag_name"] = "openclaw-newer"
    evidence = compose_runtime_compatibility_evidence(
        _supply(), upstream_releases=releases, now=NOW
    )
    receipt = build_runtime_compatibility_receipt(evidence, now=NOW)
    assert receipt.overall_state == "NOT_READY"
    openclaw = next(item for item in receipt.components if item.component_id == "openclaw")
    assert openclaw.state == "OBSERVED_DRIFT"
    assert openclaw.expected_ref == "openclaw-newer"


def test_attacker_recomputed_self_hashes_never_claim_current() -> None:
    supply = _supply()
    for key in ("installed_observations", "promoted_expectations"):
        for record in supply[key]:
            if record["component_id"] == "qwen_general":
                record["component_ref"] = "attacker-selected"
                record["receipt_id"] = canonical_digest(
                    {name: value for name, value in record.items() if name != "receipt_id"}
                )
    supply["supply_receipt_id"] = canonical_digest(
        {name: value for name, value in supply.items() if name != "supply_receipt_id"}
    )
    evidence = compose_runtime_compatibility_evidence(
        supply, upstream_releases=_releases(), now=NOW
    )
    receipt = build_runtime_compatibility_receipt(evidence, now=NOW)
    assert receipt.overall_state == "NOT_READY"
    assert "evidence_authentication_not_verified" in receipt.reasons


@pytest.mark.parametrize(
    "mutation",
    [
        lambda supply: supply["installed_observations"].pop(),
        lambda supply: supply["promoted_expectations"].pop(),
        lambda supply: supply["installed_observations"][0].update(component_ref="forged"),
        lambda supply: supply.update(verification="FAIL"),
        lambda supply: supply.update(ignored_but_signed="attacker"),
        lambda supply: supply["installed_observations"][0].update(ignored="attacker"),
    ],
)
def test_missing_or_tampered_supply_fails_closed(mutation) -> None:
    supply = _supply()
    mutation(supply)
    with pytest.raises(ValueError):
        compose_runtime_compatibility_evidence(supply, upstream_releases=_releases(), now=NOW)


def test_expired_source_and_unofficial_release_fail_closed() -> None:
    with pytest.raises(ValueError, match="source_receipt_expired"):
        compose_runtime_compatibility_evidence(
            _supply(now=NOW - timedelta(days=2)), upstream_releases=_releases(), now=NOW
        )
    releases = _releases()
    releases["hermes"]["html_url"] = "https://attacker.invalid/releases/tag/fake"
    with pytest.raises(ValueError, match="upstream_release_url_invalid"):
        compose_runtime_compatibility_evidence(_supply(), upstream_releases=releases, now=NOW)


def test_atomic_publish_is_off_repo_and_preserves_old_file_on_invalid(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    output = runtime / "compatibility.json"
    current = datetime.now(timezone.utc)
    evidence = compose_runtime_compatibility_evidence(
        _supply(now=current), upstream_releases=_releases(), now=current
    )
    publish_runtime_compatibility_evidence(
        evidence, repo_root=repo, runtime_root=runtime, output_path=output
    )
    before = output.read_bytes()
    invalid = dict(evidence)
    invalid["verification"] = "FAIL"
    with pytest.raises(ValueError, match="evidence_invalid"):
        publish_runtime_compatibility_evidence(
            invalid, repo_root=repo, runtime_root=runtime, output_path=output
        )
    assert output.read_bytes() == before
    with pytest.raises(ValueError):
        publish_runtime_compatibility_evidence(
            evidence, repo_root=repo, runtime_root=repo, output_path=repo / "bad.json"
        )


def test_watchlist_bridge_publishes_with_injected_official_fetcher(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    supply_path = runtime / "supply.json"
    output = runtime / "compatibility.json"
    current = datetime.now(timezone.utc)
    supply_path.write_text(json.dumps(_supply(now=current)), encoding="utf-8")

    def fetcher(component_id: str):
        release = _release(component_id)
        release["published_at"] = (current - timedelta(minutes=5)).isoformat()
        return release

    result = publish_compatibility_evidence(
        repo_root=repo,
        runtime_root=runtime,
        supply_path=supply_path,
        output_path=output,
        fetcher=fetcher,
    )
    assert result == output
    assert build_runtime_compatibility_receipt(json.loads(output.read_text(encoding="utf-8"))).overall_state == "NOT_READY"


def test_watchlist_bridge_rejects_supply_output_alias_without_data_loss(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    supply_path = runtime / "supply.json"
    supply_path.write_text(json.dumps(_supply()), encoding="utf-8")
    before = supply_path.read_bytes()
    for supplied_path in (supply_path, Path("supply.json")):
        with pytest.raises(ValueError, match="supply_output_alias"):
            publish_compatibility_evidence(
                repo_root=repo,
                runtime_root=runtime,
                supply_path=supplied_path,
                output_path=supply_path,
                fetcher=lambda component_id: _release(component_id),
            )
    assert supply_path.read_bytes() == before


class _Response:
    def __init__(self, url: str, body: bytes):
        self._url = url
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self) -> str:
        return self._url

    def read(self, limit: int) -> bytes:
        return self._body[:limit]


def test_release_fetcher_rejects_redirects_and_oversized_payloads(monkeypatch) -> None:
    endpoint = OFFICIAL_RELEASE_APIS["openclaw"]
    valid = json.dumps(_release("openclaw")).encode("utf-8")
    assert fetch_official_release("openclaw", opener=lambda *_a, **_k: _Response(endpoint, valid))["tag_name"]
    with pytest.raises(ValueError, match="redirected"):
        fetch_official_release("openclaw", opener=lambda *_a, **_k: _Response("https://attacker.invalid", valid))
    with pytest.raises(ValueError, match="too_large"):
        fetch_official_release("openclaw", opener=lambda *_a, **_k: _Response(endpoint, b"x" * (MAX_RELEASE_BYTES + 1)))

    captured = []

    class _Opener:
        def open(self, request, *, timeout):
            return (request, timeout)

    def fake_build_opener(*handlers):
        captured.extend(handlers)
        return _Opener()

    monkeypatch.setattr(watchlist_bridge, "build_opener", fake_build_opener)
    assert watchlist_bridge._open_release(object(), timeout=3)[1] == 3
    assert len(captured) == 1
    assert isinstance(captured[0], watchlist_bridge._RejectRedirects)
    assert captured[0].redirect_request(None) is None


def test_supplier_has_no_execution_update_or_model_loading_surface() -> None:
    path = Path(__file__).resolve().parents[1] / "src" / "runtime_compatibility_evidence_supplier.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    banned_imports = {"subprocess", "socket", "requests", "httpx", "aiohttp", "llama_cpp"}
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")])
    }
    assert not (imports & banned_imports)
    source = path.read_text(encoding="utf-8")
    for token in ("pip install", "npm install", "git checkout", "model.load", "subprocess.run"):
        assert token not in source


def test_supplier_follows_wsp62_boundaries() -> None:
    path = Path(__file__).resolve().parents[1] / "src" / "runtime_compatibility_evidence_supplier.py"
    lines = path.read_text(encoding="utf-8").splitlines()
    tree = ast.parse("\n".join(lines))
    assert len(lines) <= 600
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50
        if isinstance(node, ast.ClassDef):
            assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 200


def test_watchlist_bridge_follows_wsp62_function_boundaries() -> None:
    path = Path(__file__).resolve().parents[4] / "scripts" / "refresh_openclaw_ecosystem_watchlist.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50
