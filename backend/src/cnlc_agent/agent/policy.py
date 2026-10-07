"""工具白名单和 Agent 装配约束。"""

from importlib.resources import files

from agentscope.agent import Agent
from agentscope.skill import LocalSkillLoader
from agentscope.tool import Toolkit

from ..catalog import AGENT_ENTRY_TOOLS

BUSINESS_TOOLS = set(AGENT_ENTRY_TOOLS)

TEST_TOOLS = {"slow_mock_statistics"}

ALLOWED_TOOLS = (
    BUSINESS_TOOLS
    | TEST_TOOLS
    | {"TaskCreate", "TaskGet", "TaskList", "TaskUpdate", "ToolStop", "Skill"}
)


class RestrictedAgent(Agent):
    """只调整工具装配，随后使用父类 Agent 的全部原生执行流程。"""

    def __init__(self, *args, **kwargs):
        # 第 1 步：取得 Agent Service 已装配的 Toolkit。
        # 原生装配会合并工作区工具、计划工具、默认能力和额外业务工具。
        assembled = kwargs.get("toolkit")
        if assembled is None:
            raise ValueError("原型必须接收服务装配的工具清单。")
        # 第 2 步：逐个工具组展开工具，只保留允许清单中的对象。
        # extra_agent_tools 只能增加工具，因此需要在这里限制最终清单。
        tools = [
            tool
            for group in assembled.tool_groups
            for tool in group.tools
            if tool.name in ALLOWED_TOOLS
        ]
        skills = [
            skill
            for group in assembled.tool_groups
            for skill in (group.skills_or_loaders or [])
        ]
        skills.append(LocalSkillLoader(str(files("cnlc_agent").joinpath("skills")), scan_subdir=True))
        # 第 3 步：检查专业业务能力是否全部到位，避免不完整装配后继续聊天。
        if not BUSINESS_TOOLS <= {tool.name for tool in tools}:
            raise ValueError("业务工具装配不完整。")
        # 第 4 步：建立仅含已选工具的 Toolkit，再交给原生 Agent。
        kwargs["toolkit"] = Toolkit(tools=tools, skills_or_loaders=skills)
        super().__init__(*args, **kwargs)
