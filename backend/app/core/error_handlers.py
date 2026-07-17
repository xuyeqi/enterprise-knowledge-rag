"""把后端运行异常转换为稳定且不泄露内部细节的 HTTP 响应。

这个模块位于 core（核心基础设施）层，由 ``app.main`` 在应用创建时注册。
业务服务仍然抛出真实异常，便于事务回滚和测试；只有异常到达 HTTP 边界时，
这里才把模型、数据库和未知异常转换为前端可理解的状态码与 ``detail`` 文案。
"""

# logging 用于记录异常类别，方便排查服务类型，同时不输出可能包含上游响应、
# 数据库地址或其它敏感内容的完整异常文本。
import logging

from fastapi import FastAPI, Request, status
# OpenAIError 是 OpenAI 兼容 SDK 的异常基类，覆盖百炼请求的连接、超时、鉴权、
# 限流和服务端错误。项目通过该 SDK 调用 embedding 与聊天模型。
from openai import OpenAIError
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.services.answering import ChatResponseError
from app.services.embedding import EmbeddingResponseError


logger = logging.getLogger(__name__)

# 面向前端的提示保持简洁稳定，不包含底层异常文本。前端现有 HTTP 工具已经会读取
# FastAPI 的 detail 字段，因此无需改变页面接口或增加新的响应协议。
UPSTREAM_ERROR_MESSAGE = "模型服务暂时不可用，请稍后重试。"
DATABASE_ERROR_MESSAGE = "数据库服务暂时不可用，请稍后重试。"
INTERNAL_ERROR_MESSAGE = "服务暂时不可用，请稍后重试。"


def build_error_response(*, status_code: int, message: str) -> JSONResponse:
    """构造所有服务端运行异常共用的 FastAPI 风格 JSON 响应。"""

    return JSONResponse(
        status_code=status_code,
        content={"detail": message},
    )


async def handle_upstream_error(
    _request: Request,
    error: Exception,
) -> JSONResponse:
    """把模型 SDK 或模型响应异常转换为 HTTP 502。"""

    logger.error("upstream model service failed: %s", type(error).__name__)
    return build_error_response(
        status_code=status.HTTP_502_BAD_GATEWAY,
        message=UPSTREAM_ERROR_MESSAGE,
    )


async def handle_database_error(
    _request: Request,
    error: Exception,
) -> JSONResponse:
    """把 SQLAlchemy 连接或查询异常转换为 HTTP 503。"""

    logger.error("database service failed: %s", type(error).__name__)
    return build_error_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        message=DATABASE_ERROR_MESSAGE,
    )


async def handle_unexpected_error_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """兜底捕获未分类异常，避免 ASGI 服务器再次输出原始异常文本。"""

    try:
        return await call_next(request)
    except Exception as error:
        logger.error("unexpected application error: %s", type(error).__name__)
        return build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=INTERNAL_ERROR_MESSAGE,
        )


def register_error_handlers(app: FastAPI) -> None:
    """在 FastAPI 应用上注册模型、数据库和未知异常处理器。

    更具体的异常类型会优先匹配；FastAPI 自带的参数校验和 HTTPException 处理器
    不受影响，因此现有上传校验仍保持原来的 4xx 状态码与 detail 文案。
    """

    for exception_type in (
        OpenAIError,
        EmbeddingResponseError,
        ChatResponseError,
    ):
        app.add_exception_handler(exception_type, handle_upstream_error)

    app.add_exception_handler(SQLAlchemyError, handle_database_error)
    # Starlette 的全局 Exception handler 在返回响应后仍会把异常重新抛给服务器。
    # 这里使用最外层 HTTP 中间件直接结束请求，避免 uvicorn 再记录可能包含内部
    # 细节的原始未知异常。已注册的具体异常仍由上面的专用处理器优先处理。
    app.middleware("http")(handle_unexpected_error_middleware)
