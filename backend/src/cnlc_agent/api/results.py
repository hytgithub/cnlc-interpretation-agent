"""results 业务 HTTP 路由。"""

from fastapi import APIRouter, Depends, HTTPException

from ..business.comparison import compare_results as compare_result_versions
from ..contracts.workflow import ComparisonRequest
from ..runtime import Runtime
from .dependencies import get_runtime, owned_session

router = APIRouter()


@router.get("/business/sessions/{session_id}/results")
async def list_results(
    session_id: str,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    """读取本会话所有演示结果版本。"""
    return {"results": runtime.workflow_store.list_results(owner, session_id)}


@router.get("/business/sessions/{session_id}/results/{result_id}")
async def get_result(
    session_id: str,
    result_id: str,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    """读取一个结果版本及其 Mock 来源。"""
    result = runtime.workflow_store.get_result(owner, session_id, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="结果版本不存在。")
    return result


@router.post("/business/sessions/{session_id}/comparisons")
async def compare_results(
    session_id: str,
    request: ComparisonRequest,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    """递归比较同一会话中两个明确结果版本的结构化内容。"""
    left = runtime.workflow_store.get_result(
        owner, session_id, request.left_result_revision_id
    )
    right = runtime.workflow_store.get_result(
        owner, session_id, request.right_result_revision_id
    )
    if left is None or right is None:
        raise HTTPException(status_code=404, detail="待比较结果版本不存在。")
    return compare_result_versions(left, right)
