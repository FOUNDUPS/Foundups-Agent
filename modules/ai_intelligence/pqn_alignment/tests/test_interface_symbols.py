import importlib

def test_interface_symbols():
    import modules.ai_intelligence.pqn_alignment as mod
    
    # Remove: assert hasattr(mod, 'rerun_targeted')
    assert hasattr(mod, 'run_detector')
    assert hasattr(mod, 'phase_sweep')
    assert hasattr(mod, 'council_run')
    assert hasattr(mod, 'promote')
    assert hasattr(mod, 'get_theory_archive_context')
