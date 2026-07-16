"""把用户问题转换为向量，并从 PostgreSQL 检索相关文档切片。

这个服务属于 RAG 的 Retrieval（检索）阶段：它调用现有 embedding 服务生成
问题向量，再使用 pgvector 的余弦距离与已入库切片比较。当前只返回检索结果，
不调用 LLM，也不负责把切片组织成最终答案。
"""

# dataclass 用来定义服务层返回的轻量结果对象，避免让 API 层直接依赖
# SQLAlchemy 查询结果 Row 的内部结构。
from dataclasses import dataclass

# UUID 用于标注文档和切片主键的 Python 类型。
from uuid import UUID

# select 是 SQLAlchemy 2.x 构造 SELECT 查询的标准函数。
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentChunk
from app.services.embedding import embed_texts


@dataclass(frozen=True)
class RetrievedDocumentChunk:
    """保存一个已经计算好相似度的文档切片检索结果。"""

    chunk_id: UUID
    document_id: UUID
    filename: str
    chunk_index: int
    page_number: int | None
    content: str
    similarity: float


async def retrieve_document_chunks(
    session: AsyncSession,
    *,
    query: str,
    limit: int,
) -> list[RetrievedDocumentChunk]:
    """根据自然语言问题返回语义最相关的文档切片。

    参数：
        session：FastAPI 为当前请求创建的异步数据库会话。
        query：已经清理首尾空白并确认非空的用户问题。
        limit：最多返回的切片数量，API 层会将它限制在 1～10。

    返回值：
        按余弦相似度从高到低排列的 RetrievedDocumentChunk 列表。数据库中
        没有已索引切片时返回空列表。

    执行步骤：
        1. 使用与文档入库完全相同的 embedding 模型生成问题向量。
        2. 让 PostgreSQL 计算问题向量和每个切片向量的余弦距离。
        3. 按距离从小到大排序并限制返回数量。
        4. 使用 `1 - 距离` 转换为更直观的余弦相似度。

    异常：
        百炼鉴权、网络、响应校验或数据库查询异常会原样向上传递，接口不会
        把失败请求伪装成空检索结果。
    """

    # embed_texts 返回二维列表。这里只输入一个问题，所以取第一条向量。
    # 文档与问题必须使用同一个模型和相同维度，否则向量不能正确比较。
    query_vector = (await embed_texts([query]))[0]

    # cosine_distance 是 pgvector 为 SQLAlchemy 提供的表达式方法，对应
    # PostgreSQL 中的 `<=>` 运算符。距离越小，两个向量的语义越接近。
    cosine_distance = DocumentChunk.embedding.cosine_distance(query_vector).label(
        "cosine_distance"
    )

    statement = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.document_id,
            Document.filename,
            DocumentChunk.chunk_index,
            DocumentChunk.page_number,
            DocumentChunk.content,
            cosine_distance,
        )
        # JOIN 根据 document_id 取得文件名，后续可以把它作为引用来源返回。
        .join(Document, Document.id == DocumentChunk.document_id)
        # 当前只检索已经完整生成向量并成功提交的文档。
        .where(Document.status == "indexed")
        # 余弦距离越小越相关；主键作为第二排序条件，让距离相同时结果稳定。
        .order_by(cosine_distance.asc(), DocumentChunk.id.asc())
        .limit(limit)
    )

    # execute 只读取数据，不会开启需要手动 commit 的写事务。
    result = await session.execute(statement)
    rows = result.all()

    return [
        RetrievedDocumentChunk(
            chunk_id=row.chunk_id,
            document_id=row.document_id,
            filename=row.filename,
            chunk_index=row.chunk_index,
            page_number=row.page_number,
            content=row.content,
            similarity=1.0 - float(row.cosine_distance),
        )
        for row in rows
    ]
