"""按原生会话归属读取绘图文件。"""
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..business.plotting import CurvePlotService
from ..business.service import BusinessService
from ..runtime import Runtime
from .dependencies import get_runtime, owned_session

router = APIRouter()


@router.get('/business/sessions/{session_id}/plots/{plot_id}')
async def read_plot(session_id: str, plot_id: str,
                    owner: str = Depends(owned_session), runtime: Runtime = Depends(get_runtime)):
    path = CurvePlotService(BusinessService(runtime.business_store, runtime.well, owner, session_id)).artifact(plot_id)
    return FileResponse(path, media_type='image/svg+xml', filename='well-log-curves.svg',
                        headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})
