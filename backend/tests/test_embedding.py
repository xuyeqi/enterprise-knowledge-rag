"""验证 embedding 服务的输入校验、请求参数和响应校验。

这些测试使用本地假客户端代替百炼，不读取真实 API Key、不访问网络，也不会
消耗任何模型额度。真实接口由 scripts/check_embedding.py 单独手动验证。
"""

import asyncio
from types import SimpleNamespace

import pytest

# 导入模块而不是只导入函数，便于 monkeypatch 临时替换模块中的配置和客户端。
from app.services import embedding as embedding_service


class FakeEmbeddingsAPI:
    """模拟 `client.embeddings`，记录请求参数并返回预设响应。"""

    def __init__(self, response) -> None:
        self.response = response
        self.request_kwargs: dict | None = None

    async def create(self, **kwargs):
        """模拟异步 create 方法，不发送任何网络请求。"""

        self.request_kwargs = kwargs
        return self.response


class FakeEmbeddingClient:
    """提供与本次代码所需结构一致的最小 OpenAI 假客户端。"""

    def __init__(self, response) -> None:
        self.embeddings = FakeEmbeddingsAPI(response)


def make_embedding_item(index: int, dimension: int, value: float):
    """创建一条带 index 和 embedding 属性的假响应记录。"""

    return SimpleNamespace(index=index, embedding=[value] * dimension)


def test_embed_texts_returns_vectors_in_input_order(monkeypatch) -> None:
    """确认请求参数正确，并按响应 index 恢复为输入顺序。"""

    settings = SimpleNamespace(model="text-embedding-v4", dimension=1024)

    # 故意把 index=1 放在前面，验证服务函数会按 index 排序。
    response = SimpleNamespace(
        data=[
            make_embedding_item(index=1, dimension=1024, value=0.2),
            make_embedding_item(index=0, dimension=1024, value=0.1),
        ]
    )
    client = FakeEmbeddingClient(response)

    monkeypatch.setattr(
        embedding_service,
        "get_embedding_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        embedding_service,
        "get_embedding_client",
        lambda: client,
    )

    vectors = asyncio.run(embedding_service.embed_texts(["第一段", "第二段"]))

    assert vectors[0][0] == 0.1
    assert vectors[1][0] == 0.2
    assert len(vectors[0]) == 1024
    assert client.embeddings.request_kwargs == {
        "model": "text-embedding-v4",
        "input": ["第一段", "第二段"],
        "dimensions": 1024,
        "encoding_format": "float",
    }


@pytest.mark.parametrize("texts", [[], [""], ["   "]])
def test_embed_texts_rejects_empty_input(texts: list[str]) -> None:
    """确认无内容的请求在调用远程 API 前就会失败。"""

    with pytest.raises(ValueError):
        asyncio.run(embedding_service.embed_texts(texts))


def test_embed_texts_rejects_more_than_ten_items() -> None:
    """确认单批文本数量不会超过百炼官方限制。"""

    texts = [f"文本 {index}" for index in range(11)]

    with pytest.raises(ValueError, match="at most 10"):
        asyncio.run(embedding_service.embed_texts(texts))


def test_embed_texts_rejects_wrong_vector_dimension(monkeypatch) -> None:
    """确认返回向量不是 1024 维时不会继续交给数据库。"""

    settings = SimpleNamespace(model="text-embedding-v4", dimension=1024)
    response = SimpleNamespace(
        data=[make_embedding_item(index=0, dimension=512, value=0.1)]
    )
    client = FakeEmbeddingClient(response)

    monkeypatch.setattr(
        embedding_service,
        "get_embedding_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        embedding_service,
        "get_embedding_client",
        lambda: client,
    )

    with pytest.raises(
        embedding_service.EmbeddingResponseError,
        match="expected 1024",
    ):
        asyncio.run(embedding_service.embed_texts(["测试文本"]))
