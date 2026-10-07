"""业务拒绝到 HTTP 错误响应的映射。"""

from fastapi.responses import JSONResponse

from ..business.errors import BusinessError


async def handle_business_error(request, error):
    return JSONResponse(
        error.payload(), status_code=409 if error.code == "STALE_SELECTION" else 422
    )


def register_error_handlers(app):
    app.add_exception_handler(BusinessError, handle_business_error)
