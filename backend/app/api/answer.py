"""提供基于知识库检索结果生成答案的 HTTP 接口。

这个 API 是最小 RAG 闭环的入口：接收问题后调用服务层完成向量检索、上下文
增强和模型生成，再把答案与引用来源转换成稳定的 JSON 响应。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_database_session
from app.schemas.answer import KnowledgeAnswerRequest, KnowledgeAnswerResponse
from app.schemas.search import KnowledgeSearchResult
from app.services.answering import answer_knowledge_base


router = APIRouter(prefix="/answer", tags=["answer"])


@router.post("", response_model=KnowledgeAnswerResponse)
async def answer_from_knowledge_base(
    request: KnowledgeAnswerRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> KnowledgeAnswerResponse:
    """根据知识库资料回答自然语言问题并返回引用切片。

    参数：
        request：FastAPI 校验后的问题和召回数量。
        session：FastAPI 通过依赖注入创建的异步数据库会话。

    返回值：
        包含清理后问题、自然语言答案和实际引用切片的响应对象。
    """

    result = await answer_knowledge_base(
        session,
        query=request.query,
        limit=request.limit,
    )
    sources = [
        KnowledgeSearchResult(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            filename=chunk.filename,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            similarity=chunk.similarity,
        )
        for chunk in result.sources
    ]

    return KnowledgeAnswerResponse(
        query=request.query,
        answer=result.answer,
        source_count=len(sources),
        sources=sources,
    )
