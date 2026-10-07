"""扩展原生生命周期：业务恢复、环境凭据初始化和资源关闭。"""

import hashlib
import os
from contextlib import asynccontextmanager

from .agent.models.environment import EnvironmentModelCredential
from .runtime import Runtime


def install_lifecycle(app, runtime: Runtime):
    native_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        runtime.business_store.recover_unfinished()
        try:
            async with native_lifespan(application):
                model_name = os.getenv("MODEL_NAME", "").strip()
                api_key = os.getenv("MODEL_API_KEY", "").strip()
                if model_name and api_key:
                    user_id = (
                        os.getenv("CNLC_DEFAULT_USER_ID", "local-demo").strip()
                        or "local-demo"
                    )
                    credential_id = (
                        "cnlc-env-" + hashlib.sha256(user_id.encode()).hexdigest()[:24]
                    )
                    await runtime.storage.upsert_credential(
                        user_id,
                        EnvironmentModelCredential(
                            id=credential_id, name=f"CNLC .env 模型 · {model_name}"
                        ),
                    )
                yield
        finally:
            await runtime.pool.aclose()

    app.router.lifespan_context = lifespan
