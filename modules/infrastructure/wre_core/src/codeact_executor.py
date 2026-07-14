#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CodeAct Executor (Sprint 3 - Gap E)

Executes hybrid prompt+code skills with strict safety gates.

Per WRE_COT_DEEP_ANALYSIS.md Gap E:
- Introduce hybrid skill schema: declarative prompt + executable action
- Actions are executable programs with conditionals and tool composition
- Strict allowlist/sandbox gates for security

CodeAct Skill Schema:
{
    "format": "codeact",
    "prompt_section": {...},
    "code_section": {
        "pre_actions": [...],
        "conditionals": [...],
        "main_action": {...},
        "post_actions": [...]
    },
    "safety_gates": {
        "allowed_commands": ["git *", "echo *"],
        "blocked_patterns": ["rm -rf", "sudo *"],
        "max_execution_time_ms": 30000,
        "require_confirmation": ["git push"]
    }
}

WSP References: WSP 46, WSP 50, WSP 64
"""

import logging
import subprocess
import shlex
import os
import re
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path

from modules.infrastructure.wre_core.src.wre_worker_git_cwd_guard import (
    validate_worker_git_operation_cwd,
)

logger = logging.getLogger(__name__)


@dataclass
class CodeActResult:
    """Result of CodeAct execution."""
    success: bool
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: int = 0
    actions_executed: int = 0
    gates_triggered: List[str] = field(default_factory=list)


@dataclass
class SafetyGates:
    """
    Safety configuration for CodeAct execution.

    Per WSP 64: Strict allowlist/sandbox gates.
    """
    allowed_commands: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=lambda: [
        "rm -rf *",
        "rm -r /*",
        "sudo *",
        "> /dev/*",
        "chmod 777 *",
        "curl * | bash",
        "wget * | bash",
        "eval *",
        "exec *"
    ])
    max_execution_time_ms: int = 30000
    require_confirmation: List[str] = field(default_factory=list)
    require_allowlist: bool = False
    forbid_shell_metacharacters: bool = False

    def is_command_allowed(self, command: str) -> bool:
        """
        Check if command is allowed by safety gates.

        Order: blocked patterns checked first (deny-by-default for dangerous ops)
        """
        # Check blocked patterns first (always deny these)
        for pattern in self.blocked_patterns:
            if self._matches_pattern(command, pattern):
                logger.warning(f"[CODEACT-GATE] BLOCKED: {command} (matches: {pattern})")
                return False

        # If no allowed patterns specified, allow all non-blocked
        if not self.allowed_commands:
            if self.require_allowlist:
                logger.warning("[CODEACT-GATE] DENIED: allowlist required but empty")
                return False
            return True

        # Check allowed patterns (allowlist mode)
        for pattern in self.allowed_commands:
            if self._matches_pattern(command, pattern):
                return True

        logger.warning(f"[CODEACT-GATE] DENIED: {command} (not in allowlist)")
        return False

    def requires_confirmation(self, command: str) -> bool:
        """Check if command requires user confirmation."""
        for pattern in self.require_confirmation:
            if self._matches_pattern(command, pattern):
                return True
        return False

    def _matches_pattern(self, command: str, pattern: str) -> bool:
        """Match command against glob-style pattern."""
        # Escape regex special chars except * and ?
        escaped = re.escape(pattern).replace(r'\*', '.*').replace(r'\?', '.')
        return bool(re.match(f"^{escaped}$", command.strip(), re.IGNORECASE))


class CodeActExecutor:
    """
    Executes hybrid CodeAct skills.

    Combines:
    - Pre-actions: Shell commands to gather context
    - Conditionals: Branch based on action results
    - Main action: LLM generation or tool call
    - Post-actions: Execute based on LLM output

    All actions pass through SafetyGates.
    """

    def __init__(
        self,
        repo_root: Path,
        llm_callback: Optional[Callable[[str], str]] = None,
        confirmation_callback: Optional[Callable[[str], bool]] = None,
        worker_worktree_path: Optional[Path] = None,
    ):
        """
        Initialize CodeAct executor.

        Args:
            repo_root: Repository root for relative paths
            llm_callback: Function(prompt) -> str for LLM generation
            confirmation_callback: Function(command) -> bool for confirmations
        """
        self.repo_root = Path(repo_root).resolve()
        self.llm_callback = llm_callback
        self.confirmation_callback = confirmation_callback
        self.worker_worktree_path = Path(worker_worktree_path).resolve() if worker_worktree_path else None
        self.strict_mode = os.getenv("WRE_CODEACT_STRICT", "1").strip() == "1"

    def execute(
        self,
        skill_spec: Dict,
        input_context: Dict,
        safety_override: Optional[SafetyGates] = None
    ) -> CodeActResult:
        """
        Execute a CodeAct skill.

        Args:
            skill_spec: Full skill specification with code_section
            input_context: Input variables for template substitution
            safety_override: Optional safety gates override

        Returns:
            CodeActResult with outputs and execution metadata
        """
        start_time = time.time()
        outputs = dict(input_context)  # Start with input context
        actions_executed = 0
        gates_triggered = []

        # Load safety gates
        gates_spec = skill_spec.get("safety_gates", {})
        gates = safety_override or SafetyGates(
            allowed_commands=gates_spec.get("allowed_commands", []),
            blocked_patterns=gates_spec.get("blocked_patterns", SafetyGates().blocked_patterns),
            max_execution_time_ms=gates_spec.get("max_execution_time_ms", 30000),
            require_confirmation=gates_spec.get("require_confirmation", []),
            require_allowlist=bool(
                gates_spec.get("require_allowlist", self.strict_mode)
            ),
            forbid_shell_metacharacters=bool(
                gates_spec.get("forbid_shell_metacharacters", self.strict_mode)
            ),
        )

        code_section = skill_spec.get("code_section", {})

        try:
            # Execute pre-actions
            for action in code_section.get("pre_actions", []):
                result = self._execute_action(action, outputs, gates)
                if result.get("error"):
                    return CodeActResult(
                        success=False,
                        outputs=outputs,
                        error=f"Pre-action failed: {result['error']}",
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        actions_executed=actions_executed,
                        gates_triggered=gates_triggered
                    )
                outputs.update(result.get("outputs", {}))
                actions_executed += 1
                if result.get("gate_triggered"):
                    gates_triggered.append(result["gate_triggered"])

            # Evaluate conditionals
            for conditional in code_section.get("conditionals", []):
                branch_result = self._evaluate_conditional(conditional, outputs)
                if branch_result.get("early_return"):
                    return CodeActResult(
                        success=True,
                        outputs=branch_result.get("return_value", {}),
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        actions_executed=actions_executed,
                        gates_triggered=gates_triggered
                    )

            # Execute main action
            main_action = code_section.get("main_action")
            if main_action:
                result = self._execute_action(main_action, outputs, gates)
                if result.get("error"):
                    return CodeActResult(
                        success=False,
                        outputs=outputs,
                        error=f"Main action failed: {result['error']}",
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        actions_executed=actions_executed,
                        gates_triggered=gates_triggered
                    )
                outputs.update(result.get("outputs", {}))
                actions_executed += 1

            # Execute post-actions
            for action in code_section.get("post_actions", []):
                result = self._execute_action(action, outputs, gates)
                if result.get("error"):
                    return CodeActResult(
                        success=False,
                        outputs=outputs,
                        error=f"Post-action failed: {result['error']}",
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        actions_executed=actions_executed,
                        gates_triggered=gates_triggered
                    )
                outputs.update(result.get("outputs", {}))
                actions_executed += 1
                if result.get("gate_triggered"):
                    gates_triggered.append(result["gate_triggered"])

            logger.info(
                f"[CODEACT] Execution complete: {actions_executed} actions, "
                f"{len(gates_triggered)} gate triggers"
            )

            return CodeActResult(
                success=True,
                outputs=outputs,
                execution_time_ms=int((time.time() - start_time) * 1000),
                actions_executed=actions_executed,
                gates_triggered=gates_triggered
            )

        except Exception as exc:
            logger.error(f"[CODEACT] Execution failed: {exc}")
            return CodeActResult(
                success=False,
                outputs=outputs,
                error=str(exc),
                execution_time_ms=int((time.time() - start_time) * 1000),
                actions_executed=actions_executed,
                gates_triggered=gates_triggered
            )

    def _evaluate_conditional(self, conditional: Dict, context: Dict) -> Dict:
        """Evaluate a conditional and determine branch."""
        condition = conditional.get("if", "True")

        # Safe evaluation with restricted builtins
        safe_builtins = {
            'len': len, 'str': str, 'int': int, 'float': float,
            'bool': bool, 'True': True, 'False': False, 'None': None
        }

        try:
            condition_result = eval(condition, {"__builtins__": safe_builtins}, context)
        except Exception as e:
            logger.warning(f"[CODEACT] Conditional eval failed: {e}")
            condition_result = False

        branch = conditional.get("then") if condition_result else conditional.get("else")

        if branch:
            if branch.get("type") == "return":
                return {
                    "early_return": True,
                    "return_value": branch.get("value", {})
                }
            # "continue" type just proceeds

        return {}

    def _execute_action(
        self,
        action: Dict,
        context: Dict,
        gates: SafetyGates
    ) -> Dict:
        """Execute a single action with safety gates."""
        action_type = action.get("type")

        if action_type == "shell":
            return self._execute_shell(action, context, gates)
        elif action_type == "llm_generate":
            return self._execute_llm(action, context)
        elif action_type == "python":
            return self._execute_python(action, context)
        elif action_type == "read_file":
            return self._execute_read_file(action, context)
        else:
            return {"error": f"Unknown action type: {action_type}"}

    def _execute_shell(
        self,
        action: Dict,
        context: Dict,
        gates: SafetyGates
    ) -> Dict:
        """Execute shell command with strict safety checks."""
        command = action.get("command", "")
        capture_var = action.get("capture")

        # Template substitution
        try:
            command = command.format(**context)
        except KeyError as e:
            return {"error": f"Missing context variable: {e}"}

        # Safety check - STRICT allowlist enforcement
        if not gates.is_command_allowed(command):
            return {
                "error": f"Command blocked by safety gates: {command}",
                "gate_triggered": f"blocked:{command[:50]}"
            }

        if gates.forbid_shell_metacharacters and self._has_shell_metacharacters(command):
            return {
                "error": f"Command blocked by metacharacter policy: {command}",
                "gate_triggered": f"metachar_blocked:{command[:50]}"
            }

        # Confirmation check for sensitive commands
        if gates.requires_confirmation(command):
            if self.confirmation_callback:
                if not self.confirmation_callback(command):
                    return {
                        "error": f"User denied command: {command}",
                        "gate_triggered": f"confirmation_denied:{command[:50]}"
                    }
            else:
                return {
                    "error": f"Command requires confirmation but no callback: {command}",
                    "gate_triggered": f"confirmation_required:{command[:50]}"
                }

        # Execute with timeout
        try:
            try:
                cmd_parts = shlex.split(command, posix=(os.name != "nt"))
            except ValueError as exc:
                return {"error": f"Command parse failed: {exc}"}
            if not cmd_parts:
                return {"error": "Command parse failed: empty command"}

            command_cwd = self.worker_worktree_path or self.repo_root
            git_guard = validate_worker_git_operation_cwd(
                repo_root=self.repo_root,
                operation_cwd=command_cwd,
                claimed_worktree_path=self.worker_worktree_path,
                argv=cmd_parts,
            )
            if git_guard.ok is not True:
                return {
                    "error": f"Command blocked by worker git cwd guard: {git_guard.code}",
                    "gate_triggered": f"git_cwd_guard:{git_guard.code}",
                    "git_cwd_guard": git_guard.to_dict(),
                }

            result = subprocess.run(
                cmd_parts,
                shell=False,
                capture_output=True,
                text=True,
                timeout=gates.max_execution_time_ms / 1000,
                cwd=str(command_cwd)
            )

            output = result.stdout
            if result.returncode != 0 and result.stderr:
                output = f"{output}\nSTDERR: {result.stderr}"

            outputs = {}
            if capture_var:
                outputs[capture_var] = output.strip()

            return {"outputs": outputs}

        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {gates.max_execution_time_ms}ms"}
        except Exception as e:
            return {"error": f"Shell execution failed: {e}"}

    @staticmethod
    def _has_shell_metacharacters(command: str) -> bool:
        """Detect shell metacharacters frequently used for chaining/injection."""
        patterns = [
            r"[;&|`]",
            r"\$\(",
            r"[<>]",
        ]
        for pat in patterns:
            if re.search(pat, command):
                return True
        return False

    def _execute_llm(self, action: Dict, context: Dict) -> Dict:
        """Execute LLM generation action."""
        if not self.llm_callback:
            return {"error": "No LLM callback configured"}

        template = action.get("prompt_template", "")
        output_var = action.get("output_var", "llm_output")

        try:
            prompt = template.format(**context)
            result = self.llm_callback(prompt)
            return {"outputs": {output_var: result}}
        except Exception as e:
            return {"error": f"LLM generation failed: {e}"}

    def _execute_python(self, action: Dict, context: Dict) -> Dict:
        """Execute Python code action (sandboxed)."""
        code = action.get("code", "")
        output_var = action.get("output_var", "python_output")

        # Create very restricted execution environment
        safe_builtins = {
            'len': len, 'str': str, 'int': int, 'float': float,
            'list': list, 'dict': dict, 'bool': bool, 'tuple': tuple,
            'min': min, 'max': max, 'sum': sum, 'sorted': sorted,
            'range': range, 'enumerate': enumerate, 'zip': zip,
            'abs': abs, 'round': round,
            'True': True, 'False': False, 'None': None
        }

        local_vars = dict(context)

        try:
            exec(code, {"__builtins__": safe_builtins}, local_vars)

            # Extract result if specified
            result = local_vars.get('result', local_vars.get(output_var))
            return {"outputs": {output_var: result}}
        except Exception as e:
            return {"error": f"Python execution failed: {e}"}

    def _execute_read_file(self, action: Dict, context: Dict) -> Dict:
        """Read file contents (safe action)."""
        file_path = action.get("path", "")
        output_var = action.get("capture", "file_contents")

        try:
            file_path = file_path.format(**context)
            full_path = self.repo_root / file_path

            # Security: ensure path is within repo
            if not str(full_path.resolve()).startswith(str(self.repo_root.resolve())):
                return {"error": f"Path escape attempt blocked: {file_path}"}

            if not full_path.exists():
                return {"outputs": {output_var: ""}}

            content = full_path.read_text(encoding='utf-8')
            return {"outputs": {output_var: content}}
        except Exception as e:
            return {"error": f"File read failed: {e}"}


def detect_skill_format(skill_spec: Dict) -> str:
    """
    Detect skill format: 'prompt', 'codeact', or 'hybrid'.

    Per Sprint 3 Ticket 3.2.3: Extend skill loader for CodeAct format
    """
    if skill_spec.get("format") == "codeact":
        return "codeact"
    if "code_section" in skill_spec:
        if "prompt_section" in skill_spec:
            return "hybrid"
        return "codeact"
    return "prompt"


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("[EXAMPLE] CodeAct Executor")

    # Create executor
    executor = CodeActExecutor(
        repo_root=Path("."),
        llm_callback=lambda p: f"LLM response to: {p[:50]}..."
    )

    # Example CodeAct skill
    skill = {
        "format": "codeact",
        "code_section": {
            "pre_actions": [
                {"type": "shell", "command": "git status --porcelain", "capture": "git_status"}
            ],
            "conditionals": [
                {
                    "if": "len(git_status.strip()) == 0",
                    "then": {"type": "return", "value": {"message": "No changes to commit"}},
                    "else": {"type": "continue"}
                }
            ],
            "main_action": {
                "type": "llm_generate",
                "prompt_template": "Generate commit message for:\n{git_status}",
                "output_var": "commit_message"
            }
        },
        "safety_gates": {
            "allowed_commands": ["git status *", "git diff *", "echo *"],
            "blocked_patterns": ["rm *", "sudo *"],
            "max_execution_time_ms": 10000
        }
    }

    # Execute
    result = executor.execute(skill, {})

    print(f"  Success: {result.success}")
    print(f"  Actions executed: {result.actions_executed}")
    print(f"  Execution time: {result.execution_time_ms}ms")
    print(f"  Gates triggered: {result.gates_triggered}")
    if result.error:
        print(f"  Error: {result.error}")
    else:
        print(f"  Outputs: {list(result.outputs.keys())}")

    print("\n[OK] CodeAct execution complete")
