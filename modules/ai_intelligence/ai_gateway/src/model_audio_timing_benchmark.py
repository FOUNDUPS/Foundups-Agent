"""Offline word-timing diagnostics through the existing model benchmark seam.

No transport, credential access, audio processing, reference lyrics, scheduling,
persistence, subtitle synthesis or promotion. Structure never establishes quality.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from threading import Lock

MAX_WORDS = 10_000
MAX_RESPONSE_BYTES = 1_048_576
TASK_FAMILY = "audio_word_timing_structure"
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


def _digest(value: dict) -> str:
    raw = json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


CONTRACT_DIGEST = _digest({
    "schema": "audio_word_timing_structure.v1",
    "word_fields": ["word", "start", "end"],
    "ordering": "original_order_starts_and_ends_nondecreasing",
    "semantic_quality": "unmeasured_always_skipped",
    "max_words": MAX_WORDS,
})


def _number(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


@dataclass(frozen=True)
class TimingIssue:
    code: str
    word_index: int | None = None


@dataclass(frozen=True)
class TimingReport:
    format_valid: bool
    word_count: int
    issues: tuple[TimingIssue, ...]
    overlaps: tuple[tuple[int, int, float, float], ...] | None
    gaps: tuple[tuple[float, float], ...] | None
    word_error_rate: None = field(default=None, init=False)
    alignment_error_seconds: None = field(default=None, init=False)
    omissions: None = field(default=None, init=False)
    chorus_repetition_errors: None = field(default=None, init=False)
    instrumental_hallucinations: None = field(default=None, init=False)
    timing_provenance: None = field(default=None, init=False)
    production_rsi_eligible: bool = field(default=False, init=False)

    def to_dict(self) -> dict:
        return asdict(self)


def _word_issues(row: object, index: int, duration: float):
    issues = []
    if type(row) is not dict:
        return [TimingIssue("word_not_object", index)], None
    text = row.get("word")
    if type(text) is not str or not text.strip():
        issues.append(TimingIssue("word_text_invalid", index))
    start, end = row.get("start"), row.get("end")
    if not _number(start) or not _number(end):
        return issues + [TimingIssue("timestamp_not_finite_number", index)], None
    if start < 0 or end < 0:
        issues.append(TimingIssue("timestamp_negative", index))
    if start > end:
        issues.append(TimingIssue("interval_reversed", index))
    if start > duration or end > duration:
        issues.append(TimingIssue("timestamp_out_of_bounds", index))
    return issues, (float(start), float(end))


def _interval_diagnostics(intervals, duration):
    gaps, overlaps = [], []
    covered_end = 0.0
    for index, (start, end) in enumerate(intervals):
        if start > covered_end:
            gaps.append((covered_end, start))
        if index and start < intervals[index - 1][1]:
            overlaps.append((index - 1, index, start,
                             min(end, intervals[index - 1][1])))
        covered_end = max(covered_end, end)
    if covered_end < duration:
        gaps.append((covered_end, float(duration)))
    return tuple(overlaps), tuple(gaps)


def inspect_word_timestamps(payload: object, *, duration_seconds: float) -> TimingReport:
    """Inspect supplied word times without sorting, coercion or interpolation.

    Gaps describe uncovered supplied intervals; they do not identify instrumentals.
    Overlaps describe adjacent pairs, not every pair in a three-word overlap.
    Zero-length intervals can be structurally valid without proving usability.
    Unknown/invalid timing does not produce invented intervals or zero error rates.
    """
    if not _number(duration_seconds) or not 0 < duration_seconds <= 86_400:
        raise ValueError("duration_seconds_invalid")
    words = payload.get("words") if type(payload) is dict else None
    if type(words) is not list or not words or len(words) > MAX_WORDS:
        return TimingReport(False, 0, (TimingIssue("words_missing_empty_or_invalid"),), None, None)
    issues, intervals, previous = [], [], None
    for index, row in enumerate(words):
        current_issues, interval = _word_issues(row, index, duration_seconds)
        issues.extend(current_issues)
        if interval is not None and previous is not None:
            if interval[0] < previous[0]:
                issues.append(TimingIssue("starts_nonmonotonic", index))
            if interval[1] < previous[1]:
                issues.append(TimingIssue("ends_nonmonotonic", index))
        if interval is not None:
            previous = interval
            intervals.append(interval)
    if issues:
        return TimingReport(False, len(words), tuple(issues), None, None)
    overlaps, gaps = _interval_diagnostics(intervals, duration_seconds)
    return TimingReport(True, len(words), (), overlaps, gaps)


@dataclass(frozen=True)
class TimingCase:
    task_id: str
    audio_digest: str
    preprocessing_digest: str
    agent_config_digest: str
    duration_seconds: float

    def __post_init__(self):
        if type(self.task_id) is not str or not self.task_id.strip():
            raise ValueError("task_id_invalid")
        for value in (self.audio_digest, self.preprocessing_digest, self.agent_config_digest):
            if type(value) is not str or not _SHA256.fullmatch(value):
                raise ValueError("case_digest_invalid")
        if not _number(self.duration_seconds) or not 0 < self.duration_seconds <= 86_400:
            raise ValueError("duration_seconds_invalid")

    @property
    def digest(self) -> str:
        return _digest({"schema": "audio_timing_case.v1", **asdict(self)})


@dataclass(frozen=True)
class TimingObservation:
    """Immutable bytes plus caller-asserted identity; no authenticity assertion."""
    case_digest: str
    candidate_topology_digest: str
    response_bytes: bytes = field(repr=False)

    def __post_init__(self):
        if type(self.case_digest) is not str or not _SHA256.fullmatch(self.case_digest):
            raise ValueError("observation_case_invalid")
        if type(self.candidate_topology_digest) is not str or not self.candidate_topology_digest:
            raise ValueError("observation_candidate_invalid")
        if type(self.response_bytes) is not bytes or not 0 < len(self.response_bytes) <= MAX_RESPONSE_BYTES:
            raise ValueError("response_bytes_invalid")

    @property
    def output_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.response_bytes).hexdigest()

    @property
    def lookup_key(self) -> tuple[str, str, str]:
        """Separate identical response bytes belonging to different identities."""
        return (self.case_digest, self.candidate_topology_digest, self.output_digest)


def _strict_payload(raw: bytes):
    def reject_constant(value):
        raise ValueError("nonfinite_json")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    return json.loads(raw.decode("utf-8"), parse_constant=reject_constant,
                      object_pairs_hook=unique_pairs)


def build_timing_verifier(
    cases: dict[str, TimingCase],
    observations: dict[str | tuple[str, str, str], TimingObservation],
):
    """Use the existing BenchmarkVerifier seam; valid format remains SKIPPED.

    Callers retain structural reports separately. This adapter does not judge
    lyrics/alignment or authenticate supplied responses, cases or model identity.
    Key observations by lookup_key when collecting multiple samples. Legacy
    output-digest keys remain supported, but entries lost while constructing a
    digest-only dict cannot be recovered. Duplicate full identities are rejected.
    """
    from .model_combination_benchmark_harness import ModelBenchmarkVerifierResult
    from .model_intelligence_outcomes import VerifierDecision

    frozen_cases, frozen_observations = dict(cases), {}
    for key, value in frozen_cases.items():
        if type(value) is not TimingCase or key != value.task_id:
            raise ValueError("case_lookup_invalid")
    for key, value in dict(observations).items():
        if type(value) is not TimingObservation:
            raise ValueError("observation_lookup_invalid")
        if not ((type(key) is str and key == value.output_digest)
                or (type(key) is tuple and key == value.lookup_key)):
            raise ValueError("observation_lookup_invalid")
        if value.lookup_key in frozen_observations:
            raise ValueError("observation_lookup_duplicate")
        frozen_observations[value.lookup_key] = value

    def verify(task, candidate, output):
        case = frozen_cases.get(task.task_id)
        observation = frozen_observations.get((case.digest, candidate.topology_digest,
                                               output.output_digest)) if case is not None else None
        reason, report = "timing_identity_mismatch", None
        if (case is not None and observation is not None
                and task.task_family == TASK_FAMILY
                and task.prompt_digest == case.digest
                and task.verifier_contract_digest == CONTRACT_DIGEST
                and observation.case_digest == case.digest
                and observation.candidate_topology_digest == candidate.topology_digest):
            try:
                report = inspect_word_timestamps(_strict_payload(observation.response_bytes),
                                                 duration_seconds=case.duration_seconds)
                reason = "transcription_accuracy_unmeasured" if report.format_valid else "word_timestamps_invalid"
            except (ValueError, UnicodeError, RecursionError):
                reason = "response_json_invalid"
        decision = VerifierDecision.SKIPPED if report is not None and report.format_valid else VerifierDecision.REJECT
        receipt = _digest({"contract": CONTRACT_DIGEST, "case": case.digest if case else None,
                           "output": output.output_digest, "candidate": candidate.topology_digest,
                           "reason": reason, "report": report.to_dict() if report else None})
        return ModelBenchmarkVerifierResult(decision, receipt, False, (reason,))

    return verify


class SharedAttemptBudget:
    """Thread-safe in-memory count guard only; never grants paid-call authority.

    Share ONE instance across candidates and diagnostics. Claim before each
    provider effect; failures/unknown outcomes consume their claim permanently.
    No refund/reset, durable replay protection, spend cap or transport is supplied.
    """
    def __init__(self, max_attempts: int = 2):
        if type(max_attempts) is not int or not 1 <= max_attempts <= 2:
            raise ValueError("max_attempts_invalid")
        self._limit, self._claims, self._lock = max_attempts, [], Lock()

    def claim(self, *, model_id: str, purpose: str) -> int:
        if type(model_id) is not str or not model_id.strip():
            raise ValueError("model_id_invalid")
        if type(purpose) is not str or purpose not in ("word_timestamps", "text_diagnostic", "comparison"):
            raise ValueError("purpose_invalid")
        with self._lock:
            if len(self._claims) >= self._limit:
                raise RuntimeError("inference_attempt_budget_exhausted")
            self._claims.append((model_id, purpose))
            return len(self._claims)

    @property
    def claims(self) -> tuple[tuple[str, str], ...]:
        with self._lock:
            return tuple(self._claims)
