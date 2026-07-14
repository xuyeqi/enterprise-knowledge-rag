"""验证文档上传预览接口和正式入库接口的 HTTP 行为。

测试客户端会在内存中构造 multipart 文件，不读取本地 sample.md，不访问
PostgreSQL，也不会调用百炼，因此可以稳定验证上传边界和成功响应结构。
"""

# SimpleNamespace 用来构造只包含接口需要字段的假文档对象。
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

# 导入路由模块，便于 monkeypatch 把真实入库服务临时替换成内存假函数。
from app.api import documents as documents_api
from app.api.documents import MAX_UPLOAD_SIZE_BYTES
from app.db.session import get_database_session
from app.main import app


def test_preview_document_returns_short_markdown_chunk() -> None:
    """确认 UTF-8 Markdown 可以上传，并返回一个完整切片。"""

    client = TestClient(app)
    content = "# 报销制度\n\n员工报销需要提供真实有效的费用凭证。"

    response = client.post(
        "/documents/preview",
        files={
            # files 的结构是：字段名 -> (文件名, 二进制内容, 浏览器媒体类型)。
            "file": (
                r"C:\fakepath\GUIDE.MD",
                content.encode("utf-8"),
                "text/markdown",
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "GUIDE.MD"
    assert body["content_type"] == "text/markdown"
    assert body["character_count"] == len(content)
    assert body["chunk_count"] == 1
    assert body["chunks"][0] == {
        "index": 0,
        "character_count": len(content),
        "content": content,
    }


def test_preview_document_splits_long_text() -> None:
    """确认超过默认 800 字符的文本会返回多个切片。"""

    client = TestClient(app)
    content = "这是用于验证上传接口切片结果的中文句子。" * 100

    response = client.post(
        "/documents/preview",
        files={"file": ("policy.txt", content.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chunk_count"] > 1
    assert all(chunk["character_count"] <= 800 for chunk in body["chunks"])


def test_preview_document_rejects_unsupported_extension() -> None:
    """确认当前阶段不会误接收 PDF 等尚未支持的文件。"""

    client = TestClient(app)

    response = client.post(
        "/documents/preview",
        files={"file": ("report.pdf", b"fake pdf", "application/pdf")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "只支持上传 .txt 和 .md 文件"


def test_preview_document_rejects_file_larger_than_two_megabytes() -> None:
    """确认接口只读取到判定超限所需的大小，并返回 413。"""

    client = TestClient(app)
    oversized_content = b"a" * (MAX_UPLOAD_SIZE_BYTES + 1)

    response = client.post(
        "/documents/preview",
        files={"file": ("large.txt", oversized_content, "text/plain")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "文件大小不能超过 2 MB"


def test_preview_document_rejects_non_utf8_file() -> None:
    """确认无法按 UTF-8 解码的字节不会被错误地当作文本。"""

    client = TestClient(app)

    response = client.post(
        "/documents/preview",
        files={"file": ("invalid.txt", b"\xff\xfe\xfa", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "文件必须使用 UTF-8 编码"


@pytest.mark.parametrize("content", [b"", b"  \n\n"])
def test_preview_document_rejects_empty_file(content: bytes) -> None:
    """确认零字节和纯空白文件都不会进入切片流程。"""

    client = TestClient(app)

    response = client.post(
        "/documents/preview",
        files={"file": ("empty.md", content, "text/markdown")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "上传文件不能为空"


def test_create_document_returns_persisted_document_summary(monkeypatch) -> None:
    """确认正式上传成功后返回 HTTP 201、文档 ID、状态和切片数量。"""

    document_id = UUID("12345678-1234-5678-1234-567812345678")

    async def fake_database_session():
        """向 FastAPI 提供假会话，避免测试连接真实 PostgreSQL。"""

        yield object()

    async def fake_index_document(
        session,
        *,
        filename: str,
        content_type: str,
        text: str,
    ):
        """记录接口传入的数据，并返回模拟提交成功的文档对象。"""

        assert session is not None
        assert filename == "policy.md"
        assert content_type == "text/markdown"
        assert text == "# 报销制度"
        return SimpleNamespace(
            id=document_id,
            filename=filename,
            status="indexed",
            chunks=[object(), object()],
        )

    # dependency_overrides 是 FastAPI 专门提供的测试替换机制。它只在当前测试
    # 中把真实会话依赖替换掉，finally 会确保测试结束后恢复应用状态。
    app.dependency_overrides[get_database_session] = fake_database_session
    monkeypatch.setattr(documents_api, "index_document", fake_index_document)

    try:
        client = TestClient(app)
        response = client.post(
            "/documents",
            files={
                "file": (
                    "policy.md",
                    "# 报销制度".encode("utf-8"),
                    "text/markdown",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json() == {
        "document_id": str(document_id),
        "filename": "policy.md",
        "status": "indexed",
        "chunk_count": 2,
    }
