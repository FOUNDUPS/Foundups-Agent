---
description: Template for building layered orchestration systems using the LEGO test pattern
category: workflow
evals: []
---
# Orchestration SKILLz Template

Build automation systems using layered, composable test modules that snap together like LEGO blocks.

## First Principles

1. **Layer Independence**: Each layer tests one capability in isolation
2. **Progressive Complexity**: L0 → L1 → L2 → L3 builds up to full chain
3. **Snap Together**: Full chain combines all layers
4. **Occam's Build**: Start simple, add layers only when needed

## Layer Architecture

```
L0: Entry       → Navigate, find target (e.g., find unlisted videos)
L1: Filter      → Apply filters/constraints (e.g., unlisted filter)
L2: Edit        → Modify/interact with target (e.g., enhance metadata)
L3: Execute     → Complete action (e.g., schedule, publish)
Full Chain      → L0 + L1 + L2 + L3 snapped together
```

## Directory Structure

```
module/
├── src/
│   └── orchestrator.py      # Main DAE entry point
├── tests/
│   ├── test_layer0_entry.py
│   ├── test_layer1_filter.py
│   ├── test_layer2_edit.py
│   ├── test_layer3_execute.py
│   └── test_full_chain.py
└── scripts/
    └── launch.py            # Menu + CLI interface
```

## Implementation Pattern

### 1. Build Each Layer Independently

```python
# test_layer0_entry.py
def test_layer0():
    """L0: Can we navigate to the target?"""
    driver = connect_browser()
    result = navigate_to_target(driver)
    assert result.success, "L0 failed: could not reach target"
```

### 2. Chain Layers Together

```python
# test_full_chain.py
def test_full_chain():
    """Full chain: L0 → L1 → L2 → L3"""
    driver = connect_browser()
    
    # L0: Entry
    navigate_to_target(driver)
    
    # L1: Filter
    apply_filters(driver)
    
    # L2: Edit
    modify_target(driver)
    
    # L3: Execute
    complete_action(driver)
```

### 3. Create Menu with Layer Access

```python
def show_menu():
    print("1. Run Full Chain")
    print("2. Preview Only (DRY RUN)")
    print("D. Dev Tests (L0-L3)")
```

## When to Use This Pattern

- Browser automation (Selenium/Playwright)
- Multi-step workflows (schedule, publish, moderate)
- API orchestration with validation gates
- Any system requiring incremental testing

## Success Metrics

- Each layer passes independently
- Full chain completes without manual intervention
- 0102 can use simplified menu (dev tests hidden)
