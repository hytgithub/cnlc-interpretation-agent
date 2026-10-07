"""业务上下文注入与工具调用关联。"""

import json
from importlib.resources import files

from agentscope.middleware import MiddlewareBase

from ..business.service import BusinessService
from ..business.tracing import call_trace

BASE_SYSTEM_PROMPT = (
    files("cnlc_agent").joinpath("prompts", "system.md").read_text(encoding="utf-8")
)


class ContextMiddleware(MiddlewareBase):
    """在原生执行过程的指定节点插入业务上下文与追踪信息。

    on_reply：一次回复开始时记录实际工具清单。
    on_system_prompt：准备模型输入时附加当前选择。
    on_acting：执行工具时记录框架调用身份。
    next_handler 是后续中间件或原生逻辑，必须继续调用和转发其事件。
    """

    def __init__(self, service: BusinessService):
        self.service = service

    async def on_reply(self, agent, input_kwargs, next_handler):
        # 第 1 步：取得模型实际能看到的工具 Schema，而不是配置中的期望清单。
        schemas = await agent.toolkit.get_tool_schemas()
        self.service.store.save_manifest(
            self.service.owner,
            self.service.session,
            [x["function"]["name"] for x in schemas],
        )
        # 第 2 步：继续原生回复过程，并把每个事件原样交给上层。
        # async for 遍历异步事件流。yield 转发当前事件，不等整轮结束再返回。
        async for event in next_handler(**input_kwargs):
            yield event

    async def on_system_prompt(self, agent, current_prompt):
        # 当前选择来自服务端数据库，不根据对话里提到的井号猜测。
        # 该钩子在准备模型输入时运行，可能一轮回复中执行多次。
        snapshot = self.service.store.selection(
            self.service.owner, self.service.session
        )
        # 这是给模型看的摘要。真正的修订号检查仍由 BusinessService 执行。
        # 提示词本身不能替代业务检查，也不会给查询请求创建运行记录。
        # 固定 Prompt 规定职责边界；动态上下文只提供当前会话事实。
        # 包内 Skill 由 RestrictedAgent 注册到原生 Toolkit，按需读取。
        skill_prompt = await agent.toolkit.get_skill_instructions()
        dynamic = "\n服务端操作上下文：" + json.dumps(snapshot, ensure_ascii=False)
        return (
            current_prompt
            + "\n"
            + BASE_SYSTEM_PROMPT
            + dynamic
            + ("\n" + skill_prompt if skill_prompt else "")
        )

    async def on_acting(self, agent, input_kwargs, next_handler):
        # 第 1 步：读取原生 ToolCallBlock，建立“工具调用 → 回复 → 会话”的关联。
        call = input_kwargs["tool_call"]
        # token 保存进入本次调用前的值，用于 finally 恢复上下文。
        token = call_trace.set(
            {
                "tool_call_id": call.id,
                "reply_id": agent.state.reply_id,
                "session_id": self.service.session,
            }
        )
        try:
            # 第 2 步：执行下游工具。业务层可从 call_trace 读取关联并保存到运行记录。
            async for item in next_handler(**input_kwargs):
                yield item
        finally:
            # 第 3 步：无论成功、错误或取消，都恢复原值，避免影响后续调用。
            call_trace.reset(token)
