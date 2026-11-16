"""Synthetic stdlib fixtures; no providers, audio, reference lyrics or files."""
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import unittest

from modules.ai_intelligence.ai_gateway.src.model_audio_timing_benchmark import (
    CONTRACT_DIGEST, MAX_RESPONSE_BYTES, MAX_WORDS, TASK_FAMILY,
    SharedAttemptBudget, TimingCase, TimingObservation,
    build_timing_verifier, inspect_word_timestamps,
)
from modules.ai_intelligence.ai_gateway.src.model_combination_benchmark_harness import (
    ModelBenchmarkRoleAssignment, ModelBenchmarkTask, ModelBenchmarkTaskOutput,
    build_model_benchmark_candidate, run_model_combination_benchmark,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import VerifierDecision


def digest(text):
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def word(start=1, end=2, text="fixture"):
    return {"word": text, "start": start, "end": end}


class WordTimingTests(unittest.TestCase):
    def inspect(self, words):
        return inspect_word_timestamps({"words": words}, duration_seconds=10)

    def assert_invalid(self, words, code):
        report = self.inspect(words)
        self.assertFalse(report.format_valid)
        self.assertIn(code, [issue.code for issue in report.issues])
        self.assertIsNone(report.gaps)
        self.assertIsNone(report.overlaps)

    def test_missing_empty_and_segment_only_words(self):
        for payload in (None, [], {}, {"segments": [word()]},
                        {"words": None}, {"words": []}, {"words": ()}):
            with self.subTest(payload=payload):
                self.assertFalse(inspect_word_timestamps(payload, duration_seconds=10).format_valid)

    def test_word_limit_is_bounded(self):
        self.assert_invalid([word()] * (MAX_WORDS + 1), "words_missing_empty_or_invalid")

    def test_missing_or_invalid_word_text(self):
        for text in (None, "", "  ", 1, True):
            with self.subTest(text=text):
                self.assert_invalid([word(text=text)], "word_text_invalid")
        self.assert_invalid([{"start": 1, "end": 2}], "word_text_invalid")

    def test_nonobject_word_is_rejected(self):
        self.assert_invalid([None], "word_not_object")

    def test_missing_start_or_end(self):
        for key in ("start", "end"):
            row = word()
            del row[key]
            self.assert_invalid([row], "timestamp_not_finite_number")

    def test_nonfinite_bool_strings_and_huge_ints(self):
        for value in (True, False, "1", None, float("nan"), float("inf"),
                      -float("inf"), 10 ** 1000):
            for key in ("start", "end"):
                with self.subTest(key=key, value_type=type(value).__name__):
                    row = word()
                    row[key] = value
                    self.assert_invalid([row], "timestamp_not_finite_number")

    def test_negative_start_and_end(self):
        self.assert_invalid([word(-1, 2)], "timestamp_negative")
        self.assert_invalid([word(0, -1)], "timestamp_negative")

    def test_reversed_interval(self):
        self.assert_invalid([word(2, 1)], "interval_reversed")

    def test_excerpt_bounds_include_both_start_and_end(self):
        self.assert_invalid([word(11, 12)], "timestamp_out_of_bounds")
        self.assert_invalid([word(9, 11)], "timestamp_out_of_bounds")

    def test_starts_and_ends_have_separate_monotonic_checks(self):
        self.assert_invalid([word(2, 3), word(1, 4)], "starts_nonmonotonic")
        self.assert_invalid([word(1, 4), word(2, 3)], "ends_nonmonotonic")

    def test_exact_bounds_adjacent_and_zero_length_intervals(self):
        report = self.inspect([word(0, 1), word(1, 1), word(1, 10)])
        self.assertTrue(report.format_valid)
        self.assertEqual(report.gaps, ())
        self.assertEqual(report.overlaps, ())

    def test_gap_intervals_are_exact_and_have_no_semantic_claim(self):
        report = self.inspect([word(1, 2), word(4, 7)])
        self.assertEqual(report.gaps, ((0, 1), (2, 4), (7, 10)))
        for metric in ("word_error_rate", "alignment_error_seconds", "omissions",
                       "chorus_repetition_errors", "instrumental_hallucinations"):
            self.assertIsNone(getattr(report, metric))
        self.assertFalse(report.production_rsi_eligible)

    def test_overlaps_remain_visible_without_inventing_missing_audio(self):
        report = self.inspect([word(0, 3), word(2, 5), word(4, 10)])
        self.assertTrue(report.format_valid)
        self.assertEqual(report.overlaps, ((0, 1, 2, 3), (1, 2, 4, 5)))
        self.assertEqual(report.gaps, ())

    def test_original_payload_is_preserved(self):
        payload = {"words": [word(2, 3), word(1, 4)]}
        before = copy.deepcopy(payload)
        inspect_word_timestamps(payload, duration_seconds=10)
        self.assertEqual(payload, before)

    def test_invalid_duration_rejects_before_interpretation(self):
        for duration in (0, -1, True, "10", float("nan"), float("inf"), 10 ** 1000, 86_401):
            with self.subTest(duration_type=type(duration).__name__):
                with self.assertRaisesRegex(ValueError, "duration_seconds_invalid"):
                    inspect_word_timestamps({}, duration_seconds=duration)


class HarnessIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.case = TimingCase("song-fixture", digest("audio"), digest("preprocess"),
                               digest("agent-config"), 10)
        self.candidate = build_model_benchmark_candidate((ModelBenchmarkRoleAssignment(
            "principal", "fixture/model", "fixture"),))
        self.task = ModelBenchmarkTask(
            self.case.task_id, TASK_FAMILY, self.case.digest,
            digest("synthetic fixture expected structure, not reference lyrics"), CONTRACT_DIGEST)

    def verify_bytes(self, raw, *, case=None, topology=None):
        observation = TimingObservation((case or self.case).digest,
                                        topology or self.candidate.topology_digest, raw)
        verifier = build_timing_verifier({self.case.task_id: self.case},
                                         {observation.output_digest: observation})
        output = ModelBenchmarkTaskOutput(observation.output_digest, "fixture-receipt")
        return verifier(self.task, self.candidate, output), verifier, output

    def test_valid_format_is_skipped_in_real_existing_harness(self):
        decision, verifier, output = self.verify_bytes(json.dumps({"words": [word()]}).encode())
        self.assertEqual(decision.decision, VerifierDecision.SKIPPED)
        self.assertFalse(decision.evidence_correct)
        receipt = run_model_combination_benchmark(
            tasks=(self.task,), candidates=(self.candidate,), runner=lambda *_: output,
            verifier=verifier, verifier_digest=CONTRACT_DIGEST,
            held_out_split_id="synthetic-offline-fixtures")
        self.assertFalse(receipt.samples[0].accepted)
        self.assertEqual(receipt.benchmark_evidence_receipts[0].accepted_count, 0)
        self.assertIsNone(receipt.samples[0].metrics.cost_estimate_usd)

    def shared_response_run(self, cases, candidates):
        raw = json.dumps({"words": [word()]}).encode()
        observations = [TimingObservation(case.digest, candidate.topology_digest, raw)
                        for case in cases for candidate in candidates]
        # A byte digest is deliberately shared; registration must retain identity.
        self.assertEqual(len({item.output_digest for item in observations}), 1)
        tasks = [ModelBenchmarkTask(case.task_id, TASK_FAMILY, case.digest,
                 self.task.expected_output_digest, CONTRACT_DIGEST) for case in cases]
        output = ModelBenchmarkTaskOutput(observations[0].output_digest, "shared-response")
        return run_model_combination_benchmark(
            tasks=tasks, candidates=candidates, runner=lambda *_: output,
            verifier=build_timing_verifier({case.task_id: case for case in cases}, {
                (item.case_digest, item.candidate_topology_digest, item.output_digest): item
                for item in observations}),
            verifier_digest=CONTRACT_DIGEST, held_out_split_id="shared-response-fixtures")

    def test_identical_outputs_across_candidates_do_not_overwrite(self):
        other = build_model_benchmark_candidate((ModelBenchmarkRoleAssignment(
            "principal", "fixture/other-model", "fixture"),))
        for candidates in ((self.candidate, other), (other, self.candidate)):
            with self.subTest(order=[item.candidate_id for item in candidates]):
                receipt = self.shared_response_run((self.case,), candidates)
                self.assertEqual(len(receipt.samples), 2)
                self.assertEqual(len({s.verifier_receipt_id for s in receipt.samples}), 2)
                for sample in receipt.samples:
                    self.assertEqual(sample.decision, VerifierDecision.SKIPPED)
                    self.assertFalse(sample.accepted)
                    self.assertIn("transcription_accuracy_unmeasured", sample.rejection_reasons)

    def test_identical_outputs_across_cases_do_not_overwrite(self):
        other = TimingCase("other-song", digest("other-audio"), self.case.preprocessing_digest,
                           self.case.agent_config_digest, 20)
        for cases in ((self.case, other), (other, self.case)):
            with self.subTest(order=[item.task_id for item in cases]):
                receipt = self.shared_response_run(cases, (self.candidate,))
                self.assertEqual(len(receipt.samples), 2)
                self.assertEqual(len({s.verifier_receipt_id for s in receipt.samples}), 2)
                for sample in receipt.samples:
                    self.assertEqual(sample.decision, VerifierDecision.SKIPPED)
                    self.assertFalse(sample.accepted)
                    self.assertIn("transcription_accuracy_unmeasured", sample.rejection_reasons)

    def test_shared_output_is_checked_against_each_cases_bounds(self):
        shorter = TimingCase("short-song", digest("short-audio"), self.case.preprocessing_digest,
                             self.case.agent_config_digest, 1.5)
        receipt = self.shared_response_run((self.case, shorter), (self.candidate,))
        samples = {sample.task_id: sample for sample in receipt.samples}
        self.assertEqual(samples[self.case.task_id].decision, VerifierDecision.SKIPPED)
        self.assertEqual(samples[shorter.task_id].decision, VerifierDecision.REJECT)
        self.assertIn("word_timestamps_invalid", samples[shorter.task_id].rejection_reasons)
        self.assertTrue(all(not sample.accepted for sample in receipt.samples))

    def test_duplicate_full_identity_registration_is_rejected(self):
        observation = TimingObservation(self.case.digest, self.candidate.topology_digest, b'{}')
        compound_key = (self.case.digest, self.candidate.topology_digest, observation.output_digest)
        with self.assertRaisesRegex(ValueError, "observation_lookup_duplicate"):
            build_timing_verifier({self.case.task_id: self.case}, {
                observation.output_digest: observation, compound_key: observation})

    def test_different_outputs_for_same_identity_remain_selectable(self):
        observations = [TimingObservation(self.case.digest, self.candidate.topology_digest, raw)
                        for raw in (json.dumps({"words": [word()]}).encode(), b'{"words":[]}')]
        verifier = build_timing_verifier({self.case.task_id: self.case},
                                         {item.output_digest: item for item in observations})
        results = [verifier(self.task, self.candidate, ModelBenchmarkTaskOutput(
            item.output_digest, "fixture-receipt")) for item in observations]
        self.assertEqual([item.decision for item in results],
                         [VerifierDecision.SKIPPED, VerifierDecision.REJECT])
        self.assertIn("word_timestamps_invalid", results[1].rejection_reasons)
        self.assertTrue(all(not item.evidence_correct for item in results))

    def test_invalid_structure_is_rejected(self):
        decision, _, _ = self.verify_bytes(b'{"text":"fixture"}')
        self.assertEqual(decision.decision, VerifierDecision.REJECT)
        self.assertIn("word_timestamps_invalid", decision.rejection_reasons)

    def test_bad_json_constants_duplicate_keys_and_depth_reject(self):
        values = (b'bad json', b'\xff', b'{"words":[],"words":[]}',
                  b'{"words":[{"word":"fixture","start":NaN,"end":1}]}')
        for raw in values:
            with self.subTest(prefix=raw[:8]):
                result, _, _ = self.verify_bytes(raw)
                self.assertIn("response_json_invalid", result.rejection_reasons)
        # Well-formed JSON need not exceed this runtime's parser depth bound.
        # It is still invalid word-timing data, never accepted transcription.
        result, _, _ = self.verify_bytes(b'[' * 2000 + b'0' + b']' * 2000)
        self.assertEqual(result.decision, VerifierDecision.REJECT)
        self.assertFalse(result.evidence_correct)
        self.assertIn("word_timestamps_invalid", result.rejection_reasons)

    def test_other_case_preprocessing_or_agent_cannot_reuse_output(self):
        for field in ("audio_digest", "preprocessing_digest", "agent_config_digest"):
            changed = dict(self.case.__dict__)
            changed[field] = digest("other")
            result, _, _ = self.verify_bytes(b'{"words":[]}', case=TimingCase(**changed))
            self.assertIn("timing_identity_mismatch", result.rejection_reasons)

    def test_other_candidate_cannot_reuse_output(self):
        result, _, _ = self.verify_bytes(b'{"words":[]}', topology="other-topology")
        self.assertIn("timing_identity_mismatch", result.rejection_reasons)

    def test_wrong_output_lookup_digest_rejects_before_harness(self):
        observation = TimingObservation(self.case.digest, self.candidate.topology_digest, b'{}')
        invalid_keys = (digest("substitution"),
                        (digest("other-case"), self.candidate.topology_digest, observation.output_digest),
                        (self.case.digest, "other-topology", observation.output_digest),
                        (self.case.digest, self.candidate.topology_digest, digest("other-output")),
                        (self.case.digest, observation.output_digest))
        for key in invalid_keys:
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "observation_lookup_invalid"):
                    build_timing_verifier({self.case.task_id: self.case}, {key: observation})

    def test_wrong_task_or_contract_rejects(self):
        _, verifier, output = self.verify_bytes(b'{}')
        for field in ("prompt_digest", "verifier_contract_digest", "task_family"):
            changed = dict(self.task.__dict__)
            changed[field] = "substitution"
            result = verifier(ModelBenchmarkTask(**changed), self.candidate, output)
            self.assertIn("timing_identity_mismatch", result.rejection_reasons)

    def test_case_digest_and_response_bounds_are_strict(self):
        with self.assertRaisesRegex(ValueError, "case_digest_invalid"):
            TimingCase("fixture", "unknown", digest("p"), digest("a"), 10)
        for raw in (b'', bytearray(b'{}'), b' ' * (MAX_RESPONSE_BYTES + 1)):
            with self.assertRaisesRegex(ValueError, "response_bytes_invalid"):
                TimingObservation(self.case.digest, self.candidate.topology_digest, raw)


