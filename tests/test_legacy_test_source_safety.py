"""Bounded import regressions; never import parent application packages."""
import builtins
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_manual_gemini_probe_import_has_no_external_effect(monkeypatch, capsys):
    source = ROOT / 'modules/infrastructure/browser_actions/tests/test_final_autonomous_gemini.py'
    original_import = builtins.__import__
    blocked = ('modules', 'selenium', 'PIL', 'google', 'requests', 'httpx')

    def guarded_import(name, *args, **kwargs):
        assert name.split('.')[0] not in blocked, f'Unexpected runtime import: {name}'
        return original_import(name, *args, **kwargs)

    namespace = {'__name__': '_manual_probe_import', '__file__': str(source)}
    before_path = list(sys.path)
    with monkeypatch.context() as context:
        context.setattr(builtins, '__import__', guarded_import)
        exec(compile(source.read_bytes(), str(source), 'exec'), namespace)
    assert sys.path == before_path
    assert capsys.readouterr() == ('', '')
    assert namespace['WRE_TEST_MODE'] == 'manual'
    assert callable(namespace['main'])


def test_mock_vscode_preserves_reserved_enum_member():
    source = ROOT / 'modules/development/ide_foundups/tests/mock_vscode.py'
    namespace = {'__name__': '_mock_vscode_import', '__file__': str(source)}
    exec(compile(source.read_bytes(), str(source), 'exec'), namespace)
    state = namespace['TreeItemCollapsibleState']
    assert getattr(state, 'None') == 0
    assert state.Collapsed == 1
    assert state.Expanded == 2


def test_blockchain_package_initializer_is_importable_utf8():
    source = ROOT / 'modules/platform_integration/utilities/blockchain_integration/tests/__init__.py'
    raw = source.read_bytes()
    text = raw.decode('utf-8')
    namespace = {'__name__': '_blockchain_test_package', '__file__': str(source)}
    exec(compile(text, str(source), 'exec'), namespace)
    assert isinstance(namespace['__doc__'], str)
