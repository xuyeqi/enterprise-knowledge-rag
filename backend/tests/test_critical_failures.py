"""验证关键 RAG 链路跨越 API、服务层和事务边界时的失败行为。

与只测试单个函数的用例不同，本文件通过 FastAPI TestClient 发起真实 HTTP 请求，
保留生产接口和服务编排，只替换百炼与 PostgreSQL 这些外部资源。测试不会读取
``.env``、不会产生模型费用，也不会连接真实数据库。
"""

from uuid import UUID

from fastapi.testclient import TestClient
from openai import OpenAIError
from sqlalchemy.exc import SQLAlchemyError

from app.core.error_handlers import DATABASE_ERROR_MESSAGE, UPSTREAM_ERROR_MESSAGE
from app.db.session import get_database_session
from app.main import app
from app.services import answering as answering_service
from app.services import document_indexing as indexing_service
from app.services import retrieval as retrieval_service
from app.services.retrieval import RetrievedDocumentChunk


class FakeAsyncSession:
    """记录关键数据库动作，并按测试需要模拟提交或查询失败。"""

    def __init__(
        self,
        *,
        commit_error: Exception | None = None,
        execute_error: Exception | None = None,
    ) -> None:
        self.commit_error = commit_error
        self.execute_error = execute_error
        self.added_object = None
        self.commit_called = False
        self.rollback_called = False
        self.execute_called = False

    def add(self, value) -> None:
        """记录 ORM 对象是否已经进入待提交状态。"""

        self.added_object = value

    async def commit(self) -> None:
        """记录提交动作，并可模拟 SQLAlchemy 提交异常。"""

        self.commit_called = True
        if self.commit_error is not None:
            raise self.commit_error

    async def rollback(self) -> None:
        """记录失败事务是否执行整体回滚。"""

        self.rollback_called = True

    async def execute(self, statement):
        """记录只读查询，并可模拟 SQLAlchemy 查询异常。"""

        assert statement is not None
        self.execute_called = True
        if self.execute_error is not None:
            raise self.execute_error
        raise AssertionError("this test did not configure a query result")


def override_database_session(session: FakeAsyncSession):
    """创建绑定指定假会话的 FastAPI 异步依赖。"""

    async def fake_database_session():
        yield session

    return fake_database_session


def test_document_upload_embedding_failure_returns_502_without_writing(
    monkeypatch,
) -> None:
    """确认文档向量化失败发生在事务前，HTTP 层返回安全的 502。"""

    async def fake_embed_chunks(chunks: list[str]) -> list[list[float]]:
        assert chunks == ["# 公司制度"]
        raise OpenAIError("private embedding failure")

    session = FakeAsyncSession()
    monkeypatch.setattr(
        indexing_service,
        "embed_chunks_in_batches",
        fake_embed_chunks,
    )
    app.dependency_overrides[get_database_session] = override_database_session(
        session
    )

    try:
        response = TestClient(app).post(
            "/documents",
            files={
                "file": (
                    "policy.md",
                    "# 公司制度".encode("utf-8"),
                    "text/markdown",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": UPSTREAM_ERROR_MESSAGE}
    assert "private embedding failure" not in response.text
    assert session.added_object is None
    assert session.commit_called is False
    assert session.rollback_called is False


def test_document_upload_commit_failure_returns_503_and_rolls_back(
    monkeypatch,
) -> None:
    """确认文档提交失败时整体回滚，并由 HTTP 层返回安全的 503。"""

    async def fake_embed_chunks(chunks: list[str]) -> list[list[float]]:
        assert chunks == ["公司制度"]
        return [[0.1] * 1024]

    session = FakeAsyncSession(
        commit_error=SQLAlchemyError("private database failure")
    )
    monkeypatch.setattr(
        indexing_service,
        "embed_chunks_in_batches",
        fake_embed_chunks,
    )
    app.dependency_overrides[get_database_session] = override_database_session(
        session
    )

    try:
        response = TestClient(app).post(
            "/documents",
            files={
                "file": (
                    "policy.txt",
                    "公司制度".encode("utf-8"),
                    "text/plain",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": DATABASE_ERROR_MESSAGE}
    assert "private database failure" not in response.text
    assert session.added_object is not None
    assert session.commit_called is True
    assert session.rollback_called is True


def test_search_query_failure_returns_503_after_embedding(monkeypatch) -> None:
    """确认问题向量生成成功但 pgvector 查询失败时返回 503。"""

    async def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        assert texts == ["公司主要做什么？"]
        return [[0.1] * 1024]

    session = FakeAsyncSession(
        execute_error=SQLAlchemyError("private pgvector query failure")
    )
    monkeypatch.setattr(retrieval_service, "embed_texts", fake_embed_texts)
    app.dependency_overrides[get_database_session] = override_database_session(
        session
    )

    try:
        response = TestClient(app).post(
            "/search",
            json={"query": "公司主要做什么？", "limit": 3},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": DATABASE_ERROR_MESSAGE}
    assert "private pgvector query failure" not in response.text
    assert session.execute_called is True


def test_answer_generation_failure_returns_502_after_retrieval(monkeypatch) -> None:
    """确认检索成功但答案生成失败时，普通问答接口返回安全的 502。"""

    chunk = RetrievedDocumentChunk(
        chunk_id=UUID("11111111-1111-1111-1111-111111111111"),
        document_id=UUID("22222222-2222-2222-2222-222222222222"),
        filename="company.md",
        chunk_index=0,
        page_number=None,
        content="公司主要经营跨境电商。",
        similarity=0.91,
    )

    async def fake_retrieve_document_chunks(*args, **kwargs):
        return [chunk]

    async def fake_generate_grounded_answer(*args, **kwargs):
        raise OpenAIError("private chat failure")

    session = FakeAsyncSession()
    monkeypatch.setattr(
        answering_service,
        "retrieve_document_chunks",
        fake_retrieve_document_chunks,
    )
    monkeypatch.setattr(
        answering_service,
        "generate_grounded_answer",
        fake_generate_grounded_answer,
    )
    app.dependency_overrides[get_database_session] = override_database_session(
        session
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
    assert "private chat failure" not in response.text
