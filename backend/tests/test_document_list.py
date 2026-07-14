"""验证文档列表接口的响应结构、空列表和查询约束。

测试用假异步会话返回内存数据，不连接 PostgreSQL。除了检查 HTTP 响应，还会
检查 SQLAlchemy 生成的查询包含切片计数、外连接和创建时间倒序。
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from app.db.session import get_database_session
from app.main import app


class FakeResult:
    """模拟 SQLAlchemy 查询结果，只实现接口实际使用的 all 方法。"""

    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def all(self) -> list[SimpleNamespace]:
        """返回假数据库行。"""

        return self._rows


def test_list_documents_returns_summaries_in_query_order() -> None:
    """确认接口返回文档摘要，并生成不读取 embedding 的聚合查询。"""

    first_id = UUID("12345678-1234-5678-1234-567812345678")
    second_id = UUID("87654321-4321-8765-4321-876543218765")
    first_created_at = datetime(2026, 7, 14, 8, 30, tzinfo=UTC)
    second_created_at = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)

    class FakeSession:
        """记录列表接口提交的查询，并返回两条倒序数据。"""

        async def execute(self, statement):
            compiled_sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
            assert "count(document_chunks.id)" in compiled_sql
            assert "LEFT OUTER JOIN document_chunks" in compiled_sql
            assert "ORDER BY documents.created_at DESC" in compiled_sql
            assert "document_chunks.embedding" not in compiled_sql

            return FakeResult(
                [
                    SimpleNamespace(
                        id=first_id,
                        filename="new-policy.md",
                        status="indexed",
                        chunk_count=3,
                        created_at=first_created_at,
                    ),
                    SimpleNamespace(
                        id=second_id,
                        filename="old-guide.txt",
                        status="indexed",
                        chunk_count=1,
                        created_at=second_created_at,
                    ),
                ]
            )

    async def fake_database_session():
        """向 FastAPI 提供假会话。"""

        yield FakeSession()

    app.dependency_overrides[get_database_session] = fake_database_session

    try:
        response = TestClient(app).get("/documents")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [item["document_id"] for item in body] == [str(first_id), str(second_id)]
    assert body[0]["filename"] == "new-policy.md"
    assert body[0]["status"] == "indexed"
    assert body[0]["chunk_count"] == 3
    assert datetime.fromisoformat(body[0]["created_at"]) == first_created_at


def test_list_documents_returns_empty_list() -> None:
    """确认知识库没有文档时返回空数组，而不是 404 或 null。"""

    class FakeSession:
        async def execute(self, statement):
            assert statement is not None
            return FakeResult([])

    async def fake_database_session():
        yield FakeSession()

    app.dependency_overrides[get_database_session] = fake_database_session

    try:
        response = TestClient(app).get("/documents")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []
