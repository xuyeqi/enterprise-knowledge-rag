"""验证 LangChain 知识库问答服务和 POST /answer 接口。

测试会替换真实检索、数据库和聊天模型，因此不会读取 `.env`、调用百炼或访问
PostgreSQL。它只验证 RAG 编排、提示词上下文、空知识库与低相关拒答分支，以及
HTTP 响应结构。
"""

import asyncio
from dataclasses import replace
from uuid import UUID

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from app.api import answer as answer_api
from app.db.session import get_database_session
from app.main import app
from app.schemas.answer import KnowledgeAnswerRequest
from app.services import answering as answering_service
from app.services.answering import KnowledgeAnswer
from app.services.retrieval import RetrievedDocumentChunk


CHUNK_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCUMENT_ID = UUID("22222222-2222-2222-2222-222222222222")


def make_chunk() -> RetrievedDocumentChunk:
    """创建多个测试共用的一条本地检索结果。"""

    return RetrievedDocumentChunk(
        chunk_id=CHUNK_ID,
        document_id=DOCUMENT_ID,
        filename="expense-policy.md",
        chunk_index=2,
        page_number=None,
        content="出差期间产生的出租车费用可以报销。",
        similarity=0.91,
    )


def test_generate_grounded_answer_passes_question_and_context(monkeypatch) -> None:
    """确认 LangChain 提示词包含用户问题、来源编号和召回正文。"""

    received_messages = []

    async def fake_model_call(prompt_value):
        """记录模型实际收到的消息，并返回本地假答案。"""

        received_messages.extend(prompt_value.to_messages())
        return AIMessage(content="出租车费用可以报销。")

    # RunnableLambda 实现 LangChain Runnable 协议，可以放进 `|` 组合的链中，
    # 但不会创建 HTTP 客户端或产生真实模型费用。
    fake_model = RunnableLambda(fake_model_call)
    monkeypatch.setattr(answering_service, "get_chat_model", lambda: fake_model)

    answer = asyncio.run(
        answering_service.generate_grounded_answer(
            query="打车费怎么报销？",
            chunks=[make_chunk()],
            history=[
                ("user", "公司的交通费用政策是什么？"),
                ("assistant", "公司资料包含交通费用报销规则。"),
            ],
        )
    )

    assert answer == "出租车费用可以报销。"
    message_text = "\n".join(str(message.content) for message in received_messages)
    assert "只能根据" in message_text
    assert "不在回答正文中输出 [资料N] 标记" in message_text
    assert "打车费怎么报销？" in message_text
    assert "公司的交通费用政策是什么？" in message_text
    assert "历史回答不能作为事实依据" in message_text
    assert "[资料1]" in message_text
    assert "expense-policy.md" in message_text
    assert "出租车费用可以报销" in message_text


def test_format_knowledge_context_includes_pdf_page_number() -> None:
    """确认 PDF 页码会进入模型上下文，便于答案理解资料位置。"""

    pdf_chunk = replace(make_chunk(), filename="company.pdf", page_number=3)

    context = answering_service.format_knowledge_context([pdf_chunk])

    assert "文件名：company.pdf" in context
    assert "来源页码：第 3 页" in context


def test_answer_knowledge_base_returns_sources(monkeypatch) -> None:
    """确认问答编排只把达到相似度阈值的切片交给模型并作为来源返回。"""

    chunk = make_chunk()
    low_similarity_chunk = replace(chunk, similarity=0.49)
    received_generation_input = {}
    history = [
        ("user", "公司的交通费用政策是什么？"),
        ("assistant", "公司资料包含交通费用报销规则。"),
    ]

    async def fake_retrieve_document_chunks(session, *, query: str, limit: int):
        """模拟向量检索并检查服务层传入的参数。"""

        assert session is not None
        assert query == (
            "历史问题：\n公司的交通费用政策是什么？\n"
            "当前问题：\n打车费怎么报销？"
        )
        assert limit == 3
        return [chunk, low_similarity_chunk]

    async def fake_generate_grounded_answer(*, query: str, chunks, history):
        """记录实际交给生成阶段的问题和切片。"""

        received_generation_input["query"] = query
        received_generation_input["chunks"] = chunks
        received_generation_input["history"] = history
        return "可以报销。"

    monkeypatch.setattr(
        answering_service,
        "retrieve_document_chunks",
        fake_retrieve_document_chunks,
    )
    monkeypatch.setattr(
        answering_service,
        "generate_grounded_answer",
        fake_generate_grounded_answer,
    )

    result = asyncio.run(
        answering_service.answer_knowledge_base(
            object(),
            query="打车费怎么报销？",
            limit=3,
            history=history,
        )
    )

    assert result.answer == "可以报销。"
    assert result.sources == [chunk]
    assert received_generation_input == {
        "query": "打车费怎么报销？",
        "chunks": [chunk],
        "history": history,
    }


