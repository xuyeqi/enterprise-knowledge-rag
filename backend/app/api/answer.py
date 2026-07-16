"""提供基于知识库检索结果生成答案的 HTTP 接口。

这个 API 是最小 RAG 闭环的入口：接收问题后调用服务层完成向量检索、上下文
增强和模型生成。普通接口一次性返回 JSON；流式接口使用 SSE 逐块返回答案，
最后再发送引用来源。
"""

# json 把流式事件内容编码为单行 JSON，避免答案中的换行破坏 SSE 消息边界。
import json
# logging 把流中断的真实异常记录在后端，便于排查，同时不给浏览器暴露内部细节。
import logging
# AsyncIterator 用于标注 StreamingResponse 消费的异步文本生成器。
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_database_session
from app.schemas.answer import KnowledgeAnswerRequest, KnowledgeAnswerResponse
from app.schemas.search import KnowledgeSearchResult
from app.services.answering import answer_knowledge_base, stream_knowledge_base_answer
from app.services.retrieval import RetrievedDocumentChunk


router = APIRouter(prefix="/answer", tags=["answer"])
logger = logging.getLogger(__name__)


def encode_sse_event(event: str, data: object) -> str:
    """把事件名和可序列化数据编码为一条标准 SSE 消息。"""

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def serialize_source(chunk: RetrievedDocumentChunk) -> dict[str, object]:
    """把服务层检索结果转换成前端稳定使用的来源结构。"""

    return KnowledgeSearchResult(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        filename=chunk.filename,
        chunk_index=chunk.chunk_index,
        page_number=chunk.page_number,
        content=chunk.content,
        similarity=chunk.similarity,
    ).model_dump(mode="json")


@router.post("", response_model=KnowledgeAnswerResponse)
async def answer_from_knowledge_base(
    request: KnowledgeAnswerRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> KnowledgeAnswerResponse:
    """根据知识库资料回答自然语言问题并返回引用切片。

    参数：
        request：FastAPI 校验后的问题、历史对话和召回数量。
        session：FastAPI 通过依赖注入创建的异步数据库会话。

    返回值：
        包含清理后问题、自然语言答案和实际引用切片的响应对象。
    """

    result = await answer_knowledge_base(
        session,
        query=request.query,
        limit=request.limit,
        history=[(message.role, message.content) for message in request.history],
    )
    sources = [
        KnowledgeSearchResult(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            filename=chunk.filename,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
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


@router.post("/stream")
async def stream_answer_from_knowledge_base(
    request: KnowledgeAnswerRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> StreamingResponse:
    """使用 SSE 逐块返回知识库答案，并在结束前发送完整引用来源。"""

    async def generate_events() -> AsyncIterator[str]:
        """把与 HTTP 无关的服务层事件转换为浏览器可读取的 SSE 文本。"""

        try:
            async for stream_event in stream_knowledge_base_answer(
                session,
                query=request.query,
                limit=request.limit,
                history=[
                    (message.role, message.content)
                    for message in request.history
                ],
            ):
                if stream_event.event == "delta":
                    yield encode_sse_event(
                        "delta",
                        {"content": stream_event.content},
                    )
                else:
                    yield encode_sse_event(
                        "sources",
                        {
                            "sources": [
                                serialize_source(chunk)
                                for chunk in stream_event.sources
                            ]
                        },
                    )
            yield encode_sse_event("done", {})
        except Exception:
            # 流开始后无法再改成普通 HTTP 错误响应，因此用明确的 error 事件通知
            # 前端停止读取。这里不回传底层异常文本，避免泄露服务或配置细节。
            logger.exception("knowledge answer stream failed")
            yield encode_sse_event(
                "error",
                {"message": "回答生成中断，请稍后重试。"},
            )

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
