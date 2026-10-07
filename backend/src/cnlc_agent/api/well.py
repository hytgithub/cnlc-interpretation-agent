"""well 业务 HTTP 路由。"""

from agentscope.app.deps import get_current_user_id
from fastapi import APIRouter, Depends, HTTPException

from ..business.errors import BusinessError
from ..business.service import BusinessService
from ..runtime import Runtime
from .dependencies import get_runtime, owned_session

router = APIRouter()


@router.get("/business/well")
async def read_well(
    user_id: str = Depends(get_current_user_id), runtime: Runtime = Depends(get_runtime)
):
    return runtime.well.summary()


@router.get("/business/sessions/{session_id}/curves")
async def get_curves(
    session_id: str,
    curve_name: str | None = None,
    top_depth_m: float | None = None,
    bottom_depth_m: float | None = None,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    """读取选定范围内的原始曲线，不改变选择或计算输入。"""
    if (top_depth_m is None) != (bottom_depth_m is None):
        raise HTTPException(status_code=422, detail="顶深和底深必须同时提供。")
    top = runtime.well.depths[0] if top_depth_m is None else top_depth_m
    bottom = runtime.well.depths[-1] if bottom_depth_m is None else bottom_depth_m
    return runtime.well.curves(top, bottom, curve_name)


@router.get("/business/sessions/{session_id}/intervals")
async def get_intervals(
    session_id: str,
    layer_no: int | None = None,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    """读取与当前选择相交的预设层段，保留样本层界。"""
    selection = runtime.business_store.selection(owner, session_id)
    if selection is None:
        raise BusinessError("SELECTION_REQUIRED", "请先保存井和深度范围。")
    return BusinessService(
        runtime.business_store, runtime.well, owner, session_id
    ).query(selection["revision"], layer_no)


@router.get("/business/sessions/{session_id}/statistics")
async def get_statistics(
    session_id: str,
    curve_name: str = "GR",
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    """计算当前选择范围内的原始曲线统计，页面与 Agent 工具共用函数。"""
    selection = runtime.business_store.selection(owner, session_id)
    if selection is None:
        raise BusinessError("SELECTION_REQUIRED", "请先保存井和深度范围。")
    return BusinessService(
        runtime.business_store, runtime.well, owner, session_id
    ).statistics(selection["revision"], curve_name)
