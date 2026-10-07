"""原导入路径的兼容导出；实现分别位于各职责模块。"""

from importlib import import_module

_EXPORTS = {
    "BusinessError": ".errors",
    "BusinessService": ".service",
    "BusinessStore": "..repositories.business",
    "MockWell": "..adapters.mock.well",
    "SelectionRequest": "..contracts.selection",
    "call_trace": ".tracing",
    "now": "..timestamps",
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module = import_module(_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
