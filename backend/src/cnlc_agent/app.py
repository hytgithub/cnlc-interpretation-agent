"""装配 AgentScope、业务依赖、HTTP 路由和生命周期。"""

from pathlib import Path

from agentscope.app import create_app
from agentscope.app.workspace_manager import IsolationPolicy, LocalWorkspaceManager

from .agent.middleware import ContextMiddleware
from .agent.models.environment import EnvironmentModelCredential
from .agent.models.scripted import ScriptedCredential
from .agent.policy import RestrictedAgent
from .agent.tools import make_tools
from .api import health, plots, reports, results, runs, selection, tools, well
from .api.errors import register_error_handlers
from .api.frontend import register_frontend
from .business.service import BusinessService
from .cli import main
from .contracts.workflow import ComparisonRequest, WorkflowRequest
from .lifecycle import install_lifecycle
from .runtime import build_runtime

__all__ = ["build_app", "main", "WorkflowRequest", "ComparisonRequest"]


def build_app(
    data_dir: Path | str = "var",
    bus_mode: str = "simulated",
    redis_url: str | None = None,
    include_test_tools: bool = False,
):
    """创建保持原生聊天循环和现有业务接口的本地服务。"""
    runtime = build_runtime(data_dir, bus_mode, redis_url, include_test_tools)

    async def tool_factory(user_id, agent_id, session_id):
        service = BusinessService(
            runtime.business_store, runtime.well, user_id, session_id
        )
        return make_tools(service, include_test_tools=include_test_tools, agent_id=agent_id)

    async def middleware_factory(user_id, agent_id, session_id):
        service = BusinessService(
            runtime.business_store, runtime.well, user_id, session_id
        )
        return [ContextMiddleware(service)]

    app = create_app(
        storage=runtime.storage,
        message_bus=runtime.bus,
        workspace_manager=LocalWorkspaceManager(
            str(runtime.root / "workspaces"), isolation=IsolationPolicy.PER_SESSION
        ),
        extra_credentials=[ScriptedCredential, EnvironmentModelCredential],
        extra_agent_tools=tool_factory,
        extra_agent_middlewares=middleware_factory,
        custom_agent_cls=RestrictedAgent,
        enable_channel_worker=False,
        enable_scheduler=False,
        enable_index_worker=False,
        title="测井框架验证原型",
    )
    app.state.runtime = runtime
    for name in ("business_store", "mock_well", "workflow_store", "mock_workflow"):
        attribute = {"mock_well": "well", "mock_workflow": "workflow"}.get(name, name)
        setattr(app.state, name, getattr(runtime, attribute))
    install_lifecycle(app, runtime)
    register_error_handlers(app)
    for module in (health, well, selection, runs, results, reports, tools, plots):
        app.include_router(module.router)
    register_frontend(app)
    return app


if __name__ == "__main__":
    main()
