# -*- coding: utf-8 -*-
"""
Offline unit tests for LocalArchiveRetrievalPilot and DatasetBuilder fail-closed gates.

Uses 100% synthetic temporary fixtures (zero private transcripts, zero private paths,
zero network calls, zero model downloads, zero media decoding or ASR).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from modules.ai_intelligence.video_indexer.src.action_surface import (
    MAX_PILOT_RECORDS,
    LocalArchiveRetrievalPilot,
    run_local_archive_pilot,
)
from modules.ai_intelligence.video_indexer.src.dataset_builder import DatasetBuilder
from modules.ai_intelligence.video_indexer.src.local_archive_retrieval import (
    SPEAKER_UNKNOWN,
    SPEAKER_VERIFIED,
    STATUS_BLOCKED_MISSING_TRANSCRIPT,
    STATUS_INDEXED,
    TIMESTAMP_ABSENT,
    TIMESTAMP_GENUINE,
    TIMESTAMP_INVALID,
    TIMESTAMP_NONMONOTONIC,
    TIMESTAMP_PARTIAL_START_ONLY,
)


# =============================================================================
# Part 1: DatasetBuilder Fail-Closed Flaw Regressions
# =============================================================================


def test_dataset_builder_rejects_training_ineligible_even_with_verbatim_fields():
    builder = DatasetBuilder()
    sample_segs = [{"text": "Synthetic verbatim words spoken clearly here.", "start": 2.0, "end": 7.0, "speaker": "012"}]

    segs, src, reason = builder.inspect_record_eligibility(
        {"video_id": "syn_01", "training_eligible": False, "youtube_transcript": sample_segs}
    )
    assert segs == [] and src is None and reason == "training_ineligible"
    assert builder._extract_segments({"video_id": "syn_01", "training_eligible": False, "youtube_transcript": sample_segs}) == []

    segs2, _, reason2 = builder.inspect_record_eligibility(
        {"video_id": "syn_02", "metadata": {"training_eligible": False}, "whisper_transcript": sample_segs}
    )
    assert segs2 == [] and reason2 == "training_ineligible"

    assert builder._extract_segments({"training_eligible": "false", "youtube_transcript": sample_segs}) == []
    _, _, consent_reason = builder.inspect_record_eligibility({"consent": False, "youtube_transcript": sample_segs})
    assert consent_reason == "consent_denied"


@pytest.mark.parametrize(
    "bad_record,expected_reason",
    [
        ({"indexer": "gemini", "audio": {"segments": [{"text": "a b c d e f", "start": 1, "end": 3}]}}, "disallowed_provenance"),
        ({"transcript_source": "gemini_summary", "segments": [{"text": "a b c d e f", "start": 1, "end": 3}]}, "disallowed_provenance"),
        ({"indexer": "gemini", "youtube_transcript": [{"text": "a b c d e f", "start": 1, "end": 3}]}, "contradictory_metadata"),
        ({"transcript_source": "gemini_summary", "whisper_transcript": [{"text": "a b c d e f", "start": 1, "end": 3}]}, "contradictory_metadata"),
        ({"transcript_source": "studio_ask", "youtube_transcript": [{"text": "a b c d e f", "start": 1, "end": 3}]}, "contradictory_metadata"),
        ({"metadata": {"provenance": {"provider": "youtube_studio_ask"}}, "youtube_transcript": [{"text": "a b c d e f", "start": 1, "end": 3}]}, "contradictory_metadata"),
        ({"audio": {"extraction_method": "youtube_ask_gemini"}, "whisper_transcript": [{"text": "a b c d e f", "start": 1, "end": 3}]}, "contradictory_metadata"),
    ],
)
def test_dataset_builder_rejects_gemini_and_studio_ask_before_verbatim_fields(bad_record, expected_reason):
    builder = DatasetBuilder()
    segs, src, reason = builder.inspect_record_eligibility(bad_record)
    assert segs == [] and src is None and reason == expected_reason
    assert builder._extract_segments(bad_record) == []


def test_dataset_builder_rejects_raw_list_and_unlabeled_legacy_records():
    builder = DatasetBuilder()
    segs_payload = [{"text": "Unlabeled segment text with enough words.", "start": 1.0, "end": 5.0, "speaker": "012"}]

    segs, _, reason = builder.inspect_record_eligibility(segs_payload)
    assert segs == [] and reason == "unlabeled_raw_list"
    assert builder._extract_segments(segs_payload) == []

    for legacy in (
        {"video_id": "syn_leg1", "segments": segs_payload},
        {"video_id": "syn_leg2", "audio": {"segments": segs_payload}},
        {"video_id": "syn_leg3", "transcript": "Plain unlabeled transcript text with many words."},
        {"video_id": "syn_leg4", "training_eligible": True, "segments": segs_payload},
    ):
        extracted, _, leg_reason = builder.inspect_record_eligibility(legacy)
        assert extracted == [] and leg_reason == "missing_verbatim_provenance"

    music_segs, _, music_reason = builder.inspect_record_eligibility(
        {"video_id": "syn_mus", "channel": "antifafm", "youtube_transcript": segs_payload}
    )
    assert music_segs == [] and music_reason == "music_channel_excluded"


def test_dataset_builder_admits_valid_verbatim_and_filters_guest_speakers(tmp_path: Path):
    input_dir, output_dir = tmp_path / "in", tmp_path / "out"
    input_dir.mkdir()
    valid_doc = {
        "video_id": "syn_valid_01",
        "title": "Synthetic Architecture Talk",
        "transcript_source": "whisper_transcript",
        "training_eligible": True,
        "segments": [
            {"text": "Guest asks how modular architecture prevents coupling issues.", "start": 0.0, "end": 5.0, "speaker": "Guest Speaker"},
            {"text": "Modular boundaries isolate state and keep tests deterministic.", "start": 5.5, "end": 12.0, "speaker": "012"},
        ],
    }
    untimed_doc = {
        "video_id": "syn_valid_02",
        "transcript_source": "youtube_dom",
        "training_eligible": True,
        "speaker": "012",
        "transcript": "Untimed verbatim caption text works without fabricating zero timestamps.",
    }
    (input_dir / "01_valid.json").write_text(json.dumps(valid_doc), encoding="utf-8")
    (input_dir / "02_untimed.json").write_text(json.dumps(untimed_doc), encoding="utf-8")
    (input_dir / "03_gemini.json").write_text(
        json.dumps({"video_id": "syn_gem", "indexer": "gemini", "audio": {"segments": [{"text": "The speaker discusses synthetic testing.", "start": 0, "end": 10}]}}),
        encoding="utf-8",
    )
    (input_dir / "04_raw_list.json").write_text(json.dumps([{"text": "Raw list text should be rejected.", "start": 1, "end": 4}]), encoding="utf-8")
    (input_dir / "05_corrupt.json").write_text("{malformed json", encoding="utf-8")

    report = DatasetBuilder(min_segment_words=5).process_folder(str(input_dir), str(output_dir))
    assert (report["files_scanned"], report["videos_processed"], report["videos_rejected"], report["videos_failed"]) == (5, 2, 2, 1)
    assert report["rejection_reasons"] == {"disallowed_provenance": 1, "unlabeled_raw_list": 1, "parse_or_process_error": 1}
    assert len(report["errors"]) == 1 and report["errors"][0]["file"] == "05_corrupt.json"

    rows = [json.loads(ln) for ln in (output_dir / "training_rows.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) == 2
    row1 = next(r for r in rows if r["metadata"]["video_id"] == "syn_valid_01")
    assert "Modular boundaries isolate state" in row1["output"]["next_utterance_text"]
    assert "Guest asks" in row1["input"]["context_window_text"]
    assert (row1["metadata"]["t_start"], row1["metadata"]["t_end"], row1["metadata"]["transcript_source"]) == (5.5, 12.0, "whisper_transcript")
    row2 = next(r for r in rows if r["metadata"]["video_id"] == "syn_valid_02")
    assert row2["metadata"]["t_start"] is None and row2["metadata"]["t_end"] is None


# =============================================================================
# Part 2: Bounded Local YouTube Archive Retrieval Pilot Tests
# =============================================================================


def test_pilot_enforces_hard_10_record_cap(tmp_path: Path):
    assert MAX_PILOT_RECORDS == 10
    for invalid_cap in (0, -3, 11, 50, True, "10"):
        with pytest.raises(ValueError):
            LocalArchiveRetrievalPilot(max_records=invalid_cap)  # type: ignore[arg-type]

    files = []
    for idx in range(12):
        p = tmp_path / f"vid_{idx:02d}.json"
        p.write_text(
            json.dumps({"video_id": f"synvid_{idx:02d}", "youtube_transcript": [{"text": f"Synthetic archive segment number {idx}", "start": 1.0, "end": 4.0}]}),
            encoding="utf-8",
        )
        files.append(p)

    pilot = LocalArchiveRetrievalPilot(max_records=10)
    with pytest.raises(ValueError, match="exceeds bounded pilot hard cap"):
        pilot.load_records(files, reject_over_cap=True)
    assert len(pilot.records) == 0

    dir_summary = pilot.load_directory(tmp_path, reject_over_cap=False)
    assert (dir_summary["total_records_loaded"], dir_summary["truncated_over_cap"], len(pilot.records)) == (10, 2, 10)


def test_pilot_known_answer_and_not_found_queries_across_formats(tmp_path: Path):
    json_rec = tmp_path / "undaodu" / "SynVidJson1.json"
    json_rec.parent.mkdir()
    json_rec.write_text(
        json.dumps({"video_id": "SynVidJson1", "channel": "undaodu", "title": "Synthetic Distributed Consensus",
                    "youtube_transcript": [{"start": 42.5, "end": 49.0, "text": "Byzantine fault tolerance requires deterministic state replication."}]}),
        encoding="utf-8",
    )
    srt_rec = tmp_path / "Lecture [SynVidSrt02].en.srt"
    srt_rec.write_text("1\n00:01:15,250 --> 00:01:21,500\nSolar microgrids stabilize rural voltage fluctuations.\n\n", encoding="utf-8")
    vtt_rec = tmp_path / "Captions [SynVidVtt03].en.vtt"
    vtt_rec.write_text(
        "WEBVTT\nKind: captions\nLanguage: en\n\n00:02:10.000 --> 00:02:14.500\n"
        " Fermentation<00:02:11.000><c> kinetics</c> depend on koji enzymes.\n\n"
        "00:02:14.500 --> 00:02:18.000\nFermentation kinetics depend on koji enzymes.\nTemperature control prevents off flavors.\n",
        encoding="utf-8",
    )
    jsonl_rec = tmp_path / "SynVidJsl04.jsonl"
    jsonl_rec.write_text(json.dumps({"video_id": "SynVidJsl04", "title": "Synthetic Robotics", "timestamp_sec": 88.0, "end_sec": 95.5, "text": "Inverse kinematics solver converged within three iterations."}) + "\n", encoding="utf-8")
    json3_rec = tmp_path / "Timed [SynVidJs305].json3"
    json3_rec.write_text(json.dumps({"events": [{"tStartMs": 15500, "dDurationMs": 4500, "segs": [{"utf8": "Acoustic metamaterials "}, {"utf8": "attenuate low frequencies."}]}]}), encoding="utf-8")

    result = run_local_archive_pilot(
        sources=[json_rec, srt_rec, vtt_rec, jsonl_rec, json3_rec],
        queries=[
            "Byzantine fault tolerance state replication",
            "Solar microgrids rural voltage",
            "koji enzymes fermentation kinetics",
            "Inverse kinematics solver iterations",
            "Acoustic metamaterials low frequencies",
            "What is the atmospheric pressure on Neptune?",
            "zxqvbnm999888777",
        ],
    )
    assert (result["summary"]["indexed_records"], result["summary"]["blocked_missing_transcript_count"], result["summary"]["backend"]) == (5, 0, "tfidf")
    q_res = result["query_results"]
    assert (q_res[0]["hits"][0]["video_id"], q_res[0]["hits"][0]["source_path"], q_res[0]["hits"][0]["t_start"], q_res[0]["hits"][0]["t_end"]) == ("SynVidJson1", str(json_rec), 42.5, 49.0)
    assert q_res[0]["hits"][0]["provenance"]["is_verbatim"] is True
    assert (q_res[1]["hits"][0]["video_id"], q_res[1]["hits"][0]["t_start"], q_res[1]["hits"][0]["t_end"]) == ("SynVidSrt02", 75.25, 81.5)
    assert (q_res[2]["hits"][0]["video_id"], q_res[2]["hits"][0]["t_start"], q_res[2]["hits"][0]["t_end"]) == ("SynVidVtt03", 130.0, 134.5)
    assert "<c>" not in q_res[2]["hits"][0]["snippet"]
    assert (q_res[3]["hits"][0]["video_id"], q_res[3]["hits"][0]["t_start"], q_res[3]["hits"][0]["t_end"]) == ("SynVidJsl04", 88.0, 95.5)
    assert (q_res[4]["hits"][0]["video_id"], q_res[4]["hits"][0]["t_start"], q_res[4]["hits"][0]["t_end"]) == ("SynVidJs305", 15.5, 20.0)
    assert q_res[5]["not_found"] is True and q_res[5]["hits"] == [] and q_res[6]["not_found"] is True


def test_pilot_reports_blocked_missing_transcript_without_triggering_asr(tmp_path: Path):
    stub_json = tmp_path / "stub_vid.json"
    stub_json.write_text(
        json.dumps({"video_id": "StubVid0001", "indexer": "scheduler_stub", "title": "Stub Title Should Not Be Fabricated As Transcript",
                    "audio": {"segments": [], "transcript_summary": ""}, "metadata": {"summary": "Template description text"}}),
        encoding="utf-8",
    )
    info_json = tmp_path / "Archive Clip [InfoVid0002].info.json"
    info_json.write_text(
        json.dumps({"id": "InfoVid0002", "title": "Metadata Only Video", "description": "UniqueDescriptionKeywordXyz that is NOT a spoken transcript",
                    "webpage_url": "https://www.youtube.com/watch?v=InfoVid0002", "extractor": "youtube"}),
        encoding="utf-8",
    )
    raw_mp4 = tmp_path / "RawMedia [Mp4Vid00003].mp4"
    raw_mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    pilot = LocalArchiveRetrievalPilot(max_records=10)
    with patch.object(subprocess, "run", side_effect=AssertionError("External subprocess / ffmpeg / ASR is forbidden")):
        summary = pilot.load_records([stub_json, info_json, raw_mp4])

    assert (summary["indexed_records"], summary["blocked_missing_transcript_count"], summary["indexed_segments"]) == (0, 3, 0)
    assert all(rec["status"] == STATUS_BLOCKED_MISSING_TRANSCRIPT for rec in summary["records"])
    resp = pilot.query("UniqueDescriptionKeywordXyz Stub Title")
    assert resp.hit_count == 0 and resp.not_found is True and resp.blocked_missing_transcript_count == 3


def test_pilot_timestamp_honesty_genuine_vs_partial_vs_absent(tmp_path: Path):
    txt_file = tmp_path / "untimed_note.txt"
    txt_file.write_text("Superconducting magnet quench protection circuit telemetry.", encoding="utf-8")
    ask_json = tmp_path / "AskVid00001.json"
    ask_json.write_text(
        json.dumps({
            "video_id": "AskVid00001", "channel": "move2japan", "transcript_source": "gemini_summary",
            "metadata": {"training_eligible": False},
            "audio": {"segments": [
                {"start": 0, "end": None, "text": "Opening overview of municipal composting rules."},
                {"start": 0, "end": None, "text": "Untimed summary bullet about cardboard recycling."},
            ]},
            "gemini_summary": {"ask_segments": [
                {"time": "0:00", "summary": "Opening overview of municipal composting rules."},
                {"time": "", "summary": "Untimed summary bullet about cardboard recycling."},
            ]},
        }),
        encoding="utf-8",
    )
    zero_span_json = tmp_path / "ZeroSpan001.json"
    zero_span_json.write_text(
        json.dumps({"video_id": "ZeroSpan001", "transcript_source": "whisper_transcript",
                    "segments": [{"start": 0, "end": 0, "text": "Hydroponic nutrient conductivity calibration notes."}]}),
        encoding="utf-8",
    )

    pilot = LocalArchiveRetrievalPilot(max_records=10)
    pilot.load_records([txt_file, ask_json, zero_span_json])

    r_txt = pilot.query("Superconducting magnet quench protection").hits[0]
    assert (r_txt.t_start, r_txt.t_end, r_txt.has_genuine_timestamps, r_txt.timestamp_status, r_txt.deep_link) == (None, None, False, TIMESTAMP_ABSENT, None)

    r_zero = pilot.query("municipal composting rules").hits[0]
    assert (r_zero.t_start, r_zero.t_end, r_zero.has_genuine_timestamps, r_zero.timestamp_status) == (0.0, None, True, TIMESTAMP_PARTIAL_START_ONLY)
    assert r_zero.deep_link == "https://www.youtube.com/watch?v=AskVid00001&t=0s" and r_zero.provenance["is_verbatim"] is False
    assert pilot.query("municipal composting rules", verbatim_only=True).not_found is True

    r_blank = pilot.query("cardboard recycling").hits[0]
    assert (r_blank.t_start, r_blank.t_end, r_blank.has_genuine_timestamps, r_blank.timestamp_status, r_blank.deep_link) == (None, None, False, TIMESTAMP_ABSENT, None)

    r_zspan = pilot.query("Hydroponic nutrient conductivity").hits[0]
    assert (r_zspan.t_start, r_zspan.t_end, r_zspan.has_genuine_timestamps, r_zspan.timestamp_status) == (None, None, False, TIMESTAMP_ABSENT)


def test_pilot_lexical_fallback_and_japanese_cjk_support(tmp_path: Path):
    ja_json = tmp_path / "JaVid000001.json"
    ja_json.write_text(
        json.dumps({"video_id": "JaVid000001", "channel": "move2japan",
                    "youtube_transcript": [{"start": 18.0, "end": 26.0, "text": "福井市の地域活性化と温泉施設の再生計画について解説します。"}]}),
        encoding="utf-8",
    )
    pilot = LocalArchiveRetrievalPilot(max_records=5, force_lexical_fallback=True)
    summary = pilot.load_records([ja_json])
    assert summary["backend"] == "lexical_fallback" and summary["records"][0]["status"] == STATUS_INDEXED

    hit_resp = pilot.query("温泉施設の再生計画")
    assert hit_resp.not_found is False and hit_resp.hits[0].video_id == "JaVid000001"
    assert (hit_resp.hits[0].t_start, hit_resp.hits[0].t_end, hit_resp.hits[0].timestamp_status) == (18.0, 26.0, TIMESTAMP_GENUINE)
    assert pilot.query("量子コンピュータの超伝導回路").not_found is True


def test_pilot_attenuates_oov_queries_sharing_single_generic_word(tmp_path: Path):
    corpus_file = tmp_path / "OovGuardVid1.json"
    corpus_file.write_text(
        json.dumps({
            "video_id": "OovGuardVid1", "channel": "undaodu",
            "youtube_transcript": [
                {"start": 0.0, "end": 12.0, "text": "Introduction to the educational service and autonomous system design."},
                {"start": 12.0, "end": 25.0, "text": "Relocating to rural Japan involves local municipal registration."},
            ],
        }),
        encoding="utf-8",
    )
    for force_lex in (False, True):
        pilot = LocalArchiveRetrievalPilot(max_records=5, force_lexical_fallback=force_lex)
        pilot.load_records([corpus_file])
        hit = pilot.query("educational service autonomous system design")
        assert hit.not_found is False and hit.hits[0].video_id == "OovGuardVid1" and hit.hits[0].t_start == 0.0
        for oov_query in (
            "kerberos ticket granting service spnego GSSAPI keytab",
            "quantum chromodynamics gluon lattice gauge theory introduction",
            "PostgreSQL MVCC autovacuum wal_level system",
            "baryogenesis neutrino oscillation service",
        ):
            miss = pilot.query(oov_query)
            assert miss.hit_count == 0 and miss.not_found is True and miss.hits == []


# =============================================================================
# Part 3: Focused Adversarial Seam Regressions (5 Categories)
# =============================================================================


def test_adversarial_contradictory_metadata_rejected_and_flagged(tmp_path: Path):
    builder = DatasetBuilder()
    seg = [{"text": "Deterministic verification prevents silent admission errors.", "start": 1.0, "end": 5.0, "speaker": "012"}]
    contradictory_cases = [
        {"training_eligible": True, "metadata": {"training_eligible": False}, "youtube_transcript": seg},
        {"consent": True, "metadata": {"consent": False}, "whisper_transcript": seg},
        {"transcript_source": "youtube_transcript", "metadata": {"transcript_source": "gemini_summary"}, "segments": seg},
        {"transcript_source": "whisper", "metadata": {"indexer": "gemini"}, "segments": seg},
        {"video_id": "vid_alpha", "metadata": {"video_id": "vid_beta"}, "youtube_transcript": seg},
        {"video_id": "vid_alpha", "metadata": {"provenance": {"identity_verified": False}}, "youtube_transcript": seg},
        {"channel": "undaodu", "metadata": {"channel": "antifafm"}, "youtube_transcript": seg},
    ]
    for case in contradictory_cases:
        admitted, src, reason = builder.inspect_record_eligibility(case)
        assert admitted == [] and src is None and reason == "contradictory_metadata"

    conflict_file = tmp_path / "ConflictVid01.json"
    conflict_file.write_text(json.dumps(contradictory_cases[2] | {"youtube_transcript": seg}), encoding="utf-8")
    pilot = LocalArchiveRetrievalPilot(max_records=5)
    pilot.load_records([conflict_file])
    hit = pilot.query("Deterministic verification silent admission")
    assert hit.hit_count == 1
    assert hit.hits[0].provenance["provenance_conflict"] is True
    assert hit.hits[0].provenance["is_verbatim"] is False and hit.hits[0].provenance["training_eligible"] is False
    assert pilot.query("Deterministic verification silent admission", verbatim_only=True).not_found is True


def test_adversarial_summaries_mislabeled_as_transcripts_rejected_and_flagged(tmp_path: Path):
    builder = DatasetBuilder()
    mislabeled_cases = [
        {"youtube_transcript": [{"text": "The speaker introduces modular testing and explains protocol boundaries.", "start": 0.0, "end": 8.0, "speaker": "012"}]},
        {"whisper_transcript": [{"text": "Direct spoken words appear clean here.", "start": 0.0, "end": 5.0, "speaker": "012"}], "model": "gemini-2.5-flash"},
        {"transcript_source": "youtube_transcript", "segments": [{"text": "Direct spoken words appear clean here.", "start": 0.0, "end": 5.0, "speaker": "012"}], "gemini_summary": {"ask_response": "Teacher summary payload"}},
        {"youtube_transcript": [{"time": "0:10", "summary": "Summary schema disguised inside youtube_transcript", "speaker": "012"}]},
    ]
    for case in mislabeled_cases:
        admitted, src, reason = builder.inspect_record_eligibility(case)
        assert admitted == [] and src is None and reason == "mislabeled_summary_as_transcript"

    mislabeled_file = tmp_path / "Mislabeled01.json"
    mislabeled_file.write_text(json.dumps(mislabeled_cases[0]), encoding="utf-8")
    pilot = LocalArchiveRetrievalPilot(max_records=5)
    pilot.load_records([mislabeled_file])
    res = pilot.query("modular testing protocol boundaries")
    assert res.hit_count == 1 and res.hits[0].provenance["mislabeled_summary_suspected"] is True and res.hits[0].provenance["is_verbatim"] is False
    assert pilot.query("modular testing protocol boundaries", verbatim_only=True).not_found is True


def test_adversarial_missing_speakers_never_invent_012(tmp_path: Path):
    in_dir, out_dir = tmp_path / "in", tmp_path / "out"
    in_dir.mkdir()
    doc = {
        "video_id": "NoSpkVid0001",
        "youtube_transcript": [
            {"text": "Geothermal heat pumps reduce winter heating loads.", "start": 2.0, "end": 9.0},
            {"text": "Ground loop depth depends on soil conductivity.", "start": 9.5, "end": 16.0, "speaker": ""},
        ],
    }
    rec_path = in_dir / "no_speaker.json"
    rec_path.write_text(json.dumps(doc), encoding="utf-8")

    rep = DatasetBuilder(min_segment_words=5).process_folder(str(in_dir), str(out_dir))
    assert rep["videos_processed"] == 0 and rep["rejection_reasons"]["missing_speaker_attribution"] == 1
    assert (out_dir / "training_rows.jsonl").read_text(encoding="utf-8") == ""

    opt_out = tmp_path / "opt_out"
    lax_rep = DatasetBuilder(min_segment_words=5, require_speaker_attribution=False).process_folder(str(in_dir), str(opt_out))
    assert lax_rep["training_rows"] == 2 and lax_rep["voice_clips"] == 0
    for line in (opt_out / "training_rows.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        assert row["metadata"]["speaker"] == "unknown" and row["metadata"]["speaker_status"] == SPEAKER_UNKNOWN
        assert "012" not in json.dumps(row)

    pilot = LocalArchiveRetrievalPilot(max_records=5)
    pilot.load_records([rec_path])
    hit = pilot.query("Geothermal heat pumps winter heating")
    assert hit.hits[0].speaker is None and hit.hits[0].speaker_status == SPEAKER_UNKNOWN and pilot.records[0].has_unknown_speakers is True


def test_adversarial_mixed_speakers_and_verified_attribution(tmp_path: Path):
    in_dir, out_dir = tmp_path / "in", tmp_path / "out"
    in_dir.mkdir()
    mixed_doc = {
        "video_id": "MixSpkVid001",
        "whisper_transcript": [
            {"text": "Interviewer asks about distributed storage invariants.", "start": 0.0, "end": 4.0, "speaker": "Interviewer"},
            {"text": "Unattributed side remark from background microphone.", "start": 4.5, "end": 8.0, "speaker": ""},
            {"text": "Immutable content hashes guarantee replay reproducibility.", "start": 8.5, "end": 15.0, "speaker": "012", "speaker_verified": True},
        ],
    }
    mixed_path = in_dir / "mixed.json"
    mixed_path.write_text(json.dumps(mixed_doc), encoding="utf-8")

    builder = DatasetBuilder(min_segment_words=5, require_verified_speaker=True)
    rep = builder.process_folder(str(in_dir), str(out_dir))
    assert rep["training_rows"] == 1 and rep["voice_clips"] == 1
    row = json.loads((out_dir / "training_rows.jsonl").read_text(encoding="utf-8").strip())
    assert (row["metadata"]["speaker"], row["metadata"]["speaker_status"], row["metadata"]["has_mixed_speakers"]) == ("012", SPEAKER_VERIFIED, True)
    assert row["input"]["context_speakers"] == ["Interviewer", "unknown"]

    unver = {"whisper_transcript": [{"text": "Unverified speaker label text with five words.", "start": 1.0, "end": 5.0, "speaker": "012"}]}
    assert builder.inspect_record_eligibility(unver)[2] == "speaker_filtered_out"

    pilot = LocalArchiveRetrievalPilot(max_records=5)
    pilot.load_records([mixed_path])
    assert pilot.records[0].has_mixed_speakers is True and pilot.records[0].has_unknown_speakers is True
    h_ver = pilot.query("Immutable content hashes replay reproducibility")
    assert h_ver.hits[0].speaker == "012" and h_ver.hits[0].speaker_status == SPEAKER_VERIFIED
    h_unk = pilot.query("Unattributed side remark background microphone")
    assert h_unk.hits[0].speaker is None and h_unk.hits[0].speaker_status == SPEAKER_UNKNOWN


def test_adversarial_invalid_missing_and_nonmonotonic_timestamps(tmp_path: Path):
    builder = DatasetBuilder()
    for bad_seg in (
        {"text": "Segment with NaN start timestamp value.", "start": float("nan"), "end": 5.0, "speaker": "012"},
        {"text": "Segment with Inf end timestamp value.", "start": 1.0, "end": float("inf"), "speaker": "012"},
        {"text": "Segment with out of range seconds.", "start": "01:99", "end": "02:10", "speaker": "012"},
        {"text": "Segment with inverted end before start.", "start": 20.0, "end": 10.0, "speaker": "012"},
        {"text": "Segment with dangling end without start.", "start": None, "end": 15.0, "speaker": "012"},
        {"text": "Segment with boolean start timestamp.", "start": True, "end": 5.0, "speaker": "012"},
    ):
        assert builder.inspect_record_eligibility({"youtube_transcript": [bad_seg]})[2] == "invalid_timestamps"

    nonmono = [
        {"text": "First segment starts at thirty seconds.", "start": 30.0, "end": 40.0, "speaker": "012"},
        {"text": "Second segment regresses to ten seconds.", "start": 10.0, "end": 20.0, "speaker": "012"},
    ]
    assert builder.inspect_record_eligibility({"youtube_transcript": nonmono})[2] == "nonmonotonic_timestamps"

    bad_ts_file = tmp_path / "BadTimestamps01.json"
    bad_ts_file.write_text(
        json.dumps({
            "video_id": "BadTsVid0001",
            "segments": [
                {"text": "Invalid seconds ninety nine value.", "start": "01:99", "end": "02:10"},
                {"text": "Inverted span twenty to ten.", "start": 20.0, "end": 10.0},
                {"text": "Valid baseline segment at thirty.", "start": 30.0, "end": 40.0},
                {"text": "Nonmonotonic regression back to twelve.", "start": 12.0, "end": 18.0},
            ],
        }),
        encoding="utf-8",
    )
    pilot = LocalArchiveRetrievalPilot(max_records=5)
    pilot.load_records([bad_ts_file])
    h_inv1 = pilot.query("Invalid seconds ninety nine")
    assert h_inv1.hits[0].timestamp_status == TIMESTAMP_INVALID and h_inv1.hits[0].t_start is None and h_inv1.hits[0].deep_link is None
    h_inv2 = pilot.query("Inverted span twenty")
    assert h_inv2.hits[0].timestamp_status == TIMESTAMP_INVALID and h_inv2.hits[0].t_end is None and h_inv2.hits[0].deep_link is None
    h_nonm = pilot.query("Nonmonotonic regression twelve")
    assert h_nonm.hits[0].timestamp_status == TIMESTAMP_NONMONOTONIC and h_nonm.hits[0].t_start is None and h_nonm.hits[0].deep_link is None
