"""health 业务 HTTP 路由。"""

import os

from fastapi import APIRouter, Depends

from ..catalog import capability_manifest
from ..runtime import Runtime
from .dependencies import get_runtime

router = APIRouter()


@router.get("/business/health")
async def health(runtime: Runtime = Depends(get_runtime)):
    model_configured = bool(
        os.getenv("MODEL_NAME", "").strip() and os.getenv("MODEL_API_KEY", "").strip()
    )
    return {
        "mode": "LOCAL_PROTOTYPE",
        "model": "OPENAI_COMPATIBLE_ENV" if model_configured else "SCRIPTED_MOCK",
        "natural_language": "CONFIGURED_UNVERIFIED"
        if model_configured
        else "UNASSESSED",
        "agentscope": "2.0.9",
        "storage": "SQLITE_TEST",
        "bus": runtime.bus_mode,
        "is_mock": True,
        "professional_tools": "CONTRACT_PENDING",
        "test_tools_enabled": runtime.include_test_tools,
        "formal_publication": "DISABLED",
    }


@router.get("/business/capabilities")
async def get_capabilities(runtime: Runtime = Depends(get_runtime)):
    """返回分层能力清单，避免把内部工具和框架控制混为一组。"""
    return capability_manifest(include_test_tools=runtime.include_test_tools)
