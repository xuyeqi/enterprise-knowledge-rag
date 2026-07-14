"""定义知识库向量检索接口的请求和响应结构。

这些 Pydantic 模型位于 schemas（数据结构）模块中。FastAPI 会使用它们校验
用户问题和返回结果，并在 Swagger 中自动生成字段说明。
"""

# UUID 用于描述文档和切片在 PostgreSQL 中的唯一标识符。
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class KnowledgeSearchRequest(BaseModel):
    """表示用户提交的一次知识库检索请求。"""

    # query 是用户真正想查找的自然语言问题。最大 1000 字符可以阻止把整份
    # 文档误当作问题提交，同时足够容纳当前阶段的正常问句。
    query: str = Field(
        min_length=1,
        max_length=1000,
        description="需要在知识库中检索的自然语言问题",
    )

    # limit 控制最多返回多少个相关切片。当前数据量小，默认取 3 个即可观察
    # 检索效果；限制在 10 以内可以避免未来把过多资料交给 LLM。
    limit: int = Field(
        default=3,
        ge=1,
        le=10,
        description="最多返回的相关切片数量，范围为 1～10",
    )

    @field_validator("query")
    @classmethod
    def strip_and_validate_query(cls, value: str) -> str:
        """移除问题首尾空白，并拒绝只包含空格或换行的输入。

        参数：
            value：FastAPI 从请求 JSON 中取得的原始 query 字符串。

        返回值：
            去除首尾空白后的问题，后续 embedding 和响应都使用这个值。

        异常：
            清理后没有实际内容时抛出 ValueError，Pydantic 会把它转换成
            FastAPI 的 HTTP 422 参数校验响应，不会产生百炼调用费用。
        """

        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("query must not be blank")

        return stripped_value


class KnowledgeSearchResult(BaseModel):
    """表示一个按向量相似度召回的文档切片。"""

    chunk_id: UUID = Field(description="文档切片的唯一标识符")
    document_id: UUID = Field(description="切片所属文档的唯一标识符")
    filename: str = Field(description="切片所属的原始文件名")
    chunk_index: int = Field(description="切片在原文中的顺序，从 0 开始")
    content: str = Field(description="召回切片的完整文本")
    similarity: float = Field(description="余弦相似度，数值越大表示语义越接近")


class KnowledgeSearchResponse(BaseModel):
    """表示一次问题向量检索的完整响应。"""

    query: str = Field(description="去除首尾空白后的实际检索问题")
    result_count: int = Field(description="本次实际召回的切片数量")
    results: list[KnowledgeSearchResult] = Field(description="按相似度从高到低排列的切片")