class AttemptBudgetTests(unittest.TestCase):
    def test_one_shared_budget_covers_candidates_and_diagnostics(self):
        budget, effects = SharedAttemptBudget(), []

        def transport(model, purpose):
            budget.claim(model_id=model, purpose=purpose)
            effects.append(model)

        transport("qwen", "word_timestamps")
        transport("qwen", "text_diagnostic")
        with self.assertRaisesRegex(RuntimeError, "budget_exhausted"):
            transport("other-model", "comparison")
        self.assertEqual(effects, ["qwen", "qwen"])

    def test_failed_or_unknown_attempt_is_not_refunded(self):
        budget = SharedAttemptBudget()
        for purpose in ("word_timestamps", "text_diagnostic"):
            try:
                budget.claim(model_id="qwen", purpose=purpose)
                raise TimeoutError("synthetic unknown outcome")
            except TimeoutError:
                pass
        with self.assertRaises(RuntimeError):
            budget.claim(model_id="other", purpose="comparison")
        self.assertEqual(len(budget.claims), 2)

    def test_concurrent_claims_cannot_exceed_shared_cap(self):
        budget = SharedAttemptBudget()

        def claim(_):
            try:
                return budget.claim(model_id="fixture", purpose="comparison")
            except RuntimeError:
                return None

        with ThreadPoolExecutor(max_workers=4) as workers:
            results = list(workers.map(claim, range(12)))
        self.assertEqual(sorted(value for value in results if value is not None), [1, 2])
        self.assertEqual(len(budget.claims), 2)

    def test_invalid_caps_and_claims_do_not_consume_budget(self):
        for limit in (0, -1, 3, True, 2.0, "2"):
            with self.assertRaises(ValueError):
                SharedAttemptBudget(limit)
        budget = SharedAttemptBudget(1)
        for model, purpose in ((None, "comparison"), (" ", "comparison"), ("x", "invalid")):
            with self.assertRaises(ValueError):
                budget.claim(model_id=model, purpose=purpose)
        self.assertEqual(budget.claims, ())
        self.assertEqual(budget.claim(model_id="x", purpose="comparison"), 1)


if __name__ == "__main__":
    unittest.main()
