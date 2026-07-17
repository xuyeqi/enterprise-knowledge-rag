"""验证后端应用级错误响应不会泄露模型、数据库或内部异常细节。

测试通过 monkeypatch 和 FastAPI 依赖覆盖制造失败，不访问百炼或 PostgreSQL。
未知异常测试使用 TestClient 默认行为，确认兜底中间件真正结束请求，不会把异常
重新抛给调用方。
"""

from fastapi.testclient import TestClient
from openai import OpenAIError
from sqlalchemy.exc import SQLAlchemyError

from app.api import answer as answer_api
from app.api import search as search_api
from app.core.error_handlers import (
    DATABASE_ERROR_MESSAGE,
    INTERNAL_ERROR_MESSAGE,
    UPSTREAM_ERROR_MESSAGE,
)
from app.db.session import get_database_session
from app.main import app
from app.services.answering import ChatResponseError


async def fake_database_session():
    """向路由提供内存假会话，保证错误测试不连接真实 PostgreSQL。"""

    yield object()


def test_openai_error_returns_502_without_private_detail(monkeypatch) -> None:
    """确认检索模型失败时返回 502，且不暴露 SDK 原始异常文本。"""

    async def fake_retrieve_document_chunks(*args, **kwargs):
        raise OpenAIError("private upstream response")

    app.dependency_overrides[get_database_session] = fake_database_session
    monkeypatch.setattr(
        search_api,
        "retrieve_document_chunks",
        fake_retrieve_document_chunks,
    )

    try:
        response = TestClient(app).post(
            "/search",
            json={"query": "公司主要做什么？", "limit": 3},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": UPSTREAM_ERROR_MESSAGE}
    assert "private upstream response" not in response.text


def test_chat_response_error_returns_502(monkeypatch) -> None:
    """确认模型返回空内容等响应校验异常也使用统一的 502 文案。"""

    async def fake_answer_knowledge_base(*args, **kwargs):
        raise ChatResponseError("private invalid response")

    app.dependency_overrides[get_database_session] = fake_database_session
    monkeypatch.setattr(
        answer_api,
        "answer_knowledge_base",
        fake_answer_knowledge_base,
    )

    try:
        response = TestClient(app).post(
            "/answer",
            json={"query": "公司主要做什么？", "limit": 3},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": UPSTREAM_ERROR_MESSAGE}


def test_database_error_returns_503_without_connection_detail(monkeypatch) -> None:
    """确认数据库健康检查失败时返回 503，而不是普通 500 或连接详情。"""

    async def fake_check_database_connection() -> None:
        raise SQLAlchemyError("private database address")

    monkeypatch.setattr(
        "app.main.check_database_connection",
        fake_check_database_connection,
    )

    response = TestClient(app).get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"detail": DATABASE_ERROR_MESSAGE}
    assert "private database address" not in response.text


def test_unexpected_error_returns_generic_500(monkeypatch) -> None:
    """确认未知异常使用通用 500 文案，不把内部错误直接返回给调用方。"""

    async def fake_retrieve_document_chunks(*args, **kwargs):
        raise RuntimeError("private implementation detail")

    app.dependency_overrides[get_database_session] = fake_database_session
    monkeypatch.setattr(
        search_api,
        "retrieve_document_chunks",
        fake_retrieve_document_chunks,
    )

    try:
        response = TestClient(app).post(
            "/search",
            json={"query": "公司主要做什么？", "limit": 3},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {"detail": INTERNAL_ERROR_MESSAGE}
    assert "private implementation detail" not in response.text
