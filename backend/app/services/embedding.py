"""调用阿里云百炼文本向量接口，将文本转换为 1024 维向量。

百炼提供 OpenAI 兼容接口，所以这里使用 `AsyncOpenAI` 客户端。这个模块
只负责文本到向量的转换和响应校验，不负责文档切片或写入 PostgreSQL。
"""

# lru_cache 用于复用客户端。复用客户端可以复用底层 HTTP 连接，避免每次调用
# embedding API 都重新创建连接资源。
from functools import lru_cache

# AsyncOpenAI 是 OpenAI Python SDK 的异步客户端。把 base_url 指向百炼后，
# SDK 会把请求发送到百炼的 OpenAI 兼容接口，而不是 OpenAI 官方服务器。
from openai import AsyncOpenAI

from app.core.config import EmbeddingSettings, get_embedding_settings


# 百炼 text-embedding-v4 同步接口每次最多接收 10 条文本。
# 这是服务商接口限制，不做成环境变量，避免配置超过上限后产生远程报错。
MAX_EMBEDDING_BATCH_SIZE = 10


class EmbeddingResponseError(RuntimeError):
    """表示百炼返回的向量数量或维度不符合项目约定。"""


@lru_cache
def get_embedding_client() -> AsyncOpenAI:
    """创建并缓存百炼 OpenAI 兼容异步客户端。

    返回值：
        AsyncOpenAI 客户端。它已配置本地 `.env` 中的百炼 API Key 和地址。
    """

    settings = get_embedding_settings()

    # get_secret_value 只在创建 HTTP 客户端时取出原始 Key，不记录或打印它。
    return AsyncOpenAI(
        api_key=settings.api_key.get_secret_value(),
        base_url=settings.base_url,
    )


def validate_embedding_inputs(texts: list[str]) -> None:
    """在产生远程请求和费用前检查输入文本。

    参数：
        texts：等待向量化的字符串列表。

    异常：
        列表为空、超过百炼单批上限，或包含空白文本时抛出 ValueError。
    """

    if not texts:
        raise ValueError("texts must contain at least one item")

    if len(texts) > MAX_EMBEDDING_BATCH_SIZE:
        raise ValueError(
            f"one embedding request supports at most {MAX_EMBEDDING_BATCH_SIZE} texts"
        )

    # enumerate 同时提供列表下标和文本，报错时可以指出具体是哪一项无效。
    for index, text in enumerate(texts):
        if not text.strip():
            raise ValueError(f"texts[{index}] must not be empty")


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """把一批文本转换为顺序一致的 1024 维 dense embedding。

    参数：
        texts：1 到 10 条非空文本。返回结果与输入列表按下标一一对应。

    返回值：
        二维浮点数列表。外层长度等于输入条数，每个内层列表包含 1024 个数。

    异常：
        输入不合法时抛出 ValueError；远程响应数量、下标或维度不符合约定时
        抛出 EmbeddingResponseError；网络或鉴权错误由 OpenAI SDK 原样抛出。
    """

    validate_embedding_inputs(texts)

    settings: EmbeddingSettings = get_embedding_settings()
    client = get_embedding_client()

    # await 等待远程 API 返回，同时允许 FastAPI 处理其它请求。
    response = await client.embeddings.create(
        model=settings.model,
        input=texts,
        dimensions=settings.dimension,
        encoding_format="float",
    )

    # 百炼响应中的 index 表示向量对应输入列表的下标。显式排序可以保证即使
    # 服务端返回顺序变化，最终结果仍与 texts 的顺序一致。
    ordered_items = sorted(response.data, key=lambda item: item.index)
    returned_indices = [item.index for item in ordered_items]
    expected_indices = list(range(len(texts)))

    if returned_indices != expected_indices:
        raise EmbeddingResponseError(
            "embedding response indices do not match input texts"
        )

    vectors = [item.embedding for item in ordered_items]

    # 数据库字段是 vector(1024)。这里在写库前提前发现服务端配置或响应异常。
    for index, vector in enumerate(vectors):
        if len(vector) != settings.dimension:
            raise EmbeddingResponseError(
                f"embedding[{index}] has {len(vector)} dimensions; "
                f"expected {settings.dimension}"
            )

    return vectors
