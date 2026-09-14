"""Fail-closed runtime-admission contracts for production WRE Skillz."""

from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from modules.infrastructure.wre_core.src.libido_monitor import LibidoSignal
from modules.infrastructure.wre_core.src import skill_runtime_admission as admission
from modules.infrastructure.wre_core.src.registered_skill_executor import (
    validate_runtime_skill_admission,
)
from modules.infrastructure.wre_core.src.skill_runtime_admission import (
    ensure_runtime_skill_safety,
)
from modules.infrastructure.wre_core.src.skill_trigger import SkillTriggerMixin
from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader
from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator import (
    WREMasterOrchestrator,
)


class _Libido:
    def should_execute(self, **_kwargs):
        return LibidoSignal.ESCALATE

    def validate_step_fidelity(self, **_kwargs):
        return 1.0

    def record_execution(self, **_kwargs):
        return None


class _Memory:
    def __init__(self):
        self.outcomes = []
        self.counters = {}

    def get_active_ab_test(self, _skill_name):
        return None

    def store_outcome(self, outcome):
        self.outcomes.append(outcome)

    def increment_counter(self, name, delta=1):
        self.counters[name] = self.counters.get(name, 0) + delta


def _minimal_orchestrator(monkeypatch, tmp_path):
    orchestrator = object.__new__(WREMasterOrchestrator)
    orchestrator.repo_root = Path(__file__).resolve().parents[4]
    orchestrator.libido_monitor = _Libido()
    orchestrator.sqlite_memory = _Memory()
    orchestrator.react_fidelity_threshold = 0.90
    orchestrator._wre_skill_scan_cache = {}
    monkeypatch.setattr(
        orchestrator,
        "_ensure_wre_skill_safety",
        lambda _skill_name, force=False: (True, "test pass"),
    )
    monkeypatch.setenv("WRE_AGENTIC_RAG", "0")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    return orchestrator


def _runtime_admission_loader(skill_file: Path) -> SimpleNamespace:
    return SimpleNamespace(
        registry={
            "skills": {
                "skill": {
                    "promotion_state": "production",
                    "version": "1.0",
                    "intent_type": "DECISION",
                }
            }
        },
        get_skill_metadata=lambda _name: {
            "name": "skill",
            "version": "1.0",
            "intent_type": "DECISION",
            "promotion_state": "production",
        },
        resolve_skill_file=lambda _name: skill_file,
    )


