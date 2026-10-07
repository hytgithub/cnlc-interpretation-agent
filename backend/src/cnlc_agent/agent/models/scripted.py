"""不调用外部模型的确定性工具验证适配器。"""

import json
from typing import Literal
from uuid import uuid4

from agentscope.credential import CredentialBase
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import (
    HintBlock,
    TextBlock,
    ToolCallBlock,
    ToolResultBlock,
    ToolResultState,
)
from agentscope.model import ChatModelBase, ChatResponse

from ..policy import BUSINESS_TOOLS, TEST_TOOLS


class ScriptedCredential(CredentialBase):
    # 这是原生凭据系统中的自定义测试类型，不包含外部模型 API 密钥。
    # app.py 的 extra_credentials 注册后，会话即可选择 scripted_mock。
    type: Literal["scripted_mock"] = "scripted_mock"

    @classmethod
    def get_chat_model_class(cls):
        # 告诉 AgentScope：该凭据类型对应下面的测试模型类。
        return ScriptedModel


class ScriptedModel(ChatModelBase):
    """给原生 Agent 提供确定的测试响应，不调用外部大模型。

    测试消息示例：
    {"tool": "get_well_data", "arguments": {}}

    第一次模型调用返回 ToolCallBlock。AgentScope 执行工具后再次调用模型。
    第二次模型调用根据 ToolResultBlock 返回文字结果。
    耗时工具还会通过原生 HintBlock 通知完成，再触发一次模型调用。
    """

    def __init__(self, credential, model, parameters=None):
        # stream=False 表示模型一次返回完整响应，不关闭服务的 SSE 事件流。
        # max_retries=0 让测试模型不进行模型层重试，便于检查确定的调用结果。
        super().__init__(
            credential,
            model,
            parameters or self.Parameters(),
            stream=False,
            max_retries=0,
        )
        # 原生 Agent 需要 formatter 检查输入媒体类型。
        # 此处仅复用格式对象，不会发起 OpenAI 请求。
        self.formatter = OpenAIChatFormatter()

    @classmethod
    def list_models(cls, custom_yaml_dir=None):
        # 测试模型没有供应商模型目录，避免框架查找不存在的模型卡。
        return []

    @staticmethod
    def response(payload):
        # 统一返回原生模型响应。文字仍使用 JSON，方便自动测试检查状态。
        return ChatResponse(
            content=[TextBlock(text=json.dumps(payload, ensure_ascii=False))],
            is_last=True,
        )

    async def _call_api(
        self, model_name, messages, tools=None, tool_choice=None, **kwargs
    ):
        # 第 1 步：遍历消息，读取最后遇到的 user 文本块作为测试指令。
        # 系统提示、工具结果和 HintBlock 不作为新的 JSON 指令解析。
        # 原型只约定明确的 JSON 格式，无法通过此步骤证明自然语言理解。
        command = None
        command_index = -1
        for index, msg in enumerate(messages):
            if msg.role == "user":
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        try:
                            candidate = json.loads(block.text)
                        except (ValueError, TypeError):
                            candidate = None
                        command = candidate if isinstance(candidate, dict) else None
                        command_index = index
        # 第 2 步：不满足测试格式就说明“未评估”，不猜测工具或参数。
        if (
            not command
            or not isinstance(command.get("tool"), str)
            or not isinstance(command.get("arguments", {}), dict)
        ):
            return self.response(
                {
                    "mode": "SCRIPTED_MOCK",
                    "status": "UNASSESSED",
                    "message": "请发送 JSON 测试指令。自然语言理解未评估。",
                }
            )
        tool_name = command["tool"]
        # 第 3 步：同时检查实际 Schema 和业务工具清单。
        # 计划工具可以装配给 Agent，但本脚本模型仅发出专业业务、Skill 和显式开启的测试调用。
        names = {x["function"]["name"] for x in tools or []}
        if tool_name not in names or tool_name not in BUSINESS_TOOLS | TEST_TOOLS | {"Skill"}:
            return self.response(
                {"mode": "SCRIPTED_MOCK", "status": "ERROR", "code": "TOOL_NOT_ALLOWED"}
            )
        # 第 4 步：检查本条用户消息之后是否已经出现该工具的结果。
        # 倒序查找让较新的后台完成通知先于较旧的等待占位结果被处理。
        tail = [block for msg in messages[command_index + 1 :] for block in msg.content]
        for block in reversed(tail):
            if isinstance(block, HintBlock) and block.source:
                # 分支 A：原生后台完成通知。source 标识 tool_output 和工具名。
                # 其他业务提醒不能被当作该工具已经完成的证据。
                try:
                    source = json.loads(block.source)
                except ValueError:
                    continue
                if source.get("label") == "tool_output" and source.get(
                    "sublabel", ""
                ).startswith(tool_name + " · "):
                    text = (
                        block.hint
                        if isinstance(block.hint, str)
                        else "".join(
                            x.text for x in block.hint if isinstance(x, TextBlock)
                        )
                    )
                    # 原生通知在原工具 JSON 外加了通知文字。
                    # 当前测试输出为单个 JSON 对象，因此取首个 { 到最后一个 }。
                    # 这只是针对本原型固定输出的解析，不是通用公司响应解析器。
                    begin, end = text.find("{"), text.rfind("}") + 1
                    try:
                        result = json.loads(text[begin:end])
                    except ValueError:
                        # 解析不了结果时标为 UNKNOWN，让调用方查持久化业务记录。
                        result = {
                            "status": "UNKNOWN",
                            "message": "请查询业务运行记录。",
                        }
                    return self.response({"mode": "SCRIPTED_MOCK", **result})
            if isinstance(block, ToolResultBlock) and block.name == tool_name:
                # 分支 B：直接执行结果，或原生后台等待占位结果。
                # 原生框架可能把输出保存成字符串，也可能保存为 TextBlock 列表。
                output = (
                    block.output
                    if isinstance(block.output, str)
                    else "".join(
                        x.text for x in block.output if isinstance(x, TextBlock)
                    )
                )
                if tool_name == "Skill":
                    return self.response({
                        "mode": "SCRIPTED_MOCK",
                        "status": "SUCCESS" if block.state == ToolResultState.SUCCESS else "ERROR",
                        "content": output,
                    })
                if "running in background" in output:
                    # 占位结果的框架状态是 SUCCESS，但业务记录仍是 RUNNING。
                    # 给用户的回复必须是 PENDING，不能把“收到等待通知”说成“处理成功”。
                    return self.response(
                        {
                            "mode": "SCRIPTED_MOCK",
                            "status": "PENDING",
                            "tool_call_id": block.id,
                            "message": "后台运行中。业务尚未完成。",
                        }
                    )
                try:
                    # 普通结果直接沿用业务字典中的 SUCCESS/ERROR/FAILED 等状态。
                    result = json.loads(output)
                except ValueError:
                    result = {"status": "ERROR", "message": output}
                return self.response({"mode": "SCRIPTED_MOCK", **result})
        # 第 5 步：还没有结果，返回一个“请调用工具”的请求。
        # 此处不执行业务函数。AgentScope 收到 ToolCallBlock 后才执行工具。
        # id 用于把原生工具调用与其结果配对，业务层另建 run_id 保存耗时运行。
        return ChatResponse(
            content=[
                ToolCallBlock(
                    id=str(uuid4()),
                    name=tool_name,
                    input=json.dumps(command.get("arguments", {})),
                )
            ],
            is_last=True,
        )
