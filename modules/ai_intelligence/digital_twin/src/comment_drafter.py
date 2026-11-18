# -*- coding: utf-8 -*-
"""
Comment Drafter - Generate comments in 012's voice.

WSP Compliance:
    WSP 77: Agent Coordination (Digital Twin)
    WSP 84: Code Reuse (follows gemma_rag_inference.py patterns)
    WSP 91: DAE Observability (bracket logging)

Purpose:
    1. Retrieve top-k snippets from VoiceMemory
    2. Generate draft using Gemma LLM (or mock for tests)
    3. Apply StyleGuardrails
    4. Return CommentDraft
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.infrastructure.shared_utilities.local_model_selection import resolve_code_model_path
from .schemas import CommentDraft, Platform
from .style_guardrails import StyleGuardrails
from .voice_memory import VoiceMemory

logger = logging.getLogger(__name__)

# Default model paths (WSP 84: follows gemma_rag_inference.py)
# Local code model for generation (Qwen coder default).
DEFAULT_QWEN_PATH = resolve_code_model_path()


class LocalLLM:
    """
    LLM interface for comment draft generation.

    Supports:
    - Mock mode for testing (deterministic responses)
    - Qwen 1.5B for production generation (via llama_cpp)

    Architecture (WSP 77):
    - Qwen 1.5B: Text generation (~250ms, 1.5B params - good for writing)
    - Gemma 270M: Pattern matching (~50ms, 270M params - good for classification)

    WSP 84: Follows gemma_rag_inference.py loading pattern
    """

    def __init__(self, mock_mode: bool = False, model_path: Optional[Path] = None):
        """
        Initialize LLM.

        Args:
            mock_mode: If True, return deterministic mock responses (for tests)
            model_path: Path to local code GGUF model (default: LOCAL_MODEL_CODE_*)
        """
        self.mock_mode = mock_mode
        self.model_path = model_path or DEFAULT_QWEN_PATH
        self._llm = None

        if not mock_mode:
            self._initialize_qwen()

    def _initialize_qwen(self) -> bool:
        """Initialize Qwen 1.5B model via llama_cpp for text generation."""
        if self._llm is not None:
            return True

        if not self.model_path.exists():
            logger.warning(f"[DRAFTER-LLM] Model not found: {self.model_path}, falling back to mock mode")
            self.mock_mode = True
            return False

        try:
            from llama_cpp import Llama

            logger.info(f"[DRAFTER-LLM] Loading Qwen 1.5B from {self.model_path}")

            # Suppress llama.cpp loading noise (pattern from gemma_rag_inference.py)
            old_stdout, old_stderr = os.dup(1), os.dup(2)
            devnull = os.open(os.devnull, os.O_WRONLY)

            try:
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)

                self._llm = Llama(
                    model_path=str(self.model_path),
                    n_ctx=2048,  # Larger context for Qwen
                    n_threads=4,  # More threads for 1.5B model
                    n_gpu_layers=0,  # CPU-only
                    verbose=False
                )

            finally:
                os.dup2(old_stdout, 1)
                os.dup2(old_stderr, 2)
                os.close(devnull)
                os.close(old_stdout)
                os.close(old_stderr)

            logger.info("[DRAFTER-LLM] Qwen 1.5B loaded successfully")
            return True

        except ImportError:
            logger.warning("[DRAFTER-LLM] llama_cpp not installed, falling back to mock mode")
            self.mock_mode = True
            return False
        except Exception as e:
            logger.error(f"[DRAFTER-LLM] Failed to load Qwen: {e}")
            self.mock_mode = True
            return False

    def generate(
        self,
        prompt: str,
        context_snippets: List[str],
        max_tokens: int = 150,
        platform: str = "youtube",
        constraints: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate comment text from prompt + context using Qwen 1.5B.

        Args:
            prompt: Generation prompt with thread context
            context_snippets: Retrieved voice memory snippets for RAG
            max_tokens: Maximum output tokens (default 150 for comments)

        Returns:
            Generated comment text
        """
        if self.mock_mode:
            return self._mock_generate(prompt)

        platform_name = str(platform or "youtube").strip().lower()
        if platform_name == "linkedin":
            system_prompt = """Write a concise LinkedIn reply as 0102 operating in 012's voice.
Style: Direct, technical, grounded, useful.
Add one concrete point. No empty praise. No filler words.
No hashtags unless explicitly requested. Max 90 words."""
        else:
            system_prompt = """Write a 1-2 sentence reply as 012 (Michael Trauth).
Style: Direct, personal, helpful. Share real experience.
NO filler words. NO "Sure!" or "Great question!".
Max 50 words."""

        # Include RAG snippets as context
        context_str = ""
        if context_snippets:
            context_str = "\n\n012's experience:\n" + "\n".join(
                f"- {s[:80]}" for s in context_snippets[:2]
            )

        constraint_str = ""
        if constraints:
            constraint_lines = [f"- {k}: {v}" for k, v in constraints.items()]
            constraint_str = "\n\nConstraints:\n" + "\n".join(constraint_lines[:8])

        full_prompt = (
            f"{system_prompt}{context_str}{constraint_str}\n\n"
            f"User question: {prompt}\n\n012 reply:"
        )

        try:
            output = self._llm(
                full_prompt,
                max_tokens=80,  # Hard limit for comment length
                temperature=0.6,  # Less creative, more consistent
                top_p=0.85,
                stop=["\n\n", "User:", "Thread:", "\n012", "Question:"],
            )

            response = output["choices"][0]["text"].strip()

            # Hard truncate to ~200 chars (YouTube comment friendly)
            if len(response) > 200:
                # Find last sentence boundary within limit
                truncated = response[:200]
                last_period = truncated.rfind(".")
                last_question = truncated.rfind("?")
                last_exclaim = truncated.rfind("!")
                boundary = max(last_period, last_question, last_exclaim)
                if boundary > 50:
                    response = response[:boundary + 1]
                else:
                    response = truncated.rsplit(" ", 1)[0] + "..."

            # Apply entity correction to output (fix common LLM mistakes)
            response = self._correct_entities(response)

            logger.info(f"[DRAFTER-LLM] Generated {len(response)} chars via Qwen 1.5B")
            return response

        except Exception as e:
            logger.error(f"[DRAFTER-LLM] Generation failed: {e}")
            return self._mock_generate(prompt)

    def generate_station_json(self, system_policy: str, source_data: Dict[str, Any]) -> str:
        """Use the configured local model without mock or template fallbacks.

        Station policy has its own message role. Conversation text is serialized
        as untrusted data, and this call exposes no tools or publishing actions.
        """
        if self.mock_mode or self._llm is None:
            raise RuntimeError("local_model_unavailable")
        completion = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_policy},
                {"role": "user", "content": json.dumps(source_data, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            max_tokens=384,
            temperature=0.2,
            stream=False,
        )
        choice = completion["choices"][0]
        message = choice["message"]
        if choice.get("finish_reason") != "stop" or message.get("tool_calls") or message.get("function_call"):
            raise ValueError("incomplete_station_generation")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > 4096:
            raise ValueError("invalid_station_generation")
        return content

    @staticmethod
    def _correct_entities(text: str) -> str:
        """Fix common LLM mistakes in entity names (WSP 84 pattern from video_search.py)."""
        import re
        corrections = {
            r"\bEdutit\b": "Eduit",
            r"\bedutit\b": "Eduit",
            r"\bedu\.org\b": "eduit.org",
            r"\bMichael Trout\b": "Michael Trauth",
            r"\btrout\b": "Trauth",
            r"\bFoundups\b": "FoundUps",
            r"\bundaodu\b": "UnDaoDu",
            r'"([^"]+)"': r'\1',  # Remove unnecessary quotes
        }
        for pattern, replacement in corrections.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text.strip()

    def _mock_generate(self, prompt: str) -> str:
        """Deterministic mock for testing."""
        prompt_lower = prompt.lower()
        if "visa" in prompt_lower:
            return "The Japan visa process requires a sponsor company. I went through this myself - it takes about 2-3 months."
        elif "business" in prompt_lower:
            return "Starting a business in Japan requires capital and a solid plan. Happy to share more details!"
        elif "education" in prompt_lower:
            return "Education technology is transforming how we learn. I've been working on this in Japan for years."
        else:
            return "Thanks for the question! Based on my experience, this is an important topic."


class CommentDrafter:
    """
    Generate comments in 012's voice using RAG + LLM + Guardrails.
    
    Pipeline:
    1. Query VoiceMemory for relevant snippets
    2. Generate draft with LLM
    3. Apply StyleGuardrails
    4. Return CommentDraft with context
    
    Example:
        >>> drafter = CommentDrafter(voice_memory, guardrails)
        >>> draft = drafter.draft(thread_context, platform="youtube")
    """
    
    def __init__(
        self,
        voice_memory: Optional[VoiceMemory] = None,
        guardrails: Optional[StyleGuardrails] = None,
        llm: Optional[LocalLLM] = None,
        use_real_llm: bool = False
    ):
        """
        Initialize drafter.

        Args:
            voice_memory: VoiceMemory instance for RAG
            guardrails: StyleGuardrails instance
            llm: LLM instance for generation
            use_real_llm: If True, use real Gemma LLM (default False for tests)
        """
        self.voice_memory = voice_memory or VoiceMemory()
        self.guardrails = guardrails or StyleGuardrails()
        self.llm = llm or LocalLLM(mock_mode=not use_real_llm)

    @classmethod
    def production(cls) -> "CommentDrafter":
        """
        Create production instance with real Gemma LLM and HoloIndex.

        Example:
            >>> drafter = CommentDrafter.production()
            >>> draft = drafter.draft("How do I get a Japan visa?")
        """
        return cls(
            voice_memory=VoiceMemory(include_videos=True),
            guardrails=StyleGuardrails(),
            llm=LocalLLM(mock_mode=False),
            use_real_llm=True
        )

    @classmethod
    def for_station(cls, llm: Optional[LocalLLM] = None) -> "CommentDrafter":
        """Construct the station-only path without loading human voice memory.

        Use ``draft_station_reply`` on this instance. The normal constructor and
        ``draft`` retain their existing human-voice behavior.
        """
        drafter = cls.__new__(cls)
        drafter.voice_memory = None
        drafter.guardrails = None
        drafter.llm = llm if llm is not None else LocalLLM(mock_mode=False)
        return drafter

    def draft_station_reply(
        self,
        thread_context: str,
        *,
        context_url: str,
        reply_to_id: str,
        initiated_by_listener: bool,
    ) -> Dict[str, Any]:
        """Draft or skip an initiated station conversation; never publish."""
        from .station_reply_decision import draft_station_reply

        return draft_station_reply(
            self.llm,
            thread_context,
            context_url=context_url,
            reply_to_id=reply_to_id,
            initiated_by_listener=initiated_by_listener,
        )
    
    def draft(
        self,
        thread_context: str,
        platform: str = "youtube",
        context_url: str = "",
        reply_to_id: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> CommentDraft:
        """
        Generate a comment draft.
        
        Args:
            thread_context: The thread/comment to reply to
            platform: Platform (youtube, linkedin, x)
            context_url: URL of the thread
            reply_to_id: ID of comment being replied to
            constraints: Additional constraints (max_length, etc.)
            
        Returns:
            CommentDraft with text, confidence, violations
        """
        constraints = constraints or {}
        
        # 1. Retrieve relevant snippets
        retrieved = self.voice_memory.query(thread_context, k=5)
        snippets = [r.get("text", "") for r in retrieved]

        logger.info(f"[DRAFTER] Retrieved {len(snippets)} voice memory snippets for context")
        
        # 2. Build prompt
        prompt = self._build_prompt(thread_context, snippets, constraints, platform)

        # 3. Generate with LLM
        try:
            raw_draft = self.llm.generate(
                prompt,
                snippets,
                platform=platform,
                constraints=constraints,
            )
        except TypeError:
            raw_draft = self.llm.generate(prompt, snippets)
        
        # 4. Apply guardrails
        cleaned_text, violations = self.guardrails.enforce(raw_draft)
        
        # 5. Calculate confidence
        confidence = self._calculate_confidence(
            raw_draft,
            cleaned_text,
            violations,
            retrieved
        )
        
        # 6. Build CommentDraft
        risk_flags = [v["message"] for v in violations if v.get("severity") in ["warning", "error"]]

        draft = CommentDraft(
            platform=Platform(platform) if hasattr(Platform, platform.upper()) else Platform.YOUTUBE,
            context_url=context_url,
            reply_to_id=reply_to_id,
            text=cleaned_text,
            confidence=confidence,
            risk_flags=risk_flags,
            retrieved_snippets=snippets[:3]  # Top 3 for logging
        )

        logger.info(f"[DRAFTER] Generated draft | confidence={confidence:.2f} | len={len(cleaned_text)} | violations={len(violations)}")
        return draft
    
    def _build_prompt(
        self,
        thread_context: str,
        snippets: List[str],
        constraints: Dict[str, Any],
        platform: str,
    ) -> str:
        """Build LLM prompt with context."""
        platform_name = str(platform or "youtube").strip().lower()
        if platform_name == "linkedin":
            prompt_parts = [
                "You are 0102, drafting a LinkedIn reply through 012's account.",
                "Write like a real operator: concrete, specific, and useful.",
                "Do not write generic praise. Add a point, counterpoint, or extension.",
                "Refer to FoundUps, Holo Index, or 0102 only if it genuinely advances the discussion.",
                "",
                "LinkedIn post context:",
                thread_context,
                "",
            ]
        else:
            prompt_parts = [
                "You are 012's digital twin. Write a comment in 012's voice.",
                "",
                "Thread context:",
                thread_context,
                "",
            ]
        
        if snippets:
            prompt_parts.extend([
                "Reference examples from 012:",
                *[f"- {s[:100]}..." for s in snippets[:3]],
                "",
            ])
        
        if constraints:
            prompt_parts.extend([
                "Constraints:",
                *[f"- {k}: {v}" for k, v in constraints.items()],
                "",
            ])
        
        if platform_name == "linkedin":
            prompt_parts.append("Write the LinkedIn reply (max 300 chars, direct expert tone):")
        else:
            prompt_parts.append("Write a comment (max 300 chars, friendly expert tone):")
        
        return "\n".join(prompt_parts)
    
    def _calculate_confidence(
        self,
        raw_draft: str,
        cleaned_draft: str,
        violations: List[Dict[str, Any]],
        retrieved: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score for draft."""
        confidence = 0.7  # Base confidence
        
        # Boost for good retrieval
        if retrieved and retrieved[0].get("score", 0) > 0.5:
            confidence += 0.1
        
        # Penalty for violations
        error_count = sum(1 for v in violations if v.get("severity") == "error")
        warning_count = sum(1 for v in violations if v.get("severity") == "warning")
        
        confidence -= error_count * 0.2
        confidence -= warning_count * 0.05
        
        # Penalty if significantly modified
        if len(cleaned_draft) < len(raw_draft) * 0.7:
            confidence -= 0.1
        
        return max(0.0, min(1.0, confidence))


# =============================================================================
# Quick Test
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Comment Drafter Test")
    print("=" * 60)
    
    drafter = CommentDrafter()
    
    draft = drafter.draft(
        thread_context="How do I get a work visa for Japan?",
        platform="youtube",
        context_url="https://youtube.com/watch?v=abc123"
    )
    
    print(f"Platform: {draft.platform}")
    print(f"Text: {draft.text}")
    print(f"Confidence: {draft.confidence:.2f}")
    print(f"Risk flags: {draft.risk_flags}")
