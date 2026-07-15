"""定义知识库问答接口的请求和响应结构。

请求模型复用向量检索接口已经验证过的问题和 limit 规则；响应模型在自然语言
答案之外保留实际交给大模型的切片，便于前端展示引用和用户核对答案依据。
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.search import KnowledgeSearchRequest, KnowledgeSearchResult


class ConversationMessage(BaseModel):
    """表示一条由前端回传的历史消息。"""

    role: Literal["user", "assistant"] = Field(description="消息发送方")
    content: str = Field(
        min_length=1,
        max_length=4000,
        description="已经完成的一条用户问题或助手回答",
    )

    @field_validator("content")
    @classmethod
    def strip_and_validate_content(cls, value: str) -> str:
        """清理消息首尾空白，并拒绝只包含空白的历史消息。"""

        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("history message content must not be blank")
        return stripped_value


class KnowledgeAnswerRequest(KnowledgeSearchRequest):
    """表示当前问题、召回数量和最近五轮已完成对话。"""

    history: list[ConversationMessage] = Field(
        default_factory=list,
        max_length=10,
        description="最近五轮 user／assistant 成对历史消息",
    )

    @field_validator("history")
    @classmethod
    def validate_history_order(
        cls,
        history: list[ConversationMessage],
    ) -> list[ConversationMessage]:
        """要求历史由完整的用户问题和助手回答组成，防止角色顺序混乱。"""

        if len(history) % 2 != 0:
            raise ValueError("history must contain complete user/assistant pairs")

        for index, message in enumerate(history):
            expected_role = "user" if index % 2 == 0 else "assistant"
            if message.role != expected_role:
                raise ValueError("history roles must alternate user then assistant")

        return history


class KnowledgeAnswerResponse(BaseModel):
    """表示模型答案及其可追溯的知识库来源。"""

    query: str = Field(description="去除首尾空白后的实际问题")
    answer: str = Field(description="大模型基于召回资料生成的自然语言答案")
    source_count: int = Field(description="本次实际交给大模型的引用切片数量")
    sources: list[KnowledgeSearchResult] = Field(description="答案使用的知识库切片")
