"""验证知识库向量检索服务和 HTTP 接口。

测试会用假 embedding 函数和假数据库会话替换真实外部资源，因此不会读取
`.env`、调用百炼或查询 PostgreSQL。真实检索效果需要在离线测试通过后，
再由开发者通过 Swagger 使用已经入库的文档验证。
"""

import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

# 导入 API 模块便于替换它内部引用的检索服务函数。
from app.api import search as search_api
from app.db.session import get_database_session
from app.main import app
from app.services import retrieval as retrieval_service
from app.services.retrieval import RetrievedDocumentChunk


class FakeQueryResult:
    """模拟 SQLAlchemy execute 返回的结果对象。"""

    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self.rows = rows

    def all(self) -> list[SimpleNamespace]:
        """返回测试预先准备的全部查询结果行。"""

        return self.rows


class FakeAsyncSession:
    """记录服务层生成的 SELECT 语句，并返回本地假查询结果。"""

    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self.rows = rows
        self.statement = None

    async def execute(self, statement):
        """模拟异步数据库查询，不连接 PostgreSQL。"""

        self.statement = statement
        return FakeQueryResult(self.rows)


def test_retrieve_document_chunks_uses_cosine_distance(monkeypatch) -> None:
    """确认问题只向量化一次，并使用余弦距离返回相似度和来源。"""

    received_embedding_inputs: list[list[str]] = []

    async def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        """记录 embedding 输入，并返回一条 1024 维问题向量。"""

        received_embedding_inputs.append(texts)
        return [[0.1] * 1024]

    monkeypatch.setattr(retrieval_service, "embed_texts", fake_embed_texts)

    chunk_id = UUID("11111111-1111-1111-1111-111111111111")
    document_id = UUID("22222222-2222-2222-2222-222222222222")
    session = FakeAsyncSession(
        rows=[
            SimpleNamespace(
                chunk_id=chunk_id,
                document_id=document_id,
                filename="expense-policy.md",
                chunk_index=2,
                content="出差期间产生的出租车费用可以报销。",
                cosine_distance=0.2,
            )
        ]
    )

    chunks = asyncio.run(
        retrieval_service.retrieve_document_chunks(
            session,
            query="打车费怎么报销？",
            limit=3,
        )
    )

    assert received_embedding_inputs == [["打车费怎么报销？"]]
    assert len(chunks) == 1
    assert chunks[0].chunk_id == chunk_id
    assert chunks[0].document_id == document_id
    assert chunks[0].filename == "expense-policy.md"
    assert chunks[0].chunk_index == 2
    assert chunks[0].content == "出差期间产生的出租车费用可以报销。"
    assert chunks[0].similarity == pytest.approx(0.8)

    # 把 SQLAlchemy 表达式编译成 PostgreSQL SQL，只检查语句结构，不执行查询。
    # `<=>` 是 pgvector 的余弦距离运算符，出现它说明查询没有误用普通字符串匹配。
    compiled_sql = str(
        session.statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )
    assert "<=>" in compiled_sql
    assert "documents.status" in compiled_sql
    assert "ORDER BY" in compiled_sql


def test_retrieve_document_chunks_returns_empty_list(monkeypatch) -> None:
    """确认数据库没有已索引切片时返回空列表，而不是伪造结果。"""

    async def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        """为无结果分支提供合法的问题向量。"""

        return [[0.1] * 1024]

    monkeypatch.setattr(retrieval_service, "embed_texts", fake_embed_texts)
    session = FakeAsyncSession(rows=[])

    chunks = asyncio.run(
        retrieval_service.retrieve_document_chunks(
            session,
            query="不存在的问题",
            limit=3,
        )
    )

    assert chunks == []


def test_search_endpoint_returns_related_chunks(monkeypatch) -> None:
    """确认 POST /search 返回清理后的问题、相似度、切片和文件来源。"""

    chunk_id = UUID("11111111-1111-1111-1111-111111111111")
    document_id = UUID("22222222-2222-2222-2222-222222222222")

    async def fake_database_session():
        """向 FastAPI 提供假会话，阻止测试连接真实数据库。"""

        yield object()

    async def fake_retrieve_document_chunks(
        session,
        *,
        query: str,
        limit: int,
    ) -> list[RetrievedDocumentChunk]:
        """确认接口向服务层传入清理后的参数，并返回一个假切片。"""

        assert session is not None
        assert query == "打车费怎么报销？"
        assert limit == 2
        return [
            RetrievedDocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                filename="expense-policy.md",
                chunk_index=2,
                content="出差期间产生的出租车费用可以报销。",
                similarity=0.91,
            )
        ]

    app.dependency_overrides[get_database_session] = fake_database_session
    monkeypatch.setattr(
        search_api,
        "retrieve_document_chunks",
        fake_retrieve_document_chunks,
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/search",
            json={"query": "  打车费怎么报销？  ", "limit": 2},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "query": "打车费怎么报销？",
        "result_count": 1,
        "results": [
            {
                "chunk_id": str(chunk_id),
                "document_id": str(document_id),
                "filename": "expense-policy.md",
                "chunk_index": 2,
                "content": "出差期间产生的出租车费用可以报销。",
                "similarity": 0.91,
            }
        ],
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"query": "   ", "limit": 3},
        {"query": "正常问题", "limit": 0},
        {"query": "正常问题", "limit": 11},
    ],
)
def test_search_endpoint_rejects_invalid_request(payload: dict, monkeypatch) -> None:
    """确认空白问题和超出 1～10 的 limit 会在模型调用前返回 HTTP 422。"""

    async def fake_database_session():
        """替换真实数据库会话，保证参数校验测试完全离线。"""

        yield object()

    async def unexpected_retrieval_call(*args, **kwargs):
        """如果无效参数仍进入检索服务，立刻让测试失败。"""

        raise AssertionError("invalid request must not reach retrieval service")

    app.dependency_overrides[get_database_session] = fake_database_session
    monkeypatch.setattr(
        search_api,
        "retrieve_document_chunks",
        unexpected_retrieval_call,
    )

    try:
        client = TestClient(app)
        response = client.post("/search", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
