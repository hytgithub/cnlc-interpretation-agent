"""HTTP 共享资源依赖与原生会话归属检查。"""

from agentscope.app.deps import get_current_user_id
from fastapi import Depends, HTTPException, Request

from ..runtime import Runtime


def get_runtime(request: Request) -> Runtime:
    return request.app.state.runtime


async def owned_session(
    session_id: str,
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
    runtime: Runtime = Depends(get_runtime),
):
    session = await runtime.storage.get_session(user_id, agent_id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在。")
    return user_id
