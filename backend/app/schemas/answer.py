"""定义知识库问答接口的请求和响应结构。

请求模型复用向量检索接口已经验证过的问题和 limit 规则；响应模型在自然语言
答案之外保留实际交给大模型的切片，便于前端展示引用和用户核对答案依据。
"""

from pydantic import BaseModel, Field

from app.schemas.search import KnowledgeSearchRequest, KnowledgeSearchResult


class KnowledgeAnswerRequest(KnowledgeSearchRequest):
    """表示一次知识库问答请求，字段规则与检索请求保持一致。"""


class KnowledgeAnswerResponse(BaseModel):
    """表示模型答案及其可追溯的知识库来源。"""

    query: str = Field(description="去除首尾空白后的实际问题")
    answer: str = Field(description="大模型基于召回资料生成的自然语言答案")
    source_count: int = Field(description="本次实际交给大模型的引用切片数量")
    sources: list[KnowledgeSearchResult] = Field(description="答案使用的知识库切片")
