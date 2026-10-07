"""原导入路径的兼容导出；实现分别位于各职责模块。"""

from importlib import import_module

_EXPORTS = {
    "MockWorkflow": ".engine",
    "WorkflowStore": "..repositories.workflow",
    "MockWorkflowTools": "..adapters.mock.workflow_tools",
    "STEPS": ".definition",
    "SCENARIOS": ".definition",
    "utc_now": "..timestamps",
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module = import_module(_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
