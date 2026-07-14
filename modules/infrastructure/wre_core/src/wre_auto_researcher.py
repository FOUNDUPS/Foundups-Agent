# -*- coding: utf-8 -*-
"""
WRE ROC Auto-Researcher Orchestrator (WSP 48)
Slice Name: WRE_AUTORESEARCH_GIT_RUNNER_CONTRACT_PHASE1

Implements the contract and dry-run loop interface for the ROC auto-researcher.
This is a governed contract boundary under WSP 97 (Truth Boundaries).
All direct git operations and shell execution (subprocess/os.system) are banned
and replaced by an injected mockable Git runner interface.

================================================================================
KARPATHY AUTORESEARCH ARCHITECTURE REFERENCE (DOCUMENTATION)
================================================================================
The Auto-Researcher pattern (originally designed by Andrej Karpathy) uses an
autonomous edit-evaluate-commit/rollback loop:
1. Instruction Agenda (program.md): Guidelines for the LLM agent.
2. Immutable Oracle (prepare.py): Oracle code defining data, validation, and scoring.
3. Mutable Target (train.py): Target script modified by the AI agent.
4. Git Memory: Reverting (rollback) when validation metrics degrade, and committing
   (git commit) when validation metrics improve.

In this governed WRE implementation, the live workspace cannot be directly modified
by the agent. All operations flow through a dry-run command generator contract.
================================================================================
"""

import abc
import sys
import json
import argparse
import random
import time
import tempfile
import difflib
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.infrastructure.shared_utilities.ai_engine_singletons import get_qwen_engine
from modules.infrastructure.wre_core.src.wre_research_evaluator import (
    evaluate_target,
    load_target_config_from_source,
)


class IGitRunner(abc.ABC):
    """
    Abstract interface for Git operations inside the Auto-Researcher.
    Ensures clear separation of authority and guards against direct shell execution.
    """

    @abc.abstractmethod
    def restore(self, path: Path, fallback_code: str) -> Dict:
        """Rollback modifications to the target file."""
        pass

    @abc.abstractmethod
    def commit(self, path: Path, iteration: int, metrics: Dict) -> Dict:
        """Commit progress of the optimized target file."""
        pass

    @abc.abstractmethod
    def diff(self, original_code: str, proposed_code: str, filename: str) -> str:
        """Generate a clean unified diff between two code strings."""
        pass


class DryRunGitRunner(IGitRunner):
    """
    Default safe dry-run/fake runner that performs no live repository mutation.
    Returns planned operations only.
    
    Any future real/live runner must require:
      - signed work authority
      - fresh permission snapshot
      - signed receipt chain
      - VALVE_OPEN_WORKTREE_CREATE
      - isolated absolute worktree outside main
      - no protected branch
      - scoped allowed paths
      - cleanup/rollback plan
      - no merge authority
    """

    def __init__(self):
        self.planned_operations: List[Dict] = []

    def restore(self, path: Path, fallback_code: str) -> Dict:
        digest = hashlib.sha256(fallback_code.encode("utf-8")).hexdigest()
        op = {
            "operation": "restore",
            "relative_path": path.name,
            "path_digest": digest,
            "no_execution_performed": True
        }
        self.planned_operations.append(op)
        return op

    def commit(self, path: Path, iteration: int, metrics: Dict) -> Dict:
        # Non-dry-run live commits from the researcher are prohibited
        raise NotImplementedError("SPECIFIED_NOT_IMPLEMENTED")

    def diff(self, original_code: str, proposed_code: str, filename: str) -> str:
        original_lines = original_code.splitlines(keepends=True)
        proposed_lines = proposed_code.splitlines(keepends=True)
        diff = difflib.unified_diff(
            original_lines, proposed_lines, fromfile=f"a/{filename}", tofile=f"b/{filename}"
        )
        return "".join(diff)


