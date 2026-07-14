"""编排文档切片、向量生成和数据库持久化。

这个服务位于 HTTP 接口与底层能力之间：接口负责接收文件，`text_splitter`
负责切片，`embedding` 负责调用百炼，本文件负责把这些步骤按正确顺序串起来，
最后使用 SQLAlchemy 把一条文档记录和它的全部切片写入 PostgreSQL。
"""

# AsyncSession 是 SQLAlchemy 的异步数据库会话类型，用于执行提交和回滚。
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentChunk
from app.services.embedding import MAX_EMBEDDING_BATCH_SIZE, embed_texts
from app.services.text_splitter import split_text


async def embed_chunks_in_batches(chunks: list[str]) -> list[list[float]]:
    """按百炼单次最多 10 条的限制，为全部切片生成向量。

    参数：
        chunks：按原文顺序排列的非空文本切片。

    返回值：
        与 chunks 顺序一一对应的二维向量列表，每个向量应包含 1024 个数。

    执行步骤：
        1. 每次从切片列表中取出最多 10 条。
        2. 调用 `embed_texts` 等待百炼返回这一批向量。
        3. 按批次顺序合并结果，保持向量与原切片下标一致。

    异常：
        网络、鉴权或响应校验异常会直接向上传递。调用方收到异常后不会开始
        数据库写入，因此不会留下只有部分切片的不完整文档。
    """

    vectors: list[list[float]] = []

    # range 的步长是百炼单批上限，因此 start 依次为 0、10、20……。
    for start in range(0, len(chunks), MAX_EMBEDDING_BATCH_SIZE):
        batch = chunks[start : start + MAX_EMBEDDING_BATCH_SIZE]
        batch_vectors = await embed_texts(batch)
        vectors.extend(batch_vectors)

    return vectors


async def index_document(
    session: AsyncSession,
    *,
    filename: str,
    content_type: str,
    text: str,
) -> Document:
    """将一份已校验的文本文档完整写入向量数据库。

    参数：
        session：由 FastAPI 数据库依赖为当前请求创建的异步会话。
        filename：已经移除客户端路径信息的安全文件名。
        content_type：根据文件扩展名确定的媒体类型。
        text：已经按 UTF-8 解码并确认非空的完整文档文本。

    返回值：
        已成功提交的 Document ORM 对象，可读取 id、status 和 chunks。

    执行步骤：
        1. 把原文切成有顺序的文本片段。
        2. 在数据库事务开始前生成全部 embedding，避免慢速远程请求长期占用
           数据库连接，也避免模型调用中途失败时留下半份数据。
        3. 创建一条 Document 和与切片数量相同的 DocumentChunk。
        4. 一次 commit 提交整份文档；写库失败时 rollback 整体回滚。
    """

    chunks = split_text(text)
    vectors = await embed_chunks_in_batches(chunks)

    # embed_texts 已逐批校验返回数量。这里再次检查总数，防止未来修改批处理
    # 逻辑时发生切片和向量错位后仍继续写入数据库。
    if len(vectors) != len(chunks):
        raise RuntimeError("embedding count does not match document chunk count")

    document = Document(
        filename=filename,
        content_type=content_type,
        status="indexed",
    )

    # relationship 允许直接把切片对象挂到 document.chunks。提交 document 时，
    # SQLAlchemy 会先写 documents，再自动使用它的主键写入 document_chunks。
    document.chunks = [
        DocumentChunk(
            chunk_index=index,
            content=chunk,
            embedding=vector,
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]

    try:
        session.add(document)

        # commit 是事务成功边界：只有文档和所有切片都能写入时才会真正提交。
        await session.commit()
    except Exception:
        # rollback 清除当前失败事务。否则同一个会话不能继续执行数据库操作。
        # 这里不吞掉原异常，上层仍会得到真实错误并返回请求失败。
        await session.rollback()
        raise

    return document