@pytest.fixture
def cache_request(tmp_path, monkeypatch):
    skill_file = tmp_path / "skill" / "SKILLz.md"
    skill_file.parent.mkdir()
    skill_file.write_text("# skill", encoding="utf-8")
    (skill_file.parent / "SKILL_MANIFEST.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(admission, "SKILL_SCANNER_AVAILABLE", True)
    return dict(
        skills_loader=_runtime_admission_loader(skill_file), skill_name="skill",
        repo_root=tmp_path, cache={}, required=True, enforced=True,
        always_scan=False, ttl_seconds=900, max_severity="medium",
    )


def _scan_result(passed=True):
    return SimpleNamespace(available=True, passed=passed, manifest_passed=True)


@pytest.mark.parametrize("force_contender", [False, True])
def test_pending_refresh_blocks_cached_admission(cache_request, monkeypatch, force_contender):
    started, release = Event(), Event()
    calls = []

    def scan(**_kwargs):
        calls.append(True)
        if len(calls) == 2:
            started.set()
            assert release.wait(5)
            return _scan_result(False)
        return _scan_result()

    monkeypatch.setattr(admission, "run_skill_scan", scan)
    assert ensure_runtime_skill_safety(**cache_request)[0] is True
    with ThreadPoolExecutor(max_workers=1) as pool:
        refresh = pool.submit(ensure_runtime_skill_safety, **cache_request, force=True)
        try:
            assert started.wait(5)
            assert ensure_runtime_skill_safety(
                **cache_request, force=force_contender
            )[0] is False
            assert admission.admitted_runtime_fingerprint(
                skills_loader=cache_request["skills_loader"], skill_name="skill",
                cache=cache_request["cache"],
            ) is None
            assert len(calls) == 2
        finally:
            release.set()
        assert refresh.result(timeout=5)[0] is False
    assert ensure_runtime_skill_safety(**cache_request)[0] is False
    assert len(calls) == 2


@pytest.mark.parametrize("failure", [RuntimeError, KeyboardInterrupt])
def test_failed_refresh_removes_prior_admission(cache_request, monkeypatch, failure):
    calls = []

    def scan(**_kwargs):
        calls.append(True)
        if len(calls) == 2:
            raise failure("scanner stopped")
        return _scan_result()

    monkeypatch.setattr(admission, "run_skill_scan", scan)
    assert ensure_runtime_skill_safety(**cache_request)[0] is True
    with pytest.raises(failure, match="scanner stopped"):
        ensure_runtime_skill_safety(**cache_request, force=True)
    assert admission.admitted_runtime_fingerprint(
        skills_loader=cache_request["skills_loader"], skill_name="skill",
        cache=cache_request["cache"],
    ) is None
    assert ensure_runtime_skill_safety(**cache_request)[0] is True
    assert len(calls) == 3


def test_scan_policy_change_requires_fresh_admission(cache_request, monkeypatch):
    calls = []

    def scan(**kwargs):
        calls.append(kwargs["max_severity"])
        return _scan_result(kwargs["max_severity"] == "high")

    monkeypatch.setattr(admission, "run_skill_scan", scan)
    cache_request["max_severity"] = "high"
    assert ensure_runtime_skill_safety(**cache_request)[0] is True
    cache_request["max_severity"] = "low"
    assert ensure_runtime_skill_safety(**cache_request)[0] is False
    assert calls == ["high", "low"]
    cache_request["max_severity"] = "high"
    assert ensure_runtime_skill_safety(**cache_request)[0] is True
    reader = dict(skills_loader=cache_request["skills_loader"], skill_name="skill",
                  cache=cache_request["cache"])
    assert admission.admitted_runtime_fingerprint(**reader) is None
    assert admission.admitted_runtime_fingerprint(**reader, max_severity="low") is None
    assert admission.admitted_runtime_fingerprint(**reader, max_severity="high") is not None


def test_completed_cache_entries_are_bounded(cache_request, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(admission, "_MAX_CACHE_ENTRIES", 2, raising=False)
    monkeypatch.setattr(admission, "run_skill_scan",
                        lambda **kwargs: calls.append(kwargs) or _scan_result())
    loaders = []
    for index in range(3):
        folder = tmp_path / str(index)
        folder.mkdir()
        skill_file = folder / "SKILLz.md"
        skill_file.write_text(f"# {index}", encoding="utf-8")
        (folder / "SKILL_MANIFEST.json").write_text("{}", encoding="utf-8")
        loaders.append(_runtime_admission_loader(skill_file))
        cache_request["skills_loader"] = loaders[-1]
        assert ensure_runtime_skill_safety(**cache_request)[0] is True
        assert len(cache_request["cache"]) <= 2
    cache_request["skills_loader"] = loaders[0]
    assert ensure_runtime_skill_safety(**cache_request)[0] is True
    assert len(calls) == 4  # Oldest completed entry was evicted, requiring a scan.


@pytest.mark.parametrize("capacity", [1, 2])
def test_pending_scan_uses_capacity_without_blocking_other_callers(
    cache_request, monkeypatch, tmp_path, capacity
):
    started, release = Event(), Event()
    calls = []

    def scan(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            started.set()
            assert release.wait(5)
        return _scan_result()

    monkeypatch.setattr(admission, "_MAX_CACHE_ENTRIES", capacity, raising=False)
    monkeypatch.setattr(admission, "run_skill_scan", scan)
    second_file = tmp_path / "other" / "SKILLz.md"
    second_file.parent.mkdir()
    second_file.write_text("# other", encoding="utf-8")
    other_request = dict(cache_request, skills_loader=_runtime_admission_loader(second_file))
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(ensure_runtime_skill_safety, **cache_request)
        try:
            assert started.wait(5)
            assert ensure_runtime_skill_safety(**other_request)[0] is (capacity > 1)
            assert len(calls) == capacity
        finally:
            release.set()
        assert first.result(timeout=5)[0] is True
    assert ensure_runtime_skill_safety(**other_request)[0] is True
    assert len(calls) == 2
    assert len(cache_request["cache"]) == capacity


def test_removed_scan_reservation_cannot_republish(cache_request, monkeypatch):
    started, release = Event(), Event()

    def scan(**_kwargs):
        started.set()
        assert release.wait(5)
        return _scan_result()

    monkeypatch.setattr(admission, "run_skill_scan", scan)
    with ThreadPoolExecutor(max_workers=1) as pool:
        work = pool.submit(ensure_runtime_skill_safety, **cache_request)
        try:
            assert started.wait(5)
            cache_request["cache"].clear()
        finally:
            release.set()
        assert work.result(timeout=5)[0] is False
    assert cache_request["cache"] == {}


def test_orchestrator_reads_the_configured_scan_policy(cache_request, monkeypatch, tmp_path):
    orchestrator = _minimal_orchestrator(monkeypatch, tmp_path)
    orchestrator.skills_loader = cache_request["skills_loader"]
    orchestrator._wre_skill_admission_fingerprints = {}
    orchestrator.wre_skill_scan_required = True
    orchestrator.wre_skill_scan_enforced = True
    orchestrator.wre_skill_scan_always = False
    orchestrator.wre_skill_scan_ttl_sec = 900
    orchestrator.wre_skill_scan_max_severity = "high"
    monkeypatch.setattr(admission, "run_skill_scan", lambda **_kwargs: _scan_result())
    ok, _ = WREMasterOrchestrator._ensure_wre_skill_safety(orchestrator, "skill")
    assert ok is True
    expected = admission.admitted_runtime_fingerprint(
        skills_loader=orchestrator.skills_loader, skill_name="skill",
        cache=orchestrator._wre_skill_scan_cache, max_severity="high",
    )
    assert expected is not None
    assert orchestrator._wre_skill_admission_fingerprints["skill"] == expected


def test_runtime_admission_rejects_prototype_and_metadata_drift():
    prototype = SimpleNamespace(
        registry={"skills": {"skill": {"promotion_state": "prototype"}}},
        get_skill_metadata=lambda _name: {},
    )
    admitted, _ = validate_runtime_skill_admission(
        skills_loader=prototype, skill_name="skill"
    )
    assert admitted is False

    drifted = SimpleNamespace(
        registry={
            "skills": {
                "skill": {
                    "promotion_state": "production",
                    "version": "1.0",
                    "intent_type": "DECISION",
                }
            }
        },
        get_skill_metadata=lambda _name: {
            "name": "skill",
            "version": "2.0",
            "intent_type": "DECISION",
            "promotion_state": "production",
        },
    )
    admitted, _ = validate_runtime_skill_admission(
        skills_loader=drifted, skill_name="skill"
    )
    assert admitted is False

    malformed = SimpleNamespace(
        registry=drifted.registry,
        get_skill_metadata=lambda _name: ["valid-yaml", "wrong-root"],
    )
    admitted, message = validate_runtime_skill_admission(
        skills_loader=malformed, skill_name="skill"
    )
    assert admitted is False
    assert "malformed" in message


def test_scanner_cache_is_bound_to_current_bundle_bytes(tmp_path, monkeypatch):
    from modules.infrastructure.wre_core.src import skill_runtime_admission

    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILLz.md"
    skill_file.write_text("# v1", encoding="utf-8")
    (skill_dir / "SKILL_MANIFEST.json").write_text("{}", encoding="utf-8")
    loader = _runtime_admission_loader(skill_file)
    calls = []

    def _scan(**scan_kwargs):
        calls.append(scan_kwargs)
        return SimpleNamespace(available=True, passed=True, manifest_passed=True)

    monkeypatch.setattr(skill_runtime_admission, "SKILL_SCANNER_AVAILABLE", True)
    monkeypatch.setattr(skill_runtime_admission, "run_skill_scan", _scan)
    cache = {}
    kwargs = dict(
        skills_loader=loader,
        skill_name="skill",
        repo_root=tmp_path,
        cache=cache,
        required=True,
        enforced=True,
        always_scan=False,
        ttl_seconds=900,
        max_severity="medium",
    )

    assert ensure_runtime_skill_safety(**kwargs)[0] is True
    assert ensure_runtime_skill_safety(**kwargs)[0] is True
    skill_file.write_text("# v2", encoding="utf-8")
    assert ensure_runtime_skill_safety(**kwargs)[0] is True
    assert len(calls) == 2
    assert calls[0]["report_dir"] != calls[1]["report_dir"]
    assert len(calls[0]["report_dir"].name) == 64
    assert len(cache) == 1

    kwargs.update(required=False, enforced=False)
    ok, message = ensure_runtime_skill_safety(**kwargs)
    assert ok is False
    assert "required and enforced" in message
    assert len(calls) == 2


def test_scanner_rejects_bundle_changed_during_scan(tmp_path, monkeypatch):
    from modules.infrastructure.wre_core.src import skill_runtime_admission

    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILLz.md"
    skill_file.write_text("# v1", encoding="utf-8")
    (skill_dir / "SKILL_MANIFEST.json").write_text("{}", encoding="utf-8")

    def _scan(**_kwargs):
        skill_file.write_text("# v2", encoding="utf-8")
        return SimpleNamespace(available=True, passed=True, manifest_passed=True)

    monkeypatch.setattr(skill_runtime_admission, "SKILL_SCANNER_AVAILABLE", True)
    monkeypatch.setattr(skill_runtime_admission, "run_skill_scan", _scan)
    ok, message = ensure_runtime_skill_safety(
        skills_loader=_runtime_admission_loader(skill_file),
        skill_name="skill",
        repo_root=tmp_path,
        cache={},
        required=True,
        enforced=True,
        always_scan=True,
        ttl_seconds=0,
        max_severity="medium",
    )

    assert ok is False
    assert "changed during" in message


def test_codeact_public_surface_is_fail_closed():
    orchestrator = object.__new__(WREMasterOrchestrator)
    result = orchestrator.execute_codeact_skill({}, {})
    assert result["success"] is False
    assert result["blocked_by"] == "codeact_prototype_boundary"


def test_public_metrics_do_not_fabricate_token_reduction():
    orchestrator = object.__new__(WREMasterOrchestrator)
    orchestrator.state = "0102"
    orchestrator.coherence = 0.618
    orchestrator.pattern_memory = SimpleNamespace(patterns={})
    orchestrator.plugins = {}
    orchestrator.skills_loader = None

    metrics = orchestrator.get_metrics()

    assert metrics["token_reduction_measured"] is False
    assert "reduction" not in metrics


def test_runtime_manifest_failure_cannot_be_masked_by_scanner_policy(
    tmp_path, monkeypatch
):
    from modules.infrastructure.wre_core.src import skill_runtime_admission

    monkeypatch.setattr(skill_runtime_admission, "SKILL_SCANNER_AVAILABLE", True)
    monkeypatch.setattr(
        skill_runtime_admission,
        "run_skill_scan",
        lambda **_kwargs: SimpleNamespace(
            available=True,
            passed=False,
            manifest_passed=False,
        ),
    )

    ok, message = skill_runtime_admission._scan_bundle(
        scan_dir=tmp_path,
        report_dir=tmp_path / "reports",
        required=False,
        enforced=False,
        max_severity="medium",
    )

    assert ok is False
    assert "manifest" in message


def test_bundle_fingerprint_rejects_linked_executor(tmp_path):
    """Admission cannot hash through a linked executor before manifest checks."""
    from modules.infrastructure.wre_core.src.skill_runtime_admission import (
        _bundle_fingerprint,
    )

    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILLz.md").write_text("# skill", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text("SYNTHETIC_SECRET", encoding="utf-8")
    try:
        (skill_dir / "executor.py").symlink_to(outside)
    except OSError:
        pytest.skip("file links are unavailable on this host")

    with pytest.raises(ValueError, match="link or reparse"):
        _bundle_fingerprint(skill_dir)


def test_active_ab_execution_fails_closed_without_runtime_binding(
    monkeypatch, tmp_path
):
    orchestrator = _minimal_orchestrator(monkeypatch, tmp_path)
    orchestrator.skills_loader = SimpleNamespace(load_skill=lambda *_args: "# Skill")
    orchestrator.sqlite_memory.get_active_ab_test = lambda _name: {
        "test_id": "ab-1",
        "treatment_version": "candidate-1",
    }
    monkeypatch.setattr(
        orchestrator,
        "_try_executor_dispatch",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("unbound A/B candidate must not dispatch")
        ),
    )

    result = orchestrator._execute_skill_once(
        "skill", "qwen", {}, evolve_on_low_fidelity=False
    )

    assert result["success"] is False
    assert result["blocked_by"] == "ab_variant_binding"


def test_dae_trigger_selects_only_registered_production_domain_skillz(
    tmp_path, monkeypatch
):
    observed = {}

    def _list_skills(self, **kwargs):
        observed.update(kwargs)
        return ["production_skill"]

    monkeypatch.setattr(WRESkillsLoader, "list_skills", _list_skills)
    trigger = SkillTriggerMixin()
    trigger._trigger_repo_root = tmp_path
    trigger._trigger_domain = "streaming"

    assert trigger._discover_domain_skills() == ["production_skill"]
    assert observed == {"domain": "streaming", "promotion_state": "production"}


def test_dae_trigger_context_cannot_forge_reserved_provenance():
    trigger = object.__new__(SkillTriggerMixin)
    trigger._trigger_domain = "streaming"

    context = trigger._trigger_context(
        {
            "domain": "forged",
            "triggered_by": "forged",
            "trigger_timestamp": "forged",
            "payload": "kept",
        }
    )

    assert context["domain"] == "streaming"
    assert context["triggered_by"] == "dae_streaming"
    assert context["trigger_timestamp"] != "forged"
    assert context["payload"] == "kept"


def test_wsp95_mirror_pins_fail_closed_candidate_only_authority():
    repo_root = Path(__file__).resolve().parents[4]
    framework = repo_root / "WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md"
    knowledge = repo_root / "WSP_knowledge/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md"

    assert framework.read_bytes() == knowledge.read_bytes()
    protocol = framework.read_text(encoding="utf-8")
    for required in (
        "Execution truth",
        "Synthetic fallback instructions cannot create a successful outcome",
        "candidate_ready",
        "The proposer/author cannot be the sole verifier or promoter",
        "Production end-to-end RSI canary | Not proven",
    ):
        assert required in protocol
