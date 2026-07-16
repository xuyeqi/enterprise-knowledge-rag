"""验证文档向量入库服务的批处理和事务规则。

这些测试使用内存中的假 embedding 函数和假数据库会话，不读取 `.env`，不会
访问百炼或 PostgreSQL。测试重点是业务编排顺序，而不是重复测试第三方服务。
"""

import asyncio

import pytest

# 导入整个模块，便于 monkeypatch 临时替换模块内部引用的 embed_texts。
from app.services import document_indexing as indexing_service
from app.services.document_parser import ParsedDocumentChunk


class FakeAsyncSession:
    """实现本次服务实际使用的最小 AsyncSession 行为。"""

    def __init__(self, *, commit_error: Exception | None = None) -> None:
        self.commit_error = commit_error
        self.added_object = None
        self.commit_called = False
        self.rollback_called = False

    def add(self, value) -> None:
        """记录准备持久化的 ORM 对象，不连接真实数据库。"""

        self.added_object = value

    async def commit(self) -> None:
        """记录提交动作，并可按测试需要模拟数据库提交失败。"""

        self.commit_called = True
        if self.commit_error is not None:
            raise self.commit_error

    async def rollback(self) -> None:
        """记录失败事务是否执行了整体回滚。"""

        self.rollback_called = True


def test_embed_chunks_in_batches_uses_ten_item_batches(monkeypatch) -> None:
    """确认 23 个切片会按 10、10、3 分批，并保持最终顺序。"""

    received_batches: list[list[str]] = []

    async def fake_embed_texts(texts: list[str]) -> list[list[float]]:
        """为每条输入返回可辨认的假向量，并记录每次批量输入。"""

        received_batches.append(texts)
        return [[float(text.split("-")[1])] for text in texts]

    monkeypatch.setattr(indexing_service, "embed_texts", fake_embed_texts)
    chunks = [f"chunk-{index}" for index in range(23)]

    vectors = asyncio.run(indexing_service.embed_chunks_in_batches(chunks))

    assert [len(batch) for batch in received_batches] == [10, 10, 3]
    assert [vector[0] for vector in vectors] == [float(index) for index in range(23)]


def test_index_document_builds_document_and_chunks(monkeypatch) -> None:
    """确认文档、切片顺序、内容和向量会在一次提交中组装完整。"""

    expected_chunks = [
        ParsedDocumentChunk(content="第一段", page_number=1),
        ParsedDocumentChunk(content="第二段", page_number=2),
    ]
    expected_vectors = [[0.1] * 1024, [0.2] * 1024]

    async def fake_embed_chunks(chunks: list[str]) -> list[list[float]]:
        """返回与两个固定切片一一对应的 1024 维假向量。"""

        assert chunks == ["第一段", "第二段"]
        return expected_vectors

    monkeypatch.setattr(
        indexing_service,
        "embed_chunks_in_batches",
        fake_embed_chunks,
    )
    session = FakeAsyncSession()

    document = asyncio.run(
        indexing_service.index_document(
            session,
            filename="policy.md",
            content_type="text/markdown",
            chunks=expected_chunks,
        )
    )

    assert session.added_object is document
    assert session.commit_called is True
    assert session.rollback_called is False
    assert document.filename == "policy.md"
    assert document.content_type == "text/markdown"
    assert document.status == "indexed"
    assert [chunk.chunk_index for chunk in document.chunks] == [0, 1]
    assert [chunk.page_number for chunk in document.chunks] == [1, 2]
    assert [chunk.content for chunk in document.chunks] == ["第一段", "第二段"]
    assert [chunk.embedding for chunk in document.chunks] == expected_vectors


def test_index_document_does_not_write_when_embedding_fails(monkeypatch) -> None:
    """确认模型调用失败发生在事务前，不会创建任何数据库写入动作。"""

    async def fake_embed_chunks(chunks: list[str]) -> list[list[float]]:
        """模拟百炼鉴权、网络或响应校验失败。"""

        raise RuntimeError("embedding failed")

    monkeypatch.setattr(
        indexing_service,
        "embed_chunks_in_batches",
        fake_embed_chunks,
    )
    session = FakeAsyncSession()

    with pytest.raises(RuntimeError, match="embedding failed"):
        asyncio.run(
            indexing_service.index_document(
                session,
                filename="policy.txt",
                content_type="text/plain",
                chunks=[ParsedDocumentChunk(content="第一段")],
            )
        )

    assert session.added_object is None
    assert session.commit_called is False
    assert session.rollback_called is False


def test_index_document_rolls_back_when_commit_fails(monkeypatch) -> None:
    """确认任意数据库提交错误都会触发 rollback，并把原错误继续抛出。"""

    async def fake_embed_chunks(chunks: list[str]) -> list[list[float]]:
        """返回有效假向量，让测试只聚焦数据库失败分支。"""

        return [[0.1] * 1024]

    monkeypatch.setattr(
        indexing_service,
        "embed_chunks_in_batches",
        fake_embed_chunks,
    )
    session = FakeAsyncSession(commit_error=RuntimeError("database failed"))

    with pytest.raises(RuntimeError, match="database failed"):
        asyncio.run(
            indexing_service.index_document(
                session,
                filename="policy.txt",
                content_type="text/plain",
                chunks=[ParsedDocumentChunk(content="第一段")],
            )
        )

    assert session.commit_called is True
    assert session.rollback_called is True
