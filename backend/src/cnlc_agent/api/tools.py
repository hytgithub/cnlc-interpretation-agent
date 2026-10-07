"""tools 业务 HTTP 路由。"""

from fastapi import APIRouter, Depends

from ..runtime import Runtime
from .dependencies import get_runtime, owned_session

router = APIRouter()


@router.get("/business/sessions/{session_id}/tools")
async def get_tools(
    session_id: str,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    return {"manifest": runtime.business_store.manifest(owner, session_id)}