class WREAutoResearcher:
    """
    Orchestrates the autonomous ROC optimization loop using an injected IGitRunner.
    """

    def __init__(
        self,
        target_path: Path,
        program_path: Path,
        max_iterations: int = 5,
        dry_run: bool = True,
        runner: Optional[IGitRunner] = None,
        results_dir: Optional[Path] = None,
    ):
        self.target_path = Path(target_path)
        self.program_path = Path(program_path)
        self.max_iterations = max_iterations
        self.dry_run = dry_run
        
        # Use DryRunGitRunner by default
        self.runner = runner or DryRunGitRunner()

        # Enforce fail-closed check
        if not self.dry_run:
            raise NotImplementedError("SPECIFIED_NOT_IMPLEMENTED")

        # Initialize original content (Read-Only template)
        self.original_code = self.target_path.read_text(encoding="utf-8")

        # Load program instructions
        self.program_instructions = self.program_path.read_text(encoding="utf-8")

        # Setup results directory under system temp or isolated path (never under repo source)
        if results_dir:
            self.results_dir = Path(results_dir)
        else:
            self.results_dir = Path(tempfile.gettempdir()) / "wre_autoresearch_runs"
        
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Working target file copy located outside main repo (in sandbox)
        self.working_target_path = self.results_dir / self.target_path.name

        # WSP 97 Hardening: Assert the write target is not under REPO_ROOT
        # Resolving absolute path to prevent symlink traversal
        abs_working = self.working_target_path.resolve()
        abs_repo = REPO_ROOT.resolve()
        if abs_repo in abs_working.parents or abs_working == abs_repo:
             raise PermissionError("WSP_97 violation: Writing to target file under REPO_ROOT is strictly prohibited.")

        # Copy baseline config to the working sandboxed target file
        shutil.copy(self.target_path, self.working_target_path)

        self.results_path = self.results_dir / "results.tsv"
        self._init_results_file()

        # Attempt to load LLM engine
        self.llm = get_qwen_engine()
        if self.llm:
            print(f"[AUTO-RESEARCHER] Initialized with Qwen/Gemma backend: {self.llm.backend_name}")
        else:
            print("[AUTO-RESEARCHER] No LLM engine available. Falling back to heuristic optimizer.")

    def _init_results_file(self):
        """Create results.tsv log file with headers if it does not exist."""
        if not self.results_path.exists():
            headers = "timestamp\titeration\tstatus\tfitness\troc_ratio\tmonthly_margin\tinfo\n"
            self.results_path.write_text(headers, encoding="utf-8")

    def _log_to_tsv(self, iteration: int, status: str, metrics: Dict, info: str = ""):
        """Log iteration results in a TSV format in the isolated directory."""
        timestamp = int(time.time())
        fitness = metrics.get("fitness", 0.0)
        roc = metrics.get("roc_ratio", 0.0)
        margin = metrics.get("monthly_margin_usd", 0.0)
        safe_info = _sanitize_tsv_field(info)
        row = f"{timestamp}\t{iteration}\t{status}\t{fitness:.6f}\t{roc:.6f}\t{margin:.2f}\t{safe_info}\n"
        with open(self.results_path, "a", encoding="utf-8") as f:
            f.write(row)

    def run(self) -> Dict:
        """Run the optimization loop."""
        print(f"[AUTO-RESEARCHER] Starting research loop (max_iterations={self.max_iterations}, dry_run={self.dry_run})")

        # Baseline evaluation on working copy
        baseline_metrics = evaluate_target(self.working_target_path)
        print(f"[BASELINE] Fitness: {baseline_metrics.get('fitness'):.4f} (ROC: {baseline_metrics.get('roc_ratio'):.4f})")
        self._log_to_tsv(0, "baseline", baseline_metrics, "Initial baseline parameters")

        best_code = self.original_code
        best_metrics = baseline_metrics
        history: List[Dict] = []

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n--- Iteration {iteration}/{self.max_iterations} ---")
            
            # 1. Propose change
            proposed_code = self._propose_change(best_code, best_metrics, history)
            if not proposed_code:
                print("[WARNING] Could not generate new proposal. Skipping.")
                continue

            # 2. Write proposed code to sandboxed working target copy
            self.working_target_path.write_text(proposed_code, encoding="utf-8")

            # Calculate and display diff using injected runner
            diff_text = self.runner.diff(best_code, proposed_code, self.target_path.name)
            print("[DIFF OF PROPOSAL]:")
            print(diff_text)

            # 3. Evaluate proposed code on sandboxed working target copy
            try:
                metrics = evaluate_target(self.working_target_path)
                print(f"[EVALUATION] Fitness: {metrics.get('fitness'):.4f} (ROC: {metrics.get('roc_ratio'):.4f})")

                # If error in evaluation
                if "error" in metrics:
                    print(f"[REJECTED] Validation failed: {metrics['error']}. Rolling back.")
                    self._rollback(best_code)
                    self._log_to_tsv(iteration, "failed_validation", metrics, metrics["error"])
                    history.append({"iteration": iteration, "status": "failed_validation", "error": metrics["error"]})
                    continue

                # 4. Compare and commit/rollback
                if metrics["fitness"] > best_metrics["fitness"]:
                    print(f"[ACCEPTED] Fitness improved: {best_metrics['fitness']:.4f} -> {metrics['fitness']:.4f}")
                    best_code = proposed_code
                    best_metrics = metrics
                    self._commit(iteration, metrics)
                    self._log_to_tsv(iteration, "accepted", metrics, f"Improved from {best_metrics['fitness']:.4f}")
                    history.append({
                        "iteration": iteration,
                        "status": "accepted",
                        "fitness": metrics["fitness"],
                        "roc_ratio": metrics["roc_ratio"],
                    })
                else:
                    print(f"[REJECTED] Fitness did not improve. Rolling back.")
                    self._rollback(best_code)
                    self._log_to_tsv(iteration, "rejected", metrics, "No improvement")
                    history.append({
                        "iteration": iteration,
                        "status": "rejected",
                        "fitness": metrics["fitness"],
                        "roc_ratio": metrics["roc_ratio"],
                    })

            except Exception as eval_err:
                print(f"[REJECTED] Evaluation crashed: {eval_err}. Rolling back.")
                self._rollback(best_code)
                self._log_to_tsv(iteration, "crashed", {}, str(eval_err))
                history.append({"iteration": iteration, "status": "crashed", "error": str(eval_err)})

        # End of loop: handle final dry-run safety restore
        if self.dry_run:
            print("\n[SAFETY] Dry run active. Restoring sandboxed copy to original baseline.")
            self._rollback(self.original_code)

        summary = {
            "baseline": baseline_metrics,
            "optimized": best_metrics,
            "improvement": best_metrics["fitness"] - baseline_metrics["fitness"],
            "iterations_run": self.max_iterations,
            "history": history,
            "dry_run": self.dry_run,
        }

        print("\n" + "=" * 50)
        print("OPTIMIZATION SUMMARY")
        print("=" * 50)
        print(f"Baseline Fitness:  {summary['baseline']['fitness']:.4f}")
        print(f"Optimized Fitness: {summary['optimized']['fitness']:.4f}")
        print(f"ROC Improvement:   {summary['improvement']:.4f}")
        print(f"ROI Sustainable:   {summary['optimized']['is_roi_sustainable']}")
        print("=" * 50)

        return summary

    def _rollback(self, fallback_code: str):
        """Rollback modifications using injected Git runner and restore file state."""
        self.runner.restore(self.working_target_path, fallback_code)
        # Ensure local working target file matches fallback code
        self.working_target_path.write_text(fallback_code, encoding="utf-8")

    def _commit(self, iteration: int, metrics: Dict):
        """Commit progress via Git runner if not running in dry-run mode."""
        if self.dry_run:
            # Under dry run, we can log the planned commit but execute nothing live
            if hasattr(self.runner, "planned_operations"):
                code = self.working_target_path.read_text(encoding="utf-8")
                digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
                op = {
                    "operation": "commit",
                    "relative_path": self.target_path.name,
                    "path_digest": digest,
                    "iteration": iteration,
                    "metrics": {
                        "fitness": metrics.get("fitness", 0.0),
                        "roc_ratio": metrics.get("roc_ratio", 0.0)
                    },
                    "no_execution_performed": True
                }
                self.runner.planned_operations.append(op)
            return

        # Trigger injected commit runner (Prohibited in Phase 1)
        self.runner.commit(self.target_path, iteration, metrics)

    def _propose_change(self, current_code: str, current_metrics: Dict, history: List[Dict]) -> Optional[str]:
        """Propose the next iteration of code."""
        if self.llm:
            return self._propose_via_llm(current_code, current_metrics, history)
        else:
            return self._propose_via_heuristic(current_code)

    def _propose_via_llm(self, current_code: str, current_metrics: Dict, history: List[Dict]) -> Optional[str]:
        """Ask the LLM to propose optimizations."""
        history_summary = ""
        for h in history[-3:]:  # Last 3 attempts for context
            status = h.get("status")
            fit = h.get("fitness", 0.0)
            roc = h.get("roc_ratio", 0.0)
            err = f" (Error: {h['error']})" if "error" in h else ""
            history_summary += f"- Iteration {h['iteration']}: status={status}, fitness={fit:.4f}, ROC={roc:.4f}{err}\n"

        prompt = f"""{self.program_instructions}

### CURRENT CONFIGURATION CODE:
```python
{current_code}
```

### CURRENT PERFORMANCE METRICS:
- Fitness score: {current_metrics.get('fitness'):.4f}
- ROC Ratio: {current_metrics.get('roc_ratio'):.4f}
- Is ROI Sustainable: {current_metrics.get('is_roi_sustainable')}
- Monthly Margin: ${current_metrics.get('monthly_margin_usd', 0.0):,.2f}

### HISTORY OF RECENT ATTEMPTS:
{history_summary or "No previous attempts yet."}

### TASK:
Optimize the `AGENT_ALLOCATION` and `AGENT_PREMIUM_MULTIPLIERS` in `wre_research_target.py` to achieve a higher fitness score.
You must output ONLY valid Python source containing the two literal dictionaries.
Do not include imports, function calls, file access, network access, shell access,
markdown formatting, or explanations.
"""

        try:
            response = self.llm.generate_response(prompt, max_tokens=1024)
            return self._parse_python_block(response)
        except Exception as e:
            print(f"[LLM ERROR] Prompt generation failed: {e}")
            return None

    def _propose_via_heuristic(self, current_code: str) -> Optional[str]:
        """Perturb values slightly to simulate heuristic optimization."""
        try:
            alloc, multipliers = load_target_config_from_source(current_code)
            if not alloc or not multipliers:
                raise ValueError("missing target configuration constants")

            # Random perturbation of allocation (maintain sum = 1.0)
            keys = list(alloc.keys())
            if len(keys) >= 2:
                k1, k2 = random.sample(keys, 2)
                shift = round(random.uniform(0.01, 0.05), 3)
                if alloc[k1] > shift:
                    alloc[k1] = round(alloc[k1] - shift, 3)
                    alloc[k2] = round(alloc[k2] + shift, 3)

            # Random perturbation of multipliers (bound to [1.0, 5.0])
            for k in multipliers.keys():
                change = round(random.uniform(-0.3, 0.3), 2)
                multipliers[k] = round(max(1.0, min(5.0, multipliers[k] + change)), 2)

            # Generate python code string
            new_code = f"""# -*- coding: utf-8 -*-
# Generated by WRE ROC Auto-Researcher heuristic perturbation.

AGENT_ALLOCATION = {repr(alloc)}

AGENT_PREMIUM_MULTIPLIERS = {repr(multipliers)}
"""
            return new_code

        except Exception as e:
            print(f"[HEURISTIC ERROR] Perturbation failed: {e}")
            return None

    def _parse_python_block(self, text: str) -> str:
        """Parse raw LLM response, returning only the python block."""
        # Remove code fence formatting if present
        lines = text.strip().split("\n")
        parsed_lines = []
        in_code_block = False

        for line in lines:
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue
            # Accumulate lines
            if in_code_block or not line.startswith("```"):
                parsed_lines.append(line)

        return "\n".join(parsed_lines)


def _sanitize_tsv_field(value: object) -> str:
    """Keep one TSV event per row, even when an error string contains control chars."""

    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WRE ROC Auto-Researcher CLI")
    parser.add_argument("--iterations", type=int, default=5, help="Max iterations for optimization")
    parser.add_argument("--commit", action="store_true", help="Prohibited in Phase 1 (Raises SPECIFIED_NOT_IMPLEMENTED)")
    args = parser.parse_args()

    src_dir = Path(__file__).parent
    target_file = src_dir / "wre_research_target.py"
    program_file = src_dir / "wre_research_program.md"

    # In CLI mode, always default to DryRunGitRunner
    runner = DryRunGitRunner()

    researcher = WREAutoResearcher(
        target_path=target_file,
        program_path=program_file,
        max_iterations=args.iterations,
        dry_run=not args.commit,
        runner=runner,
    )
    researcher.run()
