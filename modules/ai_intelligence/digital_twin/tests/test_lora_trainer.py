# -*- coding: utf-8 -*-
"""Offline deterministic unit tests for VoiceLoRATrainer and VoiceTrainingConfig.

All tests execute strictly offline with synthetic JSONL fixtures in tmp_path and
in-memory stub tokenizers/models/trainers (zero downloads, zero GPU, zero real
training runs).
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

import pytest
import torch

import modules.ai_intelligence.digital_twin.src.lora_trainer as lora_trainer
from modules.ai_intelligence.digital_twin.src.lora_trainer import (
    IGNORE_INDEX,
    InspectedVoiceRecord,
    VoiceLoRATrainer,
    VoiceTrainingConfig,
    inspect_sft_record,
    load_and_validate_jsonl,
    load_and_validate_records,
    validate_sft_record,
)


class SyntheticChatTokenizer:
    """Deterministic offline ChatML tokenizer supporting pad_token_id == eos_token_id."""

    TOKEN_PATTERN = re.compile(r"<\|im_start\|>|<\|im_end\|>|\n|[^\s<]+|<")

    def __init__(
        self,
        *,
        pad_token: str | None = None,
        eos_token: str = "<|im_end|>",
        padding_side: str = "right",
    ) -> None:
        self.eos_token = eos_token
        self.pad_token = pad_token
        self.padding_side = padding_side
        self.chat_template = "chatml"
        self.saved_to: list[str] = []
        self._vocab: dict[str, int] = {
            "<|pad|>": 1,
            "<|im_end|>": 2,
            "<|im_start|>": 3,
            "\n": 4,
            "system": 5,
            "user": 6,
            "assistant": 7,
        }

    @property
    def eos_token_id(self) -> int:
        return self._id_for(self.eos_token)

    @property
    def pad_token_id(self) -> int:
        tok = self.pad_token if self.pad_token is not None else self.eos_token
        return self._id_for(tok)

    def _id_for(self, token: str) -> int:
        if token not in self._vocab:
            self._vocab[token] = len(self._vocab) + 10
        return self._vocab[token]

    def encode_text(self, text: str) -> list[int]:
        return [self._id_for(piece) for piece in self.TOKEN_PATTERN.findall(text)]

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        tokenize: bool = False,
        add_generation_prompt: bool = False,
    ) -> str | list[int]:
        parts = [
            f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
            for msg in messages
        ]
        rendered = "".join(parts)
        if add_generation_prompt:
            rendered += "<|im_start|>assistant\n"
        if tokenize:
            return self.encode_text(rendered)
        return rendered

    def __call__(
        self,
        text: str,
        truncation: bool = False,
        max_length: int = 512,
        padding: bool | str = False,
        return_tensors: str | None = "pt",
    ) -> dict[str, Any]:
        ids = self.encode_text(text)
        if truncation:
            ids = ids[:max_length]
        mask = [1] * len(ids)

        if padding == "max_length":
            pad_count = max(0, max_length - len(ids))
            pad_ids = [self.pad_token_id] * pad_count
            pad_mask = [0] * pad_count
            if self.padding_side == "left":
                ids = pad_ids + ids
                mask = pad_mask + mask
            else:
                ids = ids + pad_ids
                mask = mask + pad_mask

        if return_tensors == "pt":
            return {
                "input_ids": torch.tensor([ids], dtype=torch.long),
                "attention_mask": torch.tensor([mask], dtype=torch.long),
            }
        return {"input_ids": ids, "attention_mask": mask}

    def save_pretrained(self, path: str) -> None:
        self.saved_to.append(path)


def _write_jsonl(path: Path, lines: list[str | dict[str, Any]]) -> Path:
    serialized = [
        line if isinstance(line, str) else json.dumps(line, ensure_ascii=False)
        for line in lines
    ]
    path.write_text("\n".join(serialized) + "\n", encoding="utf-8")
    return path


def _valid_row(video_id: str | None = "vid_a", **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "user": "q",
        "assistant": "Authentic first-person verbatim speech.",
        "training_eligible": True,
        "transcript_source": "youtube_transcript",
        "consent": True,
        "speaker": "012",
        "speaker_verified": True,
    }
    if video_id is not None:
        row["video_id"] = video_id
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# 1. Security & Offline Model Loading Gates (WSP 71)
# ---------------------------------------------------------------------------


def test_config_defaults_enforce_offline_and_forbid_remote_code() -> None:
    cfg = VoiceTrainingConfig()
    assert cfg.trust_remote_code is False
    assert cfg.local_files_only is True
    assert cfg.require_verified_speaker is True
    assert cfg.require_explicit_admission is True
    assert cfg.eval_ratio == pytest.approx(0.2)


@pytest.mark.parametrize("bad_remote_code", [True, 1, "true", "False", None])
def test_config_rejects_trust_remote_code_true_or_non_bool(bad_remote_code: Any) -> None:
    with pytest.raises(ValueError, match="trust_remote_code"):
        VoiceTrainingConfig(trust_remote_code=bad_remote_code)  # type: ignore[arg-type]


def test_post_init_mutation_of_trust_remote_code_rejected_before_load() -> None:
    cfg = VoiceTrainingConfig(use_4bit=False)
    trainer = VoiceLoRATrainer(cfg)
    trainer.config.trust_remote_code = True
    with pytest.raises(ValueError, match="trust_remote_code"):
        trainer.load_model()


def test_load_model_enforces_trust_remote_code_false_and_local_files_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}
    fake_tok = SyntheticChatTokenizer(pad_token=None)

    class StubTokenizerCls:
        @staticmethod
        def from_pretrained(model_id: str, **kwargs: Any) -> SyntheticChatTokenizer:
            calls["tokenizer"] = (model_id, kwargs)
            return fake_tok

    class StubModel:
        def __init__(self) -> None:
            self.trainable_printed = False

        def print_trainable_parameters(self) -> None:
            self.trainable_printed = True

    stub_model = StubModel()

    class StubModelCls:
        @staticmethod
        def from_pretrained(model_id: str, **kwargs: Any) -> StubModel:
            calls["model"] = (model_id, kwargs)
            return stub_model

    monkeypatch.setitem(lora_trainer.__dict__, "AutoTokenizer", StubTokenizerCls)
    monkeypatch.setitem(lora_trainer.__dict__, "AutoModelForCausalLM", StubModelCls)
    monkeypatch.setitem(lora_trainer.__dict__, "LoraConfig", lambda **kwargs: {"lora": kwargs})
    monkeypatch.setitem(lora_trainer.__dict__, "get_peft_model", lambda model, _cfg: model)

    cfg = VoiceTrainingConfig(base_model="/offline/qwen-local", use_4bit=False)
    trainer = VoiceLoRATrainer(cfg)
    trainer.load_model()

    assert calls["tokenizer"] == (
        "/offline/qwen-local",
        {"trust_remote_code": False, "local_files_only": True},
    )
    assert calls["model"] == (
        "/offline/qwen-local",
        {"device_map": "auto", "trust_remote_code": False, "local_files_only": True},
    )
    assert trainer.tokenizer.pad_token == trainer.tokenizer.eos_token
    assert stub_model.trainable_printed is True


def test_load_model_4bit_enforces_cuda_and_passes_bnb_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}

    monkeypatch.setitem(
        lora_trainer.__dict__,
        "AutoTokenizer",
        type("StubTok", (), {"from_pretrained": staticmethod(lambda *_a, **_k: SyntheticChatTokenizer())}),
    )

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    trainer_no_cuda = VoiceLoRATrainer(VoiceTrainingConfig(use_4bit=True))
    with pytest.raises(RuntimeError, match="CUDA"):
        trainer_no_cuda.load_model()

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setitem(lora_trainer.__dict__, "BitsAndBytesConfig", lambda **kwargs: {"bnb": kwargs})
    monkeypatch.setitem(
        lora_trainer.__dict__,
        "AutoModelForCausalLM",
        type(
            "StubMod",
            (),
            {"from_pretrained": staticmethod(lambda m_id, **kw: calls.setdefault("model", (m_id, kw)))},
        ),
    )
    monkeypatch.setitem(lora_trainer.__dict__, "prepare_model_for_kbit_training", lambda m: ("kbit", m))
    monkeypatch.setitem(lora_trainer.__dict__, "LoraConfig", lambda **kw: kw)
    monkeypatch.setitem(lora_trainer.__dict__, "get_peft_model", lambda m, _c: m)

    trainer_cuda = VoiceLoRATrainer(VoiceTrainingConfig(base_model="/offline/m", use_4bit=True))
    trainer_cuda.load_model()

    model_id, model_kwargs = calls["model"]
    assert model_id == "/offline/m"
    assert model_kwargs["trust_remote_code"] is False
    assert model_kwargs["local_files_only"] is True
    assert model_kwargs["quantization_config"]["bnb"]["load_in_4bit"] is True


def test_cli_main_requires_explicit_consent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["lora_trainer.py"])
    with pytest.raises(PermissionError, match="--confirm-consent"):
        lora_trainer.main()


def test_check_runtime_readiness_is_offline_and_reports_blockers() -> None:
    trainer = VoiceLoRATrainer(VoiceTrainingConfig())
    report = trainer.check_runtime_readiness()
    assert report["trust_remote_code"] is False
    assert report["local_files_only"] is True
    assert isinstance(report["blockers"], list)
    if not report["cuda_available"]:
        assert "cuda_unavailable_for_4bit" in report["blockers"]
        assert report["ready_for_training"] is False


# ---------------------------------------------------------------------------
# 2. Fail-Closed JSONL Parsing, Eligibility & Verbatim Provenance Gates
# ---------------------------------------------------------------------------


def test_malformed_json_line_raises_with_exact_line_number(tmp_path: Path) -> None:
    jsonl = _write_jsonl(
        tmp_path / "corrupt.jsonl",
        [
            _valid_row("vid_a", user="q1", assistant="verbatim answer 1"),
            '{"user": "q2", "assistant": "unterminated',
            _valid_row("vid_b", user="q3", assistant="verbatim answer 3"),
        ],
    )
    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl)))
    trainer.tokenizer = SyntheticChatTokenizer()

    with pytest.raises(ValueError, match=r"line 2"):
        trainer.load_data()


def test_empty_file_and_non_dict_record_rejected(tmp_path: Path) -> None:
    empty_path = tmp_path / "empty.jsonl"
    empty_path.write_text("   \n\n", encoding="utf-8")
    with pytest.raises(ValueError, match="zero valid examples"):
        load_and_validate_jsonl(empty_path)

    list_path = _write_jsonl(tmp_path / "list_row.jsonl", ['["not", "a", "dict"]'])
    with pytest.raises(ValueError, match=r"line 1.*dict"):
        load_and_validate_jsonl(list_path)


@pytest.mark.parametrize(
    "overrides,omit_keys,expected_pattern",
    [
        ({"assistant": ""}, (), "assistant"),
        ({"assistant": "   \t\n "}, (), "assistant"),
        ({}, ("assistant",), "assistant"),
        ({"training_eligible": False}, (), "training_eligible"),
        ({"metadata": {"training_eligible": False}}, (), "training_eligible"),
        ({"training_eligible": "false"}, (), "training_eligible"),
        ({"transcript_source": "gemini"}, (), "provenance"),
        ({"transcript_source": "studio_ask"}, (), "provenance"),
        ({"metadata": {"transcript_source": "gemini_summary"}}, (), "provenance"),
        ({"indexer": "gemini"}, (), "provenance"),
        ({"audio": {"extraction_method": "youtube_ask_gemini"}}, (), "provenance"),
        ({"consent": False}, (), "Unconsented"),
        ({"rights_status": "third_party"}, (), "Unconsented"),
    ],
)
def test_ineligible_provenance_or_blank_assistant_rejected(
    tmp_path: Path,
    overrides: dict[str, Any],
    omit_keys: tuple[str, ...],
    expected_pattern: str,
) -> None:
    bad_record = {k: v for k, v in _valid_row("v1", **overrides).items() if k not in omit_keys}
    jsonl = _write_jsonl(
        tmp_path / "bad_admission.jsonl",
        [
            _valid_row("vid_ok", user="good", assistant="valid verbatim speech"),
            bad_record,
        ],
    )
    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl)))
    trainer.tokenizer = SyntheticChatTokenizer()

    with pytest.raises(ValueError, match=f"line 2.*{expected_pattern}|{expected_pattern}.*line 2"):
        trainer.load_data()


# ---------------------------------------------------------------------------
# 3. Prompt & Padding Masking (-100) + Overlong Prompt Truncation Gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("padding_side", ["right", "left"])
def test_prompt_and_padding_masked_even_when_pad_equals_eos(
    tmp_path: Path,
    padding_side: str,
) -> None:
    jsonl = _write_jsonl(
        tmp_path / "masking.jsonl",
        [
            _valid_row(
                "vid_1",
                system="Speak as 012.",
                user="What is a FoundUp?",
                assistant="Autonomous venture engine.",
                transcript_source="youtube_transcript",
            ),
            _valid_row(
                "vid_2",
                system="Speak as 012.",
                user="How do agents coordinate?",
                assistant="Through WSP protocols.",
                transcript_source="whisper_transcript",
            ),
        ],
    )

    tok = SyntheticChatTokenizer(
        pad_token="<|im_end|>",
        eos_token="<|im_end|>",
        padding_side=padding_side,
    )
    assert tok.pad_token_id == tok.eos_token_id

    cfg = VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=32, eval_ratio=0.5)
    trainer = VoiceLoRATrainer(cfg)
    trainer.tokenizer = tok
    trainer.load_data()

    assert trainer.train_dataset is not None
    assert trainer.eval_dataset is not None

    all_items = list(trainer.train_dataset) + list(trainer.eval_dataset)
    assert len(all_items) == 2

    expected_assistant_phrases = {
        tuple(tok.encode_text("Autonomous venture engine.<|im_end|>\n")),
        tuple(tok.encode_text("Through WSP protocols.<|im_end|>\n")),
    }

    observed_supervised: set[tuple[int, ...]] = set()
    for sample in all_items:
        input_ids = sample["input_ids"]
        attention_mask = sample["attention_mask"]
        labels = sample["labels"]

        assert input_ids.shape == (32,)
        assert attention_mask.shape == (32,)
        assert labels.shape == (32,)
        assert input_ids.data_ptr() != labels.data_ptr()

        # Every padding position MUST be -100 even though pad_token_id == eos_token_id
        pad_positions = attention_mask == 0
        assert int(pad_positions.sum().item()) > 0
        assert torch.all(labels[pad_positions] == IGNORE_INDEX)

        # Supervised positions equal ONLY assistant reply + closing EOS/newline
        supervised_tokens = tuple(labels[labels != IGNORE_INDEX].tolist())
        assert len(supervised_tokens) > 0
        assert tok.eos_token_id in supervised_tokens
        observed_supervised.add(supervised_tokens)

        active_labels = labels[attention_mask == 1]
        prompt_masked_prefix = active_labels[: len(active_labels) - len(supervised_tokens)]
        assert len(prompt_masked_prefix) > 0
        assert torch.all(prompt_masked_prefix == IGNORE_INDEX)

    assert observed_supervised == expected_assistant_phrases


def test_overlong_prompt_truncating_assistant_fails_closed_against_nan_loss(
    tmp_path: Path,
) -> None:
    long_question = " ".join(f"token{i}" for i in range(40))
    jsonl = _write_jsonl(
        tmp_path / "overlong.jsonl",
        [
            _valid_row("vid_1", user="short prompt", assistant="short reply"),
            _valid_row("vid_2", user=long_question, assistant="truncated away"),
        ],
    )

    cfg = VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=28)
    trainer = VoiceLoRATrainer(cfg)
    trainer.tokenizer = SyntheticChatTokenizer()

    with pytest.raises(ValueError, match=r"Overlong prompt on line 2.*zero supervised"):
        trainer.load_data()


def test_naive_template_ignoring_add_generation_prompt_still_masks_assistant_header(
    tmp_path: Path,
) -> None:
    class NaiveTokenizer(SyntheticChatTokenizer):
        def apply_chat_template(
            self,
            messages: list[dict[str, str]],
            tokenize: bool = False,
            add_generation_prompt: bool = False,
        ) -> str | list[int]:
            rendered = "".join(f"{m['role']}: {m['content']}\n" for m in messages)
            return self.encode_text(rendered) if tokenize else rendered

    jsonl = _write_jsonl(
        tmp_path / "naive.jsonl",
        [
            _valid_row("v1", system="sys", user="hi", assistant="authentic reply"),
            _valid_row("v2", system="sys", user="yo", assistant="second reply"),
        ],
    )
    tok = NaiveTokenizer(pad_token="<|im_end|>", eos_token="<|im_end|>")
    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=24, eval_ratio=0.5))
    trainer.tokenizer = tok
    trainer.load_data()

    assert trainer.train_dataset is not None and trainer.eval_dataset is not None
    for item in list(trainer.train_dataset) + list(trainer.eval_dataset):
        supervised = tuple(item["labels"][item["labels"] != IGNORE_INDEX].tolist())
        # Neither "assistant:" header nor prompt words appear in supervised labels
        assert tok._id_for("assistant:") not in supervised
        assert tok._id_for("sys") not in supervised


# ---------------------------------------------------------------------------
# 4. Group-Disjoint Held-Out Evaluation Split & Trainer Wiring
# ---------------------------------------------------------------------------


def test_group_split_prevents_video_id_leakage_and_is_deterministic(
    tmp_path: Path,
) -> None:
    rows = []
    for vid_idx in range(1, 6):
        video_id = f"yt_video_{vid_idx:02d}"
        for seg_idx in range(3):
            rows.append(
                _valid_row(
                    video_id,
                    user=f"Prompt {seg_idx} for {video_id}",
                    assistant=f"Verbatim response segment {seg_idx} from {video_id}.",
                )
            )
    jsonl = _write_jsonl(tmp_path / "grouped.jsonl", rows)

    cfg = VoiceTrainingConfig(
        data_path=str(jsonl),
        max_seq_length=48,
        eval_ratio=0.25,
        split_seed=123,
    )
    trainer_a = VoiceLoRATrainer(cfg)
    trainer_a.tokenizer = SyntheticChatTokenizer()
    trainer_a.load_data()

    trainer_b = VoiceLoRATrainer(cfg)
    trainer_b.tokenizer = SyntheticChatTokenizer()
    trainer_b.load_data()

    assert trainer_a.train_dataset is not None
    assert trainer_a.eval_dataset is not None
    assert len(trainer_a.train_dataset) > 0
    assert len(trainer_a.eval_dataset) > 0
    assert len(trainer_a.train_dataset) + len(trainer_a.eval_dataset) == 15

    train_groups = set(trainer_a.train_dataset.group_ids)
    eval_groups = set(trainer_a.eval_dataset.group_ids)
    assert train_groups.isdisjoint(eval_groups)
    assert train_groups | eval_groups == {f"yt_video_{i:02d}" for i in range(1, 6)}

    assert trainer_a.train_dataset.group_ids == trainer_b.train_dataset.group_ids
    assert trainer_a.eval_dataset.group_ids == trainer_b.eval_dataset.group_ids
    assert set(trainer_a.train_dataset[0].keys()) == {"input_ids", "attention_mask", "labels"}


def test_single_video_id_across_multiple_rows_fails_closed_against_split_leakage(
    tmp_path: Path,
) -> None:
    jsonl = _write_jsonl(
        tmp_path / "single_video.jsonl",
        [
            _valid_row("same_vid", user="q1", assistant="seg 1"),
            _valid_row("same_vid", user="q2", assistant="seg 2"),
            _valid_row("same_vid", user="q3", assistant="seg 3"),
        ],
    )
    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=32))
    trainer.tokenizer = SyntheticChatTokenizer()

    with pytest.raises(ValueError, match="at least 2 distinct source/video groups"):
        trainer.load_data()


def test_conflicting_group_ids_on_record_rejected(tmp_path: Path) -> None:
    jsonl = _write_jsonl(
        tmp_path / "conflict_id.jsonl",
        [
            _valid_row("vid_top", user="q1", assistant="seg 1", metadata={"video_id": "vid_nested_other"}),
            _valid_row("vid_2", user="q2", assistant="seg 2"),
        ],
    )
    with pytest.raises(ValueError, match="Conflicting source/video group IDs on line 1"):
        load_and_validate_jsonl(jsonl)


def test_train_wires_eval_dataset_and_epoch_eval_strategy_to_trainer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jsonl = _write_jsonl(
        tmp_path / "train_wire.jsonl",
        [
            _valid_row(None, user="q1", assistant="answer one", source_id="src_1"),
            _valid_row(None, user="q2", assistant="answer two", source_id="src_1"),
            _valid_row(None, user="q3", assistant="answer three", source_id="src_2"),
            _valid_row(None, user="q4", assistant="answer four", source_id="src_3"),
        ],
    )
    out_dir = tmp_path / "out"
    captured: dict[str, Any] = {}

    class StubModel:
        def __init__(self) -> None:
            self.saved_to: list[str] = []

        def save_pretrained(self, path: str) -> None:
            self.saved_to.append(path)

    class StubTrainingArguments:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            captured["training_args"] = kwargs

    class StubTrainer:
        def __init__(self, **kwargs: Any) -> None:
            captured["trainer_init"] = kwargs

        def train(self) -> None:
            captured["train_called"] = True

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setitem(lora_trainer.__dict__, "TrainingArguments", StubTrainingArguments)
    monkeypatch.setitem(lora_trainer.__dict__, "Trainer", StubTrainer)

    cfg = VoiceTrainingConfig(
        data_path=str(jsonl),
        output_dir=str(out_dir),
        max_seq_length=32,
        use_4bit=False,
    )
    trainer = VoiceLoRATrainer(cfg)
    trainer.model = StubModel()
    trainer.tokenizer = SyntheticChatTokenizer()

    adapter_path = trainer.train()

    assert captured["train_called"] is True
    assert captured["training_args"]["eval_strategy"] == "epoch"
    assert captured["training_args"]["save_strategy"] == "epoch"
    assert captured["training_args"]["fp16"] is False
    assert captured["training_args"]["optim"] == "adamw_torch"

    trainer_kwargs = captured["trainer_init"]
    assert trainer_kwargs["train_dataset"] is trainer.train_dataset
    assert trainer_kwargs["eval_dataset"] is trainer.eval_dataset
    assert len(trainer_kwargs["train_dataset"]) > 0
    assert len(trainer_kwargs["eval_dataset"]) > 0
    assert set(trainer.train_dataset.group_ids).isdisjoint(set(trainer.eval_dataset.group_ids))
    assert Path(adapter_path) == out_dir / "voice_lora"
    assert trainer.model.saved_to == [str(out_dir / "voice_lora")]
    assert trainer.tokenizer.saved_to == [str(out_dir / "voice_lora")]


# ---------------------------------------------------------------------------
# 5. Audit-Delta Adversarial Seams: Contradictory Metadata, Mislabeled
#    Summaries, Missing/Mixed Speakers, and Invalid/Nonmonotonic Timestamps
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides,expected_pattern",
    [
        ({"metadata": {"training_eligible": False}}, "training_eligible"),
        ({"metadata": {"provenance": {"training_eligible": False}}}, "training_eligible"),
        ({"transcript_source": "whisper_transcript", "metadata": {"indexer": "gemini"}}, "provenance"),
        (
            {"transcript_source": "youtube_transcript", "metadata": {"transcript_source": "whisper_transcript"}},
            "Contradictory metadata",
        ),
        (
            {"transcript_source": "youtube_transcript", "audio": {"extraction_method": "whisper_asr"}},
            "Contradictory transcript provenance families",
        ),
        ({"channel": "undaodu", "metadata": {"channel": "move2japan"}}, "Contradictory channel"),
        ({"channel": "antifafm"}, "Restricted music"),
        ({"consent": True, "metadata": {"consent": False}}, "Unconsented"),
        ({"consent": True, "metadata": {"consent": None}}, "Invalid 'consent'"),
    ],
)
def test_adversarial_contradictory_metadata_fails_closed(
    tmp_path: Path,
    overrides: dict[str, Any],
    expected_pattern: str,
) -> None:
    jsonl = _write_jsonl(
        tmp_path / "contradictory.jsonl",
        [
            _valid_row("v1", user="q0", assistant="First-person verbatim."),
            _valid_row("v2", **overrides),
        ],
    )
    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=32))
    trainer.tokenizer = SyntheticChatTokenizer()
    with pytest.raises(ValueError, match=f"line 2.*{expected_pattern}|{expected_pattern}.*line 2"):
        trainer.load_data()


@pytest.mark.parametrize(
    "overrides,expected_pattern",
    [
        ({"model": "gemini-2.0-flash"}, "Mislabeled summary model"),
        (
            {"transcript_source": "whisper_transcript", "metadata": {"provenance": {"teacher_model": "gemini-1.5-pro"}}},
            "Mislabeled summary model",
        ),
        ({"metadata": {"gemini_summary": "summary text"}}, "Mislabeled summary payload"),
        ({"is_verbatim": False}, "Non-verbatim"),
        (
            {"assistant": "The speaker introduces FoundUps and explains token mechanics."},
            "Mislabeled summary as transcript",
        ),
        (
            {"transcript_source": "whisper_transcript", "assistant": "Opening overview. The creator discusses living in Japan."},
            "Mislabeled summary as transcript",
        ),
        (
            {"assistant": "In this video, 012 explains recursive agent protocols."},
            "Mislabeled summary as transcript",
        ),
    ],
)
def test_adversarial_summaries_mislabeled_as_transcripts_fail_closed(
    tmp_path: Path,
    overrides: dict[str, Any],
    expected_pattern: str,
) -> None:
    jsonl = _write_jsonl(
        tmp_path / "mislabeled.jsonl",
        [
            _valid_row("v1", user="q0", assistant="Authentic first-person line."),
            _valid_row("v2", **overrides),
        ],
    )
    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=32))
    trainer.tokenizer = SyntheticChatTokenizer()
    with pytest.raises(ValueError, match=f"line 2.*{expected_pattern}|{expected_pattern}.*line 2"):
        trainer.load_data()


@pytest.mark.parametrize(
    "overrides,expected_pattern",
    [
        ({"speaker": "unknown"}, "Unknown speaker"),
        ({"speaker": ""}, "Missing or blank speaker"),
        ({"speaker": None}, "Missing or blank speaker"),
        ({"metadata": {"speaker_status": "unknown"}}, "Unverified speaker_status"),
        ({"speaker": "012", "speaker_verified": False}, "Unverified speaker"),
        ({"speaker": "012", "speaker_status": "unverified_label"}, "Unverified speaker_status"),
        ({"speaker": "Scott Ford (CEO)"}, "Non-principal or mixed speaker"),
        ({"speaker": "012 & Guest"}, "Non-principal or mixed speaker"),
        ({"speakers": ["012", "Guest"]}, "Mixed, unknown, or non-principal speakers"),
        ({"has_mixed_speakers": True}, "Mixed or unknown speakers"),
        ({"has_unknown_speakers": True}, "Mixed or unknown speakers"),
        ({"speaker": "012", "metadata": {"speaker": "undaodu"}}, "Contradictory speaker"),
    ],
)
def test_adversarial_missing_unverified_and_mixed_speakers_fail_closed(
    tmp_path: Path,
    overrides: dict[str, Any],
    expected_pattern: str,
) -> None:
    jsonl = _write_jsonl(
        tmp_path / "speakers.jsonl",
        [
            _valid_row("v1", user="q0", assistant="Authentic utterance."),
            _valid_row("v2", **overrides),
        ],
    )
    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=32))
    trainer.tokenizer = SyntheticChatTokenizer()
    with pytest.raises(ValueError, match=f"line 2.*{expected_pattern}|{expected_pattern}.*line 2"):
        trainer.load_data()


@pytest.mark.parametrize(
    "row_specs,expected_pattern",
    [
        ([("v1", {}), '{"user": "q1", "assistant": "ok", "video_id": "v2", "t_start": NaN}'], r"Non-finite JSON constant"),
        ([("v1", {}), '{"user": "q1", "assistant": "ok", "video_id": "v2", "t_end": Infinity}'], r"Non-finite JSON constant"),
        ([("v1", {}), ("v2", {"t_start": "01:99"})], r"Invalid colon timestamp"),
        ([("v1", {}), ("v2", {"t_start": "01:75:00"})], r"Invalid colon timestamp"),
        ([("v1", {}), ("v2", {"t_start": -2.5})], r"negative timestamp"),
        ([("v1", {}), ("v2", {"t_start": True})], r"boolean timestamp"),
        ([("v1", {}), ("v2", {"t_start": 30.0, "t_end": 10.0})], r"Inverted timestamps"),
        ([("v1", {}), ("v2", {"t_start": None, "t_end": 15.0})], r"Dangling end timestamp"),
        ([("v1", {}), ("v2", {"t_start": 10.0, "metadata": {"start": 22.0}})], r"Contradictory start timestamps"),
        (
            [
                ("v1", {"assistant": "seg a", "t_start": 30.0, "t_end": 40.0}),
                ("v1", {"assistant": "seg b", "t_start": 10.0, "t_end": 20.0}),
                ("v2", {"assistant": "seg c", "t_start": 0.0, "t_end": 5.0}),
            ],
            r"Nonmonotonic timestamps on line 2",
        ),
        (
            [
                ("v1", {"assistant": "seg a", "t_start": 10.0, "t_end": 30.0}),
                ("v1", {"assistant": "seg b", "t_start": 20.0, "t_end": 40.0}),
                ("v2", {"assistant": "seg c", "t_start": 0.0, "t_end": 5.0}),
            ],
            r"Nonmonotonic overlapping timestamps on line 2",
        ),
    ],
)
def test_adversarial_invalid_dangling_inverted_and_nonmonotonic_timestamps_fail_closed(
    tmp_path: Path,
    row_specs: list[str | tuple[str, dict[str, Any]]],
    expected_pattern: str,
) -> None:
    raw_rows: list[str | dict[str, Any]] = [
        spec if isinstance(spec, str) else _valid_row(spec[0], **spec[1])
        for spec in row_specs
    ]
    jsonl = _write_jsonl(tmp_path / "bad_timestamps.jsonl", raw_rows)
    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=32))
    trainer.tokenizer = SyntheticChatTokenizer()
    with pytest.raises(ValueError) as exc_info:
        trainer.load_data()
    msg = str(exc_info.value)
    assert "line 2" in msg
    assert re.search(expected_pattern, msg), f"Expected {expected_pattern!r} in {msg!r}"


# ---------------------------------------------------------------------------
# 6. Direct-Loader Fail-Closed Admission vs Read-Only Diagnostic Inspection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "legacy_unlabeled_row",
    [
        {"user": "q", "assistant": "I built this autonomous system myself."},
        {
            "system": "You are 012's Digital Twin.",
            "user": "Explain FoundUps",
            "assistant": "I built FoundUps as autonomous venture engines.",
            "source": "yt_vid_01",
            "type": "quotable",
        },
        {
            "system": "You are 012's Digital Twin.",
            "user": "Explain FoundUps",
            "assistant": "I built FoundUps as autonomous venture engines.",
            "source": "unknown",
            "type": "quotable",
        },
        {
            "system": "You are 012's Digital Twin.",
            "user": "Continue",
            "assistant": "We build layer by layer without vibecoding.",
            "source": "012.txt",
            "type": "012_history",
        },
    ],
)
def test_direct_loader_rejects_unlabeled_and_legacy_producer_rows_across_all_entrypoints(
    tmp_path: Path,
    legacy_unlabeled_row: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="line 1"):
        validate_sft_record(legacy_unlabeled_row, 1)

    with pytest.raises(ValueError, match="line 1"):
        lora_trainer._validate_record(legacy_unlabeled_row, 1)

    jsonl = _write_jsonl(
        tmp_path / "legacy_unlabeled.jsonl",
        [_valid_row("vid_ok"), legacy_unlabeled_row],
    )
    with pytest.raises(ValueError, match="line 2"):
        load_and_validate_records(jsonl)

    with pytest.raises(ValueError, match="line 2"):
        load_and_validate_jsonl(jsonl)

    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=32))
    trainer.tokenizer = SyntheticChatTokenizer()
    with pytest.raises(ValueError, match="line 2"):
        trainer.load_data()


@pytest.mark.parametrize(
    "vid,overrides,omit_keys,expected_pattern",
    [
        ("v2", {}, ("training_eligible",), r"Missing required training_eligible=True"),
        ("v2", {}, ("transcript_source",), r"Missing required verbatim provenance"),
        ("v2", {"transcript_source": "unlisted_custom_pipeline"}, (), r"Missing required verbatim provenance"),
        ("v2", {}, ("consent",), r"Missing required explicit positive consent=True"),
        ("v2", {"consent": "yes"}, (), r"must be boolean True"),
        ("v2", {"consent": 1}, (), r"Invalid 'consent'"),
        ("v2", {}, ("speaker", "speaker_verified"), r"Missing required principal speaker attribution"),
        ("v2", {}, ("speaker_verified",), r"Unverified speaker label \('012'\); verified speaker required"),
        (None, {}, (), r"Missing required source/video group ID"),
        (None, {"source": "unknown"}, (), r"Placeholder or unknown source/video group ID"),
        ("__default__", {}, (), r"Placeholder or unknown source/video group ID"),
        (None, {"source_id": "placeholder"}, (), r"Placeholder or unknown source/video group ID"),
    ],
)
def test_direct_loader_requires_each_of_five_explicit_admission_proofs(
    tmp_path: Path,
    vid: str | None,
    overrides: dict[str, Any],
    omit_keys: tuple[str, ...],
    expected_pattern: str,
) -> None:
    incomplete_row = {k: v for k, v in _valid_row(vid, **overrides).items() if k not in omit_keys}
    jsonl = _write_jsonl(tmp_path / "missing_proof.jsonl", [_valid_row("v1"), incomplete_row])
    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=32))
    trainer.tokenizer = SyntheticChatTokenizer()
    with pytest.raises(ValueError) as exc_info:
        trainer.load_data()
    msg = str(exc_info.value)
    assert "line 2" in msg
    assert re.search(expected_pattern, msg), f"Expected {expected_pattern!r} in {msg!r}"


@pytest.mark.parametrize("bad_group_id", [None, "", "   ", "unknown", "UNKNOWN", "__default__", "placeholder", "none"])
def test_split_grouped_examples_rejects_missing_or_placeholder_group_id_without_row_fallback(
    bad_group_id: str | None,
) -> None:
    dummy_features = {
        "input_ids": torch.tensor([1, 2], dtype=torch.long),
        "attention_mask": torch.tensor([1, 1], dtype=torch.long),
        "labels": torch.tensor([IGNORE_INDEX, 2], dtype=torch.long),
    }
    items = [
        (bad_group_id, dummy_features, {"line_num": 1}),
        ("vid_valid", dummy_features, {"line_num": 2}),
    ]
    with pytest.raises(ValueError, match="Missing or placeholder group_id"):
        lora_trainer._split_grouped_examples(items, eval_ratio=0.5, seed=42)


@pytest.mark.parametrize("bad_flag", [False, 0, 1, "true", None])
def test_admission_invariant_flags_locked_in_config_and_validator_entrypoints(
    tmp_path: Path,
    bad_flag: Any,
) -> None:
    with pytest.raises(ValueError, match="require_verified_speaker must be True"):
        VoiceTrainingConfig(require_verified_speaker=bad_flag)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="require_explicit_admission must be True"):
        VoiceTrainingConfig(require_explicit_admission=bad_flag)  # type: ignore[arg-type]

    row = _valid_row("v1")
    jsonl = _write_jsonl(tmp_path / "valid.jsonl", [_valid_row("v1"), _valid_row("v2")])

    with pytest.raises(ValueError, match="require_verified_speaker must be True"):
        validate_sft_record(row, 1, require_verified_speaker=bad_flag)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="require_explicit_admission must be True"):
        validate_sft_record(row, 1, require_explicit_admission=bad_flag)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="require_verified_speaker must be True"):
        load_and_validate_records(jsonl, require_verified_speaker=bad_flag)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="require_explicit_admission must be True"):
        load_and_validate_jsonl(jsonl, require_explicit_admission=bad_flag)  # type: ignore[arg-type]


def test_post_init_mutation_of_admission_flags_rejected_before_load_data_and_train(
    tmp_path: Path,
) -> None:
    jsonl = _write_jsonl(tmp_path / "valid.jsonl", [_valid_row("v1"), _valid_row("v2")])
    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=32, use_4bit=False))
    trainer.tokenizer = SyntheticChatTokenizer()

    trainer.config.require_verified_speaker = False
    with pytest.raises(ValueError, match="require_verified_speaker must be True"):
        trainer.load_data()

    trainer.config.require_verified_speaker = True
    trainer.config.require_explicit_admission = False
    with pytest.raises(ValueError, match="require_explicit_admission must be True"):
        trainer.load_data()
    with pytest.raises(ValueError, match="require_explicit_admission must be True"):
        trainer.train()


def test_inspect_sft_record_preserves_none_unknown_without_fabricating_012_or_zero(
    tmp_path: Path,
) -> None:
    bare = inspect_sft_record({"user": "q1", "assistant": "First-person speech without metadata."}, line_num=7)
    assert isinstance(bare, InspectedVoiceRecord)
    assert bare.line_num == 7
    assert bare.admissible_for_training is False
    assert bare.speaker is None
    assert bare.speaker_status == "unknown"
    assert bare.t_start is None
    assert bare.t_end is None
    assert bare.timestamp_status == "unknown"
    assert bare.group_id is None
    assert bare.training_eligible is None
    assert bare.consent_granted is None
    assert bare.verbatim_families == ()
    assert bare.rejection_reasons == (
        "missing_training_eligible",
        "missing_verbatim_provenance",
        "missing_explicit_consent",
        "missing_speaker_attribution",
        "missing_group_id",
    )

    nemo_unknown = inspect_sft_record(
        {
            "system": "You are 012's Digital Twin.",
            "user": "Explain FoundUps",
            "assistant": "I built FoundUps as autonomous engines.",
            "source": "unknown",
            "type": "quotable",
        },
        line_num=3,
    )
    assert nemo_unknown.admissible_for_training is False
    assert nemo_unknown.group_id is None
    assert nemo_unknown.speaker is None
    assert nemo_unknown.speaker_status == "unknown"
    assert "invalid_or_placeholder_group_id" in nemo_unknown.rejection_reasons

    unverified_spk = inspect_sft_record(
        {k: v for k, v in _valid_row("vid_x").items() if k != "speaker_verified"},
        line_num=4,
    )
    assert unverified_spk.admissible_for_training is False
    assert unverified_spk.speaker == "012"
    assert unverified_spk.speaker_status == "unverified_label"
    assert unverified_spk.rejection_reasons == ("unverified_speaker_attribution",)

    admissible_absent_ts = _valid_row("v1", user="q1", assistant="First verified answer.")
    admissible_partial_ts = _valid_row("v2", user="q2", assistant="Second verified answer.", t_start=25.0, t_end=None)

    insp_ok = inspect_sft_record(admissible_absent_ts, line_num=1)
    assert insp_ok.admissible_for_training is True
    assert insp_ok.rejection_reasons == ()
    assert insp_ok.speaker == "012"
    assert insp_ok.speaker_status == "verified"
    assert insp_ok.t_start is None
    assert insp_ok.t_end is None
    assert insp_ok.timestamp_status == "unknown"

    jsonl = _write_jsonl(tmp_path / "admissible_absent_ts.jsonl", [admissible_absent_ts, admissible_partial_ts])
    trainer = VoiceLoRATrainer(VoiceTrainingConfig(data_path=str(jsonl), max_seq_length=32, eval_ratio=0.5))
    trainer.tokenizer = SyntheticChatTokenizer()
    trainer.load_data()
    assert trainer.train_dataset is not None and trainer.eval_dataset is not None
    by_vid = {
        lin["group_id"]: lin
        for lin in (trainer.train_dataset.record_lineage + trainer.eval_dataset.record_lineage)
    }
    assert by_vid["v1"]["speaker"] == "012"
    assert by_vid["v1"]["speaker_status"] == "verified"
    assert by_vid["v1"]["t_start"] is None
    assert by_vid["v1"]["t_end"] is None
    assert by_vid["v1"]["timestamp_status"] == "unknown"

    assert by_vid["v2"]["speaker"] == "012"
    assert by_vid["v2"]["speaker_status"] == "verified"
    assert by_vid["v2"]["t_start"] == 25.0
    assert by_vid["v2"]["t_end"] is None
    assert by_vid["v2"]["timestamp_status"] == "partial_start_only"


def test_wsp62_file_and_function_size_bounds() -> None:
    src_dir = Path(lora_trainer.__file__).parent
    for filename in ("lora_trainer.py", "lora_record_validator.py"):
        source_path = src_dir / filename
        source = source_path.read_text(encoding="utf-8")
        lines = source.splitlines()
        assert len(lines) <= 500, f"{filename} exceeds 500 lines ({len(lines)})"

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                span = (node.end_lineno or node.lineno) - node.lineno + 1
                assert span <= 50, f"{filename}:{node.name} exceeds WSP 62 bound ({span} lines)"
