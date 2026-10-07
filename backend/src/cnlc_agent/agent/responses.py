"""业务载荷转换为 AgentScope 工具结果。"""

import json

from agentscope.message import TextBlock, ToolResultState
from agentscope.tool import ToolChunk


def chunk(payload, *, metadata=None):
    """把普通业务字典转换为 AgentScope 要求的工具返回对象。"""
    # 框架识别 ToolResultState，客户端还要读取 payload 中的业务状态。
    # ERROR/FAILED 使用框架错误状态，其余已返回业务对象使用框架成功状态。
    state = (
        ToolResultState.ERROR
        if payload["status"] in {"ERROR", "FAILED"}
        else ToolResultState.SUCCESS
    )
    # 工具结果以 JSON 文本放入 TextBlock。is_last=True 表示本工具输出结束。
    # 工具输出结束不等于完整解释完成，必须检查业务状态和操作范围。
    return ToolChunk(
        content=[TextBlock(text=json.dumps(payload, ensure_ascii=False))],
        state=state,
        is_last=True,
        metadata=metadata or {},
    )
