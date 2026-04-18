#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Analysis Assistant - LLM-Assisted Proposal Generation

SEC7 — SECURITY_ANALYSIS_ASSISTANT_PHASE1

Analyzes scan findings + recall context and produces reviewable remediation
proposals only. No auto-apply, no code mutation, no patch generation.

Architecture:
- SEC1 scans (subprocess CLI)
- SEC2 routes policy
- SEC3 wraps scan execution
- SEC4 proposes scan triggers
- SEC5 stores observations
- SEC6 recalls historical outcomes
- SEC7 (this) analyzes and writes remediation proposals

WSP Compliance:
- WSP 77: Agent Coordination (Qwen/Gemma optional)
- WSP 97: Truthful claims (proposals only, no fix claims)
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _utc_iso() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AnalysisProposal:
    """
    Remediation proposal for a security finding.

    This is a PROPOSAL for human review, not an action.
    No patches are generated. No code is modified.
    """

    # Finding identification
    fingerprint: str
    finding_id: str
    tool: str
    severity: str

    # Analysis results
    finding_summary: str = ""
    risk_explanation: str = ""
    classification: str = "needs_review"  # true_positive, false_positive, needs_review
    classification_confidence: float = 0.0

    # Remediation proposal
    remediation_proposal: str = ""
    files_likely_affected: List[str] = field(default_factory=list)

    # Metadata
    confidence_score: float = 0.0
    requires_012: bool = False
    no_patch_generated: bool = True  # Always True - hard invariant

    # Analysis source
    analysis_source: str = "deterministic"  # deterministic, qwen, gemma, qwen+gemma
    llm_available: bool = False

    # Recall context (if provided)
    recall_context_included: bool = False
    prior_outcomes: Optional[Dict[str, int]] = None
    suggested_outcome_from_history: Optional[str] = None

    # Timestamps
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class SecurityAnalysisAssistant:
    """
    LLM-assisted security analysis that produces reviewable proposals.

    This assistant:
    - Analyzes normalized scan findings
    - Incorporates SEC6 recall context when available
    - Preserves SEC2 policy decisions (especially requires_012)
    - Produces remediation proposals for human review

    Hard constraints:
    - No code mutation
    - No patch generation
    - No auto-remediation
    - No MCP/Codex/Claude dependency
    - LLM unavailability returns deterministic needs_review

    Usage:
        assistant = SecurityAnalysisAssistant()

        proposal = assistant.analyze_finding(
            finding={...},  # Normalized finding from SEC1/SEC3
            policy_decision="gate_012",
            requires_012=True,
            recall_context={...},  # Optional SEC6 recall result
        )

        if proposal.requires_012:
            # Route to 012 for review
            pass
    """

    # Classification keywords for deterministic analysis
    TRUE_POSITIVE_INDICATORS = {
        "remote code execution",
        "sql injection",
        "command injection",
        "path traversal",
        "authentication bypass",
        "privilege escalation",
        "hardcoded credentials",
        "secret exposure",
    }

    FALSE_POSITIVE_INDICATORS = {
        "test file",
        "example",
        "mock",
        "fixture",
        "sample",
        "demo",
    }

    def __init__(
        self,
        enable_qwen: bool = True,
        enable_gemma: bool = True,
        proposal_output_dir: Optional[Path] = None,
    ):
        """
        Initialize SecurityAnalysisAssistant.

        Args:
            enable_qwen: Try to use Qwen for analysis (if available)
            enable_gemma: Try to use Gemma for validation (if available)
            proposal_output_dir: Directory for proposal artifacts (optional)
        """
        self.enable_qwen = enable_qwen
        self.enable_gemma = enable_gemma
        self.proposal_output_dir = proposal_output_dir

        self._qwen_backend = None
        self._gemma_backend = None
        self._backends_resolved = False

        logger.info(
            "[SECURITY-ANALYSIS] Initialized - qwen=%s, gemma=%s",
            enable_qwen,
            enable_gemma,
        )

    def _resolve_backends(self) -> None:
        """
        Lazy-resolve LLM backends.

        Only called when analysis is requested, not at init time.
        This allows tests to run without LM Studio.
        """
        if self._backends_resolved:
            return

        self._backends_resolved = True

        if not self.enable_qwen and not self.enable_gemma:
            logger.info("[SECURITY-ANALYSIS] LLM backends disabled by config")
            return

        try:
            from modules.infrastructure.shared_utilities.local_llm_resolver import (
                resolve_qwen_backend,
                resolve_gemma_backend,
            )

            if self.enable_qwen:
                self._qwen_backend = resolve_qwen_backend()
                if self._qwen_backend:
                    logger.info("[SECURITY-ANALYSIS] Qwen backend available")

            if self.enable_gemma:
                self._gemma_backend = resolve_gemma_backend()
                if self._gemma_backend:
                    logger.info("[SECURITY-ANALYSIS] Gemma backend available")

        except ImportError as e:
            logger.debug(f"[SECURITY-ANALYSIS] LLM resolver import failed: {e}")
        except Exception as e:
            logger.debug(f"[SECURITY-ANALYSIS] Backend resolution failed: {e}")

    def analyze_finding(
        self,
        finding: Dict[str, Any],
        policy_decision: str = "report_only",
        requires_012: bool = False,
        recall_context: Optional[Dict[str, Any]] = None,
    ) -> AnalysisProposal:
        """
        Analyze a security finding and produce a remediation proposal.

        Args:
            finding: Normalized finding dict (from SEC1/SEC3)
                Required keys: fingerprint, finding_id, tool, severity
                Optional: title, description, package_name, file_path
            policy_decision: SEC2 policy decision
            requires_012: Whether finding requires 012 review
            recall_context: Optional SEC6 recall result

        Returns:
            AnalysisProposal with remediation suggestions (for review only)
        """
        # Extract finding fields
        fingerprint = finding.get("fingerprint", "unknown")
        finding_id = finding.get("finding_id", finding.get("vuln_id", "unknown"))
        tool = finding.get("tool", "unknown")
        severity = finding.get("severity", "unknown")
        title = finding.get("title", "")
        description = finding.get("description", "")
        package_name = finding.get("package_name")
        file_path = finding.get("file_path")

        # Start building proposal
        proposal = AnalysisProposal(
            fingerprint=fingerprint,
            finding_id=finding_id,
            tool=tool,
            severity=severity,
            requires_012=requires_012,
            no_patch_generated=True,  # Hard invariant
            created_at=_utc_iso(),
        )

        # Include recall context if provided
        if recall_context:
            proposal.recall_context_included = True
            proposal.prior_outcomes = recall_context.get("prior_outcomes")
            proposal.suggested_outcome_from_history = recall_context.get(
                "suggested_outcome"
            )

        # Try LLM analysis first
        self._resolve_backends()

        if self._qwen_backend or self._gemma_backend:
            proposal.llm_available = True
            self._analyze_with_llm(
                proposal=proposal,
                title=title,
                description=description,
                package_name=package_name,
                file_path=file_path,
                recall_context=recall_context,
            )
        else:
            # Deterministic fallback
            proposal.llm_available = False
            proposal.analysis_source = "deterministic"
            self._analyze_deterministic(
                proposal=proposal,
                title=title,
                description=description,
                package_name=package_name,
                file_path=file_path,
                recall_context=recall_context,
            )

        return proposal

    def _analyze_with_llm(
        self,
        proposal: AnalysisProposal,
        title: str,
        description: str,
        package_name: Optional[str],
        file_path: Optional[str],
        recall_context: Optional[Dict[str, Any]],
    ) -> None:
        """
        Analyze finding using available LLM backends.

        Qwen: Draft analysis
        Gemma: Validate/second-pass classification
        """
        analysis_sources = []

        # Build analysis prompt
        prompt = self._build_analysis_prompt(
            proposal=proposal,
            title=title,
            description=description,
            package_name=package_name,
            file_path=file_path,
            recall_context=recall_context,
        )

        # Try Qwen for primary analysis
        qwen_output = None
        if self._qwen_backend:
            try:
                qwen_output = self._qwen_backend.generate_response(prompt, max_tokens=512)
                if qwen_output and qwen_output.strip():
                    analysis_sources.append("qwen")
                    self._parse_llm_output(proposal, qwen_output)
            except Exception as e:
                logger.warning(f"[SECURITY-ANALYSIS] Qwen analysis failed: {e}")

        # Try Gemma for validation/second-pass
        if self._gemma_backend:
            try:
                validation_prompt = self._build_validation_prompt(
                    proposal=proposal,
                    qwen_output=qwen_output,
                )
                gemma_output = self._gemma_backend.generate_response(
                    validation_prompt, max_tokens=256
                )
                if gemma_output and gemma_output.strip():
                    analysis_sources.append("gemma")
                    self._apply_gemma_validation(proposal, gemma_output)
            except Exception as e:
                logger.warning(f"[SECURITY-ANALYSIS] Gemma validation failed: {e}")

        # Set analysis source
        if analysis_sources:
            proposal.analysis_source = "+".join(analysis_sources)
        else:
            # LLM available but both failed - fall back to deterministic
            proposal.analysis_source = "deterministic"
            self._analyze_deterministic(
                proposal=proposal,
                title=title,
                description=description,
                package_name=package_name,
                file_path=file_path,
                recall_context=recall_context,
            )

    def _analyze_deterministic(
        self,
        proposal: AnalysisProposal,
        title: str,
        description: str,
        package_name: Optional[str],
        file_path: Optional[str],
        recall_context: Optional[Dict[str, Any]],
    ) -> None:
        """
        Deterministic analysis when LLM is unavailable.

        Always returns needs_review with low confidence.
        """
        combined_text = f"{title} {description}".lower()

        # Build summary
        proposal.finding_summary = self._build_deterministic_summary(
            proposal, title, package_name, file_path
        )

        # Risk explanation
        proposal.risk_explanation = self._build_risk_explanation(
            proposal.severity, title, description
        )

        # Classification based on keywords
        classification = "needs_review"
        confidence = 0.3  # Low confidence for deterministic

        # Check for true positive indicators
        for indicator in self.TRUE_POSITIVE_INDICATORS:
            if indicator in combined_text:
                classification = "needs_review"  # Still needs_review, but note it
                confidence = 0.5
                break

        # Check for false positive indicators
        for indicator in self.FALSE_POSITIVE_INDICATORS:
            if indicator in combined_text:
                classification = "needs_review"  # Still needs_review
                confidence = 0.4
                break

        # Use recall context if available
        if recall_context and recall_context.get("suggested_outcome"):
            suggested = recall_context["suggested_outcome"]
            hist_confidence = recall_context.get("suggestion_confidence", 0.0)
            if suggested == "false_positive" and hist_confidence > 0.7:
                classification = "false_positive"
                confidence = min(0.7, hist_confidence)
            elif suggested == "resolved" and hist_confidence > 0.7:
                # Still needs_review for new instance
                confidence = max(confidence, 0.5)

        proposal.classification = classification
        proposal.classification_confidence = confidence
        proposal.confidence_score = confidence

        # Remediation proposal
        proposal.remediation_proposal = self._build_remediation_proposal(
            proposal.severity, title, package_name, file_path
        )

        # Files affected
        if file_path:
            proposal.files_likely_affected = [file_path]

    def _build_analysis_prompt(
        self,
        proposal: AnalysisProposal,
        title: str,
        description: str,
        package_name: Optional[str],
        file_path: Optional[str],
        recall_context: Optional[Dict[str, Any]],
    ) -> str:
        """Build prompt for LLM analysis."""
        parts = [
            "Analyze this security finding and provide a remediation proposal.",
            "Output JSON with: classification (true_positive/false_positive/needs_review),",
            "finding_summary, risk_explanation, remediation_proposal, confidence (0-1).",
            "",
            f"Finding ID: {proposal.finding_id}",
            f"Tool: {proposal.tool}",
            f"Severity: {proposal.severity}",
            f"Title: {title}",
        ]

        if description:
            parts.append(f"Description: {description[:500]}")

        if package_name:
            parts.append(f"Package: {package_name}")

        if file_path:
            parts.append(f"File: {file_path}")

        if recall_context and recall_context.get("prior_outcomes"):
            parts.append("")
            parts.append("Historical context:")
            parts.append(f"Prior outcomes: {recall_context['prior_outcomes']}")
            if recall_context.get("suggested_outcome"):
                parts.append(
                    f"Historical suggestion: {recall_context['suggested_outcome']}"
                )

        parts.extend([
            "",
            "IMPORTANT: Do not generate patches. This is analysis only.",
            "Respond with JSON only.",
        ])

        return "\n".join(parts)

    def _build_validation_prompt(
        self,
        proposal: AnalysisProposal,
        qwen_output: Optional[str],
    ) -> str:
        """Build prompt for Gemma validation."""
        parts = [
            "Validate this security finding classification.",
            f"Finding: {proposal.finding_id} ({proposal.severity})",
        ]

        if qwen_output:
            parts.append(f"Initial analysis: {qwen_output[:300]}")

        parts.extend([
            "",
            "Output: true_positive, false_positive, or needs_review",
            "Single word only.",
        ])

        return "\n".join(parts)

    def _parse_llm_output(self, proposal: AnalysisProposal, output: str) -> None:
        """Parse LLM JSON output into proposal fields."""
        try:
            # Try to extract JSON from output
            output = output.strip()
            if output.startswith("```"):
                # Strip markdown code blocks
                lines = output.split("\n")
                output = "\n".join(
                    line for line in lines if not line.startswith("```")
                )

            data = json.loads(output)

            if "classification" in data:
                classification = data["classification"].lower()
                if classification in ("true_positive", "false_positive", "needs_review"):
                    proposal.classification = classification

            if "confidence" in data:
                try:
                    conf = float(data["confidence"])
                    proposal.classification_confidence = max(0.0, min(1.0, conf))
                    proposal.confidence_score = proposal.classification_confidence
                except (ValueError, TypeError):
                    pass

            if "finding_summary" in data:
                proposal.finding_summary = str(data["finding_summary"])[:500]

            if "risk_explanation" in data:
                proposal.risk_explanation = str(data["risk_explanation"])[:500]

            if "remediation_proposal" in data:
                proposal.remediation_proposal = str(data["remediation_proposal"])[:1000]

        except json.JSONDecodeError:
            # Fall back to extracting classification keyword
            output_lower = output.lower()
            if "true_positive" in output_lower:
                proposal.classification = "true_positive"
                proposal.classification_confidence = 0.6
            elif "false_positive" in output_lower:
                proposal.classification = "false_positive"
                proposal.classification_confidence = 0.6
            else:
                proposal.classification = "needs_review"
                proposal.classification_confidence = 0.4

            proposal.confidence_score = proposal.classification_confidence

    def _apply_gemma_validation(self, proposal: AnalysisProposal, output: str) -> None:
        """Apply Gemma validation output to proposal."""
        output_lower = output.strip().lower()

        # Simple keyword extraction
        if "true_positive" in output_lower:
            if proposal.classification != "true_positive":
                # Gemma disagrees - reduce confidence
                proposal.classification_confidence *= 0.8
            else:
                # Gemma agrees - increase confidence
                proposal.classification_confidence = min(
                    1.0, proposal.classification_confidence * 1.1
                )
        elif "false_positive" in output_lower:
            if proposal.classification != "false_positive":
                proposal.classification_confidence *= 0.8
            else:
                proposal.classification_confidence = min(
                    1.0, proposal.classification_confidence * 1.1
                )
        elif "needs_review" in output_lower:
            # Gemma says needs_review - could override
            if proposal.classification != "needs_review":
                proposal.classification = "needs_review"
                proposal.classification_confidence *= 0.7

        proposal.confidence_score = proposal.classification_confidence

    def _build_deterministic_summary(
        self,
        proposal: AnalysisProposal,
        title: str,
        package_name: Optional[str],
        file_path: Optional[str],
    ) -> str:
        """Build deterministic finding summary."""
        parts = [f"{proposal.severity.upper()} severity finding"]

        if title:
            parts.append(f"'{title}'")

        parts.append(f"detected by {proposal.tool}")

        if package_name:
            parts.append(f"in package {package_name}")
        elif file_path:
            parts.append(f"in {file_path}")

        return " ".join(parts) + "."

    def _build_risk_explanation(
        self,
        severity: str,
        title: str,
        description: str,
    ) -> str:
        """Build risk explanation based on severity and content."""
        severity_explanations = {
            "critical": "This is a critical severity finding that may allow remote code execution, data exfiltration, or complete system compromise. Immediate review recommended.",
            "high": "This is a high severity finding that could lead to significant security impact if exploited. Priority review recommended.",
            "medium": "This is a medium severity finding that may pose security risks under certain conditions. Review when capacity allows.",
            "low": "This is a low severity finding with limited security impact. Review during regular maintenance.",
            "info": "This is an informational finding for awareness. No immediate action required.",
        }

        return severity_explanations.get(
            severity.lower(),
            "Severity unknown. Manual review recommended to assess risk.",
        )

    def _build_remediation_proposal(
        self,
        severity: str,
        title: str,
        package_name: Optional[str],
        file_path: Optional[str],
    ) -> str:
        """Build remediation proposal text."""
        parts = ["REMEDIATION PROPOSAL (for review only - no patch generated):"]

        if package_name:
            parts.append(f"1. Review {package_name} for known vulnerabilities")
            parts.append("2. Check if upgrade is available and compatible")
            parts.append("3. Evaluate if the vulnerable code path is reachable")
        elif file_path:
            parts.append(f"1. Review code in {file_path}")
            parts.append("2. Verify the finding is not a false positive")
            parts.append("3. If confirmed, implement secure coding fix")
        else:
            parts.append("1. Review the finding details")
            parts.append("2. Assess applicability to this codebase")
            parts.append("3. Implement appropriate remediation if confirmed")

        if severity.lower() in ("critical", "high"):
            parts.append("")
            parts.append("NOTE: High/critical severity - prioritize this review.")

        return "\n".join(parts)

    def write_proposal_artifact(
        self,
        proposal: AnalysisProposal,
        output_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Write proposal to artifact file.

        Args:
            proposal: AnalysisProposal to write
            output_dir: Override output directory

        Returns:
            Path to written file, or None if disabled
        """
        target_dir = output_dir or self.proposal_output_dir
        if target_dir is None:
            return None

        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_id = proposal.finding_id.replace("/", "_").replace(":", "_")[:50]
        filename = f"proposal_{safe_id}_{timestamp}.json"

        output_path = target_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(proposal.to_json())

        logger.info(f"[SECURITY-ANALYSIS] Wrote proposal artifact: {output_path}")
        return output_path


def get_security_analysis_assistant(
    enable_qwen: bool = True,
    enable_gemma: bool = True,
) -> SecurityAnalysisAssistant:
    """
    Factory function to get SecurityAnalysisAssistant instance.

    Args:
        enable_qwen: Try to use Qwen for analysis
        enable_gemma: Try to use Gemma for validation

    Returns:
        SecurityAnalysisAssistant instance
    """
    return SecurityAnalysisAssistant(
        enable_qwen=enable_qwen,
        enable_gemma=enable_gemma,
    )
