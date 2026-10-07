"""runs 业务 HTTP 路由。"""

from fastapi import APIRouter, Depends, HTTPException

from ..business.service import BusinessService
from ..contracts.workflow import WorkflowRequest
from ..runtime import Runtime
from .dependencies import get_runtime, owned_session

router = APIRouter()


@router.get("/business/sessions/{session_id}/runs")
async def get_runs(
    session_id: str,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    return {"runs": runtime.business_store.runs(owner, session_id)}


@router.post("/business/sessions/{session_id}/interpretation-runs")
async def start_interpretation(
    session_id: str,
    request: WorkflowRequest,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    """保留 HTTP 演示入口；模型直接调用专业工具，由 Skill 组织流程。"""
    service = BusinessService(runtime.business_store, runtime.well, owner, session_id)
    selection = service.selection(request.expected_selection_revision)
    run = runtime.workflow.start(owner, session_id, selection, request.scenario_id)
    return runtime.workflow_store.run_summary(run)


@router.get("/business/sessions/{session_id}/interpretation-runs")
async def list_interpretation_runs(
    session_id: str,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    """读取本会话的 Mock Workflow 运行列表。"""
    return {"runs": runtime.workflow_store.list_runs(owner, session_id)}


@router.get("/business/sessions/{session_id}/interpretation-runs/{run_id}")
async def get_interpretation_run(
    session_id: str,
    run_id: str,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    """按用户与会话归属读取运行步骤、结果和 Provider 投影记录。"""
    run = runtime.workflow_store.get_run(owner, session_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="运行不存在。")
    return run
