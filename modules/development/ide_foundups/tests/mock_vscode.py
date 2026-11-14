"""
Mock VSCode API module for testing FoundUps extension outside VSCode environment.
Provides all necessary VSCode API objects and functions for comprehensive testing.
"""

from unittest.mock import Mock, MagicMock
from typing import Any, Dict, List, Optional, Callable
import asyncio


class MockStatusBarItem:
    def __init__(self):
        self.text = ""
        self.tooltip = ""
        self.show = Mock()
        self.hide = Mock()
        self.dispose = Mock()


class MockTreeDataProvider:
    def __init__(self):
        self.getTreeItem = Mock()
        self.getChildren = Mock()
        self.getParent = Mock()


class MockTreeView:
    def __init__(self):
        self.onDidChangeSelection = Mock()
        self.onDidChangeVisibility = Mock()
        self.reveal = Mock()
        self.dispose = Mock()


class MockConfigurationScope:
    def __init__(self, section: str = "foundups"):
        self.section = section
        self._config = {
            "wre.endpoint": "ws://localhost:8765",
            "agents.enabled": True,
            "cmst.protocol.enabled": True,
            "logging.level": "info"
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    def update(self, key: str, value: Any, scope: Any = None) -> None:
        self._config[key] = value


class MockWorkspace:
    def __init__(self):
        self.getConfiguration = Mock(return_value=MockConfigurationScope())
        self.workspaceFolders = []
        self.onDidChangeConfiguration = Mock()


class MockWindow:
    def __init__(self):
        self.createStatusBarItem = Mock(return_value=MockStatusBarItem())
        self.createTreeView = Mock(return_value=MockTreeView())
        self.showInformationMessage = Mock()
        self.showWarningMessage = Mock()
        self.showErrorMessage = Mock()
        self.showQuickPick = Mock()
        self.showInputBox = Mock()


class MockCommands:
    def __init__(self):
        self.registerCommand = Mock()
        self.executeCommand = Mock()
        self.getCommands = Mock(return_value=[])


class MockExtensionContext:
    def __init__(self):
        self.subscriptions = []
        self.workspaceState = Mock()
        self.globalState = Mock()
        self.extensionPath = "/mock/extension/path"
        self.storagePath = "/mock/storage/path"
        self.globalStoragePath = "/mock/global/storage/path"


class MockDisposable:
    def __init__(self):
        self.dispose = Mock()


class MockEventEmitter:
    def __init__(self):
        self.event = Mock()
        self.fire = Mock()
        self.dispose = Mock()


class MockCancellationToken:
    def __init__(self):
        self.isCancellationRequested = False
        self.onCancellationRequested = Mock()


class MockProgress:
    def __init__(self):
        self.report = Mock()


class MockProgressOptions:
    def __init__(self):
        self.location = 1  # ProgressLocation.Notification
        self.title = ""
        self.cancellable = False


# Mock VSCode API objects
workspace = MockWorkspace()
window = MockWindow()
commands = MockCommands()

# Mock classes
StatusBarAlignment = Mock()
StatusBarAlignment.Left = 1
StatusBarAlignment.Right = 2

TreeItemCollapsibleState = Mock()
setattr(TreeItemCollapsibleState, "None", 0)
TreeItemCollapsibleState.Collapsed = 1
TreeItemCollapsibleState.Expanded = 2

ProgressLocation = Mock()
ProgressLocation.SourceControl = 1
ProgressLocation.Window = 10
ProgressLocation.Notification = 15

ConfigurationTarget = Mock()
ConfigurationTarget.Global = 1
ConfigurationTarget.Workspace = 2
ConfigurationTarget.WorkspaceFolder = 3

# Mock functions
def withProgress(options: MockProgressOptions, task: Callable) -> Any:
    """Mock withProgress function for testing progress indicators."""
    progress = MockProgress()
    token = MockCancellationToken()
    return task(progress, token)


# Export all necessary VSCode API components
__all__ = [
    'workspace',
    'window', 
    'commands',
    'StatusBarAlignment',
    'TreeItemCollapsibleState',
    'ProgressLocation',
    'ConfigurationTarget',
    'withProgress',
    'MockExtensionContext',
    'MockDisposable',
    'MockEventEmitter',
    'MockCancellationToken',
    'MockProgress',
    'MockProgressOptions',
    'MockStatusBarItem',
    'MockTreeDataProvider',
    'MockTreeView',
    'MockConfigurationScope'
] 