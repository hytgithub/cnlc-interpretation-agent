"""selection 业务 HTTP 路由。"""

from fastapi import APIRouter, Depends

from ..contracts.selection import SelectionRequest
from ..runtime import Runtime
from .dependencies import get_runtime, owned_session

router = APIRouter()


@router.put("/business/sessions/{session_id}/selection")
async def set_selection(
    session_id: str,
    request: SelectionRequest,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    return runtime.business_store.set_selection(
        owner, session_id, request, runtime.well
    )


@router.get("/business/sessions/{session_id}/selection")
async def get_selection(
    session_id: str,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    return {"selection": runtime.business_store.selection(owner, session_id)}
