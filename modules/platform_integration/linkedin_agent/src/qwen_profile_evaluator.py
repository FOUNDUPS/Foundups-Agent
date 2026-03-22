#!/usr/bin/env python3
"""
Qwen3 Profile Evaluator - AI-Powered LinkedIn Profile Analysis

Replaces hardcoded approve/deny logic with intelligent Qwen3 evaluation.

WSP Compliance:
- WSP 77: Agent Coordination (Qwen as decision engine)
- WSP 84: Memory Integration (pattern learning)
- WSP 97: System Execution (HoloIndex -> Research -> Hard Think)

Pattern Source: holo_index/qwen_advisor/llm_engine.py (lines 72-126)
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        pass
# === END UTF-8 ENFORCEMENT ===

import logging
import os
import requests
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# LM Studio API endpoint (OpenAI-compatible)
LM_STUDIO_PORT = int(os.getenv("LM_STUDIO_PORT", "1234"))
LM_STUDIO_BASE_URL = f"http://127.0.0.1:{LM_STUDIO_PORT}"

# Use centralized model selection (WSP 84 code reuse)
try:
    from modules.infrastructure.shared_utilities.local_model_selection import (
        resolve_triage_model_path,  # Gemma for binary classification
        resolve_general_model_path,  # Qwen for general tasks
    )
    TRIAGE_MODEL_PATH = resolve_triage_model_path()
    GENERAL_MODEL_PATH = resolve_general_model_path()
except ImportError:
    # Fallback to legacy paths
    TRIAGE_MODEL_PATH = Path("E:/HoloIndex/models/gemma-3-270m-it-Q4_K_M.gguf")
    GENERAL_MODEL_PATH = Path("E:/HoloIndex/models/qwen3.5-4b/Qwen3.5-4B-Q4_K_M.gguf")


class ProfileDecision(Enum):
    """Profile evaluation decision types."""
    APPROVE = "approve"
    APPROVE_CONNECT = "approve_connect"  # CxO/executive - approve + send connection request
    DENY = "deny"
    DENY_INCOMPLETE = "deny_incomplete"  # Missing profile pic - message + deny
    NEEDS_REVIEW = "needs_review"  # Edge case for human review


@dataclass
class ProfileEvaluation:
    """Result of Qwen3 profile evaluation."""
    decision: ProfileDecision
    confidence: float  # 0.0 to 1.0
    reasoning: str
    threat_level: str  # low, medium, high (spam/bot risk)
    engagement_potential: str  # low, medium, high (value to community)
    message_template: Optional[str] = None  # Suggested message type


class Qwen3ProfileEvaluator:
    """
    AI-powered profile evaluator using Gemma (triage) or Qwen (general).

    Uses centralized model selection (local_model_selection.py - WSP 84).
    Follows gemma_intent_classifier.py pattern for binary classification.

    Replaces hardcoded regex patterns with intelligent evaluation:
    - Analyzes name, headline, profile completeness
    - Detects bot/spam indicators
    - Identifies high-value members (CxO, founders, etc.)
    - Provides confidence scores and reasoning
    """

    def __init__(
        self,
        model_path: Path = None,  # Uses GENERAL_MODEL_PATH (Qwen3) by default
        max_tokens: int = 256,
        temperature: float = 0.3,  # Low temp for consistent decisions
        context_length: int = 2048  # Qwen needs more context than Gemma
    ):
        # Use Qwen3 for intelligent evaluation (WSP 77 Phase 2)
        # Gemma is for fast binary pattern matching - Qwen3 for reasoning
        self.model_path = model_path or GENERAL_MODEL_PATH
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.context_length = context_length
        self.llm = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize Qwen3 via LM Studio API (preferred) or llama_cpp fallback.

        Pattern from: holo_index/scripts/bootstrap_qwen3_5_lmstudio.py
        """
        if self._initialized:
            return True

        # Try LM Studio API first (OpenAI-compatible)
        try:
            resp = requests.get(f"{LM_STUDIO_BASE_URL}/v1/models", timeout=3.0)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                for model in models:
                    model_id = str(model.get("id", "")).lower()
                    if "qwen" in model_id:
                        self._use_lm_studio = True
                        self._lm_model_id = model.get("id")
                        self._initialized = True
                        logger.info(f"[QWEN3] Using LM Studio API: {self._lm_model_id}")
                        return True
                logger.warning("[QWEN3] LM Studio running but no Qwen model loaded")
        except requests.RequestException:
            logger.info("[QWEN3] LM Studio API not available, trying llama_cpp")

        # Fallback to llama_cpp direct loading
        self._use_lm_studio = False
        if not self.model_path.exists():
            logger.error(f"Qwen model not found at {self.model_path}")
            return False

        try:
            from llama_cpp import Llama

            logger.info(f"[QWEN3] Loading model via llama_cpp: {self.model_path}")

            # Suppress llama-cpp loading noise
            old_stdout = os.dup(1)
            old_stderr = os.dup(2)
            devnull = os.open(os.devnull, os.O_WRONLY)

            try:
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)

                self.llm = Llama(
                    model_path=str(self.model_path),
                    n_ctx=self.context_length,
                    n_threads=4,
                    n_gpu_layers=0,
                    verbose=False
                )
            finally:
                os.dup2(old_stdout, 1)
                os.dup2(old_stderr, 2)
                os.close(devnull)
                os.close(old_stdout)
                os.close(old_stderr)

            self._initialized = True
            logger.info("[QWEN3] Model loaded via llama_cpp")
            return True

        except ImportError as e:
            logger.error(f"llama-cpp-python not installed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load Qwen model: {e}")
            return False

    def evaluate_profile(
        self,
        name: str,
        headline: str,
        has_image: bool,
        profile_url: Optional[str] = None
    ) -> ProfileEvaluation:
        """
        Evaluate a LinkedIn profile for group membership.

        Args:
            name: Member's display name
            headline: Member's headline/title
            has_image: Whether profile has a photo
            profile_url: Optional profile URL for context

        Returns:
            ProfileEvaluation with decision, confidence, and reasoning
        """
        if not self.initialize():
            # Fallback to simple rule if Qwen unavailable
            return self._fallback_evaluate(name, headline, has_image)

        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(name, headline, has_image, profile_url)

        try:
            # Use LM Studio API if available (OpenAI-compatible)
            if getattr(self, '_use_lm_studio', False):
                raw_output = self._call_lm_studio(prompt)
            else:
                # Fallback to llama_cpp
                response = self.llm(
                    prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    stop=["\n\n", "###", "---"],
                    echo=False
                )
                if isinstance(response, dict) and 'choices' in response:
                    raw_output = response['choices'][0]['text'].strip()
                else:
                    raw_output = str(response).strip()

            return self._parse_evaluation(raw_output, name, headline, has_image)

        except Exception as e:
            logger.error(f"[QWEN3] Evaluation failed: {e}")
            return self._fallback_evaluate(name, headline, has_image)

    def _call_lm_studio(self, prompt: str) -> str:
        """Call LM Studio OpenAI-compatible API."""
        payload = {
            "model": getattr(self, '_lm_model_id', 'qwen'),
            "messages": [
                {"role": "system", "content": "You are a LinkedIn profile evaluator. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        resp = requests.post(
            f"{LM_STUDIO_BASE_URL}/v1/chat/completions",
            json=payload,
            timeout=30.0
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip()

    def _build_evaluation_prompt(
        self,
        name: str,
        headline: str,
        has_image: bool,
        profile_url: Optional[str]
    ) -> str:
        """Build the evaluation prompt for Qwen3."""
        return f"""You are evaluating a LinkedIn profile for membership in an AI agents group called "OpenClaw".

PROFILE:
- Name: {name}
- Headline: {headline}
- Has Profile Photo: {'Yes' if has_image else 'No'}
- Profile URL: {profile_url or 'N/A'}

EVALUATION CRITERIA:
1. DENY if: no photo, spam indicators, irrelevant industry, bot-like name
2. APPROVE if: real person, relevant to AI/tech, has photo
3. APPROVE_CONNECT if: CxO, founder, investor, or high-value executive
4. DENY_INCOMPLETE if: no photo but otherwise legitimate (message them first)

OUTPUT FORMAT (JSON):
{{"decision": "approve|deny|approve_connect|deny_incomplete", "confidence": 0.0-1.0, "threat_level": "low|medium|high", "engagement_potential": "low|medium|high", "reasoning": "brief explanation"}}

EVALUATE:"""

    def _parse_evaluation(
        self,
        raw_output: str,
        name: str,
        headline: str,
        has_image: bool
    ) -> ProfileEvaluation:
        """Parse Qwen3 output into ProfileEvaluation."""
        import json
        import re

        # Try to extract JSON from response
        json_match = re.search(r'\{[^}]+\}', raw_output, re.DOTALL)

        if json_match:
            try:
                data = json.loads(json_match.group())
                decision_str = data.get('decision', 'needs_review').lower().replace('_', '_')

                # Map to enum
                decision_map = {
                    'approve': ProfileDecision.APPROVE,
                    'deny': ProfileDecision.DENY,
                    'approve_connect': ProfileDecision.APPROVE_CONNECT,
                    'deny_incomplete': ProfileDecision.DENY_INCOMPLETE,
                }
                decision = decision_map.get(decision_str, ProfileDecision.NEEDS_REVIEW)

                return ProfileEvaluation(
                    decision=decision,
                    confidence=float(data.get('confidence', 0.7)),
                    reasoning=data.get('reasoning', raw_output[:200]),
                    threat_level=data.get('threat_level', 'low'),
                    engagement_potential=data.get('engagement_potential', 'medium'),
                    message_template='cxo_welcome' if decision == ProfileDecision.APPROVE_CONNECT else 'standard_welcome'
                )
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"[QWEN3] JSON parse failed: {e}")

        # Fallback: analyze raw text for keywords
        output_lower = raw_output.lower()

        if 'deny' in output_lower or 'spam' in output_lower or 'bot' in output_lower:
            decision = ProfileDecision.DENY if has_image else ProfileDecision.DENY_INCOMPLETE
        elif 'connect' in output_lower or 'ceo' in output_lower or 'founder' in output_lower:
            decision = ProfileDecision.APPROVE_CONNECT
        elif 'approve' in output_lower:
            decision = ProfileDecision.APPROVE
        else:
            decision = ProfileDecision.NEEDS_REVIEW

        return ProfileEvaluation(
            decision=decision,
            confidence=0.6,  # Lower confidence for text parsing
            reasoning=raw_output[:200],
            threat_level='medium',
            engagement_potential='medium'
        )

    def _fallback_evaluate(
        self,
        name: str,
        headline: str,
        has_image: bool
    ) -> ProfileEvaluation:
        """
        Fallback evaluation when Qwen unavailable.
        Uses simple heuristics similar to original hardcoded logic.
        """
        logger.info("[QWEN3] Using fallback evaluation (model unavailable)")

        # No image = deny with message
        if not has_image:
            return ProfileEvaluation(
                decision=ProfileDecision.DENY_INCOMPLETE,
                confidence=0.9,
                reasoning="No profile photo - requesting completion",
                threat_level='medium',
                engagement_potential='low',
                message_template='complete_profile'
            )

        headline_lower = (headline or "").lower()

        # CxO detection
        cxo_keywords = ['ceo', 'cto', 'cfo', 'coo', 'founder', 'president', 'chief', 'partner', 'investor', 'vc']
        if any(kw in headline_lower for kw in cxo_keywords):
            return ProfileEvaluation(
                decision=ProfileDecision.APPROVE_CONNECT,
                confidence=0.85,
                reasoning=f"Executive/founder detected in headline",
                threat_level='low',
                engagement_potential='high',
                message_template='cxo_welcome'
            )

        # Bot/spam indicators
        spam_keywords = ['make money', 'crypto', 'forex', 'mlm', 'network marketing', 'dm for']
        if any(kw in headline_lower for kw in spam_keywords):
            return ProfileEvaluation(
                decision=ProfileDecision.DENY,
                confidence=0.9,
                reasoning="Spam/promotional indicators in headline",
                threat_level='high',
                engagement_potential='low'
            )

        # Default approve
        return ProfileEvaluation(
            decision=ProfileDecision.APPROVE,
            confidence=0.75,
            reasoning="Standard member - no red flags",
            threat_level='low',
            engagement_potential='medium',
            message_template='standard_welcome'
        )


# Singleton instance
_evaluator: Optional[Qwen3ProfileEvaluator] = None


def get_profile_evaluator() -> Qwen3ProfileEvaluator:
    """Get or create singleton profile evaluator."""
    global _evaluator
    if _evaluator is None:
        _evaluator = Qwen3ProfileEvaluator()
    return _evaluator


def evaluate_profile_with_qwen(
    name: str,
    headline: str,
    has_image: bool,
    profile_url: Optional[str] = None
) -> ProfileEvaluation:
    """
    Convenience function for profile evaluation.

    Usage:
        result = evaluate_profile_with_qwen("John Doe", "CEO at TechCorp", True)
        if result.decision == ProfileDecision.APPROVE:
            # Approve member
        elif result.decision == ProfileDecision.DENY_INCOMPLETE:
            # Message requesting profile completion, then deny
    """
    evaluator = get_profile_evaluator()
    return evaluator.evaluate_profile(name, headline, has_image, profile_url)


if __name__ == "__main__":
    # Test the evaluator
    import argparse

    parser = argparse.ArgumentParser(description="Qwen3 Profile Evaluator")
    parser.add_argument("--name", type=str, default="Test User")
    parser.add_argument("--headline", type=str, default="Software Engineer at TechCorp")
    parser.add_argument("--no-image", action="store_true", help="Simulate no profile image")
    args = parser.parse_args()

    print(f"[QWEN3] Evaluating profile: {args.name}")
    print(f"[QWEN3] Headline: {args.headline}")
    print(f"[QWEN3] Has image: {not args.no_image}")

    result = evaluate_profile_with_qwen(
        name=args.name,
        headline=args.headline,
        has_image=not args.no_image
    )

    print(f"\n[RESULT]")
    print(f"  Decision: {result.decision.value}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Reasoning: {result.reasoning}")
    print(f"  Threat Level: {result.threat_level}")
    print(f"  Engagement Potential: {result.engagement_potential}")
    if result.message_template:
        print(f"  Message Template: {result.message_template}")
