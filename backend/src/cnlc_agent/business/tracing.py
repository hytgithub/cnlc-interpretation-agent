"""按执行上下文隔离工具调用关联。"""

from contextvars import ContextVar

call_trace: ContextVar[dict] = ContextVar("business_call_trace", default={})
