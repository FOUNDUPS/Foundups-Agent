"""Real prompt utility, synthetic input and private logging sinks only."""
import ast
import builtins
import io
import logging
from pathlib import Path
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[4]


def prompt_owner():
    path = ROOT / 'modules/infrastructure/cli/src/utilities.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    body = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
            and n.name in {'console_input', '_PromptConsoleFilter'}]
    namespace = dict(builtins=builtins, logging=logging, sys=sys, threading=threading)
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['console_input']


@pytest.mark.parametrize('outcome', ['answer', 'interrupt', 'eof'])
def test_background_logs_keep_file_evidence_without_overwriting_prompt(tmp_path, monkeypatch, outcome):
    prompt = prompt_owner()
    console = io.StringIO()
    monkeypatch.setattr(sys, 'stdout', console)
    terminal = logging.StreamHandler(console)
    disk = logging.FileHandler(tmp_path / 'events.log', encoding='utf-8')
    prior_filter = logging.Filter()
    terminal.addFilter(prior_filter)
    disk.addFilter(prior_filter)
    logger = logging.getLogger('prompt-boundary-fixture')
    old = (logger.handlers[:], logger.level, logger.propagate)
    logger.handlers, logger.level, logger.propagate = [terminal, disk], logging.INFO, False

    def enter(message):
        assert message == 'Choose: '
        worker = threading.Thread(target=lambda: logger.warning('background-while-waiting'))
        worker.start()
        worker.join(timeout=2)
        assert not worker.is_alive()
        logger.info('foreground-visible')
        if outcome == 'interrupt':
            raise KeyboardInterrupt()
        if outcome == 'eof':
            raise EOFError()
        return '1'

    monkeypatch.setattr(builtins, 'input', enter)
    try:
        if outcome == 'answer':
            assert prompt('Choose: ') == '1'
        else:
            with pytest.raises(KeyboardInterrupt if outcome == 'interrupt' else EOFError):
                prompt('Choose: ')
        worker = threading.Thread(target=lambda: logger.warning('background-after-input'))
        worker.start()
        worker.join(timeout=2)
        assert not worker.is_alive()
        disk.flush()
        assert 'background-while-waiting' not in console.getvalue()
        assert 'foreground-visible' in console.getvalue()
        assert 'background-after-input' in console.getvalue()
        assert 'background-while-waiting' in (tmp_path / 'events.log').read_text()
        assert terminal.filters == disk.filters == [prior_filter]
    finally:
        logger.handlers, logger.level, logger.propagate = old
        disk.close()


def test_main_menu_uses_local_prompt_owner_without_replacing_builtin():
    tree = ast.parse((ROOT / 'modules/infrastructure/cli/src/main_menu.py').read_text(encoding='utf-8'))
    assert any(isinstance(n, ast.ImportFrom) and n.module == 'modules.infrastructure.cli.src.utilities'
               and any(a.name == 'console_input' and a.asname == 'input' for a in n.names)
               for n in tree.body)