def test_answer_knowledge_base_refuses_low_similarity_chunks(monkeypatch) -> None:
    """确认只有低相关切片时直接拒答，不调用聊天模型也不返回误导性来源。"""

    low_similarity_chunk = replace(make_chunk(), similarity=0.49)

    async def fake_retrieve_document_chunks(session, *, query: str, limit: int):
        """模拟向量库总能返回结果、但最高相似度仍然不足的真实情况。"""

        assert session is not None
        assert query == "今天天气怎么样？"
        assert limit == 3
        return [low_similarity_chunk]

    async def unexpected_generation_call(*args, **kwargs):
        """低相关检索结果如果仍触发模型调用，应立即让测试失败。"""

        raise AssertionError("low-similarity retrieval must not call chat model")

    monkeypatch.setattr(
        answering_service,
        "retrieve_document_chunks",
        fake_retrieve_document_chunks,
    )
    monkeypatch.setattr(
        answering_service,
        "generate_grounded_answer",
        unexpected_generation_call,
    )

    result = asyncio.run(
        answering_service.answer_knowledge_base(
            object(),
            query="今天天气怎么样？",
            limit=3,
        )
    )

    assert result.answer == answering_service.NO_RELEVANT_KNOWLEDGE_ANSWER
    assert result.sources == []


def test_answer_knowledge_base_skips_model_when_no_chunks(monkeypatch) -> None:
    """确认空知识库直接返回固定说明，不产生聊天模型调用。"""

    async def fake_retrieve_document_chunks(session, *, query: str, limit: int):
        """模拟数据库中没有任何已索引切片。"""

        return []

    async def unexpected_generation_call(*args, **kwargs):
        """如果空结果仍调用模型，立即让测试失败。"""

        raise AssertionError("empty retrieval must not call chat model")

    monkeypatch.setattr(
        answering_service,
        "retrieve_document_chunks",
        fake_retrieve_document_chunks,
    )
    monkeypatch.setattr(
        answering_service,
        "generate_grounded_answer",
        unexpected_generation_call,
    )

    result = asyncio.run(
        answering_service.answer_knowledge_base(
            object(),
            query="任意问题",
            limit=3,
        )
    )

    assert result.answer == answering_service.EMPTY_KNOWLEDGE_ANSWER
    assert result.sources == []


def test_answer_endpoint_returns_answer_and_sources(monkeypatch) -> None:
    """确认 POST /answer 返回清理后的问题、答案和完整引用来源。"""

    async def fake_database_session():
        """向 FastAPI 提供假会话，阻止测试连接真实数据库。"""

        yield object()

    async def fake_answer_knowledge_base(
        session,
        *,
        query: str,
        limit: int,
        history,
    ):
        """模拟完整问答服务并检查接口传入的参数。"""

        assert session is not None
        assert query == "打车费怎么报销？"
        assert limit == 2
        assert history == [
            ("user", "公司的交通费用政策是什么？"),
            ("assistant", "公司资料包含交通费用报销规则。"),
        ]
        return KnowledgeAnswer(
            answer="出租车费用可以报销。",
            sources=[make_chunk()],
        )

    app.dependency_overrides[get_database_session] = fake_database_session
    monkeypatch.setattr(
        answer_api,
        "answer_knowledge_base",
        fake_answer_knowledge_base,
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/answer",
            json={
                "query": "  打车费怎么报销？  ",
                "limit": 2,
                "history": [
                    {"role": "user", "content": "公司的交通费用政策是什么？"},
                    {
                        "role": "assistant",
                        "content": "公司资料包含交通费用报销规则。",
                    },
                ],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "query": "打车费怎么报销？",
        "answer": "出租车费用可以报销。",
        "source_count": 1,
        "sources": [
            {
                "chunk_id": str(CHUNK_ID),
                "document_id": str(DOCUMENT_ID),
                "filename": "expense-policy.md",
                "chunk_index": 2,
                "page_number": None,
                "content": "出差期间产生的出租车费用可以报销。",
                "similarity": 0.91,
            }
        ],
    }


def test_answer_request_rejects_incomplete_history() -> None:
    """确认历史消息必须由完整的 user／assistant 对组成。"""

    try:
        KnowledgeAnswerRequest.model_validate(
            {
                "query": "她的家庭怎么样？",
                "history": [{"role": "user", "content": "老板是谁？"}],
            }
        )
    except ValidationError as error:
        assert "complete user/assistant pairs" in str(error)
    else:
        raise AssertionError("incomplete history must be rejected")


def test_answer_request_rejects_wrong_history_order() -> None:
    """确认历史消息不能以 assistant 开头或连续使用同一角色。"""

    try:
        KnowledgeAnswerRequest.model_validate(
            {
                "query": "她的家庭怎么样？",
                "history": [
                    {"role": "assistant", "content": "老板是侯林希。"},
                    {"role": "user", "content": "她的家庭怎么样？"},
                ],
            }
        )
    except ValidationError as error:
        assert "alternate user then assistant" in str(error)
    else:
        raise AssertionError("wrong history order must be rejected")
