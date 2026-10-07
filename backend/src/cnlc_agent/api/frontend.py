"""已构建 React 前端的首页、静态资源和受限 SPA 回退。"""

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def register_frontend(app, frontend_dir: Path | None = None):
    frontend_dir = (
        frontend_dir or Path(__file__).resolve().parents[1] / "static" / "agentscope"
    )

    @app.get("/", include_in_schema=False)
    async def agentscope_frontend_home():
        """提供构建后的 AgentScope Web UI。"""
        frontend_index = frontend_dir / "index.html"
        if not frontend_index.is_file():
            raise HTTPException(
                status_code=503,
                detail="AgentScope 前端尚未构建，请运行 pnpm --dir frontend build。",
            )
        return FileResponse(frontend_index)

    frontend_index = frontend_dir / "index.html"
    if frontend_index.is_file():
        assets_dir = frontend_dir / "assets"
        if assets_dir.is_dir():
            app.mount(
                "/assets", StaticFiles(directory=assets_dir), name="agentscope-assets"
            )

        @app.get("/agentscope.svg", include_in_schema=False)
        async def agentscope_frontend_icon():
            return FileResponse(frontend_dir / "agentscope.svg")

        @app.get("/{frontend_path:path}", include_in_schema=False)
        async def agentscope_frontend_routes(frontend_path: str):
            """将 AgentScope 前端的 history 路由回退到 SPA 入口。"""
            if frontend_path.split("/", 1)[0] not in {
                "chat",
                "setup",
                "schedule",
                "channel",
                "credential",
                "mcp",
                "skill",
                "knowledge",
            }:
                raise HTTPException(status_code=404, detail="页面不存在。")
            return FileResponse(frontend_index)
