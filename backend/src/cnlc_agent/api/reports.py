"""reports 业务 HTTP 路由。"""

from fastapi import APIRouter, Depends, HTTPException

from ..runtime import Runtime
from .dependencies import get_runtime, owned_session

router = APIRouter()


@router.get("/business/sessions/{session_id}/reports/{report_id}")
async def get_report(
    session_id: str,
    report_id: str,
    owner: str = Depends(owned_session),
    runtime: Runtime = Depends(get_runtime),
):
    """读取绑定具体运行和结果版本的演示或诊断报告。"""
    report = runtime.workflow_store.get_report(owner, session_id, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在。")
    return report
