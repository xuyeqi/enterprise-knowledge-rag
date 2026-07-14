"""提供知识库自然语言问题的最小向量检索接口。

本接口是 RAG 主链路中的 Retrieval（检索）入口。它接收用户问题，调用服务层
生成问题向量并查询 pgvector，最后返回相关切片和文件来源；当前阶段不调用
LLM，因此响应不是最终自然语言答案。
"""

# Annotated 可以把 Python 类型与 FastAPI 的 Depends 依赖说明组合在一起。
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_database_session
from app.schemas.search import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)
from app.services.retrieval import retrieve_document_chunks


# prefix="/search" 表示本文件中的空路径接口最终地址是 POST /search。
router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=KnowledgeSearchResponse)
async def search_knowledge_base(
    request: KnowledgeSearchRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> KnowledgeSearchResponse:
    """把用户问题转换为向量，并返回最相关的知识库切片。

    参数：
        request：FastAPI 根据请求 JSON 校验得到的问题和返回数量。
        session：FastAPI 通过依赖注入为本次请求创建的数据库会话。

    返回值：
        包含实际问题、结果数量以及相关切片列表的响应对象。

    执行步骤：
        1. Pydantic 在函数执行前完成空问题和 limit 范围校验。
        2. 服务层生成问题 embedding，并执行 pgvector 余弦距离查询。
        3. 把服务层结果转换为稳定的 API JSON 结构。
    """

    chunks = await retrieve_document_chunks(
        session,
        query=request.query,
        limit=request.limit,
    )

    results = [
        KnowledgeSearchResult(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            filename=chunk.filename,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            similarity=chunk.similarity,
        )
        for chunk in chunks
    ]

    return KnowledgeSearchResponse(
        query=request.query,
        result_count=len(results),
        results=results,
    )
