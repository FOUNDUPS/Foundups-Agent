"""QLoRA Voice Training for Digital Twin.

Fine-tunes a small LLM on 012's verbatim voice patterns with strict offline and
supply-chain safety (WSP 71), fail-closed direct-loader JSONL admission,
prompt/padding label masking, and group-disjoint held-out evaluation.
"""
from __future__ import annotations

import importlib.metadata as importlib_metadata
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import torch
from torch.utils.data import Dataset

from .lora_record_validator import (
    DEFAULT_SYSTEM_PROMPT,
    DISALLOWED_CONSENT_VALUES,
    DISALLOWED_PROVENANCE_VALUES,
    PLACEHOLDER_GROUP_IDS,
    InspectedVoiceRecord,
    ValidatedVoiceRecord,
    inspect_sft_record,
    load_and_validate_records,
    validate_sft_record,
)

logger = logging.getLogger(__name__)

IGNORE_INDEX = -100
ALLOWED_COMPUTE_DTYPES = frozenset({"float16", "bfloat16", "float32"})
_TRANSFORMERS_EXPORTS = frozenset({
    "AutoModelForCausalLM", "AutoTokenizer", "BitsAndBytesConfig", "Trainer", "TrainingArguments",
})


def _missing_peft_factory(symbol_name: str):
    def _missing(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(f"Missing required dependency 'peft' ({symbol_name}) for LoRA training.")
    _missing.__name__ = symbol_name
    return _missing


try:
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
except ImportError:
    LoraConfig = _missing_peft_factory("LoraConfig")  # type: ignore[assignment]
    get_peft_model = _missing_peft_factory("get_peft_model")  # type: ignore[assignment]
    prepare_model_for_kbit_training = _missing_peft_factory("prepare_model_for_kbit_training")  # type: ignore[assignment]


def __getattr__(name: str) -> Any:
    if name in _TRANSFORMERS_EXPORTS:
        import transformers
        value = getattr(transformers, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _is_package_installed(package_name: str) -> bool:
    try:
        importlib_metadata.version(package_name)
        return True
    except importlib_metadata.PackageNotFoundError:
        return False


class VoiceDataset(Dataset):
    """PyTorch Dataset of tokenized voice SFT examples with verified lineage."""

    def __init__(
        self,
        data: list[dict[str, torch.Tensor]],
        group_ids: Optional[list[str]] = None,
        record_lineage: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self.data = data
        self.group_ids: list[str] = list(group_ids) if group_ids is not None else []
        self.record_lineage: list[dict[str, Any]] = list(record_lineage) if record_lineage is not None else []

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return self.data[idx]


@dataclass
class VoiceTrainingConfig:
    """Configuration for voice LoRA training (locked fail-closed admission)."""

    base_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    local_files_only: bool = True
    trust_remote_code: bool = False
    data_path: str = "training_data/nemo_test/voice_sft.jsonl"
    max_seq_length: int = 512
    eval_ratio: float = 0.2
    split_seed: int = 42
    require_verified_speaker: bool = True
    require_explicit_admission: bool = True
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    target_modules: list = field(default_factory=lambda: ["q_proj", "v_proj"])
    output_dir: str = "training_output/voice_lora"
    epochs: int = 3
    batch_size: int = 1
    gradient_accumulation: int = 8
    learning_rate: float = 2e-4
    use_4bit: bool = True
    bnb_4bit_compute_dtype: str = "float16"

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Enforce hard security, offline, admission, dtype, and split invariants."""
        if type(self.trust_remote_code) is not bool or self.trust_remote_code is not False:
            raise ValueError("Security violation (WSP 71): trust_remote_code must be False.")
        if type(self.require_verified_speaker) is not bool or self.require_verified_speaker is not True:
            raise ValueError("Admission invariant: require_verified_speaker must be True.")
        if type(self.require_explicit_admission) is not bool or self.require_explicit_admission is not True:
            raise ValueError("Admission invariant: require_explicit_admission must be True.")
        for bool_field in ("local_files_only", "use_4bit"):
            if type(getattr(self, bool_field)) is not bool:
                raise ValueError(f"{bool_field} must be a boolean.")
        if not isinstance(self.base_model, str) or not self.base_model.strip():
            raise ValueError("base_model must be a non-empty string.")
        if not isinstance(self.eval_ratio, (int, float)) or isinstance(self.eval_ratio, bool):
            raise ValueError("eval_ratio must be a float in (0.0, 1.0).")
        if not (0.0 < float(self.eval_ratio) < 1.0):
            raise ValueError("eval_ratio must be strictly between 0.0 and 1.0.")
        for field_name in ("max_seq_length", "epochs", "batch_size", "gradient_accumulation"):
            val = getattr(self, field_name)
            if type(val) is not int or val <= 0:
                raise ValueError(f"{field_name} must be a positive integer.")
        if self.bnb_4bit_compute_dtype not in ALLOWED_COMPUTE_DTYPES:
            raise ValueError(f"Unsupported bnb_4bit_compute_dtype: {self.bnb_4bit_compute_dtype!r}.")


def _validate_record(
    record: Any,
    line_num: int,
    *,
    require_verified_speaker: bool = True,
    require_explicit_admission: bool = True,
) -> tuple[dict[str, str], str]:
    """Fail-closed training-boundary record validator returning (messages, group_id)."""
    validated = validate_sft_record(
        record,
        line_num,
        require_verified_speaker=require_verified_speaker,
        require_explicit_admission=require_explicit_admission,
    )
    return validated.messages, validated.group_id


def load_and_validate_jsonl(
    data_path: str | Path,
    *,
    require_verified_speaker: bool = True,
    require_explicit_admission: bool = True,
) -> list[tuple[int, dict[str, str], str]]:
    """Fail-closed JSONL training-boundary validator."""
    records = load_and_validate_records(
        data_path,
        require_verified_speaker=require_verified_speaker,
        require_explicit_admission=require_explicit_admission,
    )
    return [(rec.line_num, rec.messages, rec.group_id) for rec in records]


def _to_1d_long_tensor(raw: Any) -> torch.Tensor:
    tensor = raw.clone() if isinstance(raw, torch.Tensor) else torch.tensor(raw)
    if tensor.ndim == 2:
        if tensor.shape[0] != 1:
            raise ValueError(f"Expected batch size 1 from single-example tokenization, got {tuple(tensor.shape)}.")
        tensor = tensor.squeeze(0)
    elif tensor.ndim != 1:
        raise ValueError(f"Expected 1D or 2D tensor from tokenizer, got shape {tuple(tensor.shape)}.")
    return tensor.to(dtype=torch.long)


def _format_prompt_and_full_text(tokenizer: Any, messages: list[dict[str, str]]) -> tuple[str, str]:
    prompt_messages = messages[:2]
    use_template = hasattr(tokenizer, "apply_chat_template") and getattr(tokenizer, "chat_template", "default") is not None
    if use_template:
        prompt_text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
        full_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        if full_text.startswith(prompt_text):
            assistant_pos = full_text.find(messages[2]["content"], len(prompt_text))
            if assistant_pos != -1:
                prompt_text = full_text[:assistant_pos]
        return prompt_text, full_text
    prompt_text = (
        f"<|im_start|>system\n{messages[0]['content']}<|im_end|>\n"
        f"<|im_start|>user\n{messages[1]['content']}<|im_end|>\n<|im_start|>assistant\n"
    )
    return prompt_text, f"{prompt_text}{messages[2]['content']}<|im_end|>"


def _tokenize_and_mask_example(
    tokenizer: Any, messages: list[dict[str, str]], max_seq_length: int, line_num: int
) -> dict[str, torch.Tensor]:
    prompt_text, full_text = _format_prompt_and_full_text(tokenizer, messages)
    try:
        prompt_tokens = tokenizer(prompt_text, truncation=False, padding=False, return_tensors="pt")
    except TypeError:
        prompt_tokens = tokenizer(prompt_text, truncation=False, max_length=max_seq_length, padding=False, return_tensors="pt")
    prompt_ids = _to_1d_long_tensor(prompt_tokens["input_ids"])
    prompt_len = (
        int((_to_1d_long_tensor(prompt_tokens["attention_mask"]) == 1).sum().item())
        if "attention_mask" in prompt_tokens
        else int(prompt_ids.numel())
    )
    full_tokens = tokenizer(full_text, truncation=True, max_length=max_seq_length, padding="max_length", return_tensors="pt")
    input_ids = _to_1d_long_tensor(full_tokens["input_ids"])
    attention_mask = _to_1d_long_tensor(full_tokens["attention_mask"])

    labels = torch.full_like(input_ids, IGNORE_INDEX)
    active_indices = torch.nonzero(attention_mask == 1, as_tuple=False).flatten()
    if prompt_len < int(active_indices.numel()):
        supervised_indices = active_indices[prompt_len:]
        labels[supervised_indices] = input_ids[supervised_indices]
    if int((labels != IGNORE_INDEX).sum().item()) == 0:
        raise ValueError(
            f"Overlong prompt on line {line_num}: zero supervised assistant tokens remain "
            f"after truncation (prompt_tokens={prompt_len}, max_seq_length={max_seq_length})."
        )
    return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}


def _select_eval_group_keys(
    groups: dict[str, list[Any]], total_items: int, eval_ratio: float, seed: int
) -> set[str]:
    shuffled_keys = sorted(groups.keys())
    random.Random(seed).shuffle(shuffled_keys)
    target_eval_rows = max(1, round(total_items * eval_ratio))
    eval_keys: list[str] = []
    eval_row_count = 0
    for key in shuffled_keys:
        if len(shuffled_keys) - (len(eval_keys) + 1) < 1:
            break
        group_size = len(groups[key])
        if not eval_keys or (eval_row_count + group_size <= target_eval_rows):
            eval_keys.append(key)
            eval_row_count += group_size
            if eval_row_count >= target_eval_rows:
                break
    return set(eval_keys)


def _split_grouped_examples(
    items: list[tuple[Optional[str], dict[str, torch.Tensor], dict[str, Any]]],
    eval_ratio: float,
    seed: int,
) -> tuple[VoiceDataset, VoiceDataset]:
    groups: dict[str, list[tuple[str, dict[str, torch.Tensor], dict[str, Any]]]] = {}
    for raw_group_id, features, lineage in items:
        if not isinstance(raw_group_id, str) or not raw_group_id.strip() or raw_group_id.strip().lower() in PLACEHOLDER_GROUP_IDS:
            raise ValueError(f"Missing or placeholder group_id ({raw_group_id!r}); ungrouped examples cannot be split safely.")
        clean_group = raw_group_id.strip()
        groups.setdefault(f"group:{clean_group}", []).append((clean_group, features, lineage))
    if len(groups) < 2:
        raise ValueError(
            "Held-out evaluation requires at least 2 distinct source/video groups to prevent "
            f"train/eval leakage, got {len(groups)} group(s) across {len(items)} example(s)."
        )
    eval_key_set = _select_eval_group_keys(groups, len(items), eval_ratio, seed)
    train_data, train_groups, train_lin = [], [], []
    eval_data, eval_groups, eval_lin = [], [], []
    for key in sorted(groups.keys()):
        t_data, t_grp, t_lin = (eval_data, eval_groups, eval_lin) if key in eval_key_set else (train_data, train_groups, train_lin)
        for display_group, features, lineage in groups[key]:
            t_data.append(features)
            t_grp.append(display_group)
            t_lin.append(lineage)
    if not train_data or not eval_data or not set(train_groups).isdisjoint(set(eval_groups)):
        raise RuntimeError("Held-out split failed non-empty or disjointness invariant.")
    return VoiceDataset(train_data, train_groups, train_lin), VoiceDataset(eval_data, eval_groups, eval_lin)


class VoiceLoRATrainer:
    """Trains LoRA adapter for 012's voice patterns."""

    def __init__(self, config: VoiceTrainingConfig):
        config.validate()
        self.config = config
        self.model: Any = None
        self.tokenizer: Any = None
        self.dataset: Optional[VoiceDataset] = None
        self.train_dataset: Optional[VoiceDataset] = None
        self.eval_dataset: Optional[VoiceDataset] = None

    def check_runtime_readiness(self) -> dict[str, Any]:
        """Inspect host CUDA/package prerequisites without loading models or training."""
        self.config.validate()
        cuda_ok = bool(torch.cuda.is_available())
        pkgs = {n: _is_package_installed(n) for n in ("torch", "transformers", "peft", "accelerate", "bitsandbytes")}
        blockers = [f"missing_package:{req}" for req in ("transformers", "peft", "accelerate") if not pkgs[req]]
        if self.config.use_4bit and not cuda_ok:
            blockers.append("cuda_unavailable_for_4bit")
        if self.config.use_4bit and not pkgs["bitsandbytes"]:
            blockers.append("missing_package:bitsandbytes")
        return {
            "ready_for_training": not blockers, "cuda_available": cuda_ok, "packages": pkgs,
            "local_files_only": self.config.local_files_only, "trust_remote_code": self.config.trust_remote_code,
            "blockers": blockers,
        }

    def _build_bnb_config(self) -> Any:
        if not self.config.use_4bit:
            return None
        if not torch.cuda.is_available():
            raise RuntimeError("4-bit QLoRA training requires a CUDA GPU; set use_4bit=False or provide CUDA.")
        bnb_cls = globals().get("BitsAndBytesConfig") or __getattr__("BitsAndBytesConfig")
        try:
            return bnb_cls(
                load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=getattr(torch, self.config.bnb_4bit_compute_dtype),
            )
        except (ImportError, importlib_metadata.PackageNotFoundError) as exc:
            raise RuntimeError("4-bit QLoRA training requires 'bitsandbytes' to be installed.") from exc

    def load_model(self) -> None:
        """Load base model and LoRA adapter with strict offline and remote-code guards."""
        self.config.validate()
        logger.info("[TRAINER] Loading %s (local_files_only=%s)", self.config.base_model, self.config.local_files_only)
        tokenizer_cls = globals().get("AutoTokenizer") or __getattr__("AutoTokenizer")
        model_cls = globals().get("AutoModelForCausalLM") or __getattr__("AutoModelForCausalLM")
        self.tokenizer = tokenizer_cls.from_pretrained(
            self.config.base_model, trust_remote_code=False, local_files_only=self.config.local_files_only
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        bnb_config = self._build_bnb_config()
        model_kwargs: dict[str, Any] = {
            "device_map": "auto", "trust_remote_code": False, "local_files_only": self.config.local_files_only
        }
        if bnb_config is not None:
            model_kwargs["quantization_config"] = bnb_config
        self.model = model_cls.from_pretrained(self.config.base_model, **model_kwargs)
        if self.config.use_4bit:
            self.model = prepare_model_for_kbit_training(self.model)
        lora_config = LoraConfig(
            r=self.config.lora_r, lora_alpha=self.config.lora_alpha, lora_dropout=self.config.lora_dropout,
            target_modules=self.config.target_modules, bias="none", task_type="CAUSAL_LM",
        )
        self.model = get_peft_model(self.model, lora_config)
        if hasattr(self.model, "print_trainable_parameters"):
            self.model.print_trainable_parameters()
        logger.info("[TRAINER] Model loaded with LoRA")

    def load_data(self) -> None:
        """Validate, mask-tokenize, and group-split JSONL SFT data into train/eval sets."""
        self.config.validate()
        if self.tokenizer is None:
            raise RuntimeError("Tokenizer must be loaded before calling load_data().")
        logger.info("[TRAINER] Loading data from %s", self.config.data_path)
        validated_records = load_and_validate_records(
            self.config.data_path,
            require_verified_speaker=self.config.require_verified_speaker,
            require_explicit_admission=self.config.require_explicit_admission,
        )
        tokenized_items: list[tuple[Optional[str], dict[str, torch.Tensor], dict[str, Any]]] = []
        for rec in validated_records:
            messages = [
                {"role": "system", "content": rec.messages["system"]},
                {"role": "user", "content": rec.messages["user"]},
                {"role": "assistant", "content": rec.messages["assistant"]},
            ]
            tokenized_items.append((
                rec.group_id,
                _tokenize_and_mask_example(self.tokenizer, messages, self.config.max_seq_length, rec.line_num),
                rec.to_lineage_dict(),
            ))
        self.train_dataset, self.eval_dataset = _split_grouped_examples(
            tokenized_items, eval_ratio=self.config.eval_ratio, seed=self.config.split_seed
        )
        self.dataset = self.train_dataset
        logger.info("[TRAINER] Datasets ready: train=%d, eval=%d", len(self.train_dataset), len(self.eval_dataset))

    def _verify_ready_for_train(self) -> None:
        if self.model is None:
            self.load_model()
        if self.train_dataset is None or self.eval_dataset is None:
            self.load_data()
        if not self.train_dataset:
            raise ValueError("train_dataset must be non-empty.")
        if not self.eval_dataset:
            raise ValueError("Held-out eval_dataset must be non-empty.")
        if self.train_dataset.group_ids and not set(self.train_dataset.group_ids).isdisjoint(self.eval_dataset.group_ids):
            raise ValueError("Group leakage detected between train_dataset and eval_dataset.")

    def train(self) -> str:
        """Run training with mandatory held-out evaluation per epoch."""
        self.config.validate()
        self._verify_ready_for_train()
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        cuda_ok = bool(torch.cuda.is_available())
        optim_name = "paged_adamw_8bit" if (self.config.use_4bit and cuda_ok and _is_package_installed("bitsandbytes")) else "adamw_torch"
        training_args_cls = globals().get("TrainingArguments") or __getattr__("TrainingArguments")
        trainer_cls = globals().get("Trainer") or __getattr__("Trainer")
        training_args = training_args_cls(
            output_dir=str(output_dir), num_train_epochs=self.config.epochs,
            per_device_train_batch_size=self.config.batch_size, per_device_eval_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation, learning_rate=self.config.learning_rate,
            logging_steps=10, eval_strategy="epoch", save_strategy="epoch",
            fp16=bool(cuda_ok and self.config.bnb_4bit_compute_dtype == "float16"),
            bf16=bool(cuda_ok and self.config.bnb_4bit_compute_dtype == "bfloat16"),
            optim=optim_name, warmup_ratio=0.03, report_to="none",
        )
        trainer = trainer_cls(
            model=self.model, args=training_args, train_dataset=self.train_dataset, eval_dataset=self.eval_dataset
        )
        logger.info("[TRAINER] Starting training...")
        trainer.train()
        adapter_path = output_dir / "voice_lora"
        self.model.save_pretrained(str(adapter_path))
        self.tokenizer.save_pretrained(str(adapter_path))
        logger.info("[TRAINER] LoRA adapter saved to %s", adapter_path)
        return str(adapter_path)


def main() -> None:
    """Run voice LoRA training from CLI (requires explicit --confirm-consent)."""
    import argparse

    parser = argparse.ArgumentParser(description="Train LoRA for 012's voice")
    parser.add_argument("--data", default="training_data/nemo_test/voice_sft.jsonl")
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output", default="training_output/voice_lora")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--confirm-consent", action="store_true")
    args = parser.parse_args()
    if not args.confirm_consent:
        raise PermissionError("Training blocked: pass --confirm-consent only when authorized by 012.")
    logging.basicConfig(level=logging.INFO)
    config = VoiceTrainingConfig(
        base_model=args.model, data_path=args.data, output_dir=args.output,
        epochs=args.epochs, local_files_only=not args.allow_download, trust_remote_code=False,
    )
    adapter_path = VoiceLoRATrainer(config).train()
    print(f"\nTraining complete!\n   LoRA adapter: {adapter_path}")


if __name__ == "__main__":
    main()
